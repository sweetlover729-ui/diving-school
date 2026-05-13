"use client";

import { useState, useEffect } from 'react';
import { Card, Progress, Tag, Button, message, Modal, Radio, Space, Statistic, Row, Col } from 'antd';
import { 
  BookOutlined, CheckCircleOutlined, LockOutlined, UnlockOutlined,
  ClockCircleOutlined, TrophyOutlined, ArrowRightOutlined, ArrowLeftOutlined,
  QuestionCircleOutlined, EyeOutlined
} from '@ant-design/icons';
import { http } from '@/lib/http';

interface LearningUnit {
  id: string;
  type: string;
  content: string;
  level: number;
  keywords?: string[];
  quiz?: {
    id: string;
    type: string;
    question: string;
    options: string[];
    correct: number;
    explanation: string;
  };
}

interface LearningSection {
  id: string;
  title: string;
  level: number;
  units: LearningUnit[];
  estimated_time: number;
  key_concepts: string[];
}

interface InteractiveTextbook {
  id: string;
  title: string;
  total_sections: number;
  sections: LearningSection[];
  key_concepts_map: Record<string, string>;
}

interface SectionCardProps {
  section: LearningSection;
  index: number;
  isCompleted: boolean;
  isLocked: boolean;
  isActive: boolean;
  onClick: () => void;
}

