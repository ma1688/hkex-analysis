"""
文件上传路由
"""

import os
import re
import asyncio
from fastapi import APIRouter, File, UploadFile, Form, HTTPException
from fastapi.responses import JSONResponse
from typing import List
from pathlib import Path

from ..models.schemas import TaskCreate, TaskStatus, DocumentType
from ..services.task_service import task_manager
from ..services.data_service import data_service

router = APIRouter(prefix="/upload", tags=["upload"])

# 上传目录
UPLOAD_DIR = Path(__file__).parent.parent / "static" / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

@router.post("/", response_model=dict)
async def upload_file(
    file: UploadFile = File(...),
    stock_code: str = Form(...),
    document_type: str = Form(...),
    auto_filter: bool = Form(True)
):
    """上传单个PDF文件"""
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="仅支持PDF文件")

    # 保存文件
    file_path = UPLOAD_DIR / file.filename
    with open(file_path, "wb") as f:
        content = await file.read()
        f.write(content)

    # 检查是否需要过滤
    if auto_filter:
        # 使用可配置的文档过滤器检查
        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "scripts"))
        from document_filter_configurable import ConfigurableDocumentFilter

        filter_obj = ConfigurableDocumentFilter(str(file_path))
        should_process, reason = filter_obj.should_process()

        if not should_process:
            os.remove(file_path)
            return JSONResponse(
                status_code=200,
                content={
                    "status": "skipped",
                    "message": f"文档被过滤: {reason}",
                    "file": file.filename
                }
            )

    # 创建任务
    from ..models.schemas import DocumentType

    try:
        doc_type = DocumentType(document_type)
    except ValueError:
        raise HTTPException(status_code=400, detail="无效的文档类型")

    task_data = TaskCreate(
        stock_code=stock_code,
        document_type=doc_type,
        file_path=str(file_path),
        auto_filter=auto_filter
    )

    task_id = task_manager.create_task(task_data, str(file_path))

    # 启动异步处理
    script_path = Path(__file__).parent.parent.parent.parent / "scripts" / "chunk_pdf_by_sections.py"

    # 检查脚本是否存在
    if not script_path.exists():
        # 清理已上传的文件
        if file_path.exists():
            os.remove(file_path)
        raise HTTPException(
            status_code=500,
            detail=f"处理脚本不存在: {script_path}"
        )

    # 启动异步任务
    asyncio.create_task(task_manager.process_task(task_id, script_path))

    return {
        "task_id": task_id,
        "message": "文件上传成功，任务已启动",
        "file": file.filename
    }

@router.post("/batch", response_model=dict)
async def upload_files(
    files: List[UploadFile] = File(...),
    stock_code: str = Form(...),
    document_type: str = Form(...),
    auto_filter: bool = Form(True)
):
    """批量上传PDF文件"""
    try:
        doc_type = DocumentType(document_type)
    except ValueError:
        raise HTTPException(status_code=400, detail="无效的文档类型")

    # 检查脚本是否存在
    script_path = Path(__file__).parent.parent.parent.parent / "scripts" / "chunk_pdf_by_sections.py"
    if not script_path.exists():
        raise HTTPException(
            status_code=500,
            detail=f"处理脚本不存在: {script_path}"
        )

    task_ids = []
    skipped_files = []

    for file in files:
        if not file.filename.lower().endswith('.pdf'):
            skipped_files.append({
                "file": file.filename,
                "reason": "仅支持PDF文件"
            })
            continue

        # 保存文件
        file_path = UPLOAD_DIR / file.filename
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)

        # 检查过滤
        if auto_filter:
            import sys
            sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "scripts"))
            from document_filter_configurable import ConfigurableDocumentFilter

            filter_obj = ConfigurableDocumentFilter(str(file_path))
            should_process, reason = filter_obj.should_process()

            if not should_process:
                os.remove(file_path)
                skipped_files.append({
                    "file": file.filename,
                    "reason": f"被过滤: {reason}"
                })
                continue

        # 创建任务
        task_data = TaskCreate(
            stock_code=stock_code,
            document_type=doc_type,
            file_path=str(file_path),
            auto_filter=auto_filter
        )

        task_id = task_manager.create_task(task_data, str(file_path))
        task_ids.append(task_id)

        # 启动异步处理
        script_path = Path(__file__).parent.parent.parent.parent / "scripts" / "chunk_pdf_by_sections.py"
        asyncio.create_task(task_manager.process_task(task_id, script_path))

    return {
        "task_ids": task_ids,
        "skipped_files": skipped_files,
        "total_files": len(files),
        "uploaded_files": len(task_ids)
    }

