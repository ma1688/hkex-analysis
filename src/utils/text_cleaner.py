"""文本清理工具 - 处理数据库中的特殊字符和编码问题"""
import logging
from functools import wraps

logger = logging.getLogger(__name__)


def clean_text(text: str) -> str:
    """
    清理文本中的无效字符，特别是surrogate字符
    
    Args:
        text: 原始文本
        
    Returns:
        清理后的文本
    """
    if not isinstance(text, str):
        return text

    try:
        # 尝试编码为UTF-8，如果失败则使用替换策略
        text.encode('utf-8')
        return text
    except UnicodeEncodeError:
        # 使用'surrogatepass'错误处理策略来移除surrogate字符
        try:
            # 先用surrogateescape编码，再用ignore解码
            cleaned = text.encode('utf-8', errors='ignore').decode('utf-8', errors='ignore')
            logger.warning(f"清理了包含无效字符的文本，原长度: {len(text)}, 清理后: {len(cleaned)}")
            return cleaned
        except Exception as e:
            logger.error(f"文本清理失败: {e}")
            # 最后的fallback：移除所有非ASCII字符
            return ''.join(c for c in text if ord(c) < 128)


def clean_dict(data: dict) -> dict:
    """
    递归清理字典中所有字符串值
    
    Args:
        data: 原始字典
        
    Returns:
        清理后的字典
    """
    if not isinstance(data, dict):
        return data

    cleaned = {}
    for key, value in data.items():
        if isinstance(value, str):
            cleaned[key] = clean_text(value)
        elif isinstance(value, dict):
            cleaned[key] = clean_dict(value)
        elif isinstance(value, list):
            cleaned[key] = [
                clean_text(item) if isinstance(item, str)
                else clean_dict(item) if isinstance(item, dict)
                else item
                for item in value
            ]
        else:
            cleaned[key] = value

    return cleaned


def clean_list(data: list) -> list:
    """
    递归清理列表中所有字符串值
    
    Args:
        data: 原始列表
        
    Returns:
        清理后的列表
    """
    if not isinstance(data, list):
        return data

    return [
        clean_text(item) if isinstance(item, str)
        else clean_dict(item) if isinstance(item, dict)
        else clean_list(item) if isinstance(item, list)
        else item
        for item in data
    ]


def clean_any(data):
    """
    清理任何类型的数据（字符串、字典、列表或其他）
    
    Args:
        data: 任意类型的数据
        
    Returns:
        清理后的数据
    """
    if isinstance(data, str):
        return clean_text(data)
    elif isinstance(data, dict):
        return clean_dict(data)
    elif isinstance(data, list):
        return clean_list(data)
    else:
        return data


def clean_tool_output(func):
    """
    装饰器：自动清理工具函数的返回值中的无效字符
    
    用法:
        @clean_tool_output
        @tool
        def my_tool(...):
            return some_data
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        result = func(*args, **kwargs)
        return clean_any(result)

    return wrapper
