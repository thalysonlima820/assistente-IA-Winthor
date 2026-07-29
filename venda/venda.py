from fastapi import APIRouter, HTTPException
from database import conectar
from pathlib import Path
from typing import Literal

router = APIRouter(
    prefix="/venda",
    tags=["Vendas"],
)


@router.get("/{datainicio}/{datafim}")
async def venda_produto(datainicio: str, datafim: str):

    conexao = conectar()
    cursor = conexao.cursor()

    try:
        caminho_sql = Path(__file__).parent / "sql" / "venda.sql"

        with open(caminho_sql, "r", encoding="utf-8") as arquivo:
            sql = arquivo.read()

        cursor.execute(
            sql,
            {
                "datainicio": datainicio,
                "datafim": datafim,
            },
        )

        colunas = [coluna[0] for coluna in cursor.description]

        dados = [dict(zip(colunas, linha)) for linha in cursor.fetchall()]

        if not dados:
            raise HTTPException(status_code=404, detail="Nenhuma venda encontrada")

        return dados

    finally:
        cursor.close()
        conexao.close()


@router.get("/{datainicio}/{datafim}/{top}/{tipo}")
async def venda_produto(
    datainicio: str,
    datafim: str,
    top: int,
    tipo: Literal["MAIS", "MENOS"],
):
    conexao = conectar()
    cursor = conexao.cursor()

    try:
        caminho_sql = Path(__file__).parent / "sql" / "vendaTop.sql"

        with open(caminho_sql, "r", encoding="utf-8") as arquivo:
            sql = arquivo.read()

        cursor.execute(
            sql,
            {
                "datainicio": datainicio,
                "datafim": datafim,
                "top": top,
                "tipo": tipo,
            },
        )

        colunas = [coluna[0] for coluna in cursor.description]

        dados = [dict(zip(colunas, linha)) for linha in cursor.fetchall()]

        if not dados:
            raise HTTPException(
                status_code=404,
                detail="Nenhuma venda encontrada",
            )

        return dados

    finally:
        cursor.close()
        conexao.close()
