#!/usr/bin/env python3
"""
文档过滤器 - 判断PDF文档是否应该进行切块处理
用法：python document_filter.py <pdf_path>
返回：0=应该处理，1=应该跳过
"""

import sys
import re
from pathlib import Path

# ====== 跳过规则（不进行切块的文档类型）======

# 1. 文件名关键词黑名单（包含这些关键词的文档会被跳过）
SKIP_KEYWORDS = [
    # 定期报告类
    '月报表', '月報表',
    '季报', '季報',
    '半年报', '半年報',
    '年报', '年報',
    '环境、社会及管治', '环境社会管治', 'ESG',
    
    # 会议通知类
    '股东大会通告', '股東大會通告',
    '股东周年大会', '股東週年大會',
    '股东特别大会', '股東特別大會',
    '通告', '通知',
    '委任代表表格', '代表委任表格',
    
    # 管理性文件
    '展示文件', '展示档案',
    '送呈', '送交',
    '更改', '更换', '更換',
    '变更', '變更',
    
    # 日常运营类
    '董事会会议', '董事會會議',
    '董事名单', '董事名單',
    '业务发展最新情况', '業務發展最新情況',
    
    # 表格类
    '月份之股份发行人的证券变动月报表',
    '證券變動月報表',
    
    # 其他杂项
    '盈利警告', '盈警',
    '暂停办理过户登记手续', '暫停辦理過戶',
]

# 2. 文件名模式黑名单（匹配这些正则模式的会被跳过）
SKIP_PATTERNS = [
    r'^\d{4}-\d{2}-\d{2}_\d{5}_.*_月报表',  # 月报表
    r'^\d{4}-\d{2}-\d{2}_\d{5}_.*_月報表',
    r'^\d{4}-\d{2}-\d{2}_\d{5}_.*_委任代表表格',  # 代表委任
    r'^\d{4}-\d{2}-\d{2}_\d{5}_.*_展示文件',  # 展示文件
    r'^\d{4}-\d{2}-\d{2}_\d{5}_.*_董事名单',  # 董事名单
    r'^\d{4}-\d{2}-\d{2}_\d{5}_.*_更[换換改變]',  # 各种更改
]

# 3. 应该处理的文档类型白名单（优先级高于黑名单）
PROCESS_KEYWORDS = [
    '供股',
    '配售',
    'IPO',
    '招股',
    '上市',
    '合股',
    '股本整合',
    '收购', '收購',
    '出售', '處置',
    '须予披露交易', '須予披露交易',
    '关连交易', '關連交易',
    '非常重大出售', '非常重大收购',
]


class DocumentFilter:
    """文档过滤器"""
    
    def __init__(self, pdf_path: str):
        self.pdf_path = Path(pdf_path)
        self.filename = self.pdf_path.stem
    
    def should_process(self) -> tuple[bool, str]:
        """
        判断文档是否应该处理
        
        Returns:
            (should_process, reason) - (是否处理, 原因说明)
        """
        # 1. 白名单检查（优先）
        for keyword in PROCESS_KEYWORDS:
            if keyword in self.filename:
                return (True, f"白名单匹配: {keyword}")
        
        # 2. 黑名单关键词检查
        for keyword in SKIP_KEYWORDS:
            if keyword in self.filename:
                return (False, f"黑名单关键词: {keyword}")
        
        # 3. 黑名单模式检查
        for pattern in SKIP_PATTERNS:
            if re.search(pattern, self.filename):
                return (False, f"黑名单模式匹配: {pattern}")
        
        # 4. 默认：处理
        return (True, "未匹配跳过规则，默认处理")
    
    def print_decision(self):
        """打印过滤决策"""
        should_process, reason = self.should_process()
        
        print("=" * 80)
        print("📄 文档过滤检查")
        print("=" * 80)
        print(f"文件: {self.filename}")
        print(f"路径: {self.pdf_path}")
        print("-" * 80)
        print(f"决策: {'✅ 应该处理' if should_process else '⏭️  跳过处理'}")
        print(f"原因: {reason}")
        print("=" * 80)
        
        return should_process


def main():
    if len(sys.argv) < 2:
        print("用法: python document_filter.py <pdf_path>")
        print("返回码: 0=应该处理, 1=应该跳过")
        sys.exit(2)
    
    pdf_path = sys.argv[1]
    
    if not Path(pdf_path).exists():
        print(f"❌ 文件不存在: {pdf_path}")
        sys.exit(2)
    
    filter = DocumentFilter(pdf_path)
    should_process = filter.print_decision()
    
    # 返回码：0=应该处理，1=应该跳过
    sys.exit(0 if should_process else 1)


if __name__ == '__main__':
    main()

