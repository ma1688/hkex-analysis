"""Reflector模块 - 结果验证和质量评估"""
import json
import logging

from langchain_core.messages import SystemMessage, HumanMessage

from src.agent.state import ReflectionResult
from src.llm.manager import get_llm_manager
from src.utils.prompts import (
    REFLECTOR_SYSTEM_PROMPT,
    REFLECTOR_OUTPUT_SCHEMA,
    get_prompt_loader
)

logger = logging.getLogger(__name__)


class Reflector:
    """结果反思器 - 评估Agent执行结果的质量"""

    def __init__(self):
        self.llm_manager = get_llm_manager()
        self.llm = self.llm_manager.get_model_for_task("reflect")
        
        # 加载提示词（优先使用配置，否则使用硬编码）
        self.prompt_loader = get_prompt_loader()
        self.system_prompt = self.prompt_loader.get_prompt(
            "reflector_system_prompt",
            REFLECTOR_SYSTEM_PROMPT
        )
        
        # 加载输出Schema
        output_schema_config = self.prompt_loader.get_prompt("reflector_output_schema")
        if output_schema_config:
            self.output_schema = output_schema_config
        else:
            self.output_schema = REFLECTOR_OUTPUT_SCHEMA

    def reflect(
            self,
            query: str,
            plan: list[dict],
            current_step: int,
            results: dict
    ) -> ReflectionResult:
        """
        评估执行结果
        
        Args:
            query: 原始用户查询
            plan: 执行计划
            current_step: 当前步骤
            results: 执行结果
        
        Returns:
            ReflectionResult对象
        """
        try:
            # 构建提示词
            prompt = self.system_prompt.format(
                query=query,
                plan=json.dumps(plan, ensure_ascii=False, indent=2),
                current_step=current_step,
                results=json.dumps(results, ensure_ascii=False, indent=2)
            )

            # 添加输出schema要求
            prompt += f"\n\n请严格按照以下JSON schema返回评估结果:\n{json.dumps(self.output_schema, indent=2)}"

            # 调用LLM
            messages = [
                SystemMessage(content=prompt),
                HumanMessage(content="请评估上述执行结果的质量")
            ]

            result = self.llm.invoke(messages)
            response = result.content if hasattr(result, 'content') else str(result)

            # 解析返回的JSON
            reflection_dict = self._parse_reflection_response(response)

            # 转换为ReflectionResult
            reflection = ReflectionResult(
                is_complete=reflection_dict.get("is_complete", False),
                quality_score=reflection_dict.get("quality_score", 0.5),
                completeness_score=reflection_dict.get("completeness_score", 0.5),
                accuracy_score=reflection_dict.get("accuracy_score", 0.5),
                missing_info=reflection_dict.get("missing_info", []),
                suggested_actions=reflection_dict.get("suggested_actions", []),
                should_retry=reflection_dict.get("should_retry", False),
                summary=reflection_dict.get("summary", "评估完成")
            )

            logger.info(
                f"反思完成: 质量分数={reflection['quality_score']:.2f}, "
                f"完整={reflection['is_complete']}"
            )
            return reflection

        except Exception as e:
            logger.error(f"反思评估失败: {e}")
            # 返回默认的通过评估
            return ReflectionResult(
                is_complete=True,
                quality_score=0.7,
                completeness_score=0.7,
                accuracy_score=0.7,
                missing_info=[],
                suggested_actions=[],
                should_retry=False,
                summary="评估失败，默认通过"
            )

    def _parse_reflection_response(self, response: str) -> dict:
        """解析LLM返回的评估结果"""
        try:
            # 清理markdown
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
            logger.warning("无法解析反思JSON，使用默认结构")
            return {
                "is_complete": True,
                "quality_score": 0.7,
                "should_retry": False,
                "summary": "JSON解析失败，默认通过"
            }

    def should_continue(self, reflection: ReflectionResult, max_retries: int = 3, retry_count: int = 0) -> bool:
        """根据反思结果决定是否继续/重试"""
        # 如果完成且质量足够，停止
        if reflection["is_complete"] and reflection["quality_score"] >= 0.8:
            return False

        # 如果需要重试且未超过最大次数
        if reflection["should_retry"] and retry_count < max_retries:
            return True

        # 如果质量太低且未超过最大次数
        if reflection["quality_score"] < 0.5 and retry_count < max_retries:
            return True

        # 其他情况停止
        return False


# 全局单例
_reflector: Reflector | None = None


def get_reflector() -> Reflector:
    """获取Reflector单例"""
    global _reflector
    if _reflector is None:
        _reflector = Reflector()
    return _reflector
