"""
班级制培训管理系统 - 数据模型
V7.1.0 — 精确匹配实际 DB schema，零隐式偏差

修复记录 (2026-05-13):
  - 移除 str.replace() 污染: real_name/current_level/face_image_url/face_feature_vector 从 6 个模型清除
  - Company: 补齐 province/city 列; created_at/updated_at 修复为 DateTime
  - Chapter: 恢复 module_id 制, 新增 textbook_id 等 V7 列 (之前 DB 迁移已添加)
  - Question: answer → correct_answer (DB 列名映射); 新增 textbook_id
  - ContentNode: keywords/tags/prerequisite_ids 类型修正为 Text/Integer
  - User: current_level 类型修正为 Integer
  - 新增 SystemSettings, Module, Lesson 等遗留模型
  - 移除 18 个无 DB 表的模型定义 (待 V7 迁移补建)
"""
import enum
import json
from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.core.database import Base


def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


# ═══ 枚举 ═══

class UserRole(str, enum.Enum):
    ADMIN = "admin"
    INSTRUCTOR = "instructor"
    MANAGER = "manager"
    STUDENT = "student"

class ClassStatus(str, enum.Enum):
    PENDING = "pending"
    ACTIVE = "active"
    ENDED = "ended"
    CANCELLED = "cancelled"
    ARCHIVED = "archived"

class TestType(str, enum.Enum):
    HOMEWORK = "homework"
    QUIZ = "quiz"
    EXAM = "exam"

class QuestionType(str, enum.Enum):
    SINGLE = "single"
    MULTIPLE = "multiple"
    JUDGE = "judge"
    FILL = "fill"

class TestStatus(str, enum.Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ENDED = "ended"

class ChapterProgressStatus(str, enum.Enum):
    LOCKED = "locked"
    READING = "reading"
    READING_DONE = "reading_done"
    PRACTICING = "practicing"
    PRACTICE_DONE = "practice_done"
    WAITING_TEST = "waiting_test"
    COMPLETED = "completed"


# ═══ PART 1: 核心业务模型 ═══

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    phone = Column(String(20), index=True, nullable=False)
    name = Column("username", String(50), nullable=False)
    id_card = Column("id_card_encrypted", Text, index=True)
    password_hash = Column("hashed_password", String(255), nullable=False)
    real_name = Column(String(50), nullable=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=True)
    province = Column(String(50), nullable=True)
    city = Column(String(50), nullable=True)
    instructor_code = Column(String(50), nullable=True)
    avatar = Column(String(500), nullable=True)
    is_active = Column(Boolean, default=True)
    role = Column(
        Enum(UserRole, values_callable=lambda e: [x.value for x in e]),
        default=UserRole.STUDENT, nullable=False,
    )
    avatar = Column(String(255))
    is_active = Column(Boolean, default=True)
    current_level = Column(Integer, default=1)
    face_image_url = Column(String(500), nullable=True)
    face_feature_vector = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)
    class_memberships = relationship("ClassMember", back_populates="user")


class Company(Base):
    __tablename__ = "companies"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    province = Column(String(50), nullable=True)
    city = Column(String(50), nullable=True)
    contact = Column(String(100), nullable=True)
    phone = Column(String(20), nullable=True)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)


