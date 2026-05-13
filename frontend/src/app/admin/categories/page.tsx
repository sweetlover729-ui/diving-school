'use client';

import { useState, useEffect, useCallback } from 'react';
import { Table, Button, Modal, Form, Input, InputNumber, Switch, Space, Popconfirm, Tag, message, Card } from 'antd';
import { PlusOutlined, EditOutlined, DeleteOutlined, ReloadOutlined } from '@ant-design/icons';
import { categoryApi } from '@/lib/api';
import { useCategory } from '@/components/CategoryProvider';
import type { Category } from '@/lib/types';

export default function CategoriesPage() {
  const { categories, loading, refreshCategories } = useCategory();
  const [modalOpen, setModalOpen] = useState(false);
  const [editingRecord, setEditingRecord] = useState<Category | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [form] = Form.useForm();

  const openCreate = () => {
    setEditingRecord(null);
    form.resetFields();
    form.setFieldsValue({ is_active: true, sort_order: 0 });
    setModalOpen(true);
  };

  const openEdit = (record: Category) => {
    setEditingRecord(record);
    form.setFieldsValue(record);
    setModalOpen(true);
  };

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      setSubmitting(true);

      if (editingRecord) {
        await categoryApi.update(editingRecord.id, values);
        message.success('更新成功');
      } else {
        await categoryApi.create(values);
        message.success('创建成功');
      }

      setModalOpen(false);
      await refreshCategories();
    } catch (e: any) {
      if (e.message) message.error(e.message);
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (id: number) => {
    try {
      await categoryApi.remove(id);
      message.success('已删除');
      await refreshCategories();
    } catch (e: any) {
      message.error(e.message || '删除失败');
    }
  };

  const columns = [
    { title: 'ID', dataIndex: 'id', width: 60 },
    { title: '编码', dataIndex: 'code', width: 100 },
    { title: '名称', dataIndex: 'name', width: 140 },
    {
      title: '描述', dataIndex: 'description', ellipsis: true,
      render: (v: string) => v || '-'
    },
    { title: '排序', dataIndex: 'sort_order', width: 70, align: 'center' as const },
    {
      title: '状态', dataIndex: 'is_active', width: 80, align: 'center' as const,
      render: (v: boolean) => <Tag color={v ? 'green' : 'default'}>{v ? '启用' : '停用'}</Tag>
    },
    {
      title: '创建时间', dataIndex: 'created_at', width: 170,
      render: (v: string) => v ? v.substring(0, 19).replace('T', ' ') : '-'
    },
    {
      title: '操作', key: 'action', width: 150,
      render: (_: any, record: Category) => (
        <Space>
          <Button type="link" size="small" icon={<EditOutlined />} onClick={() => openEdit(record)}>
            编辑
          </Button>
          <Popconfirm title="确认删除？" onConfirm={() => handleDelete(record.id)} okText="确认" cancelText="取消">
            <Button type="link" size="small" danger icon={<DeleteOutlined />}>删除</Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <Card
      extra={
        <Space>
          <Button icon={<ReloadOutlined />} onClick={refreshCategories}>刷新</Button>
          <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>新建分类</Button>
        </Space>
      }
    >
      <Table
        columns={columns}
        dataSource={categories}
        rowKey="id"
        loading={loading}
        pagination={false}
        size="middle"
        locale={{ emptyText: '暂无分类数据' }}
      />

      <Modal
        title={editingRecord ? '编辑分类' : '新建分类'}
        open={modalOpen}
        onOk={handleSubmit}
        onCancel={() => setModalOpen(false)}
        confirmLoading={submitting}
        destroyOnClose
        width={520}
      >
        <Form form={form} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item name="code" label="编码" rules={[{ required: true, message: '请输入编码' }]}>
            <Input placeholder="如: diving, fire" maxLength={50} />
          </Form.Item>
          <Form.Item name="name" label="名称" rules={[{ required: true, message: '请输入名称' }]}>
            <Input placeholder="如: 潜水培训" maxLength={100} />
          </Form.Item>
          <Form.Item name="description" label="描述">
            <Input.TextArea rows={2} placeholder="可选描述" maxLength={500} />
          </Form.Item>
          <Space size="large">
            <Form.Item name="sort_order" label="排序">
              <InputNumber min={0} max={9999} />
            </Form.Item>
            <Form.Item name="is_active" label="启用" valuePropName="checked">
              <Switch />
            </Form.Item>
          </Space>
        </Form>
      </Modal>
    </Card>
  );
}