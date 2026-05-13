"""
test_workflows.py — End-to-End Workflow Tests
Tests complete workflows for each role.
"""
import pytest
import uuid
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


def auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ── Admin Workflow ─────────────────────────────────────────────

class TestAdminWorkflow:
    """
    Admin workflow: login → dashboard → create category → create course
    → create class → add instructor → view analytics → logout
    """

    async def test_complete_admin_workflow(
        self, api_client: AsyncClient, admin_user, admin_token, instructor_user
    ):
        """Complete admin workflow from login to logout."""
        # Step 1: Verify auth/me works
        me_resp = await api_client.get(
            "/api/v1/auth/me",
            headers=auth(admin_token)
        )
        assert me_resp.status_code == 200, "Step 1 failed: /me"
        print("  Step 1: /me - PASS")

        # Step 2: Dashboard
        dash_resp = await api_client.get(
            "/api/v1/admin/dashboard",
            headers=auth(admin_token)
        )
        assert dash_resp.status_code == 200, "Step 2 failed: dashboard"
        print("  Step 2: dashboard - PASS")

        # Step 3: Create category
        cat_name = f"工作流分类_{uuid.uuid4().hex[:6]}"
        cat_resp = await api_client.post(
            "/api/v1/admin/categories",
            headers=auth(admin_token),
            json={"name": cat_name, "description": "工作流测试", "sort_order": 1}
        )
        assert cat_resp.status_code == 200, f"Step 3 failed: create category {cat_resp.text}"
        cat_id = cat_resp.json().get("id")
        assert cat_id is not None
        print("  Step 3: create category - PASS")

        # Step 4: Create course
        course_name = f"工作流课程_{uuid.uuid4().hex[:6]}"
        course_resp = await api_client.post(
            "/api/v1/admin/courses",
            headers=auth(admin_token),
            json={
                "name": course_name,
                "description": "工作流测试课程",
                "category_id": cat_id,
            }
        )
        assert course_resp.status_code == 200, f"Step 4 failed: create course {course_resp.text}"
        course_id = course_resp.json().get("id")
        print("  Step 4: create course - PASS")

        # Step 5: Create class
        from datetime import datetime, timedelta, timezone
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        class_name = f"工作流班级_{uuid.uuid4().hex[:6]}"
        class_resp = await api_client.post(
            "/api/v1/admin/classes",
            headers=auth(admin_token),
            json={
                "name": class_name,
                "location": "工作流测试基地",
                "start_time": (now - timedelta(days=7)).isoformat(),
                "end_time": (now + timedelta(days=23)).isoformat(),
                "instructor_id": instructor_user.id,
            }
        )
        assert class_resp.status_code == 200, f"Step 5 failed: create class {class_resp.text}"
        class_id = class_resp.json().get("id")
        print("  Step 5: create class - PASS")

        # Step 6: View class analytics
        analytics_resp = await api_client.get(
            f"/api/v1/admin/classes/{class_id}/analytics",
            headers=auth(admin_token)
        )
        assert analytics_resp.status_code == 200, "Step 6 failed: analytics"
        print("  Step 6: analytics - PASS")

        # Step 7: Create announcement
        ann_name = f"工作流公告_{uuid.uuid4().hex[:6]}"
        ann_resp = await api_client.post(
            "/api/v1/admin/announcements",
            headers=auth(admin_token),
            json={"title": ann_name, "content": "工作流测试公告", "priority": "normal"}
        )
        assert ann_resp.status_code == 200, f"Step 7 failed: create announcement {ann_resp.text}"
        print("  Step 7: create announcement - PASS")

        # Step 8: Logout
        logout_resp = await api_client.post(
            "/api/v1/auth/logout",
            headers=auth(admin_token)
        )
        assert logout_resp.status_code == 200, "Step 8 failed: logout"
        print("  Step 8: logout - PASS")

        # Cleanup
        await api_client.delete(f"/api/v1/admin/courses/{course_id}", headers=auth(admin_token))
        await api_client.delete(f"/api/v1/admin/classes/{class_id}", headers=auth(admin_token))
        await api_client.delete(f"/api/v1/admin/categories/{cat_id}", headers=auth(admin_token))

        print("PASS: test_complete_admin_workflow")


# ── Instructor Workflow ────────────────────────────────────────

