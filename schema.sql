-- Esquema do banco do Busca SUS (SQLite).
-- Os modelos de atendimento seguem, de forma simplificada, os blocos do
-- Registro de Atendimento Clínico (RAC) da Rede Nacional de Dados em Saúde.

PRAGMA foreign_keys = ON;

DROP TABLE IF EXISTS acessos;
DROP TABLE IF EXISTS imunizacoes;
DROP TABLE IF EXISTS exames;
DROP TABLE IF EXISTS prescricoes;
DROP TABLE IF EXISTS atendimentos;
DROP TABLE IF EXISTS condicoes;
DROP TABLE IF EXISTS alergias;
DROP TABLE IF EXISTS pacientes;
DROP TABLE IF EXISTS usuarios;
DROP TABLE IF EXISTS profissionais;
DROP TABLE IF EXISTS unidades;

-- Estabelecimentos de saúde que enviam dados para o datalake
CREATE TABLE unidades (
    id                   INTEGER PRIMARY KEY,
    nome                 TEXT NOT NULL,
    tipo                 TEXT NOT NULL,          -- UBS, UPA, Hospital, Laboratório
    municipio            TEXT NOT NULL,
    cnes                 TEXT NOT NULL UNIQUE,   -- Cadastro Nacional de Estabelecimentos de Saúde
    sistema_origem       TEXT NOT NULL,          -- ex.: e-SUS APS (PEC)
    ultima_sincronizacao TEXT NOT NULL           -- ISO 8601
);

-- Profissionais que realizaram os atendimentos
CREATE TABLE profissionais (
    id            INTEGER PRIMARY KEY,
    nome          TEXT NOT NULL,
    especialidade TEXT NOT NULL,
    conselho      TEXT NOT NULL,                 -- CRM-SC, COREN-SC, CRO-SC...
    registro      TEXT NOT NULL
);

-- Usuários com acesso ao sistema (médicos e enfermeiros)
CREATE TABLE usuarios (
    id         INTEGER PRIMARY KEY,
    matricula  TEXT NOT NULL UNIQUE,
    nome       TEXT NOT NULL,
    cargo      TEXT NOT NULL,
    senha_hash TEXT NOT NULL,
    unidade_id INTEGER NOT NULL REFERENCES unidades(id)
);

-- Cadastro do paciente (baseado no CADSUS / cadastro individual do e-SUS)
CREATE TABLE pacientes (
    id                    INTEGER PRIMARY KEY,
    nome                  TEXT NOT NULL,
    nome_busca            TEXT NOT NULL,         -- nome sem acentos e em minúsculas
    nome_social           TEXT,
    cpf                   TEXT UNIQUE,           -- só dígitos
    cns                   TEXT UNIQUE,           -- Cartão Nacional de Saúde, só dígitos
    data_nascimento       TEXT NOT NULL,         -- AAAA-MM-DD
    sexo                  TEXT NOT NULL,
    raca_cor              TEXT,
    nome_mae              TEXT,
    mae_busca             TEXT,
    nome_pai              TEXT,
    municipio             TEXT NOT NULL,
    telefone              TEXT,
    unidade_referencia_id INTEGER REFERENCES unidades(id)
);

CREATE TABLE alergias (
    id          INTEGER PRIMARY KEY,
    paciente_id INTEGER NOT NULL REFERENCES pacientes(id) ON DELETE CASCADE,
    substancia  TEXT NOT NULL,
    reacao      TEXT,
    gravidade   TEXT                             -- Leve, Moderada, Grave
);

CREATE TABLE condicoes (
    id          INTEGER PRIMARY KEY,
    paciente_id INTEGER NOT NULL REFERENCES pacientes(id) ON DELETE CASCADE,
    descricao   TEXT NOT NULL,
    cid         TEXT
);

-- Cada atendimento recebido de uma unidade
CREATE TABLE atendimentos (
    id              INTEGER PRIMARY KEY,
    paciente_id     INTEGER NOT NULL REFERENCES pacientes(id) ON DELETE CASCADE,
    unidade_id      INTEGER NOT NULL REFERENCES unidades(id),
    profissional_id INTEGER NOT NULL REFERENCES profissionais(id),
    data_hora       TEXT NOT NULL,               -- ISO 8601
    tipo            TEXT NOT NULL,               -- Consulta médica, Vacinação, Urgência...
    cid_codigo      TEXT,
    cid_descricao   TEXT,
    resumo          TEXT NOT NULL,               -- texto curto exibido na lista
    anamnese        TEXT,
    conduta         TEXT,
    pa              TEXT,                        -- pressão arterial (mmHg)
    fc              INTEGER,                     -- frequência cardíaca (bpm)
    temperatura     REAL,                        -- °C
    spo2            INTEGER,                     -- saturação de O2 (%)
    peso            REAL,                        -- kg
    id_origem       TEXT NOT NULL,               -- identificador no sistema de origem
    recebido_em     TEXT NOT NULL                -- quando chegou ao datalake
);

CREATE TABLE prescricoes (
    id             INTEGER PRIMARY KEY,
    atendimento_id INTEGER NOT NULL REFERENCES atendimentos(id) ON DELETE CASCADE,
    medicamento    TEXT NOT NULL,
    posologia      TEXT NOT NULL
);

CREATE TABLE exames (
    id             INTEGER PRIMARY KEY,
    atendimento_id INTEGER NOT NULL REFERENCES atendimentos(id) ON DELETE CASCADE,
    nome           TEXT NOT NULL,
    resultado      TEXT
);

CREATE TABLE imunizacoes (
    id             INTEGER PRIMARY KEY,
    atendimento_id INTEGER NOT NULL REFERENCES atendimentos(id) ON DELETE CASCADE,
    vacina         TEXT NOT NULL,
    dose           TEXT NOT NULL,
    lote           TEXT NOT NULL,
    fabricante     TEXT NOT NULL
);

-- Registro de auditoria: quem consultou qual paciente e quando (LGPD)
CREATE TABLE acessos (
    id             INTEGER PRIMARY KEY,
    usuario_id     INTEGER NOT NULL REFERENCES usuarios(id),
    paciente_id    INTEGER NOT NULL REFERENCES pacientes(id),
    atendimento_id INTEGER REFERENCES atendimentos(id),
    acao           TEXT NOT NULL,                -- historico, atendimento
    data_hora      TEXT NOT NULL
);

CREATE INDEX idx_pacientes_nome_busca ON pacientes(nome_busca);
CREATE INDEX idx_atendimentos_paciente ON atendimentos(paciente_id, data_hora);
CREATE INDEX idx_acessos_usuario ON acessos(usuario_id, data_hora);
