'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { Card, Row, Col, Progress, Button, List, Tag, Dropdown, Avatar, Space } from 'antd';
import { BookOutlined, FileTextOutlined, TrophyOutlined, UserOutlined, LogoutOutlined, KeyOutlined, StarOutlined, BulbOutlined, AimOutlined, RocketOutlined } from '@ant-design/icons';
import { http } from '@/lib/http';

export default function StudentDashboard() {
  const router = useRouter();
  const [user, setUser] = useState<any>({});
  const [cls, setCls] = useState<any>({});
  const [dashboard, setDashboard] = useState<any>({});
  const [textbooks, setTextbooks] = useState<any[]>([]);
  const [tests, setTests] = useState<any[]>([]);
  const [isMobile, setIsMobile] = useState(false);

  useEffect(() => {
    const m = window.innerWidth < 768;
    setIsMobile(m);
    const handler = () => setIsMobile(window.innerWidth < 768);
    window.addEventListener('resize', handler);
    return () => window.removeEventListener('resize', handler);
  }, []);

  useEffect(() => {
    checkAuth();
    fetchData();
  }, []);

  const checkAuth = async () => {
    const token = localStorage.getItem('token');
    const userStr = localStorage.getItem('user');
    const classStr = localStorage.getItem('class');

    if (!token || !userStr) {
      router.push('/login');
      return;
    }

    const userData = JSON.parse(userStr);
    if (userData.role !== 'student') {
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
    { key: 'profile', icon: <UserOutlined />, label: '个人信息', onClick: () => router.push('/student/profile') },
    { key: 'password', icon: <KeyOutlined />, label: '修改密码', onClick: () => router.push('/student/profile/password') },
    { type: 'divider' as const },
    { key: 'logout', icon: <LogoutOutlined />, label: '退出登录', onClick: handleLogout, danger: true },
  ];

  const fetchData = async () => {
    try {
      const dash = await http.get('/student/dashboard');
      setDashboard(dash);

      const books = await http.get('/student/textbooks');
      setTextbooks(books);

      const t = await http.get('/student/tests');
      setTests(t);

      try {
        const progressRes = await http.get('/student/chapters/my-progress');
        setDashboard((prev) => ({ ...prev, chapter_progress: progressRes }));
      } catch (e) {
        console.error(e);
      }
      // 获取教材阅读进度（用于课程进度圆环）
      try {
        const readingProgress = await http.get('/student/reading/progress');
        setDashboard((prev) => ({ ...prev, reading_progress: readingProgress }));
      } catch (e) {
        console.error(e);
      }
    } catch (e) {
      console.error(e);
    }
  };

  return (
    <div style={{ padding: isMobile ? 12 : 24 }}>
      {/* 顶部导航 */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: isMobile ? 16 : 24,
          flexWrap: 'wrap',
          gap: 8,
        }}
      >
        <div>
          <h1 style={{ fontSize: isMobile ? 20 : 24, margin: 0 }}>欢迎，{user.name}</h1>
          <p style={{ color: '#666', margin: 0, fontSize: isMobile ? 13 : 14 }}>{cls.name}</p>
        </div>
        <Dropdown menu={{ items: userMenuItems }} placement="bottomRight">
          <Space style={{ cursor: 'pointer' }}>
            <Avatar icon={<UserOutlined />} style={{ backgroundColor: '#52c41a' }} />
            {!isMobile && <span>{user.name}</span>}
          </Space>
        </Dropdown>
      </div>

      {/* 统计卡片 — 手机单列，桌面4列 */}
      <Row gutter={[12, 12]} style={{ marginBottom: isMobile ? 16 : 24 }}>
        <Col xs={24} sm={12} md={6}>
          <Card hoverable onClick={() => router.push('/student/chapters')}>
            <div style={{ textAlign: 'center' }}>
              <Progress type="circle" percent={
                dashboard.reading_progress && dashboard.reading_progress.length > 0
                  ? Math.round(dashboard.reading_progress.reduce((sum: number, r: Record<string, unknown>) => sum + r.progress, 0) / dashboard.reading_progress.length)
                  : (dashboard.chapter_progress?.progress_percent || 0)
              } />
              <p style={{ marginTop: 8 }}>课程进度</p>
            </div>
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: isMobile ? 28 : 36, color: '#1890ff' }}>
                {dashboard.chapter_progress?.completed || 0}/72
              </div>
              <p style={{ marginTop: 8 }}>已完成章节</p>
            </div>
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: isMobile ? 28 : 36, color: '#52c41a' }}>
                {dashboard.avg_score || 0}
              </div>
              <p style={{ marginTop: 8 }}>平均成绩</p>
            </div>
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: isMobile ? 28 : 36, color: '#faad14' }}>
                {dashboard.chapter_progress?.total_reading_time_minutes || 0}
              </div>
              <p style={{ marginTop: 8 }}>学习时长(分钟)</p>
            </div>
          </Card>
        </Col>
      </Row>

      {/* 课程学习 + 待完成测验 — 手机单列，桌面双列 */}
      <Row gutter={[12, 12]} style={{ marginBottom: isMobile ? 16 : 0 }}>
        <Col xs={24} sm={24} md={12}>
          <Card
            title="课程学习"
            extra={<Button type="link" onClick={() => router.push('/student/textbooks')}>查看全部教材</Button>}
          >
            <List
              dataSource={textbooks.slice(0, 2)}
              renderItem={(item: Record<string, unknown>) => (
                <List.Item
                  actions={[
                    <Button 
                      type="primary" 
                      key="learn" 
                      onClick={() => {
                        if (item.has_interactive) {
                          router.push(`/student/textbook/${item.id}`);
                        } else {
                          router.push('/student/chapters');
                        }
                      }}
                    >
                      {item.progress > 0 ? '继续学习' : '开始学习'}
                    </Button>,
                  ]}
                >
                  <List.Item.Meta
                    avatar={<BookOutlined style={{ fontSize: 24, color: '#1890ff' }} />}
                    title={item.name}
                    description={
                      item.has_interactive 
                        ? `互动式教材 · 共${item.total_chapters}节课程`
                        : `PDF教材 · 共${item.total_pages}页`
                    }
                  />
                </List.Item>
              )}
            />
          </Card>
        </Col>
        <Col xs={24} sm={24} md={12}>
          <Card
            title="待完成测验"
            extra={<Button type="link" onClick={() => router.push('/student/tests')}>查看全部</Button>}
          >
            <List
              dataSource={tests.filter((t: Record<string, unknown>) => !t.is_completed && t.is_available)}
              renderItem={(item: Record<string, unknown>) => (
                <List.Item
                  actions={[
                    <Button
                      type="primary"
                      size="small"
                      key="start"
                      onClick={() => router.push(`/student/test/${item.id}`)}
                    >
                      开始
                    </Button>,
                  ]}
                >
                  <List.Item.Meta
                    avatar={<FileTextOutlined style={{ fontSize: 24, color: '#faad14' }} />}
                    title={item.title}
                    description={
                      <span>
                        <Tag color="blue">
                          {item.test_type === 'exam' ? '考试' : item.test_type === 'quiz' ? '测验' : '作业'}
                        </Tag>
                        {item.duration && `${item.duration}分钟`}
                      </span>
                    }
                  />
                </List.Item>
              )}
            />
          </Card>
        </Col>
      </Row>

      {/* 快捷入口 — 手机2×2网格，桌面1×4 */}
      <Row gutter={[12, 12]} style={{ marginTop: isMobile ? 16 : 24 }}>
        <Col xs={24}>
          <Card title="快捷入口">
            <Row gutter={[8, 8]}>
              <Col xs={12} sm={6}>
                <Button
                  block
                  size="large"
                  icon={<BookOutlined />}
                  onClick={() => router.push('/student/textbooks')}
                >
                  学习教材
                </Button>
              </Col>
              <Col xs={12} sm={6}>
                <Button
                  block
                  size="large"
                  icon={<FileTextOutlined />}
                  onClick={() => router.push('/student/tests')}
                >
                  我的测验
                </Button>
              </Col>
              <Col xs={12} sm={6}>
                <Button
                  block
                  size="large"
                  icon={<TrophyOutlined />}
                  onClick={() => router.push('/student/scores')}
                >
                  我的成绩
                </Button>
              </Col>
              <Col xs={12} sm={6}>
                <Button
                  block
                  size="large"
                  onClick={() => router.push('/student/wrong-answers')}
                >
                  错题本
                </Button>
              </Col>
              <Col xs={12} sm={6}>
                <Button
                  block
                  size="large"
                  icon={<BulbOutlined />}
                  onClick={() => router.push('/student/review')}
                >
                  智能复习
                </Button>
              </Col>
              <Col xs={12} sm={6}>
                <Button
                  block
                  size="large"
                  icon={<StarOutlined />}
                  onClick={() => router.push('/student/certificate')}
                >
                  结业证书
                </Button>
              </Col>
              <Col xs={12} sm={6}>
                <Button
                  block
                  size="large"
                  icon={<AimOutlined />}
                  onClick={() => router.push('/student/knowledge-map')}
                >
                  知识地图
                </Button>
              </Col>
              <Col xs={12} sm={6}>
                <Button
                  block
                  size="large"
                  icon={<RocketOutlined />}
                  onClick={() => router.push('/student/learning-path')}
                >
                  学习路径
                </Button>
              </Col>
            </Row>
          </Card>
        </Col>
      </Row>
    </div>
  );
}
