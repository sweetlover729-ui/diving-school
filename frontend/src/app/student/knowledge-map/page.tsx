"use client";

import { useState, useEffect, useMemo } from 'react';
import { useRouter } from 'next/navigation';
import { Card, Tag, Button, Progress, Spin, Empty, Tooltip, Segmented } from 'antd';
import { ArrowLeftOutlined, CheckCircleFilled, PlayCircleFilled, LockFilled, WarningFilled, NodeIndexOutlined } from '@ant-design/icons';
import { http } from '@/lib/http';

interface ChapterNode {
  chapter_id: number;
  title: string;
  status: string;
  level: number;
  parent_id: number | null;
  has_exercises: boolean;
  textbook_name: string;
}

export default function KnowledgeMapPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [chapters, setChapters] = useState<ChapterNode[]>([]);
  const [viewMode, setViewMode] = useState<string>('tree');
  const [expanded, setExpanded] = useState<Set<number>>(new Set());

  useEffect(() => {
    fetchChapters();
  }, []);

  const fetchChapters = async () => {
    try {
      const data = await http.get<{ tree: ChapterNode[] }>('/student/chapters');
      if (data && data.tree) {
        setChapters(data.tree);
        setExpanded(new Set(data.tree.filter((c: ChapterNode) => !c.parent_id).map((c: ChapterNode) => c.chapter_id)));
      }
    } catch (e) {
      console.error('Failed loading knowledge map', e);
      try {
        const list = await http.get<any[]>('/student/chapters');
        if (Array.isArray(list)) {
          setChapters(list);
        }
      } catch (_) {}
    } finally {
      setLoading(false);
    }
  };

  const statusConfig: Record<string, { color: string; icon: React.ReactNode; label: string }> = {
    completed: { color: '#52c41a', icon: <CheckCircleFilled />, label: '已完成' },
    reading: { color: '#1890ff', icon: <PlayCircleFilled />, label: '学习中' },
    reading_done: { color: '#13c2c2', icon: <PlayCircleFilled />, label: '已阅读' },
    practicing: { color: '#fa8c16', icon: <PlayCircleFilled />, label: '练习中' },
    practice_done: { color: '#722ed1', icon: <CheckCircleFilled />, label: '练习完成' },
    waiting_test: { color: '#eb2f96', icon: <WarningFilled />, label: '待测验' },
    locked: { color: '#d9d9d9', icon: <LockFilled />, label: '未解锁' },
  };

  const getStatus = (status: string) => statusConfig[status] || statusConfig.locked;

  const progressStats = useMemo(() => {
    if (!chapters.length) return { completed: 0, total: 0, percent: 0 };
    const done = chapters.filter(c =>
      c.status === 'completed' || c.status === 'waiting_test'
    ).length;
    return {
      completed: done,
      total: chapters.length,
      percent: Math.round(done / chapters.length * 100)
    };
  }, [chapters]);

  const toggleExpand = (id: number) => {
    setExpanded(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const gotoChapter = (id: number) => {
    router.push('/student/chapters/' + id);
  };

  const renderTree = (parentId: number | null = null, level: number = 0): React.ReactNode[] => {
    const children = chapters.filter(c => c.parent_id === parentId);
    return children.map(ch => {
      const st = getStatus(ch.status);
      const isExpanded = expanded.has(ch.chapter_id);
      const hasChildren = chapters.some(c => c.parent_id === ch.chapter_id);

      return (
        <div key={ch.chapter_id} style={{ marginLeft: level * 24, marginBottom: 4 }}>
          <div
            onClick={() => gotoChapter(ch.chapter_id)}
            style={{
              display: 'flex', alignItems: 'center', gap: 8,
              padding: '8px 12px', borderRadius: 8,
              background: st.color === '#d9d9d9' ? '#fafafa' : '#f6ffed',
              border: '1px solid ' + (st.color === '#d9d9d9' ? '#f0f0f0' : '#b7eb8f'),
              cursor: 'pointer', transition: 'all 0.2s',
            }}
            onMouseEnter={e => { e.currentTarget.style.boxShadow = '0 2px 8px rgba(0,0,0,0.1)'; }}
            onMouseLeave={e => { e.currentTarget.style.boxShadow = 'none'; }}
          >
            {hasChildren && (
              <span onClick={e => { e.stopPropagation(); toggleExpand(ch.chapter_id); }}
                style={{ cursor: 'pointer', fontSize: 12 }}>
                {isExpanded ? '▼' : '▶'}
              </span>
            )}
            {!hasChildren && <span style={{ width: 12 }} />}
            <span style={{ color: st.color, fontSize: 16 }}>{st.icon}</span>
            <span style={{ flex: 1 }}>{ch.title}</span>
            <Tag color={st.color === '#d9d9d9' ? 'default' : st.color} style={{ margin: 0 }}>
              {st.label}
            </Tag>
            {ch.has_exercises && (
              <Tooltip title="含课后练习">
                <NodeIndexOutlined style={{ color: '#722ed1' }} />
              </Tooltip>
            )}
          </div>
          {hasChildren && isExpanded && renderTree(ch.chapter_id, level + 1)}
        </div>
      );
    });
  };

  const renderMatrix = () => {
    const textbooks = new Map<string, ChapterNode[]>();
    chapters.forEach(ch => {
      const key = ch.textbook_name || '默认教材';
      if (!textbooks.has(key)) textbooks.set(key, []);
      textbooks.get(key)!.push(ch);
    });

    return Array.from(textbooks.entries()).map(([name, chs]) => (
      <div key={name} style={{ marginBottom: 24 }}>
        <h3 style={{ marginBottom: 12, color: '#1F4E79' }}>{name}</h3>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
          {chs.map(ch => {
            const st = getStatus(ch.status);
            return (
              <Tooltip key={ch.chapter_id} title={ch.title + ' - ' + st.label}>
                <div
                  onClick={() => gotoChapter(ch.chapter_id)}
                  style={{
                    width: 100, padding: '12px 8px', borderRadius: 8,
                    textAlign: 'center', cursor: 'pointer',
                    background: st.color === '#d9d9d9' ? '#fafafa' : st.color + '10',
                    border: '2px solid ' + st.color,
                  }}
                >
                  <div style={{ fontSize: 24, color: st.color }}>{st.icon}</div>
                  <div style={{ fontSize: 11, marginTop: 4, wordBreak: 'break-all' }}>{ch.title.slice(0, 12)}</div>
                </div>
              </Tooltip>
            );
          })}
        </div>
      </div>
    ));
  };

  if (loading) return <div style={{ textAlign: 'center', padding: 100 }}><Spin size="large" /></div>;

  return (
    <div style={{ padding: 24, maxWidth: 900, margin: '0 auto' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <Button icon={<ArrowLeftOutlined />} onClick={() => router.push('/student')}>返回</Button>
        <Segmented
          value={viewMode}
          onChange={v => setViewMode(v as string)}
          options={[
            { label: '树形', value: 'tree' },
            { label: '矩阵', value: 'matrix' },
          ]}
        />
      </div>

      <Card title="学习知识地图" style={{ marginBottom: 16 }}>
        <div style={{ marginBottom: 16 }}>
          <Progress percent={progressStats.percent} strokeColor="#52c41a" />
        </div>

        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 16 }}>
          {Object.entries(statusConfig).slice(0, 6).map(([key, cfg]) => (
            <Tag key={key} color={cfg.color} icon={cfg.icon as React.ReactNode}>
              {cfg.label}
            </Tag>
          ))}
        </div>

        {chapters.length === 0 ? (
          <Empty description="暂无学习内容" />
        ) : viewMode === 'tree' ? (
          renderTree()
        ) : (
          renderMatrix()
        )}
      </Card>
    </div>
  );
}
