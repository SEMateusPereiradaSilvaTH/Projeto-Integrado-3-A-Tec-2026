import hashlib
import hmac
import os
import sqlite3
from contextlib import contextmanager

from werkzeug.security import check_password_hash, generate_password_hash

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.getenv("DATABASE_PATH", os.path.join(BASE_DIR, "usuarios.db"))
SCHEMA_PATH = os.path.join(BASE_DIR, "schema.sql")

TIPOS_VALIDOS = ("filme", "serie")
STATUS_VALIDOS = ("quero_ver", "assistindo", "assistido")


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _migrar_usuarios(conn):
    colunas = {r["name"] for r in conn.execute("PRAGMA table_info(usuarios)")}
    if not colunas:
        return
    if "email" not in colunas:
        conn.execute("ALTER TABLE usuarios ADD COLUMN email TEXT")
    if "criado_em" not in colunas:
        conn.execute("ALTER TABLE usuarios ADD COLUMN criado_em TEXT")
        conn.execute("UPDATE usuarios SET criado_em = CURRENT_TIMESTAMP "
                     "WHERE criado_em IS NULL")


def init_db():
    with get_conn() as conn:
        _migrar_usuarios(conn)
        with open(SCHEMA_PATH, encoding="utf-8") as f:
            conn.executescript(f.read())


def _eh_sha256(valor):
    return len(valor) == 64 and all(c in "0123456789abcdef" for c in valor.lower())


def criar_usuario(nome, email, senha):
    try:
        with get_conn() as conn:
            conn.execute(
                "INSERT INTO usuarios (nome, email, senha, criado_em) "
                "VALUES (?, ?, ?, CURRENT_TIMESTAMP)",
                (nome, email.lower(), generate_password_hash(senha)),
            )
        return True, None
    except sqlite3.IntegrityError as e:
        if "email" in str(e):
            return False, "Esse email já está cadastrado."
        return False, "Esse nome de usuário já existe."


def verificar_login(nome, senha):
    with get_conn() as conn:
        u = conn.execute("SELECT * FROM usuarios WHERE nome = ?", (nome,)).fetchone()
        if u is None:
            return None

        guardado = u["senha"]
        if _eh_sha256(guardado):
            calculado = hashlib.sha256(senha.encode()).hexdigest()
            if not hmac.compare_digest(calculado, guardado):
                return None
            conn.execute("UPDATE usuarios SET senha = ? WHERE id = ?",
                         (generate_password_hash(senha), u["id"]))
            return dict(u)

        return dict(u) if check_password_hash(guardado, senha) else None


def obter_titulo_id(tmdb_id, tipo):
    with get_conn() as conn:
        r = conn.execute("SELECT id FROM titulos WHERE tmdb_id = ? AND tipo = ?",
                         (tmdb_id, tipo)).fetchone()
        return r["id"] if r else None


def salvar_titulo(tmdb_id, tipo, titulo, poster_path, ano, nota):
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO titulos (tmdb_id, tipo, titulo, poster_path, ano, nota_tmdb)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT (tmdb_id, tipo) DO UPDATE SET
                titulo = excluded.titulo,
                poster_path = excluded.poster_path,
                ano = excluded.ano,
                nota_tmdb = excluded.nota_tmdb
            """,
            (tmdb_id, tipo, titulo, poster_path, ano, nota),
        )
        return conn.execute("SELECT id FROM titulos WHERE tmdb_id = ? AND tipo = ?",
                            (tmdb_id, tipo)).fetchone()["id"]


def alternar_favorito(usuario_id, titulo_id):
    with get_conn() as conn:
        apagou = conn.execute(
            "DELETE FROM favoritos WHERE usuario_id = ? AND titulo_id = ?",
            (usuario_id, titulo_id)).rowcount
        if apagou:
            return False
        conn.execute("INSERT INTO favoritos (usuario_id, titulo_id) VALUES (?, ?)",
                     (usuario_id, titulo_id))
        return True


def eh_favorito(usuario_id, tmdb_id, tipo):
    with get_conn() as conn:
        r = conn.execute(
            """SELECT 1 FROM favoritos f JOIN titulos t ON t.id = f.titulo_id
               WHERE f.usuario_id = ? AND t.tmdb_id = ? AND t.tipo = ?""",
            (usuario_id, tmdb_id, tipo)).fetchone()
        return r is not None


def listar_favoritos(usuario_id):
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT t.* FROM favoritos f JOIN titulos t ON t.id = f.titulo_id
               WHERE f.usuario_id = ? ORDER BY f.criado_em DESC, t.id DESC""",
            (usuario_id,)).fetchall()
        return [dict(r) for r in rows]


