"""数据增强工具 - Layer 3演示"""
import logging
from typing import Dict, Any, Optional
from langchain_core.tools import tool

from src.agent.data_enhancer import enhance_query_data, get_data_enhancer

logger = logging.getLogger(__name__)


@tool
def enhance_market_data(query: str, stock_data: str = "") -> str:
    """
    增强市场数据（Layer 3演示工具）

    Args:
        query: 原始用户查询
        stock_data: 股票相关数据（JSON格式字符串）

    Returns:
        增强后的数据摘要
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
            return enhancer.generate_enhancement_summary(enhanced_data)

        # 运行异步任务
        summary = asyncio.run(run_enhancement())

        return f"数据增强完成：{summary}"

    except Exception as e:
        logger.error(f"数据增强失败: {e}")
        return f"数据增强失败: {str(e)}"


@tool
def get_real_time_stock_info(symbol: str) -> str:
    """
    获取实时股票信息（Layer 3演示工具）

    Args:
        symbol: 股票代码，如 '00700.HK' 或 'TSLA'

    Returns:
        股票信息摘要
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
                result_parts.append(f"质量分数: {market.quality_score:.2f}")

            if enhanced_data.quality:
                quality = enhanced_data.quality
                result_parts.append(f"数据质量评估: {quality.score:.2f}")

                if quality.issues:
                    result_parts.append(f"发现问题: {', '.join(quality.issues[:2])}")

            return "\n".join(result_parts) if result_parts else "暂无数据"

        # 运行异步任务
        info = asyncio.run(run_enhancement())

        return info

    except Exception as e:
        logger.error(f"获取股票信息失败: {e}")
        return f"获取股票信息失败: {str(e)}"


@tool
def assess_data_quality(data_json: str) -> str:
    """
    评估数据质量（Layer 3演示工具）

    Args:
        data_json: 要评估的数据（JSON格式字符串）

    Returns:
        数据质量评估报告
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