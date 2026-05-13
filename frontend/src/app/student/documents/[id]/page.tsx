'use client'

import { useEffect, useState, useCallback } from 'react'
import { useParams, useRouter } from 'next/navigation'
import dynamic from 'next/dynamic'
import Link from 'next/link'
import { http } from '@/lib/http'
import pinyin from 'pinyin'

const SignatureCanvas = dynamic(() => import('@/components/SignatureCanvas'), { ssr: false })

interface Field {
  id: string
  type: string
  question?: string
  label?: string
  required?: boolean
  options?: string[]
  field?: string
  source?: string
}

interface Template {
  id: number
  name: string
  doc_type: string
  static_html?: string
  fields_schema: Field[]
  coach_choices?: Array<{ id: number; name: string; code?: string; institution?: string }>
  course_choices?: Array<{ id: string; name: string }>
  institution_name?: string
}

interface MyResponse {
  id?: number
  template_id: number
  status: string
  answers: Record<string, any>
  signature_image?: string
  submitted_at?: string
  review_comment?: string
}

interface PageData {
  template: Template
  my_response?: MyResponse
  student_profile?: { name: string; id_card: string; phone: string }
  instructors?: Array<{ id: number; name: string; code?: string; institution?: string }>
  courses?: Array<{ id: string; name: string }>
  institution_choices?: Array<{ id: number; name: string }>
}

function calcAgeFromIdCard(idCard: string): number | null {
  if (!idCard || idCard.length < 14) return null
  try {
    const y = parseInt(idCard.slice(6, 10))
    const m = parseInt(idCard.slice(10, 12))
    const d = parseInt(idCard.slice(12, 14))
    const now = new Date()
    let age = now.getFullYear() - y
    if (now.getMonth() + 1 < m || (now.getMonth() + 1 === m && now.getDate() < d)) age--
    return age
  } catch { return null }
}

function getAgeDisplay(idCard: string): string {
  const age = calcAgeFromIdCard(idCard)
  if (age === null) return ''
  const y = idCard.slice(6, 10), m = idCard.slice(10, 12), d = idCard.slice(12, 14)
  return `${y}年${m}月${d}日出生，现${age}岁`
}

function maskIdCard(id: string): string {
  if (!id || id.length < 14) return id
  return id.slice(0, 6) + '********' + id.slice(14)
}

