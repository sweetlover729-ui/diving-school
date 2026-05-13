'use client'

import { useEffect, useState, useCallback } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { Card, Spin, message, Button, Progress, Tag, Drawer, Modal } from 'antd'
import { ArrowLeftOutlined, CheckCircleOutlined, ClockCircleOutlined, BookOutlined, MenuOutlined } from '@ant-design/icons'
import { http } from '@/lib/http'

// ── 类型定义 ────────────────────────────────────────────────
interface Unit {
  id: string
  type: string
  content: string
  level: number
  keywords: string[]
  is_important: boolean
  order: number
}

interface Section {
  id: string
  title: string
  level: number
  estimated_time: number
  key_concepts: string[]
  order: number
  is_hidden: boolean
  units: Unit[]
}

interface InteractiveData {
  id: string
  title: string
  total_sections: number
  sections: Section[]
  key_concepts_map: Record<string, string>
  metadata: Record<string, unknown>
}

// ── 本地存储键 ───────────────────────────────────────────────
const STORAGE_KEY = 'diving_student_progress_v2'

function getProgress(textbookId: string): Record<string, boolean> {
  try {
    const raw = localStorage.getItem(`${STORAGE_KEY}_${textbookId}`)
    return raw ? JSON.parse(raw) : {}
  } catch { return {} }
}

function saveProgress(textbookId: string, progress: Record<string, boolean>) {
  try { localStorage.setItem(`${STORAGE_KEY}_${textbookId}`, JSON.stringify(progress)) } catch {}
}

// ── 内容渲染（与管理员预览页完全一致）──────────────────────────
function renderContent(unit: Unit, kcmap: Record<string, string>, onKpClick: (name: string) => void) {
  const lines = unit.content.split('\n').filter(l => l.trim())

  if (unit.type === 'heading') {
    const isChapter = /^第[一二三四五六七八九十\d]+章/.test(unit.content) || /^本[章节]/.test(unit.content)
    return (
      <div style={{ padding: '16px 0 8px', borderBottom: '2px solid #1890ff', marginBottom: 8 }}>
        <h2 style={{ fontSize: isChapter ? 20 : 17, fontWeight: 700, color: isChapter ? '#1a1a2e' : '#333', margin: 0 }}>
          {unit.content}
        </h2>
      </div>
    )
  }

  if (unit.type === 'list') {
    return (
      <div style={{ padding: '6px 0 6px 16px', borderLeft: '3px solid #52c41a', marginBottom: 4 }}>
        <span style={{ color: '#52c41a', marginRight: 8, fontWeight: 600 }}>▸</span>
        <span style={{ fontSize: 14, lineHeight: 1.8, color: '#444' }}>
          {lines.map((l, i) => <span key={i}>{l}{i < lines.length - 1 ? <br/> : ''}</span>)}
        </span>
      </div>
    )
  }

  return (
    <p style={{ fontSize: 14, lineHeight: 2, color: '#333', margin: '0 0 12px', textAlign: 'justify', textIndent: '2em' }}>
      {lines.map((l, i) => <span key={i}>{l}{i < lines.length - 1 ? <br/> : ''}</span>)}
    </p>
  )
}

// ── 知识点标签（可点击）───────────────────────────────────────
function KpTag({ name, kcmap, onClick }: { name: string; kcmap: Record<string, string>; onClick: () => void }) {
  const hasDefinition = !!kcmap[name]
  return (
    <Tag
      onClick={hasDefinition ? onClick : undefined}
      color={hasDefinition ? 'blue' : 'default'}
      style={{ fontSize: 12, cursor: hasDefinition ? 'pointer' : 'default', marginBottom: 4 }}
    >
      <BookOutlined style={{ marginRight: 3 }} />
      {name}
    </Tag>
  )
}

