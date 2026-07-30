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
from gerador.pdf_core import render_pdf_bytes
from gerador.tailor_core import generate_markdown

bp = Blueprint("main", __name__)


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
    return render_template(
        "dashboard.html",
        master_profile=profile["master_profile_md"] if profile else "",
        job_description=latest["job_description"] if latest else "",
        generated_md=latest["generated_md"] if latest else "",
        active_tab=tab if tab in ("profile", "generator") else "profile",
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
    profile = db.get_profile(g.user["id"])
    master = (profile["master_profile_md"] if profile else "").strip()

    if not master:
        return (
            render_template(
                "partials/generate_result.html",
                error="Salve seu perfil mestre na aba Perfil antes de gerar.",
                job_description=job_description,
                generated_md="",
            ),
            400,
        )
    if not job_description:
        return (
            render_template(
                "partials/generate_result.html",
                error="Cole a descrição da vaga.",
                job_description="",
                generated_md="",
            ),
            400,
        )

    try:
        api_key = auth.decrypt_api_key(g.user["gemini_api_key_encrypted"])
        generated_md = generate_markdown(master, job_description, api_key)
        db.save_job_resume(g.user["id"], job_description, generated_md)
        return render_template(
            "partials/generate_result.html",
            error=None,
            job_description=job_description,
            generated_md=generated_md,
        )
    except Exception as exc:
        return (
            render_template(
                "partials/generate_result.html",
                error=f"Falha ao gerar com a IA: {exc}",
                job_description=job_description,
                generated_md="",
            ),
            500,
        )


@bp.route("/pdf", methods=["POST"])
@auth.login_required
def download_pdf():
    markdown = (request.form.get("generated_md") or "").strip()
    if not markdown:
        flash("Não há markdown para gerar o PDF. Gere ou cole o conteúdo antes.", "error")
        return redirect(url_for("main.dashboard", tab="generator"))

    try:
        pdf_bytes = render_pdf_bytes(markdown)
    except Exception as exc:
        flash(f"Erro ao gerar PDF: {exc}", "error")
        return redirect(url_for("main.dashboard", tab="generator"))

    return Response(
        pdf_bytes,
        mimetype="application/pdf",
        headers={"Content-Disposition": "attachment; filename=curriculo.pdf"},
    )