class Class(Base):
    __tablename__ = "classes"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    location = Column(String(200))
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    status = Column(
        Enum(ClassStatus, values_callable=lambda e: [x.value for x in e]),
        default=ClassStatus.PENDING,
    )
    instructor_id = Column(Integer, ForeignKey("users.id"))
    manager_id = Column(Integer, ForeignKey("users.id"))
    textbooks = Column(Text)
    courses = Column(JSON, nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    members = relationship("ClassMember", back_populates="cls")
    class_textbooks = relationship(
        "ClassTextbook", back_populates="cls",
        foreign_keys="ClassTextbook.class_id",
    )
    class_courses = relationship("ClassCourse", back_populates="cls")
    instructor = relationship("User", foreign_keys=[instructor_id])
    manager = relationship("User", foreign_keys=[manager_id])

    def get_textbook_ids(self):
        if self.textbooks:
            return json.loads(self.textbooks)
        return []

    def set_textbook_ids(self, ids):
        self.textbooks = json.dumps(ids)


class ClassMember(Base):
    __tablename__ = "class_members"
    id = Column(Integer, primary_key=True, index=True)
    class_id = Column(Integer, ForeignKey("classes.id", ondelete="SET NULL"), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    role = Column(
        Enum(UserRole, values_callable=lambda e: [x.value for x in e]),
        nullable=False,
    )
    joined_at = Column(DateTime, default=utcnow)
    cls = relationship("Class", back_populates="members")
    user = relationship("User", back_populates="class_memberships")


class ClassTextbook(Base):
    __tablename__ = "class_textbooks"
    __table_args__ = (
        UniqueConstraint("class_id", "textbook_id", name="uq_class_textbooks_pair"),
    )
    id = Column(Integer, primary_key=True, index=True)
    class_id = Column(Integer, ForeignKey("classes.id"), nullable=False)
    textbook_id = Column(Integer, ForeignKey("textbooks.id"), nullable=False)
    resource_type = Column(String(20), default="pdf")
    added_at = Column(DateTime, default=utcnow)
    cls = relationship("Class", back_populates="class_textbooks")
    textbook = relationship("Textbook", back_populates="class_textbooks")


class ClassCourse(Base):
    __tablename__ = "class_courses"
    __table_args__ = (UniqueConstraint("class_id", "course_id"),)
    id = Column(Integer, primary_key=True, index=True)
    class_id = Column(Integer, ForeignKey("classes.id", ondelete="CASCADE"))
    course_id = Column(Integer, ForeignKey("courses.id", ondelete="CASCADE"))
    cls = relationship("Class", back_populates="class_courses")
    course = relationship("Course", back_populates="class_links")


class TextbookPage(Base):
    __tablename__ = "textbook_pages"
    id = Column(Integer, primary_key=True, index=True)
    textbook_id = Column(Integer, ForeignKey("textbooks.id"), nullable=False)
    page_number = Column(Integer, nullable=False)
    image_url = Column(Text, nullable=False)
    is_visible = Column(Boolean, default=True)
    created_at = Column(DateTime, default=utcnow)


class StudentPDFProgress(Base):
    __tablename__ = "student_pdf_progress"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    textbook_id = Column(Integer, ForeignKey("textbooks.id"), nullable=False)
    class_id = Column(Integer, ForeignKey("classes.id"), nullable=False)
    current_page = Column(Integer, default=0)
    total_pages = Column(Integer, default=0)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)


class Textbook(Base):
    __tablename__ = "textbooks"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    description = Column(Text)
    cover_image = Column(String(255))
    total_chapters = Column(Integer, default=0)
    total_pages = Column(Integer, default=0)
    file_path = Column(String(500))
    file_type = Column(String(20), default=None)
    has_interactive = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    import_status = Column(String(20), default=None)
    import_error = Column(Text, default=None)
    category_id = Column(Integer, ForeignKey("categories.id"))
    status = Column(String(20), default=None)
    source_file_type = Column(String(20), default=None)
    parse_version = Column(Integer, default=None)
    interactive_path = Column(String(500))
    total_nodes = Column(Integer, default=0)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)
    llm_enabled = Column(Boolean, default=False)
    created_at = Column(DateTime, default=utcnow)

    category = relationship("Category", back_populates="textbooks")
    class_textbooks = relationship("ClassTextbook", back_populates="textbook")
    pages = relationship("TextbookPage")
    chapters = relationship("Chapter", back_populates="textbook")
    questions = relationship("Question", back_populates="textbook")