def definir_status(usuario_id, titulo_id, status):
    if status not in STATUS_VALIDOS:
        raise ValueError("status inválido")
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO lista_assistir (usuario_id, titulo_id, status)
            VALUES (?, ?, ?)
            ON CONFLICT (usuario_id, titulo_id) DO UPDATE SET
                status = excluded.status,
                atualizado_em = CURRENT_TIMESTAMP
            """,
            (usuario_id, titulo_id, status),
        )


def remover_status(usuario_id, titulo_id):
    with get_conn() as conn:
        conn.execute("DELETE FROM lista_assistir WHERE usuario_id = ? AND titulo_id = ?",
                     (usuario_id, titulo_id))


def obter_status(usuario_id, tmdb_id, tipo):
    with get_conn() as conn:
        r = conn.execute(
            """SELECT l.status FROM lista_assistir l JOIN titulos t ON t.id = l.titulo_id
               WHERE l.usuario_id = ? AND t.tmdb_id = ? AND t.tipo = ?""",
            (usuario_id, tmdb_id, tipo)).fetchone()
        return r["status"] if r else None


def listar_lista(usuario_id, status=None):
    sql = """SELECT t.*, l.status FROM lista_assistir l
             JOIN titulos t ON t.id = l.titulo_id
             WHERE l.usuario_id = ?"""
    params = [usuario_id]
    if status:
        sql += " AND l.status = ?"
        params.append(status)
    sql += " ORDER BY l.atualizado_em DESC, t.id DESC"
    with get_conn() as conn:
        return [dict(r) for r in conn.execute(sql, params).fetchall()]


def salvar_avaliacao(usuario_id, titulo_id, nota, comentario):
    if not 1 <= nota <= 5:
        raise ValueError("nota deve ser de 1 a 5")
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO avaliacoes (usuario_id, titulo_id, nota, comentario)
            VALUES (?, ?, ?, ?)
            ON CONFLICT (usuario_id, titulo_id) DO UPDATE SET
                nota = excluded.nota,
                comentario = excluded.comentario,
                atualizado_em = CURRENT_TIMESTAMP
            """,
            (usuario_id, titulo_id, nota, comentario or None),
        )


def remover_avaliacao(usuario_id, titulo_id):
    with get_conn() as conn:
        conn.execute("DELETE FROM avaliacoes WHERE usuario_id = ? AND titulo_id = ?",
                     (usuario_id, titulo_id))


def obter_avaliacao_usuario(usuario_id, tmdb_id, tipo):
    with get_conn() as conn:
        r = conn.execute(
            """SELECT a.nota, a.comentario FROM avaliacoes a
               JOIN titulos t ON t.id = a.titulo_id
               WHERE a.usuario_id = ? AND t.tmdb_id = ? AND t.tipo = ?""",
            (usuario_id, tmdb_id, tipo)).fetchone()
        return dict(r) if r else None


def listar_avaliacoes(tmdb_id, tipo, limite=30):
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT u.nome, a.nota, a.comentario, a.atualizado_em
               FROM avaliacoes a
               JOIN titulos t ON t.id = a.titulo_id
               JOIN usuarios u ON u.id = a.usuario_id
               WHERE t.tmdb_id = ? AND t.tipo = ?
               ORDER BY a.atualizado_em DESC LIMIT ?""",
            (tmdb_id, tipo, limite)).fetchall()
        return [dict(r) for r in rows]


def media_avaliacoes(tmdb_id, tipo):
    with get_conn() as conn:
        r = conn.execute(
            """SELECT AVG(a.nota) AS media, COUNT(*) AS total
               FROM avaliacoes a JOIN titulos t ON t.id = a.titulo_id
               WHERE t.tmdb_id = ? AND t.tipo = ?""",
            (tmdb_id, tipo)).fetchone()
        return (r["media"], r["total"]) if r["total"] else (None, 0)


def registrar_busca(usuario_id, termo):
    with get_conn() as conn:
        conn.execute("INSERT INTO historico_buscas (usuario_id, termo) VALUES (?, ?)",
                     (usuario_id, termo))


def buscas_recentes(usuario_id, limite=10):
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT termo, MAX(id) AS ultima FROM historico_buscas
               WHERE usuario_id = ? GROUP BY termo
               ORDER BY ultima DESC LIMIT ?""",
            (usuario_id, limite)).fetchall()
        return [r["termo"] for r in rows]
