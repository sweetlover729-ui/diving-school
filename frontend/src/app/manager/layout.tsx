'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';

export default function ManagerLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();

  useEffect(() => {
    const token = localStorage.getItem('token');
    const userStr = localStorage.getItem('user');
    
    if (!token || !userStr) {
      router.push('/login');
      return;
    }
    
    const user = JSON.parse(userStr);
    if (user.role !== 'manager') {
      router.push('/login');
    }
  }, [router]);

  return <>{children}</>;
}