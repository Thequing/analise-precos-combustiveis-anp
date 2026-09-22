"""Etapa 7 - Geracao do projeto Power BI (.pbip) em TMDL.

O modelo semantico e GERADO, nao montado a mao no Desktop. Vantagens:

  - versionavel: TMDL e texto, entao o modelo entra no diff do git
  - reproduzivel: qualquer pessoa regenera o mesmo modelo
  - conferivel: as medidas saem de docs/dax/medidas.dax, que continua
    sendo a unica fonte de verdade

O relatorio (paginas, visuais) continua sendo montado no Desktop
seguindo docs/guia-relatorio.md. Aqui produzimos o modelo: tabelas,
relacoes, medidas, formatos e hierarquia de exibicao.
"""
from __future__ import annotations

import json
import re
import shutil
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import config as cfg

NOME = "PrecosCombustiveisANP"
DIR_PBIP = cfg.RAIZ / "powerbi"

# --- Esquema das tabelas --------------------------------------------------
# (coluna, tipo TMDL, oculta, sortBy)
TABELAS: dict[str, list[tuple]] = {
    "Dim_Calendario": [
        ("Data", "dateTime", False, None),
        ("Ano", "int64", False, None),
        ("Mes", "int64", True, None),
        ("NomeMes", "string", False, "Mes"),
        ("AnoMes", "int64", True, None),
        ("AnoMesNome", "string", False, "AnoMes"),
        ("Trimestre", "string", False, None),
        ("AnoTrimestre", "string", False, None),
        ("SemanaISO", "int64", False, None),
        ("AnoSemanaISO", "int64", True, None),
        ("InicioSemana", "dateTime", False, None),
        ("DiaSemanaNum", "int64", True, None),
        ("NomeDiaSemana", "string", False, "DiaSemanaNum"),
        ("EhFimDeSemana", "boolean", False, None),
        ("DiasUteisComDados", "int64", True, None),
        ("EhSemanaCompleta", "boolean", False, None),
    ],
    "Dim_Produto": [
        ("SK_Produto", "int64", True, None),
        ("Produto", "string", True, None),
        ("NomeProduto", "string", False, None),
        ("Origem", "string", False, None),
        ("Unidade", "string", False, None),
    ],
    "Dim_Geografia": [
        ("SK_Municipio", "int64", True, None),
        ("Regiao", "string", True, None),
        ("UF", "string", False, None),
        ("Municipio", "string", False, None),
        ("NomeRegiao", "string", False, None),
        ("UF_Municipio", "string", False, None),
    ],
    "Dim_Bandeira": [
        ("SK_Bandeira", "int64", True, None),
        ("Bandeira", "string", False, None),
        ("GrupoBandeira", "string", False, None),
        ("EhBandeiraBranca", "boolean", False, None),
    ],
    "Dim_Revenda": [
        ("SK_Revenda", "int64", True, None),
        ("ID_Revenda", "string", True, None),
        ("NomeRevenda", "string", False, None),
    ],
    "Fato_Coleta": [
        ("Data", "dateTime", True, None),
        ("SK_Produto", "int64", True, None),
        ("SK_Municipio", "int64", True, None),
        ("SK_Bandeira", "int64", True, None),
        ("SK_Revenda", "int64", True, None),
        ("Preco", "double", False, None),
    ],
    "Fato_Evento_Preco": [
        ("SK_Evento", "int64", True, None),
        ("Data", "dateTime", False, None),
        ("SK_Produto", "int64", True, None),
        ("PrecoAntes", "double", False, None),
        ("PrecoDepois", "double", False, None),
        ("DeltaRS", "double", False, None),
        ("DeltaPct", "double", False, None),
        ("ZRobusto", "double", False, None),
        ("Direcao", "string", False, None),
    ],
}

# Colunas descartadas na carga (existem no CSV, nao no modelo).
DESCARTAR = {"Fato_Evento_Preco": ["NomeProduto"]}

RELACOES = [
    ("Dim_Calendario", "Data", "Fato_Coleta", "Data"),
    ("Dim_Produto", "SK_Produto", "Fato_Coleta", "SK_Produto"),
    ("Dim_Geografia", "SK_Municipio", "Fato_Coleta", "SK_Municipio"),
    ("Dim_Bandeira", "SK_Bandeira", "Fato_Coleta", "SK_Bandeira"),
    ("Dim_Revenda", "SK_Revenda", "Fato_Coleta", "SK_Revenda"),
    ("Dim_Calendario", "Data", "Fato_Evento_Preco", "Data"),
    ("Dim_Produto", "SK_Produto", "Fato_Evento_Preco", "SK_Produto"),
]

MOEDA = '"R$ "#,0.000'
PCT = "0.0%"
INT = "#,0"

