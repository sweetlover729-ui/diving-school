'use client';

import { useState, useEffect } from 'react';
import { Table, Card, Button, Modal, Form, Input, Select, Space, Tag, message, Popconfirm } from 'antd';
import { ReloadOutlined, SearchOutlined, PlusOutlined, EditOutlined, DeleteOutlined } from '@ant-design/icons';
import { useRouter } from 'next/navigation';
import { textbookApi } from '@/lib/api';
import StatusWrapper from '@/components/StatusWrapper';
import { useCategory } from '@/components/CategoryProvider';
import type { Textbook, TextbookCreate } from '@/lib/types';

export default function TextbooksPage() {
  const router = useRouter();
  const { categories } = useCategory();
  const [data, setData] = useState<Textbook[]>([]);
  const [loading, setLoading] = useState(false);
  const [search, setSearch] = useState('');
  const [catFilter, setCatFilter] = useState<number | undefined>();
  const [modalOpen, setModalOpen] = useState(false);
  const [editingRecord, setEditingRecord] = useState<Textbook | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [form] = Form.useForm();

  useEffect(() => { fetchData(); }, []);

  const fetchData = async () => {
    setLoading(true);
    try { const res = await textbookApi.list(); setData(Array.isArray(res) ? res : []); }
    catch (e: any) { setError(e.message || '加载失败'); }
    finally { setLoading(false); }
  };

  const openCreate = () => {
    setEditingRecord(null);
    form.resetFields();
    form.setFieldsValue({ is_active: true, file_type: 'pdf' });
    setModalOpen(true);
  };
  const openEdit = (record: Textbook) => {
    setEditingRecord(record);
    form.setFieldsValue(record);
    setModalOpen(true);
  };
  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      setSubmitting(true);
      if (editingRecord) { await textbookApi.update(editingRecord.id, values); message.success('更新成功'); }
      else { await textbookApi.create(values); message.success('创建成功'); }
      setModalOpen(false); fetchData();
    } catch (e: any) { if (e.message) message.error(e.message); }
    finally { setSubmitting(false); }
  };
  const handleDelete = async (id: number) => {
    try { await textbookApi.remove(id); message.success('已删除'); fetchData(); }
    catch (e: any) { message.error(e.message || '删除失败'); }
  };

  let filtered = data;
  if (catFilter) filtered = filtered.filter(t => t.category_id === catFilter);
  if (search) filtered = filtered.filter(t => (t.name || '').includes(search) || (t.description || '').includes(search));

  const columns = [
    { title: 'ID', dataIndex: 'id', width: 60 },
    { title: '封面', dataIndex: 'cover_image', width: 80,
      render: (v: string) => v ? <img src={v} alt="" style={{ width: 48, height: 64, objectFit: 'cover', borderRadius: 4 }} />
        : <div style={{ width: 48, height: 64, background: '#f5f5f5', borderRadius: 4, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#bbb' }}>无</div>
    },
    { title: '名称', dataIndex: 'name', width: 180, ellipsis: true,
      render: (v: string, r: Textbook) => <a onClick={() => router.push(`/admin/textbooks/${r.id}`)} style={{ cursor: 'pointer' }}>{v}</a>
    },
    { title: '描述', dataIndex: 'description', width: 200, ellipsis: true, render: (v: string) => v || '-' },
    { title: '分类', dataIndex: 'category_name', width: 100, render: (v: string) => v ? <Tag color="blue">{v}</Tag> : '-' },
    { title: '类型', dataIndex: 'file_type', width: 80, render: (v: string) => <Tag>{v?.toUpperCase() || '-'}</Tag> },
    { title: '章/页', key: 'stats', width: 100, render: (_: any, r: Textbook) => `${r.total_chapters || 0}章 ${r.total_pages || 0}页` },
    { title: '状态', dataIndex: 'is_active', width: 70, align: 'center' as const,
      render: (v: boolean) => <Tag color={v ? 'green' : 'default'}>{v ? '启用' : '停用'}</Tag>
    },
    { title: '创建时间', dataIndex: 'created_at', width: 170,
      render: (v: string) => v ? v.substring(0, 19).replace('T', ' ') : '-' },
    { title: '操作', key: 'action', width: 180, render: (_: any, r: Textbook) => (
      <Space size={0}>
        <Button type="link" size="small" onClick={() => router.push(`/admin/textbooks/${r.id}`)}>查看</Button>
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
          <Select allowClear placeholder="按分类筛选" style={{ width: 130 }}
            value={catFilter} onChange={setCatFilter}
            options={categories.filter(c => c.is_active).map(c => ({ value: c.id, label: c.name }))} />
          <Input placeholder="搜索教材名称" prefix={<SearchOutlined />} style={{ width: 180 }}
            value={search} onChange={e => setSearch(e.target.value)} allowClear />
          <Button icon={<ReloadOutlined />} onClick={fetchData}>刷新</Button>
          <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>添加教材</Button>
        </Space>
      }
    >
      <Table columns={columns} dataSource={filtered} rowKey="id" loading={loading}
        pagination={{ pageSize: 20, showSizeChanger: true, showTotal: t => `共 ${t} 本` }}
        size="middle" locale={{ emptyText: '暂无教材数据' }} />

      <Modal title={editingRecord ? '编辑教材' : '添加教材'} open={modalOpen}
        onOk={handleSubmit} onCancel={() => setModalOpen(false)}
        confirmLoading={submitting} destroyOnClose width={520}>
        <Form form={form} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item name="name" label="教材名称" rules={[{ required: true, message: '请输入' }]}>
            <Input placeholder="如: 公共安全潜水员教材" maxLength={200} />
          </Form.Item>
          <Form.Item name="category_id" label="所属分类" rules={[{ required: true }]}>
            <Select options={categories.filter(c => c.is_active).map(c => ({ value: c.id, label: c.name }))} />
          </Form.Item>
          <Form.Item name="description" label="描述">
            <Input.TextArea rows={2} maxLength={500} />
          </Form.Item>
          <Space size="large">
            <Form.Item name="file_type" label="文件类型">
              <Select options={[{ value: 'pdf', label: 'PDF' }, { value: 'docx', label: 'DOCX' }, { value: 'txt', label: 'TXT' }]} style={{ width: 120 }} />
            </Form.Item>
            <Form.Item name="is_active" label="启用" valuePropName="checked">
              <Select options={[{ value: true, label: '启用' }, { value: false, label: '停用' }]} style={{ width: 100 }} />
            </Form.Item>
          </Space>
        </Form>
      </Modal>
    </Card>
  
    </StatusWrapper>);
}