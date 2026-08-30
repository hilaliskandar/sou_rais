from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from tic_tim_analysis import auditar_equivalencia


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Compara uma tabela calculada pelo pipeline TIC-TIM com uma tabela canônica publicada."
    )
    p.add_argument("calculado", type=Path, help="CSV calculado pelo pipeline")
    p.add_argument("referencia", type=Path, help="CSV de referência canônica")
    p.add_argument("--chaves", nargs="+", required=True, help="Colunas que identificam cada observação")
    p.add_argument("--colunas", nargs="+", required=True, help="Colunas numéricas a comparar")
    p.add_argument("--tol-abs", type=float, default=1e-9, help="Tolerância absoluta")
    p.add_argument("--tol-rel", type=float, default=1e-9, help="Tolerância relativa")
    p.add_argument("--saida", type=Path, default=Path("dados/analise_tic_tim/controle/equivalencia.csv"))
    return p.parse_args()


def main() -> None:
    args = parse_args()
    calc = pd.read_csv(args.calculado, dtype={c: str for c in args.chaves})
    ref = pd.read_csv(args.referencia, dtype={c: str for c in args.chaves})

    resultado = auditar_equivalencia(
        calculado=calc,
        referencia=ref,
        chaves=args.chaves,
        colunas=args.colunas,
        tolerancia_abs=args.tol_abs,
        tolerancia_rel=args.tol_rel,
    )
    args.saida.parent.mkdir(parents=True, exist_ok=True)
    resultado.to_csv(args.saida, index=False)

    falhas = resultado[~resultado["equivalente"]]
    print(resultado.to_string(index=False))
    print(f"\nResultado salvo em: {args.saida}")
    if not falhas.empty:
        raise SystemExit(f"GATE REPROVADO: {len(falhas)} comparação(ões) fora da tolerância.")
    print("GATE APROVADO: todas as comparações estão dentro da tolerância.")


if __name__ == "__main__":
    main()
