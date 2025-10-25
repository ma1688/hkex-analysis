"""Agent相关的Pydantic模型"""
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


class PlanStep(BaseModel):
    """计划步骤"""
    step: int
    task: str = Field(..., description="任务描述，清晰具体")
    agent: Literal["document", "market", "financial", "news"]
    params: dict = Field(default_factory=dict)
    recommended_tools: list[str] = Field(
        default_factory=list,
        description="推荐使用的工具列表，帮助Agent更准确地选择工具"
    )
    tool_params_template: dict = Field(
        default_factory=dict,
        description="工具参数模板，为工具调用提供参数建议"
    )
    depends_on: list[int] = Field(default_factory=list)
    estimated_time: Optional[float] = None


class Plan(BaseModel):
    """执行计划"""
    steps: list[PlanStep]
    reasoning: str = Field(..., description="规划理由")
    is_simple: bool = Field(..., description="是否为简单单步任务")
    estimated_total_time: Optional[float] = None


class UserProfile(BaseModel):
    """用户画像"""
    user_id: str
    preferences: dict = Field(default_factory=dict)
    watched_stocks: list[str] = Field(default_factory=list)
    query_history: list[dict] = Field(default_factory=list)
    last_active: datetime
    total_queries: int = 0
