# 安全审计报告 — diving.school API

**生成时间**: 2026-05-04 00:12 (Asia/Shanghai)
**审计范围**: `/Users/wjjmac/localserver/diving.school/backend/app/api/`
**版本**: FastAPI + SQLAlchemy Async + JWT v3

---

## 1. 端点×角色矩阵

### 1.1 认证模块 (auth_v2.py) — 路由前缀 `/api/v1/auth`

| 端点 | 方法 | 认证要求 | 角色守卫 | 功能 | 安全状态 |
|------|------|---------|---------|------|---------|
| `/auth/login` | POST | 无 | 无 | 多角色统一登录（admin/instructor/manager/student） | ✅ 公开 |
| `/auth/refresh` | POST | 无（token in body） | 无 | 刷新访问令牌 | ✅ 公开 |
| `/auth/me` | GET | 是 | `get_current_user` | 获取当前用户信息 | ✅ |
| `/auth/logout` | POST | 无 | 无 | 登出（客户端清除 token） | ⚠️ 无认证要求但无害 |
| `/auth/change-password` | POST | 是 | `get_current_user` | 修改密码（含强度校验） | ✅ |
| `/auth/profile` | POST | 是 | `get_current_user` | 更新个人信息（姓名/电话） | ✅ |

---

### 1.2 管理员模块 (admin/*.py) — 路由前缀 `/api/v1/admin`

#### 1.2.1 班级管理 (admin_classes.py) — require_admin (ADMIN + MANAGER)

| 端点 | 方法 | 认证要求 | 角色守卫 | 功能 | 安全状态 |
|------|------|---------|---------|------|---------|
| `/admin/classes` | GET | 是 | `require_admin` | 班级列表（可按状态筛选） | ✅ |
| `/admin/classes` | POST | 是 | `require_admin` | 创建班级（含教练/学员批量导入） | ✅ |
| `/admin/classes/{class_id}` | GET | 是 | `require_admin` | 班级详情（含成员/教材/文书统计） | ✅ |
| `/admin/classes/{class_id}` | PUT | 是 | `require_admin` | 更新班级信息（名称/时间/课程） | ✅ |
| `/admin/classes/{class_id}` | DELETE | 是 | `require_admin` | 删除班级（级联清理关联数据） | ✅ |
| `/admin/classes/{class_id}/analytics` | GET | 是 | `require_admin` | 班级分析（学员进度+成绩） | ✅ |
| `/admin/classes/{class_id}/documents` | GET | 是 | `require_admin` | 班级关联文书列表 | ✅ |
| `/admin/classes/{class_id}/documents/{document_id}` | DELETE | 是 | `require_admin` | 移除班级关联文书 | ✅ |
| `/admin/classes/{class_id}/start` | POST | 是 | `require_admin` | 启动班级（状态→ACTIVE） | ✅ |
| `/admin/classes/{class_id}/end` | POST | 是 | `require_admin` | 结班（状态→ENDED） | ✅ |
| `/admin/classes/{class_id}/members` | GET | 是 | `require_admin` | 班级成员列表（可按角色筛选） | ✅ |
| `/admin/classes/{class_id}/members` | POST | 是 | `require_admin` | 添加班级成员（选已有或新建） | ⚠️ 创建用户时密码弱 |
| `/admin/classes/{class_id}/members/batch` | POST | 是 | `require_admin` | 批量导入学员 | ⚠️ 创建用户时密码弱 |
| `/admin/classes/{class_id}/members/{member_id}` | DELETE | 是 | `require_admin` | 移除班级成员（按member_id） | ✅ |
| `/admin/classes/{class_id}/members/user_id/{user_id}` | DELETE | 是 | `require_admin` | 移除班级成员（按user_id） | ✅ |
| `/admin/classes/{class_id}/student/{user_id}/progress` | GET | 是 | `require_admin` | 查看学员章节进度 | ✅ |
| `/admin/classes/{class_id}/textbooks` | GET | 是 | `require_admin` | 班级关联教材列表 | ✅ |
| `/admin/classes/{class_id}/textbooks/interactive` | GET | 是 | `require_admin` | 班级互动式教材列表 | ✅ |
| `/admin/classes/{class_id}/textbooks/interactive/{textbook_id}` | POST | 是 | `require_admin` | 添加互动式教材到班级 | ✅ |
| `/admin/classes/{class_id}/textbooks/interactive/{textbook_id}` | DELETE | 是 | `require_admin` | 移除班级互动式教材 | ✅ |
| `/admin/classes/{class_id}/textbooks/{textbook_id}` | POST | 是 | `require_admin` | 添加教材到班级 | ✅ |
| `/admin/classes/{class_id}/textbooks/{textbook_id}` | DELETE | 是 | `require_admin` | 移除班级教材 | ✅ |

#### 1.2.2 用户管理 (admin_users.py) — require_admin

| 端点 | 方法 | 认证要求 | 角色守卫 | 功能 | 安全状态 |
|------|------|---------|---------|------|---------|
| `/admin/users` | GET | 是 | `require_admin` | 用户列表（可按角色筛选） | ✅ |

