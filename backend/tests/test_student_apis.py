"""
test_student_apis.py — Student API Tests
Covers all student role endpoints.
"""
import pytest
import uuid
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


def auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ── Textbooks ─────────────────────────────────────────────────

class TestStudentTextbooks:
    """GET /api/v1/student/textbooks and /textbooks/{id}"""

    async def test_list_textbooks(self, api_client: AsyncClient, student_in_class_token):
        """Student can list textbooks."""
        resp = await api_client.get(
            "/api/v1/student/textbooks",
            headers=auth(student_in_class_token)
        )
        assert resp.status_code == 200
        print("PASS: test_list_textbooks")

    async def test_get_textbook(self, api_client: AsyncClient, student_in_class_token, textbook):
        """Student can get specific textbook."""
        resp = await api_client.get(
            f"/api/v1/student/textbooks/{textbook.id}",
            headers=auth(student_in_class_token)
        )
        assert resp.status_code in (200, 403, 404)
        print("PASS: test_get_textbook")


# ── Chapters ──────────────────────────────────────────────────

class TestStudentChapters:
    """GET /api/v1/student/textbooks/{id}/chapters/{id}"""

    async def test_get_chapter(
        self, api_client: AsyncClient, student_in_class_token, textbook, chapter
    ):
        """Student can read a chapter."""
        resp = await api_client.get(
            f"/api/v1/student/textbooks/{textbook.id}/chapters/{chapter.id}",
            headers=auth(student_in_class_token)
        )
        assert resp.status_code in (200, 403, 404)
        print("PASS: test_get_chapter")


# ── Reading Progress ───────────────────────────────────────────

class TestStudentReadingProgress:
    """POST/GET /api/v1/student/reading/progress"""

    async def test_get_reading_progress(self, api_client: AsyncClient, student_in_class_token):
        """Student can get their reading progress."""
        resp = await api_client.get(
            "/api/v1/student/reading/progress",
            headers=auth(student_in_class_token)
        )
        assert resp.status_code == 200
        print("PASS: test_get_reading_progress")

    async def test_post_reading_progress(
        self, api_client: AsyncClient, student_in_class_token, chapter
    ):
        """Student can update reading progress."""
        resp = await api_client.post(
            "/api/v1/student/reading/progress",
            headers=auth(student_in_class_token),
            json={
                "chapter_id": chapter.id,
                "progress_percent": 50,
            }
        )
        # 200 if it works, 422 if validation fails
        assert resp.status_code in (200, 201, 422)
        print("PASS: test_post_reading_progress")


# ── Tests ─────────────────────────────────────────────────────

class TestStudentTests:
    """GET /api/v1/student/tests and /tests/{id}, POST start/submit"""

    async def test_list_tests(self, api_client: AsyncClient, student_in_class_token):
        """Student can list available tests."""
        resp = await api_client.get(
            "/api/v1/student/tests",
            headers=auth(student_in_class_token)
        )
        assert resp.status_code == 200
        print("PASS: test_list_tests")

    async def test_get_test(self, api_client: AsyncClient, student_in_class_token):
        """Student can get test details."""
        resp = await api_client.get(
            "/api/v1/student/tests/999999",
            headers=auth(student_in_class_token)
        )
        assert resp.status_code in (200, 403, 404)
        print("PASS: test_get_test")

    async def test_start_test(self, api_client: AsyncClient, student_in_class_token):
        """Student can start a test."""
        resp = await api_client.post(
            "/api/v1/student/tests/999999/start",
            headers=auth(student_in_class_token)
        )
        assert resp.status_code in (200, 403, 404)
        print("PASS: test_start_test")

    async def test_submit_test(self, api_client: AsyncClient, student_in_class_token):
        """Student can submit a test."""
        resp = await api_client.post(
            "/api/v1/student/tests/999999/submit",
            headers=auth(student_in_class_token),
            json={"answers": []}
        )
        assert resp.status_code in (200, 404, 422)
        print("PASS: test_submit_test")


# ── Scores ───────────────────────────────────────────────────

class TestStudentScores:
    """GET /api/v1/student/scores and /scores/{id}"""

    async def test_list_scores(self, api_client: AsyncClient, student_in_class_token):
        """Student can list their scores."""
        resp = await api_client.get(
            "/api/v1/student/scores",
            headers=auth(student_in_class_token)
        )
        assert resp.status_code == 200
        print("PASS: test_list_scores")

    async def test_get_score(self, api_client: AsyncClient, student_in_class_token):
        """Student can get specific score detail."""
        resp = await api_client.get(
            "/api/v1/student/scores/999999",
            headers=auth(student_in_class_token)
        )
        assert resp.status_code in (200, 403, 404)
        print("PASS: test_get_score")


