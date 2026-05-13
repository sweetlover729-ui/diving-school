'use client';

import { useEffect, useState } from 'react';
import { useRouter, useParams } from 'next/navigation';
import { Card, Button, Radio, Checkbox, message, Progress, Space, Modal } from 'antd';
import { ClockCircleOutlined, CheckOutlined } from '@ant-design/icons';
import { http } from '@/lib/http';

export default function TestPage() {
  const router = useRouter();
  const params = useParams();
  const testId = params.id;

  const [test, setTest] = useState<any>({});
  const [questions, setQuestions] = useState<any[]>([]);
  const [answers, setAnswers] = useState<Record<number, any>>({});
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [timeLeft, setTimeLeft] = useState<number | null>(null);

  useEffect(() => {
    fetchTest();
  }, [testId]);

  useEffect(() => {
    if (timeLeft === null || timeLeft <= 0) return;
    
    const timer = setInterval(() => {
      setTimeLeft(t => {
        if (t === null || t <= 0) return 0;
        return t - 1;
      });
    }, 1000);

    return () => clearInterval(timer);
  }, [timeLeft]);

  const fetchTest = async () => {
    try {
      const data = await http.get(`/student/tests/${testId}`);
      setTest(data);
      setQuestions(data.questions || []);
      
      if (data.duration) {
        setTimeLeft(data.duration * 60);
      }
    } catch (e) {
      message.error(e.message || '获取测验失败');
      router.push('/student/tests');
    } finally {
      setLoading(false);
    }
  };

  const handleAnswer = (questionId: number, answer: unknown) => {
    setAnswers({ ...answers, [questionId]: answer });
  };

  const handleSubmit = () => {
    Modal.confirm({
      title: '确认提交',
      content: `已答 ${Object.keys(answers).length}/${questions.length} 题，确定提交吗？`,
      onOk: async () => {
        setSubmitting(true);
        try {
          const answerList = Object.entries(answers).map(([qid, ans]) => ({
            question_id: parseInt(qid),
            answer: ans
          }));

          const result = await http.post(`/student/tests/${testId}/submit`, {
            answers: answerList
          });

          message.success(`提交成功！得分: ${result.score}/${result.total_score}`);
          router.push('/student/scores');
        } catch (e) {
          message.error(e.message || '提交失败');
        } finally {
          setSubmitting(false);
        }
      }
    });
  };

  const formatTime = (seconds: number) => {
    const m = Math.floor(seconds / 60);
    const s = seconds % 60;
    return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
  };

  if (loading) {
    return <div style={{ padding: 24 }}>加载中...</div>;
  }

  return (
    <div style={{ padding: 24, maxWidth: 900, margin: '0 auto' }}>
      <Card>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
          <div>
            <h2 style={{ margin: 0 }}>{test.title}</h2>
            <p style={{ color: '#666', margin: 0 }}>共 {questions.length} 题，总分 {test.total_score} 分</p>
          </div>
          {timeLeft !== null && (
            <div style={{ fontSize: 24, color: timeLeft < 300 ? '#ff4d4f' : '#1890ff' }}>
              <ClockCircleOutlined /> {formatTime(timeLeft)}
            </div>
          )}
        </div>

        <Progress 
          percent={Math.round(Object.keys(answers).length / questions.length * 100)} 
          format={() => `已答 ${Object.keys(answers).length}/${questions.length}`}
        />
      </Card>

      {questions.map((q, index) => (
        <Card key={q.id} style={{ marginTop: 16 }}>
          <div style={{ marginBottom: 16 }}>
            <span style={{ fontWeight: 'bold' }}>{index + 1}. </span>
            <span>{q.content}</span>
            <span style={{ marginLeft: 8, color: '#999' }}>
              ({q.question_type === 'single' ? '单选' : q.question_type === 'multiple' ? '多选' : '判断'})
            </span>
          </div>

          {q.question_type === 'single' && (
            <Radio.Group
              value={answers[q.id]}
              onChange={(e) => handleAnswer(q.id, e.target.value)}
            >
              <Space direction="vertical">
                {q.options?.map((opt: string, i: number) => (
                  <Radio key={i} value={String.fromCharCode(65 + i)}>
                    {opt}
                  </Radio>
                ))}
              </Space>
            </Radio.Group>
          )}

          {q.question_type === 'multiple' && (
            <Checkbox.Group
              value={answers[q.id] || []}
              onChange={(vals) => handleAnswer(q.id, vals)}
            >
              <Space direction="vertical">
                {q.options?.map((opt: string, i: number) => (
                  <Checkbox key={i} value={String.fromCharCode(65 + i)}>
                    {opt}
                  </Checkbox>
                ))}
              </Space>
            </Checkbox.Group>
          )}

          {q.question_type === 'judge' && (
            <Radio.Group
              value={answers[q.id]}
              onChange={(e) => handleAnswer(q.id, e.target.value)}
            >
              <Radio value="A">正确</Radio>
              <Radio value="B">错误</Radio>
            </Radio.Group>
          )}
        </Card>
      ))}

      <Card style={{ marginTop: 16, textAlign: 'center' }}>
        <Space>
          <Button onClick={() => router.push('/student/tests')}>返回</Button>
          <Button
            type="primary"
            icon={<CheckOutlined />}
            loading={submitting}
            onClick={handleSubmit}
          >
            提交答卷
          </Button>
        </Space>
      </Card>
    </div>
  );
}