"""Memory Manager - 记忆管理（短期+长期）"""
import logging
from collections import deque
from typing import Dict, List, Any
import json
from datetime import datetime

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage

from src.config.settings import get_settings

logger = logging.getLogger(__name__)


class MemoryManager:
    """
    记忆管理器
    
    功能：
    - 短期记忆：会话历史（最近N条消息）
    - 长期记忆：用户画像、偏好、历史查询模式
    - 上下文摘要：自动压缩长对话
    """
    
    def __init__(self, max_short_term: int = None):
        self.settings = get_settings()
        self.max_short_term = max_short_term or self.settings.memory_max_messages
        
        # 短期记忆存储（会话级别）
        self._short_term: Dict[str, deque] = {}
        
        # 长期记忆存储（用户级别）
        self._long_term: Dict[str, Dict[str, Any]] = {}
        
        # 会话元数据
        self._session_metadata: Dict[str, Dict[str, Any]] = {}
    
    # ========== 短期记忆 ==========
    
    def add_message(self, session_id: str, role: str, content: str):
        """添加消息到短期记忆
        
        Args:
            session_id: 会话ID
            role: 消息角色（user/assistant/system）
            content: 消息内容
        """
        if session_id not in self._short_term:
            self._short_term[session_id] = deque(maxlen=self.max_short_term)
        
        # 创建消息对象
        if role == "user":
            message = HumanMessage(content=content)
        elif role == "assistant":
            message = AIMessage(content=content)
        else:
            message = SystemMessage(content=content)
        
        self._short_term[session_id].append(message)
        logger.debug(f"Added {role} message to session {session_id}, total: {len(self._short_term[session_id])}")
    
    def get_messages(self, session_id: str, limit: int = None) -> List[BaseMessage]:
        """获取会话的消息历史"""
        if session_id not in self._short_term:
            return []
        
        messages = list(self._short_term[session_id])
        if limit:
            messages = messages[-limit:]
        
        return messages
    
    def get_short_term_memory(self, session_id: str) -> Dict[str, Any]:
        """获取短期记忆摘要
        
        Args:
            session_id: 会话ID
        
        Returns:
            包含消息列表和元数据的字典
        """
        messages = self.get_messages(session_id)
        metadata = self.get_session_metadata(session_id) or {}
        
        return {
            "messages": messages,
            "created_at": metadata.get("created_at"),
            "topics": metadata.get("topics", [])
        }
    
    def clear_session(self, session_id: str):
        """清空会话记忆"""
        if session_id in self._short_term:
            self._short_term[session_id].clear()
            logger.info(f"Cleared session {session_id}")
    
    # ========== 长期记忆 ==========
    
    def update_user_profile(self, user_id: str, profile_update: Dict[str, Any]):
        """更新用户画像"""
        if user_id not in self._long_term:
            self._long_term[user_id] = {
                "user_id": user_id,
                "created_at": datetime.now().isoformat(),
                "preferences": {},
                "query_history": [],
                "favorite_stocks": [],
                "interaction_count": 0
            }
        
        # 合并更新
        self._long_term[user_id].update(profile_update)
        self._long_term[user_id]["updated_at"] = datetime.now().isoformat()
        
        logger.debug(f"Updated user profile for {user_id}")
    
    def get_user_profile(self, user_id: str) -> Dict[str, Any]:
        """获取用户画像"""
        return self._long_term.get(user_id, {})
    
    def record_query(self, user_id: str, query: str, query_type: str = None):
        """记录用户查询历史"""
        profile = self.get_user_profile(user_id)
        
        if "query_history" not in profile:
            profile["query_history"] = []
        
        # 添加查询记录
        query_record = {
            "query": query,
            "type": query_type,
            "timestamp": datetime.now().isoformat()
        }
        profile["query_history"].append(query_record)
        
        # 限制历史长度（保留最近100条）
        if len(profile["query_history"]) > 100:
            profile["query_history"] = profile["query_history"][-100:]
        
        # 增加交互计数
        profile["interaction_count"] = profile.get("interaction_count", 0) + 1
        
        self.update_user_profile(user_id, profile)
    
    def get_relevant_history(self, user_id: str, current_query: str, limit: int = 5) -> List[str]:
        """获取相关的历史查询（简化版：返回最近的）"""
        profile = self.get_user_profile(user_id)
        history = profile.get("query_history", [])
        
        # 简化实现：返回最近N条
        recent = history[-limit:] if len(history) > limit else history
        return [h["query"] for h in recent]
    
    # ========== 会话元数据 ==========
    
    def set_session_metadata(self, session_id: str, key: str, value: Any):
        """设置会话元数据"""
        if session_id not in self._session_metadata:
            self._session_metadata[session_id] = {}
        
        self._session_metadata[session_id][key] = value
    
    def get_session_metadata(self, session_id: str, key: str = None) -> Any:
        """获取会话元数据"""
        if session_id not in self._session_metadata:
            return None if key else {}
        
        if key:
            return self._session_metadata[session_id].get(key)
        return self._session_metadata[session_id]
    
    # ========== 上下文构建 ==========
    
    def build_context(self, session_id: str, user_id: str = None) -> Dict[str, Any]:
        """
        构建完整上下文
        
        Returns:
            包含短期记忆、长期记忆、元数据的上下文字典
        """
        context = {
            "session_id": session_id,
            "messages": self.get_messages(session_id),
            "metadata": self.get_session_metadata(session_id)
        }
        
        if user_id:
            context["user_profile"] = self.get_user_profile(user_id)
        
        return context
    
    # ========== 持久化（简化版，内存存储） ==========
    
    def save_to_file(self, filepath: str):
        """保存记忆到文件（简化版）"""
        data = {
            "long_term": self._long_term,
            "session_metadata": self._session_metadata,
            "saved_at": datetime.now().isoformat()
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Memory saved to {filepath}")
    
    def load_from_file(self, filepath: str):
        """从文件加载记忆（简化版）"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self._long_term = data.get("long_term", {})
            self._session_metadata = data.get("session_metadata", {})
            
            logger.info(f"Memory loaded from {filepath}")
        except FileNotFoundError:
            logger.warning(f"Memory file not found: {filepath}")
        except Exception as e:
            logger.error(f"Failed to load memory: {e}")


# 全局单例
_memory_manager: MemoryManager | None = None


def get_memory_manager() -> MemoryManager:
    """获取Memory Manager单例"""
    global _memory_manager
    if _memory_manager is None:
        _memory_manager = MemoryManager()
    return _memory_manager