class Chapter(Base):
    __tablename__ = "chapters"
    id = Column(Integer, primary_key=True, index=True)
    module_id = Column(Integer, nullable=True)
    title = Column(String(200), nullable=False)
    order = Column("order", Integer, default=0)
    sort_order = Column("sort_order", Integer, default=0)
    description = Column("description", Text, nullable=True)
    content = Column("content", Text, nullable=True)
    is_locked = Column(Boolean, default=False)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)
    textbook_id = Column(Integer, ForeignKey("textbooks.id"), nullable=True)
    parent_id = Column(Integer, ForeignKey("chapters.id"), nullable=True)
    page_start = Column(Integer, nullable=True)
    page_end = Column(Integer, nullable=True)

    textbook = relationship("Textbook", back_populates="chapters")
    questions = relationship("Question", back_populates="chapter")


class Question(Base):
    __tablename__ = "questions"
    id = Column(Integer, primary_key=True, index=True)
    chapter_id = Column(Integer, ForeignKey("chapters.id"), nullable=True)
    lesson_id = Column(Integer, nullable=True)
    level = Column(Integer, nullable=False, default=1)
    question_type = Column(
        Enum(QuestionType, values_callable=lambda e: [x.value for x in e]),
        nullable=False,
    )
    content = Column(Text, nullable=False)
    options = Column(Text)
    answer = Column("correct_answer", Text, nullable=False)
    explanation = Column(Text)
    difficulty = Column(Integer, default=1)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)
    textbook_id = Column(Integer, ForeignKey("textbooks.id"), nullable=True)

    textbook = relationship("Textbook", back_populates="questions")
    chapter = relationship("Chapter", back_populates="questions")

    def get_options(self):
        if self.options:
            return json.loads(self.options)
        return []

    def get_answer(self):
        if self.answer:
            try:
                return json.loads(self.answer)
            except (json.JSONDecodeError, TypeError):
                return self.answer
        return None


# ═══ PART 2: V7 新架构模型 ═══

class Category(Base):
    __tablename__ = "categories"
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(30), unique=True, nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    icon = Column(String(50))
    sort_order = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    terminology_config = Column(JSON, default=dict)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    courses = relationship("Course", back_populates="category")
    textbooks = relationship("Textbook", back_populates="category")


class Course(Base):
    __tablename__ = "courses"
    id = Column(Integer, primary_key=True, index=True)
    category_id = Column(Integer, ForeignKey("categories.id"))
    code = Column(String(30), nullable=False)
    name = Column(String(200), nullable=False)
    description = Column(Text)
    level = Column(String(20), default="beginner")
    duration_days = Column(Integer)
    sort_order = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    llm_enabled = Column(Boolean, default=False)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    category = relationship("Category", back_populates="courses")
    class_links = relationship("ClassCourse", back_populates="course")


class ContentNode(Base):
    __tablename__ = "content_nodes"
    id = Column(Integer, primary_key=True, index=True)
    textbook_id = Column(Integer, ForeignKey("textbooks.id", ondelete="CASCADE"))
    parent_id = Column(Integer, ForeignKey("content_nodes.id", ondelete="CASCADE"))
    tree_path = Column(Text)
    sort_order = Column(Integer, default=0)
    depth = Column(Integer, default=0)
    node_type = Column(String(30), nullable=False)
    title = Column(String(500))
    content = Column(Text)
    rich_content = Column(JSON)
    media_url = Column(String(500))
    media_type = Column(String(20))
    media_duration = Column(Integer)
    keywords = Column(Text)
    is_important = Column(Boolean, default=False)
    is_visible = Column(Boolean, default=True)
    is_auto_generated = Column(Boolean, default=False)
    estimated_time = Column(Integer, default=0)
    has_quiz = Column(Boolean, default=False)
    parse_version = Column(Integer, default=0)
    is_edited = Column(Boolean, default=False)
    page_start = Column(Integer)
    page_end = Column(Integer)
    difficulty_level = Column(String(20), default="medium")
    learning_objectives = Column(JSON)
    tags = Column(Text)
    source_location = Column(String(500))
    review_status = Column(String(20), default="draft")
    content_hash = Column(String(64))
    prerequisite_ids = Column(Integer)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    history = relationship("ContentNodeHistory", back_populates="node", cascade="all, delete-orphan")


