"""
章节学习API - 学员章节进度、课后练习、自测模式
"""
import json
from datetime import datetime, timezone

from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth_v2 import get_current_user
from app.core.database import get_db
from app.core.textbook_utils import get_class_textbook_ids
from app.models.class_system import (
    Chapter,
    ChapterBookmark,
    ChapterExercise,
    ChapterNote,
    ChapterProgress,
    ChapterProgressStatus,
    Class,
    ClassMember,
    LearningPath,
    Question,
    Test,
    TestResult,
    Textbook,
    User,
    UserRole,
)

router = APIRouter(prefix="/student/chapters", tags=["学员章节学习"])


async def get_user_class(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """获取用户所属班级（含角色校验）"""
    if user.role != UserRole.STUDENT:
        raise HTTPException(status_code=403, detail="需要学员权限")
    result = await db.execute(
        select(ClassMember).where(ClassMember.user_id == user.id)
    )
    member = result.scalar_one_or_none()
    if not member:
        raise HTTPException(status_code=400, detail="未加入班级")
    return member.class_id


# ═══════════════════════════════════════════════
# 章节列表与进度
# ═══════════════════════════════════════════════

@router.get("")
async def list_chapters(
    class_id: int = Depends(get_user_class),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """获取教材章节列表（含进度）- 统一教材查询"""
    textbook_ids = await get_class_textbook_ids(db, class_id)
    if not textbook_ids:
        return []

    # 获取第一本分配的教材
    result = await db.execute(
        select(Textbook).where(Textbook.id.in_(textbook_ids), Textbook.is_active == True).limit(1)
    )
    textbook = result.scalar_one_or_none()
    if not textbook:
        return []

    result = await db.execute(
        select(Chapter).where(
            Chapter.textbook_id == textbook.id,
            Chapter.parent_id.is_(None)
        ).order_by(Chapter.sort_order)
    )
    chapters = result.scalars().all()

    result = await db.execute(
        select(ChapterProgress).where(
            ChapterProgress.user_id == user.id,
            ChapterProgress.class_id == class_id
        )
    )
    progress_list = result.scalars().all()
    progress_map = {p.chapter_id: p for p in progress_list}

    output = []
    for ch in chapters:
        result_sections = await db.execute(
            select(Chapter).where(Chapter.parent_id == ch.id).order_by(Chapter.sort_order)
        )
        sections = result_sections.scalars().all()

        section_list = []
        for sec in sections:
            p = progress_map.get(sec.id)
            section_list.append({
                "id": sec.id,
                "title": sec.title,
                "status": p.status.value if p else "locked"
            })

        output.append({
            "id": ch.id,
            "title": ch.title,
            "sections": section_list
        })

    return output


# ═══════════════════════════════════════════════
# 进度汇总
# ═══════════════════════════════════════════════

@router.get("/my-progress")
async def get_progress_summary(
    class_id: int = Depends(get_user_class),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """获取学习进度汇总（动态计算总章节数）"""
    result = await db.execute(
        select(ChapterProgress).where(
            ChapterProgress.user_id == user.id,
            ChapterProgress.class_id == class_id
        )
    )
    progress_list = result.scalars().all()

    # 动态计算总章节数
    textbook_ids = await get_class_textbook_ids(db, class_id)
    if textbook_ids:
        result = await db.execute(
            select(Chapter).where(
                Chapter.textbook_id.in_(textbook_ids),
                Chapter.parent_id.is_not(None)
            )
        )
        total_sections = len(result.scalars().all()) or 72
    else:
        total_sections = 72

    # 弹性解锁：waiting_test 也计为完成
    completed = sum(1 for p in progress_list if p.status in
                    (ChapterProgressStatus.COMPLETED, ChapterProgressStatus.WAITING_TEST))
    reading_done = sum(1 for p in progress_list if p.status == ChapterProgressStatus.READING_DONE)
    practicing = sum(1 for p in progress_list if p.status == ChapterProgressStatus.PRACTICING)
    waiting_test = sum(1 for p in progress_list if p.status == ChapterProgressStatus.WAITING_TEST)
    self_test_completed = sum(1 for p in progress_list if p.status == ChapterProgressStatus.COMPLETED)
    total_time = sum(p.total_reading_time for p in progress_list)

    return {
        "total_sections": total_sections,
        "completed": completed,
        "reading_done": reading_done,
        "practicing": practicing,
        "waiting_test": waiting_test,
        "self_test_completed": self_test_completed,
        "progress_percent": round(completed / total_sections * 100, 1) if total_sections else 0,
        "total_reading_time_minutes": round(total_time / 60, 1)
    }


# ═══════════════════════════════════════════════
# PDF教材阅读
# ═══════════════════════════════════════════════

@router.get("/pdf")
async def get_pdf_textbook(
    class_id: int = Depends(get_user_class),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """获取PDF教材"""
    from app.models.class_system import StudentPDFProgress, TextbookPage

    pdf_ids = await get_class_textbook_ids(db, class_id, resource_type='pdf')

    if not pdf_ids:
        return {"textbook": None, "pages": [], "last_page": 0}

    result = await db.execute(
        select(Textbook).where(Textbook.id.in_(pdf_ids), Textbook.is_active == True).limit(1)
    )
    textbook = result.scalar_one_or_none()

    if not textbook:
        return {"textbook": None, "pages": [], "last_page": 0}

    result = await db.execute(
        select(TextbookPage).where(
            TextbookPage.textbook_id == textbook.id,
            TextbookPage.is_visible == True
        ).order_by(TextbookPage.page_number)
    )
    pages = result.scalars().all()

    result = await db.execute(
        select(StudentPDFProgress).where(
            StudentPDFProgress.user_id == user.id,
            StudentPDFProgress.textbook_id == textbook.id,
            StudentPDFProgress.class_id == class_id
        )
    )
    progress = result.scalar_one_or_none()

    return {
        "textbook": {"id": textbook.id, "name": textbook.name},
        "pages": [{"id": p.id, "page_number": p.page_number, "url": p.image_url} for p in pages],
        "last_page": progress.current_page if progress else 0
    }


@router.post("/pdf/progress")
async def update_pdf_progress(
    data: dict = Body(...),
    class_id: int = Depends(get_user_class),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """更新PDF阅读进度"""
    from app.models.class_system import StudentPDFProgress

    result = await db.execute(select(Textbook).where(Textbook.is_active == True).limit(1))
    textbook = result.scalar_one_or_none()
    if not textbook:
        return {"success": False}

    result = await db.execute(
        select(StudentPDFProgress).where(
            StudentPDFProgress.user_id == user.id,
            StudentPDFProgress.textbook_id == textbook.id,
            StudentPDFProgress.class_id == class_id
        )
    )
    progress = result.scalar_one_or_none()

    if progress:
        progress.current_page = data.get("current_page", 0)
        progress.total_pages = data.get("total_pages", 0)
    else:
        progress = StudentPDFProgress(
            user_id=user.id, textbook_id=textbook.id, class_id=class_id,
            current_page=data.get("current_page", 0),
            total_pages=data.get("total_pages", 0)
        )
        db.add(progress)

    await db.commit()
    return {"success": True}


# ═══════════════════════════════════════════════

# ═══════════════════════════════════════════════
# 学习工具：搜索 / 证书 / 复习 / 学习路径
# ═══════════════════════════════════════════════



@router.get("/search")
async def search_content(
    q: str,
    class_id: int = Depends(get_user_class),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """搜索章节内容"""
    if not q or len(q) < 2:
        raise HTTPException(status_code=400, detail="关键词至少2个字符")

    textbook_ids = await get_class_textbook_ids(db, class_id)
    if not textbook_ids:
        return []

    result = await db.execute(
        select(Chapter).where(
            Chapter.textbook_id.in_(textbook_ids),
            Chapter.content.ilike(f"%{q}%")
        ).limit(20)
    )
    chapters = result.scalars().all()
    return [{
        "id": c.id, "title": c.title,
        "snippet": c.content[:300].replace("<br>", "").replace("\n", " "),
        "textbook_id": c.textbook_id
    } for c in chapters]


# ═══════════════════════════════════════════════
# 结业证书
# ═══════════════════════════════════════════════

@router.get("/certificate")
async def get_certificate(
    class_id: int = Depends(get_user_class),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """获取结业证书数据（需完成全部章节）"""
    textbook_ids = await get_class_textbook_ids(db, class_id)
    if not textbook_ids:
        raise HTTPException(status_code=400, detail="未分配教材")

    # 统计总章节数
    result = await db.execute(
        select(Chapter).where(Chapter.textbook_id.in_(textbook_ids), Chapter.parent_id.is_not(None))
    )
    total_sections = len(result.scalars().all()) or 72

    # 统计完成进度
    result = await db.execute(
        select(ChapterProgress).where(
            ChapterProgress.user_id == user.id,
            ChapterProgress.class_id == class_id
        )
    )
    progress_list = result.scalars().all()
    completed = sum(1 for p in progress_list if p.status in (
        ChapterProgressStatus.COMPLETED, ChapterProgressStatus.WAITING_TEST
    ))
    total_time = sum(p.total_reading_time or 0 for p in progress_list)

    if completed < total_sections:
        raise HTTPException(status_code=403, detail=f"尚未完成全部课程（{completed}/{total_sections}）")

    # 获取班级名称
    result = await db.execute(select(Class).where(Class.id == class_id))
    cls_obj = result.scalar_one_or_none()

    # 获取平均成绩
    result = await db.execute(
        select(TestResult).join(Test).where(
            TestResult.user_id == user.id, Test.class_id == class_id
        )
    )
    all_results = result.scalars().all()
    avg_score = round(sum(r.score for r in all_results if r.score) / len(all_results), 1) if all_results else 0

    return {
        "student_name": user.name,
        "class_name": cls_obj.name if cls_obj else "",
        "completed_at": max((p.completed_at for p in progress_list if p.completed_at), default=datetime.now(timezone.utc).replace(tzinfo=None)).isoformat(),
        "total_hours": round(total_time / 3600, 1),
        "total_sections": total_sections,
        "avg_score": avg_score,
        "student_id": user.id
    }


# ═══════════════════════════════════════════════
# 智能复习
# ═══════════════════════════════════════════════

@router.get("/review")
async def get_smart_review(
    class_id: int = Depends(get_user_class),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """智能复习推荐：识别薄弱章节"""
    textbook_ids = await get_class_textbook_ids(db, class_id)
    if not textbook_ids:
        return {"weak_areas": [], "suggestion": "暂无数据"}

    # 获取所有章节进度
    result = await db.execute(
        select(ChapterProgress).where(
            ChapterProgress.user_id == user.id,
            ChapterProgress.class_id == class_id
        )
    )
    progress_list = result.scalars().all()
    progress_map = {p.chapter_id: p for p in progress_list}

    # 获取所有章节（有练习的）
    result = await db.execute(
        select(Chapter).where(Chapter.textbook_id.in_(textbook_ids), Chapter.parent_id.is_not(None))
    )
    chapters = result.scalars().all()

    weak_areas = []
    for ch in chapters:
        progress = progress_map.get(ch.id)
        # 薄弱：已完成但练习不通过（practice_done 而非 completed）或 waiting_test
        is_weak = progress and progress.status in (
            ChapterProgressStatus.PRACTICE_DONE, ChapterProgressStatus.WAITING_TEST
        )
        if is_weak:
            weak_areas.append({
                "chapter_id": ch.id,
                "title": ch.title,
                "status": progress.status.value
            })

    # 推荐复习策略
    if not weak_areas:
        suggestion = "所有已完成章节均已通过，继续保持！"
    elif len(weak_areas) <= 3:
        suggestion = f"建议复习 {len(weak_areas)} 个薄弱章节，重点练习后可自测通关"
    else:
        suggestion = f"有 {len(weak_areas)} 个章节需要复习，建议从第一章开始逐节巩固"

    return {
        "weak_areas": weak_areas,
        "suggestion": suggestion,
        "total_weak": len(weak_areas)
    }


# ═══════════════════════════════════════════════
# 分层教学 / 自适应学习路径
# ═══════════════════════════════════════════════

@router.get("/learning-path")
async def get_learning_path(
    class_id: int = Depends(get_user_class),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """获取学习路径：快速通道 / 常规 / 强化"""
    # 检查已有路径
    result = await db.execute(
        select(LearningPath).where(LearningPath.user_id == user.id)
    )
    path = result.scalar_one_or_none()

    if path:
        return {
            "path_type": path.path_type,
            "assigned_reason": path.assigned_reason,
            "current_stage": path.current_stage,
            "fast_track_skipped": json.loads(path.fast_track_skipped) if path.fast_track_skipped else []
        }

    # 自动评估：根据历史成绩分配路径
    result = await db.execute(
        select(TestResult).where(TestResult.user_id == user.id)
    )
    test_results = result.scalars().all()

    if not test_results:
        # 新学员，默认常规路径
        path_type = "normal"
        reason = "默认路径（新学员）"
    else:
        scores = [r.score for r in test_results if r.score is not None]
        avg_score = sum(scores) / len(scores) if scores else 0

        if avg_score >= 90:
            path_type = "fast"
            reason = f"成绩优秀（平均{round(avg_score)}分），进入快速通道"
        elif avg_score < 60:
            path_type = "reinforcement"
            reason = f"基础薄弱（平均{round(avg_score)}分），进入强化通道"
        else:
            path_type = "normal"
            reason = f"常规路径（平均{round(avg_score)}分）"

    # 保存路径
    path = LearningPath(
        user_id=user.id, class_id=class_id,
        path_type=path_type, assigned_reason=reason
    )
    db.add(path)
    await db.commit()

    return {
        "path_type": path_type,
        "assigned_reason": reason,
        "current_stage": 0,
        "fast_track_skipped": []
    }


@router.post("/learning-path/reassess")
async def reassess_learning_path(
    class_id: int = Depends(get_user_class),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """重新评估学习路径（删除旧路径后重新分配）"""
    result = await db.execute(
        select(LearningPath).where(LearningPath.user_id == user.id)
    )
    path = result.scalar_one_or_none()
    if path:
        await db.delete(path)
        await db.commit()

    # 重新评估
    return await get_learning_path(class_id, db, user)
# 章节内容
# ═══════════════════════════════════════════════

# ═══════════════════════════════════════════════
# 学习工具：笔记 / 书签 / 搜索
# ═══════════════════════════════════════════════

@router.get("/notes")
async def list_notes(
    class_id: int = Depends(get_user_class),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """我的笔记列表"""
    result = await db.execute(
        select(ChapterNote).where(
            ChapterNote.user_id == user.id,
            ChapterNote.class_id == class_id
        ).order_by(ChapterNote.updated_at.desc())
    )
    notes = result.scalars().all()
    return [{
        "id": n.id, "chapter_id": n.chapter_id, "content": n.content[:200],
        "created_at": n.created_at.isoformat() if n.created_at else None,
        "updated_at": n.updated_at.isoformat() if n.updated_at else None
    } for n in notes]


@router.post("/notes")
async def save_note(
    chapter_id: int,
    data: dict = Body(...),
    class_id: int = Depends(get_user_class),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """保存/更新笔记"""
    note_id = data.get("id")
    content = data.get("content", "")

    if note_id:
        note = await db.get(ChapterNote, note_id)
        if note and note.user_id == user.id:
            note.content = content
            note.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
            await db.commit()
            return {"success": True, "id": note.id}

    note = ChapterNote(user_id=user.id, class_id=class_id, chapter_id=chapter_id, content=content)
    db.add(note)
    await db.commit()
    return {"success": True, "id": note.id}


@router.delete("/notes/{note_id}")
async def delete_note(
    note_id: int,
    class_id: int = Depends(get_user_class),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """删除笔记"""
    note = await db.get(ChapterNote, note_id)
    if not note or note.user_id != user.id:
        raise HTTPException(status_code=404, detail="笔记不存在")
    await db.delete(note)
    await db.commit()
    return {"success": True}


@router.get("/bookmarks")
async def list_bookmarks(
    class_id: int = Depends(get_user_class),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """我的书签列表"""
    result = await db.execute(
        select(ChapterBookmark).where(
            ChapterBookmark.user_id == user.id,
            ChapterBookmark.class_id == class_id
        ).order_by(ChapterBookmark.created_at.desc())
    )
    bookmarks = result.scalars().all()
    chapters = {}
    for b in bookmarks:
        if b.chapter_id not in chapters:
            ch = await db.get(Chapter, b.chapter_id)
            chapters[b.chapter_id] = ch.title if ch else ""
    return [{
        "id": b.id, "chapter_id": b.chapter_id, "chapter_title": chapters.get(b.chapter_id, ""),
        "note": b.note, "created_at": b.created_at.isoformat() if b.created_at else None
    } for b in bookmarks]


@router.post("/bookmarks")
async def add_bookmark(
    chapter_id: int,
    data: dict = Body(...),
    class_id: int = Depends(get_user_class),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """添加书签"""
    bookmark = ChapterBookmark(
        user_id=user.id, class_id=class_id,
        chapter_id=chapter_id, note=data.get("note", "")
    )
    db.add(bookmark)
    await db.commit()
    return {"success": True, "id": bookmark.id}


@router.delete("/bookmarks/{bookmark_id}")
async def delete_bookmark(
    bookmark_id: int,
    class_id: int = Depends(get_user_class),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """删除书签"""
    bookmark = await db.get(ChapterBookmark, bookmark_id)
    if not bookmark or bookmark.user_id != user.id:
        raise HTTPException(status_code=404, detail="书签不存在")
    await db.delete(bookmark)
    await db.commit()
    return {"success": True}
@router.get("/{chapter_id}")
async def get_chapter_content(
    chapter_id: int,
    class_id: int = Depends(get_user_class),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """获取章节内容"""
    chapter = await db.get(Chapter, chapter_id)
    if not chapter:
        raise HTTPException(status_code=404, detail="章节不存在")

    result = await db.execute(
        select(ChapterProgress).where(
            ChapterProgress.user_id == user.id,
            ChapterProgress.class_id == class_id,
            ChapterProgress.chapter_id == chapter_id
        )
    )
    progress = result.scalar_one_or_none()

    # 解锁检查
    if chapter.parent_id and (not progress or progress.status == ChapterProgressStatus.LOCKED):
        prev = await db.execute(
            select(Chapter).where(
                Chapter.parent_id == chapter.parent_id,
                Chapter.sort_order == chapter.sort_order - 1
            )
        ).scalar_one_or_none()
        if prev:
            prev_p = await db.execute(
                select(ChapterProgress).where(
                    ChapterProgress.user_id == user.id,
                    ChapterProgress.class_id == class_id,
                    ChapterProgress.chapter_id == prev.id
                )
            ).scalar_one_or_none()
            if not prev_p or prev_p.status not in (ChapterProgressStatus.COMPLETED, ChapterProgressStatus.WAITING_TEST):
                raise HTTPException(status_code=403, detail="请先完成上一小节")

    return {
        "id": chapter.id,
        "title": chapter.title,
        "content": chapter.content,
        "status": progress.status.value if progress else "locked"
    }


# ═══════════════════════════════════════════════
# 阅读进度
# ═══════════════════════════════════════════════

@router.post("/{chapter_id}/start-reading")
async def start_reading(
    chapter_id: int,
    class_id: int = Depends(get_user_class),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """开始阅读"""
    chapter = await db.get(Chapter, chapter_id)
    if not chapter:
        raise HTTPException(status_code=404, detail="章节不存在")

    result = await db.execute(
        select(ChapterProgress).where(
            ChapterProgress.user_id == user.id,
            ChapterProgress.class_id == class_id,
            ChapterProgress.chapter_id == chapter_id
        )
    )
    progress = result.scalar_one_or_none()

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    if not progress:
        progress = ChapterProgress(
            user_id=user.id, class_id=class_id, chapter_id=chapter_id,
            status=ChapterProgressStatus.READING, reading_start_at=now
        )
        db.add(progress)
    elif progress.status == ChapterProgressStatus.LOCKED:
        progress.status = ChapterProgressStatus.READING
        progress.reading_start_at = now

    await db.commit()
    return {"success": True, "message": "开始阅读"}


@router.post("/{chapter_id}/update-progress")
async def update_reading_progress(
    chapter_id: int,
    reading_time: int,
    current_page: int,
    class_id: int = Depends(get_user_class),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """更新阅读进度"""
    result = await db.execute(
        select(ChapterProgress).where(
            ChapterProgress.user_id == user.id,
            ChapterProgress.class_id == class_id,
            ChapterProgress.chapter_id == chapter_id
        )
    )
    progress = result.scalar_one_or_none()
    if not progress:
        raise HTTPException(status_code=400, detail="请先开始阅读")

    progress.total_reading_time += reading_time
    progress.reading_pages = max(progress.reading_pages, current_page)
    progress.last_updated = datetime.now(timezone.utc).replace(tzinfo=None)

    chapter = await db.get(Chapter, chapter_id)
    if chapter and chapter.page_end and current_page >= chapter.page_end:
        progress.status = ChapterProgressStatus.READING_DONE
        progress.reading_done_at = datetime.now(timezone.utc).replace(tzinfo=None)

    await db.commit()
    return {"success": True, "status": progress.status.value}


@router.post("/{chapter_id}/finish-reading")
async def finish_reading(
    chapter_id: int,
    class_id: int = Depends(get_user_class),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """标记阅读完成 → 进入练习"""
    result = await db.execute(
        select(ChapterProgress).where(
            ChapterProgress.user_id == user.id,
            ChapterProgress.class_id == class_id,
            ChapterProgress.chapter_id == chapter_id
        )
    )
    progress = result.scalar_one_or_none()
    if not progress:
        raise HTTPException(status_code=400, detail="未开始阅读")

    progress.status = ChapterProgressStatus.PRACTICING
    progress.reading_done_at = datetime.now(timezone.utc).replace(tzinfo=None)
    await db.commit()
    return {"success": True, "message": "可以开始练习"}


# ═══════════════════════════════════════════════
# 课后练习（含自测模式）
# ═══════════════════════════════════════════════

@router.get("/{chapter_id}/exercises")
async def get_chapter_exercises(
    chapter_id: int,
    class_id: int = Depends(get_user_class),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """获取章节配套练习"""
    result = await db.execute(
        select(ChapterProgress).where(
            ChapterProgress.user_id == user.id,
            ChapterProgress.class_id == class_id,
            ChapterProgress.chapter_id == chapter_id
        )
    )
    progress = result.scalar_one_or_none()

    allowed_statuses = [
        ChapterProgressStatus.READING_DONE,
        ChapterProgressStatus.PRACTICING,
        ChapterProgressStatus.PRACTICE_DONE,
        ChapterProgressStatus.WAITING_TEST,
        ChapterProgressStatus.COMPLETED
    ]
    if not progress or progress.status not in allowed_statuses:
        raise HTTPException(status_code=403, detail="请先完成章节阅读")

    result = await db.execute(
        select(ChapterExercise).where(ChapterExercise.chapter_id == chapter_id).order_by(ChapterExercise.sort_order)
    )
    exercises = result.scalars().all()

    questions = []
    for ex in exercises:
        q = await db.get(Question, ex.question_id)
        if q:
            questions.append({
                "id": q.id,
                "content": q.content,
                "options": q.get_options()
            })

    return {"chapter_id": chapter_id, "questions": questions}


@router.post("/{chapter_id}/submit-exercises")
async def submit_exercises(
    chapter_id: int,
    data: dict = Body(...),
    class_id: int = Depends(get_user_class),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """提交练习答案"""
    # Support both old format (list) and new format (dict with answers + self_test)
    if isinstance(data, list):
        answers = data
        self_test = False
    else:
        answers = data.get("answers", [])
        self_test = data.get("self_test", False)
        tab_switches = data.get("tab_switch_count", 0)
        time_spent_val = data.get("time_spent", 0)
    result = await db.execute(
        select(ChapterProgress).where(
            ChapterProgress.user_id == user.id,
            ChapterProgress.class_id == class_id,
            ChapterProgress.chapter_id == chapter_id
        )
    )
    progress = result.scalar_one_or_none()

    if not progress or progress.status != ChapterProgressStatus.PRACTICING:
        raise HTTPException(status_code=400, detail="请先完成阅读")

    result = await db.execute(
        select(ChapterExercise).where(ChapterExercise.chapter_id == chapter_id).order_by(ChapterExercise.sort_order)
    )
    exercises = result.scalars().all()

    correct_count = 0
    total_count = len(exercises)
    results = []

    for ex in exercises:
        q = await db.get(Question, ex.question_id)
        if not q:
            continue

        user_answer = next((a["answer"] for a in answers if a["question_id"] == q.id), None)
        correct_answer = q.answer  # Question model uses 'answer' field (not 'correct_answer')
        is_correct = str(user_answer) == str(correct_answer)

        if is_correct:
            correct_count += 1

        results.append({
            "question_id": q.id,
            "user_answer": user_answer,
            "correct_answer": correct_answer,
            "is_correct": is_correct,
            "explanation": q.explanation
        })

    passed = correct_count >= total_count * 0.7
    progress.practice_done_at = datetime.now(timezone.utc).replace(tzinfo=None)
    progress.tab_switch_count = max(progress.tab_switch_count or 0, tab_switches)

    if passed:
        if self_test:
            # 自测模式：直接完成
            progress.status = ChapterProgressStatus.COMPLETED
            progress.completed_at = datetime.now(timezone.utc).replace(tzinfo=None)
            message = f"自测通过！（{correct_count}/{total_count}）本章节已完成"
        else:
            progress.status = ChapterProgressStatus.WAITING_TEST
            message = f"练习通过！（{correct_count}/{total_count}）等待教练发布随堂测验"
    else:
        message = f"练习未通过（{correct_count}/{total_count}），请重新练习"

    await db.commit()

    return {
        "success": passed,
        "score": f"{correct_count}/{total_count}",
        "results": results,
        "message": message,
        "self_test": self_test,
        "completed": passed and self_test
    }


