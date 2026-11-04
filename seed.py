"""Cria o banco de dados e preenche com dados FICTÍCIOS para desenvolvimento.

Uso:
    python seed.py

Nenhum dado aqui pertence a pessoas reais. Nomes, CPFs, CNS, telefones,
registros profissionais e códigos CNES são gerados aleatoriamente.
"""
import os
import random
import sqlite3
from datetime import date, datetime, timedelta

from dotenv import load_dotenv
from werkzeug.security import generate_password_hash

from utils import normalizar

load_dotenv()
BASE = os.path.dirname(os.path.abspath(__file__))
CAMINHO_DB = os.environ.get("DATABASE", os.path.join(BASE, "busca_sus.db"))
if not os.path.isabs(CAMINHO_DB):
    CAMINHO_DB = os.path.join(BASE, CAMINHO_DB)

random.seed(42)
AGORA = datetime.now().replace(second=0, microsecond=0)
INICIO_HISTORICO = datetime(2019, 1, 1)

# ---------------------------------------------------------------------------
# Geradores de documentos fictícios
# ---------------------------------------------------------------------------

def gerar_cpf():
    """CPF com dígitos verificadores válidos, porém aleatório."""
    base = [random.randint(0, 9) for _ in range(9)]
    for _ in range(2):
        peso = len(base) + 1
        soma = sum(d * (peso - i) for i, d in enumerate(base))
        resto = (soma * 10) % 11
        base.append(0 if resto == 10 else resto)
    return "".join(map(str, base))


def gerar_cns():
    return random.choice("78") + "".join(str(random.randint(0, 9)) for _ in range(14))


def gerar_telefone():
    return "47" + "9" + "".join(str(random.randint(0, 9)) for _ in range(8))


def gerar_cnes():
    return "".join(str(random.randint(0, 9)) for _ in range(7))


def id_origem(prefixo):
    return f"{prefixo}-{random.getrandbits(32):08X}"


def data_aleatoria(inicio, fim):
    segundos = int((fim - inicio).total_seconds())
    d = inicio + timedelta(seconds=random.randint(0, segundos))
    # atendimentos entre 7h e 19h
    return d.replace(hour=random.randint(7, 18), minute=random.choice([0, 10, 15, 20, 30, 40, 45, 50]))


# ---------------------------------------------------------------------------
# Dados de referência
# ---------------------------------------------------------------------------

MUNICIPIOS = ["Itajaí", "Balneário Camboriú", "Navegantes", "Camboriú", "Itapema",
              "Porto Belo", "Bombinhas", "Penha", "Balneário Piçarras", "Ilhota", "Luiz Alves"]

UNIDADES = [
    # nome, tipo, município, sistema de origem, horas desde a última sincronização
    ("UBS Centro", "UBS", "Itajaí", "e-SUS APS (PEC)", 2),
    ("UBS São Vicente", "UBS", "Itajaí", "e-SUS APS (PEC)", 1),
    ("UBS Nações", "UBS", "Balneário Camboriú", "e-SUS APS (PEC)", 3),
    ("UBS Gravatá", "UBS", "Navegantes", "e-SUS APS (PEC)", 2),
    ("UBS Areias", "UBS", "Camboriú", "e-SUS APS (PEC)", 5),
    ("UBS Meia Praia", "UBS", "Itapema", "e-SUS APS (PEC)", 4),
    ("UBS Centro", "UBS", "Porto Belo", "e-SUS APS (PEC)", 6),
    ("UBS Armação", "UBS", "Penha", "e-SUS APS (PEC)", 2),
    ("UPA 24h Itajaí", "UPA", "Itajaí", "Sistema da UPA", 6),
    ("UPA 24h Balneário Camboriú", "UPA", "Balneário Camboriú", "Sistema da UPA", 3),
    ("UPA 24h Navegantes", "UPA", "Navegantes", "Sistema da UPA", 8),
    ("Hospital Municipal", "Hospital", "Camboriú", "Sistema hospitalar", 72),  # fonte atrasada
    ("Hospital Regional", "Hospital", "Itajaí", "Sistema hospitalar", 10),
    ("Laboratório Municipal", "Laboratório", "Itajaí", "Sistema do laboratório", 20),
    ("Laboratório Municipal", "Laboratório", "Balneário Camboriú", "Sistema do laboratório", 12),
]

