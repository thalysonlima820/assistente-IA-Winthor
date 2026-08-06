import json
import re
import os
from datetime import date

import httpx
from dotenv import load_dotenv

import json
from datetime import datetime
from pathlib import Path
from uuid import uuid4
from calendar import monthrange


MESES_NUMERO = {
    "JAN": 1,
    "FEB": 2,
    "MAR": 3,
    "APR": 4,
    "MAY": 5,
    "JUN": 6,
    "JUL": 7,
    "AUG": 8,
    "SEP": 9,
    "OCT": 10,
    "NOV": 11,
    "DEC": 12,
}


load_dotenv()


OMNIROUTE_URL = os.getenv(
    "OMNIROUTE_URL",
    "http://localhost:20128/v1",
)

OMNIROUTE_MODEL = os.getenv(
    "OMNIROUTE_MODEL",
    "auto",
)

API_BASE_URL = os.getenv(
    "API_BASE_URL",
    "http://127.0.0.1:8000",
)


def extrair_tipo_demanda(resposta: str) -> str:
    padrao = r"área\s+([^,\n.]+)"

    resultado = re.search(
        padrao,
        resposta,
        flags=re.IGNORECASE,
    )

    if resultado:
        return resultado.group(1).strip()

    return "não identificado"


def registrar_demanda(
    pergunta: str,
    tipo: str,
):
    pasta_logs = Path(__file__).parent / "logs" / "demandas"

    pasta_logs.mkdir(
        parents=True,
        exist_ok=True,
    )

    agora = datetime.now()
    id_demanda = uuid4().hex

    nome_arquivo = f"{agora.strftime('%Y-%m-%d_%H-%M-%S')}_" f"{id_demanda[:8]}.json"

    caminho_arquivo = pasta_logs / nome_arquivo

    dados = {
        "id": id_demanda,
        "data_registro": agora.isoformat(),
        "tipo": tipo,
        "pergunta": pergunta,
        "status": "PENDENTE",
    }

    with open(caminho_arquivo, "w", encoding="utf-8") as arquivo:
        json.dump(
            dados,
            arquivo,
            ensure_ascii=False,
            indent=4,
        )


def registrar_sugestao(pergunta: str):
    pasta_logs = Path(__file__).parent / "logs" / "sugestoes"

    pasta_logs.mkdir(
        parents=True,
        exist_ok=True,
    )

    agora = datetime.now()
    id_sugestao = uuid4().hex

    nome_arquivo = f"{agora.strftime('%Y-%m-%d_%H-%M-%S')}_" f"{id_sugestao[:8]}.json"

    caminho_arquivo = pasta_logs / nome_arquivo

    dados = {
        "id": id_sugestao,
        "data_registro": agora.isoformat(),
        "pergunta": pergunta,
        "status": "PENDENTE",
    }

    with open(caminho_arquivo, "w", encoding="utf-8") as arquivo:
        json.dump(
            dados,
            arquivo,
            ensure_ascii=False,
            indent=4,
        )

    print(f"Sugestão criada em: {caminho_arquivo}")

    return {
        "sucesso": True,
        "mensagem": "Sugestão registrada com sucesso.",
        "id": id_sugestao,
        "arquivo": str(caminho_arquivo),
    }


def data_atual_formatada():

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

    hoje = date.today()

    return f"{hoje.day:02d}-" f"{meses[hoje.month]}-" f"{hoje.year}"


def obter_mes_completo(data_referencia: str) -> tuple[str, str]:
    """
    Recebe uma data como 10-JUL-2026 e retorna:
    01-JUL-2026, 31-JUL-2026.
    """
    try:
        _, mes_texto, ano_texto = data_referencia.upper().split("-")

        mes = MESES_NUMERO[mes_texto]
        ano = int(ano_texto)

        ultimo_dia = monthrange(ano, mes)[1]

        data_inicio = f"01-{mes_texto}-{ano}"
        data_fim = f"{ultimo_dia:02d}-{mes_texto}-{ano}"

        return data_inicio, data_fim

    except (ValueError, KeyError) as erro:
        raise ValueError(
            "Data inválida. Use o formato DD-MON-YYYY, "
            "por exemplo 10-JUL-2026."
        ) from erro


# =========================================================
# FUNÇÃO REAL QUE CONSULTA SUA API DE VENDAS
# =========================================================


async def consultar_vendas(
    data_inicio: str,
    data_fim: str,
):

    url = f"{API_BASE_URL}/venda/" f"{data_inicio}/" f"{data_fim}"

    async with httpx.AsyncClient(timeout=300) as client:

        resposta = await client.get(url)
        resposta.raise_for_status()
        return resposta.json()


async def consultar_estoque(
    codprod: int,
):

    url = f"{API_BASE_URL}/estoque/" f"{codprod}"

    async with httpx.AsyncClient(timeout=300) as client:

        resposta = await client.get(url)
        resposta.raise_for_status()
        return resposta.json()


async def entrada_saida_departamento(
    data_inicio: str,
    data_fim: str,
    codepto: int | None = None,
    codsec: int | None = None,
    codcategoria: int | None = None,
):
    partes_url = [
        API_BASE_URL.rstrip("/"),
        "entradasaida",
        data_inicio,
        data_fim,
    ]

    if codepto is not None:
        partes_url.append(str(codepto))

    if codsec is not None:
        partes_url.append(str(codsec))

    if codcategoria is not None:
        partes_url.append(str(codcategoria))

    url = "/".join(partes_url)

    async with httpx.AsyncClient(timeout=300) as client:
        resposta = await client.get(url)
        resposta.raise_for_status()
        dados_entrada_saida = resposta.json()

    # Busca a meta apenas na consulta inicial de departamentos.
    # Nas consultas de seção, categoria e produto, a meta já estará
    # disponível no histórico da conversa da IA.
    consulta_departamentos = (
        codepto is None
        and codsec is None
        and codcategoria is None
    )

    if not consulta_departamentos:
        return dados_entrada_saida

    data_inicio_meta, data_fim_meta = obter_mes_completo(data_inicio)

    dados_vendas = await consultar_vendas(
        data_inicio=data_inicio_meta,
        data_fim=data_fim_meta,
    )

    return {
        "periodo_entrada_saida": {
            "data_inicio": data_inicio,
            "data_fim": data_fim,
        },
        "periodo_meta": {
            "data_inicio": data_inicio_meta,
            "data_fim": data_fim_meta,
        },
        "entrada_saida": dados_entrada_saida,
        "vendas_meta_mes_completo": dados_vendas,
    }
    
async def ranking_produtos_vendidos(
    data_inicio: str,
    data_fim: str,
    top: int,
    tipo: str,
):
    url = f"{API_BASE_URL}/venda/" f"{data_inicio}/" f"{data_fim}/" f"{top}/" f"{tipo}"

    async with httpx.AsyncClient(timeout=300) as client:
        resposta = await client.get(url)
        resposta.raise_for_status()
        return resposta.json()

async def limite_comprador(
    data_inicio: str,
    data_fim: str,
):

    url = f"{API_BASE_URL}/limite/" f"{data_inicio}/" f"{data_fim}"

    async with httpx.AsyncClient(timeout=300) as client:

        resposta = await client.get(url)
        resposta.raise_for_status()
        return resposta.json()


# =========================================================
# TOOLS QUE A IA PODE ESCOLHER
# =========================================================

