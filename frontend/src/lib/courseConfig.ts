/**
 * 课程配置 - 多培训系统共享配置
 * 用于首页课程选择、登录页标题、后台侧边栏标题等
 */

export interface CourseConfig {
  key: string;
  fullTitle: string;
  shortTitle: string;
  shortCollapsed: string;
}

export const COURSE_CONFIG: Record<string, CourseConfig> = {
  diving: {
    key: 'diving',
    fullTitle: '应急救援与公共安全潜水培训系统',
    shortTitle: '潜水培训系统',
    shortCollapsed: '潜',
  },
  water: {
    key: 'water',
    fullTitle: '应急救援与公共安全水域救援培训系统',
    shortTitle: '水域救援培训系统',
    shortCollapsed: '水',
  },
  boat: {
    key: 'boat',
    fullTitle: '应急救援与公共安全舟艇培训系统',
    shortTitle: '舟艇培训系统',
    shortCollapsed: '舟',
  },
  swift: {
    key: 'swift',
    fullTitle: '应急救援与公共安全激流培训系统',
    shortTitle: '激流培训系统',
    shortCollapsed: '激',
  },
  rope: {
    key: 'rope',
    fullTitle: '应急救援与公共安全绳索培训系统',
    shortTitle: '绳索培训系统',
    shortCollapsed: '绳',
  },
};

export const COURSE_LIST = [
  { key: 'diving', label: '潜水培训' },
  { key: 'water', label: '水域救援' },
  { key: 'boat', label: '舟艇培训' },
  { key: 'swift', label: '激流培训' },
  { key: 'rope', label: '绳索培训' },
];

export function getCourseTitle(courseKey: string | null): string {
  if (!courseKey || !COURSE_CONFIG[courseKey]) {
    return '应急救援教育培训系统';
  }
  return COURSE_CONFIG[courseKey].fullTitle;
}

export function getCourseShortTitle(courseKey: string | null): string {
  if (!courseKey || !COURSE_CONFIG[courseKey]) {
    return '培训系统';
  }
  return COURSE_CONFIG[courseKey].shortTitle;
}