PROFISSIONAIS = [
    # nome, especialidade, conselho
    ("Dr. João Pereira", "Clínico geral", "CRM-SC"),
    ("Dra. Fernanda Lopes", "Médica emergencista", "CRM-SC"),
    ("Dr. Ricardo Alves", "Médico de família e comunidade", "CRM-SC"),
    ("Dra. Camila Rocha", "Médica de família e comunidade", "CRM-SC"),
    ("Dr. Marcelo Teixeira", "Clínico geral", "CRM-SC"),
    ("Dra. Patrícia Nunes", "Ginecologista e obstetra", "CRM-SC"),
    ("Dr. Henrique Duarte", "Cirurgião geral", "CRM-SC"),
    ("Dra. Juliana Castro", "Pediatra", "CRM-SC"),
    ("Enf. Carla Mendes", "Enfermeira", "COREN-SC"),
    ("Enf. Maria Souza", "Enfermeira", "COREN-SC"),
    ("Enf. Bruno Farias", "Enfermeiro", "COREN-SC"),
    ("Enf. Aline Barbosa", "Enfermeira", "COREN-SC"),
    ("Dr. Rafael Costa", "Cirurgião-dentista", "CRO-SC"),
    ("Dra. Letícia Moraes", "Cirurgiã-dentista", "CRO-SC"),
    ("Dra. Sílvia Ramos", "Farmacêutica-bioquímica", "CRF-SC"),
]

NOMES_F = ["Ana", "Maria", "Juliana", "Fernanda", "Patrícia", "Camila", "Aline", "Bruna", "Larissa",
           "Gabriela", "Mariana", "Letícia", "Beatriz", "Amanda", "Luana", "Rosângela", "Sandra",
           "Helena", "Vitória", "Isabela", "Clara", "Lúcia", "Tereza", "Jéssica", "Daniela"]
NOMES_M = ["João", "José", "Pedro", "Lucas", "Gabriel", "Rafael", "Matheus", "Bruno", "Carlos",
           "Eduardo", "Felipe", "Gustavo", "Leonardo", "Rodrigo", "Thiago", "Marcos", "Paulo",
           "André", "Vinícius", "Diego", "Antônio", "Francisco", "Daniel", "Samuel", "Miguel"]
SOBRENOMES = ["Silva", "Santos", "Oliveira", "Souza", "Pereira", "Lima", "Costa", "Ferreira",
              "Rodrigues", "Almeida", "Nascimento", "Carvalho", "Gomes", "Martins", "Ribeiro",
              "Araújo", "Schmitt", "Kraus", "Vieira", "Correia", "Machado", "Rocha", "Barbosa", "Cardoso"]
RACAS = ["Branca", "Branca", "Branca", "Parda", "Parda", "Preta", "Amarela", "Indígena"]

ALERGIAS = [("Dipirona", "Urticária e inchaço", "Moderada"),
            ("Penicilina", "Erupção cutânea", "Grave"),
            ("Ácido acetilsalicílico", "Broncoespasmo", "Grave"),
            ("Ibuprofeno", "Coceira", "Leve"),
            ("Látex", "Dermatite de contato", "Leve"),
            ("Frutos do mar", "Inchaço nos lábios", "Moderada")]

CONDICOES = [("Hipertensão arterial", "I10"), ("Diabetes tipo 2", "E11"), ("Asma", "J45"),
             ("Hipotireoidismo", "E03.9"), ("Depressão", "F32.9"), ("Obesidade", "E66.9")]

