-- app/storage/schema.sql - ИСПРАВЛЕННАЯ ВЕРСИЯ (с проверкой существования колонок)

-- Таблица пользователей
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash BLOB NOT NULL,
    created_at TEXT NOT NULL
);

-- Таблица хранилищ
CREATE TABLE IF NOT EXISTS vault_meta (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    created_at TEXT NOT NULL,
    n INTEGER NOT NULL,
    k INTEGER NOT NULL,
    password_salt BLOB NOT NULL,
    password_verifier BLOB NOT NULL,
    status TEXT DEFAULT 'locked',
    failed_attempts INTEGER DEFAULT 0,
    last_failed_attempt TEXT
);

-- Таблица долей
CREATE TABLE IF NOT EXISTS shares (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    vault_id INTEGER NOT NULL,
    share_index INTEGER NOT NULL,
    share_payload BLOB NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE(vault_id, share_index),
    FOREIGN KEY (vault_id) REFERENCES vault_meta(id) ON DELETE CASCADE
);

-- Таблица секретов
CREATE TABLE IF NOT EXISTS secrets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    vault_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    login TEXT,
    url TEXT,
    note TEXT,
    encrypted_secret BLOB NOT NULL,
    encrypted_data_key BLOB NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (vault_id) REFERENCES vault_meta(id) ON DELETE CASCADE
);

-- Добавляем колонку integrity_hash ТОЛЬКО если её нет
PRAGMA foreign_keys=off;

-- Проверяем и добавляем недостающие колонки
CREATE TABLE IF NOT EXISTS secrets_temp (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    vault_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    login TEXT,
    url TEXT,
    note TEXT,
    encrypted_secret BLOB NOT NULL,
    encrypted_data_key BLOB NOT NULL,
    integrity_hash TEXT,  -- новая колонка
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (vault_id) REFERENCES vault_meta(id) ON DELETE CASCADE
);

-- Копируем данные из старой таблицы
INSERT OR IGNORE INTO secrets_temp
SELECT id, vault_id, name, login, url, note, encrypted_secret, encrypted_data_key,
       NULL, created_at, updated_at
FROM secrets;

-- Удаляем старую и переименовываем новую
DROP TABLE secrets;
ALTER TABLE secrets_temp RENAME TO secrets;

-- Таблица прав доступа
CREATE TABLE IF NOT EXISTS user_vault_access (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    vault_id INTEGER NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('owner', 'admin', 'user', 'viewer')),
    granted_at TEXT NOT NULL,
    UNIQUE(user_id, vault_id),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (vault_id) REFERENCES vault_meta(id) ON DELETE CASCADE
);

-- Таблица аудита
CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    vault_id INTEGER,
    event_type TEXT NOT NULL,
    details TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (vault_id) REFERENCES vault_meta(id) ON DELETE SET NULL
);

-- Таблица версий секретов
CREATE TABLE IF NOT EXISTS secret_versions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    secret_id INTEGER NOT NULL,
    version INTEGER NOT NULL,
    encrypted_secret BLOB NOT NULL,
    encrypted_data_key BLOB NOT NULL,
    login TEXT,
    url TEXT,
    note TEXT,
    created_at TEXT NOT NULL,
    UNIQUE(secret_id, version),
    FOREIGN KEY (secret_id) REFERENCES secrets(id) ON DELETE CASCADE
);

-- Таблица для мастер-паролей восстановления
CREATE TABLE IF NOT EXISTS recovery_keys (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    vault_id INTEGER NOT NULL,
    encrypted_master_key BLOB NOT NULL,
    recovery_key_hint TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (vault_id) REFERENCES vault_meta(id) ON DELETE CASCADE
);

-- Таблица для истории восстановлений
CREATE TABLE IF NOT EXISTS recovery_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    vault_id INTEGER NOT NULL,
    recovery_time TEXT NOT NULL,
    success BOOLEAN NOT NULL,
    method TEXT NOT NULL,
    details TEXT,
    FOREIGN KEY (vault_id) REFERENCES vault_meta(id) ON DELETE CASCADE
);

-- Таблица для логов проверки целостности
CREATE TABLE IF NOT EXISTS integrity_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    vault_id INTEGER NOT NULL,
    check_time TEXT NOT NULL,
    status TEXT NOT NULL,
    issues_count INTEGER DEFAULT 0,
    details TEXT,
    FOREIGN KEY (vault_id) REFERENCES vault_meta(id) ON DELETE CASCADE
);

PRAGMA foreign_keys=on;

-- Индексы для производительности
CREATE INDEX IF NOT EXISTS idx_user_vault_access_user ON user_vault_access(user_id);
CREATE INDEX IF NOT EXISTS idx_user_vault_access_vault ON user_vault_access(vault_id);
CREATE INDEX IF NOT EXISTS idx_audit_vault ON audit_log(vault_id);
CREATE INDEX IF NOT EXISTS idx_audit_time ON audit_log(created_at);
CREATE INDEX IF NOT EXISTS idx_secret_versions_secret ON secret_versions(secret_id);
CREATE INDEX IF NOT EXISTS idx_integrity_log_vault ON integrity_log(vault_id);
CREATE INDEX IF NOT EXISTS idx_integrity_log_time ON integrity_log(check_time);
CREATE INDEX IF NOT EXISTS idx_recovery_keys_vault ON recovery_keys(vault_id);
CREATE INDEX IF NOT EXISTS idx_recovery_log_vault ON recovery_log(vault_id);