#### 1.2.3 学员/人员管理 (admin_people.py) — require_admin

| 端点 | 方法 | 认证要求 | 角色守卫 | 功能 | 安全状态 |
|------|------|---------|---------|------|---------|
| `/admin/people` | GET | 是 | `require_admin` | 人员列表（可按角色筛选） | ✅ |
| `/admin/people` | POST | 是 | `require_admin` | 创建人员 | ⚠️ 默认密码=手机后6位 |
| `/admin/people/{person_id}` | PUT | 是 | `require_admin` | 更新人员信息 | ✅ |
| `/admin/people/{person_id}/reset-password` | POST | 是 | `require_admin` | 重置密码（仅学员/干部） | ✅ |
| `/admin/people/{person_id}` | DELETE | 是 | `require_admin` | 删除人员（硬删除） | ✅ |
| `/admin/students` | GET | 是 | `require_admin` | 学员列表（分页别名） | ✅ |
| `/admin/students/{student_id}` | GET | 是 | `require_admin` | 学员详情（别名） | ✅ |

#### 1.2.4 单位管理 (admin_companies.py) — require_admin

| 端点 | 方法 | 认证要求 | 角色守卫 | 功能 | 安全状态 |
|------|------|---------|---------|------|---------|
| `/admin/companies` | GET | 是 | `require_admin` | 单位列表 | ✅ |
| `/admin/companies` | POST | 是 | `require_admin` | 创建单位 | ✅ |
| `/admin/companies/{company_id}` | PUT | 是 | `require_admin` | 更新单位信息 | ✅ |
| `/admin/companies/{company_id}` | DELETE | 是 | `require_admin` | 删除单位（可能影响关联用户） | ⚠️ 未级联处理 |

#### 1.2.5 教练管理 (admin_instructors.py) — require_admin

| 端点 | 方法 | 认证要求 | 角色守卫 | 功能 | 安全状态 |
|------|------|---------|---------|------|---------|
| `/admin/instructors` | GET | 是 | `require_admin` | 教练列表 | ✅ |
| `/admin/instructors` | POST | 是 | `require_admin` | 创建教练 | ⚠️ 默认密码=身份证后6位 |
| `/admin/instructors/{instructor_id}` | PUT | 是 | `require_admin` | 更新教练信息 | ✅ |
| `/admin/instructors/{instructor_id}` | DELETE | 是 | `require_admin` | 删除教练（硬删除+级联清理） | ✅ |
| `/admin/instructors/{instructor_id}/reset-password` | POST | 是 | `require_admin` | 重置教练密码 | ✅ |

#### 1.2.6 教材管理 (admin_textbooks.py) — require_admin

