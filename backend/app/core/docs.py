"""
API 文档和元数据
"""

API_DOCS = {
    "title": "消防潜水教学平台 API",
    "version": "1.0.0",
    "description": "面向消防系统的专业潜水在线教学平台 API 文档",
    "contact": {
        "name": "技术支持",
        "email": "support@example.com"
    },
    "license": {
        "name": "内部使用"
    }
}

# API 端点文档
ENDPOINTS = {
    "auth": {
        "login": {
            "method": "POST",
            "path": "/api/v1/auth/login",
            "description": "用户登录",
            "params": {
                "phone": "手机号",
                "password": "密码"
            }
        },
        "register": {
            "method": "POST",
            "path": "/api/v1/auth/register",
            "description": "用户注册",
            "params": {
                "phone": "手机号",
                "password": "密码",
                "real_name": "真实姓名"
            }
        }
    },
    "courses": {
        "list": {
            "method": "GET",
            "path": "/api/v1/courses/modules",
            "description": "获取课程模块列表"
        },
        "detail": {
            "method": "GET",
            "path": "/api/v1/courses/modules/{module_id}",
            "description": "获取课程模块详情"
        },
        "chapters": {
            "method": "GET",
            "path": "/api/v1/courses/chapters/{module_id}",
            "description": "获取章节列表"
        },
        "lessons": {
            "method": "GET",
            "path": "/api/v1/courses/lessons/{chapter_id}",
            "description": "获取课时列表"
        }
    },
    "exams": {
        "list": {
            "method": "GET",
            "path": "/api/v1/exams",
            "description": "获取考试列表"
        },
        "questions": {
            "method": "GET",
            "path": "/api/v1/exams/{exam_id}/questions",
            "description": "获取考试题目"
        },
        "submit": {
            "method": "POST",
            "path": "/api/v1/exams/{exam_id}/submit",
            "description": "提交考试答卷"
        }
    },
    "instructor": {
        "students": {
            "method": "GET",
            "path": "/api/v1/instructor/students",
            "description": "获取学员列表"
        },
        "scores": {
            "method": "GET",
            "path": "/api/v1/instructor/scores",
            "description": "获取成绩统计"
        },
        "questions": {
            "method": "GET",
            "path": "/api/v1/instructor/questions",
            "description": "获取题库"
        }
    }
}

# 错误代码
ERROR_CODES = {
    400: "请求参数错误",
    401: "未授权",
    403: "禁止访问",
    404: "资源不存在",
    422: "数据验证失败",
    500: "服务器内部错误",
    503: "服务不可用"
}
