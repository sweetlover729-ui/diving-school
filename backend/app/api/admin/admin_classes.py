"""
管理员-班级管理
"""

from .shared import *

router = APIRouter(prefix="", tags=["管理员-班级管理"])

# ============================
# 管理员-班级管理
# ============================
# ===== CLASSES (17 endpoints) =====
# ============================

@router.get("/classes")
async def list_classes(
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin)
):
    """List Classes"""
    query = select(Class)
    if status:
        query = query.where(Class.status == status)
    query = query.order_by(Class.id.desc())
    result = await db.execute(query)
    classes = result.scalars().all()
    return [c.__dict__ for c in classes]


@router.post("/classes")
async def create_class(
    req: ClassCreateRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin)
):
    """Create Class"""
    cls = Class(
        name=req.name,
        location=req.location,
        start_time=datetime.fromisoformat(req.start_time) if req.start_time else datetime.now(timezone.utc).replace(tzinfo=None),
        end_time=datetime.fromisoformat(req.end_time) if req.end_time else datetime.now(timezone.utc).replace(tzinfo=None).replace(hour=23, minute=59) + timedelta(days=30),
        status=ClassStatus(req.status) if req.status else ClassStatus.PENDING,
        created_by=user.id
    )
    db.add(cls)
    await db.commit()
    await db.refresh(cls)

    # 添加教材
    for tb_id in (req.textbooks or []):
        await db.execute(
            sql_text("INSERT INTO class_textbooks (class_id, textbook_id) VALUES (:cid, :tid)"),
            {"cid": cls.id, "tid": tb_id}
        )
    await db.commit()

    # 创建教练
    if req.instructor_name and req.instructor_phone:
        pw = req.instructor_password or (req.instructor_id_card or "000000")[-6:]
        pw_hash = bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()
        instructor = User(
            name=req.instructor_name,
            phone=req.instructor_phone,
            id_card=req.instructor_id_card or "",
            role=UserRole.INSTRUCTOR,
            password_hash=pw_hash,
            company_id=req.company_id,
            province=req.province or "",
            city=req.city or ""
        )
        db.add(instructor)
        await db.commit()
        await db.refresh(instructor)
        cm = ClassMember(class_id=cls.id, user_id=instructor.id, role=UserRole.INSTRUCTOR)
        db.add(cm)
        await db.commit()

    return {"id": cls.id, "name": cls.name, "status": cls.status.value}


@router.get("/classes/{class_id}")
async def get_class_detail(
    class_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin)
):
    """Get Class Detail"""
    cls = await db.get(Class, class_id)
    if not cls:
        raise HTTPException(status_code=404, detail="班级不存在")

    # 获取学员数
    member_result = await db.execute(
        sql_text("SELECT COUNT(*) FROM class_members WHERE class_id = :cid"),
        {"cid": class_id}
    )
    member_count = member_result.scalar() or 0

    # 获取教材
    textbooks_result = await db.execute(
        sql_text("""
            SELECT t.id, t.name, t.total_chapters as chapter_count
            FROM class_textbooks ct
            JOIN textbooks t ON ct.textbook_id = t.id
            WHERE ct.class_id = :cid
            ORDER BY ct.added_at DESC
        """),
        {"cid": class_id}
    )
    textbooks = [dict(r._mapping) for r in textbooks_result.fetchall()]

    # 获取互动式教材（统一表）
    interactive_result = await db.execute(
        sql_text("""
            SELECT ct.id, ct.textbook_id, t.name, t.total_chapters as chapter_count
            FROM class_textbooks ct
            JOIN textbooks t ON ct.textbook_id = t.id
            WHERE ct.class_id = :cid AND ct.resource_type = 'interactive'
            ORDER BY ct.added_at DESC
        """),
        {"cid": class_id}
    )
    interactive_textbooks = [dict(r._mapping) for r in interactive_result.fetchall()]

    # 获取文书（class_documents 表暂未创建，使用 savepoint 兜底）
    try:
        async with db.begin_nested():
            docs_result = await db.execute(
                sql_text("""
                    SELECT dt.id, dt.name, dt.doc_type, dt.is_required, cd.published_at
                    FROM class_documents cd
                    JOIN document_templates dt ON cd.template_id = dt.id
                    WHERE cd.class_id = :cid
                    ORDER BY cd.published_at DESC
                """),
                {"cid": class_id}
            )
            documents = [dict(r._mapping) for r in docs_result.fetchall()]
    except Exception:
        documents = []

    # 获取成员（前端依赖 data.members）
    members_result = await db.execute(
        sql_text("""
            SELECT cm.id, cm.user_id, cm.role, u.username as name, u.id_card_encrypted as id_card, u.phone,
                   u.province, u.city, cm.joined_at
            FROM class_members cm
            JOIN users u ON cm.user_id = u.id
            WHERE cm.class_id = :cid
            ORDER BY cm.joined_at
        """),
        {"cid": class_id}
    )
    members = [dict(r._mapping) for r in members_result.fetchall()]

    return {
        "id": cls.id,
        "name": cls.name,
        "location": cls.location,
        "start_time": serialize_datetime(cls.start_time),
        "end_time": serialize_datetime(cls.end_time),
        "status": cls.status.value,
        "member_count": member_count,
        "members": members,
        "courses": cls.courses or [],
        "textbooks": textbooks,
        "interactive_textbooks": interactive_textbooks,
        "documents": documents
    }


