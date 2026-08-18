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
# Fallback só para CLI legado; a web usa o 1º da lista dinâmica.
MODEL = "gemini-2.5-flash"
DEFAULT_MODEL_LIST_LIMIT = 5

_EXCLUDE_NAME_PARTS = (
    "imagen",
    "veo",
    "embedding",
    "embed",
    "tts",
    "live",
    "aqa",
    "image",
    "robotics",
    "computer-use",
)

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


def _model_id(name: str | None) -> str:
    raw = (name or "").strip()
    if raw.startswith("models/"):
        return raw[len("models/") :]
    return raw


def _supports_generate_content(model) -> bool:
    actions = getattr(model, "supported_actions", None) or ()
    methods = getattr(model, "supported_generation_methods", None) or ()
    combined = {str(item) for item in (*actions, *methods)}
    return "generateContent" in combined


def _is_excluded_model(model_id: str) -> bool:
    lowered = model_id.lower()
    return any(part in lowered for part in _EXCLUDE_NAME_PARTS)


def _model_sort_key(model_id: str) -> tuple:
    """Flash versionado primeiro; aliases -latest/-exp depois; resto no fim."""
    lowered = model_id.lower()
    is_latest_or_exp = "-latest" in lowered or "-exp" in lowered
    is_flash = "flash" in lowered
    if is_flash and not is_latest_or_exp:
        tier = 0
    elif is_flash:
        tier = 1
    else:
        tier = 2
    return (tier, lowered)


def list_text_models(
    api_key: str, limit: int = DEFAULT_MODEL_LIST_LIMIT
) -> list[str]:
    """Lista IDs de modelos de texto (generateContent), ordenados e limitados."""
    if not (api_key or "").strip():
        raise ValueError("api_key está vazia.")
    if limit < 1:
        raise ValueError("limit deve ser >= 1.")

    client = genai.Client(api_key=api_key)
    seen: set[str] = set()
    ids: list[str] = []
    for model in client.models.list():
        if not _supports_generate_content(model):
            continue
        model_id = _model_id(getattr(model, "name", None))
        if not model_id or model_id in seen or _is_excluded_model(model_id):
            continue
        seen.add(model_id)
        ids.append(model_id)

    ids.sort(key=_model_sort_key)
    return ids[:limit]


def call_gemini(prompt: str, api_key: str, model: str) -> str:
    if not (model or "").strip():
        raise ValueError("model está vazio.")
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
    model: str | None = None,
) -> str:
    """Gera o job_profile markdown a partir do master + vaga."""
    if not master_profile.strip():
        raise ValueError("master_profile está vazio.")
    if not job_description.strip():
        raise ValueError("job_description está vazio.")
    if not api_key.strip():
        raise ValueError("api_key está vazia.")

    chosen = (model or MODEL).strip()
    if not chosen:
        raise ValueError("model está vazio.")

    if prompt_template is not None:
        template = prompt_template
    else:
        template = load_prompt_for_language(language)
    prompt = build_prompt(template, master_profile, job_description)
    return call_gemini(prompt, api_key, model=chosen)
