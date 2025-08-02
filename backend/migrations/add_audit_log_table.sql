-- Миграция для добавления таблицы audit_logs
-- Выполнить эту миграцию если база данных уже существует

-- Создание таблицы для логирования действий пользователей
CREATE TABLE IF NOT EXISTS audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(50) NOT NULL,
    resource_id INTEGER,
    ip_address VARCHAR(45),
    user_agent TEXT,
    details TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (id)
);

-- Создание индексов для оптимизации запросов
CREATE INDEX IF NOT EXISTS idx_audit_logs_user_id ON audit_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_action ON audit_logs(action);
CREATE INDEX IF NOT EXISTS idx_audit_logs_resource_type ON audit_logs(resource_type);
CREATE INDEX IF NOT EXISTS idx_audit_logs_resource_id ON audit_logs(resource_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_timestamp ON audit_logs(timestamp);
CREATE INDEX IF NOT EXISTS idx_audit_logs_ip_address ON audit_logs(ip_address);

-- Создание составных индексов для часто используемых запросов
CREATE INDEX IF NOT EXISTS idx_audit_logs_user_timestamp ON audit_logs(user_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_audit_logs_resource ON audit_logs(resource_type, resource_id, timestamp DESC);

-- Добавление поля is_admin в таблицу users если его еще нет
ALTER TABLE users ADD COLUMN is_admin BOOLEAN DEFAULT FALSE;

-- Обновление существующих записей (опционально)
-- UPDATE users SET is_admin = FALSE WHERE is_admin IS NULL;

-- Создание триггера для автоматического логирования некоторых операций (SQLite)
-- Этот триггер будет автоматически логировать создание новых пользователей

CREATE TRIGGER IF NOT EXISTS trigger_log_user_creation
    AFTER INSERT ON users
    FOR EACH ROW
BEGIN
    INSERT INTO audit_logs (user_id, action, resource_type, resource_id, details, timestamp)
    VALUES (
        NEW.id,
        'USER_CREATE',
        'USER',
        NEW.id,
        json_object('email', NEW.email, 'trigger', 'auto'),
        CURRENT_TIMESTAMP
    );
END;

-- Триггер для логирования создания коллекций
CREATE TRIGGER IF NOT EXISTS trigger_log_collection_creation
    AFTER INSERT ON collections
    FOR EACH ROW
BEGIN
    INSERT INTO audit_logs (user_id, action, resource_type, resource_id, details, timestamp)
    VALUES (
        NEW.user_id,
        'COLLECTION_CREATE',
        'COLLECTION',
        NEW.id,
        json_object('name', NEW.name, 'is_public', NEW.is_public, 'trigger', 'auto'),
        CURRENT_TIMESTAMP
    );
END;

-- Триггер для логирования удаления коллекций
CREATE TRIGGER IF NOT EXISTS trigger_log_collection_deletion
    BEFORE DELETE ON collections
    FOR EACH ROW
BEGIN
    INSERT INTO audit_logs (user_id, action, resource_type, resource_id, details, timestamp)
    VALUES (
        OLD.user_id,
        'COLLECTION_DELETE',
        'COLLECTION',
        OLD.id,
        json_object('name', OLD.name, 'was_public', OLD.is_public, 'trigger', 'auto'),
        CURRENT_TIMESTAMP
    );
END;

-- Проверка что миграция прошла успешно
SELECT 'Audit logs table created successfully' as result 
WHERE EXISTS (
    SELECT 1 FROM sqlite_master 
    WHERE type='table' AND name='audit_logs'
);

-- Вставка записи о выполнении миграции
INSERT INTO audit_logs (action, resource_type, details, timestamp)
VALUES (
    'DATABASE_MIGRATION',
    'SYSTEM',
    json_object('migration', 'add_audit_log_table', 'version', '1.0'),
    CURRENT_TIMESTAMP
);