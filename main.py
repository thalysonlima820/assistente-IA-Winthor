import re
import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from datetime import date, timedelta, datetime


from venda.venda import router as Venda
from estoque.estoque import router as Estoque
from entrada_saida.entrada_saida import router as Entradasaida
from limite.limite import router as Limite
from sql.sql import router as Sql


from memoria import (
    criar_banco,
    buscar_historico,
    salvar_mensagem,
)

from claude_service import perguntar_claude
from omniroute_service import perguntar_omniroute


app = FastAPI(
    title="Assistente IA WinThor"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(Venda)
app.include_router(Estoque)
app.include_router(Entradasaida)
app.include_router(Limite)
app.include_router(Sql)

def formatar_data(data_obj):
    meses = {
        1: "JAN",
        2: "FEB",
        3: "MAR",
        4: "APR",
        5: "MAY",
        6: "JUN",
        7: "JUL",
        8: "AUG",
        9: "SEP",
        10: "OCT",
        11: "NOV",
        12: "DEC",
    }

    return f"{data_obj.day:02d}-{meses[data_obj.month]}-{data_obj.year}"



# Cria o SQLite caso ainda não exista
criar_banco()


# =========================================================
# CLAUDE DIRETO
# =========================================================

@app.get("/pergunta")
async def perguntar(
    texto: str,
    conversa_id: str = "padrao",
):

    historico = buscar_historico(
        conversa_id,
        limite=10,
    )

    resposta = await perguntar_claude(
        pergunta=texto,
        historico=historico,
    )

    salvar_mensagem(
        conversa_id=conversa_id,
        role="user",
        conteudo=texto,
    )

    salvar_mensagem(
        conversa_id=conversa_id,
        role="assistant",
        conteudo=resposta,
    )

    return {
        "provider": "claude",
        "resposta": resposta,
    }


# =========================================================
# OMNIROUTE
# =========================================================

@app.get("/pergunta-omni")
async def perguntar_omni(
    texto: str,
    conversa_id: str = "padrao-omni",
):
    
    historico = buscar_historico(
        conversa_id,
        limite=50,
    )

    resposta = await perguntar_omniroute(
        pergunta=texto,
        historico=historico,
    )

    salvar_mensagem(
        conversa_id=conversa_id,
        role="user",
        conteudo=texto,
    )

    salvar_mensagem(
        conversa_id=conversa_id,
        role="assistant",
        conteudo=resposta,
    )

    return {
        "provider": "omniroute",
        "resposta": resposta,
    }