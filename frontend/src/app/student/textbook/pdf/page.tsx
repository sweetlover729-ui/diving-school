"use client";

import { useState, useEffect, useRef, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { Layout, Card, Button, Tag, Space, message } from 'antd';
import { 
  ArrowLeftOutlined, ZoomInOutlined, ZoomOutOutlined, 
  FullscreenOutlined, FullscreenExitOutlined, ReloadOutlined
} from '@ant-design/icons';
import { http } from '@/lib/http';

const { Header, Content } = Layout;

export default function StudentTextbookPDFPage() {
  const router = useRouter();
  const [pdfPages, setPdfPages] = useState<any[]>([]);
  const [currentPdfPage, setCurrentPdfPage] = useState(0);
  const [textbookId, setTextbookId] = useState<number>(0);

  // 全屏模式
  const [isFullscreen, setIsFullscreen] = useState(false);
  
  // 缩放和拖动状态
  const [scale, setScale] = useState(1);
  const [position, setPosition] = useState({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });
  const containerRef = useRef<HTMLDivElement>(null);
  const fullscreenRef = useRef<HTMLDivElement>(null);

  // 检测移动设备和横屏
  const [isMobile, setIsMobile] = useState(false);
  const [isLandscape, setIsLandscape] = useState(false);

  useEffect(() => {
    const checkMobile = () => {
      setIsMobile(window.innerWidth < 768 || 'ontouchstart' in window);
      setIsLandscape(window.innerWidth > window.innerHeight);
    };
    checkMobile();
    window.addEventListener('resize', checkMobile);
    return () => window.removeEventListener('resize', checkMobile);
  }, []);

  // 横屏检测
  useEffect(() => {
    const handleOrientationChange = () => {
      setIsLandscape(window.innerHeight < window.innerWidth);
    };
    window.addEventListener('orientationchange', handleOrientationChange);
    window.addEventListener('resize', handleOrientationChange);
    return () => {
      window.removeEventListener('orientationchange', handleOrientationChange);
      window.removeEventListener('resize', handleOrientationChange);
    };
  }, []);

  useEffect(() => {
    fetchTextbook();
  }, []);

  // 全屏功能
  const toggleFullscreen = useCallback(() => {
    if (!document.fullscreenElement) {
      if (fullscreenRef.current) {
        fullscreenRef.current.requestFullscreen().then(() => {
          setIsFullscreen(true);
        }).catch((err) => {
          message.error('无法进入全屏模式');
          console.error(err);
        });
      }
    } else {
      document.exitFullscreen().then(() => {
        setIsFullscreen(false);
      });
    }
  }, []);

  // 监听全屏变化
  useEffect(() => {
    const handleFullscreenChange = () => {
      setIsFullscreen(!!document.fullscreenElement);
    };
    document.addEventListener('fullscreenchange', handleFullscreenChange);
    return () => document.removeEventListener('fullscreenchange', handleFullscreenChange);
  }, []);

  // 键盘控制
  useEffect(() => {
    if (pdfPages.length === 0) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) return;

      switch (e.key) {
        case 'ArrowRight':
        case 'ArrowDown':
        case ' ':
        case 'PageDown':
          e.preventDefault();
          goToNextPage();
          break;
        case 'ArrowLeft':
        case 'ArrowUp':
        case 'PageUp':
          e.preventDefault();
          goToPrevPage();
          break;
        case 'Home':
          e.preventDefault();
          setCurrentPdfPage(0);
          break;
        case 'End':
          e.preventDefault();
          setCurrentPdfPage(pdfPages.length - 1);
          break;
        case 'Escape':
          if (isFullscreen) {
            e.preventDefault();
            toggleFullscreen();
          }
          break;
        case 'f':
        case 'F':
          if (!e.ctrlKey && !e.metaKey) {
            e.preventDefault();
            toggleFullscreen();
          }
          break;
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [pdfPages.length, currentPdfPage, isFullscreen]);

  const fetchTextbook = async () => {
    try {
      const data = await http.get('/student/chapters/pdf');
      if (data.pages && data.pages.length > 0) {
        // 只获取显示的页面
        const visiblePages = data.pages.filter((p: Record<string, unknown>) => p.is_visible !== false);
        setPdfPages(visiblePages);
        setTextbookId(data.textbook?.id || 0);
      } else {
        message.warning('暂无教材');
      }
    } catch (e) {
      console.error(e);
      message.warning('获取教材失败');
    }
  };

  const goToNextPage = () => {
    if (currentPdfPage < pdfPages.length - 1) {
      setCurrentPdfPage(currentPdfPage + 1);
      if (isMobile && containerRef.current) {
        containerRef.current.scrollTop = 0;
      }
    }
  };

  const goToPrevPage = () => {
    if (currentPdfPage > 0) {
      setCurrentPdfPage(currentPdfPage - 1);
      if (isMobile && containerRef.current) {
        containerRef.current.scrollTop = 0;
      }
    }
  };

  const handleZoomIn = () => {
    setScale(s => Math.min(s * 1.2, 5));
  };

  const handleZoomOut = () => {
    setScale(s => Math.max(s / 1.2, 0.2));
  };

  const handleReset = () => {
    setScale(1);
    setPosition({ x: 0, y: 0 });
  };

  // 鼠标拖动
  const handleMouseDown = (e: React.MouseEvent) => {
    if (e.button === 0) {
      setIsDragging(true);
      setDragStart({ x: e.clientX - position.x, y: e.clientY - position.y });
    }
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (isDragging) {
      setPosition({
        x: e.clientX - dragStart.x,
        y: e.clientY - dragStart.y,
      });
    }
  };

  const handleMouseUp = () => {
    setIsDragging(false);
  };

  // 滚轮缩放
  const handleWheel = useCallback((e: React.WheelEvent) => {
    e.preventDefault();
    if (e.deltaY < 0) {
      handleZoomIn();
    } else {
      handleZoomOut();
    }
  }, []);

  // 触摸事件
  const touchStartRef = useRef({ x: 0, y: 0 });
  const swipeStartRef = useRef(0);

  const handleTouchStart = (e: React.TouchEvent) => {
    if (e.touches.length === 1) {
      touchStartRef.current = { 
        x: e.touches[0].clientX - position.x, 
        y: e.touches[0].clientY - position.y 
      };
    }
    swipeStartRef.current = e.touches[0].clientX;
  };

  const handleTouchMove = (e: React.TouchEvent) => {
    if (e.touches.length === 1) {
      setPosition({
        x: e.touches[0].clientX - touchStartRef.current.x,
        y: e.touches[0].clientY - touchStartRef.current.y,
      });
    }
  };

  const handleTouchEnd = (e: React.TouchEvent) => {
    if (e.changedTouches.length === 1) {
      const deltaX = e.changedTouches[0].clientX - swipeStartRef.current;
      if (Math.abs(deltaX) > 50) {
        if (deltaX > 0) {
          goToPrevPage();
        } else {
          goToNextPage();
        }
      }
    }
  };

  // 全屏模式下的控制栏样式
  const fullscreenControls = {
    position: 'fixed' as const,
    bottom: 20,
    left: '50%',
    transform: 'translateX(-50%)',
    display: 'flex',
    gap: 8,
    zIndex: 1000,
    background: 'rgba(0,0,0,0.7)',
    padding: '10px 20px',
    borderRadius: 30,
  };

  if (pdfPages.length === 0) {
    return (
      <Layout style={{ minHeight: '100vh' }}>
        <Header style={{ background: '#fff', padding: '0 16px', display: 'flex', alignItems: 'center', borderBottom: '1px solid #f0f0f0' }}>
          <Button icon={<ArrowLeftOutlined />} onClick={() => router.push('/student')}>返回</Button>
          <span style={{ marginLeft: 16, fontWeight: 'bold' }}>我的教材</span>
        </Header>
        <Content style={{ padding: 24 }}>
          <Card>
            <div style={{ textAlign: 'center', padding: 60, color: '#999' }}>
              <p>暂无PDF教材</p>
              <Button type="primary" onClick={() => router.push('/student/chapters')}>
                查看章节内容
              </Button>
            </div>
          </Card>
        </Content>
      </Layout>
    );
  }

  return (
    <Layout style={{ minHeight: '100vh' }} ref={fullscreenRef}>
      <Header style={{ 
        background: '#fff', 
        padding: '0 16px', 
        display: 'flex', 
        flexWrap: 'wrap',
        justifyContent: 'space-between', 
        alignItems: 'center', 
        borderBottom: '1px solid #f0f0f0',
        gap: 8,
      }}>
        <Space>
          <Button icon={<ArrowLeftOutlined />} onClick={() => router.push('/student')}>返回</Button>
          <span style={{ fontWeight: 'bold' }}>教材学习</span>
        </Space>
        <Space>
          {!isMobile && (
            <>
              <Button icon={<ZoomOutOutlined />} onClick={handleZoomOut} size="small" />
              <Tag>{Math.round(scale * 100)}%</Tag>
              <Button icon={<ZoomInOutlined />} onClick={handleZoomIn} size="small" />
              <Button icon={<ReloadOutlined />} onClick={handleReset} size="small">重置</Button>
            </>
          )}
          <Button 
            icon={isFullscreen ? <FullscreenExitOutlined /> : <FullscreenOutlined />} 
            onClick={toggleFullscreen}
          >
            {isFullscreen ? '退出全屏' : '全屏'}
          </Button>
        </Space>
      </Header>

      <Content 
        ref={containerRef}
        style={{ 
          padding: 16, 
          background: '#000',  // 全屏时黑色背景更沉浸
          overflow: 'auto',
          maxHeight: isFullscreen ? '100vh' : 'calc(100vh - 65px)',
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'flex-start',
        }}
        onTouchStart={handleTouchStart}
        onTouchMove={handleTouchMove}
        onTouchEnd={handleTouchEnd}
      >
        <div style={{ 
          display: 'flex', 
          flexDirection: 'column', 
          alignItems: 'center',
          gap: 16,
          width: '100%',
          maxWidth: isFullscreen ? '100%' : 1000,
        }}>
          {/* 非全屏时的控制栏 */}
          {!isFullscreen && (
            <div style={{ display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap', justifyContent: 'center' }}>
              <Button onClick={goToPrevPage} disabled={currentPdfPage === 0} size="small">
                ← 上一页
              </Button>
              <Tag color="blue">第 {currentPdfPage + 1} / {pdfPages.length} 页</Tag>
              <Button onClick={goToNextPage} disabled={currentPdfPage === pdfPages.length - 1} size="small">
                下一页 →
              </Button>
              <Button icon={<FullscreenOutlined />} onClick={toggleFullscreen} size="small">全屏</Button>
              {!isMobile && (
                <span style={{ fontSize: 12, color: '#999', marginLeft: 8 }}>
                  键盘: ←→翻页 空格下一页 F全屏 ESC退出
                </span>
              )}
            </div>
          )}

          {/* 全屏控制栏 */}
          {isFullscreen && (
            <div style={fullscreenControls}>
              <Button onClick={goToPrevPage} disabled={currentPdfPage === 0} style={{ color: '#fff', borderColor: '#fff' }}>
                ← 上一页
              </Button>
              <Tag color="blue" style={{ alignSelf: 'center' }}>
                {currentPdfPage + 1} / {pdfPages.length}
              </Tag>
              <Button onClick={goToNextPage} disabled={currentPdfPage === pdfPages.length - 1} style={{ color: '#fff', borderColor: '#fff' }}>
                下一页 →
              </Button>
              {!isMobile && (
                <>
                  <Button onClick={handleZoomOut} style={{ color: '#fff', borderColor: '#fff' }}>−</Button>
                  <Tag style={{ alignSelf: 'center' }}>{Math.round(scale * 100)}%</Tag>
                  <Button onClick={handleZoomIn} style={{ color: '#fff', borderColor: '#fff' }}>+</Button>
                  <Button onClick={handleReset} style={{ color: '#fff', borderColor: '#fff' }}>重置</Button>
                </>
              )}
              <Button onClick={toggleFullscreen} style={{ color: '#fff', borderColor: '#fff' }}>
                 退出
              </Button>
            </div>
          )}

          {/* 图片容器 */}
          <div
            style={{
              overflow: 'hidden',
              cursor: isDragging ? 'grabbing' : 'grab',
              touchAction: 'none',
              width: '100%',
              minHeight: isFullscreen ? '100vh' : '60vh',
              display: 'flex',
              justifyContent: 'center',
              alignItems: 'center',
            }}
            onWheel={handleWheel}
            onMouseDown={handleMouseDown}
            onMouseMove={handleMouseMove}
            onMouseUp={handleMouseUp}
            onMouseLeave={handleMouseUp}
          >
            <img
              src={pdfPages[currentPdfPage]?.url}
              alt={`第${currentPdfPage + 1}页`}
              draggable={false}
              style={{
                maxWidth: '100%',
                maxHeight: isFullscreen 
                  ? '100vh' 
                  : (isMobile ? 'calc(100vh - 200px)' : 'none'),
                // 横屏时自动旋转适配
                width: isFullscreen && isLandscape ? 'auto' : (isFullscreen ? '100%' : 'auto'),
                height: isFullscreen ? 'auto' : 'auto',
                objectFit: 'contain',  // 保持比例适配屏幕
                transform: `translate(${position.x}px, ${position.y}px) scale(${scale})`,
                transformOrigin: 'center center',
                transition: isDragging ? 'none' : 'transform 0.1s ease-out',
              }}
            />
          </div>

          {/* 进度提示 */}
          {!isFullscreen && (
            <div style={{ color: '#666', fontSize: 12 }}>
              进度: {Math.round((currentPdfPage + 1) / pdfPages.length * 100)}%
            </div>
          )}
        </div>
      </Content>

      {/* 移动端底部控制按钮 - 非全屏 */}
      {isMobile && pdfPages.length > 0 && !isFullscreen && (
        <div style={{
          position: 'fixed',
          bottom: 20,
          left: '50%',
          transform: 'translateX(-50%)',
          display: 'flex',
          gap: 8,
          zIndex: 100,
        }}>
          <Button onClick={goToPrevPage} disabled={currentPdfPage === 0}>
            ← 上一页
          </Button>
          <Tag color="blue">{currentPdfPage + 1}/{pdfPages.length}</Tag>
          <Button onClick={goToNextPage} disabled={currentPdfPage === pdfPages.length - 1}>
            下一页 →
          </Button>
          <Button icon={<FullscreenOutlined />} onClick={toggleFullscreen}>全屏</Button>
        </div>
      )}
    </Layout>
  );
}