"""Etapa 6 - Geracao do dicionario de dados.

O dicionario e gerado a partir dos arquivos reais, nao escrito a mao.
Tipo, cardinalidade e exemplo saem do dado; apenas a descricao de
negocio e curada. Assim o documento nao diverge do modelo com o tempo.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
import config as cfg

PAPEL = {
    "Dim_Calendario": ("Dimensao", "Tabela de datas. Marcar como Tabela de Datas no Power BI."),
    "Dim_Produto": ("Dimensao", "Combustiveis analisados."),
    "Dim_Geografia": ("Dimensao", "Hierarquia Regiao > UF > Municipio."),
    "Dim_Bandeira": ("Dimensao", "Bandeira do posto (distribuidora contratada)."),
    "Dim_Revenda": ("Dimensao", "Posto revendedor, pseudonimizado."),
    "Fato_Coleta": ("Fato", "Grao: posto x produto x dia de coleta."),
    "Fato_Evento_Preco": ("Fato", "Quebras estruturais detectadas na serie semanal nacional."),
    "Aux_Paridade_UF_Semana": ("Auxiliar", "Conferencia do DAX. Nao carregar no modelo final."),
}

DESCRICOES = {
    # Dim_Calendario
    "Data": "Data do calendario. Chave da relacao com os fatos.",
    "Ano": "Ano civil.",
    "Mes": "Numero do mes (1-12).",
    "NomeMes": "Abreviacao do mes em portugues.",
    "AnoMes": "Ano e mes como inteiro (202601). Usar para ordenar AnoMesNome.",
    "AnoMesNome": "Rotulo de exibicao (Jan/26).",
    "Trimestre": "Trimestre (T1-T4).",
    "AnoTrimestre": "Ano e trimestre (2026-T1).",
    "SemanaISO": "Numero da semana ISO 8601.",
    "AnoSemanaISO": "Ano e semana ISO como inteiro. Usar para ordenar.",
    "InicioSemana": "Segunda-feira da semana ISO. EIXO TEMPORAL PRINCIPAL da analise.",
    "DiaSemanaNum": "0 = segunda, 6 = domingo.",
    "NomeDiaSemana": "Dia da semana em portugues.",
    "EhFimDeSemana": "Verdadeiro para sabado e domingo.",
    "DiasUteisComDados": "Dias uteis da semana cobertos pela janela de coleta (0-5).",
    "EhSemanaCompleta": "Falso quando a semana tem menos de 5 dias uteis com dados. FILTRAR em analises de variacao semanal.",
    # Dim_Produto
    "SK_Produto": "Chave substituta do produto.",
    "Produto": "Nome do produto como publicado pela ANP.",
    "NomeProduto": "Nome tratado para exibicao.",
    "Origem": "Fossil ou Renovavel.",
    "Unidade": "Unidade de medida. Homogenea por construcao (R$ / litro).",
    # Dim_Geografia
    "SK_Municipio": "Chave substituta do municipio.",
    "Regiao": "Sigla da regiao (N, NE, CO, SE, S).",
    "UF": "Sigla da unidade da federacao.",
    "Municipio": "Nome do municipio em caixa alta, como publicado.",
    "NomeRegiao": "Nome da regiao por extenso.",
    "UF_Municipio": "Rotulo composto para desambiguar municipios homonimos.",
    # Dim_Bandeira
    "SK_Bandeira": "Chave substituta da bandeira.",
    "Bandeira": "Bandeira como publicada pela ANP.",
    "GrupoBandeira": "Agrupamento das 5 maiores; demais viram Outras.",
    "EhBandeiraBranca": "Verdadeiro para posto sem contrato de exclusividade.",
    # Dim_Revenda
    "SK_Revenda": "Chave substituta do posto.",
    "ID_Revenda": "Hash SHA-256 truncado do CNPJ. Pseudonimo estavel; o CNPJ nao e armazenado.",
    "NomeRevenda": "Razao social do posto, conforme publicado pela ANP.",
    # Fato_Coleta
    "SK_Bandeira ": "Chave da bandeira.",
    "Preco": "Preco de venda ao consumidor, R$/litro.",
    # Fato_Evento_Preco
    "SK_Evento": "Chave substituta do evento.",
    "PrecoAntes": "Mediana nacional na semana anterior ao evento.",
    "PrecoDepois": "Mediana nacional na semana do evento.",
    "DeltaRS": "Variacao em R$/litro.",
    "DeltaPct": "Variacao percentual.",
    "ZRobusto": "Z-score robusto (MAD) da variacao semanal. Modulo maior ou igual a 2,5 define o evento.",
    # Descricoes especificas por tabela vencem a global de mesmo nome.
    "Fato_Coleta.Data": "Data da coleta de preco pela ANP.",
    "Fato_Evento_Preco.Data": "Segunda-feira da semana ISO em que a quebra foi detectada.",
    "Aux_Paridade_UF_Semana.InicioSemana": "Segunda-feira da semana ISO.",
    "Direcao": "Alta ou Baixa.",
    # Aux
    "Etanol": "Mediana semanal do etanol na UF.",
    "Gasolina": "Mediana semanal da gasolina na UF.",
    "Paridade": "Razao etanol / gasolina.",
    "EtanolCompensa": "Verdadeiro quando a paridade fica abaixo de 0,70.",
}

TIPO_PT = {"int64": "Inteiro", "float64": "Decimal", "bool": "Booleano",
           "object": "Texto", "datetime64[ns]": "Data"}


def descrever(nome: str, df: pd.DataFrame) -> list[str]:
    papel, nota = PAPEL.get(nome, ("", ""))
    L = [f"### `{nome}`", "",
         f"**{papel}** — {nota}", "",
         f"{len(df):,} linhas · {len(df.columns)} colunas", "",
         "| Coluna | Tipo | Distintos | Exemplo | Descrição |",
         "|--------|------|----------:|---------|-----------|"]

    for c in df.columns:
        s = df[c]
        tipo = TIPO_PT.get(str(s.dtype), str(s.dtype))
        distintos = s.nunique()
        amostra = s.dropna()
        exemplo = "—"
        if len(amostra):
            v = amostra.iloc[0]
            exemplo = f"{v:%d/%m/%Y}" if isinstance(v, pd.Timestamp) else str(v)
            if len(exemplo) > 28:
                exemplo = exemplo[:25] + "..."
        desc = DESCRICOES.get(f"{nome}.{c}") or DESCRICOES.get(c, "")
        # Pipes quebram a tabela markdown.
        desc = desc.replace("|", "\\|")
        L.append(f"| `{c}` | {tipo} | {distintos:,} | `{exemplo}` | {desc} |")

    L.append("")
    return L


def main() -> int:
    ordem = ["Fato_Coleta", "Fato_Evento_Preco", "Dim_Calendario", "Dim_Produto",
             "Dim_Geografia", "Dim_Bandeira", "Dim_Revenda", "Aux_Paridade_UF_Semana"]

    L = ["# Dicionário de dados", "",
         "Gerado automaticamente a partir de `data/processed/` por "
         "`src/step06_dictionary.py`. Não editar à mão — reexecutar.", "",
         "Todos os arquivos: CSV, separador vírgula, decimal ponto, "
         "codificação UTF-8 com BOM.", ""]

    for nome in ordem:
        caminho = cfg.DIR_PROCESSED / f"{nome}.csv"
        if not caminho.exists():
            continue
        # Arquivo inteiro: cardinalidade calculada sobre amostra seria
        # simplesmente errada num dicionario de dados.
        df = pd.read_csv(caminho, encoding="utf-8-sig")
        for c in ("Data", "InicioSemana"):
            if c in df.columns:
                df[c] = pd.to_datetime(df[c], errors="coerce")
        L += descrever(nome, df)

    L += ["---", "", "## Relações do modelo", "",
          "| De | Para | Cardinalidade | Direção |",
          "|----|------|---------------|---------|",
          "| `Dim_Calendario[Data]` | `Fato_Coleta[Data]` | 1:N | Única |",
          "| `Dim_Produto[SK_Produto]` | `Fato_Coleta[SK_Produto]` | 1:N | Única |",
          "| `Dim_Geografia[SK_Municipio]` | `Fato_Coleta[SK_Municipio]` | 1:N | Única |",
          "| `Dim_Bandeira[SK_Bandeira]` | `Fato_Coleta[SK_Bandeira]` | 1:N | Única |",
          "| `Dim_Revenda[SK_Revenda]` | `Fato_Coleta[SK_Revenda]` | 1:N | Única |",
          "| `Dim_Calendario[Data]` | `Fato_Evento_Preco[Data]` | 1:N | Única |",
          "| `Dim_Produto[SK_Produto]` | `Fato_Evento_Preco[SK_Produto]` | 1:N | Única |",
          "",
          "Nenhuma relação bidirecional. Nenhuma relação inativa.", "",
          "## Colunas a ocultar no modelo", "",
          "Todas as `SK_*` no fato e nas dimensões, `ID_Revenda`, "
          "`DiaSemanaNum`, `AnoMes`, `AnoSemanaISO` e `DiasUteisComDados`. "
          "São chaves e auxiliares de ordenação: úteis ao modelo, ruído "
          "no painel de campos.", "",
          "## Ordenação por coluna", "",
          "| Coluna exibida | Ordenar por |",
          "|----------------|-------------|",
          "| `NomeMes` | `Mes` |",
          "| `AnoMesNome` | `AnoMes` |",
          "| `NomeDiaSemana` | `DiaSemanaNum` |", ""]

    caminho = cfg.DIR_DOCS / "dicionario-de-dados.md"
    caminho.write_text("\n".join(L), encoding="utf-8")
    print(f"-> {caminho}  ({len(L)} linhas)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
