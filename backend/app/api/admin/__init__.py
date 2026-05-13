"""
管理员API - 班级制培训管理系统
路由入口 - 注册所有子模块

注意: 共享导入/依赖/Schema 见 shared.py
      端点定义见 admin_*.py 各子模块
"""
from fastapi import APIRouter

from .admin_announcements import router as announcements_router
from .admin_categories import router as categories_router
from .admin_class_courses import router as class_courses_router

# ============================
# 子路由模块导入 (12 sub-modules)
# ============================
from .admin_classes import router as classes_router
from .admin_companies import router as companies_router
from .admin_content_nodes import router as content_nodes_router
from .admin_courses import router as courses_router
from .admin_instructors import router as instructors_router
from .admin_learning import router as learning_router
from .admin_llm_config import router as llm_config_router
from .admin_people import router as people_router
from .admin_preview import router as preview_router
from .admin_questions import router as questions_router
from .admin_settings import router as settings_router
from .admin_student_preview import router as student_preview_router
from .admin_textbooks import router as textbooks_router
from .admin_users import router as users_router
from .shared import *

router = APIRouter(prefix="/admin", tags=["管理员"])

# ============================
# 注册子路由
# ============================
router.include_router(classes_router)
router.include_router(companies_router)
router.include_router(instructors_router)
router.include_router(people_router)
router.include_router(questions_router)
router.include_router(settings_router)
router.include_router(users_router)
router.include_router(preview_router)
router.include_router(student_preview_router)
router.include_router(textbooks_router)
router.include_router(announcements_router)
router.include_router(learning_router)
router.include_router(categories_router)
router.include_router(courses_router)
router.include_router(content_nodes_router)
router.include_router(llm_config_router)
router.include_router(class_courses_router)
