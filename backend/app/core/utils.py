"""
工具函数模块
"""
import hashlib
import secrets
from datetime import datetime, timedelta, timezone


def generate_random_token(length: int = 32) -> str:
    """生成随机令牌"""
    return secrets.token_urlsafe(length)


def hash_string(text: str) -> str:
    """字符串哈希"""
    return hashlib.sha256(text.encode()).hexdigest()


def format_datetime(dt: datetime | None = None) -> str:
    """格式化日期时间"""
    if dt is None:
        dt = datetime.now(timezone.utc).replace(tzinfo=None)
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def format_date(dt: datetime | None = None) -> str:
    """格式化日期"""
    if dt is None:
        dt = datetime.now(timezone.utc).replace(tzinfo=None)
    return dt.strftime("%Y-%m-%d")


def parse_datetime(date_str: str) -> datetime:
    """解析日期时间字符串"""
    return datetime.fromisoformat(date_str)


def get_week_range(date: datetime | None = None) -> tuple[datetime, datetime]:
    """获取本周日期范围"""
    if date is None:
        date = datetime.now(timezone.utc).replace(tzinfo=None)

    start = date - timedelta(days=date.weekday())
    end = start + timedelta(days=6)

    return start, end


def calculate_age(birth_date: datetime) -> int:
    """计算年龄"""
    today = datetime.today()
    return today.year - birth_date.year - (
        (today.month, today.day) < (birth_date.month, birth_date.day)
    )


def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """截断文本"""
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix


def mask_phone(phone: str) -> str:
    """手机号脱敏"""
    if len(phone) != 11:
        return phone
    return f"{phone[:3]}****{phone[-4:]}"


def mask_id_card(id_card: str) -> str:
    """身份证号脱敏"""
    if len(id_card) < 8:
        return id_card
    return f"{id_card[:4]}**********{id_card[-4:]}"
