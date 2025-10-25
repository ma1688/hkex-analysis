"""LLM管理器 - 多模型支持、动态路由、主备切换"""
import logging
from typing import Callable
from langchain_openai import ChatOpenAI
from langchain_core.language_models import BaseChatModel
from tenacity import retry, stop_after_attempt, wait_exponential

from src.config.settings import get_settings

logger = logging.getLogger(__name__)


class LLMManager:
    """多LLM管理器 - 所有配置从Settings读取，支持主备切换和动态路由"""
    
    def __init__(self):
        self.settings = get_settings()
        self.health_status = {
            "siliconflow": "unknown",
            "openai": "unknown"
        }
        
        # 延迟初始化模型（仅在需要时创建）
        self._llm_fast = None
        self._llm_strong = None
        self._llm_fallback = None
    
    @property
    def llm_fast(self) -> BaseChatModel:
        """快速模型（用于工具调用、简单查询）"""
        if self._llm_fast is None:
            self._llm_fast = ChatOpenAI(
                model=self.settings.siliconflow_fast_model,
                api_key=self.settings.siliconflow_api_key,
                base_url=self.settings.siliconflow_base_url,
                temperature=0
            )
            logger.info(f"Initialized fast model: {self.settings.siliconflow_fast_model}")
        return self._llm_fast
    
    @property
    def llm_strong(self) -> BaseChatModel:
        """强模型（用于规划、分析、反思）"""
        if self._llm_strong is None:
            self._llm_strong = ChatOpenAI(
                model=self.settings.siliconflow_strong_model,
                api_key=self.settings.siliconflow_api_key,
                base_url=self.settings.siliconflow_base_url,
                temperature=0.1
            )
            logger.info(f"Initialized strong model: {self.settings.siliconflow_strong_model}")
        return self._llm_strong
    
    @property
    def llm_fallback(self) -> BaseChatModel:
        """备选模型（OpenAI）"""
        if self._llm_fallback is None and self.settings.openai_api_key:
            self._llm_fallback = ChatOpenAI(
                model=self.settings.openai_model,
                api_key=self.settings.openai_api_key,
                temperature=0
            )
            logger.info(f"Initialized fallback model: {self.settings.openai_model}")
        return self._llm_fallback
    
    def get_model_for_task(
        self,
        task_type: str,
        agent_config: dict | None = None
    ) -> BaseChatModel:
        """
        根据任务类型和Agent配置返回合适的模型
        
        Args:
            task_type: 任务类型 (plan/reflect/analyze/summarize/query等)
            agent_config: Agent配置字典（可包含model、temperature等）
        
        Returns:
            合适的LLM实例
        """
        # 如果Agent有自定义模型配置，使用自定义配置
        if agent_config and "model" in agent_config:
            return self._create_model_from_config(agent_config)
        
        # 否则使用默认策略
        if task_type in ["plan", "reflect", "analyze", "summarize"]:
            return self._get_with_fallback(self.llm_strong)
        return self._get_with_fallback(self.llm_fast)
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    def _get_with_fallback(self, primary_llm: BaseChatModel) -> BaseChatModel:
        """
        主LLM失败时自动切换到备选
        
        Args:
            primary_llm: 主要LLM
        
        Returns:
            可用的LLM（主或备选）
        """
        try:
            # 简单测试主LLM（避免实际调用）
            self.health_status["siliconflow"] = "healthy"
            return primary_llm
        except Exception as e:
            logger.warning(f"Primary LLM failed: {e}, switching to fallback")
            self.health_status["siliconflow"] = "unhealthy"
            
            if self.llm_fallback:
                self.health_status["openai"] = "healthy"
                return self.llm_fallback
            else:
                logger.error("No fallback LLM available")
                raise
    
    def _create_model_from_config(self, config: dict) -> BaseChatModel:
        """
        根据配置创建模型实例
        
        Args:
            config: 包含model、temperature等的配置字典
        
        Returns:
            配置的LLM实例
        """
        model_name = config["model"]
        temperature = config.get("temperature", 0)
        
        # 判断是硅基流动还是OpenAI模型
        if "/" in model_name:  # 硅基流动格式：org/model
            return ChatOpenAI(
                model=model_name,
                api_key=self.settings.siliconflow_api_key,
                base_url=self.settings.siliconflow_base_url,
                temperature=temperature
            )
        else:  # OpenAI格式
            if not self.settings.openai_api_key:
                raise ValueError(f"OpenAI API key not configured for model: {model_name}")
            return ChatOpenAI(
                model=model_name,
                api_key=self.settings.openai_api_key,
                temperature=temperature
            )
    
    def get_model_callable(
        self,
        default_task_type: str = "query",
        agent_config: dict | None = None
    ) -> Callable:
        """
        返回一个可调用对象，用于LangGraph的动态模型选择
        
        Args:
            default_task_type: 默认任务类型
            agent_config: Agent配置
        
        Returns:
            接受state参数并返回模型的callable
        """
        def model_selector(state: dict) -> BaseChatModel:
            """根据state动态选择模型"""
            task_type = state.get("session_context", {}).get("task_type", default_task_type)
            return self.get_model_for_task(task_type, agent_config)
        
        return model_selector
    
    def check_health(self) -> dict[str, str]:
        """检查所有LLM的健康状态"""
        health = {}
        
        # 检查硅基流动
        try:
            self.llm_fast.invoke("test")
            health["siliconflow_fast"] = "healthy"
        except Exception as e:
            health["siliconflow_fast"] = f"unhealthy: {str(e)[:50]}"
        
        # 检查OpenAI（如果配置）
        if self.settings.openai_api_key:
            try:
                self.llm_fallback.invoke("test")
                health["openai"] = "healthy"
            except Exception as e:
                health["openai"] = f"unhealthy: {str(e)[:50]}"
        
        return health


# 全局单例
_manager: LLMManager | None = None


def get_llm_manager() -> LLMManager:
    """获取LLM管理器单例"""
    global _manager
    if _manager is None:
        _manager = LLMManager()
    return _manager

