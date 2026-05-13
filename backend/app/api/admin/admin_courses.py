"""
管理员-课程管理 API
"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.admin.shared import require_admin
from app.core.database import get_db
from app.models.class_system import Category, Course

router = APIRouter(prefix="/courses", tags=["管理员-课程管理"])

class CourseCreate(BaseModel):
    category_id: int = Field(..., gt=0)
    code: str = Field(..., min_length=1, max_length=30)
    name: str = Field(..., min_length=1, max_length=200)
    description: str | None = None
    level: str | None = "beginner"
    duration_days: int | None = None
    sort_order: int | None = 0
    is_active: bool | None = True

class CourseUpdate(BaseModel):
    category_id: int | None = Field(None, gt=0)
    code: str | None = None
    name: str | None = None
    description: str | None = None
    level: str | None = None
    duration_days: int | None = None
    sort_order: int | None = None
    is_active: bool | None = None

class CourseResponse(BaseModel):
    id: int
    category_id: int
    category_name: str | None = None
    code: str
    name: str
    description: str | None
    level: str | None
    duration_days: int | None
    sort_order: int
    is_active: bool
    created_at: str | None
    updated_at: str | None

    class Config:
        from_attributes = True

@router.get("", response_model=list[CourseResponse])
async def list_courses(
    category_id: int | None = Query(None),
    include_inactive: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(require_admin),
):
    stmt = select(Course)
    if category_id:
        stmt = stmt.where(Course.category_id == category_id)
    if not include_inactive:
        stmt = stmt.where(Course.is_active == True)
    stmt = stmt.order_by(Course.sort_order, Course.id)
    result = await db.execute(stmt)
    rows = result.scalars().all()
    out = []
    for r in rows:
        cat_name = None
        if r.category_id:
            cat_result = await db.execute(select(Category).where(Category.id == r.category_id))
            cat = cat_result.scalar()
            if cat:
                cat_name = cat.name
        out.append({
            "id": r.id, "category_id": r.category_id, "category_name": cat_name,
            "code": r.code, "name": r.name, "description": r.description,
            "level": r.level, "duration_days": r.duration_days,
            "sort_order": r.sort_order, "is_active": r.is_active,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "updated_at": r.updated_at.isoformat() if r.updated_at else None,
        })
    return out

@router.post("", response_model=CourseResponse)
async def create_course(
    data: CourseCreate,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(require_admin),
):
    cat_result = await db.execute(select(Category).where(Category.id == data.category_id))
    cat = cat_result.scalar()
    if not cat:
        raise HTTPException(status_code=400, detail="类别不存在")
    course = Course(
        category_id=data.category_id,
        code=data.code,
        name=data.name,
        description=data.description,
        level=data.level or "beginner",
        duration_days=data.duration_days,
        sort_order=data.sort_order or 0,
        is_active=data.is_active if data.is_active is not None else True,
    )
    db.add(course)
    await db.commit()
    await db.refresh(course)
    return {
        "id": course.id, "category_id": course.category_id, "category_name": cat.name,
        "code": course.code, "name": course.name, "description": course.description,
        "level": course.level, "duration_days": course.duration_days,
        "sort_order": course.sort_order, "is_active": course.is_active,
        "created_at": course.created_at.isoformat() if course.created_at else None,
        "updated_at": course.updated_at.isoformat() if course.updated_at else None,
    }

@router.get("/{course_id}", response_model=CourseResponse)
async def get_course(
    course_id: int,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(require_admin),
):
    result = await db.execute(select(Course).where(Course.id == course_id))
    course = result.scalar()
    if not course:
        raise HTTPException(status_code=404, detail="课程不存在")
    cat_name = None
    if course.category_id:
        cat_result = await db.execute(select(Category).where(Category.id == course.category_id))
        cat = cat_result.scalar()
        if cat:
            cat_name = cat.name
    return {
        "id": course.id, "category_id": course.category_id, "category_name": cat_name,
        "code": course.code, "name": course.name, "description": course.description,
        "level": course.level, "duration_days": course.duration_days,
        "sort_order": course.sort_order, "is_active": course.is_active,
        "created_at": course.created_at.isoformat() if course.created_at else None,
        "updated_at": course.updated_at.isoformat() if course.updated_at else None,
    }

@router.put("/{course_id}", response_model=CourseResponse)
async def update_course(
    course_id: int,
    data: CourseUpdate,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(require_admin),
):
    result = await db.execute(select(Course).where(Course.id == course_id))
    course = result.scalar()
    if not course:
        raise HTTPException(status_code=404, detail="课程不存在")
    if data.category_id:
        cat_result = await db.execute(select(Category).where(Category.id == data.category_id))
        if not cat_result.scalar():
            raise HTTPException(status_code=400, detail="类别不存在")
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(course, key, value)
    course.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
    await db.commit()
    await db.refresh(course)
    cat_name = None
    if course.category_id:
        cat_result = await db.execute(select(Category).where(Category.id == course.category_id))
        cat = cat_result.scalar()
        if cat:
            cat_name = cat.name
    return {
        "id": course.id, "category_id": course.category_id, "category_name": cat_name,
        "code": course.code, "name": course.name, "description": course.description,
        "level": course.level, "duration_days": course.duration_days,
        "sort_order": course.sort_order, "is_active": course.is_active,
        "created_at": course.created_at.isoformat() if course.created_at else None,
        "updated_at": course.updated_at.isoformat() if course.updated_at else None,
    }

@router.delete("/{course_id}")
async def delete_course(
    course_id: int,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(require_admin),
):
    result = await db.execute(select(Course).where(Course.id == course_id))
    course = result.scalar()
    if not course:
        raise HTTPException(status_code=404, detail="课程不存在")
    await db.delete(course)
    await db.commit()
    return {"success": True, "message": "课程已删除"}