@router.put("/classes/{class_id}")
async def update_class(
    class_id: int,
    req: ClassUpdateRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin)
):
    """Update Class"""
    cls = await db.get(Class, class_id)
    if not cls:
        raise HTTPException(status_code=404, detail="班级不存在")
    if req.name is not None:
        cls.name = req.name
    if req.location is not None:
        cls.location = req.location
    if req.start_time is not None:
        cls.start_time = datetime.fromisoformat(req.start_time) if req.start_time else None
    if req.end_time is not None:
        cls.end_time = datetime.fromisoformat(req.end_time) if req.end_time else None
    # 保存课程分配（前端发 {code, name, is_active} 对象数组）
    if req.courses is not None:
        cls.courses = req.courses
    await db.commit()
    return {"success": True}


@router.delete("/classes/{class_id}")
async def delete_class(
    class_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin)
):
    """Delete Class"""
    cls = await db.get(Class, class_id)
    if not cls:
        raise HTTPException(status_code=404, detail="班级不存在")
    try:
        # ChapterProgress 无 cascade，需手动清理
        await db.execute(delete(ChapterProgress).where(ChapterProgress.class_id == class_id))
        # Class 的 cascade 会自动清理: ClassMember, ClassTextbook, Test → TestResult
        await db.delete(cls)
        await db.commit()
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=f"删除失败：{str(e)}")
    return {"success": True}


@router.get("/classes/{class_id}/analytics")
async def get_class_analytics(
    class_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin)
):
    """Get Class Analytics"""
    cls = await db.get(Class, class_id)
    if not cls:
        raise HTTPException(status_code=404, detail="班级不存在")

    # 获取学员进度：用 chapter_progress + test_results 分别计算
    progress_result = await db.execute(
        sql_text("""
            SELECT 
                u.id, 
                u.username as name, 
                u.phone,
                COALESCE(
                    (SELECT COUNT(*) FROM chapter_progress cp 
                     WHERE cp.user_id = u.id AND cp.class_id = :cid 
                       AND cp.status = 'completed') * 100.0 /
                    NULLIF((SELECT COUNT(*) FROM chapters c 
                          WHERE c.textbook_id IN 
                            (SELECT textbook_id FROM class_textbooks WHERE class_id = :cid)), 0)
                , 0) as reading_progress,
                COALESCE(
                    (SELECT AVG(tr2.score) FROM test_results tr2 
                     JOIN class_members cm2 ON cm2.user_id = tr2.user_id
                     WHERE tr2.user_id = u.id AND cm2.class_id = :cid)
                , 0) as score
            FROM class_members cm
            JOIN users u ON cm.user_id = u.id
            WHERE cm.class_id = :cid AND cm.role = 'student'
        """),
        {"cid": class_id}
    )
    students = [dict(r._mapping) for r in progress_result.fetchall()]

    return {
        "class_id": class_id,
        "class_name": cls.name,
        "status": cls.status.value,
        "students": students
    }


@router.get("/classes/{class_id}/documents")
async def get_class_documents(
    class_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin)
):
    """Get Class Documents"""
    try:
        result = await db.execute(
            sql_text("""
                SELECT dt.id, dt.name, dt.doc_type, dt.is_required, cd.published_at
                FROM class_documents cd
                JOIN document_templates dt ON cd.template_id = dt.id
                WHERE cd.class_id = :cid
                ORDER BY cd.published_at DESC
            """),
            {"cid": class_id}
        )
        return [dict(r._mapping) for r in result.fetchall()]
    except Exception:
        return []


@router.delete("/classes/{class_id}/documents/{document_id}")
async def remove_class_document(
    class_id: int,
    document_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin)
):
    """Remove Class Document"""
    try:
        await db.execute(
            sql_text("DELETE FROM class_documents WHERE class_id = :cid AND (id = :did OR template_id = :did)"),
            {"cid": class_id, "did": document_id}
        )
        await db.commit()
    except Exception:
        pass
    return {"success": True}


@router.post("/classes/{class_id}/start")
async def start_class(
    class_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin)
):
    """Start Class"""
    cls = await db.get(Class, class_id)
    if not cls:
        raise HTTPException(status_code=404, detail="班级不存在")
    cls.status = ClassStatus.ACTIVE
    await db.commit()
    return {"success": True, "message": "班级已开始"}