FORMATOS = {
    "Coletas": INT, "Postos Distintos": INT, "Municipios Distintos": INT,
    "Preco Mediano": MOEDA, "Preco Medio": MOEDA, "Preco Minimo": MOEDA,
    "Preco Maximo": MOEDA, "Assimetria Media-Mediana": MOEDA,
    "Amplitude P90-P10": MOEDA, "Economia Potencial": MOEDA,
    "Coeficiente de Variacao": PCT,
    "Preco Mediano Semana Anterior": MOEDA, "Variacao Semanal RS": MOEDA,
    "Variacao Semanal %": PCT, "Preco Mediano 12M Atras": MOEDA,
    "Variacao 12M %": PCT, "Preco Mediano 28d": MOEDA,
    "Preco no Inicio do Periodo": MOEDA, "Preco no Fim do Periodo": MOEDA,
    "Variacao no Periodo RS": MOEDA, "Variacao no Periodo %": PCT,
    "Variacao Nacional RS": MOEDA, "Transmissao vs Nacional %": "0%",
    "Descolamento vs Nacional RS": MOEDA, "Premio vs Nacional %": PCT,
    "Preco Mediano Gasolina": MOEDA, "Preco Mediano Etanol": MOEDA,
    "Paridade Etanol/Gasolina": PCT, "Etanol Compensa": "0",
    "% Semanas Etanol Compensa": PCT, "Vantagem Etanol RS por km": MOEDA,
    "N Eventos de Preco": INT, "Maior Alta RS": MOEDA, "Maior Baixa RS": MOEDA,
    "Impacto Acumulado dos Eventos RS": MOEDA,
    "% do Movimento Explicado por Eventos": PCT,
    "Ranking UF por Preco": INT, "Ranking UF por Dispersao": INT,
    "Data do Ultimo Evento": "dd/mm/yyyy",
}


def gid() -> str:
    return str(uuid.uuid4())


# --- Leitura das medidas --------------------------------------------------
def ler_medidas(caminho: Path) -> list[dict]:
    """Extrai (nome, pasta, expressao) de docs/dax/medidas.dax.

    O arquivo .dax continua sendo a fonte de verdade: editar la, rodar
    esta etapa de novo. Nao ha segunda copia das medidas.
    """
    medidas: list[dict] = []
    pasta = ""
    nome = None
    corpo: list[str] = []

    # Cabecalho de medida: nome na coluna 0 terminando em "=".
    # Precisa excluir palavras-chave do DAX: "VAR Algo =" tambem comeca
    # na coluna 0 e termina em "=", e seria lida como uma medida nova,
    # truncando a medida real que a contem.
    cab = re.compile(r"^(?P<nome>[A-Za-z%][^=\n]*?)\s*=\s*$")
    PALAVRAS_DAX = ("VAR ", "RETURN", "EVALUATE", "DEFINE", "MEASURE ", "ORDER BY")

    def fechar():
        nonlocal nome, corpo
        if nome:
            expr = "\n".join(corpo).strip("\n")
            while expr.endswith("\n") or expr.endswith(" "):
                expr = expr.rstrip()
            if expr:
                medidas.append({"nome": nome, "pasta": pasta, "expr": expr})
        nome, corpo = None, []

    for linha in caminho.read_text(encoding="utf-8").splitlines():
        m_pasta = re.search(r"\[Pasta:\s*([^\]]+)\]", linha)
        if m_pasta:
            fechar()
            pasta = m_pasta.group(1).strip()
            continue
        if linha.lstrip().startswith("//"):
            fechar()
            continue
        m = cab.match(linha)
        if m and not linha.upper().startswith(PALAVRAS_DAX):
            fechar()
            nome = m.group("nome").strip()
            continue
        if nome is not None:
            corpo.append(linha)

    fechar()
    return medidas


# --- Emissao TMDL ---------------------------------------------------------
def m_query(tabela: str) -> str:
    descartar = DESCARTAR.get(tabela)
    cols = TABELAS[tabela]
    tipos = ",".join(
        f'{{"{c}", {"Int64.Type" if t == "int64" else "type number" if t == "double" else "type date" if t == "dateTime" else "type logical" if t == "boolean" else "type text"}}}'
        for c, t, _, _ in cols
    )
    passos = [
        f'    Origem = Csv.Document(File.Contents(pCaminhoDados & "\\{tabela}.csv"), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),',
        "    Promovido = Table.PromoteHeaders(Origem, [PromoteAllScalars=true]),",
    ]
    ultimo = "Promovido"
    if descartar:
        lista = ",".join(f'"{c}"' for c in descartar)
        passos.append(f"    Removido = Table.RemoveColumns(Promovido, {{{lista}}}),")
        ultimo = "Removido"
    passos.append(f'    Tipos = Table.TransformColumnTypes({ultimo}, {{{tipos}}}, "en-US")')
    return "let\n" + "\n".join(passos) + "\nin\n    Tipos"


