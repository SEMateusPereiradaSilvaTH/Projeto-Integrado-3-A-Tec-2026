PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS usuarios (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    nome       TEXT NOT NULL UNIQUE,
    email      TEXT,
    senha      TEXT NOT NULL,
    criado_em  TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_usuarios_email
    ON usuarios (email) WHERE email IS NOT NULL;

CREATE TABLE IF NOT EXISTS titulos (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    tmdb_id     INTEGER NOT NULL,
    tipo        TEXT NOT NULL CHECK (tipo IN ('filme', 'serie')),
    titulo      TEXT NOT NULL,
    poster_path TEXT,
    ano         TEXT,
    nota_tmdb   REAL,
    UNIQUE (tmdb_id, tipo)
);

CREATE TABLE IF NOT EXISTS favoritos (
    usuario_id INTEGER NOT NULL,
    titulo_id  INTEGER NOT NULL,
    criado_em  TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (usuario_id, titulo_id),
    FOREIGN KEY (usuario_id) REFERENCES usuarios (id) ON DELETE CASCADE,
    FOREIGN KEY (titulo_id)  REFERENCES titulos (id)  ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS lista_assistir (
    usuario_id    INTEGER NOT NULL,
    titulo_id     INTEGER NOT NULL,
    status        TEXT NOT NULL
                  CHECK (status IN ('quero_ver', 'assistindo', 'assistido')),
    atualizado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (usuario_id, titulo_id),
    FOREIGN KEY (usuario_id) REFERENCES usuarios (id) ON DELETE CASCADE,
    FOREIGN KEY (titulo_id)  REFERENCES titulos (id)  ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS avaliacoes (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id    INTEGER NOT NULL,
    titulo_id     INTEGER NOT NULL,
    nota          INTEGER NOT NULL CHECK (nota BETWEEN 1 AND 5),
    comentario    TEXT,
    criado_em     TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    atualizado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (usuario_id, titulo_id),
    FOREIGN KEY (usuario_id) REFERENCES usuarios (id) ON DELETE CASCADE,
    FOREIGN KEY (titulo_id)  REFERENCES titulos (id)  ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS historico_buscas (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id INTEGER,
    termo      TEXT NOT NULL,
    criado_em  TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (usuario_id) REFERENCES usuarios (id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_favoritos_titulo   ON favoritos (titulo_id);
CREATE INDEX IF NOT EXISTS idx_lista_status       ON lista_assistir (usuario_id, status);
CREATE INDEX IF NOT EXISTS idx_avaliacoes_titulo  ON avaliacoes (titulo_id);
CREATE INDEX IF NOT EXISTS idx_buscas_usuario     ON historico_buscas (usuario_id, criado_em);
