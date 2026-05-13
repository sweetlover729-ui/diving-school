"use client";

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Card, Descriptions, Button } from 'antd';
import { ArrowLeftOutlined, KeyOutlined } from '@ant-design/icons';

export default function InstructorProfilePage() {
  const router = useRouter();
  const [user, setUser] = useState<any>(null);

  useEffect(() => {
    const userData = localStorage.getItem('user');
    if (userData) {
      setUser(JSON.parse(userData));
    }
  }, []);

  return (
    <div style={{ padding: 24, maxWidth: 600, margin: '0 auto' }}>
      <div style={{ marginBottom: 16 }}>
        <Button icon={<ArrowLeftOutlined />} onClick={() => router.push('/instructor')}>返回</Button>
      </div>
      
      <h1 style={{ fontSize: 24, marginBottom: 24 }}>个人信息</h1>

      <Card>
        {user && (
          <Descriptions bordered column={1}>
            <Descriptions.Item label="姓名">{user.name}</Descriptions.Item>
            <Descriptions.Item label="身份证号">{user.id_card}</Descriptions.Item>
            <Descriptions.Item label="角色">教练</Descriptions.Item>
            <Descriptions.Item label="电话">{user.phone || '-'}</Descriptions.Item>
          </Descriptions>
        )}
        
        <div style={{ marginTop: 24 }}>
          <Button icon={<KeyOutlined />} onClick={() => router.push('/instructor/profile/password')}>
            修改密码
          </Button>
        </div>
      </Card>
    </div>
  );
}