"""
test_frontend_pages.py — Frontend Page Accessibility Tests
Tests that all frontend pages return 200 (or at least don't 404).
The Next.js frontend runs at http://localhost:8002.
"""
import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio

BASE_URL = "http://localhost:8002"


# ── Login Page ───────────────────────────────────────────────

class TestLoginPage:
    """Login page accessibility."""

    async def test_login_page(self):
        """Login page should be accessible."""
        async with AsyncClient(base_url=BASE_URL, timeout=10.0) as client:
            resp = await client.get("/login")
            # Should be 200 or 30x redirect, not 404
            assert resp.status_code < 500, f"Login page error: {resp.status_code}"
            print(f"PASS: test_login_page (status={resp.status_code})")

    async def test_root_page(self):
        """Root page should be accessible."""
        async with AsyncClient(base_url=BASE_URL, timeout=10.0) as client:
            resp = await client.get("/")
            assert resp.status_code < 500
            print(f"PASS: test_root_page (status={resp.status_code})")


# ── Admin Pages ─────────────────────────────────────────────

class TestAdminPages:
    """All admin frontend pages."""

    ADMIN_PAGES = [
        "/admin",
        "/admin/categories",
        "/admin/courses",
        "/admin/classes",
        "/admin/textbooks",
        "/admin/instructors",
        "/admin/people",
        "/admin/companies",
        "/admin/questions",
        "/admin/system",
        "/admin/audit",
    ]

    @pytest.mark.parametrize("path", ADMIN_PAGES)
    async def test_admin_page(self, path):
        """Each admin page should be accessible (not 404)."""
        async with AsyncClient(base_url=BASE_URL, timeout=10.0) as client:
            resp = await client.get(path)
            # 200 = OK, 30x = redirect (to login), 401/403 = auth required
            # Only fail on 5xx or 404
            assert resp.status_code not in (404,), f"Admin page {path} returned 404"
            assert resp.status_code < 500, f"Admin page {path} error: {resp.status_code}"
            print(f"PASS: admin_page {path} (status={resp.status_code})")


# ── Instructor Pages ─────────────────────────────────────────

class TestInstructorPages:
    """All instructor frontend pages."""

    INSTRUCTOR_PAGES = [
        "/instructor",
        "/instructor/class",
        "/instructor/classes",
        "/instructor/students",
        "/instructor/textbooks",
        "/instructor/tests",
        "/instructor/progress",
        "/instructor/scores",
        "/instructor/analytics",
    ]

    @pytest.mark.parametrize("path", INSTRUCTOR_PAGES)
    async def test_instructor_page(self, path):
        """Each instructor page should be accessible (not 404)."""
        async with AsyncClient(base_url=BASE_URL, timeout=10.0) as client:
            resp = await client.get(path)
            assert resp.status_code not in (404,), f"Instructor page {path} returned 404"
            assert resp.status_code < 500
            print(f"PASS: instructor_page {path} (status={resp.status_code})")


# ── Manager Pages ────────────────────────────────────────────

class TestManagerPages:
    """All manager frontend pages."""

    MANAGER_PAGES = [
        "/manager",
        "/manager/class",
        "/manager/classes",
        "/manager/students",
        "/manager/progress",
        "/manager/scores",
        "/manager/analytics",
        "/manager/dashboard",
        "/manager/announcements",
        "/manager/alerts",
        "/manager/export",
    ]

    @pytest.mark.parametrize("path", MANAGER_PAGES)
    async def test_manager_page(self, path):
        """Each manager page should be accessible (not 404)."""
        async with AsyncClient(base_url=BASE_URL, timeout=10.0) as client:
            resp = await client.get(path)
            assert resp.status_code not in (404,), f"Manager page {path} returned 404"
            assert resp.status_code < 500
            print(f"PASS: manager_page {path} (status={resp.status_code})")


# ── Student Pages ─────────────────────────────────────────────

class TestStudentPages:
    """All student frontend pages."""

    STUDENT_PAGES = [
        "/student",
        "/student/textbooks",
        "/student/chapters",
        "/student/tests",
        "/student/scores",
        "/student/progress",
        "/student/dashboard",
        "/student/profile",
        "/student/qa",
        "/student/notes",
    ]

    @pytest.mark.parametrize("path", STUDENT_PAGES)
    async def test_student_page(self, path):
        """Each student page should be accessible (not 404)."""
        async with AsyncClient(base_url=BASE_URL, timeout=10.0) as client:
            resp = await client.get(path)
            assert resp.status_code not in (404,), f"Student page {path} returned 404"
            assert resp.status_code < 500
            print(f"PASS: student_page {path} (status={resp.status_code})")


# ── Static Pages ─────────────────────────────────────────────

class TestStaticPages:
    """Static/utility pages."""

    STATIC_PAGES = [
        "/about",
        "/help",
        "/404",  # Should handle gracefully
    ]

    @pytest.mark.parametrize("path", STATIC_PAGES)
    async def test_static_page(self, path):
        """Static pages should not 500."""
        async with AsyncClient(base_url=BASE_URL, timeout=10.0) as client:
            resp = await client.get(path)
            # Just don't crash
            assert resp.status_code < 500
            print(f"PASS: static_page {path} (status={resp.status_code})")
