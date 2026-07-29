from fastapi import APIRouter, HTTPException
from database import conectar
from pathlib import Path

router = APIRouter(
    prefix="/entradasaida",
    tags=["Entradasaida"],
)


@router.get("/{datainicio}/{datafim}")
async def venda_produto(datainicio: str, datafim: str):

    conexao = conectar()
    cursor = conexao.cursor()

    try:
        caminho_sql = Path(__file__).parent / "sql" / "departamento.sql"

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
    
@router.get("/{datainicio}/{datafim}/{codepto}")
async def venda_produto(datainicio: str, datafim: str, codepto: int):

    conexao = conectar()
    cursor = conexao.cursor()

    try:
        caminho_sql = Path(__file__).parent / "sql" / "secao.sql"

        with open(caminho_sql, "r", encoding="utf-8") as arquivo:
            sql = arquivo.read()

        cursor.execute(
            sql,
            {
                "datainicio": datainicio,
                "datafim": datafim,
                "codepto": codepto,
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
        
@router.get("/{datainicio}/{datafim}/{codepto}/{codsec}")
async def venda_produto(datainicio: str, datafim: str, codepto: int, codsec: int):

    conexao = conectar()
    cursor = conexao.cursor()

    try:
        caminho_sql = Path(__file__).parent / "sql" / "categoria.sql"

        with open(caminho_sql, "r", encoding="utf-8") as arquivo:
            sql = arquivo.read()

        cursor.execute(
            sql,
            {
                "datainicio": datainicio,
                "datafim": datafim,
                "codepto": codepto,
                "codsec": codsec,
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
        
@router.get("/{datainicio}/{datafim}/{codepto}/{codsec}/{codcategoria}")
async def venda_produto(datainicio: str, datafim: str, codepto: int, codsec: int, codcategoria: int):

    conexao = conectar()
    cursor = conexao.cursor()

    try:
        caminho_sql = Path(__file__).parent / "sql" / "produto.sql"

        with open(caminho_sql, "r", encoding="utf-8") as arquivo:
            sql = arquivo.read()

        cursor.execute(
            sql,
            {
                "datainicio": datainicio,
                "datafim": datafim,
                "codepto": codepto,
                "codsec": codsec,
                "codcategoria": codcategoria,
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
        
