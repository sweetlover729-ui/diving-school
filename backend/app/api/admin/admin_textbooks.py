"""
管理员-教材管理
"""



import os

from fastapi import APIRouter, Body, Depends, File, HTTPException, UploadFile
from sqlalchemy import text as sql_text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.class_system import Textbook

from .shared import *

router = APIRouter(prefix="", tags=["管理员-教材管理"])

# ============================
# 管理员-教材管理
# ============================
# ===== TEXTBOOKS (33 endpoints) - 核心 =====
# ============================

# ---- 基础 CRUD ----

@router.get("/textbooks")
async def list_textbooks(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin)
):
    """List Textbooks"""
    result = await db.execute(
        sql_text("""
            SELECT
                id, name,
                total_chapters as chapter_count,
                total_pages,
                file_type,
                import_status,
                import_error,
                has_interactive,
                file_path,
                interactive_path,
                is_active
            FROM textbooks
            ORDER BY id DESC
        """)
    )
    return [dict(r._mapping) for r in result.fetchall()]


@router.post("/textbooks")
async def create_textbook(
    req: TextbookCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin)
):
    """Create Textbook"""
    tb = Textbook(
        name=req.name, description=req.description,
        total_chapters=req.total_chapters, total_pages=req.total_pages,
        is_active=req.is_active
    )
    db.add(tb)
    await db.commit()
    await db.refresh(tb)
    return {"id": tb.id, "name": tb.name}


@router.get("/textbooks/{textbook_id}")
async def get_textbook_detail(
    textbook_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin)
):
    """Get Textbook Detail"""
    tb = await db.get(Textbook, textbook_id)
    if not tb:
        raise HTTPException(status_code=404, detail="教材不存在")

    # For PDF textbooks, also return pages
    pages = []
    if tb.file_type == 'pdf':
        result = await db.execute(
            sql_text("""
                SELECT id, page_number as sort_order, image_url as url,
                       COALESCE(is_visible, true) as is_visible
                FROM textbook_pages
                WHERE textbook_id = :tid
                ORDER BY page_number
            """),
            {"tid": textbook_id}
        )
        rows = result.fetchall()
        pages = [
            {"id": r[0], "sort_order": r[1], "url": r[2], "is_visible": r[3]}
            for r in rows
        ]

    return {
        "id": tb.id, "name": tb.name, "description": tb.description,
        "total_chapters": tb.total_chapters, "total_pages": tb.total_pages,
        "has_pdf": tb.file_type == "pdf",
        "has_interactive": tb.has_interactive, "file_path": tb.file_path,
        "interactive_path": tb.interactive_path, "file_type": tb.file_type,
        "pages": pages
    }


@router.put("/textbooks/{textbook_id}")
async def update_textbook(
    textbook_id: int,
    name: str | None = Body(None),
    description: str | None = Body(None),
    total_chapters: int | None = Body(None),
    total_pages: int | None = Body(None),
    is_active: bool | None = Body(None),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin)
):
    """Update Textbook"""
    tb = await db.get(Textbook, textbook_id)
    if not tb:
        raise HTTPException(status_code=404, detail="教材不存在")
    if name is not None:
        tb.name = name
    if description is not None:
        tb.description = description
    if total_chapters is not None:
        tb.total_chapters = total_chapters
    if total_pages is not None:
        tb.total_pages = total_pages
    if is_active is not None:
        tb.is_active = is_active
    await db.commit()
    return {"success": True, "message": "教材已更新"}


@router.delete("/textbooks/{textbook_id}")
async def delete_textbook(
    textbook_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin)
):
    """Delete Textbook"""
    try:
        # 先清理所有关联表（按FK依赖顺序，从叶子到根）
        # 1. textbooks 的直接子表
        await db.execute(sql_text("DELETE FROM class_textbooks WHERE textbook_id = :tid"), {"tid": textbook_id})
        await db.execute(sql_text("DELETE FROM student_pdf_progress WHERE textbook_id = :tid"), {"tid": textbook_id})
        await db.execute(sql_text("DELETE FROM textbook_pages WHERE textbook_id = :tid"), {"tid": textbook_id})
        # 2. chapters 的子表（必须在 chapters 之前清理）
        await db.execute(sql_text("DELETE FROM chapter_progress WHERE chapter_id IN (SELECT id FROM chapters WHERE textbook_id = :tid)"), {"tid": textbook_id})
        await db.execute(sql_text("DELETE FROM chapter_exercises WHERE chapter_id IN (SELECT id FROM chapters WHERE textbook_id = :tid)"), {"tid": textbook_id})
        await db.execute(sql_text("DELETE FROM chapter_notes WHERE chapter_id IN (SELECT id FROM chapters WHERE textbook_id = :tid)"), {"tid": textbook_id})
        await db.execute(sql_text("DELETE FROM chapter_bookmarks WHERE chapter_id IN (SELECT id FROM chapters WHERE textbook_id = :tid)"), {"tid": textbook_id})
        # 3. 同时关联 textbooks + chapters 的表
        await db.execute(sql_text("DELETE FROM questions WHERE textbook_id = :tid"), {"tid": textbook_id})
        await db.execute(sql_text("DELETE FROM reading_progress WHERE textbook_id = :tid"), {"tid": textbook_id})
        # 4. chapters 自身
        await db.execute(sql_text("DELETE FROM chapters WHERE textbook_id = :tid"), {"tid": textbook_id})
        tb = await db.get(Textbook, textbook_id)
        if tb:
            await db.delete(tb)
        await db.commit()
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=f"删除失败：{str(e)}")
    return {"success": True, "message": "教材已删除"}


