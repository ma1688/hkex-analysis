"""Supervisor - 主协调器，使用LangGraph构建"""
import logging
from typing import Annotated, TypedDict, Literal
import operator

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from src.agent.document_agent import get_document_agent
from src.agent.planner import get_planner
from src.agent.reflector import get_reflector
from src.agent.memory import get_memory_manager
from src.agent.context import get_context_manager
from src.agent.state import SupervisorState

logger = logging.getLogger(__name__)


class Supervisor:
    """
    Supervisor协调器 - LangGraph状态机
    
    工作流程:
    1. 接收用户查询
    2. 构建上下文
    3. 生成执行计划
    4. 路由到适当的Agent
    5. 执行并收集结果
    6. 反思评估
    7. 返回最终答案
    """
    
    def __init__(self):
        self.planner = get_planner()
        self.reflector = get_reflector()
        self.memory_manager = get_memory_manager()
        self.context_manager = get_context_manager()
        self.document_agent = get_document_agent()
        
        # 创建LangGraph状态机
        self.graph = self._build_graph()
    
    def _build_graph(self) -> StateGraph:
        """构建LangGraph状态机"""
        # 定义状态图
        workflow = StateGraph(SupervisorState)
        
        # 添加节点
        workflow.add_node("build_context", self._build_context_node)
        workflow.add_node("plan", self._plan_node)
        workflow.add_node("route", self._route_node)
        workflow.add_node("execute_document", self._execute_document_node)
        workflow.add_node("reflect", self._reflect_node)
        workflow.add_node("finalize", self._finalize_node)
        
        # 设置入口点
        workflow.set_entry_point("build_context")
        
        # 添加边
        workflow.add_edge("build_context", "plan")
        workflow.add_edge("plan", "route")
        
        # 条件路由
        workflow.add_conditional_edges(
            "route",
            self._route_decision,
            {
                "document": "execute_document",
                "end": "finalize"
            }
        )
        
        workflow.add_edge("execute_document", "reflect")
        
        # 反思后的条件边
        workflow.add_conditional_edges(
            "reflect",
            self._reflect_decision,
            {
                "continue": "route",  # 继续执行
                "finalize": "finalize"
            }
        )
        
        workflow.add_edge("finalize", END)
        
        # 编译并添加checkpointer
        checkpointer = MemorySaver()
        return workflow.compile(checkpointer=checkpointer)
    
    def _build_context_node(self, state: SupervisorState) -> SupervisorState:
        """构建上下文节点"""
        logger.info("步骤1: 构建上下文")
        
        context = self.context_manager.build_context(
            query=state["query"],
            user_id=state.get("user_id"),
            session_id=state.get("session_id")
        )
        
        state["context"] = context
        state["messages"].append({
            "role": "system",
            "content": f"上下文已构建: {len(context.get('layers', {}))}层"
        })
        
        return state
    
    def _plan_node(self, state: SupervisorState) -> SupervisorState:
        """规划节点"""
        logger.info("步骤2: 生成执行计划")
        
        user_profile = state.get("context", {}).get("layers", {}).get("user_profile", {})
        plan = self.planner.create_plan(
            query=state["query"],
            user_profile=user_profile
        )
        
        state["plan"] = plan
        state["current_step"] = 0
        state["messages"].append({
            "role": "system",
            "content": f"计划生成: {len(plan.get('steps', []))}步"
        })
        
        logger.info(f"计划: {len(plan.get('steps', []))}步, 简单={plan.get('is_simple', False)}")
        return state
    
    def _route_node(self, state: SupervisorState) -> SupervisorState:
        """路由节点 - 决定下一步"""
        current_step = state.get("current_step", 0)
        plan_steps = state.get("plan", {}).get("steps", [])
        
        if current_step < len(plan_steps):
            next_step = plan_steps[current_step]
            state["next_agent"] = next_step.get("agent", "document")
            state["current_task"] = next_step.get("task", state["query"])
            logger.info(f"路由到: {state['next_agent']} - 任务: {state['current_task'][:50]}...")
        else:
            state["next_agent"] = "end"
            logger.info("所有步骤完成，准备结束")
        
        return state
    
    def _route_decision(self, state: SupervisorState) -> Literal["document", "end"]:
        """路由决策"""
        next_agent = state.get("next_agent", "end")
        
        if next_agent == "document":
            return "document"
        else:
            return "end"
    
    def _execute_document_node(self, state: SupervisorState) -> SupervisorState:
        """执行Document Agent"""
        logger.info("步骤3: 执行Document Agent")
        
        task = state.get("current_task", state["query"])
        session_id = state.get("session_id", "default")
        
        try:
            # 调用Document Agent
            config = {
                "configurable": {
                    "thread_id": session_id
                }
            }
            
            result = self.document_agent.invoke(
                {"messages": [("user", task)]},
                config
            )
            
            # 提取结果
            messages = result.get("messages", [])
            answer = messages[-1].content if messages else "无法生成答案"
            
            # 保存结果
            state["results"].append({
                "step": state["current_step"],
                "agent": "document",
                "task": task,
                "answer": answer
            })
            
            state["messages"].append({
                "role": "assistant",
                "content": answer
            })
            
            logger.info(f"Document Agent执行完成，答案长度: {len(answer)}")
        
        except Exception as e:
            logger.error(f"Document Agent执行失败: {e}")
            state["results"].append({
                "step": state["current_step"],
                "agent": "document",
                "task": task,
                "error": str(e)
            })
        
        # 移动到下一步
        state["current_step"] += 1
        
        return state
    
    def _reflect_node(self, state: SupervisorState) -> SupervisorState:
        """反思节点"""
        logger.info("步骤4: 反思评估")
        
        # 获取当前结果
        current_results = state.get("results", [])
        if not current_results:
            state["should_continue"] = False
            return state
        
        # 评估最新结果
        latest_result = current_results[-1]
        
        reflection = self.reflector.reflect(
            query=state["query"],
            plan=state.get("plan", {}).get("steps", []),
            current_step=state.get("current_step", 0),
            results=latest_result
        )
        
        state["reflection"] = reflection
        
        # 决定是否继续
        retry_count = state.get("retry_count", 0)
        should_continue = self.reflector.should_continue(
            reflection,
            max_retries=3,
            retry_count=retry_count
        )
        
        state["should_continue"] = should_continue
        
        if reflection.get("should_retry"):
            state["retry_count"] = retry_count + 1
            logger.info(f"反思建议重试 (尝试 {state['retry_count']}/3)")
        else:
            logger.info(f"反思评估: 质量={reflection.get('quality_score', 0):.2f}")
        
        return state
    
    def _reflect_decision(self, state: SupervisorState) -> Literal["continue", "finalize"]:
        """反思决策 - 是否继续执行"""
        # 检查是否还有未完成的步骤
        current_step = state.get("current_step", 0)
        total_steps = len(state.get("plan", {}).get("steps", []))
        
        # 如果还有步骤且反思建议继续
        if current_step < total_steps and state.get("should_continue", False):
            return "continue"
        
        # 否则结束
        return "finalize"
    
    def _finalize_node(self, state: SupervisorState) -> SupervisorState:
        """最终化节点 - 生成最终答案"""
        logger.info("步骤5: 生成最终答案")
        
        # 收集所有结果
        results = state.get("results", [])
        
        if not results:
            final_answer = "抱歉，无法生成答案。"
        elif len(results) == 1:
            # 单步骤，直接使用结果
            final_answer = results[0].get("answer", "无法生成答案")
        else:
            # 多步骤，合成答案
            final_answer = self._synthesize_final_answer(state["query"], results)
        
        state["final_answer"] = final_answer
        
        # 保存到记忆
        if state.get("session_id"):
            self.memory_manager.add_message(
                session_id=state["session_id"],
                role="user",
                content=state["query"]
            )
            self.memory_manager.add_message(
                session_id=state["session_id"],
                role="assistant",
                content=final_answer
            )
        
        logger.info("最终答案已生成")
        return state
    
    def _synthesize_final_answer(self, query: str, results: list) -> str:
        """合成多个结果为最终答案"""
        # 简化版：直接合并
        answers = [r.get("answer", "") for r in results if r.get("answer")]
        
        if not answers:
            return "无法生成答案"
        
        # 如果只有一个答案，直接返回
        if len(answers) == 1:
            return answers[0]
        
        # 多个答案，合并
        synthesized = f"综合分析结果：\n\n"
        for i, answer in enumerate(answers, 1):
            synthesized += f"{i}. {answer}\n\n"
        
        return synthesized.strip()
    
    def run(
        self,
        query: str,
        user_id: str = None,
        session_id: str = None
    ) -> dict:
        """
        运行Supervisor
        
        Args:
            query: 用户查询
            user_id: 用户ID
            session_id: 会话ID
        
        Returns:
            包含最终答案的字典
        """
        # 初始状态
        initial_state = SupervisorState(
            query=query,
            user_id=user_id,
            session_id=session_id or "default",
            messages=[],
            context={},
            plan={},
            current_step=0,
            results=[],
            reflection={},
            should_continue=True,
            retry_count=0,
            next_agent="",
            current_task="",
            final_answer=""
        )
        
        # 配置
        config = {
            "configurable": {
                "thread_id": session_id or "default"
            }
        }
        
        # 执行图
        try:
            logger.info(f"Supervisor开始执行: {query[:50]}...")
            final_state = self.graph.invoke(initial_state, config)
            
            return {
                "answer": final_state.get("final_answer", "无法生成答案"),
                "steps": len(final_state.get("results", [])),
                "reflection": final_state.get("reflection", {}),
                "success": True
            }
        
        except Exception as e:
            logger.error(f"Supervisor执行失败: {e}", exc_info=True)
            return {
                "answer": f"执行失败: {str(e)}",
                "steps": 0,
                "reflection": {},
                "success": False,
                "error": str(e)
            }


# 全局单例
_supervisor: Supervisor | None = None


def get_supervisor() -> Supervisor:
    """获取Supervisor单例"""
    global _supervisor
    if _supervisor is None:
        _supervisor = Supervisor()
    return _supervisor

