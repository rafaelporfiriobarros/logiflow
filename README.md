# LogiFlow AI — Plataforma de Monitoramento Logístico e Automação de Notificações

**Plataforma de monitoramento de entregas, detecção de atrasos, automação operacional e análise de indicadores logísticos.**

O LogiFlow AI é um projeto end-to-end desenvolvido para demonstrar a aplicação de Engenharia de Dados, desenvolvimento backend, automação de processos e Business Intelligence em um cenário de operações logísticas.

A solução integra Python, FastAPI, PostgreSQL, n8n, Docker e Power BI para transformar eventos operacionais em informações rastreáveis, alertas e indicadores de desempenho.

## Problema de negócio

Operações logísticas precisam acompanhar entregas, identificar atrasos e comunicar ocorrências de maneira confiável.

Quando essas atividades dependem de processos manuais, podem ocorrer atrasos na identificação de problemas, notificações duplicadas, falta de rastreabilidade e dificuldades para acompanhar indicadores operacionais.

O LogiFlow AI propõe uma arquitetura para automatizar esse fluxo e disponibilizar dados para acompanhamento e tomada de decisão.

## Arquitetura da solução

```text
                  PostgreSQL
          Clientes | Pedidos | Entregas
                       |
                       v
                 FastAPI / Python
                       |
               Monitoramento de
                 atrasos e SLA
                       |
                       v
                 Incidentes
                       |
                       v
               Notification Outbox
                       |
                       v
                  n8n Worker
                       |
                       v
                  SMTP / E-mail

          PostgreSQL / Histórico
                       |
                       v
                SQL Analytics
                       |
                       v
                   Power BI

       GitHub Actions: Ruff + Alembic + pytest
```

A arquitetura separa o monitoramento das entregas do processamento das notificações, permitindo maior controle sobre falhas, tentativas de envio e auditoria.

## Tecnologias utilizadas

| Tecnologia | Aplicação |
|---|---|
| Python | Regras de negócio, monitoramento e serviços |
| FastAPI | API REST e endpoints operacionais |
| PostgreSQL 17 | Persistência de dados transacionais e analíticos |
| SQLAlchemy | Modelagem e acesso ao banco |
| Alembic | Versionamento do schema |
| n8n | Orquestração dos workflows |
| SMTP | Envio de notificações por e-mail |
| Docker Compose | Execução dos serviços |
| SQL | Transformações, views e indicadores |
| Power BI | Visualização e análise operacional |
| pytest | Testes automatizados |
| Ruff | Qualidade e padronização do código |
| GitHub Actions | Integração contínua |
| UV | Gerenciamento de dependências Python |

## Funcionalidades

### 1. Monitoramento de entregas

- Identificação de entregas com atraso.
- Aplicação de regras de negócio para detecção de ocorrências.
- Registro de execuções de monitoramento.
- Prevenção de incidentes duplicados.
- Persistência do histórico operacional.

### 2. Gerenciamento de incidentes

Os incidentes representam ocorrências identificadas durante o monitoramento.

A aplicação registra informações que permitem acompanhar problemas operacionais, consultar o histórico e analisar padrões de atraso.

### 3. Notification Outbox

A arquitetura utiliza o padrão Transactional Outbox para desacoplar o registro de uma notificação de sua entrega por e-mail.

O processamento contempla:

- Persistência das notificações.
- Reserva de itens elegíveis para envio.
- Controle de concorrência com PostgreSQL.
- Identificação das reservas por `claim_token`.
- Prazo de validade das reservas.
- Registro de tentativas e falhas.
- Confirmação do resultado do processamento.

O mecanismo utiliza `FOR UPDATE SKIP LOCKED` para reduzir conflitos entre consumidores concorrentes.

**Garantia de entrega:** o processamento segue uma abordagem *at-least-once*. Se o servidor SMTP aceitar uma mensagem, mas a confirmação não for registrada, poderá ocorrer um novo envio.

### 4. Automação com n8n

Foram desenvolvidos dois workflows:

**Monitoring Delays**

Executa periodicamente o monitoramento das entregas por meio da API.

**Notification Outbox Worker**

Consulta notificações elegíveis, realiza o envio por SMTP e informa à API o resultado da tentativa.

Os workflows estão documentados em `docs/workflows/` e seus arquivos JSON encontram-se em `n8n/workflows/`.

### 5. Observabilidade e Analytics

A solução mantém dados de monitoramento, incidentes e notificações para análise operacional.

As views SQL incluem:

- `analytics.incident_summary`
- `analytics.notification_summary`
- `analytics.monitoring_history`
- `analytics.incident_details`
- `analytics.notification_details`

Os scripts estão disponíveis em `sql/analytics/`.

### 6. Dashboard Power BI

O dashboard foi organizado em quatro páginas:

| Página | Objetivo |
|---|---|
| Visão Geral | Acompanhamento dos principais indicadores |
| Monitoramento | Histórico das execuções |
| Incidentes | Análise das ocorrências |
| Notificações | Acompanhamento dos envios e falhas |

A integração utiliza um usuário PostgreSQL dedicado à leitura analítica, seguindo o princípio do menor privilégio.

## API REST

Principais endpoints implementados:

