import json
import os
from datetime import date

import httpx
from anthropic import AsyncAnthropic
from dotenv import load_dotenv


load_dotenv()


client = AsyncAnthropic(
    api_key=os.getenv("ANTHROPIC_API_KEY")
)


MODEL = os.getenv(
    "CLAUDE_MODEL",
    "claude-haiku-4-5-20251001",
)


API_BASE_URL = os.getenv(
    "API_BASE_URL",
    "http://127.0.0.1:8000",
)


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

    return (
        f"{hoje.day:02d}-"
        f"{meses[hoje.month]}-"
        f"{hoje.year}"
    )

# =========================================================
# TOOL: CONSULTAR VENDAS
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
        return resposta.json()


# =========================================================
# FERRAMENTAS QUE O CLAUDE CONHECE
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
                Consulta e analisa entradas, saídas, custos, margens,
                avarias, devoluções, uso e consumo e resultado potencial
                de forma hierárquica.

                A ferramenta possui quatro níveis:

                1. Departamento
                2. Seção
                3. Categoria
                4. Produto

                Use esta ferramenta quando a pergunta estiver relacionada a:

                - entrada de mercadorias;
                - saída de mercadorias;
                - movimentação de mercadorias;
                - departamento;
                - seção;
                - categoria;
                - produto;
                - custo;
                - margem WinThor;
                - margem ideal;
                - margem do relatório;
                - participação esperada;
                - participação realizada;
                - avaria;
                - devolução;
                - uso e consumo;
                - lucro potencial;
                - prejuízo potencial;
                - possível falta de reposição;
                - possível excesso de movimentação;
                - análise dos melhores ou piores setores;
                - investigação hierárquica de problemas.

                =========================================================
                NÍVEIS DA CONSULTA
                =========================================================

                NÍVEL 1 — DEPARTAMENTOS

                Parâmetros:

                - data_inicio
                - data_fim

                Retorna todos os departamentos.

                Cada registro pode fornecer CODEPTO, utilizado para acessar
                o nível de seções.

                NÍVEL 2 — SEÇÕES

                Parâmetros:

                - data_inicio
                - data_fim
                - codepto

                Retorna todas as seções daquele departamento.

                Cada registro pode fornecer CODSEC, utilizado para acessar
                o nível de categorias.

                NÍVEL 3 — CATEGORIAS

                Parâmetros:

                - data_inicio
                - data_fim
                - codepto
                - codsec

                Retorna todas as categorias daquela seção.

                Cada registro pode fornecer CODCATEGORIA, utilizado para
                acessar os produtos.

                NÍVEL 4 — PRODUTOS

                Parâmetros:

                - data_inicio
                - data_fim
                - codepto
                - codsec
                - codcategoria

                Retorna os produtos daquela categoria.

                Nunca invente:

                - CODEPTO
                - CODSEC
                - CODCATEGORIA
                - CODPROD

                Sempre obtenha os códigos de um resultado anterior ou do
                histórico da conversa.

                =========================================================
                CAMPOS RETORNADOS
                =========================================================

                Dependendo do nível, os registros podem conter:

                - CODEPTO
                - DEPARTAMENTO
                - CODSEC
                - SECAO
                - CODCATEGORIA
                - CATEGORIA
                - CODPROD
                - PRODUTO
                - VALOR_TOTAL_ENTRADA
                - VALOR_TOTAL_SAIDA
                - CUSTO_TOTAL
                - MARGEM_WINTHOR
                - MARGEM_IDEAL
                - MARGEM
                - PARTICIPACAO_ESPERADA
                - VL_AVARIA
                - VALOR_DEVLUCAO
                - VL_USO_CONSUMO
                - RELATORIO_VALOR

                O nome do campo de devolução é:

                VALOR_DEVLUCAO

                Ele está escrito dessa forma na API.

                Não tente acessar VALOR_DEVOLUCAO, salvo se a resposta
                realmente apresentar esse campo.

                =========================================================
                ESCOLHA DO NÍVEL
                =========================================================

                Se o usuário pedir visão geral, resumo ou situação geral:

                - consulte somente departamentos;
                - apresente os principais resultados;
                - não aprofunde automaticamente todos os níveis.

                Se pedir análise dos piores departamentos:

                1. Consulte departamentos.
                2. Analise todos os departamentos retornados.
                3. Escolha os mais críticos usando vários indicadores.
                4. Consulte as seções dos departamentos críticos.
                5. Consulte as categorias das seções críticas.
                6. Consulte os produtos das categorias críticas.
                7. Explique onde cada problema começa.

                Em uma análise dos piores, aprofunde prioritariamente os
                três piores registros de cada nível.

                Caso existam vários problemas de grande relevância, pode
                aprofundar mais registros.

                Se o usuário pedir análise completa de todos:

                - percorra todos os registros dos níveis solicitados;
                - não limite a consulta somente aos piores.

                Se o usuário pedir diretamente uma seção, categoria ou
                produto pelo nome:

                - use os códigos conhecidos no histórico;
                - quando o código não estiver conhecido, consulte o nível
                  anterior para localizar o nome e obter o código.

                =========================================================
                LISTA COMPLETA DE PRODUTOS
                =========================================================

                Quando o usuário pedir:

                - todos os produtos;
                - lista completa de produtos;
                - todas as informações dos produtos;
                - produtos de todo o departamento;

                execute:

                1. Consulte todas as seções do departamento.
                2. Para cada seção, consulte todas as categorias.
                3. Para cada categoria, consulte todos os produtos.
                4. Não limite a consulta às seções ou categorias críticas.
                5. Somente diga "todos os produtos" ou "lista completa"
                   se realmente percorreu toda a hierarquia disponível.

                Caso não seja possível concluir todas as consultas dentro
                do limite de etapas, informe claramente:

                - quais níveis foram consultados;
                - quais partes ficaram pendentes;
                - que a lista é parcial.

                Nunca chame uma lista parcial de lista completa.

                Ao apresentar todas as informações de um produto, inclua,
                quando disponível:

                - CODEPTO
                - DEPARTAMENTO
                - CODSEC
                - SECAO
                - CODCATEGORIA
                - CATEGORIA
                - CODPROD
                - PRODUTO
                - VALOR_TOTAL_ENTRADA
                - VALOR_TOTAL_SAIDA
                - CUSTO_TOTAL
                - RESULTADO_BRUTO calculado
                - MARGEM_WINTHOR
                - MARGEM_IDEAL
                - DIFERENCA_MARGEM calculada
                - MARGEM
                - VL_AVARIA
                - VALOR_DEVLUCAO
                - VL_USO_CONSUMO
                - RELATORIO_VALOR

                Mostre o campo mesmo quando estiver nulo, caso o usuário
                tenha pedido todas as informações disponíveis.

                =========================================================
                VALORES NULOS
                =========================================================

                Para cálculos de soma, considere como zero quando nulos:

                - VALOR_TOTAL_ENTRADA
                - VALOR_TOTAL_SAIDA
                - CUSTO_TOTAL
                - VL_AVARIA
                - VALOR_DEVLUCAO
                - VL_USO_CONSUMO

                Isso serve somente para cálculos agregados.

                Não transforme ausência de informação em fato.

                Exemplo:

                Se VALOR_TOTAL_ENTRADA vier nulo em um produto, não diga:

                "O produto não teve entrada."

                Diga:

                "A entrada não foi retornada ou não foi detalhada no
                nível de produto."

                Não transforme automaticamente em zero:

                - MARGEM_WINTHOR
                - MARGEM_IDEAL
                - MARGEM
                - PARTICIPACAO_ESPERADA

                Se esses indicadores forem nulos, informe que não foram
                retornados ou calcule somente quando existir fórmula segura.

                =========================================================
                ENTRADA E SAÍDA
                =========================================================

                Calcule:

                SALDO_MOVIMENTACAO =
                VALOR_TOTAL_ENTRADA - VALOR_TOTAL_SAIDA

                Quando o saldo for positivo:

                - entrou mais do que saiu no período;
                - existe saldo positivo de movimentação;
                - pode existir formação de estoque;
                - pode existir capital parado;
                - precisa ser analisado com estoque, giro e disponibilidade.

                Não diga que o valor representa exatamente aumento de estoque.

                Quando o saldo for negativo:

                - saiu mais do que entrou no período;
                - pode estar sendo consumido estoque acumulado;
                - pode existir reposição insuficiente;
                - pode existir risco de ruptura.

                Não afirme ruptura real sem dados de:

                - estoque atual;
                - estoque mínimo;
                - giro;
                - disponibilidade;
                - vendas perdidas.

                Utilize:

                - possível risco de ruptura;
                - indício de falta de reposição;
                - possível consumo de estoque acumulado;
                - precisa ser investigado.

                Não use a expressão "risco de ruptura generalizado" apenas
                porque a saída total foi maior que a entrada total.

                =========================================================
                COBERTURA FINANCEIRA DA ENTRADA
                =========================================================

                Quando VALOR_TOTAL_SAIDA for maior que zero, calcule:

                COBERTURA_ENTRADA =
                (VALOR_TOTAL_ENTRADA / VALOR_TOTAL_SAIDA) * 100

                Interpretação:

                - abaixo de 100%: entrada inferior à saída;
                - igual a 100%: entrada equivalente à saída;
                - acima de 100%: entrada superior à saída.

                Esse indicador mostra somente a relação financeira entre
                entrada e saída no período.

                Ele não representa:

                - dias de estoque;
                - cobertura real de estoque;
                - quantidade física disponível;
                - ruptura confirmada.

                =========================================================
                PARTICIPAÇÃO REAL
                =========================================================

                A ferramenta pode retornar PARTICIPACAO_ESPERADA sem
                retornar a participação realizada.

                Quando a participação real não vier pronta, calcule:

                PARTICIPACAO_REAL =
                (VALOR_TOTAL_SAIDA_REGISTRO /
                VALOR_TOTAL_SAIDA_NIVEL) * 100

                VALOR_TOTAL_SAIDA_NIVEL é a soma da saída de todos os
                registros retornados na mesma consulta.

                No nível de departamento:

                PARTICIPACAO_REAL_DEPARTAMENTO =
                saída do departamento /
                saída total dos departamentos * 100

                Compare PARTICIPACAO_REAL com PARTICIPACAO_ESPERADA
                somente no nível de departamento.

                Calcule:

                DIFERENCA_PARTICIPACAO =
                PARTICIPACAO_REAL - PARTICIPACAO_ESPERADA

                Apresente em pontos percentuais.

                Nos níveis de seção, categoria e produto:

                - calcule apenas a participação dentro do conjunto consultado;
                - não compare com PARTICIPACAO_ESPERADA;
                - PARTICIPACAO_ESPERADA pertence ao departamento e pode
                  aparecer repetida nos níveis inferiores.

                =========================================================
                CUSTO, RESULTADO BRUTO E PERCENTUAL DE CUSTO
                =========================================================

                Quando houver saída e custo, calcule:

                RESULTADO_BRUTO =
                VALOR_TOTAL_SAIDA - CUSTO_TOTAL

                Quando VALOR_TOTAL_SAIDA for maior que zero:

                PERCENTUAL_CUSTO =
                (CUSTO_TOTAL / VALOR_TOTAL_SAIDA) * 100

                Se RESULTADO_BRUTO for negativo:

                - o custo informado é superior à saída informada;
                - existe resultado bruto negativo pelo cálculo simples.

                Não desconte novamente:

                - avaria;
                - devolução;
                - uso e consumo;

                sem conhecer a fórmula do SQL.

                Esses valores podem já estar considerados em outro indicador.

                =========================================================
                MARGEM WINTHOR E MARGEM IDEAL
                =========================================================

                MARGEM_WINTHOR representa a margem atual retornada pelo
                WinThor.

                MARGEM_IDEAL representa a margem esperada ou desejada.

                Calcule:

                DIFERENCA_MARGEM =
                MARGEM_WINTHOR - MARGEM_IDEAL

                Classifique:

                MARGEM BOA:

                - margem atual igual ou superior à ideal.

                MARGEM DE ATENÇÃO:

                - abaixo da ideal em até 3 pontos percentuais.

                MARGEM RUIM:

                - abaixo da ideal por mais de 3 pontos percentuais.

                MARGEM CRÍTICA:

                - margem atual negativa;
                - grande distância negativa da margem ideal;
                - resultado bruto negativo relevante.

                Se MARGEM_WINTHOR não vier preenchida, mas houver saída
                e custo, pode calcular:

                MARGEM_CALCULADA =
                ((VALOR_TOTAL_SAIDA - CUSTO_TOTAL) /
                VALOR_TOTAL_SAIDA) * 100

                Calcule somente quando VALOR_TOTAL_SAIDA for maior que zero.

                Informe claramente que se trata de uma margem calculada.

                =========================================================
                CAMPO MARGEM DO RELATÓRIO
                =========================================================

                O campo MARGEM é um indicador próprio do relatório.

                Não trate MARGEM como substituto de MARGEM_WINTHOR.

                Não invente a fórmula de MARGEM.

                Quando MARGEM e MARGEM_WINTHOR forem diferentes:

                - apresente os dois valores separadamente;
                - informe que existe divergência entre os indicadores;
                - diga que a fórmula do campo MARGEM precisa ser verificada
                  no SQL para explicar a causa.

                Não atribua automaticamente a diferença a:

                - avaria;
                - devolução;
                - uso e consumo;
                - custos adicionais;
                - impostos;
                - despesas.

                Somente explique a causa quando ela estiver suportada
                pela fórmula do SQL ou por dados explícitos.

                =========================================================
                RESULTADO POTENCIAL
                =========================================================

                RELATORIO_VALOR pode retornar:

                - LUCRO POTENCIAL
                - PREJUIZO POTENCIAL

                Esse campo deve ser apresentado exatamente como retornado.

                Não utilize somente RELATORIO_VALOR para classificar um
                registro como saudável ou crítico.

                Analise também:

                - saída;
                - custo;
                - resultado bruto;
                - margem WinThor;
                - margem ideal;
                - campo MARGEM;
                - avaria;
                - devolução;
                - uso e consumo;
                - participação;
                - entrada e saída.

                Quando RELATORIO_VALOR divergir do cálculo simples de
                saída menos custo:

                - apresente a divergência;
                - não afirme que o sistema está errado;
                - informe que a fórmula do SQL precisa ser verificada.

                Exemplo correto:

                "RELATORIO_VALOR retornou LUCRO POTENCIAL, porém o cálculo
                simples de saída menos custo resultou negativo. Existe
                divergência entre os indicadores."

                =========================================================
                DEVOLUÇÃO
                =========================================================

                Quando VALOR_TOTAL_SAIDA for maior que zero:

                PERCENTUAL_DEVOLUCAO =
                (VALOR_DEVLUCAO / VALOR_TOTAL_SAIDA) * 100

                Analise:

                - valor absoluto;
                - percentual sobre a saída.

                Não afirme a causa da devolução sem dados específicos.

                Quando o valor de devolução for atípico, recomende
                investigação no sistema.

                =========================================================
                AVARIA
                =========================================================

                Quando VALOR_TOTAL_SAIDA for maior que zero:

                PERCENTUAL_AVARIA =
                (VL_AVARIA / VALOR_TOTAL_SAIDA) * 100

                Analise:

                - maior valor absoluto;
                - maior percentual;
                - impacto possível sobre o resultado.

                Não atribua automaticamente a avaria a:

                - validade;
                - armazenamento;
                - manuseio;
                - quebra;
                - furto.

                Esses são apenas exemplos de causas que podem ser
                investigadas, e não causas comprovadas.

                Se a avaria aparecer no departamento ou seção, mas não
                no produto, informe que a API não detalhou a avaria no
                nível de produto.

                =========================================================
                USO E CONSUMO
                =========================================================

                Quando VALOR_TOTAL_SAIDA for maior que zero:

                PERCENTUAL_USO_CONSUMO =
                (VL_USO_CONSUMO / VALOR_TOTAL_SAIDA) * 100

                Uso e consumo não deve ser chamado automaticamente de
                prejuízo.

                Destaque quando for relevante em:

                - valor absoluto;
                - percentual sobre a saída.

                =========================================================
                IDENTIFICAÇÃO DOS PIORES
                =========================================================

                Não escolha o pior registro usando somente um indicador.

                Considere em conjunto:

                - PREJUIZO POTENCIAL;
                - resultado bruto negativo;
                - margem WinThor negativa;
                - distância negativa da margem ideal;
                - campo MARGEM negativo;
                - percentual de custo;
                - avaria em reais;
                - percentual de avaria;
                - devolução em reais;
                - percentual de devolução;
                - uso e consumo;
                - saldo da movimentação;
                - participação abaixo da esperada no departamento;
                - volume financeiro do registro.

                Um registro pequeno com percentual ruim pode ter impacto
                menor que um registro grande com diferença moderada.

                Considere:

                - gravidade percentual;
                - impacto financeiro;
                - volume movimentado;
                - quantidade de indicadores problemáticos.

                Ao criar o ranking, informe que ele foi baseado na combinação
                dos critérios analisados.

                Não apresente o ranking como absoluto quando não existir uma
                pontuação única definida pelo sistema.

                =========================================================
                IDENTIFICAÇÃO DOS MELHORES
                =========================================================

                Para identificar os melhores, considere:

                - margem WinThor igual ou superior à ideal;
                - resultado bruto positivo;
                - participação adequada;
                - baixa avaria;
                - baixa devolução;
                - baixo uso e consumo;
                - movimentação equilibrada;
                - volume relevante;
                - LUCRO POTENCIAL.

                Não considere saudável somente porque RELATORIO_VALOR
                retornou LUCRO POTENCIAL.

                =========================================================
                RELATÓRIO COMPLETO
                =========================================================

                Quando o usuário solicitar análise completa ou aprofundada,
                apresente, conforme os dados consultados:

                1. Resumo geral

                - período;
                - total de entradas;
                - total de saídas;
                - saldo da movimentação;
                - cobertura da entrada;
                - custo total;
                - resultado bruto;
                - margem consolidada calculável;
                - avaria total;
                - devolução total;
                - uso e consumo total.

                2. Critério do ranking

                Explique quais indicadores foram considerados para definir
                os registros prioritários.

                3. Departamentos críticos

                - código;
                - nome;
                - entrada;
                - saída;
                - saldo;
                - cobertura;
                - participação real;
                - participação esperada;
                - diferença;
                - custo;
                - resultado bruto;
                - margem WinThor;
                - margem ideal;
                - diferença de margem;
                - campo MARGEM;
                - avaria;
                - devolução;
                - uso e consumo;
                - resultado potencial.

                4. Seções responsáveis

                Mostre as seções que mais contribuíram para os problemas.

                5. Categorias responsáveis

                Mostre as categorias que mais contribuíram.

                6. Produtos envolvidos

                Mostre os produtos com maior impacto e explique os
                indicadores problemáticos.

                7. Pontos positivos

                Apresente também os registros saudáveis ou favoráveis
                quando isso for útil.

                8. Recomendações

                As recomendações devem estar ligadas aos dados.

                Exemplos permitidos:

                - revisar preço de venda;
                - verificar custo de aquisição;
                - verificar margem ideal cadastrada;
                - investigar avarias;
                - investigar devoluções;
                - controlar uso e consumo;
                - revisar volume de compras;
                - consultar estoque e giro;
                - verificar possível falta de reposição;
                - verificar possível formação de estoque;
                - revisar mix de produtos.

                Não afirme que uma ação é obrigatória quando os dados
                apenas indicarem necessidade de investigação.

                =========================================================
                FORMATO DA RESPOSTA
                =========================================================

                Responda em português do Brasil.

                Formate:

                - dinheiro: R$ 1.234,56
                - percentual: 12,50%
                - diferença percentual: pontos percentuais

                Destaque primeiro os problemas de maior impacto.

                Diferencie claramente:

                - fato retornado;
                - cálculo;
                - divergência;
                - indício;
                - risco;
                - recomendação.

                Nunca invente valores, causas, fórmulas, códigos,
                departamentos, seções, categorias ou produtos.
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
]

