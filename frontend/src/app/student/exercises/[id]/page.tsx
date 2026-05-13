"use client";

import { useState, useEffect, useCallback, useRef } from 'react';
import { useRouter, useParams, useSearchParams } from 'next/navigation';
import { Card, Button, Radio, Checkbox, Tag, message, Result, Spin, Progress, Alert } from 'antd';
import { ThunderboltOutlined, WarningOutlined } from '@ant-design/icons';
import { http } from '@/lib/http';

interface Question {
  id: number;
  content: string;
  options: string[];
}

interface ResultItem {
  question_id: number;
  user_answer: string;
  correct_answer: string;
  is_correct: boolean;
  explanation: string;
}

export default function StudentExercisesPage() {
  const router = useRouter();
  const params = useParams();
  const searchParams = useSearchParams();
  const chapterId = params.id as string;
  const isSelfTest = searchParams.get('self_test') === '1';
  
  const [loading, setLoading] = useState(true);
  const [questions, setQuestions] = useState<Question[]>([]);
  const [answers, setAnswers] = useState<Record<number, string>>({});
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState<{success: boolean; score: string; results: ResultItem[]; message: string; completed?: boolean} | null>(null);

  // 防作弊状态
  const [tabWarnings, setTabWarnings] = useState(0);
  const [focused, setFocused] = useState(true);
  const [startTime] = useState(Date.now());
  const [elapsed, setElapsed] = useState(0);
  const timerRef = useRef<NodeJS.Timeout | null>(null);
  
  // Fisher-Yates 洗牌
  const shuffle = <T extends unknown>(arr: T[]): T[] => {
    const a = [...arr];
    for (let i = a.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [a[i], a[j]] = [a[j], a[i]];
    }
    return a;
  };

  // 切标签/失焦检测
  useEffect(() => {
    const handleVisibility = () => {
      if (document.hidden) {
        setFocused(false);
        setTabWarnings(prev => {
          const next = prev + 1;
          if (next >= 3 && !result) {
            message.error(`⚠️ 已检测到 ${next} 次离开页面，可能被标记为作弊行为`);
          } else if (!result) {
            message.warning(`请不要在练习时切换窗口（${next}/3）`);
          }
          return next;
        });
      } else {
        setFocused(true);
      }
    };

    timerRef.current = setInterval(() => {
      setElapsed(Math.floor((Date.now() - startTime) / 1000));
    }, 1000);

    document.addEventListener('visibilitychange', handleVisibility);
    window.addEventListener('blur', () => setFocused(false));
    window.addEventListener('focus', () => setFocused(true));

    return () => {
      document.removeEventListener('visibilitychange', handleVisibility);
      window.removeEventListener('blur', () => setFocused(false));
      window.removeEventListener('focus', () => setFocused(true));
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [startTime, result]);

  useEffect(() => { fetchExercises(); }, [chapterId]);

  const fetchExercises = async () => {
    try {
      const res = await http.get(`/student/chapters/${chapterId}/exercises`);
      // 防作弊：随机化选项顺序
      const shuffled = (res.questions || []).map((q: Question) => ({
        ...q,
        options: shuffle(q.options)
      }));
      setQuestions(isSelfTest ? shuffled : res.questions || []);
    } catch (e) { message.error((e as Error).message || '获取练习失败'); }
    finally { setLoading(false); }
  };

  const handleAnswerChange = (questionId: number, answer: string) => {
    setAnswers(prev => ({ ...prev, [questionId]: answer }));
  };

  const handleSubmit = async () => {
    if (Object.keys(answers).length < questions.length) {
      message.warning('请完成所有题目');
      return;
    }

    setSubmitting(true);
    try {
      const answerList = Object.entries(answers).map(([qid, ans]) => ({
        question_id: parseInt(qid),
        answer: ans
      }));
      
      const res = await http.post(`/student/chapters/${chapterId}/submit-exercises`, {
        answers: answerList,
        self_test: isSelfTest,
        tab_switch_count: tabWarnings,
        time_spent: Math.floor((Date.now() - startTime) / 1000)
      });
      setResult(res);
    } catch (e) { message.error((e as Error).message || '提交失败'); }
    finally { setSubmitting(false); }
  };

  const handleRetry = () => { setAnswers({}); setResult(null); };
  const handleBack = () => router.push('/student/chapters');

  if (loading) {
    return <div className="min-h-screen flex items-center justify-center"><Spin size="large" /></div>;
  }

  if (result) {
    const correctCount = result.results.filter((r: ResultItem) => r.is_correct).length;
    const totalCount = result.results.length;
    const passPercent = Math.round((correctCount / totalCount) * 100);

    return (
      <div className="min-h-screen bg-gray-50 py-8">
        <div className="max-w-3xl mx-auto px-4">
          <Card className="mb-6">
            <Result
              status={result.success ? 'success' : 'error'}
              title={isSelfTest ? (result.success ? '自测通过！✅' : '自测未通过') : (result.success ? '练习通过！' : '练习未通过')}
              subTitle={
                <div>
                  <div>得分: {result.score} ({passPercent}%)</div>
                  {isSelfTest && result.success && (
                    <div style={{ color: '#52c41a', marginTop: 4 }}>
                      <ThunderboltOutlined /> 自测模式 · 本节已直接完成
                    </div>
                  )}
                  {!isSelfTest && result.success && (
                    <div style={{ color: '#faad14', marginTop: 4 }}>
                      等待教练发布随堂测验
                    </div>
                  )}
                </div>
              }
              extra={[
                <Button type="primary" key="back" onClick={handleBack}>
                  {result.completed ? '返回主页' : '返回学习'}
                </Button>,
                !result.success && <Button key="retry" onClick={handleRetry}>重新练习</Button>,
                result.completed && (
                  <Button key="home" onClick={() => router.push('/student')}>
                    <ThunderboltOutlined /> 自测通关！
                  </Button>
                ),
              ]}
            />
          </Card>

          <Card title="题目解析">
            {result.results.map((item: ResultItem, idx: number) => (
              <div key={idx} className={`mb-4 p-4 rounded ${item.is_correct ? 'bg-green-50' : 'bg-red-50'}`}>
                <div className="font-medium mb-2">第{idx + 1}题: {item.is_correct ? '✅ 正确' : '❌ 错误'}</div>
                <div className="text-sm mb-2">
                  你的答案: <Tag color={item.is_correct ? 'green' : 'red'}>{item.user_answer || '未作答'}</Tag>
                  {!item.is_correct && <> 正确答案: <Tag color="green">{item.correct_answer}</Tag></>}
                </div>
                {item.explanation && (
                  <div className="text-gray-600 text-sm bg-white p-2 rounded">💡 {item.explanation}</div>
                )}
              </div>
            ))}
          </Card>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-3xl mx-auto px-4">
        <Card className="mb-4">
          <div className="flex items-center justify-between">
            <h1 className="text-lg font-bold">
              {isSelfTest ? (
                <span><ThunderboltOutlined style={{ color: '#faad14', marginRight: 8 }} />自测模式 · 课后练习</span>
              ) : '课后练习'}
            </h1>
            <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
              <span style={{ fontSize: 13, color: '#999' }}>⏱ {Math.floor(elapsed / 60)}:{String(elapsed % 60).padStart(2, '0')}</span>
              <Progress 
                percent={Math.round((Object.keys(answers).length / questions.length) * 100)} 
                format={(p) => `${p}%`} size="small" style={{ width: 120 }}
              />
            </div>
          </div>
          {tabWarnings > 0 && (
            <Alert
              type="warning"
              showIcon
              icon={<WarningOutlined />}
              message={`已检测到 ${tabWarnings} 次离开页面`}
              description={tabWarnings >= 3 ? '多次切换窗口可能被标记为作弊' : '请保持专注，不要切换窗口'}
              style={{ marginTop: 10 }}
            />
          )}
          {!focused && !result && (
            <Alert type="error" message="⚠️ 窗口失去焦点" style={{ marginTop: 10 }} />
          )}
        </Card>

        {questions.map((q, idx) => (
          <Card key={q.id} className="mb-4">
            <div className="font-medium mb-3">
              <span className="text-blue-600 mr-2">{idx + 1}.</span>
              {q.content}
            </div>
            
            {q.options.length > 2 ? (
              <Checkbox.Group
                value={answers[q.id]?.split(',') || []}
                onChange={(vals: string[]) => handleAnswerChange(q.id, vals.join(','))}
              >
                {q.options.map((opt, oidx) => (
                  <div key={oidx} className="ml-4">
                    <Checkbox value={opt.charAt(0)}>{opt}</Checkbox>
                  </div>
                ))}
              </Checkbox.Group>
            ) : (
              <Radio.Group
                value={answers[q.id]}
                onChange={(e) => handleAnswerChange(q.id, e.target.value)}
              >
                {q.options.map((opt, oidx) => (
                  <div key={oidx} className="ml-4">
                    <Radio value={opt.charAt(0)}>{opt}</Radio>
                  </div>
                ))}
              </Radio.Group>
            )}
          </Card>
        ))}

        <div className="text-center mb-8">
          <Button 
            type="primary" size="large" loading={submitting} onClick={handleSubmit}
            disabled={Object.keys(answers).length < questions.length}
          >
            提交答案
          </Button>
        </div>
      </div>
    </div>
  );
}
