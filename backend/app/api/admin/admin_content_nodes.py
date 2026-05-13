"""
Admin API - Content Nodes Management
CRUD + tree query + LLM-assisted parsing trigger
"""
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.admin.shared import require_admin
from app.core.database import get_db
from app.models.class_system import ContentNode, Textbook

logger = logging.getLogger(__name__)
import json

router = APIRouter(prefix="/content-nodes", tags=["Content Nodes"])

# ============ Schemas ============

class ContentNodeCreate(BaseModel):
    textbook_id: int = Field(..., gt=0)
    title: str = Field(..., min_length=1, max_length=500)
    node_type: str = "section"
    content: str | None = None
    summary: str | None = None
    level: int = 0
    sort_order: int = 0
    parent_id: int | None = None
    page_start: int | None = None
    page_end: int | None = None
    difficulty_level: str | None = "beginner"
    learning_objectives: str | None = "[]"
    tags: str | None = "[]"
    key_concepts: str | None = "[]"
    source_location: str | None = None
    is_visible: bool | None = True

class ContentNodeUpdate(BaseModel):
    title: str | None = None
    node_type: str | None = None
    content: str | None = None
    summary: str | None = None
    level: int | None = None
    sort_order: int | None = None
    parent_id: int | None = None
    page_start: int | None = None
    page_end: int | None = None
    difficulty_level: str | None = None
    learning_objectives: str | None = None
    tags: str | None = None
    key_concepts: str | None = None
    source_location: str | None = None
    is_visible: bool | None = None
    review_status: str | None = None

class ContentNodeResponse(BaseModel):
    id: int
    textbook_id: int
    title: str
    node_type: str | None
    content_raw: str | None
    summary: str | None
    level: int
    sort_order: int
    parent_id: int | None
    page_start: int | None
    page_end: int | None
    difficulty_level: str | None
    learning_objectives: str | None
    tags: str | None
    key_concepts: str | None
    source_location: str | None
    is_visible: bool
    review_status: str | None
    content_hash: str | None
    created_at: str | None
    updated_at: str | None
    children_count: int = 0

    class Config:
        from_attributes = True

# ============ Endpoints ============

