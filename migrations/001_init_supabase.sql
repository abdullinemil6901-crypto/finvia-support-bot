-- ============================================
-- Support Bot — Миграция на Supabase
-- Дата: 2026-06-12
-- ============================================

-- Включаем UUID расширение для генерации ID
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================
-- ТАБЛИЦА: tickets (тикеты)
-- ============================================
CREATE TABLE IF NOT EXISTS tickets (
    id BIGSERIAL PRIMARY KEY,
    trader_id BIGINT NOT NULL,
    trader_username TEXT,
    trader_name TEXT,
    label TEXT NOT NULL,
    order_id TEXT,
    status TEXT DEFAULT 'open' CHECK (status IN ('open', 'in_progress', 'closed')),
    taken_by TEXT,
    taken_by_id BIGINT,
    taken_at TIMESTAMPTZ,
    closed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    trader_chat_id BIGINT,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Индексы для часто используемых запросов
CREATE INDEX IF NOT EXISTS idx_tickets_status ON tickets(status);
CREATE INDEX IF NOT EXISTS idx_tickets_status_created ON tickets(status, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_tickets_taken_by ON tickets(taken_by);
CREATE INDEX IF NOT EXISTS idx_tickets_label ON tickets(label);
CREATE INDEX IF NOT EXISTS idx_tickets_created_at ON tickets(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_tickets_trader_id ON tickets(trader_id);

-- Автообновление updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER tickets_updated_at
    BEFORE UPDATE ON tickets
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================
-- ТАБЛИЦА: supports (саппорты)
-- ============================================
CREATE TABLE IF NOT EXISTS supports (
    id BIGSERIAL PRIMARY KEY,
    tg_id BIGINT UNIQUE NOT NULL,
    username TEXT,
    full_name TEXT,
    added_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- ТАБЛИЦА: schedules (расписания дежурных)
-- ============================================
CREATE TABLE IF NOT EXISTS schedules (
    id BIGSERIAL PRIMARY KEY,
    support_id BIGINT REFERENCES supports(id) ON DELETE CASCADE,
    day_of_week INTEGER NOT NULL CHECK (day_of_week BETWEEN 0 AND 6),
    hour_start INTEGER NOT NULL CHECK (hour_start BETWEEN 0 AND 23),
    hour_end INTEGER NOT NULL CHECK (hour_end BETWEEN 0 AND 23),
    shift_type TEXT DEFAULT 'day' CHECK (shift_type IN ('day', 'night')),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- ТАБЛИЦА: duty_schedule (упрощённое расписание)
-- ============================================
CREATE TABLE IF NOT EXISTS duty_schedule (
    id BIGSERIAL PRIMARY KEY,
    date DATE NOT NULL,
    shift_type TEXT NOT NULL CHECK (shift_type IN ('day', 'night')),
    names TEXT[] NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(date, shift_type)
);

CREATE INDEX IF NOT EXISTS idx_duty_schedule_date ON duty_schedule(date);

-- ============================================
-- ТАБЛИЦА: events (события для статистики)
-- ============================================
CREATE TABLE IF NOT EXISTS events (
    id BIGSERIAL PRIMARY KEY,
    event_type TEXT NOT NULL,
    user_id BIGINT,
    username TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Индекс для группировки по типу и дате
CREATE INDEX IF NOT EXISTS idx_events_type_created ON events(event_type, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_events_created_at ON events(created_at DESC);

-- ============================================
-- ПРЕДСТАВЛЕНИЯ (Views) для аналитики
-- ============================================

-- Статистика по типам обращений за сегодня
CREATE OR REPLACE VIEW v_today_stats AS
SELECT
    event_type,
    COUNT(*) as count
FROM events
WHERE DATE(created_at AT TIME ZONE 'Europe/Moscow') = CURRENT_DATE AT TIME ZONE 'Europe/Moscow'
GROUP BY event_type;

-- Статистика по саппортам
CREATE OR REPLACE VIEW v_support_stats AS
SELECT
    taken_by as username,
    COUNT(*) FILTER (WHERE status = 'closed') as closed_count,
    COUNT(*) FILTER (WHERE status = 'in_progress') as in_progress_count,
    COUNT(*) as total_count,
    AVG(
        CASE
            WHEN status = 'closed' AND taken_at IS NOT NULL AND closed_at IS NOT NULL
            THEN EXTRACT(EPOCH FROM (closed_at - taken_at))
        END
    ) as avg_seconds
FROM tickets
WHERE taken_by IS NOT NULL
GROUP BY taken_by;

-- ============================================
-- RLS (Row Level Security)
-- ============================================

-- Для публичного бота RLS отключаем (бот пишет от имени сервиса)
-- Если нужен веб-интерфейс — включить и настроить политики

ALTER TABLE tickets ENABLE ROW LEVEL SECURITY;
ALTER TABLE supports ENABLE ROW LEVEL SECURITY;
ALTER TABLE schedules ENABLE ROW LEVEL SECURITY;
ALTER TABLE duty_schedule ENABLE ROW LEVEL SECURITY;
ALTER TABLE events ENABLE ROW LEVEL SECURITY;

-- Политики для сервисного аккаунта (бот работает через service_role key)
CREATE POLICY "Service role full access tickets" ON tickets
    FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY "Service role full access supports" ON supports
    FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY "Service role full access schedules" ON schedules
    FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY "Service role full access duty_schedule" ON duty_schedule
    FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY "Service role full access events" ON events
    FOR ALL USING (auth.role() = 'service_role');

-- Анонимный доступ для чтения (дашборд)
CREATE POLICY "Allow anon read tickets" ON tickets
    FOR SELECT USING (true);

CREATE POLICY "Allow anon read events" ON events
    FOR SELECT USING (true);

CREATE POLICY "Allow anon read duty_schedule" ON duty_schedule
    FOR SELECT USING (true);

-- ============================================
-- КОММЕНТАРИИ К ТАБЛИЦАМ
-- ============================================
COMMENT ON TABLE tickets IS 'Тикеты от трейдеров в саппорт';
COMMENT ON TABLE supports IS 'Список саппортов';
COMMENT ON TABLE schedules IS 'График дежурств саппортов';
COMMENT ON TABLE duty_schedule IS 'Упрощённое расписание дежурных на день';
COMMENT ON TABLE events IS 'События для статистики (обращения)';
