"""Núcleo: job_profile markdown → PDF (WeasyPrint)."""

from __future__ import annotations

import html
import re
from io import BytesIO
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape
from weasyprint import HTML

GERADOR = Path(__file__).resolve().parent
TEMPLATE_DIR = GERADOR / "template"

HEADING_H1 = re.compile(r"^#\s+(.+)$")
HEADING_H2 = re.compile(r"^##\s+(.+)$")
HEADING_H3 = re.compile(r"^###\s+(.+)$")
BULLET = re.compile(r"^[-*]\s+(.+)$")
MD_BOLD = re.compile(r"\*\*(.+?)\*\*")
SKILL_CATEGORY = re.compile(r"^\*\*(.+?):\*\*\s*(.*)$")
CONTACT_FIELD = re.compile(r"^([a-zA-ZÀ-ÿ_]+)\s*:\s*(.+)$")

CONTACT_KEYS = {
    "email": "email",
    "telefone": "telefone",
    "phone": "telefone",
    "cidade": "cidade",
    "location": "cidade",
    "localizacao": "cidade",
    "localização": "cidade",
    "linkedin": "linkedin",
    "github": "github",
}

SECTION_MAP = {
    # pt-BR
    "contato": "contact",
    "resumo": "summary",
    "experiência": "experience",
    "experiencia": "experience",
    "formação": "education",
    "formacao": "education",
    "educação": "education",
    "educacao": "education",
    "competências": "skills",
    "competencias": "skills",
    "habilidades": "skills",
    "projetos": "projects",
    # en-US (ATS-common)
    "contact": "contact",
    "summary": "summary",
    "professional summary": "summary",
    "experience": "experience",
    "work experience": "experience",
    "skills": "skills",
    "education": "education",
    "projects": "projects",
}

SECTION_LABELS = {
    "pt-BR": {
        "summary": "Resumo Profissional",
        "experience": "Experiência Profissional",
        "skills": "Habilidades e Competências",
        "education": "Educação",
        "projects": "Projetos e Atividades",
    },
    "en-US": {
        "summary": "Summary",
        "experience": "Experience",
        "skills": "Skills",
        "education": "Education",
        "projects": "Projects",
    },
}

_EN_SECTION_TITLES = frozenset(
    {
        "contact",
        "summary",
        "professional summary",
        "experience",
        "work experience",
        "skills",
        "education",
        "projects",
    }
)


def bold_md_to_html(text: str) -> str:
    """Converte apenas **negrito** em <strong>, escapando o restante."""
    if not text:
        return ""

    placeholders: list[str] = []

    def replace_bold(match: re.Match[str]) -> str:
        idx = len(placeholders)
        placeholders.append(f"<strong>{html.escape(match.group(1))}</strong>")
        return f"@@B{idx}@@"

    working = MD_BOLD.sub(replace_bold, text)
    working = html.escape(working)
    for idx, snippet in enumerate(placeholders):
        working = working.replace(f"@@B{idx}@@", snippet)
    return working


def _split_parts(title: str) -> list[str]:
    return [part.strip() for part in title.split("|")]


def parse_experience_heading(title: str) -> dict:
    parts = _split_parts(title)
    return {
        "company": parts[0] if parts else "",
        "role": parts[1] if len(parts) > 1 else "",
        "period": parts[2] if len(parts) > 2 else "",
        "location": parts[3] if len(parts) > 3 else "",
        "title": title,
        "bullets": [],
    }


def parse_education_heading(title: str) -> dict:
    parts = _split_parts(title)
    return {
        "institution": parts[0] if parts else "",
        "degree": parts[1] if len(parts) > 1 else "",
        "period": parts[2] if len(parts) > 2 else "",
        "location": parts[3] if len(parts) > 3 else "",
        "bullets": [],
    }


def parse_project_heading(title: str) -> dict:
    parts = _split_parts(title)
    return {
        "title": parts[0] if parts else "",
        "period": parts[1] if len(parts) > 1 else "",
        "bullets": [],
    }


