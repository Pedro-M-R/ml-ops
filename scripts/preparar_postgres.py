"""Gera senhas locais uma única vez, sem imprimi-las ou incluí-las no pacote."""

import os
import secrets
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    directory = ROOT / "runtime/secrets"
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    if os.name != "nt":
        directory.chmod(0o700)
    for name in ("db_admin_password", "db_reader_password"):
        path = directory / name
        try:
            # Compose monta arquivos, sem remapear uid: o processo postgres precisa lê-los.
            # No host, o diretório 0700 restringe o acesso ao proprietário.
            descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
        except FileExistsError:
            value = path.read_text(encoding="utf-8").strip()
            if not value:
                raise RuntimeError(f"Arquivo de senha vazio: {path}")
            # LF também no Windows: CR pode virar parte da senha no contêiner.
            if path.read_bytes() != (value + "\n").encode("utf-8"):
                path.write_bytes((value + "\n").encode("utf-8"))
            if os.name != "nt":
                path.chmod(0o644)
            continue
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as output:
            output.write(secrets.token_urlsafe(36) + "\n")
        if os.name != "nt":
            path.chmod(0o644)
    print("Senhas prontas em runtime/secrets. Senhas existentes foram preservadas.")


if __name__ == "__main__":
    main()