| 端点 | 方法 | 认证要求 | 角色守卫 | 功能 | 安全状态 |
|------|------|---------|---------|------|---------|
| `/admin/textbooks` | GET | 是 | `require_admin` | 教材列表 | ✅ |
| `/admin/textbooks` | POST | 是 | `require_admin` | 创建教材 | ✅ |
| `/admin/textbooks/{textbook_id}` | GET | 是 | `require_admin` | 教材详情 | ✅ |
| `/admin/textbooks/{textbook_id}` | PUT | 是 | `require_admin` | 更新教材 | ✅ |
| `/admin/textbooks/{textbook_id}` | DELETE | 是 | `require_admin` | 删除教材（级联清理） | ✅ |
| `/admin/textbooks/{textbook_id}/chapters` | GET | 是 | `require_admin` | 章节列表 | ✅ |
| `/admin/textbooks/{textbook_id}/import` | POST | 是 | `require_admin` | 导入Word教材（解析章节） | ✅ |
| `/admin/textbooks/{textbook_id}/upload-pdf` | POST | 是 | `require_admin` | 上传PDF教材（自动切图） | ✅ |
| `/admin/textbooks/{textbook_id}/pages` | GET | 是 | `require_admin` | 页面列表 | ✅ |
| `/admin/textbooks/{textbook_id}/pages` | DELETE | 是 | `require_admin` | 删除所有页面 | ✅ |
| `/admin/textbooks/{textbook_id}/pages/management` | GET | 是 | `require_admin` | 页面/章节管理（智能识别格式） | ✅ |
| `/admin/textbooks/{textbook_id}/pages/visibility` | PUT | 是 | `require_admin` | 批量设置页面可见性 | ✅ |
| `/admin/textbooks/{textbook_id}/restore-document` | POST | 是 | `require_admin` | 从源文档恢复教材 | ✅ |
| `/admin/textbooks/{textbook_id}/ai-structure` | GET | 是 | `require_admin` | AI教材结构 | ✅ |
| `/admin/textbooks/{textbook_id}/ai-glossary` | GET | 是 | `require_admin` | AI术语表 | ✅ |
| `/admin/textbooks/{textbook_id}/ai-glossary/{kp_id}` | GET | 是 | `require_admin` | AI术语详情 | ✅ |
| `/admin/textbooks/{textbook_id}/ai-page/{page_id}` | GET | 是 | `require_admin` | AI页面内容 | ✅ |
| `/admin/textbooks/ai-regenerate` | POST | 是 | `require_admin` | AI重新生成 | ✅ |
| `/admin/textbooks/interactive` | GET | 是 | `require_admin` | 互动式教材列表 | ✅ |
| `/admin/textbooks/{textbook_id}/interactive` | GET | 是 | `require_admin` | 互动式教材详情 | ✅ |
| `/admin/textbooks/{textbook_id}/interactive/structure` | GET | 是 | `require_admin` | 互动式结构 | ✅ |
| `/admin/textbooks/{textbook_id}/interactive/history` | GET | 是 | `require_admin` | 互动式历史版本 | ✅ |
| `/admin/textbooks/{textbook_id}/convert-interactive` | POST | 是 | `require_admin` | 转换为互动式教材 | ✅ |
| `/admin/textbooks/{textbook_id}/interactive/redo` | POST | 是 | `require_admin` | 重做互动式转换 | ✅ |
| `/admin/textbooks/{textbook_id}/interactive/undo` | POST | 是 | `require_admin` | 撤销（待实现） | ✅ |
| `/admin/textbooks/{textbook_id}/interactive/sections/{section_id}` | PUT | 是 | `require_admin` | 编辑互动式章节 | ✅ |
| `/admin/textbooks/{textbook_id}/interactive/sections/{section_id}` | DELETE | 是 | `require_admin` | 删除互动式章节 | ✅ |
| `/admin/textbooks/{textbook_id}/interactive/sections/{section_id}/hide` | POST | 是 | `require_admin` | 隐藏章节 | ✅ |
| `/admin/textbooks/{textbook_id}/interactive/sections/{section_id}/unhide` | POST | 是 | `require_admin` | 取消隐藏章节 | ✅ |
| `/admin/textbooks/{textbook_id}/interactive/sections/split` | POST | 是 | `require_admin` | 拆分章节 | ✅ |
| `/admin/textbooks/{textbook_id}/interactive/sections/merge` | POST | 是 | `require_admin` | 合并章节 | ✅ |
| `/admin/textbooks/{textbook_id}/interactive/sections/reorder` | POST | 是 | `require_admin` | 重新排序章节 | ✅ |
| `/admin/textbooks/{textbook_id}/interactive/sections/{section_id}/units/{unit_id}` | PUT | 是 | `require_admin` | 编辑单元 | ✅ |
| `/admin/textbooks/{textbook_id}/interactive/units/{unit_id}` | DELETE | 是 | `require_admin` | 删除单元 | ✅ |
| `/admin/textbooks/{textbook_id}/interactive/units/{unit_id}/hide` | POST | 是 | `require_admin` | 隐藏单元 | ✅ |
| `/admin/textbooks/{textbook_id}/interactive/units/{unit_id}/unhide` | POST | 是 | `require_admin` | 取消隐藏单元 | ✅ |
| `/admin/textbooks/{textbook_id}/interactive/units/delete` | POST | 是 | `require_admin` | 批量删除单元 | ✅ |
| `/admin/textbooks/{textbook_id}/interactive/units/merge` | POST | 是 | `require_admin` | 合并单元 | ✅ |

#### 1.2.7 题目管理 (admin_questions.py) — require_admin

| 端点 | 方法 | 认证要求 | 角色守卫 | 功能 | 安全状态 |
|------|------|---------|---------|------|---------|
| `/admin/questions` | GET | 是 | `require_admin` | 题目列表（可分页/筛选） | ✅ |
| `/admin/questions` | POST | 是 | `require_admin` | 创建题目 | ✅ |
| `/admin/questions/import` | POST | 是 | `require_admin` | 批量导入题目（TSV） | ✅ |
| `/admin/questions/{question_id}` | DELETE | 是 | `require_admin` | 删除题目 | ✅ |

#### 1.2.8 系统设置 (admin_settings.py) — require_admin

| 端点 | 方法 | 认证要求 | 角色守卫 | 功能 | 安全状态 |
|------|------|---------|---------|------|---------|
| `/admin/system-settings` | GET | 是 | `require_admin` | 读取系统配置 | ⚠️ MANAGER可见 |
| `/admin/settings` | GET | 是 | `require_admin` | 系统设置（别名） | ⚠️ MANAGER可见 |
| `/admin/settings` | PUT | 是 | `require_admin` | 更新系统设置（别名） | ⚠️ MANAGER可写 |
| `/admin/system-settings` | PUT | 是 | `require_admin` | 更新系统配置 | ⚠️ MANAGER可写 |
| `/admin/alert-rules` | GET | 是 | `require_admin` | 预警规则列表 | ⚠️ MANAGER可见 |
| `/admin/alert-rules` | POST | 是 | `require_admin` | 创建预警规则 | ⚠️ MANAGER可写 |
| `/admin/alert-rules/{rule_id}` | PUT | 是 | `require_admin` | 更新预警规则 | ⚠️ MANAGER可写 |
| `/admin/alert-rules/{rule_id}` | DELETE | 是 | `require_admin` | 删除预警规则 | ⚠️ MANAGER可删 |
| `/admin/audit-logs` | GET | 是 | `require_admin` | 审计日志列表 | ⚠️ MANAGER可见 |
| `/admin/audit-logs/stats` | GET | 是 | `require_admin` | 审计统计 | ⚠️ MANAGER可见 |
| `/admin/dashboard` | GET | 是 | `require_admin` | 管理后台仪表盘 | ⚠️ MANAGER可见 |
| `/admin/alert-records` | GET | 是 | `require_admin` | 告警记录列表 | ⚠️ MANAGER可见 |

