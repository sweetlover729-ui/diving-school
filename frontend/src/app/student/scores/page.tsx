'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { Card, Table, Tag, Button, Empty } from 'antd';
import { http } from '@/lib/http';

export default function StudentScoresPage() {
  const router = useRouter();
  const [scores, setScores] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchScores();
  }, []);

  const fetchScores = async () => {
    try {
      const data = await http.get('/student/scores');
      setScores(data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const getTypeColor = (type: string) => {
    switch (type) {
      case 'exam': return 'red';
      case 'quiz': return 'blue';
      case 'homework': return 'green';
      default: return 'default';
    }
  };

  const columns = [
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
        <Tag color={getTypeColor(type)}>
          {type === 'exam' ? '考试' : type === 'quiz' ? '测验' : '作业'}
        </Tag>
      ),
    },
    {
      title: '得分',
      key: 'score',
      render: (_: unknown, record: Record<string, unknown>) => (
        <span style={{ 
          color: record.score >= record.total_score * 0.6 ? '#52c41a' : '#ff4d4f',
          fontWeight: 'bold'
        }}>
          {record.score} / {record.total_score}
        </span>
      ),
    },
    {
      title: '用时',
      dataIndex: 'time_spent',
      key: 'time_spent',
      render: (t: number) => t ? `${Math.floor(t / 60)}分${t % 60}秒` : '-',
    },
    {
      title: '提交时间',
      dataIndex: 'submitted_at',
      key: 'submitted_at',
      render: (t: string) => t ? new Date(t).toLocaleString() : '-',
    },
    {
      title: '操作',
      key: 'action',
      render: (_: unknown, record: Record<string, unknown>) => (
        <Button type="link" onClick={() => router.push(`/student/score/${record.test_id}`)}>
          查看详情
        </Button>
      ),
    },
  ];

  return (
    <div style={{ padding: 24 }}>
      <h1 style={{ fontSize: 24, marginBottom: 24 }}>我的成绩</h1>

      <Card loading={loading}>
        {scores.length === 0 ? (
          <Empty description="暂无成绩记录" />
        ) : (
          <Table
            columns={columns}
            dataSource={scores}
            rowKey="test_id"
            pagination={{ pageSize: 10 }}
          />
        )}
      </Card>
    </div>
  );
}