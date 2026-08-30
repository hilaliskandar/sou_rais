from __future__ import annotations

"""Valida produtos calculados contra o Quadro 1 das Fichas Municipais v2.7.

O script não mascara produtos ausentes. Cada indicador é classificado como:
- OK: calculado e equivalente dentro da tolerância;
- DIVERGENTE: calculado, mas não equivalente;
- NAO_IMPLEMENTADO: o produto necessário ainda não foi gerado pelo pipeline;
- NAO_PUBLICADO: a referência é n.d. na ficha publicada.

A saída serve como gate de regressão, não como mecanismo para alterar a referência.
"""

from pathlib import Path
import argparse
import sys

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
REF_DEFAULT = ROOT / "referencias" / "tic_tim_fichas_v2_7_quadro1.csv"
ANALISE_DEFAULT = ROOT / "dados" / "analise_tic_tim" / "tabelas"


def _ler(path: Path) -> pd.DataFrame | None:
    if not path.exists():
        return None
    return pd.read_csv(path, dtype={"id_municipio": str})


def _normalizar_id(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["id_municipio"] = out["id_municipio"].astype(str).str.replace(r"\.0$", "", regex=True).str.zfill(7)
    return out


def _comparar(ref: pd.DataFrame, calc: pd.DataFrame | None, ref_col: str, calc_col: str,
             indicador: str, atol: float, rtol: float, filtro=None) -> pd.DataFrame:
    base = ref[["id_municipio", "municipio", ref_col]].copy()
    base = base.rename(columns={ref_col: "referencia"})
    if calc is None or calc_col not in calc.columns:
        base["calculado"] = np.nan
        base["dif_abs"] = np.nan
        base["status"] = np.where(base["referencia"].isna(), "NAO_PUBLICADO", "NAO_IMPLEMENTADO")
        base["indicador"] = indicador
        return base
    x = _normalizar_id(calc)
    if filtro is not None:
        x = filtro(x)
    x = x[["id_municipio", calc_col]].drop_duplicates("id_municipio", keep="last")
    x = x.rename(columns={calc_col: "calculado"})
    out = base.merge(x, on="id_municipio", how="left")
    out["dif_abs"] = (out["calculado"] - out["referencia"]).abs()
    eq = np.isclose(out["calculado"], out["referencia"], atol=atol, rtol=rtol, equal_nan=False)
    out["status"] = np.select(
        [out["referencia"].isna(), out["calculado"].isna(), eq],
        ["NAO_PUBLICADO", "NAO_IMPLEMENTADO", "OK"],
        default="DIVERGENTE",
    )
    out["indicador"] = indicador
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--referencia", type=Path, default=REF_DEFAULT)
    ap.add_argument("--analise", type=Path, default=ANALISE_DEFAULT)
    ap.add_argument("--saida", type=Path, default=ROOT / "dados" / "analise_tic_tim" / "controle" / "gate_fichas_v2_7.csv")
    ap.add_argument("--nao-falhar-por-nao-implementado", action="store_true")
    args = ap.parse_args()

    ref = _normalizar_id(pd.read_csv(args.referencia, dtype={"id_municipio": str}))
    estoque = _ler(args.analise / "01_estoque_municipio_ano.csv")
    cresc = _ler(args.analise / "03_crescimento_municipal.csv")
    remun = _ler(args.analise / "11_remuneracao_municipal.csv")
    caged = _ler(args.analise / "12_novo_caged_fluxos.csv")
    idade = _ler(args.analise / "16_perfil_etario.csv")
    sexo = _ler(args.analise / "17_perfil_sexo.csv")
    top10 = _ler(args.analise / "13_concentracao_top10_empregadores.csv")
    massa = _ler(args.analise / "18_massa_salarial.csv")

    partes = []
    partes.append(_comparar(ref, estoque, "estoque_2025", "estoque", "estoque_2025", 0, 0,
        filtro=lambda x: x[pd.to_numeric(x["ano"], errors="coerce") == 2025]))
    partes.append(_comparar(ref, cresc, "crescimento_2015_2025_pct", "variacao_pct", "crescimento_2015_2025_pct", 0.05, 1e-5))

    # O pipeline deve produzir explicitamente remuneração REAL. Se a coluna ainda for
    # apenas nominal, o indicador permanece NAO_IMPLEMENTADO em vez de ser comparado.
    remun_col = "mediana_real" if remun is not None and "mediana_real" in remun.columns else "__ausente__"
    partes.append(_comparar(ref, remun, "remuneracao_mediana_real_2025", remun_col,
        "remuneracao_mediana_real_2025", 0.02, 1e-6,
        filtro=(lambda x: x[pd.to_numeric(x["ano"], errors="coerce") == 2025]) if remun_col != "__ausente__" else None))

    massa_col = "massa_salarial_milhoes" if massa is not None and "massa_salarial_milhoes" in massa.columns else "__ausente__"
    partes.append(_comparar(ref, massa, "massa_salarial_milhoes_2025", massa_col,
        "massa_salarial_milhoes_2025", 0.06, 1e-5,
        filtro=(lambda x: x[pd.to_numeric(x["ano"], errors="coerce") == 2025]) if massa_col != "__ausente__" else None))

    if caged is not None and "ano" in caged.columns and "saldo" in caged.columns:
        caged_2025 = caged[pd.to_numeric(caged["ano"], errors="coerce") == 2025].groupby("id_municipio", as_index=False)["saldo"].sum()
    else:
        caged_2025 = None
    partes.append(_comparar(ref, caged_2025, "saldo_caged_2025", "saldo", "saldo_caged_2025", 0, 0))

    idade_col = "idade_mediana" if idade is not None and "idade_mediana" in idade.columns else "__ausente__"
    partes.append(_comparar(ref, idade, "idade_mediana_2025", idade_col, "idade_mediana_2025", 0.01, 0,
        filtro=(lambda x: x[pd.to_numeric(x["ano"], errors="coerce") == 2025]) if idade_col != "__ausente__" else None))

    mulheres_col = "mulheres_pct" if sexo is not None and "mulheres_pct" in sexo.columns else "__ausente__"
    partes.append(_comparar(ref, sexo, "mulheres_pct_2025", mulheres_col, "mulheres_pct_2025", 0.05, 1e-5,
        filtro=(lambda x: x[pd.to_numeric(x["ano"], errors="coerce") == 2025]) if mulheres_col != "__ausente__" else None))

    top_col = "share_top10" if top10 is not None and "share_top10" in top10.columns else "__ausente__"
    top_calc = top10.copy() if top10 is not None else None
    if top_calc is not None and top_col != "__ausente__":
        # O pipeline guarda participação como fração; a publicação usa porcentagem.
        top_calc["top10_pct"] = pd.to_numeric(top_calc[top_col], errors="coerce") * 100
        top_col = "top10_pct"
    partes.append(_comparar(ref, top_calc, "top10_empregadores_pct_2025", top_col,
        "top10_empregadores_pct_2025", 0.05, 1e-5,
        filtro=(lambda x: x[pd.to_numeric(x["ano"], errors="coerce") == 2025]) if top_col != "__ausente__" else None))

    out = pd.concat(partes, ignore_index=True)
    args.saida.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(args.saida, index=False)

    resumo = out.groupby(["indicador", "status"]).size().unstack(fill_value=0)
    print(resumo.to_string())
    print(f"\nGate detalhado: {args.saida}")

    if (out["status"] == "DIVERGENTE").any():
        return 2
    if not args.nao_falhar_por_nao_implementado and (out["status"] == "NAO_IMPLEMENTADO").any():
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
