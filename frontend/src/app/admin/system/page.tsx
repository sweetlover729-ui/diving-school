'use client';

import { useState, useEffect } from 'react';
import { Card, Descriptions, Tag, Button, Switch, Space, message, Spin, Table, Modal, Select } from 'antd';
import { ReloadOutlined, RobotOutlined, CheckCircleOutlined, SettingOutlined } from '@ant-design/icons';
import { dashboardApi, llmApi } from '@/lib/api';
import StatusWrapper from '@/components/StatusWrapper';
import type { LLMConfig } from '@/lib/types';

export default function SystemPage() {
  const [loading, setLoading] = useState(true);
  const [llmConfig, setLlmConfig] = useState<LLMConfig | null>(null);
  const [toggling, setToggling] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [coursesModalOpen, setCoursesModalOpen] = useState(false);
  const [textbooksModalOpen, setTextbooksModalOpen] = useState(false);
  const [courseLLMList, setCourseLLMList] = useState<any[]>([]);
  const [textbookLLMList, setTextbookLLMList] = useState<any[]>([]);

  useEffect(() => { loadAll(); }, []);

  const loadAll = async () => {
    setLoading(true);
    setError(null);
    try {
      const [config, courses, textbooks] = await Promise.all([
        llmApi.getConfig(),
        llmApi.getCoursesStatus().catch(() => ({ courses: [] })),
        llmApi.getTextbooksStatus().catch(() => ({ textbooks: [] })),
      ]);
      setLlmConfig(config);
      setCourseLLMList(courses?.courses || []);
      setTextbookLLMList(textbooks?.textbooks || []);
    } catch {}
    setLoading(false);
  };

  const toggleGlobalLLM = async (enabled: boolean) => {
    setToggling(true);
    try {
      await llmApi.updateConfig({ llm_enabled: enabled });
      setLlmConfig(prev => prev ? { ...prev, llm_enabled: enabled } : null);
      message.success(enabled ? 'LLM 已全局启用' : 'LLM 已全局关闭');
    } catch (e: any) { message.error(e.message || '操作失败'); }
    finally { setToggling(false); }
  };

  const toggleCourseLLM = async (courseId: number, enabled: boolean) => {
    try {
      await llmApi.updateCourseLLM(courseId, enabled);
      setCourseLLMList(prev => prev.map(c => c.id === courseId ? { ...c, llm_enabled: enabled } : c));
      message.success('已更新');
    } catch (e: any) { message.error(e.message || '操作失败'); }
  };

  const toggleTextbookLLM = async (textbookId: number, enabled: boolean) => {
    try {
      await llmApi.updateTextbookLLM(textbookId, enabled);
      setTextbookLLMList(prev => prev.map(t => t.id === textbookId ? { ...t, llm_enabled: enabled } : t));
      message.success('已更新');
    } catch (e: any) { message.error(e.message || '操作失败'); }
  };

  return (
    <StatusWrapper loading={loading} error={error} empty={false} onRetry={loadAll}>
      {/* LLM 配置 */}
      <Card
        title={<><RobotOutlined /> LLM 配置</>}
        style={{ marginBottom: 16 }}
        extra={
          <Space>
            <span style={{ fontSize: 13, color: '#888' }}>全局开关</span>
            <Switch
              checked={llmConfig?.llm_enabled || false}
              loading={toggling}
              onChange={toggleGlobalLLM}
              checkedChildren="开"
              unCheckedChildren="关"
            />
          </Space>
        }
      >
        <Descriptions column={2} size="small">
          <Descriptions.Item label="模型">{llmConfig?.model_name || '-'}</Descriptions.Item>
          <Descriptions.Item label="API Key">{llmConfig?.api_key_masked || '-'}</Descriptions.Item>
          <Descriptions.Item label="Max Tokens">{llmConfig?.max_tokens || '-'}</Descriptions.Item>
          <Descriptions.Item label="Temperature">{llmConfig?.temperature ?? '-'}</Descriptions.Item>
        </Descriptions>

        <div style={{ marginTop: 16, paddingTop: 16, borderTop: '1px solid #f0f0f0' }}>
          <Space size="large">
            <Button icon={<SettingOutlined />} onClick={async () => {
              try {
                const res = await llmApi.getCoursesStatus();
                setCourseLLMList(res?.courses || []);
                setCoursesModalOpen(true);
              } catch {}
            }}>
              课程 LLM 管理 ({courseLLMList.length})
            </Button>
            <Button icon={<SettingOutlined />} onClick={async () => {
              try {
                const res = await llmApi.getTextbooksStatus();
                setTextbookLLMList(res?.textbooks || []);
                setTextbooksModalOpen(true);
              } catch {}
            }}>
              教材 LLM 管理 ({textbookLLMList.length})
            </Button>
          </Space>
        </div>
      </Card>

      {/* 课程 LLM 弹窗 */}
      <Modal title="课程 LLM 开关管理" open={coursesModalOpen}
        onCancel={() => setCoursesModalOpen(false)} footer={null} width={600}>
        <Table
          dataSource={courseLLMList}
          rowKey="id"
          size="small"
          pagination={false}
          columns={[
            { title: 'ID', dataIndex: 'id', width: 60 },
            { title: '名称', dataIndex: 'name' },
            { title: 'LLM', dataIndex: 'llm_enabled', width: 80,
              render: (v: boolean, r: any) => (
                <Switch size="small" checked={v} onChange={enabled => toggleCourseLLM(r.id, enabled)} />
              )
            },
          ]}
        />
      </Modal>

      {/* 教材 LLM 弹窗 */}
      <Modal title="教材 LLM 开关管理" open={textbooksModalOpen}
        onCancel={() => setTextbooksModalOpen(false)} footer={null} width={600}>
        <Table
          dataSource={textbookLLMList}
          rowKey="id"
          size="small"
          pagination={false}
          columns={[
            { title: 'ID', dataIndex: 'id', width: 60 },
            { title: '名称', dataIndex: 'name' },
            { title: 'LLM', dataIndex: 'llm_enabled', width: 80,
              render: (v: boolean, r: any) => (
                <Switch size="small" checked={v} onChange={enabled => toggleTextbookLLM(r.id, enabled)} />
              )
            },
          ]}
        />
      </Modal>

      {/* 系统状态 */}
      <Card title={<><CheckCircleOutlined /> 系统状态</>}>
        <Descriptions column={3} size="small">
          <Descriptions.Item label="数据库">PostgreSQL</Descriptions.Item>
          <Descriptions.Item label="后端版本">V7.1</Descriptions.Item>
          <Descriptions.Item label="前端版本">V7.1</Descriptions.Item>
          <Descriptions.Item label="认证模式">JWT (HS512)</Descriptions.Item>
          <Descriptions.Item label="API 前缀">/api/v1</Descriptions.Item>
          <Descriptions.Item label="环境">生产模式</Descriptions.Item>
          <Descriptions.Item label="LLM 引擎">
            <Tag color={llmConfig?.llm_enabled ? 'green' : 'default'}>
              {llmConfig?.llm_enabled ? `已启用 (${llmConfig?.model_name || '-'})` : '已关闭'}
            </Tag>
          </Descriptions.Item>
          <Descriptions.Item label="模型安全">
            <Tag color="green">仅 flash 模型</Tag>
          </Descriptions.Item>
          <Descriptions.Item label="API Key">
            <Tag color="blue">已加密存储</Tag>
          </Descriptions.Item>
        </Descriptions>
      </Card>
    </StatusWrapper>
  );
}