TOOLS = [
    # =========================================================
    # TOOL 1 — VENDAS
    # =========================================================
    {
        "type": "function",
        "function": {
            "name": "consultar_vendas",
            "description": """
                          Consulta dados de vendas da empresa no WinThor dentro
                          de um período.
          
                          Use esta ferramenta quando a pergunta estiver relacionada a:
          
                          - venda
                          - faturamento
                          - custo
                          - lucro
                          - quantidade de vendas
                          - ticket médio
                          - margem
                          - meta
                          - atingimento de meta
                          - desempenho de filial
                          - desempenho de departamento
                          - comparação entre períodos
                          - ranking de filiais ou departamentos
          
                          A ferramenta retorna registros por filial e departamento.
          
                          Os registros podem conter:
          
                          - CODFILIAL
                          - DEPARTAMENTO
                          - CUSTO
                          - VENDA
                          - NUMVENDAS
                          - LUCRO
                          - TICKET_MEDIO
                          - MARGEM
                          - META
                          - PERCENTUAL_CARREGADO
          
                          =========================================================
                          INTERPRETAÇÃO DOS CAMPOS
                          =========================================================
          
                          CODFILIAL:
          
                          Identifica a filial da empresa.
          
                          DEPARTAMENTO:
          
                          Identifica o departamento da venda, como:
          
                          - ACOUGUE
                          - BAZAR
                          - BEBIDAS
                          - HORTIFRUTI
                          - LIMPEZA
                          - MATINAIS
                          - PADARIA
                          - PERFUMARIA
          
                          VENDA:
          
                          Representa o valor vendido naquele registro.
          
                          Para obter a venda total de uma filial:
          
                          - filtre os registros da filial;
                          - some VENDA de todos os departamentos dessa filial.
          
                          Para obter a venda total da empresa:
          
                          - some VENDA de todos os registros retornados.
          
                          CUSTO:
          
                          Representa o custo correspondente à venda daquele registro.
          
                          Para obter um custo consolidado:
          
                          - some CUSTO dos registros desejados.
          
                          LUCRO:
          
                          Representa o lucro daquele registro.
          
                          Para obter o lucro consolidado:
          
                          - some LUCRO dos registros desejados.
          
                          O lucro também pode ser validado por:
          
                          LUCRO_CALCULADO = VENDA - CUSTO
          
                          Caso o LUCRO retornado seja diferente do cálculo simples,
                          informe que existe divergência entre os indicadores.
          
                          Não afirme que o SQL está errado sem conhecer sua fórmula.
          
                          NUMVENDAS:
          
                          Representa a quantidade de vendas ou cupons daquele registro.
          
                          Para obter a quantidade consolidada:
          
                          - some NUMVENDAS dos registros desejados.
          
                          =========================================================
                          TICKET MÉDIO
                          =========================================================
          
                          O TICKET_MEDIO de cada registro pode vir calculado.
          
                          Entretanto, para calcular o ticket médio de:
          
                          - uma filial;
                          - um departamento consolidado;
                          - toda a empresa;
                          - um conjunto de registros;
          
                          NÃO faça média simples dos campos TICKET_MEDIO.
          
                          Calcule:
          
                          TICKET_MEDIO_CONSOLIDADO =
                          VENDA_TOTAL / NUMVENDAS_TOTAL
          
                          Calcule somente quando NUMVENDAS_TOTAL for maior que zero.
          
                          =========================================================
                          MARGEM
                          =========================================================
          
                          A MARGEM de cada registro pode vir calculada.
          
                          Para calcular a margem consolidada de:
          
                          - uma filial;
                          - um departamento agrupado;
                          - toda a empresa;
                          - um conjunto de registros;
          
                          NÃO faça média simples das margens.
          
                          Calcule:
          
                          MARGEM_CONSOLIDADA =
                          (LUCRO_TOTAL / VENDA_TOTAL) * 100
          
                          Calcule somente quando VENDA_TOTAL for maior que zero.
          
                          =========================================================
                          META DA FILIAL
                          =========================================================
          
                          META representa a meta TOTAL DA FILIAL para o período.
          
                          A mesma META pode aparecer repetida em todos os departamentos
                          daquela filial.
          
                          Exemplo:
          
                          Filial 1 / ACOUGUE:
                          META = 77.290,32
          
                          Filial 1 / BAZAR:
                          META = 77.290,32
          
                          Filial 1 / BEBIDAS:
                          META = 77.290,32
          
                          Isso representa uma única meta da filial, e não uma meta
                          individual para cada departamento.
          
                          Portanto:
          
                          - nunca some META entre departamentos da mesma filial;
                          - nunca divida META pela quantidade de departamentos;
                          - nunca transforme META em meta diária sem uma regra explícita;
                          - pegue META somente uma vez por CODFILIAL.
          
                          Para calcular o atingimento da filial:
          
                          ATINGIMENTO_FILIAL =
                          (VENDA_TOTAL_FILIAL / META_FILIAL) * 100
          
                          Calcule somente quando META_FILIAL for maior que zero.
          
                          Interpretação:
          
                          - abaixo de 100%: meta ainda não atingida;
                          - igual ou acima de 100%: meta atingida.
          
                          Para calcular quanto falta para atingir a meta:
          
                          VALOR_FALTANTE =
                          META_FILIAL - VENDA_TOTAL_FILIAL
          
                          Se VALOR_FALTANTE for menor ou igual a zero, a meta já
                          foi atingida.
          
                          =========================================================
                          META TOTAL DA EMPRESA
                          =========================================================
          
                          Para obter a meta total da empresa:
          
                          1. Agrupe os registros por CODFILIAL.
                          2. Pegue META somente uma vez para cada filial.
                          3. Some as metas únicas.
          
                          META_TOTAL_EMPRESA =
                          soma das metas únicas por CODFILIAL
          
                          Nunca some todas as ocorrências do campo META, pois a meta
                          pode aparecer repetida entre departamentos.
          
                          Para calcular o atingimento geral:
          
                          ATINGIMENTO_GERAL =
                          (VENDA_TOTAL_EMPRESA / META_TOTAL_EMPRESA) * 100
          
                          =========================================================
                          PERCENTUAL CARREGADO
                          =========================================================
          
                          PERCENTUAL_CARREGADO representa aproximadamente quanto
                          a venda daquele departamento corresponde à meta total
                          da filial.
          
                          Fórmula aproximada:
          
                          PERCENTUAL_CARREGADO =
                          (VENDA_DEPARTAMENTO / META_FILIAL) * 100
          
                          Para obter o percentual total carregado da filial,
                          preferencialmente calcule:
          
                          PERCENTUAL_TOTAL_FILIAL =
                          (VENDA_TOTAL_FILIAL / META_FILIAL) * 100
          
                          Não faça média simples dos valores de PERCENTUAL_CARREGADO.
          
                          A soma dos percentuais dos departamentos pode apresentar
                          pequenas diferenças de arredondamento.
          
                          =========================================================
                          AGRUPAMENTOS
                          =========================================================
          
                          Quando o usuário perguntar por uma filial:
          
                          - analise somente os registros dessa filial.
          
                          Quando perguntar por todas as filiais:
          
                          - analise todos os registros.
          
                          Quando perguntar por um departamento:
          
                          - filtre os registros pelo nome do departamento;
                          - some os valores das filiais incluídas na pergunta.
          
                          Exemplo:
          
                          "Quanto vendeu o Açougue?"
          
                          VENDA_ACOUGUE =
                          soma de VENDA de todos os registros cujo DEPARTAMENTO
                          corresponde a ACOUGUE.
          
                          Quando perguntar quanto um departamento representa da
                          venda total:
          
                          PARTICIPACAO_DEPARTAMENTO =
                          (VENDA_TOTAL_DEPARTAMENTO /
                          VENDA_TOTAL_EMPRESA) * 100
          
                          =========================================================
                          COMPARAÇÕES
                          =========================================================
          
                          Esta ferramenta pode ser chamada mais de uma vez para
                          comparar períodos.
          
                          Em uma comparação, apresente:
          
                          - valor do primeiro período;
                          - valor do segundo período;
                          - diferença absoluta;
                          - diferença percentual.
          
                          Fórmula:
          
                          VARIACAO_PERCENTUAL =
                          ((VALOR_ATUAL - VALOR_ANTERIOR) /
                          VALOR_ANTERIOR) * 100
          
                          Calcule somente quando VALOR_ANTERIOR for diferente de zero.
          
                          Se o valor anterior for zero, informe que não é possível
                          calcular uma variação percentual tradicional.
          
                          =========================================================
                          RANKINGS
                          =========================================================
          
                          Pode identificar:
          
                          - filial com maior venda;
                          - filial com menor venda;
                          - departamento com maior venda;
                          - departamento com menor venda;
                          - maior lucro;
                          - menor lucro;
                          - melhor margem consolidada;
                          - pior margem consolidada;
                          - maior ticket médio consolidado;
                          - filial mais próxima da meta;
                          - filial com maior atingimento;
                          - filial com maior valor faltante.
          
                          Sempre use os cálculos consolidados corretos.
          
                          Não faça média simples de:
          
                          - MARGEM;
                          - TICKET_MEDIO;
                          - PERCENTUAL_CARREGADO.
          
                          =========================================================
                          TRATAMENTO DE VALORES NULOS
                          =========================================================
          
                          Para cálculos de soma, campos monetários ou quantitativos
                          nulos podem ser considerados zero:
          
                          - VENDA
                          - CUSTO
                          - LUCRO
                          - NUMVENDAS
          
                          Não transforme META nula em zero para concluir que uma
                          filial bateu a meta.
          
                          Se META não for retornada, informe que não é possível
                          calcular o atingimento daquela filial.
          
                          =========================================================
                          FORMATO DA RESPOSTA
                          =========================================================
          
                          Responda somente com informações suportadas pelos dados.
          
                          Formate:
          
                          - dinheiro: R$ 1.234,56
                          - percentual: 12,50%
                          - diferenças entre percentuais: pontos percentuais
          
                          Nunca invente valores, metas, filiais ou departamentos.
                          
                          =========================================================
                            CONSULTA DE APOIO PARA ENTRADA E SAÍDA
                            ======================================

                            Quando esta ferramenta for utilizada como apoio para uma análise de entrada e saída, o período recebido deve corresponder ao mês completo.

                            Exemplo:

                            Análise de entrada e saída:

                            01-JUL-2026 até 10-JUL-2026

                            Período desta ferramenta para buscar a meta:

                            01-JUL-2026 até 31-JUL-2026

                            Nesse contexto, utilize principalmente:

                            * CODFILIAL;
                            * META;
                            * VENDA, quando necessária como informação complementar.

                            META pode aparecer repetida em todos os departamentos da mesma filial.

                            Pegue META somente uma vez por CODFILIAL.

                            Não some metas repetidas entre departamentos.

                      """,
           
            "parameters": {
                "type": "object",
                "properties": {
                    "data_inicio": {
                        "type": "string",
                        "description": (
                            "Data inicial no formato DD-MON-YYYY. "
                            "Exemplo: 01-JUL-2026."
                        ),
                    },
                    "data_fim": {
                        "type": "string",
                        "description": (
                            "Data final no formato DD-MON-YYYY. "
                            "Exemplo: 10-JUL-2026."
                        ),
                    },
                },
                "required": [
                    "data_inicio",
                    "data_fim",
                ],
                "additionalProperties": False,
            },
        },
    },
    # =========================================================
    # TOOL 2 — ESTOQUE DE PRODUTO
    # =========================================================
    {
        "type": "function",
        "function": {
            "name": "consultar_estoque",
            "description": """
                          Consulta informações de estoque de um produto no WinThor.
          
                          Use esta ferramenta quando a pergunta estiver relacionada a:
          
                          - estoque de um produto específico;
                          - quantidade disponível;
                          - estoque por filial;
                          - produto zerado;
                          - giro do produto;
                          - vendas recentes;
                          - última entrada;
                          - última saída;
                          - possível ruptura;
                          - possível excesso;
                          - produto parado;
                          - necessidade de reposição;
                          - recomendação de compra.
          
                          Esta ferramenta exige o código numérico do produto.
          
                          Nunca invente CODPROD.
          
                          Se o usuário informar somente o nome de um produto e nenhuma
                          outra ferramenta disponível conseguir localizar seu código,
                          informe que é necessário o código do produto.
          
                          Os registros podem conter:
          
                          - CODFILIAL
                          - CODPROD
                          - DESCRICAO
                          - ESTOQUE
                          - DTULTENT
                          - DTULTSAIDA
                          - QTVENDMES
                          - QTVENDMES1
                          - QTVENDMES2
                          - QTVENDMES3
                          - QTVENDDIA
                          - QTGIRODIA
          
                          =========================================================
                          INTERPRETAÇÃO DOS CAMPOS
                          =========================================================
          
                          CODFILIAL:
          
                          Identifica a filial.
          
                          CODPROD:
          
                          Código do produto.
          
                          DESCRICAO:
          
                          Nome ou descrição do produto.
          
                          ESTOQUE:
          
                          Quantidade atual informada para a filial.
          
                          DTULTENT:
          
                          Data da última entrada conhecida do produto.
          
                          DTULTSAIDA:
          
                          Data da última saída ou venda conhecida do produto.
          
                          QTVENDMES:
          
                          Quantidade vendida no mês atual.
          
                          QTVENDMES1:
          
                          Quantidade vendida no mês anterior.
          
                          QTVENDMES2:
          
                          Quantidade vendida há dois meses.
          
                          QTVENDMES3:
          
                          Quantidade vendida há três meses.
          
                          QTVENDDIA:
          
                          Quantidade vendida no dia.
          
                          QTGIRODIA:
          
                          Giro médio diário informado pelo relatório.
          
                          =========================================================
                          ANÁLISE POR FILIAL
                          =========================================================
          
                          Analise cada filial separadamente.
          
                          Não misture o estoque de uma filial com o giro de outra.
          
                          Quando o usuário solicitar um total geral:
          
                          ESTOQUE_TOTAL =
                          soma do ESTOQUE de todas as filiais
          
                          Mesmo apresentando o total, mostre também a distribuição
                          por filial quando ela for relevante.
          
                          =========================================================
                          RISCO DE RUPTURA
                          =========================================================
          
                          Um produto pode apresentar indício de ruptura quando:
          
                          - ESTOQUE for zero ou muito baixo;
                          - existir giro ou venda recente;
                          - DTULTSAIDA for recente;
                          - houver consumo frequente;
                          - não houver reposição recente.
          
                          Estoque zero com vendas recentes representa um forte
                          indício de ruptura naquela filial.
          
                          Não afirme perda de venda sem dados que comprovem isso.
          
                          Utilize expressões como:
          
                          - risco de ruptura;
                          - possível ruptura;
                          - reposição recomendada;
                          - precisa ser investigado.
          
                          =========================================================
                          EXCESSO OU PRODUTO PARADO
                          =========================================================
          
                          Um produto pode apresentar indício de excesso ou estoque
                          parado quando:
          
                          - ESTOQUE for elevado;
                          - QTGIRODIA for muito baixo ou zero;
                          - vendas dos meses anteriores forem baixas ou inexistentes;
                          - DTULTSAIDA estiver distante;
                          - houver estoque sem movimentação recente.
          
                          Não classifique estoque como excessivo apenas porque a
                          quantidade absoluta parece alta.
          
                          Compare o estoque com:
          
                          - giro;
                          - vendas recentes;
                          - histórico dos últimos meses;
                          - última saída;
                          - distribuição entre filiais.
          
                          =========================================================
                          COBERTURA ESTIMADA
                          =========================================================
          
                          Quando ESTOQUE e QTGIRODIA forem válidos e QTGIRODIA
                          for maior que zero, pode calcular:
          
                          DIAS_COBERTURA_ESTIMADA =
                          ESTOQUE / QTGIRODIA
          
                          Informe claramente que é uma estimativa baseada no giro
                          diário retornado.
          
                          Não calcule quando QTGIRODIA for zero ou nulo.
          
                          Não invente dias de cobertura quando o giro não estiver
                          disponível.
          
                          =========================================================
                          TRANSFERÊNCIA ENTRE FILIAIS
                          =========================================================
          
                          Quando uma filial possuir estoque elevado e outra apresentar
                          estoque baixo ou zerado com giro recente, pode recomendar:
          
                          - verificar transferência entre filiais.
          
                          A recomendação deve ser apresentada como possibilidade,
                          pois a ferramenta não confirma disponibilidade logística,
                          reserva, bloqueio ou política interna.
          
                          =========================================================
                          NECESSIDADE DE COMPRA
                          =========================================================
          
                          Ao analisar necessidade de compra, considere em conjunto:
          
                          - estoque atual;
                          - giro diário;
                          - vendas do mês atual;
                          - vendas dos três meses anteriores;
                          - última entrada;
                          - última saída;
                          - situação das outras filiais.
          
                          Classificações possíveis:
          
                          COMPRA OU REPOSIÇÃO RECOMENDADA:
          
                          - estoque baixo ou zero;
                          - giro ou vendas recentes relevantes;
                          - risco de ruptura.
          
                          MONITORAR:
          
                          - estoque ainda disponível;
                          - giro moderado;
                          - sem urgência comprovada.
          
                          COMPRA NÃO RECOMENDADA NO MOMENTO:
          
                          - estoque alto;
                          - giro baixo;
                          - vendas recentes fracas;
                          - possível produto parado.
          
                          VERIFICAR TRANSFERÊNCIA:
          
                          - uma filial está baixa ou zerada;
                          - outra filial possui estoque acima da necessidade aparente.
          
                          Não diga apenas "compre" ou "não compre".
          
                          Explique os indicadores utilizados.
          
                          =========================================================
                          DADOS NULOS
                          =========================================================
          
                          Não transforme automaticamente datas nulas em "produto parado".
          
                          Não transforme QTGIRODIA nulo em zero para concluir que não
                          existe giro.
          
                          Informe que o indicador não foi retornado quando necessário.
          
                          Campos quantitativos nulos podem ser tratados como zero somente
                          em somas, sem transformar ausência de informação em fato.
          
                          =========================================================
                          FORMATO DA RESPOSTA
                          =========================================================
          
                          Apresente:
          
                          - código e descrição;
                          - situação por filial;
                          - estoque;
                          - giro;
                          - vendas recentes;
                          - última entrada;
                          - última saída;
                          - cobertura estimada, quando calculável;
                          - diagnóstico;
                          - recomendação justificada.
          
                          Diferencie:
          
                          - fato retornado;
                          - cálculo;
                          - indício;
                          - risco;
                          - recomendação.
          
                          Nunca invente estoque, giro, datas ou vendas.
                      """,
            "parameters": {
                "type": "object",
                "properties": {
                    "codprod": {
                        "type": "integer",
                        "description": (
                            "Código numérico do produto no WinThor. " "Exemplo: 53541."
                        ),
                    },
                },
                "required": [
                    "codprod",
                ],
                "additionalProperties": False,
            },
        },
    },
    # =========================================================
    # TOOL 3 — ENTRADA E SAÍDA HIERÁRQUICA
    # =========================================================
    {
        "type": "function",
        "function": {
            "name": "entrada_saida_departamento",
            "description": """
                # REGRAS DE NEGÓCIO DA ANÁLISE

                Estas regras devem ser utilizadas em conjunto com as demais instruções da ferramenta.

                Quando houver conflito com qualquer interpretação anterior relacionada aos campos:

                * VALOR_TOTAL_ENTRADA;
                * VALOR_TOTAL_SAIDA;
                * VL_USO_CONSUMO;
                * VALOR_DEVLUCAO;
                * VL_AVARIA;
                * CUSTO_TOTAL;
                * MARGEM;
                * MARGEM_WINTHOR;
                * MARGEM_IDEAL;
                * PARTICIPACAO_ESPERADA;
                * VL_EXCESSO_COMPR;
                * campo de meta mensal de venda, quando retornado pela API;

                prevalecem as regras definidas neste description.

                Responda sempre em português do Brasil.

                =========================================================
                NÍVEIS DA CONSULTA
                ==================

                A consulta possui quatro níveis hierárquicos:

                1. Departamento;
                2. Seção;
                3. Categoria;
                4. Produto.

                NÍVEL 1 — DEPARTAMENTO

                Parâmetros:

                * data_inicio;
                * data_fim.

                Retorna todos os departamentos.

                Cada registro pode fornecer CODEPTO, que deve ser utilizado para consultar as seções daquele departamento.

                NÍVEL 2 — SEÇÃO

                Parâmetros:

                * data_inicio;
                * data_fim;
                * codepto.

                Retorna as seções do departamento informado.

                Cada registro pode fornecer CODSEC, que deve ser utilizado para consultar as categorias da seção.

                NÍVEL 3 — CATEGORIA

                Parâmetros:

                * data_inicio;
                * data_fim;
                * codepto;
                * codsec.

                Retorna as categorias da seção informada.

                Cada registro pode fornecer CODCATEGORIA, que deve ser utilizado para consultar os produtos.

                NÍVEL 4 — PRODUTO

                Parâmetros:

                * data_inicio;
                * data_fim;
                * codepto;
                * codsec;
                * codcategoria.

                Retorna os produtos da categoria informada.

                Nunca invente:

                * CODEPTO;
                * CODSEC;
                * CODCATEGORIA;
                * CODPROD.

                Sempre obtenha os códigos de uma consulta anterior ou de informações já disponíveis no histórico da conversa.

                =========================================================
                CAMPOS RETORNADOS
                =================

                Dependendo do nível consultado, os registros podem apresentar:

                * CODEPTO;
                * DEPARTAMENTO;
                * CODSEC;
                * SECAO;
                * CODCATEGORIA;
                * CATEGORIA;
                * CODPROD;
                * PRODUTO;
                * VL_USO_CONSUMO;
                * VALOR_TOTAL_ENTRADA;
                * VALOR_DEVLUCAO;
                * MARGEM_IDEAL;
                * PARTICIPACAO_ESPERADA;
                * VALOR_TOTAL_SAIDA;
                * VL_AVARIA;
                * CUSTO_TOTAL;
                * MARGEM_WINTHOR;
                * MARGEM;
                * RELATORIO_VALOR;
                * VL_EXCESSO_COMPR, quando disponibilizado;
                * campo de meta mensal de venda, quando disponibilizado.

                O nome do campo de devolução é:

                VALOR_DEVLUCAO

                Ele está escrito dessa forma na API.

                Não tente acessar ou apresentar VALOR_DEVOLUCAO, salvo se a resposta realmente retornar esse nome.

                Não invente o nome do campo da meta mensal de venda.

                Quando a meta for retornada, utilize exatamente o nome do campo apresentado pela API.

                =========================================================
                VALORES NULOS
                =============

                Para cálculos de soma agregada, considere como zero quando estiverem nulos:

                * VALOR_TOTAL_ENTRADA;
                * VALOR_TOTAL_SAIDA;
                * CUSTO_TOTAL;
                * VL_USO_CONSUMO;
                * VL_AVARIA;
                * VALOR_DEVLUCAO;
                * VL_EXCESSO_COMPR.

                Isso serve somente para permitir cálculos agregados.

                Não transforme ausência de informação em fato.

                Se VALOR_TOTAL_ENTRADA estiver nulo em uma seção, categoria ou produto, não diga:

                “Não houve entrada.”

                Diga:

                “O valor de entrada não foi retornado ou não foi detalhado nesse nível.”

                Não transforme automaticamente em zero:

                * MARGEM;
                * MARGEM_WINTHOR;
                * MARGEM_IDEAL;
                * PARTICIPACAO_ESPERADA;
                * meta mensal de venda.

                Se esses indicadores estiverem nulos, informe que não foram retornados.

                Não calcule diferenças percentuais utilizando um indicador nulo.

                =========================================================
                REGRA DO VALOR TOTAL DE ENTRADA
                ===============================

                Existem duas formas diferentes de utilizar VALOR_TOTAL_ENTRADA:

                1. Valor individual de departamento, seção, categoria ou produto;
                2. Valor consolidado correspondente à soma de todos os departamentos.

                Essas duas situações não devem ser confundidas.

                =========================================================
                ENTRADA INDIVIDUAL
                ==================

                Na análise individual de um departamento, seção, categoria ou produto, utilize exatamente o valor apresentado em:

                VALOR_TOTAL_ENTRADA

                Não some nem diminua VL_USO_CONSUMO desse valor.

                Para cada registro:

                VALOR_ENTRADA_DO_REGISTRO =
                VALOR_TOTAL_ENTRADA

                É proibido calcular nos níveis individuais:

                VALOR_TOTAL_ENTRADA - VL_USO_CONSUMO

                Também é proibido calcular:

                VALOR_TOTAL_ENTRADA + VL_USO_CONSUMO

                VL_USO_CONSUMO deve ser analisado separadamente como um indicador próprio.

                Ao comparar entrada e saída de um departamento, seção ou categoria, calcule:

                SALDO_MOVIMENTACAO =
                VALOR_TOTAL_ENTRADA - VALOR_TOTAL_SAIDA

                Quando o saldo for positivo:

                * a entrada foi superior à saída;
                * pode existir entrada acima da movimentação realizada;
                * pode existir formação de estoque;
                * pode existir capital imobilizado;
                * pode existir excesso de compra;
                * a situação precisa ser analisada com MARGEM, participação, VL_EXCESSO_COMPR, estoque e giro.

                Quando o saldo for negativo:

                * a saída foi superior à entrada;
                * pode existir consumo de estoque anteriormente acumulado;
                * pode existir reposição insuficiente;
                * pode existir possível risco de falta de mercadoria;
                * a situação precisa ser analisada com estoque, giro e disponibilidade.

                Não afirme aumento real de estoque ou ruptura somente com base nessa diferença.

                =========================================================
                ENTRADA TOTAL CONSOLIDADA
                =========================

                Somente no resumo geral, ao calcular o valor total de entrada correspondente à soma de todos os departamentos, some o valor total de uso e consumo.

                Calcule:

                SOMA_ENTRADA_DEPARTAMENTOS =
                soma de VALOR_TOTAL_ENTRADA de todos os departamentos

                TOTAL_USO_CONSUMO =
                soma de VL_USO_CONSUMO de todos os departamentos

                VALOR_TOTAL_ENTRADA_CONSOLIDADA =
                SOMA_ENTRADA_DEPARTAMENTOS + TOTAL_USO_CONSUMO

                Essa soma deve ser realizada exclusivamente para obter o total geral de entrada.

                Não distribua novamente o uso e consumo entre departamentos, seções, categorias ou produtos.

                Não altere o VALOR_TOTAL_ENTRADA individual dos registros.

                Caso algum VL_USO_CONSUMO esteja nulo, considere zero apenas para realizar a soma consolidada.

                Não transforme o nulo em afirmação de que não houve uso e consumo.

                Ao apresentar o resumo geral, mostre separadamente:

                * soma das entradas dos departamentos;
                * total de uso e consumo;
                * valor total de entrada consolidada;
                * valor total de saída;
                * diferença entre entrada consolidada e saída.

                Calcule:

                SALDO_GERAL_MOVIMENTACAO =
                VALOR_TOTAL_ENTRADA_CONSOLIDADA - VALOR_TOTAL_SAIDA_TOTAL

                Quando SALDO_GERAL_MOVIMENTACAO for positivo:

                * a entrada consolidada foi superior à saída;
                * existe saldo positivo de movimentação;
                * pode existir formação de estoque ou capital imobilizado;
                * isso não representa automaticamente prejuízo.

                Quando SALDO_GERAL_MOVIMENTACAO for negativo:

                * a saída foi superior à entrada consolidada;
                * pode existir consumo de estoque acumulado;
                * pode existir reposição abaixo da movimentação;
                * isso não representa automaticamente lucro.

                =========================================================
                PRIORIDADE NA LEITURA DO SALDO GERAL
                ====================================

                O saldo geral deve ser calculado e apresentado, mas não deve ser tratado isoladamente como o principal indicador de desempenho.

                Mesmo quando a saída for superior à entrada consolidada, a conclusão principal deve priorizar:

                1. MARGEM comparada à MARGEM_IDEAL;
                2. MARGEM_WINTHOR comparada à MARGEM_IDEAL;
                3. desempenho da saída comparado à meta mensal de venda;
                4. participação realizada comparada à participação esperada;
                5. saldo geral entre entrada e saída;
                6. avaria, devolução, uso e consumo e excesso de compra.

                O fato de a saída superar a entrada não significa, sozinho, que o resultado foi bom.

                Uma saída superior à entrada pode coexistir com:

                * MARGEM distante da MARGEM_IDEAL;
                * MARGEM_WINTHOR abaixo da MARGEM_IDEAL;
                * precificação inadequada;
                * venda com rentabilidade insuficiente;
                * consumo de estoque acumulado;
                * reposição insuficiente;
                * possível risco de falta de mercadoria;
                * participação abaixo da esperada;
                * saída acumulada abaixo da meta mensal.

                Da mesma forma, entrada superior à saída não representa automaticamente resultado ruim.

                Essa situação pode estar relacionada a:

                * abastecimento antes de períodos de maior venda;
                * formação planejada de estoque;
                * preparação para promoções;
                * recebimento concentrado de mercadorias;
                * pedidos realizados anteriormente;
                * necessidade de estoque de segurança;
                * primeira ou última semana do mês;
                * sazonalidade.

                O saldo deve contextualizar a análise, mas nunca substituir a leitura das margens e da meta de venda.

                =========================================================
                MARGEM — RELAÇÃO ENTRE ENTRADA E SAÍDA
                ======================================

                MARGEM representa a análise gerencial da relação entre entrada e saída.

                Ela ajuda a avaliar:

                * se o volume comprado está coerente com o volume vendido;
                * se as entradas estão acima ou abaixo da necessidade;
                * se a relação entre compra e saída está próxima do objetivo;
                * se pode existir excesso de compra;
                * se pode existir reposição insuficiente.

                O objetivo é que MARGEM fique o mais próximo possível da MARGEM_IDEAL.

                Nos níveis de departamento, seção ou categoria, considere:

                * VALOR_TOTAL_ENTRADA retornado para o registro;
                * VALOR_TOTAL_SAIDA;
                * MARGEM;
                * MARGEM_IDEAL;
                * VL_EXCESSO_COMPR;
                * participação;
                * estoque e giro, quando disponíveis.

                Não some nem diminua VL_USO_CONSUMO do VALOR_TOTAL_ENTRADA individual para analisar MARGEM.

                Quando MARGEM e MARGEM_IDEAL estiverem disponíveis, calcule:

                DIFERENCA_MARGEM =
                MARGEM - MARGEM_IDEAL

                Apresente o resultado em pontos percentuais.

                MARGEM PRÓXIMA DA IDEAL:

                * relação entre compras e saídas aparentemente equilibrada;
                * volume comprado aparentemente próximo do necessário para a saída realizada;
                * deve ser confirmada com estoque, giro, participação e excesso de compra.

                MARGEM ABAIXO DA IDEAL:

                * pode existir entrada acima do necessário;
                * pode existir saída abaixo do esperado;
                * pode existir formação de estoque;
                * pode existir redução de giro;
                * pode existir excesso de compra;
                * analise juntamente com VL_EXCESSO_COMPR, participação, estoque e giro.

                MARGEM ACIMA DA IDEAL:

                * pode existir saída superior à reposição;
                * pode existir consumo de estoque anteriormente acumulado;
                * pode existir compra insuficiente;
                * pode existir possível risco de falta de reposição;
                * analise juntamente com estoque, giro e disponibilidade.

                Não afirme excesso de estoque ou ruptura somente com base na MARGEM.

                Quando MARGEM estiver nula, não tente reconstruir sua fórmula sem conhecer o SQL.

                Informe:

                “A MARGEM de entrada versus saída não foi retornada nesse nível.”

                =========================================================
                MARGEM_WINTHOR — MARGEM DE PRECIFICAÇÃO
                =======================================

                MARGEM_WINTHOR representa a margem de precificação dos produtos efetivamente vendidos.

                Ela possui finalidade diferente da MARGEM.

                MARGEM_WINTHOR deve ser utilizada para analisar:

                * se os produtos foram vendidos com preço adequado;
                * se a rentabilidade das vendas está próxima da ideal;
                * se descontos podem estar reduzindo a margem;
                * se o custo aumentou sem atualização do preço;
                * se produtos de baixa margem estão afetando o resultado.

                Quando MARGEM_WINTHOR e MARGEM_IDEAL estiverem disponíveis, calcule:

                DIFERENCA_MARGEM_WINTHOR =
                MARGEM_WINTHOR - MARGEM_IDEAL

                Apresente o resultado em pontos percentuais.

                PRECIFICAÇÃO ADEQUADA:

                * MARGEM_WINTHOR igual ou superior à MARGEM_IDEAL;
                * preços praticados aparentemente compatíveis com a margem desejada.

                PRECIFICAÇÃO EM ATENÇÃO:

                * MARGEM_WINTHOR abaixo da ideal em até 3 pontos percentuais;
                * pequena diferença que deve ser acompanhada.

                PRECIFICAÇÃO RUIM:

                * MARGEM_WINTHOR abaixo da ideal por mais de 3 pontos percentuais;
                * preços, custos, descontos ou mix podem estar incompatíveis com o objetivo.

                PRECIFICAÇÃO CRÍTICA:

                * MARGEM_WINTHOR negativa;
                * grande distância negativa da MARGEM_IDEAL;
                * resultado bruto negativo relevante;
                * grande volume de venda afetado.

                Possíveis pontos de investigação:

                * preço de venda desatualizado;
                * aumento do custo de aquisição;
                * descontos excessivos;
                * promoções com margem baixa;
                * custo cadastrado incorretamente;
                * margem ideal cadastrada incorretamente;
                * composição desfavorável do mix;
                * produtos de baixa margem com participação elevada.

                Apresente essas possibilidades como hipóteses, não como causas comprovadas.

                =========================================================
                ANÁLISE CONJUNTA DAS MARGENS
                ============================

                Sempre analise MARGEM e MARGEM_WINTHOR em conjunto.

                MARGEM BOA + MARGEM_WINTHOR BOA:

                * relação entre compras e saídas aparentemente equilibrada;
                * precificação aparentemente adequada;
                * situação favorável, desde que participação, avaria, devolução, uso e consumo e excesso de compra estejam controlados.

                MARGEM RUIM + MARGEM_WINTHOR BOA:

                * a precificação pode estar adequada;
                * o problema pode estar na relação entre compra e saída;
                * pode existir entrada acima do necessário;
                * pode existir venda abaixo do esperado;
                * pode existir excesso de compra ou baixo giro.

                MARGEM BOA + MARGEM_WINTHOR RUIM:

                * o volume comprado pode estar equilibrado com a saída;
                * a rentabilidade dos produtos vendidos pode estar abaixo do esperado;
                * investigue preço, custo, descontos, promoções e mix.

                MARGEM RUIM + MARGEM_WINTHOR RUIM:

                * pode existir simultaneamente desequilíbrio entre compras e saídas;
                * pode existir excesso de compra;
                * pode existir saída abaixo do esperado;
                * pode existir problema de preço, custo ou desconto;
                * esse registro deve receber prioridade no aprofundamento.

                Nunca conclua que o desempenho foi bom somente porque uma das margens está adequada.

                =========================================================
                META MENSAL DE VENDA
                ====================

                Sempre que a API retornar a meta cadastrada de venda do mês, compare o valor de saída com essa meta.

                Não invente o nome ou o valor do campo da meta.

                Utilize exatamente o campo retornado pela API.

                Caso a meta mensal não seja retornada, informe:

                “A meta mensal de venda não foi retornada pela consulta. Por isso, não foi possível determinar com segurança se o ritmo de saída está adequado à meta cadastrada.”

                Não invente uma meta utilizando:

                * entrada;
                * margem;
                * participação esperada;
                * venda do período anterior;
                * qualquer outro indicador.

                Quando a consulta abranger o mês completo, calcule:

                PERCENTUAL_META_REALIZADA =
                VALOR_TOTAL_SAIDA_TOTAL / META_MENSAL_VENDA * 100

                Calcule também:

                DIFERENCA_PARA_META =
                VALOR_TOTAL_SAIDA_TOTAL - META_MENSAL_VENDA

                META ATINGIDA:

                * saída igual ou superior à meta;
                * informe quanto a meta foi superada em reais e percentual;
                * ainda analise MARGEM e MARGEM_WINTHOR;
                * atingir a meta não garante rentabilidade adequada.

                META NÃO ATINGIDA:

                * saída abaixo da meta;
                * informe quanto faltou em reais e percentual;
                * identifique departamentos, seções e categorias que mais contribuíram para a diferença;
                * analise participação, possível ruptura, preço, mix e disponibilidade.

                Quando a consulta abranger somente parte do mês, avalie o ritmo acumulado.

                Se a API retornar uma meta acumulada esperada até a data, utilize esse campo como referência principal.

                Caso a API retorne apenas a meta total do mês e a consulta comece no primeiro dia do mês, calcule somente como referência:

                META_LINEAR_ATE_A_DATA =
                META_MENSAL_VENDA
                × DIAS_DECORRIDOS_NO_MES
                ÷ DIAS_TOTAIS_DO_MES

                Calcule:

                PERCENTUAL_META_LINEAR =
                VALOR_TOTAL_SAIDA_ACUMULADA
                ÷ META_LINEAR_ATE_A_DATA
                × 100

                Informe claramente que essa é uma projeção proporcional simples e que a venda não é distribuída igualmente durante o mês.

                Se o período consultado não começar no primeiro dia do mês, não trate a saída do intervalo como venda acumulada do mês.

                Nesse caso:

                * use uma meta específica do intervalo, caso seja retornada;
                * caso não exista meta específica, informe que não é possível determinar com precisão o progresso mensal apenas com aquele intervalo.

                =========================================================
                SAZONALIDADE DENTRO DO MÊS
                ==========================

                Considere como regra de negócio que:

                * a primeira semana do mês está entre os períodos de maior venda;
                * a última semana do mês está entre os períodos de maior venda;
                * as semanas intermediárias normalmente apresentam ritmo menor;
                * as vendas não são distribuídas uniformemente entre todos os dias.

                Para esta análise, considere:

                * primeira semana: dias 1 a 7;
                * última semana: últimos sete dias corridos do mês;
                * período intermediário: demais dias.

                PERÍODO NA PRIMEIRA SEMANA:

                * espera-se ritmo de venda mais forte;
                * resultado abaixo da referência proporcional merece atenção;
                * resultado elevado é positivo, mas não deve ser projetado linearmente para o mês inteiro;
                * verifique se MARGEM e MARGEM_WINTHOR também estão adequadas.

                PERÍODO NAS SEMANAS INTERMEDIÁRIAS:

                * ritmo menor pode ser compatível com a sazonalidade;
                * não classifique automaticamente o desempenho como ruim;
                * considere que parte relevante das vendas pode ocorrer na última semana;
                * compare com meta acumulada, quando disponível.

                PERÍODO NA ÚLTIMA SEMANA:

                * espera-se aceleração das vendas;
                * verifique se o crescimento foi suficiente para aproximar ou atingir a meta;
                * desempenho fraco nesse período exige atenção maior;
                * analise possíveis rupturas, preço, mix, participação e disponibilidade.

                PERÍODO QUE ATRAVESSA DIFERENTES SEMANAS:

                * identifique os dias pertencentes à primeira semana;
                * identifique os dias intermediários;
                * identifique os dias pertencentes à última semana;
                * não trate todos os dias com o mesmo peso de expectativa;
                * não invente percentuais de peso para cada semana.

                Ao avaliar se o supermercado está indo bem, considere conjuntamente:

                * percentual da meta realizado;
                * diferença em reais para a meta;
                * parte do mês já transcorrida;
                * presença da primeira ou última semana;
                * MARGEM comparada à MARGEM_IDEAL;
                * MARGEM_WINTHOR comparada à MARGEM_IDEAL;
                * participação realizada comparada à esperada;
                * departamentos responsáveis pelo resultado;
                * possíveis perdas por ruptura, preço, mix ou indisponibilidade.

                Nunca diga que o supermercado está indo bem apenas porque a saída superou a entrada.

                Nunca diga que está indo mal apenas porque a entrada superou a saída.

                Classifique o ritmo de venda como:

                * favorável;
                * dentro do esperado;
                * em atenção;
                * preocupante;
                * inconclusivo por falta de meta.

                Explique sempre o motivo da classificação.

                =========================================================
                PARTICIPAÇÃO REAL E PARTICIPAÇÃO ESPERADA
                =========================================

                PARTICIPACAO_ESPERADA representa a participação que se espera daquele departamento, seção ou categoria.

                PARTICIPACAO_REAL representa quanto o registro efetivamente participou das saídas do conjunto consultado.

                Quando não vier pronta, calcule:

                PARTICIPACAO_REAL =
                VALOR_TOTAL_SAIDA_REGISTRO
                ÷ VALOR_TOTAL_SAIDA_TOTAL_DO_NIVEL
                × 100

                Calcule:

                DIFERENCA_PARTICIPACAO =
                PARTICIPACAO_REAL - PARTICIPACAO_ESPERADA

                Apresente o resultado em pontos percentuais.

                Compare participação realizada e esperada somente quando PARTICIPACAO_ESPERADA pertencer realmente ao nível analisado.

                Caso o mesmo valor do departamento apareça repetido em todas as seções, categorias ou produtos, não trate esse valor automaticamente como meta dos níveis inferiores.

                Quando a participação estiver abaixo da esperada, possíveis fatores incluem:

                * possível ruptura;
                * reposição insuficiente;
                * preço acima do mercado;
                * precificação inadequada;
                * baixa competitividade;
                * redução de giro;
                * mix incompleto;
                * produtos importantes sem estoque;
                * baixa exposição;
                * falta de promoção;
                * sazonalidade;
                * mudança no comportamento do cliente;
                * erro de cadastro ou classificação;
                * indisponibilidade de itens relevantes.

                Esses fatores são hipóteses de investigação.

                Cruze a participação com:

                * MARGEM;
                * MARGEM_WINTHOR;
                * MARGEM_IDEAL;
                * VALOR_TOTAL_ENTRADA;
                * VALOR_TOTAL_SAIDA;
                * VL_EXCESSO_COMPR;
                * avaria;
                * devolução;
                * uso e consumo;
                * volume financeiro.

                PARTICIPAÇÃO ABAIXO + ENTRADA ALTA:

                * possível excesso de compra;
                * possível estoque com baixo giro;
                * dificuldade de venda;
                * possível preço pouco competitivo.

                PARTICIPAÇÃO ABAIXO + ENTRADA BAIXA:

                * possível falta de reposição;
                * possível ruptura;
                * possível perda de venda por indisponibilidade.

                PARTICIPAÇÃO ABAIXO + MARGEM_WINTHOR RUIM:

                * possível problema de preço ou rentabilidade;
                * descontos ou custos podem estar afetando o resultado.

                PARTICIPAÇÃO ACIMA + MARGEM_WINTHOR RUIM:

                * existe volume relevante de venda;
                * a rentabilidade pode estar inadequada;
                * o impacto financeiro pode ser alto devido ao volume.

                =========================================================
                CUSTO E RESULTADO BRUTO
                =======================

                Quando houver saída e custo, calcule:

                RESULTADO_BRUTO =
                VALOR_TOTAL_SAIDA - CUSTO_TOTAL

                Quando VALOR_TOTAL_SAIDA for maior que zero, calcule:

                PERCENTUAL_CUSTO =
                CUSTO_TOTAL / VALOR_TOTAL_SAIDA * 100

                Se RESULTADO_BRUTO for negativo:

                * o custo informado é superior à saída informada;
                * existe resultado bruto negativo pelo cálculo simples;
                * investigue custo, preço, descontos e possíveis divergências.

                Não desconte novamente avaria, devolução ou uso e consumo do resultado bruto sem conhecer a fórmula do SQL.

                =========================================================
                DEVOLUÇÕES AO FORNECEDOR
                ========================

                VALOR_DEVLUCAO representa mercadorias devolvidas ao fornecedor.

                Quando VALOR_TOTAL_ENTRADA for maior que zero, calcule:

                PERCENTUAL_DEVOLUCAO_ENTRADA =
                VALOR_DEVLUCAO / VALOR_TOTAL_ENTRADA * 100

                Quando VALOR_TOTAL_SAIDA for maior que zero, calcule:

                PERCENTUAL_DEVOLUCAO_SAIDA =
                VALOR_DEVLUCAO / VALOR_TOTAL_SAIDA * 100

                Analise:

                * valor absoluto;
                * percentual sobre a entrada;
                * percentual sobre a saída;
                * concentração por departamento, seção, categoria ou produto;
                * impacto sobre disponibilidade e reposição.

                Possíveis pontos de investigação:

                * problema no recebimento;
                * divergência de pedido;
                * qualidade inadequada;
                * validade insuficiente;
                * excesso de compra;
                * produto com baixa saída;
                * erro de cadastro;
                * desacordo comercial.

                Não apresente nenhuma dessas possibilidades como causa comprovada.

                =========================================================
                USO E CONSUMO
                =============

                VL_USO_CONSUMO representa mercadorias utilizadas internamente pelo supermercado.

                Pode incluir:

                * materiais de limpeza;
                * produtos usados na produção da padaria;
                * ingredientes utilizados na fabricação de produtos;
                * materiais consumidos por setores internos;
                * mercadorias destinadas ao funcionamento geral.

                Uso e consumo não deve ser chamado automaticamente de prejuízo.

                Nos níveis individuais, analise VL_USO_CONSUMO separadamente.

                Não some nem diminua esse campo do VALOR_TOTAL_ENTRADA individual.

                Somente no consolidado geral, some o total de uso e consumo à soma das entradas dos departamentos.

                Quando VALOR_TOTAL_ENTRADA for maior que zero, calcule:

                PERCENTUAL_USO_CONSUMO_ENTRADA =
                VL_USO_CONSUMO / VALOR_TOTAL_ENTRADA * 100

                Quando VALOR_TOTAL_SAIDA for maior que zero, calcule:

                PERCENTUAL_USO_CONSUMO_SAIDA =
                VL_USO_CONSUMO / VALOR_TOTAL_SAIDA * 100

                Analise:

                * valor absoluto;
                * percentual sobre entrada e saída;
                * concentração anormal;
                * departamentos, categorias ou produtos com maior consumo interno;
                * possível desperdício ou erro de lançamento.

                Possíveis orientações:

                * revisar lançamentos;
                * controlar requisições internas;
                * estabelecer limites;
                * separar consumo operacional de consumo produtivo;
                * revisar fichas técnicas;
                * acompanhar produtos de alto valor;
                * investigar desperdícios.

                =========================================================
                AVARIA
                ======

                VL_AVARIA representa produtos considerados avariados e descartados.

                Calcule, quando possível:

                PERCENTUAL_AVARIA_SAIDA =
                VL_AVARIA / VALOR_TOTAL_SAIDA * 100

                PERCENTUAL_AVARIA_ENTRADA =
                VL_AVARIA / VALOR_TOTAL_ENTRADA * 100

                Analise:

                * valor absoluto;
                * percentual sobre entrada e saída;
                * concentração por departamento;
                * concentração por seção;
                * concentração por categoria;
                * concentração por produto;
                * relevância financeira;
                * recorrência.

                Possíveis fatores para investigação:

                * validade;
                * armazenamento;
                * temperatura;
                * refrigeração;
                * manuseio;
                * quebra;
                * exposição inadequada;
                * excesso de compra;
                * baixo giro;
                * falha no recebimento;
                * erro de lançamento.

                Essas possibilidades não representam causas comprovadas.

                =========================================================
                VALOR DE EXCESSO DE COMPRA
                ==========================

                VL_EXCESSO_COMPR representa o valor que deveria ter sido reduzido das entradas de um departamento, seção, categoria ou produto para que, considerando a saída, MARGEM se aproximasse da MARGEM_IDEAL.

                Quanto maior VL_EXCESSO_COMPR:

                * maior o indício de entrada acima do necessário para a saída realizada;
                * maior a referência financeira para possível ajuste das próximas compras.

                O campo não significa:

                * que todo o valor está disponível em estoque;
                * que toda compra foi incorreta;
                * que o valor deve ser automaticamente cortado dos próximos pedidos.

                Analise VL_EXCESSO_COMPR junto com:

                * VALOR_TOTAL_ENTRADA;
                * VALOR_TOTAL_SAIDA;
                * MARGEM;
                * MARGEM_IDEAL;
                * participação;
                * estoque;
                * giro;
                * avaria;
                * devolução;
                * uso e consumo;
                * pedidos pendentes;
                * sazonalidade.

                Possíveis orientações:

                * revisar volume das compras;
                * revisar frequência dos pedidos;
                * ajustar previsão de venda;
                * consultar estoque atual;
                * verificar estoque em outras filiais;
                * transferir mercadorias;
                * realizar ações de giro;
                * revisar mix;
                * suspender temporariamente compras de itens específicos;
                * negociar devolução quando aplicável.

                Nunca recomende redução automática com base apenas em VL_EXCESSO_COMPR.

                =========================================================
                RELATORIO_VALOR
                ===============

                RELATORIO_VALOR pode retornar:

                * LUCRO POTENCIAL;
                * PREJUIZO POTENCIAL.

                Esses nomes são classificações internas do relatório.

                PREJUIZO POTENCIAL geralmente está relacionado a entrada superior à saída.

                LUCRO POTENCIAL geralmente está relacionado a saída superior à entrada.

                Essas classificações não representam isoladamente lucro ou prejuízo contábil.

                Não conclua que houve lucro real apenas porque RELATORIO_VALOR retornou LUCRO POTENCIAL.

                Não conclua que houve prejuízo real apenas porque retornou PREJUIZO POTENCIAL.

                Analise também:

                * custo;
                * resultado bruto;
                * MARGEM;
                * MARGEM_WINTHOR;
                * MARGEM_IDEAL;
                * participação;
                * avaria;
                * devolução;
                * uso e consumo;
                * excesso de compra;
                * meta mensal.

                =========================================================
                ORDEM DA ANÁLISE HIERÁRQUICA
                ============================

                A análise deve começar por todos os departamentos.

                Para cada departamento, analise:

                1. VALOR_TOTAL_ENTRADA sem ajustes;
                2. VALOR_TOTAL_SAIDA;
                3. diferença entre entrada e saída;
                4. MARGEM;
                5. MARGEM_IDEAL;
                6. diferença entre MARGEM e MARGEM_IDEAL;
                7. MARGEM_WINTHOR;
                8. diferença entre MARGEM_WINTHOR e MARGEM_IDEAL;
                9. participação realizada;
                10. participação esperada;
                11. diferença de participação;
                12. CUSTO_TOTAL;
                13. RESULTADO_BRUTO;
                14. VALOR_DEVLUCAO;
                15. VL_USO_CONSUMO separadamente;
                16. VL_AVARIA;
                17. VL_EXCESSO_COMPR;
                18. meta mensal, quando retornada;
                19. ritmo da saída considerando a parte do mês;
                20. volume financeiro;
                21. riscos;
                22. recomendações.

                Quando um departamento chamar atenção, aprofunde:

                Departamento → Seção → Categoria → Produto

                O aprofundamento deve ocorrer quando existir:

                * MARGEM distante da MARGEM_IDEAL;
                * MARGEM_WINTHOR distante da MARGEM_IDEAL;
                * VL_EXCESSO_COMPR relevante;
                * participação abaixo da esperada;
                * entrada muito superior à saída;
                * saída muito superior à entrada;
                * avaria relevante;
                * devolução relevante;
                * uso e consumo relevante;
                * resultado bruto negativo;
                * grande volume financeiro afetado;
                * saída abaixo da meta esperada;
                * desempenho fraco na primeira ou última semana;
                * divergência entre indicadores.

                Nos níveis aprofundados, analise todos os campos disponíveis, não apenas o indicador que gerou o alerta.

                Se o usuário pedir análise completa de todos os registros:

                * percorra todos os departamentos;
                * percorra todas as seções;
                * percorra todas as categorias;
                * percorra todos os produtos;
                * não limite a consulta aos registros críticos.

                Nunca chame uma análise parcial de completa.

                =========================================================
                IDENTIFICAÇÃO DOS RESPONSÁVEIS
                ==============================

                Considere os seguintes compradores:

                MATIAS:

                * Bebidas;
                * Matinais;
                * Mercearia de Alto Giro;
                * Mercearia Doce.

                VANDA:

                * Bazar;
                * Perfumaria;
                * Limpeza;
                * Pet Shop.

                DEYLIANE:

                * Açougue;
                * Perecíveis Congelados e Resfriados;
                * Perecíveis Lácteos.

                RÚBIA:

                * Hortifrúti.

                Seções, categorias e produtos devem herdar o comprador do departamento ao qual pertencem.

                Quando houver problema relevante, informe o comprador responsável pelo acompanhamento.

                A identificação serve para direcionar a ação, não para atribuir culpa.

                Utilize expressões como:

                * responsável pelo acompanhamento;
                * ponto a ser revisado com o comprador;
                * recomendação direcionada ao comprador responsável.

                =========================================================
                RECOMENDAÇÕES
                =============

                Quando MARGEM estiver abaixo da ideal:

                * revisar volume das compras;
                * verificar estoque e giro;
                * analisar VL_EXCESSO_COMPR;
                * reduzir compras de itens com baixo giro;
                * revisar frequência dos pedidos;
                * transferir estoque;
                * realizar ações promocionais;
                * revisar mix.

                Quando MARGEM estiver muito acima da ideal:

                * verificar possível falta de reposição;
                * consultar estoque atual;
                * verificar possíveis rupturas;
                * revisar pedidos pendentes;
                * avaliar aumento controlado da compra;
                * priorizar itens de maior giro.

                Quando MARGEM_WINTHOR estiver abaixo da ideal:

                * revisar preço de venda;
                * verificar custo de aquisição;
                * revisar descontos;
                * revisar promoções;
                * conferir custo cadastrado;
                * conferir margem ideal;
                * identificar produtos que reduzem a margem;
                * revisar o mix vendido.

                Quando participação estiver abaixo da esperada:

                * verificar possíveis rupturas;
                * analisar preços;
                * revisar exposição;
                * conferir mix;
                * verificar disponibilidade;
                * revisar promoções;
                * verificar erros de cadastro;
                * identificar produtos que perderam venda.

                Quando devolução estiver elevada:

                * identificar produtos e fornecedores;
                * verificar qualidade e validade;
                * conferir divergências de pedido;
                * revisar recebimento;
                * revisar volume comprado;
                * acompanhar reincidências.

                Quando uso e consumo estiver elevado:

                * identificar produtos e setores;
                * revisar requisições internas;
                * conferir lançamentos;
                * estabelecer limites;
                * revisar fichas técnicas;
                * investigar desperdícios.

                Quando avaria estiver elevada:

                * identificar produtos responsáveis;
                * revisar validade;
                * revisar armazenamento;
                * revisar refrigeração;
                * revisar manuseio;
                * reduzir compras de itens de baixo giro;
                * antecipar promoções;
                * transferir produtos.

                Quando VL_EXCESSO_COMPR estiver elevado:

                * usar o valor como referência para revisar as próximas compras;
                * verificar estoque e giro antes de reduzir pedidos;
                * priorizar os produtos responsáveis;
                * revisar pedidos já emitidos;
                * revisar frequência;
                * negociar com fornecedores;
                * realizar ações de giro.

                Quando a saída estiver abaixo da meta esperada:

                * identificar os departamentos que mais contribuíram negativamente;
                * analisar participação abaixo da esperada;
                * verificar rupturas;
                * revisar preços e competitividade;
                * conferir disponibilidade dos itens de maior giro;
                * revisar mix e exposição;
                * planejar ações para o restante do mês;
                * considerar se ainda haverá a última semana para recuperação;
                * não recomendar promoções sem analisar MARGEM_WINTHOR.

                Quando a saída estiver acima da meta esperada:

                * identificar os departamentos responsáveis;
                * verificar se o crescimento ocorreu com MARGEM_WINTHOR saudável;
                * verificar se MARGEM permanece próxima da ideal;
                * conferir se o ritmo elevado está consumindo estoque sem reposição;
                * proteger a disponibilidade dos produtos de maior giro;
                * não aumentar compras automaticamente sem analisar estoque e giro.

                =========================================================
                FORMATO DA RESPOSTA
                ===================

                A resposta deve apresentar:

                1. RESUMO GERAL

                Mostre:

                * período analisado;
                * soma das entradas dos departamentos;
                * total de uso e consumo;
                * entrada total consolidada;
                * saída total;
                * saldo geral;
                * meta mensal, quando retornada;
                * percentual da meta realizado;
                * diferença em reais para a meta;
                * ritmo da venda conforme a parte do mês;
                * MARGEM;
                * MARGEM_IDEAL;
                * diferença de MARGEM;
                * MARGEM_WINTHOR;
                * diferença de MARGEM_WINTHOR;
                * participação;
                * custo;
                * resultado bruto;
                * devolução;
                * avaria;
                * excesso de compra.

                A conclusão do resumo deve priorizar:

                1. proximidade da MARGEM em relação à MARGEM_IDEAL;
                2. proximidade da MARGEM_WINTHOR em relação à MARGEM_IDEAL;
                3. desempenho da saída em relação à meta;
                4. sazonalidade da primeira, última ou semanas intermediárias;
                5. participação realizada comparada à esperada;
                6. saldo geral.

                Não dê mais destaque ao superávit de saída do que às margens e à meta.

                2. PRINCIPAIS PROBLEMAS

                Ordene por:

                * impacto financeiro;
                * gravidade percentual;
                * volume movimentado;
                * quantidade de indicadores problemáticos.

                3. ANÁLISE POR DEPARTAMENTO

                Mostre todos os departamentos e destaque os que exigem atenção.

                4. APROFUNDAMENTO

                Para os departamentos críticos, detalhe:

                * seções;
                * categorias;
                * produtos.

                5. RESPONSÁVEIS

                Informe o comprador responsável por cada departamento com problema relevante.

                6. POSSÍVEIS CAUSAS

                Apresente somente como hipóteses ou pontos de investigação.

                7. RECOMENDAÇÕES

                Dê orientações práticas e específicas para cada problema.

                8. PONTOS POSITIVOS

                Mostre registros com:

                * MARGEM próxima da ideal;
                * MARGEM_WINTHOR adequada;
                * participação satisfatória;
                * ritmo de venda favorável;
                * baixo excesso de compra;
                * baixa avaria;
                * baixa devolução;
                * uso e consumo controlado.

                =========================================================
                FORMATAÇÃO
                ==========

                Formate:

                * dinheiro: R$ 1.234,56;
                * percentual: 12,50%;
                * diferença entre percentuais: pontos percentuais.

                Destaque primeiro os problemas de maior impacto.

                Diferencie claramente:

                * fato retornado pela API;
                * cálculo realizado;
                * interpretação;
                * divergência;
                * hipótese;
                * indício;
                * risco;
                * recomendação.

                =========================================================
                REGRA FINAL OBRIGATÓRIA
                =======================

                Nunca utilize VL_USO_CONSUMO para aumentar ou diminuir o VALOR_TOTAL_ENTRADA individual de departamento, seção, categoria ou produto.

                Somente no consolidado geral calcule:

                VALOR_TOTAL_ENTRADA_CONSOLIDADA =
                SOMA DOS VALORES DE ENTRADA DOS DEPARTAMENTOS
                +
                SOMA DOS VALORES DE USO E CONSUMO

                O saldo geral deve ser apresentado, mas nunca deve ser utilizado isoladamente para afirmar que o desempenho foi bom ou ruim.

                A conclusão deve priorizar:

                * MARGEM comparada à MARGEM_IDEAL;
                * MARGEM_WINTHOR comparada à MARGEM_IDEAL;
                * saída comparada à meta mensal;
                * sazonalidade da primeira e última semana;
                * participação realizada comparada à esperada.

                Quando a meta mensal não for retornada, informe a limitação e não invente uma meta.

                Nunca invente:

                * valores;
                * códigos;
                * campos;
                * fórmulas;
                * metas;
                * causas;
                * departamentos;
                * seções;
                * categorias;
                * produtos;
                * responsáveis;
                * resultados.
                
                =========================================================
                MARGEM GERAL DE ENTRADA VERSUS SAÍDA
                ====================================

                No resumo geral, apresente obrigatoriamente a MARGEM consolidada de entrada versus saída.

                Essa MARGEM representa o resultado percentual da relação entre:

                * VALOR_TOTAL_SAIDA_TOTAL;
                * VALOR_TOTAL_ENTRADA_CONSOLIDADA.

                Calcule:

                MARGEM_GERAL =
                (
                (
                VALOR_TOTAL_SAIDA_TOTAL
                - VALOR_TOTAL_ENTRADA_CONSOLIDADA
                )
                / VALOR_TOTAL_SAIDA_TOTAL
                ) * 100

                Arredonde o resultado para duas casas decimais.

                Exemplo da forma de cálculo:

                MARGEM_GERAL =
                ROUND(
                (
                (
                VALOR_TOTAL_SAIDA_TOTAL
                - VALOR_TOTAL_ENTRADA_CONSOLIDADA
                )
                / VALOR_TOTAL_SAIDA_TOTAL
                ) * 100,
                2
                )

                Antes de calcular, confirme que VALOR_TOTAL_SAIDA_TOTAL é maior que zero.

                Caso VALOR_TOTAL_SAIDA_TOTAL seja igual a zero, não realize a divisão.

                Nesse caso, informe:

                “Não foi possível calcular a MARGEM geral porque o valor total de saída do período foi igual a zero.”

                Reforce que:

                VALOR_TOTAL_ENTRADA_CONSOLIDADA =
                SOMA DOS VALORES DE ENTRADA DOS DEPARTAMENTOS
                +
                SOMA DOS VALORES DE USO E CONSUMO

                A MARGEM geral já pode aparecer calculada no relatório geral.

                Quando a API retornar a MARGEM geral:

                * utilize o valor retornado;
                * apresente o resultado com duas casas decimais;
                * compare o valor retornado com a MARGEM_IDEAL;
                * não substitua o valor retornado por outro cálculo sem necessidade.

                O cálculo manual deve ser utilizado para:

                * validar o resultado retornado;
                * explicar de onde vem a MARGEM;
                * calcular o valor quando o relatório não o retornar;
                * identificar possível divergência.

                Caso o valor calculado seja diferente do valor retornado pela API:

                * apresente os dois valores;
                * informe que existe divergência;
                * não afirme automaticamente que a API está errada;
                * recomende verificar a fórmula e os arredondamentos utilizados no SQL.

                Calcule:

                DIFERENCA_MARGEM_GERAL =
                MARGEM_GERAL - MARGEM_IDEAL

                Apresente essa diferença em pontos percentuais.

                Exemplo:

                * MARGEM geral: 21,50%;
                * MARGEM ideal: 25,00%;
                * diferença: -3,50 pontos percentuais.

                =========================================================
                INTERPRETAÇÃO DA MARGEM GERAL
                =============================

                A análise da MARGEM geral deve receber mais importância do que o valor isolado do superávit entre saída e entrada.

                Uma saída superior à entrada pode gerar um saldo financeiro aparentemente favorável, mas a MARGEM ainda pode estar abaixo da MARGEM_IDEAL.

                MARGEM GERAL PRÓXIMA DA IDEAL:

                * indica relação aparentemente equilibrada entre entrada e saída;
                * sugere que o volume comprado está próximo do necessário para o volume vendido;
                * deve ser analisada junto com MARGEM_WINTHOR, participação, meta de venda, estoque e giro.

                MARGEM GERAL ABAIXO DA IDEAL:

                * pode indicar entrada acima do necessário;
                * pode indicar saída abaixo do esperado;
                * pode indicar excesso de compras;
                * pode indicar formação de estoque;
                * pode indicar produtos com estoque elevado e baixa movimentação;
                * exige aprofundamento por departamento, seção, categoria e produto.

                MARGEM GERAL ACIMA DA IDEAL:

                * pode indicar saída superior à reposição;
                * pode indicar consumo de estoque acumulado;
                * pode indicar compra abaixo da necessidade;
                * pode indicar possível risco de falta de reposição;
                * deve ser analisada com estoque, giro e disponibilidade.

                Não classifique automaticamente uma MARGEM acima da ideal como melhor.

                O objetivo gerencial é que a MARGEM esteja próxima da MARGEM_IDEAL, considerando o equilíbrio entre compras e vendas.

                =========================================================
                PRODUTOS QUE MAIS REDUZEM A MARGEM
                ==================================

                Quando um departamento estiver com MARGEM abaixo da MARGEM_IDEAL, aprofunde obrigatoriamente a análise até os produtos.

                O objetivo é identificar os produtos que mais contribuem para puxar a MARGEM do departamento para baixo.

                Para localizar esses produtos:

                1. Consulte todas as seções relevantes do departamento.
                2. Consulte as categorias das seções que apresentam os maiores problemas.
                3. Consulte os produtos das categorias identificadas.
                4. Analise os campos disponíveis de cada produto.
                5. Priorize os produtos que combinam os sinais mais relevantes de excesso.

                Dê foco principalmente aos produtos com:

                * VL_EXCESSO_COMPR mais negativo;
                * EST_FIC mais alto;
                * VALOR_TOTAL_ENTRADA elevado;
                * VALOR_TOTAL_SAIDA baixo em relação à entrada;
                * MARGEM abaixo da MARGEM_IDEAL, quando o campo estiver disponível;
                * baixa participação;
                * baixo giro, quando disponível;
                * avaria relevante;
                * devolução relevante.

                =========================================================
                INTERPRETAÇÃO DE VL_EXCESSO_COMPR
                =================================

                Para esta análise, valores mais negativos de VL_EXCESSO_COMPR representam maior necessidade de atenção.

                Quanto mais negativo for VL_EXCESSO_COMPR:

                * maior o indício de compra acima da necessidade;
                * maior o valor que deveria ter sido reduzido da entrada;
                * maior a possível contribuição negativa para a MARGEM;
                * maior a prioridade para investigação do produto.

                Exemplo de prioridade:

                * Produto A: VL_EXCESSO_COMPR = -R$ 20.000,00;
                * Produto B: VL_EXCESSO_COMPR = -R$ 5.000,00.

                O Produto A deve receber maior prioridade, desde que o restante dos indicadores também confirme o impacto.

                Não utilize apenas o sinal negativo isoladamente.

                Considere também:

                * volume financeiro;
                * EST_FIC;
                * entrada;
                * saída;
                * participação;
                * giro;
                * estoque atual;
                * avaria;
                * devolução;
                * sazonalidade;
                * pedidos pendentes.

                Quando VL_EXCESSO_COMPR estiver nulo, informe que o indicador não foi retornado para aquele produto.

                Nunca transforme um valor nulo em zero para classificar o produto como saudável.

                =========================================================
                INTERPRETAÇÃO DE EST_FIC
                ========================

                EST_FIC deve ser interpretado como um indicador de estoque ficto ou de possível estoque acumulado, conforme a regra de negócio do relatório.

                Quanto mais alto for EST_FIC:

                * maior o indício de mercadoria acumulada;
                * maior o possível excesso de estoque;
                * maior o capital possivelmente imobilizado;
                * maior a necessidade de verificar estoque atual, giro e movimentação;
                * maior a importância de analisar se as entradas estão acima das saídas.

                EST_FIC alto não confirma sozinho excesso real de estoque.

                Utilize expressões como:

                * indício de excesso de estoque;
                * possível estoque acumulado;
                * possível capital imobilizado;
                * produto que precisa ser verificado no estoque físico e no giro.

                Cruze EST_FIC com:

                * VL_EXCESSO_COMPR;
                * VALOR_TOTAL_ENTRADA;
                * VALOR_TOTAL_SAIDA;
                * MARGEM;
                * MARGEM_IDEAL;
                * estoque atual;
                * giro;
                * avaria;
                * devolução;
                * validade;
                * pedidos pendentes.

                A combinação de maior atenção é:

                * VL_EXCESSO_COMPR muito negativo;
                * EST_FIC alto;
                * entrada elevada;
                * saída baixa;
                * participação abaixo da esperada.

                Essa combinação representa forte indício de excesso de compra ou estoque acumulado, mas ainda deve ser confirmada com estoque atual e giro.

                =========================================================
                REFERÊNCIA HIERÁRQUICA DOS PRODUTOS
                ===================================

                Sempre que apresentar um produto responsável por reduzir a MARGEM, informe toda a sua hierarquia.

                Apresente:

                * CODEPTO;
                * DEPARTAMENTO;
                * CODSEC;
                * SECAO;
                * CODCATEGORIA;
                * CATEGORIA;
                * CODPROD;
                * PRODUTO.

                Formato recomendado:

                DEPARTAMENTO:
                [CODEPTO] — [DEPARTAMENTO]

                SEÇÃO:
                [CODSEC] — [SECAO]

                CATEGORIA:
                [CODCATEGORIA] — [CATEGORIA]

                PRODUTO:
                [CODPROD] — [PRODUTO]

                Nunca apresente um produto isoladamente sem informar a qual departamento, seção e categoria ele pertence.

                Para cada produto crítico, apresente, quando disponível:

                * VALOR_TOTAL_ENTRADA;
                * VALOR_TOTAL_SAIDA;
                * diferença entre entrada e saída;
                * MARGEM;
                * MARGEM_IDEAL;
                * diferença de MARGEM;
                * MARGEM_WINTHOR;
                * diferença de MARGEM_WINTHOR;
                * VL_EXCESSO_COMPR;
                * EST_FIC;
                * participação;
                * custo;
                * resultado bruto;
                * avaria;
                * devolução;
                * uso e consumo.

                Explique objetivamente por que o produto está puxando a MARGEM para baixo.

                =========================================================
                RANKING DOS PRODUTOS QUE MAIS PREJUDICAM A MARGEM
                =================================================

                Nos departamentos com MARGEM baixa, apresente um ranking dos produtos prioritários.

                O ranking deve considerar em conjunto:

                1. VL_EXCESSO_COMPR mais negativo;
                2. EST_FIC mais alto;
                3. diferença entre entrada e saída;
                4. volume financeiro;
                5. participação abaixo da esperada;
                6. MARGEM abaixo da ideal;
                7. MARGEM_WINTHOR abaixo da ideal;
                8. avaria;
                9. devolução;
                10. quantidade de indicadores problemáticos.

                Não escolha o pior produto usando somente um indicador.

                Um produto com VL_EXCESSO_COMPR muito negativo, mas com pequeno volume financeiro, pode ter impacto menor que um produto com diferença moderada e alto volume.

                Informe que o ranking foi criado pela combinação dos indicadores analisados.

                Não apresente o ranking como absoluto quando não existir uma pontuação única definida pelo sistema.

                =========================================================
                SEÇÕES COM PARTICIPAÇÃO ABAIXO DA IDEAL
                =======================================

                Apresente as seções cuja participação realizada esteja mais abaixo da participação ideal ou esperada.

                Para cada seção, informe obrigatoriamente o departamento ao qual ela pertence.

                Apresente:

                * CODEPTO;
                * DEPARTAMENTO;
                * CODSEC;
                * SECAO;
                * PARTICIPACAO_REAL;
                * PARTICIPACAO_ESPERADA;
                * DIFERENCA_PARTICIPACAO;
                * VALOR_TOTAL_SAIDA;
                * MARGEM;
                * MARGEM_IDEAL;
                * MARGEM_WINTHOR;
                * principais categorias responsáveis;
                * possíveis causas;
                * recomendações.

                Calcule:

                DIFERENCA_PARTICIPACAO =
                PARTICIPACAO_REAL - PARTICIPACAO_ESPERADA

                Quanto mais negativa for DIFERENCA_PARTICIPACAO:

                * maior a distância da participação esperada;
                * maior o espaço potencial para crescimento das vendas;
                * maior a necessidade de investigar preço, ruptura, mix, exposição e disponibilidade.

                Exemplo:

                * participação realizada: 3,00%;
                * participação esperada: 5,00%;
                * diferença: -2,00 pontos percentuais.

                Isso significa que a seção está 2,00 pontos percentuais abaixo da participação esperada.

                Não significa automaticamente que toda essa diferença pode ser recuperada imediatamente.

                =========================================================
                CATEGORIAS COM PARTICIPAÇÃO ABAIXO DA IDEAL
                ===========================================

                Apresente também as categorias cuja participação realizada esteja mais abaixo da participação ideal ou esperada.

                Para cada categoria, informe toda a hierarquia:

                * CODEPTO;
                * DEPARTAMENTO;
                * CODSEC;
                * SECAO;
                * CODCATEGORIA;
                * CATEGORIA;
                * PARTICIPACAO_REAL;
                * PARTICIPACAO_ESPERADA;
                * DIFERENCA_PARTICIPACAO;
                * VALOR_TOTAL_SAIDA;
                * MARGEM;
                * MARGEM_IDEAL;
                * MARGEM_WINTHOR;
                * principais produtos responsáveis;
                * possíveis causas;
                * recomendações.

                Nunca apresente uma categoria sem informar seu departamento e sua seção.

                Ordene prioritariamente pelas maiores diferenças negativas de participação.

                Considere também o volume financeiro.

                Uma categoria pequena com diferença percentual elevada pode ter impacto menor do que uma categoria grande com diferença moderada.

                =========================================================
                INTERPRETAÇÃO DA PARTICIPAÇÃO ABAIXO DA IDEAL
                =============================================

                Se uma seção ou categoria estiver abaixo da participação esperada, existe espaço potencial para melhorar as vendas.

                Analise como possíveis fatores:

                * ruptura;
                * reposição insuficiente;
                * produtos importantes sem estoque;
                * preço acima do mercado;
                * MARGEM_WINTHOR inadequada;
                * mix incompleto;
                * exposição insuficiente;
                * falta de promoção;
                * baixa competitividade;
                * redução do giro;
                * sazonalidade;
                * erro de cadastro;
                * produtos classificados na seção ou categoria errada;
                * baixa disponibilidade;
                * perda de venda para produtos substitutos;
                * redução da procura dos clientes.

                Apresente essas situações como possibilidades de investigação.

                Não afirme que a causa foi ruptura, preço ou exposição sem dados que confirmem isso.

                Cruze a participação com:

                * entrada;
                * saída;
                * MARGEM;
                * MARGEM_WINTHOR;
                * MARGEM_IDEAL;
                * VL_EXCESSO_COMPR;
                * EST_FIC;
                * estoque;
                * giro;
                * avaria;
                * devolução.

                PARTICIPAÇÃO ABAIXO + EST_FIC ALTO:

                * pode existir mercadoria disponível, mas com baixa saída;
                * pode existir problema de preço, mix ou exposição;
                * pode existir excesso de estoque com baixa demanda.

                PARTICIPAÇÃO ABAIXO + EST_FIC BAIXO:

                * pode existir falta de estoque;
                * pode existir ruptura;
                * pode existir reposição insuficiente.

                PARTICIPAÇÃO ABAIXO + MARGEM_WINTHOR RUIM:

                * pode existir precificação inadequada;
                * descontos ou custos podem estar afetando o desempenho;
                * produtos de baixa margem podem estar limitando ações comerciais.

                PARTICIPAÇÃO ABAIXO + VL_EXCESSO_COMPR MUITO NEGATIVO:

                * pode existir compra acima da necessidade;
                * pode existir saída abaixo do planejado;
                * pode existir estoque acumulado;
                * deve-se identificar os produtos responsáveis.

                =========================================================
                ORDEM DO APROFUNDAMENTO
                =======================

                Quando um departamento estiver com MARGEM abaixo da MARGEM_IDEAL:

                1. Consulte suas seções.
                2. Identifique as seções com:

                * menor MARGEM;
                * maior diferença negativa de participação;
                * maior excesso de compra;
                * maior impacto financeiro.
                3. Consulte as categorias dessas seções.
                4. Identifique as categorias com:

                * menor MARGEM;
                * participação mais abaixo da ideal;
                * VL_EXCESSO_COMPR mais negativo;
                * EST_FIC mais alto;
                * maior impacto financeiro.
                5. Consulte os produtos dessas categorias.
                6. Identifique os produtos com:

                * VL_EXCESSO_COMPR mais negativo;
                * EST_FIC mais alto;
                * entrada elevada;
                * saída insuficiente;
                * baixa participação;
                * margem inadequada.
                7. Explique como esses produtos contribuem para o resultado do departamento.
                8. Apresente recomendações específicas.

                Não interrompa o aprofundamento na seção ou na categoria quando os produtos forem necessários para explicar a causa do resultado.

                =========================================================
                ACRÉSCIMO AO RESUMO GERAL
                =========================

                No RESUMO GERAL, apresente obrigatoriamente:

                * VALOR_TOTAL_SAIDA_TOTAL;
                * SOMA_ENTRADA_DEPARTAMENTOS;
                * TOTAL_USO_CONSUMO;
                * VALOR_TOTAL_ENTRADA_CONSOLIDADA;
                * SALDO_GERAL_MOVIMENTACAO;
                * MARGEM_GERAL;
                * MARGEM_IDEAL;
                * DIFERENCA_MARGEM_GERAL;
                * MARGEM_WINTHOR consolidada;
                * diferença entre MARGEM_WINTHOR e MARGEM_IDEAL;
                * meta mensal de venda, quando retornada;
                * percentual da meta realizado;
                * participação;
                * custo;
                * resultado bruto;
                * devolução;
                * avaria;
                * excesso de compra.

                Apresente a fórmula utilizada:

                MARGEM_GERAL =
                (
                (
                VALOR_TOTAL_SAIDA_TOTAL
                - VALOR_TOTAL_ENTRADA_CONSOLIDADA
                )
                / VALOR_TOTAL_SAIDA_TOTAL
                ) * 100

                Arredonde o resultado para duas casas decimais.

                A conclusão principal deve informar:

                * se MARGEM_GERAL está próxima da MARGEM_IDEAL;
                * o que essa diferença representa;
                * se MARGEM_WINTHOR está próxima da MARGEM_IDEAL;
                * o que o resultado da precificação representa;
                * se a saída está adequada à meta mensal;
                * quais departamentos estão puxando a MARGEM para baixo;
                * quais produtos são os principais responsáveis;
                * quais seções e categorias possuem maior espaço para melhorar as vendas.

                =========================================================
                ACRÉSCIMO AO FORMATO DO RELATÓRIO
                =================================

                Inclua as seguintes partes no relatório:

                1. RESUMO GERAL

                * entrada consolidada;
                * saída consolidada;
                * saldo geral;
                * MARGEM_GERAL calculada;
                * MARGEM_IDEAL;
                * diferença em pontos percentuais;
                * MARGEM_WINTHOR;
                * situação da meta mensal;
                * interpretação principal.

                2. DEPARTAMENTOS COM MARGEM BAIXA

                Para cada departamento:

                * dados gerais;
                * diferença para a MARGEM_IDEAL;
                * comprador responsável;
                * seções e categorias responsáveis;
                * produtos que mais reduzem a MARGEM.

                3. PRODUTOS COM MAIOR INDÍCIO DE EXCESSO

                Priorize:

                * VL_EXCESSO_COMPR mais negativo;
                * EST_FIC mais alto;
                * maior impacto financeiro.

                Sempre apresente:

                Departamento → Seção → Categoria → Produto

                4. SEÇÕES ABAIXO DA PARTICIPAÇÃO IDEAL

                Apresente:

                Departamento → Seção

                Mostre:

                * participação realizada;
                * participação esperada;
                * diferença em pontos percentuais;
                * principais categorias responsáveis;
                * recomendações.

                5. CATEGORIAS ABAIXO DA PARTICIPAÇÃO IDEAL

                Apresente:

                Departamento → Seção → Categoria

                Mostre:

                * participação realizada;
                * participação esperada;
                * diferença em pontos percentuais;
                * produtos responsáveis;
                * recomendações.

                6. RECOMENDAÇÕES PRIORITÁRIAS

                Separe as recomendações em:

                * ajuste de compras;
                * ações para melhorar vendas;
                * revisão de preços e custos;
                * redução de estoque acumulado;
                * prevenção de ruptura;
                * revisão de mix;
                * ações promocionais;
                * transferências entre filiais;
                * investigação de avaria, devolução e uso e consumo.

                =========================================================
                REGRA FINAL DESTA ATUALIZAÇÃO
                =============================

                No resultado geral, sempre calcule ou apresente:

                MARGEM_GERAL =
                ROUND(
                (
                (
                VALOR_TOTAL_SAIDA_TOTAL
                - VALOR_TOTAL_ENTRADA_CONSOLIDADA
                )
                / VALOR_TOTAL_SAIDA_TOTAL
                ) * 100,
                2
                )

                Nos departamentos com MARGEM baixa, aprofunde até os produtos.

                Priorize os produtos com:

                * VL_EXCESSO_COMPR mais negativo;
                * EST_FIC mais alto;
                * maior impacto financeiro;
                * entrada alta e saída baixa.

                Sempre referencie:

                Departamento → Seção → Categoria → Produto

                Apresente também as seções e categorias com participação mais abaixo da participação esperada.

                Sempre referencie:

                Departamento → Seção

                e:

                Departamento → Seção → Categoria

                Não apresente seções, categorias ou produtos sem sua hierarquia.

                Nunca invente:

                * VL_EXCESSO_COMPR;
                * EST_FIC;
                * participação;
                * margem;
                * códigos;
                * produtos;
                * causas;
                * fórmulas;
                * valores.
                
                =========================================================
                REGRA OBRIGATÓRIA PARA BUSCAR A META MENSAL
                ===========================================

                Sempre que esta ferramenta for utilizada para produzir um relatório ou análise de entrada e saída, também utilize a ferramenta:

                consultar_vendas

                A ferramenta consultar_vendas deve ser chamada antes da resposta final para obter a meta mensal cadastrada.

                Não espere que a meta mensal seja retornada por entrada_saida_departamento.

                A meta deve ser buscada na ferramenta consultar_vendas, no campo:

                META

                =========================================================
                PERÍODO UTILIZADO PARA BUSCAR A META
                ====================================

                A consulta de entrada e saída deve continuar utilizando exatamente o período solicitado pelo usuário.

                Exemplo:

                Se o usuário solicitar:

                01-JUL-2026 até 10-JUL-2026

                consulte entrada_saida_departamento utilizando:

                data_inicio = 01-JUL-2026
                data_fim = 10-JUL-2026

                Entretanto, para buscar a META na ferramenta consultar_vendas, utilize sempre o mês completo correspondente ao período informado.

                Ignore o dia informado pelo usuário para definir o período da consulta da meta.

                Utilize:

                data_inicio_meta =
                primeiro dia do mês informado

                data_fim_meta =
                último dia do mês informado

                Exemplo:

                Período solicitado pelo usuário:

                01-JUL-2026 até 10-JUL-2026

                Consulta de entrada e saída:

                entrada_saida_departamento(
                data_inicio = "01-JUL-2026",
                data_fim = "10-JUL-2026"
                )

                Consulta obrigatória da meta:

                consultar_vendas(
                data_inicio = "01-JUL-2026",
                data_fim = "31-JUL-2026"
                )

                Outro exemplo:

                Período solicitado pelo usuário:

                10-FEB-2026 até 20-FEB-2026

                Consulta obrigatória da meta:

                consultar_vendas(
                data_inicio = "01-FEB-2026",
                data_fim = "28-FEB-2026"
                )

                Considere corretamente anos bissextos.

                Exemplo:

                Para fevereiro de 2028, utilize:

                01-FEB-2028 até 29-FEB-2028

                =========================================================
                PERÍODO COM MAIS DE UM MÊS
                ==========================

                Quando o período solicitado pelo usuário abranger mais de um mês, consulte consultar_vendas separadamente para cada mês completo.

                Exemplo:

                Período solicitado:

                20-JUL-2026 até 10-AUG-2026

                Realize:

                consultar_vendas(
                data_inicio = "01-JUL-2026",
                data_fim = "31-JUL-2026"
                )

                e:

                consultar_vendas(
                data_inicio = "01-AUG-2026",
                data_fim = "31-AUG-2026"
                )

                Analise a meta e o desempenho de cada mês separadamente.

                Não some metas de meses diferentes para apresentar um único atingimento, salvo quando o usuário solicitar expressamente uma análise consolidada de vários meses.

                =========================================================
                COMO EXTRAIR A META
                ===================

                A ferramenta consultar_vendas retorna registros por filial e departamento.

                O campo META representa a meta total da filial para o mês consultado.

                A mesma META pode aparecer repetida em todos os departamentos da mesma filial.

                Portanto:

                1. Agrupe os registros de consultar_vendas por CODFILIAL.
                2. Pegue META somente uma vez para cada CODFILIAL.
                3. Nunca some META entre departamentos da mesma filial.
                4. Some apenas as metas únicas das filiais.

                Calcule:

                META_TOTAL_EMPRESA =
                soma das metas únicas por CODFILIAL

                Não faça:

                META_TOTAL_EMPRESA =
                soma de todas as ocorrências do campo META

                Isso causaria duplicidade porque a mesma meta pode aparecer repetida nos departamentos.

                =========================================================
                DADOS QUE DEVEM SER COMPARADOS
                ==============================

                Para a análise solicitada, utilize:

                VALOR_TOTAL_SAIDA_TOTAL =
                soma das saídas retornadas por entrada_saida_departamento no período solicitado pelo usuário

                META_TOTAL_EMPRESA =
                soma das metas mensais únicas por filial retornadas por consultar_vendas para o mês completo

                Não substitua VALOR_TOTAL_SAIDA_TOTAL pelo campo VENDA da consulta mensal sem explicar a diferença.

                A ferramenta consultar_vendas deve fornecer principalmente:

                * META;
                * identificação das filiais;
                * informações complementares de venda do mês, quando forem úteis.

                A saída utilizada na análise principal deve continuar sendo a saída retornada por entrada_saida_departamento para o período solicitado.

                =========================================================
                CÁLCULO DO ATINGIMENTO
                ======================

                Quando META_TOTAL_EMPRESA for maior que zero, calcule:

                PERCENTUAL_META_REALIZADA =
                (
                VALOR_TOTAL_SAIDA_TOTAL
                / META_TOTAL_EMPRESA
                ) * 100

                Arredonde para duas casas decimais.

                Calcule:

                VALOR_FALTANTE_META =
                META_TOTAL_EMPRESA - VALOR_TOTAL_SAIDA_TOTAL

                Quando VALOR_FALTANTE_META for positivo:

                * a saída do período ainda está abaixo da meta mensal;
                * informe quanto falta em reais;
                * analise a quantidade de dias do período;
                * considere se o período pertence à primeira, última ou semanas intermediárias do mês.

                Quando VALOR_FALTANTE_META for igual ou negativo:

                * o valor de saída analisado já alcançou ou superou a meta mensal;
                * informe em quanto a meta foi superada;
                * ainda analise MARGEM e MARGEM_WINTHOR;
                * atingir a meta não significa automaticamente que a rentabilidade está adequada.

                =========================================================
                ORDEM OBRIGATÓRIA DAS CONSULTAS
                ===============================

                Para um relatório de entrada e saída com análise de meta:

                1. Consulte entrada_saida_departamento com o período exato solicitado.
                2. Identifique o mês e o ano do período.
                3. Determine o primeiro e o último dia desse mês.
                4. Consulte consultar_vendas utilizando o mês completo.
                5. Extraia META uma única vez por CODFILIAL.
                6. Some as metas únicas para encontrar META_TOTAL_EMPRESA.
                7. Compare a saída do período solicitado com a meta mensal.
                8. Considere a posição do período dentro do mês.
                9. Analise MARGEM e MARGEM_WINTHOR em relação à MARGEM_IDEAL.
                10. Somente depois produza a resposta final.

                Não produza o relatório final de entrada e saída sem consultar a meta mensal em consultar_vendas.

                Caso consultar_vendas apresente erro ou não retorne META:

                * informe claramente a limitação;
                * continue a análise dos demais indicadores;
                * não invente a meta;
                * não classifique o atingimento como favorável ou desfavorável sem a meta.
                =========================================================
                APROFUNDAMENTO OBRIGATÓRIO DE ENTRADA E SAÍDA
                =============================================

                Quando o usuário solicitar relatório, análise completa, análise gerencial, principais problemas, recomendações ou “uma análise sua” de entrada e saída, não encerre a resposta no nível de departamento.

                Depois de consultar os departamentos:

                1. Identifique prioritariamente os três departamentos mais críticos.
                2. Consulte as seções de cada departamento crítico usando CODEPTO.
                3. Identifique prioritariamente até três seções críticas por departamento.
                4. Consulte as categorias dessas seções usando CODEPTO e CODSEC.
                5. Identifique prioritariamente até três categorias críticas por seção.
                6. Consulte obrigatoriamente os produtos dessas categorias usando CODEPTO, CODSEC e CODCATEGORIA.
                7. Analise TOTAL_QT_ENTRADA, TOTAL_QT_SAIDA, EST_FIC e VL_EXCESSO_COMPR no nível de produto.
                8. Apresente os produtos com VL_EXCESSO_COMPR mais negativo e EST_FIC mais alto.
                9. Apresente sempre a hierarquia Departamento → Seção → Categoria → Produto.
                10. Somente depois produza a resposta final.

                VL_EXCESSO_COMPR e EST_FIC podem não aparecer no nível de departamento, seção ou categoria.

                A ausência desses campos nos níveis superiores não significa que eles não foram retornados pela consulta completa.

                É proibido dizer que VL_EXCESSO_COMPR ou EST_FIC não foram retornados sem antes consultar os produtos das categorias críticas.

                É proibido terminar com frases como:

                * “Posso fazer esse detalhamento se você quiser”;
                * “É necessário pedir o detalhamento”;
                * “Os dados retornaram apenas no nível de departamento”.

                O aprofundamento já faz parte do relatório solicitado pelo usuário.


                """,

            "parameters": {
                "type": "object",
                "properties": {
                    "data_inicio": {
                        "type": "string",
                        "description": (
                            "Data inicial no formato DD-MON-YYYY. "
                            "Exemplo: 01-JUL-2026."
                        ),
                    },
                    "data_fim": {
                        "type": "string",
                        "description": (
                            "Data final no formato DD-MON-YYYY. "
                            "Exemplo: 10-JUL-2026."
                        ),
                    },
                    "codepto": {
                        "type": "integer",
                        "description": (
                            "Código do departamento. Quando enviado com "
                            "as datas, consulta as seções do departamento."
                        ),
                    },
                    "codsec": {
                        "type": "integer",
                        "description": (
                            "Código da seção. Requer codepto. Quando enviado "
                            "com codepto e as datas, consulta as categorias."
                        ),
                    },
                    "codcategoria": {
                        "type": "integer",
                        "description": (
                            "Código da categoria. Requer codepto e codsec. "
                            "Consulta os produtos da categoria."
                        ),
                    },
                },
                "required": [
                    "data_inicio",
                    "data_fim",
                ],
                "additionalProperties": False,
            },
        },
    },
    # =========================================================
    # TOOL 4 — TOP PRODUTOS VENDIDO
    # =========================================================
    {
        "type": "function",
        "function": {
            "name": "ranking_produtos_vendidos",
            "description": """
            Consulta o ranking dos produtos mais ou menos vendidos
            em determinado período.

            Use quando o usuário pedir:

            - produtos mais vendidos;
            - produtos menos vendidos;
            - ranking de produtos;
            - top produtos;
            - produtos com maior venda;
            - produtos com menor venda.

            Para produtos mais vendidos, utilize tipo igual a MAIS.

            Para produtos menos vendidos, utilize tipo igual a MENOS.

            Quando o usuário não informar a quantidade, utilize top igual a 10.
        """,
            "parameters": {
                "type": "object",
                "properties": {
                    "data_inicio": {
                        "type": "string",
                        "description": ("Data inicial no formato DD-MON-YYYY."),
                    },
                    "data_fim": {
                        "type": "string",
                        "description": ("Data final no formato DD-MON-YYYY."),
                    },
                    "top": {
                        "type": "integer",
                        "description": (
                            "Quantidade de produtos no ranking. Exemplo: 10."
                        ),
                    },
                    "tipo": {
                        "type": "string",
                        "enum": ["MAIS", "MENOS"],
                        "description": (
                            "MAIS retorna os produtos com maior venda. "
                            "MENOS retorna os produtos com menor venda."
                        ),
                    },
                },
                "required": [
                    "data_inicio",
                    "data_fim",
                    "top",
                    "tipo",
                ],
                "additionalProperties": False,
            },
        },
    },
    # =========================================================
    # TOOL 4 — TOP PRODUTOS VENDIDO
    # =========================================================
    {
        "type": "function",
        "function": {
            "name": "registrar_sugestao",
            "description": """
                Registra uma sugestão explícita de melhoria feita pelo usuário.

                Use somente quando o usuário demonstrar intenção de sugerir,
                criar, adicionar ou melhorar alguma funcionalidade.

                Exemplos:

                - "Tenho uma sugestão"
                - "Adicione uma função para gerar balancete"
                - "Seria bom criar um relatório financeiro"
                - "Melhore a consulta de estoque"
                - "Crie uma funcionalidade nova"

                Não use esta ferramenta quando o usuário estiver apenas tentando
                consultar uma informação que ainda não está disponível.

                Exemplo que NÃO deve chamar esta ferramenta:

                - "Quais contas tenho para pagar hoje?"
                - "Mostre minhas contas a receber"
                - "Consulte meus fornecedores"

                Nesses casos, a solicitação deve ser tratada como demanda não
                atendida, e não como sugestão.
            """,
            "parameters": {
                "type": "object",
                "properties": {
                    "pergunta": {
                        "type": "string",
                        "description": (
                            "Pergunta ou sugestão original feita pelo usuário."
                        ),
                    },
                },
                "required": [
                    "pergunta",
                ],
                "additionalProperties": False,
            },
        },
    },
    # =========================================================
    # TOOL 5 - Limite de comrpa 
    # =========================================================
    {
        "type": "function",
        "function": {
            "name": "limite_comprador",
          "description": """
                Consulta e realiza uma análise crítica do limite mensal de compras,
                tanto no consolidado geral da empresa quanto individualmente para
                cada comprador.

                =========================================================
                CONTEXTO DO LIMITE
                =========================================================

                Cada comprador possui departamentos sob sua responsabilidade e um
                limite financeiro mensal para realizar compras destinadas a esses
                departamentos.

                O limite deve permitir a reposição adequada das mercadorias sem que
                as compras sejam concentradas de forma irresponsável em poucos dias
                ou ultrapassem a capacidade financeira definida para o mês.

                Use esta ferramenta quando o usuário perguntar sobre:

                - limite dos compradores;
                - limite geral da empresa;
                - saldo disponível;
                - valor gasto;
                - percentual do limite utilizado;
                - compradores próximos de estourar o limite;
                - possibilidade de o limite ser excedido;
                - ritmo das compras durante o mês;
                - pedidos entregues;
                - pedidos ainda não entregues;
                - concentração de compras;
                - adequação do limite à meta;
                - adequação do limite à venda esperada;
                - compradores com utilização irresponsável;
                - compradores com limite muito alto ou muito baixo;
                - necessidade de aumentar ou reduzir o limite.

                A ferramenta retorna registros por comprador.

                Os registros podem conter:

                - DATAINICIAL
                - DATAFINAL
                - CODFILIAL
                - CODCOMPRADOR
                - NOME
                - VALOR_ENTREGUE
                - VALOR_NAO_ENTREGUE
                - TOTAL_VALORLIMITE
                - VLRGASTO
                - VLRSALDO

                =========================================================
                INTERPRETAÇÃO DOS CAMPOS
                =========================================================

                TOTAL_VALORLIMITE:

                Representa o valor máximo definido para o comprador realizar
                compras no mês pesquisado.

                VALOR_ENTREGUE:

                Representa o valor das compras realizadas no mês cujas mercadorias
                já foram entregues.

                VALOR_NAO_ENTREGUE:

                Representa o valor das compras ou pedidos realizados cujas
                mercadorias ainda não foram entregues.

                Esses pedidos já podem representar um compromisso financeiro e
                precisam ser considerados na avaliação do risco, mesmo que as
                mercadorias ainda não tenham chegado.

                VLRGASTO:

                Representa o valor do limite já utilizado em pedidos.

                Em regra, esse valor deve considerar pedidos entregues e não
                entregues.

                Utilize VLRGASTO como valor oficial consumido do limite.

                VLRSALDO:

                Representa quanto ainda está disponível para o comprador realizar
                novas compras no mês.

                CODFILIAL:

                Quando for nulo, considere que o registro está consolidado e não
                associado a uma filial específica.

                Nunca trate CODFILIAL nulo como filial zero.

                =========================================================
                VALIDAÇÃO DOS VALORES
                =========================================================

                Sempre valide:

                SALDO_CALCULADO =
                TOTAL_VALORLIMITE - VLRGASTO

                Compare SALDO_CALCULADO com VLRSALDO.

                Calcule também:

                GASTO_OPERACIONAL_CALCULADO =
                VALOR_ENTREGUE + VALOR_NAO_ENTREGUE

                Compare GASTO_OPERACIONAL_CALCULADO com VLRGASTO.

                Quando houver diferença relevante:

                - apresente os valores retornados;
                - apresente o valor calculado;
                - mostre a diferença;
                - informe que existe uma divergência entre os indicadores;
                - não afirme que o SQL ou a API estão errados;
                - não invente a causa da diferença.

                Para a análise do limite, continue utilizando VLRGASTO como valor
                oficial consumido, salvo quando outra regra explícita for fornecida.

                =========================================================
                PERCENTUAL UTILIZADO
                =========================================================

                Quando TOTAL_VALORLIMITE for maior que zero, calcule:

                PERCENTUAL_UTILIZADO =
                (VLRGASTO / TOTAL_VALORLIMITE) * 100

                Calcule também:

                PERCENTUAL_DISPONIVEL =
                (VLRSALDO / TOTAL_VALORLIMITE) * 100

                Não faça média simples dos percentuais dos compradores para calcular
                o percentual geral da empresa.

                =========================================================
                ANÁLISE GERAL DA EMPRESA
                =========================================================

                Para realizar a análise consolidada, calcule:

                LIMITE_TOTAL_GERAL =
                soma de TOTAL_VALORLIMITE de todos os compradores

                GASTO_TOTAL_GERAL =
                soma de VLRGASTO de todos os compradores

                SALDO_TOTAL_GERAL =
                soma de VLRSALDO de todos os compradores

                ENTREGUE_TOTAL_GERAL =
                soma de VALOR_ENTREGUE de todos os compradores

                NAO_ENTREGUE_TOTAL_GERAL =
                soma de VALOR_NAO_ENTREGUE de todos os compradores

                Quando LIMITE_TOTAL_GERAL for maior que zero, calcule:

                PERCENTUAL_UTILIZADO_GERAL =
                (GASTO_TOTAL_GERAL / LIMITE_TOTAL_GERAL) * 100

                Analise criticamente:

                - quanto do limite geral já foi utilizado;
                - quanto ainda está disponível;
                - se o ritmo atual indica possibilidade de estouro;
                - quanto do gasto ainda está pendente de entrega;
                - se as compras estão concentradas em poucos compradores;
                - quais compradores representam maior risco;
                - se existe saldo suficiente para o restante do mês;
                - se o limite geral parece adequado à venda esperada.

                =========================================================
                ANÁLISE POR COMPRADOR
                =========================================================

                Para cada comprador, apresente e analise:

                - nome e código;
                - limite total;
                - valor gasto;
                - saldo disponível;
                - percentual utilizado;
                - percentual disponível;
                - valor entregue;
                - valor não entregue;
                - percentual ainda não entregue;
                - ritmo de utilização;
                - risco de estourar o limite;
                - possíveis divergências nos valores;
                - recomendação baseada nos dados.

                Não classifique um comprador apenas pelo maior valor gasto.

                Um comprador pode gastar mais em valores absolutos por possuir
                departamentos com maior volume de venda e um limite proporcionalmente
                maior.

                Avalie principalmente o percentual utilizado, o saldo restante, a
                fase atual do mês, o valor não entregue e a responsabilidade dos
                departamentos do comprador.

                =========================================================
                RITMO DE UTILIZAÇÃO NO MÊS
                =========================================================

                Considere que as semanas de maior movimento de venda normalmente são:

                - a primeira semana do mês;
                - a última semana do mês.

                As compras destinadas a atender uma semana de maior movimento devem,
                preferencialmente, ser realizadas com antecedência suficiente para que
                as mercadorias cheguem antes do aumento das vendas.

                Portanto:

                - mercadorias para a primeira semana podem precisar ser compradas na
                última semana do mês anterior;
                - mercadorias para a última semana devem ser compradas principalmente
                durante a terceira semana do mês;
                - gastar grande parte do limite logo no início pode deixar o comprador
                sem capacidade para reposições posteriores;
                - gastar pouco antes da última semana pode indicar risco de reposição
                insuficiente;
                - gastar todo o limite de uma única vez não representa, isoladamente,
                uma utilização responsável.

                Quando a data atual estiver dentro do período consultado, calcule:

                PERCENTUAL_TEMPO_DECORRIDO =
                dias decorridos no período / total de dias do período * 100

                Calcule:

                DESVIO_DO_RITMO =
                PERCENTUAL_UTILIZADO - PERCENTUAL_TEMPO_DECORRIDO

                Utilize esse cálculo somente como indicador de ritmo.

                Não conclua automaticamente que existe excesso quando o percentual
                utilizado estiver acima do percentual de tempo, pois as compras podem
                precisar anteceder as semanas de maior venda.

                Avalie se a antecipação faz sentido para preparar:

                - a primeira semana;
                - a última semana;
                - o prazo de entrega dos fornecedores;
                - o volume esperado de venda.

                Quando não houver datas individuais dos pedidos, não afirme que as
                compras foram feitas todas de uma vez.

                Informe apenas que o valor acumulado indica possível concentração ou
                aceleração das compras.

                =========================================================
                PROJEÇÃO DE ESTOURO
                =========================================================

                Quando o mês ainda estiver em andamento e existirem dias decorridos,
                pode calcular uma projeção linear indicativa:

                PROJECAO_GASTO_MENSAL =
                VLRGASTO / percentual decimal do tempo decorrido

                PROJECAO_UTILIZACAO =
                (PROJECAO_GASTO_MENSAL / TOTAL_VALORLIMITE) * 100

                A projeção linear é apenas um alerta preliminar.

                Nunca use essa projeção isoladamente como previsão definitiva, pois
                as vendas e compras não são distribuídas igualmente durante o mês.

                Considere também:

                - primeira e última semana com maior movimento;
                - pedidos ainda não entregues;
                - compras necessárias antes dos períodos de pico;
                - saldo restante;
                - venda esperada;
                - histórico, quando disponível.

                Classifique o risco:

                LIMITE EXCEDIDO:

                - VLRGASTO maior que TOTAL_VALORLIMITE;
                - ou VLRSALDO negativo;
                - ou percentual utilizado maior que 100%.

                RISCO CRÍTICO:

                - percentual utilizado igual ou superior a 90% com o mês ainda em
                andamento;
                - projeção indicando gasto acima do limite;
                - saldo insuficiente para uma semana de maior movimento;
                - grande volume não entregue próximo de uma semana de pico.

                RISCO ALTO:

                - percentual utilizado acima de 80%;
                - ritmo de gasto muito acima do tempo decorrido sem justificativa
                aparente;
                - projeção próxima ou superior a 100%;
                - compras muito concentradas no começo do mês.

                ATENÇÃO:

                - percentual utilizado entre 70% e 80%;
                - valor não entregue elevado;
                - saldo que pode ser insuficiente para o restante do mês;
                - ritmo acima do esperado, mas ainda controlável.

                SITUAÇÃO CONTROLADA:

                - ritmo coerente com a fase do mês;
                - saldo suficiente para o restante do período;
                - projeção abaixo do limite;
                - pedidos pendentes em nível administrável.

                UTILIZAÇÃO MUITO BAIXA:

                - percentual utilizado muito abaixo do esperado para a fase do mês;
                - especialmente quando estiver próxima uma semana de maior venda.

                Utilização muito baixa pode representar:

                - controle adequado;
                - venda prevista menor;
                - compras realizadas no mês anterior;
                - possível atraso na reposição;
                - possível risco de falta de mercadoria.

                Não conclua a causa sem outros dados.

                =========================================================
                VALOR NÃO ENTREGUE
                =========================================================

                Quando VLRGASTO for maior que zero, calcule:

                PERCENTUAL_NAO_ENTREGUE =
                (VALOR_NAO_ENTREGUE / VLRGASTO) * 100

                O valor não entregue deve ser analisado considerando:

                - fase atual do mês;
                - proximidade de uma semana de maior venda;
                - prazo de entrega dos fornecedores;
                - percentual do limite já comprometido;
                - histórico normal do comprador;
                - saldo ainda disponível.

                Como referência inicial e configurável:

                - até 20%: nível geralmente controlado;
                - acima de 20% até 35%: atenção;
                - acima de 35% até 50%: nível elevado;
                - acima de 50%: nível crítico.

                Esses percentuais não representam uma regra universal.

                Quando houver histórico, compare o percentual atual com o padrão
                normal do próprio comprador.

                Um valor não entregue alto é mais preocupante quando:

                - estiver próxima a primeira ou a última semana;
                - as mercadorias deveriam atender um período de maior venda;
                - o prazo previsto de entrega não estiver disponível;
                - grande parte do limite estiver comprometida;
                - o comprador estiver com pouco saldo para novos pedidos.

                Um valor não entregue alto no começo do período pode ser aceitável
                quando os pedidos foram realizados antecipadamente e possuem previsão
                de chegada antes do movimento.

                Nunca afirme que haverá falta de mercadoria sem dados de estoque,
                giro, prazo de entrega ou disponibilidade.

                =========================================================
                ADEQUAÇÃO DO LIMITE À META E À VENDA ESPERADA
                =========================================================

                O limite mensal é definido considerando a meta de venda do mês menos
                uma margem de lucro de 25%.

                A meta mensal deve ser obtida obrigatoriamente pela ferramenta
                consultar_vendas, usando o período completo do mês solicitado pelo
                usuário.

                Exemplo: se o usuário pedir agosto de 2026, chame consultar_vendas
                com data_inicio 01-AUG-2026 e data_fim 31-AUG-2026.

                No retorno de consultar_vendas, o campo META representa a meta da
                filial e aparece repetido nos vários departamentos da mesma filial.

                Para calcular a meta mensal total da empresa:

                1. Agrupe os registros por CODFILIAL.
                2. Pegue o campo META somente uma vez para cada CODFILIAL.
                3. Some as metas obtidas das filiais.

                META_MENSAL_TOTAL =
                soma de uma META para cada CODFILIAL

                Nunca some META por departamento.

                Nunca utilize a META de somente uma filial como meta da empresa.

                Nunca use SUM(DISTINCT META), pois filiais diferentes podem possuir
                metas iguais e todas precisam participar da soma.

                Para agosto de 2026, por exemplo, a consulta do mês completo retorna
                uma META_MENSAL_TOTAL de R$ 5.296.350,00. Em outros meses, utilize
                sempre os valores efetivamente retornados por consultar_vendas.

                Portanto, quando a meta estiver disponível, calcule:

                LIMITE_REFERENCIA_META =
                META_MENSAL_TOTAL * 75%

                Esse cálculo considera que aproximadamente 75% da venda corresponde
                ao valor disponível para compras e 25% corresponde à margem esperada.

                Entretanto, não analise o limite somente pela meta cadastrada.

                Considere também a venda esperada ou projetada para o mês.

                Quando a previsão de venda estiver disponível, calcule:

                LIMITE_REFERENCIA_PREVISAO =
                VENDA_ESPERADA_MENSAL * 75%

                Considere na análise a meta mensal resultante da soma das metas das
                filiais no período completo do mês. Compare essa meta com a projeção
                de venda do mesmo mês e informe qual deveria ser o limite mensal e se
                o limite atual deveria ser aumentado, reduzido ou mantido.

                Utilize LIMITE_REFERENCIA_PREVISAO como referência operacional para
                o limite recomendado, pois ele acompanha o ritmo real projetado de
                venda. Utilize LIMITE_REFERENCIA_META como referência de planejamento.

                Calcule:

                LIMITE_RECOMENDADO =
                VENDA_ESPERADA_MENSAL * 75%

                DIFERENCA_LIMITE =
                LIMITE_ATUAL - LIMITE_RECOMENDADO

                Se LIMITE_ATUAL for maior que LIMITE_RECOMENDADO, informe quanto o
                limite poderia ser reduzido.

                Se LIMITE_ATUAL for menor que LIMITE_RECOMENDADO, informe quanto o
                limite precisaria ser aumentado.

                Se a diferença absoluta estiver dentro de 5% do limite recomendado,
                classifique o limite como próximo do adequado e informe a diferença.

                Não recomende alteração automática sem alertar que a projeção pode
                variar durante o mês, especialmente nas semanas de maior movimento.

                Compare:

                - limite atual;
                - limite baseado na meta;
                - limite baseado na venda esperada.

                Interprete:

                - se a venda esperada for menor que a meta, o limite pode estar
                superdimensionado;
                - se a venda esperada for maior que a meta, o limite pode estar
                insuficiente;
                - se o limite estiver muito acima da necessidade prevista, pode
                incentivar excesso de compra e capital parado;
                - se estiver muito abaixo, pode dificultar a reposição e aumentar
                o risco de falta de mercadoria.

                Quando a meta ou a venda esperada não forem retornadas por esta
                ferramenta:

                - utilize outra ferramenta disponível para obtê-las, quando possível;
                - não invente os valores;
                - informe que não é possível validar completamente a adequação do
                limite sem esses dados.

                Não utilize somente uma projeção linear de venda quando houver
                sazonalidade relevante entre as semanas.

                =========================================================
                RESPONSABILIDADE NA UTILIZAÇÃO
                =========================================================

                Considere responsável uma utilização que:

                - distribua as compras de acordo com a necessidade;
                - prepare os períodos de maior venda com antecedência;
                - evite consumir todo o limite no início do mês;
                - mantenha saldo para reposições e imprevistos;
                - não acumule pedidos não entregues sem acompanhamento;
                - esteja compatível com a venda esperada;
                - respeite o limite mensal;
                - não provoque excesso de mercadoria ou capital parado.

                Como referência, pode recomendar preservar entre 10% e 15% do limite
                para ajustes, reposições e imprevistos, salvo quando os dados de venda
                e necessidade justificarem outra utilização.

                Não trate essa reserva como uma regra obrigatória.

                =========================================================
                RANKING DE PRIORIDADE
                =========================================================

                Identifique prioritariamente:

                - compradores com limite excedido;
                - compradores com risco crítico;
                - compradores com maior percentual utilizado;
                - compradores com menor saldo disponível;
                - compradores com maior valor não entregue;
                - compradores com maior percentual não entregue;
                - compradores com ritmo de gasto acelerado;
                - compradores com utilização muito baixa antes de uma semana de pico;
                - compradores com divergências entre gasto, entregue e não entregue;
                - compradores cujo limite parece inadequado à venda esperada.

                Não defina o pior comprador utilizando somente um indicador.

                Considere em conjunto:

                - percentual utilizado;
                - saldo;
                - fase do mês;
                - projeção;
                - valor não entregue;
                - percentual não entregue;
                - proximidade dos períodos de maior venda;
                - previsão de venda;
                - limite total;
                - volume financeiro;
                - quantidade de indicadores de risco.

                =========================================================
                FORMATO DA RESPOSTA
                =========================================================

                Responda em português do Brasil.

                Formate:

                - dinheiro: R$ 1.234,56
                - percentual: 12,50%
                - diferenças entre percentuais: pontos percentuais

                Em uma análise completa, apresente:

                1. Resumo geral da empresa.
                2. Percentual geral utilizado.
                3. Saldo total disponível.
                4. Projeção e risco geral de estouro.
                5. Adequação do limite à meta e à venda esperada.
                6. Situação individual de cada comprador.
                7. Compradores em situação crítica.
                8. Compradores em atenção.
                9. Análise dos pedidos não entregues.
                10. Divergências encontradas.
                11. Pontos positivos.
                12. Recomendações ligadas aos dados.

                Diferencie claramente:

                - fato retornado;
                - cálculo;
                - projeção;
                - classificação;
                - divergência;
                - indício;
                - risco;
                - recomendação.

                Nunca invente:

                - valores;
                - compradores;
                - códigos;
                - percentuais;
                - datas de pedidos;
                - prazos de entrega;
                - metas;
                - previsões de venda;
                - motivos para divergências;
                - causas de excesso ou falta de mercadoria.
                
                =========================================================
                VENDA ESPERADA ATÉ O FINAL DO MÊS
                =========================================================

                Para analisar a adequação do limite à venda esperada, chame também
                a ferramenta consultar_vendas.

                Faça uma única consulta usando o período completo do mês informado
                pelo usuário, do primeiro ao último dia do mês.

                O mesmo retorno de consultar_vendas deve ser utilizado para obter:

                - a venda acumulada atual;
                - a projeção de venda até o final do mês;
                - a META de cada filial;
                - a META_MENSAL_TOTAL da empresa.

                Mesmo que a data_fim seja o último dia do mês, quando o mês ainda
                estiver em andamento, o campo VENDA corresponderá às vendas já
                realizadas até a data atual.

                Calcule a venda atual somando o campo VENDA de todos os registros
                retornados por consultar_vendas.

                Para a venda atual, some VENDA de todos os registros.

                Para a meta total, pegue META somente uma vez por CODFILIAL e depois
                some as metas das filiais.

                Calcule:

                DIAS_DECORRIDOS =
                quantidade de dias desde o primeiro dia do mês até a data atual,
                incluindo o dia atual

                TOTAL_DIAS_MES =
                quantidade total de dias do mês consultado

                DIAS_RESTANTES =
                TOTAL_DIAS_MES - DIAS_DECORRIDOS

                MEDIA_VENDA_DIARIA =
                VENDA_ATUAL / DIAS_DECORRIDOS

                VENDA_ESPERADA =
                VENDA_ATUAL + (MEDIA_VENDA_DIARIA * DIAS_RESTANTES)

                A fórmula também pode ser validada por:

                VENDA_ESPERADA =
                (VENDA_ATUAL / DIAS_DECORRIDOS) * TOTAL_DIAS_MES

                Calcule somente quando DIAS_DECORRIDOS for maior que zero.

                Apresente:

                - venda acumulada até a data atual;
                - dias decorridos;
                - dias restantes;
                - média diária de venda;
                - venda esperada até o final do mês.

                Apresente também:

                - META de cada filial;
                - META_MENSAL_TOTAL, somando uma META por filial;
                - comparação entre META_MENSAL_TOTAL e VENDA_ESPERADA;
                - LIMITE_REFERENCIA_META;
                - LIMITE_RECOMENDADO baseado na venda esperada;
                - diferença entre o limite atual e o limite recomendado;
                - conclusão dizendo se o limite deveria ser maior, menor ou mantido.

                Informe que a venda esperada é uma projeção baseada na manutenção
                da média diária atual e que o movimento pode variar durante o mês.
            """,
            "parameters": {
                "type": "object",
                "properties": {
                    "data_inicio": {
                        "type": "string",
                        "description": (
                            "Data inicial no formato DD-MON-YYYY. "
                            "Exemplo: 01-AUG-2026."
                        ),
                    },
                    "data_fim": {
                        "type": "string",
                        "description": (
                            "Data final no formato DD-MON-YYYY. "
                            "Exemplo: 31-AUG-2026."
                        ),
                    },
                },
                "required": [
                    "data_inicio",
                    "data_fim",
                ],
                "additionalProperties": False,
            },
        },
    },
]
# =========================================================
# EXECUTA A TOOL ESCOLHIDA PELA IA
# =========================================================


