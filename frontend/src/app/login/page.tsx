"use client";

import { useState, useEffect, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Form, Input, Button, message, Card } from "antd";
import { UserOutlined, LockOutlined, PhoneOutlined } from "@ant-design/icons";
import { http } from "@/lib/http";
import { getCourseShortTitle } from "@/lib/courseConfig";

function LoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const course = searchParams.get('course');
  const [loading, setLoading] = useState(false);
  const [loginType, setLoginType] = useState<
    "admin" | "instructor" | "manager" | "student"
  >("student");

  useEffect(() => {
    const token = localStorage.getItem("token");
    const user = localStorage.getItem("user");

    // 清理旧格式 token（JWT token 以 eyJ 开头，旧 base64 token 不符合）
    if (token && !token.startsWith("eyJ")) {
      localStorage.removeItem("token");
      localStorage.removeItem("user");
      localStorage.removeItem("class");
      return;
    }

    if (token && user) {
      try {
        const userData = JSON.parse(user);
        if (userData.role === "admin") router.push("/admin");
        else if (userData.role === "instructor") router.push("/instructor");
        else if (userData.role === "manager") router.push("/manager");
        else router.push("/student");
      } catch {
        // user JSON 损坏，清理
        localStorage.removeItem("token");
        localStorage.removeItem("user");
        localStorage.removeItem("class");
      }
    }
  }, [router]);

  const onFinish = async (values: Record<string, unknown>) => {
    setLoading(true);
    try {
      const payload: Record<string, unknown> = { role: loginType };

      if (loginType === "admin") {
        payload.name = values.name;
        payload.id_card = values.id_card;
        payload.password = values.password;
      } else if (loginType === "instructor") {
        payload.name = values.name;
        payload.id_card = values.id_card;
        payload.password = values.password;
      } else if (loginType === "manager") {
        payload.name = values.name;
        payload.phone = values.phone;
      } else {
        // student
        payload.name = values.name;
        payload.id_card = values.id_card;
        payload.phone = values.phone;
      }

      const res = await http.post("/auth/login", payload);

      if (res.success) {
        localStorage.setItem("token", res.token);
        localStorage.setItem("user", JSON.stringify(res.user));
        if (res.cls) localStorage.setItem("class", JSON.stringify(res.cls));
        if (course) localStorage.setItem("course", course);
        message.success("登录成功");

        if (res.user.role === "admin") router.push("/admin");
        else if (res.user.role === "instructor") router.push("/instructor");
        else if (res.user.role === "manager") router.push("/manager");
        else router.push("/student");
      } else {
        message.error(res.message || "登录失败");
      }
    } catch (e) {
      message.error(e.message || "登录失败");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      style={{
        minHeight: "100vh",
        background: "#f0f2f5",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        position: "relative",
        zIndex: 1,
      }}
    >
      <Card
        title={
          <div style={{ textAlign: "center" }}>
            <h2 style={{ margin: 0, fontSize: 18, fontWeight: "bold" }}>应急救援与公共安全</h2>
            <h3 style={{ margin: "4px 0 0 0", fontSize: 14, color: "#666", fontWeight: "normal" }}>{getCourseShortTitle(course)}</h3>
          </div>
        }
        style={{ width: 400 }}
      >
        {/* 角色选择 */}
        <div style={{ marginBottom: 16 }}>
          <label style={{ display: "block", marginBottom: 6, fontSize: 14, color: "#000000a6" }}>
            登录身份
          </label>
          <select
            value={loginType}
            onChange={(e) => setLoginType(e.target.value as any)}
            style={{
              width: "100%",
              padding: "8px 12px",
              fontSize: 16,
              border: "1px solid #d9d9d9",
              borderRadius: 6,
              background: "#fff",
              cursor: "pointer",
            }}
          >
            <option value="student">学员登录</option>
            <option value="instructor">教练登录</option>
            <option value="manager">管理干部登录</option>
            <option value="admin">管理员登录</option>
          </select>
        </div>

        <Form layout="vertical" onFinish={onFinish}>
          {/* ===== 学员 ===== */}
          {loginType === "student" && (
            <>
              <Form.Item name="name" label="姓名" rules={[{ required: true }]}>
                <Input prefix={<UserOutlined />} placeholder="请输入姓名" />
              </Form.Item>
              <Form.Item name="id_card" label="身份证号" rules={[{ required: true }]}>
                <Input prefix={<UserOutlined />} placeholder="请输入身份证号" />
              </Form.Item>
              <Form.Item name="phone" label="手机号" rules={[{ required: true }]}>
                <Input prefix={<PhoneOutlined />} placeholder="请输入手机号" />
              </Form.Item>
            </>
          )}

          {/* ===== 教练 ===== */}
          {loginType === "instructor" && (
            <>
              <Form.Item name="name" label="姓名" rules={[{ required: true }]}>
                <Input prefix={<UserOutlined />} placeholder="请输入姓名" />
              </Form.Item>
              <Form.Item name="id_card" label="身份证号" rules={[{ required: true }]}>
                <Input prefix={<UserOutlined />} placeholder="请输入身份证号" />
              </Form.Item>
              <Form.Item name="password" label="密码" rules={[{ required: true }]}>
                <Input.Password prefix={<LockOutlined />} placeholder="请输入密码" />
              </Form.Item>
            </>
          )}

          {/* ===== 管理干部 ===== */}
          {loginType === "manager" && (
            <>
              <Form.Item name="name" label="姓名" rules={[{ required: true }]}>
                <Input prefix={<UserOutlined />} placeholder="请输入姓名" />
              </Form.Item>
              <Form.Item name="phone" label="手机号" rules={[{ required: true }]}>
                <Input prefix={<PhoneOutlined />} placeholder="请输入手机号" />
              </Form.Item>
            </>
          )}

          {/* ===== 管理员 ===== */}
          {loginType === "admin" && (
            <>
              <Form.Item name="name" label="姓名" rules={[{ required: true }]}>
                <Input prefix={<UserOutlined />} placeholder="请输入姓名" />
              </Form.Item>
              <Form.Item name="id_card" label="身份证号" rules={[{ required: true }]}>
                <Input prefix={<UserOutlined />} placeholder="请输入身份证号" />
              </Form.Item>
              <Form.Item name="password" label="密码" rules={[{ required: true }]}>
                <Input.Password prefix={<LockOutlined />} placeholder="请输入密码" />
              </Form.Item>
            </>
          )}

          <Form.Item>
            <Button type="primary" htmlType="submit" loading={loading} block>
              登录
            </Button>
          </Form.Item>
        </Form>
      </Card>
    </div>
  );
}

export default function LoginPage() {
  return (
    <Suspense fallback={
      <div style={{ minHeight: '100vh', display: 'flex', justifyContent: 'center', alignItems: 'center', background: '#f0f2f5' }}>
        <Card style={{ width: 400, textAlign: 'center' }}>加载中...</Card>
      </div>
    }>
      <LoginForm />
    </Suspense>
  );
}
