from __future__ import annotations

"""Executa a cadeia reprodutível TIC-TIM em ordem dependente.

A aquisição de dados é deliberadamente separada. Este orquestrador parte de `dados/processado`
e executa análise, intensidade de fluxos, gates regionais/municipais e produtos visuais.
Mapas dependem da malha auxiliar; figuras/mapas podem ser desabilitados para execução de
validação exclusivamente tabular.
"""

import argparse
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def executar(script: str, *args: str, permitir_falha: bool = False) -> int:
    cmd = [sys.executable, str(ROOT / "scripts" / script), *args]
    print("\n>", " ".join(cmd))
    proc = subprocess.run(cmd, cwd=ROOT, check=False)
    if proc.returncode and not permitir_falha:
        raise SystemExit(f"Etapa falhou ({proc.returncode}): {script}")
    return proc.returncode


def main() -> None:
    ap = argparse.ArgumentParser(description="Executa pipeline TIC-TIM de emprego e estrutura econômica.")
    ap.add_argument("--sem-visuais", action="store_true", help="Não gera figuras nem mapas.")
    ap.add_argument(
        "--permitir-nao-implementado",
        action="store_true",
        help="Permite que os gates terminem com indicadores ainda não implementados.",
    )
    args = ap.parse_args()

    executar("analisar_tic_tim.py")
    executar("calcular_intensidade_fluxos.py")

    gate_args = ["--nao-falhar-por-nao-implementado"] if args.permitir_nao_implementado else []
    executar("validar_controles_regionais.py", *gate_args)
    executar("validar_fichas_publicadas.py", *gate_args)

    if not args.sem_visuais:
        executar("gerar_figuras_tic_tim.py")
        executar("gerar_mapas_tic_tim.py")

    print("\nPipeline TIC-TIM concluído nas etapas solicitadas.")


if __name__ == "__main__":
    main()