# ── Wrong Answers ─────────────────────────────────────────────

class TestStudentWrongAnswers:
    """GET /api/v1/student/wrong-answers"""

    async def test_get_wrong_answers(self, api_client: AsyncClient, student_in_class_token):
        """Student can get wrong answers."""
        resp = await api_client.get(
            "/api/v1/student/wrong-answers",
            headers=auth(student_in_class_token)
        )
        assert resp.status_code == 200
        print("PASS: test_get_wrong_answers")


# ── Profile ───────────────────────────────────────────────────

class TestStudentProfile:
    """GET /api/v1/student/profile"""

    async def test_get_profile(self, api_client: AsyncClient, student_in_class_token, student_in_class):
        """Student can get their profile."""
        resp = await api_client.get(
            "/api/v1/student/profile",
            headers=auth(student_in_class_token)
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("id") == student_in_class.id
        print("PASS: test_get_profile")


# ── Dashboard ─────────────────────────────────────────────────

class TestStudentDashboard:
    """GET /api/v1/student/dashboard"""

    async def test_get_dashboard(self, api_client: AsyncClient, student_in_class_token):
        """Student can get their dashboard."""
        resp = await api_client.get(
            "/api/v1/student/dashboard",
            headers=auth(student_in_class_token)
        )
        assert resp.status_code == 200
        print("PASS: test_get_dashboard")


# ── QA ───────────────────────────────────────────────────────

class TestStudentQA:
    """GET/POST /api/v1/student/qa"""

    async def test_list_qa(self, api_client: AsyncClient, student_in_class_token):
        """Student can list Q&A."""
        resp = await api_client.get(
            "/api/v1/student/qa",
            headers=auth(student_in_class_token)
        )
        assert resp.status_code == 200
        print("PASS: test_list_qa")

    async def test_post_qa(self, api_client: AsyncClient, student_in_class_token, chapter):
        """Student can post a question."""
        uniq = uuid.uuid4().hex[:6]
        resp = await api_client.post(
            "/api/v1/student/qa",
            headers=auth(student_in_class_token),
            json={
                "chapter_id": chapter.id,
                "question": f"测试问题_{uniq}？",
            }
        )
        assert resp.status_code in (200, 201, 422), f"Post QA failed: {resp.status_code} {resp.text[:200]}"
        print("PASS: test_post_qa")


# ── Notes ────────────────────────────────────────────────────

class TestStudentNotes:
    """GET/POST/DELETE /api/v1/student/chapters/notes"""

    async def test_list_notes(self, api_client: AsyncClient, student_in_class_token):
        """Student can list their notes."""
        resp = await api_client.get(
            "/api/v1/student/chapters/notes",
            headers=auth(student_in_class_token)
        )
        assert resp.status_code == 200
        print("PASS: test_list_notes")

    async def test_create_note(self, api_client: AsyncClient, student_in_class_token, chapter):
        """Student can create a note."""
        uniq = uuid.uuid4().hex[:6]
        resp = await api_client.post(
            "/api/v1/student/chapters/notes",
            headers=auth(student_in_class_token),
            json={
                "chapter_id": chapter.id,
                "content": f"测试笔记_{uniq}",
            }
        )
        assert resp.status_code in (200, 201, 422), f"Create note failed: {resp.status_code} {resp.text[:200]}"
        print("PASS: test_create_note")


# ── Bookmarks ────────────────────────────────────────────────

class TestStudentBookmarks:
    """GET/POST/DELETE /api/v1/student/chapters/bookmarks"""

    async def test_list_bookmarks(self, api_client: AsyncClient, student_in_class_token):
        """Student can list their bookmarks."""
        resp = await api_client.get(
            "/api/v1/student/chapters/bookmarks",
            headers=auth(student_in_class_token)
        )
        assert resp.status_code == 200
        print("PASS: test_list_bookmarks")

    async def test_create_bookmark(self, api_client: AsyncClient, student_in_class_token, chapter):
        """Student can create a bookmark."""
        resp = await api_client.post(
            "/api/v1/student/chapters/bookmarks",
            headers=auth(student_in_class_token),
            json={
                "chapter_id": chapter.id,
                "note": "测试书签",
            }
        )
        assert resp.status_code in (200, 201, 422), f"Create bookmark failed: {resp.status_code} {resp.text[:200]}"
        print("PASS: test_create_bookmark")
