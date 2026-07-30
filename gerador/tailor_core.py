"""Núcleo: master profile + vaga → markdown via Gemini."""

from __future__ import annotations

from pathlib import Path

from google import genai

GERADOR = Path(__file__).resolve().parent
DEFAULT_PROMPT = GERADOR / "prompt_template.txt"
MODEL = "gemini-flash-latest"


def build_prompt(template: str, master_profile: str, job_description: str) -> str:
    return template.replace("{master_profile}", master_profile).replace(
        "{job_description}", job_description
    )


def call_gemini(prompt: str, api_key: str, model: str = MODEL) -> str:
    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(model=model, contents=prompt)
    text = (response.text or "").strip()
    if not text:
        raise RuntimeError("A API Gemini retornou uma resposta vazia.")
    if text.startswith("```"):
        lines = text.splitlines()
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    return text


def load_prompt_template(path: Path | None = None) -> str:
    prompt_path = path or DEFAULT_PROMPT
    if not prompt_path.is_file():
        raise FileNotFoundError(f"Prompt não encontrado: {prompt_path}")
    return prompt_path.read_text(encoding="utf-8")


def generate_markdown(
    master_profile: str,
    job_description: str,
    api_key: str,
    prompt_template: str | None = None,
    model: str = MODEL,
) -> str:
    """Gera o job_profile markdown a partir do master + vaga."""
    if not master_profile.strip():
        raise ValueError("master_profile está vazio.")
    if not job_description.strip():
        raise ValueError("job_description está vazio.")
    if not api_key.strip():
        raise ValueError("api_key está vazia.")

    template = prompt_template if prompt_template is not None else load_prompt_template()
    prompt = build_prompt(template, master_profile, job_description)
    return call_gemini(prompt, api_key, model=model)
