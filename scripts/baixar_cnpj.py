from pathlib import Path

from tqdm.auto import tqdm

from sou_rais import (
    carregar_config, cliente_bigquery, estimar_bytes, filtrar_strings,
    formatar_gb, gravar_parquet_atomico, lotes, manifestar, sha256,
    validar_municipios_retornados,
)


def sql_snapshot(snapshot: str, ids: list[str]) -> str:
    ids_sql = ",".join(f"'{x}'" for x in ids)
    return f"""
WITH e AS (
  SELECT *
  FROM `basedosdados.br_me_cnpj.estabelecimentos`
  WHERE data = DATE('{snapshot}')
    AND id_municipio IN ({ids_sql})
),
b AS (
  SELECT DISTINCT cnpj_basico FROM e
),
p AS (
  SELECT p.*
  FROM `basedosdados.br_me_cnpj.empresas` p
  INNER JOIN b USING (cnpj_basico)
  WHERE p.data = DATE('{snapshot}')
),
sm AS (
  SELECT sm.*
  FROM `basedosdados.br_me_cnpj.simples` sm
  INNER JOIN b USING (cnpj_basico)
)
SELECT
  e.*,
  p.razao_social,
  p.natureza_juridica,
  p.qualificacao_responsavel,
  p.ente_federativo,
  p.capital_social,
  p.porte,
  sm.opcao_simples,
  sm.data_opcao_simples,
  sm.data_exclusao_simples,
  sm.opcao_mei,
  sm.data_opcao_mei,
  sm.data_exclusao_mei
FROM e
LEFT JOIN p USING (cnpj_basico)
LEFT JOIN sm USING (cnpj_basico)
"""


def main():
    cfg = carregar_config(Path.cwd())
    bq = cliente_bigquery()
    grupos = lotes(cfg.municipios, cfg.lote_tamanho)

    snap = bq.query("""
        SELECT CAST(data AS STRING) snapshot
        FROM `basedosdados.br_me_cnpj.estabelecimentos`
        WHERE data IS NOT NULL
        GROUP BY data
        ORDER BY data
    """).to_dataframe()
    snapshots = filtrar_strings(
        snap["snapshot"].astype(str).str[:10].tolist(),
        cfg.snapshot_inicial,
        cfg.snapshot_final,
    )
    if not snapshots:
        raise RuntimeError("Nenhum snapshot CNPJ selecionado.")

    for snapshot in tqdm(snapshots, desc="CNPJ snapshots"):
        outs = [
            cfg.processado_dir / "cnpj" / f"cnpj_lote{i:02d}_{snapshot}.parquet"
            for i in range(1, len(grupos) + 1)
        ]
        if all(p.exists() for p in outs) and not cfg.sobrescrever:
            continue

        sql = sql_snapshot(snapshot, cfg.municipios)
        if cfg.estimar_custo:
            print(f"{snapshot} | estimativa: {formatar_gb(estimar_bytes(bq, sql))}")
        df = bq.query(sql).to_dataframe(create_bqstorage_client=False)
        if df.empty:
            raise RuntimeError(f"Snapshot {snapshot} retornou zero linhas.")
        df["id_municipio"] = df["id_municipio"].astype(str)
        validar_municipios_retornados(df, cfg.municipios)

        for i, ids in enumerate(grupos, 1):
            out = outs[i - 1]
            if out.exists() and not cfg.sobrescrever:
                continue
            dg = df[df["id_municipio"].isin(ids)].copy()
            validar_municipios_retornados(dg, ids)
            gravar_parquet_atomico(dg, out)
            manifestar(cfg, base="CNPJ", tipo="snapshot", lote=i, periodo=snapshot,
                       arquivo=out.relative_to(cfg.root), linhas=len(dg), sha256=sha256(out))

    print("CNPJ concluído em", cfg.processado_dir / "cnpj")


if __name__ == "__main__":
    main()
