from __future__ import annotations

"""Gera as oito pranchas cartográficas do Relatório Regional TIC-TIM.

As pranchas são A3 horizontal, EPSG:31983, com títulos, fonte, notas e escala gráfica.
Os mapas quantitativos usam uma escala sequencial/divergente de azul-claro (menores
valores) a vermelho-tinto (maiores valores), conforme o padrão editorial do relatório.

O mapa de intensidade de fluxos somente é produzido quando existe a tabela
`20_intensidade_fluxos.csv`, pois a definição exata do estoque de referência deve ser
reconciliada com o produto canônico antes de automatização definitiva.
"""

from pathlib import Path
import math

import numpy as np
import pandas as pd

try:
    import geopandas as gpd
    import matplotlib.pyplot as plt
    from matplotlib.colors import LinearSegmentedColormap, BoundaryNorm
    from matplotlib.lines import Line2D
    from matplotlib.patches import Patch
except ImportError as exc:
    raise SystemExit('Instale o extra geoespacial: pip install -e ".[geo]"') from exc


ROOT = Path(__file__).resolve().parents[1]
TAB = ROOT / "dados" / "analise_tic_tim" / "tabelas"
MAP = ROOT / "dados" / "analise_tic_tim" / "mapas"
GEO = ROOT / "dados" / "auxiliares" / "municipios_tic_tim_2022.geojson"
REF = ROOT / "referencias" / "tic_tim_fichas_v2_7_quadro1.csv"
MAP.mkdir(parents=True, exist_ok=True)

COLD_HOT = LinearSegmentedColormap.from_list(
    "tic_tim_cold_hot",
    ["#b9e4f4", "#d9eef2", "#f3e6c9", "#e6a36a", "#b84a4a", "#641b2e"],
)


def ler(nome: str, obrigatorio: bool = True) -> pd.DataFrame | None:
    p = TAB / nome
    if not p.exists():
        if obrigatorio:
            raise FileNotFoundError(f"Produto analítico ausente: {p}")
        return None
    return pd.read_csv(p, dtype={"id_municipio": str})


def geo_base() -> gpd.GeoDataFrame:
    if not GEO.exists():
        raise FileNotFoundError(
            f"Malha municipal ausente: {GEO}. Execute `python scripts/baixar_auxiliares_tic_tim.py --somente-malha`."
        )
    g = gpd.read_file(GEO)
    if "id_municipio" not in g:
        raise KeyError("Malha deve conter id_municipio")
    g["id_municipio"] = g["id_municipio"].astype(str).str.zfill(7)
    return g.to_crs(31983)


def nomes() -> pd.DataFrame:
    r = pd.read_csv(REF, dtype={"id_municipio": str})[["id_municipio", "municipio"]]
    r["id_municipio"] = r["id_municipio"].str.zfill(7)
    return r


def _scale_bar(ax, length_km: int = 50) -> None:
    xmin, xmax = ax.get_xlim(); ymin, ymax = ax.get_ylim()
    x0 = xmin + 0.055 * (xmax - xmin)
    y0 = ymin + 0.055 * (ymax - ymin)
    length = length_km * 1000
    ax.plot([x0, x0 + length], [y0, y0], color="black", lw=2)
    ax.plot([x0, x0], [y0 - 1500, y0 + 1500], color="black", lw=1)
    ax.plot([x0 + length, x0 + length], [y0 - 1500, y0 + 1500], color="black", lw=1)
    ax.text(x0, y0 + 3000, "0", fontsize=8, ha="center")
    ax.text(x0 + length, y0 + 3000, f"{length_km} km", fontsize=8, ha="center")


def _north(ax) -> None:
    ax.annotate(
        "N", xy=(0.94, 0.93), xytext=(0.94, 0.82), xycoords="axes fraction",
        ha="center", va="center", fontsize=11, fontweight="bold",
        arrowprops=dict(facecolor="black", width=2, headwidth=8),
    )


