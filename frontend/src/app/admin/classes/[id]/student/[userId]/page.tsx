"use client";

import { useState, useEffect } from 'react';
import { useRouter, useParams } from 'next/navigation';
import { Card, Progress, Table, Button, Space, Statistic, Row, Col, message, Tabs, Tag, Collapse } from 'antd';
import { ArrowLeftOutlined, BookOutlined, CheckCircleOutlined, ClockCircleOutlined, FileTextOutlined } from '@ant-design/icons';
import { http } from '@/lib/http';

const { TabPane } = Tabs;
const { Panel } = Collapse;

// 学习状态映射
const STATUS_MAP: Record<string, { color: string; text: string }> = {
  locked: { color: 'default', text: '未解锁' },
  reading: { color: 'processing', text: '阅读中' },
  reading_done: { color: 'blue', text: '待练习' },
  practicing: { color: 'warning', text: '练习中' },
  waiting_test: { color: 'purple', text: '待测验' },
  completed: { color: 'success', text: '已完成' },
};

// 文书状态映射
const DOC_STATUS_MAP: Record<string, { color: string; text: string }> = {
  pending: { color: 'orange', text: '待填写' },
  submitted: { color: 'blue', text: '待审核' },
  approved: { color: 'green', text: '已通过' },
  rejected: { color: 'red', text: '已驳回' },
};

