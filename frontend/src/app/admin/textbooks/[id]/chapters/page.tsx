"use client";

import { useState, useEffect } from 'react';
import { useRouter, useParams } from 'next/navigation';
import {
  Card, Button, message, Space, Tag, Empty, Spin, Tree,
  Switch, Typography, Layout, Input, Badge, Tooltip, Divider,
  Descriptions, Alert, Popconfirm, Modal
} from 'antd';
import {
  ArrowLeftOutlined, SaveOutlined, SearchOutlined, NodeExpandOutlined,
  EyeOutlined, EyeInvisibleOutlined, CheckCircleOutlined,
  UndoOutlined, InfoCircleOutlined, BookOutlined, FileTextOutlined,
  MenuOutlined
} from '@ant-design/icons';
import { http } from '@/lib/http';

const { Title, Text, Paragraph, Link } = Typography;
const { Sider, Content } = Layout;

// 节点类型
interface ChapterNode {
  id: number;
  title: string;
  content?: string;
  type: 'chapter' | 'section';
  is_visible: boolean;
  sort_order: number;
  children?: ChapterNode[];
}

export default function ChapterManagementPage() {
  const router = useRouter();
  const params = useParams();
  const textbookId = params.id as string;
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [treeData, setTreeData] = useState<ChapterNode[]>([]);
  const [flatList, setFlatList] = useState<ChapterNode[]>([]);
  const [textbookName, setTextbookName] = useState('教材');
  const [expandedKeys, setExpandedKeys] = useState<React.Key[]>([]);
  const [selectedKey, setSelectedKey] = useState<React.Key | null>(null);
  const [searchText, setSearchText] = useState('');
  const [originalVisible, setOriginalVisible] = useState<Record<number, boolean>>({});
  const [sidebarWidth, setSidebarWidth] = useState(420);
  const [isResizing, setIsResizing] = useState(false);

  // 统计
  const visibleCount = flatList.filter(p => p.is_visible).length;
  const hiddenCount = flatList.length - visibleCount;
  const changedCount = flatList.filter(p => p.is_visible !== (originalVisible[p.id] ?? true)).length;

  // 选中节点
  const selectedNode = flatList.find(p => String(p.id) === String(selectedKey));

  useEffect(() => {
    fetchData();
  }, [textbookId]);

  // 拉平章节树
  const flattenTree = (nodes: ChapterNode[]): ChapterNode[] => {
    const result: ChapterNode[] = [];
    const walk = (list: ChapterNode[]) => {
      for (const node of list) {
        result.push(node);
        if (node.children?.length) walk(node.children);
      }
    };
    walk(nodes);
    return result;
  };

  // 初始展开前3个顶层章节
  const initExpanded = (nodes: ChapterNode[]) => {
    const keys: React.Key[] = [];
    for (let i = 0; i < Math.min(3, nodes.length); i++) {
      keys.push(String(nodes[i].id));
    }
    return keys;
  };

  const fetchData = async () => {
    setLoading(true);
    try {
      const res = await http.get(`/admin/textbooks/${textbookId}/pages/management`);
      setTextbookName(res.textbook_name || res.data?.textbook_name || '教材');

      let raw: Record<string, unknown>[] = [];
      if (Array.isArray(res.pages)) raw = res.pages;
      else if (Array.isArray(res.data?.pages)) raw = res.data.pages;

      const processNode = (n: Record<string, unknown>): ChapterNode => ({
        id: n.id,
        title: n.title || '(无标题)',
        type: n.type || 'chapter',
        is_visible: n.is_visible ?? true,
        sort_order: n.sort_order || 0,
        content: n.content,
        children: Array.isArray(n.children) ? n.children.map(processNode) : [],
      });

      const nodes = raw.map(processNode);
      const snap: Record<number, boolean> = {};
      const walk = (list: ChapterNode[]) => {
        for (const n of list) {
          snap[n.id] = n.is_visible;
          if (n.children?.length) walk(n.children);
        }
      };
      walk(nodes);

      setTreeData(nodes);
      setFlatList(flattenTree(nodes));
      setOriginalVisible(snap);
      setExpandedKeys(initExpanded(nodes));
    } catch (e) {
      message.error('获取章节数据失败: ' + (e?.message || ''));
    } finally {
      setLoading(false);
    }
  };

  // 切换节点
  const toggleNode = (id: number) => {
    const update = (list: ChapterNode[]): ChapterNode[] =>
      list.map(n =>
        n.id === id ? { ...n, is_visible: !n.is_visible }
        : { ...n, children: n.children ? update(n.children) : [] }
      );
    const newTree = update(treeData);
    setTreeData(newTree);
    setFlatList(flattenTree(newTree));
  };

  // 批量操作（当前可见的）
  const batchSet = (visible: boolean) => {
    const ids = flatList.map(p => p.id);
    const update = (list: ChapterNode[]): ChapterNode[] =>
      list.map(n => ({
        ...n,
        is_visible: ids.includes(n.id) ? visible : n.is_visible,
        children: n.children ? update(n.children) : [],
      }));
    const newTree = update(treeData);
    setTreeData(newTree);
    setFlatList(flattenTree(newTree));
  };

  // 全部操作
  const batchSetAll = (visible: boolean) => {
    const update = (list: ChapterNode[]): ChapterNode[] =>
      list.map(n => ({
        ...n, is_visible: visible,
        children: n.children ? update(n.children) : [],
      }));
    const newTree = update(treeData);
    setTreeData(newTree);
    setFlatList(flattenTree(newTree));
  };

  const handleReset = () => {
    const revert = (list: ChapterNode[]): ChapterNode[] =>
      list.map(n => ({
        ...n,
        is_visible: originalVisible[n.id] ?? true,
        children: n.children ? revert(n.children) : [],
      }));
    const newTree = revert(treeData);
    setTreeData(newTree);
    setFlatList(flattenTree(newTree));
    message.info('已重置');
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      const visibleIds = flatList.filter(p => p.is_visible).map(p => p.id);
      await http.put(`/admin/textbooks/${textbookId}/pages/visibility`, {
        page_ids: visibleIds,
      });
      message.success('保存成功！');
      const snap: Record<number, boolean> = {};
      for (const p of flatList) snap[p.id] = p.is_visible;
      setOriginalVisible(snap);
    } catch (e) {
      message.error('保存失败: ' + (e?.message || ''));
    } finally {
      setSaving(false);
    }
  };

  // 搜索过滤
  const getFilteredTree = (): ChapterNode[] => {
    if (!searchText.trim()) return treeData;
    const kw = searchText.toLowerCase();
    const match = (n: ChapterNode): boolean => {
      if (n.title.toLowerCase().includes(kw) || (n.content || '').toLowerCase().includes(kw)) return true;
      return n.children?.some(match) || false;
    };
    const filter = (list: ChapterNode[]): ChapterNode[] =>
      list.reduce<ChapterNode[]>((acc, n) => {
        if (!match(n)) return acc;
        return [...acc, { ...n, children: n.children ? filter(n.children) : [] }];
      }, []);
    return filter(treeData);
  };

  // 拖拽调整侧边栏宽度
  const startResize = () => setIsResizing(true);
  const stopResize = () => setIsResizing(false);
  useEffect(() => {
    if (!isResizing) return;
    const onMove = (e: MouseEvent) => {
      const w = Math.max(300, Math.min(700, e.clientX - 200));
      setSidebarWidth(w);
    };
    const onUp = () => setIsResizing(false);
    window.addEventListener('mousemove', onMove);
    window.addEventListener('mouseup', onUp);
    return () => { window.removeEventListener('mousemove', onMove); window.removeEventListener('mouseup', onUp); };
  }, [isResizing]);

  // Tree 渲染
  const renderTreeNodes = (data: ChapterNode[]): React.ReactNode[] =>
    data.map(node => ({
      key: String(node.id),
      title: (
        <div key={i} style={{
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          padding: '2px 0', gap: 8,
          opacity: node.is_visible ? 1 : 0.5,
        }}>
          <div style={{ flex: 1, minWidth: 0 }}>
            <Tag color={node.type === 'chapter' ? 'blue' : 'default'} style={{ marginRight: 6, fontSize: 11 }}>
              {node.type === 'chapter' ? '章' : '节'}
            </Tag>
            <Text delete={!node.is_visible} ellipsis={{ tooltip: false }} style={{ fontSize: 13 }}>
              {node.title.split('\n')[0]}
            </Text>
          </div>
          <Switch
            size="small"
            checked={node.is_visible}
            onChange={() => toggleNode(node.id)}
            checkedChildren={<EyeOutlined />}
            unCheckedChildren={<EyeInvisibleOutlined />}
            style={{ flexShrink: 0 }}
          />
        </div>
      ),
      children: node.children?.length ? renderTreeNodes(node.children) : undefined,
    }));

  // 内容摘要（取前200字）
  const getContentPreview = (content?: string): string => {
    if (!content) return '（无正文内容）';
    const clean = content.replace(/\n/g, ' ').replace(/\s+/g, ' ').trim();
    return clean.length > 300 ? clean.slice(0, 300) + '…' : clean;
  };

  if (loading) {
    return (
      <div style={{ padding: 24, textAlign: 'center', marginTop: 100 }}>
        <Spin size="large" />
        <p style={{ marginTop: 16 }}>加载章节数据…</p>
      </div>
    );
  }

  const filteredTree = getFilteredTree();

  return (
    <div style={{ height: '100vh', display: 'flex', flexDirection: 'column', background: '#f0f2f5' }}>
      {/* 顶部导航栏 */}
      <div style={{
        background: '#fff', borderBottom: '1px solid #f0f0f0',
        padding: '12px 20px', display: 'flex', alignItems: 'center', gap: 12,
        flexShrink: 0, zIndex: 10
      }}>
        <Button icon={<ArrowLeftOutlined />} onClick={() => router.push('/admin/textbooks')}>
          返回教材列表
        </Button>
        <Divider type="vertical" style={{ margin: '0 4px' }} />
        <BookOutlined style={{ color: '#1677ff', fontSize: 16 }} />
        <Text strong style={{ fontSize: 15 }}>{textbookName}</Text>
        <Text type="secondary">— 章节可见性管理</Text>
        <div style={{ flex: 1 }} />
        <Space>
          <Badge count={changedCount} style={{ backgroundColor: changedCount > 0 ? '#1677ff' : '#52c41a' }}>
            <Button size="small">已修改</Button>
          </Badge>
          <Button icon={<CheckCircleOutlined />} onClick={() => batchSetAll(true)} size="small">
            全显
          </Button>
          <Button icon={<EyeInvisibleOutlined />} onClick={() => batchSetAll(false)} size="small">
            全隐
          </Button>
          <Button icon={<UndoOutlined />} onClick={handleReset} size="small">
            重置
          </Button>
          <Button
            type="primary"
            icon={<SaveOutlined />}
            loading={saving}
            onClick={handleSave}
            disabled={changedCount === 0}
          >
            保存 ({changedCount})
          </Button>
        </Space>
      </div>

      {/* 双栏主体 */}
      <div style={{ flex: 1, display: 'flex', overflow: 'hidden', position: 'relative' }}>
        {/* 左栏：章节树 */}
        <div style={{
          width: sidebarWidth, background: '#fff', borderRight: '1px solid #f0f0f0',
          display: 'flex', flexDirection: 'column', overflow: 'hidden', flexShrink: 0,
        }}>
          {/* 左栏头部 */}
          <div style={{ padding: '12px 14px 10px', borderBottom: '1px solid #f0f0f0', flexShrink: 0 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
              <Text strong style={{ fontSize: 13 }}>章节列表</Text>
              <Space size={4}>
                <Tag color="green" style={{ margin: 0, fontSize: 11 }}>显示 {visibleCount}</Tag>
                <Tag color="red" style={{ margin: 0, fontSize: 11 }}>隐藏 {hiddenCount}</Tag>
              </Space>
            </div>
            <Input
              prefix={<SearchOutlined style={{ color: '#bfbfbf' }} />}
              placeholder="搜索章节标题或内容…"
              value={searchText}
              onChange={e => setSearchText(e.target.value)}
              allowClear
              size="small"
            />
          </div>

          {/* 章节树 */}
          <div style={{ flex: 1, overflow: 'auto', padding: '8px 4px' }}>
            {filteredTree.length === 0 ? (
              <Empty description="无匹配章节" style={{ marginTop: 40 }} />
            ) : (
              <Tree
                showLine={{ showLeafIcon: false }}
                expandedKeys={expandedKeys}
                onExpand={keys => setExpandedKeys(keys)}
                selectedKeys={selectedKey ? [selectedKey] : []}
                onSelect={keys => setSelectedKey(keys[0] || null)}
                treeData={renderTreeNodes(filteredTree)}
                blockNode
                style={{ background: 'transparent', fontSize: 13 }}
              />
            )}
          </div>
        </div>

        {/* 拖拽分割线 */}
        <div
          onMouseDown={startResize}
          style={{
            width: 5, cursor: 'col-resize', background: 'transparent',
            transition: 'background 0.15s',
            flexShrink: 0,
          }}
          onMouseEnter={e => (e.currentTarget.style.background = '#1677ff')}
          onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
        />

        {/* 右栏：章节详情 */}
        <div style={{ flex: 1, overflow: 'auto', padding: 20 }}>
          {selectedNode ? (
            <div style={{ maxWidth: 900 }}>
              {/* 章节信息卡 */}
              <Card
                size="small"
                title={
                  <Space>
                    <Tag color={selectedNode.type === 'chapter' ? 'blue' : 'default'} style={{ fontSize: 12 }}>
                      {selectedNode.type === 'chapter' ? '章' : '节'}
                    </Tag>
                    <Text strong style={{ fontSize: 15 }}>{selectedNode.title.split('\n')[0]}</Text>
                  </Space>
                }
                extra={
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <Text type="secondary" style={{ fontSize: 12 }}>
                      ID: {selectedNode.id} · 排序: {selectedNode.sort_order}
                    </Text>
                    <Switch
                      checked={selectedNode.is_visible}
                      onChange={() => toggleNode(selectedNode.id)}
                      checkedChildren="显示"
                      unCheckedChildren="隐藏"
                    />
                  </div>
                }
                style={{ marginBottom: 16 }}
              >
                <Descriptions column={2} size="small" style={{ marginBottom: 8 }}>
                  <Descriptions.Item label="章节ID">{selectedNode.id}</Descriptions.Item>
                  <Descriptions.Item label="排序号">{selectedNode.sort_order}</Descriptions.Item>
                  <Descriptions.Item label="类型">
                    <Tag color={selectedNode.type === 'chapter' ? 'blue' : 'default'}>
                      {selectedNode.type === 'chapter' ? '大章节' : '小节'}
                    </Tag>
                  </Descriptions.Item>
                  <Descriptions.Item label="当前状态">
                    {selectedNode.is_visible
                      ? <Tag color="green" icon={<EyeOutlined />}>显示中</Tag>
                      : <Tag color="red" icon={<EyeInvisibleOutlined />}>已隐藏</Tag>
                    }
                  </Descriptions.Item>
                  {selectedNode.children && (
                    <Descriptions.Item label="下级章节">{selectedNode.children.length} 条</Descriptions.Item>
                  )}
                </Descriptions>
                <Alert
                  message={
                    <Text>
                      共 <Text strong>{flatList.filter(p => p.is_visible).length}</Text> 个章节显示，
                      <Text strong> {flatList.filter(p => !p.is_visible).length}</Text> 个章节隐藏
                    </Text>
                  }
                  type="info"
                  showIcon
                  style={{ fontSize: 12 }}
                />
              </Card>

              {/* 内容预览 */}
              <Card
                title={
                  <Space>
                    <FileTextOutlined style={{ color: '#1677ff' }} />
                    <Text strong>内容预览</Text>
                    <Text type="secondary" style={{ fontSize: 12 }}>
                      （仅供预览，正式显示时会自动截断）
                    </Text>
                  </Space>
                }
                size="small"
                style={{ marginBottom: 16 }}
              >
                {selectedNode.content ? (
                  <Paragraph style={{ fontSize: 13, lineHeight: 1.8, marginBottom: 0 }}>
                    {selectedNode.content.split('\n').map((line, i) => {
                      const trimmed = line.trim();
                      if (!trimmed) return null;
                      // 判断是否是标题行
                      if (/^[一二三四五六七八九十\(\（][^\(\（\(\）\)]/.test(trimmed)) {
                        return <div key={i} style={{ marginTop: 12, fontWeight: 600, color: '#262626' }}>{trimmed}</div>;
                      }
                      if (/^\d+[\.、]/.test(trimmed)) {
                        return <div key={i} style={{ marginTop: 6, paddingLeft: 8, color: '#595959' }}>{trimmed}</div>;
                      }
                      return <span key={i}>{trimmed} </span>;
                    })}
                  </Paragraph>
                ) : (
                  <Text type="secondary">（无正文内容）</Text>
                )}
              </Card>

              {/* 下级章节 */}
              {selectedNode.children && selectedNode.children.length > 0 && (
                <Card
                  title={`下级章节（${selectedNode.children.length} 条）`}
                  size="small"
                >
                  {selectedNode.children.map((child, idx) => (
                    <div
                      key={child.id}
                      style={{
                        display: 'flex', alignItems: 'flex-start', gap: 8,
                        padding: '6px 0', borderBottom: idx < selectedNode.children!.length - 1 ? '1px dashed #f0f0f0' : 'none',
                      }}
                    >
                      <span style={{ color: '#bfbfbf', fontSize: 12, minWidth: 20 }}>{idx + 1}.</span>
                      <Switch
                        size="small"
                        checked={child.is_visible}
                        onChange={() => toggleNode(child.id)}
                        checkedChildren={<EyeOutlined />}
                        unCheckedChildren={<EyeInvisibleOutlined />}
                        style={{ marginTop: 2, flexShrink: 0 }}
                      />
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <Text
                          delete={!child.is_visible}
                          ellipsis={{ tooltip: child.title.split('\n')[0] }}
                          style={{ fontSize: 13, display: 'block' }}
                        >
                          {child.title.split('\n')[0]}
                        </Text>
                        {child.content && (
                          <Text type="secondary" style={{ fontSize: 11 }} ellipsis>
                            {child.content.replace(/\n/g, ' ').replace(/\s+/g, ' ').trim().slice(0, 60)}…
                          </Text>
                        )}
                      </div>
                    </div>
                  ))}
                </Card>
              )}

              {/* 底部保存 */}
              <div style={{ marginTop: 16, display: 'flex', justifyContent: 'flex-end' }}>
                <Button
                  type="primary"
                  icon={<SaveOutlined />}
                  size="large"
                  loading={saving}
                  onClick={handleSave}
                  disabled={changedCount === 0}
                >
                  保存设置 ({changedCount} 项)
                </Button>
              </div>
            </div>
          ) : (
            /* 未选中状态 */
            <div style={{
              display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
              height: '60vh', color: '#bfbfbf'
            }}>
              <MenuOutlined style={{ fontSize: 48, marginBottom: 16 }} />
              <Text type="secondary" style={{ fontSize: 15 }}>点击左侧章节树中的任意章节</Text>
              <Text type="secondary" style={{ fontSize: 13 }}>查看章节详情、修改可见性</Text>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
