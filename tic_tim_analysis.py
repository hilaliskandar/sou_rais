from __future__ import annotations

"""Funções analíticas reprodutíveis do estudo TIC-TIM de emprego.

O módulo separa as operações metodológicas dos notebooks. Nenhuma função presume
que RAIS, Novo CAGED e CNPJ sejam séries intercambiáveis.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class JanelaAnalitica:
    inicial: int = 2015
    pandemia_pre: int = 2019
    pandemia: int = 2020
    ruptura_admin: int = 2022
    final: int = 2025


JANELA_PADRAO = JanelaAnalitica()


def _assert_cols(df: pd.DataFrame, cols: Iterable[str]) -> None:
    faltantes = [c for c in cols if c not in df.columns]
    if faltantes:
        raise KeyError(f"Colunas ausentes: {faltantes}")


def estoque_vinculos(df: pd.DataFrame, municipio: str = "id_municipio", ano: str = "ano") -> pd.DataFrame:
    """Conta vínculos por município e ano.

    A função supõe que a entrada já represente o universo de vínculos ativos em 31/12
    conforme a extração RAIS utilizada pelo projeto.
    """
    _assert_cols(df, [municipio, ano])
    return (
        df.groupby([municipio, ano], dropna=False)
        .size()
        .rename("estoque")
        .reset_index()
        .sort_values([municipio, ano])
        .reset_index(drop=True)
    )


def trajetoria(estoque: pd.DataFrame, ano_inicial: int = 2015, ano_final: int = 2025) -> pd.DataFrame:
    _assert_cols(estoque, ["id_municipio", "ano", "estoque"])
    p = estoque.pivot(index="id_municipio", columns="ano", values="estoque")
    out = pd.DataFrame(index=p.index)
    out["estoque_inicial"] = p.get(ano_inicial)
    out["estoque_final"] = p.get(ano_final)
    out["variacao_abs"] = out["estoque_final"] - out["estoque_inicial"]
    out["crescimento_pct"] = 100 * (out["estoque_final"] / out["estoque_inicial"] - 1)
    return out.reset_index()


def participacao_regional(estoque: pd.DataFrame) -> pd.DataFrame:
    _assert_cols(estoque, ["id_municipio", "ano", "estoque"])
    out = estoque.copy()
    total = out.groupby("ano")["estoque"].transform("sum")
    out["participacao_regional"] = out["estoque"] / total
    return out


def mudanca_participacao_regional(estoque: pd.DataFrame, ano_inicial: int = 2015, ano_final: int = 2025) -> pd.DataFrame:
    x = participacao_regional(estoque)
    p = x.pivot(index="id_municipio", columns="ano", values="participacao_regional")
    out = pd.DataFrame(index=p.index)
    out["participacao_inicial"] = p.get(ano_inicial)
    out["participacao_final"] = p.get(ano_final)
    out["mudanca_pp"] = 100 * (out["participacao_final"] - out["participacao_inicial"])
    return out.reset_index()


def quociente_locacional(
    base: pd.DataFrame,
    setor: str = "setor",
    valor: str = "vinculos",
    municipio: str = "id_municipio",
    ano: str = "ano",
) -> pd.DataFrame:
    """Calcula QL usando os 30 municípios como universo de referência.

    QL = participação do setor no município / participação do setor no universo.
    """
    _assert_cols(base, [municipio, ano, setor, valor])
    out = base.copy()
    total_m = out.groupby([municipio, ano])[valor].transform("sum")
    out["share_municipal"] = out[valor] / total_m
    reg = out.groupby([ano, setor], as_index=False)[valor].sum().rename(columns={valor: "vinculos_regiao"})
    reg["total_regiao"] = reg.groupby(ano)["vinculos_regiao"].transform("sum")
    reg["share_regional"] = reg["vinculos_regiao"] / reg["total_regiao"]
    out = out.merge(reg[[ano, setor, "share_regional"]], on=[ano, setor], how="left")
    out["ql"] = out["share_municipal"] / out["share_regional"]
    return out


def especializacao_principal(ql: pd.DataFrame, limiar: float = 1.25, min_vinculos: int = 1) -> pd.DataFrame:
    """Seleciona a especialização de maior escala entre setores com QL >= limiar.

    O critério privilegia escala substantiva: filtra pelo QL e então ordena vínculos,
    usando QL como desempate.
    """
    _assert_cols(ql, ["id_municipio", "ano", "setor", "vinculos", "ql"])
    x = ql[(ql["ql"] >= limiar) & (ql["vinculos"] >= min_vinculos)].copy()
    if x.empty:
        return pd.DataFrame(columns=["id_municipio", "ano", "setor", "vinculos", "ql"])
    x = x.sort_values(["id_municipio", "ano", "vinculos", "ql"], ascending=[True, True, False, False])
    return x.groupby(["id_municipio", "ano"], as_index=False).first()


def hhi(
    base: pd.DataFrame,
    categoria: str,
    valor: str = "vinculos",
    municipio: str = "id_municipio",
    ano: str = "ano",
) -> pd.DataFrame:
    """HHI municipal e número efetivo de categorias (1/HHI)."""
    _assert_cols(base, [municipio, ano, categoria, valor])
    x = base.copy()
    x["share"] = x[valor] / x.groupby([municipio, ano])[valor].transform("sum")
    out = x.assign(_sq=x["share"] ** 2).groupby([municipio, ano], as_index=False)["_sq"].sum()
    out = out.rename(columns={"_sq": "hhi"})
    out["numero_efetivo"] = np.where(out["hhi"] > 0, 1 / out["hhi"], np.nan)
    return out


def shift_share(
    base: pd.DataFrame,
    ano_inicial: int,
    ano_final: int,
    setor: str = "setor",
    valor: str = "vinculos",
) -> pd.DataFrame:
    """Decomposição shift-share clássica para município x setor.

    Componentes:
    - efeito_regional = E_i0 * g
    - efeito_mix = E_i0 * (g_i - g)
    - efeito_local = E_i0 * (g_ij - g_i)

    Linhas com estoque setorial inicial zero permanecem marcadas como não elegíveis.
    O erro de reconstrução é calculado explicitamente.
    """
    _assert_cols(base, ["id_municipio", "ano", setor, valor])
    b = base[base["ano"].isin([ano_inicial, ano_final])].copy()
    p = b.pivot_table(index=["id_municipio", setor], columns="ano", values=valor, aggfunc="sum", fill_value=0).reset_index()
    p = p.rename(columns={ano_inicial: "e0", ano_final: "e1"})
    if "e0" not in p: p["e0"] = 0.0
    if "e1" not in p: p["e1"] = 0.0

    reg = b.groupby(["ano", setor], as_index=False)[valor].sum()
    rp = reg.pivot(index=setor, columns="ano", values=valor).fillna(0)
    rp["g_setor"] = np.where(rp.get(ano_inicial, 0) > 0, rp.get(ano_final, 0) / rp.get(ano_inicial, 0) - 1, np.nan)
    g_setor = rp["g_setor"].to_dict()

    total0 = float(reg.loc[reg["ano"] == ano_inicial, valor].sum())
    total1 = float(reg.loc[reg["ano"] == ano_final, valor].sum())
    g = total1 / total0 - 1 if total0 > 0 else np.nan

    p["elegivel"] = p["e0"] > 0
    p["g_regional"] = g
    p["g_setorial"] = p[setor].map(g_setor)
    p["g_local"] = np.where(p["e0"] > 0, p["e1"] / p["e0"] - 1, np.nan)
    p["variacao_observada"] = p["e1"] - p["e0"]
    p["efeito_regional"] = np.where(p["elegivel"], p["e0"] * p["g_regional"], np.nan)
    p["efeito_mix"] = np.where(p["elegivel"], p["e0"] * (p["g_setorial"] - p["g_regional"]), np.nan)
    p["efeito_local"] = np.where(p["elegivel"], p["e0"] * (p["g_local"] - p["g_setorial"]), np.nan)
    p["reconstruida"] = p[["efeito_regional", "efeito_mix", "efeito_local"]].sum(axis=1, min_count=3)
    p["erro_reconstrucao"] = p["variacao_observada"] - p["reconstruida"]
    return p


def deflacionar_remuneracao(
    df: pd.DataFrame,
    ipca: pd.DataFrame,
    coluna_remuneracao: str,
    coluna_ano: str = "ano",
    coluna_indice: str = "indice",
    ano_base: int = 2025,
) -> pd.DataFrame:
    """Deflaciona remuneração nominal para preços de dezembro do ano-base.

    A tabela `ipca` deve conter um índice de nível para dezembro de cada ano.
    """
    _assert_cols(df, [coluna_ano, coluna_remuneracao])
    _assert_cols(ipca, [coluna_ano, coluna_indice])
    x = df.merge(ipca[[coluna_ano, coluna_indice]], on=coluna_ano, how="left")
    base = ipca.loc[ipca[coluna_ano] == ano_base, coluna_indice]
    if base.empty:
        raise ValueError(f"IPCA do ano-base {ano_base} não encontrado")
    indice_base = float(base.iloc[0])
    x["remuneracao_real"] = pd.to_numeric(x[coluna_remuneracao], errors="coerce") * indice_base / x[coluna_indice]
    return x


def resumo_remuneracao(
    df: pd.DataFrame,
    remuneracao: str = "remuneracao_real",
    municipio: str = "id_municipio",
    ano: str = "ano",
) -> pd.DataFrame:
    """Resumo remuneratório excluindo valores <= 0 somente dos cálculos salariais."""
    _assert_cols(df, [municipio, ano, remuneracao])
    x = df.copy()
    r = pd.to_numeric(x[remuneracao], errors="coerce")
    x["_r"] = r
    x["_positivo"] = r > 0
    total = x.groupby([municipio, ano]).size().rename("vinculos_total")
    pos = x[x["_positivo"]].groupby([municipio, ano])["_r"].agg(
        vinculos_remuneracao="count",
        media="mean",
        mediana="median",
        p25=lambda s: s.quantile(.25),
        p75=lambda s: s.quantile(.75),
        massa_salarial="sum",
    )
    out = total.to_frame().join(pos, how="left").reset_index()
    out["cobertura_remuneratoria"] = out["vinculos_remuneracao"] / out["vinculos_total"]
    return out


def intensidade_fluxos(admissoes: float, desligamentos: float, estoque_referencia: float) -> float:
    """[(admissões + desligamentos)/2] / estoque de referência."""
    if pd.isna(estoque_referencia) or estoque_referencia <= 0:
        return np.nan
    return ((admissoes + desligamentos) / 2) / estoque_referencia


def perfil_etario(df: pd.DataFrame, idade: str = "idade", municipio: str = "id_municipio", ano: str = "ano") -> pd.DataFrame:
    _assert_cols(df, [municipio, ano, idade])
    x = df[[municipio, ano, idade]].copy()
    x[idade] = pd.to_numeric(x[idade], errors="coerce")

    def _calc(g: pd.DataFrame) -> pd.Series:
        s = g[idade].dropna()
        n = len(s)
        jovens = (s <= 29).sum()
        velhos = (s >= 55).sum()
        pj = jovens / n if n else np.nan
        pv = velhos / n if n else np.nan
        ie = 100 * pv / pj if pj and pj > 0 else np.nan
        return pd.Series({
            "n_idade_valida": n,
            "idade_mediana": s.median() if n else np.nan,
            "share_ate29": pj,
            "share_55mais": pv,
            "indice_envelhecimento": ie,
        })

    return x.groupby([municipio, ano], dropna=False).apply(_calc, include_groups=False).reset_index()


def gap_mediano_sexo(df: pd.DataFrame, remuneracao: str, sexo: str = "sexo", feminino="F", masculino="M") -> pd.DataFrame:
    """Gap = 100 * (mediana feminina / mediana masculina - 1)."""
    _assert_cols(df, ["id_municipio", "ano", sexo, remuneracao])
    x = df[pd.to_numeric(df[remuneracao], errors="coerce") > 0].copy()
    med = x.groupby(["id_municipio", "ano", sexo])[remuneracao].median().unstack(sexo)
    med["gap_sexo_pct"] = 100 * (med.get(feminino) / med.get(masculino) - 1)
    return med.reset_index()


def gap_medio_raca(
    df: pd.DataFrame,
    remuneracao: str,
    raca: str = "raca_cor",
    brancos: Iterable = ("Branca", "Branco", 2, "2"),
    pretos_pardos: Iterable = ("Preta", "Preto", "Parda", "Pardo", 4, 8, "4", "8"),
) -> pd.DataFrame:
    """Gap racial publicado: média pretos/pardos versus brancos, só raça identificada."""
    _assert_cols(df, ["id_municipio", "ano", raca, remuneracao])
    x = df.copy()
    x["_r"] = pd.to_numeric(x[remuneracao], errors="coerce")
    x = x[x["_r"] > 0]
    x["grupo"] = np.select(
        [x[raca].isin(list(brancos)), x[raca].isin(list(pretos_pardos))],
        ["brancos", "pretos_pardos"],
        default="nao_identificado",
    )
    x = x[x["grupo"] != "nao_identificado"]
    med = x.groupby(["id_municipio", "ano", "grupo"])["_r"].mean().unstack("grupo")
    med["gap_raca_pct"] = 100 * (med.get("pretos_pardos") / med.get("brancos") - 1)
    return med.reset_index()


def concentracao_empregadores(
    df: pd.DataFrame,
    estabelecimento: str = "id_estabelecimento",
    municipio: str = "id_municipio",
    ano: str = "ano",
    top_ns: tuple[int, ...] = (1, 5, 10, 20),
) -> pd.DataFrame:
    _assert_cols(df, [municipio, ano, estabelecimento])
    g = df.groupby([municipio, ano, estabelecimento]).size().rename("vinculos").reset_index()

    def _calc(x: pd.DataFrame) -> pd.Series:
        total = x["vinculos"].sum()
        shares = x["vinculos"] / total if total else np.nan
        d = {
            "estabelecimentos_positivos": len(x),
            "hhi_empresarial": float((shares ** 2).sum()) if total else np.nan,
        }
        for n in top_ns:
            d[f"top{n}_share"] = x.nlargest(n, "vinculos")["vinculos"].sum() / total if total else np.nan
        return pd.Series(d)

    return g.groupby([municipio, ano]).apply(_calc, include_groups=False).reset_index()


def referencia_escolaridade_cbo(
    df: pd.DataFrame,
    escolaridade: str = "escolaridade",
    cbo: str = "cbo_familia",
    min_celula: int = 50,
) -> pd.DataFrame:
    """Benchmark empírico por família CBO/ano e classe de distância ordinal."""
    _assert_cols(df, ["ano", cbo, escolaridade])
    x = df.copy()
    x[escolaridade] = pd.to_numeric(x[escolaridade], errors="coerce")
    ref = x.groupby(["ano", cbo])[escolaridade].agg(["count", "median"]).reset_index()
    ref.loc[ref["count"] < min_celula, "median"] = np.nan
    ref = ref.rename(columns={"median": "escolaridade_ref", "count": "n_ref"})
    out = x.merge(ref, on=["ano", cbo], how="left")
    out["distancia_escolaridade"] = out[escolaridade] - out["escolaridade_ref"]
    out["classe_referencia"] = np.select(
        [out["distancia_escolaridade"] >= 2, out["distancia_escolaridade"] <= -2],
        ["acima", "abaixo"],
        default="proximo",
    )
    out.loc[out["escolaridade_ref"].isna(), "classe_referencia"] = "sem_referencia"
    return out


def salvar_csv_com_hash(df: pd.DataFrame, path: Path) -> dict:
    import hashlib

    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)
    h = hashlib.sha256(path.read_bytes()).hexdigest()
    return {"arquivo": str(path), "linhas": len(df), "sha256": h}
