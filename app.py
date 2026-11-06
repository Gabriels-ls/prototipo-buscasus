"""Busca SUS: consulta ao histórico de atendimentos da rede pública."""
import os
import secrets
from collections import Counter
from datetime import datetime, timedelta
from itertools import groupby
from functools import wraps

from dotenv import load_dotenv
from flask import Flask, abort, g, redirect, render_template, request, session, url_for
from werkzeug.middleware.proxy_fix import ProxyFix
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
    # Em produção (HTTPS) o cookie de sessão só trafega por conexão segura
    SESSION_COOKIE_SECURE=os.environ.get("COOKIE_SEGURO") == "1",
)
# Em serviços como o Render o app fica atrás de um proxy que cuida do HTTPS
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)
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
            "SELECT u.*, un.nome AS unidade_nome, un.municipio AS unidade_municipio FROM usuarios u "
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


def buscas_recentes(limite=5):
    """Últimos pacientes consultados pelo usuário logado."""
    return db.get_db().execute(
        "SELECT p.id, p.nome, p.cpf, p.data_nascimento, MAX(ac.data_hora) AS ultimo_acesso "
        "FROM acessos ac JOIN pacientes p ON p.id = ac.paciente_id "
        "WHERE ac.usuario_id = ? GROUP BY p.id ORDER BY ultimo_acesso DESC LIMIT ?",
        (g.usuario["id"], limite)).fetchall()


def registrar_acesso(paciente_id, acao, atendimento_id=None):
    """Grava quem consultou o prontuário e quando (trilha de auditoria da LGPD)."""
    con = db.get_db()
    con.execute(
        "INSERT INTO acessos (usuario_id, paciente_id, atendimento_id, acao, data_hora) VALUES (?, ?, ?, ?, ?)",
        (g.usuario["id"], paciente_id, atendimento_id, acao, datetime.now().isoformat(timespec="seconds")))
    con.commit()


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


# ---------------------------------------------------------------------------
# Histórico do paciente
# ---------------------------------------------------------------------------

CATEGORIAS = {
    "todos": ("Todos", None),
    "consultas": ("Consultas", ("Consulta médica", "Consulta de enfermagem")),
    "vacinas": ("Vacinas", ("Vacinação",)),
    "exames": ("Exames", ("Exame laboratorial",)),
    "urgencia": ("Urgência", ("Urgência",)),
    "odontologia": ("Odontologia", ("Consulta odontológica",)),
    "internacoes": ("Internações", ("Internação",)),
}
LIMITE_INICIAL = 10


def obter_paciente(paciente_id):
    paciente = db.get_db().execute(
        "SELECT p.*, u.nome AS unidade_referencia FROM pacientes p "
        "LEFT JOIN unidades u ON u.id = p.unidade_referencia_id WHERE p.id = ?", (paciente_id,)).fetchone()
    if paciente is None:
        abort(404)
    return paciente


def link_voltar(padrao_url, padrao_rotulo, origem, rotulo_origem):
    """Volta para a página anterior se ela for do próprio site e do tipo esperado."""
    anterior = request.referrer or ""
    if anterior.startswith(request.host_url) and origem in anterior:
        return anterior, rotulo_origem
    return padrao_url, padrao_rotulo


def fontes_atrasadas():
    limite = (datetime.now() - timedelta(hours=24)).isoformat()
    return db.get_db().execute(
        "SELECT nome, municipio, ultima_sincronizacao FROM unidades "
        "WHERE ultima_sincronizacao < ? ORDER BY ultima_sincronizacao", (limite,)).fetchall()


