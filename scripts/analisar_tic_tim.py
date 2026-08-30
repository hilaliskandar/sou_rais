from __future__ import annotations

from pathlib import Path

import pandas as pd

from tic_tim_analise import (
    AnalisePaths,
    caged_fluxos,
    cnpj_fotografia,
    concentracao_top_n,
    crescimento_municipal,
    estrutura_ocupacional,
    estrutura_setorial_ql,
    estoque_rais,
    estoque_regional,
    faixa_etaria,
    hhi_setorial,
    ler_parquets,
    manifesto_produtos,
    numero_efetivo_setores,
    remuneracao_municipal,
    resumo_categoria,
    salvar_json,
)


def salvar(df: pd.DataFrame, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)
    return path


def main() -> None:
    root = Path.cwd().resolve()
    paths = AnalisePaths(root)
    paths.criar()

    rais_v = ler_parquets(paths.processado / "rais" / "vinculos")
    caged = ler_parquets(paths.processado / "caged")
    cnpj = ler_parquets(paths.processado / "cnpj")

    if rais_v.empty:
        raise RuntimeError("Nenhum parquet RAIS de vínculos encontrado. Execute antes `sou-rais download rais` e `sou-rais validate`.")

    produtos: list[Path] = []

    estoque = estoque_rais(rais_v)
    produtos.append(salvar(estoque, paths.tabelas / "01_estoque_municipio_ano.csv"))
    produtos.append(salvar(estoque_regional(estoque), paths.tabelas / "02_estoque_regional_ano.csv"))
    produtos.append(salvar(crescimento_municipal(estoque), paths.tabelas / "03_crescimento_municipal.csv"))

    estrutura = estrutura_setorial_ql(rais_v)
    produtos.append(salvar(estrutura, paths.tabelas / "04_estrutura_setorial_ql.csv"))
    hhi = hhi_setorial(estrutura)
    produtos.append(salvar(hhi, paths.tabelas / "05_hhi_setorial.csv"))
    produtos.append(salvar(numero_efetivo_setores(hhi), paths.tabelas / "05b_numero_efetivo_setores.csv"))

    produtos.append(salvar(estrutura_ocupacional(rais_v), paths.tabelas / "06_estrutura_ocupacional.csv"))

    for key, nome in [
        ("escolaridade", "07_escolaridade.csv"),
        ("sexo", "08_sexo.csv"),
        ("raca_cor", "09_raca_cor.csv"),
    ]:
        try:
            produtos.append(salvar(resumo_categoria(rais_v, key), paths.tabelas / nome))
        except KeyError as e:
            print(f"AVISO: {e}")

    try:
        produtos.append(salvar(faixa_etaria(rais_v), paths.tabelas / "10_faixa_etaria.csv"))
    except KeyError as e:
        print(f"AVISO: {e}")

    try:
        produtos.append(salvar(remuneracao_municipal(rais_v), paths.tabelas / "11_remuneracao_municipal.csv"))
    except KeyError as e:
        print(f"AVISO: {e}")

    if not caged.empty:
        produtos.append(salvar(caged_fluxos(caged), paths.tabelas / "12_novo_caged_fluxos.csv"))
    else:
        print("AVISO: Novo CAGED não localizado; produto 12 não foi gerado.")

    try:
        produtos.append(salvar(concentracao_top_n(rais_v, 10), paths.tabelas / "13_concentracao_top10_empregadores.csv"))
    except KeyError as e:
        print(f"AVISO: {e}")

    if not cnpj.empty:
        produtos.append(salvar(cnpj_fotografia(cnpj), paths.tabelas / "14_cnpj_fotografia_cadastral.csv"))
    else:
        print("AVISO: CNPJ não localizado; produto 14 não foi gerado.")

    manifest = manifesto_produtos(root, produtos)
    manifest_path = paths.controle / "manifesto_produtos.csv"
    manifest.to_csv(manifest_path, index=False)

    salvar_json(
        paths.controle / "metadados_execucao.json",
        {
            "root": str(root),
            "linhas_rais_vinculos": int(len(rais_v)),
            "linhas_caged": int(len(caged)),
            "linhas_cnpj": int(len(cnpj)),
            "produtos_tabelares": int(len(produtos)),
            "nota": "RAIS, Novo CAGED e CNPJ são fontes distintas e não são concatenadas em uma série única.",
        },
    )

    print(f"Análise concluída. Produtos em: {paths.saida}")
    print(manifest.to_string(index=False))


if __name__ == "__main__":
    main()
