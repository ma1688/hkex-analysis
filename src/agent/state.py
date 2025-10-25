"""Agent状态定义"""
from datetime import datetime
from operator import add
from typing import TypedDict, Annotated, Optional, Literal

from langgraph.graph import MessagesState


class SupervisorState(MessagesState):
    """Supervisor主状态"""
    # 规划
    plan: list[dict]
    current_step: int

    # 执行
    agent_results: dict  # {agent_name: result}
    reflection_notes: Annotated[list[str], add]

    # 会话
    user_id: Optional[str]
    session_id: str
    user_profile: dict
    session_context: dict

    # 元数据
    processing_start: datetime
    tool_calls: Annotated[list[dict], add]
    error_count: int


class TaskStep(TypedDict):
    """任务步骤"""
    step: int
    task: str
    agent: Literal["document", "market", "financial", "news"]
    params: dict
    depends_on: list[int]
    status: Literal["pending", "running", "completed", "failed"]
    result: Optional[dict]
    error: Optional[str]


class ReflectionResult(TypedDict):
    """反思结果"""
    is_complete: bool
    quality_score: float  # 0-1
    completeness_score: float
    accuracy_score: float
    missing_info: list[str]
    suggested_actions: list[str]
    should_retry: bool
    summary: str
