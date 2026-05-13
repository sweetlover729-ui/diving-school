"""
LLM Configuration Manager
- Fernet加密存储API Key（任何角色查不到明文）
- 全局开关 + 课程/教材级开关
- 模型白名单校验（禁止pro/plus/premium）
"""
import logging
import os
from typing import Any

from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

_ENCRYPTION_KEY_FILE = "/var/www/diving/backend/.encryption_key"
BLOCKED_PATTERNS = ["pro", "plus", "premium", "enterprise", "ultra", "turbo"]

# ── Encryption ──

def _get_fernet() -> Fernet:
    key_path = os.path.expanduser(_ENCRYPTION_KEY_FILE)
    if os.path.exists(key_path):
        with open(key_path, "rb") as f:
            key = f.read()
    else:
        key = Fernet.generate_key()
        os.makedirs(os.path.dirname(key_path), exist_ok=True)
        with open(key_path, "wb") as f:
            f.write(key)
        os.chmod(key_path, 0o600)
        logger.info(f"Generated new encryption key at {key_path}")
    return Fernet(key)

def encrypt_value(plain: str) -> str:
    if not plain:
        return ""
    return _get_fernet().encrypt(plain.encode()).decode()

def decrypt_value(encrypted: str) -> str:
    if not encrypted:
        return ""
    try:
        return _get_fernet().decrypt(encrypted.encode()).decode()
    except InvalidToken:
        logger.error("Failed to decrypt value - encryption key mismatch or corruption")
        return ""

def mask_api_key(key: str) -> str:
    """sk-****b30"""
    if not key or len(key) < 8:
        return "****"
    return key[:3] + "****" + key[-4:]

# ── Validation ──

def validate_model(name: str) -> tuple:
    """返回 (ok, message)"""
    if not name or not name.strip():
        return False, "模型名称不能为空"
    lower = name.lower()
    for p in BLOCKED_PATTERNS:
        if p in lower:
            return False, f"禁止使用包含 '{p}' 的模型。请使用 flash 或标准模型（如 deepseek-chat）"
    return True, ""

# ── DB operations (raw SQL, no ORM model dependency) ──

async def db_get_setting(db: AsyncSession, key: str) -> str | None:
    r = await db.execute(
        text("SELECT value, is_encrypted FROM system_settings WHERE key = :k"), {"k": key}
    )
    row = r.fetchone()
    if not row:
        return None
    if row[1]:  # is_encrypted
        return decrypt_value(row[0])
    return row[0]

async def db_set_setting(db: AsyncSession, key: str, value: str, encrypted: bool = False):
    stored = (encrypt_value(value) if encrypted else value)
    await db.execute(
        text("""
            INSERT INTO system_settings (key, value, is_encrypted)
            VALUES (:k, :v, :e)
            ON CONFLICT (key) DO UPDATE SET value = :v2, is_encrypted = :e2, updated_at = NOW()
        """),
        {"k": key, "v": stored, "e": encrypted, "v2": stored, "e2": encrypted}
    )
    await db.commit()

async def db_get_all_config(db: AsyncSession) -> dict[str, Any]:
    """返回所有配置（API Key 已脱敏）"""
    r = await db.execute(text("SELECT key, value, is_encrypted, description FROM system_settings ORDER BY key"))
    result = {}
    for row in r.fetchall():
        k, v, enc, desc = row
        if k == "llm_api_key":
            try:
                plain = decrypt_value(v) if v else ""
                result[k] = mask_api_key(plain)
                result["_has_key"] = bool(plain)
            except Exception:
                result[k] = "**** （解密失败）"
                result["_has_key"] = False
        else:
            result[k] = v
        result[f"{k}_desc"] = desc
    return result

async def db_get_llm_runtime_config(db: AsyncSession) -> dict[str, str]:
    """运行时配置（含解密后的完整 key）"""
    keys = ["llm_enabled", "llm_api_key", "llm_base_url",
            "llm_model", "llm_max_tokens", "llm_temperature"]
    cfg = {}
    for k in keys:
        cfg[k] = (await db_get_setting(db, k)) or ""
    return cfg

# ── Business Logic ──

async def check_llm_allowed(db: AsyncSession, course_id: int = 0, textbook_id: int = 0) -> tuple:
    """
    检查 LLM 是否可用。
    返回 (allowed: bool, reason: str)
    逻辑：全局开 AND (课程开 OR 教材开)
    """
    global_enabled = (await db_get_setting(db, "llm_enabled")) == "true"
    if not global_enabled:
        return False, "全局LLM功能已关闭"

    course_ok = False
    textbook_ok = False

    if course_id:
        r = await db.execute(
            text("SELECT llm_enabled FROM courses WHERE id = :cid"), {"cid": course_id}
        )
        row = r.fetchone()
        course_ok = bool(row and row[0])

    if textbook_id:
        r = await db.execute(
            text("SELECT llm_enabled FROM textbooks WHERE id = :tid"), {"tid": textbook_id}
        )
        row = r.fetchone()
        textbook_ok = bool(row and row[0])

    if course_ok or textbook_ok:
        return True, ""

    return False, "当前课程/教材未开通LLM功能"

async def toggle_course_llm(db: AsyncSession, course_id: int, enabled: bool):
    await db.execute(
        text("UPDATE courses SET llm_enabled = :e WHERE id = :cid"),
        {"e": enabled, "cid": course_id}
    )
    await db.commit()

async def toggle_textbook_llm(db: AsyncSession, textbook_id: int, enabled: bool):
    await db.execute(
        text("UPDATE textbooks SET llm_enabled = :e WHERE id = :tid"),
        {"e": enabled, "tid": textbook_id}
    )
    await db.commit()

async def get_courses_llm_status(db: AsyncSession) -> list:
    r = await db.execute(
        text("SELECT id, name AS title, llm_enabled FROM courses ORDER BY id")
    )
    return [{"id": row[0], "title": row[1], "llm_enabled": row[2]} for row in r.fetchall()]

async def get_textbooks_llm_status(db: AsyncSession, course_id: int = 0) -> list:
    if course_id:
        r = await db.execute(
            text("SELECT id, name AS title, llm_enabled FROM textbooks WHERE course_id = :cid ORDER BY id"),
            {"cid": course_id}
        )
    else:
        r = await db.execute(
            text("SELECT id, name AS title, llm_enabled FROM textbooks ORDER BY id")
        )
    return [{"id": row[0], "title": row[1], "llm_enabled": row[2]} for row in r.fetchall()]