def tmdl_tabela(tabela: str, medidas: list[dict] | None = None) -> str:
    L = [f"table {tabela}", f"\tlineageTag: {gid()}", ""]

    if tabela == "Dim_Calendario":
        # Equivalente a "Marcar como tabela de datas".
        L.insert(1, "\tdataCategory: Time")

    if medidas:
        for md in medidas:
            fmt = FORMATOS.get(md["nome"])
            L.append(f"\tmeasure '{md['nome']}' =")
            for linha in md["expr"].splitlines():
                L.append(f"\t\t\t{linha}" if linha.strip() else "")
            if fmt:
                L.append(f"\t\tformatString: {fmt}")
            L.append(f"\t\tlineageTag: {gid()}")
            if md["pasta"]:
                L.append(f"\t\tdisplayFolder: {md['pasta']}")
            L.append("")

    for col, tipo, oculta, sort in TABELAS[tabela]:
        L.append(f"\tcolumn {col}")
        L.append(f"\t\tdataType: {tipo}")
        if tabela == "Dim_Calendario" and col == "Data":
            L.append("\t\tisKey")
        if oculta:
            L.append("\t\tisHidden")
        L.append("\t\tlineageTag: " + gid())
        L.append("\t\tsummarizeBy: none")
        L.append(f"\t\tsourceColumn: {col}")
        if sort:
            L.append(f"\t\tsortByColumn: {sort}")
        if tipo == "dateTime":
            L.append("")
            L.append('\t\tannotation UnderlyingDateTimeDataType = Date')
        L.append("")

    L.append(f"\tpartition {tabela} = m")
    L.append("\t\tmode: import")
    L.append("\t\tsource =")
    for linha in m_query(tabela).splitlines():
        L.append(f"\t\t\t\t{linha}")
    L.append("")
    return "\n".join(L)


def tmdl_medidas_tabela(medidas: list[dict]) -> str:
    """Tabela vazia _Medidas, com todas as medidas do modelo."""
    L = ["table _Medidas", f"\tlineageTag: {gid()}", ""]
    for md in medidas:
        fmt = FORMATOS.get(md["nome"])
        L.append(f"\tmeasure '{md['nome']}' =")
        for linha in md["expr"].splitlines():
            L.append(f"\t\t\t\t{linha}" if linha.strip() else "")
        if fmt:
            L.append(f"\t\tformatString: {fmt}")
        L.append(f"\t\tlineageTag: {gid()}")
        if md["pasta"]:
            L.append(f"\t\tdisplayFolder: {md['pasta']}")
        L.append("")

    L += [
        "\tcolumn Coluna1",
        "\t\tdataType: string",
        "\t\tisHidden",
        f"\t\tlineageTag: {gid()}",
        "\t\tsummarizeBy: none",
        "\t\tsourceColumn: Coluna1",
        "",
        "\tpartition _Medidas = m",
        "\t\tmode: import",
        "\t\tsource =",
        '\t\t\t\tlet',
        '\t\t\t\t    Origem = Table.FromRows({}, type table [Coluna1 = text])',
        '\t\t\t\tin',
        '\t\t\t\t    Origem',
        "",
    ]
    return "\n".join(L)


