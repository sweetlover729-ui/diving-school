'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { Card, Row, Col, Progress, Button, Empty } from 'antd';
import { BookOutlined } from '@ant-design/icons';
import { http } from '@/lib/http';

export default function StudentTextbooksPage() {
  const router = useRouter();
  const [textbooks, setTextbooks] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchTextbooks();
  }, []);

  const fetchTextbooks = async () => {
    try {
      const data = await http.get('/student/textbooks');
      setTextbooks(data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ padding: 24 }}>
      <h1 style={{ fontSize: 24, marginBottom: 24 }}>学习教材</h1>

      <Row gutter={[16, 16]}>
        {textbooks.length === 0 && !loading && (
          <Col span={24}>
            <Card>
              <Empty description="暂无教材" />
            </Card>
          </Col>
        )}
        
        {textbooks.map((book: Record<string, unknown>) => (
          <Col span={8} key={book.id}>
            <Card
              hoverable
              style={{ height: '100%' }}
            >
              <div style={{ textAlign: 'center', marginBottom: 16 }}>
                <BookOutlined style={{ fontSize: 48, color: '#1890ff' }} />
              </div>
              
              <h3 style={{ textAlign: 'center', marginBottom: 8 }}>{book.name}</h3>
              <p style={{ color: '#666', fontSize: 12, textAlign: 'center', marginBottom: 16 }}>
                {book.description}
              </p>
              
              <div style={{ marginBottom: 16 }}>
                <Progress percent={book.progress || 0} size="small" />
              </div>
              
              <div style={{ textAlign: 'center', color: '#999', fontSize: 12, marginBottom: 16 }}>
                <span style={{ marginRight: 16 }}>共 {book.total_pages} 页</span>
                <span>第 {book.current_page || 0} 页</span>
              </div>
              
              <Button 
                type="primary" 
                block 
                onClick={() => router.push(`/student/textbook/${book.id}`)}
              >
                {book.progress > 0 ? '继续学习' : '开始学习'}
              </Button>
            </Card>
          </Col>
        ))}
      </Row>
    </div>
  );
}