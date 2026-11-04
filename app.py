"""Busca SUS: consulta ao histórico de atendimentos da rede pública."""
import os
import secrets
from datetime import timedelta
from functools import wraps

from dotenv import load_dotenv
from flask import Flask, abort, g, redirect, request, session, url_for

import db
import utils

load_dotenv()

app = Flask(__name__)
app.config.update(
    SECRET_KEY=os.environ.get("SECRET_KEY", "dev-troque-esta-chave"),
    DATABASE=os.path.join(app.root_path, os.environ.get("DATABASE", "busca_sus.db")),
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    PERMANENT_SESSION_LIFETIME=timedelta(hours=8),
)
db.init_app(app)

# Filtros usados nos templates
for nome in ["data_br", "hora_br", "mes_ano", "idade", "tempo_relativo", "iniciais",
             "mascarar_cpf", "mascarar_cns", "mascarar_telefone"]:
    app.jinja_env.filters[nome] = getattr(utils, nome)


# ---------------------------------------------------------------------------
# Segurança: proteção CSRF simples e controle de sessão
# ---------------------------------------------------------------------------

def csrf_token():
    if "_csrf" not in session:
        session["_csrf"] = secrets.token_hex(16)
    return session["_csrf"]


app.jinja_env.globals["csrf_token"] = csrf_token


@app.before_request
def verificar_csrf():
    if request.method == "POST":
        token = request.form.get("_csrf")
        if not token or token != session.get("_csrf"):
            abort(400)


@app.before_request
def carregar_usuario():
    g.usuario = None
    usuario_id = session.get("usuario_id")
    if usuario_id:
        g.usuario = db.get_db().execute(
            "SELECT u.*, un.nome AS unidade_nome FROM usuarios u "
            "JOIN unidades un ON un.id = u.unidade_id WHERE u.id = ?", (usuario_id,)).fetchone()


def login_obrigatorio(view):
    @wraps(view)
    def interna(*args, **kwargs):
        if g.usuario is None:
            return redirect(url_for("login", proximo=request.full_path))
        return view(*args, **kwargs)
    return interna
