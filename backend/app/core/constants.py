"""
常量定义
"""
from enum import Enum


class UserRole(str, Enum):
    """用户角色"""
    STUDENT = "student"
    INSTRUCTOR = "instructor"
    ADMIN = "admin"
    MANAGER = "manager"


class CourseStatus(str, Enum):
    """课程状态"""
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class QuestionType(str, Enum):
    """题目类型"""
    SINGLE = "single"
    MULTIPLE = "multiple"
    TRUE_FALSE = "true_false"
    SHORT = "short"


class ExamType(str, Enum):
    """考试类型"""
    CHAPTER = "chapter"
    FINAL = "final"


class ExamStatus(str, Enum):
    """考试状态"""
    DRAFT = "draft"
    PUBLISHED = "published"
    CLOSED = "closed"


class LevelName:
    """等级名称"""
    ONE_STAR = "一级潜水员"
    TWO_STAR = "二级潜水员"
    THREE_STAR = "三级潜水员"
    FOUR_STAR = "四级潜水员"
    FIVE_STAR = "五级潜水员"

    @classmethod
    def get_name(cls, level: int) -> str:
        names = ["", cls.ONE_STAR, cls.TWO_STAR, cls.THREE_STAR, cls.FOUR_STAR, cls.FIVE_STAR]
        return names[level] if 1 <= level <= 5 else f"{level}级潜水员"


# 分页默认值
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100

# 考试配置
DEFAULT_EXAM_TIME_LIMIT = 30  # 分钟
DEFAULT_PASSING_SCORE = 80
DEFAULT_MAX_ATTEMPTS = 3

# 潜水等级配置
LEVEL_CONFIG = {
    1: {"name": "一级潜水员", "description": "基础入门级"},
    2: {"name": "二级潜水员", "description": "进阶开放水域级"},
    3: {"name": "三级潜水员", "description": "公共安全潜水基础级"},
    4: {"name": "四级潜水员", "description": "应急救援与专项技术级"},
    5: {"name": "五级潜水员", "description": "技术负责人/教练预备级"},
}

# 文件上传配置
ALLOWED_IMAGE_TYPES = ["image/jpeg", "image/png", "image/gif", "image/webp"]
ALLOWED_VIDEO_TYPES = ["video/mp4", "video/webm"]
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB
