"""
过滤规则配置管理路由
"""

import os
import yaml
import re
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse
from pathlib import Path
from typing import Dict, Any, List

router = APIRouter(prefix="/filter-config", tags=["filter-config"])

# 配置文件路径
CONFIG_PATH = Path(__file__).parent.parent.parent.parent / "config" / "document_filter.yaml"

def load_config() -> Dict[str, Any]:
    """加载配置文件"""
    if not CONFIG_PATH.exists():
        raise HTTPException(status_code=404, detail="配置文件不存在")

    with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def save_config(config: Dict[str, Any]):
    """保存配置文件"""
    with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
        yaml.dump(config, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

@router.get("/", response_model=Dict[str, Any])
async def get_filter_config():
    """获取过滤规则配置"""
    try:
        config = load_config()
        return {
            "status": "success",
            "config": config
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"加载配置失败: {str(e)}")

@router.put("/", response_model=Dict[str, Any])
async def update_filter_config(config_data: Dict[str, Any]):
    """更新过滤规则配置"""
    try:
        # 验证配置格式
        if not isinstance(config_data, dict):
            raise HTTPException(status_code=400, detail="配置数据格式错误")

        # 基本验证
        if 'filter_mode' not in config_data:
            raise HTTPException(status_code=400, detail="缺少 filter_mode 配置")

        if 'document_types' not in config_data:
            raise HTTPException(status_code=400, detail="缺少 document_types 配置")

        # 保存配置
        save_config(config_data)

        return {
            "status": "success",
            "message": "配置更新成功",
            "config_path": str(CONFIG_PATH)
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"保存配置失败: {str(e)}")

@router.get("/document-types", response_model=Dict[str, Any])
async def get_supported_document_types():
    """获取支持的文档类型列表"""
    document_types = {
        "rights": "供股",
        "placing": "配售",
        "ipo": "IPO",
        "consolidation": "合股/拆股",
        "split": "拆股",
        "acquisition": "收购",
        "disposal": "出售",
        "disclosable_transaction": "须予披露交易",
        "connected_transaction": "关连交易",
        "very_substantial_acquisition": "非常重大收购",
        "very_substantial_disposal": "非常重大出售",
        "share_option": "购股权计划",
        "dividend": "股息分派",
        "capital_reduction": "股本缩减",
        "share_repurchase": "股份回购",
        "other": "其他"
    }

    return {
        "status": "success",
        "document_types": document_types
    }

@router.post("/validate", response_model=Dict[str, Any])
async def validate_filter_config(config_data: Dict[str, Any]):
    """验证过滤规则配置"""
    errors = []
    warnings = []

    try:
        # 检查过滤模式
        filter_mode = config_data.get('filter_mode', {})
        mode = filter_mode.get('mode', 'hybrid')
        if mode not in ['whitelist', 'blacklist', 'hybrid']:
            errors.append(f"无效的过滤模式: {mode}，可选值: whitelist, blackhole, hybrid")

        # 检查文档类型配置
        doc_types = config_data.get('document_types', {})
        whitelist = doc_types.get('whitelist', [])
        blacklist = doc_types.get('blacklist', [])

        # 检查是否有重叠
        overlap = set(whitelist) & set(blacklist)
        if overlap:
            warnings.append(f"白名单和黑名单有重叠的类型: {list(overlap)}")

        # 检查文档类型是否有效
        supported_types = {
            "rights", "placing", "ipo", "consolidation", "split", "acquisition", "disposal",
            "disclosable_transaction", "connected_transaction", "very_substantial_acquisition",
            "very_substantial_disposal", "share_option", "dividend", "capital_reduction",
            "share_repurchase", "other"
        }

        invalid_types = set(whitelist + blacklist) - supported_types
        if invalid_types:
            errors.append(f"无效的文档类型: {list(invalid_types)}")

        # 检查正则表达式模式
        pattern_filters = config_data.get('pattern_filters', {})
        blacklist_patterns = pattern_filters.get('blacklist_patterns', [])
        whitelist_patterns = pattern_filters.get('whitelist_patterns', [])

        all_patterns = blacklist_patterns + whitelist_patterns
        for i, pattern in enumerate(all_patterns):
            try:
                re.compile(pattern)
            except re.error as e:
                errors.append(f"无效的正则表达式 (索引 {i}): {pattern} - {str(e)}")

        # 检查默认策略
        default_action = doc_types.get('default_action', 'process')
        if default_action not in ['process', 'skip']:
            errors.append(f"无效的默认动作: {default_action}，可选值: process, skip")

        return {
            "status": "success",
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"验证配置失败: {str(e)}")

@router.get("/templates", response_model=Dict[str, Any])
async def get_config_templates():
    """获取配置模板"""
    templates = {
        "strict": {
            "name": "严格模式",
            "description": "只处理明确的业务相关文档，其他全部跳过",
            "config": {
                "filter_mode": {"mode": "hybrid"},
                "document_types": {
                    "whitelist": [
                        "rights", "placing", "ipo", "consolidation", "split",
                        "acquisition", "disposal", "disclosable_transaction",
                        "connected_transaction", "very_substantial_acquisition",
                        "very_substantial_disposal"
                    ],
                    "blacklist": [],
                    "default_action": "skip"
                },
                "keyword_filters": {
                    "blacklist": [
                        "月报表", "季报", "半年报", "年报", "ESG",
                        "股东大会通告", "股东周年大会", "通告", "通知",
                        "委任代表表格", "展示文件", "送呈", "更改",
                        "董事会会议", "董事名单", "盈利警告"
                    ],
                    "whitelist": [],
                    "enabled": True
                },
                "pattern_filters": {
                    "blacklist_patterns": [
                        r'^\d{4}-\d{2}-\d{2}_\d{5}_.*_月报表',
                        r'^\d{4}-\d{2}-\d{2}_\d{5}_.*_委任代表表格',
                        r'^\d{4}-\d{2}-\d{2}_\d{5}_.*_展示文件'
                    ],
                    "whitelist_patterns": [],
                    "enabled": True
                },
                "special_rules": {
                    "force_process_patterns": ["非常重大收购"],
                    "force_skip_patterns": [],
                    "enabled": True
                }
            }
        },
        "inclusive": {
            "name": "宽松模式",
            "description": "处理所有非明确跳过类型的文档",
            "config": {
                "filter_mode": {"mode": "hybrid"},
                "document_types": {
                    "whitelist": [],
                    "blacklist": [],
                    "default_action": "process"
                },
                "keyword_filters": {
                    "blacklist": [
                        "月报表", "季报", "半年报", "年报", "通告", "通知"
                    ],
                    "whitelist": [],
                    "enabled": True
                },
                "pattern_filters": {
                    "blacklist_patterns": [
                        r'^\d{4}-\d{2}-\d{2}_\d{5}_.*_月报表'
                    ],
                    "whitelist_patterns": [],
                    "enabled": True
                },
                "special_rules": {
                    "force_process_patterns": [],
                    "force_skip_patterns": [],
                    "enabled": True
                }
            }
        }
    }

    return {
        "status": "success",
        "templates": templates
    }

@router.post("/apply-template", response_model=Dict[str, Any])
async def apply_template(template_name: str):
    """应用配置模板"""
    try:
        templates_response = await get_config_templates()
        templates = templates_response["templates"]

        if template_name not in templates:
            raise HTTPException(status_code=404, detail=f"模板不存在: {template_name}")

        template_config = templates[template_name]["config"]
        save_config(template_config)

        return {
            "status": "success",
            "message": f"已应用模板: {templates[template_name]['name']}",
            "template_name": template_name
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"应用模板失败: {str(e)}")

@router.post("/reset", response_model=Dict[str, Any])
async def reset_to_default():
    """重置为默认配置"""
    try:
        default_config = {
            'filter_mode': {'mode': 'hybrid'},
            'document_types': {
                'whitelist': [
                    'rights', 'placing', 'ipo', 'consolidation', 'split',
                    'acquisition', 'disposal', 'disclosable_transaction',
                    'connected_transaction', 'very_substantial_acquisition',
                    'very_substantial_disposal', 'share_option', 'dividend',
                    'capital_reduction', 'share_repurchase'
                ],
                'blacklist': [],
                'default_action': 'skip'
            },
            'keyword_filters': {
                'blacklist': [
                    '月报表', '月報表', '季报', '季報', '半年报', '半年報',
                    '年报', '年報', '环境、社会及管治', '环境社会管治', 'ESG',
                    '股东大会通告', '股東大會通告', '股东周年大会', '股東週年大會',
                    '股东特别大会', '股東特別大會', '通告', '通知',
                    '委任代表表格', '代表委任表格', '展示文件', '展示档案',
                    '送呈', '送交', '更改', '更换', '更換', '变更', '變更',
                    '董事会会议', '董事會會議', '董事名单', '董事名單',
                    '业务发展最新情况', '業務發展最新情況',
                    '月份之股份发行人的证券变动月報表', '證券變動月報表',
                    '盈利警告', '盈警', '暂停办理过户登记手续', '暫停辦理過戶'
                ],
                'whitelist': [
                    '供股', '配售', 'IPO', '招股', '上市', '合股', '股本整合',
                    '收购', '收購', '出售', '處置', '须予披露交易', '須予披露交易',
                    '关连交易', '關連交易', '非常重大出售', '非常重大收购'
                ],
                'enabled': True
            },
            'pattern_filters': {
                'blacklist_patterns': [
                    r'^\d{4}-\d{2}-\d{2}_\d{5}_.*_月报表',
                    r'^\d{4}-\d{2}-\d{2}_\d{5}_.*_月報表',
                    r'^\d{4}-\d{2}-\d{2}_\d{5}_.*_委任代表表格',
                    r'^\d{4}-\d{2}-\d{2}_\d{5}_.*_展示文件',
                    r'^\d{4}-\d{2}-\d{2}_\d{5}_.*_董事名单',
                    r'^\d{4}-\d{2}-\d{2}_\d{5}_.*_更[换換改變]'
                ],
                'whitelist_patterns': [],
                'enabled': True
            },
            'file_filters': {
                'size': {'enabled': False},
                'date': {'enabled': False},
                'filename_length': {'enabled': False}
            },
            'special_rules': {
                'force_process_patterns': ['非常重大收购', 'very_substantial_acquisition'],
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

        save_config(default_config)

        return {
            "status": "success",
            "message": "已重置为默认配置"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"重置配置失败: {str(e)}")
