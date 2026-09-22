"""Configuracao central do pipeline ANP -> Power BI.

Todos os caminhos e parametros de negocio ficam aqui. Nenhum outro modulo
deve conter caminho absoluto ou constante de negocio.
"""
from pathlib import Path

# --- Caminhos -------------------------------------------------------------
RAIZ = Path(__file__).resolve().parent.parent
DIR_RAW = RAIZ / "data" / "raw"
DIR_INTERIM = RAIZ / "data" / "interim"
DIR_PROCESSED = RAIZ / "data" / "processed"
DIR_OUTPUTS = RAIZ / "outputs"
DIR_DOCS = RAIZ / "docs"

for _d in (DIR_RAW, DIR_INTERIM, DIR_PROCESSED, DIR_OUTPUTS):
    _d.mkdir(parents=True, exist_ok=True)

# --- Fonte ----------------------------------------------------------------
URL_INDICE = (
    "https://www.gov.br/anp/pt-br/centrais-de-conteudo/dados-abertos/"
    "serie-historica-de-precos-de-combustiveis"
)
USER_AGENT = "Mozilla/5.0 (projeto academico - analise de precos ANP)"

# Grupos de arquivo mensais publicados pela ANP (diretorio dsan/).
# GLP fica fora de escopo: e vendido por botijao de 13kg, unidade
# incompativel com R$/litro, e misturar unidades corromperia as medias.
GRUPOS = ("gasolina-etanol", "diesel-gnv")

# --- Janela de analise ----------------------------------------------------
# 24 meses completos encerrando no ultimo mes publicado.
MES_INICIO = (2024, 9)
MES_FIM = (2026, 8)

# --- Regras de negocio ----------------------------------------------------
# Produtos mantidos. Excluimos GNV (R$/m3) pelo mesmo motivo do GLP.
PRODUTOS_ALVO = ("GASOLINA", "ETANOL", "DIESEL S10")

UNIDADE_ESPERADA = "R$ / litro"

# Limiar classico de paridade etanol/gasolina. Acima disso, a gasolina
# compensa mais por causa do menor rendimento energetico do etanol.
LIMIAR_PARIDADE = 0.70

# Faixas de sanidade por produto (R$/litro). Valores fora disso sao erro
# de digitacao do coletor, nao preco real. Derivados da faixa historica
# observada, com folga generosa nas duas pontas.
FAIXAS_PRECO = {
    "GASOLINA": (3.00, 10.00),
    "ETANOL": (2.00, 8.00),
    "DIESEL S10": (3.00, 10.00),
}

# Janela para medir repasse de reajuste ao consumidor final.
DIAS_JANELA_REPASSE = 30
