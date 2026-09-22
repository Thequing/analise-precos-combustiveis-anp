"""Etapa 11 - Geracao das 3 paginas do relatorio, em PBIR.

Injeta Report/definition/ dentro do .pbix ja salvo. O modelo (DataModel)
nao e tocado - so a camada de relatorio.

Regras aplicadas em todas as paginas:
  - uma linha de filtros no topo, nunca espalhados
  - titulo afirma o achado, nao o nome do campo
  - legenda presente com 2+ series; identidade nunca so por cor
  - nenhum eixo duplo: duas medidas de escala diferente = dois visuais
  - cor fixa por produto, jamais por ordem de classificacao

Uso:
    python src/step11_relatorio.py "C:\\caminho\\arquivo.pbix"
"""
from __future__ import annotations

import shutil
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import config as cfg
import pbir
from pbir import AMBAR, AZUL, GRADE, TINTA, TINTA2, VERDE

L, A = 1280, 720          # tela da pagina
M = 16                    # margem


def slicer(nome, x, y, w, h, tabela, col, titulo_txt, modo=None):
    obj = {"general": [{"properties": {"outlineColor": {"solid": {"color": pbir.lit(GRADE)}},
                                       "outlineWeight": pbir.lit(1)}}],
           "header": [{"properties": {"show": pbir.lit(True),
                                      "fontColor": {"solid": {"color": pbir.lit(TINTA)}},
                                      "fontSize": pbir.lit(9),
                                      "text": pbir.lit(titulo_txt)}}],
           "items": [{"properties": {"fontColor": {"solid": {"color": pbir.lit(TINTA2)}},
                                     "fontSize": pbir.lit(9)}}]}
    if modo:
        obj["data"] = [{"properties": {"mode": pbir.lit(modo)}}]
    return pbir.visual(nome, "slicer", x, y, w, h,
                       {"Values": [pbir.coluna(tabela, col)]}, objetos=obj)


def cartao(nome, x, y, w, h, medida, rotulo, casas=None):
    props = {"color": {"solid": {"color": pbir.lit(TINTA)}}, "fontSize": pbir.lit(28)}
    if casas is not None:
        props["labelPrecision"] = pbir.lit(casas)
    return pbir.visual(nome, "card", x, y, w, h,
        {"Values": [pbir.medida(medida)]},
        objetos={"labels": [{"properties": props}],
                 "categoryLabels": [{"properties": {"show": pbir.lit(False)}}]},
        container=pbir.titulo(rotulo, 10))


