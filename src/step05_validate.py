"""Etapa 5 - Suite de testes das medidas DAX.

Gera dois artefatos a partir do MESMO calculo em pandas:

  docs/valores-esperados.md  - tabela para conferencia manual
  docs/testes-dax.json       - suite executavel (consulta DAX + esperado)

A consulta e o valor esperado saem juntos, do mesmo lugar. Nao ha como
um divergir do outro por descuido.

Executar com:  powershell -File scripts/Invoke-TestesDax.ps1
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
import config as cfg

MIN_POSTOS = 30
MIN_COLETAS = 10

TOL_RS = 0.0015      # R$/litro
TOL_PCT = 0.005      # pontos percentuais em fracao
TOL_INT = 0          # contagens tem de bater exatamente


def carregar() -> pd.DataFrame:
    p = cfg.DIR_PROCESSED
    fato = pd.read_csv(p / "Fato_Coleta.csv", parse_dates=["Data"], encoding="utf-8-sig")
    dp = pd.read_csv(p / "Dim_Produto.csv", encoding="utf-8-sig")
    dg = pd.read_csv(p / "Dim_Geografia.csv", encoding="utf-8-sig")
    dc = pd.read_csv(p / "Dim_Calendario.csv", parse_dates=["Data", "InicioSemana"],
                     encoding="utf-8-sig")
    return (fato.merge(dp[["SK_Produto", "NomeProduto"]], on="SK_Produto")
                .merge(dg[["SK_Municipio", "UF", "NomeRegiao"]], on="SK_Municipio")
                .merge(dc[["Data", "InicioSemana"]], on="Data"))


def mediana_guardada(s: pd.Series) -> float | None:
    return float(s.median()) if len(s) >= MIN_COLETAS else None


def dax_data(d: pd.Timestamp) -> str:
    return f"DATE({d.year}, {d.month}, {d.day})"


def main() -> int:
    df = carregar()
    testes: list[dict] = []
    md: list[str] = []

    def add(nome, grupo, dax, esperado, tol, nota=""):
        testes.append({"nome": nome, "grupo": grupo, "dax": dax,
                       "esperado": esperado, "tolerancia": tol, "nota": nota})

    def evaluate(medida_expr, filtros=None):
        if filtros:
            return (f'EVALUATE ROW("v", CALCULATE({medida_expr}, '
                    + ", ".join(filtros) + "))")
        return f'EVALUATE ROW("v", {medida_expr})'

    def f_prod(p):
        return f'KEEPFILTERS(Dim_Produto[NomeProduto] = "{p}")'

    def f_uf(u):
        return f'KEEPFILTERS(Dim_Geografia[UF] = "{u}")'

    md += ["# Valores esperados para conferência do DAX", "",
           "Gerado por `src/step05_validate.py`. A suíte executável "
           "equivalente está em `docs/testes-dax.json` e roda com "
           "`scripts/Invoke-TestesDax.ps1`.", "",
           f"Base: {len(df):,} coletas · "
           f"{df['Data'].min():%d/%m/%Y} a {df['Data'].max():%d/%m/%Y}", ""]

    def tabela(titulo, texto=""):
        md.extend(["", f"## {titulo}", ""])
        if texto:
            md.extend([texto, ""])
        md.append("| Medida | Recorte | Esperado |")
        md.append("|--------|---------|----------|")

    def linha(medida, recorte, v, fmt="{:.4f}"):
        md.append(f"| {medida} | {recorte} | `"
                  + ("BLANK" if v is None else fmt.format(v)) + "` |")

    # --- 1. Contagens -----------------------------------------------------
    tabela("1. Contagens, sem filtro")
    for nome, valor, expr in [
        ("Coletas", len(df), "[Coletas]"),
        ("Postos Distintos", df["SK_Revenda"].nunique(), "[Postos Distintos]"),
        ("Municipios Distintos", df["SK_Municipio"].nunique(), "[Municipios Distintos]"),
    ]:
        add(nome, "Contagens", evaluate(expr), int(valor), TOL_INT)
        linha(nome, "sem filtro", valor, "{:,.0f}")

    # --- 2. Preco por produto ---------------------------------------------
    tabela("2. Preço mediano por produto")
    for prod, g in df.groupby("NomeProduto"):
        v = float(g["Preco"].median())
        add(f"Preco Mediano · {prod}", "Preco",
            evaluate("[Preco Mediano]", [f_prod(prod)]), v, TOL_RS)
        linha("Preco Mediano", f"Produto = {prod}", v)

    for prod, g in df.groupby("NomeProduto"):
        v = float(g["Preco"].quantile(.90) - g["Preco"].quantile(.10))
        add(f"Amplitude P90-P10 · {prod}", "Dispersao",
            evaluate("[Amplitude P90-P10]", [f_prod(prod)]), v, TOL_RS)
        linha("Amplitude P90-P10", f"Produto = {prod}", v)

    # --- 3. Guarda de amostra ---------------------------------------------
    sem8 = df["InicioSemana"].max() - pd.Timedelta(weeks=8)
    ult8 = df[df["InicioSemana"] >= sem8]
    tabela("3. Guarda de amostra pequena",
           "`Amplitude P90-P10` exige 30 postos distintos. RR tem 15 — "
           "deve devolver BLANK em vez de aparecer como o mercado mais "
           "homogêneo do país.")
    for uf in ("RR", "AC", "SP"):
        g = ult8[(ult8["UF"] == uf) & (ult8["NomeProduto"] == "Gasolina")]
        postos = g["SK_Revenda"].nunique()
        v = (float(g["Preco"].quantile(.90) - g["Preco"].quantile(.10))
             if postos >= MIN_POSTOS else None)
        filtros = [f_uf(uf), f_prod("Gasolina"),
                   f"Dim_Calendario[InicioSemana] >= {dax_data(sem8)}"]
        add(f"Guarda amostra · {uf} ({postos} postos)", "Guarda",
            evaluate("[Amplitude P90-P10]", filtros), v, TOL_RS,
            "deve ser BLANK" if v is None else "")
        linha("Amplitude P90-P10", f"{uf}, Gasolina, 8 sem. ({postos} postos)", v)

    # --- 4. Paridade -------------------------------------------------------
    tabela("4. Paridade etanol/gasolina",
           "Usa `REMOVEFILTERS(Dim_Produto)`: deve dar o mesmo valor com "
           "o slicer de produto em Gasolina, em Etanol ou sem seleção.")
    for uf in ("SP", "MS", "AP", "RS"):
        g = df[df["UF"] == uf]
        e = mediana_guardada(g[g["NomeProduto"] == "Etanol"]["Preco"])
        s = mediana_guardada(g[g["NomeProduto"] == "Gasolina"]["Preco"])
        v = (e / s) if e and s else None
        add(f"Paridade · {uf}", "Paridade",
            evaluate("[Paridade Etanol/Gasolina]", [f_uf(uf)]), v, TOL_PCT)
        linha("Paridade Etanol/Gasolina", f"UF = {uf}", v)

    nac = (float(df[df["NomeProduto"] == "Etanol"]["Preco"].median())
           / float(df[df["NomeProduto"] == "Gasolina"]["Preco"].median()))
    add("Paridade · Brasil", "Paridade",
        evaluate("[Paridade Etanol/Gasolina]"), nac, TOL_PCT)
    linha("Paridade Etanol/Gasolina", "Brasil", nac)

    # Invariancia: o mesmo valor sob tres contextos de produto distintos.
    for ctx, filtros in [("filtro Gasolina", [f_prod("Gasolina")]),
                         ("filtro Etanol", [f_prod("Etanol")]),
                         ("filtro Diesel S10", [f_prod("Diesel S10")])]:
        add(f"Paridade invariante · {ctx}", "Paridade",
            evaluate("[Paridade Etanol/Gasolina]", filtros), nac, TOL_PCT,
            "REMOVEFILTERS(Dim_Produto) deve anular o filtro de produto")

    # --- 5. Variacao e transmissao ----------------------------------------
    sem_min, sem_max = df["InicioSemana"].min(), df["InicioSemana"].max()

    def var_periodo(sub) -> float | None:
        i = mediana_guardada(sub[sub["InicioSemana"] == sem_min]["Preco"])
        f = mediana_guardada(sub[sub["InicioSemana"] == sem_max]["Preco"])
        return (f - i) if i is not None and f is not None else None

    tabela("5. Variação no período e transmissão",
           f"Primeira semana {sem_min:%d/%m/%Y}, última {sem_max:%d/%m/%Y}.")
    for prod in sorted(df["NomeProduto"].unique()):
        v = var_periodo(df[df["NomeProduto"] == prod])
        add(f"Variacao no Periodo RS · {prod}", "Variacao",
            evaluate("[Variacao no Periodo RS]", [f_prod(prod)]), v, TOL_RS)
        linha("Variacao no Periodo RS", f"Brasil, {prod}", v)

    gas = df[df["NomeProduto"] == "Gasolina"]
    nacional = var_periodo(gas)
    for uf in ("SP", "RJ", "AM", "MS"):
        loc = var_periodo(gas[gas["UF"] == uf])
        add(f"Variacao no Periodo RS · {uf} Gasolina", "Variacao",
            evaluate("[Variacao no Periodo RS]", [f_uf(uf), f_prod("Gasolina")]),
            loc, TOL_RS)
        t = (loc / nacional) if loc is not None and nacional else None
        add(f"Transmissao vs Nacional % · {uf}", "Transmissao",
            evaluate("[Transmissao vs Nacional %]", [f_uf(uf), f_prod("Gasolina")]),
            t, TOL_PCT)
        linha("Transmissao vs Nacional %", f"UF = {uf}, Gasolina", t, "{:.1%}")

    # --- 6. Eventos --------------------------------------------------------
    ev = pd.read_csv(cfg.DIR_PROCESSED / "Fato_Evento_Preco.csv", encoding="utf-8-sig")
    tabela("6. Eventos de preço")
    add("N Eventos de Preco", "Eventos", evaluate("[N Eventos de Preco]"),
        int(len(ev)), TOL_INT)
    linha("N Eventos de Preco", "sem filtro", len(ev), "{:,.0f}")
    for prod, g in ev.groupby("NomeProduto"):
        add(f"N Eventos · {prod}", "Eventos",
            evaluate("[N Eventos de Preco]", [f_prod(prod)]), int(len(g)), TOL_INT)
        linha("N Eventos de Preco", f"Produto = {prod}", len(g), "{:,.0f}")

    # --- Gravacao ----------------------------------------------------------
    (cfg.DIR_DOCS / "valores-esperados.md").write_text("\n".join(md), encoding="utf-8")
    (cfg.DIR_DOCS / "testes-dax.json").write_text(
        json.dumps({"gerado_de": "src/step05_validate.py",
                    "base_coletas": len(df),
                    "testes": testes}, indent=2, ensure_ascii=False),
        encoding="utf-8")

    print(f"Etapa 5 - {len(testes)} testes gerados")
    for grupo in dict.fromkeys(t["grupo"] for t in testes):
        n = sum(1 for t in testes if t["grupo"] == grupo)
        print(f"  {grupo:<14} {n:>2}")
    print(f"  -> docs/testes-dax.json")
    print(f"  -> docs/valores-esperados.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