# Modelos de atendimento: tipo -> lista de casos
CONSULTAS = [
    {"cid": ("J06.9", "Infecção aguda das vias aéreas superiores, não especificada"),
     "resumo": "Febre e dor de garganta. Prescrito antitérmico e repouso.",
     "anamnese": "Paciente relata febre, dor de garganta e coriza há 3 dias. Nega falta de ar.",
     "conduta": "Repouso e hidratação. Retornar se a febre persistir por mais de 5 dias ou se surgir falta de ar.",
     "rx": [("Paracetamol 750 mg", "1 comprimido via oral a cada 6 horas, se febre ou dor, por até 3 dias")]},
    {"cid": ("I10", "Hipertensão essencial (primária)"),
     "resumo": "Acompanhamento de hipertensão. Pressão controlada, mantida medicação.",
     "anamnese": "Retorno para acompanhamento de hipertensão. Refere boa adesão ao tratamento.",
     "conduta": "Manter medicação, reduzir sal e praticar atividade física. Retorno em 3 meses.",
     "rx": [("Losartana 50 mg", "1 comprimido via oral pela manhã, uso contínuo")]},
    {"cid": ("E11.9", "Diabetes mellitus tipo 2 sem complicações"),
     "resumo": "Acompanhamento de diabetes. Solicitados exames de controle.",
     "anamnese": "Paciente diabético em acompanhamento. Refere seguir dieta parcialmente.",
     "conduta": "Ajuste de dieta, caminhada diária e exames de controle em 30 dias.",
     "rx": [("Metformina 850 mg", "1 comprimido via oral após almoço e jantar, uso contínuo")]},
    {"cid": ("M54.5", "Dor lombar baixa"),
     "resumo": "Dor lombar após esforço. Prescrito analgésico e orientações posturais.",
     "anamnese": "Dor na região lombar há 5 dias, iniciada após carregar peso. Sem irradiação.",
     "conduta": "Compressas mornas, evitar esforço e alongamentos. Retornar se piorar.",
     "rx": [("Paracetamol 750 mg", "1 comprimido via oral a cada 8 horas, se dor, por 5 dias"),
            ("Ciclobenzaprina 5 mg", "1 comprimido via oral à noite, por 5 dias")]},
    {"cid": ("N39.0", "Infecção do trato urinário de localização não especificada"),
     "resumo": "Sintomas urinários. Iniciado antibiótico e solicitada urocultura.",
     "anamnese": "Ardência ao urinar e aumento da frequência urinária há 2 dias. Sem febre.",
     "conduta": "Aumentar ingestão de água. Retornar com resultado da urocultura.",
     "rx": [("Cefalexina 500 mg", "1 cápsula via oral a cada 6 horas, por 7 dias")]},
    {"cid": ("F41.1", "Ansiedade generalizada"),
     "resumo": "Queixa de ansiedade e insônia. Encaminhada ao psicólogo da rede.",
     "anamnese": "Relata nervosismo frequente, dificuldade para dormir e preocupação excessiva há meses.",
     "conduta": "Encaminhamento para psicologia no CAPS. Retorno em 30 dias.",
     "rx": []},
    {"cid": ("K29.7", "Gastrite não especificada"),
     "resumo": "Dor epigástrica. Prescrito protetor gástrico e orientação alimentar.",
     "anamnese": "Queimação no estômago após as refeições há 2 semanas.",
     "conduta": "Evitar café, frituras e álcool. Retorno se não houver melhora em 30 dias.",
     "rx": [("Omeprazol 20 mg", "1 cápsula em jejum, por 30 dias")]},
]

ENFERMAGEM = [
    {"cid": ("Z00.0", "Exame médico geral"), "resumo": "Aferição de pressão e glicemia capilar. Valores dentro do esperado.",
     "anamnese": "Comparece para acompanhamento de rotina.", "conduta": "Orientações sobre alimentação e atividade física."},
    {"cid": ("Z48.0", "Cuidados com curativos e suturas"), "resumo": "Troca de curativo. Ferida com boa cicatrização.",
     "anamnese": "Retorno para troca de curativo em ferida na perna.", "conduta": "Manter curativo limpo e seco. Retorno em 3 dias."},
]

VACINAS = [("Influenza", "Dose anual", "Instituto Butantan"),
           ("Covid-19", "Reforço", "Bio-Manguinhos/Fiocruz"),
           ("dT (difteria e tétano)", "Reforço", "Instituto Butantan"),
           ("Hepatite B", "1ª dose", "Instituto Butantan"),
           ("Febre amarela", "Dose única", "Bio-Manguinhos/Fiocruz"),
           ("Tríplice viral", "2ª dose", "Bio-Manguinhos/Fiocruz")]

