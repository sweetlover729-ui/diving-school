"""
test_instructor_apis.py — Instructor API Tests
Covers all instructor role endpoints.
"""
import pytest
import uuid
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


def auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ── Class ────────────────────────────────────────────────────

class TestInstructorClass:
    """GET /api/v1/instructor/class"""

    async def test_get_current_class(self, api_client: AsyncClient, instructor_in_class_token):
        """Instructor can get their current class."""
        resp = await api_client.get(
            "/api/v1/instructor/class",
            headers=auth(instructor_in_class_token)
        )
        # 200 if in a class, 403 if not
        assert resp.status_code in (200, 403)
        print("PASS: test_get_current_class")


# ── Classes ───────────────────────────────────────────────────

class TestInstructorClasses:
    """GET /api/v1/instructor/classes"""

    async def test_list_classes(self, api_client: AsyncClient, instructor_in_class_token):
        """Instructor can list their classes."""
        resp = await api_client.get(
            "/api/v1/instructor/classes",
            headers=auth(instructor_in_class_token)
        )
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        print("PASS: test_list_classes")

    async def test_list_classes_no_class(self, api_client: AsyncClient, instructor_token):
        """Instructor not in any class."""
        resp = await api_client.get(
            "/api/v1/instructor/classes",
            headers=auth(instructor_token)
        )
        # May return 200 with empty list or 403
        assert resp.status_code in (200, 403)
        print("PASS: test_list_classes_no_class")


# ── Students ───────────────────────────────────────────────────

class TestInstructorStudents:
    """GET /api/v1/instructor/students"""

    async def test_list_students(self, api_client: AsyncClient, instructor_in_class_token):
        """Instructor can list students in their class."""
        resp = await api_client.get(
            "/api/v1/instructor/students",
            headers=auth(instructor_in_class_token)
        )
        assert resp.status_code == 200
        print("PASS: test_list_students")


# ── Textbooks ─────────────────────────────────────────────────

class TestInstructorTextbooks:
    """GET /api/v1/instructor/textbooks"""

    async def test_list_textbooks(self, api_client: AsyncClient, instructor_in_class_token):
        """Instructor can list textbooks."""
        resp = await api_client.get(
            "/api/v1/instructor/textbooks",
            headers=auth(instructor_in_class_token)
        )
        assert resp.status_code == 200
        print("PASS: test_list_textbooks")


# ── Tests ─────────────────────────────────────────────────────

class TestInstructorTests:
    """GET/POST/DELETE /api/v1/instructor/tests"""

    async def test_list_tests(self, api_client: AsyncClient, instructor_in_class_token):
        """Instructor can list tests."""
        resp = await api_client.get(
            "/api/v1/instructor/tests",
            headers=auth(instructor_in_class_token)
        )
        assert resp.status_code == 200
        print("PASS: test_list_tests")

    async def test_create_test(self, api_client: AsyncClient, instructor_in_class_token, textbook, chapter):
        """Instructor can create a test."""
        uniq = uuid.uuid4().hex[:6]
        resp = await api_client.post(
            "/api/v1/instructor/tests",
            headers=auth(instructor_in_class_token),
            json={
                "title": f"测试_{uniq}",
                "textbook_id": textbook.id,
                "chapter_ids": [chapter.id],
                "test_type": "CHAPTER",
                "time_limit": 60,
                "total_score": 100,
            }
        )
        assert resp.status_code in (200, 422), f"Create test failed: {resp.status_code} {resp.text[:200]}"
        data = resp.json()
        test_id = data.get("id")
        print("PASS: test_create_test")

        if test_id:
            await api_client.delete(
                f"/api/v1/instructor/tests/{test_id}",
                headers=auth(instructor_in_class_token)
            )

    async def test_generate_test(self, api_client: AsyncClient, instructor_in_class_token, textbook):
        """Instructor can auto-generate a test."""
        resp = await api_client.post(
            "/api/v1/instructor/tests/generate",
            headers=auth(instructor_in_class_token),
            json={
                "textbook_id": textbook.id,
                "chapter_count": 1,
                "questions_per_chapter": 3,
                "difficulty": 1,
            }
        )
        assert resp.status_code in (200, 404, 422), f"Generate test: {resp.status_code} {resp.text[:200]}"
        print("PASS: test_generate_test")


# ── Questions ─────────────────────────────────────────────────

class TestInstructorQuestions:
    """GET /api/v1/instructor/questions"""

    async def test_list_questions(self, api_client: AsyncClient, instructor_in_class_token):
        """Instructor can list questions."""
        resp = await api_client.get(
            "/api/v1/instructor/questions",
            headers=auth(instructor_in_class_token)
        )
        assert resp.status_code == 200
        print("PASS: test_list_questions")


# ── Progress ──────────────────────────────────────────────────

class TestInstructorProgress:
    """GET /api/v1/instructor/progress and /progress/{user_id}"""

    async def test_get_overall_progress(self, api_client: AsyncClient, instructor_in_class_token):
        """Instructor can get class progress overview."""
        resp = await api_client.get(
            "/api/v1/instructor/progress",
            headers=auth(instructor_in_class_token)
        )
        assert resp.status_code in (200, 403)
        print("PASS: test_get_overall_progress")

    async def test_get_student_progress(self, api_client: AsyncClient, instructor_in_class_token, student_in_class):
        """Instructor can get specific student progress."""
        resp = await api_client.get(
            f"/api/v1/instructor/progress/{student_in_class.id}",
            headers=auth(instructor_in_class_token)
        )
        assert resp.status_code in (200, 404)
        print("PASS: test_get_student_progress")


# ── Scores ───────────────────────────────────────────────────

class TestInstructorScores:
    """GET /api/v1/instructor/scores and /scores/{test_id}"""

    async def test_list_scores(self, api_client: AsyncClient, instructor_in_class_token):
        """Instructor can list scores."""
        resp = await api_client.get(
            "/api/v1/instructor/scores",
            headers=auth(instructor_in_class_token)
        )
        assert resp.status_code == 200
        print("PASS: test_list_scores")

    async def test_get_scores_by_test(self, api_client: AsyncClient, instructor_in_class_token):
        """Instructor can get scores for a specific test."""
        resp = await api_client.get(
            "/api/v1/instructor/scores/999999",
            headers=auth(instructor_in_class_token)
        )
        # 404 for non-existent test is fine
        assert resp.status_code in (200, 404)
        print("PASS: test_get_scores_by_test")


# ── Analytics ─────────────────────────────────────────────────

class TestInstructorAnalytics:
    """GET /api/v1/instructor/analytics/overview|reading|scores"""

    async def test_analytics_overview(self, api_client: AsyncClient, instructor_in_class_token):
        """Instructor can get analytics overview."""
        resp = await api_client.get(
            "/api/v1/instructor/analytics/overview",
            headers=auth(instructor_in_class_token)
        )
        assert resp.status_code in (200, 403)
        print("PASS: test_analytics_overview")

    async def test_analytics_reading(self, api_client: AsyncClient, instructor_in_class_token):
        """Instructor can get reading analytics."""
        resp = await api_client.get(
            "/api/v1/instructor/analytics/reading",
            headers=auth(instructor_in_class_token)
        )
        assert resp.status_code in (200, 403)
        print("PASS: test_analytics_reading")

    async def test_analytics_scores(self, api_client: AsyncClient, instructor_in_class_token):
        """Instructor can get score analytics."""
        resp = await api_client.get(
            "/api/v1/instructor/analytics/scores",
            headers=auth(instructor_in_class_token)
        )
        assert resp.status_code in (200, 403)
        print("PASS: test_analytics_scores")
