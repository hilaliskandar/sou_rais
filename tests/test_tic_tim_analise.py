from __future__ import annotations

import pandas as pd
import pytest

from tic_tim_analise import (
    caged_fluxos,
    concentracao_top_n,
    crescimento_municipal,
    estrutura_setorial_ql,
    estoque_rais,
    estoque_regional,
    hhi_setorial,
    numero_efetivo_setores,
)


def amostra_rais() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "id_municipio": ["3500001", "3500001", "3500002", "3500001", "3500002", "3500002", "3500002"],
            "ano": [2020, 2020, 2020, 2021, 2021, 2021, 2021],
            "cnae_2": ["10", "10", "20", "10", "10", "20", "20"],
            "id_estabelecimento": ["A", "A", "B", "A", "C", "B", "B"],
        }
    )


def test_estoque_e_crescimento() -> None:
    estoque = estoque_rais(amostra_rais())
    reg = estoque_regional(estoque)
    cresc = crescimento_municipal(estoque, 2020, 2021)

    assert reg.set_index("ano").loc[2020, "estoque"] == 3
    assert reg.set_index("ano").loc[2021, "estoque"] == 4

    m1 = cresc.set_index("id_municipio").loc["3500001"]
    m2 = cresc.set_index("id_municipio").loc["3500002"]
    assert m1["acrescimo"] == -1
    assert m2["acrescimo"] == 2
    assert pytest.approx(m1["variacao_pct"]) == -50.0
    assert pytest.approx(m2["variacao_pct"]) == 100.0


def test_ql_e_hhi() -> None:
    estrutura = estrutura_setorial_ql(amostra_rais())
    hhi = hhi_setorial(estrutura)
    ne = numero_efetivo_setores(hhi)

    ql_m1_2020 = estrutura.query("id_municipio == '3500001' and ano == 2020 and setor == '10'")["ql"].iloc[0]
    assert ql_m1_2020 > 1

    hhi_m2_2021 = hhi.query("id_municipio == '3500002' and ano == 2021")["hhi"].iloc[0]
    assert pytest.approx(hhi_m2_2021) == (1 / 3) ** 2 + (2 / 3) ** 2
    ne_m2_2021 = ne.query("id_municipio == '3500002' and ano == 2021")["numero_efetivo_setores"].iloc[0]
    assert pytest.approx(ne_m2_2021) == 1 / hhi_m2_2021


def test_concentracao_top_n() -> None:
    out = concentracao_top_n(amostra_rais(), n=1)
    m2 = out.query("id_municipio == '3500002' and ano == 2021").iloc[0]
    assert m2["vinculos_total"] == 3
    assert m2["vinculos_top1"] == 2
    assert pytest.approx(m2["share_top1"]) == 2 / 3


def test_caged_fluxos_por_saldo() -> None:
    df = pd.DataFrame(
        {
            "id_municipio": ["3500001", "3500001", "3500002"],
            "ano_mes": ["2021-01", "2021-01", "2021-01"],
            "saldo_movimentacao": [1, -1, 3],
        }
    )
    out = caged_fluxos(df)
    assert out.query("id_municipio == '3500001'")["saldo"].iloc[0] == 0
    assert out.query("id_municipio == '3500002'")["saldo"].iloc[0] == 3
