'use client';

import React from 'react';
import { Spin } from 'antd';

export default function LoadingPage() {
  return (
    <div style={{ 
      minHeight: '100vh', 
      display: 'flex', 
      alignItems: 'center', 
      justifyContent: 'center',
      flexDirection: 'column'
    }}>
      <Spin size="large" />
      <div style={{ marginTop: 16, color: '#666' }}>加载中...</div>
    </div>
  );
}
