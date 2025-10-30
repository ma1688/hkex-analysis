"""
数据管理服务
"""

from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
import clickhouse_connect
from pathlib import Path
import sys

from ..models.schemas import (
    DocumentInfo, SectionInfo, Statistics,
    DuplicateFile, CleanupResult
)
from src.config.settings import get_settings

settings = get_settings()

class DataService:
    """数据服务"""

    def __init__(self):
        self.client = None
        self._init_client()

    def _init_client(self):
        """初始化 ClickHouse 客户端，增加超时和错误处理"""
        try:
            self.client = clickhouse_connect.get_client(
                host=settings.clickhouse_host,
                port=settings.clickhouse_port,
                database=settings.clickhouse_database,
                username=settings.clickhouse_user,
                password=settings.clickhouse_password,
                connect_timeout=5  # 连接超时5秒
            )
            # 测试连接
            self.client.query("SELECT 1")
        except Exception as e:
            print(f"ClickHouse 连接失败: {e}")
            self.client = None

    def _ensure_client(self):
        """确保客户端连接有效"""
        if self.client is None:
            self._init_client()
        return self.client is not None

    def get_documents(
        self,
        stock_code: Optional[str] = None,
        document_type: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> Tuple[List[DocumentInfo], int]:
        """获取文档列表"""
        # 确保客户端连接有效
        if not self._ensure_client():
            return [], 0

        try:
            query = """
            SELECT
                doc_id, stock_code, company_name, title, document_type,
                document_subtype, announcement_date, section_count,
                metadata, created_at
            FROM documents_v2
            """

            conditions = []

            if stock_code:
                conditions.append(f"stock_code = '{stock_code}'")

            if document_type:
                conditions.append(f"document_type = '{document_type}'")

            if conditions:
                query += " WHERE " + " AND ".join(conditions)

            query += f" ORDER BY created_at DESC LIMIT {limit} OFFSET {offset}"

            result = self.client.query(query).result_rows

            # 获取总数
            count_query = "SELECT count() FROM documents_v2"
            if conditions:
                count_query += " WHERE " + " AND ".join(conditions)

            total = self.client.query(count_query).result_rows[0][0]

            documents = []
            for row in result:
                doc = DocumentInfo(
                    doc_id=row[0],
                    stock_code=row[1],
                    company_name=row[2],
                    title=row[3],
                    document_type=row[4],
                    document_subtype=row[5],
                    announcement_date=row[6],
                    section_count=row[7],
                    metadata=eval(row[8]) if row[8] else {},
                    created_at=row[9]
                )
                documents.append(doc)

            return documents, total
        except Exception as e:
            print(f"获取文档列表失败: {e}")
            return [], 0

    def get_document(self, doc_id: str) -> Optional[DocumentInfo]:
        """获取单个文档"""
        # 确保客户端连接有效
        if not self._ensure_client():
            return None

        try:
            query = f"""
            SELECT
                doc_id, stock_code, company_name, title, document_type,
                document_subtype, announcement_date, section_count,
                metadata, created_at
            FROM documents_v2
            WHERE doc_id = '{doc_id}'
            """

            result = self.client.query(query).result_rows

            if not result:
                return None

            row = result[0]
            return DocumentInfo(
                doc_id=row[0],
                stock_code=row[1],
                company_name=row[2],
                title=row[3],
                document_type=row[4],
                document_subtype=row[5],
                announcement_date=row[6],
                section_count=row[7],
                metadata=eval(row[8]) if row[8] else {},
                created_at=row[9]
            )
        except Exception as e:
            print(f"获取文档失败: {e}")
            return None

    def get_sections(self, doc_id: str, limit: int = 100) -> List[SectionInfo]:
        """获取章节列表"""
        # 确保客户端连接有效
        if not self._ensure_client():
            return []

        try:
            query = f"""
            SELECT
                section_id, doc_id, section_type, section_title,
                section_index, content, char_count, metadata
            FROM document_sections
            WHERE doc_id = '{doc_id}'
            ORDER BY section_index
            LIMIT {limit}
            """

            result = self.client.query(query).result_rows

            sections = []
            for row in result:
                section = SectionInfo(
                    section_id=row[0],
                    doc_id=row[1],
                    section_type=row[2],
                    section_title=row[3],
                    section_index=row[4],
                    content=row[5],
                    char_count=row[6],
                    metadata=eval(row[7]) if row[7] else {}
                )
                sections.append(section)

            return sections
        except Exception as e:
            print(f"获取章节列表失败: {e}")
            return []

    def get_statistics(self) -> Statistics:
        """获取统计数据"""
        # 确保客户端连接有效
        if not self._ensure_client():
            # 连接失败时返回默认值
            return Statistics(
                total_documents=0,
                total_sections=0,
                documents_by_type={},
                documents_by_status={},
                recent_documents=[],
                top_companies=[],
                processing_stats={
                    'this_week': 0,
                    'total': 0
                }
            )

        try:
            # 总文档数
            total_documents = self.client.query(
                "SELECT count() FROM documents_v2"
            ).result_rows[0][0]

            # 总章节数
            total_sections = self.client.query(
                "SELECT count() FROM document_sections"
            ).result_rows[0][0]

            # 按类型统计
            documents_by_type = {}
            type_result = self.client.query("""
                SELECT document_type, count() as cnt
                FROM documents_v2
                GROUP BY document_type
            """).result_rows

            for row in type_result:
                documents_by_type[row[0]] = row[1]

            # 最近文档
            recent_docs, _ = self.get_documents(limit=10)
            recent_documents = recent_docs

            # 热门公司
            top_companies = []
            company_result = self.client.query("""
                SELECT company_name, count(*) as cnt
                FROM documents_v2
                GROUP BY company_name
                ORDER BY cnt DESC
                LIMIT 10
            """).result_rows

            for row in company_result:
                top_companies.append({
                    'company_name': row[0],
                    'count': row[1]
                })

            # 处理统计
            last_week = datetime.now() - timedelta(days=7)
            last_week_str = last_week.strftime('%Y-%m-%d %H:%M:%S')
            query_str = f"""
                SELECT count()
                FROM documents_v2
                WHERE created_at >= toDateTime('{last_week_str}')
            """
            processing_stats = {
                'this_week': self.client.query(query_str).result_rows[0][0],
                'total': total_documents
            }

            return Statistics(
                total_documents=total_documents,
                total_sections=total_sections,
                documents_by_type=documents_by_type,
                documents_by_status={},
                recent_documents=recent_documents,
                top_companies=top_companies,
                processing_stats=processing_stats
            )
        except Exception as e:
            print(f"获取统计数据失败: {e}")
            # 返回默认值
            return Statistics(
                total_documents=0,
                total_sections=0,
                documents_by_type={},
                documents_by_status={},
                recent_documents=[],
                top_companies=[],
                processing_stats={
                    'this_week': 0,
                    'total': 0
                }
            )

    def check_duplicates(self) -> CleanupResult:
        """检查重复数据"""
        # 确保客户端连接有效
        if not self._ensure_client():
            return CleanupResult(
                dry_run=True,
                duplicates_found=0,
                files_to_delete=[],
                total_records_to_delete=0
            )

        try:
            duplicates_query = """
            SELECT
                file_path,
                groupArray(doc_id) as doc_ids,
                count() as cnt
            FROM documents_v2
            GROUP BY file_path
            HAVING cnt > 1
            ORDER BY cnt DESC
            """

            duplicates = self.client.query(duplicates_query).result_rows

            if not duplicates:
                return CleanupResult(
                    dry_run=True,
                    duplicates_found=0,
                    files_to_delete=[],
                    total_records_to_delete=0
                )

            files_to_delete = []

            for file_path, doc_ids, count in duplicates:
                # 查询创建时间，保留最新的
                # ClickHouse IN子句不支持参数化，需要手动构建
                in_clause = ','.join([f"'{d}'" for d in doc_ids])
                time_query = f"""
                SELECT doc_id, created_at
                FROM documents_v2
                WHERE doc_id IN ({in_clause})
                ORDER BY created_at DESC
                """

                records = self.client.query(time_query).result_rows
                keep_doc_id = records[0][0] if records else doc_ids[0]
                delete_doc_ids = [r[0] for r in records[1:]] if len(records) > 1 else doc_ids[1:]

                duplicate_file = DuplicateFile(
                    file_path=file_path,
                    doc_ids=doc_ids,
                    count=count,
                    keep_doc_id=keep_doc_id,
                    delete_doc_ids=delete_doc_ids
                )
                files_to_delete.append(duplicate_file)

            total_to_delete = sum(len(f.delete_doc_ids) for f in files_to_delete)

            return CleanupResult(
                dry_run=True,
                duplicates_found=len(duplicates),
                files_to_delete=files_to_delete,
                total_records_to_delete=total_to_delete
            )
        except Exception as e:
            print(f"检查重复数据失败: {e}")
            return CleanupResult(
                dry_run=True,
                duplicates_found=0,
                files_to_delete=[],
                total_records_to_delete=0
            )

    def cleanup_duplicates(self, dry_run: bool = True) -> CleanupResult:
        """清理重复数据"""
        if dry_run:
            return self.check_duplicates()

        result = self.check_duplicates()

        for file_info in result.files_to_delete:
            for doc_id in file_info.delete_doc_ids:
                # 先删除章节
                self.client.command(
                    f"ALTER TABLE document_sections DELETE WHERE doc_id = '{doc_id}'"
                )
                # 再删除文档
                self.client.command(
                    f"ALTER TABLE documents_v2 DELETE WHERE doc_id = '{doc_id}'"
                )

        # 优化表
        self.client.command("OPTIMIZE TABLE documents_v2 FINAL")
        self.client.command("OPTIMIZE TABLE document_sections FINAL")

        return CleanupResult(
            dry_run=False,
            duplicates_found=result.duplicates_found,
            files_to_delete=result.files_to_delete,
            total_records_to_delete=result.total_records_to_delete
        )

    def search_documents(self, query: str, limit: int = 50) -> List[DocumentInfo]:
        """搜索文档"""
        # 确保客户端连接有效
        if not self._ensure_client():
            return []

        try:
            search_pattern = f'%{query}%'
            search_query = f"""
            SELECT
                doc_id, stock_code, company_name, title, document_type,
                document_subtype, announcement_date, section_count,
                metadata, created_at
            FROM documents_v2
            WHERE company_name ILIKE '{search_pattern}'
               OR stock_code = '{query}'
            ORDER BY created_at DESC
            LIMIT {limit}
            """

            result = self.client.query(search_query).result_rows

            documents = []
            for row in result:
                doc = DocumentInfo(
                    doc_id=row[0],
                    stock_code=row[1],
                    company_name=row[2],
                    title=row[3],
                    document_type=row[4],
                    document_subtype=row[5],
                    announcement_date=row[6],
                    section_count=row[7],
                    metadata=eval(row[8]) if row[8] else {},
                    created_at=row[9]
                )
                documents.append(doc)

            return documents
        except Exception as e:
            print(f"搜索文档失败: {e}")
            return []

    def delete_document(self, doc_id: str) -> bool:
        """删除单个文档"""
        # 确保客户端连接有效
        if not self._ensure_client():
            return False

        try:
            # 先删除章节
            self.client.command(
                f"ALTER TABLE document_sections DELETE WHERE doc_id = '{doc_id}'"
            )
            # 再删除文档
            self.client.command(
                f"ALTER TABLE documents_v2 DELETE WHERE doc_id = '{doc_id}'"
            )
            return True
        except Exception as e:
            print(f"删除文档失败: {e}")
            return False

    def delete_documents_batch(self, doc_ids: List[str]) -> int:
        """批量删除文档"""
        deleted_count = 0
        for doc_id in doc_ids:
            if self.delete_document(doc_id):
                deleted_count += 1
        return deleted_count

    def delete_all_data(self) -> bool:
        """清空所有数据（危险操作）"""
        # 确保客户端连接有效
        if not self._ensure_client():
            return False

        try:
            # 删除所有章节
            self.client.command("ALTER TABLE document_sections DELETE WHERE 1")
            # 删除所有文档
            self.client.command("ALTER TABLE documents_v2 DELETE WHERE 1")
            # 优化表
            self.client.command("OPTIMIZE TABLE documents_v2 FINAL")
            self.client.command("OPTIMIZE TABLE document_sections FINAL")
            return True
        except Exception as e:
            print(f"清空数据失败: {e}")
            return False

# 全局数据服务实例
data_service = DataService()
