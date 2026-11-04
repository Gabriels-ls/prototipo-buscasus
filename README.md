# Busca SUS

Sistema web para médicos e enfermeiros da rede pública consultarem o histórico de atendimentos dos pacientes da região da AMFRI, reunindo em um só lugar os dados de UBS, UPAs, hospitais e laboratórios.

Projeto desenvolvido para a **CIS-AMFRI** (Consórcio Público Interfederativo de Saúde da Região da Foz do Rio Itajaí).

> ⚠️ **Todos os dados deste repositório são fictícios.** Nomes, CPFs, Cartões SUS, telefones, registros profissionais e códigos CNES são gerados aleatoriamente pelo script `seed.py` e não pertencem a pessoas ou estabelecimentos reais.

## Funcionalidades

- **Login** com matrícula e senha (senhas guardadas com hash).
- **Busca de pacientes** por CPF, Cartão SUS (CNS) ou nome, com filtros por data de nascimento, nome da mãe e município. A busca por nome ignora acentos e maiúsculas.
- **Página de resultados** sempre exibida, com três situações:
  - um paciente encontrado;
  - vários pacientes, com aviso quando há homônimos;
  - nenhum paciente, explicando os possíveis motivos.
- **Histórico do paciente** agrupado por ano, com filtros por tipo (consultas, vacinas, exames, urgência, odontologia, internações), alertas clínicos (alergias e condições crônicas) e a origem de cada registro.
- **Aviso de fonte atrasada** quando alguma unidade está há mais de 24 horas sem sincronizar.
- **Detalhe do atendimento** com anamnese, sinais vitais, diagnóstico (CID), vacinas, exames, prescrições e conduta.
- **Registro de acessos** (auditoria): cada abertura de histórico ou atendimento é gravada com usuário, paciente e horário, como pede a LGPD para dados sensíveis.
- **Buscas recentes** de cada usuário na tela inicial.
- Layout responsivo e páginas prontas para impressão.

## Tecnologias

