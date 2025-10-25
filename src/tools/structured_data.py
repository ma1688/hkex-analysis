"""结构化数据查询工具 - 查询IPO/配售/供股/合股数据"""
import json
import logging

from langchain_core.tools import tool

from src.utils.clickhouse import get_clickhouse_client
from src.utils.text_cleaner import clean_list

logger = logging.getLogger(__name__)


@tool
def query_placing_data(
        stock_code: str,
        start_date: str = None,
        end_date: str = None,
        limit: int = 10
) -> str:
    """查询配售公告数据
    
    【适用场景】
    - 用户明确询问"配售"相关信息
    - 需要配售价、新股比例、承销商等结构化字段
    - 快速获取配售数据摘要，无需完整公告原文
    - 对比多家公司的配售条款
    
    【不适用场景】
    - 需要完整公告原文和详细条款 → 使用 retrieve_chunks
    - 不确定是否为配售公告 → 先用 search_documents 确认文档类型
    - 需要供股数据 → 使用 query_rights_data
    - 需要合股数据 → 使用 query_consolidation_data
    
    【前置条件】
    - 必须提供 stock_code（格式：5位数字+.hk，如 00700.hk）
    - 如需按时间筛选，提供 start_date/end_date（格式：YYYY-MM-DD）
    
    【返回格式】
    JSON数组，每个元素包含：
    - stock_code（股票代码）、company_name（公司名）
    - announcement_date（公告日期）
    - placing_price（配售价）、current_price（当前价）
    - new_share_ratio（配售比例）
    - placing_agent（承销商）、completion_date（完成日期）
    - status（状态）
    
    【后续工具链】
    - 如需更多详细条款 → retrieve_chunks(doc_id=xxx, keyword="配售详情")
    - 如需对比其他公司 → 再次调用本工具查询另一家公司，然后用 compare_data
    - 如需提取关键信息 → extract_key_info(text=result, info_type="terms")
    
    【使用示例】
    query_placing_data(stock_code="00700.hk", start_date="2024-01-01", limit=5)
    
    Args:
        stock_code: 股票代码，格式如'00700.hk'（必需）
        start_date: 起始日期 YYYY-MM-DD（可选）
        end_date: 结束日期 YYYY-MM-DD（可选）
        limit: 返回数量，默认10，建议5-20
        
    Returns:
        JSON格式的配售数据列表
    """
    try:
        client = get_clickhouse_client()

        # 构建查询条件
        where_clauses = [f"stock_code = '{stock_code}'"]
        if start_date:
            where_clauses.append(f"announcement_date >= '{start_date}'")
        if end_date:
            where_clauses.append(f"announcement_date <= '{end_date}'")

        where_str = " AND ".join(where_clauses)

        query = f"""
        SELECT 
            stock_code,
            company_name,
            announcement_date,
            placing_price,
            new_share_ratio,
            current_price,
            placing_agent,
            completion_date,
            status
        FROM placing_data
        WHERE {where_str}
        ORDER BY announcement_date DESC
        LIMIT {limit}
        """

        results = client.query(query).result_rows

        # 转换为字典列表
        data = []
        for row in results:
            data.append({
                "stock_code": row[0],
                "company_name": row[1],
                "announcement_date": str(row[2]),
                "placing_price": row[3],
                "new_share_ratio": row[4],
                "current_price": row[5],
                "placing_agent": row[6],
                "completion_date": str(row[7]) if row[7] else None,
                "status": row[8]
            })

        logger.info(f"查询配售数据: {stock_code}, 返回{len(data)}条记录")
        # 清理文本中的无效字符
        cleaned_data = clean_list(data)
        return json.dumps(cleaned_data, ensure_ascii=False, indent=2)

    except Exception as e:
        logger.error(f"查询配售数据失败: {e}")
        return json.dumps({"error": str(e)}, ensure_ascii=False)


