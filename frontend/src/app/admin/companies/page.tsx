'use client';

import { useState, useEffect } from 'react';
import { Table, Card, Button, Modal, Form, Input, Space, message, Popconfirm } from 'antd';
import { ReloadOutlined, SearchOutlined, PlusOutlined, EditOutlined, DeleteOutlined } from '@ant-design/icons';
import { companyApi } from '@/lib/api';
import StatusWrapper from '@/components/StatusWrapper';
import type { Company, CompanyCreate } from '@/lib/types';

export default function CompaniesPage() {
  const [data, setData] = useState<Company[]>([]);
  const [loading, setLoading] = useState(false);
  const [search, setSearch] = useState('');
  const [modalOpen, setModalOpen] = useState(false);
  const [editingRecord, setEditingRecord] = useState<Company | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [form] = Form.useForm();

  useEffect(() => { fetchData(); }, []);

  const fetchData = async () => {
    setLoading(true);
    try { const res = await companyApi.list(); setData(Array.isArray(res) ? res : []); }
    catch (e: any) { setError(e.message || '加载失败'); }
    finally { setLoading(false); }
  };

  const openCreate = () => {
    setEditingRecord(null);
    form.resetFields();
    setModalOpen(true);
  };
  const openEdit = (record: Company) => {
    setEditingRecord(record);
    form.setFieldsValue(record);
    setModalOpen(true);
  };
  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      setSubmitting(true);
      if (editingRecord) { await companyApi.update(editingRecord.id, values); message.success('更新成功'); }
      else { await companyApi.create(values); message.success('创建成功'); }
      setModalOpen(false); fetchData();
    } catch (e: any) { if (e.message) message.error(e.message); }
    finally { setSubmitting(false); }
  };
  const handleDelete = async (id: number) => {
    try { await companyApi.remove(id); message.success('已删除'); fetchData(); }
    catch (e: any) { message.error(e.message || '删除失败'); }
  };

  const filtered = search
    ? data.filter(d => (d.name || '').includes(search) || (d.contact || '').includes(search))
    : data;

  const columns = [
    { title: 'ID', dataIndex: 'id', width: 60 },
    { title: '单位名称', dataIndex: 'name', width: 220 },
    { title: '地区', key: 'region', width: 160,
      render: (_: any, r: Company) => r.province && r.city ? `${r.province} ${r.city}` : r.province || '-' },
    { title: '联系人', dataIndex: 'contact', width: 120, render: (v: string) => v || '-' },
    { title: '创建时间', dataIndex: 'created_at', width: 170,
      render: (v: string) => v ? v.substring(0, 19).replace('T', ' ') : '-' },
    { title: '操作', key: 'action', width: 150, render: (_: any, r: Company) => (
      <Space size={0}>
        <Button type="link" size="small" icon={<EditOutlined />} onClick={() => openEdit(r)}>编辑</Button>
        <Popconfirm title="确认删除？" onConfirm={() => handleDelete(r.id)}>
          <Button type="link" size="small" danger icon={<DeleteOutlined />}>删除</Button>
        </Popconfirm>
      </Space>
    )},
  ];

  return (
    <StatusWrapper loading={loading} error={error} empty={data.length === 0} onRetry={fetchData}>
    <Card
      extra={
        <Space>
          <Input placeholder="搜索单位名称" prefix={<SearchOutlined />} style={{ width: 200 }}
            value={search} onChange={e => setSearch(e.target.value)} allowClear />
          <Button icon={<ReloadOutlined />} onClick={fetchData}>刷新</Button>
          <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>添加单位</Button>
        </Space>
      }
    >
      <Table columns={columns} dataSource={filtered} rowKey="id" loading={loading}
        pagination={{ pageSize: 20, showSizeChanger: true, showTotal: t => `共 ${t} 条` }}
        size="middle" locale={{ emptyText: '暂无单位数据' }} />

      <Modal title={editingRecord ? '编辑单位' : '添加单位'} open={modalOpen}
        onOk={handleSubmit} onCancel={() => setModalOpen(false)}
        confirmLoading={submitting} destroyOnClose width={480}>
        <Form form={form} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item name="name" label="单位名称" rules={[{ required: true }]}>
            <Input placeholder="如: 三亚市消防救援支队" maxLength={200} />
          </Form.Item>
          <Space size="large">
            <Form.Item name="province" label="省份">
              <Input placeholder="如: 海南" style={{ width: 140 }} />
            </Form.Item>
            <Form.Item name="city" label="城市">
              <Input placeholder="如: 三亚" style={{ width: 140 }} />
            </Form.Item>
          </Space>
          <Form.Item name="contact" label="联系人">
            <Input placeholder="可选联系人" maxLength={50} />
          </Form.Item>
        </Form>
      </Modal>
    </Card>
  
    </StatusWrapper>);
}