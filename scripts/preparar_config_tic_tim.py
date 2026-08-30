from __future__ import annotations

"""Prepara a configuração canônica do estudo TIC-TIM para execução automatizada.

A lista de 30 municípios é derivada da referência congelada das fichas municipais,
evita duplicação manual e garante que a execução use exatamente o universo publicado.
"""

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
REF = ROOT / "referencias" / "tic_tim_fichas_v2_7_quadro1.csv"
MUNICIPIOS = ROOT / "municipios.csv"
CONFIG = ROOT / "config.json"


def main() -> None:
    ref = pd.read_csv(REF, dtype={"id_municipio": str})
    esperado = {"id_municipio", "municipio"}
    faltantes = esperado - set(ref.columns)
    if faltantes:
        raise KeyError(f"Referência municipal sem colunas obrigatórias: {sorted(faltantes)}")

    municipios = ref[["id_municipio", "municipio"]].drop_duplicates().copy()
    municipios["id_municipio"] = municipios["id_municipio"].astype(str).str.zfill(7)
    municipios = municipios.sort_values("id_municipio").rename(columns={"municipio": "nome"})
    if len(municipios) != 30:
        raise RuntimeError(f"Universo canônico deve ter 30 municípios; encontrados {len(municipios)}")
    if municipios["id_municipio"].duplicated().any():
        raise RuntimeError("Há códigos IBGE duplicados no universo canônico")
    municipios.to_csv(MUNICIPIOS, index=False)

    cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
    cfg.update(
        {
            "arquivo_municipios": "municipios.csv",
            "lote_tamanho": 5,
            "ano_inicial": 2015,
            "ano_final": 2025,
            "competencia_inicial": "2020-01",
            "competencia_final": "2025-12",
            "snapshot_inicial": None,
            "snapshot_final": "2026-01-11",
            "estimar_custo": True,
            "sobrescrever": False,
            "validacao_municipios": "strict",
        }
    )
    CONFIG.write_text(json.dumps(cfg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"Municípios canônicos: {MUNICIPIOS} ({len(municipios)})")
    print(f"Configuração TIC-TIM: {CONFIG}")
    print(json.dumps(cfg, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
