"""Planner模块 - 任务规划和分解"""
import json
import logging

import yaml
from langchain_core.messages import SystemMessage, HumanMessage

from src.agent.schemas import Plan, PlanStep
from src.llm.manager import get_llm_manager
from src.utils.prompts import (
    PLANNER_SYSTEM_PROMPT,
    PLANNER_FEW_SHOT_EXAMPLES,
    get_prompt_loader
)

logger = logging.getLogger(__name__)


class Planner:
    """任务规划器 - 将复杂查询分解为多步骤执行计划"""

    def __init__(self):
        self.llm_manager = get_llm_manager()
        self.llm = self.llm_manager.get_model_for_task("plan")
        
        # 加载提示词（优先使用配置，否则使用默认硬编码）
        self.prompt_loader = get_prompt_loader()
        self.system_prompt = self.prompt_loader.get_prompt(
            "planner_system_prompt",
            PLANNER_SYSTEM_PROMPT
        )
        
        # 加载few-shot示例
        few_shot_config = self.prompt_loader.get_prompt("planner_few_shot_examples")
        if few_shot_config:
            # 如果配置文件提供了示例，使用配置的
            self.few_shot_examples = few_shot_config
        else:
            # 否则使用硬编码的默认示例
            self.few_shot_examples = PLANNER_FEW_SHOT_EXAMPLES

    def create_plan(
            self,
            query: str,
            user_profile: dict = None
    ) -> Plan:
        """
        创建执行计划
        
        Args:
            query: 用户查询
            user_profile: 用户画像（可选）
        
        Returns:
            Plan对象，包含步骤列表
        """
        try:
            # 构建提示词
            profile_str = json.dumps(user_profile, ensure_ascii=False) if user_profile else "无"
            prompt = self.system_prompt.format(
                query=query,
                user_profile=profile_str
            )

            # 添加few-shot示例
            examples_str = "\n\n示例:\n"
            for i, example in enumerate(self.few_shot_examples, 1):
                examples_str += f"\n示例{i}:\n"
                examples_str += f"查询: {example['query']}\n"
                examples_str += f"计划: {json.dumps(example['plan'], ensure_ascii=False, indent=2)}\n"

            full_prompt = prompt + examples_str

            # 调用LLM
            messages = [
                SystemMessage(content=full_prompt),
                HumanMessage(content=f"请为以下查询生成执行计划:\n{query}")
            ]

            result = self.llm.invoke(messages)
            response = result.content if hasattr(result, 'content') else str(result)

            # 解析返回的JSON
            plan_dict = self._parse_plan_response(response)

            # 转换为Plan对象
            plan = Plan(**plan_dict)

            logger.info(
                f"生成计划: {len(plan.steps)}步, "
                f"简单任务={plan.is_simple}"
            )
            return plan

        except Exception as e:
            logger.error(f"生成计划失败: {e}")
            # 返回默认的单步计划
            return Plan(
                steps=[
                    PlanStep(
                        step=1,
                        task=query,
                        agent="document",
                        params={},
                        depends_on=[]
                    )
                ],
                reasoning="规划失败，使用默认单步执行",
                is_simple=True
            )

    def _parse_plan_response(self, response: str) -> dict:
        """解析LLM返回的计划"""
        try:
            # 尝试直接解析JSON
            # 可能需要清理markdown代码块标记
            response = response.strip()
            if response.startswith("```json"):
                response = response[7:]
            if response.startswith("```"):
                response = response[3:]
            if response.endswith("```"):
                response = response[:-3]
            response = response.strip()

            return json.loads(response)
        except json.JSONDecodeError:
            # 如果解析失败，返回默认结构
            logger.warning("无法解析计划JSON，使用默认结构")
            return {
                "steps": [
                    {
                        "step": 1,
                        "task": "执行查询",
                        "agent": "document",
                        "params": {},
                        "depends_on": []
                    }
                ],
                "reasoning": "JSON解析失败",
                "is_simple": True
            }


# 全局单例
_planner: Planner | None = None


def get_planner() -> Planner:
    """获取Planner单例"""
    global _planner
    if _planner is None:
        _planner = Planner()
    return _planner
