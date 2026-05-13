"use client";

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Layout, Card, Table, Progress, Tag, Button, Modal, message, Badge, Space } from 'antd';
import { TeamOutlined, ReadOutlined, EditOutlined, CheckCircleOutlined, ClockCircleOutlined, ArrowLeftOutlined } from '@ant-design/icons';
import { http } from '@/lib/http';

const { Content } = Layout;

interface StudentProgress {
  user_id: number;
  name: string;
  progress: {
    total: number;
    completed: number;
    reading_done: number;
    practicing: number;
    waiting_test: number;
    progress_percent: number;
    total_reading_time_minutes: number;
  };
  last_active: string | null;
}

export default function InstructorStudentsPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [students, setStudents] = useState<StudentProgress[]>([]);
  const [selectedStudent, setSelectedStudent] = useState<number | null>(null);
  const [detailVisible, setDetailVisible] = useState(false);
  const [studentDetail, setStudentDetail] = useState<any>(null);
  const [pendingTests, setPendingTests] = useState<any[]>([]);

  useEffect(() => {
    fetchStudents();
    fetchPendingTests();
  }, []);

  const fetchStudents = async () => {
    try {
      const res = await http.get('/instructor/progress');
      setStudents(res.students || []);
    } catch (e) {
      message.error('获取学员列表失败');
    } finally {
      setLoading(false);
    }
  };

  const fetchPendingTests = async () => {
    try {
      const res = await http.get('/instructor/students/pending-tests');
      setPendingTests(res.pending_tests || []);
    } catch (e) {
      console.error(e);
    }
  };

  const handleViewDetail = async (userId: number) => {
    setSelectedStudent(userId);
    try {
      const res = await http.get(`/instructor/students/${userId}/progress`);
      setStudentDetail(res);
      setDetailVisible(true);
    } catch (e) {
      message.error('获取学员详情失败');
    }
  };

  const columns = [
    {
      title: '学员',
      dataIndex: 'name',
      key: 'name',
      render: (name: string, record: StudentProgress) => (
        <Button type="link" onClick={() => handleViewDetail(record.user_id)}>
          {name}
        </Button>
      ),
    },
    {
      title: '进度',
      key: 'progress',
      render: (_: unknown, record: StudentProgress) => (
        <Progress 
          percent={record.progress.progress_percent} 
          size="small"
          status={record.progress.progress_percent === 100 ? 'success' : 'active'}
        />
      ),
    },
    {
      title: '已完成',
      key: 'stats',
      render: (_: unknown, record: StudentProgress) => (
        <div className="text-xs space-y-1">
          <div><CheckCircleOutlined className="text-green-500" /> 已完成: {record.progress.completed}</div>
          <div><ReadOutlined className="text-blue-500" /> 阅读: {record.progress.reading_done}</div>
          <div><EditOutlined className="text-orange-500" /> 练习: {record.progress.practicing}</div>
          <div><ClockCircleOutlined className="text-purple-500" /> 待测验: {record.progress.waiting_test}</div>
        </div>
      ),
    },
    {
      title: '学习时长',
      key: 'time',
      render: (_: unknown, record: StudentProgress) => (
        <span>{record.progress.total_reading_time_minutes} 分钟</span>
      ),
    },
    {
      title: '最近活跃',
      key: 'last_active',
      render: (_: unknown, record: StudentProgress) => (
        <span className="text-gray-500">
          {record.last_active ? new Date(record.last_active).toLocaleString('zh-CN') : '未开始'}
        </span>
      ),
    },
  ];

  return (
    <Layout className="min-h-screen bg-gray-100">
      <Content className="p-6">
        {/* 返回按钮 */}
        <div className="mb-4">
          <Button icon={<ArrowLeftOutlined />} onClick={() => router.push('/instructor')}>
            返回工作台
          </Button>
        </div>

        {/* 待发布测验提醒 */}
        {pendingTests.length > 0 && (
          <Card className="mb-4 border-l-4 border-l-yellow-500">
            <div className="flex items-center gap-2 mb-2">
              <Badge count={pendingTests.length} />
              <span className="font-bold">待发布随堂测验</span>
            </div>
            {pendingTests.map((item, idx) => (
              <div key={idx} className="text-sm py-1 flex items-center justify-between">
                <span>{item.student_name} - {item.chapter_title}</span>
                <Button size="small" type="primary" onClick={() => message.info('请在测验发布页面操作')}>
                  发布测验
                </Button>
              </div>
            ))}
          </Card>
        )}

        <Card title={<><TeamOutlined /> 学员学习进度</>}>
          <Table
            dataSource={students}
            columns={columns}
            rowKey="user_id"
            loading={loading}
            pagination={false}
          />
        </Card>

        {/* 学员详情弹窗 */}
        <Modal
          title="学员学习详情"
          open={detailVisible}
          onCancel={() => setDetailVisible(false)}
          footer={null}
          width={800}
        >
          {studentDetail && (
            <div>
              <div className="mb-4 flex items-center justify-between">
                <span className="font-bold text-lg">{studentDetail.name}</span>
                <Progress 
                  percent={studentDetail.summary.progress_percent}
                  format={(p) => `${p}%`}
                />
              </div>
              
              {studentDetail.chapters.map((ch: Record<string, unknown>) => (
                <div key={ch.id} className="mb-4">
                  <div className="font-medium bg-gray-50 p-2 rounded">{ch.title}</div>
                  <div className="grid grid-cols-4 gap-2 mt-2">
                    {ch.sections.map((sec: Record<string, unknown>) => {
                      const statusColors: Record<string, string> = {
                        locked: 'bg-gray-100',
                        reading: 'bg-blue-100',
                        reading_done: 'bg-yellow-100',
                        practicing: 'bg-orange-100',
                        waiting_test: 'bg-purple-100',
                        completed: 'bg-green-100',
                      };
                      return (
                        <div 
                          key={sec.id}
                          className={`p-2 rounded text-xs ${statusColors[sec.status] || 'bg-gray-100'}`}
                        >
                          <div className="truncate">{sec.title.replace(/^第\d+节 /, '')}</div>
                          <div className="text-gray-500">
                            {sec.status === 'completed' ? '正确' : 
                             sec.status === 'reading_done' ? '阅读' :
                             sec.status === 'practicing' ? '练习' :
                             sec.status === 'waiting_test' ? '等待' : '锁定'}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              ))}
            </div>
          )}
        </Modal>
      </Content>
    </Layout>
  );
}