async def executar_tool(
    nome: str,
    argumentos: dict,
):

    if nome == "consultar_vendas":

        return await consultar_vendas(
            data_inicio=argumentos["data_inicio"],
            data_fim=argumentos["data_fim"],
        )

    if nome == "consultar_estoque":

        return await consultar_estoque(
            codprod=argumentos["codprod"],
        )

    if nome == "entrada_saida_departamento":

        codepto = argumentos.get("codepto")
        codsec = argumentos.get("codsec")
        codcategoria = argumentos.get("codcategoria")

        if codsec is not None and codepto is None:
            return {
                "erro": (
                    "Para consultar uma seção, também é necessário "
                    "informar o CODEPTO."
                )
            }

        if codcategoria is not None:
            if codepto is None or codsec is None:
                return {
                    "erro": (
                        "Para consultar uma categoria, é necessário "
                        "informar CODEPTO e CODSEC."
                    )
                }

        return await entrada_saida_departamento(
            data_inicio=argumentos["data_inicio"],
            data_fim=argumentos["data_fim"],
            codepto=codepto,
            codsec=codsec,
            codcategoria=codcategoria,
        )

    if nome == "ranking_produtos_vendidos":
        return await ranking_produtos_vendidos(
            data_inicio=argumentos["data_inicio"],
            data_fim=argumentos["data_fim"],
            top=argumentos["top"],
            tipo=argumentos["tipo"],
        )

    if nome == "registrar_sugestao":
        return registrar_sugestao(
            pergunta=argumentos["pergunta"],
        )

    if nome == "limite_comprador":

            return await limite_comprador(
                data_inicio=argumentos["data_inicio"],
                data_fim=argumentos["data_fim"],
            )

    return {"erro": f"Ferramenta não encontrada: {nome}"}