#### 1.2.9 公告管理 (admin_announcements.py) — require_admin

| 端点 | 方法 | 认证要求 | 角色守卫 | 功能 | 安全状态 |
|------|------|---------|---------|------|---------|
| `/admin/announcements` | GET | 是 | `require_admin` | 公告列表（可分页/筛选） | ✅ |
| `/admin/announcements` | POST | 是 | `require_admin` | 创建公告 | ✅ |
| `/admin/announcements/{ann_id}` | PUT | 是 | `require_admin` | 更新公告 | ✅ |
| `/admin/announcements/{ann_id}` | DELETE | 是 | `require_admin` | 删除公告 | ✅ |

#### 1.2.10 教材预览 (admin_preview.py) — require_admin

| 端点 | 方法 | 认证要求 | 角色守卫 | 功能 | 安全状态 |
|------|------|---------|---------|------|---------|
| `/admin/textbook-preview/chapters` | GET | 是 | `require_admin` | 教材章节预览（树形结构） | ✅ |
| `/admin/textbook-preview/chapters/{chapter_id}` | GET | 是 | `require_admin` | 章节内容预览 | ✅ |
| `/admin/textbook-preview/chapters/{chapter_id}` | PUT | 是 | `require_admin` | 更新章节内容 | ✅ |

#### 1.2.11 学员预览 (admin_student_preview.py) — require_admin

| 端点 | 方法 | 认证要求 | 角色守卫 | 功能 | 安全状态 |
|------|------|---------|---------|------|---------|
| `/admin/student-preview/{student_id}/chapters` | GET | 是 | `require_admin` | 学员章节进度预览 | ✅ |
| `/admin/student-preview/{student_id}/chapters/{chapter_id}` | GET | 是 | `require_admin` | 学员章节内容预览 | ✅ |

#### 1.2.12 学习路径与对比 (admin_learning.py) — require_admin

| 端点 | 方法 | 认证要求 | 角色守卫 | 功能 | 安全状态 |
|------|------|---------|---------|------|---------|
| `/admin/learning-paths` | GET | 是 | `require_admin` | 学习路径列表 | ✅ |
| `/admin/comparison` | GET | 是 | `require_admin` | 跨班级对比分析 | ✅ |

#### 1.2.13 课程管理 (courses.py) — 路由前缀 `/api/v1/admin/courses`

| 端点 | 方法 | 认证要求 | 角色守卫 | 功能 | 安全状态 |
|------|------|---------|---------|------|---------|
| `/admin/courses` | GET | 是 | `require_admin` (router) | 课程列表 | ✅ |
| `/admin/courses` | POST | 是 | `require_admin` | 创建课程 | ✅ |
| `/admin/courses/{course_id}` | GET | 是 | `require_admin` | 课程详情 | ✅ |
| `/admin/courses/{course_id}` | PUT | 是 | `require_admin` | 更新课程 | ✅ |
| `/admin/courses/{course_id}` | DELETE | 是 | `require_admin` | 停用课程（软删除） | ✅ |
| `/admin/courses/{course_id}/restore` | POST | 是 | `require_admin` | 恢复课程 | ✅ |
| `/admin/courses/init-defaults` | POST | 是 | `require_admin` | 初始化默认课程 | ✅ |

---

### 1.3 文书模块 (documents.py) — 路由前缀 `/api/v1`

| 端点 | 方法 | 认证要求 | 角色守卫 | 功能 | 安全状态 |
|------|------|---------|---------|------|---------|
| `/admin/document-templates` | GET | 是 | `require_staff` | 文书模板列表（含初始化） | ✅ |
| `/admin/document-templates/{template_id}` | GET | 是 | `require_staff` | 文书模板详情 | ✅ |
| `/admin/document-templates/{template_id}` | PUT | 是 | `require_admin` | 更新文书模板 | ✅ |
| `/admin/document-templates/parse` | POST | 是 | `require_admin` | 解析DOCX表单字段 | ✅ |
| `/admin/document-templates` | POST | 是 | `require_admin` | 创建文书模板（含DOCX解析） | ✅ |
| `/admin/document-templates/{template_id}` | DELETE | 是 | `require_admin` | 删除文书模板 | ✅ |
| `/students/me/documents` | GET | 是 | `require_student` | 我的文书填写状态 | ✅ |
| `/students/me/documents/{template_id}` | GET | 是 | `require_student` | 单份文书详情（含可选项） | ✅ |
| `/students/me/documents/{template_id}` | POST | 是 | `require_student` | 提交/更新文书 | ✅ |

---

### 1.4 教练模块 (instructor.py) — 路由前缀 `/api/v1/instructor`

**Router-level guard**: `require_instructor`

