import sqlite3


BANCO = "memoria.db"


def conectar():
    return sqlite3.connect(BANCO)


def criar_banco():

    with conectar() as conn:

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS mensagens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversa_id TEXT NOT NULL,
                role TEXT NOT NULL,
                conteudo TEXT NOT NULL,
                criado_em DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """
        )


def salvar_mensagem(
    conversa_id: str,
    role: str,
    conteudo: str,
):

    with conectar() as conn:

        conn.execute(
            """
            INSERT INTO mensagens (
                conversa_id,
                role,
                conteudo
            )
            VALUES (?, ?, ?)
            """,
            (
                conversa_id,
                role,
                conteudo,
            ),
        )


def buscar_historico(
    conversa_id: str,
    limite: int = 10,
):

    with conectar() as conn:

        cursor = conn.execute(
            """
            SELECT role, conteudo
            FROM mensagens
            WHERE conversa_id = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (
                conversa_id,
                limite,
            ),
        )

        mensagens = cursor.fetchall()

    mensagens.reverse()

    return [
        {
            "role": role,
            "content": conteudo,
        }
        for role, conteudo in mensagens
    ]