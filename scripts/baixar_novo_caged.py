import argparse
from pathlib import Path

from tqdm.auto import tqdm

from sou_rais import (
    carregar_config, cliente_bigquery, estimar_bytes, filtrar_strings,
    formatar_gb, gravar_parquet_atomico, lotes, manifestar, plano_resumo,
    salvar_plano, sha256, validar_municipios_retornados,
)

TABLE = "basedosdados.br_me_caged.microdados_movimentacao"


def sql_particao(ids: list[str], ano: int, mes: int) -> str:
    ids_sql = ",".join(f"'{x}'" for x in ids)
    return f"SELECT * FROM `{TABLE}` WHERE id_municipio IN ({ids_sql}) AND ano={ano} AND mes={mes}"


def main(dry_run: bool = False):
    cfg = carregar_config(Path.cwd())
    bq = cliente_bigquery()
    grupos = lotes(cfg.municipios, cfg.lote_tamanho)

    periodos = [f"{int(r.ano):04d}-{int(r.mes):02d}" for r in bq.query(
        f"SELECT DISTINCT ano, mes FROM `{TABLE}` WHERE ano IS NOT NULL AND mes IS NOT NULL ORDER BY ano, mes"
    ).result()]
    periodos = filtrar_strings(periodos, cfg.competencia_inicial, cfg.competencia_final)
    if not periodos:
        raise RuntimeError("Nenhuma competência do Novo CAGED selecionada.")

    if dry_run:
        total_bytes = 0
        indisponivel = False
        for ids in grupos:
            for comp in periodos:
                ano, mes = map(int, comp.split("-"))
                n = estimar_bytes(bq, sql_particao(ids, ano, mes))
                if n is None:
                    indisponivel = True
                else:
                    total_bytes += n
        plano = plano_resumo(
            "Novo CAGED", len(periodos), len(grupos),
            len(periodos) * len(grupos), len(periodos) * len(grupos),
            None if indisponivel else total_bytes,
        )
        path = salvar_plano(cfg, "novo_caged", [plano])
        print(plano)
        print("DRY-RUN: nenhum microdado foi baixado.")
        print("Plano salvo em", path)
        return

    for lote_n, ids in enumerate(grupos, 1):
        for comp in tqdm(periodos, desc=f"Novo CAGED lote {lote_n:02d}"):
            ano, mes = map(int, comp.split("-"))
            out = cfg.processado_dir / "caged" / f"novo_caged_lote{lote_n:02d}_{ano}_{mes:02d}.parquet"
            if out.exists() and not cfg.sobrescrever:
                continue
            sql = sql_particao(ids, ano, mes)
            if cfg.estimar_custo:
                print(f"{comp} lote {lote_n:02d} | estimativa: {formatar_gb(estimar_bytes(bq, sql))}")
            df = bq.query(sql).to_dataframe(create_bqstorage_client=False)
            faltantes = validar_municipios_retornados(
                df, ids, cfg.validacao_municipios,
                contexto=f"Novo CAGED {comp} lote {lote_n:02d}",
            )
            df["regime_caged"] = "novo_caged"
            gravar_parquet_atomico(df, out)
            manifestar(
                cfg, base="Novo CAGED", tipo="movimentacao", lote=lote_n, periodo=comp,
                arquivo=out.relative_to(cfg.root), linhas=len(df), sha256=sha256(out),
                municipios_faltantes="|".join(faltantes),
            )

    print("Novo CAGED concluído em", cfg.processado_dir / "caged")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Baixa Novo CAGED para municípios selecionados.")
    parser.add_argument("--dry-run", action="store_true", help="Descobre cobertura e estima processamento sem baixar microdados.")
    args = parser.parse_args()
    main(dry_run=args.dry_run)
