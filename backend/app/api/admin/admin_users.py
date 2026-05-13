"""
管理员-用户管理
"""



from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db

from .shared import *

router = APIRouter(prefix="", tags=["管理员-用户管理"])

# ============================
# 管理员-用户管理
# ============================
# ===== USERS (1 endpoint) =====
# ============================

@router.get("/users")
async def list_users(
    role: str | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin)
):
    """List Users"""
    sql = "SELECT id, username AS name, id_card_encrypted AS id_card, phone, role, avatar, is_active FROM users WHERE 1=1"
    params = {}
    if role:
        sql += " AND role = :role"
        params["role"] = role
    sql += " ORDER BY id DESC"

    result = await db.execute(sql_text(sql), params)
    return [dict(r._mapping) for r in result.fetchall()]


# ============================
