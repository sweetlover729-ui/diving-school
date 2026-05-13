'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { Card, Table, Progress, Button, message, Space } from 'antd'
import { ArrowLeftOutlined, BookOutlined } from '@ant-design/icons'
import { http } from '@/lib/http'

interface StudentProgress {
  user_id: number
  name: string
  reading_progress: number
  tests_completed: number
  tests_total: number
  avg_score: number
}

export default function InstructorProgressPage() {
  const router = useRouter()
  const [loading, setLoading] = useState(true)
  const [students, setStudents] = useState<StudentProgress[]>([])

  useEffect(() => {
    fetchProgress()
  }, [])

  const fetchProgress = async () => {
    try {
      const res = await http.get('/instructor/progress')
      setStudents(Array.isArray(res) ? res : [])
    } catch (e) {
      message.error('获取学员进度失败')
    } finally {
      setLoading(false)
    }
  }

  const columns = [
    {
      title: '学员姓名',
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: '阅读进度',
      key: 'reading',
      render: (_: unknown, record: StudentProgress) => (
        <Progress percent={Math.round(record.reading_progress || 0)} size="small" />
      ),
    },
    {
      title: '测验完成',
      key: 'tests',
      render: (_: unknown, record: StudentProgress) => `${record.tests_completed}/${record.tests_total}`,
    },
    {
      title: '平均成绩',
      dataIndex: 'avg_score',
      key: 'avg_score',
      render: (score: number) => score > 0 ? `${score}分` : '-',
    },
    {
      title: '操作',
      key: 'action',
      render: (_: unknown, record: StudentProgress) => (
        <Button type="link" icon={<BookOutlined />} onClick={() => router.push(`/instructor/student/${record.user_id}`)}>
          详情
        </Button>
      ),
    },
  ]

  return (
    <div style={{ padding: 24, maxWidth: 1200, margin: '0 auto' }}>
      <Space style={{ marginBottom: 16 }}>
        <Button icon={<ArrowLeftOutlined />} onClick={() => router.push('/instructor')}>
          返回工作台
        </Button>
      </Space>

      <Card title="学员学习进度">
        <Table
          dataSource={students}
          columns={columns}
          rowKey="user_id"
          loading={loading}
          pagination={{ pageSize: 20 }}
        />
      </Card>
    </div>
  )
}
