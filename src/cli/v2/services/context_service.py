"""上下文服务层 - 封装上下文注入逻辑"""
from typing import Tuple, Dict, Optional
import logging

from src.agent.context_injector import inject_query_context_async

logger = logging.getLogger(__name__)


class ContextService:
    """
    上下文注入服务封装
    
    职责：
    - 为用户查询注入上下文信息
    - 提供统一的上下文管理接口
    - 处理注入结果的格式化
    """
    
    def __init__(self):
        """初始化上下文服务"""
        pass
    
    async def enhance_query(
        self,
        question: str,
        user_id: Optional[str] = None
    ) -> Tuple[str, Dict]:
        """
        异步增强查询（添加上下文）
        
        Args:
            question: 原始问题
            user_id: 用户ID（可选）
            
        Returns:
            (增强后的查询, 上下文信息字典)
        """
        try:
            enhanced_query, context_info = await inject_query_context_async(
                question,
                user_id
            )
            return enhanced_query, context_info
        except Exception as e:
            logger.error(f"上下文注入失败: {e}", exc_info=True)
            # 失败时返回原始查询
            return question, {
                "injected": False,
                "error": str(e)
            }
    
    def format_context_info(self, context_info: Dict) -> str:
        """
        格式化上下文信息为可读字符串
        
        Args:
            context_info: 上下文信息字典
            
        Returns:
            格式化后的字符串
        """
        if not context_info.get("injected"):
            return "未注入上下文"
        
        parts = []
        confidence = context_info.get("confidence", 0)
        parts.append(f"置信度: {confidence:.2f}")
        
        injected_context = context_info.get("injected_context", [])
        if injected_context:
            parts.append(f"上下文: {injected_context[0]}")
        
        return " | ".join(parts)
    
    def should_display_context(self, context_info: Dict) -> bool:
        """
        判断是否应该显示上下文信息
        
        Args:
            context_info: 上下文信息字典
            
        Returns:
            True表示应该显示，False表示可以跳过
        """
        return context_info.get("injected", False) and \
               context_info.get("confidence", 0) > 0.3


# 全局单例
_context_service: Optional[ContextService] = None


def get_context_service() -> ContextService:
    """获取上下文服务单例"""
    global _context_service
    if _context_service is None:
        _context_service = ContextService()
    return _context_service

