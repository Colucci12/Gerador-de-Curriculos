# Resume Tailor — Gerador de Currículos

Interface web (Flask) para adaptar seu perfil a uma vaga via Gemini e baixar o PDF. A lógica de IA/PDF é a mesma dos scripts CLI, chamada como funções Python dentro do container.

## Setup

1. Copie o `.env`:
   ```bash
   cp .env.example .env
   ```
2. Preencha no `.env`:
   - `SECRET_KEY` — string longa aleatória (sessão)
   - `ENCRYPTION_KEY` — gere com:
     ```bash
     docker run --rm python:3.12-slim python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
     ```
     (ou após o build: `docker compose run --rm web python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`)
   - `GOOGLE_API_KEY` — opcional, só para o CLI

3. Build e suba a web:
   ```bash
   docker compose build
   docker compose up
   ```
   Abra http://localhost:8000

4. Cadastre-se com e-mail, senha e **sua** chave Gemini ([AI Studio](https://aistudio.google.com/apikey)).

## Uso (web)

1. Aba **Perfil mestre** — cole/salve seu markdown de competências.
2. Aba **Gerador** — cole a vaga → **Gerar com IA** → revise o MD → **Baixar PDF**.
3. O banco (`data/app.db`) guarda perfil e os MDs gerados. O PDF só é baixado (não fica no DB).

## CLI opcional (mesmas funções)

```bash
docker compose run --rm web python gerador/script_tailor.py input/exemplo_vaga.txt
docker compose run --rm web python gerador/script_pdf.py output/job_profile.md --out output/exemplo.pdf
```

## Estrutura

- `web/` — Flask, auth, SQLite, templates HTMX + Pico.css
- `gerador/tailor_core.py` / `pdf_core.py` — lógica reutilizada pela web e pelo CLI
- `gerador/prompt_template_pt-BR.txt` / `prompt_template_en-US.txt` / `template/` — prompts por idioma e layout do PDF
- `data/` — `app.db` (volume Docker)
