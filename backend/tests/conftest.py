"""conftest.py — 全局测试配置（V3 修复版）"""
import os
import sys
import pytest
import pytest_asyncio
from typing import AsyncGenerator
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
import bcrypt

# 关键：在导入 app.main 之前设置 TEST_DATABASE_URL
os.environ.setdefault("TEST_DATABASE_URL", "postgresql+asyncpg://onedive:Onedive2024!@localhost:5432/diving_test")
os.environ["DATABASE_URL"] = os.environ["TEST_DATABASE_URL"]

sys.path.insert(0, "/var/www/diving/backend")

from app.main import app
from app.core.database import Base, get_db
from app.models.class_system import (
    User, UserRole, Class, ClassMember, ClassStatus,
    Company, Textbook, Chapter, Question, QuestionType,
    Test as TestModel, TestType, TestStatus,
    Category, Course, Module,
)

TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://onedive:Onedive2024!@localhost:5432/diving_test"
)


def _hash_pw(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def _make_token(user_id: int, role: str) -> str:
    from datetime import datetime, timedelta, timezone
    from jose import jwt
    from app.core.config import settings
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": str(user_id), "role": role, "exp": expire,
        "iat": datetime.now(timezone.utc), "type": "access"
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


@pytest_asyncio.fixture(scope="function")
async def db_engine():
    engine = create_async_engine(TEST_DATABASE_URL, echo=False, pool_pre_ping=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    # Use TRUNCATE CASCADE to avoid deadlock from open connections
    async with engine.begin() as conn:
        from sqlalchemy import text
        try:
            # Use TRUNCATE with CASCADE - best for test cleanup
            # Set short timeout to avoid hanging on locks
            await conn.execute(text("SET statement_timeout = '5s'"))
            # Get list of tables (excluding sqlalchemy migration tables)
            result = await conn.execute(text(
                "SELECT tablename FROM pg_tables WHERE schemaname = 'public' AND tablename NOT LIKE 'alembic%'"
            ))
            tables = [row[0] for row in result.fetchall()]
            for tbl in tables:
                try:
                    await conn.execute(text(f"TRUNCATE TABLE {tbl} CASCADE"))
                except Exception as e:
                    # Table might be locked or have issues, try DELETE as fallback
                    try:
                        await conn.execute(text(f"DELETE FROM {tbl}"))
                    except Exception:
                        pass
        except Exception as e:
            print(f"Cleanup warning: {e}")
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def db_session(db_engine) -> AsyncGenerator[AsyncSession, None]:
    session_factory = async_sessionmaker(db_engine, expire_on_commit=False, autoflush=False)
    session = session_factory()
    try:
        yield session
    finally:
        await session.rollback()
        await session.close()


@pytest_asyncio.fixture(scope="function")
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    async def override_get_db():
        yield db_session
    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture(scope="function")
async def api_client(client):
    """Alias for client fixture (used by test files expecting api_client)."""
    return client


@pytest.fixture
def make_token():
    return _make_token


async def _create_user(db_session, username, phone, role, password="test123",
                        id_card=None, company_id=None, province=None, city=None,
                        instructor_code=None) -> User:
    user = User(
        name=username,
        phone=phone,
        id_card=id_card or ("11010119900101" + phone[-4:]),
        password_hash=_hash_pw(password),
        role=role,
        is_active=True,
        company_id=company_id,
        province=province,
        city=city,
        instructor_code=instructor_code,
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest_asyncio.fixture
async def admin_user(db_session) -> User:
    return await _create_user(db_session, "test_admin", "13800000011", UserRole.ADMIN)


@pytest.fixture
def admin_token(admin_user):
    return _make_token(admin_user.id, "admin")


@pytest_asyncio.fixture
async def manager_user(db_session) -> User:
    return await _create_user(db_session, "test_manager", "13800000012", UserRole.MANAGER,
                               province="广东", city="广州")


@pytest.fixture
def manager_token(manager_user):
    return _make_token(manager_user.id, "manager")


@pytest_asyncio.fixture
async def instructor_user(db_session) -> User:
    return await _create_user(db_session, "test_instructor", "13800000013", UserRole.INSTRUCTOR,
                               province="广东", city="广州", instructor_code="TEST001")


@pytest.fixture
def instructor_token(instructor_user):
    return _make_token(instructor_user.id, "instructor")


@pytest_asyncio.fixture
async def student_user(db_session) -> User:
    return await _create_user(db_session, "test_student", "13800000014", UserRole.STUDENT)


@pytest.fixture
def student_token(student_user):
    return _make_token(student_user.id, "student")


@pytest_asyncio.fixture
async def active_class(db_session, instructor_user, manager_user, admin_user) -> Class:
    from datetime import datetime, timedelta, timezone
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    cls = Class(
        name="测试班级", location="广州",
        start_time=now - timedelta(days=7), end_time=now + timedelta(days=23),
        status=ClassStatus.ACTIVE,
        instructor_id=instructor_user.id, manager_id=manager_user.id, created_by=admin_user.id,
    )
    db_session.add(cls)
    await db_session.flush()
    return cls


@pytest_asyncio.fixture
async def student_in_class(db_session, student_user, active_class) -> User:
    member = ClassMember(class_id=active_class.id, user_id=student_user.id, role=UserRole.STUDENT)
    db_session.add(member)
    await db_session.flush()
    return student_user


@pytest.fixture
def student_in_class_token(student_in_class):
    return _make_token(student_in_class.id, "student")


@pytest_asyncio.fixture
async def instructor_in_class(db_session, active_class, instructor_user) -> User:
    member = ClassMember(class_id=active_class.id, user_id=instructor_user.id, role=UserRole.INSTRUCTOR)
    db_session.add(member)
    await db_session.flush()
    return instructor_user


@pytest.fixture
def instructor_in_class_token(instructor_in_class):
    return _make_token(instructor_in_class.id, "instructor")


@pytest_asyncio.fixture
async def manager_in_class(db_session, active_class, manager_user) -> User:
    member = ClassMember(class_id=active_class.id, user_id=manager_user.id, role=UserRole.MANAGER)
    db_session.add(member)
    await db_session.flush()
    return manager_user


@pytest.fixture
def manager_in_class_token(manager_in_class):
    return _make_token(manager_in_class.id, "manager")


@pytest_asyncio.fixture
async def textbook(db_session) -> Textbook:
    tb = Textbook(name="测试教材", description="测试用教材", total_chapters=3, is_active=True)
    db_session.add(tb)
    await db_session.flush()
    await db_session.commit()
    return tb


@pytest_asyncio.fixture
async def module(db_session) -> Module:
    mod = Module(level=1, name="测试模块", description="测试用模块", order=1)
    db_session.add(mod)
    await db_session.flush()
    await db_session.commit()
    return mod


@pytest_asyncio.fixture
async def chapter(db_session, textbook, module) -> Chapter:
    ch = Chapter(module_id=module.id, textbook_id=textbook.id, title="第一章", content="测试内容", sort_order=1)
    db_session.add(ch)
    await db_session.flush()
    await db_session.commit()
    return ch


@pytest_asyncio.fixture
async def question(db_session, textbook, chapter, admin_user) -> Question:
    q = Question(
        textbook_id=textbook.id, chapter_id=chapter.id,
        question_type=QuestionType.SINGLE,
        content="测试题目？",
        options='["A选项","B选项","C选项","D选项"]',
        answer='["A"]',
        difficulty=1,
    )
    db_session.add(q)
    await db_session.flush()
    return q


# ── Additional fixtures for test_admin_apis.py ──────────────────────────────────

@pytest_asyncio.fixture
async def test_category(db_session) -> Category:
    cat = Category(
        name="测试分类",
        code="TEST_CAT_FIXTURE",
        description="测试分类描述",
        sort_order=0,
        is_active=True,
    )
    db_session.add(cat)
    await db_session.flush()
    return cat


@pytest_asyncio.fixture
async def test_course(db_session, test_category) -> Course:
    course = Course(
        name="测试课程",
        code="TEST_COURSE_FIXTURE",
        category_id=test_category.id,
        description="测试课程描述",
        is_active=True,
    )
    db_session.add(course)
    await db_session.flush()
    return course


@pytest_asyncio.fixture
async def test_question(db_session, textbook, chapter, admin_user) -> Question:
    q = Question(
        textbook_id=textbook.id, chapter_id=chapter.id,
        question_type=QuestionType.SINGLE,
        content="测试题目内容？",
        options='["选项A","选项B","选项C","选项D"]',
        answer='["A"]',
        difficulty=1,
    )
    db_session.add(q)
    await db_session.flush()
    await db_session.commit()
    return q


@pytest_asyncio.fixture
async def test_company(db_session) -> Company:
    company = Company(
        name="测试公司",
        province="广东",
        city="深圳",
        contact="测试联系人",
        phone="13800000000",
    )
    db_session.add(company)
    await db_session.flush()
    return company
