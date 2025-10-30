"""
Web应用数据模型
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

class TaskStatus(str, Enum):
    """任务状态"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class DocumentType(str, Enum):
    """文档类型"""
    RIGHTS = "rights"  # 供股
    PLACING = "placing"  # 配售
    IPO = "ipo"  # IPO
    CONSOLIDATION = "consolidation"  # 合股/拆股
    SPLIT = "split"  # 拆股
    ACQUISITION = "acquisition"  # 收购
    DISPOSAL = "disposal"  # 出售
    DISCLOSABLE_TRANSACTION = "disclosable_transaction"  # 须予披露交易
    CONNECTED_TRANSACTION = "connected_transaction"  # 关连交易
    VERY_SUBSTANTIAL_ACQUISITION = "very_substantial_acquisition"  # 非常重大收购
    VERY_SUBSTANTIAL_DISPOSAL = "very_substantial_disposal"  # 非常重大出售
    SHARE_OPTION = "share_option"  # 购股权计划
    DIVIDEND = "dividend"  # 股息分派
    CAPITAL_REDUCTION = "capital_reduction"  # 股本缩减
    SHARE_REPURCHASE = "share_repurchase"  # 股份回购
    OTHER = "other"

class TaskCreate(BaseModel):
    """创建任务模型"""
    stock_code: str = Field(..., description="股票代码", example="00328")
    document_type: DocumentType = Field(..., description="文档类型")
    file_path: Optional[str] = Field(None, description="文件路径")
    auto_filter: bool = Field(True, description="是否自动过滤")

class TaskInfo(BaseModel):
    """任务信息模型"""
    task_id: str
    stock_code: str
    document_type: str
    file_path: str
    status: TaskStatus
    progress: float = Field(0, ge=0, le=100)
    message: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None
    doc_id: Optional[str] = None
    section_count: Optional[int] = None

class DocumentInfo(BaseModel):
    """文档信息模型"""
    doc_id: str
    stock_code: str
    company_name: str
    document_type: str
    document_subtype: str
    announcement_date: datetime
    section_count: int
    metadata: Dict[str, Any]
    created_at: datetime

class SectionInfo(BaseModel):
    """章节信息模型"""
    section_id: str
    doc_id: str
    section_type: str
    section_title: str
    section_index: int
    content: str
    char_count: int
    metadata: Dict[str, Any]

class Statistics(BaseModel):
    """统计数据模型"""
    total_documents: int
    total_sections: int
    documents_by_type: Dict[str, int]
    documents_by_status: Dict[str, int]
    recent_documents: List[DocumentInfo]
    top_companies: List[Dict[str, Any]]
    processing_stats: Dict[str, Any]

class DuplicateFile(BaseModel):
    """重复文件模型"""
    file_path: str
    doc_ids: List[str]
    count: int
    keep_doc_id: str
    delete_doc_ids: List[str]

class CleanupResult(BaseModel):
    """清理结果模型"""
    dry_run: bool
    duplicates_found: int
    files_to_delete: List[DuplicateFile]
    total_records_to_delete: int
