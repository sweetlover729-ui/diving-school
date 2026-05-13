'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { http } from '@/lib/http'

interface Template {
  id: number
  name: string
  doc_type: string
  description?: string
  sort_order: number
}

interface ResponseStatus {
  template_id: number
  status: string
  answers?: Record<string, any>
  submitted_at?: string
  review_comment?: string
}

const STATUS_CONFIG: Record<string, { label: string; color: string; bg: string }> = {
  pending:   { label: '未填写',  color: '#6a6f73', bg: '#f0f0f0' },
  draft:     { label: '草稿',    color: '#6a6f73', bg: '#f0f0f0' },
  submitted: { label: '待审核',  color: '#0056d2', bg: '#e6f0fa' },
  approved:  { label: '已通过',  color: '#00a880', bg: '#e0f7f1' },
  rejected:  { label: '已驳回',  color: '#ef4444', bg: '#fee2e2' },
}

const DOC_ICONS: Record<string, string> = {
  health:        '[健康]',
  waiver:        '[免责]',
  agreement:     '[同意]',
  questionnaire: '[问卷]',
}

export default function StudentDocumentsPage() {
  const [templates, setTemplates] = useState<Template[]>([])
  const [statuses, setStatuses] = useState<Record<number, ResponseStatus>>({})
  const [loading, setLoading] = useState(true)
  const [overallLocked, setOverallLocked] = useState(false)
  const [isMobile, setIsMobile] = useState(false)

  useEffect(() => {
    const m = window.innerWidth < 768
    setIsMobile(m)
    const handler = () => setIsMobile(window.innerWidth < 768)
    window.addEventListener('resize', handler)
    return () => window.removeEventListener('resize', handler)
  }, [])

  useEffect(() => {
    http.get('/students/me/documents/')
      .then((data: Record<string, unknown>) => {
        const items: Record<string, unknown>[] = Array.isArray(data) ? data : (data.responses || [])
        const tmplList: Template[] = items.map((r: Record<string, unknown>) => ({
          id: r.template_id,
          name: r.template_name,
          doc_type: r.doc_type,
          description: r.description,
          sort_order: r.template_id,
        }))
        const statusMap: Record<number, ResponseStatus> = {}
        items.forEach((r: Record<string, unknown>) => {
          statusMap[r.template_id] = {
            template_id: r.template_id,
            status: r.status,
            answers: r.answers,
            submitted_at: r.submitted_at,
            review_comment: r.review_comment,
          }
        })
        setTemplates(tmplList)
        setStatuses(statusMap)
        const allApproved = tmplList.length > 0 && tmplList.every(t => statusMap[t.id]?.status === 'approved')
        setOverallLocked(!allApproved)
        setLoading(false)
      })
      .catch(() => setLoading(false))
  }, [])

  if (loading) return <div style={{ padding: isMobile ? 20 : 40, color: '#6a6f73' }}>加载中…</div>

  return (
    <div style={{
      padding: isMobile ? 12 : '24px 32px',
      maxWidth: 800,
      margin: '0 auto',
    }}>
      {/* 顶部提示 */}
      <div style={{
        background: overallLocked ? '#fff3cd' : '#d4edda',
        border: `1px solid ${overallLocked ? '#ffc107' : '#28a745'}`,
        borderRadius: 8,
        padding: isMobile ? '10px 14px' : '12px 16px',
        marginBottom: isMobile ? 16 : 24,
        fontSize: isMobile ? 13 : 14,
        color: overallLocked ? '#856404' : '#155724',
      }}>
        {overallLocked
          ? '请完成以下入学文书并通过审核后，方可开始课程学习。'
          : '您的入学文书已全部审核通过，可以开始课程学习！'
        }
      </div>

      <h2 style={{
        fontSize: isMobile ? 16 : 18,
        fontWeight: 600,
        marginBottom: isMobile ? 14 : 20,
        color: '#1c1d1f',
      }}>
        入学文书 ({templates.length}份)
      </h2>

      <div style={{ display: 'flex', flexDirection: 'column', gap: isMobile ? 10 : 12 }}>
        {templates
          .sort((a, b) => a.sort_order - b.sort_order)
          .map(tmpl => {
            const st = statuses[tmpl.id]
            const cfg = st ? STATUS_CONFIG[st.status] || STATUS_CONFIG.pending : STATUS_CONFIG.pending
            return (
              <div key={tmpl.id} style={{
                border: '1px solid #e0e0e0',
                borderRadius: 10,
                padding: isMobile ? '14px 14px' : '16px 20px',
                background: '#fff',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                gap: 10,
                flexWrap: 'wrap',
              }}>
                {/* 左侧：图标+名称 */}
                <div style={{ display: 'flex', alignItems: 'center', gap: isMobile ? 10 : 14, flex: 1, minWidth: 0 }}>
                  <span style={{ fontSize: isMobile ? 13 : 14, flexShrink: 0, color: '#0056d2', fontWeight: 600 }}>{DOC_ICONS[tmpl.doc_type] || '[文书]'}</span>
                  <div style={{ minWidth: 0 }}>
                    <div style={{
                      fontWeight: 600,
                      fontSize: isMobile ? 14 : 15,
                      color: '#1c1d1f',
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      whiteSpace: 'nowrap',
                    }}>{tmpl.name}</div>
                    {st?.review_comment && st.status === 'rejected' && (
                      <div style={{ fontSize: isMobile ? 11 : 12, color: '#ef4444', marginTop: 4 }}>
                        驳回原因：{st.review_comment}
                      </div>
                    )}
                  </div>
                </div>
                {/* 右侧：状态+按钮 */}
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexShrink: 0 }}>
                  <span style={{
                    padding: '4px 10px',
                    borderRadius: 20,
                    fontSize: 12,
                    fontWeight: 600,
                    background: cfg.bg,
                    color: cfg.color,
                    whiteSpace: 'nowrap',
                  }}>
                    {cfg.label}
                  </span>
                  <Link
                    href={`/student/documents/${tmpl.id}`}
                    style={{
                      padding: isMobile ? '8px 14px' : '8px 18px',
                      background: '#0056d2',
                      color: '#fff',
                      borderRadius: 6,
                      fontSize: isMobile ? 12 : 13,
                      fontWeight: 500,
                      textDecoration: 'none',
                      whiteSpace: 'nowrap',
                    }}
                  >
                    {st?.status === 'submitted' ? '查看' : st?.status === 'approved' ? '查看' : st?.status === 'rejected' ? '重新填写' : '填写'}
                  </Link>
                </div>
              </div>
            )
          })}
      </div>
    </div>
  )
}
