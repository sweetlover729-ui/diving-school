"""
数据模型单元测试
覆盖：User, Class, ClassMember, Textbook, Chapter, Question, Test, TestResult
"""
import json
from datetime import datetime, timedelta, timezone

import pytest

from app.models.class_system import (
    Chapter,
    Class,
    ClassMember,
    ClassStatus,
    Company,
    Question,
    QuestionType,
    TestStatus,
    TestType,
    Textbook,
    User,
    UserRole,
)
from app.models.class_system import (
    Test as TestModel,
)


class TestUserModel:
    """用户模型测试"""

    async def test_create_user_basic(self, db_session):
        user = User(name="张三", phone="13800138001", role=UserRole.STUDENT)
        db_session.add(user)
        await db_session.flush()

        assert user.id is not None
        assert user.name == "张三"
        assert user.role == UserRole.STUDENT
        assert user.is_active is True
        assert user.created_at is not None

    async def test_create_user_all_fields(self, db_session):
        user = User(
            name="李四",
            id_card="440102199001011234",
            phone="13900139001",
            password_hash="hashed_secure_pw",
            role=UserRole.INSTRUCTOR,
            is_active=True,
            company_id=1,
            province="广东",
            city="深圳",
            training_institution="XX消防培训",
            instructor_code="INS099",
        )
        db_session.add(user)
        await db_session.flush()

        assert user.province == "广东"
        assert user.training_institution == "XX消防培训"
        assert user.instructor_code == "INS099"

    async def test_user_role_enum_values(self, db_session):
        """角色枚举值必须为合法值"""
        valid_roles = [UserRole.ADMIN, UserRole.INSTRUCTOR, UserRole.MANAGER, UserRole.STUDENT]
        for role in valid_roles:
            user = User(name=f"test_{role.value}", phone=f"13800{role.value}", role=role)
            db_session.add(user)
        await db_session.flush()

        from sqlalchemy import func, select
        result = await db_session.execute(select(func.count()).select_from(User))
        assert result.scalar() == 4

    async def test_user_default_is_active_true(self, db_session):
        user = User(name="默认激活", phone="13800138002", role=UserRole.STUDENT)
        db_session.add(user)
        await db_session.flush()
        assert user.is_active is True

    async def test_user_inactive_flag(self, db_session):
        user = User(name="禁用用户", phone="13800138003", role=UserRole.STUDENT, is_active=False)
        db_session.add(user)
        await db_session.flush()
        assert user.is_active is False

    async def test_user_phone_unique(self, db_session):
        """手机号在业务层面应有唯一约束（模型层面无硬约束）"""
        u1 = User(name="用户1", phone="13800138004", role=UserRole.STUDENT)
        db_session.add(u1)
        await db_session.flush()

        u2 = User(name="用户2", phone="13800138004", role=UserRole.STUDENT)
        db_session.add(u2)
        await db_session.flush()  # 模型无unique约束，不应报错
        assert u2.id != u1.id

    async def test_user_name_required(self, db_session):
        """name 为必填字段 nullable=False"""
        from sqlalchemy.exc import IntegrityError
        user = User(phone="13800138005", role=UserRole.STUDENT, name=None)
        db_session.add(user)
        with pytest.raises(IntegrityError):
            await db_session.flush()