function FieldRenderer({
  field,
  value,
  onChange,
  profile,
  instructors = [],
  courses = [],
  isReadOnly,
}: {
  field: Field
  value: unknown
  onChange: (id: string, val: unknown) => void
  profile?: { name: string; id_card: string; phone: string }
  instructors?: Array<{ id: number; name: string; code?: string; institution?: string }>
  courses?: Array<{ id: string; name: string }>
  institution_choices?: Array<{ id: number; name: string }>
  isReadOnly: boolean
}) {
  const label = field.label || field.question || field.id
  const required = field.required

  // Auto-fill from profile
  if (!isReadOnly && field.type === 'profile_auto' && field.field === 'name') {
    return (
      <FieldWrapper label={label} required={required}>
        <input type="text" value={profile?.name || ''} readOnly
          style={inputStyle} />
      </FieldWrapper>
    )
  }
  if (!isReadOnly && field.type === 'profile_auto' && field.field !== 'name') {
    return (
      <FieldWrapper label={label} required={required}>
        <input type="text" value={profile?.[field.field] || ''} readOnly
          style={inputStyle} />
      </FieldWrapper>
    )
  }
  // Auto-generate pinyin from Chinese name, or copy English name directly
  if (field.type === 'name_pinyin') {
    const pinyinName = profile?.name
      ? /^[a-zA-Z\s]+$/.test(profile.name)
        ? profile.name  // English name - use directly
        : pinyin(profile.name, { style: pinyin.STYLE_NORMAL }).join(' ')
      : ''
    return (
      <FieldWrapper label={label} required={required}>
        <input type="text" value={pinyinName} readOnly
          style={inputStyle} />
      </FieldWrapper>
    )
  }
  if (field.type === 'id_number') {
    return (
      <FieldWrapper label={label} required={required}>
        <input type="text" value={profile ? maskIdCard(profile.id_card) : ''} readOnly
          style={{ ...inputStyle, color: '#6a6f73' }} />
      </FieldWrapper>
    )
  }
  if (field.type === 'phone') {
    return (
      <FieldWrapper label={label} required={required}>
        <input type="text" value={profile?.phone || ''} readOnly
          style={inputStyle} />
      </FieldWrapper>
    )
  }
  if (field.type === 'id_auto') {
    const calc = (field as any).calc
    let displayValue = ''
    if (profile?.id_card && profile.id_card.length >= 14) {
      if (calc === 'age') {
        const age = calcAgeFromIdCard(profile.id_card)
        displayValue = age !== null ? String(age) : ''
      } else {
        displayValue = `${profile.id_card.slice(6, 10)}-${profile.id_card.slice(10, 12)}-${profile.id_card.slice(12, 14)}`
      }
    }
    return (
      <FieldWrapper label={label} required={required}>
        <input type="text" value={displayValue} readOnly
          style={inputStyle} />
      </FieldWrapper>
    )
  }
  if (field.type === 'date_auto') {
    return (
      <FieldWrapper label={label} required={required}>
        <input type="text" value={new Date().toLocaleDateString('zh-CN')} readOnly
          style={inputStyle} />
      </FieldWrapper>
    )
  }
  if (field.type === 'select_instructor') {
    return (
      <FieldWrapper label={label} required={required}>
        <select
          value={value || ''}
          onChange={e => onChange(field.id, e.target.value)}
          disabled={isReadOnly}
          style={{ ...inputStyle, cursor: isReadOnly ? 'default' : 'pointer' }}
        >
          <option value="">请选择教练</option>
          {instructors.map(i => (
            <option key={i.id} value={i.name}>{i.name}（{i.institution || '未填写机构'}）</option>
          ))}
        </select>
      </FieldWrapper>
    )
  }
  if (field.type === 'profile_institution') {
    return (
      <FieldWrapper label={label} required={required}>
        <input
          type="text"
          value={value || ''}
          readOnly
          placeholder="选择教练后自动填入"
          style={{ ...inputStyle, backgroundColor: '#f5f5f5', color: '#333' }}
        />
      </FieldWrapper>
    )
  }
  if (field.type === 'select_course') {
    // 课程由班级分配，学员只能查看确认，不能选择
    if (courses.length === 0) {
      return (
        <FieldWrapper label={label} required={required}>
          <div style={{ 
            padding: '10px 14px', 
            background: '#fff2e6', 
            border: '1px solid #ffbb96', 
            borderRadius: 6, 
            color: '#d46b08', 
            fontSize: 14 
          }}>
            班级暂未分配课程，请联系管理员
          </div>
        </FieldWrapper>
      )
    }
    return (
      <FieldWrapper label={label} required={required}>
        <div style={{ 
          padding: '10px 14px', 
          background: '#f6ffed', 
          border: '1px solid #b7eb8f', 
          borderRadius: 6, 
          color: '#52c41a', 
          fontSize: 14,
          fontWeight: 600
        }}>
          {courses.length === 1 ? courses[0].name : courses.map(c => c.name).join(' / ')}
        </div>
        <div key={i} style={{ fontSize: 12, color: '#999', marginTop: 4 }}>
          课程由班级统一安排，无需选择
        </div>
      </FieldWrapper>
    )
  }
  if (field.type === 'yesno') {
    return (
      <FieldWrapper label={field.question || label} required={required}>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '12px 24px' }}>
          {['是', '否'].map(opt => (
            <label key={opt} style={{ 
              display: 'flex', 
              alignItems: 'center', 
              gap: 8, 
              cursor: isReadOnly ? 'default' : 'pointer',
              padding: '6px 0',
              minWidth: '60px'
            }}>
              <input
                type="radio"
                name={field.id}
                value={opt}
                checked={value === opt}
                onChange={() => !isReadOnly && onChange(field.id, opt)}
                disabled={isReadOnly}
                style={{ width: 18, height: 18 }}
              />
              <span style={{ fontSize: 15 }}>{opt}</span>
            </label>
          ))}
        </div>
      </FieldWrapper>
    )
  }
  if (field.type === 'radio') {
    return (
      <FieldWrapper label={label} required={required}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {(field.options || []).map(opt => (
            <label key={opt} style={{ 
              display: 'flex', 
              alignItems: 'flex-start', 
              gap: 10, 
              cursor: isReadOnly ? 'default' : 'pointer',
              padding: '8px 10px',
              backgroundColor: value === opt ? '#e6f7ff' : 'transparent',
              borderRadius: 6,
              border: value === opt ? '1px solid #1890ff' : '1px solid transparent'
            }}>
              <input
                type="radio"
                name={field.id}
                value={opt}
                checked={value === opt}
                onChange={() => !isReadOnly && onChange(field.id, opt)}
                disabled={isReadOnly}
                style={{ width: 18, height: 18, marginTop: 2, flexShrink: 0 }}
              />
              <span style={{ fontSize: 15, lineHeight: 1.5, flex: 1 }}>{opt}</span>
            </label>
          ))}
        </div>
      </FieldWrapper>
    )
  }
  if (field.type === 'instructor_auto') {
    return (
      <FieldWrapper label={label} required={required}>
        <input type="text"
          value={value || ''}
          readOnly
          placeholder="选择教练后自动填入"
          style={{ ...inputStyle, backgroundColor: '#f5f5f5', color: '#333' }} />
      </FieldWrapper>
    )
  }

  if (field.type === 'multi_checkbox' || field.type === 'multi_text') {
    return (
      <FieldWrapper label={label} required={required}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {(field.options || []).map(opt => {
            const selected: string[] = value || []
            const isChecked = selected.includes(opt)
            return (
              <label key={opt} style={{ 
                display: 'flex', 
                alignItems: 'flex-start', 
                gap: 10, 
                cursor: isReadOnly ? 'default' : 'pointer',
                padding: '8px 10px',
                backgroundColor: isChecked ? '#f6ffed' : 'transparent',
                borderRadius: 6,
                border: isChecked ? '1px solid #52c41a' : '1px solid #e8e8e8'
              }}>
                <input
                  type="checkbox"
                  checked={isChecked}
                  onChange={() => {
                    if (isReadOnly) return
                    const next = isChecked ? selected.filter(v => v !== opt) : [...selected, opt]
                    onChange(field.id, next)
                  }}
                  disabled={isReadOnly}
                  style={{ width: 18, height: 18, marginTop: 2, flexShrink: 0 }}
                />
                <span style={{ fontSize: 15, lineHeight: 1.5, flex: 1 }}>{opt}</span>
              </label>
            )
          })}
        </div>
      </FieldWrapper>
    )
  }
  if (field.type === 'radio_text') {
    const parts = (value as string) || ''
    const selected = parts.split('||')[0] || ''
    const text = parts.split('||')[1] || ''
    return (
      <FieldWrapper label={label} required={required}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {(field.options || []).map(opt => (
              <label key={opt} style={{ 
                display: 'flex', 
                alignItems: 'flex-start', 
                gap: 10, 
                cursor: isReadOnly ? 'default' : 'pointer',
                padding: '8px 10px',
                backgroundColor: selected === opt ? '#e6f7ff' : 'transparent',
                borderRadius: 6,
                border: selected === opt ? '1px solid #1890ff' : '1px solid #e8e8e8'
              }}>
                <input type="radio" name={field.id} value={opt}
                  checked={selected === opt}
                  onChange={() => !isReadOnly && onChange(field.id, opt + '||' + text)}
                  disabled={isReadOnly}
                  style={{ width: 18, height: 18, marginTop: 2, flexShrink: 0 }} />
                <span style={{ fontSize: 15, lineHeight: 1.5, flex: 1 }}>{opt}</span>
              </label>
            ))}
          </div>
          {!isReadOnly && selected && (
            <input type="text" value={text} placeholder="请填写详情"
              onChange={e => onChange(field.id, selected + '||' + e.target.value)}
              style={{ ...inputStyle, marginTop: 8 }} />
          )}
          {!selected && !isReadOnly && (
            <input type="text" placeholder="请先选择选项，再填写详情"
              disabled style={{ ...inputStyle, color: '#aaa', marginTop: 8 }} />
          )}
        </div>
      </FieldWrapper>
    )
  }
  if (field.type === 'signature') {
    return (
      <FieldWrapper label={label} required={required}>
        {isReadOnly && value ? (
          <img src={value} alt="签名" style={{ maxWidth: 400, maxHeight: 150, border: '1px solid #e0e0e0', borderRadius: 4 }} />
        ) : !isReadOnly ? (
          <>
            {value && <img src={value} alt="当前签名" style={{ maxWidth: 400, maxHeight: 150, border: '1px solid #e0e0e0', borderRadius: 4, marginBottom: 8 }} />}
            <SignatureCanvas
              onSave={(dataUrl) => onChange(field.id, dataUrl)}
              width={500}
              height={160}
            />
            <div style={{ fontSize: 12, color: '#6a6f73', marginTop: 6 }}>请在上方签名后点击"保存草稿"</div>
          </>
        ) : (
          <span style={{ color: '#aaa', fontSize: 14 }}>（未签名）</span>
        )}
      </FieldWrapper>
    )
  }
  if (field.type === 'guardian_signature') {
    const age = profile?.id_card ? calcAgeFromIdCard(profile.id_card) : null
    if (age !== null && age >= 18) return null // 成年了不显示
    return (
      <FieldWrapper label={label} required={required}>
        {isReadOnly && value ? (
          <img src={value} alt="监护人签名" style={{ maxWidth: 400, maxHeight: 150, border: '1px solid #e0e0e0', borderRadius: 4 }} />
        ) : !isReadOnly ? (
          <>
            <div style={{ fontSize: 12, color: '#856404', background: '#fff3cd', padding: '6px 10px', borderRadius: 4, marginBottom: 8 }}>
              您未满18周岁，需由亲属或监护人签名
            </div>
            {value && <img src={value} alt="当前签名" style={{ maxWidth: 400, maxHeight: 150, border: '1px solid #e0e0e0', borderRadius: 4, marginBottom: 8 }} />}
            <SignatureCanvas
              onSave={(dataUrl) => onChange(field.id, dataUrl)}
              width={500}
              height={160}
            />
          </>
        ) : (
          <span style={{ color: '#aaa', fontSize: 14 }}>（无需填写）</span>
        )}
      </FieldWrapper>
    )
  }
  if (field.type === 'agreement_checkbox') {
    return (
      <FieldWrapper label={label} required={required}>
        <label style={{ display: 'flex', alignItems: 'flex-start', gap: 8, cursor: isReadOnly ? 'default' : 'pointer' }}>
          <input type="checkbox" checked={!!value}
            onChange={e => onChange(field.id, e.target.checked)}
            disabled={isReadOnly}
            style={{ marginTop: 3 }} />
          <span style={{ fontSize: 13, lineHeight: 1.6, color: '#3e414d' }}>
            我已仔细阅读上述内容，确认所填信息真实准确，并同意遵守其中所有规定。
          </span>
        </label>
      </FieldWrapper>
    )
  }
  if (field.type === 'textarea') {
    return (
      <FieldWrapper label={label} required={required}>
        <textarea
          value={value || ''}
          onChange={e => onChange(field.id, e.target.value)}
          disabled={isReadOnly}
          rows={4}
          style={{ ...inputStyle, resize: 'vertical', minHeight: 80 }}
          placeholder={isReadOnly ? '' : '请输入…'}
        />
      </FieldWrapper>
    )
  }
  if (field.type === 'readonly_static') {
    return (
      <FieldWrapper label={label} required={false}>
        <span style={{ fontSize: 14, color: '#3e414d' }}>{value || '——'}</span>
      </FieldWrapper>
    )
  }
  if (field.type === 'text' || field.type === 'select') {
    if (field.options && field.options.length > 0) {
      return (
        <FieldWrapper label={label} required={required}>
          <select
            value={value || ''}
            onChange={e => onChange(field.id, e.target.value)}
            disabled={isReadOnly}
            style={{ ...inputStyle, cursor: isReadOnly ? 'default' : 'pointer' }}
          >
            <option value="">请选择</option>
            {field.options.map(o => <option key={o} value={o}>{o}</option>)}
          </select>
        </FieldWrapper>
      )
    }
    return (
      <FieldWrapper label={label} required={required}>
        <input type="text"
          value={value || ''}
          onChange={e => onChange(field.id, e.target.value)}
          disabled={isReadOnly}
          style={inputStyle}
          placeholder={isReadOnly ? '' : `请输入${label}`} />
      </FieldWrapper>
    )
  }
  // 默认文本
  return (
    <FieldWrapper label={label} required={required}>
      <input type="text"
        value={value || ''}
        onChange={e => onChange(field.id, e.target.value)}
        disabled={isReadOnly}
        style={inputStyle} />
    </FieldWrapper>
  )
}

