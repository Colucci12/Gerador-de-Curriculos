"""Rotas Flask: auth + dashboard HTMX."""

from __future__ import annotations

from flask import (
    Blueprint,
    Response,
    flash,
    g,
    redirect,
    render_template,
    request,
    url_for,
)

from . import auth, db
from gerador.pdf_core import (
    DEFAULT_FONT_FAMILY,
    DEFAULT_LANGUAGE,
    DEFAULT_PRESET,
    count_pdf_pages,
    detect_language_from_markdown,
    normalize_font_family,
    normalize_language,
    normalize_preset,
    render_pdf_bytes,
)
from gerador.tailor_core import generate_markdown

bp = Blueprint("main", __name__)


def _selected_preset() -> str:
    try:
        return normalize_preset(request.form.get("preset") or DEFAULT_PRESET)
    except ValueError:
        return DEFAULT_PRESET


def _selected_font_family() -> str:
    try:
        return normalize_font_family(
            request.form.get("font_family") or DEFAULT_FONT_FAMILY
        )
    except ValueError:
        return DEFAULT_FONT_FAMILY


def _selected_language(markdown: str | None = None) -> str:
    raw = (request.form.get("language") or "").strip()
    if raw:
        try:
            return normalize_language(raw)
        except ValueError:
            pass
    if markdown:
        return detect_language_from_markdown(markdown)
    return DEFAULT_LANGUAGE


@bp.route("/register", methods=["GET", "POST"])
def register():
    if g.user:
        return redirect(url_for("main.dashboard"))

    if request.method == "POST":
        email = (request.form.get("email") or "").strip()
        password = request.form.get("password") or ""
        api_key = (request.form.get("gemini_api_key") or "").strip()

        if not email or not password or not api_key:
            flash("Preencha e-mail, senha e chave Gemini.", "error")
            return render_template("register.html"), 400
        if len(password) < 6:
            flash("A senha deve ter pelo menos 6 caracteres.", "error")
            return render_template("register.html"), 400
        if db.get_user_by_email(email):
            flash("Este e-mail já está cadastrado.", "error")
            return render_template("register.html"), 400

        try:
            encrypted = auth.encrypt_api_key(api_key)
            user_id = db.create_user(email, auth.hash_password(password), encrypted)
            auth.login_user(user_id)
            flash("Conta criada. Preencha seu perfil mestre.", "success")
            return redirect(url_for("main.dashboard"))
        except Exception as exc:
            flash(f"Erro ao cadastrar: {exc}", "error")
            return render_template("register.html"), 500

    return render_template("register.html")


@bp.route("/login", methods=["GET", "POST"])
def login():
    if g.user:
        return redirect(url_for("main.dashboard"))

    if request.method == "POST":
        email = (request.form.get("email") or "").strip()
        password = request.form.get("password") or ""
        user = db.get_user_by_email(email)
        if not user or not auth.verify_password(password, user["password_hash"]):
            flash("E-mail ou senha inválidos.", "error")
            return render_template("login.html"), 401
        auth.login_user(user["id"])
        return redirect(url_for("main.dashboard"))

    return render_template("login.html")


@bp.route("/logout", methods=["POST", "GET"])
def logout():
    auth.logout_user()
    flash("Sessão encerrada.", "success")
    return redirect(url_for("main.login"))


@bp.route("/")
@auth.login_required
def dashboard():
    profile = db.get_profile(g.user["id"])
    latest = db.get_latest_job_resume(g.user["id"])
    tab = request.args.get("tab", "profile")
    step = request.args.get("step", "input")
    if step not in ("input", "review"):
        step = "input"
    # Review só faz sentido com MD existente
    if tab == "generator" and step == "review" and not (latest and latest["generated_md"]):
        step = "input"

    return render_template(
        "dashboard.html",
        master_profile=profile["master_profile_md"] if profile else "",
        job_description=latest["job_description"] if latest else "",
        generated_md=latest["generated_md"] if latest else "",
        preset=DEFAULT_PRESET,
        font_family=DEFAULT_FONT_FAMILY,
        language=(
            detect_language_from_markdown(latest["generated_md"])
            if latest and latest["generated_md"]
            else DEFAULT_LANGUAGE
        ),
        active_tab=tab if tab in ("profile", "generator") else "profile",
        generator_step=step,
    )


