"use client";

import { useState, useEffect } from 'react';
import { useRouter, useParams } from 'next/navigation';
import { Card, Table, Progress, Button, Space, Statistic, Row, Col, message } from 'antd';
import { ArrowLeftOutlined, UserOutlined, BookOutlined, CheckCircleOutlined } from '@ant-design/icons';
import { http } from '@/lib/http';

export default function ClassAnalyticsPage() {
  const router = useRouter();
  const params = useParams();
  const classId = params.id as string;
  
  const [loading, setLoading] = useState(true);
  const [classInfo, setClassInfo] = useState<any>(null);
  const [students, setStudents] = useState<any[]>([]);
  const [summary, setSummary] = useState<any>(null);

  useEffect(() => {
    fetchAnalytics();
  }, [classId]);

  const fetchAnalytics = async () => {
    try {
      const data = await http.get(`/admin/classes/${classId}/analytics`);
      setClassInfo(data.class_info);
      setStudents(data.students || []);
      setSummary(data.summary);
    } catch (e) {
      message.error('获取统计数据失败');
    } finally {
      setLoading(false);
    }
  };

  const columns = [
    { 
      title: '学员', 
      dataIndex: 'name', 
      key: 'name',
      render: (name: string, record: Record<string, unknown>) => (
        <Button type="link" onClick={() => router.push(`/admin/classes/${classId}/student/${record.user_id}`)}>
          {name}
        </Button>
      )
    },
    { 
      title: '学习进度', 
      key: 'progress',
      render: (_: unknown, record: Record<string, unknown>) => (
        <Progress percent={record.progress_percent || 0} size="small" />
      )
    },
    { title: '已完成', dataIndex: 'completed', key: 'completed', render: (v: number) => `${v || 0}/72` },
    { title: '学习时长(分钟)', dataIndex: 'total_time', key: 'total_time', render: (v: number) => Math.round(v || 0) },
    { title: '待测验', dataIndex: 'waiting_test', key: 'waiting_test' },
    { 
      title: '最近活跃', 
      dataIndex: 'last_active', 
      key: 'last_active',
      render: (t: string) => t ? new Date(t).toLocaleDateString('zh-CN') : '-'
    },
  ];

  return (
    <div style={{ padding: 24 }}>
      <div style={{ marginBottom: 16 }}>
        <Button icon={<ArrowLeftOutlined />} onClick={() => router.push(`/admin/classes/${classId}`)}>返回班级详情</Button>
      </div>
      
      <h1 style={{ fontSize: 24, marginBottom: 24 }}>学习统计分析</h1>

      {summary && (
        <Row gutter={16} style={{ marginBottom: 24 }}>
          <Col span={6}>
            <Card>
              <Statistic 
                title="班级平均进度" 
                value={summary.avg_progress || 0} 
                suffix="%"
                prefix={<BookOutlined />}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic 
                title="学员总数" 
                value={summary.total_students || 0}
                prefix={<UserOutlined />}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic 
                title="已完成学员" 
                value={summary.completed_students || 0}
                prefix={<CheckCircleOutlined />}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic 
                title="总学习时长" 
                value={Math.round(summary.total_time_minutes || 0)} 
                suffix="分钟"
              />
            </Card>
          </Col>
        </Row>
      )}

      <Card title="学员学习进度排行">
        <Table
          columns={columns}
          dataSource={students}
          rowKey="user_id"
          loading={loading}
          pagination={{ pageSize: 20 }}
        />
      </Card>
    </div>
  );
}