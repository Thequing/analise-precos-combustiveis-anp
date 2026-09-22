"""Etapa 10 - Exportacao das medidas para consumo pelo PowerShell.

Le docs/dax/medidas.dax - que continua sendo a unica fonte de verdade -
e grava outputs/medidas.json no formato que scripts/Preparar-Modelo.ps1
aplica no modelo via TOM.

Editar uma medida: mexa no .dax e rode Preparar-Modelo.ps1 de novo.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import config as cfg
import step07_build_pbip as pbip


def main() -> int:
    medidas = pbip.ler_medidas(cfg.DIR_DOCS / "dax" / "medidas.dax")
    saida = [
        {
            "nome": m["nome"],
            "pasta": m["pasta"],
            "expr": m["expr"],
            "formato": pbip.FORMATOS.get(m["nome"], ""),
        }
        for m in medidas
    ]
    destino = cfg.DIR_OUTPUTS / "medidas.json"
    destino.write_text(json.dumps(saida, indent=2, ensure_ascii=False), encoding="utf-8")

    sem_formato = [m["nome"] for m in saida if not m["formato"]]
    print(f"Etapa 10 - {len(saida)} medidas -> {destino}")
    if sem_formato:
        print(f"  sem formato (texto): {', '.join(sem_formato)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
