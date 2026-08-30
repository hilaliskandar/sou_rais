from __future__ import annotations

"""Gera a camada analítica TIC-TIM a partir dos Parquets adquiridos pelo sou_rais.

O script implementa o núcleo municipal/regional necessário aos gates de equivalência das
fichas publicadas. Mantém RAIS Vínculos, RAIS Estabelecimentos, Novo CAGED e CNPJ como
universos distintos e falha explicitamente quando uma variável necessária não existe.
"""

import hashlib
import json
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd

from tic_tim_analysis import (
    deflacionar_remuneracao,
    especializacao_principal,
    gap_medio_raca,
    gap_mediano_sexo,
    hhi,
    mudanca_participacao_regional,
    perfil_etario,
    quociente_locacional,
    referencia_escolaridade_cbo,
    resumo_remuneracao,
    shift_share,
    trajetoria,
)


MARCOS = [2015, 2019, 2020, 2022, 2025]


def ler_parquets(pasta: Path) -> pd.DataFrame:
    arquivos = sorted(pasta.rglob("*.parquet")) if pasta.exists() else []
    if not arquivos:
        return pd.DataFrame()
    partes = []
    for arquivo in arquivos:
        df = pd.read_parquet(arquivo)
        df["_arquivo_fonte"] = str(arquivo)
        partes.append(df)
    return pd.concat(partes, ignore_index=True)


def resolver(df: pd.DataFrame, candidatos: Iterable[str], obrigatoria: bool = True) -> str | None:
    for c in candidatos:
        if c in df.columns:
            return c
    if obrigatoria:
        raise KeyError(f"Nenhuma das colunas candidatas foi encontrada: {list(candidatos)}")
    return None