| 端点 | 方法 | 认证要求 | 角色守卫 | 功能 | 安全状态 |
|------|------|---------|---------|------|---------|
| `/instructor/class` | GET | 是 | `require_instructor` + `get_current_class` | 当前班级信息 | ✅ |
| `/instructor/classes` | GET | 是 | `require_instructor` + `get_current_class` | 班级信息（别名） | ✅ |
| `/instructor/students` | GET | 是 | `require_instructor` + `get_current_class` | 学员列表 | ✅ |
| `/instructor/textbooks` | GET | 是 | `require_instructor` + `get_current_class` | 可用教材列表 | ✅ |
| `/instructor/tests` | GET | 是 | `require_instructor` + `get_current_class` | 测验列表 | ✅ |
| `/instructor/tests` | POST | 是 | `require_instructor` + `get_current_class` | 发布测验 | ✅ |
| `/instructor/tests/{test_id}` | GET | 是 | `require_instructor` + `get_current_class` | 测验详情（含题目） | ✅ |
| `/instructor/tests/{test_id}` | DELETE | 是 | `require_instructor` + `get_current_class` | 删除测验 | ✅ |
| `/instructor/tests/generate` | POST | 是 | `require_instructor` + `get_current_class` | 智能抽题组卷 | ✅ |
| `/instructor/questions` | GET | 是 | `require_instructor` + `get_current_class` | 题库浏览 | ✅ |
| `/instructor/progress` | GET | 是 | `require_instructor` + `get_current_class` | 学员进度概览 | ✅ |
| `/instructor/progress/{user_id}` | GET | 是 | `require_instructor` + `get_current_class` | 单个学员详细进度 | ✅ |
| `/instructor/scores` | GET | 是 | `require_instructor` + `get_current_class` | 成绩汇总表 | ✅ |
| `/instructor/scores/{test_id}` | GET | 是 | `require_instructor` + `get_current_class` | 单次测验成绩详情 | ✅ |
| `/instructor/analytics/overview` | GET | 是 | `require_instructor` + `get_current_class` | 班级统计概览 | ✅ |
| `/instructor/analytics/reading` | GET | 是 | `require_instructor` + `get_current_class` | 阅读统计排行 | ✅ |
| `/instructor/analytics/scores` | GET | 是 | `require_instructor` + `get_current_class` | 成绩统计排行 | ✅ |

---

### 1.5 教练学员进度模块 (instructor_progress.py) — 路由前缀 `/api/v1/instructor/students`

| 端点 | 方法 | 认证要求 | 角色守卫 | 功能 | 安全状态 |
|------|------|---------|---------|------|---------|
| `/instructor/students/progress` | GET | 是 | `get_instructor_class` | 班级所有学员学习进度 | ✅ |
| `/instructor/students/{user_id}/progress` | GET | 是 | `get_instructor_class` | 单个学员详细进度 | ✅ |
| `/instructor/students/pending-tests` | GET | 是 | `get_instructor_class` | 等待发布随堂测验列表 | ✅ |
| `/instructor/students/scores` | GET | 是 | `get_instructor_class` | 班级所有测验成绩 | ✅ |
| `/instructor/students/analytics/overview` | GET | 是 | `get_instructor_class` | 班级统计分析 | ✅ |

---

### 1.6 管理干部模块 (manager.py) — 路由前缀 `/api/v1/manager`

**注意**: 多数端点通过 `get_manager_class` 进行角色校验 (MANAGER only)

| 端点 | 方法 | 认证要求 | 角色守卫 | 功能 | 安全状态 |
|------|------|---------|---------|------|---------|
| `/manager/class` | GET | 是 | `get_manager_class` | 当前/指定班级信息 | ✅ |
| `/manager/classes` | GET | 是 | `get_manager_class` | 班级信息（别名） | ✅ |
| `/manager/students` | GET | 是 | `get_manager_class` | 学员列表（含阅读进度） | ✅ |
| `/manager/students/{user_id}` | GET | 是 | `get_manager_class` | 学员详情（含成绩分析） | ✅ |
| `/manager/progress` | GET | 是 | `get_manager_class` | 所有学员进度 | ✅ |
| `/manager/scores` | GET | 是 | `get_manager_class` | 成绩汇总表 | ✅ |
| `/manager/scores/{test_id}` | GET | 是 | `get_manager_class` | 单次测验成绩 | ✅ |
| `/manager/analytics/overview` | GET | 是 | `get_manager_class` | 班级统计概览（含通过率） | ✅ |
| `/manager/dashboard/summary` | GET | 是 | `get_manager_class` | 干部大屏汇总（别名） | ✅ |
| `/manager/analytics/reading` | GET | 是 | `get_manager_class` | 阅读统计排行 | ✅ |
| `/manager/analytics/scores` | GET | 是 | `get_manager_class` | 成绩统计排行 | ✅ |
| `/manager/analytics/anti-cheat` | GET | 是 | `get_manager_class` | 反作弊：切标签统计 | ✅ |
| `/manager/export/students` | GET | 是 | `get_manager_class` | 导出学员名单（xlsx/csv/json） | ✅ |
| `/manager/export/scores` | GET | 是 | `get_manager_class` | 导出成绩表（xlsx/csv/json） | ✅ |
| `/manager/announcements` | GET | 是 | `get_manager_class` | 班级公告列表 | ✅ |
| `/manager/announcements` | POST | 是 | `get_manager_class` | 发布公告 | ✅ |
| `/manager/announcements/{ann_id}` | DELETE | 是 | `get_manager_class` | 删除公告 | ✅ |
| `/manager/cross-class/comparison` | GET | 是 | `get_manager_class` | 跨班对比分析 | ✅ |
| `/manager/alerts` | GET | 是 | `get_manager_class` | 预警记录（可筛选） | ✅ |
| `/manager/alerts/{alert_id}/read` | POST | 是 | `get_manager_class` | 标记预警已读 | ✅ |
| `/manager/alerts/{alert_id}/resolve` | POST | 是 | `get_manager_class` | 解决预警 | ✅ |
| `/manager/alerts/stats` | GET | 是 | `get_manager_class` | 预警统计 | ✅ |
| `/manager/alerts/detect` | POST | 是 | `get_manager_class` | 手动触发预警检测 | ✅ |
| `/manager/audit-logs` | GET | 是 | 🔴 `get_current_user` 仅认证 | 审计日志查询 | 🔴 缺少角色守卫 |
| `/manager/audit-logs/stats` | GET | 是 | 🔴 `get_current_user` 仅认证 | 审计日志统计 | 🔴 缺少角色守卫 |