EXAMES = [("Hemograma completo", "Sem alterações."),
          ("Glicemia de jejum", "98 mg/dL (referência: 70 a 99 mg/dL)."),
          ("Glicemia de jejum", "132 mg/dL, acima da referência (70 a 99 mg/dL)."),
          ("Colesterol total e frações", "Colesterol total 212 mg/dL, LDL 138 mg/dL. Levemente elevado."),
          ("Creatinina", "0,9 mg/dL. Função renal preservada."),
          ("TSH", "2,1 µUI/mL (referência: 0,4 a 4,0)."),
          ("Urina tipo 1", "Sem alterações.")]

URGENCIAS = [
    {"cid": ("I10", "Hipertensão essencial (primária)"),
     "resumo": "Pico hipertensivo. Medicado e liberado após estabilização.",
     "anamnese": "Dor de cabeça intensa e tontura. PA elevada na chegada.",
     "conduta": "Liberado após estabilização. Encaminhado para acompanhamento na UBS.",
     "rx": [("Captopril 25 mg", "1 comprimido sublingual, dose única na unidade")], "pa": "180/110"},
    {"cid": ("S93.4", "Entorse e distensão do tornozelo"),
     "resumo": "Entorse de tornozelo. Raio-X sem fratura, imobilização.",
     "anamnese": "Torceu o tornozelo direito jogando futebol. Dor e inchaço local.",
     "conduta": "Gelo, repouso e elevação do membro. Retorno se não melhorar em 7 dias.",
     "rx": [("Paracetamol 750 mg", "1 comprimido via oral a cada 6 horas, se dor, por 5 dias")]},
    {"cid": ("R10.4", "Outras dores abdominais e as não especificadas"),
     "resumo": "Dor abdominal. Avaliado, sem sinais de gravidade.",
     "anamnese": "Dor abdominal difusa há 1 dia, sem febre ou vômitos.",
     "conduta": "Dieta leve e hidratação. Retornar se houver febre ou piora da dor.",
     "rx": [("Escopolamina 10 mg", "1 comprimido via oral a cada 8 horas, se dor, por 3 dias")]},
    {"cid": ("T78.4", "Alergia não especificada"),
     "resumo": "Reação alérgica na pele. Medicado e liberado.",
     "anamnese": "Placas vermelhas e coceira pelo corpo após contato com produto de limpeza.",
     "conduta": "Evitar o produto. Retornar imediatamente se houver falta de ar.",
     "rx": [("Loratadina 10 mg", "1 comprimido via oral ao dia, por 5 dias")]},
]

ODONTO = [
    {"cid": ("Z01.2", "Exame odontológico"), "resumo": "Limpeza e avaliação periódica. Sem necessidade de procedimentos."},
    {"cid": ("K02.1", "Cáries da dentina"), "resumo": "Restauração em resina no dente 36."},
    {"cid": ("K05.1", "Gengivite crônica"), "resumo": "Raspagem e orientação de higiene bucal."},
]

INTERNACOES = [
    {"cid": ("J18.9", "Pneumonia não especificada"),
     "resumo": "Internação por pneumonia por 5 dias. Alta com melhora.",
     "anamnese": "Febre alta, tosse com secreção e falta de ar há 4 dias.",
     "conduta": "Alta hospitalar com antibiótico oral. Retorno na UBS em 7 dias.",
     "rx": [("Amoxicilina + clavulanato 875/125 mg", "1 comprimido via oral a cada 12 horas, por 7 dias")]},
    {"cid": ("K35.8", "Apendicite aguda, outras e as não especificadas"),
     "resumo": "Apendicectomia por videolaparoscopia. Alta após 2 dias.",
     "anamnese": "Dor abdominal em fossa ilíaca direita há 12 horas, com náuseas.",
     "conduta": "Alta com orientações sobre a cirurgia. Retirada de pontos em 10 dias.",
     "rx": [("Paracetamol 750 mg", "1 comprimido via oral a cada 6 horas, se dor, por 5 dias")]},
]

TIPOS_PESOS = [("Consulta médica", 35), ("Consulta de enfermagem", 12), ("Vacinação", 15),
               ("Exame laboratorial", 15), ("Urgência", 10), ("Consulta odontológica", 10), ("Internação", 3)]


# ---------------------------------------------------------------------------
# Inserção
# ---------------------------------------------------------------------------