def parse_stock_code_from_path(file_path: str) -> str:
    """从文件路径中解析股票代码"""
    # 匹配 HKEX/XXXXX/ 模式
    match = re.search(r'/HKEX/(\d{5})/', file_path)
    if match:
        return match.group(1)

    # 匹配文件名开头的股票代码
    match = re.search(r'^(\d{5})_', Path(file_path).name)
    if match:
        return match.group(1)

    return "00001"  # 默认值

def parse_document_type_from_filename(filename: str) -> str:
    """从文件名中解析文档类型（按优先级排序）"""
    filename_lower = filename.lower()

    # 按优先级排序：更具体的类型优先于通用类型

    # 1. 非常重大收购/出售（最具体）
    if any(keyword in filename_lower for keyword in [
        '非常重大收购', '非常重大出售', '非常重大收購', 'very_substantial_acquisition', 'very_substantial_disposal'
    ]):
        if '收购' in filename_lower or '收購' in filename_lower or 'acquisition' in filename_lower:
            return 'very_substantial_acquisition'
        else:
            return 'very_substantial_disposal'

    # 2. 关连交易
    elif any(keyword in filename_lower for keyword in [
        '关连交易', 'connected_transaction', '關連交易'
    ]):
        return 'connected_transaction'

    # 3. 须予披露交易
    elif any(keyword in filename_lower for keyword in [
        '须予披露交易', '須予披露交易', 'disclosable_transaction'
    ]):
        return 'disclosable_transaction'

    # 4. 收购
    elif any(keyword in filename_lower for keyword in [
        '收购', '收購', 'acquisition', '購併', '并购'
    ]):
        return 'acquisition'

    # 5. 出售/处置
    elif any(keyword in filename_lower for keyword in [
        '出售', '处置', '處置', 'disposal', '出售資產'
    ]):
        return 'disposal'

    # 6. 供股
    elif any(keyword in filename_lower for keyword in [
        '供股', 'rights', 'rights_issue', 'rights issue'
    ]):
        return 'rights'

    # 7. 配售
    elif any(keyword in filename_lower for keyword in [
        '配售', 'placing'
    ]):
        return 'placing'

    # 8. IPO/招股/上市
    elif any(keyword in filename_lower for keyword in [
        'ipo', '招股', '上市', '招股書', '招股书'
    ]):
        return 'ipo'

    # 9. 合股/股本整合
    elif any(keyword in filename_lower for keyword in [
        '合股', 'consolidation', '股本整合', '股本重組', '股本重组', 'share consolidation'
    ]):
        return 'consolidation'

    # 10. 拆股（分股）
    elif any(keyword in filename_lower for keyword in [
        '拆股', '分股', 'share split', 'stock split', '股份分拆', 'share_split'
    ]):
        return 'split'

    # 11. 股份回购
    elif any(keyword in filename_lower for keyword in [
        '股份回购', '股份回購', 'share repurchase', '股份回購要約', 'share_repurchase'
    ]):
        return 'share_repurchase'

    # 12. 股息分派
    elif any(keyword in filename_lower for keyword in [
        '股息', '分派', 'dividend', '派息', '末期股息', '特別股息'
    ]):
        return 'dividend'

    # 13. 股本缩减
    elif any(keyword in filename_lower for keyword in [
        '股本缩减', '股本縮減', 'capital reduction', '股本削減', 'capital_reduction'
    ]):
        return 'capital_reduction'

    # 14. 购股权计划
    elif any(keyword in filename_lower for keyword in [
        '购股权', '購股權', 'share option', '購股權計劃', 'share option scheme', 'share_option', 'share_option_scheme'
    ]):
        return 'share_option'

    # 15. 其他
    else:
        return 'other'

