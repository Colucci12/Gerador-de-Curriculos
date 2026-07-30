"""CLI opcional: adapta master_profile.md à vaga via Gemini."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

from gerador.tailor_core import generate_markdown, load_prompt_template

GERADOR = Path(__file__).resolve().parent
DEFAULT_MASTER = GERADOR / "master_profile.md"
DEFAULT_PROMPT = GERADOR / "prompt_template.txt"
DEFAULT_OUTPUT = ROOT / "output" / "job_profile.md"


def read_text(path: Path) -> str:
    if not path.is_file():
        raise FileNotFoundError(f"Arquivo não encontrado: {path}")
    return path.read_text(encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Gera job_profile.md a partir de uma vaga (.txt) e do master_profile.md."
    )
    parser.add_argument(
        "vaga",
        type=Path,
        help="Caminho do arquivo .txt com o texto da vaga (ex.: input/vaga_empresa_x.txt)",
    )
    parser.add_argument(
        "--master",
        type=Path,
        default=DEFAULT_MASTER,
        help=f"Caminho do master profile (padrão: {DEFAULT_MASTER})",
    )
    parser.add_argument(
        "--prompt",
        type=Path,
        default=DEFAULT_PROMPT,
        help=f"Caminho do prompt template (padrão: {DEFAULT_PROMPT})",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Arquivo de saída (padrão: {DEFAULT_OUTPUT})",
    )
    return parser.parse_args()


def main() -> int:
    load_dotenv(ROOT / ".env")
    args = parse_args()

    api_key = os.getenv("GOOGLE_API_KEY", "").strip()
    if not api_key or api_key == "sua_chave_aqui":
        print(
            "Erro: defina GOOGLE_API_KEY no arquivo .env (veja .env.example).",
            file=sys.stderr,
        )
        return 1

    try:
        job_description = read_text(args.vaga)
        master_profile = read_text(args.master)
        template = load_prompt_template(args.prompt)
        tailored = generate_markdown(
            master_profile, job_description, api_key, prompt_template=template
        )
    except Exception as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        return 1

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(tailored + "\n", encoding="utf-8")
    print(f"Currículo adaptado salvo em: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
