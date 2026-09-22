"""Etapa 5 - Valores esperados para conferencia das medidas DAX.

Uma medida DAX so esta certa quando alguem confere. Este script calcula
em pandas o que cada medida-chave deve devolver em recortes especificos.
Ao montar o relatorio, reproduza o recorte e compare o numero.

Divergencia aqui significa erro de contexto de filtro no DAX - quase
sempre falta de REMOVEFILTERS ou ALLSELECTED.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
import config as cfg

MIN_POSTOS = 30
MIN_COLETAS = 10


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
    return s.median() if len(s) >= MIN_COLETAS else None


def main() -> int:
    df = carregar()
    L: list[str] = []

    def secao(t):
        L.extend(["", f"## {t}", ""])

    def linha(medida, recorte, valor, fmt="{:.4f}"):
        v = "BLANK" if valor is None or pd.isna(valor) else fmt.format(valor)
        L.append(f"| {medida} | {recorte} | `{v}` |")

    def cabecalho():
        L.append("| Medida | Recorte | Valor esperado |")
        L.append("|--------|---------|----------------|")

    L.append("# Valores esperados para conferencia do DAX")
    L.append("")
    L.append("Reproduza cada recorte no Power BI e compare. Divergencia "
             "indica erro de contexto de filtro, nao de dados.")
    L.append("")
    L.append(f"Base: {len(df):,} coletas | "
             f"{df['Data'].min():%d/%m/%Y} a {df['Data'].max():%d/%m/%Y}")

    # --- 1. Medidas base, sem filtro --------------------------------------
    secao("1. Sem nenhum filtro (total geral)")
    cabecalho()
    linha("Coletas", "todos", len(df), "{:,.0f}")
    linha("Postos Distintos", "todos", df["SK_Revenda"].nunique(), "{:,.0f}")
    linha("Municipios Distintos", "todos", df["SK_Municipio"].nunique(), "{:,.0f}")
    linha("Preco Mediano", "todos os produtos juntos", df["Preco"].median())
    linha("Preco Medio", "todos os produtos juntos", df["Preco"].mean())

    # --- 2. Por produto ----------------------------------------------------
    secao("2. Filtro: um produto, periodo completo")
    cabecalho()
    for prod, g in df.groupby("NomeProduto"):
        linha("Preco Mediano", f"Produto = {prod}", g["Preco"].median())
    for prod, g in df.groupby("NomeProduto"):
        linha("Amplitude P90-P10", f"Produto = {prod}",
              g["Preco"].quantile(.90) - g["Preco"].quantile(.10))

    # --- 3. Guarda de amostra ----------------------------------------------
    secao("3. Guarda de amostra pequena (deve devolver BLANK)")
    L.append("A medida `Amplitude P90-P10` exige 30 postos distintos. "
             "Roraima tem 15, entao deve ficar em branco - e nao aparecer "
             "como o mercado mais homogeneo do pais.")
    L.append("")
    cabecalho()
    ult8 = df[df["InicioSemana"] >= df["InicioSemana"].max() - pd.Timedelta(weeks=8)]
    for uf in ("RR", "AC", "SP"):
        g = ult8[(ult8["UF"] == uf) & (ult8["NomeProduto"] == "Gasolina")]
        postos = g["SK_Revenda"].nunique()
        amp = (g["Preco"].quantile(.90) - g["Preco"].quantile(.10)
               if postos >= MIN_POSTOS else None)
        linha("Amplitude P90-P10", f"UF = {uf}, Gasolina, ultimas 8 semanas "
                                   f"({postos} postos)", amp)

    # --- 4. Paridade -------------------------------------------------------
    secao("4. Paridade Etanol/Gasolina")
    L.append("Estas medidas usam `REMOVEFILTERS(Dim_Produto)`. Devem "
             "devolver o MESMO valor com o slicer de produto em "
             "'Gasolina', em 'Etanol' ou sem selecao. Se mudarem, "
             "o REMOVEFILTERS nao foi aplicado.")
    L.append("")
    cabecalho()
    for uf in ("SP", "MS", "AP", "RS"):
        g = df[df["UF"] == uf]
        e = mediana_guardada(g[g["NomeProduto"] == "Etanol"]["Preco"])
        s = mediana_guardada(g[g["NomeProduto"] == "Gasolina"]["Preco"])
        linha("Paridade Etanol/Gasolina", f"UF = {uf}, periodo completo",
              (e / s) if e and s else None)

    nac_e = df[df["NomeProduto"] == "Etanol"]["Preco"].median()
    nac_g = df[df["NomeProduto"] == "Gasolina"]["Preco"].median()
    linha("Paridade Etanol/Gasolina", "Brasil, periodo completo", nac_e / nac_g)

    # --- 5. Variacao no periodo e transmissao ------------------------------
    secao("5. Variacao no periodo e transmissao")
    L.append("Primeira e ultima semana ISO da janela completa.")
    L.append("")
    cabecalho()

    sem_min, sem_max = df["InicioSemana"].min(), df["InicioSemana"].max()

    def var_periodo(sub: pd.DataFrame) -> float | None:
        ini = mediana_guardada(sub[sub["InicioSemana"] == sem_min]["Preco"])
        fim = mediana_guardada(sub[sub["InicioSemana"] == sem_max]["Preco"])
        return (fim - ini) if ini is not None and fim is not None else None

    for prod in sorted(df["NomeProduto"].unique()):
        p = df[df["NomeProduto"] == prod]
        linha("Variacao no Periodo RS", f"Brasil, {prod}", var_periodo(p))

    gas = df[df["NomeProduto"] == "Gasolina"]
    nacional = var_periodo(gas)
    L.append("")
    cabecalho()
    for uf in ("SP", "RJ", "AM", "MS"):
        local = var_periodo(gas[gas["UF"] == uf])
        linha("Variacao no Periodo RS", f"UF = {uf}, Gasolina", local)
        linha("Transmissao vs Nacional %", f"UF = {uf}, Gasolina",
              (local / nacional) if local is not None and nacional else None,
              "{:.1%}")

    # --- 6. Tempo ----------------------------------------------------------
    secao("6. Variacao semanal (ultima semana com dados)")
    cabecalho()
    penultima = sorted(df["InicioSemana"].unique())[-2]
    for prod in sorted(df["NomeProduto"].unique()):
        p = df[df["NomeProduto"] == prod]
        a = mediana_guardada(p[p["InicioSemana"] == sem_max]["Preco"])
        b = mediana_guardada(p[p["InicioSemana"] == penultima]["Preco"])
        linha("Variacao Semanal RS", f"{prod}, semana de {sem_max:%d/%m/%Y}",
              (a - b) if a is not None and b is not None else None)

    caminho = cfg.DIR_DOCS / "valores-esperados.md"
    caminho.write_text("\n".join(L), encoding="utf-8")
    print("\n".join(L))
    print(f"\n-> {caminho}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
