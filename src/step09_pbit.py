"""Etapa 9 - Geracao de um template do Power BI (.pbit).

Por que .pbit e nao .pbip ou injecao por XMLA:

  - o .pbip gerado nao abre nesta versao do Desktop (ver README)
  - o modelo injetado por XMLA CARREGA no Desktop, e os 35 testes
    passam nele, mas o Desktop nao consegue SALVAR um modelo que nao
    passou pelo pipeline dele: o "Salvar como" trava indefinidamente

O .pbit resolve os dois: e um ZIP cujo modelo e JSON puro
(DataModelSchema), formato que o proprio Desktop le nativamente. Ao
abrir, ele pede o parametro, atualiza a partir dos CSVs e produz um
relatorio comum - que salva como .pbix normalmente.

Template nao carrega dados, so a definicao. Os ~1 milhao de linhas
entram no refresh da abertura.
"""
from __future__ import annotations

import json
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import config as cfg
import step07_build_pbip as pbip
import step08_tmsl

NOME = "Precos-Combustiveis-ANP"

CONTENT_TYPES = """<?xml version="1.0" encoding="utf-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="json" ContentType="" />
  <Override PartName="/Version" ContentType="" />
  <Override PartName="/DataModelSchema" ContentType="" />
  <Override PartName="/DiagramLayout" ContentType="" />
  <Override PartName="/Report/Layout" ContentType="" />
  <Override PartName="/Settings" ContentType="" />
  <Override PartName="/Metadata" ContentType="" />
</Types>"""


def u16(texto: str) -> bytes:
    """Partes internas do .pbit sao UTF-16 LE COM BOM.

    O BOM nao e opcional: sem os bytes FF FE iniciais o Desktop nao
    reconhece a parte e abre um arquivo em branco, sem mensagem de erro.
    encode("utf-16") acrescenta o BOM; encode("utf-16-le") nao.
    """
    return texto.encode("utf-16")


def modelo() -> dict:
    """Objeto 'database' do TMSL, sem o envelope createOrReplace."""
    # Reaproveita exatamente a mesma definicao ja validada pelos testes.
    sys.argv = ["step08", "Model"]
    medidas = pbip.ler_medidas(cfg.DIR_DOCS / "dax" / "medidas.dax")

    tabelas = []
    for nome, cols in pbip.TABELAS.items():
        t: dict = {
            "name": nome,
            "columns": [step08_tmsl.coluna(nome, c, tp, oc, so) for c, tp, oc, so in cols],
            "partitions": [{
                "name": nome,
                "mode": "import",
                "source": {"type": "m", "expression": pbip.m_query(nome)},
            }],
        }
        if nome == "Dim_Calendario":
            t["dataCategory"] = "Time"
        tabelas.append(t)

    tabelas.append({
        "name": "_Medidas",
        "columns": [{"name": "Coluna1", "dataType": "string", "sourceColumn": "Coluna1",
                     "summarizeBy": "none", "isHidden": True}],
        "partitions": [{"name": "_Medidas", "mode": "import", "source": {
            "type": "m",
            "expression": "let\n    Origem = Table.FromRows({}, type table [Coluna1 = text])\nin\n    Origem"}}],
        "measures": step08_tmsl.medidas_tmsl(medidas),
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

    return {
        "name": "Model",
        "compatibilityLevel": 1606,
        "model": {
            "culture": "pt-BR",
            "defaultPowerBIDataSourceVersion": "powerBI_V3",
            "sourceQueryCulture": "pt-BR",
            "dataAccessOptions": {"legacyRedirects": True, "returnErrorValuesAsNull": True},
            "expressions": [{
                "name": "pCaminhoDados",
                "kind": "m",
                "expression": json.dumps(str(cfg.DIR_PROCESSED))
                              + ' meta [IsParameterQuery=true, Type="Text", '
                                'IsParameterQueryRequired=true]',
            }],
            "tables": tabelas,
            "relationships": relacoes,
            "annotations": [{"name": "__PBI_TimeIntelligenceEnabled", "value": "0"}],
        },
    }, len(medidas), len(relacoes)


def layout(tema: dict) -> dict:
    """Relatorio minimo: uma pagina em branco, com o tema aplicado."""
    cfg_relatorio = {
        "version": "5.43",
        "themeCollection": {"customTheme": {"name": tema["name"], "version": "5.43", "type": 2}},
        "activeSectionIndex": 0,
        "defaultDrillFilterOtherVisuals": True,
    }
    return {
        "id": 0,
        "resourcePackages": [{
            "resourcePackage": {
                "name": "SharedResources", "type": 2, "disabled": False,
                "items": [{"type": 202, "path": "BaseThemes/CY24SU10.json", "name": "CY24SU10"}],
            }
        }],
        "config": json.dumps(cfg_relatorio),
        "layoutOptimization": 0,
        "sections": [{
            "id": 0,
            "name": "ReportSection",
            "displayName": "Visao Geral",
            "filters": "[]",
            "ordinal": 0,
            "visualContainers": [],
            "config": "{}",
            "displayOption": 1,
            "width": 1280,
            "height": 720,
        }],
        "filters": "[]",
        "pods": [],
        "publicCustomVisuals": [],
    }


def main() -> int:
    db, n_medidas, n_rel = modelo()
    tema = json.loads((cfg.DIR_DOCS / "tema-anp.json").read_text(encoding="utf-8"))

    destino = cfg.RAIZ / "powerbi" / f"{NOME}.pbit"
    destino.parent.mkdir(parents=True, exist_ok=True)

    metadata = {"Version": 3, "AutoCreatedRelationships": [], "FileDescription": None}
    settings = {"Version": 4, "ReportSettings": {"UseStylableVisualContainerHeader": True}}
    diagrama = {"version": "1.1.0", "diagrams": [{
        "ordinal": 0, "scrollPosition": {"x": 0, "y": 0}, "nodes": [],
        "name": "Todas as tabelas", "zoomValue": 100, "pinKeyFieldsToTop": False,
        "showExtraHeaderInfo": False, "hideKeyFieldsWhenCollapsed": False,
        "tablesListPaneWidth": 0, "defaultColumnDisplayMode": "all",
    }]}

    with zipfile.ZipFile(destino, "w", zipfile.ZIP_DEFLATED) as z:
        # [Content_Types].xml vai em UTF-8, as demais partes em UTF-16 LE.
        z.writestr("[Content_Types].xml", CONTENT_TYPES.encode("utf-8"))
        z.writestr("Version", u16("1.28"))
        z.writestr("DataModelSchema", u16(json.dumps(db, ensure_ascii=False)))
        z.writestr("DiagramLayout", u16(json.dumps(diagrama, ensure_ascii=False)))
        z.writestr("Metadata", u16(json.dumps(metadata, ensure_ascii=False)))
        z.writestr("Settings", u16(json.dumps(settings, ensure_ascii=False)))
        z.writestr("Report/Layout", u16(json.dumps(layout(tema), ensure_ascii=False)))
        z.writestr("Report/StaticResources/SharedResources/BaseThemes/CY24SU10.json",
                   json.dumps(tema, ensure_ascii=False).encode("utf-8"))

    kb = destino.stat().st_size / 1024
    print("Etapa 9 - template .pbit gerado")
    print(f"  tabelas:  {len(db['model']['tables'])}")
    print(f"  medidas:  {n_medidas}")
    print(f"  relacoes: {n_rel}")
    print(f"  -> {destino}  ({kb:.0f} KB)")
    print()
    print("  Abrir no Power BI Desktop: ele pede o parametro pCaminhoDados,")
    print("  atualiza a partir dos CSVs e entao permite Salvar como .pbix.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
