"""
Admin API - 班级课程关联管理 (V7)
管理班级与课程的绑定关系
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.core.database import get_db
from app.models.class_system import Class, Course, ClassCourse
from app.api.admin.shared import require_admin, User

router = APIRouter(prefix="", tags=["V7-班级课程管理"])


# ── Schemas ──

class ClassCourseCreate(BaseModel):
    class_id: int = Field(..., description="班级ID")
    course_id: int = Field(..., description="课程ID")


class ClassCourseBatchCreate(BaseModel):
    class_id: int = Field(..., description="班级ID")
    course_ids: list[int] = Field(..., description="课程ID列表")


class ClassCourseItem(BaseModel):
    id: int
    class_id: int
    course_id: int
    course_name: str = ""
    course_code: str = ""


# ── Endpoints ──

@router.get("/classes/{class_id}/courses")
async def get_class_courses(
    class_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin),
):
    """获取班级绑定的课程列表"""
    cls = await db.get(Class, class_id)
    if not cls:
        raise HTTPException(status_code=404, detail="班级不存在")

    result = await db.execute(
        text("""
            SELECT cc.id, cc.class_id, cc.course_id, co.name AS course_name, co.code AS course_code
            FROM class_courses cc
            JOIN courses co ON cc.course_id = co.id
            WHERE cc.class_id = :cid
            ORDER BY co.sort_order, co.id
        """),
        {"cid": class_id}
    )
    rows = result.fetchall()
    return [
        {"id": r[0], "class_id": r[1], "course_id": r[2], "course_name": r[3], "course_code": r[4]}
        for r in rows
    ]


@router.post("/classes/{class_id}/courses")
async def add_course_to_class(
    class_id: int,
    data: ClassCourseCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin),
):
    """绑定课程到班级"""
    cls = await db.get(Class, class_id)
    if not cls:
        raise HTTPException(status_code=404, detail="班级不存在")

    course = await db.get(Course, data.course_id)
    if not course:
        raise HTTPException(status_code=404, detail="课程不存在")

    # Check if already exists
    existing = await db.execute(
        text("SELECT id FROM class_courses WHERE class_id = :cid AND course_id = :coid"),
        {"cid": class_id, "coid": data.course_id}
    )
    if existing.fetchone():
        raise HTTPException(status_code=400, detail="该课程已绑定到此班级")

    cc = ClassCourse(class_id=class_id, course_id=data.course_id)
    db.add(cc)
    await db.commit()
    await db.refresh(cc)
    return {"success": True, "id": cc.id}


@router.post("/classes/{class_id}/courses/batch")
async def batch_add_courses(
    class_id: int,
    data: ClassCourseBatchCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin),
):
    """批量绑定课程到班级"""
    cls = await db.get(Class, class_id)
    if not cls:
        raise HTTPException(status_code=404, detail="班级不存在")

    added = 0
    skipped = 0
    for course_id in data.course_ids:
        course = await db.get(Course, course_id)
        if not course:
            continue
        existing = await db.execute(
            text("SELECT id FROM class_courses WHERE class_id = :cid AND course_id = :coid"),
            {"cid": class_id, "coid": course_id}
        )
        if existing.fetchone():
            skipped += 1
            continue
        cc = ClassCourse(class_id=class_id, course_id=course_id)
        db.add(cc)
        added += 1

    await db.commit()
    return {"success": True, "added": added, "skipped": skipped}


@router.delete("/classes/{class_id}/courses/{course_id}")
async def remove_course_from_class(
    class_id: int,
    course_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin),
):
    """解除班级与课程的绑定"""
    result = await db.execute(
        text("DELETE FROM class_courses WHERE class_id = :cid AND course_id = :coid RETURNING id"),
        {"cid": class_id, "coid": course_id}
    )
    deleted = result.scalar()
    await db.commit()
    if not deleted:
        raise HTTPException(status_code=404, detail="绑定关系不存在")
    return {"success": True, "deleted_id": deleted}


@router.get("/courses/{course_id}/classes")
async def get_course_classes(
    course_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin),
):
    """获取课程被哪些班级使用"""
    course = await db.get(Course, course_id)
    if not course:
        raise HTTPException(status_code=404, detail="课程不存在")

    result = await db.execute(
        text("""
            SELECT cc.id, cc.class_id, c.name AS class_name, c.status
            FROM class_courses cc
            JOIN classes c ON cc.class_id = c.id
            WHERE cc.course_id = :coid
            ORDER BY c.id DESC
        """),
        {"coid": course_id}
    )
    rows = result.fetchall()
    return [
        {"id": r[0], "class_id": r[1], "class_name": r[2], "status": r[3]}
        for r in rows
    ]
