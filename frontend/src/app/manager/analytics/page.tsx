"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { Card, Row, Col, Statistic, Table, Button, Spin, Progress, Tag, Space, Badge } from "antd";
import { ArrowLeftOutlined, BookOutlined, TeamOutlined, TrophyOutlined, FullscreenOutlined, FullscreenExitOutlined, ReloadOutlined, WarningOutlined, ClockCircleOutlined } from "@ant-design/icons";
import { http } from "@/lib/http";

export default function ManagerAnalyticsPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [overview, setOverview] = useState<any>(null);
  const [readingData, setReadingData] = useState<any[]>([]);
  const [scoresData, setScoresData] = useState<any[]>([]);
  const [tabWarnings, setTabWarnings] = useState<any[]>([]);
  const [fullscreen, setFullscreen] = useState(false);
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date());

  useEffect(() => {
    fetchData();
    // 自动刷新（每60秒）
    const interval = setInterval(fetchData, 60000);
    return () => clearInterval(interval);
  }, []);

  const fetchData = () => {
    setLoading(true);
    Promise.all([
      http.get("/manager/analytics/overview"),
      http.get("/manager/analytics/reading"),
      http.get("/manager/analytics/scores"),
      http.get("/manager/analytics/anti-cheat").then((res: any) => 
        (res.suspicious || []).map((s: any) => ({ 
          name: s.name, 
          count: s.total_switches,
          chapters: s.affected_chapters 
        }))
      ).catch(() => []),
    ])
      .then(([ov, rd, sd, tw]) => {
        setOverview(ov);
        setReadingData(rd.students || []);
        setScoresData(sd.distribution || []);
        setTabWarnings(tw);
        setLastUpdate(new Date());
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  };

  if (loading) return <div style={{ textAlign: "center", padding: 48 }}><Spin size="large" /></div>;

  // CSS 柱状图渲染函数
  const renderBar = (value: number, max: number, color: string) => (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
      <div style={{ flex: 1, height: 20, background: '#f0f0f0', borderRadius: 4, overflow: 'hidden' }}>
        <div style={{ width: `${(value / max) * 100}%`, height: '100%', background: color, transition: 'width 0.5s' }} />
      </div>
      <span style={{ width: 40, textAlign: 'right', fontSize: 13 }}>{value}</span>
    </div>
  );

  // 全屏模式样式
  const containerStyle: React.CSSProperties = fullscreen ? {
    position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
    background: 'linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%)',
    padding: 24, overflow: 'auto', zIndex: 1000, color: '#fff'
  } : { padding: 24, background: '#f5f5f5', minHeight: '100vh' };

  const cardStyle: React.CSSProperties = fullscreen ? {
    background: 'rgba(255,255,255,0.08)', backdropFilter: 'blur(10px)',
    border: '1px solid rgba(255,255,255,0.1)', borderRadius: 12, color: '#fff'
  } : {};

  return (
    <div style={containerStyle}>
      {/* 顶部操作栏 */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <Space>
          {!fullscreen && (
            <Button icon={<ArrowLeftOutlined />} onClick={() => router.push("/manager")}>返回</Button>
          )}
          <h1 style={{ fontSize: fullscreen ? 28 : 20, margin: 0, color: fullscreen ? '#fff' : 'inherit' }}>
            📊 数据大屏{fullscreen && ' · 实时监控'}
          </h1>
        </Space>
        <Space>
          <Tag color="blue"><ClockCircleOutlined /> {lastUpdate.toLocaleTimeString()}</Tag>
          <Button icon={<ReloadOutlined />} onClick={fetchData}>刷新</Button>
          <Button
            icon={fullscreen ? <FullscreenExitOutlined /> : <FullscreenOutlined />}
            onClick={() => setFullscreen(!fullscreen)}
          >
            {fullscreen ? '退出全屏' : '大屏模式'}
          </Button>
        </Space>
      </div>

      {/* 核心指标卡片 */}
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col xs={12} sm={6}>
          <Card style={cardStyle}>
            <Statistic 
              title={<span style={fullscreen ? { color: 'rgba(255,255,255,0.7)' } : {}}>学员总数</span>}
              value={overview?.total_students || 0} 
              prefix={<TeamOutlined />} 
              valueStyle={fullscreen ? { color: '#52c41a' } : {}}
            />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card style={cardStyle}>
            <Statistic 
              title={<span style={fullscreen ? { color: 'rgba(255,255,255,0.7)' } : {}}>完成阅读</span>}
              value={overview?.completed_readings || 0} 
              prefix={<BookOutlined />} 
              valueStyle={fullscreen ? { color: '#1890ff' } : {}}
            />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card style={cardStyle}>
            <Statistic 
              title={<span style={fullscreen ? { color: 'rgba(255,255,255,0.7)' } : {}}>测试总数</span>}
              value={overview?.total_tests || 0} 
              valueStyle={fullscreen ? { color: '#faad14' } : {}}
            />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card style={cardStyle}>
            <Statistic 
              title={<span style={fullscreen ? { color: 'rgba(255,255,255,0.7)' } : {}}>平均成绩</span>}
              value={overview?.avg_score || 0} 
              suffix="分" 
              prefix={<TrophyOutlined />} 
              valueStyle={fullscreen ? { color: '#ff4d4f' } : { color: '#3f8600' }}
            />
          </Card>
        </Col>
      </Row>

      {/* 图表区 */}
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col xs={24} lg={12}>
          <Card title={<span style={fullscreen ? { color: '#fff' } : {}}>📈 阅读进度排行</span>} style={cardStyle}>
            {readingData.length > 0 ? (
              <div style={{ maxHeight: 280, overflow: 'auto' }}>
                {readingData.slice(0, 8).map((r: any, i: number) => (
                  <div key={r.user_id} style={{ marginBottom: 12 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                      <span style={fullscreen ? { color: '#fff' } : {}}>
                        {i < 3 && ['🥇', '🥈', '🥉'][i]} {r.user_name}
                      </span>
                      <Tag color={i < 3 ? 'gold' : 'blue'}>{Math.round((r.progress || 0) * 100)}%</Tag>
                    </div>
                    {renderBar(r.completed_chapters || 0, r.total_chapters || 1, i < 3 ? '#faad14' : '#1890ff')}
                  </div>
                ))}
              </div>
            ) : (
              <div style={{ textAlign: "center", padding: 32, color: fullscreen ? 'rgba(255,255,255,0.5)' : '#999' }}>暂无阅读数据</div>
            )}
          </Card>
        </Col>

        <Col xs={24} lg={12}>
          <Card title={<span style={fullscreen ? { color: '#fff' } : {}}>📊 成绩分布</span>} style={cardStyle}>
            {scoresData.length > 0 ? (
              <div style={{ maxHeight: 280 }}>
                {scoresData.map((s: any) => {
                  const maxCount = Math.max(...scoresData.map((x: any) => x.count || 0), 1);
                  const getColor = (range: string) => {
                    if (range.includes('90') || range.includes('100')) return '#52c41a';
                    if (range.includes('80')) return '#1890ff';
                    if (range.includes('70')) return '#faad14';
                    if (range.includes('60')) return '#fa8c16';
                    return '#ff4d4f';
                  };
                  return (
                    <div key={s.range} style={{ marginBottom: 12 }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                        <span style={fullscreen ? { color: '#fff' } : {}}>{s.range}</span>
                        <Badge count={s.count} style={{ background: getColor(s.range) }} />
                      </div>
                      {renderBar(s.count || 0, maxCount, getColor(s.range))}
                    </div>
                  );
                })}
              </div>
            ) : (
              <div style={{ textAlign: "center", padding: 32, color: fullscreen ? 'rgba(255,255,255,0.5)' : '#999' }}>暂无成绩数据</div>
            )}
          </Card>
        </Col>
      </Row>

      {/* 防作弊监控 */}
      <Row gutter={16}>
        <Col xs={24} lg={12}>
          <Card 
            title={<span style={fullscreen ? { color: '#fff' } : {}}><WarningOutlined style={{ color: '#ff4d4f', marginRight: 8 }} />防作弊监控</span>} 
            style={cardStyle}
          >
            {tabWarnings.length > 0 ? (
              <Table
                dataSource={tabWarnings}
                rowKey="name"
                size="small"
                pagination={false}
                columns={[
                  { title: "学员", dataIndex: "name", render: (v: string) => <span style={fullscreen ? { color: '#fff' } : {}}>{v}</span> },
                  { 
                    title: "切换次数", 
                    dataIndex: "count",
                    render: (v: number) => <Tag color={v >= 5 ? 'red' : v >= 3 ? 'orange' : 'blue'}>{v} 次</Tag>
                  },
                  { 
                    title: "风险", 
                    dataIndex: "count",
                    render: (v: number) => v >= 5 ? <Tag color="red">高风险</Tag> : v >= 3 ? <Tag color="orange">中风险</Tag> : <Tag color="blue">低风险</Tag>
                  },
                ]}
              />
            ) : (
              <div style={{ textAlign: 'center', padding: 24, color: fullscreen ? 'rgba(255,255,255,0.5)' : '#999' }}>
                ✅ 暂无异常行为
              </div>
            )}
          </Card>
        </Col>

        <Col xs={24} lg={12}>
          <Card title={<span style={fullscreen ? { color: '#fff' } : {}}>📋 学员详细进度</span>} style={cardStyle}>
            <Table
              dataSource={readingData.slice(0, 5)}
              rowKey="user_id"
              size="small"
              pagination={false}
              columns={[
                { title: "学员", dataIndex: "user_name", render: (v: string) => <span style={fullscreen ? { color: '#fff' } : {}}>{v}</span> },
                { title: "完成章节", dataIndex: "completed_chapters", render: (v: number, r: any) => `${v || 0}/${r.total_chapters || 0}` },
                { title: "进度", dataIndex: "progress", render: (v: number) => <Progress percent={Math.round((v || 0) * 100)} size="small" /> },
              ]}
            />
          </Card>
        </Col>
      </Row>
    </div>
  );
}