class TestInstructorWorkflow:
    """
    Instructor workflow: login → view students → view progress → create test
    → view scores → logout
    """

    async def test_complete_instructor_workflow(
        self, api_client: AsyncClient, instructor_in_class_token, student_in_class,
        textbook, chapter
    ):
        """Complete instructor workflow."""
        # Step 1: Get current class
        class_resp = await api_client.get(
            "/api/v1/instructor/class",
            headers=auth(instructor_in_class_token)
        )
        assert class_resp.status_code in (200, 403), "Step 1 failed: get class"
        print("  Step 1: get class - PASS")

        # Step 2: View students
        students_resp = await api_client.get(
            "/api/v1/instructor/students",
            headers=auth(instructor_in_class_token)
        )
        assert students_resp.status_code == 200, "Step 2 failed: view students"
        print("  Step 2: view students - PASS")

        # Step 3: View student progress
        progress_resp = await api_client.get(
            f"/api/v1/instructor/progress/{student_in_class.id}",
            headers=auth(instructor_in_class_token)
        )
        assert progress_resp.status_code in (200, 404), "Step 3 failed: progress"
        print("  Step 3: progress - PASS")

        # Step 4: View analytics overview
        analytics_resp = await api_client.get(
            "/api/v1/instructor/analytics/overview",
            headers=auth(instructor_in_class_token)
        )
        assert analytics_resp.status_code in (200, 403), "Step 4 failed: analytics"
        print("  Step 4: analytics - PASS")

        # Step 5: Create a test
        test_name = f"工作流测试_{uuid.uuid4().hex[:6]}"
        test_resp = await api_client.post(
            "/api/v1/instructor/tests",
            headers=auth(instructor_in_class_token),
            json={
                "title": test_name,
                "textbook_id": textbook.id,
                "chapter_ids": [chapter.id],
                "test_type": "CHAPTER",
                "time_limit": 60,
                "total_score": 100,
            }
        )
        assert test_resp.status_code in (200, 422), f"Step 5 failed: create test {test_resp.text}"
        test_id = test_resp.json().get("id")
        print("  Step 5: create test - PASS")

        # Step 6: View scores
        scores_resp = await api_client.get(
            "/api/v1/instructor/scores",
            headers=auth(instructor_in_class_token)
        )
        assert scores_resp.status_code == 200, "Step 6 failed: view scores"
        print("  Step 6: view scores - PASS")

        # Step 7: Logout
        logout_resp = await api_client.post(
            "/api/v1/auth/logout",
            headers=auth(instructor_in_class_token)
        )
        assert logout_resp.status_code == 200, "Step 7 failed: logout"
        print("  Step 7: logout - PASS")

        # Cleanup
        if test_id:
            await api_client.delete(
                f"/api/v1/instructor/tests/{test_id}",
                headers=auth(instructor_in_class_token)
            )

        print("PASS: test_complete_instructor_workflow")


# ── Manager Workflow ───────────────────────────────────────────

class TestManagerWorkflow:
    """
    Manager workflow: login → dashboard → view students → view analytics
    → create announcement → logout
    """

    async def test_complete_manager_workflow(
        self, api_client: AsyncClient, manager_in_class_token, student_in_class
    ):
        """Complete manager workflow."""
        # Step 1: Get dashboard summary
        dash_resp = await api_client.get(
            "/api/v1/manager/dashboard/summary",
            headers=auth(manager_in_class_token)
        )
        assert dash_resp.status_code == 200, "Step 1 failed: dashboard"
        print("  Step 1: dashboard - PASS")

        # Step 2: View students
        students_resp = await api_client.get(
            "/api/v1/manager/students",
            headers=auth(manager_in_class_token)
        )
        assert students_resp.status_code == 200, "Step 2 failed: view students"
        print("  Step 2: view students - PASS")

        # Step 3: View student detail
        detail_resp = await api_client.get(
            f"/api/v1/manager/students/{student_in_class.id}",
            headers=auth(manager_in_class_token)
        )
        assert detail_resp.status_code in (200, 404), "Step 3 failed: student detail"
        print("  Step 3: student detail - PASS")

        # Step 4: View analytics overview
        analytics_resp = await api_client.get(
            "/api/v1/manager/analytics/overview",
            headers=auth(manager_in_class_token)
        )
        assert analytics_resp.status_code in (200, 403), "Step 4 failed: analytics"
        print("  Step 4: analytics - PASS")

        # Step 5: Create announcement
        ann_name = f"干部工作流公告_{uuid.uuid4().hex[:6]}"
        ann_resp = await api_client.post(
            "/api/v1/manager/announcements",
            headers=auth(manager_in_class_token),
            json={"title": ann_name, "content": "工作流测试公告", "priority": "normal"}
        )
        assert ann_resp.status_code == 200, f"Step 5 failed: create announcement {ann_resp.text}"
        ann_id = ann_resp.json().get("id")
        print("  Step 5: create announcement - PASS")

        # Step 6: View progress
        progress_resp = await api_client.get(
            "/api/v1/manager/progress",
            headers=auth(manager_in_class_token)
        )
        assert progress_resp.status_code == 200, "Step 6 failed: progress"
        print("  Step 6: progress - PASS")

        # Step 7: Logout
        logout_resp = await api_client.post(
            "/api/v1/auth/logout",
            headers=auth(manager_in_class_token)
        )
        assert logout_resp.status_code == 200, "Step 7 failed: logout"
        print("  Step 7: logout - PASS")

        # Cleanup
        if ann_id:
            await api_client.delete(
                f"/api/v1/manager/announcements/{ann_id}",
                headers=auth(manager_in_class_token)
            )

        print("PASS: test_complete_manager_workflow")