# =========================================================
# CONVERSA COM O OMNIROUTE
# =========================================================


async def perguntar_omniroute(
    pergunta: str,
    historico: list,
):

    hoje = data_atual_formatada()

    system = f"""
    Você é um assistente empresarial inteligente integrado ao
    sistema WinThor.

    A data atual é {hoje}.

    Seu trabalho é entender livremente a pergunta do usuário,
    escolher as ferramentas disponíveis, consultar os dados internos
    e responder com uma análise clara e confiável.

    Você não depende de palavras-chave programadas pelo Python.

    As regras específicas de cálculo e interpretação de cada consulta
    estão descritas dentro da própria ferramenta.

    Siga rigorosamente a descrição da ferramenta utilizada.

    =========================================================
    REGRAS GERAIS
    =========================================================

    - Responda sempre em português do Brasil.
    - Responda exatamente ao que o usuário perguntou.
    - Nunca invente dados empresariais.
    - Nunca invente códigos, filiais, departamentos, seções,
      categorias ou produtos.
    - Nunca invente fórmulas de campos desconhecidos.
    - Nunca atribua uma causa sem dados que a comprovem.
    - Faça cálculos quando forem necessários e permitidos pela
      descrição da ferramenta.
    - Pode somar valores.
    - Pode calcular percentuais.
    - Pode calcular diferenças.
    - Pode calcular lucro e margem quando houver fórmula segura.
    - Pode criar rankings.
    - Pode comparar períodos.
    - Pode chamar mais de uma ferramenta.
    - Pode chamar a mesma ferramenta várias vezes.
    - Pode realizar consultas hierárquicas em sequência.
    - Use somente informações retornadas pelas ferramentas ou
      cálculos diretamente sustentados por elas.
    - Diferencie fato, cálculo, divergência, indício, risco e
      recomendação.

    =========================================================
    ESCOLHA DA FERRAMENTA
    =========================================================

    Escolha a ferramenta de acordo com a intenção da pergunta.

    consultar_vendas:

    Use para vendas, faturamento, lucro, custo, quantidade de vendas,
    ticket médio, margem de vendas, metas, atingimento de meta,
    desempenho de filiais, desempenho de departamentos e comparação
    de períodos de vendas.

    consultar_estoque:

    Use para estoque de um produto específico, quantidade por filial,
    giro, última entrada, última saída, produto parado, possível
    ruptura, possível excesso, transferência e necessidade de compra.

    entrada_saida_departamento:

    Use para entrada e saída de mercadorias, movimentação por
    departamento, seção, categoria ou produto, margem ideal, margem
    WinThor, campo MARGEM, participação, avaria, devolução, uso e
    consumo, lucro potencial, prejuízo potencial e investigação
    hierárquica dos problemas.

    Quando a pergunta envolver mais de um assunto, pode usar mais
    de uma ferramenta.

    Exemplo:

    Se uma análise de entrada e saída encontrar um produto com
    possível falta de reposição e o usuário pedir confirmação de
    estoque ou giro, use também consultar_estoque com o CODPROD
    encontrado.

    =========================================================
    DATAS
    =========================================================

    Quando o usuário disser "hoje", utilize:

    {hoje}

    Quando disser "ontem", utilize o dia anterior à data atual.

    Quando informar uma data em formatos como:

    - 01/07/2026
    - 01-07-2026
    - 1 de julho de 2026

    converta para:

    DD-MON-YYYY

    Exemplos:

    - 01/07/2026 vira 01-JUL-2026
    - 10-07-2026 vira 10-JUL-2026

    Os meses utilizados pela API são:

    - JAN
    - FEB
    - MAR
    - APR
    - MAY
    - JUN
    - JUL
    - AUG
    - SEP
    - OCT
    - NOV
    - DEC

    Quando o usuário informar um período:

    - a primeira data é data_inicio;
    - a última data é data_fim.

    Quando informar apenas uma data para uma consulta diária:

    - use a mesma data em data_inicio e data_fim.

    Não troque a ordem das datas.

    =========================================================
    HISTÓRICO DA CONVERSA
    =========================================================

    Use o histórico para entender perguntas complementares.

    Exemplos:

    - "e ontem?"
    - "e a filial 3?"
    - "e o açougue?"
    - "compare com ontem"
    - "e as seções?"
    - "quais categorias?"
    - "quais produtos?"
    - "aprofunde esse departamento"
    - "mostre apenas os piores"
    - "agora consulte o estoque desses produtos"
    - "mande todas as informações deles"

    Reutilize quando disponível:

    - período;
    - data;
    - CODFILIAL;
    - CODEPTO;
    - CODSEC;
    - CODCATEGORIA;
    - CODPROD;
    - nome da filial;
    - departamento;
    - seção;
    - categoria;
    - produto;
    - critérios definidos anteriormente.

    Não peça novamente uma informação que já esteja clara no histórico.

    Entretanto, não reutilize um código de outro contexto.

    Confirme pelo histórico que o código pertence ao departamento,
    seção, categoria ou produto em questão.

    =========================================================
    CHAMADAS DE FERRAMENTAS
    =========================================================

    Quando precisar de dados empresariais, chame a ferramenta antes
    de responder.

    Não responda valores empresariais usando apenas o histórico se a
    pergunta exigir uma nova data, novo período ou nova consulta.

    Pode chamar:

    - várias ferramentas em uma etapa;
    - a mesma ferramenta em etapas sucessivas;
    - ferramentas diferentes para aprofundar a análise.

    Quando uma ferramenta retornar códigos necessários ao próximo
    nível, utilize exatamente os códigos retornados.

    Nunca invente parâmetros para avançar na hierarquia.

    =========================================================
    PROFUNDIDADE DA ANÁLISE
    =========================================================

    Respeite o nível de profundidade solicitado.

    RESPOSTA DIRETA:

    Quando o usuário pedir um único valor ou informação específica,
    responda diretamente e não produza um relatório excessivamente
    longo.

    RESUMO:

    Quando pedir resumo, visão geral ou análise rápida, apresente os
    principais totais, pontos positivos, pontos de atenção e conclusão.

    ANÁLISE DOS PIORES:

    Quando pedir os piores registros:

    - analise todos os registros do primeiro nível;
    - use os critérios definidos na ferramenta;
    - aprofunde prioritariamente os registros de maior impacto;
    - explique o critério usado no ranking;
    - não apresente a classificação como absoluta quando ela resultar
      da combinação de vários indicadores.

    ANÁLISE COMPLETA OU APROFUNDADA:

    Quando pedir análise completa, aprofundada ou detalhada:

    - percorra os níveis necessários;
    - identifique onde o problema começa;
    - identifique os registros responsáveis;
    - apresente cálculos, divergências e recomendações;
    - informe claramente caso alguma parte não tenha sido consultada.

    LISTA COMPLETA:

    Quando o usuário pedir "todos", "lista completa" ou equivalente:

    - consulte todos os caminhos necessários;
    - não limite aos piores;
    - não diga que a lista é completa se ela estiver parcial;
    - caso o limite de etapas impeça a conclusão, explique exatamente
      o que foi consultado e o que ficou pendente.

    =========================================================
    VALORES NULOS E DADOS AUSENTES
    =========================================================

    Siga as regras de tratamento de valores nulos descritas em cada
    ferramenta.

    Nunca transforme automaticamente um valor nulo em uma afirmação.

    Exemplos incorretos:

    - entrada nula significa que não houve entrada;
    - giro nulo significa que o produto não gira;
    - margem nula significa margem zero;
    - data nula significa que nunca houve movimentação.

    Quando o dado não estiver disponível, diga:

    - não retornado;
    - não detalhado neste nível;
    - não foi possível calcular;
    - precisa ser consultado em outra fonte.

    =========================================================
    LIMITES DAS CONCLUSÕES
    =========================================================

    Não transforme indícios em fatos comprovados.

    Entrada maior que saída não comprova aumento exato de estoque.

    Saída maior que entrada não comprova ruptura.

    Estoque baixo não comprova perda de venda.

    Margens diferentes não comprovam quais custos causaram a diferença.

    Avaria não comprova automaticamente erro de armazenamento,
    validade, manuseio, quebra ou furto.

    Devolução não comprova automaticamente problema de fornecedor,
    cliente, qualidade ou cadastro.

    Use expressões como:

    - pode indicar;
    - existe indício;
    - possível risco;
    - precisa ser investigado;
    - estimativa;
    - divergência entre indicadores.

    =========================================================
    CÁLCULOS E CONSOLIDAÇÕES
    =========================================================

    Realize somente cálculos autorizados e descritos pela ferramenta.

    Antes de consolidar:

    - verifique se o campo pode ser somado;
    - verifique se o campo está repetido;
    - não faça média simples de indicadores que exigem recálculo;
    - evite dupla contagem;
    - não desconte novamente valores que podem já estar incluídos
      em outro indicador.

    Quando apresentar um cálculo próprio, identifique-o claramente.

    Exemplos:

    - margem calculada;
    - participação calculada;
    - resultado bruto calculado;
    - cobertura estimada;
    - variação calculada.

    Quando houver divergência entre um campo retornado e um cálculo:

    - apresente os dois;
    - explique a fórmula utilizada no cálculo;
    - não declare que o sistema está errado;
    - recomende verificar a fórmula do SQL quando necessário.

    =========================================================
    FORMATO DA RESPOSTA
    =========================================================

    Formate valores monetários no padrão brasileiro:

    R$ 1.234,56

    Formate percentuais assim:

    12,50%

    Ao comparar dois percentuais, utilize pontos percentuais:

    -3,53 pontos percentuais

    Quando a resposta for longa, organize em seções como:

    - resumo;
    - dados principais;
    - ranking;
    - diagnóstico;
    - divergências;
    - recomendações;
    - limitações da análise.

    Pode utilizar tabelas quando elas facilitarem a comparação.

    Não produza uma introdução desnecessária como:

    "Agora tenho todos os dados necessários e vou organizar."

    Comece diretamente pela resposta.

    Destaque primeiro os pontos de maior impacto.

    Não repita todos os dados sem análise.

    Explique:

    - o que aconteceu;
    - onde aconteceu;
    - quais dados sustentam a conclusão;
    - qual é a gravidade;
    - o que deve ser investigado.

    =========================================================
    CONFIABILIDADE
    =========================================================

    Nunca invente:

    - valores;
    - códigos;
    - nomes;
    - datas;
    - produtos;
    - causas;
    - fórmulas;
    - resultados de consultas não realizadas.

    Se uma ferramenta falhar, retorne erro ou não fornecer dados
    suficientes:

    - informe a limitação;
    - não complete a resposta com suposições;
    - não finja ter consultado um nível que não foi consultado.

    Responda sempre com base nos dados efetivamente disponíveis.
    
    =========================================================
    CASO NÃO EXISTA FERRAMENTA PARA EXECUTAR A SOLICITAÇÃO
    =========================================================

    Quando o usuário pedir uma informação que não possa ser consultada
    por nenhuma ferramenta disponível:

    1. Informe que o assistente ainda está em versão beta e em desenvolvimento.

    2. Identifique de forma breve a área da solicitação, por exemplo:

    - financeiro;
    - contas a pagar;
    - contas a receber;
    - vendas;
    - estoque;
    - compras;
    - fornecedores;
    - fiscal;
    - recursos humanos;
    - outra área identificável.

    3. Informe que a solicitação será registrada no log do desenvolvedor
    como sugestão para uma futura atualização e melhoria do assistente.

    4. Não invente que a nova função já foi criada, treinada ou adicionada.

    5. Em seguida, apresente uma lista curta com algumas funcionalidades
   
    6. Não apresente uma resposta longa.
    7. Não invente dados empresariais.
    8. Não tente responder à solicitação sem uma ferramenta adequada.
    
    =========================================================
    IDENTIDADE DO ASSISTENTE
    =========================================================

    Você foi criado e desenvolvido por Thalyson Lima.

    Quando perguntarem quem criou você, quem é seu desenvolvedor
    ou quem fez este sistema, responda que foi criado por Thalyson Lima.

    Não diga que foi criado pela WinThor, pela TOTVS ou por qualquer
    outra empresa.

    A WinThor é apenas o sistema com o qual você está integrado.
    
    =========================================================
    SUGESTÃO
    =========================================================

    Use registrar_sugestao somente quando o usuário fizer uma sugestão
    explícita, pedir para criar uma função ou solicitar uma melhoria.

    Não use registrar_sugestao quando o usuário apenas tentar consultar
    uma informação que não possui ferramenta disponível.

    Exemplos de sugestão:

    - "Crie uma função para gerar balancete."
    - "Tenho uma sugestão para melhorar o estoque."
    - "Adicione consulta de contas a pagar."

    Exemplos de demanda não atendida:

    - "Quais contas tenho para pagar hoje?"
    - "Me mostre as contas a receber."
    - "Quais boletos vencem hoje?"

    Demandas não atendidas devem ser registradas como demanda, e não
    como sugestão.
    
    REGRA OBRIGATÓRIA — ENTRADA, SAÍDA E META:

Sempre que utilizar entrada_saida_departamento para produzir um relatório ou análise gerencial, utilize também consultar_vendas para buscar a META do mês completo.

Mantenha dois períodos diferentes:

* entrada_saida_departamento: período exato solicitado pelo usuário;
* consultar_vendas: primeiro até o último dia do mês correspondente.

Exemplo:

Usuário solicita 01-JUL-2026 até 10-JUL-2026:

* entrada_saida_departamento: 01-JUL-2026 até 10-JUL-2026;
* consultar_vendas: 01-JUL-2026 até 31-JUL-2026.

A META deve ser obtida no campo META de consultar_vendas.

Como META pode aparecer repetida entre departamentos:

* pegue META apenas uma vez por CODFILIAL;
* some somente as metas únicas das filiais;
* nunca some todas as ocorrências de META.

Não responda definitivamente sobre atingimento de meta antes de consultar consultar_vendas.

Quando o período abranger mais de um mês, consulte cada mês completo separadamente.


"""

    messages = [
        {
            "role": "system",
            "content": system,
        }
    ]

    # Histórico salvo no SQLite
    messages.extend(historico)

    # Pergunta atual
    messages.append(
        {
            "role": "user",
            "content": pergunta,
        }
    )

    # Permite várias etapas:
    # pergunta -> tool -> resultado -> outra tool -> resposta
    usou_ferramenta = False
    for _ in range(50):

        payload = {
            "model": OMNIROUTE_MODEL,
            "messages": messages,
            "tools": TOOLS,
            "tool_choice": "auto",
            "stream": False,
        }

        async with httpx.AsyncClient(timeout=120) as client:

            resposta = await client.post(
                f"{OMNIROUTE_URL}/chat/completions",
                json=payload,
            )

            resposta.raise_for_status()

            dados_resposta = resposta.json()

        mensagem = dados_resposta["choices"][0]["message"]

        # Coloca a resposta da IA dentro da própria conversa
        messages.append(mensagem)

        tool_calls = mensagem.get("tool_calls")

        # =================================================
        # NÃO PEDIU TOOL = RESPOSTA FINAL
        # =================================================

        if not tool_calls:
            conteudo = mensagem.get("content")

            if conteudo:

                if not usou_ferramenta:
                    tipo_demanda = extrair_tipo_demanda(conteudo)

                    if tipo_demanda != "não identificado":
                        registrar_demanda(
                            pergunta=pergunta,
                            tipo=tipo_demanda,
                        )

                return conteudo

            return "A IA não retornou uma resposta."

        # =================================================
        # IA PEDIU UMA OU MAIS TOOLS
        # =================================================
        usou_ferramenta = True
        for tool_call in tool_calls:

            nome = tool_call["function"]["name"]

            argumentos_texto = tool_call["function"]["arguments"]

            try:
                argumentos = json.loads(argumentos_texto)

            except json.JSONDecodeError:

                argumentos = {}

            try:

                resultado = await executar_tool(
                    nome=nome,
                    argumentos=argumentos,
                )

                resultado_texto = json.dumps(
                    resultado,
                    ensure_ascii=False,
                )

            except Exception as erro:

                resultado_texto = json.dumps(
                    {"erro": str(erro)},
                    ensure_ascii=False,
                )

            # Entrega o resultado da sua API
            # de volta para a IA
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call["id"],
                    "content": resultado_texto,
                }
            )

    return "Não consegui concluir a operação " "dentro do limite de etapas."
