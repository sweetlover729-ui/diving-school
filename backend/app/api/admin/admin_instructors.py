"""
管理员-教官管理
"""


import bcrypt
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.class_system import Class, ClassMember

from .shared import *

router = APIRouter(prefix="", tags=["管理员-教官管理"])

# ============================
# 管理员-教官管理
# ============================
# ===== INSTRUCTORS (3 endpoints) =====
# ============================

@router.get("/instructors")
async def list_instructors(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin)
):
    """List Instructors"""
    result = await db.execute(
        sql_text("""
            SELECT u.id, u.username AS name, u.instructor_code, u.id_card_encrypted AS id_card, u.phone, c.name AS company_name, u.company_id,
                   u.province, u.city
            FROM users u
            LEFT JOIN companies c ON u.company_id = c.id
            WHERE u.role = 'instructor' AND (u.is_active = true)
            ORDER BY u.id DESC
        """)
    )
    return [dict(r._mapping) for r in result.fetchall()]


@router.post("/instructors")
async def create_instructor(
    req: InstructorCreateRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin)
):
    """Create Instructor"""
    pw = req.password or (req.id_card or "000000")[-6:]
    pw_hash = bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()

    instructor = User(
        name=req.name, instructor_code=req.instructor_code or "",
        id_card=req.id_card or "", phone=req.phone,
        role=UserRole.INSTRUCTOR, password_hash=pw_hash,
        company_id=req.company_id, province=req.province, city=req.city
    )
    db.add(instructor)
    await db.commit()
    await db.refresh(instructor)

    return {
        "id": instructor.id, "name": instructor.name, "phone": instructor.phone,
        "password": pw  # 仅创建时返回
    }


@router.put("/instructors/{instructor_id}")
async def update_instructor(
    instructor_id: int,
    req: InstructorCreateRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin)
):
    """Update Instructor"""
    instructor = await db.get(User, instructor_id)
    if not instructor:
        raise HTTPException(status_code=404, detail="教练不存在")
    for key in ["name", "instructor_code", "id_card", "phone", "company_id", "province", "city"]:
        val = getattr(req, key, None)
        if val is not None:
            setattr(instructor, key, val)
    if req.password:
        instructor.password_hash = bcrypt.hashpw(req.password.encode(), bcrypt.gensalt()).decode()
    await db.commit()
    return {"success": True}


@router.delete("/instructors/{instructor_id}")
async def delete_instructor(
    instructor_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin)
):
    """Delete Instructor (硬删除)"""
    instructor = await db.get(User, instructor_id)
    if not instructor:
        raise HTTPException(status_code=404, detail="教练不存在")
    try:
        # 先清除关联表中的外键引用
        await db.execute(update(Class).where(Class.instructor_id == instructor_id).values(instructor_id=None))
        await db.execute(update(ClassMember).where(ClassMember.user_id == instructor_id).values(user_id=None))
        await db.delete(instructor)
        await db.commit()
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=f"删除失败：{str(e)}")
    return {"success": True}


@router.post("/instructors/{instructor_id}/reset-password")
async def reset_instructor_password(
    instructor_id: int,
    req: InstructorPasswordResetRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin)
):
    """Reset Instructor Password"""
    instructor = await db.get(User, instructor_id)
    if not instructor:
        raise HTTPException(status_code=404, detail="教练不存在")
    instructor.password_hash = bcrypt.hashpw(req.password.encode(), bcrypt.gensalt()).decode()
    await db.commit()
    return {"success": True, "message": "密码已重置"}


# ============================

