from __future__ import annotations

"""Baixa os auxiliares externos mínimos da análise TIC-TIM.

Fontes:
- IPCA mensal: `basedosdados.br_ibge_ipca.mes_brasil` (IBGE/Base dos Dados),
  retendo o índice de dezembro de cada ano para deflação a dezembro de 2025;
- malha municipal: IBGE via pacote `geobr`, SIRGAS 2000 (EPSG:4674).

Os dados são gravados em `dados/auxiliares/` e recebem SHA-256 no manifesto.
"""

from pathlib import Path
import argparse
import json

import pandas as pd

from sou_rais import carregar_config, cliente_bigquery, sha256


IPCA_TABLE = "basedosdados.br_ibge_ipca.mes_brasil"


def baixar_ipca(root: Path, ano_inicial: int = 2015, ano_final: int = 2025) -> Path:
    bq = cliente_bigquery()
    sql = f"""
    SELECT ano, mes, indice
    FROM `{IPCA_TABLE}`
    WHERE ano BETWEEN {int(ano_inicial)} AND {int(ano_final)}
      AND mes = 12
      AND indice IS NOT NULL
    ORDER BY ano
    """
    df = bq.query(sql).to_dataframe(create_bqstorage_client=False)
    if df.empty:
        raise RuntimeError("Consulta do IPCA não retornou observações de dezembro.")
    df["ano"] = pd.to_numeric(df["ano"], errors="raise").astype(int)
    df["mes"] = pd.to_numeric(df["mes"], errors="raise").astype(int)
    df["indice"] = pd.to_numeric(df["indice"], errors="raise")
    faltantes = sorted(set(range(ano_inicial, ano_final + 1)) - set(df["ano"]))
    if faltantes:
        raise RuntimeError(f"IPCA de dezembro ausente para anos: {faltantes}")
    out = root / "dados" / "auxiliares" / "ipca_dezembro_2015_2025.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out, index=False)
    return out


def baixar_malha(root: Path, municipios: list[str], ano: int = 2022, simplificada: bool = False) -> Path:
    try:
        from geobr import read_municipality
    except ImportError as exc:
        raise RuntimeError('Instale o extra geoespacial: pip install -e ".[geo]"') from exc

    # 35 = Estado de São Paulo. A seleção dos 30 municípios ocorre depois do download
    # para reduzir chamadas externas e preservar uma única fonte espacial.
    geo = read_municipality(code_muni=35, year=ano, simplified=simplificada)
    candidatas = ["code_muni", "id_municipio", "CD_MUN"]
    cod = next((c for c in candidatas if c in geo.columns), None)
    if cod is None:
        raise KeyError(f"Código municipal não encontrado na malha geobr; colunas: {list(geo.columns)}")
    geo["id_municipio"] = geo[cod].astype(str).str.replace(r"\.0$", "", regex=True).str.zfill(7)
    recorte = geo[geo["id_municipio"].isin(set(municipios))].copy()
    ausentes = sorted(set(municipios) - set(recorte["id_municipio"]))
    if ausentes:
        raise RuntimeError(f"Municípios ausentes na malha {ano}: {ausentes}")
    out = root / "dados" / "auxiliares" / f"municipios_tic_tim_{ano}.geojson"
    out.parent.mkdir(parents=True, exist_ok=True)
    recorte.to_file(out, driver="GeoJSON")
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ano-malha", type=int, default=2022)
    ap.add_argument("--somente-ipca", action="store_true")
    ap.add_argument("--somente-malha", action="store_true")
    args = ap.parse_args()

    if args.somente_ipca and args.somente_malha:
        raise SystemExit("Escolha no máximo uma das opções --somente-ipca/--somente-malha")

    root = Path.cwd().resolve()
    cfg = carregar_config(root)
    produzidos: list[Path] = []
    if not args.somente_malha:
        produzidos.append(baixar_ipca(root))
    if not args.somente_ipca:
        produzidos.append(baixar_malha(root, cfg.municipios, ano=args.ano_malha))

    manifesto = [
        {"arquivo": str(p.relative_to(root)), "bytes": p.stat().st_size, "sha256": sha256(p)}
        for p in produzidos
    ]
    meta = root / "dados" / "auxiliares" / "manifesto_auxiliares_tic_tim.json"
    meta.write_text(json.dumps(manifesto, ensure_ascii=False, indent=2), encoding="utf-8")
    for item in manifesto:
        print(item)


if __name__ == "__main__":
    main()
