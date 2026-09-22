"""Etapa 2 - Limpeza, minimizacao de dados e auditoria de qualidade.

Principios aplicados:

1. MINIMIZACAO NA ORIGEM. Colunas de endereco e CNPJ sao descartadas no
   momento da leitura, nao depois. O CNPJ e substituido por um hash
   estavel: preserva o grao analitico (contar postos distintos, seguir um
   posto ao longo do tempo) sem distribuir um cadastro identificavel.

2. AUDITORIA. Toda linha descartada e contabilizada por motivo. Um
   pipeline que descarta dados em silencio nao e confiavel.

3. FALHA VISIVEL. Divergencia de schema aborta a etapa em vez de produzir
   um resultado silenciosamente errado.
"""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
import config as cfg

# Colunas descartadas na leitura - endereco e identificacao do posto.
COLS_PII = ["Nome da Rua", "Numero Rua", "Complemento", "Bairro", "Cep"]

COLS_ESPERADAS = [
    "Regiao - Sigla", "Estado - Sigla", "Municipio", "Revenda",
    "CNPJ da Revenda", "Nome da Rua", "Numero Rua", "Complemento",
    "Bairro", "Cep", "Produto", "Data da Coleta", "Valor de Venda",
    "Valor de Compra", "Unidade de Medida", "Bandeira",
]

# Sal fixo: o hash precisa ser estavel entre execucoes para que um posto
# mantenha o mesmo ID. Nao e segredo criptografico, e pseudonimizacao.
SAL = "anp-precos-2026"


def _hash_posto(cnpj: pd.Series) -> pd.Series:
    limpo = cnpj.fillna("").str.replace(r"\D", "", regex=True)
    return limpo.map(
        lambda c: hashlib.sha256((SAL + c).encode()).hexdigest()[:12] if c else "DESCONHECIDO"
    )


def ler_bruto(caminho: Path) -> pd.DataFrame:
    df = pd.read_csv(caminho, sep=";", dtype=str, encoding="utf-8-sig")

    faltando = set(COLS_ESPERADAS) - set(df.columns)
    if faltando:
        raise ValueError(f"{caminho.name}: schema divergente, faltam {sorted(faltando)}")

    df["ID_Revenda"] = _hash_posto(df["CNPJ da Revenda"])
    return df.drop(columns=COLS_PII + ["CNPJ da Revenda"])


def limpar(df: pd.DataFrame, auditoria: dict) -> pd.DataFrame:
    def registrar(motivo: str, n: int):
        auditoria[motivo] = auditoria.get(motivo, 0) + int(n)

    auditoria["00_lidas"] = auditoria.get("00_lidas", 0) + len(df)

    df = df.rename(columns={
        "Regiao - Sigla": "Regiao", "Estado - Sigla": "UF",
        "Data da Coleta": "Data", "Valor de Venda": "Preco",
        "Unidade de Medida": "Unidade",
    })

    # Produto: normaliza espacos e descarta o que esta fora de escopo.
    df["Produto"] = df["Produto"].str.strip().str.upper()
    antes = len(df)
    df = df[df["Produto"].isin(cfg.PRODUTOS_ALVO)]
    registrar("01_produto_fora_escopo", antes - len(df))

    # Unidade: garante homogeneidade antes de qualquer media.
    antes = len(df)
    df = df[df["Unidade"].str.strip() == cfg.UNIDADE_ESPERADA]
    registrar("02_unidade_incompativel", antes - len(df))

    # Data: dd/mm/yyyy. Formato explicito para nao depender de inferencia.
    df["Data"] = pd.to_datetime(df["Data"], format="%d/%m/%Y", errors="coerce")
    antes = len(df)
    df = df[df["Data"].notna()]
    registrar("03_data_invalida", antes - len(df))

    # Preco: virgula decimal.
    df["Preco"] = pd.to_numeric(
        df["Preco"].str.strip().str.replace(",", ".", regex=False), errors="coerce"
    )
    antes = len(df)
    df = df[df["Preco"].notna()]
    registrar("04_preco_nao_numerico", antes - len(df))

    # Faixa de sanidade por produto.
    limites = df["Produto"].map(cfg.FAIXAS_PRECO)
    lo = limites.map(lambda t: t[0])
    hi = limites.map(lambda t: t[1])
    antes = len(df)
    df = df[(df["Preco"] >= lo) & (df["Preco"] <= hi)]
    registrar("05_preco_fora_faixa", antes - len(df))

    for c in ("Regiao", "UF", "Municipio", "Bandeira", "Revenda"):
        df[c] = df[c].str.strip().str.upper()
    df["Bandeira"] = df["Bandeira"].replace({"": "BRANCA"}).fillna("BRANCA")

    return df[["Data", "Regiao", "UF", "Municipio", "ID_Revenda",
               "Revenda", "Bandeira", "Produto", "Preco"]]