@tool
def query_ipo_data(
        stock_code: str = None,
        start_date: str = None,
        end_date: str = None,
        limit: int = 10
) -> str:
    """查询IPO上市数据
    
    【适用场景】
    - 查询特定公司的IPO信息（提供stock_code）
    - 查询某个时间段的IPO列表（提供start_date/end_date）
    - 获取IPO发行价、募资额、上市日期等结构化信息
    - 分析IPO市场趋势
    
    【不适用场景】
    - 需要IPO招股书详细内容 → 使用 search_documents + retrieve_chunks
    - 查询配售/供股/合股数据 → 使用对应的专用工具
    - 需要上市后的股价表现 → 使用 enhance_market_data
    
    【前置条件】
    - stock_code 可选（格式：5位数字+.hk）
    - start_date/end_date 可选（格式：YYYY-MM-DD）
    - 至少提供一个筛选条件，否则返回最近的IPO
    
    【返回格式】
    JSON数组，每个元素包含：
    - stock_code（股票代码）、company_name（公司名）
    - listing_date（上市日期）
    - offer_price（发行价）、total_fundraising（募资总额）
    - expense_ratio（费用率）、market_value（市值）
    - placing_ratio（配售比例）、industry（行业）
    
    【后续工具链】
    - 如需招股书详情 → search_documents(stock_code=xxx, document_type="招股书")
    - 如需对比多个IPO → 多次调用本工具，然后用 compare_data
    - 如需分析IPO表现 → enhance_market_data(stock_code=xxx)
    
    【使用示例】
    # 查询特定公司
    query_ipo_data(stock_code="00700.hk")
    
    # 查询时间段
    query_ipo_data(start_date="2024-01-01", end_date="2024-12-31", limit=50)
    
    Args:
        stock_code: 股票代码（可选，如'00638.hk'）
        start_date: 起始上市日期 YYYY-MM-DD（可选）
        end_date: 结束日期（可选）
        limit: 返回数量，默认10，建议10-50
        
    Returns:
        JSON格式的IPO数据列表
    """
    try:
        client = get_clickhouse_client()

        # 构建查询条件
        where_clauses = []
        if stock_code:
            where_clauses.append(f"stock_code = '{stock_code}'")
        if start_date:
            where_clauses.append(f"listing_date >= '{start_date}'")
        if end_date:
            where_clauses.append(f"listing_date <= '{end_date}'")

        where_str = " AND ".join(where_clauses) if where_clauses else "1=1"

        query = f"""
        SELECT 
            stock_code,
            company_name,
            listing_date,
            offer_price,
            total_fundraising,
            expense_ratio,
            market_value,
            placing_ratio,
            industry
        FROM ipo_data
        WHERE {where_str}
        ORDER BY listing_date DESC
        LIMIT {limit}
        """

        results = client.query(query).result_rows

        # 转换为字典列表
        data = []
        for row in results:
            data.append({
                "stock_code": row[0],
                "company_name": row[1],
                "listing_date": row[2],
                "offer_price": row[3],
                "total_fundraising": row[4],
                "expense_ratio": row[5],
                "market_value": row[6],
                "placing_ratio": row[7],
                "industry": row[8]
            })

        logger.info(f"查询IPO数据: {stock_code or 'ALL'}, 返回{len(data)}条记录")
        # 清理文本中的无效字符
        cleaned_data = clean_list(data)
        return json.dumps(cleaned_data, ensure_ascii=False, indent=2)

    except Exception as e:
        logger.error(f"查询IPO数据失败: {e}")
        return json.dumps({"error": str(e)}, ensure_ascii=False)


@tool
def query_rights_data(
        stock_code: str,
        start_date: str = None,
        end_date: str = None,
        limit: int = 10
) -> str:
    """查询供股数据
    
    【适用场景】
    - 用户明确询问"供股"相关信息
    - 需要供股价、供股比例、包销商等结构化字段
    - 查询供股的时间安排（除权日、交易起止日）
    - 对比多家公司的供股方案
    
    【不适用场景】
    - 需要完整供股章程详细条款 → 使用 retrieve_chunks
    - 查询配售数据 → 使用 query_placing_data（注意区分配售vs供股）
    - 查询合股数据 → 使用 query_consolidation_data
    
    【前置条件】
    - 必须提供 stock_code（格式：5位数字+.hk）
    - 可选时间筛选 start_date/end_date（格式：YYYY-MM-DD）
    
    【返回格式】
    JSON数组，每个元素包含：
    - stock_code、company_name、announcement_date
    - rights_price（供股价）、rights_ratio（供股比例，如"1供2"）
    - current_price（当前价）、underwriter（包销商）
    - ex_rights_date（除权日）
    - rights_trading_start/end（供股权交易起止日）
    - status（状态）
    
    【后续工具链】
    - 如需供股章程详情 → retrieve_chunks(keyword="供股详情")
    - 如需对比其他公司 → 再次调用本工具，然后用 compare_data
    - 如需分析供股影响 → enhance_market_data 获取除权前后股价
    
    【使用示例】
    query_rights_data(stock_code="00122.hk", limit=5)
    
    Args:
        stock_code: 股票代码，格式如'00122.hk'（必需）
        start_date: 起始公告日期 YYYY-MM-DD（可选）
        end_date: 结束日期（可选）
        limit: 返回数量，默认10，建议5-20
        
    Returns:
        JSON格式的供股数据列表
    """
    try:
        client = get_clickhouse_client()

        # 构建查询条件
        where_clauses = [f"stock_code = '{stock_code}'"]
        if start_date:
            where_clauses.append(f"announcement_date >= '{start_date}'")
        if end_date:
            where_clauses.append(f"announcement_date <= '{end_date}'")

        where_str = " AND ".join(where_clauses)

        query = f"""
        SELECT 
            stock_code,
            company_name,
            announcement_date,
            rights_price,
            rights_ratio,
            current_price,
            underwriter,
            ex_rights_date,
            rights_trading_start,
            rights_trading_end,
            status
        FROM rights_data
        WHERE {where_str}
        ORDER BY announcement_date DESC
        LIMIT {limit}
        """

        results = client.query(query).result_rows

        # 转换为字典列表
        data = []
        for row in results:
            data.append({
                "stock_code": row[0],
                "company_name": row[1],
                "announcement_date": str(row[2]),
                "rights_price": row[3],
                "rights_ratio": row[4],
                "current_price": row[5],
                "underwriter": row[6],
                "ex_rights_date": str(row[7]) if row[7] else None,
                "rights_trading_start": str(row[8]) if row[8] else None,
                "rights_trading_end": str(row[9]) if row[9] else None,
                "status": row[10]
            })

        logger.info(f"查询供股数据: {stock_code}, 返回{len(data)}条记录")
        # 清理文本中的无效字符
        cleaned_data = clean_list(data)
        return json.dumps(cleaned_data, ensure_ascii=False, indent=2)

    except Exception as e:
        logger.error(f"查询供股数据失败: {e}")
        return json.dumps({"error": str(e)}, ensure_ascii=False)


