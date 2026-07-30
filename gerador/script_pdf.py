"""CLI opcional: job_profile.md → PDF."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from gerador.pdf_core import render_pdf

DEFAULT_OUTPUT = ROOT / "output" / "curriculo.pdf"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Transforma job_profile.md em PDF via HTML/CSS."
    )
    parser.add_argument(
        "markdown",
        type=Path,
        nargs="?",
        default=ROOT / "output" / "job_profile.md",
        help="Caminho do markdown (padrão: output/job_profile.md)",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"PDF de saída (padrão: {DEFAULT_OUTPUT})",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if not args.markdown.is_file():
        print(f"Erro: arquivo não encontrado: {args.markdown}", file=sys.stderr)
        return 1

    try:
        render_pdf(args.markdown, args.out)
    except Exception as exc:
        print(f"Erro ao gerar PDF: {exc}", file=sys.stderr)
        return 1

    print(f"PDF gerado em: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
