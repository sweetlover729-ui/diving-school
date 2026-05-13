"""
test_auth.py — Authentication API Tests
Tests login/logout/refresh/change-password/me for all roles.
"""
import pytest
import bcrypt
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


# ── Login Tests ──────────────────────────────────────────────

class TestLogin:
    """Test POST /api/v1/auth/login"""

    async def test_login_admin_success(self, api_client: AsyncClient, admin_user):
        """Admin login with name+id_card+password succeeds."""
        resp = await api_client.post(
            "/api/v1/auth/login",
            json={
                "name": admin_user.name,
                "id_card": admin_user.id_card,
                "password": "test123",
                "role": "admin",
            }
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert data["success"] is True
        assert data["token"] is not None
        assert data["refresh_token"] is not None
        assert data["user"]["role"] == "admin"
        assert data["user"]["name"] == admin_user.name
        print("PASS: test_login_admin_success")

    async def test_login_instructor_success(self, api_client: AsyncClient, instructor_user):
        """Instructor login with name+id_card+password succeeds."""
        resp = await api_client.post(
            "/api/v1/auth/login",
            json={
                "name": instructor_user.name,
                "id_card": instructor_user.id_card,
                "password": "test123",
                "role": "instructor",
            }
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["token"] is not None
        assert data["user"]["role"] == "instructor"
        print("PASS: test_login_instructor_success")

    async def test_login_manager_success(self, api_client: AsyncClient, manager_user):
        """Manager login with name+phone succeeds."""
        resp = await api_client.post(
            "/api/v1/auth/login",
            json={
                "name": manager_user.name,
                "phone": manager_user.phone,
                "role": "manager",
            }
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["token"] is not None
        assert data["user"]["role"] == "manager"
        print("PASS: test_login_manager_success")

    async def test_login_student_without_active_class_fails(self, api_client: AsyncClient, student_user):
        """Student login fails if not in an active class."""
        resp = await api_client.post(
            "/api/v1/auth/login",
            json={
                "name": student_user.name,
                "id_card": student_user.id_card,
                "phone": student_user.phone,
                "role": "student",
            }
        )
        # Student must be in an active class
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is False
        assert "班级" in data.get("message", "") or "培训" in data.get("message", "")
        print("PASS: test_login_student_without_active_class_fails")

    async def test_login_wrong_password(self, api_client: AsyncClient, admin_user):
        """Login with wrong password fails."""
        resp = await api_client.post(
            "/api/v1/auth/login",
            json={
                "name": admin_user.name,
                "id_card": admin_user.id_card,
                "password": "WrongPassword1!",
                "role": "admin",
            }
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is False
        assert "密码错误" in data.get("message", "") or "不存在" in data.get("message", "")
        print("PASS: test_login_wrong_password")

    async def test_login_nonexistent_user(self, api_client: AsyncClient):
        """Login with non-existent credentials fails."""
        resp = await api_client.post(
            "/api/v1/auth/login",
            json={
                "name": "不存在的人_xxx",
                "id_card": "000000000000000000",
                "password": "SomePass1!",
                "role": "admin",
            }
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is False
        print("PASS: test_login_nonexistent_user")

    async def test_login_invalid_role(self, api_client: AsyncClient, admin_user):
        """Login with valid credentials but wrong role fails with validation error."""
        resp = await api_client.post(
            "/api/v1/auth/login",
            json={
                "name": admin_user.name,
                "id_card": admin_user.id_card,
                "password": "test123",
                "role": "superadmin",  # Invalid role - Pydantic validation fails
            }
        )
        # Pydantic rejects invalid role before checking credentials
        assert resp.status_code == 422, f"Expected 422, got {resp.status_code}: {resp.text}"
        print("PASS: test_login_invalid_role")

    async def test_login_missing_fields_admin(self, api_client: AsyncClient):
        """Admin login without required fields fails."""
        resp = await api_client.post(
            "/api/v1/auth/login",
            json={"name": "admin", "role": "admin"}
        )
        # Missing id_card and password
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is False
        print("PASS: test_login_missing_fields_admin")

    async def test_login_inactive_user(self, api_client: AsyncClient, db_session, admin_user):
        """Login with inactive user fails."""
        admin_user.is_active = False
        await db_session.flush()
        resp = await api_client.post(
            "/api/v1/auth/login",
            json={
                "name": admin_user.name,
                "id_card": admin_user.id_card,
                "password": "test123",
                "role": "admin",
            }
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is False
        print("PASS: test_login_inactive_user")


# ── Token Refresh Tests ──────────────────────────────────────

class TestTokenRefresh:
    """Test POST /api/v1/auth/refresh"""

    async def test_refresh_token_success(self, api_client: AsyncClient, admin_user):
        """Valid refresh token returns new access token."""
        # First login
        login_resp = await api_client.post(
            "/api/v1/auth/login",
            json={
                "name": admin_user.name,
                "id_card": admin_user.id_card,
                "password": "test123",
                "role": "admin",
            }
        )
        refresh_token = login_resp.json()["refresh_token"]

        # Refresh
        resp = await api_client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token}
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert "token" in data
        assert data.get("token_type") == "bearer"
        print("PASS: test_refresh_token_success")

    async def test_refresh_token_invalid(self, api_client: AsyncClient):
        """Invalid refresh token returns 401."""
        resp = await api_client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": "invalid.token.here"}
        )
        assert resp.status_code == 401
        print("PASS: test_refresh_token_invalid")

    async def test_refresh_token_wrong_type(self, api_client: AsyncClient, admin_token):
        """Using access token as refresh token fails."""
        resp = await api_client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": admin_token}
        )
        assert resp.status_code == 401
        print("PASS: test_refresh_token_wrong_type")


# ── Get Me Tests ─────────────────────────────────────────────

class TestGetMe:
    """Test GET /api/v1/auth/me"""

    async def test_me_admin(self, api_client: AsyncClient, admin_user, admin_token):
        """Admin can get their own profile."""
        resp = await api_client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert data["id"] == admin_user.id
        assert data["role"] == "admin"
        assert data["name"] == admin_user.name
        print("PASS: test_me_admin")

    async def test_me_instructor(self, api_client: AsyncClient, instructor_user, instructor_token):
        """Instructor can get their own profile."""
        resp = await api_client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {instructor_token}"}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == instructor_user.id
        assert data["role"] == "instructor"
        print("PASS: test_me_instructor")

    async def test_me_manager(self, api_client: AsyncClient, manager_user, manager_token):
        """Manager can get their own profile."""
        resp = await api_client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {manager_token}"}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == manager_user.id
        assert data["role"] == "manager"
        print("PASS: test_me_manager")

    async def test_me_student(self, api_client: AsyncClient, student_in_class_token, student_in_class):
        """Student can get their own profile."""
        resp = await api_client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {student_in_class_token}"}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == student_in_class.id
        assert data["role"] == "student"
        print("PASS: test_me_student")

    async def test_me_no_token(self, api_client: AsyncClient):
        """Request without token returns 401/403."""
        resp = await api_client.get("/api/v1/auth/me")
        assert resp.status_code in (401, 403)
        print("PASS: test_me_no_token")

    async def test_me_invalid_token(self, api_client: AsyncClient):
        """Request with invalid token returns 401."""
        resp = await api_client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer invalid.token.here"}
        )
        assert resp.status_code == 401
        print("PASS: test_me_invalid_token")


# ── Change Password Tests ─────────────────────────────────────

class TestChangePassword:
    """Test POST /api/v1/auth/change-password"""

    async def test_change_password_success(self, api_client: AsyncClient, admin_user, admin_token):
        """User can change their password."""
        new_password = "NewPass1!!"
        resp = await api_client.post(
            "/api/v1/auth/change-password",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "old_password": "test123",
                "new_password": new_password,
            }
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert data["success"] is True

        # Verify new password works
        login_resp = await api_client.post(
            "/api/v1/auth/login",
            json={
                "name": admin_user.name,
                "id_card": admin_user.id_card,
                "password": new_password,
                "role": "admin",
            }
        )
        assert login_resp.json()["success"] is True
        print("PASS: test_change_password_success")

    async def test_change_password_wrong_old(self, api_client: AsyncClient, admin_token):
        """Wrong old password fails."""
        resp = await api_client.post(
            "/api/v1/auth/change-password",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "old_password": "WrongOld1!",
                "new_password": "NewPass2!!",
            }
        )
        assert resp.status_code == 400
        data = resp.json()
        assert "原密码" in str(data.get("detail", ""))
        print("PASS: test_change_password_wrong_old")

    async def test_change_password_same_as_old(self, api_client: AsyncClient, admin_token):
        """New password same as old fails."""
        resp = await api_client.post(
            "/api/v1/auth/change-password",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "old_password": "Test1234!",
                "new_password": "Test1234!",
            }
        )
        assert resp.status_code == 400
        print("PASS: test_change_password_same_as_old")

    async def test_change_password_weak_password(self, api_client: AsyncClient, admin_token):
        """Weak new password fails (password policy)."""
        resp = await api_client.post(
            "/api/v1/auth/change-password",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "old_password": "test123",
                "new_password": "123",
            }
        )
        assert resp.status_code in (400, 422)
        print("PASS: test_change_password_weak_password")

    async def test_change_password_no_auth(self, api_client: AsyncClient):
        """Change password without auth fails."""
        resp = await api_client.post(
            "/api/v1/auth/change-password",
            json={
                "old_password": "Old1!",
                "new_password": "NewPass1!",
            }
        )
        assert resp.status_code in (401, 403)
        print("PASS: test_change_password_no_auth")


# ── Logout Tests ──────────────────────────────────────────────

class TestLogout:
    """Test POST /api/v1/auth/logout"""

    async def test_logout_success(self, api_client: AsyncClient, admin_token):
        """Logout succeeds (stateless JWT - client clears token)."""
        resp = await api_client.post(
            "/api/v1/auth/logout",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert data["success"] is True
        print("PASS: test_logout_success")

    async def test_logout_without_token(self, api_client: AsyncClient):
        """Logout without token still succeeds (stateless)."""
        resp = await api_client.post("/api/v1/auth/logout")
        assert resp.status_code == 200
        print("PASS: test_logout_without_token")
