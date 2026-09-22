"""Etapa 4 - Deteccao de eventos de preco e achados analiticos.

Por que detectar eventos a partir do dado, e nao de uma lista digitada de
comunicados da Petrobras:

  1. Nao existe feed publico e estruturado dos reajustes de refinaria.
     Transcrever datas a mao introduz erro nao auditavel no projeto.
  2. O que interessa ao consumidor e ao regulador e o movimento que
     efetivamente chegou a bomba. Partir do anuncio pressupoe justamente
     o que a analise deveria medir.

Metodo: mediana nacional semanal por produto -> variacao semanal ->
z-score robusto (MAD). Semana e o grao correto porque a coleta da ANP se
concentra em segunda e terca; uma serie diaria mediria o calendario de
campo da agencia, nao o mercado.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
import config as cfg

Z_MINIMO = 2.5        # desvios robustos
DELTA_MINIMO = 0.03   # R$/litro - abaixo disso e ruido de arredondamento


def carregar() -> pd.DataFrame:
    p = cfg.DIR_PROCESSED
    fato = pd.read_csv(p / "Fato_Coleta.csv", parse_dates=["Data"], encoding="utf-8-sig")
    dp = pd.read_csv(p / "Dim_Produto.csv", encoding="utf-8-sig")
    dg = pd.read_csv(p / "Dim_Geografia.csv", encoding="utf-8-sig")
    dc = pd.read_csv(p / "Dim_Calendario.csv", parse_dates=["Data", "InicioSemana"],
                     encoding="utf-8-sig")
    return (fato.merge(dp[["SK_Produto", "NomeProduto"]], on="SK_Produto")
                .merge(dg[["SK_Municipio", "UF", "NomeRegiao", "Municipio"]], on="SK_Municipio")
                .merge(dc[["Data", "InicioSemana", "AnoSemanaISO"]], on="Data"))


def serie_semanal(df, chaves) -> pd.DataFrame:
    return (df.groupby(chaves + ["InicioSemana"], as_index=False)
              .agg(PrecoMediano=("Preco", "median"),
                   Coletas=("Preco", "size"),
                   Postos=("SK_Revenda", "nunique")))


def detectar_eventos(nac: pd.DataFrame) -> pd.DataFrame:
    eventos = []
    for produto, g in nac.groupby("NomeProduto"):
        g = g.sort_values("InicioSemana").reset_index(drop=True)
        delta = g["PrecoMediano"].diff()

        mad = (delta - delta.median()).abs().median()
        escala = 1.4826 * mad if mad > 0 else delta.std(ddof=0)
        z = (delta - delta.median()) / escala

        sel = (z.abs() >= Z_MINIMO) & (delta.abs() >= DELTA_MINIMO)
        for i in g.index[sel]:
            eventos.append({
                "Data": g.loc[i, "InicioSemana"],
                "NomeProduto": produto,
                "PrecoAntes": round(g.loc[i - 1, "PrecoMediano"], 3),
                "PrecoDepois": round(g.loc[i, "PrecoMediano"], 3),
                "DeltaRS": round(delta[i], 3),
                "DeltaPct": round(delta[i] / g.loc[i - 1, "PrecoMediano"] * 100, 2),
                "ZRobusto": round(z[i], 2),
                "Direcao": "Alta" if delta[i] > 0 else "Baixa",
            })

    ev = pd.DataFrame(eventos).sort_values(["NomeProduto", "Data"]).reset_index(drop=True)
    ev.insert(0, "SK_Evento", range(1, len(ev) + 1))
    return ev


def paridade(df: pd.DataFrame) -> pd.DataFrame:
    """Razao etanol/gasolina por UF e semana. Abaixo de 0,70 o etanol compensa."""
    s = serie_semanal(df[df["NomeProduto"].isin(["Etanol", "Gasolina"])], ["UF", "NomeProduto"])
    w = s.pivot_table(index=["UF", "InicioSemana"], columns="NomeProduto",
                      values="PrecoMediano").dropna().reset_index()
    w["Paridade"] = w["Etanol"] / w["Gasolina"]
    w["EtanolCompensa"] = w["Paridade"] < cfg.LIMIAR_PARIDADE
    return w


def main() -> int:
    df = carregar()
    print(f"Etapa 4 - analise sobre {len(df):,} coletas\n")

    nac = serie_semanal(df, ["NomeProduto"])
    ev = detectar_eventos(nac)

    # Chave substituta do produto: permite relacionar Fato_Evento_Preco a
    # Dim_Produto por inteiro, em vez de por texto.
    dp = pd.read_csv(cfg.DIR_PROCESSED / "Dim_Produto.csv", encoding="utf-8-sig")
    ev = ev.merge(dp[["SK_Produto", "NomeProduto"]], on="NomeProduto", how="left")
    if ev["SK_Produto"].isna().any():
        raise ValueError("evento sem produto correspondente em Dim_Produto")
    ev["SK_Produto"] = ev["SK_Produto"].astype(int)
    ev = ev[["SK_Evento", "Data", "SK_Produto", "NomeProduto", "PrecoAntes",
             "PrecoDepois", "DeltaRS", "DeltaPct", "ZRobusto", "Direcao"]]

    ev.to_csv(cfg.DIR_PROCESSED / "Fato_Evento_Preco.csv", index=False,
              encoding="utf-8-sig", date_format="%Y-%m-%d")

    print(f"  Eventos de preco detectados: {len(ev)}")
    print(ev[["Data", "NomeProduto", "PrecoAntes", "PrecoDepois",
              "DeltaRS", "DeltaPct", "Direcao"]].to_string(index=False))

    # --- Achados -----------------------------------------------------------
    linhas = ["# Achados quantitativos", "",
              f"Base: {len(df):,} coletas da ANP, "
              f"{df['Data'].min():%d/%m/%Y} a {df['Data'].max():%d/%m/%Y}.", ""]

    linhas.append("## 1. Variacao de preco no periodo\n")
    for produto, g in nac.groupby("NomeProduto"):
        g = g.sort_values("InicioSemana")
        ini, fim = g["PrecoMediano"].iloc[0], g["PrecoMediano"].iloc[-1]
        linhas.append(f"- **{produto}**: R$ {ini:.3f} -> R$ {fim:.3f} "
                      f"({(fim/ini-1)*100:+.1f}%), minima R$ {g['PrecoMediano'].min():.3f}, "
                      f"maxima R$ {g['PrecoMediano'].max():.3f}")

    linhas += ["", "## 2. Dispersao entre postos (ultimas 8 semanas)\n"]
    recente = df[df["InicioSemana"] >= df["InicioSemana"].max() - pd.Timedelta(weeks=8)]
    disp = (recente.groupby(["NomeProduto", "UF"])["Preco"]
                   .agg(p10=lambda s: s.quantile(.10), p90=lambda s: s.quantile(.90),
                        mediana="median", postos="size").reset_index())
    disp["Amplitude"] = disp["p90"] - disp["p10"]
    for produto, g in disp.groupby("NomeProduto"):
        g = g[g["postos"] >= 100].sort_values("Amplitude", ascending=False)
        if g.empty:
            continue
        top, bot = g.iloc[0], g.iloc[-1]
        linhas.append(f"- **{produto}**: maior dispersao em **{top['UF']}** "
                      f"(P90-P10 = R$ {top['Amplitude']:.2f}), menor em **{bot['UF']}** "
                      f"(R$ {bot['Amplitude']:.2f})")

    linhas += ["", "## 3. Paridade etanol/gasolina\n"]
    par = paridade(df)
    por_uf = (par.groupby("UF")
                 .agg(ParidadeMedia=("Paridade", "mean"),
                      PctSemanasCompensa=("EtanolCompensa", "mean"),
                      Semanas=("Paridade", "size"))
                 .sort_values("ParidadeMedia").reset_index())
    por_uf["PctSemanasCompensa"] *= 100
    linhas.append(f"Limiar de {cfg.LIMIAR_PARIDADE:.0%}. "
                  f"Media nacional da razao: **{par['Paridade'].mean():.1%}**. "
                  f"O etanol compensou em **{par['EtanolCompensa'].mean():.1%}** "
                  f"das combinacoes UF-semana.\n")
    linhas.append("UFs onde o etanol mais compensa:\n")
    linhas.append("| UF | Paridade media | % semanas < 70% |")
    linhas.append("|----|----------------|-----------------|")
    for _, r in por_uf.head(6).iterrows():
        linhas.append(f"| {r['UF']} | {r['ParidadeMedia']:.1%} | {r['PctSemanasCompensa']:.0f}% |")
    linhas.append("\nUFs onde quase nunca compensa:\n")
    linhas.append("| UF | Paridade media | % semanas < 70% |")
    linhas.append("|----|----------------|-----------------|")
    for _, r in por_uf.tail(6).iterrows():
        linhas.append(f"| {r['UF']} | {r['ParidadeMedia']:.1%} | {r['PctSemanasCompensa']:.0f}% |")

    linhas += ["", "## 4. Cobertura da coleta\n",
               f"- Postos distintos: {df['SK_Revenda'].nunique():,}",
               f"- Municipios: {df.groupby(['UF','Municipio']).ngroups} de ~5.570 no pais "
               f"(**{df.groupby(['UF','Municipio']).ngroups/5570:.1%}**) "
               f"[contagem por UF+nome: Valenca existe na BA e no RJ]",
               f"- Semanas cobertas: {df['InicioSemana'].nunique()}"]

    par.to_csv(cfg.DIR_PROCESSED / "Aux_Paridade_UF_Semana.csv", index=False,
               encoding="utf-8-sig", date_format="%Y-%m-%d")
    (cfg.DIR_OUTPUTS / "achados.md").write_text("\n".join(linhas), encoding="utf-8")

    print("\n" + "\n".join(linhas[3:]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