| Método | Endpoint | Finalidade |
|---|---|---|
| POST | `/api/v1/monitoring/delays` | Executar monitoramento |
| POST | `/api/v1/notifications/claim` | Reservar notificações |
| POST | `/api/v1/notifications/{id}/sent` | Confirmar envio |
| POST | `/api/v1/notifications/{id}/failed` | Registrar falha |
| GET | `/api/v1/observability/summary` | Consultar indicadores |
| GET | `/api/v1/health/database` | Verificar conexão com o banco |

Os endpoints operacionais protegidos utilizam autenticação por chave de API no cabeçalho `X-API-Key`.

## Execução local

### Pré-requisitos

- Git
- Docker Desktop com Docker Compose
- Python 3.12
- UV

### Clonar o projeto

```bash
git clone https://github.com/rafaelporfiriobarros/logiflow-ai.git
cd logiflow-ai
```

### Configurar o ambiente

Utilize o arquivo `.env.example` como referência para configurar as variáveis necessárias.

No PowerShell:

```powershell
Copy-Item .env.example .env
```

Preencha os valores locais adequados antes de iniciar os serviços.

**Nunca publique o arquivo `.env` nem credenciais reais.**

### Iniciar os serviços

```powershell
docker compose up -d --build
```

No ambiente local utilizado durante o desenvolvimento:

| Serviço | Endereço |
|---|---|
| FastAPI | `http://localhost:8000` |
| Documentação da API | `http://localhost:8000/docs` |
| n8n | `http://localhost:5678` |
| PostgreSQL operacional | `localhost:5433` |

As portas podem ser alteradas conforme a configuração do Docker Compose.

### Instalar dependências Python

```powershell
uv sync --frozen
```

### Migrações

O projeto utiliza Alembic para controlar a evolução do banco de dados.

```powershell
uv run alembic current
uv run alembic upgrade head
```

Antes de executar migrações, confirme que as variáveis de conexão apontam para o banco pretendido.

## Testes e qualidade

O projeto possui uma suíte automatizada com testes unitários e de integração.

Os testes abrangem regras de monitoramento, incidentes, notificações, concorrência, API, persistência e views analíticas.

### Ruff

```powershell
uv run ruff check .
```

### pytest

```powershell
uv run pytest -ra -q
```

Os testes PostgreSQL exigem um banco dedicado chamado `logiflow_test`, configurado por meio de `TEST_DATABASE_URL`.

**Não utilize o banco operacional para executar os testes de integração.**

### Resultados validados

- 91 testes aprovados no ambiente local.
- Ruff sem erros.
- Migrações Alembic executadas com sucesso.
- GitHub Actions executado com sucesso no ambiente Ubuntu.

## Integração contínua

O projeto utiliza GitHub Actions para validar automaticamente alterações na branch `master`.

O pipeline realiza:

1. Inicialização do PostgreSQL de testes.
2. Instalação do Python e UV.
3. Instalação das dependências.
4. Validação do destino do banco de testes.
5. Execução das migrações Alembic.
6. Verificação da consistência do schema.
7. Análise estática com Ruff.
8. Execução dos testes automatizados.

[Visualizar execuções do GitHub Actions](https://github.com/rafaelporfiriobarros/logiflow-ai/actions)

## Decisões técnicas

**Separação entre monitoramento e notificação:** evita que o envio de e-mails faça parte do processamento principal de detecção de atrasos.

**Transactional Outbox:** permite registrar notificações junto às alterações de negócio e processá-las posteriormente.

**Controle de concorrência:** reduz a possibilidade de dois consumidores reservarem simultaneamente a mesma notificação.

**Migrações versionadas:** tornam a evolução do schema reproduzível.

**Banco de testes isolado:** protege os dados operacionais durante a execução dos testes de integração.

**Camada analítica SQL:** separa consultas destinadas a relatórios das operações transacionais da aplicação.

**Integração contínua:** valida automaticamente qualidade, migrações e testes em um ambiente independente do computador de desenvolvimento.

## Estrutura do projeto

```text
logiflow-ai/
├── .github/
│   └── workflows/
│       └── ci.yml
├── dashboard/
├── docs/
│   ├── architecture/
│   └── workflows/
├── migrations/
│   └── versions/
├── n8n/
│   └── workflows/
├── sql/
│   ├── analytics/
│   └── security/
├── src/
│   └── logiflow_ai/
│       ├── api/
│       ├── core/
│       ├── models/
│       ├── schemas/
│       └── services/
├── tests/
├── docker-compose.yml
├── pyproject.toml
├── uv.lock
└── README.md
```

## Limitações e evoluções futuras

O projeto pode evoluir com:

- Métricas de desempenho e disponibilidade dos serviços.
- Alertas para falhas recorrentes nos workflows.
- Estratégias adicionais de deduplicação no envio de mensagens.
- Melhorias na gestão de segredos e credenciais.
- Implantação em infraestrutura de nuvem.
- Testes de carga e avaliação de escalabilidade.

## Objetivo do projeto

O LogiFlow AI foi desenvolvido como projeto de portfólio para demonstrar competências em:

**Engenharia de Dados, Analytics, SQL, Python, APIs REST, automação, modelagem de dados, testes, observabilidade, integração contínua e visualização de indicadores.**

O foco está na construção de uma solução integrada, com regras de negócio, rastreabilidade e práticas de desenvolvimento aplicáveis a ambientes corporativos.