def criar_banco():
    if os.path.exists(CAMINHO_DB):
        os.remove(CAMINHO_DB)
    con = sqlite3.connect(CAMINHO_DB)
    con.row_factory = sqlite3.Row
    with open(os.path.join(BASE, "schema.sql"), encoding="utf-8") as f:
        con.executescript(f.read())
    return con


def inserir_unidades(con):
    ids = {}
    for nome, tipo, municipio, sistema, horas in UNIDADES:
        sinc = (AGORA - timedelta(hours=horas)).isoformat()
        cur = con.execute(
            "INSERT INTO unidades (nome, tipo, municipio, cnes, sistema_origem, ultima_sincronizacao) "
            "VALUES (?, ?, ?, ?, ?, ?)", (nome, tipo, municipio, gerar_cnes(), sistema, sinc))
        ids[(nome, municipio)] = cur.lastrowid
    return ids


def inserir_profissionais(con):
    ids = {}
    for nome, esp, conselho in PROFISSIONAIS:
        cur = con.execute(
            "INSERT INTO profissionais (nome, especialidade, conselho, registro) VALUES (?, ?, ?, ?)",
            (nome, esp, conselho, str(random.randint(10000, 99999))))
        ids[nome] = cur.lastrowid
    return ids


def inserir_paciente(con, nome, nascimento, sexo, mae, municipio, unidade_ref, cpf=None, **extra):
    cur = con.execute(
        "INSERT INTO pacientes (nome, nome_busca, nome_social, cpf, cns, data_nascimento, sexo, raca_cor, "
        "nome_mae, mae_busca, nome_pai, municipio, telefone, unidade_referencia_id) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (nome, normalizar(nome), extra.get("nome_social"), cpf or gerar_cpf(), gerar_cns(),
         nascimento, sexo, extra.get("raca_cor", random.choice(RACAS)), mae, normalizar(mae),
         extra.get("nome_pai"), municipio, gerar_telefone(), unidade_ref))
    return cur.lastrowid


def unidades_por_tipo(con, tipo, municipio=None):
    linhas = con.execute("SELECT id, municipio FROM unidades WHERE tipo = ?", (tipo,)).fetchall()
    locais = [r["id"] for r in linhas if r["municipio"] == municipio]
    return locais or [r["id"] for r in linhas]


def profissionais_para(tipo, prof_ids):
    medicos = ["Dr. João Pereira", "Dr. Ricardo Alves", "Dra. Camila Rocha", "Dr. Marcelo Teixeira"]
    mapa = {
        "Consulta médica": medicos + ["Dra. Patrícia Nunes"],
        "Consulta de enfermagem": ["Enf. Carla Mendes", "Enf. Maria Souza", "Enf. Bruno Farias", "Enf. Aline Barbosa"],
        "Vacinação": ["Enf. Carla Mendes", "Enf. Bruno Farias", "Enf. Aline Barbosa"],
        "Exame laboratorial": ["Dra. Sílvia Ramos"],
        "Urgência": ["Dra. Fernanda Lopes", "Dr. Marcelo Teixeira"],
        "Consulta odontológica": ["Dr. Rafael Costa", "Dra. Letícia Moraes"],
        "Internação": ["Dr. Henrique Duarte", "Dra. Fernanda Lopes"],
    }
    return prof_ids[random.choice(mapa[tipo])]


def sinais_vitais(pa=None):
    return {
        "pa": pa or f"{random.randint(110, 145)}/{random.randint(70, 95)}",
        "fc": random.randint(62, 98),
        "temperatura": round(random.uniform(36.0, 37.4), 1),
        "spo2": random.randint(95, 99),
        "peso": round(random.uniform(52, 98), 1),
    }