# =========================================================================
def pagina_1() -> tuple[dict, list[dict]]:
    """Visao geral: onde o preco esta, e quanto ele varia."""
    pg = pbir.pagina(pbir.ident("p1"), "1. Visao Geral", L, A)
    v = []
    y = M

    v.append(pbir.caixa_texto(pbir.ident("p1", "h"), M, y, 720, 46,
        "Precos de combustiveis no Brasil", 20))
    v.append(pbir.caixa_texto(pbir.ident("p1", "h2"), M, y + 40, 900, 26,
        "1.053.221 coletas da ANP em 11.151 postos, set/2024 a ago/2026", 10, False, TINTA2))

    # --- linha unica de filtros ---
    fy = y + 72
    v.append(slicer(pbir.ident("p1", "s1"), M, fy, 200, 52, "Dim_Produto", "NomeProduto", "Produto"))
    v.append(slicer(pbir.ident("p1", "s2"), M + 210, fy, 200, 52, "Dim_Geografia", "NomeRegiao", "Regiao"))
    v.append(slicer(pbir.ident("p1", "s3"), M + 420, fy, 300, 52, "Dim_Calendario", "Data", "Periodo", "Between"))

    # --- faixa de indicadores ---
    cy = fy + 62
    cw = (L - 2 * M - 3 * 10) // 4
    cards = [("Preco Mediano", "Preco mediano (R$/L)", 3),
             ("Variacao no Periodo %", "Variacao no periodo", None),
             ("Amplitude P90-P10", "Dispersao P90-P10 (R$)", 2),
             ("Postos Distintos", "Postos pesquisados", 0)]
    for i, (med, rot, cas) in enumerate(cards):
        v.append(cartao(pbir.ident("p1", f"c{i}"), M + i * (cw + 10), cy, cw, 96, med, rot, cas))

    # --- serie temporal ---
    gy = cy + 106
    v.append(pbir.visual(pbir.ident("p1", "g1"), "lineChart", M, gy, L - 2 * M, 236,
        {"Category": [pbir.coluna("Dim_Calendario", "InicioSemana")],
         "Y": [pbir.medida("Preco Mediano")],
         "Series": [pbir.coluna("Dim_Produto", "NomeProduto")]},
        objetos={**pbir.eixos_discretos(), **pbir.legenda(),
                 "dataPoint": [{"properties": {"fill": pbir.cor(AZUL)}}]},
        container={**pbir.titulo("Diesel subiu 15% no periodo; o etanol caiu 2,6%"),
                   **pbir.subtitulo("Mediana semanal. A coleta da ANP se concentra na segunda-feira, por isso o grao e semanal.")}))

    # --- rankings por UF ---
    by = gy + 246
    bh = A - by - M
    bw = (L - 2 * M - 10) // 2
    v.append(pbir.visual(pbir.ident("p1", "b1"), "barChart", M, by, bw, bh,
        {"Category": [pbir.coluna("Dim_Geografia", "UF")],
         "Y": [pbir.medida("Preco Mediano")]},
        objetos={**pbir.eixos_discretos(),
                 "dataPoint": [{"properties": {"fill": pbir.cor(AZUL)}}]},
        container=pbir.titulo("Onde o combustivel custa mais")))
    v.append(pbir.visual(pbir.ident("p1", "b2"), "barChart", M + bw + 10, by, bw, bh,
        {"Category": [pbir.coluna("Dim_Geografia", "UF")],
         "Y": [pbir.medida("Amplitude P90-P10")]},
        objetos={**pbir.eixos_discretos(),
                 "dataPoint": [{"properties": {"fill": pbir.cor(AMBAR)}}]},
        container={**pbir.titulo("Onde vale a pena procurar posto"),
                   **pbir.subtitulo("Faixa P90-P10. Em branco onde ha menos de 30 postos - amostra insuficiente.")}))
    return pg, v


