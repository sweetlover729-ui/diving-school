"use client";

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Card, Button, Tag, Spin, Alert, List, Progress, Space } from 'antd';
import { ArrowLeftOutlined, BookOutlined, ThunderboltOutlined, BulbOutlined } from '@ant-design/icons';
import { http } from '@/lib/http';

interface WeakArea {
  chapter_id: number;
  title: string;
  status: string;
}

export default function SmartReviewPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [review, setReview] = useState<{ weak_areas: WeakArea[]; suggestion: string; total_weak: number } | null>(null);

  useEffect(() => { fetchReview(); }, []);

  const fetchReview = async () => {
    try {
      const res = await http.get('/student/chapters/review');
      setReview(res);
    } catch (e) { console.error(e); }
    finally { setLoading(false); }
  };

  const goToChapter = (id: number) => {
    router.push(`/student/exercises/${id}?self_test=1`);
  };

  if (loading) return <div style={{ textAlign: 'center', padding: 80 }}><Spin size="large" /></div>;

  return (
    <div style={{ padding: 24, maxWidth: 700, margin: '0 auto' }}>
      <Button icon={<ArrowLeftOutlined />} onClick={() => router.push('/student')} style={{ marginBottom: 16 }}>
        返回
      </Button>

      <Card>
        <h1 style={{ fontSize: 22, display: 'flex', alignItems: 'center', gap: 8 }}>
          <BulbOutlined style={{ color: '#faad14' }} /> 智能复习推荐
        </h1>

        {review && (
          <Alert
            type={review.total_weak === 0 ? 'success' : 'warning'}
            message={review.suggestion}
            style={{ marginBottom: 20 }}
            showIcon
          />
        )}

        {review && review.total_weak > 0 ? (
          <>
            <Progress
              percent={Math.round((1 - review.total_weak / (review.weak_areas.length + review.total_weak || 1)) * 100)}
              format={() => `${review.total_weak} 个`}
              status="exception"
              style={{ marginBottom: 16 }}
            />

            <List
              dataSource={review.weak_areas}
              renderItem={(item: WeakArea) => (
                <List.Item
                  actions={[
                    <Button size="small" icon={<BookOutlined />} key="read"
                      onClick={() => router.push('/student/chapters')}>
                      复习
                    </Button>,
                    <Button size="small" type="primary" ghost icon={<ThunderboltOutlined />} key="test"
                      onClick={() => goToChapter(item.chapter_id)}>
                      自测通关
                    </Button>
                  ]}
                >
                  <List.Item.Meta
                    title={<Space>
                      <Tag color={item.status === 'waiting_test' ? 'orange' : 'red'}>
                        {item.status === 'waiting_test' ? '待测验' : '待练习'}
                      </Tag>
                      {item.title}
                    </Space>}
                  />
                </List.Item>
              )}
            />
          </>
        ) : (
          <div style={{ textAlign: 'center', padding: 24 }}>
            <TrophyOutlined style={{ fontSize: 48, color: '#52c41a' }} />
            <p style={{ marginTop: 16, fontSize: 16, color: '#52c41a' }}>🏆 太棒了！所有章节均已通关！</p>
            <Button type="primary" onClick={() => router.push('/student/certificate')}>
              查看结业证书
            </Button>
          </div>
        )}
      </Card>
    </div>
  );
}