def parse_skill_line(content: str) -> dict | str:
    match = SKILL_CATEGORY.match(content.strip())
    if match:
        return {"category": match.group(1).strip(), "items": match.group(2).strip()}
    return content


def parse_contact_line(content: str, contact: dict) -> None:
    match = CONTACT_FIELD.match(content.strip())
    if not match:
        return
    key = match.group(1).strip().lower()
    value = match.group(2).strip()
    mapped = CONTACT_KEYS.get(key)
    if mapped:
        contact[mapped] = value


def parse_markdown(text: str) -> dict:
    """Parse por headings alinhado ao prompt e ao template (contato tipado)."""
    data: dict = {
        "name": "",
        "contact": {
            "email": "",
            "telefone": "",
            "cidade": "",
            "linkedin": "",
            "github": "",
        },
        "summary": "",
        "experience": [],
        "education": [],
        "skills": [],
        "projects": [],
    }

    section: str | None = None
    current_item: dict | None = None
    summary_lines: list[str] = []

    def flush_item() -> None:
        nonlocal current_item
        if current_item is None:
            return
        if section == "experience":
            data["experience"].append(current_item)
        elif section == "education":
            data["education"].append(current_item)
        elif section == "projects":
            data["projects"].append(current_item)
        current_item = None

    def flush_summary() -> None:
        if summary_lines:
            data["summary"] = " ".join(summary_lines).strip()
            summary_lines.clear()

    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        if not line.strip():
            continue

        m1 = HEADING_H1.match(line)
        if m1:
            flush_item()
            flush_summary()
            data["name"] = m1.group(1).strip()
            section = None
            continue

        m2 = HEADING_H2.match(line)
        if m2:
            flush_item()
            flush_summary()
            title = m2.group(1).strip().lower()
            section = SECTION_MAP.get(title)
            continue

        m3 = HEADING_H3.match(line)
        if m3:
            flush_item()
            title = m3.group(1).strip()
            if section == "experience":
                current_item = parse_experience_heading(title)
            elif section == "education":
                current_item = parse_education_heading(title)
            elif section == "projects":
                current_item = parse_project_heading(title)
            continue

        bullet = BULLET.match(line.strip())
        if bullet:
            content = bullet.group(1).strip()
            if section == "contact":
                parse_contact_line(content, data["contact"])
            elif section == "skills":
                data["skills"].append(parse_skill_line(content))
            elif section == "summary":
                summary_lines.append(content)
            elif (
                section in ("experience", "education", "projects")
                and current_item is not None
            ):
                current_item["bullets"].append(content)
            elif section == "education":
                data["education"].append(content)
            continue

        if section == "summary":
            summary_lines.append(line.strip())
        elif (
            section in ("experience", "education", "projects")
            and current_item is not None
        ):
            current_item["bullets"].append(line.strip())

    flush_item()
    flush_summary()
    return data


def enrich_context_with_html(data: dict) -> dict:
    """Aplica conversão de **negrito** nos campos de texto (links ficam no template)."""
    data["summary"] = bold_md_to_html(data.get("summary", ""))

    for job in data.get("experience", []):
        job["bullets"] = [bold_md_to_html(b) for b in job.get("bullets", [])]

    education_out: list = []
    for edu in data.get("education", []):
        if isinstance(edu, dict):
            edu["bullets"] = [bold_md_to_html(b) for b in edu.get("bullets", [])]
            education_out.append(edu)
        else:
            education_out.append(bold_md_to_html(edu))
    data["education"] = education_out

    skills_out: list = []
    for item in data.get("skills", []):
        if isinstance(item, dict):
            skills_out.append(
                {
                    "category": item.get("category", ""),
                    "items": bold_md_to_html(item.get("items", "")),
                }
            )
        else:
            skills_out.append(bold_md_to_html(item))
    data["skills"] = skills_out

    for project in data.get("projects", []):
        project["bullets"] = [bold_md_to_html(b) for b in project.get("bullets", [])]

    return data


def has_contact(contact: dict) -> bool:
    return any(
        contact.get(key) for key in ("email", "telefone", "cidade", "linkedin", "github")
    )