@router.post("/classes/{class_id}/end")
async def end_class(
    class_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin)
):
    """End Class"""
    cls = await db.get(Class, class_id)
    if not cls:
        raise HTTPException(status_code=404, detail="班级不存在")
    cls.status = ClassStatus.ENDED
    await db.commit()
    return {"success": True, "message": "班级已结班"}


@router.get("/classes/{class_id}/members")
async def list_class_members(
    class_id: int,
    role: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin)
):
    """List Class Members"""
    sql = """
        SELECT cm.id, cm.user_id, cm.role, u.username as name, u.id_card_encrypted as id_card, u.phone,
               u.province, u.city, cm.joined_at
        FROM class_members cm
        JOIN users u ON cm.user_id = u.id
        WHERE cm.class_id = :cid
    """
    params = {"cid": class_id}
    if role:
        sql += " AND cm.role = :role"
        params["role"] = role
    sql += " ORDER BY cm.joined_at"

    result = await db.execute(sql_text(sql), params)
    return [dict(r._mapping) for r in result.fetchall()]


class AddMemberRequest(BaseModel):
    """添加班级成员请求 - 支持选择已有用户或创建新用户"""
    user_id: Optional[int] = None   # 有值=选已有用户；无值=创建新用户
    name: Optional[str] = None
    id_card: Optional[str] = None
    phone: Optional[str] = ""
    role: str = "student"


@router.post("/classes/{class_id}/members")
async def add_class_member(
    class_id: int,
    req: AddMemberRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin)
):
    """Add Class Member - 支持选择已有成员或创建新成员"""
    if req.user_id:
        # 模式1：使用已有用户
        target_user = await db.get(User, req.user_id)
        if not target_user:
            raise HTTPException(status_code=404, detail="用户不存在")
        uid = target_user.id
    else:
        # 模式2：创建新用户
        if not req.name:
            raise HTTPException(status_code=400, detail="姓名不能为空")
        if req.role == "student" and not req.id_card:
            raise HTTPException(status_code=400, detail="学员身份证号不能为空")
        # 生成密码（手机后6位，无手机则000000）
        raw_pw = req.phone[-6:] if req.phone and len(req.phone) >= 6 else "000000"
        pw_hash = bcrypt.hashpw(raw_pw.encode(), bcrypt.gensalt()).decode()
        new_user = User(
            name=req.name,
            id_card=req.id_card or None,
            phone=req.phone or None,
            password_hash=pw_hash,
            role=UserRole(req.role)
        )
        db.add(new_user)
        await db.commit()
        await db.refresh(new_user)
        uid = new_user.id

    # 添加到班级
    cm = ClassMember(class_id=class_id, user_id=uid, role=UserRole(req.role))
    db.add(cm)
    await db.commit()
    await db.refresh(cm)
    return {"id": cm.id, "user_id": uid, "role": req.role}


@router.post("/classes/{class_id}/members/batch")
async def batch_import_students(
    class_id: int,
    req: StudentImportRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin)
):
    """Batch Import Students"""
    imported = []
    for s in (req.students or []):
        name = s.get("name", "")
        phone = s.get("phone", "")
        id_card = s.get("id_card", "")
        pw = s.get("password", phone[-6:] if phone else "000000")
        pw_hash = bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()

        # 检查是否已存在
        exist = await db.execute(
            select(User).where(User.phone == phone)
        )
        existing = exist.scalar_one_or_none()

        if existing:
            uid = existing.id
        else:
            u = User(name=name, phone=phone, id_card=id_card,
                     password_hash=pw_hash, role=UserRole.STUDENT)
            db.add(u)
            await db.commit()
            await db.refresh(u)
            uid = u.id

        # 添加到班级
        cm = ClassMember(class_id=class_id, user_id=uid, role=UserRole.STUDENT)
        db.add(cm)
        imported.append({"name": name, "user_id": uid})

    await db.commit()
    return {"imported": imported, "count": len(imported)}


@router.delete("/classes/{class_id}/members/{member_id}")
async def remove_class_member(
    class_id: int,
    member_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin)
):
    """Remove Class Member"""
    await db.execute(
        sql_text("DELETE FROM class_members WHERE id = :mid AND class_id = :cid"),
        {"mid": member_id, "cid": class_id}
    )
    await db.commit()
    return {"success": True}


@router.delete("/classes/{class_id}/members/user_id/{user_id}")
async def remove_class_member_by_user(
    class_id: int,
    user_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin)
):
    """Remove Class Member"""
    await db.execute(
        sql_text("DELETE FROM class_members WHERE user_id = :uid AND class_id = :cid"),
        {"uid": user_id, "cid": class_id}
    )
    await db.commit()
    return {"success": True}



