"use client";

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Layout, Card, Table, Tag, Button, message, Space, Statistic, Row, Col } from 'antd';
import { ArrowLeftOutlined, TrophyOutlined, FileTextOutlined } from '@ant-design/icons';
import { http } from '@/lib/http';

const { Content } = Layout;

interface TestResult {
  id: number;
  student_name: string;
  test_title: string;
  test_type: string;
  score: number;
  total_score: number;
  submitted_at: string;
}

interface ScoreStats {
  total_tests: number;
  avg_score: number;
  pass_count: number;
  fail_count: number;
}

export default function InstructorScoresPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [results, setResults] = useState<TestResult[]>([]);
  const [stats, setStats] = useState<ScoreStats>({ total_tests: 0, avg_score: 0, pass_count: 0, fail_count: 0 });

  useEffect(() => {
    fetchScores();
  }, []);

  const fetchScores = async () => {
    try {
      const res = await http.get('/instructor/scores');
      setResults(res.results || []);
      setStats(res.stats || { total_tests: 0, avg_score: 0, pass_count: 0, fail_count: 0 });
    } catch (e) {
      message.error('获取成绩数据失败');
    } finally {
      setLoading(false);
    }
  };

  const columns = [
    {
      title: '学员姓名',
      dataIndex: 'student_name',
      key: 'student_name',
    },
    {
      title: '测验名称',
      dataIndex: 'test_title',
      key: 'test_title',
    },
    {
      title: '类型',
      dataIndex: 'test_type',
      key: 'test_type',
      render: (type: string) => (
        <Tag color={type === 'exam' ? 'red' : type === 'quiz' ? 'blue' : 'green'}>
          {type === 'exam' ? '考试' : type === 'quiz' ? '测验' : '作业'}
        </Tag>
      ),
    },
    {
      title: '得分',
      key: 'score',
      render: (_: unknown, record: TestResult) => (
        <span className={record.score >= 60 ? 'text-green-600 font-bold' : 'text-red-600 font-bold'}>
          {record.score}/{record.total_score}
        </span>
      ),
    },
    {
      title: '结果',
      key: 'result',
      render: (_: unknown, record: TestResult) => (
        <Tag color={record.score >= 60 ? 'success' : 'error'}>
          {record.score >= 60 ? '通过' : '未通过'}
        </Tag>
      ),
    },
    {
      title: '提交时间',
      dataIndex: 'submitted_at',
      key: 'submitted_at',
      render: (date: string) => date ? new Date(date).toLocaleString('zh-CN') : '-',
    },
  ];

  return (
    <Layout className="min-h-screen bg-gray-100">
      <Content className="p-6">
        <Space className="mb-4">
          <Button icon={<ArrowLeftOutlined />} onClick={() => router.push('/instructor')}>
            返回工作台
          </Button>
        </Space>

        <Row gutter={16} className="mb-4">
          <Col span={6}>
            <Card>
              <Statistic title="总测验数" value={stats.total_tests} prefix={<FileTextOutlined />} />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic title="平均分" value={stats.avg_score} suffix="分" prefix={<TrophyOutlined />} />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic title="通过人数" value={stats.pass_count} valueStyle={{ color: '#3f8600' }} />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic title="未通过人数" value={stats.fail_count} valueStyle={{ color: '#cf1322' }} />
            </Card>
          </Col>
        </Row>

        <Card title="成绩汇总">
          <Table
            dataSource={results}
            columns={columns}
            rowKey="id"
            loading={loading}
            pagination={{ pageSize: 20 }}
          />
        </Card>
      </Content>
    </Layout>
  );
}
