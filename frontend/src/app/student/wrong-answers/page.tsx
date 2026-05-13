'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { Card, List, Tag, Button, Empty, Spin, message } from 'antd'
import { ArrowLeftOutlined, CloseCircleOutlined, CheckCircleOutlined } from '@ant-design/icons'
import { http } from '@/lib/http'

interface WrongQuestion {
  id: number
  test_title: string
  content: string
  options: Record<string, unknown>
  correct_answer: unknown
  user_answer: unknown
  explanation: string
}

export default function WrongAnswersPage() {
  const router = useRouter()
  const [loading, setLoading] = useState(true)
  const [questions, setQuestions] = useState<WrongQuestion[]>([])

  useEffect(() => {
    async function fetchWrongAnswers() {
      try {
        const data = await http.get('/student/wrong-answers')
        setQuestions(Array.isArray(data) ? data : [])
      } catch (e) {
        message.error('加载错题本失败: ' + (e.message || ''))
      } finally {
        setLoading(false)
      }
    }
    fetchWrongAnswers()
  }, [])

  const renderAnswer = (answer: unknown) => {
    if (Array.isArray(answer)) return answer.join(', ')
    return String(answer ?? '-')
  }

  const renderOptions = (options: Record<string, unknown>) => {
    if (!options || typeof options !== 'object') return null
    return (
      <div style={{ marginTop: 8 }}>
        {Object.entries(options).map(([key, value]) => (
          <div key={key} style={{ fontSize: 13, lineHeight: 1.8, color: '#555' }}>
            {key}. {String(value)}
          </div>
        ))}
      </div>
    )
  }

  if (loading) {
    return (
      <div style={{ padding: 100, textAlign: 'center' }}>
        <Spin size="large" tip="加载错题本..." />
      </div>
    )
  }

  return (
    <div style={{ padding: '16px 24px', maxWidth: 800, margin: '0 auto' }}>
      <div style={{ marginBottom: 16, display: 'flex', alignItems: 'center', gap: 12 }}>
        <Button icon={<ArrowLeftOutlined />} onClick={() => router.push('/student')}>返回主页</Button>
        <h2 style={{ margin: 0, fontSize: 18 }}>错题本</h2>
        <Tag color="red">{questions.length} 题</Tag>
      </div>

      {questions.length === 0 ? (
        <Empty description="暂无错题，继续加油！" />
      ) : (
        <List
          dataSource={questions}
          renderItem={(q, idx) => (
            <Card
              size="small"
              style={{ marginBottom: 12 }}
              title={
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 14 }}>
                  <CloseCircleOutlined style={{ color: '#ff4d4f' }} />
                  <span>第 {idx + 1} 题</span>
                  <Tag color="blue" style={{ fontSize: 11 }}>{q.test_title}</Tag>
                </div>
              }
            >
              <div style={{ fontSize: 14, lineHeight: 1.8, marginBottom: 8 }}>{q.content}</div>
              {renderOptions(q.options)}
              <div style={{ marginTop: 12, padding: '8px 12px', background: '#fff1f0', borderRadius: 6, border: '1px solid #ffa39e' }}>
                <div style={{ fontSize: 13 }}>
                  <CloseCircleOutlined style={{ color: '#ff4d4f', marginRight: 6 }} />
                  你的答案：<strong>{renderAnswer(q.user_answer)}</strong>
                </div>
              </div>
              <div style={{ marginTop: 8, padding: '8px 12px', background: '#f6ffed', borderRadius: 6, border: '1px solid #b7eb8f' }}>
                <div style={{ fontSize: 13 }}>
                  <CheckCircleOutlined style={{ color: '#52c41a', marginRight: 6 }} />
                  正确答案：<strong>{renderAnswer(q.correct_answer)}</strong>
                </div>
              </div>
              {q.explanation && (
                <div style={{ marginTop: 8, fontSize: 12, color: '#888', fontStyle: 'italic' }}>
                  解析：{q.explanation}
                </div>
              )}
            </Card>
          )}
        />
      )}
    </div>
  )
}
