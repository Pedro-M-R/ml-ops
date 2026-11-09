"""Copia a base existente para a publicação do painel, sem treinar o modelo."""

import argparse
import hashlib
from io import BytesIO
from pathlib import Path

import pandas as pd

from churn.dashboard_client import customers_from_frame

ROOT = Path(__file__).resolve().parents[1]


def prepare_base(source: Path):
    content = source.read_bytes()
    frame = pd.read_csv(BytesIO(content), dtype=str, keep_default_na=False, encoding="utf-8-sig")
    customers_from_frame(frame)
    destination = ROOT / "frontend/data/churn.csv"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(content)
    return destination, len(frame), hashlib.sha256(content).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=ROOT / "data/churn.csv")
    args = parser.parse_args()
    destination, rows, digest = prepare_base(args.input)
    print(f"Base do painel preparada: {rows} clientes em {destination}")
    print(f"SHA-256: {digest}")


if __name__ == "__main__":
    main()
