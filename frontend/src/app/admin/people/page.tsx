'use client';

import { useState, useEffect } from 'react';
import { Table, Card, Button, Modal, Form, Input, Select, Space, Tag, message, Popconfirm } from 'antd';
import { ReloadOutlined, SearchOutlined, PlusOutlined, EditOutlined, DeleteOutlined } from '@ant-design/icons';
import { peopleApi, companyApi } from '@/lib/api';
import StatusWrapper from '@/components/StatusWrapper';
import type { Person, PersonCreate, Company } from '@/lib/types';

const ROLE_OPTIONS = [
  { value: 'admin', label: '管理员', color: 'red' },
  { value: 'instructor', label: '教练', color: 'blue' },
  { value: 'manager', label: '管理干部', color: 'orange' },
  { value: 'student', label: '学员', color: 'green' },
];

const roleMap: Record<string, { label: string; color: string }> = Object.fromEntries(
  ROLE_OPTIONS.map(o => [o.value, { label: o.label, color: o.color }])
);

export default function PeoplePage() {
  const [data, setData] = useState<Person[]>([]);
  const [loading, setLoading] = useState(false);
  const [search, setSearch] = useState('');
  const [modalOpen, setModalOpen] = useState(false);
  const [editingRecord, setEditingRecord] = useState<Person | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [companies, setCompanies] = useState<Company[]>([]);
  const [form] = Form.useForm();

  useEffect(() => { fetchData(); loadCompanies(); }, []);

  const fetchData = async () => {
    setLoading(true);
    try { const res = await peopleApi.list(); setData(Array.isArray(res) ? res : []); }
    catch (e: any) { setError(e.message || '加载失败'); }
    finally { setLoading(false); }
  };

  const loadCompanies = async () => {
    try { const res = await companyApi.list(); setCompanies(Array.isArray(res) ? res : []); }
    catch {}
  };

  const openCreate = () => {
    setEditingRecord(null);
    form.resetFields();
    form.setFieldsValue({ is_active: true, role: 'student' });
    setModalOpen(true);
  };
  const openEdit = (record: Person) => {
    setEditingRecord(record);
    form.setFieldsValue(record);
    setModalOpen(true);
  };
  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      setSubmitting(true);
      if (editingRecord) {
        const { password, ...rest } = values;
        await peopleApi.update(editingRecord.id, rest);
        message.success('更新成功');
      } else {
        await peopleApi.create(values);
        message.success('创建成功');
      }
      setModalOpen(false); fetchData();
    } catch (e: any) { if (e.message) message.error(e.message); }
    finally { setSubmitting(false); }
  };
  const handleDelete = async (id: number) => {
    try { await peopleApi.remove(id); message.success('已删除'); fetchData(); }
    catch (e: any) { message.error(e.message || '删除失败'); }
  };

  const filtered = search
    ? data.filter(d => (d.name || '').includes(search) || (d.phone || '').includes(search) || (d.id_card || '').includes(search))
    : data;

  const columns = [
    { title: 'ID', dataIndex: 'id', width: 60 },
    { title: '姓名', dataIndex: 'name', width: 120 },
    { title: '手机号', dataIndex: 'phone', width: 130, render: (v: string) => v || '-' },
    { title: '角色', dataIndex: 'role', width: 100,
      render: (v: string) => { const m = roleMap[v] || { label: v, color: 'default' }; return <Tag color={m.color}>{m.label}</Tag>; }
    },
    { title: '地区', key: 'region', width: 140,
      render: (_: any, r: Person) => r.province && r.city ? `${r.province} ${r.city}` : r.province || '-' },
    { title: '单位', dataIndex: 'company_name', width: 150, render: (v: string) => v || '-' },
    { title: '状态', dataIndex: 'is_active', width: 80, align: 'center' as const,
      render: (v: boolean) => <Tag color={v ? 'green' : 'default'}>{v ? '正常' : '停用'}</Tag> },
    { title: '创建时间', dataIndex: 'created_at', width: 170,
      render: (v: string) => v ? v.substring(0, 19).replace('T', ' ') : '-' },
    { title: '操作', key: 'action', width: 150, render: (_: any, r: Person) => (
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
          <Input placeholder="搜索用户名/手机/身份证" prefix={<SearchOutlined />} style={{ width: 220 }}
            value={search} onChange={e => setSearch(e.target.value)} allowClear />
          <Button icon={<ReloadOutlined />} onClick={fetchData}>刷新</Button>
          <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>添加人员</Button>
        </Space>
      }
    >
      <Table columns={columns} dataSource={filtered} rowKey="id" loading={loading}
        pagination={{ pageSize: 20, showSizeChanger: true, showTotal: t => `共 ${t} 条` }}
        size="middle" locale={{ emptyText: '暂无人员数据' }} />

      <Modal title={editingRecord ? '编辑人员' : '添加人员'} open={modalOpen}
        onOk={handleSubmit} onCancel={() => setModalOpen(false)}
        confirmLoading={submitting} destroyOnClose width={520}>
        <Form form={form} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item name="name" label="姓名" rules={[{ required: true }]}>
            <Input placeholder="姓名" maxLength={50} />
          </Form.Item>
          <Form.Item name="phone" label="手机号" rules={[{ required: true }]}>
            <Input placeholder="如: 13800138000" maxLength={20} />
          </Form.Item>
          {!editingRecord && (
            <Form.Item name="password" label="密码" rules={[{ required: true, min: 6 }]}>
              <Input.Password placeholder="至少6位" />
            </Form.Item>
          )}
          <Form.Item name="role" label="角色" rules={[{ required: true }]}>
            <Select options={ROLE_OPTIONS} />
          </Form.Item>
          <Form.Item name="id_card" label="身份证号">
            <Input placeholder="可选" maxLength={18} />
          </Form.Item>
          <Space size="large">
            <Form.Item name="province" label="省份">
              <Input placeholder="如: 广东" style={{ width: 120 }} />
            </Form.Item>
            <Form.Item name="city" label="城市">
              <Input placeholder="如: 广州" style={{ width: 120 }} />
            </Form.Item>
          </Space>
          <Form.Item name="company_id" label="所属单位">
            <Select allowClear placeholder="选择单位" options={companies.map(c => ({ value: c.id, label: c.name }))} />
          </Form.Item>
          <Form.Item name="is_active" label="状态">
            <Select options={[{ value: true, label: '启用' }, { value: false, label: '停用' }]} style={{ width: 100 }} />
          </Form.Item>
        </Form>
      </Modal>
    </Card>
  
    </StatusWrapper>);
}