def normalizar_municipio(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df.copy()
    out = df.copy()
    c = resolver(out, ["id_municipio", "municipio", "cod_municipio", "codigo_municipio"])
    if c != "id_municipio":
        out = out.rename(columns={c: "id_municipio"})
    out["id_municipio"] = (
        out["id_municipio"].astype(str).str.replace(r"\.0$", "", regex=True).str.zfill(7)
    )
    return out


def normalizar_ano(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    c = resolver(out, ["ano", "ano_rais"])
    if c != "ano":
        out = out.rename(columns={c: "ano"})
    out["ano"] = pd.to_numeric(out["ano"], errors="raise").astype(int)
    return out


def setor2(v: object) -> str:
    s = "" if pd.isna(v) else str(v)
    d = "".join(ch for ch in s if ch.isdigit())
    return d[:2] if len(d) >= 2 else s


def familia_cbo4(v: object) -> str:
    s = "" if pd.isna(v) else str(v)
    d = "".join(ch for ch in s if ch.isdigit())
    return d[:4] if len(d) >= 4 else d


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for bloco in iter(lambda: f.read(1024 * 1024), b""):
            h.update(bloco)
    return h.hexdigest()


def salvar(df: pd.DataFrame, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)
    return path


def estoque_rais(vinculos: pd.DataFrame) -> pd.DataFrame:
    return (
        vinculos.groupby(["id_municipio", "ano"], dropna=False)
        .size()
        .rename("estoque")
        .reset_index()
        .sort_values(["id_municipio", "ano"])
        .reset_index(drop=True)
    )


def crescimento_municipal(estoque: pd.DataFrame, ano_inicial: int = 2015, ano_final: int = 2025) -> pd.DataFrame:
    t = trajetoria(estoque, ano_inicial, ano_final).rename(
        columns={"variacao_abs": "acrescimo", "crescimento_pct": "variacao_pct"}
    )
    total = t["acrescimo"].sum()
    t["contribuicao_pct"] = np.where(total != 0, 100 * t["acrescimo"] / total, np.nan)
    return t.sort_values("acrescimo", ascending=False).reset_index(drop=True)


def estrutura_setorial(vinculos: pd.DataFrame) -> pd.DataFrame:
    cnae = resolver(vinculos, ["cnae_2", "cnae_2_subclasse", "cnae_2_classe", "cnae"])
    base = vinculos[["id_municipio", "ano", cnae]].copy()
    base["setor"] = base[cnae].map(setor2)
    base = base[base["setor"].astype(str).str.len() > 0]
    return (
        base.groupby(["id_municipio", "ano", "setor"])
        .size().rename("vinculos").reset_index()
    )


def estrutura_ocupacional(vinculos: pd.DataFrame) -> pd.DataFrame:
    cbo = resolver(vinculos, ["cbo_2002", "cbo_2002_familia", "cbo"])
    base = vinculos[["id_municipio", "ano", cbo]].copy()
    base["cbo_familia"] = base[cbo].map(familia_cbo4)
    base = base[base["cbo_familia"].str.len() == 4]
    return (
        base.groupby(["id_municipio", "ano", "cbo_familia"])
        .size().rename("vinculos").reset_index()
    )


def remuneracao_real(vinculos: pd.DataFrame, ipca_path: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    remun = resolver(
        vinculos,
        [
            "valor_remuneracao_dezembro",
            "remuneracao_dezembro_nominal",
            "valor_remuneracao_media",
            "remuneracao_media",
        ],
    )
    if not ipca_path.exists():
        raise FileNotFoundError(
            f"IPCA auxiliar não encontrado em {ipca_path}. Execute `python scripts/baixar_auxiliares_tic_tim.py --somente-ipca`."
        )
    ipca = pd.read_csv(ipca_path)
    base = vinculos.copy()
    base[remun] = pd.to_numeric(base[remun], errors="coerce")
    real = deflacionar_remuneracao(base, ipca, coluna_remuneracao=remun, coluna_ano="ano", ano_base=2025)
    resumo = resumo_remuneracao(real, remuneracao="remuneracao_real")
    resumo = resumo.rename(
        columns={
            "media": "media_real",
            "mediana": "mediana_real",
            "p25": "p25_real",
            "p75": "p75_real",
        }
    )
    resumo["massa_salarial_milhoes"] = resumo["massa_salarial"] / 1_000_000
    return real, resumo


def _sexo_norm(v: object) -> str | None:
    if pd.isna(v):
        return None
    s = str(v).strip().lower()
    # Base dos Dados/MTE pode expor código ou rótulo conforme versão da tabela.
    # A função aceita apenas codificações usuais e transparentes; valores desconhecidos
    # permanecem ausentes e são relatados na auditoria.
    if s in {"1", "m", "masculino", "homem"}:
        return "M"
    if s in {"2", "f", "feminino", "mulher"}:
        return "F"
    return None


def perfil_sexo(vinculos: pd.DataFrame, remuneracao_col: str = "remuneracao_real") -> pd.DataFrame:
    sexo = resolver(vinculos, ["sexo"])
    x = vinculos[["id_municipio", "ano", sexo]].copy()
    x["sexo_norm"] = x[sexo].map(_sexo_norm)
    rows = []
    for (m, a), g in x.groupby(["id_municipio", "ano"]):
        valid = g["sexo_norm"].notna().sum()
        mulheres = (g["sexo_norm"] == "F").sum()
        rows.append(
            {
                "id_municipio": m,
                "ano": int(a),
                "sexo_classificado": int(valid),
                "mulheres": int(mulheres),
                "mulheres_pct": 100 * mulheres / valid if valid else np.nan,
                "cobertura_sexo": valid / len(g) if len(g) else np.nan,
            }
        )
    return pd.DataFrame(rows)


def consolidar_caged(caged: pd.DataFrame) -> pd.DataFrame:
    """Consolida movimentos do Novo CAGED em ano municipal.

    O microdado público registra `saldo_movimentacao` com +1 para admissão e -1 para
    desligamento. Caso uma versão futura ofereça colunas agregadas de admissões e
    desligamentos, elas são aceitas explicitamente.
    """
    if caged.empty:
        return pd.DataFrame()
    x = normalizar_municipio(caged)
    ano = resolver(x, ["ano"])
    if ano != "ano":
        x = x.rename(columns={ano: "ano"})
    x["ano"] = pd.to_numeric(x["ano"], errors="raise").astype(int)

    adm = resolver(x, ["admissoes", "admitidos"], obrigatoria=False)
    des = resolver(x, ["desligamentos", "desligados"], obrigatoria=False)
    if adm and des:
        g = x.groupby(["id_municipio", "ano"], as_index=False)[[adm, des]].sum()
        g = g.rename(columns={adm: "admissoes", des: "desligamentos"})
    else:
        saldo = resolver(x, ["saldo_movimentacao", "saldo"])
        sm = pd.to_numeric(x[saldo], errors="coerce")
        valid = sm.isin([-1, 1])
        if not valid.all():
            valores = sorted(sm[~valid].dropna().unique().tolist())[:20]
            raise ValueError(
                "Novo CAGED em nível de microdado exige saldo_movimentacao em {-1,+1}. "
                f"Valores inesperados encontrados: {valores}"
            )
        x["_adm"] = (sm == 1).astype(int)
        x["_des"] = (sm == -1).astype(int)
        g = x.groupby(["id_municipio", "ano"], as_index=False)[["_adm", "_des"]].sum()
        g = g.rename(columns={"_adm": "admissoes", "_des": "desligamentos"})
    g["saldo"] = g["admissoes"] - g["desligamentos"]
    return g.sort_values(["ano", "id_municipio"]).reset_index(drop=True)


def concentracao_empregadores_rais(estabelecimentos: pd.DataFrame) -> pd.DataFrame:
    """Calcula concentração com RAIS Estabelecimentos e estoque positivo.

    A rotina usa a quantidade de vínculos ativos do estabelecimento como peso. O identificador
    do estabelecimento precisa existir no schema; se não existir, o erro é explícito.
    """
    if estabelecimentos.empty:
        return pd.DataFrame()
    x = normalizar_ano(normalizar_municipio(estabelecimentos))
    estoque = resolver(
        x,
        ["quantidade_vinculos_ativos", "qtd_vinculos_ativos", "vinculos_ativos", "estoque_vinculos"],
    )
    estab = resolver(
        x,
        ["id_estabelecimento", "cnpj", "cnpj_estabelecimento", "cnpj_completo", "cnpj_basico"],
    )
    x["_estoque"] = pd.to_numeric(x[estoque], errors="coerce")
    x = x[x["_estoque"] > 0].copy()
    # Um mesmo estabelecimento pode aparecer duplicado por schema/particionamento; soma-se
    # dentro do município-ano-identificador antes de calcular shares.
    g = x.groupby(["id_municipio", "ano", estab], as_index=False)["_estoque"].sum()
    rows = []
    for (m, a), b in g.groupby(["id_municipio", "ano"]):
        total = float(b["_estoque"].sum())
        shares = b["_estoque"] / total if total > 0 else pd.Series(dtype=float)
        ordv = b["_estoque"].sort_values(ascending=False)
        rec = {
            "id_municipio": m,
            "ano": int(a),
            "empregadores_positivos": int(len(b)),
            "estoque_rais_estabelecimentos": total,
            "hhi_empresarial": float((shares ** 2).sum()) if total > 0 else np.nan,
        }
        for n in [1, 5, 10, 20]:
            rec[f"top{n}_share"] = float(ordv.head(n).sum() / total) if total > 0 else np.nan
        rows.append(rec)
    return pd.DataFrame(rows).sort_values(["ano", "id_municipio"]).reset_index(drop=True)


def fotografia_cnpj(cnpj: pd.DataFrame) -> pd.DataFrame:
    if cnpj.empty:
        return pd.DataFrame()
    x = normalizar_municipio(cnpj)
    snap = resolver(x, ["snapshot", "data", "data_extracao"], obrigatoria=False)
    situ = resolver(x, ["situacao_cadastral", "situacao"], obrigatoria=False)
    if situ:
        s = x[situ].astype(str).str.strip().str.lower()
        # Receita Federal: situação 2 = ativa. Também aceita rótulo textual.
        ativos = x[s.isin({"2", "ativa", "ativo"})].copy()
    else:
        ativos = x.copy()
    keys = ["id_municipio"] + ([snap] if snap else [])
    out = ativos.groupby(keys).size().rename("cnpjs_ativos").reset_index()
    if snap and snap != "snapshot":
        out = out.rename(columns={snap: "snapshot"})
    return out


def main() -> None:
    root = Path.cwd().resolve()
    proc = root / "dados" / "processado"
    aux = root / "dados" / "auxiliares"
    saida = root / "dados" / "analise_tic_tim"
    tab = saida / "tabelas"
    ctrl = saida / "controle"
    tab.mkdir(parents=True, exist_ok=True)
    ctrl.mkdir(parents=True, exist_ok=True)

    rais_v = normalizar_ano(normalizar_municipio(ler_parquets(proc / "rais" / "vinculos")))
    rais_e = normalizar_municipio(ler_parquets(proc / "rais" / "estabelecimentos"))
    caged = ler_parquets(proc / "caged")
    cnpj = ler_parquets(proc / "cnpj")
    if rais_v.empty:
        raise RuntimeError("RAIS Vínculos não localizada. Execute `sou-rais download rais` e `sou-rais validate`.")

    produtos: list[Path] = []

    # 1. Escala e trajetória
    estoque = estoque_rais(rais_v)
    produtos.append(salvar(estoque, tab / "01_estoque_municipio_ano.csv"))
    reg = estoque.groupby("ano", as_index=False)["estoque"].sum().sort_values("ano")
    reg["variacao_pct"] = reg["estoque"].pct_change() * 100
    produtos.append(salvar(reg, tab / "02_estoque_regional_ano.csv"))
    produtos.append(salvar(crescimento_municipal(estoque), tab / "03_crescimento_municipal.csv"))
    produtos.append(salvar(mudanca_participacao_regional(estoque), tab / "04_mudanca_participacao_regional.csv"))

    # 2. Estrutura setorial
    setorial = estrutura_setorial(rais_v)
    ql_s = quociente_locacional(setorial)
    produtos.append(salvar(ql_s, tab / "05_ql_setorial.csv"))
    produtos.append(salvar(especializacao_principal(ql_s, limiar=1.25), tab / "06_especializacao_principal.csv"))
    produtos.append(salvar(hhi(setorial, "setor"), tab / "07_hhi_setorial.csv"))
    produtos.append(salvar(shift_share(setorial, 2015, 2025), tab / "08_shift_share_2015_2025.csv"))

    # 3. Estrutura ocupacional
    ocup = estrutura_ocupacional(rais_v)
    ql_o = quociente_locacional(ocup.rename(columns={"cbo_familia": "setor"})).rename(columns={"setor": "cbo_familia"})
    produtos.append(salvar(ql_o, tab / "09_ql_ocupacional.csv"))
    produtos.append(salvar(hhi(ocup, "cbo_familia"), tab / "10_hhi_ocupacional.csv"))

    # 4. Remuneração real, massa salarial e perfis
    real, remun = remuneracao_real(rais_v, aux / "ipca_dezembro_2015_2025.csv")
    produtos.append(salvar(remun, tab / "11_remuneracao_municipal.csv"))

    # 5. Novo CAGED anual
    if not caged.empty:
        fluxos = consolidar_caged(caged)
        produtos.append(salvar(fluxos, tab / "12_novo_caged_fluxos.csv"))
    else:
        print("AVISO: Novo CAGED não localizado; tabela 12 não gerada.")

    # 6. Empregadores positivos/concentração
    if not rais_e.empty:
        conc = concentracao_empregadores_rais(rais_e)
        produtos.append(salvar(conc, tab / "13_concentracao_empregadores.csv"))
    else:
        print("AVISO: RAIS Estabelecimentos não localizada; tabela 13 não gerada.")

    # 7. CNPJ fotografia cadastral
    if not cnpj.empty:
        foto = fotografia_cnpj(cnpj)
        produtos.append(salvar(foto, tab / "14_cnpj_fotografia_cadastral.csv"))
    else:
        print("AVISO: CNPJ não localizado; tabela 14 não gerada.")

    # 8. Escolaridade e referência empírica CBO
    escolaridade = resolver(rais_v, ["escolaridade", "grau_instrucao"], obrigatoria=False)
    if escolaridade:
        esc = real[["id_municipio", "ano", escolaridade]].copy()
        esc["escolaridade"] = pd.to_numeric(esc[escolaridade], errors="coerce")
        produtos.append(salvar(esc.groupby(["id_municipio", "ano", "escolaridade"]).size().rename("vinculos").reset_index(), tab / "15_escolaridade.csv"))
        cbo = resolver(real, ["cbo_2002", "cbo_2002_familia", "cbo"], obrigatoria=False)
        if cbo:
            eb = real[["ano", cbo, escolaridade]].copy()
            eb["cbo_familia"] = eb[cbo].map(familia_cbo4)
            eb["escolaridade"] = pd.to_numeric(eb[escolaridade], errors="coerce")
            eb = eb[eb["cbo_familia"].str.len() == 4]
            produtos.append(salvar(referencia_escolaridade_cbo(eb[["ano", "cbo_familia", "escolaridade"]]), tab / "15b_referencia_escolaridade_cbo.csv"))

    # 9. Perfil etário
    idade = resolver(real, ["idade"], obrigatoria=False)
    if idade:
        produtos.append(salvar(perfil_etario(real, idade=idade), tab / "16_perfil_etario.csv"))

    # 10. Sexo e gap remuneratório
    sexo = resolver(real, ["sexo"], obrigatoria=False)
    if sexo:
        psexo = perfil_sexo(real)
        produtos.append(salvar(psexo, tab / "17_perfil_sexo.csv"))
        rg = real.copy()
        rg["sexo_norm"] = rg[sexo].map(_sexo_norm)
        produtos.append(salvar(gap_mediano_sexo(rg, "remuneracao_real", sexo="sexo_norm"), tab / "17b_gap_remuneracao_sexo.csv"))

    # 11. Massa salarial separada para facilitar gate editorial
    massa = remun[["id_municipio", "ano", "massa_salarial", "massa_salarial_milhoes"]].copy()
    produtos.append(salvar(massa, tab / "18_massa_salarial.csv"))

    # 12. Raça/cor e gap publicado com médias
    raca = resolver(real, ["raca_cor", "raca"], obrigatoria=False)
    if raca:
        rr = real.rename(columns={raca: "raca_cor"}) if raca != "raca_cor" else real
        produtos.append(salvar(gap_medio_raca(rr, "remuneracao_real", raca="raca_cor"), tab / "19_gap_remuneracao_raca.csv"))

    # Auditoria básica de universos e marcos
    universo = pd.DataFrame(
        [
            {
                "fonte": "RAIS Vínculos",
                "linhas": len(rais_v),
                "municipios": rais_v["id_municipio"].nunique(),
                "periodo_min": rais_v["ano"].min(),
                "periodo_max": rais_v["ano"].max(),
            },
            {
                "fonte": "RAIS Estabelecimentos",
                "linhas": len(rais_e),
                "municipios": rais_e["id_municipio"].nunique() if not rais_e.empty else 0,
                "periodo_min": "",
                "periodo_max": "",
            },
            {
                "fonte": "Novo CAGED",
                "linhas": len(caged),
                "municipios": normalizar_municipio(caged)["id_municipio"].nunique() if not caged.empty else 0,
                "periodo_min": "",
                "periodo_max": "",
            },
            {
                "fonte": "CNPJ",
                "linhas": len(cnpj),
                "municipios": normalizar_municipio(cnpj)["id_municipio"].nunique() if not cnpj.empty else 0,
                "periodo_min": "",
                "periodo_max": "",
            },
        ]
    )
    produtos.append(salvar(universo, ctrl / "auditoria_universos.csv"))

    manifest = pd.DataFrame(
        [
            {"arquivo": str(p.relative_to(root)), "bytes": p.stat().st_size, "sha256": sha256(p)}
            for p in produtos
        ]
    )
    manifest.to_csv(ctrl / "manifesto_produtos.csv", index=False)
    (ctrl / "metadados_execucao.json").write_text(
        json.dumps(
            {
                "root": str(root),
                "linhas_rais_vinculos": int(len(rais_v)),
                "linhas_rais_estabelecimentos": int(len(rais_e)),
                "linhas_caged": int(len(caged)),
                "linhas_cnpj": int(len(cnpj)),
                "produtos": int(len(produtos)),
                "marcos": MARCOS,
                "remuneracao": "valor_remuneracao_dezembro quando disponível; deflacionada pelo IPCA para dezembro de 2025",
                "nota": "RAIS Vínculos, RAIS Estabelecimentos, Novo CAGED e CNPJ permanecem universos distintos.",
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"Concluído: {len(produtos)} produtos tabulares/controle em {saida}")


if __name__ == "__main__":
    main()
