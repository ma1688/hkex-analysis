"""数据增强工具 - Layer 3演示"""
import logging

from langchain_core.tools import tool

from src.agent.data_enhancer import get_data_enhancer

logger = logging.getLogger(__name__)


@tool
def enhance_market_data(query: str, stock_data: str = "") -> str:
    """增强市场数据（通过外部API获取补充信息）
    
    【适用场景】
    - 需要股票的实时市场数据补充
    - 查询IPO/配售后需要当前股价对比
    - 评估配售折让率、供股价是否合理
    
    【不适用场景】
    - 只需要历史公告数据 → 使用结构化查询工具
    - 基本信息查询 → query_*_data工具已足够
    
    【注意】此工具会调用外部API，可能较慢，仅在必要时使用

    Args:
        query: 原始用户查询
        stock_data: 股票相关数据（JSON格式字符串）

    Returns:
        增强后的数据摘要，包含市场数据和质量评估
    """
    try:
        import asyncio

        # 解析股票数据
        data = {}
        if stock_data:
            import json
            try:
                data = json.loads(stock_data)
            except json.JSONDecodeError:
                logger.warning(f"无法解析股票数据: {stock_data[:100]}...")
                data = {"raw_data": stock_data}

        # 异步执行数据增强
        async def run_enhancement():
            enhancer = await get_data_enhancer()
            enhanced_data = await enhancer.enhance_data(query, data, "tool_call")

            # 检查数据增强是否成功
            if enhanced_data is None:
                return "数据增强失败：所有数据源均无法获取数据"

            return enhancer.generate_enhancement_summary(enhanced_data)

        # 运行异步任务
        summary = asyncio.run(run_enhancement())

        return f"数据增强完成：{summary}"

    except Exception as e:
        logger.error(f"数据增强失败: {e}")
        return f"数据增强失败: {str(e)}"


@tool
def get_real_time_stock_info(symbol: str) -> str:
    """获取实时股票信息（通过外部API）
    
    【适用场景】
    - 需要当前股价、涨跌幅等实时市场数据
    - 对比配售价/供股价与当前价的差距
    - 判断当前市场状态（开盘/休市）
    
    【不适用场景】
    - 只需要公告中的历史数据
    - 需要详细的K线数据（本工具只提供基本报价）
    
    【注意】
    - 会调用外部API，可能较慢或受限流影响
    - 非交易时段返回最近收盘价
    - 包含数据质量评估和降级提示

    Args:
        symbol: 股票代码，如 '00700.HK'（港股）或 'TSLA'（美股）

    Returns:
        股票信息摘要，包含价格、涨跌、数据源、市场状态等
    """
    try:
        import asyncio
        import json

        # 准备查询和数据
        query = f"查询{symbol}的股票信息"
        data = {"symbol": symbol, "request_type": "real_time_quote"}

        # 异步执行数据增强
        async def run_enhancement():
            enhancer = await get_data_enhancer()
            enhanced_data = await enhancer.enhance_data(query, data, "real_time_query")

            # 检查数据增强是否成功
            if enhanced_data is None:
                return f"❌ 无法获取 {symbol} 的股票信息：所有数据源均失败"

            # 构建返回信息
            result_parts = []

            if enhanced_data.market_data:
                market = enhanced_data.market_data
                result_parts.append(f"股票代码: {market.symbol}")

                if market.price:
                    result_parts.append(f"当前价格: {market.price:.2f}")

                if market.change is not None:
                    result_parts.append(f"涨跌: {market.change:+.2f}")

                if market.change_percent is not None:
                    result_parts.append(f"涨跌幅: {market.change_percent:+.2f}%")

                result_parts.append(f"数据源: {market.source}")
                result_parts.append(f"数据质量: {market.quality_score:.2f}")

            if enhanced_data.quality:
                quality = enhanced_data.quality
                result_parts.append(f"质量评估: {quality.score:.2f}")

                if quality.issues:
                    result_parts.append(f"问题: {', '.join(quality.issues[:2])}")

                if market.source in ["fallback", "failed", "unavailable"]:
                    result_parts.append("⚠️  当前为降级模式")

            # 添加当前市场状态信息
            import pytz
            from datetime import datetime
            hk_tz = pytz.timezone('Asia/Hong_Kong')
            now = datetime.now(hk_tz)
            weekday = now.weekday()

            if weekday >= 5:  # 周末
                result_parts.append("📅 港股市场休市")
            elif 9.5 <= now.hour < 12 or 13 <= now.hour < 16:
                result_parts.append("📈 港股交易时段")
            elif 12 <= now.hour < 13:
                result_parts.append("☕ 港股午休时间")
            else:
                result_parts.append("📉 港股收盘")

            return "\n".join(result_parts) if result_parts else "暂无数据"

        # 运行异步任务
        info = asyncio.run(run_enhancement())

        return info

    except Exception as e:
        logger.error(f"获取股票信息失败: {e}")

        # 提供更友好的错误信息
        if "429" in str(e) or "Too Many Requests" in str(e):
            return (
                "🚫 请求过于频繁，系统已自动启用降级模式。\n"
                "• 当前显示为缓存或模拟数据\n"
                "• 建议稍后重试或使用专业股票软件查看实时数据\n"
                "• 系统将在5-30分钟后自动恢复实时数据获取"
            )
        elif "timeout" in str(e).lower():
            return "⏳  请求超时，请稍后再试或使用其他数据源。"
        elif "429重试次数超限" in str(e):
            return (
                "🔄 当前股票代码请求次数过多，已临时切换到降级模式。\n"
                f"• {symbol} 的实时数据获取已暂停\n"
                "• 建议查询其他股票代码或30分钟后再试"
            )
        else:
            return f"❌ 获取股票信息失败: {str(e)[:100]}"