- [Python 3.10+](https://www.python.org/)
- [Gunicorn](https://gunicorn.org/) (servidor de produção) e [Render](https://render.com) (hospedagem)
- [Flask](https://flask.palletsprojects.com/) (servidor web e templates Jinja)
- [SQLite](https://www.sqlite.org/) (banco de dados em arquivo, já incluso no Python)
- HTML, CSS e um pouco de JavaScript, sem frameworks de front-end

## Como rodar

```bash
# 1. Clone o repositório
git clone https://github.com/SEU-USUARIO/busca-sus.git
cd busca-sus

# 2. Crie e ative um ambiente virtual
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

# 3. Instale as dependências
pip install -r requirements.txt

# 4. Configure as variáveis de ambiente
cp .env.example .env        # no Windows: copy .env.example .env
# (edite o .env e troque a SECRET_KEY)

# 5. Crie o banco com dados fictícios
python seed.py

# 6. Inicie o servidor
flask --app app run --debug
```

Acesse **http://localhost:5000**.

### Usuários de teste

| Matrícula | Nome             | Cargo      | Senha      |
|-----------|------------------|------------|------------|
| 1001      | Enf. Maria Souza | Enfermeira | `saude123` |
| 1002      | Dr. João Pereira | Médico     | `saude123` |

### Buscas para testar

| O que digitar          | Resultado esperado                                  |
|------------------------|-----------------------------------------------------|
| `Maria da Silva`       | 3 pacientes com o mesmo nome (aviso de homônimos)   |
| `123.456.789-09`       | 1 paciente, com histórico completo e alergia        |
| `Lucas Andrade Martins`| 1 paciente cadastrado, mas sem atendimentos na rede |
| `Mariana Silvaa`       | Nenhum paciente encontrado                          |

Para recomeçar do zero, rode `python seed.py` de novo: o banco é apagado e recriado.

## Deploy no Render

O projeto já vem com o arquivo `render.yaml`, que configura tudo automaticamente.

1. Envie o projeto para um repositório no GitHub.
2. Acesse [render.com](https://render.com), entre com sua conta do GitHub e clique em **New > Blueprint**.
3. Selecione o repositório `busca-sus` e confirme em **Apply**.
4. Aguarde o build (cerca de 2 minutos). O endereço do site aparece no topo da página do serviço, no formato `https://busca-sus-xxxx.onrender.com`.

A partir daí, cada `git push` na branch `main` atualiza o site sozinho.

O que o `render.yaml` faz:

- instala as dependências e inicia o site com o `gunicorn`;
- recria o banco fictício a cada inicialização, para as datas de sincronização das unidades ficarem atuais;
- gera uma `SECRET_KEY` aleatória e ativa o cookie de sessão seguro (HTTPS).

Limitações do plano gratuito do Render:

- O site "dorme" depois de 15 minutos sem acessos, e o primeiro acesso seguinte leva cerca de 1 minuto. Antes de uma apresentação, abra o site alguns minutos antes.
- O disco é temporário: como o banco é recriado a cada inicialização, o registro de acessos e as buscas recentes voltam ao estado inicial de tempos em tempos. Para guardar dados de forma permanente, seria preciso um banco hospedado, como o PostgreSQL.

## Estrutura do projeto

```
busca-sus/
├── app.py              # rotas, busca, histórico e auditoria
├── db.py               # conexão com o SQLite
├── utils.py            # máscaras de CPF/CNS/telefone, datas e normalização de texto
├── schema.sql          # criação das tabelas
├── seed.py             # gera o banco com dados fictícios
├── requirements.txt
├── render.yaml         # configuração de deploy no Render
├── .env.example
├── static/
│   ├── css/style.css   # cores e componentes do protótipo no Figma
│   ├── img/            # logo e favicon
│   └── js/app.js
└── templates/
    ├── base.html       # layout com a barra superior
    ├── login.html
    ├── busca.html
    ├── resultados.html # 1 resultado, vários ou nenhum
    ├── historico.html
    ├── atendimento.html
    └── erro.html
```

## Modelo de dados

O banco segue, de forma simplificada, os modelos de informação da **Rede Nacional de Dados em Saúde (RNDS)**, principalmente o Registro de Atendimento Clínico (RAC):

| Tabela          | O que guarda                                                       |
|-----------------|--------------------------------------------------------------------|
| `unidades`      | Estabelecimentos (UBS, UPA, hospital, laboratório), CNES e última sincronização |
| `profissionais` | Quem atendeu, especialidade e registro no conselho (CRM, COREN, CRO) |
| `usuarios`      | Quem pode acessar o sistema                                        |
| `pacientes`     | Cadastro: CPF, CNS, nascimento, mãe, município, unidade de referência |
| `alergias`      | Substância, reação e gravidade                                     |
| `condicoes`     | Condições crônicas com CID                                         |
| `atendimentos`  | Cada atendimento: tipo, CID, anamnese, sinais vitais, conduta e origem |
| `prescricoes`   | Medicamentos prescritos em um atendimento                          |
| `exames`        | Resultados de exames                                               |
| `imunizacoes`   | Vacinas aplicadas: dose, lote e fabricante                         |
| `acessos`       | Trilha de auditoria: quem consultou qual paciente e quando         |

## Privacidade e segurança

- CPF, CNS e telefone aparecem sempre mascarados na interface.
- Todas as consultas ao banco usam parâmetros (proteção contra SQL injection).
- Formulários têm proteção contra CSRF e a sessão expira em 8 horas.
- O arquivo `.env` e o banco `*.db` ficam fora do Git (veja `.gitignore`).

Antes de usar com dados reais, seria necessário, entre outros pontos: HTTPS, política de senhas e bloqueio após tentativas, banco de dados de produção (ex.: PostgreSQL), integração com os sistemas de origem ou com a RNDS, e avaliação jurídica sobre o tratamento de dados sensíveis.

## Próximos passos

- [ ] Integração real com as fontes de dados (e-SUS APS, sistemas hospitalares, RNDS)
- [ ] Seções de medicamentos em uso e sumário de alta de internações
- [ ] Unificação de cadastros duplicados do mesmo paciente
- [ ] Painel administrativo de usuários e status das integrações
- [ ] Testes automatizados
