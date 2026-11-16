# Banco de Dados — TelaCheia

**SGBD:** SQLite (arquivo `usuarios.db`, criado automaticamente ao iniciar o `app.py`)
**Esquema:** `schema.sql` · **Acesso:** `database.py`

## Diagrama Entidade-Relacionamento

```mermaid
erDiagram
    USUARIOS ||--o{ FAVORITOS : possui
    USUARIOS ||--o{ LISTA_ASSISTIR : monta
    USUARIOS ||--o{ AVALIACOES : escreve
    USUARIOS |o--o{ HISTORICO_BUSCAS : realiza
    TITULOS  ||--o{ FAVORITOS : "é favoritado em"
    TITULOS  ||--o{ LISTA_ASSISTIR : "está em"
    TITULOS  ||--o{ AVALIACOES : recebe

    USUARIOS {
        int id PK
        text nome UK
        text email UK
        text senha "hash"
        text criado_em
    }
    TITULOS {
        int id PK
        int tmdb_id
        text tipo "filme|serie"
        text titulo
        text poster_path
        text ano
        real nota_tmdb
    }
    FAVORITOS {
        int usuario_id PK,FK
        int titulo_id PK,FK
        text criado_em
    }
    LISTA_ASSISTIR {
        int usuario_id PK,FK
        int titulo_id PK,FK
        text status "quero_ver|assistindo|assistido"
        text atualizado_em
    }
    AVALIACOES {
        int id PK
        int usuario_id FK
        int titulo_id FK
        int nota "1 a 5"
        text comentario
        text criado_em
        text atualizado_em
    }
    HISTORICO_BUSCAS {
        int id PK
        int usuario_id FK
        text termo
        text criado_em
    }
```

## Dicionário de dados (resumo)

| Tabela | Função | Regras principais |
|---|---|---|
| `usuarios` | Contas do site | `nome` único; `email` único; senha guardada como hash |
| `titulos` | Cache dos filmes/séries do TMDB | `(tmdb_id, tipo)` único |
| `favoritos` | Títulos favoritados | PK composta `(usuario_id, titulo_id)` |
| `lista_assistir` | Quero ver / assistindo / assistido | `status` restrito por `CHECK` |
| `avaliacoes` | Nota (1–5) + comentário | 1 avaliação por usuário/título; `CHECK (nota BETWEEN 1 AND 5)` |
| `historico_buscas` | Termos pesquisados | `usuario_id` pode ser nulo (visitante) |

## Decisões de projeto

- **Chaves estrangeiras com `ON DELETE CASCADE`:** apagar um usuário ou título remove os registros dependentes (`historico_buscas` usa `SET NULL`).
- **Segurança:** senhas com hash salgado (`werkzeug.security`); contas antigas em SHA-256 são convertidas no primeiro login; todas as consultas são parametrizadas (`?`).
- **Migração automática:** `init_db()` atualiza bancos criados pela versão anterior sem perder usuários.
- **Por que `titulos`:** as telas "Meus favoritos" e "Minha lista" são montadas só com o banco, sem chamar a API do TMDB para cada item.
