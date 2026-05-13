'use client';

import { useState, useEffect } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { Layout, Menu, Dropdown, Avatar, Space, Select, Button } from 'antd';
import {
  DashboardOutlined, AppstoreOutlined, ReadOutlined, TeamOutlined,
  BookOutlined, UserOutlined, ApartmentOutlined, CheckCircleOutlined,
  EyeOutlined, SettingOutlined, FileTextOutlined,
  LogoutOutlined, KeyOutlined, MenuFoldOutlined, MenuUnfoldOutlined,
} from '@ant-design/icons';
import { useCategory } from './CategoryProvider';
import ErrorBoundary from './ErrorBoundary';

const { Sider, Content, Header } = Layout;

const PAGE_TITLES: Record<string, string> = {
  '/admin': '仪表盘',
  '/admin/categories': '分类管理',
  '/admin/courses': '课程管理',
  '/admin/classes': '班级管理',
  '/admin/textbooks': '教材管理',
  '/admin/instructors': '教练管理',
  '/admin/people': '人员管理',
  '/admin/companies': '单位管理',
  '/admin/questions': '题库管理',
  '/admin/student-preview': '课程预览',
  '/admin/system': '系统设置',
  '/admin/audit': '审计日志',
};

const menuItems = [
  { key: '/admin', icon: <DashboardOutlined />, label: '仪表盘' },
  { key: '/admin/categories', icon: <AppstoreOutlined />, label: '分类管理' },
  { key: '/admin/courses', icon: <ReadOutlined />, label: '课程管理' },
  { key: '/admin/classes', icon: <TeamOutlined />, label: '班级管理' },
  { key: '/admin/textbooks', icon: <BookOutlined />, label: '教材管理' },
  { key: '/admin/instructors', icon: <UserOutlined />, label: '教练管理' },
  { key: '/admin/people', icon: <TeamOutlined />, label: '人员管理' },
  { key: '/admin/companies', icon: <ApartmentOutlined />, label: '单位管理' },
  { key: '/admin/questions', icon: <CheckCircleOutlined />, label: '题库管理' },
  { key: '/admin/student-preview', icon: <EyeOutlined />, label: '课程预览' },
  { key: '/admin/system', icon: <SettingOutlined />, label: '系统设置' },
  { key: '/admin/audit', icon: <FileTextOutlined />, label: '审计日志' },
];

function getPageTitle(pathname: string): string {
  if (PAGE_TITLES[pathname]) return PAGE_TITLES[pathname];
  const key = Object.keys(PAGE_TITLES)
    .filter(k => pathname.startsWith(k) && k !== '/admin')
    .sort((a, b) => b.length - a.length)[0];
  return key ? PAGE_TITLES[key] : '管理后台';
}

function getSelectedKey(pathname: string): string {
  if (menuItems.some(item => item.key === pathname)) return pathname;
  const match = menuItems
    .filter(item => pathname.startsWith(item.key) && item.key !== '/admin')
    .sort((a, b) => b.key.length - a.key.length);
  return match[0]?.key || '/admin';
}

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const [collapsed, setCollapsed] = useState(false);
  const [currentUser, setCurrentUser] = useState<{ username?: string; name?: string } | null>(null);
  const { categories, currentCategoryId, setCurrentCategoryId } = useCategory();

  useEffect(() => {
    try {
      const userStr = localStorage.getItem('user');
      if (userStr) setCurrentUser(JSON.parse(userStr));
    } catch {}
  }, []);

  const handleLogout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    localStorage.removeItem('adminCategoryId');
    router.push('/login');
  };

  const userMenuItems = [
    { key: 'profile', icon: <UserOutlined />, label: '个人中心', onClick: () => router.push('/admin/profile') },
    { key: 'password', icon: <KeyOutlined />, label: '修改密码', onClick: () => router.push('/admin/profile/password') },
    { type: 'divider' as const },
    { key: 'logout', icon: <LogoutOutlined />, label: '退出登录', onClick: handleLogout, danger: true },
  ];

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider
        trigger={null}
        collapsible
        collapsed={collapsed}
        theme="light"
        width={220}
        style={{ boxShadow: '2px 0 8px rgba(0,0,0,0.06)', zIndex: 10 }}
      >
        <div style={{
          height: 64, display: 'flex', alignItems: 'center', justifyContent: 'center',
          borderBottom: '1px solid #f0f0f0', fontSize: collapsed ? 16 : 17,
          fontWeight: 700, color: '#1677ff', whiteSpace: 'nowrap', overflow: 'hidden',
          letterSpacing: collapsed ? 0 : 1,
        }}>
          {collapsed ? '培训' : '应急救援培训平台'}
        </div>

        <Menu
          mode="inline"
          selectedKeys={[getSelectedKey(pathname)]}
          style={{ borderRight: 0 }}
          items={menuItems.map(item => ({
            key: item.key, icon: item.icon, label: item.label,
            onClick: () => router.push(item.key),
          }))}
        />
      </Sider>

      <Layout>
        <Header style={{
          background: '#fff', padding: '0 24px', display: 'flex',
          alignItems: 'center', justifyContent: 'space-between',
          boxShadow: '0 1px 4px rgba(0,0,0,0.08)', zIndex: 5, height: 56,
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
            <Button
              type="text"
              icon={collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
              onClick={() => setCollapsed(!collapsed)}
              style={{ fontSize: 16, width: 36, height: 36 }}
            />
            <h1 style={{ margin: 0, fontSize: 16, fontWeight: 600, color: '#1f1f1f' }}>
              {getPageTitle(pathname)}
            </h1>

            {categories.length > 0 && (
              <Select
                size="small"
                style={{ width: 140 }}
                value={currentCategoryId}
                onChange={setCurrentCategoryId}
                options={categories.filter(c => c.is_active).map(c => ({ value: c.id, label: c.name }))}
              />
            )}
          </div>

          <Dropdown menu={{ items: userMenuItems }} placement="bottomRight">
            <Space style={{ cursor: 'pointer' }}>
              <Avatar size="small" icon={<UserOutlined />} style={{ backgroundColor: '#1677ff' }} />
              <span style={{ fontSize: 14, color: '#4a4a4a' }}>
                {currentUser?.username || currentUser?.name || '管理员'}
              </span>
            </Space>
          </Dropdown>
        </Header>

        <Content style={{ margin: 20, overflow: 'auto' }}>
          <ErrorBoundary>
            {children}
          </ErrorBoundary>
        </Content>
      </Layout>
    </Layout>
  );
}