@router.get("/classes/{class_id}/student/{user_id}/progress")
async def get_student_progress(
    class_id: int,
    user_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin)
):
    """Get Student Progress"""
    # 读取进度
    progress_result = await db.execute(
        sql_text("""
            SELECT chapter_id, reading_pages, status, reading_start_at, last_updated
            FROM chapter_progress
            WHERE user_id = :uid
            ORDER BY last_updated DESC
        """),
        {"uid": user_id}
    )
    progress = [dict(r._mapping) for r in progress_result.fetchall()]
    return {"user_id": user_id, "progress": progress}


@router.get("/classes/{class_id}/textbooks")
async def get_class_textbooks(
    class_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin)
):
    """Get Class Textbooks"""
    result = await db.execute(
        sql_text("""
            SELECT t.id, t.name, t.total_chapters, t.total_pages, ct.added_at
            FROM class_textbooks ct
            JOIN textbooks t ON ct.textbook_id = t.id
            WHERE ct.class_id = :cid
            ORDER BY ct.added_at DESC
        """),
        {"cid": class_id}
    )
    return [dict(r._mapping) for r in result.fetchall()]


@router.get("/classes/{class_id}/textbooks/interactive")
async def get_class_interactive_textbooks(
    class_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin)
):
    """Get Class Interactive Textbooks"""
    result = await db.execute(
        sql_text("""
            SELECT ct.id, ct.textbook_id, t.name, t.total_chapters as chapter_count
            FROM class_textbooks ct
            JOIN textbooks t ON ct.textbook_id = t.id
            WHERE ct.class_id = :cid AND ct.resource_type = 'interactive'
            ORDER BY ct.added_at DESC
        """),
        {"cid": class_id}
    )
    return [dict(r._mapping) for r in result.fetchall()]


@router.post("/classes/{class_id}/textbooks/interactive/{textbook_id}")
async def add_class_interactive_textbook(
    class_id: int,
    textbook_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin)
):
    """Add Class Interactive Textbook"""
    # 检查班级和教材是否存在
    cls = await db.get(Class, class_id)
    if not cls:
        raise HTTPException(status_code=404, detail="班级不存在")
    tb = await db.get(Textbook, textbook_id)
    if not tb:
        raise HTTPException(status_code=404, detail="教材不存在")
    # 使用统一表，设 resource_type='interactive'
    existing = await db.execute(
        select(ClassTextbook).where(
            ClassTextbook.class_id == class_id,
            ClassTextbook.textbook_id == textbook_id
        )
    )
    ct = existing.scalar_one_or_none()
    if ct:
        ct.resource_type = 'interactive'
    else:
        db.add(ClassTextbook(
            class_id=class_id,
            textbook_id=textbook_id,
            resource_type='interactive',
            added_at=datetime.now(timezone.utc).replace(tzinfo=None)
        ))
    await db.commit()
    return {"success": True}


@router.delete("/classes/{class_id}/textbooks/interactive/{textbook_id}")
async def remove_class_interactive_textbook(
    class_id: int,
    textbook_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin)
):
    """Remove Class Interactive Textbook"""
    result = await db.execute(
        select(ClassTextbook).where(
            ClassTextbook.class_id == class_id,
            ClassTextbook.textbook_id == textbook_id,
            ClassTextbook.resource_type == 'interactive'
        )
    )
    ct = result.scalar_one_or_none()
    if ct:
        await db.delete(ct)
    await db.commit()
    return {"success": True}


@router.post("/classes/{class_id}/textbooks/{textbook_id}")
async def add_class_textbook(
    class_id: int,
    textbook_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin)
):
    """Add Class Textbook"""
    # 检查班级和教材是否存在
    cls = await db.get(Class, class_id)
    if not cls:
        raise HTTPException(status_code=404, detail="班级不存在")
    tb = await db.get(Textbook, textbook_id)
    if not tb:
        raise HTTPException(status_code=404, detail="教材不存在")
    await db.execute(
        sql_text("""
            INSERT INTO class_textbooks (class_id, textbook_id, added_at)
            VALUES (:cid, :tid, :now)
            ON CONFLICT (class_id, textbook_id) DO NOTHING
        """),
        {"cid": class_id, "tid": textbook_id, "now": datetime.now(timezone.utc).replace(tzinfo=None)}
    )
    await db.commit()
    return {"success": True}


@router.delete("/classes/{class_id}/textbooks/{textbook_id}")
async def remove_class_textbook(
    class_id: int,
    textbook_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin)
):
    """Remove Class Textbook"""
    await db.execute(
        sql_text("DELETE FROM class_textbooks WHERE class_id = :cid AND textbook_id = :tid"),
        {"cid": class_id, "tid": textbook_id}
    )
    await db.commit()
    return {"success": True}