def _labels(ax, g: gpd.GeoDataFrame, value_col: str | None = None, decimals: int = 1) -> None:
    pts = g.geometry.representative_point()
    for (_, row), p in zip(g.iterrows(), pts):
        nome = row.get("municipio", row["id_municipio"])
        text = nome
        if value_col and pd.notna(row.get(value_col)):
            text += f"\n{row[value_col]:.{decimals}f}"
        ax.annotate(
            text, (p.x, p.y), xytext=(2, 2), textcoords="offset points",
            fontsize=6.5, ha="left", va="bottom",
            bbox=dict(boxstyle="round,pad=0.15", fc="white", ec="none", alpha=0.68),
        )


def _footer(fig, fonte: str, nota: str) -> None:
    fig.text(0.055, 0.042, f"Fonte: {fonte}", fontsize=8, ha="left")
    fig.text(0.055, 0.024, f"Nota: {nota}", fontsize=7.5, ha="left")
    fig.text(0.945, 0.024, "Elaboração própria. SIRGAS 2000 / UTM 23S — EPSG:31983.", fontsize=7.5, ha="right")


def _base_plot(g: gpd.GeoDataFrame, title: str, subtitle: str):
    fig, ax = plt.subplots(figsize=(16.54, 11.69))
    fig.suptitle(title, fontsize=18, fontweight="bold", y=0.965)
    ax.set_title(subtitle, fontsize=11, pad=10)
    ax.set_axis_off()
    return fig, ax


def _save(fig, stem: str) -> None:
    fig.savefig(MAP / f"{stem}.png", dpi=220, bbox_inches="tight")
    fig.savefig(MAP / f"{stem}.pdf", bbox_inches="tight")
    plt.close(fig)


def mapa1(g0):
    mud = ler("04_mudanca_participacao_regional.csv")
    cres = ler("03_crescimento_municipal.csv")
    g = g0.merge(mud[["id_municipio", "mudanca_pp"]], on="id_municipio").merge(
        cres[["id_municipio", "acrescimo"]], on="id_municipio"
    )
    fig, ax = _base_plot(g, "Mapa 1 — Redistribuição relativa do emprego formal, 2015–2025",
                         "Cor: mudança da participação no estoque regional (p.p.) | círculos: acréscimo absoluto de vínculos")
    vmax = np.nanmax(np.abs(g["mudanca_pp"]))
    g.plot(column="mudanca_pp", cmap=COLD_HOT, vmin=-vmax, vmax=vmax, edgecolor="white", linewidth=.7, ax=ax, legend=True,
           legend_kwds={"label": "Mudança da participação regional (p.p.)", "shrink": .62})
    pts = g.geometry.representative_point()
    maxa = max(float(g["acrescimo"].clip(lower=0).max()), 1)
    sizes = 60 + 1050 * np.sqrt(g["acrescimo"].clip(lower=0) / maxa)
    ax.scatter(pts.x, pts.y, s=sizes, facecolors="none", edgecolors="black", linewidths=.8)
    refs = [10000, 50000, 100000]
    handles = [Line2D([], [], marker="o", linestyle="none", markerfacecolor="none", markeredgecolor="black",
                      markersize=math.sqrt(60 + 1050 * math.sqrt(min(v, maxa) / maxa)) / 1.7,
                      label=f"{v/1000:.0f} mil vínculos") for v in refs]
    ax.legend(handles=handles, title="Acréscimo absoluto", loc="lower right", frameon=True)
    _labels(ax, g, "mudanca_pp", 2); _scale_bar(ax); _north(ax)
    _footer(fig, "RAIS Vínculos/MTE.", "Mudança de participação é contábil e relativa; não implica transferência física de postos entre municípios.")
    _save(fig, "01_redistribuicao_emprego_2015_2025")


