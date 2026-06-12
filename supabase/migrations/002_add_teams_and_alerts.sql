-- Миграция: Добавляем поддержку 30 команд
-- Добавляем таблицу chats и поле team_name в tickets

-- ============================================
-- 1. Таблица chats — список чатов где есть бот
-- ============================================
CREATE TABLE IF NOT EXISTS chats (
    id BIGSERIAL PRIMARY KEY,
    chat_id BIGINT UNIQUE NOT NULL,           -- Telegram Chat ID
    team_name TEXT NOT NULL,                   -- "309 арс", "281 арс" и тд
    is_active BOOLEAN DEFAULT true,            -- Бот добавлен в чат?
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Индекс для быстрого поиска по chat_id
CREATE INDEX IF NOT EXISTS idx_chats_chat_id ON chats(chat_id);

-- ============================================
-- 2. Добавляем team_name и chat_id в tickets
-- ============================================
ALTER TABLE tickets
ADD COLUMN IF NOT EXISTS team_name TEXT,
ADD COLUMN IF NOT EXISTS chat_id BIGINT;

-- Индекс для группировки по команде
CREATE INDEX IF NOT EXISTS idx_tickets_team_name ON tickets(team_name);

-- ============================================
-- 3. Добавляем поле alert_sent для SLA алертов
-- ============================================
ALTER TABLE tickets
ADD COLUMN IF NOT EXISTS alert_sent BOOLEAN DEFAULT FALSE;

-- ============================================
-- 4. Добавляем поле role в supports
-- ============================================
ALTER TABLE supports
ADD COLUMN IF NOT EXISTS role TEXT DEFAULT 'support';  -- 'admin' или 'support'

-- ============================================
-- 5. Автообновление updated_at
-- ============================================
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE TRIGGER chats_updated_at
    BEFORE UPDATE ON chats
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();