# ---- 章节管理 ----

@router.get("/textbooks/{textbook_id}/chapters")
async def list_textbook_chapters(
    textbook_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin)
):
    """List Textbook Chapters"""
    result = await db.execute(
        sql_text("""
            SELECT id, title, sort_order, parent_id, page_start, page_end
            FROM chapters WHERE textbook_id = :tid
            ORDER BY sort_order
        """),
        {"tid": textbook_id}
    )
    return [dict(r._mapping) for r in result.fetchall()]


@router.post("/textbooks/{textbook_id}/import")
async def import_textbook_content(
    textbook_id: int,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin)
):
    """Import Textbook Content"""
    tb = await db.get(Textbook, textbook_id)
    if not tb:
        raise HTTPException(status_code=404, detail="教材不存在")

    content = await file.read()

    # 保存源文件
    backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    src_dir = os.path.join(backend_dir, "static", "textbooks", str(textbook_id))
    os.makedirs(src_dir, exist_ok=True)
    src_path = os.path.join(src_dir, "source.docx")
    with open(src_path, 'wb') as f:
        f.write(content)

    # 更新数据库 file_path
    relative_path = f"static/textbooks/{textbook_id}/source.docx"
    tb.file_path = relative_path
    await db.commit()

    # 解析章节（直接解析 docx，不依赖 textbook_import.py 的端点签名）
    try:
        from io import BytesIO

        from docx import Document
        doc = Document(BytesIO(content))

        # 解析章节
        chapters_data = []
        current_chapter = None
        current_section = None
        chapter_count = 0

        for para in doc.paragraphs:
            para_text = para.text.strip()
            if not para_text:
                continue
            style_name = para.style.name if para.style else ""

            def is_chapter_title(text):
                skip_indicators = ['包括', '本节', '本章', '如下：', '如下列', '具体内容', '具体如下',
                                   '共分', '共为', '分别', '个部分', '个章节', '如下。']
                for skip in skip_indicators:
                    if skip in text:
                        return False
                import re
                patterns = [r'^第[一二三四五六七八九十百零\d]+[章篇部分]', r'^第[一二三四五六七八九十百零\d]+节',
                            r'^[单元][一二三四五六七八九十百零\d]+', r'^Unit\s*\d+', r'^Chapter\s*\d+',
                            r'^前言$', r'^目录$', r'^总体结论$']
                for p in patterns:
                    if re.match(p, text):
                        return True
                return False

            def is_section_title(text):
                import re
                patterns = [r'^\d+\.\d+', r'^[（(][一二三四五六七八九十\d]+[）)]']
                for p in patterns:
                    if re.match(p, text):
                        return True
                return False

            is_heading1 = style_name.startswith('Heading 1') or is_chapter_title(para_text)
            is_heading2 = style_name.startswith('Heading 2') or style_name.startswith('Heading 3') or is_section_title(para_text)

            if is_heading1:
                if current_chapter:
                    if current_section:
                        current_chapter['sections'].append(current_section)
                    chapters_data.append(current_chapter)
                current_chapter = {'title': para_text, 'sections': [], 'content_parts': []}
                current_section = None
                chapter_count += 1
            elif is_heading2 and current_chapter:
                if current_section:
                    current_chapter['sections'].append(current_section)
                current_section = {'title': para_text, 'content': ""}
            elif current_chapter:
                if current_section:
                    current_section['content'] += para_text + "\n\n"
                else:
                    current_chapter['content_parts'].append(para_text)

        if current_chapter:
            if current_section:
                current_chapter['sections'].append(current_section)
            chapters_data.append(current_chapter)

        # 清理旧章节
        await db.execute(sql_text("DELETE FROM chapters WHERE textbook_id = :tid"), {"tid": textbook_id})

        # 插入新章节
        for idx, ch in enumerate(chapters_data):
            chapter = Chapter(
                textbook_id=textbook_id, title=ch['title'],
                content="\n\n".join(ch.get('content_parts', [])),
                sort_order=idx + 1
            )
            db.add(chapter)
            await db.flush()
            parent_id = chapter.id
            for s_idx, sec in enumerate(ch.get('sections', [])):
                db.add(Chapter(
                    textbook_id=textbook_id, parent_id=parent_id, title=sec['title'],
                    content=sec.get('content', '') or f"## {sec['title']}\n\n本节内容见教材。",
                    sort_order=s_idx + 1
                ))

        tb.total_chapters = chapter_count
        tb.file_type = 'word'
        tb.import_status = 'success'
        await db.commit()
        return {"success": True, "message": f"成功导入 {chapter_count} 个章节", "chapter_count": chapter_count}
    except Exception as e:
        tb.import_status = 'failed'
        tb.import_error = str(e)
        await db.commit()
        raise HTTPException(status_code=500, detail=f"导入失败: {str(e)}")