def mapa2(g0):
    esp = ler("06_especializacao_principal.csv")
    e = esp[pd.to_numeric(esp["ano"], errors="coerce") == 2025].copy()
    g = g0.merge(e[["id_municipio", "setor", "ql"]], on="id_municipio", how="left")
    cats = sorted(g["setor"].dropna().astype(str).unique())
    cmap = plt.get_cmap("tab20", max(len(cats), 1))
    mapping = {c: i for i, c in enumerate(cats)}
    g["_cat"] = g["setor"].map(mapping)
    fig, ax = _base_plot(g, "Mapa 2 — Principal especialização setorial relativa, 2025",
                         "Divisão CNAE com QL ≥ 1,25, selecionada pela maior escala de vínculos")
    g.plot(column="_cat", categorical=True, cmap=cmap, edgecolor="white", linewidth=.7, ax=ax)
    patches = [Patch(facecolor=cmap(i), label=f"CNAE {c}") for c, i in mapping.items()]
    ax.legend(handles=patches, title="Divisão CNAE", loc="lower right", fontsize=7, ncol=2)
    _labels(ax, g); _scale_bar(ax); _north(ax)
    _footer(fig, "RAIS Vínculos/MTE.", "QL mede especialização relativa no conjunto dos 30 municípios; não mede competitividade nem tamanho absoluto.")
    _save(fig, "02_especializacao_setorial_2025")


def _quant(g0, df, col, title, subtitle, fonte, nota, stem, decimals=1):
    g = g0.merge(df[["id_municipio", col]], on="id_municipio", how="left")
    fig, ax = _base_plot(g, title, subtitle)
    g.plot(column=col, cmap=COLD_HOT, edgecolor="white", linewidth=.7, ax=ax, legend=True,
           legend_kwds={"label": subtitle, "shrink": .62}, missing_kwds={"color": "#eeeeee", "label": "n.d."})
    _labels(ax, g, col, decimals); _scale_bar(ax); _north(ax); _footer(fig, fonte, nota); _save(fig, stem)


def mapa3(g0):
    d = ler("10_hhi_ocupacional.csv"); d = d[pd.to_numeric(d["ano"], errors="coerce") == 2025]
    _quant(g0, d, "hhi", "Mapa 3 — Concentração ocupacional, 2025", "HHI das famílias CBO",
           "RAIS Vínculos/MTE; CBO 2002.", "HHI é descritivo e não constitui medida automática de vulnerabilidade ou qualificação.",
           "03_hhi_ocupacional_2025", 3)


def mapa4(g0):
    d = ler("11_remuneracao_municipal.csv")
    p = d.pivot(index="id_municipio", columns="ano", values="mediana_real")
    out = pd.DataFrame({"id_municipio": p.index, "variacao_real_pct": 100 * (p.get(2025) / p.get(2015) - 1)}).reset_index(drop=True)
    _quant(g0, out, "variacao_real_pct", "Mapa 4 — Variação real da remuneração mediana, 2015–2025",
           "Variação da mediana da remuneração de dezembro, em preços de dezembro de 2025 (%)",
           "RAIS Vínculos/MTE; IPCA/IBGE.", "Remunerações ≤ 0 são excluídas somente das estatísticas remuneratórias.",
           "04_variacao_remuneracao_real_2015_2025", 1)


def mapa5(g0):
    d = ler("20_intensidade_fluxos.csv", obrigatorio=False)
    if d is None:
        print("MAPA 5 NÃO GERADO: falta 20_intensidade_fluxos.csv com a regra canônica do estoque de referência reconciliada.")
        return
    d = d[pd.to_numeric(d["ano"], errors="coerce") == 2025]
    _quant(g0, d, "intensidade_pct", "Mapa 5 — Intensidade aproximada dos fluxos, 2025",
           "[(admissões + desligamentos)/2] / estoque de referência (%)",
           "Novo CAGED/MTE e RAIS Vínculos/MTE.", "Indicador de movimentação relativa; não é taxa longitudinal de rotatividade individual.",
           "05_intensidade_fluxos_2025", 1)


