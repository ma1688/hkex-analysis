"""文档检索工具 - 检索公告文档和chunks"""
import json
import logging

from langchain_core.tools import tool

from src.utils.clickhouse import get_clickhouse_client
from src.utils.text_cleaner import clean_list, clean_dict

logger = logging.getLogger(__name__)


@tool
def search_documents(
        stock_code: str = None,
        document_type: str = None,
        document_category: str = None,
        start_date: str = None,
        end_date: str = None,
        limit: int = 5
) -> str:
    """搜索公告文档元信息
    
    【适用场景】
    - 需要获取文档列表（doc_id、标题、发布日期）
    - 不确定具体文档类型，需要探索性搜索
    - 作为retrieve_chunks的前置步骤（获取doc_id）
    - 按时间段筛选公告
    - 按文档类型（配售/供股/招股书等）筛选
    
    【不适用场景】
    - 明确需要配售/IPO/供股结构化数据 → 优先用 query_*_data 工具（更快）
    - 已知doc_id需要内容 → 直接用 retrieve_chunks
    - 需要完整文档内容 → 需要配合 retrieve_chunks 使用
    
    【前置条件】
    - 至少提供一个筛选条件（stock_code、document_type、date范围等）
    - 如果都不提供，返回最近的公告
    
    【返回格式】
    JSON数组，每个元素包含：
    - doc_id（文档ID，用于retrieve_chunks）
    - stock_code、company_name
    - document_type（文档类型）、document_category（类别）
    - document_title（标题）、publish_date（发布日期）
    - page_count（页数）、chunks_count（切块数）
    
    【后续工具链】
    - 获取内容 → retrieve_chunks(doc_id="从本工具返回结果获取")
    - 整合内容 → synthesize_chunks
    - 提取信息 → extract_key_info
    
    【使用示例】
    # 搜索特定公司最新公告
    search_documents(stock_code="00700.hk", limit=5)
    
    # 按类型搜索
    search_documents(stock_code="00700.hk", document_type="配售", limit=3)
    
    # 按时间段搜索
    search_documents(
        stock_code="00700.hk",
        start_date="2024-01-01",
        end_date="2024-12-31",
        limit=10
    )
    
    Args:
        stock_code: 股票代码，如'00700.hk'（可选）
        document_type: 文档类型，如'配售''招股书''财报'（可选）
        document_category: 文档类别，如'公告及通告'（可选）
        start_date: 起始发布日期 YYYY-MM-DD（可选）
        end_date: 结束日期（可选）
        limit: 返回数量，默认5，建议5-20
        
    Returns:
        JSON格式的文档列表，包含doc_id等元信息
    """
    try:
        client = get_clickhouse_client()

        # 构建查询条件
        where_clauses = []
        if stock_code:
            where_clauses.append(f"stock_code = '{stock_code}'")
        if document_type:
            where_clauses.append(f"document_type = '{document_type}'")
        if document_category:
            where_clauses.append(f"document_category = '{document_category}'")
        if start_date:
            where_clauses.append(f"publish_date >= '{start_date}'")
        if end_date:
            where_clauses.append(f"publish_date <= '{end_date}'")

        where_str = " AND ".join(where_clauses) if where_clauses else "1=1"

        query = f"""
        SELECT 
            doc_id,
            stock_code,
            company_name,
            document_type,
            document_category,
            document_title,
            publish_date,
            page_count,
            chunks_count
        FROM pdf_documents
        WHERE {where_str}
        ORDER BY publish_date DESC
        LIMIT {limit}
        """

        results = client.query(query).result_rows

        # 转换为字典列表
        data = []
        for row in results:
            data.append({
                "doc_id": row[0],
                "stock_code": row[1],
                "company_name": row[2],
                "document_type": row[3],
                "document_category": row[4],
                "document_title": row[5],
                "publish_date": str(row[6]),
                "page_count": row[7],
                "chunks_count": row[8]
            })

        logger.info(
            f"搜索文档: stock={stock_code}, type={document_type}, "
            f"返回{len(data)}条记录"
        )
        # 清理文本中的无效字符
        cleaned_data = clean_list(data)
        return json.dumps(cleaned_data, ensure_ascii=False, indent=2)

    except Exception as e:
        logger.error(f"搜索文档失败: {e}")
        return json.dumps({"error": str(e)}, ensure_ascii=False)


