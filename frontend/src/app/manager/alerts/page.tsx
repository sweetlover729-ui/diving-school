"use client";

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Card, Table, Tag, Button, Select, Space, Row, Col, message, Spin, Popconfirm, Statistic } from 'antd';
import { ArrowLeftOutlined, BellOutlined, CheckCircleOutlined, ThunderboltOutlined, ExclamationCircleOutlined } from '@ant-design/icons';
import { http } from '@/lib/http';

const severityColors: Record<string, string> = { critical: 'red', warning: 'orange', info: 'blue' };
const typeLabels: Record<string, string> = {
  inactivity: '不活跃', score_drop: '成绩下降', fail_rate: '不及格率', low_progress: '进度极低'
};

export default function AlertsPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [detecting, setDetecting] = useState(false);
  const [alerts, setAlerts] = useState<any[]>([]);
  const [stats, setStats] = useState<any>({});
  const [filter, setFilter] = useState<string>('all');

  useEffect(() => { fetchData(); }, []);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [a, s] = await Promise.all([
        http.get<any[]>('/manager/alerts'),
        http.get<any>('/manager/alerts/stats'),
      ]);
      setAlerts(Array.isArray(a) ? a : []);
      setStats(s || {});
    } catch (_) {} finally { setLoading(false); }
  };

  const runDetection = async () => {
    setDetecting(true);
    try {
      const r = await http.post<{ created: number }>('/manager/alerts/detect', {});
      message.success('检测完成，新增 ' + (r?.created || 0) + ' 条预警');
      fetchData();
    } catch (_) { message.error('检测失败'); }
    finally { setDetecting(false); }
  };

  const markRead = async (id: number) => { await http.post('/manager/alerts/' + id + '/read', {}); fetchData(); };
  const resolveAlert = async (id: number) => { await http.post('/manager/alerts/' + id + '/resolve', {}); fetchData(); };

  const filtered = filter === 'all' ? alerts :
    filter === 'unread' ? alerts.filter((a: any) => !a.is_read) :
    alerts.filter((a: any) => a.severity === filter);

  const columns = [
    { title: '学员', dataIndex: 'user_name', key: 'user_name', width: 100 },
    { title: '类型', dataIndex: 'alert_type', key: 'alert_type', width: 90,
      render: (t: string) => typeLabels[t] || t },
    { title: '详情', dataIndex: 'alert_message', key: 'alert_message', ellipsis: true },
    { title: '严重', dataIndex: 'severity', key: 'severity', width: 70,
      render: (s: string) => <Tag color={severityColors[s] || 'default'}>{s}</Tag> },
    { title: '状态', dataIndex: 'is_read', key: 'is_read', width: 80,
      render: (r: boolean, rec: any) => rec.is_resolved ? <Tag color="green">已解决</Tag> :
        r ? <Tag>已读</Tag> : <Tag color="red">未读</Tag> },
    { title: '时间', dataIndex: 'created_at', key: 'created_at', width: 140,
      render: (t: string) => t ? new Date(t).toLocaleString('zh-CN') : '-' },
    { title: '操作', key: 'actions', width: 140, render: (_: any, rec: any) => (
      <Space size={4}>
        {!rec.is_read && <Button size="small" onClick={() => markRead(rec.id)}>标记已读</Button>}
        {!rec.is_resolved && (
          <Popconfirm title="确认已处理此预警？" onConfirm={() => resolveAlert(rec.id)}>
            <Button size="small" type="primary" danger>解决</Button>
          </Popconfirm>
        )}
      </Space>
    )},
  ];

  if (loading) return <div style={{ textAlign: 'center', padding: 100 }}><Spin size="large" /></div>;

  return (
    <div style={{ padding: 24 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <Button icon={<ArrowLeftOutlined />} onClick={() => router.push('/manager')}>返回</Button>
        <Button type="primary" icon={<ThunderboltOutlined />} loading={detecting} onClick={runDetection}>
          执行检测
        </Button>
      </div>

      <Row gutter={16} style={{ marginBottom: 16 }}>
        {[
          { title: '未读预警', value: stats.unread || 0, icon: <BellOutlined />, color: '#ff4d4f' },
          { title: '严重预警', value: stats.critical || 0, icon: <ExclamationCircleOutlined />, color: '#cf1322' },
          { title: '总计', value: stats.total || alerts.length, icon: <CheckCircleOutlined />, color: '#1890ff' },
        ].map((item) => (
          <Col span={8} key={item.title}>
            <Card size="small"><Statistic title={item.title} value={item.value} valueStyle={{ color: item.color }} prefix={item.icon} /></Card>
          </Col>
        ))}
      </Row>

      <Card title="预警列表" extra={
        <Select value={filter} onChange={setFilter} style={{ width: 130 }}>
          <Select.Option value="all">全部</Select.Option>
          <Select.Option value="unread">未读</Select.Option>
          <Select.Option value="critical">严重</Select.Option>
          <Select.Option value="warning">警告</Select.Option>
        </Select>
      }>
        <Table rowKey="id" columns={columns} dataSource={filtered} pagination={{ pageSize: 15 }} size="small" scroll={{ x: 750 }} />
      </Card>
    </div>
  );
}
