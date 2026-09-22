"""Construtor de relatorio no formato PBIR.

O .pbix e um ZIP. Desde o formato PBIR, o relatorio deixou de ser um blob
unico e virou uma arvore de JSON com esquema publicado:

    Report/definition/
        version.json
        report.json
        pages/
            pages.json
            <pagina>/
                page.json
                visuals/
                    <visual>/
                        visual.json

Isso torna os visuais GERAVEIS - e versionaveis em diff, como o resto do
projeto. Este modulo monta as estruturas; quem decide o conteudo das
paginas e src/step11_relatorio.py.

Esquemas de referencia:
  https://developer.microsoft.com/json-schemas/fabric/item/report/definition
"""
from __future__ import annotations

import hashlib
import json

SCHEMA = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition"
S_VISUAL = f"{SCHEMA}/visualContainer/2.0.0/schema.json"
S_PAGE = f"{SCHEMA}/page/2.1.0/schema.json"
S_PAGES = f"{SCHEMA}/pagesMetadata/1.1.0/schema.json"

# Paleta validada contra daltonismo (ver docs/tema-anp.json).
AZUL, VERDE, AMBAR = "#3B6FD6", "#1A8A6B", "#C2611A"
TINTA, TINTA2, GRADE = "#1A1A19", "#5A5A55", "#E8E8E4"
FUNDO = "#FCFCFB"


def ident(*partes: str) -> str:
    """ID estavel de 20 hex: o mesmo conteudo gera sempre o mesmo nome."""
    return hashlib.sha1("|".join(partes).encode()).hexdigest()[:20]


# --- expressoes de campo --------------------------------------------------
def medida(nome: str, tabela: str = "_Medidas") -> dict:
    return {
        "field": {"Measure": {"Expression": {"SourceRef": {"Entity": tabela}},
                              "Property": nome}},
        "queryRef": f"{tabela}.{nome}",
        "nativeQueryRef": nome,
    }


def coluna(tabela: str, nome: str) -> dict:
    return {
        "field": {"Column": {"Expression": {"SourceRef": {"Entity": tabela}},
                             "Property": nome}},
        "queryRef": f"{tabela}.{nome}",
        "nativeQueryRef": nome,
    }


# --- formatacao -----------------------------------------------------------
def lit(v) -> dict:
    if isinstance(v, bool):
        return {"expr": {"Literal": {"Value": "true" if v else "false"}}}
    if isinstance(v, (int, float)):
        return {"expr": {"Literal": {"Value": f"{v}D"}}}
    return {"expr": {"Literal": {"Value": f"'{v}'"}}}


def cor(hexa: str) -> dict:
    return {"solid": {"color": {"expr": {"Literal": {"Value": f"'{hexa}'"}}}}}


def titulo(texto: str, tamanho: float = 13) -> dict:
    """Titulo do container. Afirma o achado, nao o nome do campo."""
    return {
        "title": [{"properties": {
            "text": lit(texto),
            "fontSize": lit(tamanho),
            "fontColor": {"solid": {"color": lit(TINTA)}},
            "bold": lit(True),
            "alignment": lit("left"),
        }}]
    }


def subtitulo(texto: str) -> dict:
    return {
        "subTitle": [{"properties": {
            "text": lit(texto),
            "fontSize": lit(9),
            "fontColor": {"solid": {"color": lit(TINTA2)}},
            "show": lit(True),
        }}]
    }


def eixos_discretos() -> dict:
    """Grade recessiva: referencia, nao conteudo."""
    return {
        "categoryAxis": [{"properties": {
            "showAxisTitle": lit(False),
            "fontSize": lit(9),
            "labelColor": {"solid": {"color": lit(TINTA2)}},
            "gridlineShow": lit(False),
        }}],
        "valueAxis": [{"properties": {
            "showAxisTitle": lit(False),
            "fontSize": lit(9),
            "labelColor": {"solid": {"color": lit(TINTA2)}},
            "gridlineColor": {"solid": {"color": lit(GRADE)}},
            "gridlineThickness": lit(1),
        }}],
    }


def legenda(mostrar: bool = True, pos: str = "TopLeft") -> dict:
    return {"legend": [{"properties": {
        "show": lit(mostrar),
        "position": lit(pos),
        "showTitle": lit(False),
        "fontSize": lit(9),
        "labelColor": {"solid": {"color": lit(TINTA2)}},
    }}]}


def cores_por_serie(mapa: dict[str, str]) -> list:
    """Cor fixa por entidade - nunca por ordem de classificacao."""
    out = []
    for valor, hexa in mapa.items():
        out.append({
            "properties": {"fill": cor(hexa)},
            "selector": {"data": [{"dataViewWildcard": {"matchingOption": 0}}],
                         "metadata": None},
        })
    return out


# --- construcao -----------------------------------------------------------
def visual(nome: str, tipo: str, x: int, y: int, w: int, h: int,
           papeis: dict[str, list[dict]] | None = None,
           objetos: dict | None = None,
           container: dict | None = None,
           z: int = 0, ordem: int = 0) -> dict:
    v: dict = {"visualType": tipo}
    if papeis:
        v["query"] = {"queryState": {
            papel: {"projections": proj} for papel, proj in papeis.items()
        }}
    if objetos:
        v["objects"] = objetos
    if container:
        v["visualContainerObjects"] = container
    return {
        "$schema": S_VISUAL,
        "name": nome,
        "position": {"x": x, "y": y, "z": z, "width": w, "height": h,
                     "tabOrder": ordem},
        "visual": v,
    }


def caixa_texto(nome: str, x: int, y: int, w: int, h: int,
                texto: str, tamanho: int = 20, negrito: bool = True,
                cor_txt: str = TINTA) -> dict:
    """Cabecalho da pagina. Usa o visual nativo de caixa de texto."""
    return {
        "$schema": S_VISUAL,
        "name": nome,
        "position": {"x": x, "y": y, "z": 0, "width": w, "height": h, "tabOrder": 0},
        "visual": {
            "visualType": "textbox",
            "objects": {"general": [{"properties": {"paragraphs": [{
                "textRuns": [{
                    "value": texto,
                    "textStyle": {
                        "fontSize": f"{tamanho}pt",
                        "fontWeight": "bold" if negrito else "normal",
                        "color": cor_txt,
                        "fontFamily": "'Segoe UI', wf_segoe-ui_normal, helvetica, arial, sans-serif",
                    },
                }],
                "horizontalTextAlignment": "left",
            }]}}]},
        },
    }


def pagina(nome: str, exibicao: str, largura: int = 1280, altura: int = 720) -> dict:
    return {
        "$schema": S_PAGE,
        "name": nome,
        "displayName": exibicao,
        "displayOption": "FitToPage",
        "height": altura,
        "width": largura,
    }


def gravar(z, caminho: str, obj: dict) -> None:
    z.writestr(caminho, json.dumps(obj, indent=2, ensure_ascii=False).encode("utf-8"))