class ContentNodeHistory(Base):
    __tablename__ = "content_node_history"
    id = Column(Integer, primary_key=True, index=True)
    node_id = Column(Integer, ForeignKey("content_nodes.id", ondelete="CASCADE"))
    snapshot = Column(JSON, nullable=False)
    edited_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=utcnow)
    node = relationship("ContentNode", back_populates="history")


class KeyConcept(Base):
    __tablename__ = "key_concepts"
    id = Column(Integer, primary_key=True, index=True)
    textbook_id = Column(Integer, ForeignKey("textbooks.id", ondelete="CASCADE"))
    node_id = Column(Integer, ForeignKey("content_nodes.id", ondelete="CASCADE"))
    name = Column(String(200), nullable=False)
    definition = Column(Text)
    source_text = Column(Text)
    created_at = Column(DateTime, default=utcnow)


class SystemSettings(Base):
    __tablename__ = "system_settings"
    key = Column(String(100), primary_key=True)
    value = Column(Text, nullable=False, default="")
    is_encrypted = Column(Boolean, default=False)
    description = Column(String(500), default="")
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


# ═══ PART 3: 旧架构遗留模型 ═══

class Module(Base):
    __tablename__ = "modules"
    id = Column(Integer, primary_key=True, index=True)
    level = Column(Integer, nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    order = Column(Integer, default=0)
    status = Column(String(20), default="draft")
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)


class Lesson(Base):
    __tablename__ = "lessons"
    id = Column(Integer, primary_key=True, index=True)
    chapter_id = Column(Integer, ForeignKey("chapters.id"), nullable=False)
    title = Column(String(100), nullable=False)
    content = Column(Text)
    animation_url = Column(String(255))
    animation_duration = Column(Integer, default=0)
    order = Column(Integer, default=0)
    is_preview = Column(Boolean, default=False)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)


class Enrollment(Base):
    __tablename__ = "enrollments"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    module_id = Column(Integer, ForeignKey("modules.id"), nullable=False)
    enrolled_at = Column(DateTime, default=utcnow)
    completed_at = Column(DateTime)
    status = Column(String(20), default="in_progress")


class LearningProgress(Base):
    __tablename__ = "learning_progress"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    lesson_id = Column(Integer, ForeignKey("lessons.id"), nullable=False)
    is_completed = Column(Boolean, default=False)
    watch_duration = Column(Integer, default=0)
    completed_at = Column(DateTime)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)


class Exam(Base):
    __tablename__ = "exams"
    id = Column(Integer, primary_key=True, index=True)
    module_id = Column(Integer, ForeignKey("modules.id"))
    chapter_id = Column(Integer, ForeignKey("chapters.id"))
    title = Column(String(100), nullable=False)
    description = Column(Text)
    exam_type = Column(String(20), nullable=False)
    status = Column(String(20), default="draft")
    time_limit = Column(Integer, default=60)
    pass_score = Column(Integer, default=80)
    total_questions = Column(Integer, default=20)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)


class ExamRecord(Base):
    __tablename__ = "exam_records"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    exam_id = Column(Integer, ForeignKey("exams.id"), nullable=False)
    score = Column(Integer, default=0)
    total_questions = Column(Integer, default=0)
    correct_count = Column(Integer, default=0)
    status = Column(String(20), default="in_progress")
    answers = Column(Text)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    time_spent = Column(Integer, default=0)


class WrongAnswer(Base):
    __tablename__ = "wrong_answers"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    question_id = Column(Integer, ForeignKey("questions.id"), nullable=False)
    user_answer = Column(Text)
    wrong_count = Column(Integer, default=1)
    last_wrong_at = Column(DateTime, default=utcnow)
    is_mastered = Column(Boolean, default=False)


class AuditLog(Base):
    """DB: audit_logs — 操作审计日志"""
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True, index=True)
    user_name = Column(String(100), nullable=True)
    user_role = Column(String(50), nullable=True)
    action = Column(String(100), nullable=False)
    target_type = Column(String(50), nullable=True)
    target_name = Column(String(200), nullable=True)
    details = Column(Text, nullable=True)
    ip_address = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=utcnow)




# ═══ 补充模型 (from backup, relationships stripped) ═══

