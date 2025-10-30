"""
数据管理路由
"""

from fastapi import APIRouter, HTTPException, Query, Path
from typing import List, Optional
from ..models.schemas import DocumentInfo, SectionInfo

from ..services.data_service import data_service

router = APIRouter(prefix="/data", tags=["data"])

@router.get("/documents", response_model=dict)
async def list_documents(
    stock_code: Optional[str] = Query(None, description="股票代码过滤"),
    document_type: Optional[str] = Query(None, description="文档类型过滤"),
    limit: int = Query(50, ge=1, le=100, description="返回数量限制"),
    offset: int = Query(0, ge=0, description="偏移量")
):
    """获取文档列表"""
    documents, total = data_service.get_documents(
        stock_code=stock_code,
        document_type=document_type,
        limit=limit,
        offset=offset
    )

    return {
        "documents": documents,
        "total": total,
        "limit": limit,
        "offset": offset
    }

@router.get("/documents/{doc_id}", response_model=DocumentInfo)
async def get_document(doc_id: str = Path(..., description="文档ID")):
    """获取单个文档详情"""
    document = data_service.get_document(doc_id)
    if not document:
        raise HTTPException(status_code=404, detail="文档不存在")
    return document

@router.get("/documents/{doc_id}/sections", response_model=List[SectionInfo])
async def get_document_sections(
    doc_id: str = Path(..., description="文档ID"),
    limit: int = Query(100, ge=1, le=500, description="返回数量限制")
):
    """获取文档章节"""
    sections = data_service.get_sections(doc_id, limit=limit)
    return sections

@router.get("/search", response_model=List[DocumentInfo])
async def search_documents(
    q: str = Query(..., description="搜索关键词"),
    limit: int = Query(50, ge=1, le=100, description="返回数量限制")
):
    """搜索文档"""
    documents = data_service.search_documents(q, limit=limit)
    return documents

@router.post("/cleanup/duplicates", response_model=dict)
async def cleanup_duplicates(
    dry_run: bool = Query(True, description="是否仅预览，不执行删除")
):
    """清理重复数据"""
    result = data_service.cleanup_duplicates(dry_run=dry_run)

    return {
        "dry_run": result.dry_run,
        "duplicates_found": result.duplicates_found,
        "total_records_to_delete": result.total_records_to_delete,
        "files": [
            {
                "file_path": f.file_path,
                "count": f.count,
                "keep_doc_id": f.keep_doc_id,
                "delete_doc_ids": f.delete_doc_ids
            }
            for f in result.files_to_delete
        ]
    }

@router.get("/cleanup/duplicates/preview", response_model=dict)
async def preview_duplicates():
    """预览重复数据"""
    result = data_service.check_duplicates()

    return {
        "duplicates_found": result.duplicates_found,
        "total_records_to_delete": result.total_records_to_delete,
        "files": [
            {
                "file_path": f.file_path,
                "count": f.count,
                "keep_doc_id": f.keep_doc_id,
                "delete_doc_ids": f.delete_doc_ids
            }
            for f in result.files_to_delete
        ]
    }

@router.delete("/documents/{doc_id}", response_model=dict)
async def delete_document(doc_id: str = Path(..., description="文档ID")):
    """删除单个文档"""
    success = data_service.delete_document(doc_id)
    if not success:
        raise HTTPException(status_code=500, detail="删除文档失败")

    return {"message": "文档删除成功", "doc_id": doc_id}

@router.post("/documents/batch-delete", response_model=dict)
async def batch_delete_documents(doc_ids: List[str]):
    """批量删除文档"""
    deleted_count = data_service.delete_documents_batch(doc_ids)

    return {
        "message": f"成功删除 {deleted_count} 个文档",
        "total_requested": len(doc_ids),
        "deleted_count": deleted_count
    }

@router.delete("/all", response_model=dict)
async def delete_all_data():
    """清空所有数据（危险操作）"""
    success = data_service.delete_all_data()
    if not success:
        raise HTTPException(status_code=500, detail="清空数据失败")

    return {"message": "所有数据已清空"}
