import argparse
from pathlib import Path

from tqdm.auto import tqdm

from sou_rais import (
    carregar_config, cliente_bigquery, estimar_bytes, filtrar_anos,
    formatar_gb, gravar_parquet_atomico, lotes, manifestar, plano_resumo,
    salvar_plano, sha256, validar_municipios_retornados,
)

TABLES = {
    "vinculos": "basedosdados.br_me_rais.microdados_vinculos",
    "estabelecimentos": "basedosdados.br_me_rais.microdados_estabelecimentos",
}


def sql_particao(tabela: str, ids: list[str], ano: int) -> str:
    ids_sql = ",".join(f"'{x}'" for x in ids)
    return f"SELECT * FROM `{tabela}` WHERE id_municipio IN ({ids_sql}) AND ano={ano}"


def main(dry_run: bool = False):
    cfg = carregar_config(Path.cwd())
    bq = cliente_bigquery()
    grupos = lotes(cfg.municipios, cfg.lote_tamanho)
    planos = []

    for tipo, tabela in TABLES.items():
        anos = [int(r.ano) for r in bq.query(
            f"SELECT DISTINCT ano FROM `{tabela}` WHERE ano IS NOT NULL ORDER BY ano"
        ).result()]
        anos = filtrar_anos(anos, cfg)
        if not anos:
            raise RuntimeError(f"Nenhum ano selecionado para {tipo}.")

        if dry_run:
            total_bytes = 0
            indisponivel = False
            for ids in grupos:
                for ano in anos:
                    n = estimar_bytes(bq, sql_particao(tabela, ids, ano))
                    if n is None:
                        indisponivel = True
                    else:
                        total_bytes += n
            plano = plano_resumo(
                f"RAIS {tipo}", len(anos), len(grupos),
                len(anos) * len(grupos), len(anos) * len(grupos),
                None if indisponivel else total_bytes,
            )
            planos.append(plano)
            print(plano)
            continue

        for lote_n, ids in enumerate(grupos, 1):
            for ano in tqdm(anos, desc=f"RAIS {tipo} lote {lote_n:02d}"):
                out = cfg.processado_dir / "rais" / tipo / f"rais_{tipo}_lote{lote_n:02d}_{ano}.parquet"
                if out.exists() and not cfg.sobrescrever:
                    continue
                sql = sql_particao(tabela, ids, ano)
                if cfg.estimar_custo:
                    print(f"{tipo} {ano} lote {lote_n:02d} | estimativa: {formatar_gb(estimar_bytes(bq, sql))}")
                df = bq.query(sql).to_dataframe(create_bqstorage_client=False)
                faltantes = validar_municipios_retornados(
                    df, ids, cfg.validacao_municipios,
                    contexto=f"RAIS {tipo} {ano} lote {lote_n:02d}",
                )
                gravar_parquet_atomico(df, out)
                manifestar(
                    cfg, base="RAIS", tipo=tipo, lote=lote_n, periodo=ano,
                    arquivo=out.relative_to(cfg.root), linhas=len(df), sha256=sha256(out),
                    municipios_faltantes="|".join(faltantes),
                )

    if dry_run:
        path = salvar_plano(cfg, "rais", planos)
        print("DRY-RUN: nenhum microdado foi baixado.")
        print("Plano salvo em", path)
    else:
        print("RAIS concluída em", cfg.processado_dir / "rais")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Baixa RAIS para municípios selecionados.")
    parser.add_argument("--dry-run", action="store_true", help="Descobre cobertura e estima processamento sem baixar microdados.")
    args = parser.parse_args()
    main(dry_run=args.dry_run)
