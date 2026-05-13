'use client';

import { useState, useEffect } from 'react';
import { Table, Card, Button, Space, Tag, message, Input, DatePicker } from 'antd';
import { ReloadOutlined, SearchOutlined } from '@ant-design/icons';
import dayjs from 'dayjs';
import { auditApi } from '@/lib/api';
import type { AuditLog } from '@/lib/types';

export default function AuditPage() {
  const [data, setData] = useState<AuditLog[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(50);
  const [search, setSearch] = useState('');

  useEffect(() => { fetchData(); }, [page, pageSize]);

  const fetchData = async () => {
    setLoading(true);
    try {
      const res = await auditApi.list();
      setData(res?.items || []);
      setTotal(res?.total || 0);
    } catch (e: any) {
      message.error(e.message || '加载失败');
    } finally { setLoading(false); }
  };

  const filtered = search
    ? data.filter(d =>
        (d.user_name || '').includes(search) ||
        (d.action || '').includes(search) ||
        (d.target_name || '').includes(search)
      )
    : data;

  const actionColorMap: Record<string, string> = {
    CREATE: 'green', UPDATE: 'blue', DELETE: 'red', LOGIN: 'cyan',
    LOGOUT: 'default', VIEW: 'default',
  };

  const columns = [
    { title: 'ID', dataIndex: 'id', width: 70 },
    { title: '用户', dataIndex: 'user_name', width: 120 },
    {
      title: '角色', dataIndex: 'user_role', width: 80,
      render: (v: string) => <Tag>{v}</Tag>
    },
    {
      title: '操作', dataIndex: 'action', width: 90,
      render: (v: string) => <Tag color={actionColorMap[v] || 'default'}>{v}</Tag>
    },
    { title: '目标类型', dataIndex: 'target_type', width: 110 },
    { title: '目标名称', dataIndex: 'target_name', width: 150, ellipsis: true },
    { title: 'IP', dataIndex: 'ip_address', width: 130 },
    {
      title: '时间', dataIndex: 'created_at', width: 170,
      render: (v: string) => v ? v.substring(0, 19).replace('T', ' ') : '-',
      sorter: (a: AuditLog, b: AuditLog) => (a.created_at > b.created_at ? -1 : 1),
      defaultSortOrder: 'descend' as const,
    },
  ];

  return (
    <Card
      extra={
        <Space>
          <Input
            placeholder="搜索用户/操作/目标"
            prefix={<SearchOutlined />}
            style={{ width: 200 }}
            value={search}
            onChange={e => setSearch(e.target.value)}
            allowClear
          />
          <Button icon={<ReloadOutlined />} onClick={fetchData}>刷新</Button>
        </Space>
      }
    >
      <Table
        columns={columns}
        dataSource={filtered}
        rowKey="id"
        loading={loading}
        pagination={{
          current: page,
          pageSize,
          total: search ? filtered.length : total,
          showSizeChanger: true,
          showTotal: t => `共 ${t} 条`,
          onChange: (p, s) => { setPage(p); setPageSize(s); },
        }}
        size="middle"
        locale={{ emptyText: '暂无审计日志' }}
      />
    </Card>
  );
}