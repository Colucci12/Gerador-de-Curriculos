# Gerador de Currículos

Adapta seu perfil (`master_profile.md`) a uma vaga (arquivo `.txt`) via Gemini e gera um PDF com HTML/CSS. Tudo roda no Docker — não precisa instalar Python localmente.

## Setup

1. Copie a chave da API:
   ```bash
   cp .env.example .env
   ```
   Edite `.env` e coloque sua `GOOGLE_API_KEY` ([Google AI Studio](https://aistudio.google.com/apikey)).

2. Preencha `gerador/master_profile.md` com suas experiências reais.

3. Build da imagem:
   ```bash
   docker compose build
   ```

## Uso

1. Coloque o texto da vaga em `input/`, por exemplo `input/vaga_empresa_x.txt`.

2. Gere o markdown adaptado:
   ```bash
   docker compose run --rm app python gerador/script_tailor.py input/vaga_empresa_x.txt
   ```
   Saída: `output/job_profile.md`

3. Gere o PDF:
   ```bash
   docker compose run --rm app python gerador/script_pdf.py output/job_profile.md --out output/vaga_empresa_x.pdf
   ```

Teste rápido com o exemplo incluso:
```bash
docker compose run --rm app python gerador/script_tailor.py input/exemplo_vaga.txt
docker compose run --rm app python gerador/script_pdf.py output/job_profile.md --out output/exemplo.pdf
```

## Estrutura

- `gerador/master_profile.md` — seu banco de competências
- `gerador/prompt_template.txt` — instruções da IA
- `gerador/script_tailor.py` — vaga + master → `job_profile.md`
- `gerador/script_pdf.py` — markdown → PDF
- `gerador/template/` — HTML/CSS do currículo (substitua pelo seu layout quando quiser)
- `input/` — textos de vaga
- `output/` — markdown e PDFs gerados