// 章节卡片组件
function SectionCard({ section, index, isCompleted, isLocked, isActive, onClick }: SectionCardProps) {
  const getStatusIcon = () => {
    if (isLocked) return <LockOutlined style={{ color: '#999' }} />;
    if (isCompleted) return <CheckCircleOutlined style={{ color: '#52c41a' }} />;
    if (isActive) return <EyeOutlined style={{ color: '#1890ff' }} />;
    return <UnlockOutlined style={{ color: '#faad14' }} />;
  };

  const getStatusColor = () => {
    if (isLocked) return '#f5f5f5';
    if (isCompleted) return '#f6ffed';
    if (isActive) return '#e6f7ff';
    return '#fff';
  };

  const getBorderColor = () => {
    if (isLocked) return '#d9d9d9';
    if (isCompleted) return '#b7eb8f';
    if (isActive) return '#1890ff';
    return '#d9d9d9';
  };

  return (
    <div
      onClick={!isLocked ? onClick : undefined}
      style={{
        padding: 16,
        background: getStatusColor(),
        border: `2px solid ${getBorderColor()}`,
        borderRadius: 8,
        cursor: isLocked ? 'not-allowed' : 'pointer',
        opacity: isLocked ? 0.6 : 1,
        transition: 'all 0.3s',
        marginBottom: 12,
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <div style={{ 
            width: 40, 
            height: 40, 
            borderRadius: '50%', 
            background: isActive ? '#1890ff' : isCompleted ? '#52c41a' : '#f0f0f0',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: isActive || isCompleted ? '#fff' : '#666',
            fontWeight: 'bold'
          }}>
            {index + 1}
          </div>
          <div>
            <div style={{ fontWeight: 500, fontSize: 15 }}>{section.title}</div>
            <div style={{ fontSize: 12, color: '#666', marginTop: 4 }}>
              <ClockCircleOutlined /> {section.estimated_time}分钟
              {section.key_concepts && section.key_concepts.length > 0 && (
                <span style={{ marginLeft: 12 }}>
                  <BookOutlined /> {section.key_concepts.length}个知识点
                </span>
              )}
            </div>
          </div>
        </div>
        <div style={{ fontSize: 20 }}>
          {getStatusIcon()}
        </div>
      </div>
      
      {section.key_concepts && section.key_concepts.length > 0 && (
        <div style={{ marginTop: 8, paddingLeft: 52 }}>
          {section.key_concepts.slice(0, 3).map((concept, i) => (
            <Tag key={i} style={{ marginRight: 4, marginBottom: 4 }}>
              {concept}
            </Tag>
          ))}
          {section.key_concepts.length > 3 && (
            <Tag style={{ marginBottom: 4 }}>+{section.key_concepts.length - 3}</Tag>
          )}
        </div>
      )}
    </div>
  );
}

interface InteractiveReaderProps {
  textbookId: string;
  classId?: string;
}

// 互动式阅读器主组件
export default function InteractiveReader({ textbookId, classId }: InteractiveReaderProps) {
  const [loading, setLoading] = useState(true);
  const [textbook, setTextbook] = useState<InteractiveTextbook | null>(null);
  const [currentSectionIndex, setCurrentSectionIndex] = useState(0);
  const [completedSections, setCompletedSections] = useState<string[]>([]);
  const [currentUnitIndex, setCurrentUnitIndex] = useState(0);
  const [quizModalVisible, setQuizModalVisible] = useState(false);
  const [currentQuiz, setCurrentQuiz] = useState<any>(null);
  const [quizAnswer, setQuizAnswer] = useState<number | null>(null);
  const [quizSubmitted, setQuizSubmitted] = useState(false);
  const [readingStartTime, setReadingStartTime] = useState<number>(Date.now());
  const [scrollProgress, setScrollProgress] = useState(0);

  useEffect(() => {
    fetchTextbook();
  }, [textbookId]);

  const fetchTextbook = async () => {
    try {
      setLoading(true);
      const data = await http.get(`/admin/textbooks/${textbookId}/interactive`);
      setTextbook(data);
      
      // 加载已完成的章节（从本地存储或服务器）
      const saved = localStorage.getItem(`textbook_${textbookId}_completed`);
      if (saved) {
        setCompletedSections(JSON.parse(saved));
      }
    } catch (e) {
      message.error(e.message || '加载教材失败');
    } finally {
      setLoading(false);
    }
  };

  const currentSection = textbook?.sections[currentSectionIndex];

  // 计算总体进度
  const totalProgress = textbook ? Math.round((completedSections.length / textbook.total_sections) * 100) : 0;

  // 检查章节是否锁定
  const isSectionLocked = (index: number) => {
    if (index === 0) return false;
    // 前一章节必须完成
    const prevSectionId = textbook?.sections[index - 1]?.id;
    return prevSectionId ? !completedSections.includes(prevSectionId) : true;
  };

  // 开始阅读章节
  const startSection = (index: number) => {
    if (isSectionLocked(index)) {
      message.warning('请先完成前面的章节');
      return;
    }
    setCurrentSectionIndex(index);
    setCurrentUnitIndex(0);
    setReadingStartTime(Date.now());
    setScrollProgress(0);
  };

  // 处理单元滚动
  const handleUnitScroll = (e: React.UIEvent<HTMLDivElement>) => {
    const target = e.target as HTMLDivElement;
    const scrollPercent = (target.scrollTop / (target.scrollHeight - target.clientHeight)) * 100;
    setScrollProgress(scrollPercent);
  };

  // 触发测验
  const triggerQuiz = (quiz: Record<string, unknown>) => {
    setCurrentQuiz(quiz);
    setQuizModalVisible(true);
    setQuizAnswer(null);
    setQuizSubmitted(false);
  };

  // 提交测验
  const submitQuiz = () => {
    if (quizAnswer === null) {
      message.warning('请选择答案');
      return;
    }
    
    setQuizSubmitted(true);
    
    if (quizAnswer === currentQuiz.correct) {
      message.success('回答正确！');
      setTimeout(() => {
        setQuizModalVisible(false);
        // 继续阅读
        nextUnit();
      }, 1500);
    } else {
      message.error('回答错误，请重试');
      setTimeout(() => {
        setQuizSubmitted(false);
        setQuizAnswer(null);
      }, 1500);
    }
  };

  // 下一个单元
  const nextUnit = () => {
    if (!currentSection) return;
    
    if (currentUnitIndex < currentSection.units.length - 1) {
      setCurrentUnitIndex(currentUnitIndex + 1);
    } else {
      // 章节完成
      completeSection();
    }
  };

  // 上一个单元
  const prevUnit = () => {
    if (currentUnitIndex > 0) {
      setCurrentUnitIndex(currentUnitIndex - 1);
    }
  };

  // 完成章节
  const completeSection = () => {
    if (!currentSection) return;
    
    const sectionId = currentSection.id;
    if (!completedSections.includes(sectionId)) {
      const newCompleted = [...completedSections, sectionId];
      setCompletedSections(newCompleted);
      localStorage.setItem(`textbook_${textbookId}_completed`, JSON.stringify(newCompleted));
      
      // 计算学习时长
      const duration = Math.round((Date.now() - readingStartTime) / 60000);
      message.success(`章节完成！学习时长: ${duration}分钟`);
    }
    
    // 返回章节列表或进入下一章
    if (currentSectionIndex < (textbook?.sections.length || 0) - 1) {
      Modal.confirm({
        title: '章节完成',
        content: '是否进入下一章节？',
        onOk: () => startSection(currentSectionIndex + 1),
        onCancel: () => setCurrentUnitIndex(0),
      });
    } else {
      Modal.success({
        title: '恭喜！',
        content: '您已完成全部章节学习！',
      });
    }
  };

  // 渲染当前单元
  const renderUnit = (unit: LearningUnit) => {
    switch (unit.type) {
      case 'heading':
        return (
          <h2 style={{ 
            fontSize: unit.level === 1 ? 24 : 20, 
            fontWeight: 'bold',
            marginBottom: 16,
            color: '#1a1a2e'
          }}>
            {unit.content}
          </h2>
        );
      
      case 'key_concept':
        return (
          <div style={{ 
            padding: 16, 
            background: '#e6f7ff', 
            borderLeft: '4px solid #1890ff',
            borderRadius: 4,
            marginBottom: 16
          }}>
            <div style={{ fontWeight: 500, marginBottom: 8, color: '#1890ff' }}>
              <BookOutlined /> 关键概念
            </div>
            <div>{unit.content}</div>
            {unit.keywords && unit.keywords.length > 0 && (
              <div style={{ marginTop: 8 }}>
                {unit.keywords.map((kw, i) => (
                  <Tag key={i} color="blue">{kw}</Tag>
                ))}
              </div>
            )}
          </div>
        );
      
      case 'quiz_placeholder':
        return (
          <div style={{ marginBottom: 16 }}>
            <div style={{ 
              padding: 16, 
              background: '#f6ffed',
              border: '1px dashed #b7eb8f',
              borderRadius: 4,
              textAlign: 'center'
            }}>
              <QuestionCircleOutlined style={{ fontSize: 24, color: '#52c41a', marginBottom: 8 }} />
              <div style={{ marginBottom: 8 }}>本节包含一个随堂测验</div>
              <Button 
                type="primary" 
                icon={<QuestionCircleOutlined />}
                onClick={() => unit.quiz && triggerQuiz(unit.quiz)}
              >
                开始测验
              </Button>
            </div>
          </div>
        );
      
      default:
        return (
          <p style={{ 
            fontSize: 16, 
            lineHeight: 1.8, 
            marginBottom: 16,
            textAlign: 'justify'
          }}>
            {unit.content}
          </p>
        );
    }
  };

  if (loading) {
    return <Card loading title="加载互动教材..." />;
  }

  if (!textbook) {
    return <Card>教材加载失败</Card>;
  }

  // 章节列表视图
  if (!currentSection) {
    return (
      <div>
        <Card style={{ marginBottom: 24 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div>
              <h2 style={{ margin: 0 }}>{textbook.title}</h2>
              <p style={{ color: '#666', marginTop: 8 }}>
                共 {textbook.total_sections} 个章节 · 已完成 {completedSections.length} 个
              </p>
            </div>
            <div style={{ textAlign: 'center' }}>
              <Progress type="circle" percent={totalProgress} width={80} />
              <div style={{ fontSize: 12, color: '#666', marginTop: 4 }}>总进度</div>
            </div>
          </div>
        </Card>

        <Row gutter={24}>
          <Col span={16}>
            <Card title="章节列表">
              {textbook.sections.map((section, index) => (
                <SectionCard
                  key={section.id}
                  section={section}
                  index={index}
                  isCompleted={completedSections.includes(section.id)}
                  isLocked={isSectionLocked(index)}
                  isActive={index === currentSectionIndex}
                  onClick={() => startSection(index)}
                />
              ))}
            </Card>
          </Col>
          <Col span={8}>
            <Card title="学习统计">
              <Statistic 
                title="已完成章节" 
                value={completedSections.length} 
                suffix={`/ ${textbook.total_sections}`}
              />
              <div style={{ marginTop: 16 }}>
                <div style={{ marginBottom: 8 }}>学习进度</div>
                <Progress percent={totalProgress} status={totalProgress === 100 ? 'success' : 'active'} />
              </div>
            </Card>
            
            <Card title="知识点概览" style={{ marginTop: 16 }}>
              {Object.keys(textbook.key_concepts_map).slice(0, 10).map((concept, i) => (
                <Tag key={i} style={{ marginBottom: 8 }}>{concept}</Tag>
              ))}
              {Object.keys(textbook.key_concepts_map).length > 10 && (
                <Tag>+{Object.keys(textbook.key_concepts_map).length - 10} 更多</Tag>
              )}
            </Card>
          </Col>
        </Row>
      </div>
    );
  }

  // 阅读视图
  const currentUnit = currentSection.units[currentUnitIndex];

  return (
    <div>
      {/* 顶部导航 */}
      <Card style={{ marginBottom: 16 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Button icon={<ArrowLeftOutlined />} onClick={() => setCurrentSectionIndex(-1)}>
            返回章节列表
          </Button>
          <div style={{ textAlign: 'center' }}>
            <div style={{ fontWeight: 500 }}>{currentSection.title}</div>
            <div style={{ fontSize: 12, color: '#666' }}>
              单元 {currentUnitIndex + 1} / {currentSection.units.length}
            </div>
          </div>
          <div style={{ width: 100 }}>
            <Progress 
              percent={Math.round(((currentUnitIndex + 1) / currentSection.units.length) * 100)} 
              size="small"
            />
          </div>
        </div>
      </Card>

      <Row gutter={24}>
        <Col span={18}>
          {/* 阅读区域 */}
          <Card 
            style={{ minHeight: 500 }}
            bodyStyle={{ padding: 24 }}
          >
            <div 
              style={{ 
                maxHeight: 600, 
                overflowY: 'auto',
                paddingRight: 16
              }}
              onScroll={handleUnitScroll}
            >
              {renderUnit(currentUnit)}
            </div>
          </Card>

          {/* 底部导航 */}
          <Card style={{ marginTop: 16 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <Button 
                icon={<ArrowLeftOutlined />}
                onClick={prevUnit}
                disabled={currentUnitIndex === 0}
              >
                上一个
              </Button>
              <Button 
                type="primary"
                icon={<ArrowRightOutlined />}
                onClick={nextUnit}
              >
                {currentUnitIndex < currentSection.units.length - 1 ? '下一个' : '完成章节'}
              </Button>
            </div>
          </Card>
        </Col>

        <Col span={6}>
          {/* 侧边栏 */}
          <Card title="本章进度" size="small">
            <Progress 
              percent={Math.round(((currentUnitIndex + 1) / currentSection.units.length) * 100)} 
            />
            <div style={{ marginTop: 8, fontSize: 12, color: '#666' }}>
              已读 {currentUnitIndex + 1} / {currentSection.units.length} 单元
            </div>
          </Card>

          <Card title="本章知识点" size="small" style={{ marginTop: 16 }}>
            {currentSection.key_concepts?.map((concept, i) => (
              <div key={i} style={{ 
                padding: '8px 0', 
                borderBottom: i < (currentSection.key_concepts?.length || 0) - 1 ? '1px solid #f0f0f0' : 'none'
              }}>
                <BookOutlined style={{ color: '#1890ff', marginRight: 8 }} />
                {concept}
              </div>
            ))}
          </Card>

          <Card title="预计时间" size="small" style={{ marginTop: 16 }}>
            <div style={{ textAlign: 'center' }}>
              <ClockCircleOutlined style={{ fontSize: 24, color: '#faad14' }} />
              <div style={{ fontSize: 20, fontWeight: 'bold', marginTop: 8 }}>
                {currentSection.estimated_time}分钟
              </div>
            </div>
          </Card>
        </Col>
      </Row>

      {/* 测验模态框 */}
      <Modal
        title="随堂测验"
        open={quizModalVisible}
        onCancel={() => setQuizModalVisible(false)}
        footer={[
          <Button key="cancel" onClick={() => setQuizModalVisible(false)}>
            取消
          </Button>,
          <Button 
            key="submit" 
            type="primary" 
            onClick={submitQuiz}
            disabled={quizAnswer === null || quizSubmitted}
          >
            提交答案
          </Button>
        ]}
        width={600}
      >
        {currentQuiz && (
          <div>
            <div style={{ fontSize: 16, fontWeight: 500, marginBottom: 16 }}>
              {currentQuiz.question}
            </div>
            <Radio.Group 
              onChange={(e) => setQuizAnswer(e.target.value)}
              value={quizAnswer}
              disabled={quizSubmitted}
            >
              <Space direction="vertical" style={{ width: '100%' }}>
                {currentQuiz.options.map((option: string, index: number) => (
                  <Radio 
                    key={index} 
                    value={index}
                    style={{
                      padding: 12,
                      background: quizSubmitted 
                        ? index === currentQuiz.correct 
                          ? '#f6ffed' 
                          : quizAnswer === index 
                            ? '#fff2f0' 
                            : '#f5f5f5'
                        : '#f5f5f5',
                      borderRadius: 4,
                      width: '100%'
                    }}
                  >
                    {option}
                    {quizSubmitted && index === currentQuiz.correct && (
                      <CheckCircleOutlined style={{ color: '#52c41a', marginLeft: 8 }} />
                    )}
                  </Radio>
                ))}
              </Space>
            </Radio.Group>
            
            {quizSubmitted && quizAnswer !== currentQuiz.correct && (
              <div style={{ marginTop: 16, padding: 12, background: '#fff7e6', borderRadius: 4 }}>
                <div style={{ fontWeight: 500, marginBottom: 4 }}>解析：</div>
                <div>{currentQuiz.explanation}</div>
              </div>
            )}
          </div>
        )}
      </Modal>
    </div>
  );
}