@router.post("/scan-directory", response_model=dict)
async def scan_directory(
    request: dict
):
    """扫描目录并返回PDF文件列表"""
    directory_path = request.get('directory_path')
    recursive = request.get('recursive', True)
    auto_filter = request.get('auto_filter', True)

    if not directory_path:
        raise HTTPException(status_code=400, detail="目录路径不能为空")

    base_path = Path(directory_path)

    if not base_path.exists():
        raise HTTPException(status_code=404, detail="目录不存在")

    if not base_path.is_dir():
        raise HTTPException(status_code=400, detail="路径不是目录")

    # 查找PDF文件
    if recursive:
        pdf_files = list(base_path.rglob("*.pdf"))
    else:
        pdf_files = list(base_path.glob("*.pdf"))

    scanned_files = []
    skipped_files = []

    for pdf_path in pdf_files:
        file_info = {
            "name": pdf_path.name,
            "path": str(pdf_path),
            "stock_code": parse_stock_code_from_path(str(pdf_path)),
            "document_type": parse_document_type_from_filename(pdf_path.name)
        }

        # 检查过滤
        if auto_filter:
            import sys
            sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "scripts"))
            from document_filter_configurable import ConfigurableDocumentFilter

            filter_obj = ConfigurableDocumentFilter(str(pdf_path))
            should_process, reason = filter_obj.should_process()

            if not should_process:
                skipped_files.append({
                    "file": pdf_path.name,
                    "reason": reason
                })
                continue

        scanned_files.append(file_info)

    return {
        "files": scanned_files,
        "skipped": skipped_files,
        "total_found": len(pdf_files),
        "total_valid": len(scanned_files)
    }

@router.post("/batch-from-directory", response_model=dict)
async def upload_files_from_directory(
    request: dict
):
    """从扫描的文件列表批量上传"""
    files = request.get('files', [])
    auto_filter = request.get('auto_filter', True)
    task_ids = []
    skipped_files = []

    # 检查脚本是否存在
    script_path = Path(__file__).parent.parent.parent.parent / "scripts" / "chunk_pdf_by_sections.py"
    if not script_path.exists():
        raise HTTPException(
            status_code=500,
            detail=f"处理脚本不存在: {script_path}"
        )

    for file_info in files:
        pdf_path = Path(file_info["path"])

        if not pdf_path.exists():
            skipped_files.append({
                "file": pdf_path.name,
                "reason": "文件不存在"
            })
            continue

        # 复制文件到上传目录
        target_path = UPLOAD_DIR / pdf_path.name
        import shutil
        shutil.copy2(pdf_path, target_path)

        # 再次检查过滤（如果需要）
        if auto_filter:
            import sys
            sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "scripts"))
            from document_filter_configurable import ConfigurableDocumentFilter

            filter_obj = ConfigurableDocumentFilter(str(target_path))
            should_process, reason = filter_obj.should_process()

            if not should_process:
                target_path.unlink()
                skipped_files.append({
                    "file": pdf_path.name,
                    "reason": f"被过滤: {reason}"
                })
                continue

        # 创建任务
        try:
            doc_type = DocumentType(file_info["document_type"])
        except ValueError:
            doc_type = DocumentType.other

        task_data = TaskCreate(
            stock_code=file_info["stock_code"],
            document_type=doc_type,
            file_path=str(target_path),
            auto_filter=auto_filter
        )

        task_id = task_manager.create_task(task_data, str(target_path))
        task_ids.append(task_id)

        # 启动异步处理
        script_path = Path(__file__).parent.parent.parent.parent / "scripts" / "chunk_pdf_by_sections.py"
        asyncio.create_task(task_manager.process_task(task_id, script_path))

    return {
        "task_ids": task_ids,
        "skipped_files": skipped_files,
        "total_files": len(files),
        "uploaded_files": len(task_ids)
    }