# ---- PDF 上传 ----

@router.post("/textbooks/{textbook_id}/upload-pdf")
async def upload_textbook_pdf(
    textbook_id: int,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin)
):
    """Upload Textbook Pdf"""
    tb = await db.get(Textbook, textbook_id)
    if not tb:
        raise HTTPException(status_code=404, detail="教材不存在")

    content = await file.read()

    # 保存 PDF
    backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    pdf_dir = os.path.join(backend_dir, "static", "textbooks", str(textbook_id))
    os.makedirs(pdf_dir, exist_ok=True)
    pdf_path = os.path.join(pdf_dir, "textbook.pdf")
    with open(pdf_path, 'wb') as f:
        f.write(content)

    tb.file_type = 'pdf'
    tb.import_status = 'success'
    await db.commit()

    # ── 自动生成页面图片并写入 textbook_pages ─────────────────────────
    try:

        import fitz

        # 1. 清理旧记录
        await db.execute(
            sql_text("DELETE FROM textbook_pages WHERE textbook_id = :tid"),
            {"tid": textbook_id}
        )

        # 2. 删除旧图片
        for f in os.listdir(pdf_dir):
            if f.startswith('page_') and f.endswith('.jpg'):
                os.remove(os.path.join(pdf_dir, f))

        # 3. 转换 PDF → 图片
        doc = fitz.open(pdf_path)
        records = []
        for page_num in range(len(doc)):
            page = doc[page_num]
            mat = fitz.Matrix(2, 2)
            pix = page.get_pixmap(matrix=mat)
            img_name = f"page_{page_num + 1}.jpg"
            pix.save(os.path.join(pdf_dir, img_name))
            records.append((page_num + 1, f"/static/textbooks/{textbook_id}/{img_name}", 1, textbook_id))
        doc.close()

        # 4. 批量写入 textbook_pages
        await db.execute(
            sql_text("DELETE FROM textbook_pages WHERE textbook_id = :tid"),
            {"tid": textbook_id}
        )
        for r in records:
            await db.execute(
                sql_text("INSERT INTO textbook_pages (page_number, image_url, is_visible, textbook_id) VALUES (:pn, :url, :vis, :tid)"),
                {"pn": r[0], "url": r[1], "vis": r[2], "tid": r[3]}
            )

        tb.total_pages = len(records)
        await db.commit()
        logger.info(f"[upload-pdf] 生成 {len(records)} 张图片 for textbook_id={textbook_id}")
    except Exception as img_err:
        logger.warning(f"[upload-pdf] 图片生成失败（PDF转图片流程）: {img_err}")
    # ── END ─────────────────────────────────────────────────────────────

    return {"success": True, "message": "PDF已上传并生成页面图片", "file_type": "pdf", "import_status": "success", "pages_count": tb.total_pages}


# ---- 页面管理 ----

@router.get("/textbooks/{textbook_id}/pages")
async def get_textbook_pages(
    textbook_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin)
):
    """Get Textbook Pages"""
    result = await db.execute(
        sql_text("""
            SELECT id, textbook_id, page_number, image_url, is_visible
            FROM textbook_pages WHERE textbook_id = :tid ORDER BY page_number
        """),
        {"tid": textbook_id}
    )
    return [dict(r._mapping) for r in result.fetchall()]


@router.delete("/textbooks/{textbook_id}/pages")
async def delete_textbook_pages(
    textbook_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin)
):
    """Delete Textbook Pages"""
    await db.execute(sql_text("DELETE FROM textbook_pages WHERE textbook_id = :tid"), {"tid": textbook_id})
    await db.commit()
    return {"success": True}


