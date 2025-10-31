#!/usr/bin/env python3
"""
可配置的文档过滤器 - 支持自定义过滤规则
基于 YAML 配置文件，支持多种过滤方式
"""

import sys
import re
import os
import yaml
import hashlib
from pathlib import Path
from typing import Tuple, Optional, Dict, Any
from datetime import datetime

# 缓存配置
_FILTER_CACHE = {}
_CONFIG_HASH = None
_CONFIG_PATH = None

class ConfigurableDocumentFilter:
    """可配置的文档过滤器"""

    def __init__(self, pdf_path: str, config_path: str = None):
        self.pdf_path = Path(pdf_path)
        self.filename = self.pdf_path.stem
        self.config_path = config_path or self._get_default_config_path()
        self.config = self._load_config()
        self.cached_decision = None

    def _get_default_config_path(self) -> str:
        """获取默认配置文件路径"""
        current_dir = Path(__file__).parent
        config_dir = current_dir.parent / "config"
        return str(config_dir / "document_filter.yaml")

    def _load_config(self) -> Dict[str, Any]:
        """加载配置文件"""
        global _CONFIG_HASH

        if not os.path.exists(self.config_path):
            print(f"⚠️  配置文件不存在: {self.config_path}")
            print("📝 使用默认配置")
            return self._get_default_config()

        # 读取配置文件
        with open(self.config_path, 'r', encoding='utf-8') as f:
            content = f.read()
            config = yaml.safe_load(content)

        # 计算配置文件哈希，用于检测配置变更
        _CONFIG_HASH = hashlib.md5(content.encode('utf-8')).hexdigest()

        return config

    def _get_default_config(self) -> Dict[str, Any]:
        """获取默认配置（当配置文件不存在时使用）"""
        return {
            'filter_mode': {'mode': 'hybrid'},
            'document_types': {
                'whitelist': [],
                'blacklist': [],
                'default_action': 'process'
            },
            'keyword_filters': {
                'blacklist': [],
                'whitelist': [],
                'enabled': True
            },
            'pattern_filters': {
                'blacklist_patterns': [],
                'whitelist_patterns': [],
                'enabled': True
            },
            'file_filters': {
                'size': {'enabled': False},
                'date': {'enabled': False},
                'filename_length': {'enabled': False}
            },
            'special_rules': {
                'force_process_patterns': [],
                'force_skip_patterns': [],
                'enabled': True
            },
            'logging': {
                'verbose': True,
                'log_decisions': True
            },
            'cache': {
                'enabled': True,
                'ttl': 3600
            }
        }

    def _check_config_changed(self) -> bool:
        """检查配置文件是否发生变化"""
        global _CONFIG_HASH
        if not os.path.exists(self.config_path):
            return False

        with open(self.config_path, 'r', encoding='utf-8') as f:
            content = f.read()
            current_hash = hashlib.md5(content.encode('utf-8')).hexdigest()

        return current_hash != _CONFIG_HASH

    def _get_cached_decision(self) -> Optional[Tuple[bool, str]]:
        """获取缓存的决策"""
        if not self.config.get('cache', {}).get('enabled', True):
            return None

        if self._check_config_changed():
            # 配置已变更，清空缓存
            global _FILTER_CACHE
            _FILTER_CACHE.clear()
            return None

        cache_key = f"{self.pdf_path}_{_CONFIG_HASH}"
        return _FILTER_CACHE.get(cache_key)

    def _cache_decision(self, decision: Tuple[bool, str]):
        """缓存决策结果"""
        if not self.config.get('cache', {}).get('enabled', True):
            return

        global _FILTER_CACHE
        cache_key = f"{self.pdf_path}_{_CONFIG_HASH}"
        _FILTER_CACHE[cache_key] = decision

    def _parse_document_type(self) -> str:
        """解析文档类型（复用之前的逻辑）"""
        filename_lower = self.filename.lower()

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

    def _check_document_type_filter(self) -> Optional[Tuple[bool, str]]:
        """检查文档类型过滤"""
        doc_type = self._parse_document_type()
        doc_config = self.config.get('document_types', {})
        whitelist = doc_config.get('whitelist') or []
        blacklist = doc_config.get('blacklist') or []
        default_action = doc_config.get('default_action', 'process')

        # 黑名单检查
        if doc_type in blacklist:
            return (False, f"文档类型在黑名单中: {doc_type}")

        # 白名单检查
        if doc_type in whitelist:
            return (True, f"文档类型在白名单中: {doc_type}")

        # 默认处理
        return (default_action == 'process', f"文档类型未指定，使用默认策略: {default_action}")

    def _check_keyword_filter(self) -> Optional[Tuple[bool, str]]:
        """检查关键词过滤"""
        keyword_config = self.config.get('keyword_filters', {})
        if not keyword_config.get('enabled', True):
            return None

        filename_lower = self.filename.lower()
        whitelist = keyword_config.get('whitelist') or []
        blacklist = keyword_config.get('blacklist') or []

        # 白名单关键词检查
        for keyword in whitelist:
            if keyword in filename_lower:
                return (True, f"白名单关键词匹配: {keyword}")

        # 黑名单关键词检查
        for keyword in blacklist:
            if keyword in filename_lower:
                return (False, f"黑名单关键词匹配: {keyword}")

        return None

    def _check_pattern_filter(self) -> Optional[Tuple[bool, str]]:
        """检查模式过滤（正则表达式）"""
        pattern_config = self.config.get('pattern_filters', {})
        if not pattern_config.get('enabled', True):
            return None

        whitelist_patterns = pattern_config.get('whitelist_patterns') or []
        blacklist_patterns = pattern_config.get('blacklist_patterns') or []

        # 白名单模式检查
        for pattern in whitelist_patterns:
            if re.search(pattern, self.filename):
                return (True, f"白名单模式匹配: {pattern}")

        # 黑名单模式检查
        for pattern in blacklist_patterns:
            if re.search(pattern, self.filename):
                return (False, f"黑名单模式匹配: {pattern}")

        return None

    def _check_file_filters(self) -> Optional[Tuple[bool, str]]:
        """检查文件属性过滤"""
        file_config = self.config.get('file_filters', {})

        # 文件大小过滤
        size_config = file_config.get('size', {})
        if size_config.get('enabled', False):
            file_size = self.pdf_path.stat().st_size
            min_size = size_config.get('min_size', 0)
            max_size = size_config.get('max_size', float('inf'))

            if file_size < min_size:
                return (False, f"文件过小: {file_size} bytes < {min_size} bytes")
            if file_size > max_size:
                return (False, f"文件过大: {file_size} bytes > {max_size} bytes")

        # 文件名长度过滤
        length_config = file_config.get('filename_length', {})
        if length_config.get('enabled', False):
            filename_len = len(self.filename)
            min_length = length_config.get('min_length', 0)
            max_length = length_config.get('max_length', 1000)

            if filename_len < min_length:
                return (False, f"文件名过短: {filename_len} < {min_length}")
            if filename_len > max_length:
                return (False, f"文件名过长: {filename_len} > {max_length}")

        return None

    def _check_special_rules(self) -> Optional[Tuple[bool, str]]:
        """检查特殊规则"""
        special_config = self.config.get('special_rules', {})
        if not special_config.get('enabled', True):
            return None

        filename_lower = self.filename.lower()
        force_process = special_config.get('force_process_patterns') or []
        force_skip = special_config.get('force_skip_patterns') or []

        # 强制处理检查
        for pattern in force_process:
            if pattern.lower() in filename_lower:
                return (True, f"特殊规则-强制处理: {pattern}")

        # 强制跳过检查
        for pattern in force_skip:
            if pattern.lower() in filename_lower:
                return (False, f"特殊规则-强制跳过: {pattern}")

        return None

    def should_process(self) -> Tuple[bool, str]:
        """
        判断文档是否应该处理

        Returns:
            (should_process, reason) - (是否处理, 原因说明)
        """
        # 检查缓存
        cached = self._get_cached_decision()
        if cached:
            return cached

        filter_mode = self.config.get('filter_mode', {}).get('mode', 'hybrid')

        # 按优先级检查各种过滤规则
        checks = [
            self._check_special_rules,      # 特殊规则（最高优先级）
            self._check_document_type_filter,  # 文档类型过滤
            self._check_keyword_filter,     # 关键词过滤
            self._check_pattern_filter,     # 模式过滤
            self._check_file_filters,       # 文件属性过滤
        ]

        decisions = []
        for check in checks:
            result = check()
            if result:
                decisions.append(result)

        # 根据过滤模式决定最终结果
        if filter_mode == 'whitelist':
            # 白名单模式：必须有匹配的规则才处理
            should_process = any(d[0] for d in decisions)
            reason = "白名单模式: " + ("匹配白名单规则" if should_process else "未匹配任何白名单规则")
        elif filter_mode == 'blacklist':
            # 黑名单模式：只要匹配黑名单就跳过
            should_process = not any(not d[0] for d in decisions)
            reason = "黑名单模式: " + ("未匹配黑名单规则" if should_process else "匹配黑名单规则")
        else:  # hybrid 模式
            # 混合模式：白名单优先，然后应用黑名单
            process_decisions = [d for d in decisions if d[0]]
            skip_decisions = [d for d in decisions if not d[0]]

            if process_decisions:
                # 有匹配的处理规则
                should_process = True
                reason = process_decisions[0][1]
            elif skip_decisions:
                # 有匹配的跳过规则
                should_process = False
                reason = skip_decisions[0][1]
            else:
                # 没有匹配的规则，使用默认策略
                doc_config = self.config.get('document_types', {})
                default_action = doc_config.get('default_action', 'process')
                should_process = (default_action == 'process')
                reason = f"混合模式: 未匹配规则，使用默认策略 ({default_action})"

        # 缓存决策结果
        self._cache_decision((should_process, reason))

        # 记录日志
        if self.config.get('logging', {}).get('log_decisions', True):
            status = "✅ 处理" if should_process else "⏭️ 跳过"
            print(f"[过滤] {status} - {self.filename} - {reason}")

        return (should_process, reason)

    def print_decision(self) -> bool:
        """打印过滤决策"""
        should_process, reason = self.should_process()

        print("=" * 80)
        print("📄 可配置文档过滤检查")
        print("=" * 80)
        print(f"文件: {self.filename}")
        print(f"路径: {self.pdf_path}")
        print(f"文档类型: {self._parse_document_type()}")
        print(f"过滤模式: {self.config.get('filter_mode', {}).get('mode', 'hybrid')}")
        print("-" * 80)
        print(f"决策: {'✅ 应该处理' if should_process else '⏭️ 跳过处理'}")
        print(f"原因: {reason}")
        print("=" * 80)

        return should_process


def main():
    """主函数 - 命令行接口"""
    if len(sys.argv) < 2:
        print("用法: python document_filter_configurable.py <pdf_path> [config_path]")
        print("返回码: 0=应该处理, 1=应该跳过")
        sys.exit(2)

    pdf_path = sys.argv[1]
    config_path = sys.argv[2] if len(sys.argv) > 2 else None

    if not Path(pdf_path).exists():
        print(f"❌ 文件不存在: {pdf_path}")
        sys.exit(2)

    filter_obj = ConfigurableDocumentFilter(pdf_path, config_path)
    should_process = filter_obj.print_decision()

    # 返回码：0=应该处理，1=应该跳过
    sys.exit(0 if should_process else 1)


if __name__ == '__main__':
    main()