@tool
def retrieve_chunks(
        doc_id: str = None,
        stock_code: str = None,
        keyword: str = None,
        chunk_type: str = None,
        limit: int = 20
) -> str:
    """检索公告内容切块（获取详细原文）
    
    【适用场景】
    - 已有doc_id，需要获取完整公告内容
    - 需要在公告中搜索特定关键词
    - 需要获取特定类型的内容（表格、段落、列表）
    - 作为synthesize_chunks的输入数据
    
    【不适用场景】
    - 只需要结构化摘要数据 → 优先用 query_*_data 工具（更快更准确）
    - 没有doc_id也没有关键词 → 先用 search_documents 获取doc_id
    
    【前置条件】
    - 必须提供以下之一：doc_id（推荐）、stock_code、keyword
    - doc_id 优先级最高（精确检索）
    - stock_code 次之（检索该公司最近5个文档的chunks）
    - keyword 可与上述参数组合使用
    
    【返回格式】
    JSON数组，每个元素包含：
    - chunk_id（切块ID）、doc_id（文档ID）
    - chunk_index（切块索引，用于排序）
    - page_number（页码）
    - text（文本内容）
    - chunk_type（类型：paragraph/table/list/title）
    - table_data（如果是表格类型，包含表格数据）
    
    【后续工具链】
    - 整合多个chunks → synthesize_chunks(chunks_json="从本工具返回的结果")
    - 提取关键信息 → extract_key_info(text="从synthesize返回的文本")
    - 对比分析 → 如果检索了多个文档，可以分别synthesize后用compare_data
    
    【使用示例】
    # 方式1：精确检索（推荐）
    search_documents(stock_code="00700.hk", limit=1)  # 先获取doc_id
    retrieve_chunks(doc_id="<从上一步获得>", limit=30)
    
    # 方式2：关键词搜索
    retrieve_chunks(
        doc_id="<doc_id>",
        keyword="配售价",
        limit=10
    )
    
    # 方式3：按股票代码宽泛检索
    retrieve_chunks(stock_code="00700.hk", keyword="回购", limit=20)
    
    # 方式4：只检索特定类型
    retrieve_chunks(doc_id="<doc_id>", chunk_type="table", limit=10)
    
    Args:
        doc_id: 文档ID（从search_documents获取，优先使用）
        stock_code: 股票代码（宽泛检索时使用）
        keyword: 关键词（SQL LIKE匹配text字段）
        chunk_type: 切块类型，可选：paragraph/table/list/title
        limit: 返回数量，默认20，建议20-50
        
    Returns:
        JSON格式的chunk列表，包含文本内容和元信息
    """
    try:
        client = get_clickhouse_client()

        # 构建查询条件
        where_clauses = []
        if doc_id:
            where_clauses.append(f"doc_id = '{doc_id}'")
        elif stock_code:
            # 如果没有doc_id，通过stock_code关联查询
            where_clauses.append(f"""
                doc_id IN (
                    SELECT doc_id FROM pdf_documents 
                    WHERE stock_code = '{stock_code}' 
                    ORDER BY publish_date DESC 
                    LIMIT 5
                )
            """)

        if keyword:
            # 使用LIKE进行关键词匹配
            where_clauses.append(f"text LIKE '%{keyword}%'")

        if chunk_type:
            where_clauses.append(f"chunk_type = '{chunk_type}'")

        if not where_clauses:
            return json.dumps(
                {"error": "必须提供doc_id或stock_code或keyword之一"},
                ensure_ascii=False
            )

        where_str = " AND ".join(where_clauses)

        query = f"""
        SELECT 
            chunk_id,
            doc_id,
            chunk_index,
            page_number,
            text,
            chunk_type,
            table_data
        FROM pdf_chunks
        WHERE {where_str}
        ORDER BY chunk_index ASC
        LIMIT {limit}
        """

        results = client.query(query).result_rows

        # 转换为字典列表
        data = []
        for row in results:
            chunk_data = {
                "chunk_id": row[0],
                "doc_id": row[1],
                "chunk_index": row[2],
                "page_number": row[3],
                "text": row[4],
                "chunk_type": row[5]
            }

            # 如果是table类型且有table_data，添加到结果
            if row[6]:
                chunk_data["table_data"] = row[6]

            data.append(chunk_data)

        logger.info(
            f"检索chunks: doc_id={doc_id}, keyword={keyword}, "
            f"返回{len(data)}条记录"
        )
        # 清理文本中的无效字符
        cleaned_data = clean_list(data)
        return json.dumps(cleaned_data, ensure_ascii=False, indent=2)

    except Exception as e:
        logger.error(f"检索chunks失败: {e}")
        return json.dumps({"error": str(e)}, ensure_ascii=False)


@tool
def get_document_metadata(doc_id: str) -> str:
    """获取文档元信息
    
    Args:
        doc_id: 文档ID
        
    Returns:
        JSON格式的文档元信息
    """
    try:
        client = get_clickhouse_client()

        query = f"""
        SELECT 
            doc_id,
            file_name,
            stock_code,
            company_name,
            document_type,
            document_category,
            document_title,
            publish_date,
            page_count,
            chunks_count,
            vectors_count,
            processing_status
        FROM pdf_documents
        WHERE doc_id = '{doc_id}'
        LIMIT 1
        """

        results = client.query(query).result_rows

        if not results:
            return json.dumps(
                {"error": f"未找到文档: {doc_id}"},
                ensure_ascii=False
            )

        row = results[0]
        data = {
            "doc_id": row[0],
            "file_name": row[1],
            "stock_code": row[2],
            "company_name": row[3],
            "document_type": row[4],
            "document_category": row[5],
            "document_title": row[6],
            "publish_date": str(row[7]),
            "page_count": row[8],
            "chunks_count": row[9],
            "vectors_count": row[10],
            "processing_status": row[11]
        }

        logger.info(f"获取文档元信息: {doc_id}")
        # 清理文本中的无效字符
        cleaned_data = clean_dict(data)
        return json.dumps(cleaned_data, ensure_ascii=False, indent=2)

    except Exception as e:
        logger.error(f"获取文档元信息失败: {e}")
        return json.dumps({"error": str(e)}, ensure_ascii=False)