---

### 1.7 学员模块 (student.py) — 路由前缀 `/api/v1/student`

**Router-level guard**: `require_student`

| 端点 | 方法 | 认证要求 | 角色守卫 | 功能 | 安全状态 |
|------|------|---------|---------|------|---------|
| `/student/textbooks` | GET | 是 | `require_student` + `get_current_class` | 可学习教材列表 | ✅ |
| `/student/textbooks/{textbook_id}` | GET | 是 | `require_student` + `get_current_class` | 教材详情（含章节） | ✅ |
| `/student/textbooks/{textbook_id}/chapters/{chapter_id}` | GET | 是 | `require_student` + `get_current_class` | 章节内容 | ✅ |
| `/student/reading/progress` | POST | 是 | `require_student` + `get_current_class` | 上报阅读进度 | ✅ |
| `/student/reading/progress` | GET | 是 | `require_student` + `get_current_class` | 我的阅读进度 | ✅ |
| `/student/tests` | GET | 是 | `require_student` + `get_current_class` | 测验列表 | ✅ |
| `/student/tests/{test_id}` | GET | 是 | `require_student` + `get_current_class` | 测验详情（含题目） | ✅ |
| `/student/tests/{test_id}/start` | POST | 是 | `require_student` + `get_current_class` | 开始答题（创建记录） | ✅ |
| `/student/tests/{test_id}/submit` | POST | 是 | `require_student` + `get_current_class` | 提交答案（自动评分） | ✅ |
| `/student/scores` | GET | 是 | `require_student` + `get_current_class` | 我的成绩列表 | ✅ |
| `/student/scores/{test_id}` | GET | 是 | `require_student` + `get_current_class` | 单次测验详情+答案 | ✅ |
| `/student/wrong-answers` | GET | 是 | `require_student` + `get_current_class` | 错题本 | ✅ |
| `/student/profile` | GET | 是 | `require_student` + `get_current_class` | 个人信息 | ✅ |
| `/student/dashboard` | GET | 是 | `require_student` + `get_current_class` | 学习概览 | ✅ |
| `/student/qa` | GET | 是 | `require_student` + `get_current_class` | 问答列表 | ✅ |
| `/student/qa` | POST | 是 | `require_student` + `get_current_class` | 提问 | ✅ |

---

### 1.8 学员章节学习模块 (student_chapters.py) — 路由前缀 `/api/v1/student/chapters`

