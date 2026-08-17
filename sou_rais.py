from __future__ import annotations

import csv
import hashlib
import json
import os
import warnings
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

import pandas as pd
from google.cloud import bigquery

VALIDATION_MODES = {"strict", "warning", "off"}


@dataclass(frozen=True)
class Config:
    root: Path
    municipios: list[str]
    lote_tamanho: int = 5
    ano_inicial: int | None = None
    ano_final: int | None = None
    competencia_inicial: str | None = None
    competencia_final: str | None = None
    snapshot_inicial: str | None = None
    snapshot_final: str | None = None
    estimar_custo: bool = True
    sobrescrever: bool = False
    validacao_municipios: str = "warning"

    @property
    def data_dir(self) -> Path:
        return self.root / "dados"

    @property
    def processado_dir(self) -> Path:
        return self.data_dir / "processado"

    @property
    def controle_dir(self) -> Path:
        return self.data_dir / "controle"


def _dedupe(values: Iterable[str]) -> list[str]:
    return list(dict.fromkeys(str(v).strip() for v in values if str(v).strip()))


def validar_codigos_ibge(ids: Iterable[str]) -> list[str]:
    ids = _dedupe(ids)
    if not ids:
        raise ValueError("Nenhum município informado.")
    invalidos = [x for x in ids if len(x) != 7 or not x.isdigit()]
    if invalidos:
        raise ValueError(f"Códigos IBGE municipais inválidos: {invalidos}")
    return ids


def carregar_municipios(root: Path, inline: Iterable[str] | None = None, arquivo: str = "municipios.csv") -> list[str]:
    path = root / arquivo
    if path.exists():
        df = pd.read_csv(path, dtype=str)
        if "id_municipio" not in df.columns:
            raise ValueError(f"{arquivo} deve conter a coluna id_municipio")
        ids = df["id_municipio"].dropna().astype(str).tolist()
    else:
        ids = list(inline or [])
    return validar_codigos_ibge(ids)


def carregar_config(root: Path | None = None, inline: Iterable[str] | None = None) -> Config:
    root = Path(root or Path.cwd()).resolve()
    cfg_path = root / "config.json"
    raw: dict = {}
    if cfg_path.exists():
        raw = json.loads(cfg_path.read_text(encoding="utf-8"))
    ids = carregar_municipios(root, inline=inline, arquivo=raw.get("arquivo_municipios", "municipios.csv"))
    modo = str(raw.get("validacao_municipios", "warning")).strip().lower()
    if modo not in VALIDATION_MODES:
        raise ValueError(f"validacao_municipios deve ser um de {sorted(VALIDATION_MODES)}")
    cfg = Config(
        root=root,
        municipios=ids,
        lote_tamanho=int(raw.get("lote_tamanho", 5)),
        ano_inicial=raw.get("ano_inicial"),
        ano_final=raw.get("ano_final"),
        competencia_inicial=raw.get("competencia_inicial"),
        competencia_final=raw.get("competencia_final"),
        snapshot_inicial=raw.get("snapshot_inicial"),
        snapshot_final=raw.get("snapshot_final"),
        estimar_custo=bool(raw.get("estimar_custo", True)),
        sobrescrever=bool(raw.get("sobrescrever", False)),
        validacao_municipios=modo,
    )
    if cfg.lote_tamanho < 1:
        raise ValueError("lote_tamanho deve ser >= 1")
    for p in [cfg.data_dir, cfg.processado_dir, cfg.controle_dir]:
        p.mkdir(parents=True, exist_ok=True)
    return cfg


def lotes(ids: list[str], tamanho: int) -> list[list[str]]:
    return [ids[i:i + tamanho] for i in range(0, len(ids), tamanho)]


def cliente_bigquery() -> bigquery.Client:
    project = os.getenv("BIGQUERY_PROJECT")
    if not project:
        raise EnvironmentError("Defina BIGQUERY_PROJECT com um projeto Google Cloud habilitado para cobrança do BigQuery.")
    return bigquery.Client(project=project)


def estimar_bytes(bq: bigquery.Client, sql: str) -> int | None:
    job = bq.query(sql, job_config=bigquery.QueryJobConfig(dry_run=True, use_query_cache=False))
    return getattr(job, "total_bytes_processed", None)


def formatar_gb(n: int | None) -> str:
    return "indisponível" if n is None else f"{n / 1024**3:.3f} GB"


def filtrar_anos(anos: Iterable[int], cfg: Config) -> list[int]:
    out = sorted(int(x) for x in anos)
    if cfg.ano_inicial is not None:
        out = [x for x in out if x >= int(cfg.ano_inicial)]
    if cfg.ano_final is not None:
        out = [x for x in out if x <= int(cfg.ano_final)]
    return out


def filtrar_strings(valores: Iterable[str], inicio: str | None, fim: str | None) -> list[str]:
    out = sorted(str(x) for x in valores)
    if inicio:
        out = [x for x in out if x >= inicio]
    if fim:
        out = [x for x in out if x <= fim]
    return out


def municipios_faltantes(df: pd.DataFrame, esperados: Iterable[str]) -> list[str]:
    if "id_municipio" not in df.columns:
        raise ValueError("A consulta não retornou a coluna id_municipio.")
    encontrados = set(df["id_municipio"].dropna().astype(str).unique())
    return sorted(set(str(x) for x in esperados) - encontrados)


def validar_municipios_retornados(
    df: pd.DataFrame,
    esperados: Iterable[str],
    modo: str = "warning",
    contexto: str | None = None,
) -> list[str]:
    modo = str(modo).strip().lower()
    if modo not in VALIDATION_MODES:
        raise ValueError(f"Modo de validação inválido: {modo}")
    if modo == "off":
        return []
    faltantes = municipios_faltantes(df, esperados)
    if not faltantes:
        return []
    prefixo = f"{contexto}: " if contexto else ""
    msg = f"{prefixo}municípios sem registros na partição: {faltantes}"
    if modo == "strict":
        raise RuntimeError(msg)
    warnings.warn(msg, RuntimeWarning, stacklevel=2)
    return faltantes


def plano_resumo(base: str, itens: int, lotes_n: int, consultas: int, particoes: int, bytes_estimados: int | None) -> dict:
    return {
        "base": base,
        "itens_temporais": int(itens),
        "lotes": int(lotes_n),
        "consultas_bigquery": int(consultas),
        "particoes_previstas": int(particoes),
        "bytes_estimados": bytes_estimados,
        "gb_estimados": formatar_gb(bytes_estimados),
    }


def salvar_plano(cfg: Config, nome: str, rows: list[dict]) -> Path:
    path = cfg.controle_dir / f"plano_{nome}.csv"
    pd.DataFrame(rows).to_csv(path, index=False)
    return path


def sha256(path: Path, chunk: int = 1024 * 1024) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for bloco in iter(lambda: f.read(chunk), b""):
            h.update(bloco)
    return h.hexdigest()


def manifestar(cfg: Config, **row) -> None:
    path = cfg.controle_dir / "manifesto_execucoes.csv"
    registro = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        **{k: str(v) for k, v in row.items()},
    }
    existe = path.exists()
    with path.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(registro.keys()))
        if not existe:
            w.writeheader()
        w.writerow(registro)


def gravar_parquet_atomico(df: pd.DataFrame, out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_suffix(out.suffix + ".tmp")
    df.to_parquet(tmp, index=False, compression="snappy")
    tmp.replace(out)
