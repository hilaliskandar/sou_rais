from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping

import numpy as np
import pandas as pd


COLUMN_CANDIDATES: dict[str, tuple[str, ...]] = {
    "municipio": ("id_municipio", "municipio", "cod_municipio", "codigo_municipio"),
    "ano": ("ano", "ano_rais"),
    "competencia": ("ano_mes", "competencia", "mes"),
    "cnae": ("cnae_2", "cnae_2_subclasse", "cnae_2_classe", "cnae"),
    "cbo": ("cbo_2002", "cbo_2002_familia", "cbo"),
    "remuneracao": (
        "remuneracao_media",
        "valor_remuneracao_media",
        "remuneracao_dezembro_nominal",
        "salario_medio",
    ),
    "sexo": ("sexo",),
    "idade": ("idade",),
    "escolaridade": ("escolaridade",),
    "raca_cor": ("raca_cor", "raca"),
    "estabelecimento": ("id_estabelecimento", "cnpj", "cnpj_basico"),
    "saldo": ("saldo_movimentacao", "saldo"),
    "admissoes": ("admissoes", "admitidos"),
    "desligamentos": ("desligamentos", "desligados"),
    "snapshot": ("snapshot", "data", "data_extracao"),
}


@dataclass(frozen=True)
class AnalisePaths:
    root: Path

    @property
    def processado(self) -> Path:
        return self.root / "dados" / "processado"

    @property
    def saida(self) -> Path:
        return self.root / "dados" / "analise_tic_tim"

    @property
    def tabelas(self) -> Path:
        return self.saida / "tabelas"

    @property
    def figuras(self) -> Path:
        return self.saida / "figuras"

    @property
    def mapas(self) -> Path:
        return self.saida / "mapas"

    @property
    def controle(self) -> Path:
        return self.saida / "controle"

    def criar(self) -> None:
        for p in (self.saida, self.tabelas, self.figuras, self.mapas, self.controle):
            p.mkdir(parents=True, exist_ok=True)


def resolve_col(df: pd.DataFrame, key: str, required: bool = False) -> str | None:
    for name in COLUMN_CANDIDATES[key]:
        if name in df.columns:
            return name
    if required:
        raise KeyError(f"Nenhuma coluna compatível com '{key}' encontrada. Candidatas: {COLUMN_CANDIDATES[key]}")
    return None


