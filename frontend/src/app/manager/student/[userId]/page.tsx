'use client';

import { useState, useEffect } from 'react';
import { useRouter, useParams } from 'next/navigation';
import { Card, Descriptions, Progress, Table, Tag, Button, Statistic, Row, Col, Spin, message } from 'antd';
import { ArrowLeftOutlined } from '@ant-design/icons';
import { http } from '@/lib/http';

export default function ManagerStudentDetailPage() {
  const router = useRouter();
  const params = useParams();
  const userId = params.userId as string;
  const [loading, setLoading] = useState(true);
  const [student, setStudent] = useState<any>(null);

  useEffect(() => {
    if (userId) {
      http.get(`/manager/students/${userId}`)
        .then(setStudent)
        .catch(() => message.error('获取学员详情失败'))
        .finally(() => setLoading(false));
    }
  }, [userId]);

  const readingColumns = [
    { title: '教材', dataIndex: 'textbook_id', key: 'textbook_id', render: (id: number) => `教材 #${id}` },
    { title: '进度', dataIndex: 'progress', key: 'progress', render: (p: number) => <Progress percent={p} size="small" /> },
    { title: '阅读时长', dataIndex: 'duration', key: 'duration', render: (d: number) => d ? `${Math.round(d / 60)}分钟` : '-' },
  ];

  const testsColumns = [
    { title: '测验', dataIndex: 'test_title', key: 'test_title' },
    { title: '得分', dataIndex: 'score', key: 'score', render: (s: number) => s !== null ? `${s}分` : '未参加' },
    { title: '提交时间', dataIndex: 'submitted_at', key: 'submitted_at', render: (t: string) => t ? new Date(t).toLocaleString('zh-CN') : '-' },
  ];

  return (
    <div style={{ padding: 24 }}>
      <Button icon={<ArrowLeftOutlined />} onClick={() => router.push('/manager')} style={{ marginBottom: 16 }}>
        返回工作台
      </Button>

      <Spin spinning={loading}>
        {student && (
          <>
            <Card title="学员信息" style={{ marginBottom: 24 }}>
              <Descriptions bordered column={2}>
                <Descriptions.Item label="姓名">{student.name}</Descriptions.Item>
                <Descriptions.Item label="手机号">{student.phone || '-'}</Descriptions.Item>
                <Descriptions.Item label="身份证号">{student.id_card || '-'}</Descriptions.Item>
                <Descriptions.Item label="总测验次数">{student.tests_completed || 0}次</Descriptions.Item>
                <Descriptions.Item label="测验平均分">{student.avg_score || 0}分</Descriptions.Item>
              </Descriptions>
            </Card>

            <Card title="阅读进度" style={{ marginBottom: 24 }}>
              {student.reading_progress?.length > 0 ? (
                <Table
                  columns={readingColumns}
                  dataSource={student.reading_progress}
                  rowKey="textbook_id"
                  pagination={false}
                />
              ) : (
                <p style={{ color: '#999', textAlign: 'center' }}>暂无阅读记录</p>
              )}
            </Card>

            <Card title="测验成绩">
              <p style={{ color: '#999', textAlign: 'center' }}>暂无测验记录</p>
            </Card>
          </>
        )}
      </Spin>
    </div>
  );
}
