"""Agent服务层 - 封装异步Agent调用"""
from typing import AsyncIterator, Dict, Any, Optional
import logging
import asyncio

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
        self._interrupted = False

    def interrupt(self):
        """中断当前执行"""
        self._interrupted = True
        logger.info("Agent执行被中断")

    def reset_interrupt(self):
        """重置中断标志"""
        self._interrupted = False

    def check_interrupt(self) -> bool:
        """检查是否被中断"""
        return self._interrupted

    async def _check_interrupt_periodically(self):
        """定期检查中断标志（每20ms检查一次）"""
        while not self._interrupted:
            await asyncio.sleep(0.02)  # 20ms检查一次，确保快速响应
        logger.info("Agent执行检测到中断信号")
        
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
        # 重置中断标志
        self.reset_interrupt()

        input_data = {"messages": [("user", question)]}
        config = {
            "configurable": {
                "thread_id": session_id
            },
            "recursion_limit": recursion_limit
        }

        try:
            # 启动中断检查任务
            interrupt_task = asyncio.create_task(self._check_interrupt_periodically())

            # 创建事件流迭代器
            event_stream = self.agent.astream(input_data, config)
            
            # 使用队列来缓存事件，避免阻塞
            event_queue = asyncio.Queue(maxsize=10)
            stream_done = asyncio.Event()
            stream_error = None

            async def _consume_stream():
                """后台任务：消费事件流"""
                nonlocal stream_error
                try:
                    async for event in event_stream:
                        if self._interrupted:
                            logger.info("检测到中断信号，停止消费事件流")
                            break
                        await event_queue.put(event)
                        # 每次放入事件后，快速检查中断标志
                        await asyncio.sleep(0)  # 让出控制权
                except Exception as e:
                    stream_error = e
                    logger.error(f"消费事件流失败: {e}")
                finally:
                    stream_done.set()

            # 启动后台消费任务
            consume_task = asyncio.create_task(_consume_stream())

            try:
                # 持续从队列中取事件，同时监控中断标志
                while not stream_done.is_set() or not event_queue.empty():
                    # 检查中断
                    if self._interrupted:
                        logger.info("Agent执行被中断，停止生成事件")
                        break

                    # 使用超时来避免永久阻塞（50ms超时，确保快速响应）
                    try:
                        event = await asyncio.wait_for(event_queue.get(), timeout=0.05)
                        yield event
                    except asyncio.TimeoutError:
                        # 超时后继续循环，检查中断标志
                        continue

                    # 再次检查中断（在yield后立即检查）
                    if self._interrupted:
                        logger.info("Agent执行被中断（在yield后）")
                        break

                # 检查是否有错误
                if stream_error:
                    raise stream_error

            finally:
                # 清理任务
                if not consume_task.done():
                    consume_task.cancel()
                    try:
                        await consume_task
                    except asyncio.CancelledError:
                        pass

                if not interrupt_task.done():
                    interrupt_task.cancel()
                    try:
                        await interrupt_task
                    except asyncio.CancelledError:
                        pass

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