def main() -> int:
    medidas = ler_medidas(cfg.DIR_DOCS / "dax" / "medidas.dax")
    print(f"Etapa 7 - gerando .pbip")
    print(f"  medidas lidas de docs/dax/medidas.dax: {len(medidas)}")

    sem_formato = [m["nome"] for m in medidas if m["nome"] not in FORMATOS]
    if sem_formato:
        print(f"  sem formato explicito (texto): {', '.join(sem_formato)}")

    if DIR_PBIP.exists():
        shutil.rmtree(DIR_PBIP)
    modelo = DIR_PBIP / f"{NOME}.SemanticModel"
    definicao = modelo / "definition"
    tabelas_dir = definicao / "tables"
    relatorio = DIR_PBIP / f"{NOME}.Report"
    tabelas_dir.mkdir(parents=True)
    relatorio.mkdir(parents=True)

    # --- .pbip ------------------------------------------------------------
    (DIR_PBIP / f"{NOME}.pbip").write_text(json.dumps({
        "version": "1.0",
        "artifacts": [{"report": {"path": f"{NOME}.Report"}}],
        "settings": {"enableAutoRecovery": True},
    }, indent=2), encoding="utf-8")

    # --- SemanticModel ----------------------------------------------------
    (modelo / ".platform").write_text(json.dumps({
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/gitIntegration/platformProperties/2.0.0/schema.json",
        "metadata": {"type": "SemanticModel", "displayName": NOME},
        "config": {"version": "2.0", "logicalId": gid()},
    }, indent=2), encoding="utf-8")

    (modelo / "definition.pbism").write_text(json.dumps({
        "version": "4.2",
        "settings": {"qualifiedFilters": []},
    }, indent=2), encoding="utf-8")

    (definicao / "database.tmdl").write_text(
        "database\n\tcompatibilityLevel: 1606\n", encoding="utf-8")

    # Parametro de caminho: unico ponto a trocar em outra maquina.
    caminho = str(cfg.DIR_PROCESSED).replace("\\", "\\\\")
    (definicao / "expressions.tmdl").write_text(
        f'expression pCaminhoDados = "{caminho}" meta '
        '[IsParameterQuery=true, Type="Text", IsParameterQueryRequired=true]\n'
        f"\tlineageTag: {gid()}\n\n"
        "\tannotation PBI_NavigationStepName = Navigation\n\n"
        "\tannotation PBI_ResultType = Text\n",
        encoding="utf-8")

    nomes_tabelas = list(TABELAS) + ["_Medidas"]
    linhas_modelo = [
        "model Model",
        "\tculture: pt-BR",
        "\tdefaultPowerBIDataSourceVersion: powerBI_V3",
        "\tdiscourageImplicitMeasures",
        "\tsourceQueryCulture: pt-BR",
        "\tdataAccessOptions",
        "\t\tlegacyRedirects",
        "\t\treturnErrorValuesAsNull",
        "",
        "\tannotation PBI_QueryOrder = " + json.dumps(nomes_tabelas),
        "",
        "\tannotation PBI_ProTooling = [\"DevMode\"]",
        "",
    ]
    for t in nomes_tabelas:
        linhas_modelo.append(f"ref table {t}")
    linhas_modelo.append("")
    linhas_modelo.append("ref expression pCaminhoDados")
    linhas_modelo.append("")
    (definicao / "model.tmdl").write_text("\n".join(linhas_modelo), encoding="utf-8")

    # --- Relacoes ---------------------------------------------------------
    rel = []
    for td, cd, tf, cf in RELACOES:
        rel.append(f"relationship {gid()}")
        rel.append(f"\tfromColumn: {tf}.{cf}")
        rel.append(f"\ttoColumn: {td}.{cd}")
        rel.append("")
    (definicao / "relationships.tmdl").write_text("\n".join(rel), encoding="utf-8")

    # --- Tabelas ----------------------------------------------------------
    for t in TABELAS:
        (tabelas_dir / f"{t}.tmdl").write_text(tmdl_tabela(t), encoding="utf-8")
    (tabelas_dir / "_Medidas.tmdl").write_text(
        tmdl_medidas_tabela(medidas), encoding="utf-8")

    # --- Report (pagina em branco; as paginas sao montadas no Desktop) ----
    (relatorio / ".platform").write_text(json.dumps({
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/gitIntegration/platformProperties/2.0.0/schema.json",
        "metadata": {"type": "Report", "displayName": NOME},
        "config": {"version": "2.0", "logicalId": gid()},
    }, indent=2), encoding="utf-8")

    (relatorio / "definition.pbir").write_text(json.dumps({
        "version": "4.0",
        "datasetReference": {"byPath": {"path": f"../{NOME}.SemanticModel"}},
    }, indent=2), encoding="utf-8")

    tema = json.loads((cfg.DIR_DOCS / "tema-anp.json").read_text(encoding="utf-8"))
    (relatorio / "report.json").write_text(json.dumps({
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/report/1.0.0/schema.json",
        "themeCollection": {"customTheme": {"name": tema["name"]}},
        "layoutOptimization": "None",
        "resourcePackages": [{
            "name": "SharedResources", "type": "SharedResources",
            "items": [{"name": "BaseThemeANP", "path": "BaseTheme.json", "type": "BaseTheme"}],
        }],
        "sections": [{
            "name": gid(), "displayName": "Visao Geral",
            "width": 1280, "height": 720, "displayOption": "FitToPage",
            "visualContainers": [],
        }],
    }, indent=2), encoding="utf-8")

    recursos = relatorio / "StaticResources" / "SharedResources" / "BaseThemes"
    recursos.mkdir(parents=True)
    (recursos / "BaseTheme.json").write_text(
        json.dumps(tema, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"  tabelas: {len(TABELAS)} + _Medidas")
    print(f"  relacoes: {len(RELACOES)}")
    print(f"  -> {DIR_PBIP / (NOME + '.pbip')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
