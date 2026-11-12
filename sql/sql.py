
from fastapi import APIRouter, HTTPException
from database import conectar
from pydantic import BaseModel
from datetime import datetime, date
from decimal import Decimal
import oracledb
import re

router = APIRouter(
    prefix="/sql",
    tags=["sql"],
)

class SQLRequest(BaseModel):
    sql: str


def converter_valor(valor):
    if valor is None:
        return None

    if isinstance(valor, oracledb.LOB):
        conteudo = valor.read()

        if isinstance(conteudo, bytes):
            return f"[BLOB: {len(conteudo)} bytes]"

        return conteudo

    if isinstance(valor, (datetime, date)):
        return valor.isoformat()

    if isinstance(valor, Decimal):
        return float(valor)

    if isinstance(valor, bytes):
        return f"[BINARIO: {len(valor)} bytes]"

    return valor


@router.post("/")
def executar_sql(dados: SQLRequest):

    sql = dados.sql.strip()

    if not re.match(r"^SELECT\b", sql, re.IGNORECASE):
        raise HTTPException(
            status_code=400,
            detail="Apenas consultas SELECT são permitidas"
        )

    conexao = None
    cursor = None

    try:
        conexao = conectar()
        cursor = conexao.cursor()

        cursor.execute(sql)

        colunas = [coluna[0] for coluna in cursor.description]

        resultados = []

        for linha in cursor.fetchmany(100):
            registro = {
                coluna: converter_valor(valor)
                for coluna, valor in zip(colunas, linha)
            }
            resultados.append(registro)

        return {
            "mensagem": "certo",
            "sql_recebido": sql,
            "total": len(resultados),
            "resposta": resultados
        }

    except oracledb.Error:
        raise HTTPException(
            status_code=500,
            detail="Erro ao consultar o banco Oracle"
        )

    finally:
        if cursor:
            cursor.close()

        if conexao:
            conexao.close()
