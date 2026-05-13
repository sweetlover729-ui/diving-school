import React from 'react';
import { Result, Button } from 'antd';

export default function NotFoundPage() {
  return (
    <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <Result
        status="404"
        title="404"
        subTitle="抱歉，您访问的页面不存在"
        extra={
          <Button type="primary" href="/">
            返回首页
          </Button>
        }
      />
    </div>
  );
}
