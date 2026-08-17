from pathlib import Path

from tqdm.auto import tqdm

from sou_rais import (
    carregar_config, cliente_bigquery, estimar_bytes, filtrar_anos,
    formatar_gb, gravar_parquet_atomico, lotes, manifestar, sha256,
    validar_municipios_retornados,
)

TABLES = {
    "vinculos": "basedosdados.br_me_rais.microdados_vinculos",
    "estabelecimentos": "basedosdados.br_me_rais.microdados_estabelecimentos",
}


def main():
    cfg = carregar_config(Path.cwd())
    bq = cliente_bigquery()
    grupos = lotes(cfg.municipios, cfg.lote_tamanho)

    for tipo, tabela in TABLES.items():
        anos = [int(r.ano) for r in bq.query(
            f"SELECT DISTINCT ano FROM `{tabela}` WHERE ano IS NOT NULL ORDER BY ano"
        ).result()]
        anos = filtrar_anos(anos, cfg)
        if not anos:
            raise RuntimeError(f"Nenhum ano selecionado para {tipo}.")

        for lote_n, ids in enumerate(grupos, 1):
            ids_sql = ",".join(f"'{x}'" for x in ids)
            for ano in tqdm(anos, desc=f"RAIS {tipo} lote {lote_n:02d}"):
                out = cfg.processado_dir / "rais" / tipo / f"rais_{tipo}_lote{lote_n:02d}_{ano}.parquet"
                if out.exists() and not cfg.sobrescrever:
                    continue
                sql = f"SELECT * FROM `{tabela}` WHERE id_municipio IN ({ids_sql}) AND ano={ano}"
                if cfg.estimar_custo:
                    print(f"{tipo} {ano} lote {lote_n:02d} | estimativa: {formatar_gb(estimar_bytes(bq, sql))}")
                df = bq.query(sql).to_dataframe(create_bqstorage_client=False)
                validar_municipios_retornados(df, ids)
                gravar_parquet_atomico(df, out)
                manifestar(cfg, base="RAIS", tipo=tipo, lote=lote_n, periodo=ano,
                           arquivo=out.relative_to(cfg.root), linhas=len(df), sha256=sha256(out))

    print("RAIS concluída em", cfg.processado_dir / "rais")


if __name__ == "__main__":
    main()
