"use client";

import { useState, useEffect } from 'react';
import { useRouter, useParams } from 'next/navigation';
import { Layout, Progress, Card, Button, Tag, message, Dropdown, Avatar, Space } from 'antd';
import { BookOutlined, ReadOutlined, EditOutlined, CheckCircleOutlined, LockOutlined, ClockCircleOutlined, ArrowLeftOutlined, UserOutlined } from '@ant-design/icons';
import { http } from '@/lib/http';

const { Sider, Content, Header } = Layout;

export default function AdminStudentChaptersPreviewPage() {
  const router = useRouter();
  const params = useParams();
  const studentId = params.id as string;
  
  const [loading, setLoading] = useState(true);
  const [chapters, setChapters] = useState<any[]>([]);
  const [progress, setProgress] = useState<any>(null);
  const [currentSection, setCurrentSection] = useState<number | null>(null);
  const [sectionContent, setSectionContent] = useState<any>(null);
  const [studentInfo, setStudentInfo] = useState<any>(null);

  const statusMap: Record<string, { color: string; text: string }> = {
    locked: { color: 'default', text: '未解锁' },
    reading: { color: 'processing', text: '阅读中' },
    reading_done: { color: 'blue', text: '待练习' },
    practicing: { color: 'warning', text: '练习中' },
    practice_done: { color: 'orange', text: '待测验' },
    waiting_test: { color: 'purple', text: '待发布' },
    completed: { color: 'success', text: '已完成' },
  };

  useEffect(() => {
    fetchData();
  }, [studentId]);

  const fetchData = async () => {
    try {
      const data = await http.get(`/admin/student-preview/${studentId}/chapters`);
      setChapters(data.chapters || []);
      setProgress(data.progress);
      setStudentInfo(data.student);
    } catch (e) {
      message.error('获取数据失败');
    } finally {
      setLoading(false);
    }
  };

  const handleSectionClick = async (sectionId: number, status: string) => {
    if (status === 'locked') {
      message.warning('该章节未解锁');
      return;
    }

    try {
      const res = await http.get(`/admin/student-preview/${studentId}/chapters/${sectionId}`);
      setSectionContent(res);
      setCurrentSection(sectionId);
    } catch (e) {
      message.error(e.message || '获取章节内容失败');
    }
  };

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Header style={{ background: '#fff', padding: '0 24px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid #f0f0f0' }}>
        <Space>
          <Button icon={<ArrowLeftOutlined />} onClick={() => router.push('/admin/student-preview')}>返回</Button>
          <span style={{ fontSize: 18, fontWeight: 'bold', marginLeft: 16 }}>
            学员学习预览 {studentInfo && `- ${studentInfo.name}`}
          </span>
        </Space>
        <Tag color="orange">管理员预览模式</Tag>
      </Header>

      <Layout>
        <Sider width={320} theme="light" style={{ borderRight: '1px solid #f0f0f0' }}>
          <div style={{ padding: 16, borderBottom: '1px solid #f0f0f0' }}>
            {progress && (
              <div>
                <Progress percent={progress.progress_percent || 0} />
                <div style={{ fontSize: 12, color: '#999', marginTop: 8, display: 'flex', justifyContent: 'space-between' }}>
                  <span>已完成 {progress.completed || 0}/72 节</span>
                  <span>学习 {progress.total_reading_time_minutes || 0} 分钟</span>
                </div>
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
                  {chapter.sections?.map((section: Record<string, unknown>) => {
                    const statusInfo = statusMap[section.status] || statusMap.locked;
                    const isActive = currentSection === section.id;
                    return (
                      <div
                        key={section.id}
                        onClick={() => handleSectionClick(section.id, section.status)}
                        style={{
                          padding: '4px 8px',
                          fontSize: 13,
                          cursor: 'pointer',
                          borderRadius: 4,
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'space-between',
                          background: isActive ? '#e6f7ff' : undefined,
                          border: isActive ? '1px solid #1890ff' : undefined,
                        }}
                      >
                        <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                          {section.title}
                        </span>
                        <Tag color={statusInfo.color} style={{ fontSize: 10, marginLeft: 4 }}>
                          {statusInfo.text}
                        </Tag>
                      </div>
                    );
                  })}
                </div>
              </div>
            ))}
          </div>
        </Sider>

        <Content style={{ padding: 24, background: '#fff' }}>
          {sectionContent ? (
            <div>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
                <h1 style={{ fontSize: 20, fontWeight: 'bold', margin: 0 }}>{sectionContent.title}</h1>
                <Tag color="blue">阅读模式</Tag>
              </div>
              
              <Card style={{ marginBottom: 16 }}>
                <div style={{ fontSize: 15, lineHeight: 1.8, whiteSpace: 'pre-wrap' }}>
                  {sectionContent.content || '暂无内容'}
                </div>
              </Card>
            </div>
          ) : (
            <div style={{ textAlign: 'center', padding: 80, color: '#999' }}>
              <BookOutlined style={{ fontSize: 48 }} />
              <p style={{ marginTop: 16 }}>请从左侧选择章节开始预览</p>
            </div>
          )}
        </Content>
      </Layout>
    </Layout>
  );
}