@tool
def query_consolidation_data(
        stock_code: str,
        start_date: str = None,
        end_date: str = None,
        limit: int = 10
) -> str:
    """查询股本整合（合股）数据
    
    【适用场景】
    - 用户询问"合股"或"股本整合"相关信息
    - 需要合股比例（如"10合1"）、生效日期等结构化字段
    - 查询股东大会（AGM）日期
    - 了解其他资本活动（如同时进行的拆股、配股等）
    
    【不适用场景】
    - 需要完整股东通函详细内容 → 使用 retrieve_chunks
    - 查询拆股（分股）数据 → 通常也在本表，但比例为如"1拆10"
    - 查询配售/供股 → 使用对应工具
    
    【前置条件】
    - 必须提供 stock_code（格式：5位数字+.hk）
    - 可选时间筛选 start_date/end_date
    
    【返回格式】
    JSON数组，每个元素包含：
    - stock_code、company_name、announcement_date
    - consolidation_ratio（合股比例，如"10合1"）
    - agm_date（股东大会日期）
    - effective_date（生效日期）
    - other_capital_activities（其他资本活动说明）
    - status（状态）
    
    【后续工具链】
    - 如需股东通函详情 → retrieve_chunks(keyword="合股")
    - 如需分析合股影响 → enhance_market_data 获取合股前后股价
    - 如需对比其他公司 → 再次调用本工具，然后用 compare_data
    
    【使用示例】
    query_consolidation_data(stock_code="00064.hk", limit=5)
    
    Args:
        stock_code: 股票代码，格式如'00064.hk'（必需）
        start_date: 起始公告日期 YYYY-MM-DD（可选）
        end_date: 结束日期（可选）
        limit: 返回数量，默认10，建议5-20
        
    Returns:
        JSON格式的合股数据列表
    """
    try:
        client = get_clickhouse_client()

        # 构建查询条件
        where_clauses = [f"stock_code = '{stock_code}'"]
        if start_date:
            where_clauses.append(f"announcement_date >= '{start_date}'")
        if end_date:
            where_clauses.append(f"announcement_date <= '{end_date}'")

        where_str = " AND ".join(where_clauses)

        query = f"""
        SELECT 
            stock_code,
            company_name,
            announcement_date,
            agm_date,
            consolidation_ratio,
            effective_date,
            other_capital_activities,
            status
        FROM consolidation_data
        WHERE {where_str}
        ORDER BY announcement_date DESC
        LIMIT {limit}
        """

        results = client.query(query).result_rows

        # 转换为字典列表
        data = []
        for row in results:
            data.append({
                "stock_code": row[0],
                "company_name": row[1],
                "announcement_date": str(row[2]),
                "agm_date": row[3],
                "consolidation_ratio": row[4],
                "effective_date": str(row[5]) if row[5] else None,
                "other_capital_activities": row[6],
                "status": row[7]
            })

        logger.info(f"查询合股数据: {stock_code}, 返回{len(data)}条记录")
        # 清理文本中的无效字符
        cleaned_data = clean_list(data)
        return json.dumps(cleaned_data, ensure_ascii=False, indent=2)

    except Exception as e:
        logger.error(f"查询合股数据失败: {e}")
        return json.dumps({"error": str(e)}, ensure_ascii=False)
