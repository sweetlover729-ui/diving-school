"use client";

import { useState, useEffect } from 'react';
import { useRouter, useParams } from 'next/navigation';
import { Card, Upload, Button, message, Progress, Image, Space, Tag, InputNumber, Modal } from 'antd';
import { ArrowLeftOutlined, UploadOutlined, DeleteOutlined, EyeOutlined, FileTextOutlined } from '@ant-design/icons';
import { http } from '@/lib/http';

export default function TextbookDetailPage() {
  const router = useRouter();
  const params = useParams();
  const textbookId = params.id as string;
  
  const [textbook, setTextbook] = useState<any>(null);
  const [pages, setPages] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);

  useEffect(() => {
    fetchTextbook();
  }, [textbookId]);

  const fetchTextbook = async () => {
    try {
      const data = await http.get(`/admin/textbooks/${textbookId}`);
      setTextbook(data);
      setPages(data.pages || []);
    } catch (e) {
      message.error('获取教材失败');
    } finally {
      setLoading(false);
    }
  };

  const handleUploadPDF = async (file: File) => {
    if (!file.name.endsWith('.pdf')) {
      message.error('只支持PDF文件');
      return false;
    }

    setUploading(true);
    try {
      const formData = new FormData();
      formData.append('file', file);
      
      const res = await http.post(`/admin/textbooks/${textbookId}/upload-pdf`, formData);
      message.success(`成功导入 ${res.pages_count} 页`);
      fetchTextbook();
    } catch (e) {
      message.error(e.message || '上传失败');
    } finally {
      setUploading(false);
    }
    return false;
  };

  const handleDeletePages = async () => {
    Modal.confirm({
      title: '确定删除所有PDF页面？',
      content: '删除后可以重新上传',
      onOk: async () => {
        try {
          await http.delete(`/admin/textbooks/${textbookId}/pages`);
          message.success('已删除');
          setPages([]);
        } catch (e) {
          message.error(e.message || '删除失败');
        }
      }
    });
  };

  return (
    <div style={{ padding: 24 }}>
      <div style={{ marginBottom: 16 }}>
        <Button icon={<ArrowLeftOutlined />} onClick={() => router.push('/admin/textbooks')}>返回</Button>
      </div>
      
      <h1 style={{ fontSize: 24, marginBottom: 24 }}>教材详情</h1>

      <Card loading={loading} style={{ marginBottom: 24 }}>
        <Space direction="vertical" size="large" style={{ width: '100%' }}>
          <div>
            <h3>{textbook?.name}</h3>
            <Space>
              <Tag color="blue">{textbook?.total_pages || 0} 页</Tag>
              <Tag color={pages.length > 0 ? 'green' : 'default'}>
                {pages.length > 0 ? 'PDF模式' : '章节模式'}
              </Tag>
            </Space>
          </div>

          {pages.length === 0 ? (
            <Card style={{ background: '#fafafa' }}>
              <p>当前教材使用章节模式，可以上传PDF文件转换为图片模式：</p>
              <Upload beforeUpload={handleUploadPDF} accept=".pdf" showUploadList={false}>
                <Button icon={<UploadOutlined />} loading={uploading}>上传PDF文件</Button>
              </Upload>
            </Card>
          ) : (
            <div>
              <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between' }}>
                <Space>
                  <FileTextOutlined />
                  <span>PDF图片模式（共 {pages.length} 页）</span>
                </Space>
                <Space>
                  <Button icon={<EyeOutlined />} onClick={() => router.push(`/admin/textbooks/${textbookId}/preview`)}>
                    预览PDF
                  </Button>
                  <Button danger icon={<DeleteOutlined />} onClick={handleDeletePages}>
                    删除PDF
                  </Button>
                </Space>
              </div>
              
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 16 }}>
                {pages.slice(0, 8).map((page, idx) => (
                  <Card key={page.id} size="small" hoverable style={{ textAlign: 'center' }}>
                    <Image 
                      src={page.url || page.content || ''} 
                      alt={`第${page.sort_order || idx + 1}页`}
                      style={{ maxHeight: 150, objectFit: 'contain' }}
                    />
                    <div style={{ marginTop: 8 }}>第 {page.sort_order || idx + 1} 页</div>
                  </Card>
                ))}
              </div>
              
              {pages.length > 8 && (
                <div style={{ textAlign: 'center', marginTop: 16 }}>
                  <Button onClick={() => router.push(`/admin/textbooks/${textbookId}/preview`)}>
                    查看全部 {pages.length} 页
                  </Button>
                </div>
              )}
            </div>
          )}
        </Space>
      </Card>
    </div>
  );
}