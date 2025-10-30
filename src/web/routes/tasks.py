"""
任务管理路由
"""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
import asyncio

from ..models.schemas import TaskInfo, TaskStatus
from ..services.task_service import task_manager

router = APIRouter(prefix="/tasks", tags=["tasks"])

@router.get("/", response_model=List[TaskInfo])
async def list_tasks(
    status: Optional[TaskStatus] = Query(None, description="任务状态过滤"),
    limit: int = Query(50, ge=1, le=100, description="返回数量限制")
):
    """获取任务列表"""
    return task_manager.list_tasks(status=status, limit=limit)

@router.get("/{task_id}", response_model=TaskInfo)
async def get_task(task_id: str):
    """获取单个任务详情"""
    task = task_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    return task

@router.post("/{task_id}/cancel", response_model=dict)
async def cancel_task(task_id: str):
    """取消任务"""
    task = task_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    if task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
        raise HTTPException(status_code=400, detail="已完成或失败的任务无法取消")

    task_manager.update_task_status(
        task_id,
        TaskStatus.CANCELLED,
        message="任务已取消"
    )

    return {"message": "任务已取消"}

@router.delete("/{task_id}", response_model=dict)
async def delete_task(task_id: str):
    """删除任务"""
    if not task_manager.delete_task(task_id):
        raise HTTPException(status_code=404, detail="任务不存在")

    return {"message": "任务已删除"}

@router.post("/{task_id}/retry", response_model=dict)
async def retry_task(task_id: str):
    """重试失败的任务"""
    task = task_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    if task.status != TaskStatus.FAILED:
        raise HTTPException(status_code=400, detail="只有失败的任务可以重试")

    # 重置任务状态
    task_manager.update_task_status(
        task_id,
        TaskStatus.PENDING,
        progress=0,
        message="任务已重置，等待处理"
    )

    # 重新启动处理
    from pathlib import Path
    script_path = Path(__file__).parent.parent.parent.parent / "scripts" / "chunk_pdf.py"
    asyncio.create_task(task_manager.process_task(task_id, script_path))

    return {"message": "任务已重启"}

@router.get("/stats/summary", response_model=dict)
async def task_stats():
    """获取任务统计"""
    all_tasks = task_manager.list_tasks(limit=1000)

    stats = {
        "total": len(all_tasks),
        "pending": len([t for t in all_tasks if t.status == TaskStatus.PENDING]),
        "processing": len([t for t in all_tasks if t.status == TaskStatus.PROCESSING]),
        "completed": len([t for t in all_tasks if t.status == TaskStatus.COMPLETED]),
        "failed": len([t for t in all_tasks if t.status == TaskStatus.FAILED]),
        "cancelled": len([t for t in all_tasks if t.status == TaskStatus.CANCELLED])
    }

    return stats
