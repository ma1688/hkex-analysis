"""
统计信息路由
"""

from fastapi import APIRouter

from ..models.schemas import Statistics
from ..services.data_service import data_service

router = APIRouter(prefix="/stats", tags=["stats"])

@router.get("/", response_model=Statistics)
async def get_statistics():
    """获取系统统计信息"""
    return data_service.get_statistics()

@router.get("/overview", response_model=dict)
async def get_overview():
    """获取概览统计"""
    stats = data_service.get_statistics()

    return {
        "total_documents": stats.total_documents,
        "total_sections": stats.total_sections,
        "documents_by_type": stats.documents_by_type,
        "processing_stats": stats.processing_stats,
        "recent_activity": len(stats.recent_documents),
        "top_companies": stats.top_companies[:5]
    }
