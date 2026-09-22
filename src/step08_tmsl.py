"""Etapa 8 - Geracao do modelo em TMSL, para teste automatizado.

O .pbip da etapa 7 e o entregavel que se abre no Desktop. Este script
produz o MESMO modelo em TMSL (JSON), que pode ser enviado por XMLA a
uma instancia do Analysis Services e refrescado sem interface grafica.

E o que permite rodar a suite de testes DAX de forma reproduzivel, em
vez de conferir numero por numero na tela.

As definicoes de tabela, relacao e medida vem de step07_build_pbip.py -
nao ha segunda copia.

Uso:
    python src/step08_tmsl.py <id-do-banco>
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import config as cfg
import step07_build_pbip as pbip


def coluna(tabela: str, nome: str, tipo: str, oculta: bool, sort: str | None) -> dict:
    c: dict = {
        "name": nome,
        "dataType": tipo,
        "sourceColumn": nome,
        "summarizeBy": "none",
    }
    if oculta:
        c["isHidden"] = True
    if sort:
        c["sortByColumn"] = sort
    # Marcacao de tabela de datas: a coluna-chave precisa ser declarada.
    if tabela == "Dim_Calendario" and nome == "Data":
        c["isKey"] = True
    return c


def medidas_tmsl(medidas: list[dict]) -> list[dict]:
    out = []
    for md in medidas:
        m: dict = {"name": md["nome"], "expression": md["expr"]}
        fmt = pbip.FORMATOS.get(md["nome"])
        if fmt:
            m["formatString"] = fmt
        if md["pasta"]:
            m["displayFolder"] = md["pasta"]
        out.append(m)
    return out


def main() -> int:
    if len(sys.argv) < 2:
        print("uso: python src/step08_tmsl.py <id-do-banco>")
        return 2
    db_id = sys.argv[1]

    medidas = pbip.ler_medidas(cfg.DIR_DOCS / "dax" / "medidas.dax")

    tabelas = []
    for nome, cols in pbip.TABELAS.items():
        t: dict = {
            "name": nome,
            "columns": [coluna(nome, c, tp, oc, so) for c, tp, oc, so in cols],
            "partitions": [{
                "name": nome,
                "mode": "import",
                "source": {"type": "m", "expression": pbip.m_query(nome)},
            }],
        }
        if nome == "Dim_Calendario":
            t["dataCategory"] = "Time"
        tabelas.append(t)

    # Tabela tecnica que hospeda as medidas, sem linhas.
    tabelas.append({
        "name": "_Medidas",
        "columns": [{
            "name": "Coluna1", "dataType": "string", "sourceColumn": "Coluna1",
            "summarizeBy": "none", "isHidden": True,
        }],
        "partitions": [{
            "name": "_Medidas", "mode": "import",
            "source": {"type": "m", "expression":
                       "let\n    Origem = Table.FromRows({}, type table [Coluna1 = text])\nin\n    Origem"},
        }],
        "measures": medidas_tmsl(medidas),
    })

    relacoes = []
    for td, cd, tf, cf in pbip.RELACOES:
        relacoes.append({
            "name": f"{tf}_{cf}_to_{td}_{cd}",
            "fromTable": tf, "fromColumn": cf,
            "toTable": td, "toColumn": cd,
            "fromCardinality": "many", "toCardinality": "one",
            "crossFilteringBehavior": "oneDirection",
        })

    caminho = str(cfg.DIR_PROCESSED)
    tmsl = {
        "createOrReplace": {
            "object": {"database": db_id},
            "database": {
                "name": db_id,
                "compatibilityLevel": 1606,
                "model": {
                    "culture": "pt-BR",
                    "defaultPowerBIDataSourceVersion": "powerBI_V3",
                    "sourceQueryCulture": "pt-BR",
                    "dataAccessOptions": {
                        "legacyRedirects": True,
                        "returnErrorValuesAsNull": True,
                    },
                    "expressions": [{
                        "name": "pCaminhoDados",
                        "kind": "m",
                        "expression": (
                            json.dumps(caminho)
                            + ' meta [IsParameterQuery=true, Type="Text", '
                              'IsParameterQueryRequired=true]'
                        ),
                    }],
                    "tables": tabelas,
                    "relationships": relacoes,
                },
            },
        }
    }

    destino = cfg.DIR_OUTPUTS / "modelo.tmsl"
    destino.write_text(json.dumps(tmsl, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"Etapa 8 - TMSL gerado")
    print(f"  banco:     {db_id}")
    print(f"  tabelas:   {len(tabelas)}")
    print(f"  relacoes:  {len(relacoes)}")
    print(f"  medidas:   {len(medidas)}")
    print(f"  -> {destino}  ({destino.stat().st_size/1024:.0f} KB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