export default function StudentLearningDetailPage() {
  const router = useRouter();
  const params = useParams();
  const classId = params.id as string;
  const userId = params.userId as string;
  
  const [loading, setLoading] = useState(true);
  const [studentInfo, setStudentInfo] = useState<any>(null);
  const [summary, setSummary] = useState<any>(null);
  const [textbooksProgress, setTextbooksProgress] = useState<any[]>([]);
  const [documentsStatus, setDocumentsStatus] = useState<any[]>([]);
  const [activeTab, setActiveTab] = useState('0');
  const [activeMainTab, setActiveMainTab] = useState('learning');

  useEffect(() => {
    fetchStudentDetail();
  }, [classId, userId]);

  const fetchStudentDetail = async () => {
    try {
      setLoading(true);
      const data = await http.get(`/admin/classes/${classId}/student/${userId}/progress`);
      setStudentInfo(data.student);
      setSummary(data.summary);
      setTextbooksProgress(data.textbooks_progress || []);
      setDocumentsStatus(data.documents_status || []);
    } catch (e) {
      message.error('获取学员学习情况失败');
    } finally {
      setLoading(false);
    }
  };

  const chapterColumns = [
    { title: '章节', dataIndex: 'title', key: 'title', width: '40%' },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: '20%',
      render: (status: string) => {
        const s = STATUS_MAP[status] || { color: 'default', text: status };
        return <Tag color={s.color}>{s.text}</Tag>;
      }
    },
    {
      title: '阅读时长',
      key: 'time',
      width: '20%',
      render: (_: unknown, record: Record<string, unknown>) => `${Math.round((record.total_reading_time || 0) / 60)}分钟`
    },
    {
      title: '完成时间',
      dataIndex: 'completed_at',
      key: 'completed_at',
      width: '20%',
      render: (t: string) => t ? new Date(t).toLocaleDateString('zh-CN') : '-'
    },
  ];

  // 文书表格列
  const documentColumns = [
    { title: '文书名称', dataIndex: 'template_name', key: 'template_name', width: '30%' },
    {
      title: '类型',
      dataIndex: 'doc_type',
      key: 'doc_type',
      width: '15%',
    },
    {
      title: '是否必填',
      dataIndex: 'is_required',
      key: 'is_required',
      width: '12%',
      render: (required: boolean) => (
        <Tag color={required ? 'red' : 'default'}>{required ? '是' : '否'}</Tag>
      )
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: '15%',
      render: (status: string) => {
        const s = DOC_STATUS_MAP[status] || { color: 'default', text: status };
        return <Tag color={s.color}>{s.text}</Tag>;
      }
    },
    {
      title: '提交时间',
      dataIndex: 'submitted_at',
      key: 'submitted_at',
      width: '18%',
      render: (t: string) => t ? new Date(t).toLocaleString('zh-CN') : '-'
    },
    {
      title: '操作',
      key: 'action',
      width: '10%',
      render: (_: unknown, record: Record<string, unknown>) => (
        record.response_id ? (
          <Button
            type="link"
            size="small"
            onClick={() => window.open(`/admin/document-responses/${record.response_id}/pdf`, '_blank')}
          >
            下载PDF
          </Button>
        ) : (
          <span style={{ color: '#999' }}>-</span>
        )
      ),
    },
  ];

  return (
    <div style={{ padding: 24 }}>
      <div style={{ marginBottom: 16 }}>
        <Button icon={<ArrowLeftOutlined />} onClick={() => router.push(`/admin/classes/${classId}`)}>
          返回班级详情
        </Button>
      </div>
      
      <h1 style={{ fontSize: 24, marginBottom: 24 }}>学员学习情况</h1>

      {/* 学员基本信息 */}
      {studentInfo && (
        <Card style={{ marginBottom: 24 }}>
          <Row gutter={24}>
            <Col span={6}>
              <Statistic title="学员姓名" value={studentInfo.name} />
            </Col>
            <Col span={6}>
              <Statistic title="身份证" value={studentInfo.id_card?.slice(-4)} prefix="****" />
            </Col>
            <Col span={6}>
              <Statistic title="电话" value={studentInfo.phone || '-'} />
            </Col>
            <Col span={6}>
              <Statistic title="关联教材" value={summary?.total_textbooks || 0} suffix="本" />
            </Col>
          </Row>
        </Card>
      )}

      {/* 总体统计 */}
      {summary && (
        <Row gutter={16} style={{ marginBottom: 24 }}>
          <Col span={6}>
            <Card>
              <Progress type="circle" percent={summary.progress_percent || 0} />
              <div style={{ textAlign: 'center', marginTop: 8 }}>总进度</div>
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic 
                title="已完成章节" 
                value={summary.completed || 0} 
                suffix={`/ ${summary.total_chapters || 0}`}
                prefix={<CheckCircleOutlined />}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic 
                title="学习时长" 
                value={Math.round(summary.total_reading_time_minutes || 0)} 
                suffix="分钟"
                prefix={<ClockCircleOutlined />}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic 
                title="待测验" 
                value={summary.waiting_test || 0}
                prefix={<BookOutlined />}
              />
            </Card>
          </Col>
        </Row>
      )}

      {/* 主标签页：学习情况 / 文书签署 */}
      <Tabs activeKey={activeMainTab} onChange={setActiveMainTab} type="card" style={{ marginBottom: 24 }}>
        <TabPane
          tab={
            <span>
              <BookOutlined />
              学习情况
              {summary && summary.total_textbooks > 0 && (
                <Tag color="blue" style={{ marginLeft: 8 }}>{summary.progress_percent}%</Tag>
              )}
            </span>
          }
          key="learning"
        >
          <Card title="教材学习详情" loading={loading}>
            {textbooksProgress.length === 0 ? (
              <div style={{ textAlign: 'center', padding: 40, color: '#999' }}>
                暂无教材学习数据
              </div>
            ) : textbooksProgress.length === 1 ? (
              // 单教材直接展示
              <div>
                <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <h3 style={{ margin: 0 }}>{textbooksProgress[0].textbook_name}</h3>
                  <Space>
                    <Tag color="blue">{textbooksProgress[0].total_chapters} 章节</Tag>
                    <Tag color="green">已完成 {textbooksProgress[0].completed}</Tag>
                    <Tag color="orange">待测验 {textbooksProgress[0].waiting_test}</Tag>
                  </Space>
                </div>
                <Progress
                  percent={textbooksProgress[0].progress_percent}
                  status={textbooksProgress[0].progress_percent === 100 ? 'success' : 'active'}
                  style={{ marginBottom: 16 }}
                />
                <Table
                  columns={chapterColumns}
                  dataSource={textbooksProgress[0].chapters}
                  rowKey="id"
                  size="small"
                  pagination={{ pageSize: 10 }}
                />
              </div>
            ) : (
              // 多教材使用标签页
              <Tabs activeKey={activeTab} onChange={setActiveTab} type="card">
                {textbooksProgress.map((tb, index) => (
                  <TabPane
                    tab={
                      <span key={index}>
                        {tb.textbook_name}
                        <Tag color={tb.progress_percent === 100 ? 'success' : 'processing'} style={{ marginLeft: 8 }}>
                          {tb.progress_percent}%
                        </Tag>
                      </span>
                    }
                    key={String(index)}
                  >
                    <div style={{ marginBottom: 16 }}>
                      <Row gutter={16}>
                        <Col span={8}>
                          <Card size="small">
                            <Statistic title="总章节" value={tb.total_chapters} />
                          </Card>
                        </Col>
                        <Col span={8}>
                          <Card size="small">
                            <Statistic title="已完成" value={tb.completed} valueStyle={{ color: '#52c41a' }} />
                          </Card>
                        </Col>
                        <Col span={8}>
                          <Card size="small">
                            <Statistic title="学习时长" value={tb.total_reading_time_minutes} suffix="分钟" />
                          </Card>
                        </Col>
                      </Row>
                    </div>
                    <Progress
                      percent={tb.progress_percent}
                      status={tb.progress_percent === 100 ? 'success' : 'active'}
                      style={{ marginBottom: 16 }}
                    />
                    <Table
                      columns={chapterColumns}
                      dataSource={tb.chapters}
                      rowKey="id"
                      size="small"
                      pagination={{ pageSize: 10 }}
                    />
                  </TabPane>
                ))}
              </Tabs>
            )}
          </Card>
        </TabPane>

        <TabPane
          tab={
            <span>
              <FileTextOutlined />
              文书签署
              {summary && summary.total_documents > 0 && (
                <Tag color={summary.documents_approved === summary.total_documents ? 'success' : 'orange'} style={{ marginLeft: 8 }}>
                  {summary.documents_approved}/{summary.total_documents}
                </Tag>
              )}
            </span>
          }
          key="documents"
        >
          <Card title="文书签署状态" loading={loading}>
            {documentsStatus.length === 0 ? (
              <div style={{ textAlign: 'center', padding: 40, color: '#999' }}>
                暂无文书模板数据
              </div>
            ) : (
              <div>
                <Row gutter={16} style={{ marginBottom: 16 }}>
                  <Col span={6}>
                    <Card size="small">
                      <Statistic
                        title="总文书数"
                        value={summary?.total_documents || 0}
                      />
                    </Card>
                  </Col>
                  <Col span={6}>
                    <Card size="small">
                      <Statistic
                        title="已通过"
                        value={summary?.documents_approved || 0}
                        valueStyle={{ color: '#52c41a' }}
                      />
                    </Card>
                  </Col>
                  <Col span={6}>
                    <Card size="small">
                      <Statistic
                        title="待处理"
                        value={summary?.documents_pending || 0}
                        valueStyle={{ color: '#faad14' }}
                      />
                    </Card>
                  </Col>
                  <Col span={6}>
                    <Card size="small">
                      <Statistic
                        title="已驳回"
                        value={summary?.documents_rejected || 0}
                        valueStyle={{ color: '#ff4d4f' }}
                      />
                    </Card>
                  </Col>
                </Row>

                <Table
                  columns={documentColumns}
                  dataSource={documentsStatus}
                  rowKey="template_id"
                  size="small"
                  pagination={false}
                />
              </div>
            )}
          </Card>
        </TabPane>
      </Tabs>
    </div>
  );
}
