"""文档检索工具 - 检索公告文档和chunks"""
from langchain_core.tools import tool
import json
import logging

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
    """搜索公告文档
    
    Args:
        stock_code: 股票代码，如'00700.hk'（可选）
        document_type: 文档类型，如'配股'（可选）
        document_category: 文档类别，如'公告及通告'（可选）
        start_date: 起始发布日期 YYYY-MM-DD（可选）
        end_date: 结束日期（可选）
        limit: 返回数量，默认5
        
    Returns:
        JSON格式的文档列表，包含doc_id, stock_code, company_name, document_title, publish_date
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
    """检索公告切块内容
    
    Args:
        doc_id: 文档ID（从search_documents获取，优先使用）
        stock_code: 股票代码（宽泛检索时使用）
        keyword: 关键词（SQL LIKE匹配text字段）
        chunk_type: 切块类型，可选：paragraph/table/list/title
        limit: 返回数量，默认20
        
    Returns:
        JSON格式的chunk列表，包含chunk_id, text, page_number, chunk_type, table_data
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

