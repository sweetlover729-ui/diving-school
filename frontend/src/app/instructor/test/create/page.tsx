'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Card, Form, Input, Select, InputNumber, DatePicker, Button, message, Space, Table, Tag } from 'antd';
import { PlusOutlined, DeleteOutlined, ThunderboltOutlined } from '@ant-design/icons';
import { http } from '@/lib/http';

const { RangePicker } = DatePicker;

export default function CreateTestPage() {
  const router = useRouter();
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [questions, setQuestions] = useState<any[]>([]);
  const [selectedQuestions, setSelectedQuestions] = useState<any[]>([]);
  const [textbooks, setTextbooks] = useState<any[]>([]);

  useEffect(() => {
    fetchTextbooks();
    fetchQuestions();
  }, []);

  const fetchTextbooks = async () => {
    try {
      const data = await http.get('/instructor/textbooks');
      setTextbooks(data);
    } catch (e) {
      console.error(e);
    }
  };

  const fetchQuestions = async () => {
    try {
      const data = await http.get('/instructor/questions');
      setQuestions(data);
    } catch (e) {
      console.error(e);
    }
  };

  const handleGenerate = async () => {
    try {
      const values = await form.validateFields(['textbook_id', 'question_types', 'count']);
      const data = await http.post('/instructor/tests/generate', {
        textbook_id: values.textbook_id,
        question_types: values.question_types,
        count: values.count || 20
      });
      setSelectedQuestions(data.questions);
      message.success(`已抽取 ${data.count} 道题目`);
    } catch (e) {
      message.error(e.message || '抽题失败');
    }
  };

  const handleRemoveQuestion = (id: number) => {
    setSelectedQuestions(selectedQuestions.filter(q => q.id !== id));
  };

  const handleSubmit = async () => {
    if (selectedQuestions.length === 0) {
      message.error('请先选择题目');
      return;
    }

    setLoading(true);
    try {
      const values = await form.validateFields();
      
      await http.post('/instructor/tests', {
        title: values.title,
        test_type: values.test_type,
        questions: selectedQuestions.map(q => q.id),
        duration: values.duration,
        start_time: values.time_range?.[0]?.toDate(),
        end_time: values.time_range?.[1]?.toDate()
      });

      message.success('测验发布成功');
      router.push('/instructor');
    } catch (e) {
      message.error(e.message || '发布失败');
    } finally {
      setLoading(false);
    }
  };

  const columns = [
    {
      title: '题型',
      dataIndex: 'question_type',
      key: 'question_type',
      render: (type: string) => (
        <Tag color={type === 'single' ? 'blue' : type === 'multiple' ? 'purple' : 'green'}>
          {type === 'single' ? '单选' : type === 'multiple' ? '多选' : '判断'}
        </Tag>
      ),
    },
    { title: '题目内容', dataIndex: 'content', key: 'content', ellipsis: true },
    { title: '难度', dataIndex: 'difficulty', key: 'difficulty' },
    {
      title: '操作',
      key: 'action',
      render: (_: unknown, record: Record<string, unknown>) => (
        <Button danger icon={<DeleteOutlined />} onClick={() => handleRemoveQuestion(record.id)} />
      ),
    },
  ];

  return (
    <div style={{ padding: 24 }}>
      <h1 style={{ fontSize: 24, marginBottom: 24 }}>发布测验</h1>

      <Card title="基本信息" style={{ marginBottom: 16 }}>
        <Form form={form} layout="vertical">
          <Form.Item name="title" label="测验标题" rules={[{ required: true }]}>
            <Input placeholder="如：第一章测试" />
          </Form.Item>
          <Form.Item name="test_type" label="测验类型" rules={[{ required: true }]}>
            <Select options={[
              { label: '课后作业', value: 'homework' },
              { label: '随堂测验', value: 'quiz' },
              { label: '正式考试', value: 'exam' }
            ]} />
          </Form.Item>
          <Form.Item name="duration" label="考试时长（分钟）">
            <InputNumber min={10} max={180} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="time_range" label="考试时间">
            <RangePicker showTime style={{ width: '100%' }} />
          </Form.Item>
        </Form>
      </Card>

      <Card title="组卷方式" style={{ marginBottom: 16 }}>
        <Form form={form} layout="inline">
          <Form.Item name="textbook_id" label="教材">
            <Select style={{ width: 200 }} allowClear options={textbooks.map(t => ({ label: t.name, value: t.id }))} />
          </Form.Item>
          <Form.Item name="question_types" label="题型">
            <Select mode="multiple" style={{ width: 200 }} options={[
              { label: '单选题', value: 'single' },
              { label: '多选题', value: 'multiple' },
              { label: '判断题', value: 'judge' }
            ]} />
          </Form.Item>
          <Form.Item name="count" label="题数">
            <InputNumber min={5} max={100} defaultValue={20} />
          </Form.Item>
          <Form.Item>
            <Button type="primary" icon={<ThunderboltOutlined />} onClick={handleGenerate}>
              智能抽题
            </Button>
          </Form.Item>
        </Form>
      </Card>

      <Card
        title={`已选题目 (${selectedQuestions.length}道)`}
        extra={<Button onClick={() => setSelectedQuestions([])}>清空</Button>}
        style={{ marginBottom: 16 }}
      >
        <Table
          columns={columns}
          dataSource={selectedQuestions}
          rowKey="id"
          pagination={false}
          scroll={{ y: 300 }}
        />
      </Card>

      <div style={{ textAlign: 'right' }}>
        <Space>
          <Button onClick={() => router.back()}>取消</Button>
          <Button type="primary" loading={loading} onClick={handleSubmit}>
            发布测验
          </Button>
        </Space>
      </div>
    </div>
  );
}