@router.get("/textbooks/{textbook_id}/pages/management")
async def get_page_management(
    textbook_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin)
):
    """Get Page/Chapter Management - 智能读取 chapters 表（word/interactive）或 textbook_pages（pdf）"""
    tb = await db.get(Textbook, textbook_id)
    if not tb:
        raise HTTPException(status_code=404, detail="教材不存在")

    if tb.file_type == 'pdf':
        # PDF 模式：读取 textbook_pages（图片分页）
        result = await db.execute(
            sql_text("""
                SELECT id, page_number as sort_order, image_url as content, is_visible, 'page' as type
                FROM textbook_pages WHERE textbook_id = :tid ORDER BY page_number
            """),
            {"tid": textbook_id}
        )
        pages = [dict(r._mapping) for r in result.fetchall()]
    else:
        # Word / Interactive 模式：读取 chapters 表
        result = await db.execute(
            sql_text("""
                SELECT id, sort_order, title, content,
                       'chapter' as type
                FROM chapters
                WHERE textbook_id = :tid AND parent_id IS NULL
                ORDER BY sort_order
            """),
            {"tid": textbook_id}
        )
        chapters_list = [dict(r._mapping) for r in result.fetchall()]

        # 每个章节下附上其子节
        for ch in chapters_list:
            child_result = await db.execute(
                sql_text("""
                    SELECT id, sort_order, title, content,
                           'section' as type
                    FROM chapters
                    WHERE textbook_id = :tid AND parent_id = :pid
                    ORDER BY sort_order
                """),
                {"tid": textbook_id, "pid": ch['id']}
            )
            ch['children'] = [dict(r._mapping) for r in child_result.fetchall()]

        pages = chapters_list

    return {"pages": pages, "file_type": tb.file_type or "none", "textbook_name": tb.name}


@router.put("/textbooks/{textbook_id}/pages/visibility")
async def update_page_visibility(
    textbook_id: int,
    page_ids: list[int] = Body(...),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin)
):
    """Update Page/Chapter Visibility - 智能写入 chapters 表或 textbook_pages"""
    tb = await db.get(Textbook, textbook_id)
    if not tb:
        raise HTTPException(status_code=404, detail="教材不存在")

    if tb.file_type == 'pdf':
        # PDF 模式：写入 textbook_pages
        await db.execute(
            sql_text("UPDATE textbook_pages SET is_visible = 0 WHERE textbook_id = :tid"),
            {"tid": textbook_id}
        )
        for pid in page_ids:
            await db.execute(
                sql_text("UPDATE textbook_pages SET is_visible = 1 WHERE id = :id AND textbook_id = :tid"),
                {"id": pid, "tid": textbook_id}
            )
    else:
        # Word / Interactive 模式：写入 chapters 表
        await db.execute(
            sql_text("UPDATE chapters SET is_visible = 0 WHERE textbook_id = :tid"),
            {"tid": textbook_id}
        )
        for pid in page_ids:
            await db.execute(
                sql_text("UPDATE chapters SET is_visible = 1 WHERE id = :id AND textbook_id = :tid"),
                {"id": pid, "tid": textbook_id}
            )

    await db.commit()
    return {"success": True}


# ---- 文档恢复 ----

@router.post("/textbooks/{textbook_id}/restore-document")
async def restore_textbook_to_document(
    textbook_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin)
):
    """Restore Textbook To Document"""
    tb = await db.get(Textbook, textbook_id)
    if not tb:
        raise HTTPException(status_code=404, detail="教材不存在")

    if tb.file_path:
        backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        doc_path = tb.file_path if os.path.isabs(tb.file_path) else os.path.join(backend_dir, tb.file_path)
        if os.path.exists(doc_path):
            with open(doc_path, 'rb') as f:
                content = f.read()

            # 重新导入
            from app.api.textbook_import import import_textbook_content as do_import
            try:
                result = await do_import(textbook_id, content, db)
                # import_textbook_content 返回字典，提取章节计数
                if isinstance(result, dict):
                    chapter_count = result.get('chapters_count', result.get('chapter_count', 0))
                else:
                    chapter_count = result
                tb.total_chapters = chapter_count
                await db.commit()
                return {"success": True, "message": f"文档已恢复，共 {chapter_count} 个章节"}
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"恢复失败: {str(e)}")

    raise HTTPException(status_code=404, detail="未找到源文档")


# ---- AI 增强功能 ----

@router.get("/textbooks/{textbook_id}/ai-structure")
async def get_ai_textbook_structure(
    textbook_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin)
):
    """Get Ai Textbook Structure"""
    # 读取互动式数据
    interactive_path = os.path.join(settings.INTERACTIVE_DATA_DIR, f"{textbook_id}_interactive.json")
    if not os.path.exists(interactive_path):
        raise HTTPException(status_code=404, detail="互动式数据不存在")

    with open(interactive_path) as f:
        data = json.load(f)

    return {
        "textbook_id": textbook_id,
        "title": data.get("title", ""),
        "total_sections": data.get("total_sections", 0),
        "sections": [
            {"id": s.get("id", ""), "title": s.get("title", ""), "level": s.get("level", 1)}
            for s in data.get("sections", [])
        ]
    }


