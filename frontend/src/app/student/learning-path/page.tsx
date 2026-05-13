"use client";

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Card, Button, Tag, Spin, message, Descriptions, Alert, Space, Result } from 'antd';
import { ArrowLeftOutlined, RocketOutlined, ThunderboltOutlined, AimOutlined, ReloadOutlined } from '@ant-design/icons';
import { http } from '@/lib/http';

const pathLabels: Record<string, { color: string; label: string; icon: React.ReactNode; desc: string }> = {
  fast: { color: '#52c41a', label: '快速通道', icon: <RocketOutlined />, desc: '成绩优异，可跳过部分基础章节' },
  normal: { color: '#1890ff', label: '常规路径', icon: <AimOutlined />, desc: '按标准教学计划顺序学习' },
  reinforcement: { color: '#fa8c16', label: '强化通道', icon: <ThunderboltOutlined />, desc: '基础薄弱，需要更多练习和复习' },
};

export default function LearningPathPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [pathData, setPathData] = useState<any>(null);

  useEffect(() => { fetchPath(); }, []);

  const fetchPath = async () => {
    setLoading(true);
    try {
      const data = await http.get('/student/chapters/learning-path');
      setPathData(data);
    } catch (_) { message.error('加载失败'); }
    finally { setLoading(false); }
  };

  const reassess = async () => {
    try {
      await http.post('/student/chapters/learning-path/reassess', {});
      fetchPath();
      message.success('已重新评估');
    } catch (_) { message.error('重新评估失败'); }
  };

  if (loading) return <div style={{ textAlign: 'center', padding: 100 }}><Spin size="large" /></div>;
  if (!pathData) return <Result status="warning" title="暂无学习路径数据" />;

  const config = pathLabels[pathData.path_type] || pathLabels.normal;

  return (
    <div style={{ padding: 24, maxWidth: 700, margin: '0 auto' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
        <Button icon={<ArrowLeftOutlined />} onClick={() => router.push('/student')}>返回</Button>
        <Button icon={<ReloadOutlined />} onClick={reassess}>重新评估</Button>
      </div>

      <Alert
        type={pathData.path_type === 'fast' ? 'success' : pathData.path_type === 'reinforcement' ? 'warning' : 'info'}
        message={
          <span style={{ fontSize: 18 }}>
            {config.icon} {config.label} — {pathData.path_type === 'fast' ? '快速通过' : pathData.path_type === 'reinforcement' ? '夯实基础' : '循序渐进'}
          </span>
        }
        description={config.desc}
        showIcon={false}
        style={{ marginBottom: 16 }}
      />

      <Card title="路径详情">
        <Descriptions column={1} size="small">
          <Descriptions.Item label="当前路径">
            <Tag color={config.color}>{config.label}</Tag>
          </Descriptions.Item>
          <Descriptions.Item label="分配原因">{pathData.assigned_reason || '-'}</Descriptions.Item>
          <Descriptions.Item label="当前阶段">
            第 {pathData.current_stage !== undefined ? pathData.current_stage + 1 : 1} 阶段
          </Descriptions.Item>
          {pathData.fast_track_skipped && pathData.fast_track_skipped.length > 0 && (
            <Descriptions.Item label="已跳过章节">
              <Space wrap>{pathData.fast_track_skipped.map((s: string) => <Tag key={s}>{s}</Tag>)}</Space>
            </Descriptions.Item>
          )}
        </Descriptions>
      </Card>

      <Card title="路径说明" style={{ marginTop: 16 }}>
        {pathData.path_type === 'fast' && (
          <div>
            <p>✅ 您的平均成绩在 90 分以上，已为您开启快速通道。</p>
            <p>📌 可以跳过已掌握的基础章节，直接进入高级内容。</p>
            <p>⚠️ 跳过的章节仍可随时回头复习。</p>
          </div>
        )}
        {pathData.path_type === 'normal' && (
          <div>
            <p>📚 您正在按照标准教学计划学习。</p>
            <p>📌 完成当前章节的阅读+练习后，自动解锁下一章。</p>
            <p>💡 保持当前学习节奏即可顺利结业。</p>
          </div>
        )}
        {pathData.path_type === 'reinforcement' && (
          <div>
            <p>🔧 检测到您的基础需要巩固，已为您配置强化通道。</p>
            <p>📌 每章节需完成附加练习和复习测试才能进入下一章。</p>
            <p>💡 别灰心！扎实的基础是成为优秀潜水员的关键。</p>
          </div>
        )}
      </Card>
    </div>
  );
}
