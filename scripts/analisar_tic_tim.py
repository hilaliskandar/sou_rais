from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd

from tic_tim_analysis import (
    concentracao_empregadores,
    especializacao_principal,
    estoque_vinculos,
    hhi,
    mudanca_participacao_regional,
    perfil_etario,
    quociente_locacional,
    shift_share,
    trajetoria,
)


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


def resolver(df: pd.DataFrame, candidatos: list[str], obrigatoria: bool = True) -> str | None:
    for c in candidatos:
        if c in df.columns:
            return c
    if obrigatoria:
        raise KeyError(f"Nenhuma das colunas candidatas foi encontrada: {candidatos}")
    return None


def normalizar_municipio(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df.copy()
    out = df.copy()
    c = resolver(out, ["id_municipio", "municipio", "cod_municipio", "codigo_municipio"])
    if c != "id_municipio":
        out = out.rename(columns={c: "id_municipio"})
    out["id_municipio"] = out["id_municipio"].astype(str).str.replace(r"\.0$", "", regex=True).str.zfill(7)
    return out


def setor2(v: object) -> str:
    s = "" if pd.isna(v) else str(v)
    d = "".join(ch for ch in s if ch.isdigit())
    return d[:2] if len(d) >= 2 else s


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


def main() -> None:
    root = Path.cwd().resolve()
    proc = root / "dados" / "processado"
    saida = root / "dados" / "analise_tic_tim"
    tab = saida / "tabelas"
    ctrl = saida / "controle"
    tab.mkdir(parents=True, exist_ok=True)
    ctrl.mkdir(parents=True, exist_ok=True)

    rais = normalizar_municipio(ler_parquets(proc / "rais" / "vinculos"))
    if rais.empty:
        raise RuntimeError("RAIS Vínculos não localizada. Execute `sou-rais download rais` e `sou-rais validate`.")

    ano_col = resolver(rais, ["ano", "ano_rais"])
    if ano_col != "ano":
        rais = rais.rename(columns={ano_col: "ano"})
    rais["ano"] = pd.to_numeric(rais["ano"], errors="raise").astype(int)

    produtos: list[Path] = []

    estoque = estoque_vinculos(rais)
    produtos.append(salvar(estoque, tab / "01_estoque_municipio_ano.csv"))
    produtos.append(salvar(trajetoria(estoque), tab / "02_trajetoria_2015_2025.csv"))
    produtos.append(salvar(mudanca_participacao_regional(estoque), tab / "03_mudanca_participacao_regional.csv"))

    cnae = resolver(rais, ["cnae_2", "cnae_2_subclasse", "cnae_2_classe", "cnae"])
    base_setorial = rais[["id_municipio", "ano", cnae]].copy()
    base_setorial["setor"] = base_setorial[cnae].map(setor2)
    base_setorial = (
        base_setorial.groupby(["id_municipio", "ano", "setor"])
        .size().rename("vinculos").reset_index()
    )
    ql = quociente_locacional(base_setorial)
    produtos.append(salvar(ql, tab / "04_ql_setorial.csv"))
    produtos.append(salvar(especializacao_principal(ql, limiar=1.25), tab / "05_especializacao_principal.csv"))
    produtos.append(salvar(hhi(base_setorial, "setor"), tab / "06_hhi_setorial.csv"))
    produtos.append(salvar(shift_share(base_setorial, 2015, 2025), tab / "07_shift_share_2015_2025.csv"))

    idade = resolver(rais, ["idade"], obrigatoria=False)
    if idade:
        produtos.append(salvar(perfil_etario(rais, idade=idade), tab / "08_perfil_etario.csv"))

    estab = resolver(rais, ["id_estabelecimento", "cnpj", "cnpj_basico"], obrigatoria=False)
    if estab:
        tmp = rais.rename(columns={estab: "id_estabelecimento"}) if estab != "id_estabelecimento" else rais
        produtos.append(salvar(concentracao_empregadores(tmp), tab / "09_concentracao_empregadores.csv"))

    manifest = pd.DataFrame([
        {"arquivo": str(p.relative_to(root)), "bytes": p.stat().st_size, "sha256": sha256(p)}
        for p in produtos
    ])
    manifest.to_csv(ctrl / "manifesto_produtos.csv", index=False)
    (ctrl / "metadados_execucao.json").write_text(
        json.dumps(
            {
                "root": str(root),
                "linhas_rais": int(len(rais)),
                "produtos": int(len(produtos)),
                "janela_principal": [2015, 2025],
                "nota": "RAIS, Novo CAGED e CNPJ permanecem universos distintos. Este script executa o núcleo RAIS; o notebook 90 orquestra os demais blocos.",
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"Concluído: {len(produtos)} tabelas em {tab}")


if __name__ == "__main__":
    main()