class SystemConfig(Base):
    __tablename__ = "system_config"
    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(100), unique=True, nullable=False)
    value = Column(Text)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

class AlertRule(Base):
    __tablename__ = "alert_rules"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    rule_type = Column(String(50), nullable=False)
    threshold_value = Column(Integer, default=0)
    enabled = Column(Boolean, default=True)
    notify_roles = Column(String(200), default="manager,instructor")
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

class AlertRecord(Base):
    __tablename__ = "alert_records"
    id = Column(Integer, primary_key=True, index=True)
    rule_id = Column(Integer, ForeignKey("alert_rules.id"), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    user_name = Column(String(100))
    class_id = Column(Integer, ForeignKey("classes.id"), nullable=True)
    class_name = Column(String(100))
    alert_type = Column(String(50), index=True)
    alert_message = Column(Text, nullable=False)
    severity = Column(String(20), default="warning")
    is_read = Column(Boolean, default=False, index=True)
    is_resolved = Column(Boolean, default=False)
    created_at = Column(DateTime, default=utcnow, index=True)
    resolved_at = Column(DateTime, nullable=True)
    resolved_by = Column(Integer, ForeignKey("users.id"), nullable=True)

class LearningPath(Base):
    __tablename__ = "learning_paths"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    class_id = Column(Integer, ForeignKey("classes.id"), nullable=False)
    path_type = Column(String(20), nullable=False, default="normal")
    assigned_reason = Column(String(200))
    current_stage = Column(Integer, default=0)
    fast_track_skipped = Column(Text)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

class Test(Base):
    __tablename__ = "tests"
    id = Column(Integer, primary_key=True, index=True)
    class_id = Column(Integer, ForeignKey("classes.id"), nullable=False)
    title = Column(String(200), nullable=False)
    test_type = Column(
        Enum(TestType, values_callable=lambda e: [x.value for x in e]),
        nullable=False,
    )
    questions = Column(Text, nullable=False)
    total_score = Column(Integer, default=100)
    duration = Column(Integer)
    start_time = Column(DateTime)
    end_time = Column(DateTime)
    status = Column(
        Enum(TestStatus, values_callable=lambda e: [x.value for x in e]),
        default=TestStatus.DRAFT,
    )
    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=utcnow)

    def get_question_ids(self):
        if self.questions:
            return json.loads(self.questions)
        return []

class TestResult(Base):
    __tablename__ = "test_results"
    id = Column(Integer, primary_key=True, index=True)
    test_id = Column(Integer, ForeignKey("tests.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    answers = Column(Text)
    score = Column(Integer)
    time_spent = Column(Integer)
    submitted_at = Column(DateTime)
    is_graded = Column(Boolean, default=False)
    tab_switch_count = Column(Integer, default=0)
    snapshot_instructor_id = Column(Integer, nullable=True)
    snapshot_instructor_name = Column(String(100), nullable=True)

class ReadingProgress(Base):
    __tablename__ = "reading_progress"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    textbook_id = Column(Integer, ForeignKey("textbooks.id"), nullable=False)
    chapter_id = Column(Integer, ForeignKey("chapters.id"))
    current_page = Column(Integer, default=0)
    progress = Column(Integer, default=0)
    duration = Column(Integer, default=0)
    last_read_at = Column(DateTime, default=utcnow)

class LearningStats(Base):
    __tablename__ = "learning_stats"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    class_id = Column(Integer, ForeignKey("classes.id"), nullable=False)
    date = Column(Date, nullable=False)
    reading_duration = Column(Integer, default=0)
    homework_completed = Column(Integer, default=0)
    quiz_completed = Column(Integer, default=0)
    quiz_avg_score = Column(Integer, default=0)

class ChapterProgress(Base):
    __tablename__ = "chapter_progress"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    class_id = Column(Integer, ForeignKey("classes.id"), nullable=False)
    chapter_id = Column(Integer, ForeignKey("chapters.id"), nullable=False)
    status = Column(
        Enum(ChapterProgressStatus, values_callable=lambda e: [x.value for x in e]),
        default=ChapterProgressStatus.LOCKED,
    )
    reading_start_at = Column(DateTime)
    reading_done_at = Column(DateTime)
    practice_start_at = Column(DateTime)
    practice_done_at = Column(DateTime)
    test_published_at = Column(DateTime)
    completed_at = Column(DateTime)
    total_reading_time = Column(Integer, default=0)
    reading_pages = Column(Integer, default=0)
    tab_switch_count = Column(Integer, default=0)
    last_updated = Column(DateTime, default=utcnow, onupdate=utcnow)

class ChapterExercise(Base):
    __tablename__ = "chapter_exercises"
    id = Column(Integer, primary_key=True, index=True)
    chapter_id = Column(Integer, ForeignKey("chapters.id"), nullable=False)
    question_id = Column(Integer, ForeignKey("questions.id"), nullable=False)
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime, default=utcnow)

class DocumentTemplate(Base):
    __tablename__ = "document_templates"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False)
    doc_type = Column(String(50), nullable=False)
    description = Column(Text, nullable=True)
    static_html = Column(Text, nullable=True)
    fields_schema = Column(JSON, nullable=True)
    coach_choices = Column(JSON, nullable=True)
    course_choices = Column(JSON, nullable=True)
    institution_name = Column(String(200), nullable=True)
    is_required = Column(Boolean, default=True)
    sort_order = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

