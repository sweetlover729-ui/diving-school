"use client";

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Card, Descriptions, Button, message, Progress, Statistic, Row, Col } from 'antd';
import { ArrowLeftOutlined, KeyOutlined, BookOutlined, CheckCircleOutlined, ClockCircleOutlined } from '@ant-design/icons';
import { http } from '@/lib/http';

export default function StudentProfilePage() {
  const router = useRouter();
  const [user, setUser] = useState<any>(null);
  const [progress, setProgress] = useState<any>(null);

  useEffect(() => {
    const userData = localStorage.getItem('user');
    if (userData) {
      setUser(JSON.parse(userData));
    }
    fetchProgress();
  }, []);

  const fetchProgress = async () => {
    try {
      const res = await http.get('/student/chapters/my-progress');
      setProgress(res);
    } catch (e) {
      console.error(e);
    }
  };

  return (
    <div style={{ padding: 24, maxWidth: 800, margin: '0 auto' }}>
      <div style={{ marginBottom: 16 }}>
        <Button icon={<ArrowLeftOutlined />} onClick={() => router.push('/student')}>返回</Button>
      </div>
      
      <h1 style={{ fontSize: 24, marginBottom: 24 }}>个人信息</h1>

      <Card style={{ marginBottom: 24 }}>
        {user && (
          <Descriptions bordered column={1}>
            <Descriptions.Item label="姓名">{user.name}</Descriptions.Item>
            <Descriptions.Item label="身份证号">{user.id_card}</Descriptions.Item>
            <Descriptions.Item label="班级">{user.class_name || '-'}</Descriptions.Item>
            <Descriptions.Item label="电话">{user.phone || '-'}</Descriptions.Item>
          </Descriptions>
        )}
        
        <div style={{ marginTop: 24 }}>
          <Button icon={<KeyOutlined />} onClick={() => router.push('/student/profile/password')}>
            修改密码
          </Button>
        </div>
      </Card>

      {progress && (
        <Card title="学习进度">
          <Row gutter={16}>
            <Col span={8}>
              <Statistic 
                title="学习进度" 
                value={progress.progress_percent || 0} 
                suffix="%" 
                prefix={<BookOutlined />}
              />
            </Col>
            <Col span={8}>
              <Statistic 
                title="已完成" 
                value={progress.completed || 0} 
                suffix={`/ ${progress.total || 72} 节`}
                prefix={<CheckCircleOutlined />}
              />
            </Col>
            <Col span={8}>
              <Statistic 
                title="学习时长" 
                value={Math.round(progress.total_reading_time_minutes || 0)} 
                suffix="分钟"
                prefix={<ClockCircleOutlined />}
              />
            </Col>
          </Row>
          <div style={{ marginTop: 16 }}>
            <Progress percent={progress.progress_percent || 0} />
          </div>
        </Card>
      )}
    </div>
  );
}