"""Context Manager - 多层上下文构建和管理"""
import logging
from typing import Dict, Any, List
from datetime import datetime, timedelta

from src.utils.clickhouse import get_clickhouse_manager
from src.agent.memory import get_memory_manager

logger = logging.getLogger(__name__)


class ContextManager:
    """上下文管理器 - 构建多层次上下文信息"""
    
    def __init__(self):
        self.ch_manager = get_clickhouse_manager()
        self.memory_manager = get_memory_manager()
    
    def build_context(
        self,
        query: str,
        user_id: str = None,
        session_id: str = None,
        include_history: bool = True,
        include_profile: bool = True,
        include_domain: bool = True
    ) -> Dict[str, Any]:
        """
        构建完整上下文
        
        Args:
            query: 用户查询
            user_id: 用户ID
            session_id: 会话ID
            include_history: 是否包含历史对话
            include_profile: 是否包含用户画像
            include_domain: 是否包含领域知识
        
        Returns:
            上下文字典
        """
        context = {
            "query": query,
            "user_id": user_id,
            "session_id": session_id,
            "timestamp": datetime.now().isoformat(),
            "layers": {}
        }
        
        try:
            # Layer 1: 对话历史
            if include_history and session_id:
                context["layers"]["conversation"] = self._get_conversation_context(session_id)
            
            # Layer 2: 用户画像
            if include_profile and user_id:
                context["layers"]["user_profile"] = self._get_user_profile_context(user_id)
            
            # Layer 3: 领域知识
            if include_domain:
                context["layers"]["domain_knowledge"] = self._get_domain_knowledge_context(query)
            
            # Layer 4: 相关性上下文
            context["layers"]["relevance"] = self._get_relevance_context(query)
            
            logger.info(f"构建上下文完成: {len(context['layers'])}层")
            return context
        
        except Exception as e:
            logger.error(f"构建上下文失败: {e}")
            return context
    
    def _get_conversation_context(self, session_id: str) -> Dict[str, Any]:
        """获取对话历史上下文"""
        try:
            # 从Memory Manager获取短期记忆
            short_term = self.memory_manager.get_short_term_memory(session_id)
            
            return {
                "recent_messages": short_term.get("messages", [])[-5:],  # 最近5条
                "message_count": len(short_term.get("messages", [])),
                "session_start": short_term.get("created_at"),
                "topics": short_term.get("topics", [])
            }
        except Exception as e:
            logger.warning(f"获取对话历史失败: {e}")
            return {}
    
    def _get_user_profile_context(self, user_id: str) -> Dict[str, Any]:
        """获取用户画像上下文"""
        try:
            # 从Memory Manager获取用户画像
            profile = self.memory_manager.get_user_profile(user_id)
            
            return {
                "user_id": user_id,
                "preferences": profile.get("preferences", {}),
                "interests": profile.get("interests", []),
                "expertise_level": profile.get("expertise_level", "beginner"),
                "frequent_queries": profile.get("frequent_queries", [])[:3]  # 前3个
            }
        except Exception as e:
            logger.warning(f"获取用户画像失败: {e}")
            return {"user_id": user_id}
    
    def _get_domain_knowledge_context(self, query: str) -> Dict[str, Any]:
        """获取领域知识上下文"""
        try:
            # 提取查询中的关键实体
            entities = self._extract_entities(query)
            
            # 获取相关的市场信息
            market_context = self._get_market_context(entities)
            
            return {
                "entities": entities,
                "market_info": market_context,
                "domain": "hkex_stock_market"
            }
        except Exception as e:
            logger.warning(f"获取领域知识失败: {e}")
            return {"domain": "hkex_stock_market"}
    
    def _get_relevance_context(self, query: str) -> Dict[str, Any]:
        """获取相关性上下文（时间范围、数据可用性等）"""
        try:
            # 检查数据库中的最新数据时间
            latest_data = self._check_latest_data_availability()
            
            return {
                "data_freshness": latest_data,
                "suggested_time_range": self._suggest_time_range(query),
                "data_quality": "good"  # 简化版
            }
        except Exception as e:
            logger.warning(f"获取相关性上下文失败: {e}")
            return {}
    
    def _extract_entities(self, query: str) -> Dict[str, List[str]]:
        """从查询中提取实体（简化版）"""
        entities = {
            "stock_codes": [],
            "company_names": [],
            "document_types": [],
            "time_references": []
        }
        
        # 简单的关键词匹配
        query_lower = query.lower()
        
        # 检测股票代码模式 (如 00700, 00700.hk)
        import re
        stock_pattern = r'\b\d{5}(?:\.hk)?\b'
        entities["stock_codes"] = re.findall(stock_pattern, query)
        
        # 检测常见公司名
        common_companies = ["腾讯", "阿里", "小米", "美团", "京东", "比亚迪"]
        entities["company_names"] = [c for c in common_companies if c in query]
        
        # 检测文档类型
        doc_types = ["配售", "供股", "合股", "IPO", "上市", "公告"]
        entities["document_types"] = [d for d in doc_types if d in query]
        
        # 检测时间引用
        time_refs = ["最近", "今年", "去年", "本月", "上月"]
        entities["time_references"] = [t for t in time_refs if t in query]
        
        return entities
    
    def _get_market_context(self, entities: Dict[str, List[str]]) -> Dict[str, Any]:
        """获取市场上下文信息"""
        market_info = {
            "market_status": "open",  # 简化版
            "trading_day": True,
            "relevant_stocks": []
        }
        
        # 如果有股票代码，获取基本信息
        if entities.get("stock_codes"):
            for code in entities["stock_codes"][:3]:  # 最多3个
                try:
                    # 查询股票基本信息
                    stock_info = self._query_stock_info(code)
                    if stock_info:
                        market_info["relevant_stocks"].append(stock_info)
                except Exception as e:
                    logger.debug(f"查询股票{code}信息失败: {e}")
        
        return market_info
    
    def _query_stock_info(self, stock_code: str) -> Dict[str, Any] | None:
        """查询股票基本信息"""
        try:
            # 从pdf_documents表获取该股票的基本信息
            query = """
            SELECT stock_code, company_name, COUNT(*) as doc_count
            FROM pdf_documents
            WHERE stock_code = {code:String}
            GROUP BY stock_code, company_name
            LIMIT 1
            """
            result = self.ch_manager.execute_query(query, {"code": stock_code})
            
            if result:
                return {
                    "stock_code": result[0][0],
                    "company_name": result[0][1],
                    "document_count": result[0][2]
                }
        except Exception as e:
            logger.debug(f"查询股票信息失败: {e}")
        
        return None
    
    def _check_latest_data_availability(self) -> Dict[str, Any]:
        """检查最新数据可用性"""
        try:
            # 查询各类数据的最新日期
            freshness = {}
            
            tables = {
                "pdf_documents": "publish_date",
                "placing_data": "announcement_date",
                "ipo_data": "listing_date"
            }
            
            for table, date_field in tables.items():
                try:
                    query = f"SELECT MAX({date_field}) FROM {table}"
                    result = self.ch_manager.execute_query(query)
                    if result and result[0][0]:
                        latest = result[0][0]
                        # 计算距今天数
                        if isinstance(latest, str):
                            from datetime import datetime
                            latest = datetime.fromisoformat(latest.replace('Z', '+00:00'))
                        days_ago = (datetime.now() - latest).days
                        freshness[table] = {
                            "latest_date": str(latest),
                            "days_ago": days_ago
                        }
                except Exception as e:
                    logger.debug(f"检查{table}数据新鲜度失败: {e}")
            
            return freshness
        except Exception as e:
            logger.warning(f"检查数据可用性失败: {e}")
            return {}
    
    def _suggest_time_range(self, query: str) -> Dict[str, str]:
        """根据查询建议时间范围"""
        query_lower = query.lower()
        
        today = datetime.now()
        
        if "最近" in query or "近期" in query:
            return {
                "start": (today - timedelta(days=30)).strftime("%Y-%m-%d"),
                "end": today.strftime("%Y-%m-%d"),
                "description": "最近30天"
            }
        elif "今年" in query or "本年" in query:
            return {
                "start": f"{today.year}-01-01",
                "end": today.strftime("%Y-%m-%d"),
                "description": "今年至今"
            }
        elif "去年" in query:
            last_year = today.year - 1
            return {
                "start": f"{last_year}-01-01",
                "end": f"{last_year}-12-31",
                "description": "去年全年"
            }
        else:
            # 默认最近3个月
            return {
                "start": (today - timedelta(days=90)).strftime("%Y-%m-%d"),
                "end": today.strftime("%Y-%m-%d"),
                "description": "默认3个月"
            }


# 全局单例
_context_manager: ContextManager | None = None


def get_context_manager() -> ContextManager:
    """获取Context Manager单例"""
    global _context_manager
    if _context_manager is None:
        _context_manager = ContextManager()
    return _context_manager

