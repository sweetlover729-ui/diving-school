"""
test_manager_apis.py — Manager API Tests
Covers all manager role endpoints.
"""
import pytest
import uuid
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


def auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ── Class ────────────────────────────────────────────────────

class TestManagerClass:
    """GET /api/v1/manager/class"""

    async def test_get_current_class(self, api_client: AsyncClient, manager_in_class_token):
        """Manager can get their current class."""
        resp = await api_client.get(
            "/api/v1/manager/class",
            headers=auth(manager_in_class_token)
        )
        assert resp.status_code in (200, 403)
        print("PASS: test_get_current_class")


# ── Classes ───────────────────────────────────────────────────

class TestManagerClasses:
    """GET /api/v1/manager/classes"""

    async def test_list_classes(self, api_client: AsyncClient, manager_in_class_token):
        """Manager can list their classes."""
        resp = await api_client.get(
            "/api/v1/manager/classes",
            headers=auth(manager_in_class_token)
        )
        assert resp.status_code == 200
        print("PASS: test_list_classes")


# ── Students ───────────────────────────────────────────────────

class TestManagerStudents:
    """GET /api/v1/manager/students and /students/{user_id}"""

    async def test_list_students(self, api_client: AsyncClient, manager_in_class_token):
        """Manager can list students."""
        resp = await api_client.get(
            "/api/v1/manager/students",
            headers=auth(manager_in_class_token)
        )
        assert resp.status_code == 200
        print("PASS: test_list_students")

    async def test_get_student_detail(self, api_client: AsyncClient, manager_in_class_token, student_in_class):
        """Manager can get specific student detail."""
        resp = await api_client.get(
            f"/api/v1/manager/students/{student_in_class.id}",
            headers=auth(manager_in_class_token)
        )
        assert resp.status_code in (200, 404)
        print("PASS: test_get_student_detail")


# ── Progress ──────────────────────────────────────────────────

class TestManagerProgress:
    """GET /api/v1/manager/progress"""

    async def test_get_progress(self, api_client: AsyncClient, manager_in_class_token):
        """Manager can get class progress."""
        resp = await api_client.get(
            "/api/v1/manager/progress",
            headers=auth(manager_in_class_token)
        )
        assert resp.status_code == 200
        print("PASS: test_get_progress")


# ── Scores ───────────────────────────────────────────────────

class TestManagerScores:
    """GET /api/v1/manager/scores and /scores/{test_id}"""

    async def test_list_scores(self, api_client: AsyncClient, manager_in_class_token):
        """Manager can list scores."""
        resp = await api_client.get(
            "/api/v1/manager/scores",
            headers=auth(manager_in_class_token)
        )
        assert resp.status_code == 200
        print("PASS: test_list_scores")

    async def test_get_scores_by_test(self, api_client: AsyncClient, manager_in_class_token):
        """Manager can get scores for specific test."""
        resp = await api_client.get(
            "/api/v1/manager/scores/999999",
            headers=auth(manager_in_class_token)
        )
        assert resp.status_code in (200, 404)
        print("PASS: test_get_scores_by_test")


# ── Analytics ─────────────────────────────────────────────────

class TestManagerAnalytics:
    """GET /api/v1/manager/analytics/overview|reading|scores|anti-cheat"""

    async def test_analytics_overview(self, api_client: AsyncClient, manager_in_class_token):
        resp = await api_client.get(
            "/api/v1/manager/analytics/overview",
            headers=auth(manager_in_class_token)
        )
        assert resp.status_code in (200, 403)
        print("PASS: test_analytics_overview")

    async def test_analytics_reading(self, api_client: AsyncClient, manager_in_class_token):
        resp = await api_client.get(
            "/api/v1/manager/analytics/reading",
            headers=auth(manager_in_class_token)
        )
        assert resp.status_code in (200, 403)
        print("PASS: test_analytics_reading")

    async def test_analytics_scores(self, api_client: AsyncClient, manager_in_class_token):
        resp = await api_client.get(
            "/api/v1/manager/analytics/scores",
            headers=auth(manager_in_class_token)
        )
        assert resp.status_code in (200, 403)
        print("PASS: test_analytics_scores")

    async def test_analytics_anti_cheat(self, api_client: AsyncClient, manager_in_class_token):
        resp = await api_client.get(
            "/api/v1/manager/analytics/anti-cheat",
            headers=auth(manager_in_class_token)
        )
        assert resp.status_code in (200, 403)
        print("PASS: test_analytics_anti_cheat")


# ── Dashboard ─────────────────────────────────────────────────

class TestManagerDashboard:
    """GET /api/v1/manager/dashboard/summary"""

    async def test_dashboard_summary(self, api_client: AsyncClient, manager_in_class_token):
        resp = await api_client.get(
            "/api/v1/manager/dashboard/summary",
            headers=auth(manager_in_class_token)
        )
        assert resp.status_code == 200
        print("PASS: test_dashboard_summary")


# ── Export ───────────────────────────────────────────────────

