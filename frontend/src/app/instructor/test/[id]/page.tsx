"use client";

import { useState, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import { Card, Table, Tag, Button, Space, message, Spin, Descriptions, Result } from "antd";
import { ArrowLeftOutlined, CheckCircleOutlined, CloseCircleOutlined } from "@ant-design/icons";
import { http } from "@/lib/http";

interface TestDetail {
  id: number;
  title: string;
  class_id: number;
  class_name: string;
  question_count: number;
  total_score: number;
  duration_minutes: number;
  created_at: string;
  results?: {
    id: number;
    user_id: number;
    user_name: string;
    id_card: string;
    score: number | null;
    submitted_at: string | null;
    status: string;
  }[];
}

export default function TestDetailPage() {
  const params = useParams();
  const router = useRouter();
  const testId = params.id as string;

  const [loading, setLoading] = useState(true);
  const [test, setTest] = useState<TestDetail | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    fetchTest();
  }, [testId]);

  const fetchTest = async () => {
    try {
      setLoading(true);
      const data = await http.get(`/instructor/tests/${testId}`);
      setTest(data);
    } catch (e) {
      setError(e.message || "获取测试详情失败");
    } finally {
      setLoading(false);
    }
  };

  if (loading) return <div style={{ textAlign: "center", padding: 48 }}><Spin size="large" /></div>;
  if (error) return <Result status="error" title="加载失败" subTitle={error} extra={<Button onClick={() => router.back()}>返回</Button>} />;
  if (!test) return null;

  const resultColumns = [
    { title: "学员", dataIndex: "user_name", key: "user_name" },
    {
      title: "身份证",
      dataIndex: "id_card",
      key: "id_card",
      render: (v: string) => v ? v.slice(0, 6) + "****" + v.slice(-4) : "-",
    },
    {
      title: "得分",
      dataIndex: "score",
      key: "score",
      render: (s: number | null) =>
        s !== null ? <Tag color="blue">{s}分</Tag> : <Tag color="default">未交卷</Tag>,
    },
    {
      title: "状态",
      dataIndex: "status",
      key: "status",
      render: (s: string, r: Record<string, unknown>) =>
        r.score !== null ? (
          <Tag icon={<CheckCircleOutlined />} color="success">已完成</Tag>
        ) : (
          <Tag icon={<CloseCircleOutlined />} color="default">未完成</Tag>
        ),
    },
    {
      title: "交卷时间",
      dataIndex: "submitted_at",
      key: "submitted_at",
      render: (t: string | null) => t ? t.replace("T", " ").slice(0, 19) : "-",
    },
  ];

  return (
    <div style={{ padding: 24 }}>
      <Button icon={<ArrowLeftOutlined />} onClick={() => router.back()} style={{ marginBottom: 16 }}>
        返回
      </Button>

      <Card title={test.title} style={{ marginBottom: 16 }}>
        <Descriptions column={{ xs: 1, sm: 2 }} size="small">
          <Descriptions.Item label="所属班级">{test.class_name}</Descriptions.Item>
          <Descriptions.Item label="题目数量">{test.question_count} 题</Descriptions.Item>
          <Descriptions.Item label="总分">{test.total_score} 分</Descriptions.Item>
          <Descriptions.Item label="时长">{test.duration_minutes} 分钟</Descriptions.Item>
          <Descriptions.Item label="创建时间">{test.created_at?.replace("T", " ").slice(0, 19)}</Descriptions.Item>
          <Descriptions.Item label="完成人数">
            {test.results?.filter((r) => r.score !== null).length || 0} / {test.results?.length || 0}
          </Descriptions.Item>
        </Descriptions>
      </Card>

      <Card title="学员答题情况">
        {test.results && test.results.length > 0 ? (
          <Table
            columns={resultColumns}
            dataSource={test.results}
            rowKey="id"
            pagination={false}
            size="small"
          />
        ) : (
          <div style={{ textAlign: "center", padding: 32, color: "#999" }}>暂无学员答题记录</div>
        )}
      </Card>
    </div>
  );
}
