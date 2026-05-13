"""
管理员-学员预览
"""

from fastapi import APIRouter

from .shared import *

router = APIRouter(prefix="", tags=["管理员-学员预览"])

# ============================
# 管理员-学员预览
# ============================
# ===== STUDENT PREVIEW (2 endpoints) =====
# ============================

@router.get("/student-preview/{student_id}/chapters")
async def admin_preview_student_chapters(
    student_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin)
):
    """Admin Preview Student Chapters"""
    result = await db.execute(
        sql_text("""
            SELECT c.id, c.title, c.sort_order,
                   COALESCE(cp.status::text, 'locked') as status,
                   COALESCE(cp.reading_pages, 0) as reading_pages
            FROM chapters c
            LEFT JOIN chapter_progress cp ON cp.chapter_id = c.id AND cp.user_id = :uid
            ORDER BY c.sort_order
        """),
        {"uid": student_id}
    )
    return [dict(r._mapping) for r in result.fetchall()]


@router.get("/student-preview/{student_id}/chapters/{chapter_id}")
async def admin_preview_chapter_content(
    student_id: int,
    chapter_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin)
):
    """Admin Preview Chapter Content"""
    result = await db.execute(
        sql_text("SELECT * FROM chapters WHERE id = :id"),
        {"id": chapter_id}
    )
    row = result.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="章节不存在")
    return dict(row._mapping)


# ============================