@router.get("/textbooks/{textbook_id}/ai-glossary")
async def get_ai_textbook_glossary(
    textbook_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin)
):
    """Get Ai Textbook Glossary"""
    try:
        interactive_path = os.path.join(settings.INTERACTIVE_DATA_DIR, f"{textbook_id}_interactive.json")
        if not os.path.exists(interactive_path):
            return []

        with open(interactive_path) as f:
            data = json.load(f)

        glossary = []
        for kp_id, kp_data in data.get("key_concepts_map", {}).items():
            glossary.append({"id": kp_id, "name": kp_data.get("name", ""), "description": kp_data.get("description", "")})

        return glossary
    except Exception as e:
        logger.error(f"[ai-glossary] textbook_id={textbook_id} 错误: {e}")
        return []


@router.get("/textbooks/{textbook_id}/ai-glossary/{kp_id}")
async def get_ai_glossary_detail(
    textbook_id: int,
    kp_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin)
):
    """Get Ai Glossary Detail"""
    interactive_path = os.path.join(settings.INTERACTIVE_DATA_DIR, f"{textbook_id}_interactive.json")
    if not os.path.exists(interactive_path):
        raise HTTPException(status_code=404, detail="互动式数据不存在")

    with open(interactive_path) as f:
        data = json.load(f)

    kp_data = data.get("key_concepts_map", {}).get(kp_id, {})
    if not kp_data:
        raise HTTPException(status_code=404, detail="知识点不存在")

    return kp_data


@router.get("/textbooks/{textbook_id}/ai-page/{page_id}")
async def get_ai_textbook_page(
    textbook_id: int,
    page_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin)
):
    """Get Ai Textbook Page"""
    interactive_path = os.path.join(settings.INTERACTIVE_DATA_DIR, f"{textbook_id}_interactive.json")
    if not os.path.exists(interactive_path):
        raise HTTPException(status_code=404, detail="互动式数据不存在")

    with open(interactive_path) as f:
        data = json.load(f)

    # 查找对应章节
    for section in data.get("sections", []):
        if section.get("id") == page_id:
            return {
                "id": section.get("id"),
                "title": section.get("title"),
                "level": section.get("level", 1),
                "units": section.get("units", []),
                "estimated_time": section.get("estimated_time", 10)
            }

    raise HTTPException(status_code=404, detail="页面不存在")


@router.post("/textbooks/ai-regenerate")
async def regenerate_ai_textbook(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin)
):
    """Regenerate Ai Textbook"""
    return {"success": True, "message": "AI生成功能待实现"}


# ---- 互动式教材 CRUD ----

@router.get("/textbooks/interactive")
async def list_all_interactive_textbooks(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin)
):
    """List All Interactive Textbooks"""
    result = await db.execute(
        sql_text("""
            SELECT id, name, total_chapters, has_interactive
            FROM textbooks WHERE has_interactive IS TRUE
            ORDER BY id DESC
        """)
    )
    return [dict(r._mapping) for r in result.fetchall()]


@router.get("/textbooks/{textbook_id}/interactive")
async def get_interactive_textbook(
    textbook_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin)
):
    """Get Interactive Textbook"""
    interactive_path = os.path.join(settings.INTERACTIVE_DATA_DIR, f"{textbook_id}_interactive.json")
    if not os.path.exists(interactive_path):
        raise HTTPException(status_code=404, detail="互动式数据不存在，请先点击「重新转换」")

    with open(interactive_path) as f:
        data = json.load(f)

    return data


@router.get("/textbooks/{textbook_id}/interactive/structure")
async def get_interactive_structure(
    textbook_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin)
):
    """Get Interactive Structure"""
    interactive_path = os.path.join(settings.INTERACTIVE_DATA_DIR, f"{textbook_id}_interactive.json")
    if not os.path.exists(interactive_path):
        raise HTTPException(status_code=404, detail="互动式数据不存在")

    with open(interactive_path) as f:
        data = json.load(f)

    return {
        "id": data.get("id"),
        "title": data.get("title"),
        "total_sections": data.get("total_sections"),
        "sections": [
            {
                "id": s.get("id"),
                "title": s.get("title"),
                "level": s.get("level", 1),
                "estimated_time": s.get("estimated_time", 10)
            }
            for s in data.get("sections", [])
        ]
    }


@router.get("/textbooks/{textbook_id}/interactive/history")
async def get_interactive_history(
    textbook_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin)
):
    """Get Interactive History"""
    # 返回当前版本的元数据
    interactive_path = os.path.join(settings.INTERACTIVE_DATA_DIR, f"{textbook_id}_interactive.json")
    if os.path.exists(interactive_path):
        stat = os.stat(interactive_path)
        import time
        return {
            "textbook_id": textbook_id,
            "version": 1,
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(stat.st_mtime)),
            "size": stat.st_size
        }
    return {}