function FieldWrapper({ label, required, children }: { label: string; required?: boolean; children: React.ReactNode }) {
  return (
    <div style={{ marginBottom: 20, padding: '0 4px' }}>
      <div style={{ fontSize: 15, fontWeight: 600, color: '#3e414d', marginBottom: 8, lineHeight: 1.4 }}>
        {label}
        {required && <span style={{ color: '#ef4444', marginLeft: 4 }}>*</span>}
      </div>
      {children}
    </div>
  )
}

const inputStyle: React.CSSProperties = {
  width: '100%',
  padding: '12px 14px',
  border: '1px solid #d0d0d0',
  borderRadius: 8,
  fontSize: 16,
  color: '#1c1d1f',
  background: '#fff',
  boxSizing: 'border-box',
  minHeight: 44,
}

export default function DocumentFillPage() {
  const params = useParams()
  const router = useRouter()
  const templateId = params.id as string

  const [data, setData] = useState<PageData | null>(null)
  const [answers, setAnswers] = useState<Record<string, any>>({})
  const [signature, setSignature] = useState('')
  const [guardianSignature, setGuardianSignature] = useState('')
  const [saving, setSaving] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [msg, setMsg] = useState('')
  const [msgType, setMsgType] = useState<'success' | 'error'>('success')
  const [isReadOnly, setIsReadOnly] = useState(false)

  useEffect(() => {
    http.get(`/students/me/documents/${templateId}`)
      .then((d: Record<string, unknown>) => {
        setData(d)
        
        // 初始化答案（包含 readonly_static 字段从 class_info 获取的值）
        const initialAnswers: Record<string, string> = d.my_response?.answers || {}
        
        // 从 class_info 填充 readonly_static 字段
        if (d.class_info) {
          const fields = d.template?.fields_schema || []
          fields.forEach((field: Record<string, unknown>) => {
            if (field.type === 'readonly_static') {
              const fieldId = field.id
              if (fieldId === 'unit_name' && d.class_info.unit_name) {
                initialAnswers[fieldId] = d.class_info.unit_name
              } else if (fieldId === 'course_session') {
                initialAnswers[fieldId] = d.class_info.course_session || ''
              } else if (fieldId === 'course_start' && d.class_info.course_start) {
                initialAnswers[fieldId] = d.class_info.course_start
              } else if (fieldId === 'course_end' && d.class_info.course_end) {
                initialAnswers[fieldId] = d.class_info.course_end
              }
            }
          })
        }
        
        setAnswers(initialAnswers)
        setSignature(d.my_response?.signature_image || '')
        if (d.my_response?.signature_image) {
          setSignature(d.my_response.signature_image)
        }
        // 检查是否只读（已提交/已审核）
        const st = d.my_response?.status
        setIsReadOnly(st === 'submitted' || st === 'approved')
      })
  }, [templateId])

  // 提前解构，避免 TDZ（instructors 在 JSX 里解构太晚）
  const instructors = data?.instructors || []
  const courses = data?.courses || data?.template?.course_choices || []
  const institution_choices = data?.institution_choices || []
  const profile = data?.student_profile || { name: '', id_card: '', phone: '' }

  const onFieldChange = useCallback((id: string, val: unknown) => {
    // 基础赋值
    setAnswers(prev => ({ ...prev, [id]: val }))

    // 同步更新签名状态
    if (id === 'signature') {
      setSignature(val)
    }
    if (id === 'guardian_signature') {
      setGuardianSignature(val)
    }

    // 联动：选择教练 → 自动填机构和教练编号
    if (id === 'instructor_name' && val && instructors) {
      const selected = instructors.find((i: Record<string, unknown>) => i.name === val)
      if (selected) {
        setAnswers(prev => ({
          ...prev,
          institution: selected.institution || '',
          instructor_code: selected.code || '',
        }))
      }
    }
  }, [instructors, setAnswers, setSignature, setGuardianSignature])

  const showMsg = (text: string, type: 'success' | 'error' = 'success') => {
    setMsg(text)
    setMsgType(type)
    setTimeout(() => setMsg(''), 5000)
  }

  const handleSaveDraft = async () => {
    if (!signature) {
      showMsg('请先在签名区完成手写签名', 'error')
      return
    }
    setSaving(true)
    try {
      await http.post(`/students/me/documents/${templateId}`, {
        answers,
        signature_image: signature,
        guardian_signature_image: guardianSignature,
        action: 'draft',
      })
      showMsg('草稿保存成功')
      setIsReadOnly(false)
    } catch (e) {
      showMsg(e.message || '保存失败', 'error')
    }
    setSaving(false)
  }

  const handleSubmit = async () => {
    if (!data) {
      showMsg('页面数据加载中，请稍后再试', 'error')
      return
    }
    // 必填检查（排除自动填充字段和签名字段）
    const requiredFields = (data.template.fields_schema || []).filter(f => 
      f.required && 
      f.type !== 'signature' && 
      f.type !== 'guardian_signature' &&
      f.type !== 'profile_auto' &&
      f.type !== 'id_number' &&
      f.type !== 'phone' &&
      f.type !== 'id_auto' &&
      f.type !== 'date_auto' &&
      f.type !== 'instructor_auto' &&
      f.type !== 'profile_institution' &&
      f.type !== 'select_course' &&
      f.type !== 'select_instructor' &&
      f.type !== 'name_pinyin'
    )
    for (const f of requiredFields) {
      if (!answers[f.id]) {
        showMsg(`请填写：${f.label || f.question || f.id}`, 'error')
        return
      }
    }
    if (!signature) {
      showMsg('请完成手写签名', 'error')
      return
    }
    // 同意书必须勾选（仅当模板有 agreement_checkbox 字段时）
    const hasAgreeField = (data?.template?.fields_schema || []).some((f: Record<string, unknown>) => f.type === 'agreement_checkbox')
    if (hasAgreeField && !answers['agree']) {
      showMsg('请勾选同意声明', 'error')
      return
    }
    setSubmitting(true)
    try {
      await http.post(`/students/me/documents/${templateId}`, {
        answers,
        signature_image: signature,
        guardian_signature_image: guardianSignature,
        action: 'submit',
      })
      showMsg('提交成功，等待教练审核！')
      setTimeout(() => router.push('/student/documents'), 1500)
    } catch (e) {
      showMsg(e.message || '提交失败', 'error')
    }
    setSubmitting(false)
  }

  if (!data) return <div style={{ padding: 40, color: '#6a6f73' }}>加载中…</div>

  const { template, my_response } = data
  const currentStatus = my_response?.status || 'pending'

  return (
    <div style={{ padding: '24px 32px', maxWidth: 900, margin: '0 auto' }}>
      {/* 顶部导航 */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 20 }}>
        <Link href="/student/documents"
          style={{ color: '#0056d2', textDecoration: 'none', fontSize: 14 }}>
          ← 返回文书列表
        </Link>
        <span style={{ color: '#cecece' }}>|</span>
        <span style={{ fontSize: 14, color: '#6a6f73' }}>文书填写</span>
      </div>

      {/* 标题 */}
      <h1 style={{ fontSize: 22, fontWeight: 700, color: '#1c1d1f', marginBottom: 6 }}>
        {template.name}
      </h1>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 24 }}>
        <span style={{
          padding: '3px 12px', borderRadius: 20, fontSize: 12, fontWeight: 600,
          background: currentStatus === 'approved' ? '#e0f7f1' : currentStatus === 'rejected' ? '#fee2e2' : currentStatus === 'submitted' ? '#e6f0fa' : '#f0f0f0',
          color: currentStatus === 'approved' ? '#00a880' : currentStatus === 'rejected' ? '#ef4444' : currentStatus === 'submitted' ? '#0056d2' : '#6a6f73',
        }}>
          {currentStatus === 'approved' ? '已通过' : currentStatus === 'rejected' ? '已驳回' : currentStatus === 'submitted' ? '待审核' : currentStatus === 'draft' ? '草稿' : '未填写'}
        </span>
        {profile.id_card && (
          <span style={{ fontSize: 13, color: '#6a6f73' }}>
            {getAgeDisplay(profile.id_card)}
          </span>
        )}
      </div>

      {/* 驳回原因 */}
      {my_response?.review_comment && currentStatus === 'rejected' && (
        <div style={{ background: '#fee2e2', border: '1px solid #ef4444', borderRadius: 8, padding: '12px 16px', marginBottom: 20, fontSize: 14, color: '#991b1b' }}>
          教练驳回原因：{my_response.review_comment}
        </div>
      )}

      {/* 消息提示 - 屏幕中央弹窗 */}
      {msg && (
        <div style={{
          position: 'fixed',
          top: 0, left: 0, right: 0, bottom: 0,
          backgroundColor: 'rgba(0,0,0,0.5)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 9999,
        }} onClick={() => setMsg('')}>
          <div style={{
            background: '#fff',
            borderRadius: 12,
            padding: '24px 32px',
            maxWidth: 320,
            width: '80%',
            textAlign: 'center',
            boxShadow: '0 4px 20px rgba(0,0,0,0.3)',
          }} onClick={e => e.stopPropagation()}>
            <div style={{
              width: 48,
              height: 48,
              borderRadius: '50%',
              backgroundColor: msgType === 'success' ? '#e0f7f1' : '#fee2e2',
              color: msgType === 'success' ? '#00a880' : '#ef4444',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: 24,
              margin: '0 auto 16px',
            }}>
              {msgType === 'success' ? '' : ''}
            </div>
            <div style={{ fontSize: 16, fontWeight: 600, color: '#1c1d1f', marginBottom: 8 }}>
              {msgType === 'success' ? '成功' : '错误'}
            </div>
            <div style={{ fontSize: 15, color: '#3e414d', lineHeight: 1.5 }}>
              {msg}
            </div>
            <button
              onClick={() => setMsg('')}
              style={{
                marginTop: 20,
                padding: '10px 32px',
                background: '#0056d2',
                color: '#fff',
                border: 'none',
                borderRadius: 6,
                fontSize: 15,
                cursor: 'pointer',
              }}
            >
              确定
            </button>
          </div>
        </div>
      )}

      {/* 声明书正文（只读展示） */}
      {template.static_html && (
        <div style={{
          background: '#f8f9fa', border: '1px solid #e0e0e0',
          borderRadius: 8, padding: '16px 20px', marginBottom: 24, fontSize: 13,
          lineHeight: 1.8, color: '#3e414d', maxHeight: 300, overflowY: 'auto',
        }}>
          <pre style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word', fontFamily: 'inherit', margin: 0 }}>
            {template.static_html}
          </pre>
        </div>
      )}

      {/* 动态字段 */}
      <div style={{ background: '#fff', border: '1px solid #e0e0e0', borderRadius: 12, padding: '24px 28px' }}>
        {(template.fields_schema || []).map(field => {
          if (field.type === 'guardian_signature') {
            return (
              <FieldRenderer
                key={field.id}
                field={field}
                value={guardianSignature}
                onChange={(_, val) => setGuardianSignature(val)}
                profile={profile}
                instructors={instructors}
                courses={courses}
                institution_choices={institution_choices}
                isReadOnly={isReadOnly}
              />
            )
          }
          return (
            <FieldRenderer
              key={field.id}
              field={field}
              value={answers[field.id]}
              onChange={onFieldChange}
              profile={profile}
              instructors={instructors}
              courses={courses}
              institution_choices={institution_choices}
              isReadOnly={isReadOnly}
            />
          )
        })}
      </div>

      {/* 操作按钮 */}
      {!isReadOnly && (
        <div style={{ display: 'flex', gap: 12, marginTop: 24 }}>
          <button
            onClick={handleSaveDraft}
            disabled={saving}
            style={{
              padding: '10px 24px', background: '#f7f7f7', border: '1px solid #d0d0d0',
              borderRadius: 8, fontSize: 14, cursor: saving ? 'not-allowed' : 'pointer',
              color: '#3e414d',
            }}
          >
            {saving ? '保存中…' : '保存草稿'}
          </button>
          <button
            onClick={handleSubmit}
            disabled={submitting}
            style={{
              padding: '10px 28px', background: '#0056d2', border: 'none',
              borderRadius: 8, fontSize: 14, cursor: submitting ? 'not-allowed' : 'pointer',
              color: '#fff', fontWeight: 600,
            }}
          >
            {submitting ? '提交中…' : ' 提交审核'}
          </button>
        </div>
      )}

      {isReadOnly && currentStatus === 'submitted' && (
        <div style={{ marginTop: 20, color: '#6a6f73', fontSize: 14 }}>
          此表单已提交审核，请等待教练确认。如有疑问请联系教练。
        </div>
      )}
    </div>
  )
}
