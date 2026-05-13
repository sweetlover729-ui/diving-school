"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { Card, Table, Tag, Space, Button, Input } from "antd";
import { ArrowLeftOutlined, SearchOutlined } from "@ant-design/icons";
import { http } from "@/lib/http";

export default function ManagerStudentsPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [students, setStudents] = useState<any[]>([]);
  const [searchText, setSearchText] = useState("");

  useEffect(() => {
    http.get("/manager/students")
      .then(setStudents)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const filtered = students.filter(
    (s) =>
      !searchText ||
      s.name?.includes(searchText) ||
      s.phone?.includes(searchText) ||
      s.id_card?.includes(searchText)
  );

  const columns = [
    { title: "姓名", dataIndex: "name", key: "name" },
    {
      title: "身份证",
      dataIndex: "id_card",
      key: "id_card",
      render: (v: string) => (v ? v.slice(0, 6) + "****" + v.slice(-4) : "-"),
    },
    { title: "手机", dataIndex: "phone", key: "phone" },
    {
      title: "状态",
      dataIndex: "status",
      key: "status",
      render: () => <Tag color="green">正常</Tag>,
    },
    {
      title: "班级",
      dataIndex: "class_name",
      key: "class_name",
      render: (v: string) => v || "-",
    },
  ];

  return (
    <div style={{ padding: 24 }}>
      <Button icon={<ArrowLeftOutlined />} onClick={() => router.push("/manager")} style={{ marginBottom: 16 }}>
        返回
      </Button>

      <Card title="学员列表">
        <div style={{ marginBottom: 12 }}>
          <Input
            prefix={<SearchOutlined />}
            placeholder="搜索姓名/手机/身份证"
            value={searchText}
            onChange={(e) => setSearchText(e.target.value)}
            style={{ width: 280 }}
            allowClear
          />
        </div>
        <Table
          columns={columns}
          dataSource={filtered}
          rowKey="id"
          loading={loading}
          pagination={{ pageSize: 20 }}
        />
      </Card>
    </div>
  );
}