# ---- ★★★ 核心：转换互动式教材（已修复） ----

@router.post("/textbooks/{textbook_id}/convert-interactive")
async def convert_textbook_to_interactive(
    textbook_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin)
):
    """Convert Textbook To Interactive"""
    tb = await db.get(Textbook, textbook_id)
    if not tb:
        raise HTTPException(status_code=404, detail="教材不存在")

    # ★★★ 修复：直接用数据库记录的 file_path（上传时已正确设置）
    docx_path = None

    if tb.file_path:
        backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        candidate = tb.file_path if os.path.isabs(tb.file_path) else os.path.join(backend_dir, tb.file_path)
        if os.path.exists(candidate):
            docx_path = candidate
            logger.info(f"[convert-interactive] 使用数据库 file_path: {docx_path}")

    # 兜底：直接在 static/textbooks/{id}/source.docx
    if not docx_path:
        backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        fallback = os.path.join(backend_dir, "static", "textbooks", str(textbook_id), "source.docx")
        if os.path.exists(fallback):
            docx_path = fallback
            logger.info(f"[convert-interactive] 使用兜底路径: {docx_path}")

    if not docx_path:
        raise HTTPException(status_code=404, detail=f"未找到教材文件: {tb.file_path}")

    try:
        # 使用增强版转换器
        converter = EnhancedAIConverter(docx_path)
        interactive_data = converter.convert()

        # 保存 JSON 文件
        output_dir = settings.INTERACTIVE_DATA_DIR
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, f"{textbook_id}_interactive.json")
        converter.save_json(output_path)

        # 更新数据库
        tb.file_type = 'interactive'
        tb.has_interactive = True
        tb.interactive_path = output_path
        await db.commit()

        return {
            "success": True,
            "message": f"转换成功！共生成 {interactive_data.total_sections} 个章节",
            "textbook_id": textbook_id,
            "title": interactive_data.title,
            "total_sections": interactive_data.total_sections,
            "key_concepts_count": len(interactive_data.key_concepts_map),
            "sections_preview": [s.title for s in interactive_data.sections[:5]]
        }
    except Exception as e:
        logger.error(f"[convert-interactive] 转换失败: {e}")
        raise HTTPException(status_code=500, detail=f"转换失败: {str(e)}")


@router.post("/textbooks/{textbook_id}/interactive/redo")
async def redo_interactive(
    textbook_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin)
):
    """Redo Interactive"""
    # 直接复用 convert-interactive 逻辑
    return await convert_textbook_to_interactive(textbook_id, db, user)


@router.post("/textbooks/{textbook_id}/interactive/undo")
async def undo_interactive(
    textbook_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin)
):
    """Undo Interactive"""
    return {"success": True, "message": "撤销功能待实现"}


# ---- 互动式章节编辑 ----

@router.put("/textbooks/{textbook_id}/interactive/sections/{section_id}")
async def update_interactive_section(
    textbook_id: int,
    section_id: str,
    title: str | None = Body(None),
    content: str | None = Body(None),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin)
):
    """Update Interactive Section"""
    interactive_path = os.path.join(settings.INTERACTIVE_DATA_DIR, f"{textbook_id}_interactive.json")
    if not os.path.exists(interactive_path):
        raise HTTPException(status_code=404, detail="互动式数据不存在")

    with open(interactive_path) as f:
        data = json.load(f)

    for section in data.get("sections", []):
        if section.get("id") == section_id:
            if title is not None:
                section["title"] = title
            if content is not None:
                section["content"] = content
            break

    with open(interactive_path, 'w') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    return {"success": True}


@router.delete("/textbooks/{textbook_id}/interactive/sections/{section_id}")
async def delete_interactive_section(
    textbook_id: int,
    section_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin)
):
    """Delete Interactive Section"""
    interactive_path = os.path.join(settings.INTERACTIVE_DATA_DIR, f"{textbook_id}_interactive.json")
    if not os.path.exists(interactive_path):
        raise HTTPException(status_code=404, detail="互动式数据不存在")

    with open(interactive_path) as f:
        data = json.load(f)

    data["sections"] = [s for s in data.get("sections", []) if s.get("id") != section_id]
    data["total_sections"] = len(data["sections"])

    with open(interactive_path, 'w') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    return {"success": True}


@router.post("/textbooks/{textbook_id}/interactive/sections/{section_id}/hide")
async def hide_interactive_section(
    textbook_id: int,
    section_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin)
):
    """Hide Interactive Section"""
    interactive_path = os.path.join(settings.INTERACTIVE_DATA_DIR, f"{textbook_id}_interactive.json")
    if not os.path.exists(interactive_path):
        raise HTTPException(status_code=404, detail="互动式数据不存在")

    with open(interactive_path) as f:
        data = json.load(f)

    for section in data.get("sections", []):
        if section.get("id") == section_id:
            section["is_hidden"] = True
            break

    with open(interactive_path, 'w') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    return {"success": True}


