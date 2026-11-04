"""Busca SUS: consulta ao histórico de atendimentos da rede pública."""
import os
import secrets
from collections import Counter
from datetime import timedelta
from functools import wraps

from dotenv import load_dotenv
from flask import Flask, abort, g, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash

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


# ---------------------------------------------------------------------------
# Autenticação
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    return redirect(url_for("busca") if g.usuario else url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if g.usuario:
        return redirect(url_for("busca"))
    erro = None
    matricula = ""
    if request.method == "POST":
        matricula = request.form.get("matricula", "").strip()
        senha = request.form.get("senha", "")
        usuario = db.get_db().execute(
            "SELECT * FROM usuarios WHERE matricula = ?", (matricula,)).fetchone()
        if usuario and check_password_hash(usuario["senha_hash"], senha):
            session.clear()
            session.permanent = True
            session["usuario_id"] = usuario["id"]
            proximo = request.args.get("proximo", "")
            # Só aceita redirecionar para caminhos internos
            if not proximo.startswith("/") or proximo.startswith("//"):
                proximo = url_for("busca")
            return redirect(proximo)
        erro = "Matrícula ou senha incorretas. Confira os dados e tente de novo."
    return render_template("login.html", erro=erro, matricula=matricula)


@app.route("/sair", methods=["POST"])
def sair():
    session.clear()
    return redirect(url_for("login"))


# ---------------------------------------------------------------------------
# Busca de pacientes
# ---------------------------------------------------------------------------

TIPOS_BUSCA = ("todos", "cpf", "cns", "nome")


def _like(palavra):
    """Monta o padrão do LIKE escapando os caracteres especiais."""
    palavra = palavra.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{palavra}%"


def buscar_pacientes(termo, tipo, nascimento="", mae="", municipio=""):
    """Retorna (pacientes, mensagem_de_erro)."""
    digitos = utils.so_digitos(termo)
    so_numeros = termo.replace(".", "").replace("-", "").replace(" ", "").isdigit()

    if tipo == "todos":
        if so_numeros and len(digitos) == 11:
            tipo = "cpf"
        elif so_numeros and len(digitos) == 15:
            tipo = "cns"
        elif so_numeros:
            return None, "O CPF tem 11 dígitos e o Cartão SUS (CNS) tem 15. Confira o número digitado."
        else:
            tipo = "nome"

    condicoes, params = [], []
    if tipo == "cpf":
        if len(digitos) != 11:
            return None, "O CPF precisa ter 11 dígitos."
        condicoes.append("p.cpf = ?")
        params.append(digitos)
    elif tipo == "cns":
        if len(digitos) != 15:
            return None, "O Cartão SUS (CNS) precisa ter 15 dígitos."
        condicoes.append("p.cns = ?")
        params.append(digitos)
    else:
        palavras = [p for p in utils.normalizar(termo).split() if len(p) > 1]
        if not palavras:
            return None, "Digite o nome do paciente para buscar."
        for palavra in palavras:
            condicoes.append("p.nome_busca LIKE ? ESCAPE '\\'")
            params.append(_like(palavra))

    if nascimento:
        condicoes.append("p.data_nascimento = ?")
        params.append(nascimento)
    for palavra in utils.normalizar(mae).split():
        condicoes.append("p.mae_busca LIKE ? ESCAPE '\\'")
        params.append(_like(palavra))
    if municipio:
        condicoes.append("p.municipio = ?")
        params.append(municipio)

    sql = (
        "SELECT p.*, (SELECT MAX(a.data_hora) FROM atendimentos a WHERE a.paciente_id = p.id) AS ultimo_atendimento "
        f"FROM pacientes p WHERE {' AND '.join(condicoes)} "
        "ORDER BY ultimo_atendimento IS NULL, ultimo_atendimento DESC, p.nome LIMIT 50"
    )
    return db.get_db().execute(sql, params).fetchall(), None


def contexto_busca(**extra):
    municipios = [r["municipio"] for r in db.get_db().execute(
        "SELECT DISTINCT municipio FROM pacientes ORDER BY municipio")]
    contexto = {"municipios": municipios, "recentes": buscas_recentes(),
                "termo": "", "tipo": request.args.get("tipo", "todos"),
                "nascimento": "", "mae": "", "municipio": "", "erro": None}
    contexto.update(extra)
    return contexto


def buscas_recentes():
    return []


@app.route("/busca")
@login_obrigatorio
def busca():
    return render_template("busca.html", **contexto_busca())


@app.route("/resultados")
@login_obrigatorio
def resultados():
    termo = request.args.get("q", "").strip()
    tipo = request.args.get("tipo", "todos")
    if tipo not in TIPOS_BUSCA:
        tipo = "todos"
    filtros = {
        "nascimento": request.args.get("nascimento", "").strip(),
        "mae": request.args.get("mae", "").strip(),
        "municipio": request.args.get("municipio", "").strip(),
    }
    if not termo:
        return redirect(url_for("busca"))

    pacientes, erro = buscar_pacientes(termo, tipo, **filtros)
    if erro:
        return render_template("busca.html", **contexto_busca(erro=erro, termo=termo, tipo=tipo, **filtros))

    repeticoes = Counter(p["nome_busca"] for p in pacientes)
    homonimos = any(n > 1 for n in repeticoes.values())
    return render_template("resultados.html", pacientes=pacientes, termo=termo, homonimos=homonimos)
