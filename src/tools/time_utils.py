"""时间工具集 - 为Agent提供时间感知能力"""
import logging
from datetime import datetime

import pytz
from langchain_core.tools import tool

logger = logging.getLogger(__name__)

# 香港时区
HONGKONG_TZ = pytz.timezone('Asia/Hong_Kong')

# 港股交易时间
MARKET_HOURS = {
    'morning_start': (9, 30),  # 上午9:30开盘
    'morning_end': (12, 0),  # 中午12:00休市
    'afternoon_start': (13, 0),  # 下午1:00开盘
    'afternoon_end': (16, 0),  # 下午4:00收盘
}


@tool
def get_current_time() -> str:
    """获取当前时间（香港时间）
    
    【适用场景】
    - 需要确认当前日期和时间
    - 分析"最近""今天""本周"等相对时间概念
    - 判断公告发布的时效性
    
    【返回】当前香港时间的自然语言描述，如"2025年10月25日 下午3:15 (星期六)"
    """
    try:
        # 获取香港时间
        now_hk = datetime.now(HONGKONG_TZ)

        # 格式化为自然语言
        weekdays = ['星期一', '星期二', '星期三', '星期四', '星期五', '星期六', '星期日']
        weekday = weekdays[now_hk.weekday()]

        # 根据时间选择上午/下午/晚上
        hour = now_hk.hour
        if 5 <= hour < 12:
            time_period = "上午"
        elif 12 <= hour < 14:
            time_period = "中午"
        elif 14 <= hour < 18:
            time_period = "下午"
        elif 18 <= hour < 22:
            time_period = "晚上"
        else:
            time_period = "深夜"

        # 格式化时间
        time_str = now_hk.strftime("%Y年%m月%d日 %H:%M")

        return f"{time_str} ({weekday}) {time_period}"

    except Exception as e:
        logger.error(f"获取当前时间失败: {e}")
        return "抱歉，无法获取当前时间"


@tool
def get_market_time() -> str:
    """获取港股市场当前状态和时间
    
    【适用场景】
    - 判断当前是否为交易时间
    - 解释股价是否会实时变动
    - 提供市场开盘/休市状态
    
    【交易时间】上午9:30-12:00，下午1:00-4:00，周末休市
    【返回】港股市场状态描述，如"目前是交易时间，上午10:15，市场开盘"
    """
    try:
        now_hk = datetime.now(HONGKONG_TZ)
        current_time = (now_hk.hour, now_hk.minute)
        current_str = now_hk.strftime("%H:%M")

        # 判断市场状态
        weekday = now_hk.weekday()  # 0=周一, 6=周日

        # 周末不开市
        if weekday >= 5:  # 周六、周日
            return f"目前是{current_str}，周末港股市场休市"

        # 检查是否在交易时间内
        is_morning = (MARKET_HOURS['morning_start'] <= current_time < MARKET_HOURS['morning_end'])
        is_afternoon = (MARKET_HOURS['afternoon_start'] <= current_time < MARKET_HOURS['afternoon_end'])

        if is_morning:
            return f"目前是{current_str}，上午交易时间，市场开盘中"
        elif is_afternoon:
            return f"目前是{current_str}，下午交易时间，市场开盘中"
        elif current_time >= MARKET_HOURS['afternoon_end']:
            return f"目前是{current_str}，今日交易已结束"
        elif current_time >= MARKET_HOURS['morning_end']:
            return f"目前是{current_str}，午休时间，市场暂时休市"
        else:
            return f"目前是{current_str}，市场尚未开盘"

    except Exception as e:
        logger.error(f"获取市场时间失败: {e}")
        return "抱歉，无法获取市场时间信息"


@tool
def calculate_time_diff(date_str: str, format_type: str = "natural") -> str:
    """计算给定日期与当前时间的差值
    
    【适用场景】
    - 计算公告发布距今多长时间
    - 判断数据是否过时
    - 分析事件的时间跨度
    
    【支持格式】YYYY-MM-DD, YYYY-MM-DD HH:MM等
    【返回】时间差描述，如"该日期是3天前"、"该日期在5天后"

    Args:
        date_str: 日期字符串，格式如"2025-10-25", "2025-10-25 14:30"等
        format_type: 输出格式，"natural"(自然语言)或"days"(天数)

    Returns:
        str: 时间差描述
    """
    try:
        # 尝试解析日期
        date_formats = [
            "%Y-%m-%d",
            "%Y-%m-%d %H:%M",
            "%Y-%m-%d %H:%M:%S",
            "%Y/%m/%d",
            "%Y/%m/%d %H:%M",
        ]

        parsed_date = None
        for fmt in date_formats:
            try:
                # 先假设是本地时间，然后转换为香港时间
                naive_date = datetime.strptime(date_str, fmt)
                parsed_date = HONGKONG_TZ.localize(naive_date)
                break
            except ValueError:
                continue

        if not parsed_date:
            return "无法解析日期格式，请使用YYYY-MM-DD或YYYY-MM-DD HH:MM格式"

        # 计算时间差
        now_hk = datetime.now(HONGKONG_TZ)
        diff = now_hk - parsed_date

        if diff.total_seconds() < 0:
            # 未来时间
            future_diff = parsed_date - now_hk
            days = future_diff.days
            hours = future_diff.seconds // 3600

            if days > 0:
                return f"该日期在{days}天后"
            elif hours > 0:
                return f"该日期在{hours}小时后"
            else:
                return "该日期即将到达"
        else:
            # 过去时间
            days = diff.days
            hours = diff.seconds // 3600

            if format_type == "days":
                return f"距今{days}天"
            else:  # natural
                if days > 0:
                    if days == 1:
                        return "该日期是昨天"
                    elif days < 7:
                        return f"该日期是{days}天前"
                    elif days < 30:
                        weeks = days // 7
                        return f"该日期是{weeks}周前"
                    elif days < 365:
                        months = days // 30
                        return f"该日期是{months}个月前"
                    else:
                        years = days // 365
                        return f"该日期是{years}年前"
                elif hours > 0:
                    return f"该日期是{hours}小时前"
                else:
                    return "该日期是刚刚"

    except Exception as e:
        logger.error(f"计算时间差失败: {e}")
        return "抱歉，无法计算时间差"


