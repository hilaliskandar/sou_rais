import numpy as np
import pandas as pd

from scripts.calcular_intensidade_fluxos import agregar_regional, calcular_intensidade


def test_intensidade_usa_media_estoques_extremos():
    estoque = pd.DataFrame(
        {
            "id_municipio": ["3500000", "3500000"],
            "ano": [2019, 2020],
            "estoque": [100.0, 120.0],
        }
    )
    fluxos = pd.DataFrame(
        {
            "id_municipio": ["3500000"],
            "ano": [2020],
            "admissoes": [66.0],
            "desligamentos": [44.0],
        }
    )
    out = calcular_intensidade(estoque, fluxos).iloc[0]
    assert out["estoque_medio_aprox"] == 110.0
    assert out["movimentacao_media"] == 55.0
    assert out["intensidade_fluxos"] == 0.5
    assert out["intensidade_fluxos_pct"] == 50.0


def test_regressao_regional_2020_caderno_metodologico():
    # Controles canônicos: estoque regional 2019 = 1.299.350; 2020 = 1.291.061;
    # Novo CAGED 2020 = 464.439 admissões e 467.947 desligamentos.
    estoque = pd.DataFrame(
        {
            "id_municipio": ["TOTAL", "TOTAL"],
            "ano": [2019, 2020],
            "estoque": [1_299_350.0, 1_291_061.0],
        }
    )
    fluxos = pd.DataFrame(
        {
            "id_municipio": ["TOTAL"],
            "ano": [2020],
            "admissoes": [464_439.0],
            "desligamentos": [467_947.0],
        }
    )
    municipal = calcular_intensidade(estoque, fluxos)
    regional = agregar_regional(municipal).iloc[0]
    esperado = ((464_439 + 467_947) / 2) / ((1_299_350 + 1_291_061) / 2)
    assert np.isclose(regional["intensidade_fluxos"], esperado)
    assert round(regional["intensidade_fluxos_pct"], 1) == 36.0
