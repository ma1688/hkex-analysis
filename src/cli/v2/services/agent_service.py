"""Agent服务层 - 封装异步Agent调用"""
from typing import AsyncIterator, Dict, Any, Optional
import logging

from src.agent.document_agent import get_document_agent, load_agent_config
from src.config.settings import get_settings

logger = logging.getLogger(__name__)


class AgentService:
    """
    Agent服务封装
    
    职责：
    - 管理Agent实例生命周期
    - 提供统一的异步调用接口
    - 处理配置加载和session管理
    """
    
    def __init__(self):
        """初始化Agent服务"""
        self._agent = None
        self._settings = get_settings()
        self._agent_config = load_agent_config("document")
        
    @property
    def agent(self):
        """延迟加载Agent实例"""
        if self._agent is None:
            self._agent = get_document_agent()
        return self._agent
    
    @property
    def model_name(self) -> str:
        """获取当前使用的模型名称"""
        return self._agent_config.get("model") or self._settings.siliconflow_fast_model
    
    @property
    def temperature(self) -> float:
        """获取当前模型温度"""
        return self._agent_config.get("temperature", 0.1)
    
    async def ask_stream(
        self,
        question: str,
        session_id: str,
        recursion_limit: int = 50
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        流式执行Agent问答
        
        Args:
            question: 用户问题
            session_id: 会话ID
            recursion_limit: 递归限制
            
        Yields:
            事件字典，格式：{"node_name": {"messages": [...]}}
        """
        input_data = {"messages": [("user", question)]}
        config = {
            "configurable": {
                "thread_id": session_id
            },
            "recursion_limit": recursion_limit
        }
        
        try:
            async for event in self.agent.astream(input_data, config):
                yield event
        except Exception as e:
            logger.error(f"Agent流式执行失败: {e}", exc_info=True)
            raise
    
    def ask_sync(
        self,
        question: str,
        session_id: str,
        recursion_limit: int = 50
    ) -> Dict[str, Any]:
        """
        同步执行Agent问答
        
        Args:
            question: 用户问题
            session_id: 会话ID
            recursion_limit: 递归限制
            
        Returns:
            完整的执行结果
        """
        input_data = {"messages": [("user", question)]}
        config = {
            "configurable": {
                "thread_id": session_id
            },
            "recursion_limit": recursion_limit
        }
        
        try:
            result = self.agent.invoke(input_data, config)
            return result
        except Exception as e:
            logger.error(f"Agent同步执行失败: {e}", exc_info=True)
            raise
    
    def extract_answer(self, result: Dict[str, Any]) -> Optional[str]:
        """
        从执行结果中提取最终答案
        
        Args:
            result: Agent执行结果
            
        Returns:
            最终答案文本，如果无法提取则返回None
        """
        try:
            messages = result.get("messages", [])
            if messages:
                last_message = messages[-1]
                if hasattr(last_message, 'content'):
                    return last_message.content
            return None
        except Exception as e:
            logger.error(f"提取答案失败: {e}")
            return None


# 全局单例
_agent_service: Optional[AgentService] = None


def get_agent_service() -> AgentService:
    """获取Agent服务单例"""
    global _agent_service
    if _agent_service is None:
        _agent_service = AgentService()
    return _agent_service

