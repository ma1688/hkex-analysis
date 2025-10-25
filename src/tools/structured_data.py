"""结构化数据查询工具 - 查询IPO/配售/供股/合股数据"""
from langchain_core.tools import tool
import json
import logging

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
    
    Args:
        stock_code: 股票代码，格式如'00700.hk'
        start_date: 起始日期 YYYY-MM-DD（可选）
        end_date: 结束日期 YYYY-MM-DD（可选）
        limit: 返回数量，默认10
        
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
    
    Args:
        stock_code: 股票代码（可选，如'00638.hk'）
        start_date: 起始上市日期 YYYY-MM-DD（可选）
        end_date: 结束日期（可选）
        limit: 返回数量，默认10
        
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
    
    Args:
        stock_code: 股票代码，格式如'00122.hk'
        start_date: 起始公告日期 YYYY-MM-DD（可选）
        end_date: 结束日期（可选）
        limit: 返回数量，默认10
        
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
    
    Args:
        stock_code: 股票代码，格式如'00064.hk'
        start_date: 起始公告日期 YYYY-MM-DD（可选）
        end_date: 结束日期（可选）
        limit: 返回数量，默认10
        
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

