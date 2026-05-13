"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { Card, Table, Tag, Button } from "antd";
import { ArrowLeftOutlined } from "@ant-design/icons";
import { http } from "@/lib/http";

export default function ManagerScoresPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState<any[]>([]);

  useEffect(() => {
    http.get("/manager/scores")
      .then(setData)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  if (!data.length && !loading) {
    return (
      <div style={{ padding: 24 }}>
        <Button icon={<ArrowLeftOutlined />} onClick={() => router.push("/manager")}>返回</Button>
        <Card title="成绩汇总" style={{ marginTop: 16 }}>
          <div style={{ textAlign: "center", padding: 48, color: "#999" }}>暂无成绩数据</div>
        </Card>
      </div>
    );
  }

  return (
    <div style={{ padding: 24 }}>
      <Button icon={<ArrowLeftOutlined />} onClick={() => router.push("/manager")} style={{ marginBottom: 16 }}>
        返回
      </Button>
      <Card title="成绩汇总">
        <Table
          dataSource={data}
          rowKey="id"
          loading={loading}
          pagination={{ pageSize: 20 }}
          columns={[
            { title: "学员", dataIndex: "user_name", key: "user_name" },
            { title: "班级", dataIndex: "class_name", key: "class_name" },
            {
              title: "得分",
              dataIndex: "score",
              key: "score",
              render: (s: number | null) =>
                s !== null ? <Tag color="blue">{s}分</Tag> : <Tag>未提交</Tag>,
            },
            { title: "提交时间", dataIndex: "submitted_at", key: "submitted_at",
              render: (t: string) => t ? t.replace("T", " ").slice(0, 19) : "-" },
          ]}
        />
      </Card>
    </div>
  );
}
