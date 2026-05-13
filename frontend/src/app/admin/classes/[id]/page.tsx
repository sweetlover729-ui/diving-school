"use client";

import { useState, useEffect } from 'react';
import { useRouter, useParams } from 'next/navigation';
import { Card, Table, Button, Tag, Space, message, Modal, Form, Input, Select, Popconfirm, Row, Col, Statistic, Transfer, Empty } from 'antd';
import { ArrowLeftOutlined, PlusOutlined, DeleteOutlined, SendOutlined, CheckCircleOutlined } from '@ant-design/icons';
import { http } from '@/lib/http';

export default function ClassDetailPage() {
  const router = useRouter();
  const params = useParams();
  const classId = params.id as string;
  
  const [loading, setLoading] = useState(true);
  const [classInfo, setClassInfo] = useState<any>(null);
  const [members, setMembers] = useState<any[]>([]);
  const [textbooks, setTextbooks] = useState<any[]>([]);
  const [interactiveTextbooks, setInteractiveTextbooks] = useState<any[]>([]);
  const [allTextbooks, setAllTextbooks] = useState<any[]>([]);
  const [allInteractive, setAllInteractive] = useState<any[]>([]);
  const [allInstructors, setAllInstructors] = useState<any[]>([]);
  const [allPeople, setAllPeople] = useState<any[]>([]);
  const [allCompanies, setAllCompanies] = useState<any[]>([]);
  const [selectedRole, setSelectedRole] = useState<string>('student');
  const [selectedCompany, setSelectedCompany] = useState<number | null>(null);
  const [classDocuments, setClassDocuments] = useState<any[]>([]);
  
  // 课程管理
  const [allCourses, setAllCourses] = useState<any[]>([]);
  const [courseModalVisible, setCourseModalVisible] = useState(false);
  const [selectedCourseIds, setSelectedCourseIds] = useState<string[]>([]);
  const [savingCourses, setSavingCourses] = useState(false);
  
  // 模态框状态
  const [addMemberModalVisible, setAddMemberModalVisible] = useState(false);
  const [addTextbookModalVisible, setAddTextbookModalVisible] = useState(false);
  const [publishDocModalVisible, setPublishDocModalVisible] = useState(false);
  const [allDocuments, setAllDocuments] = useState<any[]>([]);
  const [selectedDocs, setSelectedDocs] = useState<number[]>([]);
  const [publishing, setPublishing] = useState(false);
  const [addForm] = Form.useForm();

  useEffect(() => {
    fetchClassDetail();
  }, [classId]);

  const fetchClassDetail = async () => {
    try {
      setLoading(true);
      const data = await http.get(`/admin/classes/${classId}`);
      setClassInfo(data);
      setMembers(data.members || []);
      
      // 获取班级教材
      const textbooksData = await http.get(`/admin/classes/${classId}/textbooks`);
      setTextbooks(textbooksData || []);
      
      // 获取班级互动式教材
      try {
        const intData = await http.get(`/admin/classes/${classId}/textbooks/interactive`);
        setInteractiveTextbooks(intData || []);
      } catch {
        setInteractiveTextbooks([]);
      }
      
      // 获取所有普通教材
      const allTextbooksData = await http.get('/admin/textbooks');
      setAllTextbooks(allTextbooksData || []);
      
      // 获取所有互动式教材（已转换的）
      try {
        const allIntData = await http.get('/admin/textbooks/interactive');
        setAllInteractive(allIntData || []);
      } catch {
        setAllInteractive([]);
      }
      
      // 获取所有教练
      const instructorsData = await http.get('/admin/instructors');
      setAllInstructors(instructorsData || []);
      
      // 获取班级已发布的文书
      try {
        const classDocsData = await http.get(`/admin/classes/${classId}/documents`);
        setClassDocuments(classDocsData || []);
      } catch {
        setClassDocuments([]);
      }
      
      // 获取所有人员
      try {
        const peopleData = await http.get('/admin/people');
        setAllPeople(peopleData || []);
      } catch {
        setAllPeople([]);
      }
      
      // 获取所有单位
      try {
        const companiesData = await http.get('/admin/companies');
        setAllCompanies(companiesData || []);
      } catch {
        setAllCompanies([]);
      }

      // 获取所有文书模板
      try {
        const docsData = await http.get('/admin/document-templates');
        setAllDocuments(docsData || []);
      } catch {
        setAllDocuments([]);
      }
      
      // 获取所有课程
      try {
        const coursesData = await http.get('/admin/courses');
        setAllCourses(coursesData || []);
      } catch {
        setAllCourses([]);
      }
    } catch (e) {
      message.error('获取班级详情失败');
    } finally {
      setLoading(false);
    }
  };

  // 添加成员
  const handleAddMember = async (values: Record<string, unknown>) => {
    try {
      let name = values.name;
      let id_card = values.id_card || null;
      let phone = values.phone || '';
      
      // 如果选择的是已有人员
      if (values.person_id) {
        const selectedPerson = allPeople.find((p: Record<string, unknown>) => p.id === values.person_id);
        if (selectedPerson) {
          name = selectedPerson.name;
          id_card = selectedPerson.id_card || selectedPerson.id_number || null;
          phone = selectedPerson.phone || '';
        }
      }
      
      // 如果是教练，从选择的教练信息获取
      if (values.role === 'instructor' && values.instructor_id) {
        const selectedInstructor = allInstructors.find((i: Record<string, unknown>) => i.id === values.instructor_id);
        if (selectedInstructor) {
          name = selectedInstructor.name;
          id_card = selectedInstructor.id_card || null;
          phone = selectedInstructor.phone || '';
        }
      }
      
      if (!name) {
        message.error('姓名不能为空');
        return;
      }
      
      // 学员必须有身份证，教练和管理干部不需要
      if (values.role === 'student' && !id_card) {
        message.error('学员身份证号不能为空');
        return;
      }
      
      const payload: Record<string, unknown> = {
        name: name,
        id_card: id_card,
        phone: phone,
        role: values.role,
      };
      
      if (values.role === 'instructor' && values.instructor_id) {
        payload.instructor_id = values.instructor_id;
      }
      
      await http.post(`/admin/classes/${classId}/members`, payload);
      message.success('添加成功');
      setAddMemberModalVisible(false);
      addForm.resetFields();
      setSelectedRole('student');
      setSelectedCompany(null);
      fetchClassDetail();
    } catch (e) {
      message.error(e.message || '添加失败');
    }
  };

  // 移除成员
  const handleRemoveMember = async (userId: number) => {
    try {
      await http.delete(`/admin/classes/${classId}/members/${userId}`);
      message.success('移除成功');
      fetchClassDetail();
    } catch (e) {
      message.error(e.message || '移除失败');
    }
  };

  // 添加教材（普通）
  const handleAddTextbook = async (textbookId: number) => {
    try {
      await http.post(`/admin/classes/${classId}/textbooks/${textbookId}`);
      message.success('教材已添加');
      fetchClassDetail();
    } catch (e) {
      message.error(e.message || '添加失败');
    }
  };

  // 添加互动式教材
  const handleAddInteractive = async (interactiveId: number) => {
    try {
      await http.post(`/admin/classes/${classId}/textbooks/interactive/${interactiveId}`);
      message.success('互动式教材已添加');
      setAddTextbookModalVisible(false);
      fetchClassDetail();
    } catch (e) {
      message.error(e.message || '添加失败');
    }
  };

  // 移除教材
  const handleRemoveTextbook = async (textbookId: number) => {
    try {
      await http.delete(`/admin/classes/${classId}/textbooks/${textbookId}`);
      message.success('教材已移除');
      fetchClassDetail();
    } catch (e) {
      message.error(e.message || '移除失败');
    }
  };

  const handleRemoveInteractive = async (textbookId: number) => {
    try {
      await http.delete(`/admin/classes/${classId}/textbooks/interactive/${textbookId}`);
      message.success('互动式教材已移除');
      fetchClassDetail();
    } catch (e) {
      message.error(e.message || '移除失败');
    }
  };

  // 保存班级课程
  const handleSaveCourses = async () => {
    setSavingCourses(true);
    try {
      const selectedCourses = allCourses
        .filter(c => selectedCourseIds.includes(c.code))
        .map(c => ({
          code: c.code,
          name: c.name,
          is_active: c.is_active
        }));
      
      await http.put(`/admin/classes/${classId}`, { courses: selectedCourses });
      message.success('班级课程已保存');
      setCourseModalVisible(false);
      fetchClassDetail();
    } catch (e) {
      message.error(e.message || '保存失败');
    } finally {
      setSavingCourses(false);
    }
  };

  // 打开课程分配弹窗
  const openCourseModal = () => {
    const currentCodes = classInfo?.courses?.map((c: Record<string, unknown>) => c.code) || [];
    setSelectedCourseIds(currentCodes);
    setCourseModalVisible(true);
  };

  // 发布文书到班级
  const handlePublishDocuments = async () => {
    if (selectedDocs.length === 0) {
      message.warning('请选择要发布的文书');
      return;
    }
    
    setPublishing(true);
    try {
      const result = await http.post(`/admin/classes/${classId}/publish-documents`, {
        template_ids: selectedDocs
      });
      message.success(result.message || '发布成功');
      setPublishDocModalVisible(false);
      setSelectedDocs([]);
      fetchClassDetail();
    } catch (e) {
      message.error(e.message || '发布失败');
    } finally {
      setPublishing(false);
    }
  };

  // 已选中的教材ID列表（普通+互动式）
  const assignedTextbookIds = textbooks.map((t: Record<string, unknown>) => t.id);
  const assignedInteractiveIds = interactiveTextbooks.map((t: Record<string, unknown>) => t.id);

  // 可选的普通教材
  const availableTextbooks = allTextbooks.filter((t: Record<string, unknown>) => !assignedTextbookIds.includes(t.id)
  );

  // 可选的互动式教材（排除已分配的）
  // 可选的互动式教材：排除已分配的，且过滤掉 chapter_count=1 的未实质转换教材
  const availableInteractive = allInteractive.filter((t: Record<string, unknown>) => !assignedInteractiveIds.includes(t.id) && (t.chapter_count || 0) > 1
  );

  // 成员表格列
  const memberColumns = [
    { title: '序号', key: 'index', width: 60, render: (_: unknown, __: unknown, idx: number) => idx + 1 },
    { title: '姓名', dataIndex: 'name', key: 'name', width: 100 },
    { 
      title: '角色', 
      dataIndex: 'role', 
      key: 'role', 
      width: 100,
      render: (role: string) => {
        const roleMap: Record<string, { color: string; text: string }> = {
          instructor: { color: 'blue', text: '教练' },
          manager: { color: 'purple', text: '管理干部' },
          student: { color: 'green', text: '学员' }
        };
        const r = roleMap[role] || { color: 'default', text: role };
        return <Tag color={r.color}>{r.text}</Tag>;
      }
    },
    { title: '身份证', dataIndex: 'id_card', key: 'id_card', width: 170, render: (v: string) => v || '-' },
    { title: '电话', dataIndex: 'phone', key: 'phone', width: 120, render: (v: string) => v || '-' },
    { 
      title: '密码', 
      key: 'password',
      width: 100,
      render: (_: unknown, record: Record<string, unknown>) => (
        <Tag color="orange">
          {record.phone ? record.phone.slice(-6) : '无手机号'}
        </Tag>
      )
    },
    {
      title: '操作',
      key: 'action',
      width: 150,
      render: (_: unknown, record: Record<string, unknown>) => (
        <Space>
          {record.role === 'student' && (
            <Button type="link" size="small" onClick={() => router.push(`/admin/classes/${classId}/student/${record.user_id}`)}>
              学习情况
            </Button>
          )}
          <Popconfirm title="确定移除？" onConfirm={() => handleRemoveMember(record.user_id)}>
            <Button type="link" danger size="small">移除</Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  // 教材表格列（普通教材）
  const textbookColumns = [
    { title: '教材名称', dataIndex: 'name', key: 'name' },
    { title: '章节数', dataIndex: 'total_chapters', key: 'total_chapters', width: 100 },
    { title: '页数', dataIndex: 'total_pages', key: 'total_pages', width: 80 },
    {
      title: '操作',
      key: 'action',
      width: 80,
      render: (_: unknown, record: Record<string, unknown>) => (
        <Popconfirm title="确定移除此教材？" onConfirm={() => handleRemoveTextbook(record.id)}>
          <Button type="link" danger icon={<DeleteOutlined />} />
        </Popconfirm>
      ),
    },
  ];

  // 互动式教材列
  const interactiveColumns = [
    {
      title: '教材名称',
      dataIndex: 'name',
      key: 'name',
      render: (name: string, record: Record<string, unknown>) => (
        <span>{name} <Tag color="cyan">互动式</Tag></span>
      )
    },
    { title: '章节数', dataIndex: 'chapter_count', key: 'chapter_count', width: 100 },
    {
      title: '操作',
      key: 'action',
      width: 120,
      render: (_: unknown, record: Record<string, unknown>) => (
        <Space>
          <Button type="link" size="small" onClick={() => router.push(`/admin/interactive-textbooks/${record.textbook_id}`)}>
            预览
          </Button>
          <Popconfirm title="确定移除？" onConfirm={() => handleRemoveInteractive(record.textbook_id)}>
            <Button type="link" danger size="small">移除</Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  const students = members.filter(m => m.role === 'student');
  const instructors = members.filter(m => m.role === 'instructor');
  const managers = members.filter(m => m.role === 'manager');

  return (
    <div style={{ padding: 24 }}>
      <div style={{ marginBottom: 16 }}>
        <Button icon={<ArrowLeftOutlined />} onClick={() => router.push('/admin/classes')}>返回班级列表</Button>
      </div>
      
      <h1 style={{ fontSize: 24, marginBottom: 24 }}>班级详情</h1>

      {/* 班级信息 */}
      <Card loading={loading} style={{ marginBottom: 24 }}>
        {classInfo && (
          <Row gutter={16}>
            <Col span={6}>
              <Statistic title="班级名称" value={classInfo.name} />
            </Col>
            <Col span={6}>
              <Statistic title="状态" value={classInfo.status === 'active' ? '进行中' : classInfo.status === 'pending' ? '待开班' : classInfo.status === 'ended' ? '已结班' : classInfo.status} />
            </Col>
            <Col span={6}>
              <Statistic title="地点" value={classInfo.location || '-'} />
            </Col>
            <Col span={6}>
              <Statistic title="开班时间" value={classInfo.start_time ? new Date(classInfo.start_time).toLocaleDateString('zh-CN') : '-'} />
            </Col>
          </Row>
        )}
      </Card>

      {/* 统计卡片 */}
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={8}>
          <Card><Statistic title="学员数" value={students.length} valueStyle={{ color: '#52c41a' }} /></Card>
        </Col>
        <Col span={8}>
          <Card><Statistic title="教练数" value={instructors.length} valueStyle={{ color: '#1890ff' }} /></Card>
        </Col>
        <Col span={8}>
          <Card><Statistic title="管理干部" value={managers.length} valueStyle={{ color: '#722ed1' }} /></Card>
        </Col>
      </Row>

      {/* 班级课程 */}
      <Card
        title="本期课程"
        style={{ marginBottom: 24 }}
        extra={
          <Button type="primary" onClick={openCourseModal}>
            {classInfo?.courses?.length > 0 ? '修改课程' : '分配课程'}
          </Button>
        }
      >
        {classInfo?.courses && classInfo.courses.length > 0 ? (
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
            {classInfo.courses.map((course: Record<string, unknown>) => (
              <Tag
                key={course.code}
                color={course.level === 'beginner' ? 'green' : course.level === 'intermediate' ? 'blue' : 'purple'}
                style={{ fontSize: 14, padding: '4px 12px' }}
              >
                {course.name}
              </Tag>
            ))}
          </div>
        ) : (
          <div style={{ color: '#999' }}>
            暂未分配课程。点击右上角「分配课程」为此班级分配本期开设的课程。
          </div>
        )}
      </Card>

      {/* 成员管理 */}
      <Card 
        title="班级成员"
        style={{ marginBottom: 24 }}
        extra={<Button type="primary" icon={<PlusOutlined />} onClick={() => setAddMemberModalVisible(true)}>添加成员</Button>}
      >
        <Table columns={memberColumns} dataSource={members} rowKey="user_id" loading={loading} pagination={{ pageSize: 10 }} size="small" />
      </Card>

      {/* 文书发布 */}
      <Card
        title="班级文书"
        style={{ marginBottom: 24 }}
        extra={<Button type="primary" icon={<SendOutlined />} onClick={() => setPublishDocModalVisible(true)}>发布文书</Button>}
      >
        {classDocuments.length > 0 ? (
          <div>
            <div style={{ marginBottom: 12, color: '#666' }}>已发布 {classDocuments.length} 份文书：</div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
              {classDocuments.map((doc: Record<string, unknown>) => (
                <Tag
                  key={doc.id || doc.template_id}
                  color="blue"
                  style={{ padding: '2px 8px 2px 12px', fontSize: 14, cursor: 'pointer' }}
                  onClick={() => router.push(`/admin/documents/preview/${doc.template_id || doc.id}`)}
                >
                  <span onClick={(e) => e.stopPropagation()}>{doc.name}</span>
                  <Popconfirm
                    title="确认移除"
                    description={`确定要从班级移除「${doc.name}」吗？`}
                    onConfirm={async () => {
                      const docId = doc.id || doc.template_id;
                      try {
                        await http.delete(`/admin/classes/${classId}/documents/${docId}`);
                        setClassDocuments(prev => prev.filter((d: Record<string, unknown>) => (d.id || d.template_id) !== docId));
                        message.success('文书已移除');
                      } catch (err) {
                        message.error(err.message || '移除失败');
                      }
                    }}
                    onCancel={() => {}}
                    okText="确认移除"
                    cancelText="取消"
                    okButtonProps={{ danger: true }}
                  >
                    <span
                      onClick={(e) => { e.stopPropagation(); }}
                      style={{ marginLeft: 6, color: '#999', cursor: 'pointer', fontSize: 12 }}
                      title="移除文书"
                    >×</span>
                  </Popconfirm>
                </Tag>
              ))}
            </div>
          </div>
        ) : (
          <div style={{ color: '#999' }}>暂无已发布文书。点击「发布文书」向班级学员推送需要签署的文书。</div>
        )}
      </Card>

      {/* 教材管理 */}
      <Card
        title="班级教材"
        extra={<Button type="primary" icon={<PlusOutlined />} onClick={() => setAddTextbookModalVisible(true)}>添加教材</Button>}
      >
        {textbooks.length > 0 || interactiveTextbooks.length > 0 ? (
          <div>
            {textbooks.length > 0 && (
              <>
                <div style={{ fontWeight: 600, marginBottom: 8, color: '#333' }}>PDF教材</div>
                <Table columns={textbookColumns} dataSource={textbooks} rowKey="id" pagination={false} size="small" style={{ marginBottom: 16 }} />
              </>
            )}
            {interactiveTextbooks.length > 0 && (
              <>
                <div style={{ fontWeight: 600, marginBottom: 8, color: '#333' }}>互动式教材</div>
                <Table columns={interactiveColumns} dataSource={interactiveTextbooks} rowKey="id" pagination={false} size="small" />
              </>
            )}
          </div>
        ) : (
          <Empty description="暂无教材，请点击上方按钮添加" />
        )}
      </Card>

      {/* ──────────── 添加成员模态框 ──────────── */}
      <Modal
        title="添加班级成员"
        open={addMemberModalVisible}
        onCancel={() => { setAddMemberModalVisible(false); addForm.resetFields(); setSelectedRole('student'); setSelectedCompany(null); }}
        footer={null}
        width={520}
      >
        <Form form={addForm} layout="vertical" onFinish={handleAddMember}>
          <Form.Item name="role" label="角色" rules={[{ required: true }]} initialValue="student">
            <Select onChange={(value) => { setSelectedRole(value); setSelectedCompany(null); addForm.setFieldValue('person_id', undefined); addForm.setFieldValue('instructor_id', undefined); }}>
              <Select.Option value="student"><Tag color="green">学员</Tag></Select.Option>
              <Select.Option value="instructor"><Tag color="blue">教练</Tag></Select.Option>
              <Select.Option value="manager"><Tag color="purple">管理干部</Tag></Select.Option>
            </Select>
          </Form.Item>
          
          {/* 教练和管理干部需要选择单位 */}
          {(selectedRole === 'instructor' || selectedRole === 'manager') && (
            <Form.Item name="company_id" label="所属单位" rules={[{ required: true }]}>
              <Select placeholder="请选择所属单位" showSearch optionFilterProp="children" onChange={(value) => setSelectedCompany(value)}>
                {allCompanies.map((company: Record<string, unknown>) => (
                  <Select.Option key={company.id} value={company.id}>{company.name}</Select.Option>
                ))}
              </Select>
            </Form.Item>
          )}
          
          {/* 教练选择 */}
          {selectedRole === 'instructor' && (
            <Form.Item name="instructor_id" label="选择教练" rules={[{ required: true }]}>
              <Select placeholder="请选择教练" showSearch optionFilterProp="children"
                onChange={(value) => {
                  const inst = allInstructors.find((i: Record<string, unknown>) => i.id === value);
                  if (inst) { addForm.setFieldsValue({ name: inst.name, id_card: inst.id_card || '', phone: inst.phone || '' }); }
                }}
              >
                {allInstructors.filter((inst: Record<string, unknown>) => !selectedCompany || inst.company_id === selectedCompany).map((inst: Record<string, unknown>) => (
                  <Select.Option key={inst.id} value={inst.id}>{inst.name} - {inst.phone || '无手机'}</Select.Option>
                ))}
              </Select>
            </Form.Item>
          )}
          
          {/* 学员和管理干部 */}
          {(selectedRole === 'student' || selectedRole === 'manager') && (
            <>
              <Form.Item name="person_id" label="从现有人员选择（可选）">
                <Select placeholder="不选择则手动输入" showSearch allowClear optionFilterProp="children"
                  onChange={(value) => {
                    if (value) {
                      const person = allPeople.find((p: Record<string, unknown>) => p.id === value);
                      if (person) { addForm.setFieldsValue({ name: person.name, id_card: person.id_card || person.id_number || '', phone: person.phone || '' }); }
                    } else {
                      addForm.setFieldsValue({ name: '', id_card: '', phone: '' });
                    }
                  }}
                >
                  {allPeople.filter((p: Record<string, unknown>) => {
                    const role = (p.role || '').toUpperCase();
                    const targetRole = selectedRole === 'student' ? 'STUDENT' : 'MANAGER';
                    return role === targetRole && (!selectedCompany || p.company_id === selectedCompany);
                  }).map((person: Record<string, unknown>) => (
                    <Select.Option key={person.id} value={person.id}>{person.name} - {person.id_card || '无身份证'}</Select.Option>
                  ))}
                </Select>
              </Form.Item>
              
              <Form.Item name="name" label="姓名" rules={[{ required: true, message: '请输入姓名' }]}>
                <Input placeholder="请输入姓名" />
              </Form.Item>
              
              <Form.Item 
                name="id_card" 
                label="身份证号" 
                rules={selectedRole === 'student' ? [{ required: true, message: '学员必须填写身份证号' }] : []}
                extra={selectedRole === 'manager' ? '管理干部可不填' : ''}
              >
                <Input placeholder={selectedRole === 'manager' ? '可不填写' : '请输入身份证号'} />
              </Form.Item>
              
              <Form.Item name="phone" label="手机号码">
                <Input placeholder="请输入手机号码" />
              </Form.Item>
            </>
          )}
          
          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit">添加</Button>
              <Button onClick={() => { setAddMemberModalVisible(false); addForm.resetFields(); setSelectedRole('student'); }}>取消</Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>

      {/* ──────────── 发布文书模态框（多选）──────────── */}
      <Modal
        title="发布文书到班级"
        open={publishDocModalVisible}
        onCancel={() => { setPublishDocModalVisible(false); setSelectedDocs([]); }}
        onOk={handlePublishDocuments}
        confirmLoading={publishing}
        okText={`发布 ${selectedDocs.length > 0 ? `(${selectedDocs.length}份)` : ''}`}
        width={600}
      >
        <div style={{ marginBottom: 16, color: '#666' }}>勾选要发布的文书（可多选），发布后班级所有学员将收到签署通知：</div>
        <div style={{ maxHeight: 400, overflow: 'auto' }}>
          {allDocuments.length === 0 ? (
            <div style={{ color: '#999', textAlign: 'center', padding: 20 }}>暂无文书模板</div>
          ) : allDocuments.map(doc => (
            <div
              key={doc.id}
              style={{
                padding: '12px 16px',
                marginBottom: 8,
                background: selectedDocs.includes(doc.id) ? '#e6f7ff' : '#fafafa',
                border: selectedDocs.includes(doc.id) ? '1px solid #1890ff' : '1px solid #f0f0f0',
                borderRadius: 8,
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                cursor: 'pointer',
              }}
              onClick={() => {
                setSelectedDocs(prev => prev.includes(doc.id) ? prev.filter(id => id !== doc.id) : [...prev, doc.id]);
              }}
            >
              <div>
                <div style={{ fontWeight: 500 }}>{doc.name}</div>
                <div style={{ fontSize: 12, color: '#999' }}>
                  {doc.doc_type === 'health' ? '健康声明' : doc.doc_type === 'waiver' ? '免责协议' : doc.doc_type === 'agreement' ? '同意书' : '问卷调查'}
                  {doc.is_required ? <Tag color="red" style={{ marginLeft: 8 }}>必填</Tag> : <Tag style={{ marginLeft: 8 }}>选填</Tag>}
                </div>
              </div>
              {selectedDocs.includes(doc.id) && <CheckCircleOutlined style={{ color: '#1890ff', fontSize: 18 }} />}
            </div>
          ))}
        </div>
        {selectedDocs.length > 0 && (
          <div style={{ marginTop: 16, padding: 12, background: '#f6ffed', borderRadius: 8, textAlign: 'center' }}>
            已选择 {selectedDocs.length} 份文书，将统一发布给班级所有学员
          </div>
        )}
      </Modal>

      {/* ──────────── 添加教材模态框（普通+互动式分开）──────────── */}
      <Modal
        title="添加班级教材"
        open={addTextbookModalVisible}
        onCancel={() => setAddTextbookModalVisible(false)}
        footer={null}
        width={560}
      >
        <div style={{ maxHeight: 500, overflow: 'auto' }}>
          {/* 普通教材 */}
          <div style={{ marginBottom: 24 }}>
            <div style={{ fontWeight: 600, marginBottom: 12, color: '#333', borderBottom: '1px solid #f0f0f0', paddingBottom: 8 }}>
              PDF教材（{availableTextbooks.length}个可用）
            </div>
            {availableTextbooks.length === 0 ? (
              <div style={{ color: '#999', textAlign: 'center', padding: 12 }}>所有教材已添加完毕</div>
            ) : availableTextbooks.map(t => (
              <div key={t.id}
                style={{ padding: '10px 14px', marginBottom: 6, background: '#f5f5f5', borderRadius: 8, display: 'flex', justifyContent: 'space-between', alignItems: 'center', cursor: 'pointer' }}
                onClick={() => { handleAddTextbook(t.id); setAddTextbookModalVisible(false); }}
              >
                <div>
                  <div style={{ fontWeight: 500 }}>{t.name}</div>
                  <div style={{ fontSize: 12, color: '#999' }}>{t.total_chapters}章节 · {t.total_pages}页</div>
                </div>
                <Button type="primary" size="small">添加</Button>
              </div>
            ))}
          </div>

          {/* 互动式教材 */}
          <div>
            <div style={{ fontWeight: 600, marginBottom: 12, color: '#333', borderBottom: '1px solid #f0f0f0', paddingBottom: 8 }}>
              互动式教材（{availableInteractive.length}个可用）
            </div>
            {availableInteractive.length === 0 ? (
              <div style={{ color: '#999', textAlign: 'center', padding: 12 }}>暂无可用的互动式教材</div>
            ) : availableInteractive.map(t => (
              <div key={t.id}
                style={{ padding: '10px 14px', marginBottom: 6, background: '#f0f5ff', borderRadius: 8, display: 'flex', justifyContent: 'space-between', alignItems: 'center', cursor: 'pointer' }}
                onClick={() => handleAddInteractive(t.id)}
              >
                <div>
                  <div style={{ fontWeight: 500 }}>{t.name} <Tag color="cyan" style={{ marginLeft: 6 }}>互动式</Tag></div>
                  <div style={{ fontSize: 12, color: '#999' }}>{t.chapter_count || t.total_chapters}章节</div>
                </div>
                <Button type="primary" size="small" style={{ background: '#1890ff' }}>添加</Button>
              </div>
            ))}
          </div>
        </div>
      </Modal>

      {/* ──────────── 分配课程弹窗 ──────────── */}
      <Modal
        title="分配本期课程"
        open={courseModalVisible}
        onCancel={() => setCourseModalVisible(false)}
        footer={null}
        width={600}
      >
        <div style={{ marginBottom: 16, color: '#666', fontSize: 13 }}>
          选择此班级本期开设的课程。分配后，班级学员在填写入学文书时，将从以下课程中选择自己要上的课程。
        </div>
        
        {allCourses.length === 0 ? (
          <div style={{ textAlign: 'center', padding: 32, color: '#999' }}>
            <div>暂无课程可选</div>
            <div style={{ marginTop: 8, fontSize: 12 }}>
              请先在「课程设置」中添加课程，或点击「初始化默认课程」
            </div>
          </div>
        ) : (
          <div style={{ maxHeight: 400, overflow: 'auto' }}>
            {allCourses.filter(c => c.is_active).length === 0 ? (
              <div style={{ textAlign: 'center', padding: 32, color: '#999' }}>
                所有课程均已停用，无法分配
              </div>
            ) : (
              allCourses.filter(c => c.is_active).map(course => (
                <div
                  key={course.code}
                  style={{
                    padding: '12px 16px',
                    marginBottom: 8,
                    background: selectedCourseIds.includes(course.code) ? '#e6f7ff' : '#fafafa',
                    border: selectedCourseIds.includes(course.code) ? '1px solid #1890ff' : '1px solid #f0f0f0',
                    borderRadius: 8,
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    cursor: 'pointer',
                  }}
                  onClick={() => {
                    setSelectedCourseIds(prev =>
                      prev.includes(course.code)
                        ? prev.filter(id => id !== course.code)
                        : [...prev, course.code]
                    );
                  }}
                >
                  <div>
                    <div style={{ fontWeight: 500 }}>{course.name}</div>
                    <div style={{ fontSize: 12, color: '#999' }}>
                      代码：{course.code}
                      {course.duration_days && ` · ${course.duration_days}天`}
                      {course.max_depth && ` · 最大深度${course.max_depth}米`}
                    </div>
                  </div>
                  {selectedCourseIds.includes(course.code) && (
                    <CheckCircleOutlined style={{ color: '#1890ff', fontSize: 18 }} />
                  )}
                </div>
              ))
            )}
          </div>
        )}
        
        {selectedCourseIds.length > 0 && (
          <div style={{ marginTop: 16, padding: 12, background: '#f6ffed', borderRadius: 8, textAlign: 'center' }}>
            已选择 {selectedCourseIds.length} 门课程
          </div>
        )}
        
        <div style={{ marginTop: 16, display: 'flex', justifyContent: 'flex-end', gap: 8 }}>
          <Button onClick={() => setCourseModalVisible(false)}>取消</Button>
          <Button
            type="primary"
            loading={savingCourses}
            onClick={handleSaveCourses}
            disabled={selectedCourseIds.length === 0}
          >
            保存分配
          </Button>
        </div>
      </Modal>
    </div>
  );
}