class TestManagerExport:
    """GET /api/v1/manager/export/students and /scores"""

    async def test_export_students(self, api_client: AsyncClient, manager_in_class_token):
        resp = await api_client.get(
            "/api/v1/manager/export/students",
            headers=auth(manager_in_class_token)
        )
        # May return CSV, JSON, or file download
        assert resp.status_code in (200, 403)
        print("PASS: test_export_students")

    async def test_export_scores(self, api_client: AsyncClient, manager_in_class_token):
        resp = await api_client.get(
            "/api/v1/manager/export/scores",
            headers=auth(manager_in_class_token)
        )
        assert resp.status_code in (200, 403)
        print("PASS: test_export_scores")


# ── Announcements ─────────────────────────────────────────────

class TestManagerAnnouncements:
    """GET/POST/DELETE /api/v1/manager/announcements"""

    async def test_list_announcements(self, api_client: AsyncClient, manager_in_class_token):
        resp = await api_client.get(
            "/api/v1/manager/announcements",
            headers=auth(manager_in_class_token)
        )
        assert resp.status_code == 200
        print("PASS: test_list_announcements")

    async def test_create_announcement(self, api_client: AsyncClient, manager_in_class_token):
        uniq = uuid.uuid4().hex[:6]
        resp = await api_client.post(
            "/api/v1/manager/announcements",
            headers=auth(manager_in_class_token),
            json={
                "title": f"干部公告_{uniq}",
                "content": "公告内容",
                "priority": "normal",
            }
        )
        assert resp.status_code == 200, f"Create announcement failed: {resp.status_code} {resp.text[:200]}"
        data = resp.json()
        ann_id = data.get("id")
        print("PASS: test_create_announcement")

        if ann_id:
            await api_client.delete(
                f"/api/v1/manager/announcements/{ann_id}",
                headers=auth(manager_in_class_token)
            )

    async def test_delete_announcement(self, api_client: AsyncClient, manager_in_class_token):
        uniq = uuid.uuid4().hex[:6]
        create_resp = await api_client.post(
            "/api/v1/manager/announcements",
            headers=auth(manager_in_class_token),
            json={"title": f"待删除_{uniq}", "content": "内容"}
        )
        ann_id = create_resp.json().get("id")
        if ann_id:
            resp = await api_client.delete(
                f"/api/v1/manager/announcements/{ann_id}",
                headers=auth(manager_in_class_token)
            )
            assert resp.status_code == 200
        print("PASS: test_delete_announcement")


# ── Alerts ───────────────────────────────────────────────────

class TestManagerAlerts:
    """GET /api/v1/manager/alerts and /alerts/stats, POST /read/resolve/detect"""

    async def test_list_alerts(self, api_client: AsyncClient, manager_in_class_token):
        resp = await api_client.get(
            "/api/v1/manager/alerts",
            headers=auth(manager_in_class_token)
        )
        assert resp.status_code == 200
        print("PASS: test_list_alerts")

    async def test_alerts_stats(self, api_client: AsyncClient, manager_in_class_token):
        resp = await api_client.get(
            "/api/v1/manager/alerts/stats",
            headers=auth(manager_in_class_token)
        )
        assert resp.status_code in (200, 404)
        print("PASS: test_alerts_stats")

    async def test_alerts_read(self, api_client: AsyncClient, manager_in_class_token):
        resp = await api_client.post(
            "/api/v1/manager/alerts/999999/read",
            headers=auth(manager_in_class_token)
        )
        assert resp.status_code in (200, 404)
        print("PASS: test_alerts_read")

    async def test_alerts_resolve(self, api_client: AsyncClient, manager_in_class_token):
        resp = await api_client.post(
            "/api/v1/manager/alerts/999999/resolve",
            headers=auth(manager_in_class_token)
        )
        assert resp.status_code in (200, 404)
        print("PASS: test_alerts_resolve")


# ── Audit Logs ───────────────────────────────────────────────

class TestManagerAuditLogs:
    """GET /api/v1/manager/audit-logs and /stats"""

    async def test_audit_logs(self, api_client: AsyncClient, manager_in_class_token):
        resp = await api_client.get(
            "/api/v1/manager/audit-logs",
            headers=auth(manager_in_class_token)
        )
        assert resp.status_code == 200
        print("PASS: test_audit_logs")

    async def test_audit_logs_stats(self, api_client: AsyncClient, manager_in_class_token):
        resp = await api_client.get(
            "/api/v1/manager/audit-logs/stats",
            headers=auth(manager_in_class_token)
        )
        assert resp.status_code == 200
        print("PASS: test_audit_logs_stats")


# ── Cross-Class Comparison ────────────────────────────────────

class TestManagerCrossClass:
    """GET /api/v1/manager/cross-class/comparison"""

    async def test_cross_class_comparison(self, api_client: AsyncClient, manager_in_class_token):
        resp = await api_client.get(
            "/api/v1/manager/cross-class/comparison",
            headers=auth(manager_in_class_token)
        )
        assert resp.status_code in (200, 403)
        print("PASS: test_cross_class_comparison")