@router.post("/textbooks/{textbook_id}/interactive/sections/{section_id}/unhide")
async def unhide_interactive_section(
    textbook_id: int,
    section_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin)
):
    """Unhide Interactive Section"""
    interactive_path = os.path.join(settings.INTERACTIVE_DATA_DIR, f"{textbook_id}_interactive.json")
    if not os.path.exists(interactive_path):
        raise HTTPException(status_code=404, detail="互动式数据不存在")

    with open(interactive_path) as f:
        data = json.load(f)

    for section in data.get("sections", []):
        if section.get("id") == section_id:
            section["is_hidden"] = False
            break

    with open(interactive_path, 'w') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    return {"success": True}


# ---- 互动式章节拆分合并 ----

@router.post("/textbooks/{textbook_id}/interactive/sections/split")
async def split_interactive_section(
    textbook_id: int,
    section_id: str = Body(...),
    upper_content: str | None = Body(None),
    lower_content: str | None = Body(None),
    upper_title: str | None = Body(None),
    lower_title: str | None = Body(None),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin)
):
    """Split Interactive Section"""
    interactive_path = os.path.join(settings.INTERACTIVE_DATA_DIR, f"{textbook_id}_interactive.json")
    if not os.path.exists(interactive_path):
        raise HTTPException(status_code=404, detail="互动式数据不存在")

    with open(interactive_path) as f:
        data = json.load(f)

    # 找到要拆分的章节
    sections = data.get("sections", [])
    split_idx = None
    for i, s in enumerate(sections):
        if s.get("id") == section_id:
            split_idx = i
            break

    if split_idx is None:
        raise HTTPException(status_code=404, detail="章节不存在")

    import uuid
    # 创建下半部分章节
    new_section = {
        "id": f"section_{uuid.uuid4().hex[:8]}",
        "title": lower_title or (sections[split_idx].get("title", "") + "（续）"),
        "level": sections[split_idx].get("level", 2),
        "units": [],
        "estimated_time": 5,
        "key_concepts": []
    }

    sections.insert(split_idx + 1, new_section)
    data["sections"] = sections
    data["total_sections"] = len(sections)

    with open(interactive_path, 'w') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    return {"success": True, "new_section_id": new_section["id"]}


@router.post("/textbooks/{textbook_id}/interactive/sections/merge")
async def merge_interactive_sections(
    textbook_id: int,
    section_ids: list[str] = Body(...),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin)
):
    """Merge Interactive Sections"""
    if len(section_ids) < 2:
        raise HTTPException(status_code=400, detail="至少选择2个章节才能合并")

    interactive_path = os.path.join(settings.INTERACTIVE_DATA_DIR, f"{textbook_id}_interactive.json")
    if not os.path.exists(interactive_path):
        raise HTTPException(status_code=404, detail="互动式数据不存在")

    with open(interactive_path) as f:
        data = json.load(f)

    sections = data.get("sections", [])
    to_merge = [s for s in sections if s.get("id") in section_ids]

    if len(to_merge) < 2:
        raise HTTPException(status_code=404, detail="未找到要合并的章节")

    # 合并为第一个章节
    merged = to_merge[0]
    for s in to_merge[1:]:
        merged["units"] = (merged.get("units", []) or []) + (s.get("units", []) or [])
        sections = [s2 for s2 in sections if s2.get("id") != s.get("id")]

    data["sections"] = sections
    data["total_sections"] = len(sections)

    with open(interactive_path, 'w') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    return {"success": True}


@router.post("/textbooks/{textbook_id}/interactive/sections/reorder")
async def reorder_interactive_sections(
    textbook_id: int,
    section_ids: list[str] = Body(...),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin)
):
    """Reorder Interactive Sections"""
    interactive_path = os.path.join(settings.INTERACTIVE_DATA_DIR, f"{textbook_id}_interactive.json")
    if not os.path.exists(interactive_path):
        raise HTTPException(status_code=404, detail="互动式数据不存在")

    with open(interactive_path) as f:
        data = json.load(f)

    # 按新顺序重新排列
    sections = data.get("sections", [])
    sections_map = {s.get("id"): s for s in sections}
    new_order = [sections_map.get(sid) for sid in section_ids if sid in sections_map]
    new_order = [s for s in new_order if s is not None]

    data["sections"] = new_order
    data["total_sections"] = len(new_order)

    with open(interactive_path, 'w') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    return {"success": True}


# ---- 单元编辑 ----

