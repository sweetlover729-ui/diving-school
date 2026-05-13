'use client';

import { useEffect, useState, useCallback, useRef } from 'react';
import { useRouter } from 'next/navigation';
import { Modal, Tag, Button, Typography } from 'antd';
import { ExclamationCircleOutlined } from '@ant-design/icons';
import { http } from '@/lib/http';

async function checkPendingRequiredDocs(): Promise<any[]> {
  try {
    const docs = await http.get('/students/me/documents');
    return docs.filter((d: Record<string, unknown>) => d.is_required && d.status !== 'approved');
  } catch {
    return [];
  }
}

export default function StudentLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [pendingDocs, setPendingDocs] = useState<any[]>([]);
  const [showDocModal, setShowDocModal] = useState(false);

  /** 标记是否来自"立即填写"按钮——允许本次导航不弹窗 */
  const bypassRef = useRef(false);

  const recheckAndShow = useCallback(async () => {
    const pending = await checkPendingRequiredDocs();
    setPendingDocs(pending);
    setShowDocModal(pending.length > 0);
  }, []);

  useEffect(() => {
    const token = localStorage.getItem('token');
    const userStr = localStorage.getItem('user');
    if (!token || !userStr) {
      router.push('/login');
      return;
    }
    const user = JSON.parse(userStr);
    if (user.role !== 'student') {
      router.push('/login');
      return;
    }
    setLoading(false);
    recheckAndShow();
  }, [router, recheckAndShow]);

  /** 拦截 router.push：每次导航前都重新检查必填文书 */
  useEffect(() => {
    const originalPush = router.push.bind(router);
    router.push = (...args: Parameters<typeof router.push>) => {
      // 来自"立即填写"按钮的导航：绕过检查
      if (bypassRef.current) {
        bypassRef.current = false;
        return originalPush(...args);
      }

      const href = args[0];
      const allowed = ['/student/profile', '/student/profile/password', '/login', '/student/documents'];
      let target = '';
      if (typeof href === 'string') {
        target = href;
      } else if (href != null) {
        const h = href as { pathname?: string };
        target = h.pathname || '';
      }
      if (!allowed.some(p => target.startsWith(p))) {
        if (pendingDocs.length > 0) {
          setShowDocModal(true);
          return Promise.resolve();
        }
      }
      return originalPush(...args);
    };
    return () => { router.push = originalPush; };
  }, [router, pendingDocs]);

  if (loading) return null;

  return (
    <>
      {children}

      <Modal
        title={
          <span style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <ExclamationCircleOutlined style={{ color: '#faad14', fontSize: 20 }} />
            必须完成入学文书
          </span>
        }
        open={showDocModal}
        onCancel={() => setShowDocModal(false)}
        footer={[
          <Button key="later" onClick={() => setShowDocModal(false)}>
            稍后处理
          </Button>,
          <Button
            key="goto"
            type="primary"
            onClick={() => {
              // 标记bypass → 关闭弹窗 → 路由导航（wrapper会放行）
              bypassRef.current = true;
              setShowDocModal(false);
              router.push('/student/documents');
            }}
          >
            立即填写（{pendingDocs.length}份必填文书待完成）
          </Button>,
        ]}
        width={420}
        styles={{ body: { padding: '16px 24px' } }}
      >
        {/* 提示文字 */}
        <div style={{
          background: '#fffbe6',
          border: '1px solid #ffe58f',
          borderRadius: 8,
          padding: '10px 14px',
          marginBottom: 16,
          color: '#ad6800',
          fontSize: 14,
          lineHeight: 1.6,
        }}>
          以下文书为<strong>必填项</strong>，完成前点击任何功能都将重新提示
        </div>

        {/* 文书列表 */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {pendingDocs.map((doc) => (
            <div
              key={doc.template_id}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 10,
                padding: '10px 12px',
                background: doc.status === 'rejected' ? '#fff2e8' : '#f6ffed',
                border: `1px solid ${doc.status === 'rejected' ? '#ffbb96' : '#b7eb8f'}`,
                borderRadius: 8,
              }}
            >
              <Tag color="red" style={{ flexShrink: 0 }}>
                必填
              </Tag>
              <Typography.Text
                strong
                style={{
                  flex: 1,
                  fontSize: 14,
                  lineHeight: 1.4,
                  wordBreak: 'break-word',
                }}
              >
                {doc.template_name}
              </Typography.Text>
              {doc.status === 'rejected' && (
                <Tag color="orange" style={{ flexShrink: 0 }}>已驳回</Tag>
              )}
              {doc.status === 'pending' && (
                <Tag color="blue" style={{ flexShrink: 0 }}>未填写</Tag>
              )}
            </div>
          ))}
        </div>
      </Modal>
    </>
  );
}