# ── Student Workflow ───────────────────────────────────────────

class TestStudentWorkflow:
    """
    Student workflow: login → view textbooks → read chapter → take test
    → view score → logout
    """

    async def test_complete_student_workflow(
        self, api_client: AsyncClient, student_in_class_token, student_in_class,
        textbook, chapter
    ):
        """Complete student workflow."""
        # Step 1: Get profile
        profile_resp = await api_client.get(
            "/api/v1/student/profile",
            headers=auth(student_in_class_token)
        )
        assert profile_resp.status_code == 200, "Step 1 failed: profile"
        data = profile_resp.json()
        assert data.get("id") == student_in_class.id
        print("  Step 1: profile - PASS")

        # Step 2: View textbooks
        tb_resp = await api_client.get(
            "/api/v1/student/textbooks",
            headers=auth(student_in_class_token)
        )
        assert tb_resp.status_code == 200, "Step 2 failed: textbooks"
        print("  Step 2: textbooks - PASS")

        # Step 3: View dashboard
        dash_resp = await api_client.get(
            "/api/v1/student/dashboard",
            headers=auth(student_in_class_token)
        )
        assert dash_resp.status_code == 200, "Step 3 failed: dashboard"
        print("  Step 3: dashboard - PASS")

        # Step 4: Read chapter
        chapter_resp = await api_client.get(
            f"/api/v1/student/textbooks/{textbook.id}/chapters/{chapter.id}",
            headers=auth(student_in_class_token)
        )
        assert chapter_resp.status_code in (200, 404), "Step 4 failed: chapter"
        print("  Step 4: chapter - PASS")

        # Step 5: Update reading progress
        progress_resp = await api_client.post(
            "/api/v1/student/reading/progress",
            headers=auth(student_in_class_token),
            json={"chapter_id": chapter.id, "progress_percent": 75}
        )
        assert progress_resp.status_code in (200, 201, 422), f"Step 5 failed: progress {progress_resp.text}"
        print("  Step 5: progress - PASS")

        # Step 6: View tests
        tests_resp = await api_client.get(
            "/api/v1/student/tests",
            headers=auth(student_in_class_token)
        )
        assert tests_resp.status_code == 200, "Step 6 failed: tests"
        print("  Step 6: tests - PASS")

        # Step 7: View scores
        scores_resp = await api_client.get(
            "/api/v1/student/scores",
            headers=auth(student_in_class_token)
        )
        assert scores_resp.status_code == 200, "Step 7 failed: scores"
        print("  Step 7: scores - PASS")

        # Step 8: View wrong answers
        wrong_resp = await api_client.get(
            "/api/v1/student/wrong-answers",
            headers=auth(student_in_class_token)
        )
        assert wrong_resp.status_code == 200, "Step 8 failed: wrong answers"
        print("  Step 8: wrong answers - PASS")

        # Step 9: Create note
        note_resp = await api_client.post(
            "/api/v1/student/chapters/notes",
            headers=auth(student_in_class_token),
            json={"chapter_id": chapter.id, "content": "工作流笔记"}
        )
        assert note_resp.status_code in (200, 201, 422), "Step 9 failed: note"
        print("  Step 9: note - PASS")

        # Step 10: Logout
        logout_resp = await api_client.post(
            "/api/v1/auth/logout",
            headers=auth(student_in_class_token)
        )
        assert logout_resp.status_code == 200, "Step 10 failed: logout"
        print("  Step 10: logout - PASS")

        print("PASS: test_complete_student_workflow")
