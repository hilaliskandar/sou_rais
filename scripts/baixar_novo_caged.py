from pathlib import Path

from tqdm.auto import tqdm

from sou_rais import (
    carregar_config, cliente_bigquery, estimar_bytes, filtrar_strings,
    formatar_gb, gravar_parquet_atomico, lotes, manifestar, sha256,
    validar_municipios_retornados,
)

TABLE = "basedosdados.br_me_caged.microdados_movimentacao"


def main():
    cfg = carregar_config(Path.cwd())
    bq = cliente_bigquery()
    grupos = lotes(cfg.municipios, cfg.lote_tamanho)

    periodos = [f"{int(r.ano):04d}-{int(r.mes):02d}" for r in bq.query(
        f"SELECT DISTINCT ano, mes FROM `{TABLE}` WHERE ano IS NOT NULL AND mes IS NOT NULL ORDER BY ano, mes"
    ).result()]
    periodos = filtrar_strings(periodos, cfg.competencia_inicial, cfg.competencia_final)
    if not periodos:
        raise RuntimeError("Nenhuma competência do Novo CAGED selecionada.")

    for lote_n, ids in enumerate(grupos, 1):
        ids_sql = ",".join(f"'{x}'" for x in ids)
        for comp in tqdm(periodos, desc=f"Novo CAGED lote {lote_n:02d}"):
            ano, mes = map(int, comp.split("-"))
            out = cfg.processado_dir / "caged" / f"novo_caged_lote{lote_n:02d}_{ano}_{mes:02d}.parquet"
            if out.exists() and not cfg.sobrescrever:
                continue
            sql = f"SELECT * FROM `{TABLE}` WHERE id_municipio IN ({ids_sql}) AND ano={ano} AND mes={mes}"
            if cfg.estimar_custo:
                print(f"{comp} lote {lote_n:02d} | estimativa: {formatar_gb(estimar_bytes(bq, sql))}")
            df = bq.query(sql).to_dataframe(create_bqstorage_client=False)
            validar_municipios_retornados(df, ids)
            df["regime_caged"] = "novo_caged"
            gravar_parquet_atomico(df, out)
            manifestar(cfg, base="Novo CAGED", tipo="movimentacao", lote=lote_n, periodo=comp,
                       arquivo=out.relative_to(cfg.root), linhas=len(df), sha256=sha256(out))

    print("Novo CAGED concluído em", cfg.processado_dir / "caged")


if __name__ == "__main__":
    main()
