"use client";

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Card, Button, message, Space, Tag, Tabs, List, Empty, Modal, Descriptions, Spin } from 'antd';
import { 
  ArrowLeftOutlined, EyeOutlined, BookOutlined,
  FileTextOutlined, QuestionCircleOutlined, FilePdfOutlined, FormOutlined
} from '@ant-design/icons';
import { http } from '@/lib/http';

const { TabPane } = Tabs;

const FIELD_TYPE_MAP: Record<string, { label: string; color: string }> = {
  text: { label: '文本', color: 'blue' },
  textarea: { label: '多行', color: 'cyan' },
  radio: { label: '单选', color: 'green' },
  checkbox: { label: '多选', color: 'orange' },
  yesno: { label: '是否', color: 'purple' },
  signature: { label: '签名', color: 'red' },
  date: { label: '日期', color: 'magenta' },
  date_auto: { label: '日期', color: 'magenta' },
  id_number: { label: '身份证', color: 'gold' },
  phone: { label: '手机', color: 'volcano' },
  guardian_signature: { label: '监护人签名', color: 'red' },
};

function DocumentPdfPreview({ template }: { template: Record<string, unknown> }) {
  const fields = template.fields_schema || [];
  
  return (
    <div style={{ padding: 32, maxWidth: 800, margin: '0 auto', background: '#fff' }}>
      {/* 文书头部 */}
      <div style={{ textAlign: 'center', marginBottom: 32 }}>
        <h2 style={{ fontSize: 22, fontWeight: 700 }}>{template.name}</h2>
        {template.institution_name && (
          <div style={{ color: '#666', marginTop: 4 }}>{template.institution_name}</div>
        )}
      </div>

      {/* 静态HTML部分 */}
      {template.static_html && (
        <div
          dangerouslySetInnerHTML={{ __html: template.static_html }}
          style={{ marginBottom: 24, lineHeight: 1.8 }}
        />
      )}

      {/* 字段预览（静态展示） */}
      {fields.map((field: Record<string, unknown>, idx: number) => {
        const typeInfo = FIELD_TYPE_MAP[field.type] || { label: field.type, color: 'default' };
        const isRequired = field.required !== false;

        if (field.type === 'signature' || field.type === 'guardian_signature') {
          return (
            <div key={idx} style={{ marginBottom: 24 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
                <span style={{ fontWeight: 500 }}>
                  {field.label || field.question}{isRequired && <span style={{ color: 'red' }}> *</span>}
                </span>
                <Tag color={typeInfo.color}>{typeInfo.label}</Tag>
              </div>
              <div style={{
                border: '2px dashed #999',
                borderRadius: 8,
                height: 100,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: '#999',
                fontSize: 13,
                background: '#fafafa'
              }}>
                [ 签名区域 ]
              </div>
            </div>
          );
        }

        if (field.type === 'radio' || field.type === 'yesno') {
          const opts = field.options || ['是', '否'];
          return (
            <div key={idx} style={{ marginBottom: 20 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
                <span style={{ fontWeight: 500 }}>
                  {field.label || field.question}{isRequired && <span style={{ color: 'red' }}> *</span>}
                </span>
                <Tag color={typeInfo.color}>{typeInfo.label}</Tag>
              </div>
              <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap' }}>
                {opts.map((opt: string, i: number) => (
                  <div key={i} style={{
                    padding: '8px 16px',
                    border: '1px solid #d9d9d9',
                    borderRadius: 6,
                    background: i === 0 ? '#e6f7ff' : '#fafafa',
                    fontSize: 14
                  }}>
                    ○ {opt}
                  </div>
                ))}
              </div>
            </div>
          );
        }

        if (field.type === 'checkbox' || field.type === 'multi_checkbox') {
          const opts = field.options || ['选项A', '选项B'];
          return (
            <div key={idx} style={{ marginBottom: 20 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
                <span style={{ fontWeight: 500 }}>
                  {field.label || field.question}{isRequired && <span style={{ color: 'red' }}> *</span>}
                </span>
                <Tag color={typeInfo.color}>{typeInfo.label}</Tag>
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                {opts.map((opt: string, i: number) => (
                  <div key={i} style={{
                    padding: '8px 12px',
                    border: '1px solid #d9d9d9',
                    borderRadius: 6,
                    background: '#fafafa',
                    fontSize: 14
                  }}>
                     {opt}
                  </div>
                ))}
              </div>
            </div>
          );
        }

        if (field.type === 'textarea' || field.type === 'multi_text') {
          return (
            <div key={idx} style={{ marginBottom: 20 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
                <span style={{ fontWeight: 500 }}>
                  {field.label || field.question}{isRequired && <span style={{ color: 'red' }}> *</span>}
                </span>
                <Tag color={typeInfo.color}>{typeInfo.label}</Tag>
              </div>
              <div style={{
                border: '1px solid #d9d9d9',
                borderRadius: 6,
                minHeight: 80,
                padding: 12,
                color: '#999',
                background: '#fafafa',
                fontSize: 14
              }}>
                [ 请在此填写... ]
              </div>
            </div>
          );
        }

        return (
          <div key={idx} style={{ marginBottom: 20 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
              <span style={{ fontWeight: 500 }}>
                {field.label || field.question}{isRequired && <span style={{ color: 'red' }}> *</span>}
              </span>
              <Tag color={typeInfo.color}>{typeInfo.label}</Tag>
            </div>
            <div style={{
              border: '1px solid #d9d9d9',
              borderRadius: 6,
              padding: '8px 12px',
              color: '#999',
              background: '#fafafa',
              fontSize: 14
            }}>
              [ 请在此填写 ]
            </div>
          </div>
        );
      })}

      {/* 底部签名区 */}
      <div style={{ marginTop: 40, display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end' }}>
        <div>
          <div style={{ color: '#666', marginBottom: 8 }}>学员签名：</div>
          <div style={{ width: 200, borderBottom: '1px solid #333', height: 50 }} />
        </div>
        <div>
          <div style={{ color: '#666', marginBottom: 8 }}>日期：______年______月______日</div>
        </div>
      </div>
    </div>
  );
}

function DocumentFillPreview({ template, onClose }: { template: Record<string, unknown>; onClose: () => void }) {
  const [answers, setAnswers] = useState<Record<string, any>>({});
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [canvasRef, setCanvasRef] = useState<HTMLCanvasElement | null>(null);
  const [isDrawing, setIsDrawing] = useState(false);
  const fields = template.fields_schema || [];

  const handleFieldChange = (fieldId: string, value: unknown) => {
    setAnswers(prev => ({ ...prev, [fieldId]: value }));
  };

  const startDraw = (e: React.MouseEvent<HTMLCanvasElement>) => {
    if (!canvasRef) return;
    setIsDrawing(true);
    const ctx = canvasRef.getContext('2d');
    if (!ctx) return;
    const rect = canvasRef.getBoundingClientRect();
    ctx.beginPath();
    ctx.moveTo(e.clientX - rect.left, e.clientY - rect.top);
  };

  const draw = (e: React.MouseEvent<HTMLCanvasElement>) => {
    if (!isDrawing || !canvasRef) return;
    const ctx = canvasRef.getContext('2d');
    if (!ctx) return;
    const rect = canvasRef.getBoundingClientRect();
    ctx.lineTo(e.clientX - rect.left, e.clientY - rect.top);
    ctx.strokeStyle = '#000';
    ctx.lineWidth = 2;
    ctx.stroke();
  };

  const endDraw = () => setIsDrawing(false);

  const clearCanvas = () => {
    if (!canvasRef) return;
    const ctx = canvasRef.getContext('2d');
    if (!ctx) return;
    ctx.clearRect(0, 0, canvasRef.width, canvasRef.height);
  };

  const handleSubmit = () => {
    // 管理员测试提交：不做任何数据保存，只演示提交成功
    setSubmitting(true);
    setTimeout(() => {
      setSubmitting(false);
      setSubmitted(true);
    }, 1000);
  };

  if (submitted) {
    return (
      <div style={{ padding: 48, textAlign: 'center' }}>
        <div style={{ fontSize: 48, marginBottom: 16 }}></div>
        <h2 style={{ color: '#52c41a', marginBottom: 8 }}>提交成功</h2>
        <p style={{ color: '#666' }}>以上是管理员测试填写演示，数据未实际保存</p>
        <Button onClick={() => { setSubmitted(false); setAnswers({}); clearCanvas(); }} style={{ marginTop: 16 }}>
          重新填写测试
        </Button>
      </div>
    );
  }

  return (
    <div style={{ maxWidth: 800, margin: '0 auto', padding: 24 }}>
      <div style={{ textAlign: 'center', marginBottom: 24 }}>
        <h2>{template.name}</h2>
        <p style={{ color: '#faad14', fontSize: 13 }}>️ 管理员体验模式 - 测试填写，不保存数据</p>
      </div>

      <div style={{ marginBottom: 24, padding: '12px 16px', background: '#fffbe6', borderRadius: 8, fontSize: 13, color: '#666' }}>
         提示：管理员在此可以完整体验学员的文书填写流程，包括手写签名功能。填写后点击「模拟提交」验证流程。
      </div>

      {fields.map((field: Record<string, unknown>, idx: number) => {
        const typeInfo = FIELD_TYPE_MAP[field.type] || { label: field.type, color: 'default' };
        const isRequired = field.required !== false;
        const label = field.label || field.question || '';

        if (field.type === 'signature') {
          return (
            <div key={idx} style={{ marginBottom: 24 }}>
              <div style={{ marginBottom: 8, fontWeight: 500 }}>
                {label}{isRequired && <span style={{ color: 'red' }}> *</span>}
                <Tag color={typeInfo.color} style={{ marginLeft: 8 }}>{typeInfo.label}</Tag>
              </div>
              <canvas
                ref={el => { if (el) setCanvasRef(el); }}
                width={600}
                height={120}
                style={{ border: '2px dashed #1890ff', borderRadius: 8, cursor: 'crosshair', background: '#fff', display: 'block' }}
                onMouseDown={startDraw}
                onMouseMove={draw}
                onMouseUp={endDraw}
                onMouseLeave={endDraw}
              />
              <Button size="small" onClick={clearCanvas} style={{ marginTop: 8 }}>清除签名</Button>
            </div>
          );
        }

        if (field.type === 'radio' || field.type === 'yesno') {
          const opts = field.options || ['是', '否'];
          return (
            <div key={idx} style={{ marginBottom: 20 }}>
              <div style={{ marginBottom: 8, fontWeight: 500 }}>
                {label}{isRequired && <span style={{ color: 'red' }}> *</span>}
                <Tag color={typeInfo.color} style={{ marginLeft: 8 }}>{typeInfo.label}</Tag>
              </div>
              <Space wrap>
                {opts.map((opt: string, i: number) => (
                  <Button
                    key={i}
                    type={answers[field.id] === opt ? 'primary' : 'default'}
                    onClick={() => handleFieldChange(field.id, opt)}
                  >
                    {opt}
                  </Button>
                ))}
              </Space>
            </div>
          );
        }

        if (field.type === 'checkbox' || field.type === 'multi_checkbox') {
          const opts = field.options || ['选项A', '选项B'];
          return (
            <div key={idx} style={{ marginBottom: 20 }}>
              <div style={{ marginBottom: 8, fontWeight: 500 }}>
                {label}{isRequired && <span style={{ color: 'red' }}> *</span>}
                <Tag color={typeInfo.color} style={{ marginLeft: 8 }}>{typeInfo.label}</Tag>
              </div>
              <Space wrap>
                {opts.map((opt: string, i: number) => {
                  const checked = (answers[field.id] || []).includes(opt);
                  return (
                    <Button
                      key={i}
                      type={checked ? 'primary' : 'default'}
                      onClick={() => {
                        const current = answers[field.id] || [];
                        if (checked) {
                          handleFieldChange(field.id, current.filter((c: string) => c !== opt));
                        } else {
                          handleFieldChange(field.id, [...current, opt]);
                        }
                      }}
                    >
                      {checked ? '' : ''} {opt}
                    </Button>
                  );
                })}
              </Space>
            </div>
          );
        }

        if (field.type === 'textarea' || field.type === 'multi_text') {
          return (
            <div key={idx} style={{ marginBottom: 20 }}>
              <div style={{ marginBottom: 8, fontWeight: 500 }}>
                {label}{isRequired && <span style={{ color: 'red' }}> *</span>}
                <Tag color={typeInfo.color} style={{ marginLeft: 8 }}>{typeInfo.label}</Tag>
              </div>
              <textarea
                value={answers[field.id] || ''}
                onChange={e => handleFieldChange(field.id, e.target.value)}
                rows={4}
                style={{ width: '100%', padding: 8, borderRadius: 6, border: '1px solid #d9d9d9', fontSize: 14 }}
                placeholder={`请输入${label}...`}
              />
            </div>
          );
        }

        return (
          <div key={idx} style={{ marginBottom: 20 }}>
            <div style={{ marginBottom: 8, fontWeight: 500 }}>
              {label}{isRequired && <span style={{ color: 'red' }}> *</span>}
              <Tag color={typeInfo.color} style={{ marginLeft: 8 }}>{typeInfo.label}</Tag>
            </div>
            <input
              type="text"
              value={answers[field.id] || ''}
              onChange={e => handleFieldChange(field.id, e.target.value)}
              style={{ width: '100%', padding: '8px 12px', borderRadius: 6, border: '1px solid #d9d9d9', fontSize: 14 }}
              placeholder={`请输入${label}...`}
            />
          </div>
        );
      })}

      <div style={{ marginTop: 32, textAlign: 'center' }}>
        <Button
          type="primary"
          size="large"
          loading={submitting}
          onClick={handleSubmit}
          style={{ minWidth: 200 }}
        >
          模拟提交（测试用，不保存数据）
        </Button>
      </div>
    </div>
  );
}

export default function AdminPreviewPage() {
  const router = useRouter();
  const [students, setStudents] = useState<any[]>([]);
  const [selectedStudent, setSelectedStudent] = useState<any>(null);
  const [textbooks, setTextbooks] = useState<any[]>([]);
  const [documents, setDocuments] = useState<any[]>([]);
  const [questions, setQuestions] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  // 预览模态框
  const [pdfPreviewVisible, setPdfPreviewVisible] = useState(false);
  const [fillPreviewVisible, setFillPreviewVisible] = useState(false);
  const [selectedDoc, setSelectedDoc] = useState<any>(null);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      setLoading(true);
      const classes = await http.get('/admin/classes');
      const allStudents: Record<string, unknown>[] = [];
      
      for (const cls of classes) {
        try {
          const classDetail = await http.get(`/admin/classes/${cls.id}`);
          const students = (classDetail.members || []).filter((m: Record<string, unknown>) => m.role === 'student');
          students.forEach((s: Record<string, unknown>) => {
            allStudents.push({ ...s, class_id: cls.id, class_name: cls.name });
          });
        } catch {}
      }
      setStudents(allStudents);

      const [tb, docs, qs] = await Promise.all([
        http.get('/admin/textbooks').catch(() => []),
        http.get('/admin/document-templates').catch(() => []),
        http.get('/admin/questions').catch(() => []),
      ]);
      setTextbooks(tb || []);
      setDocuments(docs || []);
      setQuestions((qs && qs.items && Array.isArray(qs.items)) ? qs.items : []);
    } catch (e) {
      message.error('获取数据失败');
    } finally {
      setLoading(false);
    }
  };

  const openPdfPreview = (doc: Record<string, unknown>) => {
    setSelectedDoc(doc);
    setPdfPreviewVisible(true);
  };

  const openFillPreview = (doc: Record<string, unknown>) => {
    setSelectedDoc(doc);
    setFillPreviewVisible(true);
  };

  return (
    <div style={{ padding: 24 }}>
      <div style={{ marginBottom: 16 }}>
        <Button icon={<ArrowLeftOutlined />} onClick={() => router.push('/admin')}>返回</Button>
      </div>
      
      <h1 style={{ fontSize: 24, marginBottom: 24 }}>️ 管理员课程预览中心</h1>

      <Tabs type="card" defaultActiveKey="course">
        {/* ── 课程预览 ── */}
        <TabPane tab={<span><BookOutlined /> 课程预览</span>} key="course">
          <Card loading={loading}>
            <div style={{ marginBottom: 24 }}>
              <h3>全课程预览（管理员模式）</h3>
              <p style={{ color: '#666', margin: '8px 0 16px' }}>
                以管理员身份预览完整教材，所有章节完全解锁，不受学员进度限制。
              </p>
              <Button type="primary" icon={<EyeOutlined />} onClick={() => router.push('/admin/textbook-preview/chapters')}>
                进入全课程预览
              </Button>
            </div>

            <div style={{ marginTop: 32, paddingTop: 24, borderTop: '1px solid #f0f0f0' }}>
              <h3>学员视角预览</h3>
              <p style={{ color: '#666', margin: '8px 0 16px' }}>
                选择学员后，以该学员身份预览学习界面。
              </p>
              <Space wrap>
                <select
                  style={{ padding: '8px 12px', border: '1px solid #d9d9d9', borderRadius: 6, minWidth: 280 }}
                  onChange={(e) => {
                    const student = students.find(s => s.user_id === parseInt(e.target.value));
                    setSelectedStudent(student);
                  }}
                >
                  <option value="">选择学员...</option>
                  {students.map(s => (
                    <option key={s.user_id} value={s.user_id}>{s.name} ({s.class_name})</option>
                  ))}
                </select>

                {selectedStudent && (
                  <Card size="small" style={{ background: '#fafafa' }}>
                    <strong>{selectedStudent.name}</strong>
                    <div style={{ fontSize: 12, color: '#666' }}>{selectedStudent.class_name}</div>
                  </Card>
                )}

                <Button type="primary" icon={<EyeOutlined />}
                  onClick={() => {
                    if (!selectedStudent) { message.warning('请选择学员'); return; }
                    router.push(`/admin/student-preview/${selectedStudent.user_id}/chapters`);
                  }}
                  disabled={!selectedStudent}
                >
                  预览学员学习
                </Button>
              </Space>
            </div>
          </Card>
        </TabPane>

        {/* ── 文书及问卷预览 ── */}
        <TabPane tab={<span><FileTextOutlined /> 文书及问卷预览</span>} key="documents">
          <Card loading={loading} title={`文书模板（${documents.length}份）`}>
            {documents.length === 0 ? (
              <Empty description="暂无文书模板" />
            ) : (
              <List
                dataSource={documents}
                renderItem={(doc: Record<string, unknown>) => (
                  <List.Item
                    actions={[
                      <Button key="pdf" icon={<FilePdfOutlined />} size="small"
                        onClick={() => openPdfPreview(doc)}>
                        PDF预览
                      </Button>,
                      <Button key="fill" icon={<FormOutlined />} size="small" type="primary"
                        onClick={() => openFillPreview(doc)}>
                        填写预览
                      </Button>,
                    ]}
                  >
                    <List.Item.Meta
                      title={
                        <Space>
                          {doc.name}
                          <Tag color={doc.is_required ? 'red' : 'default'}>
                            {doc.is_required ? '必填' : '选填'}
                          </Tag>
                          <Tag color={doc.is_active === false ? 'gray' : 'green'}>
                            {doc.is_active === false ? '已禁用' : '启用中'}
                          </Tag>
                        </Space>
                      }
                      description={
                        <div>
                          <div style={{ color: '#666' }}>{doc.description || '无描述'}</div>
                          <Space style={{ marginTop: 4 }}>
                            <Tag color="blue">{doc.fields_schema?.length || 0} 个字段</Tag>
                            <Tag>{doc.doc_type}</Tag>
                          </Space>
                        </div>
                      }
                    />
                  </List.Item>
                )}
              />
            )}
          </Card>
        </TabPane>

        {/* ── 试题预览 ── */}
        <TabPane tab={<span><QuestionCircleOutlined /> 试题预览</span>} key="questions">
          <Card loading={loading} title={`题库（${questions.length}题）`}>
            {(!Array.isArray(questions) || questions.length === 0) ? (
              <Empty description="暂无试题，请先在题库管理中添加题目" />
            ) : (
              <List
                dataSource={questions}
                renderItem={(q: Record<string, unknown>, index: number) => (
                  <List.Item>
                    <div style={{ width: '100%' }}>
                      <div style={{ marginBottom: 10 }}>
                        <Tag color="blue" style={{ marginRight: 8 }}>#{index + 1}</Tag>
                        {q.question_type === 'single' && <Tag color="cyan">单选题</Tag>}
                        {q.question_type === 'multiple' && <Tag color="purple">多选题</Tag>}
                        {q.question_type === 'judge' && <Tag color="orange">判断题</Tag>}
                        {q.question_type === 'fill' && <Tag color="blue">填空题</Tag>}
                      </div>
                      <div style={{ fontWeight: 600, fontSize: 15, marginBottom: 12, lineHeight: 1.6 }}>
                        {q.content || q.question}
                      </div>
                      {(q.options || q.choices) && (
                        <div style={{ paddingLeft: 8, color: '#444' }}>
                          {q.options.map((opt: string, i: number) => (
                            <div key={i} style={{ marginBottom: 6, padding: '6px 12px', background: '#fafafa', borderRadius: 6, border: '1px solid #f0f0f0' }}>
                              <Tag style={{ marginRight: 8 }}>{String.fromCharCode(65 + i)}</Tag>
                              {opt}
                            </div>
                          ))}
                        </div>
                      )}
                      {q.correct_answer && (
                        <div style={{ marginTop: 10, padding: '8px 12px', background: '#f6ffed', borderRadius: 6, display: 'inline-block' }}>
                          <Tag color="green"> 正确答案：{q.correct_answer}</Tag>
                          {q.explanation && <span style={{ marginLeft: 8, color: '#666', fontSize: 13 }}>{q.explanation}</span>}
                        </div>
                      )}
                    </div>
                  </List.Item>
                )}
              />
            )}
          </Card>
        </TabPane>
      </Tabs>

      {/* ── PDF预览模态框 ── */}
      <Modal
        title={<Space><FilePdfOutlined /> {selectedDoc?.name} - PDF预览</Space>}
        open={pdfPreviewVisible}
        onCancel={() => { setPdfPreviewVisible(false); setSelectedDoc(null); }}
        footer={null}
        width={850}
        centered
        styles={{ body: { maxHeight: '70vh', overflow: 'auto' } }}
      >
        {selectedDoc && <DocumentPdfPreview template={selectedDoc} />}
      </Modal>

      {/* ── 填写预览模态框 ── */}
      <Modal
        title={<Space><FormOutlined /> {selectedDoc?.name} - 填写体验</Space>}
        open={fillPreviewVisible}
        onCancel={() => { setFillPreviewVisible(false); setSelectedDoc(null); }}
        footer={null}
        width={850}
        centered
        styles={{ body: { maxHeight: '70vh', overflow: 'auto' } }}
      >
        {selectedDoc && <DocumentFillPreview template={selectedDoc} onClose={() => setFillPreviewVisible(false)} />}
      </Modal>
    </div>
  );
}
