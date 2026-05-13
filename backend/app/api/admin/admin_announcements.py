"""
管理员-公告管理 CRUD
"""

from fastapi import APIRouter, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.class_system import Announcement, Class

from .shared import *

router = APIRouter(prefix="", tags=["管理员-公告管理"])


@router.get("/announcements")
async def list_announcements(
    class_id: int | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin)
):
    """公告列表（可按班级筛选）"""
    q = select(Announcement)
    if class_id:
        q = q.where(Announcement.class_id == class_id)
    count_q = select(func.count()).select_from(q.subquery())
    total = (await db.execute(count_q)).scalar() or 0
    q = q.order_by(Announcement.pinned.desc(), Announcement.created_at.desc())
    q = q.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(q)
    items = result.scalars().all()
    return {
        "total": total, "page": page, "page_size": page_size,
        "data": [{
            "id": a.id, "class_id": a.class_id, "title": a.title,
            "content": a.content, "created_by": a.created_by,
            "pinned": a.pinned,
            "created_at": a.created_at.isoformat() if a.created_at else None
        } for a in items]
    }


class AnnouncementCreate(BaseModel):
    class_id: int  # Required - must specify which class
    title: str = ""
    content: str = ""
    pinned: bool = False


@router.post("/announcements")
async def create_announcement(
    data: AnnouncementCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin)
):
    """创建公告"""
    try:
        cls = await db.get(Class, data.class_id)
        if not cls:
            raise HTTPException(status_code=404, detail="班级不存在")
        ann = Announcement(
            class_id=data.class_id,
            title=data.title,
            content=data.content,
            created_by=user.id,
            pinned=data.pinned
        )
        db.add(ann)
        await db.commit()
        await db.refresh(ann)
        return {"success": True, "id": ann.id}
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=f"创建失败：{str(e)}")


@router.put("/announcements/{ann_id}")
async def update_announcement(
    ann_id: int,
    data: dict = Body(...),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin)
):
    """更新公告"""
    ann = await db.get(Announcement, ann_id)
    if not ann:
        raise HTTPException(status_code=404, detail="公告不存在")
    for field in ["title", "content", "pinned"]:
        if field in data:
            setattr(ann, field, data[field])
    await db.commit()
    return {"success": True}


@router.delete("/announcements/{ann_id}")
async def delete_announcement(
    ann_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin)
):
    """删除公告"""
    ann = await db.get(Announcement, ann_id)
    if not ann:
        raise HTTPException(status_code=404, detail="公告不存在")
    await db.delete(ann)
    await db.commit()
    return {"success": True}