@tool
def assess_data_quality(data_json: str) -> str:
    """评估数据质量（完整性、准确性、时效性、一致性）
    
    【适用场景】
    - 判断查询结果的可信度
    - 评估数据是否完整或存在缺失
    - 识别数据中的潜在问题
    - 提供数据改进建议
    
    【评估维度】
    - 完整性：字段是否齐全
    - 准确性：数据是否合理
    - 时效性：数据是否过时
    - 一致性：数据是否矛盾
    
    【返回】包含质量评分、发现的问题和改进建议

    Args:
        data_json: 要评估的数据（JSON格式字符串）

    Returns:
        数据质量评估报告，包含总体评分、各项细分评分、问题和建议
    """
    try:
        import asyncio
        import json

        # 解析数据
        try:
            data = json.loads(data_json)
        except json.JSONDecodeError:
            return "数据格式错误：无法解析JSON"

        if not isinstance(data, dict):
            return "数据格式错误：需要JSON对象"

        # 异步执行质量评估
        async def run_assessment():
            enhancer = await get_data_enhancer()
            quality = enhancer._assess_data_quality(data, "tool_assessment")

            # 构建评估报告
            report_parts = []

            # 总体评分
            score_desc = "优秀" if quality.score >= 0.8 else \
                "良好" if quality.score >= 0.6 else \
                    "一般" if quality.score >= 0.4 else "较差"
            report_parts.append(f"总体质量: {score_desc} ({quality.score:.2f})")

            # 各项评分
            report_parts.append(f"完整性: {quality.completeness:.2f}")
            report_parts.append(f"准确性: {quality.accuracy:.2f}")
            report_parts.append(f"时效性: {quality.timeliness:.2f}")
            report_parts.append(f"一致性: {quality.consistency:.2f}")

            # 问题和建议
            if quality.issues:
                report_parts.append("\n发现问题:")
                for issue in quality.issues[:3]:  # 限制显示数量
                    report_parts.append(f"  • {issue}")

            if quality.recommendations:
                report_parts.append("\n改进建议:")
                for rec in quality.recommendations[:3]:  # 限制显示数量
                    report_parts.append(f"  • {rec}")

            return "\n".join(report_parts)

        # 运行异步任务
        report = asyncio.run(run_assessment())

        return report

    except Exception as e:
        logger.error(f"数据质量评估失败: {e}")
        return f"数据质量评估失败: {str(e)}"
