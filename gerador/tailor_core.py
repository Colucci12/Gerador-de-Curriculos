"""Núcleo: master profile + vaga → markdown via Gemini."""

from __future__ import annotations

from pathlib import Path

from google import genai

GERADOR = Path(__file__).resolve().parent
DEFAULT_LANGUAGE = "pt-BR"
VALID_LANGUAGES = frozenset({"pt-BR", "en-US"})
DEFAULT_PROMPT = GERADOR / "prompt_template_pt-BR.txt"
# Legado: alguns scripts ainda apontam para prompt_template.txt
LEGACY_PROMPT = GERADOR / "prompt_template.txt"
MODEL = "gemini-flash-latest"

_PROMPT_BY_LANGUAGE = {
    "pt-BR": GERADOR / "prompt_template_pt-BR.txt",
    "en-US": GERADOR / "prompt_template_en-US.txt",
}


def normalize_language(language: str | None) -> str:
    value = (language or DEFAULT_LANGUAGE).strip()
    # Aceita variações comuns
    lowered = value.lower().replace("_", "-")
    aliases = {
        "pt": "pt-BR",
        "pt-br": "pt-BR",
        "en": "en-US",
        "en-us": "en-US",
    }
    normalized = aliases.get(lowered, value if value in VALID_LANGUAGES else "")
    if normalized not in VALID_LANGUAGES:
        raise ValueError(
            f"Idioma inválido: {language!r}. Use: pt-BR ou en-US."
        )
    return normalized


def prompt_path_for_language(language: str | None = None) -> Path:
    lang = normalize_language(language)
    return _PROMPT_BY_LANGUAGE[lang]


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


def load_prompt_for_language(language: str | None = None) -> str:
    return load_prompt_template(prompt_path_for_language(language))


def generate_markdown(
    master_profile: str,
    job_description: str,
    api_key: str,
    prompt_template: str | None = None,
    language: str | None = None,
    model: str = MODEL,
) -> str:
    """Gera o job_profile markdown a partir do master + vaga."""
    if not master_profile.strip():
        raise ValueError("master_profile está vazio.")
    if not job_description.strip():
        raise ValueError("job_description está vazio.")
    if not api_key.strip():
        raise ValueError("api_key está vazia.")

    if prompt_template is not None:
        template = prompt_template
    else:
        template = load_prompt_for_language(language)
    prompt = build_prompt(template, master_profile, job_description)
    return call_gemini(prompt, api_key, model=model)