# =========================================================================
def pagina_2() -> tuple[dict, list[dict]]:
    """Transmissao: quanto do movimento nacional chega a cada estado."""
    pg = pbir.pagina(pbir.ident("p2"), "2. Transmissao", L, A)
    v = []
    y = M

    v.append(pbir.caixa_texto(pbir.ident("p2", "h"), M, y, 900, 46,
        "Quando o preco se move no pais, quanto chega a cada estado?", 20))

    fy = y + 52
    v.append(slicer(pbir.ident("p2", "s1"), M, fy, 200, 52, "Dim_Produto", "NomeProduto", "Produto"))
    v.append(slicer(pbir.ident("p2", "s2"), M + 210, fy, 300, 52, "Dim_Calendario", "Data", "Periodo", "Between"))

    # Linha em cima, colunas de evento embaixo, MESMO eixo de tempo.
    # Nao e grafico de eixo duplo: sao dois visuais, cada um com um eixo.
    gy = fy + 62
    gw = L - 2 * M
    v.append(pbir.visual(pbir.ident("p2", "g1"), "lineChart", M, gy, gw, 210,
        {"Category": [pbir.coluna("Dim_Calendario", "InicioSemana")],
         "Y": [pbir.medida("Preco Mediano")]},
        objetos={**pbir.eixos_discretos(), **pbir.legenda(False),
                 "dataPoint": [{"properties": {"fill": pbir.cor(AZUL)}}]},
        container=pbir.titulo("Preco mediano nacional")))
    v.append(pbir.visual(pbir.ident("p2", "g2"), "columnChart", M, gy + 214, gw, 118,
        {"Category": [pbir.coluna("Dim_Calendario", "InicioSemana")],
         "Y": [pbir.medida("Impacto Acumulado dos Eventos RS")]},
        objetos={**pbir.eixos_discretos(), **pbir.legenda(False),
                 "dataPoint": [{"properties": {"fill": pbir.cor(AMBAR)}}]},
        container={**pbir.titulo("Eventos de preco detectados (R$/L)"),
                   **pbir.subtitulo("Quebras estruturais na serie, por z-score robusto. Nao sao reajustes da Petrobras.")}))

    my = gy + 340
    mh = A - my - M
    mw = (L - 2 * M - 10) * 55 // 100
    v.append(pbir.visual(pbir.ident("p2", "m1"), "pivotTable", M, my, mw, mh,
        {"Rows": [pbir.coluna("Dim_Geografia", "UF")],
         "Columns": [pbir.coluna("Dim_Produto", "NomeProduto")],
         "Values": [pbir.medida("Transmissao vs Nacional %")]},
        objetos={"grid": [{"properties": {"gridVertical": pbir.lit(False),
                                          "gridHorizontalColor": pbir.cor(GRADE),
                                          "rowPadding": pbir.lit(3)}}],
                 "columnHeaders": [{"properties": {"fontColor": {"solid": {"color": pbir.lit(TINTA)}},
                                                   "bold": pbir.lit(True), "fontSize": pbir.lit(9)}}],
                 "values": [{"properties": {"fontSize": pbir.lit(9)}}]},
        container={**pbir.titulo("SP repassa 119% do movimento nacional; MS, 63%"),
                   **pbir.subtitulo("100% = acompanhou o pais. Abaixo = absorveu parte na margem.")}))
    v.append(pbir.visual(pbir.ident("p2", "d1"), "scatterChart",
        M + mw + 10, my, L - 2 * M - mw - 10, mh,
        {"Category": [pbir.coluna("Dim_Geografia", "UF")],
         "X": [pbir.medida("Variacao no Periodo RS")],
         "Y": [pbir.medida("Preco Mediano")],
         "Size": [pbir.medida("Postos Distintos")]},
        objetos={**pbir.eixos_discretos(), **pbir.legenda(False),
                 "dataPoint": [{"properties": {"fill": pbir.cor(VERDE)}}]},
        container=pbir.titulo("Nivel de preco x tamanho do movimento")))
    return pg, v


