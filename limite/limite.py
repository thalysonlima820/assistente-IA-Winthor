from fastapi import APIRouter, HTTPException
from database import conectar
from pathlib import Path

router = APIRouter(
    prefix="/limite",
    tags=["Limite"],
)


@router.get("/{datainicio}/{datafim}")
async def limite_compra(datainicio: str, datafim: str):

    conexao = conectar()
    cursor = conexao.cursor()

    try:
        caminho_sql = Path(__file__).parent / "sql" / "limite.sql"

        with open(caminho_sql, "r", encoding="utf-8") as arquivo:
            sql = arquivo.read()

        cursor.execute(
            sql,
            {
                "datainicio": datainicio,
                "datafim": datafim,
            }
        )

        colunas = [coluna[0] for coluna in cursor.description]

        dados = [
            dict(zip(colunas, linha))
            for linha in cursor.fetchall()
        ]

        if not dados:
            raise HTTPException(
                status_code=404,
                detail="Nenhuma venda encontrada"
            )

        return dados

    finally:
        cursor.close()
        conexao.close()
    