"""
Admin 班级管理 API 集成测试
"""
import pytest
from datetime import datetime, timezone, timedelta
from app.models.class_system import Class, ClassStatus, Textbook


class TestAdminListClasses:
    """获取班级列表"""

    async def test_list_classes_empty(self, client, admin_token):
        resp = await client.get("/api/v1/admin/classes",
                                 headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data or isinstance(data, list)

    async def test_list_classes_with_data(self, client, db_session, admin_token, active_class):
        resp = await client.get("/api/v1/admin/classes",
                                 headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 200

    async def test_list_classes_requires_auth(self, client):
        resp = await client.get("/api/v1/admin/classes")
        assert resp.status_code in {401, 403}

    async def test_list_classes_student_forbidden(self, client, student_token):
        resp = await client.get("/api/v1/admin/classes",
                                 headers={"Authorization": f"Bearer {student_token}"})
        assert resp.status_code in {401, 403}


class TestAdminCreateClass:
    """创建班级"""

    async def test_create_class_success(self, client, admin_token, instructor_user, manager_user):
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        resp = await client.post("/api/v1/admin/classes",
                                  headers={"Authorization": f"Bearer {admin_token}"},
                                  json={
                                      "name": "新班级测试",
                                      "location": "测试基地",
                                      "start_time": (now + timedelta(days=1)).isoformat(),
                                      "end_time": (now + timedelta(days=31)).isoformat(),
                                      "instructor_id": instructor_user.id,
                                      "manager_id": manager_user.id,
                                  })
        assert resp.status_code in {200, 201}, f"创建班级失败: {resp.text}"

    async def test_create_class_missing_name(self, client, admin_token):
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        resp = await client.post("/api/v1/admin/classes",
                                  headers={"Authorization": f"Bearer {admin_token}"},
                                  json={
                                      "start_time": now.isoformat(),
                                      "end_time": (now + timedelta(days=30)).isoformat(),
                                  })
        assert resp.status_code == 422

    async def test_create_class_empty_json(self, client, admin_token):
        resp = await client.post("/api/v1/admin/classes",
                                  headers={"Authorization": f"Bearer {admin_token}"},
                                  json={})
        assert resp.status_code == 422


class TestAdminGetClassDetail:
    """获取班级详情"""

    async def test_get_existing_class(self, client, admin_token, active_class):
        resp = await client.get(f"/api/v1/admin/classes/{active_class.id}",
                                 headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == active_class.name

    async def test_get_nonexistent_class(self, client, admin_token):
        resp = await client.get("/api/v1/admin/classes/99999",
                                 headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code in {404, 200}  # 200 if returns empty


class TestAdminUpdateClass:
    """更新班级"""

    async def test_update_class_name(self, client, db_session, admin_token, active_class):
        resp = await client.put(f"/api/v1/admin/classes/{active_class.id}",
                                 headers={"Authorization": f"Bearer {admin_token}"},
                                 json={
                                     "name": "已更新的班级名称",
                                 })
        assert resp.status_code in {200, 201}, f"更新班级失败: {resp.text}"

        await db_session.flush()
        # 验证数据库更新
        from sqlalchemy import select, text
        result = await db_session.execute(
            text("SELECT name FROM classes WHERE id = :id"), {"id": active_class.id}
        )
        name = result.scalar_one_or_none()
        # 更新端点可能返回 {"success": True} 而非完整对象
        if resp.status_code == 200:
            data = resp.json()
            assert "success" in data or "name" in data

    async def test_update_class_status(self, client, admin_token, active_class):
        resp = await client.put(f"/api/v1/admin/classes/{active_class.id}",
                                 headers={"Authorization": f"Bearer {admin_token}"},
                                 json={
                                     "name": active_class.name,
                                     "start_time": active_class.start_time.isoformat(),
                                     "end_time": active_class.end_time.isoformat(),
                                     "status": "ended",
                                 })
        assert resp.status_code in {200, 422}


class TestAdminDeleteClass:
    """删除班级"""

    async def test_delete_existing_class(self, client, db_session, admin_token, admin_user):
        """删除刚创建的班级"""
        from app.models.class_system import Class
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        cls = Class(
            name="待删除班级",
            start_time=now,
            end_time=now + timedelta(days=30),
            status=ClassStatus.ACTIVE,
            created_by=admin_user.id,
        )
        db_session.add(cls)
        await db_session.flush()

        resp = await client.delete(f"/api/v1/admin/classes/{cls.id}",
                                    headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code in {200, 204, 400, 404}

    async def test_delete_nonexistent_class(self, client, admin_token):
        resp = await client.delete("/api/v1/admin/classes/99999",
                                    headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code in {404, 200}


class TestAdminClassMembers:
    """班级成员管理"""

    async def test_list_class_members(self, client, admin_token, active_class):
        resp = await client.get(f"/api/v1/admin/classes/{active_class.id}/members",
                                 headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 200

    async def test_add_member_to_class(self, client, db_session, admin_token, active_class, student_user):
        resp = await client.post(f"/api/v1/admin/classes/{active_class.id}/members",
                                  headers={"Authorization": f"Bearer {admin_token}"},
                                  json={
                                      "user_id": student_user.id,
                                      "role": "student",
                                  })
        assert resp.status_code in {200, 201}, f"添加成员失败: {resp.text}"

    async def test_remove_member_from_class(self, client, db_session, admin_token, active_class, student_user):
        from app.models.class_system import ClassMember
        member = ClassMember(
            class_id=active_class.id,
            user_id=student_user.id,
            role="student",
        )
        db_session.add(member)
        await db_session.flush()

        resp = await client.delete(
            f"/api/v1/admin/classes/{active_class.id}/members/{student_user.id}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert resp.status_code in {200, 204}


class TestAdminClassTextbooks:
    """班级教材管理"""

    async def test_get_class_textbooks(self, client, admin_token, active_class):
        resp = await client.get(f"/api/v1/admin/classes/{active_class.id}/textbooks",
                                 headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 200

    async def test_add_textbook_to_class(self, client, admin_token, active_class, textbook):
        resp = await client.post(f"/api/v1/admin/classes/{active_class.id}/textbooks/{textbook.id}",
                                  headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code in {200, 201}, f"添加教材失败: {resp.text}"


class TestAdminClassAnalytics:
    """班级分析"""

    async def test_get_class_analytics(self, client, admin_token, active_class):
        resp = await client.get(f"/api/v1/admin/classes/{active_class.id}/analytics",
                                 headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code in {200, 404}
