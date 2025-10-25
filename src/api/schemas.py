"""API请求/响应数据模型"""
from pydantic import BaseModel, Field
from typing import Optional, Literal, Any
from datetime import datetime


class QueryRequest(BaseModel):
    """问答请求"""
    question: str = Field(..., min_length=1, description="用户问题")
    session_id: Optional[str] = Field(None, description="会话ID")
    user_id: Optional[str] = Field(None, description="用户ID")
    stream: bool = Field(False, description="是否流式返回")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "question": "查询腾讯控股最近的配售公告",
                "session_id": "sess_abc123",
                "user_id": "user_456"
            }
        }
    }


class ToolCallRecord(BaseModel):
    """工具调用记录"""
    tool_name: str
    tool_input: dict
    tool_output: str
    timestamp: datetime
    agent: str


class QueryResponse(BaseModel):
    """问答响应"""
    answer: str = Field(..., description="最终答案")
    session_id: str
    user_id: Optional[str] = None
    plan: Optional[list[dict]] = None
    tool_calls: list[ToolCallRecord] = Field(default_factory=list)
    reflection_notes: list[str] = Field(default_factory=list)
    processing_time: float
    metadata: dict = Field(default_factory=dict)


class StreamEvent(BaseModel):
    """流式事件"""
    event: Literal[
        "start", "plan", "step", "progress",
        "tool_call", "tool_result", "reflection", 
        "answer", "error", "done"
    ]
    data: dict
    timestamp: datetime = Field(default_factory=datetime.now)


class SessionHistoryResponse(BaseModel):
    """会话历史"""
    session_id: str
    messages: list[dict]
    total: int
    offset: int = 0
    limit: int = 50
    metadata: dict = Field(default_factory=dict)


class HealthResponse(BaseModel):
    """健康检查响应"""
    status: Literal["healthy", "degraded", "unhealthy"]
    services: dict[str, str]  # service_name: status
    timestamp: datetime
    version: str


class ToolInfo(BaseModel):
    """工具信息"""
    name: str
    description: str
    parameters: dict
    agent: str
    enabled: bool = True

