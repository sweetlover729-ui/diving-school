'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { Card, Row, Col, Statistic, Table, Button, Space, Tag, Progress, Dropdown, Avatar } from 'antd';
import { TeamOutlined, FileTextOutlined, BarChartOutlined, PlusOutlined, UserOutlined, LogoutOutlined, KeyOutlined } from '@ant-design/icons';
import { http } from '@/lib/http';

export default function InstructorDashboard() {
  const router = useRouter();
  const [user, setUser] = useState<any>({});
  const [cls, setCls] = useState<any>({});
  const [analytics, setAnalytics] = useState<any>({});
  const [students, setStudents] = useState<any[]>([]);
  const [tests, setTests] = useState<any[]>([]);

  useEffect(() => {
    checkAuth();
    fetchData();
  }, []);

  const checkAuth = () => {
    const token = localStorage.getItem('token');
    const userStr = localStorage.getItem('user');
    const classStr = localStorage.getItem('class');
    
    if (!token || !userStr) {
      router.push('/login');
      return;
    }
    
    const userData = JSON.parse(userStr);
    if (userData.role !== 'instructor') {
      router.push('/login');
      return;
    }
    
    setUser(userData);
    if (classStr) {
      setCls(JSON.parse(classStr));
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    localStorage.removeItem('class');
    router.push('/login');
  };

  const userMenuItems = [
    { key: 'profile', icon: <UserOutlined />, label: '个人信息', onClick: () => router.push('/instructor/profile') },
    { key: 'password', icon: <KeyOutlined />, label: '修改密码', onClick: () => router.push('/instructor/profile/password') },
    { type: 'divider' as const },
    { key: 'logout', icon: <LogoutOutlined />, label: '退出登录', onClick: handleLogout, danger: true },
  ];

  const fetchData = async () => {
    try {
      const a = await http.get('/instructor/analytics/overview');
      setAnalytics(a);
      
      const s = await http.get('/instructor/students');
      setStudents(s);
      
      const t = await http.get('/instructor/tests');
      setTests(t);
    } catch (e) {
      console.error(e);
    }
  };

  const studentColumns = [
    { title: '姓名', dataIndex: 'name', key: 'name' },
    { title: '身份证号', dataIndex: 'id_card', key: 'id_card' },
    { title: '手机号', dataIndex: 'phone', key: 'phone' },
    {
      title: '操作',
      key: 'action',
      render: (_: unknown, record: Record<string, unknown>) => (
        <Button type="link" onClick={() => router.push(`/instructor/student/${record.user_id}`)}>查看进度</Button>
      )
    }
  ];

  const testColumns = [
    { title: '标题', dataIndex: 'title', key: 'title' },
    { 
      title: '类型', 
      dataIndex: 'test_type', 
      key: 'test_type',
      render: (type: string) => (
        <Tag color={type === 'exam' ? 'red' : type === 'quiz' ? 'blue' : 'green'}>
          {type === 'exam' ? '考试' : type === 'quiz' ? '测验' : '作业'}
        </Tag>
      )
    },
    { title: '题目数', dataIndex: 'question_count', key: 'question_count' },
    { title: '总分', dataIndex: 'total_score', key: 'total_score' },
    { title: '时长', dataIndex: 'duration', key: 'duration', render: (d: number) => d ? `${d}分钟` : '不限' },
    {
      title: '操作',
      key: 'action',
      render: (_: unknown, record: Record<string, unknown>) => (
        <Space>
          <Button type="link" onClick={() => router.push(`/instructor/test/${record.id}`)}>详情</Button>
          <Button type="link" onClick={() => router.push(`/instructor/test/${record.id}/results`)}>成绩</Button>
        </Space>
      )
    }
  ];

  return (
    <div style={{ padding: 24 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <div>
          <h1 style={{ fontSize: 24, margin: 0 }}>教练员工作台</h1>
          <p style={{ color: '#666', margin: 0 }}>{cls.name}</p>
        </div>
        <Dropdown menu={{ items: userMenuItems }} placement="bottomRight">
          <Space style={{ cursor: 'pointer' }}>
            <Avatar icon={<UserOutlined />} style={{ backgroundColor: '#1890ff' }} />
            <span>{user.name}</span>
          </Space>
        </Dropdown>
      </div>

      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={6}>
          <Card>
            <Statistic title="学员总数" value={analytics.student_count || 0} prefix={<TeamOutlined />} />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic title="测验总数" value={analytics.test_count || 0} prefix={<FileTextOutlined />} />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic 
              title="平均成绩" 
              value={analytics.avg_score || 0} 
              suffix="分"
              valueStyle={{ color: '#3f8600' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic title="剩余天数" value={analytics.remaining_days || 0} suffix="天" />
          </Card>
        </Col>
      </Row>

      <Row gutter={16}>
        <Col span={16}>
          <Card
            title="测验管理"
            extra={
              <Space>
                <Button onClick={() => router.push('/instructor/test/generate')}>智能组卷</Button>
                <Button type="primary" icon={<PlusOutlined />} onClick={() => router.push('/instructor/test/create')}>
                  发布测验
                </Button>
              </Space>
            }
          >
            <Table columns={testColumns} dataSource={tests} rowKey="id" pagination={{ pageSize: 5 }} />
          </Card>
        </Col>
        <Col span={8}>
          <Card title="快捷入口">
            <Space direction="vertical" style={{ width: '100%' }}>
              <Button block onClick={() => router.push('/instructor/students')}>学员管理</Button>
              <Button block onClick={() => router.push('/instructor/documents')}>文书审批</Button>
              <Button block onClick={() => router.push('/instructor/progress')}>学习进度</Button>
              <Button block onClick={() => router.push('/instructor/scores')}>成绩汇总</Button>
              <Button block onClick={() => router.push('/instructor/analytics')}>统计分析</Button>
            </Space>
          </Card>

          <Card title="班级进度" style={{ marginTop: 16 }}>
            <div style={{ textAlign: 'center' }}>
              <Progress type="circle" percent={analytics.avg_reading_progress || 0} />
              <p style={{ marginTop: 8 }}>平均阅读进度</p>
            </div>
          </Card>
        </Col>
      </Row>

      <Card title="学员列表" style={{ marginTop: 16 }}>
        <Table columns={studentColumns} dataSource={students} rowKey="id" pagination={{ pageSize: 10 }} />
      </Card>
    </div>
  );
}