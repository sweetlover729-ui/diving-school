'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { CategoryProvider } from '@/components/CategoryProvider';
import AdminLayout from '@/components/AdminLayout';

function AuthGuard({ children }: { children: React.ReactNode }) {
  const router = useRouter();

  useEffect(() => {
    const token = localStorage.getItem('token');
    const userStr = localStorage.getItem('user');
    if (!token || !userStr) {
      router.push('/login');
      return;
    }
    try {
      const user = JSON.parse(userStr);
      if (user.role !== 'admin') {
        router.push('/login');
      }
    } catch {
      router.push('/login');
    }
  }, [router]);

  return <>{children}</>;
}

export default function AdminRootLayout({ children }: { children: React.ReactNode }) {
  return (
    <CategoryProvider>
      <AuthGuard>
        <AdminLayout>{children}</AdminLayout>
      </AuthGuard>
    </CategoryProvider>
  );
}