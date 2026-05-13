"use client";

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Card, Table, Button, Tag, Space, message, Modal, Descriptions, Tabs, Empty } from 'antd';
import { CheckOutlined, CloseOutlined, EyeOutlined, ReloadOutlined, ArrowLeftOutlined } from '@ant-design/icons';
import { http } from '@/lib/http';

const { TabPane } = Tabs;

// 状态映射
const STATUS_MAP: Record<string, { label: string; color: string }> = {
  pending: { label: '待填写', color: 'default' },
  submitted: { label: '待审核', color: 'orange' },
  approved: { label: '已通过', color: 'green' },
  rejected: { label: '已驳回', color: 'red' },
};

// 文书类型映射
const DOC_TYPE_MAP: Record<string, string> = {
  health: '健康声明',
  waiver: '免责协议',
  agreement: '同意书',
  questionnaire: '问卷调查',
};

export default function InstructorDocumentReviewPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [responses, setResponses] = useState<any[]>([]);
  const [activeTab, setActiveTab] = useState('submitted');
  const [detailModalVisible, setDetailModalVisible] = useState(false);
  const [selectedResponse, setSelectedResponse] = useState<any>(null);
  const [processing, setProcessing] = useState(false);
  const [rejectModalVisible, setRejectModalVisible] = useState(false);
  const [rejectReason, setRejectReason] = useState('');

  useEffect(() => {
    fetchResponses();
  }, [activeTab]);

  const fetchResponses = async () => {
    try {
      setLoading(true);
      const data = await http.get(`/admin/document-responses?status=${activeTab}`);
      setResponses(data || []);
    } catch (e) {
      message.error('获取文书列表失败：' + (e.message || '未知错误'));
    } finally {
      setLoading(false);
    }
  };

  const handleViewDetail = async (record: Record<string, unknown>) => {
    try {
      const data = await http.get(`/admin/document-responses/${record.id}`);
      setSelectedResponse(data);
      setDetailModalVisible(true);
    } catch (e) {
      message.error('获取详情失败');
    }
  };

  const handleApprove = async (id: number) => {
    Modal.confirm({
      title: '确认通过',
      content: '确定批准该文书吗？',
      okText: '通过',
      okType: 'primary',
      cancelText: '取消',
      onOk: async () => {
        try {
          setProcessing(true);
          await http.post(`/admin/document-responses/${id}/approve`);
          message.success('审批通过');
          fetchResponses();
        } catch (e) {
          message.error(e.message || '审批失败');
        } finally {
          setProcessing(false);
        }
      }
    });
  };

  const handleReject = async (id: number) => {
    if (!rejectReason.trim()) {
      message.error('请输入驳回理由');
      return;
    }
    try {
      setProcessing(true);
      await http.post(`/admin/document-responses/${id}/reject`, { reason: rejectReason });
      message.success('已驳回');
      setRejectModalVisible(false);
      setRejectReason('');
      fetchResponses();
    } catch (e) {
      message.error(e.message || '驳回失败');
    } finally {
      setProcessing(false);
    }
  };

  const columns = [
    {
      title: '学员',
      key: 'student',
      render: (_: unknown, record: Record<string, unknown>) => (
        <div>
          <div style={{ fontWeight: 500 }}>{record.student_name}</div>
          <div style={{ fontSize: 12, color: '#999' }}>{record.class_name || '无班级'}</div>
        </div>
      )
    },
    {
      title: '文书名称',
      key: 'template',
      render: (_: unknown, record: Record<string, unknown>) => (
        <div>
          <div>{record.template_name}</div>
          <Tag>{DOC_TYPE_MAP[record.doc_type] || record.doc_type}</Tag>
        </div>
      )
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status: string) => {
        const config = STATUS_MAP[status] || { label: status, color: 'default' };
        return <Tag color={config.color}>{config.label}</Tag>;
      }
    },
    {
      title: '提交时间',
      dataIndex: 'submitted_at',
      key: 'submitted_at',
      width: 180,
      render: (time: string) => time ? new Date(time).toLocaleString('zh-CN') : '-'
    },
    {
      title: '操作',
      key: 'action',
      width: 200,
      render: (_: unknown, record: Record<string, unknown>) => (
        <Space>
          <Button
            type="link"
            icon={<EyeOutlined />}
            onClick={() => handleViewDetail(record)}
          >
            查看
          </Button>
          {record.status === 'submitted' && (
            <>
              <Button
                type="link"
                style={{ color: '#52c41a' }}
                icon={<CheckOutlined />}
                onClick={() => handleApprove(record.id)}
                loading={processing}
              >
                通过
              </Button>
              <Button
                type="link"
                danger
                icon={<CloseOutlined />}
                onClick={() => {
                  setSelectedResponse(record);
                  setRejectModalVisible(true);
                }}
              >
                驳回
              </Button>
            </>
          )}
        </Space>
      )
    }
  ];

  return (
    <div style={{ padding: 24 }}>
      <div style={{ marginBottom: 16 }}>
        <Button icon={<ArrowLeftOutlined />} onClick={() => router.push('/instructor')}>
          返回工作台
        </Button>
      </div>

      <Card
        title="学员文书审批"
        extra={
          <Button icon={<ReloadOutlined />} onClick={fetchResponses}>
            刷新
          </Button>
        }
      >
        <Tabs activeKey={activeTab} onChange={setActiveTab}>
          <TabPane tab="待审核" key="submitted" />
          <TabPane tab="已通过" key="approved" />
          <TabPane tab="已驳回" key="rejected" />
          <TabPane tab="全部" key="" />
        </Tabs>

        {responses.length === 0 && !loading ? (
          <Empty description={`暂无${activeTab === 'submitted' ? '待审核' : activeTab === 'approved' ? '已通过' : activeTab === 'rejected' ? '已驳回' : ''}的文书`} />
        ) : (
          <Table
            columns={columns}
            dataSource={responses}
            rowKey="id"
            loading={loading}
            pagination={{ pageSize: 10 }}
          />
        )}
      </Card>

      {/* 详情弹窗 */}
      <Modal
        title="文书详情"
        open={detailModalVisible}
        onCancel={() => setDetailModalVisible(false)}
        width={800}
        footer={
          selectedResponse?.status === 'submitted' ? [
            <Button key="close" onClick={() => setDetailModalVisible(false)}>
              关闭
            </Button>,
            <Button
              key="reject"
              danger
              onClick={() => {
                setDetailModalVisible(false);
                setRejectModalVisible(true);
              }}
            >
              驳回
            </Button>,
            <Button
              key="approve"
              type="primary"
              onClick={() => {
                handleApprove(selectedResponse.id);
                setDetailModalVisible(false);
              }}
            >
              通过
            </Button>
          ] : [
            <Button key="close" onClick={() => setDetailModalVisible(false)}>
              关闭
            </Button>
          ]
        }
      >
        {selectedResponse && (
          <Descriptions bordered column={1}>
            <Descriptions.Item label="学员">{selectedResponse.student_name}</Descriptions.Item>
            <Descriptions.Item label="文书">{selectedResponse.template_name}</Descriptions.Item>
            <Descriptions.Item label="状态">
              <Tag color={STATUS_MAP[selectedResponse.status]?.color}>
                {STATUS_MAP[selectedResponse.status]?.label}
              </Tag>
            </Descriptions.Item>
            <Descriptions.Item label="提交时间">
              {selectedResponse.submitted_at ? new Date(selectedResponse.submitted_at).toLocaleString('zh-CN') : '-'}
            </Descriptions.Item>
            {selectedResponse.review_comment && (
              <Descriptions.Item label="审核意见">{selectedResponse.review_comment}</Descriptions.Item>
            )}
          </Descriptions>
        )}
      </Modal>

      {/* 驳回弹窗 */}
      <Modal
        title="驳回理由"
        open={rejectModalVisible}
        onCancel={() => {
          setRejectModalVisible(false);
          setRejectReason('');
        }}
        onOk={() => handleReject(selectedResponse?.id)}
        confirmLoading={processing}
      >
        <p>请输入驳回理由（学员将看到此说明）：</p>
        <textarea
          value={rejectReason}
          onChange={(e) => setRejectReason(e.target.value)}
          style={{ width: '100%', height: 100, padding: 8 }}
          placeholder="例如：信息填写不完整，请补充..."
        />
      </Modal>
    </div>
  );
}
