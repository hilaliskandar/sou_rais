import math

import pandas as pd

from tic_tim_analysis import (
    concentracao_empregadores,
    deflacionar_remuneracao,
    gap_medio_raca,
    gap_mediano_sexo,
    hhi,
    intensidade_fluxos,
    mudanca_participacao_regional,
    perfil_etario,
    quociente_locacional,
    referencia_escolaridade_cbo,
    resumo_remuneracao,
    shift_share,
)


def test_ql_e_hhi_basicos():
    base = pd.DataFrame(
        {
            "id_municipio": ["1", "1", "2", "2"],
            "ano": [2025] * 4,
            "setor": ["A", "B", "A", "B"],
            "vinculos": [80, 20, 20, 80],
        }
    )
    ql = quociente_locacional(base)
    q1a = ql.query("id_municipio == '1' and setor == 'A'").iloc[0]
    assert math.isclose(q1a.ql, 1.6)
    hh = hhi(base, "setor")
    assert math.isclose(hh.query("id_municipio == '1'").iloc[0].hhi, 0.68)


def test_mudanca_participacao_regional():
    est = pd.DataFrame(
        {
            "id_municipio": ["1", "2", "1", "2"],
            "ano": [2015, 2015, 2025, 2025],
            "estoque": [50, 50, 75, 25],
        }
    )
    out = mudanca_participacao_regional(est)
    assert math.isclose(out.query("id_municipio == '1'").iloc[0].mudanca_pp, 25.0)


def test_shift_share_reconstroi_variacao():
    base = pd.DataFrame(
        {
            "id_municipio": ["1", "1", "2", "2", "1", "1", "2", "2"],
            "ano": [2015, 2015, 2015, 2015, 2025, 2025, 2025, 2025],
            "setor": ["A", "B", "A", "B", "A", "B", "A", "B"],
            "vinculos": [50, 50, 50, 50, 80, 40, 60, 70],
        }
    )
    ss = shift_share(base, 2015, 2025)
    assert ss.loc[ss.elegivel, "erro_reconstrucao"].abs().max() < 1e-9


def test_intensidade_fluxos():
    assert math.isclose(intensidade_fluxos(100, 80, 200), 0.45)


def test_perfil_etario_indice():
    df = pd.DataFrame(
        {
            "id_municipio": ["1"] * 4,
            "ano": [2025] * 4,
            "idade": [20, 29, 55, 60],
        }
    )
    p = perfil_etario(df).iloc[0]
    assert math.isclose(p.share_ate29, 0.5)
    assert math.isclose(p.share_55mais, 0.5)
    assert math.isclose(p.indice_envelhecimento, 100.0)


def test_remuneracao_zero_excluida_somente_do_calculo():
    df = pd.DataFrame(
        {
            "id_municipio": ["1", "1", "1"],
            "ano": [2025, 2025, 2025],
            "remuneracao_real": [0, 1000, 3000],
        }
    )
    r = resumo_remuneracao(df).iloc[0]
    assert r.vinculos_total == 3
    assert r.vinculos_remuneracao == 2
    assert math.isclose(r.mediana, 2000)
    assert math.isclose(r.cobertura_remuneratoria, 2 / 3)


def test_deflacao_ipca():
    df = pd.DataFrame({"ano": [2020, 2025], "rem": [100.0, 100.0]})
    ipca = pd.DataFrame({"ano": [2020, 2025], "indice": [80.0, 100.0]})
    x = deflacionar_remuneracao(df, ipca, "rem")
    assert math.isclose(x.loc[x.ano == 2020, "remuneracao_real"].iloc[0], 125.0)
    assert math.isclose(x.loc[x.ano == 2025, "remuneracao_real"].iloc[0], 100.0)


def test_gaps_sexo_e_raca():
    df = pd.DataFrame(
        {
            "id_municipio": ["1"] * 8,
            "ano": [2025] * 8,
            "sexo": ["M", "M", "F", "F", "M", "M", "F", "F"],
            "raca_cor": ["Branco", "Branco", "Pardo", "Pardo", "Branco", "Branco", "Preto", "Preto"],
            "r": [100, 200, 80, 120, 100, 200, 80, 120],
        }
    )
    gs = gap_mediano_sexo(df, "r").iloc[0]
    assert gs.gap_sexo_pct < 0
    gr = gap_medio_raca(df, "r").iloc[0]
    assert gr.gap_raca_pct < 0


def test_concentracao_empregadores():
    df = pd.DataFrame(
        {
            "id_municipio": ["1"] * 10,
            "ano": [2025] * 10,
            "id_estabelecimento": ["A"] * 6 + ["B"] * 3 + ["C"],
        }
    )
    c = concentracao_empregadores(df).iloc[0]
    assert c.estabelecimentos_positivos == 3
    assert math.isclose(c.top1_share, 0.6)
    assert math.isclose(c.top10_share, 1.0)


def test_referencia_empirica_escolaridade():
    df = pd.DataFrame(
        {
            "ano": [2025] * 5,
            "cbo_familia": ["1234"] * 5,
            "escolaridade": [3, 3, 3, 5, 1],
        }
    )
    out = referencia_escolaridade_cbo(df, min_celula=5)
    assert out.escolaridade_ref.iloc[0] == 3
    assert set(out.classe_referencia) == {"proximo", "acima", "abaixo"}
