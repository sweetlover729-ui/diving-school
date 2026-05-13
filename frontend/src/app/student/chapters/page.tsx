"use client";

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Layout, Progress, Card, Button, Tag, Space, message, Dropdown, Avatar, Input, Drawer, Modal, Tooltip } from 'antd';
import { BookOutlined, ReadOutlined, EditOutlined, CheckCircleOutlined, LockOutlined, ClockCircleOutlined, UserOutlined, LogoutOutlined, KeyOutlined, ArrowLeftOutlined, HomeOutlined, ThunderboltOutlined, SearchOutlined, BookOutlined as BookmarkIcon, FileTextOutlined, DeleteOutlined, SaveOutlined } from '@ant-design/icons';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeRaw from 'rehype-raw';
import { http } from '@/lib/http';

const { Sider, Content, Header } = Layout;

interface Section {
  id: number;
  title: string;
  status: string;
}

interface Chapter {
  id: number;
  title: string;
  sections: Section[];
}

interface ProgressInfo {
  total_sections: number;
  completed: number;
  reading_done: number;
  practicing: number;
  waiting_test: number;
  self_test_completed: number;
  progress_percent: number;
  total_reading_time_minutes: number;
}

export default function StudentChaptersPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [chapters, setChapters] = useState<Chapter[]>([]);
  const [progress, setProgress] = useState<ProgressInfo | null>(null);
  const [currentSection, setCurrentSection] = useState<number | null>(null);
  const [sectionContent, setSectionContent] = useState<Record<string, unknown> | null>(null);
  const [contentLoading, setContentLoading] = useState(false);
  const [currentUser, setCurrentUser] = useState<Record<string, unknown> | null>(null);

  // 学习工具状态
  const [searchVisible, setSearchVisible] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<any[]>([]);
  const [notesVisible, setNotesVisible] = useState(false);
  const [noteContent, setNoteContent] = useState('');
  const [savedNotes, setSavedNotes] = useState<any[]>([]);
  const [isBookmarked, setIsBookmarked] = useState(false);

  const statusMap: Record<string, { color: string; text: string; icon: React.ReactNode }> = {
    locked: { color: 'default', text: '未解锁', icon: <LockOutlined /> },
    reading: { color: 'processing', text: '阅读中', icon: <ReadOutlined /> },
    reading_done: { color: 'blue', text: '待练习', icon: <EditOutlined /> },
    practicing: { color: 'warning', text: '练习中', icon: <EditOutlined /> },
    practice_done: { color: 'orange', text: '待测验', icon: <ClockCircleOutlined /> },
    waiting_test: { color: 'blue', text: '待测验(可跳过)', icon: <ClockCircleOutlined /> },
    completed: { color: 'success', text: '已完成', icon: <CheckCircleOutlined /> },
  };

  useEffect(() => {
    checkAuth();
    fetchChapters();
    fetchProgress();
  }, []);

  const checkAuth = () => {
    const token = localStorage.getItem('token');
    const user = localStorage.getItem('user');
    if (!token || !user) { router.push('/login'); return; }
    const userData = JSON.parse(user);
    if (userData.role !== 'student') { router.push('/login'); } else { setCurrentUser(userData); }
  };

  const handleLogout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    router.push('/login');
  };

  const userMenuItems = [
    { key: 'home', icon: <HomeOutlined />, label: '返回首页', onClick: () => router.push('/student') },
    { key: 'profile', icon: <UserOutlined />, label: '个人信息', onClick: () => router.push('/student/profile') },
    { key: 'password', icon: <KeyOutlined />, label: '修改密码', onClick: () => router.push('/student/profile/password') },
    { type: 'divider' as const },
    { key: 'logout', icon: <LogoutOutlined />, label: '退出登录', onClick: handleLogout, danger: true },
  ];

  const fetchChapters = async () => {
    try {
      const res = await http.get('/student/chapters');
      setChapters(res);
    } catch (e) { message.error('获取章节失败'); } finally { setLoading(false); }
  };

  const fetchProgress = async () => {
    try {
      const res = await http.get('/student/chapters/my-progress');
      setProgress(res);
    } catch (e) { console.error(e); }
  };

  const handleSectionClick = async (sectionId: number, status: string) => {
    if (status === 'locked') { message.warning('请先完成上一小节'); return; }
    setContentLoading(true);
    try {
      await http.post(`/student/chapters/${sectionId}/start-reading`);
      const res = await http.get(`/student/chapters/${sectionId}`);
      setSectionContent(res);
      setCurrentSection(sectionId);
    } catch (e) {
      const err = e as Error;
      message.error(err.message || '获取章节内容失败');
    } finally { setContentLoading(false); }
  };

  const handleFinishReading = async () => {
    if (!currentSection) return;
    try {
      await http.post(`/student/chapters/${currentSection}/finish-reading`);
      message.success('阅读完成，可以开始练习');
      fetchChapters();
      fetchProgress();
    } catch (e) { message.error((e as Error).message || '操作失败'); }
  };

  const handleGoToExercises = () => {
    if (currentSection) router.push(`/student/exercises/${currentSection}`);
  };

  const handleSelfTest = () => {
    if (currentSection) router.push(`/student/exercises/${currentSection}?self_test=1`);
  };

  // ═══ 搜索 ═══
  const handleSearch = async () => {
    if (!searchQuery.trim()) return;
    try {
      const res = await http.get(`/student/chapters/search?q=${encodeURIComponent(searchQuery)}`);
      setSearchResults(res);
    } catch { message.error('搜索失败'); }
  };

  // ═══ 笔记 ═══
  const fetchNotes = async () => {
    try {
      const res = await http.get('/student/chapters/notes');
      setSavedNotes(res);
    } catch { console.error('获取笔记失败'); }
  };

  const saveNote = async () => {
    if (!currentSection || !noteContent.trim()) return;
    try {
      await http.post('/student/chapters/notes', { chapter_id: currentSection, content: noteContent });
      message.success('笔记已保存');
      fetchNotes();
    } catch { message.error('保存失败'); }
  };

  const deleteNote = async (id: number) => {
    try {
      await http.delete(`/student/chapters/notes/${id}`);
      message.success('已删除');
      fetchNotes();
    } catch { message.error('删除失败'); }
  };

  // ═══ 书签 ═══
  const checkBookmark = async () => {
    if (!currentSection) return;
    try {
      const res = await http.get('/student/chapters/bookmarks');
      setIsBookmarked(res.some((b: any) => b.chapter_id === currentSection));
    } catch { console.error('检查书签失败'); }
  };

  const toggleBookmark = async () => {
    if (!currentSection) return;
    try {
      if (isBookmarked) {
        const res = await http.get('/student/chapters/bookmarks');
        const bm = res.find((b: any) => b.chapter_id === currentSection);
        if (bm) await http.delete(`/student/chapters/bookmarks/${bm.id}`);
        setIsBookmarked(false);
        message.success('已取消收藏');
      } else {
        await http.post('/student/chapters/bookmarks', { chapter_id: currentSection });
        setIsBookmarked(true);
        message.success('已收藏');
      }
    } catch { message.error('操作失败'); }
  };

  useEffect(() => {
    fetchNotes();
  }, []);

  useEffect(() => {
    if (currentSection) {
      checkBookmark();
      const existing = savedNotes.find((n: any) => n.chapter_id === currentSection);
      if (existing) setNoteContent(existing.content || '');
      else setNoteContent('');
    }
  }, [currentSection]);

  // Markdown 渲染组件
  const markdownComponents = {
    // 多媒体组件（rehype-raw 渲染原始 HTML）
    video: ({ src, ...props }: React.DetailedHTMLProps<React.VideoHTMLAttributes<HTMLVideoElement>, HTMLVideoElement>) => (
      <div style={{ margin: '16px 0', textAlign: 'center' }}>
        <video controls style={{ maxWidth: '100%', borderRadius: 8, boxShadow: '0 2px 8px rgba(0,0,0,0.1)' }} {...props}>
          <source src={src} />
          您的浏览器不支持视频播放
        </video>
      </div>
    ),
    img: ({ src, alt, ...props }: React.ImgHTMLAttributes<HTMLImageElement>) => (
      <div style={{ margin: '14px 0', textAlign: 'center' }}>
        <img 
          src={src} 
          alt={alt || ''} 
          style={{ maxWidth: '100%', maxHeight: 500, borderRadius: 6, boxShadow: '0 2px 6px rgba(0,0,0,0.08)' }}
          loading="lazy"
          {...props}
        />
        {alt && <p style={{ fontSize: 12, color: '#999', marginTop: 4, fontStyle: 'italic' }}>{alt}</p>}
      </div>
    ),
    h1: ({ children }: { children: React.ReactNode }) => <h1 style={{ fontSize: 22, fontWeight: 700, color: '#1a1a2e', borderBottom: '2px solid #1890ff', paddingBottom: 8, marginTop: 24 }}>{children}</h1>,
    h2: ({ children }: { children: React.ReactNode }) => <h2 style={{ fontSize: 19, fontWeight: 600, color: '#1890ff', marginTop: 20 }}>{children}</h2>,
    h3: ({ children }: { children: React.ReactNode }) => <h3 style={{ fontSize: 16, fontWeight: 600, color: '#333', marginTop: 16 }}>{children}</h3>,
    p: ({ children }: { children: React.ReactNode }) => <p style={{ fontSize: 15, lineHeight: 2, color: '#333', textIndent: '2em', margin: '8px 0' }}>{children}</p>,
    ul: ({ children }: { children: React.ReactNode }) => <ul style={{ paddingLeft: 24, margin: '8px 0' }}>{children}</ul>,
    ol: ({ children }: { children: React.ReactNode }) => <ol style={{ paddingLeft: 24, margin: '8px 0' }}>{children}</ol>,
    li: ({ children }: { children: React.ReactNode }) => <li style={{ fontSize: 14, lineHeight: 2 }}>{children}</li>,
    strong: ({ children }: { children: React.ReactNode }) => <strong style={{ color: '#cf1322', fontWeight: 700 }}>{children}</strong>,
    em: ({ children }: { children: React.ReactNode }) => <em style={{ color: '#1890ff', fontStyle: 'italic' }}>{children}</em>,
    blockquote: ({ children }: { children: React.ReactNode }) => <blockquote style={{ borderLeft: '4px solid #1890ff', padding: '8px 16px', background: '#f0f7ff', margin: '12px 0', color: '#444' }}>{children}</blockquote>,
    code: ({ children, className }: { children: React.ReactNode; className?: string }) => {
      const isInline = !className;
      return isInline
        ? <code style={{ background: '#fff7e6', padding: '2px 6px', borderRadius: 4, fontSize: 13, color: '#d4380d' }}>{children}</code>
        : <pre style={{ background: '#1a1a2e', color: '#52c41a', padding: '16px', borderRadius: 8, overflow: 'auto', fontSize: 13, lineHeight: 1.6 }}><code>{children}</code></pre>;
    },
    table: ({ children }: { children: React.ReactNode }) => <div style={{ overflowX: 'auto', margin: '12px 0' }}><table style={{ width: '100%', borderCollapse: 'collapse' }}>{children}</table></div>,
    th: ({ children }: { children: React.ReactNode }) => <th style={{ border: '1px solid #e8e8e8', padding: '8px 12px', background: '#fafafa', fontWeight: 600, textAlign: 'left' }}>{children}</th>,
    td: ({ children }: { children: React.ReactNode }) => <td style={{ border: '1px solid #e8e8e8', padding: '8px 12px' }}>{children}</td>,
  };

  const totalSections = progress?.total_sections || 0;

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Header style={{ background: '#fff', padding: '0 24px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid #f0f0f0' }}>
        <Space>
          <Button icon={<ArrowLeftOutlined />} onClick={() => router.push('/student')}>返回</Button>
          <span style={{ fontSize: 18, fontWeight: 'bold', marginLeft: 16 }}>课程学习</span>
        </Space>
        <Space>
          <Button icon={<SearchOutlined />} onClick={() => setSearchVisible(true)}>搜索</Button>
          <Button icon={<FileTextOutlined />} onClick={() => { fetchNotes(); setNotesVisible(true); }}>笔记</Button>
          {currentUser && (
            <Dropdown menu={{ items: userMenuItems }} placement="bottomRight">
              <Space style={{ cursor: 'pointer' }}>
                <Avatar icon={<UserOutlined />} style={{ backgroundColor: '#52c41a' }} />
                <span>{(currentUser as Record<string, string>).name}</span>
              </Space>
            </Dropdown>
          )}
        </Space>
      </Header>

      <Layout>
        <Sider width={320} theme="light" style={{ borderRight: '1px solid #f0f0f0' }}>
          <div style={{ padding: 16, borderBottom: '1px solid #f0f0f0' }}>
            {progress && (
              <div>
                <Progress percent={progress.progress_percent} status={progress.progress_percent === 100 ? 'success' : 'active'} />
                <div style={{ fontSize: 12, color: '#999', marginTop: 8, display: 'flex', justifyContent: 'space-between' }}>
                  <span>已完成 {progress.completed}/{totalSections} 节</span>
                  <span>学习 {progress.total_reading_time_minutes} 分钟</span>
                </div>
                {progress.self_test_completed > 0 && (
                  <div style={{ fontSize: 11, color: '#52c41a', marginTop: 4 }}>
                    <ThunderboltOutlined /> {progress.self_test_completed} 节已自测通过
                  </div>
                )}
              </div>
            )}
          </div>
          
          <div style={{ padding: 8, overflow: 'auto', maxHeight: 'calc(100vh - 200px)' }}>
            {loading ? (
              <div style={{ textAlign: 'center', padding: 20 }}>加载中...</div>
            ) : chapters.map((chapter) => (
              <div key={chapter.id} style={{ marginBottom: 8 }}>
                <div style={{ fontWeight: 500, padding: '4px 8px', background: '#fafafa', borderRadius: 4 }}>
                  {chapter.title}
                </div>
                <div style={{ paddingLeft: 8, marginTop: 4 }}>
                  {chapter.sections.map((section) => {
                    const statusInfo = statusMap[section.status] || statusMap.locked;
                    const isActive = currentSection === section.id;
                    return (
                      <div
                        key={section.id}
                        onClick={() => handleSectionClick(section.id, section.status)}
                        style={{
                          padding: '4px 8px', fontSize: 13,
                          cursor: section.status === 'locked' ? 'not-allowed' : 'pointer',
                          borderRadius: 4, display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                          background: isActive ? '#e6f7ff' : undefined,
                          border: isActive ? '1px solid #1890ff' : undefined,
                          opacity: section.status === 'locked' ? 0.5 : 1,
                        }}
                      >
                        <span style={{ display: 'flex', alignItems: 'center', gap: 4, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                          {statusInfo.icon}
                          {section.title.replace(/^第\d+节 /, '')}
                        </span>
                        <Tag color={statusInfo.color} style={{ fontSize: 10, marginLeft: 4 }}>{statusInfo.text}</Tag>
                      </div>
                    );
                  })}
                </div>
              </div>
            ))}
          </div>
        </Sider>

        <Content style={{ padding: 24, background: '#fff' }}>
          {contentLoading ? (
            <div style={{ textAlign: 'center', padding: 80 }}>加载中...</div>
          ) : sectionContent ? (
            <div>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
                <h1 style={{ fontSize: 20, fontWeight: 'bold', margin: 0 }}>{(sectionContent as Record<string, string>).title}</h1>
                <Space>
                  <Tooltip title={isBookmarked ? '取消收藏' : '添加到书签'}>
                    <Button icon={<BookmarkIcon />} danger={isBookmarked} type={isBookmarked ? 'primary' : 'default'}
                      onClick={toggleBookmark} style={isBookmarked ? { background: '#ff4d4f', borderColor: '#ff4d4f' } : {}}>
                      {isBookmarked ? '已收藏' : '收藏'}
                    </Button>
                  </Tooltip>
                  <Tag color="blue">阅读模式</Tag>
                  <Button icon={<EditOutlined />} onClick={handleGoToExercises}>正式练习</Button>
                  <Button icon={<ThunderboltOutlined />} type="primary" ghost onClick={handleSelfTest}>快速自测</Button>
                </Space>
              </div>
              
              <Card style={{ marginBottom: 16 }}>
                <div style={{ padding: '8px 0', maxWidth: 800 }}>
                  <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeRaw]} components={markdownComponents}>
                    {((sectionContent as Record<string, string>).content || '暂无内容')}
                  </ReactMarkdown>
                </div>
              </Card>

              <div style={{ textAlign: 'center', marginTop: 16 }}>
                <Space>
                  <Button type="primary" size="large" onClick={handleFinishReading}>
                    ✓ 完成本节学习
                  </Button>
                  <Button size="large" onClick={handleSelfTest}>
                    <ThunderboltOutlined /> 直接自测通关
                  </Button>
                </Space>
                {/* 笔记输入区 */}
                <Card size="small" title="📝 本节笔记" style={{ marginTop: 16, textAlign: 'left' }}>
                  <Input.TextArea
                    rows={3}
                    value={noteContent}
                    onChange={e => setNoteContent(e.target.value)}
                    placeholder="记录你的想法、重点、疑问..."
                  />
                  <Space style={{ marginTop: 8 }}>
                    <Button icon={<SaveOutlined />} type="primary" size="small" onClick={saveNote}>
                      保存笔记
                    </Button>
                    {savedNotes.filter((n: any) => n.chapter_id === currentSection).length > 0 && (
                      <Tag color="green">已保存 {savedNotes.filter((n: any) => n.chapter_id === currentSection).length} 条笔记</Tag>
                    )}
                  </Space>
                </Card>
              </div>
            </div>
          ) : (
            <div style={{ textAlign: 'center', padding: 80, color: '#999' }}>
              <BookOutlined style={{ fontSize: 48, color: '#d9d9d9' }} />
              <p style={{ marginTop: 16 }}>请从左侧选择章节开始学习</p>
            </div>
          )}
        </Content>
      </Layout>

      {/* 搜索抽屉 */}
      <Drawer
        title="🔍 搜索课程内容"
        open={searchVisible}
        onClose={() => { setSearchVisible(false); setSearchResults([]); setSearchQuery(''); }}
        width={450}
      >
        <Space.Compact style={{ width: '100%', marginBottom: 16 }}>
          <Input
            placeholder="输入关键词搜索..."
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
            onPressEnter={handleSearch}
          />
          <Button type="primary" icon={<SearchOutlined />} onClick={handleSearch}>搜索</Button>
        </Space.Compact>
        {searchResults.length > 0 && (
          <div>
            {searchResults.map((r: any, i: number) => (
              <Card
                key={i}
                size="small"
                style={{ marginBottom: 10 }}
                hoverable
                onClick={() => {
                  setSearchVisible(false);
                  handleSectionClick(r.id, '');
                }}
                title={<span style={{ fontSize: 13 }}>{r.title}</span>}
              >
                <p style={{ fontSize: 12, color: '#666', margin: 0, maxHeight: 60, overflow: 'hidden', lineHeight: 1.6 }}>
                  {r.snippet}
                </p>
              </Card>
            ))}
          </div>
        )}
        {searchQuery && searchResults.length === 0 && (
          <div style={{ textAlign: 'center', padding: 30, color: '#999' }}>未找到相关结果</div>
        )}
      </Drawer>

      {/* 笔记抽屉 */}
      <Drawer
        title="📝 我的笔记"
        open={notesVisible}
        onClose={() => setNotesVisible(false)}
        width={420}
      >
        {savedNotes.length === 0 ? (
          <div style={{ textAlign: 'center', padding: 40, color: '#999' }}>
            暂无笔记，在阅读时写下你的想法吧
          </div>
        ) : savedNotes.map((n: any, i: number) => (
          <Card
            key={i}
            size="small"
            style={{ marginBottom: 10 }}
            extra={
              <Button size="small" danger icon={<DeleteOutlined />} onClick={() => deleteNote(n.id)} />
            }
            title={<span style={{ fontSize: 12, color: '#999' }}>第{n.chapter_id}节 · {n.updated_at?.slice(0, 10)}</span>}
          >
            <p style={{ fontSize: 13, color: '#333', margin: 0, whiteSpace: 'pre-wrap', lineHeight: 1.8 }}>{n.content}</p>
          </Card>
        ))}
      </Drawer>
    </Layout>
  );
}
