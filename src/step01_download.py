"""Etapa 1 - Descoberta e download dos arquivos mensais da ANP.

A ANP nao mantem padrao de nomenclatura entre anos. Exemplos reais
encontrados no indice em 2026-09:

    2024/precos-gasolina-etanol-09.csv
    2026/01-dados-abertos-precos-gasolina-etanol.csv
    2026/02-cados-abertos-preco-gasolina-etanol.csv   <- erro de digitacao da ANP
    2026/06-dados-abertos-precos-2026-06-gasolina-etanol.csv

Por isso nao hardcodamos nomes: lemos o indice HTML e casamos por
ano (do diretorio) + mes (primeiro numero de 2 digitos util) + grupo.
Assim o pipeline sobrevive a renomeacoes futuras.
"""
from __future__ import annotations

import re
import sys
import time
from dataclasses import dataclass

import requests

sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent))
import config as cfg


@dataclass(frozen=True)
class ArquivoANP:
    ano: int
    mes: int
    grupo: str
    url: str

    @property
    def nome_local(self) -> str:
        return f"{self.ano}-{self.mes:02d}-{self.grupo}.csv"


def meses_desejados() -> list[tuple[int, int]]:
    """Lista (ano, mes) da janela configurada, inclusive nas duas pontas."""
    ai, mi = cfg.MES_INICIO
    af, mf = cfg.MES_FIM
    out, ano, mes = [], ai, mi
    while (ano, mes) <= (af, mf):
        out.append((ano, mes))
        mes += 1
        if mes == 13:
            ano, mes = ano + 1, 1
    return out


def baixar_indice() -> str:
    r = requests.get(cfg.URL_INDICE, timeout=60, headers={"User-Agent": cfg.USER_AGENT})
    r.raise_for_status()
    return r.text


def descobrir(html: str) -> dict[tuple[int, int, str], str]:
    """Mapeia (ano, mes, grupo) -> url a partir do indice da ANP."""
    achados: dict[tuple[int, int, str], str] = {}
    hrefs = re.findall(r'href="([^"]*/shpc/dsan/[^"]+\.csv)"', html, re.I)

    for href in hrefs:
        m_ano = re.search(r"/dsan/(\d{4})/", href)
        if not m_ano:
            continue
        ano = int(m_ano.group(1))
        arquivo = href.rsplit("/", 1)[-1].lower()

        # Normaliza o erro de digitacao conhecido ("cados" -> "dados")
        # e a forma singular ("preco" -> "precos").
        norm = arquivo.replace("cados-abertos", "dados-abertos").replace("preco-", "precos-")

        grupo = next((g for g in cfg.GRUPOS if g in norm), None)
        if grupo is None:
            continue

        # O mes aparece ou como sufixo (-09.csv) ou como prefixo (09-...).
        m_mes = re.search(rf"{re.escape(grupo)}-(\d{{2}})\.csv$", norm) or re.match(r"^(\d{2})-", norm)
        if not m_mes:
            continue
        mes = int(m_mes.group(1))
        if not 1 <= mes <= 12:
            continue

        achados[(ano, mes, grupo)] = href

    return achados


def baixar(arq: ArquivoANP) -> tuple[str, int]:
    """Baixa se ainda nao existir. Retorna (status, bytes)."""
    destino = cfg.DIR_RAW / arq.nome_local
    if destino.exists() and destino.stat().st_size > 1024:
        return "cache", destino.stat().st_size

    r = requests.get(arq.url, timeout=300, headers={"User-Agent": cfg.USER_AGENT})
    r.raise_for_status()
    destino.write_bytes(r.content)
    return "baixado", len(r.content)


def main() -> int:
    print("Etapa 1 - download ANP")
    print(f"  janela: {cfg.MES_INICIO[0]}-{cfg.MES_INICIO[1]:02d} ate "
          f"{cfg.MES_FIM[0]}-{cfg.MES_FIM[1]:02d}")

    catalogo = descobrir(baixar_indice())
    print(f"  indice: {len(catalogo)} arquivos mensais localizados")

    pendentes, faltando = [], []
    for ano, mes in meses_desejados():
        for grupo in cfg.GRUPOS:
            url = catalogo.get((ano, mes, grupo))
            if url:
                pendentes.append(ArquivoANP(ano, mes, grupo, url))
            else:
                faltando.append((ano, mes, grupo))

    total = 0
    for i, arq in enumerate(pendentes, 1):
        status, n = baixar(arq)
        total += n
        print(f"  [{i:>2}/{len(pendentes)}] {arq.nome_local:<34} {status:>8}  {n/1e6:6.1f} MB")
        if status == "baixado":
            time.sleep(0.4)  # cortesia com o servidor publico

    print(f"\n  {len(pendentes)} arquivos, {total/1e6:.0f} MB em {cfg.DIR_RAW}")

    if faltando:
        print("\n  LACUNAS NA FONTE (nao publicadas pela ANP):")
        for ano, mes, grupo in faltando:
            print(f"    - {ano}-{mes:02d} {grupo}")
        print("  Registrar em docs/limitacoes.md. Nao e falha do pipeline.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
