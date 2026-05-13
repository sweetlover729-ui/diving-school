// V7 统一 API 服务层
// 所有 API 调用集中在此，提供类型安全的接口
// CRUD: create → get → update → remove

import { http } from './http';
import type {
  Category, CategoryCreate, CategoryUpdate,
  Course, CourseCreate, CourseUpdate,
  ClassInfo, ClassCreate, ClassUpdate, ClassCourse,
  Textbook, TextbookCreate, TextbookUpdate,
  User, Instructor, InstructorCreate, InstructorUpdate,
  Person, PersonCreate, PersonUpdate,
  Company, CompanyCreate, CompanyUpdate,
  LLMConfig,
  Question, QuestionCreate, QuestionUpdate,
  AuditLog,
  Announcement,
  SystemSetting,
  DashboardQuickStats,
  PaginatedResponse,
} from './types';

// ============================================================
// 分类 API
// ============================================================
export const categoryApi = {
  list: () => http.get<Category[]>('/admin/categories'),
  get: (id: number) => http.get<Category>(`/admin/categories/${id}`),
  create: (data: CategoryCreate) => http.post<Category>('/admin/categories', data),
  update: (id: number, data: CategoryUpdate) =>
    http.put<Category>(`/admin/categories/${id}`, data),
  remove: (id: number) => http.delete(`/admin/categories/${id}`),
};

// ============================================================
// 课程 API
// ============================================================
export const courseApi = {
  list: () => http.get<Course[]>('/admin/courses'),
  get: (id: number) => http.get<Course>(`/admin/courses/${id}`),
  create: (data: CourseCreate) => http.post<Course>('/admin/courses', data),
  update: (id: number, data: CourseUpdate) =>
    http.put<Course>(`/admin/courses/${id}`, data),
  remove: (id: number) => http.delete(`/admin/courses/${id}`),
};

// ============================================================
// 班级 API
// ============================================================
export const classApi = {
  list: () => http.get<ClassInfo[]>('/admin/classes'),
  get: (id: number) => http.get<ClassInfo>(`/admin/classes/${id}`),
  create: (data: ClassCreate) => http.post<ClassInfo>('/admin/classes', data),
  update: (id: number, data: ClassUpdate) =>
    http.put<ClassInfo>(`/admin/classes/${id}`, data),
  remove: (id: number) => http.delete(`/admin/classes/${id}`),

  // 班级课程绑定
  getCourses: (classId: number) => http.get<ClassCourse[]>(`/admin/classes/${classId}/courses`),
  addCourse: (classId: number, data: { course_id: number }) =>
    http.post<ClassCourse>(`/admin/classes/${classId}/courses`, data),
  addCoursesBatch: (classId: number, data: { course_ids: number[] }) =>
    http.post(`/admin/classes/${classId}/courses/batch`, data),
  removeCourse: (classId: number, courseId: number) =>
    http.delete(`/admin/classes/${classId}/courses/${courseId}`),

  // 班级操作
  start: (classId: number) => http.post(`/admin/classes/${classId}/start`),
  end: (classId: number) => http.post(`/admin/classes/${classId}/end`),
  getAnalytics: (classId: number) => http.get(`/admin/classes/${classId}/analytics`),
};

// ============================================================
// 教材 API
// ============================================================
export const textbookApi = {
  list: () => http.get<Textbook[]>('/admin/textbooks'),
  get: (id: number) => http.get<Textbook>(`/admin/textbooks/${id}`),
  create: (data: TextbookCreate) => http.post<Textbook>('/admin/textbooks', data),
  update: (id: number, data: TextbookUpdate) =>
    http.put<Textbook>(`/admin/textbooks/${id}`, data),
  remove: (id: number) => http.delete(`/admin/textbooks/${id}`),

  // 章节
  getChapters: (textbookId: number) => http.get(`/admin/textbooks/${textbookId}/chapters`),
  importContent: (textbookId: number, data: { content: string }) =>
    http.post(`/admin/textbooks/${textbookId}/import`, data),
  uploadPdf: (textbookId: number, formData: FormData) =>
    http.post(`/admin/textbooks/${textbookId}/upload-pdf`, formData),
  getPages: (textbookId: number) => http.get(`/admin/textbooks/${textbookId}/pages`),
};

// ============================================================
// 教练 API
// ============================================================
export const instructorApi = {
  list: () => http.get<Instructor[]>('/admin/instructors'),
  get: (id: number) => http.get<Instructor>(`/admin/instructors/${id}`),
  create: (data: InstructorCreate) => http.post<Instructor>('/admin/instructors', data),
  update: (id: number, data: InstructorUpdate) =>
    http.put<Instructor>(`/admin/instructors/${id}`, data),
  remove: (id: number) => http.delete(`/admin/instructors/${id}`),
  resetPassword: (id: number, data: { password: string }) =>
    http.post(`/admin/instructors/${id}/reset-password`, data),
};

