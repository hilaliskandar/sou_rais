from __future__ import annotations

import re
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq

from sou_rais import carregar_config, lotes, sha256

RE_RAIS = re.compile(r"^rais_(vinculos|estabelecimentos)_lote(\d{2})_(\d{4})\.parquet$")
RE_CAGED = re.compile(r"^novo_caged_lote(\d{2})_(\d{4})_(\d{2})\.parquet$")
RE_CNPJ = re.compile(r"^cnpj_lote(\d{2})_(\d{4}-\d{2}-\d{2})\.parquet$")


def metadata_parquet(path: Path) -> tuple[int, int, int]:
    meta = pq.ParquetFile(path).metadata
    return meta.num_rows, meta.num_row_groups, meta.num_columns


def main():
    cfg = carregar_config(Path.cwd())
    n_lotes = len(lotes(cfg.municipios, cfg.lote_tamanho))
    rows = []
    fora = []

    bases = [
        (cfg.processado_dir / "rais" / "vinculos", "RAIS", "vinculos", RE_RAIS),
        (cfg.processado_dir / "rais" / "estabelecimentos", "RAIS", "estabelecimentos", RE_RAIS),
        (cfg.processado_dir / "caged", "Novo CAGED", "movimentacao", RE_CAGED),
        (cfg.processado_dir / "cnpj", "CNPJ", "snapshot", RE_CNPJ),
    ]

    for pasta, base, tipo, regex in bases:
        if not pasta.exists():
            continue
        for p in sorted(pasta.glob("*.parquet")):
            m = regex.match(p.name)
            if not m:
                fora.append(str(p.relative_to(cfg.root)))
                continue
            linhas, row_groups, colunas = metadata_parquet(p)
            if linhas <= 0:
                raise RuntimeError(f"Parquet vazio: {p}")

            rec = {
                "base": base,
                "tipo": tipo,
                "arquivo": str(p.relative_to(cfg.root)),
                "nome_arquivo": p.name,
                "tamanho_bytes": p.stat().st_size,
                "linhas": linhas,
                "row_groups": row_groups,
                "colunas": colunas,
                "sha256": sha256(p),
                "lote": int(m.group(2 if base == "RAIS" else 1)),
                "ano": None,
                "mes": None,
                "snapshot": None,
            }
            if base == "RAIS":
                rec["ano"] = int(m.group(3))
            elif base == "Novo CAGED":
                rec["ano"] = int(m.group(2)); rec["mes"] = int(m.group(3))
            else:
                rec["snapshot"] = m.group(2)
            rows.append(rec)

    idx = pd.DataFrame(rows)
    fora_df = pd.DataFrame({"arquivo_fora_padrao": fora})
    idx_path = cfg.controle_dir / "indice_particoes.csv"
    fora_path = cfg.controle_dir / "indice_particoes_fora_padrao.csv"
    idx.to_csv(idx_path, index=False)
    fora_df.to_csv(fora_path, index=False)

    if not idx.empty:
        lotes_invalidos = sorted(set(idx.loc[(idx["lote"] < 1) | (idx["lote"] > n_lotes), "lote"].astype(int)))
        if lotes_invalidos:
            raise RuntimeError(f"Lotes fora do intervalo configurado 1..{n_lotes}: {lotes_invalidos}")

    if fora:
        raise RuntimeError(f"Há {len(fora)} arquivos fora do padrão. Consulte {fora_path}.")

    print(f"Partições indexadas: {len(idx)}")
    print(f"Lotes configurados: {n_lotes}")
    print("ÍNDICE DE PARTIÇÕES: OK")


if __name__ == "__main__":
    main()
