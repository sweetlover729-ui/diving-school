'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Button, Dropdown, message } from 'antd';
import { UserOutlined, BookOutlined, TrophyOutlined, DownOutlined } from '@ant-design/icons';
import { COURSE_LIST, COURSE_CONFIG } from '@/lib/courseConfig';

export default function HomePage() {
  const router = useRouter();
  const [courseLoading, setCourseLoading] = useState(false);

  const handleCourseSelect = (key: string) => {
    setCourseLoading(true);
    message.loading({ content: '正在进入...', key: 'course-loading', duration: 0 });
    router.push(`/login?course=${key}`);
  };

  const courseMenuItems = COURSE_LIST.map(item => ({
    key: item.key,
    label: item.label,
    onClick: () => handleCourseSelect(item.key),
  }));

  return (
    <div style={{
      minHeight: '100vh',
      background: '#c41e3a',
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      position: 'relative',
    }}>
      {/* 主标题横幅 */}
      <div style={{
        textAlign: 'center',
        marginBottom: 56,
        padding: '0 24px',
      }}>
        <h1 style={{
          fontSize: 36,
          fontWeight: 700,
          color: '#ffffff',
          letterSpacing: 4,
          margin: 0,
          textShadow: '0 2px 8px rgba(0,0,0,0.2)',
        }}>
          应急救援与公共安全教育培训管理系统
        </h1>
      </div>

      {/* 三个功能按钮 */}
      <div style={{
        display: 'flex',
        gap: 32,
        flexWrap: 'wrap',
        justifyContent: 'center',
        padding: '0 24px',
      }}>
        {/* 注册/登陆 */}
        <Button
          type="primary"
          size="large"
          icon={<UserOutlined />}
          onClick={() => router.push('/login')}
          style={{
            height: 56,
            fontSize: 18,
            fontWeight: 600,
            padding: '0 40px',
            borderRadius: 8,
            background: '#ffffff',
            color: '#c41e3a',
            border: 'none',
            boxShadow: '0 4px 16px rgba(0,0,0,0.15)',
          }}
        >
          注册/登陆
        </Button>

        {/* 课程选择（下拉菜单） */}
        <Dropdown
          menu={{ items: courseMenuItems }}
          placement="bottomCenter"
          onOpenChange={(open) => {
            if (!open) setCourseLoading(false);
          }}
        >
          <Button
            size="large"
            icon={<BookOutlined />}
            loading={courseLoading}
            style={{
              height: 56,
              fontSize: 18,
              fontWeight: 600,
              padding: '0 40px',
              borderRadius: 8,
              background: '#ffffff',
              color: '#c41e3a',
              border: 'none',
              boxShadow: '0 4px 16px rgba(0,0,0,0.15)',
            }}
          >
            课程选择 <DownOutlined style={{ fontSize: 12, marginLeft: 6 }} />
          </Button>
        </Dropdown>

        {/* 考核入口 */}
        <Button
          size="large"
          icon={<TrophyOutlined />}
          onClick={() => {
            message.info('考核入口功能开发中，敬请期待');
          }}
          style={{
            height: 56,
            fontSize: 18,
            fontWeight: 600,
            padding: '0 40px',
            borderRadius: 8,
            background: '#ffffff',
            color: '#c41e3a',
            border: 'none',
            boxShadow: '0 4px 16px rgba(0,0,0,0.15)',
          }}
        >
          考核入口
        </Button>
      </div>

      {/* 底部提示 */}
      <div style={{
        position: 'absolute',
        bottom: 32,
        color: 'rgba(255,255,255,0.6)',
        fontSize: 13,
      }}>
        选择课程后进入对应培训系统
      </div>
    </div>
  );
}
