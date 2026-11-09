"""Linhagem do dado versionado pelo DVC e do código no Git."""

import subprocess
from pathlib import Path

import yaml

from churn.config import PROJECT_ROOT


def data_md5(dvc_pointer: Path = PROJECT_ROOT / "data/churn.csv.dvc") -> str:
    """Lê a versão do dado no ponteiro DVC, sem fixar o hash no código."""
    doc = yaml.safe_load(Path(dvc_pointer).read_text(encoding="utf-8"))
    return doc["outs"][0]["md5"]


def git_commit() -> str:
    """Retorna o commit atual, ou unknown quando executado sem Git (Docker)."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=PROJECT_ROOT, capture_output=True, text=True, check=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        return "unknown"
    return result.stdout.strip()


def git_dirty() -> str:
    """Indica se o treino usou alterações ainda não presentes no commit."""
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=PROJECT_ROOT, capture_output=True, text=True, check=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        return "unknown"
    return str(bool(result.stdout.strip())).lower()
