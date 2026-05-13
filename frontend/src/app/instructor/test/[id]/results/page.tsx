"use client";

import { useState, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import { Card, Table, Tag, Button, message, Spin, Result, Descriptions } from "antd";
import { ArrowLeftOutlined } from "@ant-design/icons";
import { http } from "@/lib/http";

export default function TestResultsPage() {
  const params = useParams();
  const router = useRouter();
  const testId = params.id as string;

  const [loading, setLoading] = useState(true);
  const [data, setData] = useState<any>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    http.get(`/instructor/tests/${testId}`)
      .then(setData)
      .catch((e) => setError(e.message || "加载失败"))
      .finally(() => setLoading(false));
  }, [testId]);

  if (loading) return <div style={{ textAlign: "center", padding: 48 }}><Spin size="large" /></div>;
  if (error) return <Result status="error" title={error} extra={<Button onClick={() => router.back()}>返回</Button>} />;
  if (!data) return null;

  return (
    <div style={{ padding: 24 }}>
      <Button icon={<ArrowLeftOutlined />} onClick={() => router.back()} style={{ marginBottom: 16 }}>
        返回
      </Button>
      <Card title={data.title}>
        <Descriptions column={2} size="small">
          <Descriptions.Item label="班级">{data.class_name}</Descriptions.Item>
          <Descriptions.Item label="总分">{data.total_score}分</Descriptions.Item>
        </Descriptions>
      </Card>
      <Card title="成绩列表" style={{ marginTop: 16 }}>
        {data.results?.length > 0 ? (
          <Table
            dataSource={data.results}
            rowKey="id"
            pagination={false}
            columns={[
              { title: "学员", dataIndex: "user_name" },
              {
                title: "得分",
                dataIndex: "score",
                render: (s: number | null) => s !== null ? <Tag color="blue">{s}分</Tag> : <Tag>未提交</Tag>,
              },
            ]}
          />
        ) : (
          <div style={{ textAlign: "center", padding: 32, color: "#999" }}>暂无数据</div>
        )}
      </Card>
    </div>
  );
}
