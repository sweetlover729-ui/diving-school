"""
管理员-教材预览
"""


from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy import text as sql_text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db

from .shared import *

router = APIRouter(prefix="", tags=["管理员-教材预览"])

# ============================
# 管理员-教材预览
# ============================
# ===== TEXTBOOK PREVIEW (2 endpoints) =====
# ============================

@router.get("/textbook-preview/chapters")
async def admin_textbook_preview_chapters(
    textbook_id: int | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin)
):
    """Admin Textbook Preview Chapters"""
    if not textbook_id:
        return []
    result = await db.execute(
        # chapters表字段：id, textbook_id, parent_id, title, content, sort_order, page_start, page_end, is_visible
        # 无level列；用 parent_id 是否为 NULL 来判断层级
        sql_text("""
            SELECT id, title, sort_order, parent_id, content,
                   CASE WHEN parent_id IS NULL THEN 1 ELSE 2 END as level
            FROM chapters WHERE textbook_id = :tid ORDER BY sort_order
        """),
        {"tid": textbook_id}
    )
    rows = result.fetchall()
    # 构建树形结构
    chapters = []
    for r in rows:
        ch = {
            "id": r.id,
            "name": r.title,      # 列名是 title，前端用 name
            "level": r.level,      # 动态计算：1=顶层，2=子章节
            "sort_order": r.sort_order,
            "parent_id": r.parent_id,
            "children": []
        }
        chapters.append(ch)
    # 转为树
    by_id = {c["id"]: c for c in chapters}
    roots = []
    for c in chapters:
        if c["parent_id"] is None:
            roots.append(c)
        elif c["parent_id"] in by_id:
            by_id[c["parent_id"]]["children"].append(c)
    return {"chapters": roots}


@router.get("/textbook-preview/chapters/{chapter_id}")
async def admin_textbook_preview_chapter_content(
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


@router.put("/textbook-preview/chapters/{chapter_id}")
async def admin_update_chapter_content(
    chapter_id: int,
    content: str = Body(...),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin)
):
    """Admin Update Chapter Content"""
    await db.execute(
        sql_text("UPDATE chapters SET content = :content WHERE id = :id"),
        {"id": chapter_id, "content": content}
    )
    await db.commit()
    return {"success": True}


# ============================