def mapa6(g0):
    d = ler("16_perfil_etario.csv"); d = d[pd.to_numeric(d["ano"], errors="coerce") == 2025]
    _quant(g0, d, "indice_envelhecimento", "Mapa 6 — Índice de envelhecimento do emprego formal, 2025",
           "100 × participação 55+ / participação até 29 anos",
           "RAIS Vínculos/MTE.", "Indicador do estoque formal; não corresponde ao índice demográfico da população residente.",
           "06_indice_envelhecimento_2025", 1)


def mapa7(g0):
    d = ler("13_concentracao_empregadores.csv"); d = d[pd.to_numeric(d["ano"], errors="coerce") == 2025].copy()
    d["top10_pct"] = 100 * d["top10_share"]
    _quant(g0, d, "top10_pct", "Mapa 7 — Concentração nos dez maiores empregadores, 2025",
           "Participação dos dez maiores estabelecimentos no estoque municipal (%)",
           "RAIS Estabelecimentos/MTE.", "Concentração empresarial é descritiva e não equivale automaticamente a vulnerabilidade ou poder de mercado.",
           "07_top10_empregadores_2025", 1)


def mapa8(g0):
    cres = ler("03_crescimento_municipal.csv")[["id_municipio", "variacao_pct"]].rename(columns={"variacao_pct": "crescimento_pct"})
    rem = ler("11_remuneracao_municipal.csv")
    p = rem.pivot(index="id_municipio", columns="ano", values="mediana_real")
    r = pd.DataFrame({"id_municipio": p.index, "rem_pct": 100 * (p.get(2025) / p.get(2015) - 1)}).reset_index(drop=True)
    d = cres.merge(r, on="id_municipio")
    regional = 23.6
    d["classe"] = np.select(
        [(d["crescimento_pct"] > regional) & (d["rem_pct"] > 0),
         (d["crescimento_pct"] > regional) & (d["rem_pct"] <= 0),
         (d["crescimento_pct"] <= regional) & (d["rem_pct"] > 0)],
        ["Crescimento > regional; ganho real", "Crescimento > regional; perda real", "Crescimento ≤ regional; ganho real"],
        default="Crescimento ≤ regional; perda real",
    )
    g = g0.merge(d, on="id_municipio")
    classes = ["Crescimento ≤ regional; perda real", "Crescimento ≤ regional; ganho real",
               "Crescimento > regional; perda real", "Crescimento > regional; ganho real"]
    colors = ["#b9e4f4", "#efe4c7", "#d78065", "#641b2e"]
    cmap = LinearSegmentedColormap.from_list("biv", colors, N=4)
    mapping = {c: i for i, c in enumerate(classes)}; g["_cat"] = g["classe"].map(mapping)
    fig, ax = _base_plot(g, "Mapa 8 — Crescimento do emprego e remuneração real, 2015–2025",
                         "Síntese bivariada: crescimento do estoque × variação real da remuneração mediana")
    g.plot(column="_cat", categorical=True, cmap=cmap, vmin=0, vmax=3, edgecolor="white", linewidth=.7, ax=ax)
    ax.legend(handles=[Patch(facecolor=colors[i], label=c) for i, c in enumerate(classes)], loc="lower right", title="Configuração")
    _labels(ax, g); _scale_bar(ax); _north(ax)
    _footer(fig, "RAIS Vínculos/MTE; IPCA/IBGE.", "Referência de crescimento regional: 23,6%. As classes não constituem tipologia rígida nem índice sintético.")
    _save(fig, "08_sintese_crescimento_remuneracao")


def main():
    g = geo_base().merge(nomes(), on="id_municipio", how="left")
    if len(g) != 30:
        raise RuntimeError(f"A malha deve conter 30 municípios; encontrados {len(g)}")
    mapa1(g); mapa2(g); mapa3(g); mapa4(g); mapa5(g); mapa6(g); mapa7(g); mapa8(g)
    print(f"Mapas gerados em {MAP}")


if __name__ == "__main__":
    main()
