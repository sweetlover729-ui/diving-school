'use client';

import { useState, useEffect, useMemo } from 'react';
import { Table, Card, Button, Modal, Form, Input, InputNumber, Select, DatePicker, Space, Tag, message, Popconfirm } from 'antd';
import { ReloadOutlined, SearchOutlined, PlusOutlined, EditOutlined, DeleteOutlined } from '@ant-design/icons';
import { useRouter } from 'next/navigation';
import dayjs from 'dayjs';
import { classApi, instructorApi, peopleApi } from '@/lib/api';
import StatusWrapper from '@/components/StatusWrapper';
import { useCategory } from '@/components/CategoryProvider';
import type { ClassInfo, ClassCreate, Instructor, User } from '@/lib/types';

const STATUS_MAP: Record<string, { label: string; color: string }> = {
  ACTIVE: { label: '进行中', color: 'green' },
  INACTIVE: { label: '未开始', color: 'default' },
  ENDED: { label: '已结束', color: 'blue' },
  CANCELLED: { label: '已取消', color: 'red' },
};

export default function ClassesPage() {
  const router = useRouter();
  const { categories } = useCategory();
  const [data, setData] = useState<ClassInfo[]>([]);
  const [loading, setLoading] = useState(false);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState<string | undefined>();
  const [modalOpen, setModalOpen] = useState(false);
  const [editingRecord, setEditingRecord] = useState<ClassInfo | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [instructors, setInstructors] = useState<Instructor[]>([]);
  const [managers, setManagers] = useState<User[]>([]);
  const [form] = Form.useForm();

  useEffect(() => { fetchData(); loadPersonnel(); }, []);

  const fetchData = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await classApi.list();
      setData(Array.isArray(res) ? res : []);
    } catch (e: any) { setError(e.message || '加载失败'); }
    finally { setLoading(false); }
  };

  const loadPersonnel = async () => {
    try {
      const [inst, ppl] = await Promise.all([instructorApi.list(), peopleApi.list()]);
      setInstructors(Array.isArray(inst) ? inst : []);
      setManagers(Array.isArray(ppl) ? ppl.filter((p: User) => p.role === 'manager') : []);
    } catch {}
  };

  const openCreate = () => {
    setEditingRecord(null);
    form.resetFields();
    form.setFieldsValue({ category_id: categories[0]?.id });
    setModalOpen(true);
  };
  const openEdit = (record: ClassInfo) => {
    setEditingRecord(record);
    form.setFieldsValue({
      ...record,
      start_date: record.start_date ? dayjs(record.start_date) : undefined,
      end_date: record.end_date ? dayjs(record.end_date) : undefined,
    });
    setModalOpen(true);
  };

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      const payload: any = { ...values };
      if (payload.start_date) payload.start_date = payload.start_date.format('YYYY-MM-DD');
      if (payload.end_date) payload.end_date = payload.end_date.format('YYYY-MM-DD');
      setSubmitting(true);
      if (editingRecord) {
        await classApi.update(editingRecord.id, payload);
        message.success('更新成功');
      } else {
        await classApi.create(payload);
        message.success('创建成功');
      }
      setModalOpen(false);
      fetchData();
    } catch (e: any) { if (e.message) message.error(e.message); }
    finally { setSubmitting(false); }
  };

  const handleDelete = async (id: number) => {
    try { await classApi.remove(id); message.success('已删除'); fetchData(); }
    catch (e: any) { message.error(e.message || '删除失败'); }
  };

  let filtered = data;
  if (statusFilter) filtered = filtered.filter(c => c.status === statusFilter);
  if (search) filtered = filtered.filter(c =>
    (c.name || '').includes(search) || (c.location || '').includes(search) || (c.instructor_name || '').includes(search)
  );

  const statusStats = useMemo(() => {
    const counts: Record<string, number> = {};
    data.forEach(c => { counts[c.status] = (counts[c.status] || 0) + 1; });
    return counts;
  }, [data]);

  const columns = [
    { title: 'ID', dataIndex: 'id', width: 60 },
    { title: '班级名称', dataIndex: 'name', width: 180,
      render: (v: string, r: ClassInfo) => (
        <a onClick={() => router.push(`/admin/classes/${r.id}`)} style={{ fontWeight: 500, cursor: 'pointer' }}>{v}</a>
      )
    },
    { title: '状态', dataIndex: 'status', width: 90,
      render: (v: string) => { const m = STATUS_MAP[v] || { label: v, color: 'default' }; return <Tag color={m.color}>{m.label}</Tag>; }
    },
    { title: '起止日期', key: 'dates', width: 200,
      render: (_: any, r: ClassInfo) => `${r.start_date ? dayjs(r.start_date).format('YYYY-MM-DD') : '-'} ~ ${r.end_date ? dayjs(r.end_date).format('YYYY-MM-DD') : '-'}`
    },
    { title: '地点', dataIndex: 'location', width: 130, render: (v: string) => v || '-' },
    { title: '教练', dataIndex: 'instructor_name', width: 100, render: (v: string) => v || '-' },
    { title: '限额', dataIndex: 'max_students', width: 70, align: 'center' as const, render: (v: number) => v || '-' },
    { title: '创建时间', dataIndex: 'created_at', width: 170,
      render: (v: string) => v ? v.substring(0, 19).replace('T', ' ') : '-' },
    { title: '操作', key: 'action', width: 200, render: (_: any, r: ClassInfo) => (
      <Space size={0}>
        <Button type="link" size="small" onClick={() => router.push(`/admin/classes/${r.id}`)}>详情</Button>
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
          <Select allowClear placeholder="状态" style={{ width: 110 }}
            value={statusFilter} onChange={setStatusFilter}
            options={Object.entries(STATUS_MAP).map(([k, v]) => ({ value: k, label: v.label }))} />
          <Input placeholder="搜索名称/地点/教练" prefix={<SearchOutlined />} style={{ width: 200 }}
            value={search} onChange={e => setSearch(e.target.value)} allowClear />
          <Button icon={<ReloadOutlined />} onClick={fetchData}>刷新</Button>
          <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>新建班级</Button>
        </Space>
      }
    >
      <div style={{ marginBottom: 16, display: 'flex', gap: 12 }}>
        <span style={{ color: '#999' }}>总计 {data.length} 个班级</span>
        {Object.entries(statusStats).filter(([k]) => STATUS_MAP[k]).map(([k, v]) => (
          <Tag key={k} color={STATUS_MAP[k]?.color}>{STATUS_MAP[k]?.label}: {v}</Tag>
        ))}
      </div>
      <Table columns={columns} dataSource={filtered} rowKey="id" loading={loading}
        pagination={{ pageSize: 20, showSizeChanger: true, showTotal: t => `共 ${t} 个班级` }}
        size="middle" locale={{ emptyText: '暂无班级数据' }} />

      <Modal title={editingRecord ? '编辑班级' : '新建班级'} open={modalOpen}
        onOk={handleSubmit} onCancel={() => setModalOpen(false)}
        confirmLoading={submitting} destroyOnClose width={600}>
        <Form form={form} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item name="name" label="班级名称" rules={[{ required: true, message: '请输入' }]}>
            <Input placeholder="如: 2026第一期初级潜水班" maxLength={100} />
          </Form.Item>
          <Form.Item name="category_id" label="所属分类" rules={[{ required: true }]}>
            <Select options={categories.filter(c => c.is_active).map(c => ({ value: c.id, label: c.name }))} />
          </Form.Item>
          <Space size="large">
            <Form.Item name="start_date" label="开始日期">
              <DatePicker placeholder="选择日期" />
            </Form.Item>
            <Form.Item name="end_date" label="结束日期">
              <DatePicker placeholder="选择日期" />
            </Form.Item>
          </Space>
          <Form.Item name="location" label="培训地点">
            <Input placeholder="如: 三亚潜水基地" maxLength={200} />
          </Form.Item>
          <Space size="large">
            <Form.Item name="instructor_id" label="教练">
              <Select allowClear placeholder="选择教练" style={{ width: 160 }}
                options={instructors.filter(i => i.is_active).map(i => ({ value: i.id, label: i.name || i.username }))} />
            </Form.Item>
            <Form.Item name="manager_id" label="管理干部">
              <Select allowClear placeholder="选择干部" style={{ width: 160 }}
                options={managers.filter(m => m.is_active).map(m => ({ value: m.id, label: m.name || m.username }))} />
            </Form.Item>
            <Form.Item name="max_students" label="人数上限">
              <InputNumber min={1} max={999} />
            </Form.Item>
          </Space>
          <Form.Item name="description" label="描述">
            <Input.TextArea rows={2} maxLength={500} />
          </Form.Item>
        </Form>
      </Modal>
    </Card>
  
    </StatusWrapper>);
}