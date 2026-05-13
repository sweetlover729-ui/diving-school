'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Card, Form, Input, Select, Button, InputNumber, message, Slider, Row, Col } from 'antd';
import { ArrowLeftOutlined, ThunderboltOutlined } from '@ant-design/icons';
import { http } from '@/lib/http';

const { Option } = Select;

export default function GenerateTestPage() {
  const router = useRouter();
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [textbooks, setTextbooks] = useState<any[]>([]);

  useEffect(() => {
    fetchTextbooks();
  }, []);

  const fetchTextbooks = async () => {
    try {
      const res = await http.get('/instructor/textbooks');
      setTextbooks(res || []);
    } catch (e) {
      console.error(e);
    }
  };

  const handleSubmit = async (values: Record<string, unknown>) => {
    try {
      setLoading(true);
      const res = await http.post('/instructor/tests/generate', values);
      message.success('智能组卷成功！');
      router.push(`/instructor/test/${res.test_id}`);
    } catch (e) {
      message.error(e.message || '组卷失败');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ padding: 24 }}>
      <div style={{ marginBottom: 24 }}>
        <Button icon={<ArrowLeftOutlined />} onClick={() => router.push('/instructor')}>
          返回工作台
        </Button>
      </div>

      <Card title="智能组卷" style={{ maxWidth: 800, margin: '0 auto' }}>
        <Form
          form={form}
          layout="vertical"
          onFinish={handleSubmit}
          initialValues={{
            question_count: 20,
            difficulty: 0.5,
            duration: 30,
          }}
        >
          <Form.Item
            label="试卷标题"
            name="title"
            rules={[{ required: true, message: '请输入试卷标题' }]}
          >
            <Input placeholder="例如：第一章测验" />
          </Form.Item>

          <Form.Item
            label="教材范围"
            name="textbook_ids"
            rules={[{ required: true, message: '请选择教材' }]}
          >
            <Select mode="multiple" placeholder="选择教材范围">
              {textbooks.map((t: Record<string, unknown>) => (
                <Option key={t.id} value={t.id}>{t.name}</Option>
              ))}
            </Select>
          </Form.Item>

          <Form.Item
            label="测验类型"
            name="test_type"
            rules={[{ required: true, message: '请选择类型' }]}
          >
            <Select placeholder="选择类型">
              <Option value="quiz">测验</Option>
              <Option value="exam">考试</Option>
              <Option value="homework">作业</Option>
            </Select>
          </Form.Item>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                label="题目数量"
                name="question_count"
                rules={[{ required: true, message: '请输入题目数量' }]}
              >
                <InputNumber min={5} max={100} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                label="考试时长（分钟）"
                name="duration"
                rules={[{ required: true, message: '请输入时长' }]}
              >
                <InputNumber min={5} max={180} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item
            label="难度系数"
            name="difficulty"
            rules={[{ required: true, message: '请设置难度' }]}
          >
            <Slider
              min={0}
              max={1}
              step={0.1}
              marks={{
                0: '简单',
                0.5: '中等',
                1: '困难',
              }}
            />
          </Form.Item>

          <Form.Item>
            <Button 
              type="primary" 
              htmlType="submit" 
              loading={loading}
              icon={<ThunderboltOutlined />}
              size="large"
              block
            >
              开始智能组卷
            </Button>
          </Form.Item>
        </Form>
      </Card>
    </div>
  );
}
