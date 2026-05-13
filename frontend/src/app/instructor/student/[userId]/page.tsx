'use client';

import { useState, useEffect } from 'react';
import { useRouter, useParams } from 'next/navigation';
import { Card, Descriptions, Progress, Table, Tag, Button, message, Statistic, Row, Col } from 'antd';
import { ArrowLeftOutlined, BookOutlined, CheckCircleOutlined, ClockCircleOutlined } from '@ant-design/icons';
import { http } from '@/lib/http';

export default function StudentDetailPage() {
  const router = useRouter();
  const params = useParams();
  const userId = params.userId as string;
  
  const [loading, setLoading] = useState(true);
  const [student, setStudent] = useState<any>(null);
  const [progress, setProgress] = useState<any>(null);

  useEffect(() => {
    if (userId) {
      fetchStudentDetail();
    }
  }, [userId]);

  const fetchStudentDetail = async () => {
    try {
      setLoading(true);
      const [progressRes, studentsRes] = await Promise.all([
        http.get(`/instructor/students/${userId}/progress`),
        http.get('/instructor/students'),
      ]);
      const studentInfo = (studentsRes || []).find((s: Record<string, unknown>) => String(s.user_id) === String(userId)
      );
      setStudent(studentInfo || { name: progressRes.name, phone: '-', id_card: '-' });
      setProgress(progressRes);
    } catch (e) {
      message.error('获取学员详情失败');
    } finally {
      setLoading(false);
    }
  };

  const chapterColumns = [
    { title: '章节', dataIndex: 'chapter_title', key: 'chapter_title' },
    { 
      title: '状态', 
      dataIndex: 'status', 
      key: 'status',
      render: (status: string) => {
        const colors: Record<string, string> = { completed: 'green', reading: 'blue', locked: 'default' };
        const labels: Record<string, string> = { completed: '已完成', reading: '学习中', locked: '未解锁' };
        return <Tag color={colors[status] || 'default'}>{labels[status] || status}</Tag>;
      }
    },
    { title: '阅读时长', dataIndex: 'reading_time', key: 'reading_time', render: (t: number) => t ? `${Math.round(t/60)}分钟` : '-' },
    { title: '完成时间', dataIndex: 'completed_at', key: 'completed_at', render: (t: string) => t ? new Date(t).toLocaleDateString('zh-CN') : '-' },
  ];

  return (
    <div style={{ padding: 24 }}>
      <div style={{ marginBottom: 24 }}>
        <Button icon={<ArrowLeftOutlined />} onClick={() => router.push('/instructor')}>
          返回工作台
        </Button>
      </div>

      <Card title="学员信息" loading={loading} style={{ marginBottom: 24 }}>
        {student && (
          <Descriptions bordered column={2}>
            <Descriptions.Item label="姓名">{student.name}</Descriptions.Item>
            <Descriptions.Item label="手机号">{student.phone || '-'}</Descriptions.Item>
            <Descriptions.Item label="身份证号">{student.id_card || '-'}</Descriptions.Item>
            <Descriptions.Item label="加入时间">{student.joined_at ? new Date(student.joined_at).toLocaleDateString('zh-CN') : '-'}</Descriptions.Item>
          </Descriptions>
        )}
      </Card>

      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={6}>
          <Card>
            <Statistic 
              title="总进度" 
              value={progress?.overall_progress || 0} 
              suffix="%"
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic 
              title="已完成章节" 
              value={progress?.completed_chapters || 0} 
              suffix={`/ ${progress?.total_chapters || 0}`}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic 
              title="总阅读时长" 
              value={Math.round((progress?.total_reading_time || 0) / 60)} 
              suffix="分钟"
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic 
              title="测验平均分" 
              value={progress?.avg_test_score || 0} 
              suffix="分"
            />
          </Card>
        </Col>
      </Row>

      <Card title="章节进度" loading={loading}>
        <Table 
          columns={chapterColumns} 
          dataSource={progress?.chapters || []} 
          rowKey="chapter_id"
          pagination={{ pageSize: 10 }}
        />
      </Card>
    </div>
  );
}