// ── 主组件 ───────────────────────────────────────────────────
export default function StudentTextbookReadPage() {
  const params = useParams()
  const router = useRouter()
  const textbookId = params.id as string

  const [loading, setLoading] = useState(true)
  const [data, setData] = useState<InteractiveData | null>(null)
  const [currentSection, setCurrentSection] = useState(0)
  const [completedUnits, setCompletedUnits] = useState<Set<string>>(new Set())
  const [kpModalVisible, setKpModalVisible] = useState(false)
  const [kpModalTitle, setKpModalTitle] = useState('')
  const [kpModalContent, setKpModalContent] = useState('')
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false)

  // ── 取数据 ─────────────────────────────────────────────────
  const fetchData = useCallback(async () => {
    try {
      setLoading(true)
      // 优先用新版互动教材API；若无则回退旧API
      try {
        const result = await http.get(`/admin/textbooks/${textbookId}/interactive`)
        setData(result)
      } catch {
        // 回退到学员旧API
        const result = await http.get(`/student/textbooks/${textbookId}`)
        setData(result)
      }
    } catch (e) {
      message.error('加载失败: ' + (e.message || ''))
    } finally {
      setLoading(false)
    }
  }, [textbookId])

  useEffect(() => {
    fetchData()
    // 加载本地进度
    const saved = getProgress(textbookId)
    setCompletedUnits(new Set(Object.keys(saved).filter(k => saved[k])))
  }, [fetchData, textbookId])

  // ── 持久化进度（本地 + 后端同步）─────────────────────────────
  const persistProgress = useCallback(async (units: Set<string>) => {
    // 本地存储
    const obj: Record<string, boolean> = {}
    units.forEach(id => { obj[id] = true })
    saveProgress(textbookId, obj)

    // 同步到后端（计算完成百分比）
    try {
      const totalUnits = data?.sections.reduce(
        (sum: number, s: Section) => sum + (s.units?.length || 0), 0
      ) || 0
      const completedCount = units.size
      const progressPercent = totalUnits > 0 ? Math.round((completedCount / totalUnits) * 100) : 0
      await http.post('/student/reading/progress', {
        textbook_id: parseInt(textbookId),
        chapter_id: null,
        current_page: completedCount,
        duration: 0,
        progress_percent: progressPercent
      })
    } catch {
      // 静默失败，不影响本地进度
    }
  }, [textbookId, data])

  // ── 切换单元完成状态 ────────────────────────────────────────
  const toggleUnitComplete = (unitId: string, forceDone?: boolean) => {
    const newSet = new Set(completedUnits)
    const isDone = forceDone !== undefined ? forceDone : newSet.has(unitId)
    if (isDone) {
      newSet.delete(unitId)
    } else {
      newSet.add(unitId)
    }
    setCompletedUnits(newSet)
    persistProgress(newSet)
  }

  // ── 知识点弹窗 ──────────────────────────────────────────────
  const openKpModal = (kpName: string) => {
    const def = data?.key_concepts_map?.[kpName] || '暂无详解'
    setKpModalTitle(kpName)
    setKpModalContent(def)
    setKpModalVisible(true)
  }

  // ── 顺序解锁逻辑 ───────────────────────────────────────────
  // 所有单元按章节+单元顺序展平
  const allUnits = data ? data.sections.flatMap((s, si) =>
    (s.units || []).map((u, ui) => ({ ...u, _si: si, _ui: ui }))
  ) : []

  const isUnitUnlocked = (sectionIndex: number, unitIndex: number, unitId: string): boolean => {
    // 已完成的直接解锁
    if (completedUnits.has(unitId)) return true
    // 章节内第一单元始终解锁
    if (unitIndex === 0) return true
    // 该章节所有前面的单元都完成了才解锁
    const section = data?.sections[sectionIndex]
    if (!section) return false
    const sectionUnits = section.units || []
    for (let i = 0; i < unitIndex; i++) {
      if (!completedUnits.has(sectionUnits[i].id)) return false
    }
    return true
  }

  const isSectionUnlocked = (sectionIndex: number): boolean => {
    if (sectionIndex === 0) return true
    // 前一章节所有单元都完成
    const prevSection = data?.sections[sectionIndex - 1]
    if (!prevSection) return false
    const prevUnits = prevSection.units || []
    return prevUnits.every(u => completedUnits.has(u.id))
  }

  if (loading) {
    return (
      <div style={{ padding: 100, textAlign: 'center' }}>
        <Spin size="large" tip="加载教材内容..." />
      </div>
    )
  }

  if (!data) {
    return (
      <div style={{ padding: 60, textAlign: 'center' }}>
        <p style={{ color: '#ef4444', marginBottom: 16 }}>教材加载失败</p>
        <Button onClick={() => router.push('/student/textbooks')}>返回教材列表</Button>
      </div>
    )
  }

  const visibleSections = data.sections.filter((s: Section) => !s.is_hidden)
  const current = visibleSections[currentSection]
  const totalUnits = visibleSections.reduce((sum: number, s: Section) => sum + (s.units?.length || 0), 0)
  const completedCount = visibleSections.reduce((sum: number, s: Section) => {
    return sum + (s.units?.filter((u: Unit) => completedUnits.has(u.id)).length || 0)
  }, 0)
  const totalTime = visibleSections.reduce((sum: number, s: Section) => sum + (s.estimated_time || 0), 0)
  const progress = totalUnits > 0 ? Math.round((completedCount / totalUnits) * 100) : 0
  const kcmap = data.key_concepts_map || {}

  // ── 左侧导航（桌面端）───────────────────────────────────────
  const Sidebar = () => (
    <div style={{
      width: 300, background: '#fff', borderRight: '1px solid #e8e8e8',
      overflowY: 'auto', height: '100vh', position: 'sticky', top: 0,
      display: 'flex', flexDirection: 'column',
    }}>
      {/* 顶部 */}
      <div style={{ padding: '16px 14px 12px', borderBottom: '1px solid #f0f0f0' }}>
        <div style={{ fontSize: 14, fontWeight: 600, color: '#1a1a2e', lineHeight: 1.4, marginBottom: 10 }}>
          {data.title}
        </div>
        <Progress
          percent={progress}
          size="small"
          strokeColor="#1890ff"
          format={(p) => <span style={{ color: '#666', fontSize: 11 }}>{p}%</span>}
        />
        <div style={{ fontSize: 11, color: '#999', marginTop: 4 }}>
          已完成 {completedCount}/{totalUnits} 单元
        </div>
      </div>

      {/* 章节列表 */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '8px 0' }}>
        {visibleSections.map((section: Section, idx: number) => {
          const sectionUnits = section.units || []
          const completed = sectionUnits.filter((u: Unit) => completedUnits.has(u.id)).length
          const isActive = idx === currentSection
          const unlocked = isSectionUnlocked(idx)
          const isComplete = completed === sectionUnits.length && sectionUnits.length > 0

          return (
            <div
              key={section.id}
              onClick={() => unlocked && setCurrentSection(idx)}
              style={{
                padding: '9px 14px',
                cursor: unlocked ? 'pointer' : 'not-allowed',
                background: isActive ? '#e6f7ff' : unlocked ? 'transparent' : '#f5f5f5',
                borderLeft: isActive ? '3px solid #1890ff' : '3px solid transparent',
                opacity: unlocked ? 1 : 0.5,
                transition: 'all 0.2s',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 2 }}>
                {isComplete ? (
                  <CheckCircleOutlined style={{ color: '#52c41a', fontSize: 12 }} />
                ) : unlocked ? (
                  <ClockCircleOutlined style={{ color: '#d9d9d9', fontSize: 12 }} />
                ) : (
                  <span style={{ display: 'inline-block', width: 12, height: 12, borderRadius: '50%', background: '#d9d9d9', fontSize: 10, color: '#fff', textAlign: 'center', lineHeight: '12px' }}></span>
                )}
                <span style={{ fontWeight: isActive ? 600 : 400, fontSize: 12.5, color: isActive ? '#1890ff' : '#444', lineHeight: 1.4 }}>
                  {idx + 1}. {section.title}
                </span>
              </div>
              <div style={{ display: 'flex', gap: 6, alignItems: 'center', paddingLeft: 18 }}>
                <span style={{ fontSize: 11, color: '#999' }}>{sectionUnits.length}单元</span>
                {completed > 0 && (
                  <Tag color="green" style={{ fontSize: 10, padding: '0 4px', margin: 0 }}>{completed}/{sectionUnits.length}</Tag>
                )}
                {!unlocked && <Tag color="default" style={{ fontSize: 10, padding: '0 4px', margin: 0 }}>未解锁</Tag>}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )

  return (
    <div style={{ display: 'flex', minHeight: '100vh', background: '#f0f2f5' }}>
      {/* 桌面端侧边栏 */}
      <div className="desktop-sidebar"><Sidebar /></div>

      {/* 移动端抽屉 */}
      <Drawer
        placement="left" width={300} open={mobileSidebarOpen}
        onClose={() => setMobileSidebarOpen(false)}
        headerStyle={{ display: 'none' }} bodyStyle={{ padding: 0 }}
      >
        <Sidebar />
      </Drawer>

      {/* 主内容区 */}
      <div style={{ flex: 1, padding: '24px 32px', maxWidth: 1100, margin: '0 auto' }}>
        {/* 顶栏 */}
        <div style={{ marginBottom: 20, display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 12 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <Button icon={<ArrowLeftOutlined />} onClick={() => router.push('/student')}>返回主页</Button>
            <Button onClick={() => setMobileSidebarOpen(true)} className="mobile-only">目录</Button>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <span style={{ color: '#666', fontSize: 13 }}>已完成 {completedCount}/{totalUnits} 单元</span>
            <Button disabled={currentSection === 0} onClick={() => setCurrentSection(Math.max(0, currentSection - 1))}>上一章</Button>
            <Tag color="blue" style={{ fontSize: 13, padding: '2px 12px' }}>{currentSection + 1} / {visibleSections.length}</Tag>
            <Button
              disabled={
                currentSection === visibleSections.length - 1 ||
                !visibleSections[currentSection].units.every(u => completedUnits.has(u.id))
              }
              onClick={() => setCurrentSection(Math.min(visibleSections.length - 1, currentSection + 1))}
              title={
                currentSection < visibleSections.length - 1 &&
                !visibleSections[currentSection].units.every(u => completedUnits.has(u.id))
                  ? '请先完成当前章节所有单元'
                  : undefined
              }
            >
              {completedUnits.size > 0 &&
              currentSection < visibleSections.length - 1 &&
              !visibleSections[currentSection].units.every(u => completedUnits.has(u.id))
                ? '本章未完成'
                : '下一章'}
            </Button>
          </div>
        </div>

        {/* 总进度条 */}
        <Progress percent={progress} style={{ marginBottom: 20 }} />

        {current && (
          <>
            {/* 章节标题卡 */}
            <Card style={{ marginBottom: 16 }} bodyStyle={{ padding: '16px 24px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
                <div>
                  <Tag color="blue" style={{ marginRight: 8 }}>第{currentSection + 1}章</Tag>
                  <span style={{ fontSize: 17, fontWeight: 700, color: '#1a1a2e' }}>{current.title}</span>
                </div>
                <span style={{ color: '#999', fontSize: 13 }}>
                  <ClockCircleOutlined /> 约{current.estimated_time}分钟 · {current.units?.length || 0}单元
                </span>
              </div>
            </Card>

            {/* 知识点导航 */}
            {current.key_concepts && current.key_concepts.length > 0 && (
              <Card
                size="small"
                title={<span style={{ fontSize: 13 }}><BookOutlined style={{ marginRight: 6, color: '#52c41a' }} />本章核心知识点（点击查看详解）</span>}
                style={{ marginBottom: 16, background: '#fafff0', border: '1px solid #b7eb8f' }}
                bodyStyle={{ padding: '12px 16px' }}
              >
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                  {current.key_concepts.map((kw: string, i: number) => (
                    <KpTag key={i} name={kw} kcmap={kcmap} onClick={() => openKpModal(kw)} />
                  ))}
                </div>
              </Card>
            )}

            {/* 正文内容 */}
            <Card
              title={<span style={{ fontSize: 14 }}><BookOutlined style={{ marginRight: 6 }} />章节内容</span>}
              extra={<span style={{ fontSize: 12, color: '#999' }}>点击单元标记完成</span>}
            >
              <div>
                {(current.units || []).map((unit: Unit, unitIndex: number) => {
                  const isDone = completedUnits.has(unit.id)
                  const unlocked = isUnitUnlocked(currentSection, unitIndex, unit.id)

                  let bg = '#fff'
                  let border = '#e8e8e8'
                  if (isDone) { bg = '#f6ffed'; border = '#b7eb8f' }
                  else if (unit.is_important) { bg = '#fffbe6'; border = '#ffe58f' }
                  else if (!unlocked) { bg = '#fafafa'; border = '#f0f0f0' }

                  return (
                    <div
                      key={unit.id}
                      onClick={() => unlocked && toggleUnitComplete(unit.id)}
                      style={{
                        marginBottom: unit.type === 'heading' ? 4 : 12,
                        padding: unit.type === 'heading' ? '4px 0' : '12px 16px',
                        background: bg,
                        border: `1px solid ${border}`,
                        borderRadius: 6,
                        cursor: unlocked ? 'pointer' : 'not-allowed',
                        opacity: isDone ? 0.75 : unlocked ? 1 : 0.5,
                        transition: 'all 0.2s',
                        position: 'relative',
                      }}
                    >
                      {/* 锁定提示 */}
                      {!unlocked && !isDone && (
                        <div style={{
                          position: 'absolute', top: 8, right: 12,
                          fontSize: 11, color: '#bfbfbf',
                        }}>
                           学完前文后解锁
                        </div>
                      )}

                      {/* 单元类型标签 */}
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: unit.type !== 'heading' ? 8 : 0, flexWrap: 'wrap', gap: 4 }}>
                        <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
                          {unit.type === 'heading' && <Tag color="purple" style={{ fontSize: 11, margin: 0 }}>章节</Tag>}
                          {unit.type === 'list' && <Tag color="green" style={{ fontSize: 11, margin: 0 }}>要点</Tag>}
                          {unit.is_important && <Tag color="orange" style={{ fontSize: 11, margin: 0 }}>重点</Tag>}
                          {!unlocked && !isDone && <Tag color="default" style={{ fontSize: 11, margin: 0 }}>未解锁</Tag>}
                        </div>
                        <div style={{ color: isDone ? '#52c41a' : '#ccc', fontSize: 18, flexShrink: 0, marginLeft: 8 }}>
                          {isDone ? (
                            <CheckCircleOutlined />
                          ) : unlocked ? (
                            <span style={{ display: 'inline-block', width: 18, height: 18, border: '2px solid #ccc', borderRadius: '50%' }} />
                          ) : (
                            <span></span>
                          )}
                        </div>
                      </div>

                      {/* 段落渲染 */}
                      {renderContent(unit, kcmap, openKpModal)}

                      {/* 关键词标签 */}
                      {unit.keywords && unit.keywords.length > 0 && unit.type !== 'heading' && (
                        <div style={{ marginTop: 8, display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                          {unit.keywords.map((kw: string, ki: number) => (
                            <KpTag key={ki} name={kw} kcmap={kcmap} onClick={() => openKpModal(kw)} />
                          ))}
                        </div>
                      )}
                    </div>
                  )
                })}
              </div>
            </Card>
          </>
        )}

        {/* 底部导航 */}
        <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 24, paddingBottom: 40 }}>
          <Button disabled={currentSection === 0} onClick={() => setCurrentSection(Math.max(0, currentSection - 1))}>← 上一章</Button>
          <Button
            type="primary"
            disabled={
              currentSection === visibleSections.length - 1 ||
              !visibleSections[currentSection].units.every(u => completedUnits.has(u.id))
            }
            onClick={() => setCurrentSection(Math.min(visibleSections.length - 1, currentSection + 1))}
            title={
              currentSection < visibleSections.length - 1 &&
              !visibleSections[currentSection].units.every(u => completedUnits.has(u.id))
                ? '请先完成当前章节所有单元'
                : undefined
            }
          >
            {completedUnits.size > 0 &&
            currentSection < visibleSections.length - 1 &&
            !visibleSections[currentSection].units.every(u => completedUnits.has(u.id))
              ? '本章未完成 →'
              : '下一章 →'}
          </Button>
        </div>
      </div>

      {/* 知识点弹窗 */}
      <Modal
        open={kpModalVisible}
        onCancel={() => setKpModalVisible(false)}
        title={
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <BookOutlined style={{ color: '#1890ff' }} />
            <span style={{ fontWeight: 600 }}>{kpModalTitle}</span>
          </div>
        }
        footer={<Button type="primary" onClick={() => setKpModalVisible(false)}>我知道了</Button>}
        width={600}
      >
        <div style={{ padding: '8px 4px', fontSize: 14, lineHeight: 2, color: '#333', maxHeight: '60vh', overflowY: 'auto' }}>
          {kpModalContent}
        </div>
      </Modal>

      <style>{`
        @media (max-width: 768px) { .desktop-sidebar { display: none !important; } }
        @media (min-width: 769px) { .mobile-only { display: none !important; } }
      `}</style>
    </div>
  )
}
