-- LLM Config Migration
-- 1. System settings table (encrypted key-value store)
CREATE TABLE IF NOT EXISTS system_settings (
    key VARCHAR(100) PRIMARY KEY,
    value TEXT NOT NULL DEFAULT '',
    is_encrypted BOOLEAN DEFAULT FALSE,
    description VARCHAR(500) DEFAULT '',
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 2. Per-course LLM toggle
ALTER TABLE courses ADD COLUMN IF NOT EXISTS llm_enabled BOOLEAN DEFAULT FALSE;

-- 3. Per-textbook LLM toggle
ALTER TABLE textbooks ADD COLUMN IF NOT EXISTS llm_enabled BOOLEAN DEFAULT FALSE;

-- 4. Seed default config (all OFF)
INSERT INTO system_settings (key, value, is_encrypted, description) VALUES
('llm_enabled', 'false', false, '全局LLM功能开关'),
('llm_api_key', '', true, 'LLM API密钥（Fernet加密）'),
('llm_base_url', 'https://api.deepseek.com/v1/chat/completions', false, 'LLM API地址'),
('llm_model', 'deepseek-chat', false, 'LLM模型名称（仅限flash/标准，禁止pro）'),
('llm_max_tokens', '4096', false, 'LLM最大token数'),
('llm_temperature', '0.2', false, 'LLM温度参数')
ON CONFLICT (key) DO NOTHING;