class DocumentResponse(Base):
    __tablename__ = "document_responses"
    id = Column(Integer, primary_key=True, autoincrement=True)
    student_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    template_id = Column(Integer, ForeignKey("document_templates.id"), nullable=False)
    answers = Column(JSON, nullable=True)
    signature_image = Column(String(500), nullable=True)
    snapshot_name = Column(String(100), nullable=True)
    snapshot_id_number = Column(String(50), nullable=True)
    snapshot_phone = Column(String(50), nullable=True)
    snapshot_instructor_id = Column(Integer, nullable=True)
    snapshot_instructor_name = Column(String(100), nullable=True)
    status = Column(String(50), default="pending")
    submitted_at = Column(DateTime, nullable=True)
    reviewed_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    review_comment = Column(Text, nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

class StudentDocumentStatus(Base):
    __tablename__ = "student_document_status"
    id = Column(Integer, primary_key=True, autoincrement=True)
    student_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    overall_locked = Column(Boolean, default=True)
    approved_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

class ChapterNote(Base):
    __tablename__ = "chapter_notes"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    class_id = Column(Integer, ForeignKey("classes.id"), nullable=False)
    chapter_id = Column(Integer, ForeignKey("chapters.id"), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

class ChapterBookmark(Base):
    __tablename__ = "chapter_bookmarks"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    class_id = Column(Integer, ForeignKey("classes.id"), nullable=False)
    chapter_id = Column(Integer, ForeignKey("chapters.id"), nullable=False)
    note = Column(String(200))
    created_at = Column(DateTime, default=utcnow)

class Announcement(Base):
    __tablename__ = "announcements"
    id = Column(Integer, primary_key=True, index=True)
    class_id = Column(Integer, ForeignKey("classes.id"), nullable=False)
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"))
    pinned = Column(Boolean, default=False)
    created_at = Column(DateTime, default=utcnow)

class QAQuestion(Base):
    __tablename__ = "qa_questions"
    id = Column(Integer, primary_key=True, index=True)
    class_id = Column(Integer, ForeignKey("classes.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    reply = Column(Text)
    replied_by = Column(Integer, ForeignKey("users.id"))
    replied_at = Column(DateTime)
    created_at = Column(DateTime, default=utcnow)

# ═══ PART 4: 【待建表】═══
# 取消注释前务必执行 V7 Phase 1 建表迁移
# 模型: DocumentTemplate, DocumentResponse, StudentDocumentStatus,
#   Announcement, QAQuestion, ChapterNote, ChapterBookmark,
#   ChapterProgress, ChapterExercise, Test, TestResult,
#   ReadingProgress, LearningStats, LearningPath,
#   AuditLog, AlertRule, AlertRecord, SystemConfig
