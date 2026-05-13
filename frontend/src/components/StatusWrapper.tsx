'use client';

import React from 'react';
import { Spin, Empty, Result, Button } from 'antd';
import { ReloadOutlined } from '@ant-design/icons';

interface StatusWrapperProps {
  loading?: boolean;
  empty?: boolean;
  error?: string | null;
  emptyText?: string;
  emptyImage?: React.ReactNode;
  onRetry?: () => void;
  children: React.ReactNode;
}

/**
 * 统一状态包装器：loading → empty → error → content
 * 自动按优先级判定，每次只显示一个状态
 */
export default function StatusWrapper({
  loading,
  empty,
  error,
  emptyText = '暂无数据',
  emptyImage,
  onRetry,
  children,
}: StatusWrapperProps) {
  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: '80px 0' }}>
        <Spin size="large" tip="加载中..." />
      </div>
    );
  }

  if (error) {
    return (
      <Result
        status="error"
        title="加载失败"
        subTitle={error}
        extra={
          onRetry && (
            <Button type="primary" icon={<ReloadOutlined />} onClick={onRetry}>
              重试
            </Button>
          )
        }
      />
    );
  }

  if (empty) {
    return emptyImage ? (
      <Empty image={emptyImage} description={emptyText} style={{ padding: '80px 0' }} />
    ) : (
      <Empty description={emptyText} style={{ padding: '80px 0' }} />
    );
  }

  return <>{children}</>;
}