class TestClassModel:
    """班级模型测试"""

    async def test_create_class_basic(self, db_session, admin_user):
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        cls = Class(
            name="潜水初级班",
            location="广州基地",
            start_time=now,
            end_time=now + timedelta(days=30),
            status=ClassStatus.PENDING,
            created_by=admin_user.id,
        )
        db_session.add(cls)
        await db_session.flush()

        assert cls.id is not None
        assert cls.status == ClassStatus.PENDING

    async def test_class_status_transitions(self, db_session, admin_user):
        """班级状态: PENDING → ACTIVE → ENDED → ARCHIVED"""
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        cls = Class(
            name="状态测试班",
            start_time=now,
            end_time=now + timedelta(days=30),
            status=ClassStatus.PENDING,
            created_by=admin_user.id,
        )
        db_session.add(cls)
        await db_session.flush()

        cls.status = ClassStatus.ACTIVE
        await db_session.flush()
        assert cls.status == ClassStatus.ACTIVE

        cls.status = ClassStatus.ENDED
        await db_session.flush()
        assert cls.status == ClassStatus.ENDED

        cls.status = ClassStatus.ARCHIVED
        await db_session.flush()
        assert cls.status == ClassStatus.ARCHIVED

    async def test_class_textbook_ids_json(self, db_session, admin_user):
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        cls = Class(
            name="教材测试班",
            start_time=now,
            end_time=now + timedelta(days=30),
            created_by=admin_user.id,
        )
        cls.set_textbook_ids([1, 2, 3])
        db_session.add(cls)
        await db_session.flush()

        assert cls.get_textbook_ids() == [1, 2, 3]

    async def test_class_name_required(self, db_session, admin_user):
        from sqlalchemy.exc import IntegrityError
        cls = Class(
            name=None,
            start_time=datetime.now(timezone.utc).replace(tzinfo=None),
            end_time=datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=30),
            created_by=admin_user.id,
        )
        db_session.add(cls)
        with pytest.raises(IntegrityError):
            await db_session.flush()

    async def test_class_with_instructor_and_manager(self, db_session, admin_user, instructor_user, manager_user):
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        cls = Class(
            name="全配置班级",
            start_time=now,
            end_time=now + timedelta(days=30),
            instructor_id=instructor_user.id,
            manager_id=manager_user.id,
            created_by=admin_user.id,
        )
        db_session.add(cls)
        await db_session.flush()

        assert cls.instructor_id == instructor_user.id
        assert cls.manager_id == manager_user.id


class TestClassMemberModel:
    """班级成员模型测试"""

    async def test_add_student_to_class(self, db_session, active_class, student_user):
        member = ClassMember(
            class_id=active_class.id,
            user_id=student_user.id,
            role=UserRole.STUDENT,
        )
        db_session.add(member)
        await db_session.flush()

        assert member.id is not None
        assert member.class_id == active_class.id
        assert member.user_id == student_user.id

    async def test_cascade_delete_class_removes_members(self, db_session, active_class, student_user):
        member = ClassMember(
            class_id=active_class.id,
            user_id=student_user.id,
            role=UserRole.STUDENT,
        )
        db_session.add(member)
        await db_session.flush()

        await db_session.delete(active_class)
        await db_session.flush()

        from sqlalchemy import func, select
        result = await db_session.execute(
            select(func.count()).select_from(ClassMember).where(ClassMember.class_id == active_class.id)
        )
        assert result.scalar() == 0


class TestTextbookModel:
    """教材模型测试"""

    async def test_create_textbook_basic(self, db_session):
        tb = Textbook(
            name="潜水基础理论",
            description="公共安全潜水员培训教材",
            total_chapters=5,
        )
        db_session.add(tb)
        await db_session.flush()

        assert tb.id is not None
        assert tb.is_active is True

    async def test_textbook_with_import_status(self, db_session):
        tb = Textbook(
            name="待导入教材",
            import_status="pending",
            import_error=None,
        )
        db_session.add(tb)
        await db_session.flush()

        assert tb.import_status == "pending"
        assert tb.import_error is None

    async def test_textbook_import_failed_with_error(self, db_session):
        tb = Textbook(
            name="导入失败教材",
            import_status="failed",
            import_error="PDF解析错误：无法读取第3页",
        )
        db_session.add(tb)
        await db_session.flush()

        assert tb.import_status == "failed"
        assert "PDF解析错误" in tb.import_error


class TestChapterModel:
    """章节模型测试"""

    async def test_create_chapter(self, db_session, textbook):
        ch = Chapter(
            textbook_id=textbook.id,
            title="第一章 潜水物理学",
            content="阿基米德原理...",
            sort_order=1,
            page_start=1,
            page_end=15,
        )
        db_session.add(ch)
        await db_session.flush()

        assert ch.id is not None
        assert ch.title == "第一章 潜水物理学"
        assert ch.page_end == 15

    async def test_chapter_hierarchy(self, db_session, textbook):
        parent = Chapter(textbook_id=textbook.id, title="第一单元", sort_order=1)
        db_session.add(parent)
        await db_session.flush()

        child = Chapter(
            textbook_id=textbook.id,
            parent_id=parent.id,
            title="1.1 基本原理",
            sort_order=1,
        )
        db_session.add(child)
        await db_session.flush()

        assert child.parent_id == parent.id


