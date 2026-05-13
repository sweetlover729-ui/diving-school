"""
数据验证器
"""
import re
from typing import Optional


def validate_phone(phone: str) -> bool:
    """验证手机号"""
    pattern = r'^1[3-9]\d{9}$'
    return bool(re.match(pattern, phone))


def validate_email(email: str) -> bool:
    """验证邮箱"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def validate_password(password: str) -> tuple[bool, Optional[str]]:
    """
    验证密码强度
    返回: (是否有效, 错误信息)
    """
    if len(password) < 6:
        return False, "密码长度不能少于6位"
    if len(password) > 20:
        return False, "密码长度不能超过20位"
    return True, None


def validate_username(username: str) -> tuple[bool, Optional[str]]:
    """
    验证用户名
    """
    if len(username) < 2:
        return False, "用户名至少2个字符"
    if len(username) > 20:
        return False, "用户名不能超过20个字符"
    if not re.match(r'^[a-zA-Z0-9_\u4e00-\u9fa5]+$', username):
        return False, "用户名只能包含字母、数字、下划线和中文"
    return True, None


def validate_id_card(id_card: str) -> bool:
    """验证身份证号（简单验证）"""
    if len(id_card) not in [15, 18]:
        return False
    pattern = r'^\d{15}$|^\d{17}[\dXx]$'
    return bool(re.match(pattern, id_card))


def sanitize_filename(filename: str) -> str:
    """清理文件名"""
    # 移除非法字符
    filename = re.sub(r'[<>:"/\\|?*]', '', filename)
    # 限制长度
    if len(filename) > 100:
        name, ext = filename.rsplit('.', 1) if '.' in filename else (filename, '')
        filename = name[:100-len(ext)-1] + '.' + ext if ext else name[:100]
    return filename
