"use client";

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Result, Button, Card, Spin, Descriptions, Tag } from 'antd';
import { TrophyOutlined, DownloadOutlined, ArrowLeftOutlined } from '@ant-design/icons';
import { http } from '@/lib/http';

export default function StudentCertificatePage() {
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [cert, setCert] = useState<any>(null);
  const [error, setError] = useState('');

  useEffect(() => { fetchCertificate(); }, []);

  const fetchCertificate = async () => {
    try {
      const res = await http.get('/student/chapters/certificate');
      setCert(res);
    } catch (e: any) {
      setError(e.message || '未达到结业条件');
    } finally { setLoading(false); }
  };

  if (loading) return <div style={{ textAlign: 'center', padding: 80 }}><Spin size="large" /></div>;

  if (error) {
    return (
      <div style={{ padding: 24, maxWidth: 600, margin: '0 auto' }}>
        <Result
          status="warning"
          title="暂未达到结业条件"
          subTitle={error}
          extra={<Button type="primary" onClick={() => router.push('/student/chapters')}>继续学习</Button>}
        />
      </div>
    );
  }

  return (
    <div style={{ padding: 24, maxWidth: 800, margin: '0 auto' }}>
      <Button icon={<ArrowLeftOutlined />} onClick={() => router.push('/student')} style={{ marginBottom: 16 }}>
        返回首页
      </Button>

      {/* 证书卡片 */}
      <Card
        style={{
          background: 'linear-gradient(135deg, #ffecd2 0%, #fcb69f 100%)',
          borderRadius: 16,
          border: '3px solid #d4a574',
          padding: '32px 24px',
          textAlign: 'center',
          position: 'relative',
          overflow: 'hidden',
        }}
      >
        {/* 装饰边框 */}
        <div style={{
          position: 'absolute', top: 8, left: 8, right: 8, bottom: 8,
          border: '2px solid rgba(139, 90, 43, 0.3)', borderRadius: 12, pointerEvents: 'none'
        }} />

        <TrophyOutlined style={{ fontSize: 56, color: '#b8860b', marginBottom: 16 }} />
        <h1 style={{ fontSize: 32, fontWeight: 700, color: '#5c3317', marginBottom: 8 }}>
          结业证书
        </h1>
        <p style={{ fontSize: 16, color: '#8b5a2b', marginBottom: 24 }}>CERTIFICATE OF COMPLETION</p>

        <div style={{ fontSize: 22, color: '#5c3317', marginBottom: 8 }}>
          兹证明
        </div>
        <div style={{ fontSize: 32, fontWeight: 700, color: '#b8860b', marginBottom: 16, letterSpacing: 4 }}>
          {cert?.student_name}
        </div>
        <div style={{ fontSize: 16, color: '#5c3317', marginBottom: 24, lineHeight: 2 }}>
          已完成 <strong>{cert?.class_name}</strong> 全部课程学习<br />
          共计 <Tag color="gold">{cert?.total_sections}</Tag> 个章节，累计学习 <Tag color="blue">{cert?.total_hours} 小时</Tag><br />
          平均成绩 <Tag color="green">{cert?.avg_score} 分</Tag>
        </div>

        <div style={{ borderTop: '1px solid rgba(139,90,43,0.3)', paddingTop: 16, marginTop: 16 }}>
          <p style={{ fontSize: 13, color: '#8b5a2b' }}>
            结业日期：{cert?.completed_at?.slice(0, 10)}　　证书编号：CERT-{cert?.student_id}-{cert?.completed_at?.slice(0, 7)?.replace('-', '')}
          </p>
        </div>
      </Card>

      <div style={{ textAlign: 'center', marginTop: 24 }}>
        <Button
          type="primary"
          size="large"
          icon={<DownloadOutlined />}
          onClick={() => window.print()}
        >
          打印/保存证书
        </Button>
      </div>
    </div>
  );
}
