from pathlib import Path

import pandas as pd
import pytest

from sou_rais import carregar_config, lotes, validar_codigos_ibge


def test_validar_codigos_ibge_remove_duplicatas():
    assert validar_codigos_ibge(["3516408", "3516408", "3525904"]) == ["3516408", "3525904"]


def test_validar_codigos_ibge_rejeita_invalido():
    with pytest.raises(ValueError):
        validar_codigos_ibge(["123", "abcdefg"])


def test_lotes():
    assert lotes(["1", "2", "3", "4", "5"], 2) == [["1", "2"], ["3", "4"], ["5"]]


def test_carregar_config_por_csv(tmp_path: Path):
    pd.DataFrame({"id_municipio": ["3516408", "3525904"]}).to_csv(tmp_path / "municipios.csv", index=False)
    cfg = carregar_config(tmp_path)
    assert cfg.municipios == ["3516408", "3525904"]
    assert cfg.processado_dir.exists()
    assert cfg.controle_dir.exists()
