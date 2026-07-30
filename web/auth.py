"""Auth: bcrypt para senhas, Fernet para chave Gemini, sessão Flask."""

from __future__ import annotations

import os
from functools import wraps

from cryptography.fernet import Fernet, InvalidToken
from flask import flash, g, redirect, session, url_for
from passlib.hash import bcrypt

from . import db


def _fernet() -> Fernet:
    key = os.environ.get("ENCRYPTION_KEY", "").strip()
    if not key:
        raise RuntimeError(
            "ENCRYPTION_KEY não definida no .env. "
            'Gere com: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"'
        )
    return Fernet(key.encode() if isinstance(key, str) else key)


def hash_password(password: str) -> str:
    return bcrypt.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.verify(password, password_hash)
    except (ValueError, TypeError):
        return False


def encrypt_api_key(api_key: str) -> str:
    return _fernet().encrypt(api_key.encode("utf-8")).decode("utf-8")


def decrypt_api_key(token: str) -> str:
    try:
        return _fernet().decrypt(token.encode("utf-8")).decode("utf-8")
    except InvalidToken as exc:
        raise RuntimeError("Não foi possível descriptografar a chave Gemini.") from exc


def login_user(user_id: int) -> None:
    session.clear()
    session["user_id"] = user_id
    session.permanent = True


def logout_user() -> None:
    session.clear()


def current_user_id() -> int | None:
    return session.get("user_id")


def load_current_user() -> None:
    user_id = current_user_id()
    g.user = db.get_user_by_id(user_id) if user_id else None


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if g.get("user") is None:
            flash("Faça login para continuar.", "error")
            return redirect(url_for("main.login"))
        return view(*args, **kwargs)

    return wrapped
