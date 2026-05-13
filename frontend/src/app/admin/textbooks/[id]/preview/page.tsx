"use client";

import { useState, useEffect } from 'react';
import { useRouter, useParams } from 'next/navigation';
import { Card, Button, message, Space, Tag, Progress } from 'antd';
import { ArrowLeftOutlined, LeftOutlined, RightOutlined, FileTextOutlined } from '@ant-design/icons';
import { http } from '@/lib/http';

export default function TextbookPDFPreviewPage() {
  const router = useRouter();
  const params = useParams();
  const textbookId = params.id as string;
  
  const [pages, setPages] = useState<any[]>([]);
  const [currentPage, setCurrentPage] = useState(0);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchPages();
  }, [textbookId]);

  const fetchPages = async () => {
    try {
      const data = await http.get(`/admin/textbooks/${textbookId}/pages`);
      setPages(data.pages || []);
    } catch (e) {
      message.error('获取页面失败');
    } finally {
      setLoading(false);
    }
  };

  const handlePrev = () => {
    if (currentPage > 0) {
      setCurrentPage(currentPage - 1);
    }
  };

  const handleNext = () => {
    if (currentPage < pages.length - 1) {
      setCurrentPage(currentPage + 1);
    }
  };

  const page = pages[currentPage];

  return (
    <div style={{ height: '100vh', display: 'flex', flexDirection: 'column', background: '#f5f5f5' }}>
      {/* Header */}
      <div style={{ 
        padding: '12px 24px', 
        background: '#fff', 
        borderBottom: '1px solid #e8e8e8',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center'
      }}>
        <Space>
          <Button icon={<ArrowLeftOutlined />} onClick={() => router.push(`/admin/textbooks/${textbookId}`)}>返回</Button>
          <Tag color="blue">PDF预览模式</Tag>
        </Space>
        
        <Space>
          <Button icon={<LeftOutlined />} onClick={handlePrev} disabled={currentPage === 0}>上一页</Button>
          <span style={{ fontWeight: 500 }}>
            第 {currentPage + 1} / {pages.length} 页
          </span>
          <Button icon={<RightOutlined />} onClick={handleNext} disabled={currentPage >= pages.length - 1}>下一页</Button>
        </Space>
        
        <Progress 
          percent={Math.round((currentPage + 1) / pages.length * 100)} 
          style={{ width: 200 }}
          size="small"
        />
      </div>

      {/* Content */}
      <div style={{ 
        flex: 1, 
        display: 'flex', 
        justifyContent: 'center', 
        alignItems: 'center',
        padding: 24,
        overflow: 'auto'
      }}>
        {loading ? (
          <div>加载中...</div>
        ) : page ? (
          <img 
            src={page.url || page.content || ''} 
            alt={`第${page.sort_order || currentPage + 1}页`}
            style={{ 
              maxWidth: '100%', 
              maxHeight: '100%', 
              boxShadow: '0 4px 12px rgba(0,0,0,0.15)',
              borderRadius: 4
            }}
          />
        ) : (
          <div>暂无页面</div>
        )}
      </div>

      {/* Footer */}
      <div style={{
        padding: '12px 24px',
        background: '#fff',
        borderTop: '1px solid #e8e8e8',
        textAlign: 'center'
      }}>
        <Space size="large">
          <span>使用方向键 ← → 翻页</span>
          <span>进度: {Math.round((currentPage + 1) / pages.length * 100)}%</span>
        </Space>
      </div>
    </div>
  );
}