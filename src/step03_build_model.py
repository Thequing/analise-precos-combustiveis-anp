"""Etapa 3 - Construcao do esquema estrela para o Power BI.

Saida: CSVs em data/processed/, prontos para importacao via conector
Pasta. Chaves substitutas inteiras mantem o arquivo de fatos compacto e
as relacoes eficientes no VertiPaq.

Grao do fato: posto x produto x dia de coleta.
Esse grao e necessario - medidas de dispersao (P90-P10) exigem a
variancia entre postos. Agregar por municipio destruiria a analise.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
import config as cfg

NOMES_REGIAO = {
    "N": "Norte", "NE": "Nordeste", "CO": "Centro-Oeste",
    "SE": "Sudeste", "S": "Sul",
}

# Agrupamento de bandeiras. As quatro grandes distribuidoras mais a
# categoria BRANCA (posto sem contrato de bandeira) cobrem ~97% das
# coletas. O restante vira OUTRAS para nao poluir o eixo dos graficos.
#
# Nota factual importante: VIBRA e a antiga BR Distribuidora, desligada
# do grupo Petrobras em 2021. Ela compra da Petrobras, mas NAO e
# Petrobras. Tratar como se fosse seria erro material.
GRUPOS_BANDEIRA = {
    "BRANCA": "Branca (sem bandeira)",
    "VIBRA": "Vibra",
    "IPIRANGA": "Ipiranga",
    "RAIZEN": "Raizen",
    "ALE": "Ale",
}

CATEGORIAS_PRODUTO = {
    "GASOLINA": ("Gasolina", "Fossil"),
    "ETANOL": ("Etanol", "Renovavel"),
    "DIESEL S10": ("Diesel S10", "Fossil"),
}

MESES_PT = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun",
            "Jul", "Ago", "Set", "Out", "Nov", "Dez"]
DIAS_PT = ["Segunda", "Terca", "Quarta", "Quinta", "Sexta", "Sabado", "Domingo"]


def dim_calendario(dmin: pd.Timestamp, dmax: pd.Timestamp) -> pd.DataFrame:
    # A tabela de datas cobre semanas ISO inteiras, mesmo que a coleta
    # comece ou termine no meio de uma. Uma tabela de datas com buracos
    # quebra DATEADD e invalida toda a inteligencia temporal.
    inicio = dmin - pd.Timedelta(days=int(dmin.dayofweek))
    fim = dmax + pd.Timedelta(days=6 - int(dmax.dayofweek))

    d = pd.DataFrame({"Data": pd.date_range(inicio, fim, freq="D")})
    iso = d["Data"].dt.isocalendar()

    d["Ano"] = d["Data"].dt.year
    d["Mes"] = d["Data"].dt.month
    d["NomeMes"] = d["Mes"].map(lambda m: MESES_PT[m - 1])
    d["AnoMes"] = d["Ano"] * 100 + d["Mes"]                      # ordenavel
    d["AnoMesNome"] = d["NomeMes"] + "/" + d["Ano"].astype(str).str[-2:]
    d["Trimestre"] = "T" + d["Data"].dt.quarter.astype(str)
    d["AnoTrimestre"] = d["Ano"].astype(str) + "-" + d["Trimestre"]
    d["SemanaISO"] = iso["week"].astype(int)
    d["AnoSemanaISO"] = iso["year"].astype(int) * 100 + d["SemanaISO"]
    # Segunda-feira da semana ISO: eixo temporal real da analise, ja que
    # a coleta da ANP se concentra no inicio da semana.
    d["InicioSemana"] = d["Data"] - pd.to_timedelta(d["Data"].dt.dayofweek, unit="D")
    d["DiaSemanaNum"] = d["Data"].dt.dayofweek
    d["NomeDiaSemana"] = d["DiaSemanaNum"].map(lambda i: DIAS_PT[i])
    d["EhFimDeSemana"] = d["DiaSemanaNum"] >= 5

    # Uma semana so e comparavel se a coleta cobriu seus dias uteis. A
    # ultima semana da janela costuma ter um unico dia, o que faz a
    # variacao semanal parecer nula quando na verdade falta dado.
    # O relatorio filtra por esta coluna em vez de exibir um numero falso.
    uteis = d.loc[~d["EhFimDeSemana"]].copy()
    uteis["NoIntervalo"] = uteis["Data"].between(dmin, dmax)
    cobertura = uteis.groupby("InicioSemana")["NoIntervalo"].sum()
    d["DiasUteisComDados"] = d["InicioSemana"].map(cobertura).fillna(0).astype(int)
    d["EhSemanaCompleta"] = d["DiasUteisComDados"] >= 5
    return d


def main() -> int:
    origem = cfg.DIR_INTERIM / "coletas_limpas.pkl"
    if not origem.exists():
        print("Rode a etapa 2 primeiro.")
        return 1

    df = pd.read_pickle(origem)
    print(f"Etapa 3 - modelagem a partir de {len(df):,} coletas")

    # --- Dim_Produto ------------------------------------------------------
    dp = pd.DataFrame(
        [(p, *CATEGORIAS_PRODUTO[p]) for p in sorted(df["Produto"].unique())],
        columns=["Produto", "NomeProduto", "Origem"],
    )
    dp.insert(0, "SK_Produto", range(1, len(dp) + 1))
    dp["Unidade"] = cfg.UNIDADE_ESPERADA

    # --- Dim_Geografia ----------------------------------------------------
    dg = (df[["Regiao", "UF", "Municipio"]].drop_duplicates()
            .sort_values(["Regiao", "UF", "Municipio"]).reset_index(drop=True))
    dg.insert(0, "SK_Municipio", range(1, len(dg) + 1))
    dg["NomeRegiao"] = dg["Regiao"].map(NOMES_REGIAO)
    dg["UF_Municipio"] = dg["Municipio"] + " / " + dg["UF"]

    # --- Dim_Bandeira -----------------------------------------------------
    db = pd.DataFrame({"Bandeira": sorted(df["Bandeira"].unique())})
    db["GrupoBandeira"] = db["Bandeira"].map(GRUPOS_BANDEIRA).fillna("Outras")
    db["EhBandeiraBranca"] = db["Bandeira"].eq("BRANCA")
    db.insert(0, "SK_Bandeira", range(1, len(db) + 1))

    # --- Dim_Revenda ------------------------------------------------------
    dr = (df.sort_values("Data")
            .groupby("ID_Revenda", as_index=False)
            .agg(NomeRevenda=("Revenda", "last")))
    dr.insert(0, "SK_Revenda", range(1, len(dr) + 1))

    # --- Fato_Coleta ------------------------------------------------------
    f = (df.merge(dp[["SK_Produto", "Produto"]], on="Produto")
           .merge(dg[["SK_Municipio", "Regiao", "UF", "Municipio"]],
                  on=["Regiao", "UF", "Municipio"])
           .merge(db[["SK_Bandeira", "Bandeira"]], on="Bandeira")
           .merge(dr[["SK_Revenda", "ID_Revenda"]], on="ID_Revenda"))

    if len(f) != len(df):
        raise ValueError(f"perda de linhas no join: {len(df):,} -> {len(f):,}")

    fato = f[["Data", "SK_Produto", "SK_Municipio", "SK_Bandeira",
              "SK_Revenda", "Preco"]].sort_values(["Data", "SK_Produto"])
    fato["Preco"] = fato["Preco"].round(3)

    dc = dim_calendario(fato["Data"].min(), fato["Data"].max())

    # --- Gravacao ---------------------------------------------------------
    saidas = {
        "Dim_Calendario": dc, "Dim_Produto": dp, "Dim_Geografia": dg,
        "Dim_Bandeira": db, "Dim_Revenda": dr, "Fato_Coleta": fato,
    }
    print()
    for nome, tab in saidas.items():
        caminho = cfg.DIR_PROCESSED / f"{nome}.csv"
        tab.to_csv(caminho, index=False, encoding="utf-8-sig",
                   date_format="%Y-%m-%d")
        mb = caminho.stat().st_size / 1e6
        print(f"  {nome:<16} {len(tab):>9,} linhas  {len(tab.columns):>2} col  {mb:7.1f} MB")

    # --- Verificacoes de integridade referencial --------------------------
    print("\n  Integridade referencial:")
    checagens = [
        ("SK_Produto",    fato["SK_Produto"],    dp["SK_Produto"]),
        ("SK_Municipio",  fato["SK_Municipio"],  dg["SK_Municipio"]),
        ("SK_Bandeira",   fato["SK_Bandeira"],   db["SK_Bandeira"]),
        ("SK_Revenda",    fato["SK_Revenda"],    dr["SK_Revenda"]),
    ]
    ok = True
    for nome, chaves_fato, chaves_dim in checagens:
        orfas = set(chaves_fato.unique()) - set(chaves_dim.unique())
        ok &= not orfas
        print(f"    {nome:<14} orfas: {len(orfas)}")
    faltam_datas = set(fato["Data"].unique()) - set(dc["Data"].unique())
    ok &= not faltam_datas
    print(f"    {'Data':<14} orfas: {len(faltam_datas)}")
    print(f"\n  {'OK - modelo integro' if ok else 'FALHA - chaves orfas'}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
