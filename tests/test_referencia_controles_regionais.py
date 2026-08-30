from pathlib import Path

import pandas as pd
import pytest


REF = Path(__file__).resolve().parents[1] / "referencias" / "tic_tim_controles_regionais_v16_26.csv"


def carregar():
    return pd.read_csv(REF, dtype={"periodo": str})


def valor(df, indicador, periodo):
    x = df[(df["indicador"] == indicador) & (df["periodo"] == str(periodo))]
    assert len(x) == 1
    return float(x.iloc[0]["valor"])


def test_controles_regionais_2025():
    df = carregar()
    assert valor(df, "estoque_formal", 2025) == 1_632_887
    assert valor(df, "admissoes_novo_caged", 2025) == 866_560
    assert valor(df, "desligamentos_novo_caged", 2025) == 845_332
    assert valor(df, "saldo_novo_caged", 2025) == 21_228
    assert valor(df, "empregadores_positivos_rais", 2025) == 89_424


def test_saldo_reconcilia_com_fluxos():
    df = carregar()
    adm = valor(df, "admissoes_novo_caged", 2025)
    des = valor(df, "desligamentos_novo_caged", 2025)
    saldo = valor(df, "saldo_novo_caged", 2025)
    assert adm - des == saldo


def test_cnpj_snapshot_final():
    df = carregar()
    ativos = valor(df, "cnpjs_ativos", "2026-01-11")
    mei = valor(df, "cnpjs_mei_ativos", "2026-01-11")
    simples = valor(df, "cnpjs_simples_ativos", "2026-01-11")
    assert ativos == 772_968
    assert 100 * mei / ativos == pytest.approx(valor(df, "cnpjs_mei_ativos_pct", "2026-01-11"), abs=0.0001)
    assert 100 * simples / ativos == pytest.approx(valor(df, "cnpjs_simples_ativos_pct", "2026-01-11"), abs=0.0001)


def test_participacao_maiores_mercados_cai_na_decada():
    df = carregar()
    assert valor(df, "top3_participacao", 2025) < valor(df, "top3_participacao", 2015)
    assert valor(df, "top5_participacao", 2025) < valor(df, "top5_participacao", 2015)
