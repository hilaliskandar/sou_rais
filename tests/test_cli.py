import os

from sou_rais_cli import _bases, build_parser, main


def test_bases_all():
    assert _bases("all") == ["rais", "caged", "cnpj"]


def test_bases_individual():
    assert _bases("rais") == ["rais"]


def test_parser_plan_default_all():
    args = build_parser().parse_args(["plan"])
    assert args.command == "plan"
    assert args.base == "all"


def test_parser_download_dry_run():
    args = build_parser().parse_args(["download", "caged", "--dry-run"])
    assert args.base == "caged"
    assert args.dry_run is True


def test_doctor_sem_config_retorna_erro(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("BIGQUERY_PROJECT", raising=False)
    assert main(["doctor"]) == 1
