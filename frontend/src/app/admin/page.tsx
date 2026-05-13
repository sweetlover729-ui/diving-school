'use client';

import { useState, useEffect } from 'react';
import { Card, Row, Col, Statistic, Table, Tag, Button, Spin } from 'antd';
import { TeamOutlined, BookOutlined, ReadOutlined, AppstoreOutlined } from '@ant-design/icons';
import { dashboardApi } from '@/lib/api';
import type { ClassInfo } from '@/lib/types';
import type { DashboardStats } from '@/lib/types';

export default function AdminDashboard() {
  const [stats, setStats] = useState<DashboardStats>({
    categories: 0, courses: 0, classes: 0, activeClasses: 0, textbooks: 0, students: 0,
  });
  const [recentClasses, setRecentClasses] = useState<ClassInfo[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadDashboard();
  }, []);

  const loadDashboard = async () => {
    try {
      const data = await dashboardApi.getStats();
      setStats(data);
    } catch {
      // 容错：保持默认值
    }
    setLoading(false);
  };

  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', padding: 100 }}>
        <Spin size="large" />
      </div>
    );
  }

  return (
    <div>
      {/* 统计卡片 */}
      <Row gutter={[16, 16]} style={{ marginBottom: 20 }}>
        <Col xs={24} sm={12} md={6}>
          <Card hoverable>
            <Statistic title="培训分类" value={stats.categories} prefix={<AppstoreOutlined />} />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card hoverable>
            <Statistic title="课程总数" value={stats.courses} prefix={<ReadOutlined />} />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card hoverable>
            <Statistic title="班级总数" value={stats.classes} prefix={<TeamOutlined />} />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card hoverable>
            <Statistic
              title="教材数量"
              value={stats.textbooks}
              prefix={<BookOutlined />}
            />
          </Card>
        </Col>
      </Row>

      {/* 进行中班级 */}
      <Row gutter={16}>
        <Col xs={24} md={12}>
          <Card title="平台概况" style={{ height: '100%' }}>
            <Row gutter={[16, 16]}>
              <Col span={12}>
                <Statistic title="进行中班级" value={stats.activeClasses} valueStyle={{ color: '#52c41a' }} />
              </Col>
              <Col span={12}>
                <Statistic title="学员总数" value={stats.students} />
              </Col>
              <Col span={12} style={{ marginTop: 16 }}>
                <Statistic title="培训分类" value={stats.categories} />
              </Col>
              <Col span={12} style={{ marginTop: 16 }}>
                <Statistic title="课程数量" value={stats.courses} />
              </Col>
            </Row>
          </Card>
        </Col>

        <Col xs={24} md={12}>
          <Card title="快捷导航">
            <Row gutter={[12, 12]}>
              {[
                { label: '分类管理', path: '/admin/categories' },
                { label: '课程管理', path: '/admin/courses' },
                { label: '班级管理', path: '/admin/classes' },
                { label: '教材管理', path: '/admin/textbooks' },
                { label: '教练管理', path: '/admin/instructors' },
                { label: '人员管理', path: '/admin/people' },
                { label: '题库管理', path: '/admin/questions' },
                { label: '系统设置', path: '/admin/system' },
                { label: '审计日志', path: '/admin/audit' },
              ].map(item => (
                <Col xs={8} key={item.path}>
                  <Button block href={item.path}>{item.label}</Button>
                </Col>
              ))}
            </Row>
          </Card>
        </Col>
      </Row>
    </div>
  );
}