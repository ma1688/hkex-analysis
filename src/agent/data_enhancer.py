"""数据增强器 - Layer 3"""
import logging
import asyncio
import httpx
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
import pytz
from dataclasses import dataclass
import json
import re

from src.config.settings import get_settings
from src.utils.clickhouse import get_clickhouse_manager

logger = logging.getLogger(__name__)

# 香港时区
HONGKONG_TZ = pytz.timezone('Asia/Hong_Kong')


@dataclass
class DataQuality:
    """数据质量评估结果"""
    score: float  # 0-1
    completeness: float  # 完整性
    accuracy: float  # 准确性
    timeliness: float  # 时效性
    consistency: float  # 一致性
    issues: List[str]  # 发现的问题
    recommendations: List[str]  # 改进建议


@dataclass
class MarketData:
    """市场数据结构"""
    symbol: str
    price: Optional[float] = None
    change: Optional[float] = None
    change_percent: Optional[float] = None
    volume: Optional[int] = None
    market_cap: Optional[float] = None
    timestamp: Optional[datetime] = None
    source: str = "unknown"
    quality_score: float = 0.0


@dataclass
class EnhancedData:
    """增强后的数据"""
    original_data: Dict[str, Any]
    enhanced_data: Dict[str, Any]
    market_data: Optional[MarketData] = None
    quality: Optional[DataQuality] = None
    enrichment_sources: List[str] = None
    enhancement_metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.enrichment_sources is None:
            self.enrichment_sources = []
        if self.enhancement_metadata is None:
            self.enhancement_metadata = {}


