import json
from pathlib import Path

import pandas as pd
import pytest

from sou_rais import (
    carregar_config,
    lotes,
    validar_codigos_ibge,
    validar_municipios_retornados,
)


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
    assert cfg.validacao_municipios == "warning"
    assert cfg.processado_dir.exists()
    assert cfg.controle_dir.exists()


def test_config_rejeita_modo_validacao_invalido(tmp_path: Path):
    pd.DataFrame({"id_municipio": ["3516408"]}).to_csv(tmp_path / "municipios.csv", index=False)
    (tmp_path / "config.json").write_text(
        json.dumps({"validacao_municipios": "talvez"}), encoding="utf-8"
    )
    with pytest.raises(ValueError):
        carregar_config(tmp_path)


def test_validacao_strict_interrompe():
    df = pd.DataFrame({"id_municipio": ["3516408"]})
    with pytest.raises(RuntimeError):
        validar_municipios_retornados(df, ["3516408", "3525904"], modo="strict")


def test_validacao_warning_retorna_faltantes():
    df = pd.DataFrame({"id_municipio": ["3516408"]})
    with pytest.warns(RuntimeWarning):
        faltantes = validar_municipios_retornados(
            df, ["3516408", "3525904"], modo="warning"
        )
    assert faltantes == ["3525904"]


def test_validacao_off_ignora_ausencias():
    df = pd.DataFrame({"outra_coluna": [1]})
    assert validar_municipios_retornados(
        df, ["3516408"], modo="off"
    ) == []