def inserir_atendimento(con, paciente_id, unidade_id, prof_id, quando, tipo, caso=None,
                        vitais=None, rx=(), exames=(), vacinas=(), resumo=None, prefixo="RAC"):
    caso = caso or {}
    vitais = vitais or {}
    cid = caso.get("cid", (None, None))
    recebido = min(quando + timedelta(minutes=random.randint(10, 300)), AGORA)
    cur = con.execute(
        "INSERT INTO atendimentos (paciente_id, unidade_id, profissional_id, data_hora, tipo, cid_codigo, "
        "cid_descricao, resumo, anamnese, conduta, pa, fc, temperatura, spo2, peso, id_origem, recebido_em) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (paciente_id, unidade_id, prof_id, quando.isoformat(), tipo, cid[0], cid[1],
         resumo or caso.get("resumo"), caso.get("anamnese"), caso.get("conduta"),
         vitais.get("pa"), vitais.get("fc"), vitais.get("temperatura"), vitais.get("spo2"),
         vitais.get("peso"), id_origem(prefixo), recebido.isoformat()))
    at_id = cur.lastrowid
    for med, pos in rx:
        con.execute("INSERT INTO prescricoes (atendimento_id, medicamento, posologia) VALUES (?, ?, ?)",
                    (at_id, med, pos))
    for nome, res in exames:
        con.execute("INSERT INTO exames (atendimento_id, nome, resultado) VALUES (?, ?, ?)", (at_id, nome, res))
    for vacina, dose, fab in vacinas:
        lote = f"{random.choice('ABCDEFGHJK')}{random.choice('ABCDEFGHJK')}{random.randint(1000, 9999)}"
        con.execute("INSERT INTO imunizacoes (atendimento_id, vacina, dose, lote, fabricante) VALUES (?, ?, ?, ?, ?)",
                    (at_id, vacina, dose, lote, fab))
    return at_id


def atendimento_aleatorio(con, paciente, prof_ids, alergias):
    tipo = random.choices([t for t, _ in TIPOS_PESOS], weights=[p for _, p in TIPOS_PESOS])[0]
    quando = data_aleatoria(INICIO_HISTORICO, AGORA - timedelta(hours=3))
    municipio = paciente["municipio"]
    prof = profissionais_para(tipo, prof_ids)

    def sem_alergia(rx):
        return [(m, p) for m, p in rx if not any(a.lower() in m.lower() for a in alergias)]

    if tipo == "Consulta médica":
        caso = random.choice(CONSULTAS)
        vit = sinais_vitais()
        if caso["cid"][0] == "J06.9":
            vit["temperatura"] = round(random.uniform(37.8, 38.9), 1)
        return inserir_atendimento(con, paciente["id"], random.choice(unidades_por_tipo(con, "UBS", municipio)),
                                   prof, quando, tipo, caso, vit, sem_alergia(caso["rx"]))
    if tipo == "Consulta de enfermagem":
        caso = random.choice(ENFERMAGEM)
        return inserir_atendimento(con, paciente["id"], random.choice(unidades_por_tipo(con, "UBS", municipio)),
                                   prof, quando, tipo, caso, sinais_vitais())
    if tipo == "Vacinação":
        vacina = random.choice(VACINAS)
        return inserir_atendimento(con, paciente["id"], random.choice(unidades_por_tipo(con, "UBS", municipio)),
                                   prof, quando, tipo, vacinas=[vacina],
                                   resumo=f"Aplicada vacina {vacina[0]} ({vacina[1].lower()}). Sem reações adversas.")
    if tipo == "Exame laboratorial":
        escolhidos = random.sample(EXAMES, k=random.randint(1, 3))
        nomes = " e ".join(e[0].lower() for e in escolhidos)
        return inserir_atendimento(con, paciente["id"], random.choice(unidades_por_tipo(con, "Laboratório", municipio)),
                                   prof, quando, tipo, exames=escolhidos, prefixo="REL",
                                   resumo=f"Resultado de {nomes} disponível.")
    if tipo == "Urgência":
        caso = random.choice(URGENCIAS)
        return inserir_atendimento(con, paciente["id"], random.choice(unidades_por_tipo(con, "UPA", municipio)),
                                   prof, quando, tipo, caso, sinais_vitais(caso.get("pa")), sem_alergia(caso["rx"]))
    if tipo == "Consulta odontológica":
        caso = random.choice(ODONTO)
        return inserir_atendimento(con, paciente["id"], random.choice(unidades_por_tipo(con, "UBS", municipio)),
                                   prof, quando, tipo, caso)
    caso = random.choice(INTERNACOES)
    return inserir_atendimento(con, paciente["id"], random.choice(unidades_por_tipo(con, "Hospital", municipio)),
                               prof, quando, tipo, caso, sinais_vitais(), sem_alergia(caso["rx"]), prefixo="SA")


