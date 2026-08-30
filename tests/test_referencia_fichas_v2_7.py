from pathlib import Path

import pandas as pd
import pytest


REF = Path(__file__).resolve().parents[1] / "referencias" / "tic_tim_fichas_v2_7_quadro1.csv"


def carregar():
    return pd.read_csv(REF, dtype={"id_municipio": str})


def test_referencia_tem_30_municipios_unicos():
    df = carregar()
    assert len(df) == 30
    assert df["id_municipio"].nunique() == 30
    assert df["municipio"].nunique() == 30
    assert df["id_municipio"].str.fullmatch(r"\d{7}").all()


def test_ancoras_publicadas():
    df = carregar().set_index("municipio")
    assert df.loc["Campinas", "estoque_2025"] == 485323
    assert df.loc["Jundiaí", "estoque_2025"] == 208840
    assert df.loc["Paulínia", "remuneracao_mediana_real_2025"] == pytest.approx(4213.93)
    assert df.loc["Morungaba", "crescimento_2015_2025_pct"] == pytest.approx(-47.3)
    assert df.loc["Santa Bárbara d'Oeste", "saldo_caged_2025"] == 0


def test_ausencia_publicada_preservada():
    df = carregar().set_index("municipio")
    assert pd.isna(df.loc["Caieiras", "top10_empregadores_pct_2025"])


def test_sem_ausencias_nos_demais_indicadores_chave():
    df = carregar()
    cols = [
        "estoque_2025",
        "crescimento_2015_2025_pct",
        "remuneracao_mediana_real_2025",
        "massa_salarial_milhoes_2025",
        "saldo_caged_2025",
        "idade_mediana_2025",
        "mulheres_pct_2025",
    ]
    assert not df[cols].isna().any().any()
