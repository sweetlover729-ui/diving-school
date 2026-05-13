'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { Card, List, Tag, Button, Empty } from 'antd';
import { FileTextOutlined, ClockCircleOutlined } from '@ant-design/icons';
import { http } from '@/lib/http';

export default function StudentTestsPage() {
  const router = useRouter();
  const [tests, setTests] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchTests();
  }, []);

  const fetchTests = async () => {
    try {
      const data = await http.get('/student/tests');
      setTests(data);
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

  const getTypeText = (type: string) => {
    switch (type) {
      case 'exam': return '考试';
      case 'quiz': return '测验';
      case 'homework': return '作业';
      default: return type;
    }
  };

  return (
    <div style={{ padding: 24 }}>
      <h1 style={{ fontSize: 24, marginBottom: 24 }}>我的测验</h1>

      <Card loading={loading}>
        {tests.length === 0 ? (
          <Empty description="暂无测验" />
        ) : (
          <List
            dataSource={tests}
            renderItem={(item: Record<string, unknown>) => (
              <List.Item
                actions={[
                  item.is_completed ? (
                    <Button disabled>已完成</Button>
                  ) : item.is_available ? (
                    <Button type="primary" onClick={() => router.push(`/student/test/${item.id}`)}>
                      开始答题
                    </Button>
                  ) : (
                    <Button disabled>未开始</Button>
                  )
                ]}
              >
                <List.Item.Meta
                  avatar={<FileTextOutlined style={{ fontSize: 32, color: '#1890ff' }} />}
                  title={
                    <span>
                      {item.title}
                      <Tag color={getTypeColor(item.test_type)} style={{ marginLeft: 8 }}>
                        {getTypeText(item.test_type)}
                      </Tag>
                      {item.is_completed && <Tag color="success" style={{ marginLeft: 4 }}>已完成</Tag>}
                    </span>
                  }
                  description={
                    <span>
                      <span style={{ marginRight: 16 }}>共 {item.question_count} 题</span>
                      <span style={{ marginRight: 16 }}>总分 {item.total_score} 分</span>
                      {item.duration && (
                        <span style={{ marginRight: 16 }}>
                          <ClockCircleOutlined /> {item.duration} 分钟
                        </span>
                      )}
                      {item.score !== null && (
                        <span style={{ color: '#52c41a', fontWeight: 'bold' }}>
                          得分: {item.score}
                        </span>
                      )}
                    </span>
                  }
                />
              </List.Item>
            )}
          />
        )}
      </Card>
    </div>
  );
}