@app.route("/pacientes/<int:paciente_id>")
@login_obrigatorio
def historico(paciente_id):
    con = db.get_db()
    paciente = obter_paciente(paciente_id)
    alergias = con.execute("SELECT * FROM alergias WHERE paciente_id = ?", (paciente_id,)).fetchall()
    condicoes = con.execute("SELECT * FROM condicoes WHERE paciente_id = ?", (paciente_id,)).fetchall()

    categoria = request.args.get("categoria", "todos")
    if categoria not in CATEGORIAS:
        categoria = "todos"
    mostrar_todos = request.args.get("todos") == "1"

    filtro, params = "", [paciente_id]
    tipos = CATEGORIAS[categoria][1]
    if tipos:
        filtro = f"AND a.tipo IN ({','.join('?' * len(tipos))})"
        params.extend(tipos)

    atendimentos = con.execute(f"""
        SELECT a.id, a.data_hora, a.tipo, a.resumo, a.cid_codigo,
               COALESCE(a.cid_codigo,
                        (SELECT i.vacina FROM imunizacoes i WHERE i.atendimento_id = a.id LIMIT 1),
                        (SELECT e.nome FROM exames e WHERE e.atendimento_id = a.id LIMIT 1)) AS etiqueta,
               u.nome AS unidade, u.municipio AS unidade_municipio, u.sistema_origem, u.ultima_sincronizacao,
               pr.nome AS profissional, pr.especialidade
        FROM atendimentos a
        JOIN unidades u ON u.id = a.unidade_id
        JOIN profissionais pr ON pr.id = a.profissional_id
        WHERE a.paciente_id = ? {filtro}
        ORDER BY a.data_hora DESC""", params).fetchall()

    visiveis = atendimentos if mostrar_todos else atendimentos[:LIMITE_INICIAL]
    grupos = [(ano, list(itens)) for ano, itens in groupby(visiveis, key=lambda a: a["data_hora"][:4])]
    totais = con.execute(
        "SELECT COUNT(*) AS total, MIN(data_hora) AS primeiro, MAX(data_hora) AS ultimo "
        "FROM atendimentos WHERE paciente_id = ?", (paciente_id,)).fetchone()

    registrar_acesso(paciente_id, "historico")
    voltar_url, voltar_rotulo = link_voltar(url_for("busca"), "← Voltar para a busca",
                                            "/resultados", "← Voltar aos resultados")
    return render_template(
        "historico.html", paciente=paciente, alergias=alergias, condicoes=condicoes,
        grupos=grupos, totais=totais, categorias=CATEGORIAS, categoria=categoria,
        ocultos=len(atendimentos) - len(visiveis), fontes_atrasadas=fontes_atrasadas(),
        voltar_url=voltar_url, voltar_rotulo=voltar_rotulo)


# ---------------------------------------------------------------------------
# Detalhe do atendimento
# ---------------------------------------------------------------------------

@app.route("/atendimentos/<int:atendimento_id>")
@login_obrigatorio
def atendimento(atendimento_id):
    con = db.get_db()
    at = con.execute("""
        SELECT a.*, u.nome AS unidade, u.municipio AS unidade_municipio, u.cnes,
               pr.nome AS profissional, pr.especialidade, pr.conselho, pr.registro
        FROM atendimentos a
        JOIN unidades u ON u.id = a.unidade_id
        JOIN profissionais pr ON pr.id = a.profissional_id
        WHERE a.id = ?""", (atendimento_id,)).fetchone()
    if at is None:
        abort(404)
    paciente = obter_paciente(at["paciente_id"])
    registrar_acesso(paciente["id"], "atendimento", atendimento_id)
    return render_template(
        "atendimento.html", at=at, paciente=paciente,
        prescricoes=con.execute("SELECT * FROM prescricoes WHERE atendimento_id = ?", (atendimento_id,)).fetchall(),
        exames=con.execute("SELECT * FROM exames WHERE atendimento_id = ?", (atendimento_id,)).fetchall(),
        imunizacoes=con.execute("SELECT * FROM imunizacoes WHERE atendimento_id = ?", (atendimento_id,)).fetchall(),
        alergias=con.execute("SELECT * FROM alergias WHERE paciente_id = ?", (paciente["id"],)).fetchall())


@app.errorhandler(404)
def nao_encontrado(_erro):
    return render_template("erro.html", titulo="Página não encontrada",
                           mensagem="O endereço pode ter sido digitado errado ou o registro não existe mais."), 404
