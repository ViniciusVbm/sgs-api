"""Gera as chaves do `FieldCipher` no formato de CRYPTO_KEYS (spec 002, T5).

    uv run python -m src.tools.crypto_keys --output secrets/crypto-keys.json

Sem `--output`, escreve na saída padrão. Sai um objeto JSON `{"1": "<32 bytes em base64>"}`, nova
a cada execução; CRYPTO_ACTIVE_KEY=1 diz que a versão 1 cifra. Na rotação, acrescente uma versão
nova e aponte CRYPTO_ACTIVE_KEY para ela; mantenha as antigas para decifrar o que já existe. O
arquivo é segredo: `secrets/` fica fora do Git.
"""

import argparse
import base64
import json
import os
import sys
from collections.abc import Sequence
from pathlib import Path

from src.core.config import CRYPTO_KEY_BYTES


def novas_chaves(versao: int = 1) -> dict[str, str]:
    return {str(versao): base64.b64encode(os.urandom(CRYPTO_KEY_BYTES)).decode()}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Gera CRYPTO_KEYS para o FieldCipher.")
    parser.add_argument("--output", type=Path, default=None, help="arquivo de saída")
    args = parser.parse_args(argv)
    conteudo = json.dumps(novas_chaves()) + "\n"
    if args.output is None:
        sys.stdout.write(conteudo)
        return 0
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(conteudo, encoding="utf-8")
    args.output.chmod(0o600)
    sys.stdout.write(f"Chaves gravadas em {args.output} (CRYPTO_ACTIVE_KEY=1).\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
