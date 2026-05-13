'use client';

import { useState, useEffect, useMemo } from 'react';
import { Table, Button, Modal, Form, Input, InputNumber, Select, Switch, Space, Popconfirm, Tag, message, Card, Row, Col } from 'antd';
import { PlusOutlined, EditOutlined, DeleteOutlined, ReloadOutlined, FilterOutlined } from '@ant-design/icons';
import { courseApi } from '@/lib/api';
import { useCategory } from '@/components/CategoryProvider';
import type { Course } from '@/lib/types';

const LEVEL_OPTIONS = [
  { label: '初级', value: 'beginner' },
  { label: '中级', value: 'intermediate' },
  { label: '高级', value: 'advanced' },
  { label: '专家', value: 'expert' },
];

export default function CoursesPage() {
  const { categories, currentCategoryId } = useCategory();
  const [courses, setCourses] = useState<Course[]>([]);
  const [loading, setLoading] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [editingRecord, setEditingRecord] = useState<Course | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [filterCategory, setFilterCategory] = useState<number | undefined>();
  const [form] = Form.useForm();

  const fetchCourses = async () => {
    setLoading(true);
    try {
      const data = await courseApi.list();
      setCourses(Array.isArray(data) ? data : []);
    } catch (e: any) {
      message.error(e.message || '加载失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchCourses(); }, []);

  const filteredCourses = useMemo(() => {
    if (!filterCategory) return courses;
    return courses.filter(c => c.category_id === filterCategory);
  }, [courses, filterCategory]);

  const openCreate = () => {
    setEditingRecord(null);
    form.resetFields();
    form.setFieldsValue({
      category_id: currentCategoryId || undefined,
      is_active: true,
      sort_order: 0,
    });
    setModalOpen(true);
  };

  const openEdit = (record: Course) => {
    setEditingRecord(record);
    form.setFieldsValue(record);
    setModalOpen(true);
  };

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      setSubmitting(true);

      if (editingRecord) {
        await courseApi.update(editingRecord.id, values);
        message.success('更新成功');
      } else {
        await courseApi.create(values);
        message.success('创建成功');
      }

      setModalOpen(false);
      fetchCourses();
    } catch (e: any) {
      if (e.message) message.error(e.message);
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (id: number) => {
    try {
      await courseApi.remove(id);
      message.success('已删除');
      fetchCourses();
    } catch (e: any) {
      message.error(e.message || '删除失败');
    }
  };

  const categoryMap = useMemo(() => {
    const map: Record<number, string> = {};
    categories.forEach(c => { map[c.id] = c.name; });
    return map;
  }, [categories]);

  const columns = [
    { title: 'ID', dataIndex: 'id', width: 60 },
    {
      title: '分类', dataIndex: 'category_id', width: 100,
      render: (id: number) => categoryMap[id] || '-'
    },
    { title: '编码', dataIndex: 'code', width: 100 },
    { title: '名称', dataIndex: 'name', width: 160 },
    {
      title: '等级', dataIndex: 'level', width: 80,
      render: (v: string) => {
        const opt = LEVEL_OPTIONS.find(o => o.value === v);
        const colors: Record<string, string> = { beginner: 'blue', intermediate: 'orange', advanced: 'red', expert: 'purple' };
        return <Tag color={colors[v] || 'default'}>{opt?.label || v || '-'}</Tag>;
      }
    },
    { title: '天数', dataIndex: 'duration_days', width: 70, align: 'center' as const },
    {
      title: '人数', key: 'capacity', width: 100, align: 'center' as const,
      render: (_: any, r: Course) => r.min_students || r.max_students ? `${r.min_students || 0}-${r.max_students || '不限'}` : '-'
    },
    {
      title: 'LLM', dataIndex: 'llm_enabled', width: 70, align: 'center' as const,
      render: (v: boolean) => <Tag color={v ? 'blue' : 'default'}>{v ? '开' : '关'}</Tag>
    },
    {
      title: '状态', dataIndex: 'is_active', width: 70, align: 'center' as const,
      render: (v: boolean) => <Tag color={v ? 'green' : 'default'}>{v ? '启用' : '停用'}</Tag>
    },
    {
      title: '操作', key: 'action', width: 150,
      render: (_: any, record: Course) => (
        <Space>
          <Button type="link" size="small" icon={<EditOutlined />} onClick={() => openEdit(record)}>编辑</Button>
          <Popconfirm title="确认删除？" onConfirm={() => handleDelete(record.id)}>
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
          <Button icon={<ReloadOutlined />} onClick={fetchCourses}>刷新</Button>
          <Select
            allowClear
            placeholder="按分类筛选"
            style={{ width: 130 }}
            value={filterCategory}
            onChange={setFilterCategory}
            options={categories.filter(c => c.is_active).map(c => ({ value: c.id, label: c.name }))}
          />
          <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>新建课程</Button>
        </Space>
      }
    >
      <Table
        columns={columns}
        dataSource={filteredCourses}
        rowKey="id"
        loading={loading}
        pagination={false}
        size="middle"
        locale={{ emptyText: '暂无课程数据，请先创建培训分类' }}
      />

      <Modal
        title={editingRecord ? '编辑课程' : '新建课程'}
        open={modalOpen}
        onOk={handleSubmit}
        onCancel={() => setModalOpen(false)}
        confirmLoading={submitting}
        destroyOnClose
        width={560}
      >
        <Form form={form} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item name="category_id" label="所属分类" rules={[{ required: true, message: '请选择分类' }]}>
            <Select options={categories.filter(c => c.is_active).map(c => ({ value: c.id, label: c.name }))} />
          </Form.Item>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="code" label="编码" rules={[{ required: true, message: '请输入编码' }]}>
                <Input placeholder="如: diving-basic" maxLength={50} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="name" label="名称" rules={[{ required: true, message: '请输入名称' }]}>
                <Input placeholder="如: 公共安全潜水基础" maxLength={100} />
              </Form.Item>
            </Col>
          </Row>
          <Form.Item name="description" label="描述">
            <Input.TextArea rows={2} maxLength={500} />
          </Form.Item>
          <Row gutter={16}>
            <Col span={8}>
              <Form.Item name="level" label="等级">
                <Select options={LEVEL_OPTIONS} allowClear placeholder="选择等级" />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="duration_days" label="培训天数">
                <InputNumber min={1} max={365} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="sort_order" label="排序">
                <InputNumber min={0} max={9999} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={16}>
            <Col span={8}>
              <Form.Item name="min_students" label="最少人数">
                <InputNumber min={1} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="max_students" label="最多人数">
                <InputNumber min={1} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="is_active" label="启用" valuePropName="checked">
                <Switch />
              </Form.Item>
            </Col>
          </Row>
        </Form>
      </Modal>
    </Card>
  );
}