def main() -> int:
    arquivos = sorted(cfg.DIR_RAW.glob("*.csv"))
    if not arquivos:
        print("Nenhum arquivo em data/raw. Rode a etapa 1 primeiro.")
        return 1

    print(f"Etapa 2 - limpeza de {len(arquivos)} arquivos")
    auditoria: dict[str, int] = {}
    partes = []

    for i, caminho in enumerate(arquivos, 1):
        bruto = ler_bruto(caminho)
        limpo = limpar(bruto, auditoria)
        partes.append(limpo)
        print(f"  [{i:>2}/{len(arquivos)}] {caminho.name:<34} "
              f"{len(bruto):>7,} -> {len(limpo):>7,}")

    df = pd.concat(partes, ignore_index=True)

    # Uma coleta por posto/produto/dia. Coletas repetidas viram a media,
    # evitando que um posto pesquisado duas vezes pese o dobro na mediana.
    antes = len(df)
    df = (df.groupby(["Data", "Regiao", "UF", "Municipio", "ID_Revenda",
                      "Revenda", "Bandeira", "Produto"], as_index=False)["Preco"]
            .mean())
    auditoria["06_coletas_duplicadas_agregadas"] = antes - len(df)

    # Recorta exatamente a janela configurada.
    ini = pd.Timestamp(*cfg.MES_INICIO, 1)
    fim = (pd.Timestamp(*cfg.MES_FIM, 1) + pd.offsets.MonthEnd(0))
    antes = len(df)
    df = df[(df["Data"] >= ini) & (df["Data"] <= fim)]
    auditoria["07_fora_da_janela"] = antes - len(df)

    df = df.sort_values(["Data", "UF", "Produto"]).reset_index(drop=True)
    df.to_pickle(cfg.DIR_INTERIM / "coletas_limpas.pkl")

    lidas = auditoria.pop("00_lidas")
    print(f"\n  Auditoria de qualidade (base lida: {lidas:,} linhas)")
    for motivo in sorted(auditoria):
        n = auditoria[motivo]
        print(f"    {motivo:<34} {n:>9,}  ({n/lidas*100:5.2f}%)")
    print(f"    {'>> retidas':<34} {len(df):>9,}  ({len(df)/lidas*100:5.2f}%)")

    print(f"\n  Periodo:  {df['Data'].min():%Y-%m-%d} a {df['Data'].max():%Y-%m-%d}")
    print(f"  Postos:   {df['ID_Revenda'].nunique():,}")
    municipios = df.groupby(["UF", "Municipio"]).ngroups
    print(f"  Municipios: {municipios:,}   UFs: {df['UF'].nunique()}")
    # Contar so o nome subestima: Valenca existe na BA e no RJ.
    print(f"  Produtos: {dict(df['Produto'].value_counts())}")

    pd.Series(auditoria).to_csv(cfg.DIR_INTERIM / "auditoria_qualidade.csv",
                                header=["linhas_descartadas"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