def inserir_casos_demonstracao(con, uni, prof):
    """Pacientes fixos usados nas telas do protótipo (homônimos, sem histórico etc.)."""
    ubs_centro = uni[("UBS Centro", "Itajaí")]

    # Três pacientes com o mesmo nome, para testar a tela de homônimos
    maria1 = inserir_paciente(con, "Maria da Silva", "1985-03-12", "Feminino", "Ana Pereira da Silva",
                              "Itajaí", ubs_centro, cpf="12345678909", raca_cor="Parda", nome_pai="Jorge da Silva")
    inserir_paciente(con, "Maria da Silva", "1962-09-05", "Feminino", "Joana Souza da Silva",
                     "Balneário Camboriú", uni[("UBS Nações", "Balneário Camboriú")])
    inserir_paciente(con, "Maria da Silva", "2001-11-27", "Feminino", "Lúcia Ferreira da Silva",
                     "Navegantes", uni[("UBS Gravatá", "Navegantes")])

    con.execute("INSERT INTO alergias (paciente_id, substancia, reacao, gravidade) VALUES (?, ?, ?, ?)",
                (maria1, "Dipirona", "Urticária e inchaço", "Moderada"))
    for desc, cid in [("Hipertensão arterial", "I10"), ("Diabetes tipo 2", "E11")]:
        con.execute("INSERT INTO condicoes (paciente_id, descricao, cid) VALUES (?, ?, ?)", (maria1, desc, cid))

    # Histórico igual ao do protótipo no Figma (datas relativas a hoje)
    hoje = AGORA
    casos = [
        (hoje - timedelta(days=12), "Consulta médica", ubs_centro, "Dr. João Pereira", CONSULTAS[0],
         {"pa": "128/82", "fc": 92, "temperatura": 38.2, "spo2": 97, "peso": 68.0},
         CONSULTAS[0]["rx"] + [("Cloreto de sódio 0,9% (spray nasal)", "2 jatos em cada narina, 3 vezes ao dia, por 5 dias")],
         [], [], None),
        (hoje - timedelta(days=40), "Vacinação", ubs_centro, "Enf. Carla Mendes", None, None, [], [],
         [("Influenza", "Dose anual", "Instituto Butantan")],
         "Aplicada dose anual da vacina contra Influenza. Sem reações adversas."),
        (hoje - timedelta(days=55), "Exame laboratorial", uni[("Laboratório Municipal", "Itajaí")],
         "Dra. Sílvia Ramos", None, None, [], [EXAMES[0], EXAMES[2]], [],
         "Hemograma sem alterações. Glicemia de jejum acima da meta."),
        (hoje - timedelta(days=160), "Urgência", uni[("UPA 24h Itajaí", "Itajaí")], "Dra. Fernanda Lopes",
         URGENCIAS[0], {"pa": "180/110", "fc": 96, "temperatura": 36.6, "spo2": 98, "peso": 68.5},
         URGENCIAS[0]["rx"], [], [], None),
        (hoje - timedelta(days=260), "Consulta odontológica", ubs_centro, "Dr. Rafael Costa", ODONTO[0],
         None, [], [], [], None),
        (hoje - timedelta(days=400), "Consulta médica", ubs_centro, "Dr. João Pereira", CONSULTAS[2],
         {"pa": "134/86", "fc": 80, "temperatura": 36.5, "spo2": 98, "peso": 70.2}, CONSULTAS[2]["rx"], [], [], None),
        (hoje - timedelta(days=700), "Consulta médica", ubs_centro, "Dr. Ricardo Alves", CONSULTAS[1],
         {"pa": "142/92", "fc": 78, "temperatura": 36.4, "spo2": 98, "peso": 71.0}, CONSULTAS[1]["rx"], [], [], None),
    ]
    for quando, tipo, unidade, prof_nome, caso, vit, rx, exames, vacinas, resumo in casos:
        quando = quando.replace(hour=random.randint(8, 16), minute=random.choice([0, 15, 30, 45]))
        inserir_atendimento(con, maria1, unidade, prof[prof_nome], quando, tipo, caso, vit, rx, exames, vacinas,
                            resumo, prefixo="REL" if tipo == "Exame laboratorial" else "RAC")

    # Pacientes das "buscas recentes"
    recentes = [
        inserir_paciente(con, "João Carlos Pereira", "1978-07-04", "Masculino", "Rita Pereira", "Itajaí", ubs_centro),
        inserir_paciente(con, "Ana Beatriz Souza", "1994-01-21", "Feminino", "Cláudia Souza", "Itajaí", ubs_centro),
        inserir_paciente(con, "Pedro Henrique Lima", "2015-10-30", "Masculino", "Paula Lima", "Itajaí", ubs_centro),
    ]
    # Paciente cadastrado, mas sem nenhum atendimento na rede
    inserir_paciente(con, "Lucas Andrade Martins", "1990-06-18", "Masculino", "Sônia Andrade",
                     "Penha", uni[("UBS Armação", "Penha")])
    return maria1, recentes