VALID_PRESETS = frozenset({"compacto", "normal", "confortavel"})
DEFAULT_PRESET = "normal"
VALID_FONT_FAMILIES = frozenset({"serif", "sans"})
DEFAULT_FONT_FAMILY = "sans"
DEFAULT_LANGUAGE = "pt-BR"
VALID_LANGUAGES = frozenset({"pt-BR", "en-US"})


def normalize_preset(preset: str | None) -> str:
    value = (preset or DEFAULT_PRESET).strip().lower()
    if value not in VALID_PRESETS:
        raise ValueError(
            f"Preset inválido: {preset!r}. Use: compacto, normal ou confortavel."
        )
    return value


def normalize_font_family(font_family: str | None) -> str:
    value = (font_family or DEFAULT_FONT_FAMILY).strip().lower()
    if value not in VALID_FONT_FAMILIES:
        raise ValueError(
            f"Família de fonte inválida: {font_family!r}. Use: serif ou sans."
        )
    return value


def normalize_language(language: str | None) -> str:
    value = (language or DEFAULT_LANGUAGE).strip()
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


def detect_language_from_markdown(markdown_text: str) -> str:
    """Infere idioma pelos H2 ATS; default pt-BR."""
    for raw_line in markdown_text.splitlines():
        m2 = HEADING_H2.match(raw_line.rstrip())
        if not m2:
            continue
        title = m2.group(1).strip().lower()
        if title in _EN_SECTION_TITLES:
            return "en-US"
        if title in SECTION_MAP:
            return "pt-BR"
    return DEFAULT_LANGUAGE


def section_labels_for(language: str) -> dict[str, str]:
    return dict(SECTION_LABELS[normalize_language(language)])


def markdown_to_html(
    markdown_text: str,
    preset: str = DEFAULT_PRESET,
    font_family: str = DEFAULT_FONT_FAMILY,
    language: str | None = None,
) -> str:
    preset = normalize_preset(preset)
    font_family = normalize_font_family(font_family)
    if language:
        lang = normalize_language(language)
    else:
        lang = detect_language_from_markdown(markdown_text)
    context = enrich_context_with_html(parse_markdown(markdown_text))
    context["has_contact"] = has_contact(context.get("contact", {}))
    context["preset"] = preset
    context["font_family"] = font_family
    context["language"] = lang
    context["labels"] = section_labels_for(lang)
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATE_DIR)),
        autoescape=select_autoescape(["html", "xml"]),
    )
    return env.get_template("resume.html").render(**context)


def render_pdf_bytes(
    markdown_text: str,
    preset: str = DEFAULT_PRESET,
    font_family: str = DEFAULT_FONT_FAMILY,
    language: str | None = None,
) -> bytes:
    """Compila markdown em PDF e retorna bytes (para download/preview web)."""
    if not markdown_text.strip():
        raise ValueError("markdown está vazio.")
    html_str = markdown_to_html(
        markdown_text,
        preset=preset,
        font_family=font_family,
        language=language,
    )
    buffer = BytesIO()
    HTML(string=html_str, base_url=str(TEMPLATE_DIR)).write_pdf(buffer)
    return buffer.getvalue()


def count_pdf_pages(pdf_bytes: bytes) -> int:
    from pypdf import PdfReader

    reader = PdfReader(BytesIO(pdf_bytes))
    return len(reader.pages)


def render_pdf_to_path(
    markdown_text: str,
    out_path: Path,
    preset: str = DEFAULT_PRESET,
    font_family: str = DEFAULT_FONT_FAMILY,
    language: str | None = None,
) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(
        render_pdf_bytes(
            markdown_text,
            preset=preset,
            font_family=font_family,
            language=language,
        )
    )


def render_pdf(
    md_path: Path,
    out_path: Path,
    preset: str = DEFAULT_PRESET,
    font_family: str = DEFAULT_FONT_FAMILY,
    language: str | None = None,
) -> None:
    """Compatível com o CLI: lê arquivo MD e grava PDF."""
    text = md_path.read_text(encoding="utf-8")
    render_pdf_to_path(
        text,
        out_path,
        preset=preset,
        font_family=font_family,
        language=language,
    )