| 端点 | 方法 | 认证要求 | 角色守卫 | 功能 | 安全状态 |
|------|------|---------|---------|------|---------|
| `/student/chapters` | GET | 是 | `get_user_class` (STUDENT) | 章节列表（含进度） | ✅ |
| `/student/chapters/my-progress` | GET | 是 | `get_user_class` | 学习进度汇总 | ✅ |
| `/student/chapters/pdf` | GET | 是 | `get_user_class` | PDF教材页面列表 | ✅ |
| `/student/chapters/pdf/progress` | POST | 是 | `get_user_class` | 更新PDF阅读进度 | ✅ |
| `/student/chapters/search` | GET | 是 | `get_user_class` | 搜索章节内容 | ✅ |
| `/student/chapters/certificate` | GET | 是 | `get_user_class` | 结业证书数据（需全完成） | ✅ |
| `/student/chapters/review` | GET | 是 | `get_user_class` | 智能复习推荐 | ✅ |
| `/student/chapters/learning-path` | GET | 是 | `get_user_class` | 自适应学习路径 | ✅ |
| `/student/chapters/learning-path/reassess` | POST | 是 | `get_user_class` | 重新评估学习路径 | ✅ |
| `/student/chapters/notes` | GET | 是 | `get_user_class` | 我的笔记 | ✅ |
| `/student/chapters/notes` | POST | 是 | `get_user_class` | 保存/更新笔记 | ✅ |
| `/student/chapters/notes/{note_id}` | DELETE | 是 | `get_user_class` | 删除笔记 | ✅ |
| `/student/chapters/bookmarks` | GET | 是 | `get_user_class` | 我的书签 | ✅ |
| `/student/chapters/bookmarks` | POST | 是 | `get_user_class` | 添加书签 | ✅ |
| `/student/chapters/bookmarks/{bookmark_id}` | DELETE | 是 | `get_user_class` | 删除书签 | ✅ |
| `/student/chapters/{chapter_id}` | GET | 是 | `get_user_class` | 章节内容 | ✅ |
| `/student/chapters/{chapter_id}/start-reading` | POST | 是 | `get_user_class` | 开始阅读 | ✅ |
| `/student/chapters/{chapter_id}/update-progress` | POST | 是 | `get_user_class` | 更新阅读进度 | ✅ |
| `/student/chapters/{chapter_id}/finish-reading` | POST | 是 | `get_user_class` | 标记阅读完成→进入练习 | ✅ |
| `/student/chapters/{chapter_id}/exercises` | GET | 是 | `get_user_class` | 章节配套练习 | ✅ |
| `/student/chapters/{chapter_id}/submit-exercises` | POST | 是 | `get_user_class` | 提交练习答案（含自测） | ✅ |

---

## 2. 安全缺口分析

### 2.1 🔴 严重：缺少角色守卫的端点

以下端点仅使用 `get_current_user` 进行身份验证，但**未进行角色校验**，任何已登录用户均可访问：

| 端点 | 文件 | 问题 | 影响 |
|------|------|------|------|
| `/manager/audit-logs` | manager.py | 仅 `Depends(get_current_user)`，无角色守卫 | 任何已登录用户（学员/教练）可查询全局审计日志 |
| `/manager/audit-logs/stats` | manager.py | 仅 `Depends(get_current_user)`，无角色守卫 | 任何已登录用户可查看审计统计 |

**对比**: 同模块的其他端点均通过 `get_manager_class` 进行严格的 MANAGER 角色验证。这两个审计日志端点很可能是**遗漏添加 `get_manager_class` 依赖**的编码疏忽。

### 2.2 🟡 中危：过度权限端点（require_admin 包含 MANAGER）

当前 `require_admin` 守卫 = ADMIN + MANAGER，这意味着**管理干部（MANAGER）拥有所有管理功能的访问权**，包括但不限于：

| 端点组 | 风险 |
|--------|------|
| `/admin/settings`, `/admin/system-settings` | MANAGER 可读写全局系统配置 |
| `/admin/alert-rules` | MANAGER 可创建/修改/删除预警规则 |
| `/admin/audit-logs` | MANAGER 可查看所有操作的审计日志 |
| `/admin/dashboard` | MANAGER 可查看全局仪表盘（含告警） |
| `/admin/alert-records` | MANAGER 可查看所有告警记录 |
| `/admin/users` | MANAGER 可查看所有用户列表（含管理员） |
| `/admin/people` | MANAGER 可 CRUD 所有人员 |
| `/admin/companies` | MANAGER 可 CRUD 单位 |
| `/admin/instructors` | MANAGER 可 CRUD 教练并重置其密码 |
| `/admin/textbooks` | MANAGER 可完全管理教材、章节、互动式内容 |
| `/admin/questions` | MANAGER 可管理题库 |
| `/admin/comparison` | MANAGER 可跨班级对比 |

**建议**: 将 `require_admin` 拆分为 `require_superadmin` (ADMIN only) 和 `require_staff_admin` (ADMIN + MANAGER)，系统设置/用户管理/审计日志等敏感功能应仅限 ADMIN。

### 2.3 🟡 中危：密码策略相关问题

| 问题 | 位置 | 详情 |
|------|------|------|
| 自动生成弱密码 | admin_classes.py, admin_people.py, admin_instructors.py | 新用户默认密码=手机号后6位或身份证后6位 (`"000000"[-6:]`) |
| 管理员可任意设密码 | admin_instructors.py `reset_instructor_password` | 无密码强度校验 |
| 管理员创建时返回明文密码 | admin_people.py, admin_instructors.py | `create_person()` 和 `create_instructor()` 在响应中返回 `"password": pw` |

### 2.4 🟡 中危：缺少资源归属校验

部分端点验证了角色但未验证数据归属：

| 端点 | 问题 |
|------|------|
| `/instructor/progress/{user_id}` (instructor.py) | 教练可查看**任意学员**的详细进度，无需验证该学员是否属于教练的班级 |
| `/manager/students/{user_id}` (manager.py) | 虽验证了学员属于当前班级，但 `get_manager_class` 默认取第一个活跃班级 |
| `/manager/alerts/detect` (manager.py) | 手动触发告警检测时审计日志的 `AuditLog.user_id` 引用可能为 None |
| `/admin/student-preview/{student_id}/chapters` (admin_student_preview.py) | 未验证 student_id 对应的章节属于当前管理的班级 |

