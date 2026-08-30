from __future__ import annotations

"""Gera as figuras analíticas regionais usadas na edição do Relatório TIC-TIM.

As figuras são derivadas exclusivamente das tabelas produzidas por `scripts/analisar_tic_tim.py`.
O script evita inserir uma figura quando o produto necessário ainda não foi reconciliado.
"""

from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parents[1]
TAB = ROOT / "dados" / "analise_tic_tim" / "tabelas"
FIG = ROOT / "dados" / "analise_tic_tim" / "figuras"
FIG.mkdir(parents=True, exist_ok=True)


def ler(nome, obrigatorio=True):
    p = TAB / nome
    if not p.exists():
        if obrigatorio:
            raise FileNotFoundError(p)
        return None
    return pd.read_csv(p, dtype={"id_municipio": str})


def salvar(fig, stem):
    fig.tight_layout()
    fig.savefig(FIG / f"{stem}.png", dpi=220, bbox_inches="tight")
    fig.savefig(FIG / f"{stem}.pdf", bbox_inches="tight")
    plt.close(fig)


def figura1():
    d = ler("02_estoque_regional_ano.csv")
    d = d[d["ano"].isin([2015, 2019, 2020, 2022, 2025])]
    fig, ax = plt.subplots(figsize=(10, 5.5))
    ax.plot(d["ano"], d["estoque"], marker="o", linewidth=2)
    for _, r in d.iterrows():
        ax.annotate(f"{int(r.estoque):,}".replace(",", "."), (r.ano, r.estoque), xytext=(0, 8), textcoords="offset points", ha="center", fontsize=8)
    ax.set(title="Evolução do estoque formal regional", xlabel="Ano", ylabel="Vínculos formais ativos")
    ax.grid(axis="y", alpha=.25)
    salvar(fig, "01_evolucao_estoque_regional")


def figura2():
    d = ler("03_crescimento_municipal.csv").sort_values("acrescimo", ascending=False).head(15).sort_values("acrescimo")
    fig, ax = plt.subplots(figsize=(10, 7))
    ax.barh(d["id_municipio"], d["acrescimo"])
    ax.set(title="Maiores acréscimos absolutos municipais, 2015–2025", xlabel="Acréscimo de vínculos", ylabel="Código IBGE")
    ax.grid(axis="x", alpha=.2)
    salvar(fig, "02_maiores_acrescimos_municipais")


def figura3():
    d = ler("05_ql_setorial.csv")
    # A contribuição setorial usa o universo completo, independentemente do QL.
    g = d.groupby(["ano", "setor"], as_index=False)["vinculos"].sum()
    p = g.pivot(index="setor", columns="ano", values="vinculos").fillna(0)
    p["delta"] = p.get(2025, 0) - p.get(2015, 0)
    top = p.sort_values("delta", ascending=False).head(15).sort_values("delta")
    fig, ax = plt.subplots(figsize=(10, 7))
    ax.barh(top.index.astype(str), top["delta"])
    ax.set(title="Contribuição setorial ao crescimento líquido, 2015–2025", xlabel="Variação de vínculos", ylabel="Divisão CNAE")
    ax.grid(axis="x", alpha=.2)
    salvar(fig, "03_contribuicao_setorial_crescimento")


def figura4():
    d = ler("09_ql_ocupacional.csv")
    g = d.groupby(["ano", "cbo_familia"], as_index=False)["vinculos"].sum()
    p = g.pivot(index="cbo_familia", columns="ano", values="vinculos").fillna(0)
    p["delta"] = p.get(2025, 0) - p.get(2015, 0)
    top = p.sort_values("delta", ascending=False).head(15).sort_values("delta")
    fig, ax = plt.subplots(figsize=(10, 7))
    ax.barh(top.index.astype(str), top["delta"])
    ax.set(title="Famílias CBO com maior acréscimo de vínculos, 2015–2025", xlabel="Variação de vínculos", ylabel="Família CBO")
    ax.grid(axis="x", alpha=.2)
    salvar(fig, "04_crescimento_familias_cbo")


def figura5():
    d = ler("20_intensidade_fluxos.csv", obrigatorio=False)
    if d is None:
        print("FIGURA 5 NÃO GERADA: falta 20_intensidade_fluxos.csv com estoque de referência reconciliado.")
        return
    reg = d.groupby("ano", as_index=False).agg(admissoes=("admissoes", "sum"), desligamentos=("desligamentos", "sum"), estoque_referencia=("estoque_referencia", "sum"))
    reg["intensidade_pct"] = 100 * ((reg["admissoes"] + reg["desligamentos"]) / 2) / reg["estoque_referencia"]
    fig, ax = plt.subplots(figsize=(10, 5.5))
    ax.plot(reg["ano"], reg["intensidade_pct"], marker="o", linewidth=2)
    ax.set(title="Intensidade aproximada dos fluxos regionais", xlabel="Ano", ylabel="% do estoque de referência")
    ax.grid(axis="y", alpha=.25)
    salvar(fig, "05_intensidade_fluxos_2020_2025")


def figura6():
    d = ler("16_perfil_etario.csv")
    g = d.groupby("ano", as_index=False).agg(share_ate29=("share_ate29", "mean"), share_55mais=("share_55mais", "mean"))
    g = g[g["ano"].isin([2015, 2019, 2020, 2022, 2025])]
    fig, ax = plt.subplots(figsize=(10, 5.5))
    ax.plot(g["ano"], 100 * g["share_ate29"], marker="o", label="Até 29 anos")
    ax.plot(g["ano"], 100 * g["share_55mais"], marker="o", label="55 anos ou mais")
    ax.set(title="Mudança da estrutura etária do emprego formal", xlabel="Ano", ylabel="Participação média municipal (%)")
    ax.legend(); ax.grid(axis="y", alpha=.25)
    salvar(fig, "06_estrutura_etaria")


def figura7():
    d = ler("13_concentracao_empregadores.csv")
    d = d[pd.to_numeric(d["ano"], errors="coerce") == 2025].copy()
    d["top10_pct"] = 100 * d["top10_share"]
    top = d.sort_values("top10_pct", ascending=False).head(15).sort_values("top10_pct")
    fig, ax = plt.subplots(figsize=(10, 7))
    ax.barh(top["id_municipio"], top["top10_pct"])
    ax.set(title="Participação dos dez maiores empregadores, 2025", xlabel="% dos vínculos municipais", ylabel="Código IBGE")
    ax.grid(axis="x", alpha=.2)
    salvar(fig, "07_top10_empregadores")


def main():
    figura1(); figura2(); figura3(); figura4(); figura5(); figura6(); figura7()
    print(f"Figuras disponíveis em {FIG}")


if __name__ == "__main__":
    main()
