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
        document_category: str = None,
        announcement_category: str = None,
        start_date: str = None,
        end_date: str = None,
        limit: int = 5
) -> str:
    """搜索公告文档元信息（V2.2）
    
    【V2.2更新】
    - 使用documents_v2表
    - document_type已移除，使用document_category
    - 新增announcement_category（二级分类）
    - section_count从metadata中提取
    
    【适用场景】
    - 获取文档列表（doc_id、标题、发布日期）
    - 作为retrieve_sections的前置步骤（获取doc_id）
    - 按时间段/分类筛选公告
    
    【返回格式】
    JSON数组，每个元素包含：
    - doc_id、stock_code、company_name
    - document_category（一级分类，如"供股"、"合股"）
    - announcement_category（二级分类，如"公告及通告"）
    - announcement_title（公告标题）
    - announcement_date（发布日期）
    - page_count（页数）、section_count（章节数）
    
    Args:
        stock_code: 股票代码（可选）
        document_category: 文档主分类，如'供股''合股'（可选）
        announcement_category: 公告子分类，如'公告及通告'（可选）
        start_date: 起始日期 YYYY-MM-DD（可选）
        end_date: 结束日期（可选）
        limit: 返回数量，默认5
        
    Returns:
        JSON格式的文档列表
    """
    try:
        client = get_clickhouse_client()

        # 构建查询条件
        where_clauses = []
        if stock_code:
            where_clauses.append(f"stock_code = '{stock_code}'")
        if document_category:
            where_clauses.append(f"document_category = '{document_category}'")
        if announcement_category:
            where_clauses.append(f"announcement_category = '{announcement_category}'")
        if start_date:
            where_clauses.append(f"announcement_date >= '{start_date}'")
        if end_date:
            where_clauses.append(f"announcement_date <= '{end_date}'")

        where_str = " AND ".join(where_clauses) if where_clauses else "1=1"

        query = f"""
        SELECT 
            doc_id,
            stock_code,
            company_name,
            document_category,
            announcement_category,
            announcement_title,
            announcement_date,
            page_count,
            metadata
        FROM documents_v2
        WHERE {where_str}
        ORDER BY announcement_date DESC
        LIMIT {limit}
        """

        results = client.query(query).result_rows

        # 转换为字典列表
        data = []
        for row in results:
            metadata = json.loads(row[8]) if row[8] else {}
            data.append({
                "doc_id": row[0],
                "stock_code": row[1],
                "company_name": row[2],
                "document_category": row[3],
                "announcement_category": row[4],
                "announcement_title": row[5],
                "announcement_date": str(row[6]),
                "page_count": row[7],
                "section_count": metadata.get('section_count', 0)
            })

        logger.info(
            f"[V2.2] 搜索文档: stock={stock_code}, category={document_category}, "
            f"返回{len(data)}条"
        )
        cleaned_data = clean_list(data)
        return json.dumps(cleaned_data, ensure_ascii=False, indent=2)

    except Exception as e:
        logger.error(f"搜索文档失败: {e}")
        return json.dumps({"error": str(e)}, ensure_ascii=False)


@tool
def retrieve_sections(
        doc_id: str = None,
        stock_code: str = None,
        keyword: str = None,
        section_type: str = None,
        limit: int = 20
) -> str:
    """检索公告章节内容（V2.2）
    
    【V2.2更新】
    - 使用document_sections表
    - chunk → section概念变更
    - 新增page_start/page_end（页码范围）
    - 新增priority（章节优先级）
    
    【适用场景】
    - 已有doc_id，获取公告章节内容
    - 关键词搜索特定内容
    - 按章节类型筛选
    
    【返回格式】
    JSON数组，每个元素包含：
    - section_id、doc_id、section_index
    - section_type（章节类型）
    - section_title（章节标题）
    - page_start/page_end（页码范围）
    - content（文本内容）
    - priority（优先级，越小越重要）
    
    Args:
        doc_id: 文档ID（推荐）
        stock_code: 股票代码（宽泛检索）
        keyword: 关键词（LIKE匹配content）
        section_type: 章节类型（summary/terms/financial等）
        limit: 返回数量，默认20
        
    Returns:
        JSON格式的章节列表
    """
    try:
        client = get_clickhouse_client()

        # 构建查询条件
        where_clauses = []
        if doc_id:
            where_clauses.append(f"doc_id = '{doc_id}'")
        elif stock_code:
            # 通过stock_code关联查询
            where_clauses.append(f"""
                doc_id IN (
                    SELECT doc_id FROM documents_v2 
                    WHERE stock_code = '{stock_code}' 
                    ORDER BY announcement_date DESC 
                    LIMIT 5
                )
            """)

        if keyword:
            where_clauses.append(f"content LIKE '%{keyword}%'")

        if section_type:
            where_clauses.append(f"section_type = '{section_type}'")

        if not where_clauses:
            return json.dumps(
                {"error": "必须提供doc_id或stock_code或keyword之一"},
                ensure_ascii=False
            )

        where_str = " AND ".join(where_clauses)

        query = f"""
        SELECT 
            section_id,
            doc_id,
            section_index,
            section_type,
            section_title,
            page_start,
            page_end,
            content,
            priority
        FROM document_sections
        WHERE {where_str}
        ORDER BY section_index ASC
        LIMIT {limit}
        """

        results = client.query(query).result_rows

        # 转换为字典列表
        data = []
        for row in results:
            data.append({
                "section_id": row[0],
                "doc_id": row[1],
                "section_index": row[2],
                "section_type": row[3],
                "section_title": row[4],
                "page_start": row[5],
                "page_end": row[6],
                "content": row[7],
                "priority": row[8]
            })

        logger.info(
            f"[V2.2] 检索章节: doc_id={doc_id}, keyword={keyword}, "
            f"返回{len(data)}条"
        )
        cleaned_data = clean_list(data)
        return json.dumps(cleaned_data, ensure_ascii=False, indent=2)

    except Exception as e:
        logger.error(f"检索章节失败: {e}")
        return json.dumps({"error": str(e)}, ensure_ascii=False)


@tool
def get_document_metadata(doc_id: str) -> str:
    """获取文档元信息（V2.2）
    
    【V2.2更新】
    - 使用documents_v2表
    - 返回V2.2字段结构
    - metadata从JSON中解析
    
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
            announcement_title,
            stock_code,
            company_name,
            document_category,
            announcement_category,
            announcement_date,
            file_path,
            page_count,
            metadata,
            created_at
        FROM documents_v2
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
        metadata = json.loads(row[9]) if row[9] else {}
        
        data = {
            "doc_id": row[0],
            "announcement_title": row[1],
            "stock_code": row[2],
            "company_name": row[3],
            "document_category": row[4],
            "announcement_category": row[5],
            "announcement_date": str(row[6]),
            "file_path": row[7],
            "page_count": row[8],
            "section_count": metadata.get('section_count', 0),
            "document_subtype": metadata.get('document_subtype', ''),
            "processing_version": metadata.get('processing_version', ''),
            "created_at": str(row[10])
        }

        logger.info(f"[V2.2] 获取文档元信息: {doc_id}")
        cleaned_data = clean_dict(data)
        return json.dumps(cleaned_data, ensure_ascii=False, indent=2)

    except Exception as e:
        logger.error(f"获取文档元信息失败: {e}")
        return json.dumps({"error": str(e)}, ensure_ascii=False)