@bp.route("/profile", methods=["POST"])
@auth.login_required
def save_profile():
    master = request.form.get("master_profile_md") or ""
    db.save_profile(g.user["id"], master)
    if request.headers.get("HX-Request"):
        return render_template("partials/profile_saved.html")
    flash("Perfil salvo.", "success")
    return redirect(url_for("main.dashboard", tab="profile"))


@bp.route("/generate", methods=["POST"])
@auth.login_required
def generate():
    job_description = (request.form.get("job_description") or "").strip()
    language = _selected_language()
    profile = db.get_profile(g.user["id"])
    master = (profile["master_profile_md"] if profile else "").strip()

    if not master:
        return (
            render_template(
                "partials/generator_input.html",
                error="Salve seu perfil mestre na aba Perfil antes de gerar.",
                job_description=job_description,
                language=language,
            ),
            400,
        )
    if not job_description:
        return (
            render_template(
                "partials/generator_input.html",
                error="Cole a descrição da vaga.",
                job_description="",
                language=language,
            ),
            400,
        )

    try:
        api_key = auth.decrypt_api_key(g.user["gemini_api_key_encrypted"])
        generated_md = generate_markdown(
            master, job_description, api_key, language=language
        )
        db.save_job_resume(g.user["id"], job_description, generated_md)
        response = render_template(
            "partials/generator_review.html",
            job_description=job_description,
            generated_md=generated_md,
            preset=DEFAULT_PRESET,
            font_family=DEFAULT_FONT_FAMILY,
            language=language,
        )
        # Atualiza a URL do browser para o passo review (HTMX)
        headers = {"HX-Push-Url": url_for("main.dashboard", tab="generator", step="review")}
        return response, 200, headers
    except Exception as exc:
        return (
            render_template(
                "partials/generator_input.html",
                error=f"Falha ao gerar com a IA: {exc}",
                job_description=job_description,
                language=language,
            ),
            500,
        )


def _pdf_response(
    markdown: str, preset: str, font_family: str, language: str, *, inline: bool
) -> Response:
    pdf_bytes = render_pdf_bytes(
        markdown, preset=preset, font_family=font_family, language=language
    )
    pages = count_pdf_pages(pdf_bytes)
    disposition = "inline" if inline else "attachment; filename=curriculo.pdf"
    return Response(
        pdf_bytes,
        mimetype="application/pdf",
        headers={
            "Content-Disposition": disposition,
            "X-Page-Count": str(pages),
            "X-Preset": preset,
            "X-Font-Family": font_family,
            "X-Language": language,
            "Cache-Control": "no-store",
        },
    )


@bp.route("/preview", methods=["POST"])
@auth.login_required
def preview_pdf():
    markdown = (request.form.get("generated_md") or "").strip()
    if not markdown:
        return Response("Markdown vazio.", status=400, mimetype="text/plain")

    preset = _selected_preset()
    font_family = _selected_font_family()
    language = _selected_language(markdown)
    try:
        return _pdf_response(
            markdown, preset, font_family, language, inline=True
        )
    except Exception as exc:
        return Response(f"Erro ao gerar preview: {exc}", status=500, mimetype="text/plain")


@bp.route("/pdf", methods=["POST"])
@auth.login_required
def download_pdf():
    markdown = (request.form.get("generated_md") or "").strip()
    if not markdown:
        flash("Não há markdown para gerar o PDF. Gere ou cole o conteúdo antes.", "error")
        return redirect(url_for("main.dashboard", tab="generator", step="review"))

    preset = _selected_preset()
    font_family = _selected_font_family()
    language = _selected_language(markdown)
    try:
        return _pdf_response(
            markdown, preset, font_family, language, inline=False
        )
    except Exception as exc:
        flash(f"Erro ao gerar PDF: {exc}", "error")
        return redirect(url_for("main.dashboard", tab="generator", step="review"))
