"""Adapta o master_profile.md à vaga via Gemini e grava job_profile.md."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from google import genai

ROOT = Path(__file__).resolve().parent.parent
GERADOR = Path(__file__).resolve().parent
DEFAULT_MASTER = GERADOR / "master_profile.md"
DEFAULT_PROMPT = GERADOR / "prompt_template.txt"
DEFAULT_OUTPUT = ROOT / "output" / "job_profile.md"
MODEL = "gemini-flash-latest"


def read_text(path: Path) -> str:
    if not path.is_file():
        raise FileNotFoundError(f"Arquivo não encontrado: {path}")
    return path.read_text(encoding="utf-8")


def build_prompt(template: str, master_profile: str, job_description: str) -> str:
    return (
        template.replace("{master_profile}", master_profile).replace(
            "{job_description}", job_description
        )
    )


def call_gemini(prompt: str, api_key: str) -> str:
    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(model=MODEL, contents=prompt)
    text = (response.text or "").strip()
    if not text:
        raise RuntimeError("A API Gemini retornou uma resposta vazia.")
    # Remove cercas de código se o modelo envolver a resposta em ```markdown
    if text.startswith("```"):
        lines = text.splitlines()
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    return text


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
        template = read_text(args.prompt)
    except FileNotFoundError as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        return 1

    if not job_description.strip():
        print(f"Erro: o arquivo de vaga está vazio: {args.vaga}", file=sys.stderr)
        return 1

    prompt = build_prompt(template, master_profile, job_description)
    print(f"Chamando Gemini ({MODEL})...")

    try:
        tailored = call_gemini(prompt, api_key)
    except Exception as exc:
        print(f"Erro na API Gemini: {exc}", file=sys.stderr)
        return 1

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(tailored + "\n", encoding="utf-8")
    print(f"Currículo adaptado salvo em: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
