from __future__ import annotations

import argparse
import os
import runpy
import sys
from pathlib import Path

from sou_rais import carregar_config, lotes

ROOT = Path(__file__).resolve().parent
SCRIPTS = {
    "rais": ROOT / "scripts" / "baixar_rais.py",
    "caged": ROOT / "scripts" / "baixar_novo_caged.py",
    "cnpj": ROOT / "scripts" / "baixar_cnpj.py",
    "validate": ROOT / "scripts" / "validar_e_indexar.py",
}


def _executar_script(path: Path, args: list[str] | None = None) -> None:
    if not path.exists():
        raise FileNotFoundError(f"Script não encontrado: {path}")
    argv_anterior = sys.argv[:]
    try:
        sys.argv = [str(path), *(args or [])]
        runpy.run_path(str(path), run_name="__main__")
    finally:
        sys.argv = argv_anterior


def _bases(valor: str) -> list[str]:
    return ["rais", "caged", "cnpj"] if valor == "all" else [valor]


def cmd_plan(args: argparse.Namespace) -> int:
    for base in _bases(args.base):
        print(f"\n=== PLANO: {base.upper()} ===")
        _executar_script(SCRIPTS[base], ["--dry-run"])
    return 0


def cmd_download(args: argparse.Namespace) -> int:
    extras = ["--dry-run"] if args.dry_run else []
    for base in _bases(args.base):
        print(f"\n=== DOWNLOAD: {base.upper()} ===")
        _executar_script(SCRIPTS[base], extras)
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    _executar_script(SCRIPTS["validate"])
    return 0


def cmd_config(args: argparse.Namespace) -> int:
    cfg = carregar_config(Path.cwd())
    grupos = lotes(cfg.municipios, cfg.lote_tamanho)
    print("Configuração carregada com sucesso")
    print(f"Raiz: {cfg.root}")
    print(f"Municípios: {len(cfg.municipios)}")
    print(f"Lotes: {len(grupos)} | tamanho máximo: {cfg.lote_tamanho}")
    print(f"Validação municipal: {cfg.validacao_municipios}")
    print(f"RAIS: {cfg.ano_inicial or 'início disponível'} a {cfg.ano_final or 'fim disponível'}")
    print(f"Novo CAGED: {cfg.competencia_inicial or 'início disponível'} a {cfg.competencia_final or 'fim disponível'}")
    print(f"CNPJ: {cfg.snapshot_inicial or 'primeiro snapshot'} a {cfg.snapshot_final or 'último snapshot'}")
    print(f"Estimativa de custo: {cfg.estimar_custo}")
    print(f"Sobrescrever: {cfg.sobrescrever}")
    return 0


def cmd_doctor(args: argparse.Namespace) -> int:
    erros: list[str] = []
    try:
        cfg = carregar_config(Path.cwd())
        print(f"[OK] configuração: {len(cfg.municipios)} município(s)")
    except Exception as exc:
        erros.append(f"configuração: {exc}")

    if os.getenv("BIGQUERY_PROJECT"):
        print(f"[OK] BIGQUERY_PROJECT={os.getenv('BIGQUERY_PROJECT')}")
    else:
        erros.append("variável BIGQUERY_PROJECT não definida")

    if erros:
        for erro in erros:
            print(f"[ERRO] {erro}")
        return 1

    print("Ambiente básico: OK")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="sou-rais",
        description="Aquisição reproduzível de RAIS, Novo CAGED e snapshots do CNPJ por municípios.",
    )
    parser.add_argument("--version", action="version", version="sou-rais 0.1.0")
    sub = parser.add_subparsers(dest="command", required=True)

    p_plan = sub.add_parser("plan", help="Descobre cobertura e estima consultas/bytes sem baixar microdados.")
    p_plan.add_argument("base", choices=["rais", "caged", "cnpj", "all"], nargs="?", default="all")
    p_plan.set_defaults(func=cmd_plan)

    p_download = sub.add_parser("download", help="Baixa uma base ou todas as bases configuradas.")
    p_download.add_argument("base", choices=["rais", "caged", "cnpj", "all"])
    p_download.add_argument("--dry-run", action="store_true", help="Somente planeja e estima; não grava Parquets.")
    p_download.set_defaults(func=cmd_download)

    p_validate = sub.add_parser("validate", help="Valida Parquets locais e gera índice com SHA-256.")
    p_validate.set_defaults(func=cmd_validate)

    p_config = sub.add_parser("config", help="Mostra a configuração resolvida da execução.")
    p_config.set_defaults(func=cmd_config)

    p_doctor = sub.add_parser("doctor", help="Verifica configuração local e variável BIGQUERY_PROJECT.")
    p_doctor.set_defaults(func=cmd_doctor)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args) or 0)


if __name__ == "__main__":
    raise SystemExit(main())
