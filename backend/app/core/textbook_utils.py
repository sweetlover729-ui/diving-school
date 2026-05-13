"""
教材查询统一工具 - 消除双轨查询混乱
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.class_system import ClassTextbook, Textbook


async def get_class_textbooks(
    db: AsyncSession,
    class_id: int,
    resource_type: str | None = None
) -> list[Textbook]:
    """
    获取班级教材（统一查询，已合并 pdf 和 interactive 为单表）
    """
    query = select(ClassTextbook).where(ClassTextbook.class_id == class_id)
    if resource_type:
        query = query.where(ClassTextbook.resource_type == resource_type)

    result = await db.execute(query)
    class_books = result.scalars().all()

    if not class_books:
        return []

    textbook_ids = [cb.textbook_id for cb in class_books]
    result = await db.execute(
        select(Textbook).where(Textbook.id.in_(textbook_ids), Textbook.is_active == True)
    )
    return result.scalars().all()


async def get_class_textbook_ids(
    db: AsyncSession,
    class_id: int,
    resource_type: str | None = None
) -> list[int]:
    """获取班级教材ID列表"""
    textbooks = await get_class_textbooks(db, class_id, resource_type)
    return [t.id for t in textbooks]


async def get_class_textbook_pairs(
    db: AsyncSession,
    class_id: int
) -> list[tuple[int, str]]:
    """获取班级教材 (id, type) 对列表（统一表）"""
    result = await db.execute(
        select(ClassTextbook).where(ClassTextbook.class_id == class_id)
    )
    class_books = result.scalars().all()
    return [(cb.textbook_id, cb.resource_type or 'pdf') for cb in class_books]


async def assign_textbook_to_class(
    db: AsyncSession,
    class_id: int,
    textbook_id: int,
    resource_type: str = 'pdf'
) -> ClassTextbook:
    """
    分配教材到班级
    
    Args:
        resource_type: 'pdf' 或 'interactive'
    """
    # 检查是否已存在
    result = await db.execute(
        select(ClassTextbook).where(
            ClassTextbook.class_id == class_id,
            ClassTextbook.textbook_id == textbook_id
        )
    )
    existing = result.scalar_one_or_none()

    if existing:
        # 更新类型
        existing.resource_type = resource_type
        await db.commit()
        return existing

    # 新建
    ct = ClassTextbook(
        class_id=class_id,
        textbook_id=textbook_id,
        resource_type=resource_type
    )
    db.add(ct)
    await db.commit()
    return ct


async def remove_textbook_from_class(
    db: AsyncSession,
    class_id: int,
    textbook_id: int
) -> bool:
    """从班级移除教材（统一表）"""
    result = await db.execute(
        select(ClassTextbook).where(
            ClassTextbook.class_id == class_id,
            ClassTextbook.textbook_id == textbook_id
        )
    )
    ct = result.scalar_one_or_none()
    if ct:
        await db.delete(ct)
        await db.commit()
        return True
    return False
