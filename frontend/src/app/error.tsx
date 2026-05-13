'use client';

import React from 'react';
import { Result, Button } from 'antd';

export default function ErrorPage() {
  return (
    <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <Result
        status="500"
        title="500"
        subTitle="抱歉，服务器出错了"
        extra={
          <Button type="primary" href="/">
            返回首页
          </Button>
        }
      />
    </div>
  );
}
