#!/usr/bin/env python3
"""
供股PDF按章节切块脚本（无向量版本）
用法：python chunk_pdf_by_sections.py <pdf_path> <stock_code>
"""

import json
import re
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Tuple

import clickhouse_connect
import fitz  # PyMuPDF

# 导入项目配置
sys.path.insert(0, str(Path(__file__).parent.parent))
from src.config.settings import get_settings

# ====== 配置 ======
settings = get_settings()
CLICKHOUSE_HOST = settings.clickhouse_host
CLICKHOUSE_PORT = settings.clickhouse_port
CLICKHOUSE_DB = settings.clickhouse_database
CLICKHOUSE_USER = settings.clickhouse_user
CLICKHOUSE_PASSWORD = settings.clickhouse_password

# ====== 章节类型关键词映射 ======
SECTION_TYPE_KEYWORDS = {
    'terms': ['供股', '认购', '条款', '供股详情', '参与供股', '配售'],
    'timetable': ['时间表', '预期时间表', '重要日期', '日程'],
    'underwriting': ['包销', '承配', '保荐人', '包销商'],
    'financials': ['财务', '业绩', '财务资料', '债务', '債務', '营运资金', '營運資金', '财务概要', '財務資料',
                   '貿易前景'],
    'risk_factors': ['风险因素', '投资风险', '主要风险', '不利变动', '不利變動'],
    'suspension': ['暂停办理', '过户登记', '暂停过户'],
    'use_of_proceeds': ['募集资金', '所得款项', '资金用途'],
    'management': ['董事', '高级管理层', '高級管理層', '董事服务', '董事服務'],
    'company_info': ['公司资料', '公司資料', '公司信息'],
    'legal': ['责任声明', '責任聲明', '法律', '专家', '專家'],
    'contracts': ['重大合约', '重大合約', '合同'],
    'disclosure': ['权益披露', '權益披露', '披露'],
    'market': ['市场价格', '市場價格', '股价'],
    'interests': ['竞争权益', '競爭權益', '利益冲突'],
    'documents': ['展示文件', '送呈', '文件'],
    'appendix': ['附录', '附件', '補充資料'],
    'misc': ['其他事項', '其他事项', '杂项'],  # 新增：明确的其他类
}

# ====== 章节标题正则模式 ======
SECTION_PATTERNS = [
    # 中文数字主章节：一、二、三、... （必须有"、"分隔，且标题至少2字符）
    (r'^([一二三四五六七八九十]+)[、]\s*(.{2,})$', 1),
    # 括号章节：（一）（二）（三）（标题至少2字符）
    (r'^[（(]([一二三四五六七八九十]+)[)）]\s*(.{2,})$', 2),
    # 数字章节：1. 2. 3. （1-2位数字+点号+非数字开头的标题）
    (r'^(\d{1,2})\.\s+([^\d].{2,})$', 3),
]


