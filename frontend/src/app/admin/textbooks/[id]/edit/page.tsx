"use client";

import { useState, useEffect } from 'react';
import { useRouter, useParams } from 'next/navigation';
import { Card, Form, Input, Button, Space, message, Switch, Tag, Descriptions, Divider } from 'antd';
import { ArrowLeftOutlined, UploadOutlined } from '@ant-design/icons';
import { http } from '@/lib/http';

export default function EditTextbookPage() {
  const router = useRouter();
  const params = useParams();
  const textbookId = params.id as string;
  const [loading, setLoading] = useState(false);
  const [fetching, setFetching] = useState(true);
  const [form] = Form.useForm();
  const [textbook, setTextbook] = useState<any>(null);

  useEffect(() => {
    fetchTextbook();
  }, [textbookId]);

  const fetchTextbook = async () => {
    try {
      const data = await http.get(`/admin/textbooks/${textbookId}`);
      setTextbook(data);
      form.setFieldsValue({
        name: data.name,
        description: data.description,
        is_active: data.is_active,
      });
    } catch (e) {
      message.error('获取教材失败');
    } finally {
      setFetching(false);
    }
  };

  const handleSubmit = async (values: Record<string, unknown>) => {
    setLoading(true);
    try {
      await http.put(`/admin/textbooks/${textbookId}`, {
        name: values.name,
        description: values.description,
        is_active: values.is_active !== false,
      });
      message.success('教材更新成功');
      fetchTextbook();
    } catch (e) {
      message.error(e.message || '更新失败');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ padding: 24 }}>
      <div style={{ marginBottom: 16 }}>
        <Button icon={<ArrowLeftOutlined />} onClick={() => router.push('/admin/textbooks')}>
          返回教材列表
        </Button>
      </div>

      <h1 style={{ fontSize: 24, marginBottom: 24 }}>编辑教材 — {textbook?.name}</h1>

      <Card loading={fetching}>
        {/* 基本信息 */}
        <Form form={form} layout="vertical" onFinish={handleSubmit}>
          <Form.Item
            name="name"
            label="教材名称"
            rules={[{ required: true, message: '请输入教材名称' }]}
          >
            <Input placeholder="教材名称" />
          </Form.Item>

          <Form.Item name="description" label="描述">
            <Input.TextArea rows={3} placeholder="教材简介" />
          </Form.Item>

          <Form.Item name="is_active" label="启用状态" valuePropName="checked">
            <Switch checkedChildren="启用" unCheckedChildren="禁用" />
          </Form.Item>

          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit" loading={loading}>
                保存修改
              </Button>
              <Button onClick={() => router.push('/admin/textbooks')}>取消</Button>
            </Space>
          </Form.Item>
        </Form>

        {/* 统计信息 */}
        {textbook && (
          <>
            <Divider>教材统计</Divider>
            <Descriptions column={3} bordered size="small">
              <Descriptions.Item label="教材模式">
                {textbook.has_pdf ? (
                  <Tag color="blue">PDF 模式</Tag>
                ) : (
                  <Tag color="green">章节模式</Tag>
                )}
              </Descriptions.Item>
              <Descriptions.Item label="总页数">
                <strong>{textbook.total_pages || 0}</strong>
              </Descriptions.Item>
              <Descriptions.Item label="章节数">
                <strong>{textbook.total_chapters || 0}</strong>
              </Descriptions.Item>
              <Descriptions.Item label="状态">
                <Tag color={textbook.is_active ? 'green' : 'red'}>
                  {textbook.is_active ? '启用' : '禁用'}
                </Tag>
              </Descriptions.Item>
            </Descriptions>

            <Divider>快速操作</Divider>
            <Space wrap>
              <Button
                icon={<UploadOutlined />}
                onClick={() => router.push(`/admin/textbooks?upload=${textbookId}`)}
              >
                替换教材内容
              </Button>
              {(textbook.has_pdf || textbook.total_pages > 0 || textbook.total_chapters > 0) && (
                <Button
                  onClick={() => router.push(`/admin/textbooks/${textbookId}/chapters`)}
                >
                  章节管理
                </Button>
              )}
            </Space>
          </>
        )}
      </Card>
    </div>
  );
}