# =========================================================================
def pagina_3() -> tuple[dict, list[dict]]:
    """Paridade: onde o etanol realmente compensa."""
    pg = pbir.pagina(pbir.ident("p3"), "3. Paridade do Etanol", L, A)
    v = []
    y = M

    v.append(pbir.caixa_texto(pbir.ident("p3", "h"), M, y, 900, 46,
        "O mapa do etanol e o mapa da cana", 20))
    v.append(pbir.caixa_texto(pbir.ident("p3", "h2"), M, y + 40, 1000, 26,
        "Abaixo de 70% da gasolina o etanol compensa - ele rende cerca de 30% menos por litro.",
        10, False, TINTA2))

    fy = y + 72
    v.append(slicer(pbir.ident("p3", "s1"), M, fy, 300, 52, "Dim_Calendario", "Data", "Periodo", "Between"))

    cw = 210
    v.append(cartao(pbir.ident("p3", "c1"), M + 320, fy, cw, 52, "Paridade Etanol/Gasolina", "Paridade nacional"))
    v.append(cartao(pbir.ident("p3", "c2"), M + 320 + cw + 10, fy, cw, 52, "% Semanas Etanol Compensa", "Semanas favoraveis"))

    my = fy + 62
    mh = 300
    v.append(pbir.visual(pbir.ident("p3", "m1"), "pivotTable", M, my, L - 2 * M, mh,
        {"Rows": [pbir.coluna("Dim_Geografia", "UF")],
         "Columns": [pbir.coluna("Dim_Calendario", "AnoMesNome")],
         "Values": [pbir.medida("Paridade Etanol/Gasolina")]},
        objetos={"grid": [{"properties": {"gridVertical": pbir.lit(False),
                                          "gridHorizontalColor": pbir.cor(GRADE),
                                          "rowPadding": pbir.lit(2)}}],
                 "columnHeaders": [{"properties": {"fontColor": {"solid": {"color": pbir.lit(TINTA)}},
                                                   "bold": pbir.lit(True), "fontSize": pbir.lit(8)}}],
                 "values": [{"properties": {"fontSize": pbir.lit(8)}}]},
        container={**pbir.titulo("Paridade por UF e mes"),
                   **pbir.subtitulo("Aplicar formatacao condicional divergente com CENTRO EM 0,70 - e isso que transforma a matriz em resposta.")}))

    by = my + mh + 10
    bh = A - by - M
    bw = (L - 2 * M - 10) // 2
    v.append(pbir.visual(pbir.ident("p3", "b1"), "barChart", M, by, bw, bh,
        {"Category": [pbir.coluna("Dim_Geografia", "UF")],
         "Y": [pbir.medida("% Semanas Etanol Compensa")]},
        objetos={**pbir.eixos_discretos(),
                 "dataPoint": [{"properties": {"fill": pbir.cor(VERDE)}}]},
        container=pbir.titulo("MS: 100% das semanas. AP: nenhuma.")))
    v.append(pbir.visual(pbir.ident("p3", "b2"), "barChart", M + bw + 10, by, bw, bh,
        {"Category": [pbir.coluna("Dim_Geografia", "UF")],
         "Y": [pbir.medida("Vantagem Etanol RS por km")]},
        objetos={**pbir.eixos_discretos(),
                 "dataPoint": [{"properties": {"fill": pbir.cor(VERDE)}}]},
        container={**pbir.titulo("Vantagem em R$ por litro equivalente"),
                   **pbir.subtitulo("Ja corrigido pelo menor rendimento do etanol.")}))
    return pg, v


# =========================================================================
def main() -> int:
    if len(sys.argv) < 2:
        print("uso: python src/step11_relatorio.py <caminho.pbix>")
        return 2
    alvo = Path(sys.argv[1])
    if not alvo.exists():
        print(f"nao encontrado: {alvo}")
        return 2

    backup = alvo.with_suffix(".pbix.bak")
    if not backup.exists():
        shutil.copy(alvo, backup)
        print(f"backup -> {backup.name}")

    paginas = [pagina_1(), pagina_2(), pagina_3()]
    ordem = [p["name"] for p, _ in paginas]

    tmp = alvo.with_suffix(".pbix.tmp")
    zin = zipfile.ZipFile(backup)
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as z:
        for n in zin.namelist():
            if n.startswith("Report/definition/"):
                continue
            if n == "SecurityBindings":      # assinatura do pacote anterior
                continue
            z.writestr(n, zin.read(n))
        z.writestr("Report/definition/version.json", zin.read("Report/definition/version.json"))
        z.writestr("Report/definition/report.json", zin.read("Report/definition/report.json"))
        pbir.gravar(z, "Report/definition/pages/pages.json",
                    {"$schema": pbir.S_PAGES, "pageOrder": ordem, "activePageName": ordem[0]})
        total = 0
        for pg, vis in paginas:
            pbir.gravar(z, f"Report/definition/pages/{pg['name']}/page.json", pg)
            for vv in vis:
                pbir.gravar(z, f"Report/definition/pages/{pg['name']}/visuals/{vv['name']}/visual.json", vv)
                total += 1
    zin.close()
    tmp.replace(alvo)

    print(f"Etapa 11 - relatorio gerado em {alvo.name}")
    for pg, vis in paginas:
        print(f"  {pg['displayName']:<26} {len(vis):>2} visuais")
    print(f"  total: {total} visuais em {len(paginas)} paginas")
    print()
    print("  Falta a mao no Desktop (formatacao condicional nao e gerada aqui):")
    print("   - Pagina 2, matriz: escala divergente, CENTRO em 1 (=100%)")
    print("   - Pagina 3, matriz: escala divergente, CENTRO em 0,70")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