# =========================================================
# EXECUTAR UMA TOOL
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

    return {"erro": f"Ferramenta não encontrada: {nome}"}


# =========================================================
# CONVERSAR COM CLAUDE
# =========================================================

async def perguntar_claude(
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
"""
   

    messages = historico.copy()

    messages.append(
        {
            "role": "user",
            "content": pergunta,
        }
    )


    # Permite várias rodadas de ferramentas.
    # Exemplo:
    #
    # consultar hoje
    # consultar ontem
    # comparar
    #
    for _ in range(10):

        resposta = await client.messages.create(

            model=MODEL,

            max_tokens=1500,

            system=system,

            tools=TOOLS,

            messages=messages,
        )


        # Adiciona a resposta do Claude ao contexto
        conteudo_assistente = []

        for bloco in resposta.content:

            conteudo_assistente.append(
                bloco.model_dump()
            )


        messages.append(
            {
                "role": "assistant",
                "content": conteudo_assistente,
            }
        )


        # =================================================
        # CLAUDE NÃO PRECISA MAIS DE TOOL
        # =================================================

        if resposta.stop_reason != "tool_use":

            textos = []

            for bloco in resposta.content:

                if bloco.type == "text":
                    textos.append(
                        bloco.text
                    )

            return "\n".join(textos)


        # =================================================
        # CLAUDE SOLICITOU FERRAMENTAS
        # =================================================

        resultados_tools = []


        for bloco in resposta.content:

            if bloco.type != "tool_use":
                continue


            try:

                resultado = await executar_tool(
                    nome=bloco.name,
                    parametros=bloco.input,
                )


                resultados_tools.append(
                    {
                        "type": "tool_result",

                        "tool_use_id": bloco.id,

                        "content": json.dumps(
                            resultado,
                            ensure_ascii=False,
                        ),
                    }
                )


            except Exception as erro:

                resultados_tools.append(
                    {
                        "type": "tool_result",

                        "tool_use_id": bloco.id,

                        "is_error": True,

                        "content": str(erro),
                    }
                )


        # Devolve o resultado das APIs para Claude
        messages.append(
            {
                "role": "user",
                "content": resultados_tools,
            }
        )


    return (
        "Não consegui concluir a análise "
        "dentro do limite de operações."
    )