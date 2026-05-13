"use client";

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Layout, Card, Button, message, Space, Statistic, Row, Col, Progress, List } from 'antd';
import { ArrowLeftOutlined, TeamOutlined, BookOutlined, TrophyOutlined, ClockCircleOutlined } from '@ant-design/icons';
import { http } from '@/lib/http';

const { Content } = Layout;

interface AnalyticsData {
  student_count: number;
  avg_score: number;
  avg_reading_progress: number;
  total_reading_time: number;
  test_count: number;
  remaining_days: number;
  chapter_stats: {
    chapter_id: number;
    chapter_title: string;
    completion_rate: number;
    avg_score: number;
  }[];
}

export default function InstructorAnalyticsPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState<AnalyticsData>({
    student_count: 0,
    avg_score: 0,
    avg_reading_progress: 0,
    total_reading_time: 0,
    test_count: 0,
    remaining_days: 0,
    chapter_stats: [],
  });

  useEffect(() => {
    fetchAnalytics();
  }, []);

  const fetchAnalytics = async () => {
    try {
      const res = await http.get('/instructor/analytics/overview');
      setData(res);
    } catch (e) {
      message.error('获取统计数据失败');
    } finally {
      setLoading(false);
    }
  };

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
            <Card loading={loading}>
              <Statistic title="学员总数" value={data.student_count} prefix={<TeamOutlined />} />
            </Card>
          </Col>
          <Col span={6}>
            <Card loading={loading}>
              <Statistic title="平均成绩" value={data.avg_score} suffix="分" prefix={<TrophyOutlined />} />
            </Card>
          </Col>
          <Col span={6}>
            <Card loading={loading}>
              <Statistic title="平均阅读进度" value={data.avg_reading_progress} suffix="%" prefix={<BookOutlined />} />
            </Card>
          </Col>
          <Col span={6}>
            <Card loading={loading}>
              <Statistic title="剩余天数" value={data.remaining_days} suffix="天" prefix={<ClockCircleOutlined />} />
            </Card>
          </Col>
        </Row>

        <Row gutter={16}>
          <Col span={12}>
            <Card title="章节完成情况" loading={loading}>
              <List
                dataSource={data.chapter_stats}
                renderItem={(item) => (
                  <List.Item>
                    <div className="w-full">
                      <div className="flex justify-between mb-1">
                        <span>{item.chapter_title}</span>
                        <span className="text-gray-500">{item.completion_rate}%</span>
                      </div>
                      <Progress percent={item.completion_rate} size="small" />
                    </div>
                  </List.Item>
                )}
              />
            </Card>
          </Col>
          <Col span={12}>
            <Card title="学习概况" loading={loading}>
              <div className="space-y-4">
                <div>
                  <div className="text-gray-500 mb-1">总学习时长</div>
                  <div className="text-2xl font-bold">{Math.round(data.total_reading_time / 60)} 小时</div>
                </div>
                <div>
                  <div className="text-gray-500 mb-1">已发布测验</div>
                  <div className="text-2xl font-bold">{data.test_count} 次</div>
                </div>
                <div>
                  <div className="text-gray-500 mb-1">人均学习时长</div>
                  <div className="text-2xl font-bold">
                    {data.student_count > 0 ? Math.round(data.total_reading_time / data.student_count / 60) : 0} 小时
                  </div>
                </div>
              </div>
            </Card>
          </Col>
        </Row>
      </Content>
    </Layout>
  );
}