def padronizar_municipio(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df.copy()
    out = df.copy()
    c = resolve_col(out, "municipio", required=True)
    if c != "id_municipio":
        out = out.rename(columns={c: "id_municipio"})
    out["id_municipio"] = out["id_municipio"].astype(str).str.replace(r"\.0$", "", regex=True).str.zfill(7)
    return out


def ler_parquets(pasta: Path) -> pd.DataFrame:
    arquivos = sorted(pasta.rglob("*.parquet")) if pasta.exists() else []
    if not arquivos:
        return pd.DataFrame()
    partes: list[pd.DataFrame] = []
    for arquivo in arquivos:
        df = pd.read_parquet(arquivo)
        df["_arquivo_fonte"] = str(arquivo)
        partes.append(df)
    return pd.concat(partes, ignore_index=True) if partes else pd.DataFrame()


def setor_cnae_2(value: object) -> str:
    s = "" if pd.isna(value) else str(value)
    digitos = "".join(ch for ch in s if ch.isdigit())
    return digitos[:2] if len(digitos) >= 2 else s


def estoque_rais(vinculos: pd.DataFrame) -> pd.DataFrame:
    df = padronizar_municipio(vinculos)
    ano = resolve_col(df, "ano", required=True)
    out = (
        df.groupby(["id_municipio", ano], dropna=False)
        .size()
        .rename("estoque")
        .reset_index()
        .rename(columns={ano: "ano"})
    )
    out["ano"] = pd.to_numeric(out["ano"], errors="raise").astype(int)
    return out.sort_values(["id_municipio", "ano"]).reset_index(drop=True)


def estoque_regional(estoque: pd.DataFrame) -> pd.DataFrame:
    out = estoque.groupby("ano", as_index=False)["estoque"].sum().sort_values("ano")
    out["variacao_pct"] = out["estoque"].pct_change() * 100
    return out.reset_index(drop=True)


def crescimento_municipal(estoque: pd.DataFrame, ano_inicial: int | None = None, ano_final: int | None = None) -> pd.DataFrame:
    if estoque.empty:
        return pd.DataFrame(columns=["id_municipio", "estoque_inicial", "estoque_final", "acrescimo", "variacao_pct", "contribuicao_pct"])
    ano_inicial = int(ano_inicial if ano_inicial is not None else estoque["ano"].min())
    ano_final = int(ano_final if ano_final is not None else estoque["ano"].max())
    p = estoque.pivot_table(index="id_municipio", columns="ano", values="estoque", aggfunc="sum", fill_value=0)
    out = pd.DataFrame(index=p.index)
    out["estoque_inicial"] = p[ano_inicial] if ano_inicial in p.columns else 0
    out["estoque_final"] = p[ano_final] if ano_final in p.columns else 0
    out["acrescimo"] = out["estoque_final"] - out["estoque_inicial"]
    out["variacao_pct"] = np.where(out["estoque_inicial"] > 0, 100 * (out["estoque_final"] / out["estoque_inicial"] - 1), np.nan)
    total = out["acrescimo"].sum()
    out["contribuicao_pct"] = np.where(total != 0, 100 * out["acrescimo"] / total, np.nan)
    return out.reset_index().sort_values("acrescimo", ascending=False).reset_index(drop=True)


def estrutura_setorial_ql(vinculos: pd.DataFrame) -> pd.DataFrame:
    df = padronizar_municipio(vinculos)
    ano = resolve_col(df, "ano", required=True)
    cnae = resolve_col(df, "cnae", required=True)
    base = df[["id_municipio", ano, cnae]].copy()
    base.columns = ["id_municipio", "ano", "cnae"]
    base["setor"] = base["cnae"].map(setor_cnae_2)
    g = base.groupby(["id_municipio", "ano", "setor"], dropna=False).size().rename("vinculos").reset_index()
    g["share_mun"] = g["vinculos"] / g.groupby(["id_municipio", "ano"])["vinculos"].transform("sum")
    reg = g.groupby(["ano", "setor"], as_index=False)["vinculos"].sum()
    reg["share_reg"] = reg["vinculos"] / reg.groupby("ano")["vinculos"].transform("sum")
    out = g.merge(reg[["ano", "setor", "share_reg"]], on=["ano", "setor"], how="left")
    out["ql"] = out["share_mun"] / out["share_reg"]
    return out.sort_values(["ano", "id_municipio", "setor"]).reset_index(drop=True)


def hhi_setorial(estrutura: pd.DataFrame) -> pd.DataFrame:
    x = estrutura.copy()
    x["_sq"] = x["share_mun"] ** 2
    return (
        x.groupby(["id_municipio", "ano"], as_index=False)["_sq"]
        .sum()
        .rename(columns={"_sq": "hhi"})
        .sort_values(["ano", "id_municipio"])
        .reset_index(drop=True)
    )


def numero_efetivo_setores(hhi: pd.DataFrame) -> pd.DataFrame:
    out = hhi.copy()
    out["numero_efetivo_setores"] = np.where(out["hhi"] > 0, 1 / out["hhi"], np.nan)
    return out


def estrutura_ocupacional(vinculos: pd.DataFrame) -> pd.DataFrame:
    df = padronizar_municipio(vinculos)
    ano = resolve_col(df, "ano", required=True)
    cbo = resolve_col(df, "cbo", required=True)
    base = df[["id_municipio", ano, cbo]].copy()
    base.columns = ["id_municipio", "ano", "cbo"]
    base["cbo"] = base["cbo"].astype(str)
    return base.groupby(["id_municipio", "ano", "cbo"]).size().rename("vinculos").reset_index()


def resumo_categoria(vinculos: pd.DataFrame, key: str) -> pd.DataFrame:
    df = padronizar_municipio(vinculos)
    ano = resolve_col(df, "ano", required=True)
    cat = resolve_col(df, key, required=True)
    out = df.groupby(["id_municipio", ano, cat], dropna=False).size().rename("vinculos").reset_index()
    return out.rename(columns={ano: "ano", cat: key})


def faixa_etaria(vinculos: pd.DataFrame) -> pd.DataFrame:
    df = padronizar_municipio(vinculos)
    ano = resolve_col(df, "ano", required=True)
    idade = resolve_col(df, "idade", required=True)
    base = df[["id_municipio", ano, idade]].copy()
    base.columns = ["id_municipio", "ano", "idade"]
    base["idade"] = pd.to_numeric(base["idade"], errors="coerce")
    bins = [-np.inf, 17, 24, 29, 39, 49, 59, np.inf]
    labels = ["<=17", "18-24", "25-29", "30-39", "40-49", "50-59", "60+"]
    base["faixa_etaria"] = pd.cut(base["idade"], bins=bins, labels=labels)
    return base.groupby(["id_municipio", "ano", "faixa_etaria"], observed=True).size().rename("vinculos").reset_index()


def remuneracao_municipal(vinculos: pd.DataFrame) -> pd.DataFrame:
    df = padronizar_municipio(vinculos)
    ano = resolve_col(df, "ano", required=True)
    remun = resolve_col(df, "remuneracao", required=True)
    base = df[["id_municipio", ano, remun]].copy()
    base.columns = ["id_municipio", "ano", "remuneracao"]
    base["remuneracao"] = pd.to_numeric(base["remuneracao"], errors="coerce")
    return base.groupby(["id_municipio", "ano"])["remuneracao"].agg(n="count", media="mean", mediana="median").reset_index()


def concentracao_top_n(vinculos: pd.DataFrame, n: int = 10) -> pd.DataFrame:
    df = padronizar_municipio(vinculos)
    ano = resolve_col(df, "ano", required=True)
    estab = resolve_col(df, "estabelecimento", required=True)
    g = df.groupby(["id_municipio", ano, estab]).size().rename("vinculos").reset_index()
    g.columns = ["id_municipio", "ano", "estabelecimento", "vinculos"]
    rows: list[dict[str, object]] = []
    for (mun, a), bloco in g.groupby(["id_municipio", "ano"]):
        total = int(bloco["vinculos"].sum())
        top = int(bloco.nlargest(n, "vinculos")["vinculos"].sum())
        rows.append({"id_municipio": mun, "ano": int(a), "vinculos_total": total, f"vinculos_top{n}": top, f"share_top{n}": top / total if total else np.nan})
    return pd.DataFrame(rows).sort_values(["ano", "id_municipio"]).reset_index(drop=True)


def caged_fluxos(caged: pd.DataFrame) -> pd.DataFrame:
    df = padronizar_municipio(caged)
    comp = resolve_col(df, "competencia", required=True)
    saldo = resolve_col(df, "saldo")
    adm = resolve_col(df, "admissoes")
    deslig = resolve_col(df, "desligamentos")
    keys = ["id_municipio", comp]
    if saldo:
        out = df.groupby(keys, as_index=False)[saldo].sum().rename(columns={comp: "competencia", saldo: "saldo"})
    elif adm and deslig:
        out = df.groupby(keys, as_index=False)[[adm, deslig]].sum().rename(columns={comp: "competencia", adm: "admissoes", deslig: "desligamentos"})
        out["saldo"] = out["admissoes"] - out["desligamentos"]
    else:
        out = df.groupby(keys).size().rename("movimentacoes").reset_index().rename(columns={comp: "competencia"})
    return out


def cnpj_fotografia(cnpj: pd.DataFrame) -> pd.DataFrame:
    df = padronizar_municipio(cnpj)
    snapshot = resolve_col(df, "snapshot")
    keys = ["id_municipio"] + ([snapshot] if snapshot else [])
    out = df.groupby(keys).size().rename("cnpjs").reset_index()
    if snapshot and snapshot != "snapshot":
        out = out.rename(columns={snapshot: "snapshot"})
    return out


def sha256(path: Path, chunk: int = 1024 * 1024) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for bloco in iter(lambda: f.read(chunk), b""):
            h.update(bloco)
    return h.hexdigest()


def manifesto_produtos(root: Path, arquivos: Iterable[Path]) -> pd.DataFrame:
    rows = []
    for path in sorted(set(Path(p) for p in arquivos)):
        if path.is_file():
            try:
                rel = str(path.relative_to(root))
            except ValueError:
                rel = str(path)
            rows.append({"arquivo": rel, "bytes": path.stat().st_size, "sha256": sha256(path)})
    return pd.DataFrame(rows)


def salvar_json(path: Path, payload: Mapping[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