class DataEnhancer:
    """数据增强器 - Layer 3实现"""

    def __init__(self):
        self.settings = get_settings()
        self.http_client = None
        self.clickhouse_manager = None
        self.market_data_cache = {}
        self.cache_ttl = 300  # 5分钟缓存

        # 请求限流 - 针对429错误优化
        self.request_count = 0
        self.last_request_time = 0
        self.rate_limit_delay = 3.0  # 增加到3秒间隔
        self.max_requests_per_minute = 20  # 降低到每分钟20次
        self._429_retry_count = {}  # 记录每个符号的429重试次数
        self.max_429_retries = 2  # 429错误最大重试次数

        # 数据源配置
        self.data_sources = {
            "akshare": {
                "enabled": True,
                "timeout": 15,
                "priority": 1,  # 最高优先级，稳定免费
                "fallback": True,
                "description": "AkShare - 国内开源金融数据接口"
            },
            "yahoo_finance": {
                "enabled": True,
                "base_url": "https://query1.finance.yahoo.com/v8/finance/chart",
                "timeout": 10,
                "priority": 2,  # 降级为第二优先级
                "fallback": True,
                "description": "Yahoo Finance - 免费但有频率限制"
            },
            "alpha_vantage": {
                "enabled": False,  # 需要API key
                "base_url": "https://www.alphavantage.co/query",
                "timeout": 10,
                "priority": 3,
                "fallback": False,
                "description": "Alpha Vantage - 需要付费API key"
            }
        }

        # 模拟数据（用于API失败时的降级）
        self.fallback_data = {
            "default_market_data": {
                "source": "fallback",
                "quality_score": 0.3,
                "note": "数据源不可用，使用默认值"
            }
        }

    async def __aenter__(self):
        """异步上下文管理器入口"""
        self.http_client = httpx.AsyncClient(timeout=30.0)
        self.clickhouse_manager = get_clickhouse_manager()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        if self.http_client:
            await self.http_client.aclose()

    def _extract_stock_symbols(self, query: str, data: Dict[str, Any]) -> List[str]:
        """
        从查询和数据中提取股票代码

        Args:
            query: 用户查询
            data: 相关数据

        Returns:
            股票代码列表
        """
        symbols = []

        # 从查询中提取
        query_patterns = [
            r'(\d{5})\.hk',  # 00700.hk
            r'(\d{5})',      # 00700
            r'[A-Z]{1,5}\.HK',  # TCEHY.HK
            r'[A-Z]{1,5}',   # AAPL
        ]

        for pattern in query_patterns:
            matches = re.findall(pattern, query.upper())
            symbols.extend([f"{match}.HK" if len(match) == 5 else match for match in matches])

        # 从数据中提取（如果有）
        if isinstance(data, dict):
            if "stock_code" in data:
                symbols.append(data["stock_code"])
            if "symbol" in data:
                symbols.append(data["symbol"])

        # 去重并标准化
        unique_symbols = []
        for symbol in symbols:
            # 标准化股票代码格式
            if symbol.isdigit() and len(symbol) == 5:
                symbol = f"{symbol}.HK"
            elif symbol.isdigit() and len(symbol) < 5:
                symbol = f"{symbol.zfill(5)}.HK"

            if symbol not in unique_symbols:
                unique_symbols.append(symbol)

        return unique_symbols

    def _is_cache_valid(self, cache_entry: Dict) -> bool:
        """检查缓存是否有效"""
        if not cache_entry:
            return False

        cached_time = cache_entry.get("timestamp")
        if not cached_time:
            return False

        age = (datetime.now(HONGKONG_TZ) - cached_time).total_seconds()
        return age < self.cache_ttl

    async def _apply_rate_limit(self, symbol: str = ""):
        """应用请求限流 - 针对429错误优化"""
        import time

        current_time = time.time()

        # 检查429重试次数
        retry_count = self._429_retry_count.get(symbol, 0)
        if retry_count >= self.max_429_retries:
            logger.warning(f"符号 {symbol} 429错误重试次数已达上限，直接返回降级数据")
            raise httpx.HTTPStatusError("429重试次数超限", request=None, response=None)

        # 检查是否需要限流
        if current_time - self.last_request_time < 60:  # 1分钟内
            if self.request_count >= self.max_requests_per_minute:
                wait_time = 60 - (current_time - self.last_request_time)
                logger.warning(f"API请求达到限制，等待 {wait_time:.1f} 秒")
                await asyncio.sleep(wait_time)
                self.request_count = 0
                self.last_request_time = time.time()

        # 如果有429错误历史，增加延迟
        actual_delay = self.rate_limit_delay
        if retry_count > 0:
            actual_delay = self.rate_limit_delay * (2 ** retry_count)  # 指数退避
            logger.info(f"符号 {symbol} 有429错误历史，延迟增加到 {actual_delay:.1f} 秒")

        # 添加请求间隔延迟
        if self.request_count > 0 and current_time - self.last_request_time < actual_delay:
            delay = actual_delay - (current_time - self.last_request_time)
            await asyncio.sleep(delay)

        self.request_count += 1
        if current_time - self.last_request_time > 60:
            self.request_count = 1
        self.last_request_time = current_time

    def _create_fallback_market_data(self, symbol: str) -> MarketData:
        """创建降级市场数据"""
        logger.info(f"为 {symbol} 创建降级市场数据")

        return MarketData(
            symbol=symbol,
            price=None,
            change=None,
            change_percent=None,
            volume=None,
            timestamp=datetime.now(HONGKONG_TZ),
            source="fallback",
            quality_score=0.2
        )

    async def _fetch_akshare(self, symbol: str) -> Optional[MarketData]:
        """从AkShare获取港股数据"""
        try:
            import akshare as ak
            import pandas as pd
            from datetime import datetime

            # 标准化股票代码格式
            if symbol.endswith('.HK'):
                hk_code = symbol.replace('.HK', '')
                # 转换为5位数字格式
                hk_code = hk_code.zfill(5)
            else:
                hk_code = symbol.zfill(5)

            logger.info(f"从AkShare获取港股数据: {symbol} -> {hk_code}")

            # 获取港股实时数据
            data = ak.stock_hk_spot()

            # 查找对应股票代码的数据
            stock_data = data[data['代码'] == hk_code]

            if stock_data.empty:
                logger.warning(f"AkShare未找到股票代码 {hk_code} 的数据")
                return None

            # 取第一条匹配记录
            row = stock_data.iloc[0]

            # 解析数据
            price = float(row['最新价']) if pd.notna(row['最新价']) else None
            change = float(row['涨跌额']) if pd.notna(row['涨跌额']) else None
            change_percent = float(row['涨跌幅']) if pd.notna(row['涨跌幅']) else None
            volume = int(row['成交量']) if pd.notna(row['成交量']) else None

            # 解析时间
            timestamp = datetime.now(HONGKONG_TZ)  # 使用当前时间
            if pd.notna(row['日期时间']):
                try:
                    # 尝试解析时间戳
                    time_str = str(row['日期时间'])
                    timestamp = datetime.strptime(time_str, '%Y/%m/%d %H:%M:%S')
                    timestamp = HONGKONG_TZ.localize(timestamp)
                except Exception as e:
                    logger.debug(f"时间解析失败: {e}, 使用当前时间")

            market_data = MarketData(
                symbol=symbol,
                price=price,
                change=change,
                change_percent=change_percent,
                volume=volume,
                timestamp=timestamp,
                source="akshare",
                quality_score=0.9  # AkShare数据质量较高，且稳定
            )

            logger.info(f"成功从AkShare获取数据: {symbol}, 价格: {price}, 涨跌: {change}")
            return market_data

        except Exception as e:
            logger.error(f"AkShare API错误 {symbol}: {e}")
            return None

    async def get_market_data(self, symbol: str) -> MarketData:
        """
        获取市场数据

        Args:
            symbol: 股票代码

        Returns:
            市场数据
        """
        # 检查缓存
        cache_key = symbol.upper()
        if self._is_cache_valid(self.market_data_cache.get(cache_key)):
            logger.debug(f"使用缓存的市场数据: {symbol}")
            return self.market_data_cache[cache_key]["data"]

        # 应用请求限流（传递symbol用于429处理）
        try:
            await self._apply_rate_limit(symbol)
        except httpx.HTTPStatusError as e:
            # 429重试次数超限，直接返回降级数据
            logger.warning(f"符号 {symbol} 429重试次数超限，使用降级数据")
            market_data = self._create_fallback_market_data(symbol)
            self.market_data_cache[cache_key] = {
                "data": market_data,
                "timestamp": datetime.now(HONGKONG_TZ)
            }
            return market_data

        # 按优先级尝试从各个数据源获取
        market_data = None
        last_error = None

        # 按优先级排序数据源
        sorted_sources = sorted(
            [(name, config) for name, config in self.data_sources.items() if config["enabled"]],
            key=lambda x: x[1]["priority"]
        )

        for source_name, source_config in sorted_sources:
            if not source_config["enabled"]:
                continue

            try:
                if source_name == "akshare":
                    market_data = await self._fetch_akshare(symbol)
                    if market_data:
                        logger.info(f"从AkShare获取到数据: {symbol}")
                        # 重置429重试计数
                        if symbol in self._429_retry_count:
                            del self._429_retry_count[symbol]
                        break  # 成功获取数据，退出循环

                elif source_name == "yahoo_finance":
                    market_data = await self._fetch_yahoo_finance(symbol)
                    if market_data:
                        logger.info(f"从Yahoo Finance获取到数据: {symbol}")
                        # 重置429重试计数
                        if symbol in self._429_retry_count:
                            del self._429_retry_count[symbol]
                        break  # 成功获取数据，退出循环

            except httpx.HTTPStatusError as e:
                last_error = f"HTTP {e.response.status_code}"
                if source_name == "yahoo_finance":
                    if e.response.status_code == 429:
                        logger.warning(f"Yahoo Finance请求过于频繁 {symbol}: {last_error}")
                        # 记录429错误
                        self._429_retry_count[symbol] = self._429_retry_count.get(symbol, 0) + 1
                        # 增加缓存时间以减少后续请求
                        self.cache_ttl = min(self.cache_ttl * 2, 1800)  # 最多30分钟
                    elif e.response.status_code == 404:
                        logger.warning(f"Yahoo Finance找不到股票代码 {symbol}: {last_error}")
                    else:
                        logger.warning(f"Yahoo Finance HTTP错误 {symbol}: {last_error}")
                else:
                    logger.warning(f"{source_name} HTTP错误 {symbol}: {last_error}")

            except Exception as e:
                last_error = str(e)
                logger.warning(f"{source_name}获取数据失败 {symbol}: {last_error}")

        # 如果主数据源失败，尝试降级策略
        if not market_data and last_error:
            logger.info(f"主数据源失败，使用降级策略: {symbol}")
            market_data = self._create_fallback_market_data(symbol)

        # 如果完全没有数据，创建空数据对象
        if not market_data:
            logger.warning(f"无法获取市场数据，返回空数据: {symbol}")
            market_data = MarketData(
                symbol=symbol,
                source="failed",
                quality_score=0.0
            )

        # 缓存数据
        self.market_data_cache[cache_key] = {
            "data": market_data,
            "timestamp": datetime.now(HONGKONG_TZ)
        }

        return market_data

    async def _fetch_yahoo_finance(self, symbol: str) -> Optional[MarketData]:
        """从Yahoo Finance获取数据"""
        try:
            # Yahoo Finance API
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"

            response = await self.http_client.get(url)
            response.raise_for_status()

            data = response.json()

            # 解析数据
            chart = data.get("chart", {})
            result = chart.get("result", [])

            if not result:
                return None

            meta = result[0].get("meta", {})

            # 提取关键信息
            price = meta.get("regularMarketPrice")
            change = meta.get("regularMarketChange")
            change_percent = meta.get("regularMarketChangePercent")

            market_data = MarketData(
                symbol=symbol,
                price=float(price) if price else None,
                change=float(change) if change else None,
                change_percent=float(change_percent) if change_percent else None,
                timestamp=datetime.fromtimestamp(meta.get("regularMarketTime", 0), HONGKONG_TZ),
                source="yahoo_finance",
                quality_score=0.8  # Yahoo Finance数据质量较高
            )

            return market_data

        except Exception as e:
            logger.error(f"Yahoo Finance API错误 {symbol}: {e}")
            return None

    def _assess_data_quality(self, data: Dict[str, Any], context: str = "") -> DataQuality:
        """
        评估数据质量

        Args:
            data: 要评估的数据
            context: 数据上下文

        Returns:
            数据质量评估结果
        """
        completeness_score = self._assess_completeness(data)
        accuracy_score = self._assess_accuracy(data, context)
        timeliness_score = self._assess_timeliness(data)
        consistency_score = self._assess_consistency(data)

        # 计算总体质量分数
        overall_score = (completeness_score * 0.3 +
                        accuracy_score * 0.3 +
                        timeliness_score * 0.2 +
                        consistency_score * 0.2)

        # 识别问题
        issues = []
        recommendations = []

        if completeness_score < 0.7:
            issues.append("数据完整性不足")
            recommendations.append("补充缺失的关键字段")

        if accuracy_score < 0.7:
            issues.append("数据准确性存疑")
            recommendations.append("进行数据验证和清洗")

        if timeliness_score < 0.7:
            issues.append("数据时效性较差")
            recommendations.append("更新到最新数据")

        if consistency_score < 0.7:
            issues.append("数据一致性有问题")
            recommendations.append("检查数据格式和标准")

        return DataQuality(
            score=overall_score,
            completeness=completeness_score,
            accuracy=accuracy_score,
            timeliness=timeliness_score,
            consistency=consistency_score,
            issues=issues,
            recommendations=recommendations
        )

    def _assess_completeness(self, data: Dict[str, Any]) -> float:
        """评估数据完整性"""
        if not isinstance(data, dict):
            return 0.0

        total_fields = len(data)
        if total_fields == 0:
            return 0.0

        non_empty_fields = sum(1 for value in data.values()
                              if value is not None and value != "" and value != 0)

        return non_empty_fields / total_fields

    def _assess_accuracy(self, data: Dict[str, Any], context: str = "") -> float:
        """评估数据准确性"""
        # 简化的准确性评估
        score = 0.8  # 基础分数

        # 检查数值字段的合理性
        for key, value in data.items():
            if isinstance(value, (int, float)):
                if key.lower().endswith("ratio") or key.lower().endswith("percent"):
                    if not (0 <= value <= 100):
                        score -= 0.1
                elif key.lower() in ["price", "amount", "volume"]:
                    if value <= 0:
                        score -= 0.1

        return max(0.0, score)

    def _assess_timeliness(self, data: Dict[str, Any]) -> float:
        """评估数据时效性"""
        # 检查是否有时间戳
        timestamp_fields = ["date", "timestamp", "created_at", "updated_at"]

        for field in timestamp_fields:
            if field in data and data[field]:
                try:
                    if isinstance(data[field], str):
                        timestamp = datetime.fromisoformat(data[field].replace("Z", "+00:00"))
                    else:
                        timestamp = data[field]

                    # 计算数据年龄
                    age = (datetime.now(HONGKONG_TZ) - timestamp).total_seconds()
                    age_days = age / (24 * 3600)

                    # 根据年龄评分
                    if age_days <= 1:
                        return 1.0
                    elif age_days <= 7:
                        return 0.8
                    elif age_days <= 30:
                        return 0.6
                    elif age_days <= 90:
                        return 0.4
                    else:
                        return 0.2

                except Exception:
                    continue

        # 没有时间戳信息，给予中等分数
        return 0.6

    def _assess_consistency(self, data: Dict[str, Any]) -> float:
        """评估数据一致性"""
        if not isinstance(data, dict):
            return 0.0

        # 检查数据格式一致性
        score = 0.9  # 基础分数

        # 检查股票代码格式
        if "stock_code" in data:
            code = str(data["stock_code"])
            if not (code.isdigit() and len(code) == 5):
                score -= 0.2

        # 检查日期格式
        date_fields = ["date", "created_at", "updated_at"]
        for field in date_fields:
            if field in data and data[field]:
                try:
                    str(data[field])
                    # 简单的日期格式检查
                    if not re.match(r'\d{4}-\d{2}-\d{2}', str(data[field])):
                        score -= 0.1
                except Exception:
                    score -= 0.1

        return max(0.0, score)

    async def enhance_data(self, query: str, data: Dict[str, Any], context: str = "") -> EnhancedData:
        """
        增强数据

        Args:
            query: 用户查询
            data: 原始数据
            context: 数据上下文

        Returns:
            增强后的数据
        """
        logger.info(f"开始数据增强: query='{query[:50]}...'")

        enhanced_data = data.copy()
        enrichment_sources = []
        enhancement_metadata = {
            "enhanced_at": datetime.now(HONGKONG_TZ).isoformat(),
            "query_context": query[:100],
            "original_fields": list(data.keys())
        }

        # 1. 提取股票代码
        symbols = self._extract_stock_symbols(query, data)
        enhancement_metadata["extracted_symbols"] = symbols

        # 2. 获取市场数据
        market_data = None
        if symbols:
            try:
                # 为每个股票代码获取市场数据
                symbol_market_data = []
                for symbol in symbols[:3]:  # 限制最多3个股票
                    m_data = await self.get_market_data(symbol)
                    symbol_market_data.append(m_data)

                if symbol_market_data:
                    market_data = symbol_market_data[0]  # 使用第一个
                    enhanced_data["market_data"] = {
                        "symbol": market_data.symbol,
                        "current_price": market_data.price,
                        "change": market_data.change,
                        "change_percent": market_data.change_percent,
                        "data_source": market_data.source,
                        "quality_score": market_data.quality_score
                    }
                    enrichment_sources.append("yahoo_finance")
                    enhancement_metadata["market_enhancement"] = True

            except Exception as e:
                logger.error(f"市场数据增强失败: {e}")

        # 3. 数据质量评估
        quality = self._assess_data_quality(enhanced_data, context)
        enhancement_metadata["quality_assessment"] = {
            "overall_score": quality.score,
            "completeness": quality.completeness,
            "accuracy": quality.accuracy,
            "timeliness": quality.timeliness,
            "consistency": quality.consistency
        }

        # 4. 添加统计信息
        if isinstance(data, dict):
            enhanced_data["_enhancement_stats"] = {
                "total_fields": len(data),
                "enriched_fields": len(enhanced_data) - len(data),
                "data_sources": enrichment_sources,
                "quality_score": quality.score
            }

        # 5. 时间增强
        current_time = datetime.now(HONGKONG_TZ)
        enhanced_data["_enhancement_timestamp"] = current_time.isoformat()
        enhanced_data["_data_age_hours"] = self._calculate_data_age(data, current_time)

        result = EnhancedData(
            original_data=data,
            enhanced_data=enhanced_data,
            market_data=market_data,
            quality=quality,
            enrichment_sources=enrichment_sources,
            enhancement_metadata=enhancement_metadata
        )

        logger.info(f"数据增强完成，质量分数: {quality.score:.2f}")
        return result

    def _calculate_data_age(self, data: Dict[str, Any], current_time: datetime) -> Optional[float]:
        """计算数据年龄（小时）"""
        timestamp_fields = ["date", "timestamp", "created_at", "updated_at"]

        for field in timestamp_fields:
            if field in data and data[field]:
                try:
                    if isinstance(data[field], str):
                        timestamp = datetime.fromisoformat(data[field].replace("Z", "+00:00"))
                    else:
                        timestamp = data[field]

                    age_seconds = (current_time - timestamp).total_seconds()
                    return age_seconds / 3600  # 转换为小时

                except Exception:
                    continue

        return None

    def generate_enhancement_summary(self, enhanced_data: EnhancedData) -> str:
        """
        生成数据增强摘要

        Args:
            enhanced_data: 增强后的数据

        Returns:
            增强摘要文本
        """
        summary_parts = []

        # 基础信息
        if enhanced_data.quality:
            quality_score = enhanced_data.quality.score
            if quality_score >= 0.8:
                quality_desc = "优秀"
            elif quality_score >= 0.6:
                quality_desc = "良好"
            elif quality_score >= 0.4:
                quality_desc = "一般"
            else:
                quality_desc = "较差"

            summary_parts.append(f"数据质量: {quality_desc} ({quality_score:.2f})")

        # 市场数据增强
        if enhanced_data.market_data and enhanced_data.market_data.price:
            market_info = (
                f"当前股价: {enhanced_data.market_data.price:.2f} "
                f"({enhanced_data.market_data.change:+.2f}, "
                f"{enhanced_data.market_data.change_percent:+.2f}%)"
            )
            summary_parts.append(market_info)

        # 数据源
        if enhanced_data.enrichment_sources:
            sources = ", ".join(enhanced_data.enrichment_sources)
            summary_parts.append(f"数据源: {sources}")

        # 年龄信息
        if "_data_age_hours" in enhanced_data.enhanced_data:
            age_hours = enhanced_data.enhanced_data["_data_age_hours"]
            if age_hours is not None:
                if age_hours < 1:
                    age_desc = "最新"
                elif age_hours < 24:
                    age_desc = f"{age_hours:.1f}小时前"
                elif age_hours < 24 * 7:
                    age_desc = f"{age_hours/24:.1f}天前"
                else:
                    age_desc = f"{age_hours/(24*7):.1f}周前"
                summary_parts.append(f"数据时效: {age_desc}")

        return " | ".join(summary_parts) if summary_parts else "数据增强完成"


# 全局单例
_data_enhancer: Optional[DataEnhancer] = None


async def get_data_enhancer() -> DataEnhancer:
    """获取数据增强器单例"""
    global _data_enhancer
    if _data_enhancer is None:
        _data_enhancer = DataEnhancer()
        await _data_enhancer.__aenter__()
    return _data_enhancer


async def enhance_query_data(query: str, data: Dict[str, Any], context: str = "") -> EnhancedData:
    """
    快捷函数：增强查询数据

    Args:
        query: 用户查询
        data: 原始数据
        context: 数据上下文

    Returns:
        增强后的数据
    """
    enhancer = await get_data_enhancer()
    return await enhancer.enhance_data(query, data, context)