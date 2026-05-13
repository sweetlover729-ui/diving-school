'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { Card, Row, Col, Statistic, Table, Button, Progress, Dropdown, Avatar, Space } from 'antd';
import { TeamOutlined, TrophyOutlined, DownloadOutlined, UserOutlined, LogoutOutlined, KeyOutlined } from '@ant-design/icons';
import { http } from '@/lib/http';

export default function ManagerDashboard() {
  const router = useRouter();
  const [user, setUser] = useState<any>({});
  const [cls, setCls] = useState<any>({});
  const [analytics, setAnalytics] = useState<any>({});
  const [progress, setProgress] = useState<any[]>([]);
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

  const checkAuth = () => {
    const token = localStorage.getItem('token');
    const userStr = localStorage.getItem('user');
    const classStr = localStorage.getItem('class');

    if (!token || !userStr) {
      router.push('/login');
      return;
    }

    const userData = JSON.parse(userStr);
    if (userData.role !== 'manager') {
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
    { key: 'profile', icon: <UserOutlined />, label: '个人信息', onClick: () => router.push('/manager/profile') },
    { key: 'password', icon: <KeyOutlined />, label: '修改密码', onClick: () => router.push('/manager/profile/password') },
    { type: 'divider' as const },
    { key: 'logout', icon: <LogoutOutlined />, label: '退出登录', onClick: handleLogout, danger: true },
  ];

  const fetchData = async () => {
    try {
      const a = await http.get('/manager/analytics/overview');
      setAnalytics(a);

      const p = await http.get('/manager/progress');
      setProgress(p);
    } catch (e) {
      console.error(e);
    }
  };

  const columns = [
    { title: '姓名', dataIndex: 'name', key: 'name', width: 100, fixed: 'left' as const },
    {
      title: '阅读进度',
      dataIndex: 'reading_progress',
      key: 'reading_progress',
      width: 180,
      render: (p: number) => <Progress percent={p} size="small" />,
    },
    {
      title: '测验完成',
      dataIndex: 'tests_completed',
      key: 'tests_completed',
      width: 120,
      render: (_: unknown, record: Record<string, unknown>) => `${record.tests_completed}/${record.tests_total}`,
    },
    {
      title: '平均成绩',
      dataIndex: 'avg_score',
      key: 'avg_score',
      width: 100,
      render: (s: number) => (
        <span style={{ color: s >= 60 ? '#52c41a' : '#ff4d4f' }}>{s}分</span>
      ),
    },
    {
      title: '操作',
      key: 'action',
      width: 80,
      fixed: 'right' as const,
      render: (_: unknown, record: Record<string, unknown>) => (
        <Button type="link" onClick={() => router.push(`/manager/student/${record.user_id}`)}>
          详情
        </Button>
      ),
    },
  ];

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
          <h1 style={{ fontSize: isMobile ? 20 : 24, margin: 0 }}>管理干部查看</h1>
          <p style={{ color: '#666', margin: 0, fontSize: isMobile ? 13 : 14 }}>{cls.name}</p>
        </div>
        <Dropdown menu={{ items: userMenuItems }} placement="bottomRight">
          <Space style={{ cursor: 'pointer' }}>
            <Avatar icon={<UserOutlined />} style={{ backgroundColor: '#722ed1' }} />
            {!isMobile && <span>{user.name}</span>}
          </Space>
        </Dropdown>
      </div>

      {/* 统计卡片 — 手机单列，桌面4列 */}
      <Row gutter={[12, 12]} style={{ marginBottom: isMobile ? 16 : 24 }}>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic title="学员总数" value={analytics.student_count || 0} prefix={<TeamOutlined />} />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic title="测验总数" value={analytics.test_count || 0} />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="平均成绩"
              value={analytics.avg_score || 0}
              suffix="分"
              valueStyle={{ color: '#3f8600' }}
              prefix={<TrophyOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic title="剩余天数" value={analytics.remaining_days || 0} suffix="天" />
          </Card>
        </Col>
      </Row>

      {/* 表格 + 右侧面板 — 手机单列堆叠，桌面双列 */}
      <Row gutter={[12, 12]}>
        <Col xs={24} md={16}>
          <Card title="学员学习进度">
            <Table
              columns={columns}
              dataSource={progress}
              rowKey="user_id"
              pagination={{ pageSize: 10 }}
              scroll={{ x: 600 }}
              size={isMobile ? 'small' : 'middle'}
            />
          </Card>
        </Col>
        <Col xs={24} md={8}>
          <Card title="导出报表">
            <Button
              block
              icon={<DownloadOutlined />}
              onClick={() => handleExport('students')}
              style={{ marginBottom: 8 }}
            >
              导出学员名单
            </Button>
            <Button
              block
              icon={<DownloadOutlined />}
              onClick={() => handleExport('scores')}
              style={{ marginBottom: 8 }}
            >
              导出成绩表
            </Button>
            <Button block icon={<DownloadOutlined />} onClick={() => handleExport('report')}>
              导出培训报告
            </Button>
          </Card>

          <Card title="快捷入口" style={{ marginTop: isMobile ? 12 : 16 }}>
            <Button
              block
              onClick={() => router.push('/manager/students')}
              style={{ marginBottom: 8 }}
            >
              学员列表
            </Button>
            <Button
              block
              onClick={() => router.push('/manager/scores')}
              style={{ marginBottom: 8 }}
            >
              成绩汇总
            </Button>
            <Button block onClick={() => router.push('/manager/analytics')}>
              统计分析
            </Button>
            <Button
              block
              onClick={() => router.push('/manager/alerts')}
              style={{ marginTop: 8 }}
            >
              预警面板
            </Button>
          </Card>
        </Col>
      </Row>
    </div>
  );
}

// 将JSON数组转为CSV并触发浏览器下载
function downloadCSV(data: Record<string, unknown>[], filename: string, columns?: { title: string; dataIndex: string }[]) {
  if (!data || data.length === 0) {
    alert('暂无数据可导出');
    return;
  }
  const headers = columns || Object.keys(data[0]);
  const csvRows = [
    headers.map((h: Record<string, unknown>) => (typeof h === 'string' ? h : h.title)).join(','),
    ...data.map((row: Record<string, unknown>) =>
      headers.map((h: Record<string, unknown>) => {
        const key = typeof h === 'string' ? h : h.dataIndex;
        let val = row[key] ?? '';
        // 身份证号脱敏
        if (key === 'id_card' && String(val).length > 10) {
          val = String(val).slice(0, 6) + '****' + String(val).slice(-4);
        }
        // 逗号引号处理
        if (String(val).includes(',') || String(val).includes('"')) {
          val = '"' + String(val).replace(/"/g, '""') + '"';
        }
        return val;
      }).join(',')
    ),
  ];
  const blob = new Blob(['\ufeff' + csvRows.join('\n')], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = `${filename}_${new Date().toISOString().slice(0, 10)}.csv`;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

async function handleExport(type: string) {
  try {
    const classId = cls.id;
    if (!classId) {
      alert('未找到班级信息');
      return;
    }
    if (type === 'report') {
      // 导出培训报告：汇总班级信息
      const [membersRes, analyticsRes] = await Promise.all([
        http.get(`/admin/classes/${classId}/members`),
        http.get(`/admin/classes/${classId}/analytics`),
      ]);

      const report = [
        { 项目: '班级名称', 内容: cls.name || '' },
        { 项目: '导出时间', 内容: new Date().toLocaleString() },
        { 项目: '学员总数', 内容: membersRes?.length || 0 },
        { 项目: '平均成绩', 内容: analyticsRes.avg_score || 0 },
      ];
      downloadCSV(report, '培训报告');
      return;
    }

    const res = await http.get(`/admin/classes/${classId}/members`);
    let rows: Record<string, unknown>[] = [];
    let filename = '';

    if (type === 'students') {
      rows = res || [];
      filename = '学员名单';
    } else if (type === 'scores') {
      rows = res || [];
      filename = '成绩表';
    }

    if (rows.length === 0) {
      alert('暂无数据可导出');
      return;
    }
    downloadCSV(rows, filename);
  } catch (e) {
    alert('导出失败：' + (e.message || '未知错误'));
  }
}