@router.get("", response_model=list[ContentNodeResponse])
async def list_content_nodes(
    textbook_id: int | None = Query(None),
    parent_id: int | None = Query(None),
    node_type: str | None = Query(None),
    is_visible: bool | None = Query(None),
    limit: int = Query(100, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(require_admin),
):
    stmt = select(ContentNode)
    if textbook_id:
        stmt = stmt.where(ContentNode.textbook_id == textbook_id)
    if parent_id is not None:
        stmt = stmt.where(ContentNode.parent_id == parent_id)
    elif textbook_id:
        # Default: show root nodes only when filtering by textbook
        stmt = stmt.where(ContentNode.parent_id == None)
    if node_type:
        stmt = stmt.where(ContentNode.node_type == node_type)
    if is_visible is not None:
        stmt = stmt.where(ContentNode.is_visible == is_visible)
    stmt = stmt.order_by(ContentNode.sort_order, ContentNode.id).offset(offset).limit(limit)
    result = await db.execute(stmt)
    nodes = result.scalars().all()
    out = []
    for n in nodes:
        child_count = await db.execute(
            select(ContentNode).where(ContentNode.parent_id == n.id)
        )
        out.append(_node_to_response(n, len(child_count.scalars().all())))
    return out

@router.get("/tree/{textbook_id}", response_model=list[ContentNodeResponse])
async def get_content_tree(
    textbook_id: int,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(require_admin),
):
    """Get full content tree for a textbook"""
    result = await db.execute(
        select(ContentNode)
        .where(ContentNode.textbook_id == textbook_id)
        .order_by(ContentNode.sort_order, ContentNode.id)
    )
    all_nodes = result.scalars().all()
    # Build tree
    node_map = {}
    for n in all_nodes:
        node_map[n.id] = _node_to_response(n, 0)
    # Count children
    for n in all_nodes:
        if n.parent_id and n.parent_id in node_map:
            node_map[n.parent_id]["children_count"] += 1
    # Return root nodes (parent_id is None)
    roots = [node_map[n.id] for n in all_nodes if n.parent_id is None]
    return roots

@router.get("/{node_id}", response_model=ContentNodeResponse)
async def get_content_node(
    node_id: int,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(require_admin),
):
    result = await db.execute(select(ContentNode).where(ContentNode.id == node_id))
    node = result.scalar()
    if not node:
        raise HTTPException(status_code=404, detail="Content node not found")
    return _node_to_response(node, 0)

@router.post("", response_model=ContentNodeResponse)
async def create_content_node(
    data: ContentNodeCreate,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(require_admin),
):
    # Verify textbook exists
    tb = await db.execute(select(Textbook).where(Textbook.id == data.textbook_id))
    if not tb.scalar():
        raise HTTPException(status_code=400, detail="Textbook not found")
    node = ContentNode(
        textbook_id=data.textbook_id,
        title=data.title,
        node_type=data.node_type,
        content=data.content,
        depth=data.level,
        sort_order=data.sort_order,
        parent_id=data.parent_id,
        page_start=data.page_start,
        page_end=data.page_end,
        difficulty_level=data.difficulty_level,
        learning_objectives=data.learning_objectives,
        tags=data.tags,
        source_location=data.source_location,
        is_visible=data.is_visible if data.is_visible is not None else True,
        review_status="pending",
    )
    db.add(node)
    await db.commit()
    await db.refresh(node)
    return _node_to_response(node, 0)

@router.put("/{node_id}", response_model=ContentNodeResponse)
async def update_content_node(
    node_id: int,
    data: ContentNodeUpdate,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(require_admin),
):
    result = await db.execute(select(ContentNode).where(ContentNode.id == node_id))
    node = result.scalar()
    if not node:
        raise HTTPException(status_code=404, detail="Content node not found")
    # Map schema field names to model column names
    field_map = {
        "node_type": "node_type",
        "content": "content",  # schema field -> model column
        "title": "title",
        "level": "depth",
        "sort_order": "sort_order",
        "parent_id": "parent_id",
        "page_start": "page_start",
        "page_end": "page_end",
        "difficulty_level": "difficulty_level",
        "learning_objectives": "learning_objectives",
        "tags": "keywords",  # schema field -> model column
        "source_location": "source_location",
        "is_visible": "is_visible",
        "review_status": "review_status",
    }
    update_data = data.model_dump(exclude_unset=True)
    for schema_key, value in update_data.items():
        if schema_key in field_map:
            model_key = field_map[schema_key]
            if value is not None or model_key not in ("content_raw",):
                setattr(node, model_key, value)
    node.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
    await db.commit()
    await db.refresh(node)
    return _node_to_response(node, 0)

@router.delete("/{node_id}")
async def delete_content_node(
    node_id: int,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(require_admin),
):
    result = await db.execute(select(ContentNode).where(ContentNode.id == node_id))
    node = result.scalar()
    if not node:
        raise HTTPException(status_code=404, detail="Content node not found")
    # Cascade delete children
    await _delete_children(db, node_id)
    await db.delete(node)
    await db.commit()
    return {"success": True, "message": "Content node deleted"}

@router.post("/parse/{textbook_id}")
async def trigger_parse(
    textbook_id: int,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(require_admin),
):
    """Trigger LLM-assisted parsing for a textbook"""
    result = await db.execute(select(Textbook).where(Textbook.id == textbook_id))
    textbook = result.scalar()
    if not textbook:
        raise HTTPException(status_code=404, detail="Textbook not found")
    if not textbook.file_path:
        raise HTTPException(status_code=400, detail="Textbook has no source file")
    background_tasks.add_task(_run_parse, textbook_id, textbook.file_path)
    return {"success": True, "message": "Parsing started in background"}

# ============ Helpers ============

def _node_to_response(node, children_count: int = 0) -> dict:
    # Map ContentNode model attributes to ContentNodeResponse schema fields
    # Model: node_type, content, depth, keywords (NOT level/tags/summary/key_concepts)
    lo = node.learning_objectives
    if isinstance(lo, (list, dict)):
        import json
        lo = json.dumps(lo)
    return {
        "id": node.id,
        "textbook_id": node.textbook_id,
        "title": node.title,
        "node_type": node.node_type,
        "content_raw": getattr(node, "content", None),
        "summary": None,
        "level": getattr(node, "depth", 0),
        "sort_order": node.sort_order,
        "parent_id": node.parent_id,
        "page_start": node.page_start,
        "page_end": node.page_end,
        "difficulty_level": node.difficulty_level,
        "learning_objectives": lo,
        "tags": getattr(node, "keywords", None),
        "key_concepts": None,
        "source_location": node.source_location,
        "is_visible": node.is_visible if node.is_visible is not None else True,
        "review_status": node.review_status,
        "content_hash": node.content_hash,
        "created_at": node.created_at.isoformat() if node.created_at else None,
        "updated_at": node.updated_at.isoformat() if node.updated_at else None,
        "children_count": children_count,
    }

async def _delete_children(db: AsyncSession, parent_id: int):
    result = await db.execute(
        select(ContentNode).where(ContentNode.parent_id == parent_id)
    )
    children = result.scalars().all()
    for child in children:
        await _delete_children(db, child.id)
        await db.delete(child)

async def _run_parse(textbook_id: int, file_path: str):
    """Background task: run full parsing pipeline with LLM config check"""
    from app.core import llm_config
    from app.core.content_parser_v2 import ContentParserV2
    from app.core.database import AsyncSessionLocal
    from app.core.llm import get_llm_helper

    llm = get_llm_helper()
    parser = ContentParserV2(llm_helper=llm)

    async with AsyncSessionLocal() as db:
        # 1. 检查 LLM 是否允许
        allowed, reason = await llm_config.check_llm_allowed(db, textbook_id=textbook_id)
        if not allowed:
            logger.warning(f"Parse blocked for textbook {textbook_id}: {reason}")
            return
        # 2. 加载 LLM 配置
        cfg = await llm_config.db_get_llm_runtime_config(db)
        llm.configure(cfg)
        if not llm.is_configured:
            logger.error(f"LLM not configured for textbook {textbook_id}")
            return

        try:
            if file_path.endswith(".pdf"):
                nodes = await parser.parse_from_pdf(file_path, textbook_id, 0, db_session=db)
            elif file_path.endswith((".docx", ".doc")):
                nodes = await parser.parse_from_docx(file_path, textbook_id, 0, db_session=db)
            else:
                logger.error(f"Unsupported file type: {file_path}")
                return

            # 3. 保存到数据库
            for node in nodes:
                db_node = ContentNode(
                    textbook_id=textbook_id,
                    title=node.title,
                    node_type=node.node_type,
                    content=node.content_raw,
                    depth=node.depth,
                    sort_order=node.sort_order,
                    page_start=node.page_start,
                    page_end=node.page_end,
                    difficulty_level=node.difficulty_level,
                    learning_objectives=json.dumps(node.learning_objectives, ensure_ascii=False),
                    keywords=json.dumps(node.keywords, ensure_ascii=False),
                    source_location=node.source_location,
                    is_visible=True,
                    review_status="pending",
                )
                db.add(db_node)
            await db.commit()
            logger.info(f"Parsed {len(nodes)} content nodes for textbook {textbook_id}")
        except Exception as e:
            logger.error(f"Parse failed for textbook {textbook_id}: {e}")
        finally:
            await llm.close()
