"""上下文自动注入系统 - Layer 2"""
import asyncio
import logging
import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import pytz

# Layer 3数据增强导入
try:
    from .data_enhancer import enhance_query_data, EnhancedData

    LAYER_3_AVAILABLE = True
except ImportError:
    LAYER_3_AVAILABLE = False
    logging.warning("Layer 3 data enhancement not available")

# 香港时区
HONGKONG_TZ = pytz.timezone('Asia/Hong_Kong')

logger = logging.getLogger(__name__)


class ContextInjector:
    """上下文自动注入器 - 为用户查询自动添加相关上下文"""

    def __init__(self):
        self.time_patterns = self._compile_time_patterns()
        self.market_patterns = self._compile_market_patterns()
        self.business_patterns = self._compile_business_patterns()

    def _compile_time_patterns(self) -> List[re.Pattern]:
        """编译时间相关关键词模式"""
        patterns = [
            # 明确时间问题
            r'现在.*?几点|当前.*?时间|现在.*?时间|目前.*?时间',
            r'今天.*?日期|今天.*?号|今天.*?几号',
            r'现在.*?星期|今天.*?星期|今天是.*?星期',
            r'现在.*?年|今年.*?年|当前.*?年份',

            # 相对时间问题
            r'最近|近期|近段时间|最近一段时间',
            r'昨天|前天|明天|后天',
            r'上周|本周|下周|这周|那周',
            r'上个月|这个月|下个月|本月|当月',
            r'去年|今年|明年|当年',

            # 时间范围查询
            r'.*?天前|.*?小时前|.*?分钟前|.*?周前|.*?月前|.*?年前',
            r'.*?天后|.*?小时后|.*?周后|.*?月后|.*?年后',
            r'.*?之内|.*?以内|.*?期间|.*?时间段',

            # 特定时间查询
            r'截止.*?|截至.*?|到.*?为止|在.*?之前|在.*?之后',
            r'从.*?开始|始于.*?|自.*?起',
            r'到.*?结束|至.*?|直到.*?',
        ]
        return [re.compile(pattern, re.IGNORECASE) for pattern in patterns]

    def _compile_market_patterns(self) -> List[re.Pattern]:
        """编译市场相关关键词模式"""
        patterns = [
            # 市场状态
            r'开盘|休市|收市|交易时间|市场状态',
            r'开盘.*?时间|收市.*?时间|交易.*?时间',
            r'早上.*?开盘|下午.*?收盘',
            r'港股.*?开盘|港股.*?休市|港股.*?交易',

            # 交易相关
            r'交易|买卖|成交|涨跌|涨跌幅',
            r'股价|股票|证券|市场|行情',
            r'买入|卖出|持有|持仓',

            # 市场时间
            r'上午.*?时段|下午.*?时段',
            r'午休.*?时间|休市.*?时间',
            r'早市|晚市|上午盘|下午盘',
        ]
        return [re.compile(pattern, re.IGNORECASE) for pattern in patterns]

    def _compile_business_patterns(self) -> List[re.Pattern]:
        """编译业务相关关键词模式"""
        patterns = [
            # 数据时效性
            r'最新.*?数据|近期.*?公告|最新.*?消息',
            r'当前.*?状况|最新.*?情况|最新.*?动态',
            r'实时.*?信息|最新.*?信息|即时.*?消息',

            # 决策相关
            r'是否.*?现在|应该.*?现在|当前.*?建议',
            r'现在.*?操作|目前.*?策略|当下.*?决定',

            # 趋势分析
            r'最近.*?趋势|近期.*?表现|当前.*?走势',
            r'最新.*?发展|近期.*?变化|当前.*?形势',
        ]
        return [re.compile(pattern, re.IGNORECASE) for pattern in patterns]

    def analyze_query_context(self, query: str) -> Dict[str, any]:
        """
        分析查询需要的上下文类型

        Args:
            query: 用户查询

        Returns:
            包含上下文需求的字典
        """
        context_needs = {
            "time_sensitive": False,
            "market_aware": False,
            "business_critical": False,
            "detected_patterns": [],
            "confidence": 0.0
        }

        # 检查时间相关模式
        time_matches = 0
        for pattern in self.time_patterns:
            if pattern.search(query):
                time_matches += 1
                context_needs["detected_patterns"].append(f"time:{pattern.pattern}")

        # 检查市场相关模式
        market_matches = 0
        for pattern in self.market_patterns:
            if pattern.search(query):
                market_matches += 1
                context_needs["detected_patterns"].append(f"market:{pattern.pattern}")

        # 检查业务相关模式
        business_matches = 0
        for pattern in self.business_patterns:
            if pattern.search(query):
                business_matches += 1
                context_needs["detected_patterns"].append(f"business:{pattern.pattern}")

        # 确定上下文需求
        total_patterns = len(self.time_patterns) + len(self.market_patterns) + len(self.business_patterns)
        total_matches = time_matches + market_matches + business_matches

        if time_matches > 0:
            context_needs["time_sensitive"] = True
        if market_matches > 0:
            context_needs["market_aware"] = True
        if business_matches > 0:
            context_needs["business_critical"] = True

        # 计算置信度
        context_needs["confidence"] = total_matches / max(total_patterns, 1)

        return context_needs

    def generate_time_context(self) -> str:
        """
        生成时间上下文信息

        Returns:
            自然语言的时间上下文描述
        """
        try:
            now_hk = datetime.now(HONGKONG_TZ)

            # 基础时间信息
            weekdays = ['星期一', '星期二', '星期三', '星期四', '星期五', '星期六', '星期日']
            weekday = weekdays[now_hk.weekday()]
            time_str = now_hk.strftime("%Y年%m月%d日 %H:%M")

            # 时段描述
            hour = now_hk.hour
            if 5 <= hour < 12:
                time_period = "上午"
            elif 12 <= hour < 14:
                time_period = "中午"
            elif 14 <= hour < 18:
                time_period = "下午"
            elif 18 <= hour < 22:
                time_period = "晚上"
            else:
                time_period = "深夜"

            context_parts = [f"当前时间：{time_str} ({weekday}) {time_period}"]

            # 市场状态
            weekday_num = now_hk.weekday()
            if weekday_num < 5:  # 工作日
                current_time = (now_hk.hour, now_hk.minute)

                # 港股交易时间
                morning_start = (9, 30)
                morning_end = (12, 0)
                afternoon_start = (13, 0)
                afternoon_end = (16, 0)

                if morning_start <= current_time < morning_end:
                    market_status = "港股上午交易时段，市场开盘中"
                elif morning_end <= current_time < afternoon_start:
                    market_status = "港股午休时间，市场暂时休市"
                elif afternoon_start <= current_time < afternoon_end:
                    market_status = "港股下午交易时段，市场开盘中"
                elif current_time >= afternoon_end:
                    market_status = "港股今日交易已结束"
                else:
                    market_status = "港股市场尚未开盘"

                context_parts.append(market_status)
            else:
                context_parts.append("周末港股市场休市")

            return "；".join(context_parts) + "。"

        except Exception as e:
            logger.error(f"生成时间上下文失败: {e}")
            return "时间信息获取失败。"

    async def inject_context_async(self, query: str, user_id: Optional[str] = None,
                                   tool_data: Optional[Dict] = None) -> Tuple[str, Dict]:
        """
        异步为查询注入上下文信息（包含Layer 3数据增强）

        Args:
            query: 原始用户查询
            user_id: 用户ID（可选，用于个性化上下文）
            tool_data: 工具返回的数据（可选，用于Layer 3增强）

        Returns:
            增强后的查询和上下文信息
        """
        # 分析查询需求
        context_info = self.analyze_query_context(query)

        # 如果不需要任何上下文，直接返回原查询
        if not any([
            context_info["time_sensitive"],
            context_info["market_aware"],
            context_info["business_critical"]
        ]):
            # 仍然尝试Layer 3数据增强
            if LAYER_3_AVAILABLE and tool_data:
                try:
                    enhanced_data = await enhance_query_data(query, tool_data, "context_injection")
                    if enhanced_data.quality and enhanced_data.quality.score > 0.7:
                        summary = self._generate_layer_3_summary(enhanced_data)
                        enhanced_query = f"{summary}\n\n用户查询：{query}"
                        return enhanced_query, {
                            "injected": True,
                            "reason": "layer_3_only",
                            "layer_3_enhancement": True,
                            "enhanced_data": enhanced_data.enhanced_data
                        }
                except Exception as e:
                    logger.warning(f"Layer 3增强失败: {e}")

            return query, {"injected": False, "reason": "no_context_needed"}

        # 生成Layer 2上下文
        context_parts = []

        if context_info["time_sensitive"] or context_info["market_aware"]:
            time_context = self.generate_time_context()
            context_parts.append(f"[时间上下文] {time_context}")

        # 如果是业务关键查询，添加数据时效性提醒
        if context_info["business_critical"]:
            now_hk = datetime.now(HONGKONG_TZ)
            date_str = now_hk.strftime("%Y-%m-%d")
            context_parts.append(f"[数据时效性] 基于查询日期 {date_str} 的数据分析")

        # Layer 3数据增强
        layer_3_summary = None
        if LAYER_3_AVAILABLE and tool_data:
            try:
                enhanced_data = await enhance_query_data(query, tool_data, "context_injection")
                if enhanced_data.quality and enhanced_data.quality.score > 0.5:
                    layer_3_summary = self._generate_layer_3_summary(enhanced_data)
                    context_parts.append(f"[数据增强] {layer_3_summary}")
            except Exception as e:
                logger.warning(f"Layer 3增强失败: {e}")

        # 构建增强查询
        if context_parts:
            context_prefix = "\n".join(context_parts)
            enhanced_query = f"{context_prefix}\n\n用户查询：{query}"

            injection_info = {
                "injected": True,
                "context_types": {
                    "time_sensitive": context_info["time_sensitive"],
                    "market_aware": context_info["market_aware"],
                    "business_critical": context_info["business_critical"]
                },
                "confidence": context_info["confidence"],
                "detected_patterns": context_info["detected_patterns"][:5],  # 限制返回的模式数量
                "injected_context": context_parts,
                "layer_3_enhanced": layer_3_summary is not None
            }

            logger.info(f"上下文注入完成（包含Layer 3增强），置信度: {context_info['confidence']:.2f}")
            return enhanced_query, injection_info

        return query, {"injected": False, "reason": "no_patterns_matched"}

    def inject_context(self, query: str, user_id: Optional[str] = None) -> Tuple[str, Dict]:
        """
        为查询注入上下文信息（同步版本，保持兼容性）

        Args:
            query: 原始用户查询
            user_id: 用户ID（可选，用于个性化上下文）

        Returns:
            增强后的查询和上下文信息
        """
        # 对于同步调用，不包含Layer 3数据增强
        return asyncio.run(self.inject_context_async(query, user_id, None))

    def _generate_layer_3_summary(self, enhanced_data) -> str:
        """
        生成Layer 3数据增强摘要

        Args:
            enhanced_data: 增强后的数据

        Returns:
            摘要文本
        """
        summary_parts = []

        # 质量信息
        if enhanced_data.quality:
            quality_score = enhanced_data.quality.score
            if quality_score >= 0.8:
                quality_desc = "优秀"
            elif quality_score >= 0.6:
                quality_desc = "良好"
            elif quality_score >= 0.4:
                quality_desc = "一般"
            else:
                quality_desc = "需改进"
            summary_parts.append(f"数据质量{quality_desc}")

        # 市场数据信息
        if enhanced_data.market_data and enhanced_data.market_data.price:
            price_info = (
                f"当前股价 {enhanced_data.market_data.price:.2f} "
                f"({enhanced_data.market_data.change:+.2f}, {enhanced_data.market_data.change_percent:+.1f}%)"
            )
            summary_parts.append(price_info)

        # 时效性信息
        if "_data_age_hours" in enhanced_data.enhanced_data:
            age_hours = enhanced_data.enhanced_data["_data_age_hours"]
            if age_hours is not None:
                if age_hours < 1:
                    age_desc = "实时"
                elif age_hours < 24:
                    age_desc = f"{age_hours:.0f}小时内"
                elif age_hours < 24 * 7:
                    age_desc = f"{age_hours / 24:.0f}天内"
                else:
                    age_desc = f"{age_hours / (24 * 7):.0f}周内"
                summary_parts.append(f"数据时效{age_desc}")

        return "；".join(summary_parts) if summary_parts else "数据已增强"


# 全局单例
_context_injector: Optional[ContextInjector] = None


def get_context_injector() -> ContextInjector:
    """获取上下文注入器单例"""
    global _context_injector
    if _context_injector is None:
        _context_injector = ContextInjector()
    return _context_injector


def inject_query_context(query: str, user_id: Optional[str] = None) -> Tuple[str, Dict]:
    """
    快捷函数：为查询注入上下文

    Args:
        query: 用户查询
        user_id: 用户ID（可选）

    Returns:
        增强后的查询和上下文信息
    """
    injector = get_context_injector()
    return injector.inject_context(query, user_id)
