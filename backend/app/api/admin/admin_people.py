"""
管理员-学员管理
"""



import bcrypt
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db

from .shared import *

router = APIRouter(prefix="", tags=["管理员-学员管理"])

# ============================
# 管理员-学员管理
# ============================
# ===== PEOPLE (4 endpoints) =====
# ============================

@router.get("/people")
async def list_people(
    role: str | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin)
):
    """List People"""
    sql = """
        SELECT u.id, u.username AS name, u.id_card_encrypted AS id_card, u.phone, u.role, c.name AS company_name, u.company_id,
               u.province, u.city
        FROM users u
        LEFT JOIN companies c ON u.company_id = c.id
        WHERE (u.is_active = true)
    """
    params = {}
    if role:
        sql += " AND u.role = :role"
        params["role"] = role
    sql += " ORDER BY u.id DESC"

    result = await db.execute(sql_text(sql), params)
    return [dict(r._mapping) for r in result.fetchall()]


@router.post("/people")
async def create_person(
    req: PersonCreateRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin)
):
    """Create Person"""
    pw = (req.phone or "000000")[-6:]
    pw_hash = bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()

    person = User(
        name=req.name, role=UserRole(req.role), phone=req.phone,
        id_card=req.id_card or "", company_id=req.company_id,
        province=req.province, city=req.city, password_hash=pw_hash
    )
    db.add(person)
    await db.commit()
    await db.refresh(person)

    return {"id": person.id, "name": person.name, "phone": person.phone, "password": pw}


@router.put("/people/{person_id}")
async def update_person(
    person_id: int,
    req: PersonCreateRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin)
):
    """Update Person"""
    person = await db.get(User, person_id)
    if not person:
        raise HTTPException(status_code=404, detail="人员不存在")
    for key in ["name", "id_card", "phone", "company_id", "province", "city"]:
        val = getattr(req, key, None)
        if val is not None:
            setattr(person, key, val)
    await db.commit()
    return {"success": True}


@router.post("/people/{person_id}/reset-password")
async def reset_person_password(
    person_id: int,
    req: PersonPasswordResetRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin)
):
    """Reset Person Password (管理员)"""
    person = await db.get(User, person_id)
    if not person:
        raise HTTPException(status_code=404, detail="人员不存在")
    if person.role not in [UserRole.STUDENT, UserRole.MANAGER]:
        raise HTTPException(status_code=400, detail="该接口仅用于学员和管理干部")
    person.password_hash = bcrypt.hashpw(req.password.encode(), bcrypt.gensalt()).decode()
    await db.commit()
    return {"success": True, "message": "密码已重置"}


@router.delete("/people/{person_id}")
async def delete_person(
    person_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin)
):
    """Delete Person (硬删除)"""
    person = await db.get(User, person_id)
    if not person:
        raise HTTPException(status_code=404, detail="人员不存在")
    await db.delete(person)
    await db.commit()
    return {"success": True}


# ============================
# 前端兼容别名: /students → /people (filtered to students)
# ============================

@router.get("/students")
async def list_students_alias(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin)
):
    """学员列表（前端别名）"""
    base_sql = """SELECT u.id, u.username AS name, u.id_card_encrypted AS id_card, u.phone, u.role, c.name AS company_name, u.company_id, u.province, u.city FROM users u LEFT JOIN companies c ON u.company_id = c.id WHERE u.role = 'student' AND (u.is_active = true)"""
    count_result = await db.execute(sql_text(f"SELECT COUNT(*) FROM ({base_sql}) sub"))
    total = count_result.scalar()
    sql = base_sql + " ORDER BY u.id DESC"
    sql += f" LIMIT {page_size} OFFSET {(page-1)*page_size}"
    result = await db.execute(sql_text(sql))
    return {"total": total, "page": page, "page_size": page_size, "data": [dict(r._mapping) for r in result.fetchall()]}


@router.get("/students/{student_id}")
async def get_student_detail_alias(
    student_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin)
):
    """学员详情（前端别名）"""
    student = await db.get(User, student_id)
    if not student:
        raise HTTPException(status_code=404, detail="学员不存在")
    return {"id": student.id, "name": student.name, "id_card": student.id_card, "phone": student.phone, "role": student.role.value, "company_id": student.company_id, "province": student.province, "city": student.city, "is_active": student.is_active, "created_at": student.created_at.isoformat() if student.created_at else None}


# ============================

