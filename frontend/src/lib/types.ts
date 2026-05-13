// V7 统一 TypeScript 类型定义

// === 分类 ===
export interface Category {
  id: number;
  code: string;
  name: string;
  description?: string;
  icon?: string;
  sort_order: number;
  is_active: boolean;
  created_at?: string;
  updated_at?: string;
}

export interface CategoryCreate {
  code: string;
  name: string;
  description?: string;
  sort_order?: number;
  is_active?: boolean;
}

export type CategoryUpdate = Partial<CategoryCreate>;

// === 课程 ===
export interface Course {
  id: number;
  category_id: number;
  code: string;
  name: string;
  description?: string;
  level?: string;
  duration_days?: number;
  min_students?: number;
  max_students?: number;
  sort_order: number;
  is_active: boolean;
  llm_enabled: boolean;
  created_at?: string;
  updated_at?: string;
  category_name?: string;
}

export interface CourseCreate {
  category_id: number;
  code: string;
  name: string;
  description?: string;
  level?: string;
  duration_days?: number;
  min_students?: number;
  max_students?: number;
  sort_order?: number;
  is_active?: boolean;
}

export type CourseUpdate = Partial<CourseCreate>;

// === 班级 ===
export interface ClassInfo {
  id: number;
  name: string;
  category_id?: number;
  status: string;
  start_date?: string;
  end_date?: string;
  max_students?: number;
  location?: string;
  description?: string;
  instructor_id?: number;
  manager_id?: number;
  instructor_name?: string;
  manager_name?: string;
  created_at?: string;
}

export interface ClassCreate {
  name: string;
  category_id: number;
  start_date?: string;
  end_date?: string;
  max_students?: number;
  location?: string;
  description?: string;
  instructor_id?: number;
  manager_id?: number;
}

export type ClassUpdate = Partial<ClassCreate>;

export interface ClassCourse {
  id: number;
  class_id: number;
  course_id: number;
  course_name?: string;
  sort_order?: number;
}

// === 教材 ===
export interface Textbook {
  id: number;
  name: string;
  description?: string;
  cover_image?: string;
  category_id?: number;
  category_name?: string;
  total_chapters?: number;
  total_pages?: number;
  file_type?: string;
  is_active: boolean;
  status?: string;
  llm_enabled: boolean;
  created_at?: string;
}

export interface TextbookCreate {
  name: string;
  description?: string;
  category_id: number;
  file_type?: string;
  is_active?: boolean;
}

export type TextbookUpdate = Partial<TextbookCreate>;

// === 用户 ===
export interface User {
  id: number;
  username: string;
  role: string;
  phone?: string;
  id_card?: string;
  province?: string;
  city?: string;
  company_id?: number;
  company_name?: string;
  is_active: boolean;
  created_at?: string;
}

// === 教练 ===
export interface Instructor extends User {
  instructor_code?: string;
}

export interface InstructorCreate {
  name: string;
  phone: string;
  password: string;
  instructor_code?: string;
  province?: string;
  city?: string;
  company_id?: number;
  is_active?: boolean;
}

export type InstructorUpdate = Partial<Omit<InstructorCreate, 'password'>>;

// === 人员 ===
export interface Person extends User {}

export interface PersonCreate {
  name: string;
  phone: string;
  password: string;
  role: string;
  id_card?: string;
  province?: string;
  city?: string;
  company_id?: number;
  is_active?: boolean;
}

export type PersonUpdate = Partial<Omit<PersonCreate, 'password'>>;

// === 单位 ===
export interface Company {
  id: number;
  name: string;
  province?: string;
  city?: string;
  contact?: string;
  created_at?: string;
}

export interface CompanyCreate {
  name: string;
  province?: string;
  city?: string;
  contact?: string;
}

export type CompanyUpdate = Partial<CompanyCreate>;

// === LLM 配置 ===
export interface LLMConfig {
  llm_enabled: boolean;
  api_key_masked?: string;
  model_name?: string;
  max_tokens?: number;
  temperature?: number;
}

// === 分页响应 ===
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}

// === 题目 ===
export interface Question {
  id: number;
  type: 'single' | 'multiple' | 'judge';
  content: string;
  options?: string[];
  correct_answer?: string;
  explanation?: string;
  chapter_id?: number;
  textbook_id?: number;
  difficulty_level?: string;
}

export interface QuestionCreate {
  question_type: string;
  content: string;
  options?: string[];
  answer?: string[];
  explanation?: string;
  chapter_id?: number;
  textbook_id?: number;
  difficulty?: number;
}

export type QuestionUpdate = Partial<Omit<QuestionCreate, 'content'>> & { content?: string };

// === 审计日志 ===
export interface AuditLog {
  id: number;
  user_name: string;
  user_role: string;
  action: string;
  target_type: string;
  target_name: string;
  details?: string;
  ip_address?: string;
  created_at: string;
}

// === 公告 ===
export interface Announcement {
  id: number;
  title: string;
  content: string;
  class_id?: number;
  class_name?: string;
  is_published: boolean;
  created_at: string;
}

// === 系统设置 ===
export interface SystemSetting {
  key: string;
  value: string;
  description?: string;
}

// === 仪表盘统计 ===
export interface DashboardStats {
  categories: number;
  courses: number;
  classes: number;
  activeClasses: number;
  textbooks: number;
  students: number;
}

// === 仪表盘快速数据 ===
export interface DashboardQuickStats {
  total_categories: number;
  total_courses: number;
  total_classes: number;
  active_classes: number;
  total_textbooks: number;
  total_students: number;
  llm_enabled?: boolean;
}

// === API 通用响应 ===
export interface ApiResponse<T = unknown> {
  success?: boolean;
  data?: T;
  message?: string;
  total?: number;
  page?: number;
  page_size?: number;
}