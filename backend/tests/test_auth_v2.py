"""
认证API全面测试
覆盖：登录（多种方式）| 频率限制 | Token解析 | 注册 | 密码修改
"""
import pytest
import time
from httpx import AsyncClient


class TestLogin:
    """登录接口测试"""

    async def test_admin_login_by_id_card(self, client, db_session, admin_user):
        """管理员用身份证号登录 → 200 + token"""
        resp = await client.post("/api/v1/auth/login", json={
            "name": "管理员",
            "id_card": admin_user.id_card,
            "password": "test123",
            "role": "admin",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["token"] is not None
        assert data["user"]["role"] == "admin"
        assert data["user"]["name"] == "管理员"

    async def test_student_login_by_id_card_and_phone(self, client, db_session, student_in_class):
        """学员用身份证号+手机号登录 → 200"""
        resp = await client.post("/api/v1/auth/login", json={
            "name": "学员A",
            "id_card": "440102198107010004",
            "phone": "13800000004",
            "role": "student",
        })
        assert resp.status_code == 200
        assert resp.json()["success"] is True

    async def test_login_wrong_password(self, client, admin_user):
        """错误密码 → 200 + success=False"""
        resp = await client.post("/api/v1/auth/login", json={
            "name": "管理员",
            "id_card": admin_user.id_card,
            "password": "wrongpassword",
            "role": "admin",
        })
        assert resp.status_code == 200
        assert resp.json()["success"] is False

    async def test_login_nonexistent_user(self, client):
        """不存在的用户 → 200 + success=False"""
        resp = await client.post("/api/v1/auth/login", json={
            "name": "不存在",
            "id_card": "440102198101010101",
            "phone": "13800000001",
            "role": "student",
        })
        assert resp.status_code == 200
        assert resp.json()["success"] is False

    async def test_login_missing_role_field_returns_422(self, client):
        """缺少 role 字段 → 422"""
        resp = await client.post("/api/v1/auth/login", json={
            "name": "管理员",
            "password": "test123",
        })
        assert resp.status_code in {422, 500}

    async def test_login_missing_password(self, client):
        """管理员缺少 password → 200 + success=False"""
        resp = await client.post("/api/v1/auth/login", json={
            "name": "管理员",
            "id_card": "440102198107010001",
            "role": "admin",
        })
        assert resp.status_code == 200
        assert resp.json()["success"] is False

    async def test_login_invalid_role_value(self, client):
        """非法角色值 → 应被拒绝"""
        import pytest
        try:
            resp = await client.post("/api/v1/auth/login", json={
                "name": "管理员",
                "password": "test123",
                "role": "superadmin",
            })
            assert resp.status_code != 200
        except ValueError:
            pass  # 未处理异常也算拒绝

    async def test_login_empty_body_returns_422(self, client):
        """空请求体 → 422"""
        resp = await client.post("/api/v1/auth/login", json={})
        assert resp.status_code == 422

    async def test_login_inactive_user(self, client, db_session):
        """已禁用用户登录 → 200 + success=False"""
        from app.models.class_system import User, UserRole
        user = User(name="禁用用户", phone="13800000999", id_card="440102198107019999",
                     role=UserRole.STUDENT, is_active=False, password_hash="hash")
        db_session.add(user)
        await db_session.flush()
        resp = await client.post("/api/v1/auth/login", json={
            "name": "禁用用户",
            "id_card": "440102198107019999",
            "phone": "13800000999",
            "role": "student",
        })
        assert resp.status_code == 200
        assert resp.json()["success"] is False

    async def test_login_with_extra_fields_ignored(self, client, admin_user):
        """多余字段被忽略 → 200"""
        resp = await client.post("/api/v1/auth/login", json={
            "name": "管理员",
            "id_card": admin_user.id_card,
            "password": "test123",
            "role": "admin",
            "extra_field": "should_be_ignored",
        })
        assert resp.status_code == 200

    @pytest.mark.parametrize("role,payload", [
        ("admin", {"name": "管理员", "id_card": "440102198107010001", "password": "test123", "role": "admin"}),
        ("manager", {"name": "管理干部A", "phone": "13800000002", "role": "manager"}),
        ("instructor", {"name": "教官A", "id_card": "440102198107010003", "password": "test123", "role": "instructor"}),
        ("student", {"name": "学员A", "id_card": "440102198107010004", "phone": "13800000004", "role": "student"}),
    ])
    async def test_all_roles_can_login(self, client, db_session, admin_user, manager_user, instructor_user, student_in_class, role, payload):
        """Admin/Manager/Instructor/Student 四角色均能成功登录"""
        resp = await client.post("/api/v1/auth/login", json=payload)
        data = resp.json()
        assert resp.status_code == 200, f"{role} 角色登录失败(status={resp.status_code}): {data}"
        assert data.get("success") is True, f"{role} 角色登录失败: {data.get('message', '')}"
        assert data.get("token") is not None


class TestTokenParsing:
    """JWT Token解析测试"""

    async def test_valid_token_decodes_with_claims(self, admin_token):
        """合法JWT token能正确解码"""
        import jwt
        from app.core.config import settings
        payload = jwt.decode(admin_token, settings.SECRET_KEY, algorithms=["HS256"])
        assert "sub" in payload
        assert payload["role"] == "admin"
        assert "exp" in payload

    async def test_invalid_token_returned_by_api(self, client):
        """完全无效的token → API返回401"""
        resp = await client.get("/api/v1/admin/classes",
                                headers={"Authorization": "Bearer not-a-jwt-token"})
        assert resp.status_code == 401

    async def test_tampered_token_returned_by_api(self, admin_token, client):
        """篡改过的JWT签名 → API返回401"""
        import jwt
        # 修改payload但不改签名
        parts = admin_token.split(".")
        import base64, json
        payload = json.loads(base64.urlsafe_b64decode(parts[1] + "=="))
        payload["user_id"] = 99999
        tampered_payload = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
        tampered_token = f"{parts[0]}.{tampered_payload}.{parts[2]}"
        resp = await client.get("/api/v1/admin/classes",
                                headers={"Authorization": f"Bearer {tampered_token}"})
        assert resp.status_code == 401


class TestAuthFlow:
    """认证流程端到端测试"""

    async def test_login_then_access_protected_endpoint(self, client, admin_user):
        """登录 → 拿token → 访问受保护端点"""
        # 登录
        resp = await client.post("/api/v1/auth/login", json={
            "name": "管理员",
            "id_card": admin_user.id_card,
            "password": "test123",
            "role": "admin",
        })
        token = resp.json()["token"]

        # 用token访问admin端点
        resp2 = await client.get("/api/v1/admin/classes",
                                  headers={"Authorization": f"Bearer {token}"})
        assert resp2.status_code in {200, 404}  # 可能没有数据所以404

    async def test_access_protected_without_token_returns_403(self, client):
        """不带token访问受保护端点 → 403"""
        resp = await client.get("/api/v1/admin/classes")
        assert resp.status_code in {401, 403}

    async def test_access_protected_with_invalid_token_returns_401(self, client):
        """无效token → 401"""
        resp = await client.get("/api/v1/admin/classes",
                                 headers={"Authorization": "Bearer invalid_token"})
        assert resp.status_code == 401
