'use client';

import { useState, useEffect } from 'react';
import { Table, Card, Button, Modal, Form, Input, Select, Space, Tag, message, Popconfirm } from 'antd';
import { ReloadOutlined, SearchOutlined, PlusOutlined, EditOutlined, DeleteOutlined, MinusCircleOutlined } from '@ant-design/icons';
import { questionApi } from '@/lib/api';
import StatusWrapper from '@/components/StatusWrapper';
import type { Question, QuestionCreate } from '@/lib/types';

const TYPE_OPTIONS = [
  { value: 'single', label: '单选题', color: 'blue' },
  { value: 'multiple', label: '多选题', color: 'purple' },
  { value: 'judge', label: '判断题', color: 'orange' },
];

const typeMap: Record<string, { label: string; color: string }> = Object.fromEntries(
  TYPE_OPTIONS.map(o => [o.value, { label: o.label, color: o.color }])
);

const DIFFICULTY_OPTIONS = [
  { value: 1, label: '简单' },
  { value: 2, label: '中等' },
  { value: 3, label: '困难' },
];

export default function QuestionsPage() {
  const [data, setData] = useState<Question[]>([]);
  const [loading, setLoading] = useState(false);
  const [search, setSearch] = useState('');
  const [typeFilter, setTypeFilter] = useState<string | undefined>();
  const [modalOpen, setModalOpen] = useState(false);
  const [editingRecord, setEditingRecord] = useState<Question | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [questionType, setQuestionType] = useState<string>('single');
  const [form] = Form.useForm();

  useEffect(() => { fetchData(); }, []);

  const fetchData = async () => {
    setLoading(true);
    try { const res = await questionApi.list(); setData(Array.isArray(res) ? res : []); }
    catch (e: any) { setError(e.message || '加载失败'); }
    finally { setLoading(false); }
  };

  const openCreate = () => {
    setEditingRecord(null);
    setQuestionType('single');
    form.resetFields();
    form.setFieldsValue({ question_type: 'single', options: [''], difficulty: 2 });
    setModalOpen(true);
  };

  const openEdit = (record: Question) => {
    setEditingRecord(record);
    setQuestionType(record.question_type);
    form.setFieldsValue({
      ...record,
      options: record.options && record.options.length > 0 ? record.options : [''],
      answer: record.answer || [],
    });
    setModalOpen(true);
  };

  const handleTypeChange = (value: string) => {
    setQuestionType(value);
    if (value === 'judge') {
      form.setFieldsValue({ options: ['正确', '错误'], answer: [] });
    } else {
      const currentOpts = form.getFieldValue('options');
      if (!currentOpts || currentOpts.length === 0) {
        form.setFieldsValue({ options: [''], answer: [] });
      }
    }
  };

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      const payload: any = { ...values };
      // 判断题自动设置选项
      if (payload.question_type === 'judge') {
        payload.options = ['正确', '错误'];
      }
      // 过滤空选项
      if (payload.options) {
        payload.options = payload.options.filter((o: string) => o.trim() !== '');
      }
      // 确保 answer 是数组
      if (!Array.isArray(payload.answer)) {
        payload.answer = payload.answer ? payload.answer.split(',').map((s: string) => s.trim()).filter(Boolean) : [];
      }
      setSubmitting(true);
      if (editingRecord) {
        await questionApi.update(editingRecord.id, payload);
        message.success('更新成功');
      } else {
        await questionApi.create(payload);
        message.success('创建成功');
      }
      setModalOpen(false); fetchData();
    } catch (e: any) { if (e.message) message.error(e.message); }
    finally { setSubmitting(false); }
  };

  const handleDelete = async (id: number) => {
    try { await questionApi.remove(id); message.success('已删除'); fetchData(); }
    catch (e: any) { message.error(e.message || '删除失败'); }
  };

  let filtered = data;
  if (typeFilter) filtered = filtered.filter(q => q.question_type === typeFilter);
  if (search) filtered = filtered.filter(q => (q.content || '').includes(search));

  const columns = [
    { title: 'ID', dataIndex: 'id', width: 60 },
    { title: '类型', dataIndex: 'question_type', width: 80,
      render: (v: string) => { const m = typeMap[v] || { label: v, color: 'default' }; return <Tag color={m.color}>{m.label}</Tag>; }
    },
    { title: '题目', dataIndex: 'content', ellipsis: true,
      render: (v: string) => <span style={{ maxWidth: 400, display: 'inline-block', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{v}</span>
    },
    { title: '答案', dataIndex: 'answer', width: 120, render: (v: string[]) => Array.isArray(v) ? v.join(', ') : (v || '-') },
    { title: '难度', dataIndex: 'difficulty', width: 80,
      render: (v: number) => { const d = DIFFICULTY_OPTIONS.find(o => o.value === v); return d?.label || v || '-'; }
    },
    { title: '操作', key: 'action', width: 150, render: (_: any, r: Question) => (
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
          <Select allowClear placeholder="题型" style={{ width: 100 }}
            value={typeFilter} onChange={setTypeFilter}
            options={TYPE_OPTIONS} />
          <Input placeholder="搜索题目" prefix={<SearchOutlined />} style={{ width: 200 }}
            value={search} onChange={e => setSearch(e.target.value)} allowClear />
          <Button icon={<ReloadOutlined />} onClick={fetchData}>刷新</Button>
          <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>添加题目</Button>
        </Space>
      }
    >
      <Table columns={columns} dataSource={filtered} rowKey="id" loading={loading}
        pagination={{ pageSize: 20, showSizeChanger: true, showTotal: t => `共 ${filtered.length} 题 (总计 ${data.length})` }}
        size="middle" locale={{ emptyText: '暂无题目数据' }} />

      <Modal title={editingRecord ? '编辑题目' : '添加题目'} open={modalOpen}
        onOk={handleSubmit} onCancel={() => setModalOpen(false)}
        confirmLoading={submitting} destroyOnClose width={640}>
        <Form form={form} layout="vertical" style={{ marginTop: 16 }}>
          <Space size="large">
            <Form.Item name="question_type" label="题型" rules={[{ required: true }]}>
              <Select options={TYPE_OPTIONS} style={{ width: 110 }} onChange={handleTypeChange} />
            </Form.Item>
            <Form.Item name="difficulty" label="难度">
              <Select options={DIFFICULTY_OPTIONS} style={{ width: 100 }} allowClear />
            </Form.Item>
            <Form.Item name="chapter_id" label="章节ID">
              <Input placeholder="可选" style={{ width: 80 }} />
            </Form.Item>
            <Form.Item name="textbook_id" label="教材ID">
              <Input placeholder="可选" style={{ width: 80 }} />
            </Form.Item>
          </Space>
          <Form.Item name="content" label="题目" rules={[{ required: true }]}>
            <Input.TextArea rows={2} placeholder="题目标题/内容" maxLength={1000} />
          </Form.Item>

          {questionType !== 'judge' && (
            <Form.List name="options">
              {(fields, { add, remove }) => (
                <>
                  {fields.map(({ key, name, ...restField }) => (
                    <Space key={key} style={{ display: 'flex', marginBottom: 8 }} align="baseline">
                      <Form.Item {...restField} name={[name]}
                        rules={[{ required: true, message: '请输入选项' }]}
                        style={{ marginBottom: 0, width: 440 }}>
                        <Input placeholder={`选项 ${String.fromCharCode(65 + name)}`} />
                      </Form.Item>
                      {fields.length > 1 && (
                        <MinusCircleOutlined onClick={() => remove(name)} style={{ color: '#ff4d4f' }} />
                      )}
                    </Space>
                  ))}
                  <Button type="dashed" onClick={() => add()} block icon={<PlusOutlined />} style={{ marginBottom: 8 }}>
                    添加选项
                  </Button>
                </>
              )}
            </Form.List>
          )}
          <Form.Item name="answer" label="正确答案" rules={[{ required: true }]}>
            <Input
              placeholder={questionType === 'judge' ? '正确 或 错误' : questionType === 'multiple' ? '如: A,B,D' : '如: A'}
              maxLength={100}
            />
          </Form.Item>
          <Form.Item name="explanation" label="解析">
            <Input.TextArea rows={2} placeholder="可选：答案解析" maxLength={2000} />
          </Form.Item>
        </Form>
      </Modal>
    </Card>
  
    </StatusWrapper>);
}