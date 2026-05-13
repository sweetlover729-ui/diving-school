'use client';

import { useEffect } from 'react';
import { usePathname, useSearchParams } from 'next/navigation';
import { getCourseTitle } from '@/lib/courseConfig';

/**
 * 客户端组件：根据当前 course 动态设置 document.title
 * 
 * 优先级：
 * 1. URL 参数中的 course（如 ?course=diving）
 * 2. localStorage 中的 course
 * 3. 默认标题（从 COURSE_CONFIG 读取第一个课程）
 */
export default function CourseTitleSetter() {
  const pathname = usePathname();
  const searchParams = useSearchParams();

  useEffect(() => {
    // 从 URL 参数获取 course
    const urlCourse = searchParams.get('course');

    // 如果 URL 中没有，从 localStorage 获取
    const currentCourse = urlCourse || localStorage.getItem('course');

    // 设置文档标题
    const title = getCourseTitle(currentCourse);
    document.title = title;
  }, [pathname, searchParams]);

  return null;  // 不渲染任何 UI
}
