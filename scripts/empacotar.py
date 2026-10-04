"""Gera ZIP transportável; não copia venv nem URIs absolutas do banco de tracking."""

import argparse
import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--include-data", action="store_true", help="Inclui CSV e ponteiro para retreino.")
    args = parser.parse_args()
    selection = json.loads((ROOT / "reports/selection.json").read_text(encoding="utf-8"))
    files = []
    for name in ("pyproject.toml", "uv.lock", ".python-version", "README.md", "Dockerfile", "docker-compose.yml", ".dockerignore"):
        files.append(ROOT / name)
    for name in ("src", "scripts", "tests", "reports", "docs", selection["export_path"]):
        files.extend(path for path in (ROOT / name).rglob("*") if path.is_file()
                     and "__pycache__" not in path.parts and path.suffix != ".pyc")
    if args.include_data:
        files.extend([ROOT / "data/churn.csv", ROOT / "data/churn.csv.dvc"])
    destination = ROOT / "dist/churn-portatil.zip"
    destination.parent.mkdir(exist_ok=True)
    with ZipFile(destination, "w", compression=ZIP_DEFLATED) as archive:
        for path in sorted(set(files)):
            archive.write(path, Path("churn-portatil") / path.relative_to(ROOT))
    print(f"{destination} ({destination.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