// ============================================================
// 人员 API
// ============================================================
export const peopleApi = {
  list: () => http.get<Person[]>('/admin/people'),
  get: (id: number) => http.get<Person>(`/admin/people/${id}`),
  create: (data: PersonCreate) => http.post<Person>('/admin/people', data),
  update: (id: number, data: PersonUpdate) =>
    http.put<Person>(`/admin/people/${id}`, data),
  remove: (id: number) => http.delete(`/admin/people/${id}`),
  resetPassword: (id: number, data: { password: string }) =>
    http.post(`/admin/people/${id}/reset-password`, data),
};

// ============================================================
// 单位 API
// ============================================================
export const companyApi = {
  list: () => http.get<Company[]>('/admin/companies'),
  get: (id: number) => http.get<Company>(`/admin/companies/${id}`),
  create: (data: CompanyCreate) => http.post<Company>('/admin/companies', data),
  update: (id: number, data: CompanyUpdate) =>
    http.put<Company>(`/admin/companies/${id}`, data),
  remove: (id: number) => http.delete(`/admin/companies/${id}`),
};

// ============================================================
// 题库 API
// ============================================================
export const questionApi = {
  list: (params?: { type?: string; search?: string; page?: number; page_size?: number }) =>
    http.get<PaginatedResponse<Question> | Question[]>(
      `/admin/questions${params ? '?' + new URLSearchParams(
        Object.entries(params).filter(([, v]) => v !== undefined).map(([k, v]) => [k, String(v)])
      ).toString() : ''}`
    ),
  get: (id: number) => http.get<Question>(`/admin/questions/${id}`),
  create: (data: QuestionCreate) => http.post<Question>('/admin/questions', data),
  update: (id: number, data: QuestionUpdate) =>
    http.put<Question>(`/admin/questions/${id}`, data),
  remove: (id: number) => http.delete(`/admin/questions/${id}`),
  getImportTemplate: () => http.get('/admin/questions/import-template'),
  importBatch: (data: { questions: QuestionCreate[] }) =>
    http.post('/admin/questions/import', data),
};

// ============================================================
// LLM 配置
// ============================================================
export const llmApi = {
  getConfig: () => http.get<LLMConfig>('/admin/llm-config'),
  updateConfig: (data: Partial<LLMConfig>) => http.put('/admin/llm-config', data),
  getCoursesStatus: () => http.get<{ courses: { id: number; name: string; llm_enabled: boolean }[] }>('/admin/llm-config/courses'),
  getTextbooksStatus: () => http.get<{ textbooks: { id: number; name: string; llm_enabled: boolean }[] }>('/admin/llm-config/textbooks'),
  updateCourseLLM: (courseId: number, enabled: boolean) =>
    http.put(`/admin/llm-config/courses/${courseId}`, { llm_enabled: enabled }),
  updateTextbookLLM: (textbookId: number, enabled: boolean) =>
    http.put(`/admin/llm-config/textbooks/${textbookId}`, { llm_enabled: enabled }),
};

// ============================================================
// 系统管理
// ============================================================
export const auditApi = {
  list: (params?: { page?: number; page_size?: number; search?: string }) =>
    http.get<PaginatedResponse<AuditLog>>(
      `/admin/audit-logs${params ? '?' + new URLSearchParams(
        Object.entries(params).filter(([, v]) => v !== undefined).map(([k, v]) => [k, String(v)])
      ).toString() : ''}`
    ),
};

export const announcementApi = {
  list: () => http.get<Announcement[]>('/admin/announcements'),
  create: (data: { title: string; content: string; class_id?: number }) =>
    http.post<Announcement>('/admin/announcements', data),
  update: (id: number, data: Partial<{ title: string; content: string }>) =>
    http.put<Announcement>(`/admin/announcements/${id}`, data),
  remove: (id: number) => http.delete(`/admin/announcements/${id}`),
};

export const settingsApi = {
  list: () => http.get<SystemSetting[]>('/admin/settings'),
  update: (key: string, value: string) => http.put(`/admin/settings/${key}`, { value }),
};

// ============================================================
// 仪表盘
// ============================================================
export const dashboardApi = {
  getStats: async (): Promise<DashboardQuickStats> => {
    try {
      const [categories, courses, classes, textbooks] = await Promise.all([
        categoryApi.list(),
        courseApi.list(),
        classApi.list(),
        textbookApi.list(),
      ]);
      return {
        total_categories: Array.isArray(categories) ? categories.length : 0,
        total_courses: Array.isArray(courses) ? courses.length : 0,
        total_classes: Array.isArray(classes) ? classes.length : 0,
        active_classes: Array.isArray(classes) ? classes.filter((c: ClassInfo) => c.status === 'ACTIVE').length : 0,
        total_textbooks: Array.isArray(textbooks) ? textbooks.length : 0,
        total_students: 0,
      };
    } catch {
      return { total_categories: 0, total_courses: 0, total_classes: 0, active_classes: 0, total_textbooks: 0, total_students: 0 };
    }
  },

  getLlmStatus: () => llmApi.getConfig(),
  getCoursesLLM: () => llmApi.getCoursesStatus(),
  getTextbooksLLM: () => llmApi.getTextbooksStatus(),
};