class PDFSectionChunker:
    """PDF章节切块处理器"""

    def __init__(self, pdf_path: str, stock_code: str):
        self.pdf_path = Path(pdf_path)
        self.stock_code = stock_code
        self.doc = None
        self.doc_id = None
        self.ch_client = None

    def connect_clickhouse(self):
        """连接ClickHouse"""
        print(f"📡 连接ClickHouse: {CLICKHOUSE_HOST}:{CLICKHOUSE_PORT}/{CLICKHOUSE_DB}")
        self.ch_client = clickhouse_connect.get_client(
            host=CLICKHOUSE_HOST,
            port=CLICKHOUSE_PORT,
            database=CLICKHOUSE_DB,
            username=CLICKHOUSE_USER,
            password=CLICKHOUSE_PASSWORD
        )
        print("✅ ClickHouse连接成功")

    def open_pdf(self):
        """打开PDF文档"""
        if not self.pdf_path.exists():
            raise FileNotFoundError(f"PDF文件不存在: {self.pdf_path}")

        print(f"📄 打开PDF: {self.pdf_path.name}")
        self.doc = fitz.open(self.pdf_path)
        print(f"   总页数: {len(self.doc)}")

    def generate_doc_id(self) -> str:
        """生成文档ID"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        random_suffix = uuid.uuid4().hex[:8]
        return f"{self.stock_code}_{timestamp}_{random_suffix}"

    def extract_metadata_from_filename(self) -> Dict:
        """从文件名提取元信息"""
        filename = self.pdf_path.stem
        full_filename = self.pdf_path.name  # 包含扩展名的完整文件名

        # 提取日期（YYYY-MM-DD格式）
        date_match = re.search(r'(\d{4}-\d{2}-\d{2})', filename)
        publish_date = datetime.strptime(date_match.group(1),
                                         '%Y-%m-%d').date() if date_match else datetime.now().date()

        # 提取公司名（股票代码后的第一个中文片段）
        company_match = re.search(rf'{self.stock_code}_(.+?)_', filename)
        company_name = company_match.group(1) if company_match else ''

        # 判断是否包销（更准确的判断）
        # "非包銷" 优先级高于 "包銷"
        if '非包銷' in full_filename or '非包销' in full_filename:
            is_underwritten = False
        elif '包銷' in full_filename or '包销' in full_filename:
            is_underwritten = True
        else:
            is_underwritten = False
        sub_type = 'underwritten' if is_underwritten else 'non-underwritten'

        # 提取供股比例（多种模式）
        rights_ratio = ''
        # 模式1: 每持有一(1)股經調整股份獲發四(4)股
        ratio_match1 = re.search(r'每持有.{0,5}[（(]?(\d+)[)）]?.{0,10}獲發.{0,5}[（(]?(\d+)[)）]?.?股', full_filename)
        if ratio_match1:
            rights_ratio = f"{ratio_match1.group(1)}:{ratio_match1.group(2)}"
        else:
            # 模式2: 简化版
            ratio_match2 = re.search(r'(\d+).?股.+?(\d+).?股', full_filename)
            if ratio_match2:
                rights_ratio = f"{ratio_match2.group(1)}:{ratio_match2.group(2)}"

        return {
            'publish_date': publish_date,
            'company_name': company_name,
            'sub_type': sub_type,
            'rights_ratio': rights_ratio,
            'title': filename
        }

    def detect_section_level(self, line: str) -> Tuple[int, str, str]:
        """
        检测章节标题及层级
        返回: (层级, 章节编号, 章节标题)
        """
        line = line.strip()

        for pattern, level in SECTION_PATTERNS:
            match = re.match(pattern, line)
            if match:
                if len(match.groups()) == 2:
                    section_num = match.group(1)
                    section_title = match.group(2).strip()
                    return (level, section_num, section_title)

        return (0, '', '')

    def classify_section_type(self, title: str) -> str:
        """根据标题关键词分类章节类型"""
        for section_type, keywords in SECTION_TYPE_KEYWORDS.items():
            if any(kw in title for kw in keywords):
                return section_type
        return 'other'

    def extract_sections(self) -> List[Dict]:
        """提取文档的所有章节"""
        sections = []
        current_section = None
        section_index = 0

        print("\n🔍 开始提取章节...")

        for page_num in range(len(self.doc)):
            page = self.doc[page_num]
            text = page.get_text()

            # 按行处理
            lines = text.split('\n')

            for line in lines:
                level, section_num, section_title = self.detect_section_level(line)

                # 检测到新章节
                if level > 0:
                    # 保存上一个章节
                    if current_section:
                        sections.append(current_section)

                    # 创建新章节
                    section_type = self.classify_section_type(section_title)
                    current_section = {
                        'section_id': str(uuid.uuid4()),
                        'section_index': section_index,
                        'section_level': level,
                        'section_num': section_num,
                        'section_title': section_title,
                        'section_type': section_type,
                        'content': '',
                        'page_start': page_num + 1,
                        'page_end': page_num + 1
                    }
                    section_index += 1

                    print(f"   [{section_index}] Lv{level} {section_type:12s} | {section_num} {section_title}")

                # 追加内容到当前章节
                elif current_section:
                    current_section['content'] += line + '\n'
                    current_section['page_end'] = page_num + 1

        # 保存最后一个章节
        if current_section:
            sections.append(current_section)

        print(f"\n✅ 共提取 {len(sections)} 个章节")
        return sections

    def insert_document_metadata(self, metadata: Dict, total_sections: int):
        """插入文档元信息"""
        print("\n💾 插入文档元信息到 documents_v2...")

        # 匹配最新表结构（无embedding字段）
        data = [[
            self.doc_id,  # doc_id
            metadata['title'],  # title
            self.stock_code,  # stock_code
            metadata['company_name'],  # company_name
            'rights',  # document_type
            metadata['sub_type'],  # document_subtype
            metadata['publish_date'],  # announcement_date
            datetime.now(),  # processing_date
            str(self.pdf_path),  # file_path
            self.pdf_path.stat().st_size if self.pdf_path.exists() else 0,  # file_size
            len(self.doc),  # page_count
            'completed',  # processing_status
            '',  # error_message
            total_sections,  # section_count
            0,  # total_chars (暂时为0)
            json.dumps({  # metadata (JSON格式)
                'rights_ratio': metadata['rights_ratio'],
                'processing_version': '2.0',
                'source_system': 'hkex'
            }, ensure_ascii=False)
        ]]

        self.ch_client.insert(
            'documents_v2',
            data,
            column_names=[
                'doc_id', 'title', 'stock_code', 'company_name', 'document_type',
                'document_subtype', 'announcement_date', 'processing_date', 'file_path',
                'file_size', 'page_count', 'processing_status', 'error_message',
                'section_count', 'total_chars', 'metadata'
            ]
        )
        print("✅ 文档元信息已插入")

    def check_if_processed(self) -> bool:
        """检查文档是否已处理（断点续传）"""
        try:
            # 通过文件路径查询
            result = self.ch_client.query(
                f"SELECT count() FROM documents_v2 WHERE file_path = '{str(self.pdf_path)}'"
            )
            count = result.result_rows[0][0]
            return count > 0
        except Exception:
            return False

    def insert_sections(self, sections: List[Dict]):
        """批量插入章节数据（带进度提示）"""
        total = len(sections)
        print(f"\n💾 插入 {total} 个章节到 document_sections...")

        # 批量插入（提高性能）
        batch_size = 50
        for i in range(0, total, batch_size):
            batch = sections[i:i + batch_size]
            data = []

            for section in batch:
                data.append([
                    section['section_id'],  # section_id
                    self.doc_id,  # doc_id
                    'rights',  # document_type
                    section['section_type'],  # section_type
                    '',  # section_subtype
                    section['section_title'],  # section_title
                    section['section_index'],  # section_index
                    section['page_start'],  # page_start
                    section['page_end'],  # page_end
                    section['content'],  # content
                    '',  # content_hash
                    len(section['content']),  # char_count
                    0,  # word_count
                    section['section_level'],  # priority
                    'normal',  # importance
                    1.0,  # confidence
                    'regex',  # identification_method
                    json.dumps({  # metadata (JSON格式)
                        'section_num': section['section_num'],
                        'has_table': False,
                        'table_count': 0
                    }, ensure_ascii=False)
                ])

            self.ch_client.insert(
                'document_sections',
                data,
                column_names=[
                    'section_id', 'doc_id', 'document_type', 'section_type',
                    'section_subtype', 'section_title', 'section_index',
                    'page_start', 'page_end', 'content', 'content_hash',
                    'char_count', 'word_count', 'priority', 'importance',
                    'confidence', 'identification_method', 'metadata'
                ]
            )

            # 进度提示
            progress = min(i + batch_size, total)
            percentage = (progress / total) * 100
            print(f"   [{progress}/{total}] {percentage:.0f}%", end='\r')

        print(f"\n✅ 章节数据已插入完成")

    def verify_integrity(self):
        """验证数据完整性"""
        print(f"\n🔍 验证数据完整性...")

        # 1. 验证文档记录
        doc_count = self.ch_client.query(
            f"SELECT count() FROM documents_v2 WHERE doc_id = '{self.doc_id}'"
        ).result_rows[0][0]

        if doc_count != 1:
            raise ValueError(f"文档记录异常: 期望1条，实际{doc_count}条")

        # 2. 验证章节记录数
        section_count = self.ch_client.query(
            f"SELECT count() FROM document_sections WHERE doc_id = '{self.doc_id}'"
        ).result_rows[0][0]

        expected_count = self.ch_client.query(
            f"SELECT section_count FROM documents_v2 WHERE doc_id = '{self.doc_id}'"
        ).result_rows[0][0]

        if section_count != expected_count:
            raise ValueError(f"章节数不匹配: 期望{expected_count}条，实际{section_count}条")

        # 3. 验证章节连续性
        indices = self.ch_client.query(
            f"SELECT section_index FROM document_sections WHERE doc_id = '{self.doc_id}' ORDER BY section_index"
        ).result_rows

        for i, (idx,) in enumerate(indices):
            if idx != i:
                raise ValueError(f"章节索引不连续: 期望{i}，实际{idx}")

        print(f"✅ 数据完整性验证通过")
        print(f"   文档记录: {doc_count}条")
        print(f"   章节记录: {section_count}条")
        print(f"   索引连续: 是")

    def process(self, skip_if_exists: bool = True):
        """
        完整处理流程（带断点续传）
        
        Args:
            skip_if_exists: 如果文档已存在，是否跳过处理
        """
        try:
            # 1. 连接数据库
            self.connect_clickhouse()

            # 2. 断点续传检查
            if skip_if_exists and self.check_if_processed():
                print(f"\n⏭️  文档已处理，跳过: {self.pdf_path.name}")
                print(f"   如需重新处理，请先删除数据库中的记录")
                return

            # 3. 打开PDF
            self.open_pdf()

            # 4. 生成doc_id
            self.doc_id = self.generate_doc_id()
            print(f"\n🆔 文档ID: {self.doc_id}")

            # 5. 提取元信息
            metadata = self.extract_metadata_from_filename()
            print(f"\n📋 元信息:")
            print(f"   公司: {metadata['company_name']}")
            print(f"   日期: {metadata['publish_date']}")
            print(f"   类型: {metadata['sub_type']}")
            print(f"   比例: {metadata['rights_ratio'] if metadata['rights_ratio'] else '未提取到'}")

            # 6. 提取章节
            sections = self.extract_sections()

            # 7. 插入数据库
            self.insert_document_metadata(metadata, len(sections))
            self.insert_sections(sections)

            # 8. 完整性验证
            self.verify_integrity()

            print(f"\n✅ 处理完成！")
            print(f"   文档ID: {self.doc_id}")
            print(f"   文件: {self.pdf_path.name}")

            # 9. 显示示例查询
            print(f"\n📊 查询示例:")
            print(
                f"   SELECT section_type, section_title FROM document_sections WHERE doc_id = '{self.doc_id}' ORDER BY section_index;")

        except Exception as e:
            print(f"\n❌ 处理失败: {e}")
            import traceback
            traceback.print_exc()
            raise
        finally:
            if self.doc:
                self.doc.close()
            if self.ch_client:
                self.ch_client.close()


def main():
    if len(sys.argv) < 3:
        print("用法: python chunk_pdf_by_sections.py <pdf_path> <stock_code>")
        print("示例: python chunk_pdf_by_sections.py '../HKEX/00328/供股/xxx.pdf' 00328")
        sys.exit(1)

    pdf_path = sys.argv[1]
    stock_code = sys.argv[2]

    chunker = PDFSectionChunker(pdf_path, stock_code)
    chunker.process()


if __name__ == '__main__':
    main()
