CREATE TABLE IF NOT EXISTS vault_meta (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL,
    n INTEGER NOT NULL,
    k INTEGER NOT NULL,
    password_salt BLOB NOT NULL,
    password_verifier BLOB NOT NULL,
    status TEXT NOT NULL DEFAULT 'locked'
);

CREATE TABLE IF NOT EXISTS shares (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    vault_id INTEGER NOT NULL,
    share_index INTEGER NOT NULL,
    share_payload BLOB NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (vault_id) REFERENCES vault_meta(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS secrets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    vault_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    login TEXT,
    url TEXT,
    note TEXT,
    encrypted_secret BLOB NOT NULL,
    encrypted_data_key BLOB NOT NULL, -- 🔥 новое поле
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (vault_id) REFERENCES vault_meta(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    vault_id INTEGER,
    event_type TEXT NOT NULL,
    details TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (vault_id) REFERENCES vault_meta(id) ON DELETE SET NULL
);