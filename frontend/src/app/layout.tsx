/**
 * 全局布局
 */
import './globals.css';
import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import { Suspense } from 'react';
import AntdRegistry from '@/components/AntdRegistry';
import CourseTitleSetter from '@/components/CourseTitleSetter';

const inter = Inter({ subsets: ['latin'] });

export const metadata: Metadata = {
  title: '公共安全潜水培训平台',
  description: '消防系统公共安全潜水班级制培训管理系统',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="zh-CN">
      <body className={inter.className}>
        <AntdRegistry>
          <Suspense fallback={null}>
            <CourseTitleSetter />
          </Suspense>
          {children}
        </AntdRegistry>
      </body>
    </html>
  );
}
