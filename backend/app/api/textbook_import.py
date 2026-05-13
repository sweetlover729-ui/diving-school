"""教材导入API - 解析Word文档导入章节内容"""
import io
import re

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import text as sql_text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.admin.shared import require_admin
from app.core.database import get_db
from app.models.class_system import Chapter, Textbook

router = APIRouter(prefix="/admin/textbooks", tags=["管理员教材导入"])


def is_chapter_title(text):
    """判断是否是章节标题（严格版）"""
    # 排除含有说明文字的段落
    skip_indicators = ['包括', '本节', '本章', '如下：', '如下列', '具体内容', '具体如下',
                       '共分', '共为', '分别', '个部分', '个章节', '如下：', '如下', '如下。']
    for skip in skip_indicators:
        if skip in text:
            return False

    # 阿拉伯数字编号：必须2位以上（11. xxx 才算章节，1. xxx 是列表项）
    arabic_pattern = r'^\d{2,}[.、]\s*[\u4e00-\u9fa5A-Za-z]'

    # 中文数字编号：必须2+个中文数字字符（排除"1、"这种阿拉伯数字）
    # 匹配：一、二、三...（单字符），十一、十二...（多字符）
    chinese_num_pattern = r'^[一二三四五六七八九十百零][、.]\s*[\u4e00-\u9fa5]'

    patterns = [
        r'^第[一二三四五六七八九十百零\d]+[章篇部分]',
        r'^第[一二三四五六七八九十百零\d]+节',
        r'^[单元][一二三四五六七八九十百零\d]+',
        r'^Unit\s*\d+',
        r'^Chapter\s*\d+',
        r'^前言$',
        r'^目录$',
        r'^总体结论$',
        r'^第[一二三四五六七八九十百零\d]+[、\s]',
        chinese_num_pattern,
        arabic_pattern,
    ]
    for p in patterns:
        if re.match(p, text):
            return True
    return False


def is_section_title(text):
    """判断是否是小节（二级标题），在一级章节之后"""
    patterns = [
        r'^\d+\.\d+[.\s]',    # 1.1 小节（阿拉伯数字小节）
        r'^\d+\.\d+[.、\u4e00-\u9fa5]',  # 1.1中文
        r'^[（(][一二三四五六七八九十\d]+[）)]',  # （一）（二）
        r'^\d+\.\d+\.\d+',    # 1.1.1 子小节
    ]
    for p in patterns:
        if re.match(p, text):
            return True
    return False


@router.post("/{textbook_id}/import")
async def import_textbook_content(
    textbook_id: int,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    user = Depends(require_admin)
):
    """导入Word文档作为教材章节内容"""
    textbook = await db.get(Textbook, textbook_id)
    if not textbook:
        raise HTTPException(status_code=404, detail="教材不存在")

    # 兼容：支持 UploadFile 对象（有 filename 属性）或直接传 bytes
    if hasattr(file, 'filename'):
        if not file.filename.endswith('.docx'):
            raise HTTPException(status_code=400, detail="只支持.docx格式")
        content = await file.read()
    else:
        # file 是 bytes（从 admin.py 直接调用时）
        content = file

    # 设置导入状态为处理中
    textbook.import_status = 'processing'
    textbook.import_error = None
    await db.commit()

    try:
        from docx import Document
        doc = Document(io.BytesIO(content))
    except Exception as e:
        error_msg = f"无法解析Word文档: {str(e)}"
        textbook.import_status = 'failed'
        textbook.import_error = error_msg
        await db.commit()
        raise HTTPException(status_code=400, detail=error_msg)

    try:
        # 解析文档结构
        chapters_data = []
        current_chapter = None
        current_section = None
        chapter_count = 0
        section_count = 0

        for para in doc.paragraphs:
            para_text = para.text.strip()
            if not para_text:
                continue

            style_name = para.style.name if para.style else ""

            # 判断标题级别
            is_heading1 = style_name.startswith('Heading 1') or is_chapter_title(para_text)
            is_heading2 = style_name.startswith('Heading 2') or style_name.startswith('Heading 3') or is_section_title(para_text)

            if is_heading1:
                # 保存上一章节
                if current_chapter:
                    if current_section:
                        current_chapter['sections'].append(current_section)
                    chapters_data.append(current_chapter)

                current_chapter = {
                    'title': para_text.replace('**', ''),
                    'sections': [],
                    'content_parts': []
                }
                current_section = None
                chapter_count += 1

            elif is_heading2 and current_chapter:
                # 保存上一小节
                if current_section:
                    current_chapter['sections'].append(current_section)

                current_section = {
                    'title': para_text.replace('**', ''),
                    'content': ""
                }
                section_count += 1

            elif current_chapter:
                # 添加内容
                if current_section:
                    current_section['content'] += para_text + "\n\n"
                else:
                    current_chapter['content_parts'].append(para_text)

        # 保存最后一个章节
        if current_chapter:
            if current_section:
                current_chapter['sections'].append(current_section)
            chapters_data.append(current_chapter)

        # 清理旧章节
        await db.execute(sql_text("DELETE FROM chapters WHERE textbook_id = :tid"), {"tid": textbook_id})

        # 导入章节
        for idx, ch in enumerate(chapters_data):
            chapter = Chapter(
                textbook_id=textbook_id,
                title=ch['title'],
                content="\n\n".join(ch.get('content_parts', [])),
                sort_order=idx + 1,
                page_start=idx * 12 + 1,
                page_end=(idx + 1) * 12
            )
            db.add(chapter)
            await db.flush()

            parent_id = chapter.id

            for s_idx, section in enumerate(ch.get('sections', [])):
                sec = Chapter(
                    textbook_id=textbook_id,
                    parent_id=parent_id,
                    title=section['title'],
                    content=section.get('content', '') or f"## {section['title']}\n\n本节内容见教材。",
                    sort_order=s_idx + 1,
                    page_start=idx * 12 + s_idx + 1,
                    page_end=idx * 12 + s_idx + 1
                )
                db.add(sec)

        textbook.total_chapters = chapter_count
        textbook.file_type = 'word'
        # 保存原始文件
        from pathlib import Path
        upload_dir = Path("static/textbooks") / str(textbook_id)
        upload_dir.mkdir(parents=True, exist_ok=True)
        docx_path = upload_dir / "source.docx"
        with open(docx_path, 'wb') as f:
            f.write(content)
        textbook.file_path = str(docx_path)
        # 设置导入状态为成功
        textbook.import_status = 'success'
        textbook.import_error = None
        await db.commit()

        return {
            "success": True,
            "message": f"成功导入 {chapter_count} 个章节，{section_count} 个小节",
            "chapters_count": chapter_count,
            "sections_count": section_count
        }
    except Exception as e:
        error_msg = f"导入失败: {str(e)}"
        textbook.import_status = 'failed'
        textbook.import_error = error_msg
        await db.commit()
        raise HTTPException(status_code=500, detail=error_msg)
