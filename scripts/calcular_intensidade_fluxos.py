from __future__ import annotations

"""Calcula a intensidade aproximada dos fluxos do Novo CAGED.

Contrato metodológico TIC-TIM (Bloco 5):

    estoque_medio_t = (estoque_RAIS_{t-1} + estoque_RAIS_t) / 2
    intensidade_t = ((admissoes_t + desligamentos_t) / 2) / estoque_medio_t

A medida descreve a intensidade relativa de entradas e saídas. Não acompanha o mesmo
trabalhador longitudinalmente e, por isso, não deve ser denominada taxa de turnover
individual em sentido estrito.
"""

import argparse
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
ESTOQUE_DEFAULT = ROOT / "dados" / "analise_tic_tim" / "tabelas" / "01_estoque_municipio_ano.csv"
CAGED_DEFAULT = ROOT / "dados" / "analise_tic_tim" / "tabelas" / "12_novo_caged_fluxos.csv"
SAIDA_DEFAULT = ROOT / "dados" / "analise_tic_tim" / "tabelas" / "20_intensidade_fluxos.csv"
REGIONAL_DEFAULT = ROOT / "dados" / "analise_tic_tim" / "tabelas" / "20b_intensidade_fluxos_regional.csv"


def _normalizar_id(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["id_municipio"] = (
        out["id_municipio"].astype(str).str.replace(r"\.0$", "", regex=True).str.zfill(7)
    )
    out["ano"] = pd.to_numeric(out["ano"], errors="raise").astype(int)
    return out


def calcular_intensidade(estoque: pd.DataFrame, fluxos: pd.DataFrame) -> pd.DataFrame:
    obrig_estoque = {"id_municipio", "ano", "estoque"}
    obrig_fluxos = {"id_municipio", "ano", "admissoes", "desligamentos"}
    if not obrig_estoque.issubset(estoque.columns):
        raise KeyError(f"Estoque sem colunas obrigatórias: {sorted(obrig_estoque - set(estoque.columns))}")
    if not obrig_fluxos.issubset(fluxos.columns):
        raise KeyError(f"Fluxos sem colunas obrigatórias: {sorted(obrig_fluxos - set(fluxos.columns))}")

    e = _normalizar_id(estoque)
    f = _normalizar_id(fluxos)
    if e.duplicated(["id_municipio", "ano"]).any():
        raise ValueError("Estoque contém duplicidade município-ano.")
    if f.duplicated(["id_municipio", "ano"]).any():
        raise ValueError("Fluxos contêm duplicidade município-ano; consolide o Novo CAGED antes do cálculo.")

    atual = e[["id_municipio", "ano", "estoque"]].rename(columns={"estoque": "estoque_fim_ano"})
    anterior = e[["id_municipio", "ano", "estoque"]].copy()
    anterior["ano"] = anterior["ano"] + 1
    anterior = anterior.rename(columns={"estoque": "estoque_fim_ano_anterior"})

    out = f.merge(atual, on=["id_municipio", "ano"], how="left", validate="one_to_one")
    out = out.merge(anterior, on=["id_municipio", "ano"], how="left", validate="one_to_one")
    out["estoque_medio_aprox"] = (
        pd.to_numeric(out["estoque_fim_ano_anterior"], errors="coerce")
        + pd.to_numeric(out["estoque_fim_ano"], errors="coerce")
    ) / 2
    out["movimentacao_media"] = (
        pd.to_numeric(out["admissoes"], errors="coerce")
        + pd.to_numeric(out["desligamentos"], errors="coerce")
    ) / 2
    out["intensidade_fluxos"] = np.where(
        out["estoque_medio_aprox"] > 0,
        out["movimentacao_media"] / out["estoque_medio_aprox"],
        np.nan,
    )
    out["intensidade_fluxos_pct"] = 100 * out["intensidade_fluxos"]
    out["saldo"] = (
        pd.to_numeric(out["admissoes"], errors="coerce")
        - pd.to_numeric(out["desligamentos"], errors="coerce")
    )
    return out.sort_values(["ano", "id_municipio"]).reset_index(drop=True)


def agregar_regional(municipal: pd.DataFrame) -> pd.DataFrame:
    cols = [
        "admissoes",
        "desligamentos",
        "saldo",
        "estoque_fim_ano_anterior",
        "estoque_fim_ano",
    ]
    g = municipal.groupby("ano", as_index=False)[cols].sum(min_count=1)
    g["estoque_medio_aprox"] = (g["estoque_fim_ano_anterior"] + g["estoque_fim_ano"]) / 2
    g["movimentacao_media"] = (g["admissoes"] + g["desligamentos"]) / 2
    g["intensidade_fluxos"] = np.where(
        g["estoque_medio_aprox"] > 0,
        g["movimentacao_media"] / g["estoque_medio_aprox"],
        np.nan,
    )
    g["intensidade_fluxos_pct"] = 100 * g["intensidade_fluxos"]
    return g


def main() -> None:
    ap = argparse.ArgumentParser(description="Calcula intensidade aproximada dos fluxos TIC-TIM.")
    ap.add_argument("--estoque", type=Path, default=ESTOQUE_DEFAULT)
    ap.add_argument("--caged", type=Path, default=CAGED_DEFAULT)
    ap.add_argument("--saida", type=Path, default=SAIDA_DEFAULT)
    ap.add_argument("--saida-regional", type=Path, default=REGIONAL_DEFAULT)
    args = ap.parse_args()

    estoque = pd.read_csv(args.estoque, dtype={"id_municipio": str})
    fluxos = pd.read_csv(args.caged, dtype={"id_municipio": str})
    municipal = calcular_intensidade(estoque, fluxos)
    regional = agregar_regional(municipal)

    args.saida.parent.mkdir(parents=True, exist_ok=True)
    municipal.to_csv(args.saida, index=False)
    regional.to_csv(args.saida_regional, index=False)
    print(f"Intensidade municipal: {args.saida}")
    print(f"Intensidade regional: {args.saida_regional}")


if __name__ == "__main__":
    main()
