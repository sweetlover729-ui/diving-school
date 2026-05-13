"use client";

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Card, Form, Input, Button, message } from 'antd';
import { ArrowLeftOutlined } from '@ant-design/icons';
import { http } from '@/lib/http';

export default function InstructorChangePasswordPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [form] = Form.useForm();

  const handleSubmit = async (values: Record<string, unknown>) => {
    if (values.newPassword !== values.confirmPassword) {
      message.error('两次输入的密码不一致');
      return;
    }

    setLoading(true);
    try {
      await http.post('/auth/change-password', {
        old_password: values.oldPassword,
        new_password: values.newPassword,
      });
      message.success('密码修改成功，请重新登录');
      localStorage.removeItem('token');
      localStorage.removeItem('user');
      router.push('/login');
    } catch (e) {
      message.error(e.message || '修改失败');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ padding: 24, maxWidth: 500, margin: '0 auto' }}>
      <div style={{ marginBottom: 16 }}>
        <Button icon={<ArrowLeftOutlined />} onClick={() => router.push('/instructor/profile')}>返回</Button>
      </div>
      
      <h1 style={{ fontSize: 24, marginBottom: 24 }}>修改密码</h1>

      <Card>
        <Form form={form} layout="vertical" onFinish={handleSubmit}>
          <Form.Item name="oldPassword" label="原密码" rules={[{ required: true }]}>
            <Input.Password />
          </Form.Item>
          <Form.Item name="newPassword" label="新密码" rules={[{ required: true }, { min: 6 }]}>
            <Input.Password />
          </Form.Item>
          <Form.Item name="confirmPassword" label="确认新密码" rules={[{ required: true }]}>
            <Input.Password />
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit" loading={loading}>确认修改</Button>
          </Form.Item>
        </Form>
      </Card>
    </div>
  );
}