def inserir_pacientes_aleatorios(con, quantidade=250):
    ubs = [r["id"] for r in con.execute("SELECT id FROM unidades WHERE tipo = 'UBS'")]
    for _ in range(quantidade):
        sexo = random.choice(["Feminino", "Masculino"])
        primeiro = random.choice(NOMES_F if sexo == "Feminino" else NOMES_M)
        meio = random.choice(SOBRENOMES)
        ultimo = random.choice(SOBRENOMES)
        nome = f"{primeiro} {meio} {ultimo}" if meio != ultimo else f"{primeiro} {ultimo}"
        mae = f"{random.choice(NOMES_F)} {meio}"
        nasc = date(random.randint(1940, 2023), random.randint(1, 12), random.randint(1, 28)).isoformat()
        pid = inserir_paciente(con, nome, nasc, sexo, mae, random.choice(MUNICIPIOS), random.choice(ubs))
        if random.random() < 0.15:
            con.execute("INSERT INTO alergias (paciente_id, substancia, reacao, gravidade) VALUES (?, ?, ?, ?)",
                        (pid, *random.choice(ALERGIAS)))
        for desc, cid in random.sample(CONDICOES, k=random.choice([0, 0, 0, 1, 1, 2])):
            con.execute("INSERT INTO condicoes (paciente_id, descricao, cid) VALUES (?, ?, ?)", (pid, desc, cid))


def main():
    con = criar_banco()
    uni = inserir_unidades(con)
    prof = inserir_profissionais(con)
    maria1, recentes = inserir_casos_demonstracao(con, uni, prof)
    inserir_pacientes_aleatorios(con)

    # Atendimentos aleatórios (exceto o paciente sem histórico)
    pacientes = con.execute("SELECT id, municipio FROM pacientes WHERE nome != 'Lucas Andrade Martins'").fetchall()
    for p in pacientes:
        alergias = [r["substancia"] for r in con.execute("SELECT substancia FROM alergias WHERE paciente_id = ?", (p["id"],))]
        extras = random.randint(2, 6) if p["id"] == maria1 else random.randint(0, 14)
        for _ in range(extras):
            atendimento_aleatorio(con, p, prof, alergias)

    # Usuários de demonstração (senha: saude123)
    senha = generate_password_hash("saude123")
    ubs_centro = uni[("UBS Centro", "Itajaí")]
    usuarios = [("1001", "Enf. Maria Souza", "Enfermeira"), ("1002", "Dr. João Pereira", "Médico")]
    for matricula, nome, cargo in usuarios:
        con.execute("INSERT INTO usuarios (matricula, nome, cargo, senha_hash, unidade_id) VALUES (?, ?, ?, ?, ?)",
                    (matricula, nome, cargo, senha, ubs_centro))

    # Algumas consultas anteriores, para preencher "Buscas recentes"
    for i, pid in enumerate(recentes):
        quando = AGORA - timedelta(minutes=[15, 60, 60 * 26][i])
        con.execute("INSERT INTO acessos (usuario_id, paciente_id, acao, data_hora) VALUES (1, ?, 'historico', ?)",
                    (pid, quando.isoformat()))

    con.commit()
    total_p = con.execute("SELECT COUNT(*) FROM pacientes").fetchone()[0]
    total_a = con.execute("SELECT COUNT(*) FROM atendimentos").fetchone()[0]
    con.close()
    print(f"Banco criado em {CAMINHO_DB}")
    print(f"{total_p} pacientes e {total_a} atendimentos fictícios.")
    print("Usuários de teste: matrícula 1001 ou 1002, senha saude123")


if __name__ == "__main__":
    main()