@tool
def format_time_period(start_date: str, end_date: str = None) -> str:
    """格式化时间段描述
    
    【适用场景】
    - 描述事件的持续时间
    - 计算供股、配售等的时间跨度
    - 格式化数据查询的时间范围
    
    【返回】如"从2024年1月1日到2024年12月31日，持续12个月"

    Args:
        start_date: 开始日期（YYYY-MM-DD）
        end_date: 结束日期（可选，默认为当前时间）

    Returns:
        str: 时间段的自然语言描述
    """
    try:
        # 解析开始日期
        date_formats = ["%Y-%m-%d", "%Y-%m-%d %H:%M", "%Y/%m/%d", "%Y/%m/%d %H:%M"]

        parsed_start = None
        for fmt in date_formats:
            try:
                naive_date = datetime.strptime(start_date, fmt)
                parsed_start = HONGKONG_TZ.localize(naive_date)
                break
            except ValueError:
                continue

        if not parsed_start:
            return "无法解析开始日期格式"

        # 解析结束日期
        if end_date:
            parsed_end = None
            for fmt in date_formats:
                try:
                    naive_date = datetime.strptime(end_date, fmt)
                    parsed_end = HONGKONG_TZ.localize(naive_date)
                    break
                except ValueError:
                    continue

            if not parsed_end:
                return "无法解析结束日期格式"
        else:
            parsed_end = datetime.now(HONGKONG_TZ)

        # 计算持续时间
        duration = parsed_end - parsed_start

        if duration.total_seconds() < 0:
            return "结束日期不能早于开始日期"

        days = duration.days
        hours = duration.seconds // 3600

        # 格式化输出
        if days > 0:
            if days == 1:
                duration_str = "1天"
            elif days < 7:
                duration_str = f"{days}天"
            elif days < 30:
                weeks = days // 7
                duration_str = f"{weeks}周"
            elif days < 365:
                months = days // 30
                duration_str = f"{months}个月"
            else:
                years = days // 365
                duration_str = f"{years}年"
        else:
            duration_str = f"{hours}小时"

        start_str = parsed_start.strftime("%Y年%m月%d日")
        end_str = parsed_end.strftime("%Y年%m月%d日")

        if end_date:
            return f"从{start_str}到{end_str}，持续{duration_str}"
        else:
            return f"从{start_str}至今，持续{duration_str}"

    except Exception as e:
        logger.error(f"格式化时间段失败: {e}")
        return "抱歉，无法格式化时间段"


@tool
def get_date_info(date_str: str = None) -> str:
    """获取指定日期或当前日期的详细信息
    
    【适用场景】
    - 判断某日期是否为交易日
    - 检查是否为周末或节假日
    - 获取日期的详细属性（星期几、是否休市等）
    
    【返回】如"2024年1月15日 星期一，港股交易日"
    【包含】星期、是否为周末/节假日、是否为港股交易日

    Args:
        date_str: 日期字符串（YYYY-MM-DD，可选），不提供则返回当前日期信息

    Returns:
        str: 日期详细信息，包括星期、节假日、交易日判断等
    """
    try:
        if date_str:
            # 解析指定日期
            date_formats = ["%Y-%m-%d", "%Y/%m/%d"]
            parsed_date = None

            for fmt in date_formats:
                try:
                    naive_date = datetime.strptime(date_str, fmt)
                    parsed_date = HONGKONG_TZ.localize(naive_date)
                    break
                except ValueError:
                    continue

            if not parsed_date:
                return "无法解析日期格式，请使用YYYY-MM-DD格式"
        else:
            parsed_date = datetime.now(HONGKONG_TZ)

        # 获取日期信息
        weekdays = ['星期一', '星期二', '星期三', '星期四', '星期五', '星期六', '星期日']
        weekday = weekdays[parsed_date.weekday()]

        date_str = parsed_date.strftime("%Y年%m月%d日")

        # 判断是否为交易日
        is_weekend = parsed_date.weekday() >= 5

        # 简单的节假日判断（这里可以扩展更复杂的节假日逻辑）
        is_holiday = False
        month, day = parsed_date.month, parsed_date.day

        # 香港主要节假日（简化版）
        holidays = [
            (1, 1),  # 元旦
            (2, 10),  # 春节（示例，实际按农历计算）
            (2, 11),  # 春节
            (2, 12),  # 春节
            (4, 4),  # 清明节
            (5, 1),  # 劳动节
            (7, 1),  # 香港回归纪念日
            (10, 1),  # 国庆节
            (12, 25),  # 圣诞节
            (12, 26),  # 节礼日
        ]

        if (month, day) in holidays:
            is_holiday = True

        # 构建返回信息
        info_parts = [f"{date_str} {weekday}"]

        if is_weekend:
            info_parts.append("周末")
        if is_holiday:
            info_parts.append("香港公众假期")

        # 交易日判断
        if not is_weekend and not is_holiday:
            info_parts.append("港股交易日")
        else:
            info_parts.append("港股休市日")

        return "，".join(info_parts)

    except Exception as e:
        logger.error(f"获取日期信息失败: {e}")
        return "抱歉，无法获取日期信息"
