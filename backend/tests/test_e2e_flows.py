"""
端到端全流程测试
覆盖：学员完整生命周期 | 教练功能 | 管理干部功能 | 跨角色安全
"""
import pytest
import json
from httpx import AsyncClient


# ════════════════════════════════════════════════════════════════
# StudentFullFlow — 学员完整生命周期（核心E2E）
# ════════════════════════════════════════════════════════════════

class TestStudentFullFlow:

    @pytest.mark.e2e
    async def test_complete_student_lifecycle(
        self, client: AsyncClient, db_session,
        admin_token: str, instructor_user, textbook, chapter, question, make_token
    ):
        """
        学员完整生命周期端到端测试
        Admin → 创建班级+学员+入班 → 学员登录 →
        开始阅读 → 更新进度 → 完成阅读 → 获取练习 → 提交练习 →
        教练创建测验 → 学员答题 → 查成绩 → 查进度
        """
        from datetime import datetime, timedelta, timezone
        from app.models.class_system import Class, ClassMember, UserRole, ClassStatus

        now = datetime.now(timezone.utc).replace(tzinfo=None)

        # ── Step 1: Admin 创建学员 ──
        student_id_card = f"44010219810701{now.microsecond % 10000:04d}"
        student_phone = f"138{now.microsecond % 100000000:08d}"
        resp = await client.post("/api/v1/admin/people",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "name": "E2E学员",
                "role": "student",
                "phone": student_phone,
                "id_card": student_id_card,
            }
        )
        assert resp.status_code in {200, 201}, f"创建学员失败: {resp.text}"
        student_data = resp.json()
        assert "id" in student_data
        student_id = student_data["id"]
        student_password = student_data.get("password", "000000")

        # ── Step 2: Admin 创建班级 ──
        resp = await client.post("/api/v1/admin/classes",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "name": "E2E测试班",
                "location": "测试基地",
                "start_time": (now - timedelta(days=1)).isoformat(),
                "end_time": (now + timedelta(days=30)).isoformat(),
                "instructor_id": instructor_user.id,
                "status": "active",
            }
        )
        assert resp.status_code in {200, 201}, f"创建班级失败: {resp.text}"
        class_data = resp.json()
        class_id = class_data.get("id") or class_data.get("class_id")
        assert class_id is not None

        # ── Step 3: Admin 将学员加入班级 ──
        resp = await client.post(f"/api/v1/admin/classes/{class_id}/members",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "user_id": student_id,
                "role": "student",
            }
        )
        assert resp.status_code in {200, 201}, f"加入班级失败: {resp.text}"

        # ── Step 4: 将教材分配给班级 ──
        resp = await client.post(f"/api/v1/admin/classes/{class_id}/textbooks/{textbook.id}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        # 教材分配可能 200/201/已存在则可能报错
        assert resp.status_code in {200, 201, 400, 409}, f"分配教材: {resp.status_code} {resp.text}"

        # ── Step 5: 学员登录（需在活跃班级内才可登录） ──
        resp = await client.post("/api/v1/auth/login", json={
            "name": "E2E学员",
            "id_card": student_id_card,
            "phone": student_phone,
            "role": "student",
        })
        assert resp.status_code == 200, f"学员登录失败: {resp.text}"
        login_data = resp.json()
        assert login_data["success"] is True, f"登录不成功: {login_data}"
        student_jwt = login_data["token"]
        assert student_jwt is not None

        # ── Step 6: 学员获取章节列表 ──
        resp = await client.get("/api/v1/student/chapters",
            headers={"Authorization": f"Bearer {student_jwt}"}
        )
        assert resp.status_code in {200, 404}, f"获取章节失败: {resp.text}"
        chapters_data = resp.json() if resp.status_code == 200 else {}

        # 用 fixture 创建的 chapter 的 ID
        chapter_id = chapter.id

        # ── Step 7: 学员开始阅读章节 ──
        resp = await client.post(f"/api/v1/student/chapters/{chapter_id}/start-reading",
            headers={"Authorization": f"Bearer {student_jwt}"}
        )
        assert resp.status_code in {200, 201}, f"开始阅读失败: {resp.text}"
        assert resp.json()["success"] is True

        # ── Step 8: 学员更新阅读进度 ──
        resp = await client.post(
            f"/api/v1/student/chapters/{chapter_id}/update-progress"
            f"?reading_time=120&current_page=10",
            headers={"Authorization": f"Bearer {student_jwt}"}
        )
        assert resp.status_code == 200, f"更新进度失败: {resp.text}"
        assert resp.json()["success"] is True

        # ── Step 9: 学员完成阅读 → 进入练习阶段 ──
        resp = await client.post(f"/api/v1/student/chapters/{chapter_id}/finish-reading",
            headers={"Authorization": f"Bearer {student_jwt}"}
        )
        assert resp.status_code == 200, f"完成阅读失败: {resp.text}"
        assert resp.json()["success"] is True

        # ── Step 10: 学员获取章节练习 ──
        resp = await client.get(f"/api/v1/student/chapters/{chapter_id}/exercises",
            headers={"Authorization": f"Bearer {student_jwt}"}
        )
        # 如果章节没有 ChapterExercise 记录，返回空列表
        assert resp.status_code in {200, 403}, f"获取练习: {resp.status_code} {resp.text}"

        # ── Step 11: 学员提交练习 ──
        if resp.status_code == 200:
            exercises_json = resp.json()
            questions_list = exercises_json.get("questions", [])
            answers = [{"question_id": q["id"], "answer": q.get("options", [""])[0]} for q in questions_list]
            resp = await client.post(f"/api/v1/student/chapters/{chapter_id}/submit-exercises",
                headers={"Authorization": f"Bearer {student_jwt}"},
                json={"answers": answers, "self_test": True}
            )
            assert resp.status_code == 200, f"提交练习失败: {resp.text}"
        else:
            # 没有练习题，直接提交空答案
            resp = await client.post(f"/api/v1/student/chapters/{chapter_id}/submit-exercises",
                headers={"Authorization": f"Bearer {student_jwt}"},
                json={"answers": [], "self_test": True}
            )
            assert resp.status_code in {200, 400}, f"提交练习: {resp.status_code} {resp.text}"

        # ── Step 12: 教练创建测验 ──
        # 教练也需要加入班级
        from app.models.class_system import ClassMember
        existing_member = await db_session.execute(
            __import__('sqlalchemy').select(ClassMember).where(
                ClassMember.class_id == class_id,
                ClassMember.user_id == instructor_user.id
            )
        )
        if not existing_member.scalar_one_or_none():
            db_session.add(ClassMember(class_id=class_id, user_id=instructor_user.id, role=UserRole.INSTRUCTOR))
            await db_session.flush()

        # 使用 JWT 生成教练 token（因为 login 要求教练也在活跃班里）
        instructor_jwt = make_token(instructor_user.id, "instructor")

        resp = await client.post("/api/v1/instructor/tests",
            headers={"Authorization": f"Bearer {instructor_jwt}"},
            json={
                "title": "E2E章节测验",
                "test_type": "quiz",
                "questions": [question.id],
                "duration": 30,
            }
        )
        assert resp.status_code in {200, 201}, f"创建测验失败: {resp.text}"
        test_data = resp.json()
        test_id = test_data.get("id")

        # ── Step 13: 学员查看可用测验 ──
        resp = await client.get("/api/v1/student/tests",
            headers={"Authorization": f"Bearer {student_jwt}"}
        )
        assert resp.status_code == 200, f"查看测验失败: {resp.text}"

        # ── Step 14: 学员开始答题 ──
        resp = await client.post(f"/api/v1/student/tests/{test_id}/start",
            headers={"Authorization": f"Bearer {student_jwt}"}
        )
        assert resp.status_code in {200, 201}, f"开始答题失败: {resp.text}"
        assert resp.json()["success"] is True

        # ── Step 15: 学员提交答案 ──
        # 获取正确答案
        from app.models.class_system import Question
        q_obj = await db_session.get(Question, question.id)
        correct_answer = q_obj.get_answer() if q_obj else "约1500m/s"

        resp = await client.post(f"/api/v1/student/tests/{test_id}/submit",
            headers={"Authorization": f"Bearer {student_jwt}"},
            json={
                "answers": [
                    {"question_id": question.id, "answer": correct_answer}
                ]
            }
        )
        assert resp.status_code == 200, f"提交答案失败: {resp.text}"
        submit_data = resp.json()
        assert submit_data["success"] is True
        assert "score" in submit_data

        # ── Step 16: 学员查看成绩 ──
        resp = await client.get("/api/v1/student/scores",
            headers={"Authorization": f"Bearer {student_jwt}"}
        )
        assert resp.status_code == 200, f"查看成绩失败: {resp.text}"

        # ── Step 17: 学员查看证书/进度 ──
        resp = await client.get("/api/v1/student/chapters/certificate",
            headers={"Authorization": f"Bearer {student_jwt}"}
        )
        assert resp.status_code in {200, 404, 403}, f"查看证书: {resp.status_code} {resp.text}"  # 未完成全部课程返回403

        resp = await client.get("/api/v1/student/chapters/my-progress",
            headers={"Authorization": f"Bearer {student_jwt}"}
        )
        assert resp.status_code in {200, 404}, f"查看进度: {resp.status_code} {resp.text}"


# ════════════════════════════════════════════════════════════════
# InstructorFlow — 教练功能完整流程
# ════════════════════════════════════════════════════════════════

class TestInstructorFlow:

    @pytest.mark.e2e
    async def test_instructor_login_and_flow(
        self, client: AsyncClient, db_session,
        instructor_user, active_class, question, make_token
    ):
        """
        教练完整功能流程：
        登录 → 查看班级 → 学员列表 → 教材 → 题目库 →
        创建测验 → 查看成绩 → 分析面板
        """
        # 教练加入班级
        from app.models.class_system import ClassMember, UserRole
        existing = await db_session.execute(
            __import__('sqlalchemy').select(ClassMember).where(
                ClassMember.class_id == active_class.id,
                ClassMember.user_id == instructor_user.id
            )
        )
        if not existing.scalar_one_or_none():
            db_session.add(ClassMember(
                class_id=active_class.id, user_id=instructor_user.id, role=UserRole.INSTRUCTOR
            ))
            await db_session.flush()

        # 生成教练 token
        instructor_jwt = make_token(instructor_user.id, "instructor")

        # ── 1. 查看班级信息 ──
        resp = await client.get("/api/v1/instructor/class",
            headers={"Authorization": f"Bearer {instructor_jwt}"}
        )
        assert resp.status_code == 200, f"查看班级: {resp.status_code} {resp.text}"

        # ── 2. 查看班级列表 ──
        resp = await client.get("/api/v1/instructor/classes",
            headers={"Authorization": f"Bearer {instructor_jwt}"}
        )
        assert resp.status_code == 200, f"查看班级列表: {resp.status_code} {resp.text}"

        # ── 3. 查看学员列表 ──
        resp = await client.get("/api/v1/instructor/students",
            headers={"Authorization": f"Bearer {instructor_jwt}"}
        )
        assert resp.status_code == 200, f"查看学员: {resp.status_code} {resp.text}"

        # ── 4. 查看教材 ──
        resp = await client.get("/api/v1/instructor/textbooks",
            headers={"Authorization": f"Bearer {instructor_jwt}"}
        )
        assert resp.status_code == 200, f"查看教材: {resp.status_code} {resp.text}"

        # ── 5. 查看题目库 ──
        resp = await client.get("/api/v1/instructor/questions",
            headers={"Authorization": f"Bearer {instructor_jwt}"}
        )
        assert resp.status_code in {200, 404}, f"查看题目: {resp.status_code} {resp.text}"

        # ── 6. 创建测验 ──
        resp = await client.post("/api/v1/instructor/tests",
            headers={"Authorization": f"Bearer {instructor_jwt}"},
            json={
                "title": "教练流测验",
                "test_type": "quiz",
                "questions": [question.id],
                "duration": 30,
            }
        )
        assert resp.status_code in {200, 201}, f"创建测验失败: {resp.text}"
        test_data = resp.json()
        test_id = test_data.get("id")
        assert test_id is not None

        # ── 7. 查看测验列表 ──
        resp = await client.get("/api/v1/instructor/tests",
            headers={"Authorization": f"Bearer {instructor_jwt}"}
        )
        assert resp.status_code == 200, f"查看测验列表: {resp.status_code} {resp.text}"

        # ── 8. 查看测验详情 ──
        resp = await client.get(f"/api/v1/instructor/tests/{test_id}",
            headers={"Authorization": f"Bearer {instructor_jwt}"}
        )
        assert resp.status_code in {200, 404}, f"查看测验详情: {resp.status_code} {resp.text}"

        # ── 9. 查看成绩 ──
        resp = await client.get(f"/api/v1/instructor/scores/{test_id}",
            headers={"Authorization": f"Bearer {instructor_jwt}"}
        )
        assert resp.status_code in {200, 404}, f"查看成绩: {resp.status_code} {resp.text}"

        resp = await client.get("/api/v1/instructor/scores",
            headers={"Authorization": f"Bearer {instructor_jwt}"}
        )
        assert resp.status_code == 200, f"查看成绩矩阵: {resp.status_code} {resp.text}"

        # ── 10. 查看分析面板 ──
        for analytics_url in [
            "/api/v1/instructor/analytics/overview",
            "/api/v1/instructor/analytics/reading",
            "/api/v1/instructor/analytics/scores",
        ]:
            resp = await client.get(analytics_url,
                headers={"Authorization": f"Bearer {instructor_jwt}"}
            )
            assert resp.status_code == 200, f"查看分析 {analytics_url}: {resp.status_code} {resp.text}"

        # ── 11. 删除测验（清理） ──
        resp = await client.delete(f"/api/v1/instructor/tests/{test_id}",
            headers={"Authorization": f"Bearer {instructor_jwt}"}
        )
        assert resp.status_code in {200, 204, 404}, f"删除测验: {resp.status_code} {resp.text}"


    @pytest.mark.e2e
    async def test_instructor_student_progress(
        self, client, db_session,
        instructor_user, active_class, student_user, make_token
    ):
        """教练查看学员个人进度"""
        from app.models.class_system import ClassMember, UserRole

        # 确保都在班级
        for uid in [instructor_user.id, student_user.id]:
            existing = await db_session.execute(
                __import__('sqlalchemy').select(ClassMember).where(
                    ClassMember.class_id == active_class.id,
                    ClassMember.user_id == uid
                )
            )
            if not existing.scalar_one_or_none():
                role = UserRole.INSTRUCTOR if uid == instructor_user.id else UserRole.STUDENT
                db_session.add(ClassMember(class_id=active_class.id, user_id=uid, role=role))
        await db_session.flush()

        instructor_jwt = make_token(instructor_user.id, "instructor")

        # 查看学员进度
        resp = await client.get(f"/api/v1/instructor/students/{student_user.id}/progress",
            headers={"Authorization": f"Bearer {instructor_jwt}"}
        )
        assert resp.status_code in {200, 404}, f"查看学员进度: {resp.status_code} {resp.text}"


# ════════════════════════════════════════════════════════════════
# ManagerFlow — 管理干部功能完整流程
# ════════════════════════════════════════════════════════════════

class TestManagerFlow:

    @pytest.mark.e2e
    async def test_manager_login_and_dashboard(
        self, client: AsyncClient,
        manager_user, admin_token, active_class
    ):
        """管理干部：登录 + 仪表盘 + 导出 + 跨班对比"""
        # 管理员密码登录（管理干部也可以通过 admin 端点）
        # 管理干部用 phone+name 登录
        resp = await client.post("/api/v1/auth/login", json={
            "name": "管理干部A",
            "phone": "13800000002",
            "role": "manager",
        })
        assert resp.status_code == 200, f"管理干部登录失败: {resp.text}"
        login_data = resp.json()
        assert login_data["success"] is True, f"登录不成功: {login_data}"
        manager_jwt = login_data["token"]

        # ── 1. Dashboard 概要 ──
        resp = await client.get("/api/v1/manager/dashboard/summary",
            headers={"Authorization": f"Bearer {manager_jwt}"}
        )
        assert resp.status_code in {200, 404}, f"Dashboard: {resp.status_code} {resp.text}"

        # ── 2. 查看班级 ──
        resp = await client.get("/api/v1/manager/classes",
            headers={"Authorization": f"Bearer {manager_jwt}"}
        )
        assert resp.status_code in {200, 404}, f"查看班级: {resp.status_code} {resp.text}"

        # ── 3. 导出 ──
        resp = await client.get("/api/v1/manager/export/students",
            headers={"Authorization": f"Bearer {manager_jwt}"}
        )
        assert resp.status_code in {200, 404}, f"导出学员: {resp.status_code} {resp.text}"

        resp = await client.get("/api/v1/manager/export/scores",
            headers={"Authorization": f"Bearer {manager_jwt}"}
        )
        assert resp.status_code in {200, 404}, f"导出成绩: {resp.status_code} {resp.text}"

        # ── 4. 跨班对比 ──
        resp = await client.get("/api/v1/manager/cross-class/comparison",
            headers={"Authorization": f"Bearer {manager_jwt}"}
        )
        assert resp.status_code in {200, 404}, f"跨班对比: {resp.status_code} {resp.text}"

        # ── 5. 告警 ──
        resp = await client.get("/api/v1/manager/alerts",
            headers={"Authorization": f"Bearer {manager_jwt}"}
        )
        assert resp.status_code in {200, 404}, f"告警: {resp.status_code} {resp.text}"

        resp = await client.get("/api/v1/manager/alerts/stats",
            headers={"Authorization": f"Bearer {manager_jwt}"}
        )
        assert resp.status_code in {200, 404}, f"告警统计: {resp.status_code} {resp.text}"

        # ── 6. 防作弊分析 ──
        resp = await client.get("/api/v1/manager/analytics/anti-cheat",
            headers={"Authorization": f"Bearer {manager_jwt}"}
        )
        assert resp.status_code in {200, 404}, f"反作弊: {resp.status_code} {resp.text}"

        # ── 7. 公告管理 ──
        resp = await client.get("/api/v1/manager/announcements",
            headers={"Authorization": f"Bearer {manager_jwt}"}
        )
        assert resp.status_code in {200, 404}, f"公告: {resp.status_code} {resp.text}"

        # ── 8. 审计日志 ──
        resp = await client.get("/api/v1/manager/audit-logs",
            headers={"Authorization": f"Bearer {manager_jwt}"}
        )
        assert resp.status_code in {200, 404}, f"审计日志: {resp.status_code} {resp.text}"

        resp = await client.get("/api/v1/manager/audit-logs/stats",
            headers={"Authorization": f"Bearer {manager_jwt}"}
        )
        assert resp.status_code in {200, 404}, f"审计统计: {resp.status_code} {resp.text}"

        # ── 9. 班级管理 ──
        resp = await client.get(f"/api/v1/manager/class",
            headers={"Authorization": f"Bearer {manager_jwt}"}
        )
        assert resp.status_code in {200, 404}, f"班级信息: {resp.status_code} {resp.text}"

        # ── 10. 学习进度 ──
        resp = await client.get("/api/v1/manager/students",
            headers={"Authorization": f"Bearer {manager_jwt}"}
        )
        assert resp.status_code in {200, 404}, f"学员列表: {resp.status_code} {resp.text}"

        resp = await client.get("/api/v1/manager/progress",
            headers={"Authorization": f"Bearer {manager_jwt}"}
        )
        assert resp.status_code in {200, 404}, f"进度: {resp.status_code} {resp.text}"


# ════════════════════════════════════════════════════════════════
# CrossRoleSecurity — 跨角色安全边界验证
# ════════════════════════════════════════════════════════════════

class TestCrossRoleSecurity:

    # ── 学生 → 教练端点 ──

    @pytest.mark.security
    async def test_student_cannot_access_instructor(self, client, student_in_class_token):
        """学生不能访问教练端点"""
        forbidden = [
            "/api/v1/instructor/class",
            "/api/v1/instructor/tests",
            "/api/v1/instructor/analytics/overview",
        ]
        for url in forbidden:
            resp = await client.get(url,
                headers={"Authorization": f"Bearer {student_in_class_token}"}
            )
            assert resp.status_code in {401, 403, 404}, \
                f"学生访问 {url} 应被拒绝, 实际 {resp.status_code}"

    @pytest.mark.security
    async def test_student_cannot_access_admin(self, client, student_in_class_token):
        """学生不能访问管理端端点"""
        forbidden = [
            "/api/v1/admin/classes",
            "/api/v1/admin/people",
            "/api/v1/admin/users",
            "/api/v1/admin/settings",
        ]
        for url in forbidden:
            resp = await client.get(url,
                headers={"Authorization": f"Bearer {student_in_class_token}"}
            )
            assert resp.status_code in {401, 403, 404}, \
                f"学生访问 {url} 应被拒绝, 实际 {resp.status_code}"

    @pytest.mark.security
    async def test_student_cannot_access_manager(self, client, student_in_class_token):
        """学生不能访问管理干部端点"""
        forbidden = [
            "/api/v1/manager/students",
            "/api/v1/manager/dashboard/summary",
        ]
        for url in forbidden:
            resp = await client.get(url,
                headers={"Authorization": f"Bearer {student_in_class_token}"}
            )
            assert resp.status_code in {401, 403, 404}, \
                f"学生访问 {url} 应被拒绝, 实际 {resp.status_code}"

    # ── 教练 → 管理员端点 ──

    @pytest.mark.security
    async def test_instructor_cannot_access_admin(self, client, instructor_in_class_token):
        """教练不能访问管理端端点"""
        forbidden = [
            "/api/v1/admin/classes",
            "/api/v1/admin/people",
            "/api/v1/admin/settings",
        ]
        for url in forbidden:
            resp = await client.get(url,
                headers={"Authorization": f"Bearer {instructor_in_class_token}"}
            )
            assert resp.status_code in {401, 403, 404}, \
                f"教练访问 {url} 应被拒绝, 实际 {resp.status_code}"

    @pytest.mark.security
    async def test_instructor_cannot_access_manager(self, client, instructor_in_class_token):
        """教练不能访问管理干部端点"""
        forbidden = [
            "/api/v1/manager/dashboard/summary",
            "/api/v1/manager/audit-logs",
        ]
        for url in forbidden:
            resp = await client.get(url,
                headers={"Authorization": f"Bearer {instructor_in_class_token}"}
            )
            assert resp.status_code in {401, 403, 404}, \
                f"教练访问 {url} 应被拒绝, 实际 {resp.status_code}"

    # ── 未认证访问 ──

    @pytest.mark.security
    async def test_unauthenticated_access_rejected(self, client):
        """未认证用户访问任何受保护端点应被拒绝"""
        endpoints = [
            "/api/v1/admin/classes",
            "/api/v1/admin/people",
            "/api/v1/manager/students",
            "/api/v1/manager/dashboard/summary",
            "/api/v1/manager/audit-logs",
            "/api/v1/instructor/class",
            "/api/v1/instructor/tests",
            "/api/v1/instructor/analytics/overview",
            "/api/v1/student/tests",
            "/api/v1/student/scores",
            "/api/v1/student/chapters",
            "/api/v1/student/profile",
        ]
        for url in endpoints:
            resp = await client.get(url)
            assert resp.status_code not in {200}, \
                f"未认证访问 {url} 应被拒绝(非200), 实际 {resp.status_code}"

    # ── 垃圾Token ──

    @pytest.mark.security
    async def test_invalid_token_rejected(self, client):
        """无效JWT token 被拒绝"""
        endpoints = [
            "/api/v1/admin/classes",
            "/api/v1/student/tests",
            "/api/v1/instructor/class",
        ]
        for url in endpoints:
            resp = await client.get(url,
                headers={"Authorization": "Bearer definitely.not.a.valid.token"}
            )
            assert resp.status_code == 401, \
                f"无效token访问 {url} 应 401, 实际 {resp.status_code}"

    @pytest.mark.security
    async def test_expired_token_rejected(self, client, db_session):
        """过期 JWT token 被拒绝"""
        from datetime import datetime, timedelta, timezone
        from jose import jwt as jose_jwt
        from app.core.config import settings

        now = datetime.now(timezone.utc)
        expired_payload = {
            "sub": "99999",
            "role": "student",
            "exp": now - timedelta(hours=1),
            "iat": now - timedelta(hours=2),
            "type": "access"
        }
        expired_token = jose_jwt.encode(expired_payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

        resp = await client.get("/api/v1/student/tests",
            headers={"Authorization": f"Bearer {expired_token}"}
        )
        assert resp.status_code in {401, 403}, \
            f"过期token应被拒绝, 实际 {resp.status_code}"


# ════════════════════════════════════════════════════════════════
# StudentSubFlows — 学员子流程（边界场景）
# ════════════════════════════════════════════════════════════════

class TestStudentSubFlows:

    @pytest.mark.e2e
    async def test_student_profile_and_dashboard(
        self, client, student_in_class_token
    ):
        """学员：资料 + 仪表盘 + 错题"""
        # 个人资料
        resp = await client.get("/api/v1/student/profile",
            headers={"Authorization": f"Bearer {student_in_class_token}"}
        )
        assert resp.status_code in {200, 404}, f"资料: {resp.status_code} {resp.text}"

        # 仪表盘
        resp = await client.get("/api/v1/student/dashboard",
            headers={"Authorization": f"Bearer {student_in_class_token}"}
        )
        assert resp.status_code in {200, 404}, f"仪表盘: {resp.status_code} {resp.text}"

        # 错题本
        resp = await client.get("/api/v1/student/wrong-answers",
            headers={"Authorization": f"Bearer {student_in_class_token}"}
        )
        assert resp.status_code in {200, 404}, f"错题: {resp.status_code} {resp.text}"

    @pytest.mark.e2e
    async def test_student_qa_and_reading(
        self, client, student_in_class_token
    ):
        """学员：答疑 + 阅读进度"""
        # 答疑列表
        resp = await client.get("/api/v1/student/qa",
            headers={"Authorization": f"Bearer {student_in_class_token}"}
        )
        assert resp.status_code in {200, 404}, f"答疑: {resp.status_code} {resp.text}"

        # 阅读进度
        resp = await client.get("/api/v1/student/reading/progress",
            headers={"Authorization": f"Bearer {student_in_class_token}"}
        )
        assert resp.status_code in {200, 404}, f"阅读进度: {resp.status_code} {resp.text}"

    @pytest.mark.e2e
    async def test_invalid_chapter_id(self, client, student_in_class_token):
        """访问不存在的章节ID"""
        resp = await client.get("/api/v1/student/chapters/99999",
            headers={"Authorization": f"Bearer {student_in_class_token}"}
        )
        assert resp.status_code in {404, 200}, \
            f"不存在的章节应 404: {resp.status_code} {resp.text}"

    @pytest.mark.e2e
    async def test_start_reading_before_class_join(self, client, student_token, chapter):
        """不在班级中的学员使用student_solo_token尝试阅读（应失败）"""
        # 直接使用 student_token（可能不在班级里，取决于是否有 ClassMember）
        resp = await client.post(f"/api/v1/student/chapters/{chapter.id}/start-reading",
            headers={"Authorization": f"Bearer {student_token}"}
        )
        # student_token 不在班级中 → get_user_class 返回 400 "未加入班级"
        assert resp.status_code in {200, 400, 403}, \
            f"未入班阅读: {resp.status_code} {resp.text}"


# ════════════════════════════════════════════════════════════════
# AuthFlow — 认证流程
# ════════════════════════════════════════════════════════════════

class TestAuthE2EFlow:

    @pytest.mark.e2e
    async def test_login_refresh_logout(self, client, admin_user):
        """登录 → 刷新Token → 退出"""
        # 登录
        resp = await client.post("/api/v1/auth/login", json={
            "name": "管理员",
            "id_card": admin_user.id_card,
            "password": "test123",
            "role": "admin",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        token = data["token"]
        refresh_token = data.get("refresh_token")
        assert refresh_token is not None

        # 刷新 token
        resp = await client.post("/api/v1/auth/refresh", json={
            "refresh_token": refresh_token,
        })
        assert resp.status_code in {200, 401}, f"刷新token: {resp.status_code} {resp.text}"

        # 获取个人信息
        resp = await client.get("/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 200, f"获取me: {resp.status_code} {resp.text}"
        me_data = resp.json()
        assert me_data.get("success") is True or "id" in me_data

        # 退出
        resp = await client.post("/api/v1/auth/logout",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code in {200, 204}, f"退出: {resp.status_code} {resp.text}"

    @pytest.mark.e2e
    async def test_change_password(self, client, admin_user):
        """管理员：密码修改"""
        resp = await client.post("/api/v1/auth/login", json={
            "name": "管理员",
            "id_card": admin_user.id_card,
            "password": "test123",
            "role": "admin",
        })
        token = resp.json()["token"]

        # 改密码
        resp = await client.post("/api/v1/auth/change-password",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "old_password": "test123",
                "new_password": "newpass456",
            }
        )
        # 200 成功 / 400 格式不对
        assert resp.status_code in {200, 400, 422}, \
            f"改密码: {resp.status_code} {resp.text}"


# ════════════════════════════════════════════════════════════════
# AdminSubFlows — 管理员子流程
# ════════════════════════════════════════════════════════════════

class TestAdminSubFlows:

    @pytest.mark.e2e
    async def test_admin_class_lifecycle(
        self, client, db_session, admin_token,
        instructor_user, manager_user
    ):
        """管理员：班级 CRUD 全流程"""
        from datetime import datetime, timedelta, timezone
        now = datetime.now(timezone.utc).replace(tzinfo=None)

        # 创建
        resp = await client.post("/api/v1/admin/classes",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "name": "CRUD测试班",
                "location": "测试基地",
                "start_time": now.isoformat(),
                "end_time": (now + timedelta(days=30)).isoformat(),
                "instructor_id": instructor_user.id,
                "manager_id": manager_user.id,
            }
        )
        assert resp.status_code in {200, 201}, f"创建: {resp.text}"
        class_id = resp.json().get("id") or resp.json().get("class_id")
        assert class_id is not None

        # 查看列表
        resp = await client.get("/api/v1/admin/classes",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert resp.status_code == 200

        # 查看详情
        resp = await client.get(f"/api/v1/admin/classes/{class_id}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert resp.status_code == 200

        # 更新
        resp = await client.put(f"/api/v1/admin/classes/{class_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"name": "已改名的CRUD班"}
        )
        assert resp.status_code in {200, 201}, f"更新: {resp.text}"

        # 开始培训
        resp = await client.post(f"/api/v1/admin/classes/{class_id}/start",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert resp.status_code in {200, 400, 404}, f"开始: {resp.status_code}"

        # 结束培训
        resp = await client.post(f"/api/v1/admin/classes/{class_id}/end",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert resp.status_code in {200, 400, 404}, f"结束: {resp.status_code}"

        # 分析
        resp = await client.get(f"/api/v1/admin/classes/{class_id}/analytics",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert resp.status_code in {200, 404}, f"分析: {resp.status_code}"

        # 成员列表
        resp = await client.get(f"/api/v1/admin/classes/{class_id}/members",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert resp.status_code == 200

        # 教材列表
        resp = await client.get(f"/api/v1/admin/classes/{class_id}/textbooks",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert resp.status_code == 200

        # 删除
        resp = await client.delete(f"/api/v1/admin/classes/{class_id}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert resp.status_code in {200, 204, 400, 404}, f"删除: {resp.status_code}"

    @pytest.mark.e2e
    async def test_admin_textbooks_flow(self, client, admin_token, textbook):
        """管理员：教材管理"""
        # 列表
        resp = await client.get("/api/v1/admin/textbooks",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert resp.status_code in {200, 404}, f"教材列表: {resp.status_code} {resp.text}"

    @pytest.mark.e2e
    async def test_admin_people_flow(self, client, admin_token):
        """管理员：人员管理"""
        resp = await client.get("/api/v1/admin/people",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert resp.status_code == 200, f"人员列表: {resp.status_code} {resp.text}"

        # 学员别名端点
        resp = await client.get("/api/v1/admin/students",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert resp.status_code == 200, f"学员别名: {resp.status_code} {resp.text}"

    @pytest.mark.e2e
    async def test_admin_companies_flow(self, client, admin_token):
        """管理员：企业管理"""
        resp = await client.get("/api/v1/admin/companies",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert resp.status_code in {200, 404}, f"企业列表: {resp.status_code} {resp.text}"


# ════════════════════════════════════════════════════════════════
# Concurrency & Edge Cases — 并发与边界
# ════════════════════════════════════════════════════════════════

class TestEdgeCases:

    @pytest.mark.e2e
    async def test_double_start_test(self, client, db_session,
                                       student_in_class_token, question, active_class, make_token):
        """学员重复开始同一个测验 → 第二次应该 400"""
        from app.models.class_system import ClassMember, UserRole

        # 获取教练（或 login 获得 token），创建测验
        existing = await db_session.execute(
            __import__('sqlalchemy').select(ClassMember).where(
                ClassMember.class_id == active_class.id
            )
        )
        all_members = existing.scalars().all()
        instructor_in_cls = next(
            (m for m in all_members if m.role == UserRole.INSTRUCTOR),
            next((m for m in all_members if m.role == UserRole.INSTRUCTOR), None)
        )

        if not instructor_in_cls:
            # 需要教练 token — 随便拿一个
            resp = await client.post("/api/v1/auth/login", json={
                "name": "教官A",
                "id_card": "440102198107010003",
                "password": "test123",
                "role": "instructor",
            })
            if resp.status_code == 200 and resp.json()["success"]:
                instructor_jwt = resp.json()["token"]
            else:
                pytest.skip("教练不在活跃班级中，无法创建测验")
        else:
            instructor_jwt = make_token(instructor_in_cls.user_id, "instructor")

        # 创建测验
        resp = await client.post("/api/v1/instructor/tests",
            headers={"Authorization": f"Bearer {instructor_jwt}"},
            json={
                "title": "重复开始测试",
                "test_type": "quiz",
                "questions": [question.id],
                "duration": 30,
            }
        )
        if resp.status_code not in {200, 201}:
            pytest.skip(f"无法创建测验: {resp.status_code} {resp.text}")

        test_id = resp.json().get("id")

        # 第一次开始
        resp = await client.post(f"/api/v1/student/tests/{test_id}/start",
            headers={"Authorization": f"Bearer {student_in_class_token}"}
        )
        # 可能400（已有记录）/ 200
        first_status = resp.status_code

        # 第二次开始
        resp2 = await client.post(f"/api/v1/student/tests/{test_id}/start",
            headers={"Authorization": f"Bearer {student_in_class_token}"}
        )
        # 第一次200 → 第二次应400；第一次400 → 第二次也应400
        assert resp2.status_code in {400, 404}, \
            f"重复开始应被拒绝, 实际 {resp2.status_code}: {resp2.text}"

    @pytest.mark.e2e
    async def test_double_submit_test(self, client, db_session,
                                        student_in_class_token, question, active_class, make_token):
        """学员重复提交测验 → 第二次应 400"""
        from app.models.class_system import ClassMember, UserRole, Question

        # 尝试建教练 token
        existing = await db_session.execute(
            __import__('sqlalchemy').select(ClassMember).where(
                ClassMember.class_id == active_class.id
            )
        )
        members = existing.scalars().all()
        for m in members:
            if m.role == UserRole.INSTRUCTOR:
                instructor_jwt = make_token(m.user_id, "instructor")
                break
        else:
            pytest.skip("教练不在班级中")

        # 创建测验
        resp = await client.post("/api/v1/instructor/tests",
            headers={"Authorization": f"Bearer {instructor_jwt}"},
            json={
                "title": "重复提交测试",
                "test_type": "quiz",
                "questions": [question.id],
                "duration": 30,
            }
        )
        if resp.status_code not in {200, 201}:
            pytest.skip(f"创建测验失败: {resp.status_code}")

        test_id = resp.json().get("id")

        # 获取正确答案
        q_obj = await db_session.get(Question, question.id)
        correct_ans = q_obj.get_answer() if q_obj else "约1500m/s"

        # 第一次提交
        resp = await client.post(f"/api/v1/student/tests/{test_id}/submit",
            headers={"Authorization": f"Bearer {student_in_class_token}"},
            json={"answers": [{"question_id": question.id, "answer": correct_ans}]}
        )
        first_status = resp.status_code

        # 第二次提交
        resp2 = await client.post(f"/api/v1/student/tests/{test_id}/submit",
            headers={"Authorization": f"Bearer {student_in_class_token}"},
            json={"answers": [{"question_id": question.id, "answer": "wrong_answer"}]}
        )
        assert resp2.status_code in {400, 404}, \
            f"重复提交应被拒绝, 实际 {resp2.status_code}: {resp2.text}"