class TestQuestionModel:
    """题目模型测试"""

    async def test_create_single_choice_question(self, db_session, textbook, chapter, admin_user):
        q = Question(
            textbook_id=textbook.id,
            chapter_id=chapter.id,
            question_type=QuestionType.SINGLE,
            content="水中声音传播速度约是多少？",
            options='["约340m/s", "约1500m/s", "约3000m/s", "约500m/s"]',
            answer='["约1500m/s"]',
            difficulty=2,
        )
        db_session.add(q)
        await db_session.flush()

        assert q.question_type == QuestionType.SINGLE
        assert len(q.get_options()) == 4
        assert q.get_answer() == ["约1500m/s"]

    async def test_create_judge_question(self, db_session, textbook, chapter, admin_user):
        q = Question(
            textbook_id=textbook.id,
            chapter_id=chapter.id,
            question_type=QuestionType.JUDGE,
            content="潜水气瓶应每年进行水压测试。",
            options='["正确", "错误"]',
            answer='["正确"]',
            difficulty=1,
        )
        db_session.add(q)
        await db_session.flush()

        assert q.question_type == QuestionType.JUDGE

    async def test_all_question_types(self, db_session, textbook, chapter, admin_user):
        for qt in QuestionType:
            q = Question(
                textbook_id=textbook.id,
                chapter_id=chapter.id,
                question_type=qt,
                content=f"测试题-{qt.value}",
                options='["A", "B", "C", "D"]',
                answer='["A"]',
            )
            db_session.add(q)
        await db_session.flush()

        from sqlalchemy import func, select
        result = await db_session.execute(select(func.count()).select_from(Question))
        assert result.scalar() == 4


class TestExamModel:
    """测验/考试模型测试"""

    async def test_create_test(self, db_session, active_class, admin_user):
        t = TestModel(
            class_id=active_class.id,
            title="潜水理论期末考试",
            test_type=TestType.EXAM,
            questions=json.dumps([1, 2, 3]),
            total_score=100,
            duration=60,
            status=TestStatus.DRAFT,
            created_by=admin_user.id,
        )
        db_session.add(t)
        await db_session.flush()

        assert t.test_type == TestType.EXAM
        assert t.get_question_ids() == [1, 2, 3]
        assert t.total_score == 100

    async def test_test_status_lifecycle(self, db_session, active_class, admin_user):
        t = TestModel(
            class_id=active_class.id,
            title="状态测试",
            test_type=TestType.QUIZ,
            questions=json.dumps([1]),
            total_score=50,
            created_by=admin_user.id,
        )
        db_session.add(t)
        await db_session.flush()

        t.status = TestStatus.PUBLISHED
        await db_session.flush()
        assert t.status == TestStatus.PUBLISHED

        t.status = TestStatus.ENDED
        await db_session.flush()
        assert t.status == TestStatus.ENDED


class TestCompanyModel:
    """单位模型测试"""

    async def test_create_company(self, db_session):
        c = Company(
            name="XX消防总队",
            province="广东",
            city="广州",
            contact="张队长",
            phone="020-12345678",
        )
        db_session.add(c)
        await db_session.flush()

        assert c.id is not None
        assert c.province == "广东"


class TestModelRelationships:
    """模型关系测试"""

    async def test_class_member_user_relationship(self, db_session, active_class, student_user):
        member = ClassMember(
            class_id=active_class.id,
            user_id=student_user.id,
            role=UserRole.STUDENT,
        )
        db_session.add(member)
        await db_session.flush()

        # 验证外键关联
        assert member.class_id == active_class.id
        assert member.user_id == student_user.id

    async def test_question_textbook_relationship(self, db_session, question, textbook):
        assert question.textbook_id == textbook.id

    async def test_question_chapter_relationship(self, db_session, question, chapter):
        assert question.chapter_id == chapter.id