@router.put("/textbooks/{textbook_id}/interactive/sections/{section_id}/units/{unit_id}")
async def update_interactive_unit(
    textbook_id: int,
    section_id: str,
    unit_id: str,
    content: str = Body(...),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin)
):
    """Update Interactive Unit"""
    interactive_path = os.path.join(settings.INTERACTIVE_DATA_DIR, f"{textbook_id}_interactive.json")
    if not os.path.exists(interactive_path):
        raise HTTPException(status_code=404, detail="互动式数据不存在")

    with open(interactive_path) as f:
        data = json.load(f)

    for section in data.get("sections", []):
        if section.get("id") == section_id:
            for unit in section.get("units", []):
                if unit.get("id") == unit_id:
                    unit["content"] = content
                    break
            break

    with open(interactive_path, 'w') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    return {"success": True}


@router.delete("/textbooks/{textbook_id}/interactive/units/{unit_id}")
async def delete_interactive_unit(
    textbook_id: int,
    unit_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin)
):
    """Delete Interactive Unit"""
    interactive_path = os.path.join(settings.INTERACTIVE_DATA_DIR, f"{textbook_id}_interactive.json")
    if not os.path.exists(interactive_path):
        raise HTTPException(status_code=404, detail="互动式数据不存在")

    with open(interactive_path) as f:
        data = json.load(f)

    for section in data.get("sections", []):
        section["units"] = [u for u in section.get("units", []) if u.get("id") != unit_id]

    with open(interactive_path, 'w') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    return {"success": True}


@router.post("/textbooks/{textbook_id}/interactive/units/{unit_id}/hide")
async def hide_interactive_unit(
    textbook_id: int,
    unit_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin)
):
    """Hide Interactive Unit"""
    interactive_path = os.path.join(settings.INTERACTIVE_DATA_DIR, f"{textbook_id}_interactive.json")
    if not os.path.exists(interactive_path):
        raise HTTPException(status_code=404, detail="互动式数据不存在")

    with open(interactive_path) as f:
        data = json.load(f)

    for section in data.get("sections", []):
        for unit in section.get("units", []):
            if unit.get("id") == unit_id:
                unit["is_hidden"] = True
                break

    with open(interactive_path, 'w') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    return {"success": True}


@router.post("/textbooks/{textbook_id}/interactive/units/{unit_id}/unhide")
async def unhide_interactive_unit(
    textbook_id: int,
    unit_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin)
):
    """Unhide Interactive Unit"""
    interactive_path = os.path.join(settings.INTERACTIVE_DATA_DIR, f"{textbook_id}_interactive.json")
    if not os.path.exists(interactive_path):
        raise HTTPException(status_code=404, detail="互动式数据不存在")

    with open(interactive_path) as f:
        data = json.load(f)

    for section in data.get("sections", []):
        for unit in section.get("units", []):
            if unit.get("id") == unit_id:
                unit["is_hidden"] = False
                break

    with open(interactive_path, 'w') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    return {"success": True}


@router.post("/textbooks/{textbook_id}/interactive/units/delete")
async def delete_interactive_units_batch(
    textbook_id: int,
    unit_ids: list[str] = Body(...),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin)
):
    """Delete Interactive Units Batch"""
    interactive_path = os.path.join(settings.INTERACTIVE_DATA_DIR, f"{textbook_id}_interactive.json")
    if not os.path.exists(interactive_path):
        raise HTTPException(status_code=404, detail="互动式数据不存在")

    with open(interactive_path) as f:
        data = json.load(f)

    for section in data.get("sections", []):
        section["units"] = [u for u in section.get("units", []) if u.get("id") not in unit_ids]

    with open(interactive_path, 'w') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    return {"success": True, "deleted": len(unit_ids)}


@router.post("/textbooks/{textbook_id}/interactive/units/merge")
async def merge_interactive_units(
    textbook_id: int,
    unit_ids: list[str] = Body(...),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin)
):
    """Merge Interactive Units"""
    if len(unit_ids) < 2:
        raise HTTPException(status_code=400, detail="至少选择2个单元才能合并")

    interactive_path = os.path.join(settings.INTERACTIVE_DATA_DIR, f"{textbook_id}_interactive.json")
    if not os.path.exists(interactive_path):
        raise HTTPException(status_code=404, detail="互动式数据不存在")

    with open(interactive_path) as f:
        data = json.load(f)

    merged_content = ""
    for section in data.get("sections", []):
        for unit in section.get("units", []):
            if unit.get("id") in unit_ids:
                merged_content += unit.get("content", "") + "\n\n"
                section["units"] = [u for u in section.get("units", []) if u.get("id") != unit.get("id")]

    if section.get("units"):
        section["units"][-1]["content"] = merged_content.strip()
    else:
        section["units"].append({
            "id": unit_ids[0],
            "type": "paragraph",
            "content": merged_content.strip()
        })

    with open(interactive_path, 'w') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    return {"success": True}

