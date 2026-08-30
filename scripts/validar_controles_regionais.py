from __future__ import annotations

"""Valida agregados regionais calculados contra os controles canônicos TIC-TIM.

A referência é imutável durante a validação. Divergências não são corrigidas por ajuste
ad hoc dos valores publicados: devem ser investigadas quanto a cobertura, filtros, schema,
versão de fonte ou regra de agregação.
"""

import argparse
from pathlib import Path
import sys

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
TAB_DEFAULT = ROOT / "dados" / "analise_tic_tim" / "tabelas"
REF_DEFAULT = ROOT / "referencias" / "tic_tim_controles_regionais_v16_26.csv"
OUT_DEFAULT = ROOT / "dados" / "analise_tic_tim" / "controle" / "gate_controles_regionais.csv"


def _ref(ref: pd.DataFrame, indicador: str, periodo: str | int) -> float:
    x = ref[(ref["indicador"] == indicador) & (ref["periodo"].astype(str) == str(periodo))]
    if len(x) != 1:
        raise ValueError(f"Referência não unívoca: {indicador} / {periodo}")
    return float(x.iloc[0]["valor"])


def _registrar(rows: list[dict], indicador: str, periodo: str | int,
               calculado: float | None, referencia: float,
               atol: float = 0.0, rtol: float = 0.0) -> None:
    calc = np.nan if calculado is None else float(calculado)
    if np.isnan(calc):
        status = "NAO_IMPLEMENTADO"
        dif = np.nan
    else:
        dif = abs(calc - referencia)
        status = "OK" if np.isclose(calc, referencia, atol=atol, rtol=rtol) else "DIVERGENTE"
    rows.append({
        "indicador": indicador,
        "periodo": str(periodo),
        "referencia": referencia,
        "calculado": calc,
        "dif_abs": dif,
        "status": status,
    })


def _ler(path: Path) -> pd.DataFrame | None:
    return pd.read_csv(path) if path.exists() else None


def main() -> int:
    ap = argparse.ArgumentParser(description="Gate dos controles regionais TIC-TIM v16.26.")
    ap.add_argument("--tabelas", type=Path, default=TAB_DEFAULT)
    ap.add_argument("--referencia", type=Path, default=REF_DEFAULT)
    ap.add_argument("--saida", type=Path, default=OUT_DEFAULT)
    ap.add_argument("--nao-falhar-por-nao-implementado", action="store_true")
    args = ap.parse_args()

    ref = pd.read_csv(args.referencia, dtype={"periodo": str})
    rows: list[dict] = []

    estoque = _ler(args.tabelas / "02_estoque_regional_ano.csv")
    if estoque is not None and {"ano", "estoque"}.issubset(estoque.columns):
        x = estoque[pd.to_numeric(estoque["ano"], errors="coerce") == 2025]
        calc = float(x.iloc[0]["estoque"]) if len(x) == 1 else None
    else:
        calc = None
    _registrar(rows, "estoque_formal", 2025, calc, _ref(ref, "estoque_formal", 2025))

    crescimento = _ler(args.tabelas / "03_crescimento_municipal.csv")
    calc = None
    if crescimento is not None and "acrescimo" in crescimento.columns:
        calc = float(pd.to_numeric(crescimento["acrescimo"], errors="coerce").sum())
    _registrar(rows, "crescimento_liquido_estoque", "2015-2025", calc,
               _ref(ref, "crescimento_liquido_estoque", "2015-2025"))

    massa = _ler(args.tabelas / "18_massa_salarial.csv")
    calc = None
    if massa is not None and {"ano", "massa_salarial"}.issubset(massa.columns):
        x = massa[pd.to_numeric(massa["ano"], errors="coerce") == 2025]
        calc = float(pd.to_numeric(x["massa_salarial"], errors="coerce").sum())
    _registrar(rows, "massa_salarial_observada", 2025, calc,
               _ref(ref, "massa_salarial_observada", 2025), atol=0.05, rtol=1e-10)

    caged = _ler(args.tabelas / "12_novo_caged_fluxos.csv")
    for indicador, coluna in [
        ("admissoes_novo_caged", "admissoes"),
        ("desligamentos_novo_caged", "desligamentos"),
        ("saldo_novo_caged", "saldo"),
    ]:
        calc = None
        if caged is not None and {"ano", coluna}.issubset(caged.columns):
            x = caged[pd.to_numeric(caged["ano"], errors="coerce") == 2025]
            calc = float(pd.to_numeric(x[coluna], errors="coerce").sum())
        _registrar(rows, indicador, 2025, calc, _ref(ref, indicador, 2025))

    conc = _ler(args.tabelas / "13_concentracao_empregadores.csv")
    calc = None
    if conc is not None and {"ano", "empregadores_positivos"}.issubset(conc.columns):
        x = conc[pd.to_numeric(conc["ano"], errors="coerce") == 2025]
        calc = float(pd.to_numeric(x["empregadores_positivos"], errors="coerce").sum())
    _registrar(rows, "empregadores_positivos_rais", 2025, calc,
               _ref(ref, "empregadores_positivos_rais", 2025))

    intensidade = _ler(args.tabelas / "20b_intensidade_fluxos_regional.csv")
    for ano in range(2020, 2026):
        calc = None
        if intensidade is not None and {"ano", "intensidade_fluxos_pct"}.issubset(intensidade.columns):
            x = intensidade[pd.to_numeric(intensidade["ano"], errors="coerce") == ano]
            if len(x) == 1:
                calc = round(float(x.iloc[0]["intensidade_fluxos_pct"]), 1)
        _registrar(rows, "intensidade_fluxos_regional", ano, calc,
                   _ref(ref, "intensidade_fluxos_regional", ano), atol=0.05)

    out = pd.DataFrame(rows)
    args.saida.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(args.saida, index=False)
    print(out.to_string(index=False))
    print(f"\nGate regional detalhado: {args.saida}")

    if (out["status"] == "DIVERGENTE").any():
        return 2
    if not args.nao_falhar_por_nao_implementado and (out["status"] == "NAO_IMPLEMENTADO").any():
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
