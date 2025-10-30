"""
任务管理服务
"""

import uuid
import asyncio
from datetime import datetime
from typing import Dict, Optional, List
from pathlib import Path
import json
import subprocess
import sys

from ..models.schemas import TaskInfo, TaskStatus, TaskCreate
from src.config.settings import get_settings

settings = get_settings()

class TaskManager:
    """任务管理器"""

    def __init__(self):
        self.tasks: Dict[str, TaskInfo] = {}
        self.task_queues: Dict[str, asyncio.Queue] = {}

    def create_task(self, task_data: TaskCreate, file_path: str) -> str:
        """创建新任务"""
        task_id = str(uuid.uuid4())

        task_info = TaskInfo(
            task_id=task_id,
            stock_code=task_data.stock_code,
            document_type=task_data.document_type.value,
            file_path=file_path,
            status=TaskStatus.PENDING,
            progress=0,
            message="任务已创建",
            created_at=datetime.now(),
            updated_at=datetime.now()
        )

        self.tasks[task_id] = task_info
        return task_id

    def get_task(self, task_id: str) -> Optional[TaskInfo]:
        """获取任务信息"""
        return self.tasks.get(task_id)

    def list_tasks(self, status: Optional[TaskStatus] = None, limit: int = 50) -> List[TaskInfo]:
        """列出任务"""
        tasks = list(self.tasks.values())

        if status:
            tasks = [t for t in tasks if t.status == status]

        # 按创建时间倒序排列
        tasks.sort(key=lambda x: x.created_at, reverse=True)

        return tasks[:limit]

    def update_task_status(
        self,
        task_id: str,
        status: TaskStatus,
        progress: Optional[float] = None,
        message: Optional[str] = None,
        doc_id: Optional[str] = None,
        section_count: Optional[int] = None
    ) -> bool:
        """更新任务状态"""
        if task_id not in self.tasks:
            return False

        task = self.tasks[task_id]
        task.status = status
        task.updated_at = datetime.now()

        if progress is not None:
            task.progress = progress
        if message is not None:
            task.message = message
        if doc_id is not None:
            task.doc_id = doc_id
        if section_count is not None:
            task.section_count = section_count

        if status == TaskStatus.COMPLETED:
            task.completed_at = datetime.now()

        return True

    async def process_task(self, task_id: str, script_path: str) -> None:
        """异步处理任务"""
        task = self.get_task(task_id)
        if not task:
            print(f"[ERROR] 任务不存在: {task_id}")
            return

        # 检查脚本路径
        if not Path(script_path).exists():
            error_msg = f"处理脚本不存在: {script_path}"
            print(f"[ERROR] {error_msg}")
            self.update_task_status(
                task_id,
                TaskStatus.FAILED,
                message=error_msg
            )
            return

        try:
            print(f"[INFO] 开始处理任务 {task_id}: {task.file_path}")
            self.update_task_status(task_id, TaskStatus.PROCESSING, 0, "开始处理...")

            # 构建命令
            cmd = [
                sys.executable,
                str(script_path),
                task.file_path,
                task.stock_code
            ]

            print(f"[DEBUG] 执行命令: {' '.join(cmd)}")

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=Path(__file__).parent.parent.parent.parent
            )

            stdout, stderr = await process.communicate()

            stdout_text = stdout.decode('utf-8')
            stderr_text = stderr.decode('utf-8')

            print(f"[DEBUG] 脚本返回码: {process.returncode}")
            if stdout_text:
                print(f"[DEBUG] 标准输出:\n{stdout_text[:500]}")
            if stderr_text:
                print(f"[DEBUG] 标准错误:\n{stderr_text[:500]}")

            if process.returncode == 0:
                # 解析输出获取doc_id
                doc_id = self._extract_doc_id(stdout_text)

                print(f"[INFO] 任务 {task_id} 处理完成，文档ID: {doc_id}")
                self.update_task_status(
                    task_id,
                    TaskStatus.COMPLETED,
                    100,
                    "处理完成",
                    doc_id=doc_id
                )
            else:
                error_msg = stderr_text if stderr_text else stdout_text
                print(f"[ERROR] 任务 {task_id} 处理失败: {error_msg[:200]}")
                self.update_task_status(
                    task_id,
                    TaskStatus.FAILED,
                    message=f"处理失败: {error_msg[:500]}"
                )

        except Exception as e:
            error_msg = str(e)
            print(f"[ERROR] 任务 {task_id} 处理异常: {error_msg}")
            import traceback
            traceback.print_exc()
            self.update_task_status(
                task_id,
                TaskStatus.FAILED,
                message=f"异常: {error_msg}"
            )

    def _extract_doc_id(self, output: str) -> Optional[str]:
        """从输出中提取doc_id"""
        import re
        match = re.search(r'文档ID:\s*(\S+)', output)
        return match.group(1) if match else None

    def delete_task(self, task_id: str) -> bool:
        """删除任务"""
        if task_id in self.tasks:
            del self.tasks[task_id]
            return True
        return False

# 全局任务管理器实例
task_manager = TaskManager()
