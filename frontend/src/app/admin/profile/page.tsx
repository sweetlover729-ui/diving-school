"use client";

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Card, Descriptions, Button, message, Form, Input, Space, Tag } from 'antd';
import { ArrowLeftOutlined, KeyOutlined, EditOutlined } from '@ant-design/icons';
import { http } from '@/lib/http';

export default function ProfilePage() {
  const router = useRouter();
  const [user, setUser] = useState<any>(null);
  const [editing, setEditing] = useState(false);
  const [loading, setLoading] = useState(false);
  const [form] = Form.useForm();

  useEffect(() => {
    const userData = localStorage.getItem('user');
    if (userData) {
      setUser(JSON.parse(userData));
      form.setFieldsValue(JSON.parse(userData));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleSave = async (values: Record<string, unknown>) => {
    setLoading(true);
    try {
      const res = await http.post('/auth/profile', {
        name: values.name,
        phone: values.phone,
      });
      // 更新本地存储
      const updated = { ...user, name: values.name, phone: values.phone };
      localStorage.setItem('user', JSON.stringify(updated));
      setUser(updated);
      setEditing(false);
      message.success('个人信息已更新');
    } catch (e) {
      message.error(e.message || '保存失败');
    } finally {
      setLoading(false);
    }
  };

  const roleLabel: Record<string, string> = {
    admin: '管理员',
    coach: '教练',
    student: '学员',
  };

  return (
    <div style={{ padding: 24 }}>
      <div style={{ marginBottom: 16 }}>
        <Button icon={<ArrowLeftOutlined />} onClick={() => router.push('/admin')}>返回</Button>
      </div>
      
      <h1 style={{ fontSize: 24, marginBottom: 24 }}>个人信息</h1>

      <Card
        style={{ maxWidth: 600 }}
        title="基本信息"
        extra={
          !editing && (
            <Button icon={<EditOutlined />} onClick={() => setEditing(true)}>
              编辑姓名
            </Button>
          )
        }
      >
        <Form form={form} layout="vertical" onFinish={handleSave}>
          <Form.Item label="姓名" name="name" rules={[{ required: true, message: '请输入姓名' }]}>
            <Input disabled={!editing} placeholder="请输入姓名" maxLength={50} />
          </Form.Item>

          <Form.Item label="身份证号" name="id_card">
            <Input disabled />
          </Form.Item>

          <Form.Item label="角色" name="role">
            <Input disabled />
          </Form.Item>

          <Form.Item label="电话" name="phone">
            <Input disabled={!editing} placeholder="选填" maxLength={20} />
          </Form.Item>

          {editing && (
            <Space>
              <Button type="primary" htmlType="submit" loading={loading}>保存</Button>
              <Button onClick={() => { setEditing(false); form.setFieldsValue(user); }}>取消</Button>
            </Space>
          )}
        </Form>

        {!editing && (
          <div style={{ marginTop: 24, borderTop: '1px solid #f0f0f0', paddingTop: 24 }}>
            <Button icon={<KeyOutlined />} onClick={() => router.push('/admin/profile/password')}>
              修改密码
            </Button>
          </div>
        )}
      </Card>
    </div>
  );
}