### 2.5 🟢 低危：其他发现

| 问题 | 位置 | 详情 |
|------|------|------|
| `/auth/logout` 无认证 | auth_v2.py | 公开端点，虽然无实际影响但不符合 REST 惯例 |
| 内存级速率限制 | auth_v2.py | 登录频率限制使用 Python `defaultdict`，服务重启后丢失 |
| `await db.get()` 返回 None 时未统一处理 | 多文件 | 多处使用 `await db.get()` 但部分未对 None 做判断 |
| DELETE companies 无级联 | admin_companies.py | 删除公司时未清除关联用户的 `company_id`，可能导致孤儿引用 |
| 文件删除未限制 | admin_textbooks.py | `/admin/textbooks/{textbook_id}/pages` 批量删除无二次确认 |

### 2.6 ⚠️ 潜在 SQL 注入风险

在 `admin_people.py` 中：
```python
result = await db.execute(sql_text(f"SELECT COUNT(*) FROM ({base_sql}) sub"))
```
以及
```python
sql += f" LIMIT {page_size} OFFSET {(page-1)*page_size}"
```
`page` 和 `page_size` 虽来自 `Query` 参数（已校验类型），但使用 **f-string 拼接 SQL** 是不安全的模式。未来若重构时使用字符串参数可能导致注入。应改为参数化查询。

---

## 3. 端点统计总览

| 模块 | 端点数 | 安全状态 |
|------|--------|---------|
| 认证 (auth_v2.py) | 6 | ✅ 基本安全，/logout 无认证 |
| 管理员-班级 (admin_classes.py) | 22 | ✅ |
| 管理员-用户 (admin_users.py) | 1 | ✅ |
| 管理员-人员 (admin_people.py) | 7 | ⚠️ 弱密码 |
| 管理员-单位 (admin_companies.py) | 4 | ⚠️ 无级联 |
| 管理员-教练 (admin_instructors.py) | 5 | ⚠️ 弱密码 |
| 管理员-教材 (admin_textbooks.py) | 35 | ✅ |
| 管理员-题目 (admin_questions.py) | 4 | ✅ |
| 管理员-设置 (admin_settings.py) | 12 | ⚠️ MANAGER权限过大 |
| 管理员-公告 (admin_announcements.py) | 4 | ✅ |
| 管理员-预览 (admin_preview.py) | 3 | ✅ |
| 管理员-学员预览 (admin_student_preview.py) | 2 | ⚠️ 无归属校验 |
| 管理员-学习路径 (admin_learning.py) | 2 | ✅ |
| 课程管理 (courses.py) | 7 | ✅ |
| 文书 (documents.py) | 9 | ✅ |
| 教练 (instructor.py) | 17 | ✅ |
| 教练进度 (instructor_progress.py) | 5 | ✅ |
| 管理干部 (manager.py) | 25 | 🔴 2个端点缺守卫 |
| 学员 (student.py) | 16 | ✅ |
| 学员章节 (student_chapters.py) | 21 | ✅ |
| **总计** | **~207** | |

---

## 4. 改进建议

### P0 - 立即修复

1. **修复 `/manager/audit-logs` 和 `/manager/audit-logs/stats`**: 添加 `get_manager_class` 依赖替换 `get_current_user`
   ```python
   # manager.py L441, L480
   # 将 Depends(get_current_user) 改为 Depends(get_manager_class)
   ```

### P1 - 高优先级

2. **细化 `require_admin` 守卫**: 新增 `require_superadmin` (ADMIN only) 用于系统设置和审计日志
   - `/admin/system-settings` → `require_superadmin`
   - `/admin/settings` → `require_superadmin`
   - `/admin/audit-logs` → `require_superadmin`
   - `/admin/alert-rules` → `require_superadmin`
   - `/admin/users` → `require_superadmin`

3. **增强密码策略**:
   - 自动生成密码改为随机8位强密码（或首次登录强制修改）
   - `reset_password` 接口增加强度校验（复用 `validate_password_strength`）
   - 删除管理员创建用户时返回明文密码的行为

4. **修复资源归属校验**:
   - `/instructor/progress/{user_id}` 增加验证：该学员是否属于教练的班级
   - `/admin/student-preview/*` 增加验证：学员是否在管理员管辖范围内
   - DELETE companies 增加级联：清除关联用户的 `company_id`

### P2 - 中优先级

5. **使用参数化查询**: 替换所有 f-string SQL 拼接为参数化查询（`admin_people.py`）
6. **添加全局异常处理**: 统一 `await db.get()` 的 None 处理
7. **审计日志完善**: `POST /auth/logout` 添加审计记录
8. **DELETE pages 增加确认**: 大量数据删除操作增加 `confirm` 参数

### P3 - 低优先级

9. **登录限流**: 改为 Redis 或数据库持久化存储，避免服务重启丢失
10. **CSRF 保护**: 添加 CSRF token 机制（适用于非 API-only 场景）
11. **请求日志**: 对敏感操作（创建用户、重置密码、删除数据）进行结构化审计日志

---

*审计工具: 人工代码审查 | 覆盖 207+ 个端点 | 发现 2 个严重缺口*
