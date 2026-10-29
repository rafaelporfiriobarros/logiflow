# LogiFlow  — Plataforma de Monitoramento Logístico e Automação de Notificações

**Plataforma de monitoramento de entregas, detecção de atrasos, automação operacional e análise de indicadores logísticos.**

O LogiFlow  é um projeto end-to-end desenvolvido para demonstrar a aplicação de Engenharia de Dados, desenvolvimento backend, automação de processos e Business Intelligence em um cenário de operações logísticas.

A solução integra Python, FastAPI, PostgreSQL, n8n, Docker e Power BI para transformar eventos operacionais em informações rastreáveis, alertas e indicadores de desempenho.

## Problema de negócio

Operações logísticas precisam acompanhar entregas, identificar atrasos e comunicar ocorrências de maneira confiável.

Quando essas atividades dependem de processos manuais, podem ocorrer atrasos na identificação de problemas, notificações duplicadas, falta de rastreabilidade e dificuldades para acompanhar indicadores operacionais.

O LogiFlow  propõe uma arquitetura para automatizar esse fluxo e disponibilizar dados para acompanhamento e tomada de decisão.

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

**[📊 Acessar dashboard interativo no Power BI](https://app.powerbi.com/view?r=eyJrIjoiNmVjYWJlN2EtYTJkZi00MjkyLWI0MTgtYmQyZGVkYTg4NjhiIiwidCI6IjY1OWNlMmI4LTA3MTQtNDE5OC04YzM4LWRjOWI2MGFhYmI1NyJ9)**

![Dashboard executivo](docs/images/dashboard-1.PNG)

---

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

## Guia completo: executar do zero no Windows

> **Ambiente:** Windows 10/11, PowerShell, VS Code, Docker Desktop com Docker Compose, Python 3.12 e [UV](https://docs.astral.sh/uv/). Este guia foi elaborado a partir dos arquivos deste repositório. A execução integral em uma máquina limpa **não foi realizada** durante esta revisão.

### 1. Obter o código e verificar ferramentas

No terminal PowerShell do VS Code:

```powershell
 git clone https://github.com/rafaelporfiriobarros/logiflow.git
 cd logiflow
 docker --version
 docker compose version
 uv --version
```

Se estiver usando o ZIP do projeto, extraia-o e abra a pasta `logiflow` no VS Code; não precisa clonar. Instale o UV, caso necessário, seguindo a documentação oficial. O `uv` gerencia o Python do projeto: `uv python install 3.12`.

### 2. Configurar `.env` e preservar credenciais

```powershell
 Copy-Item .env.example .env
 notepad .env
```

Ajuste os valores abaixo, que representam um **exemplo**, e substitua os segredos por valores locais próprios:

```dotenv
APP_NAME=LogiFlow 
APP_VERSION=0.1.0
APP_ENV=development
DB_HOST=127.0.0.1
DB_PORT=5433
DB_NAME=logiflow
DB_USER=logiflow
DB_PASSWORD=SUBSTITUA_POR_SENHA_LOCAL_FORTE
MONITORING_API_KEY=SUBSTITUA_POR_CHAVE_LOCAL_FORTE
N8N_ENCRYPTION_KEY=SUBSTITUA_POR_CHAVE_ESTAVEL_E_SECRETA
N8N_TIMEZONE=America/Sao_Paulo
ALERTS_EMAIL_TO=seu-email-de-teste@exemplo.com
```

**Atenção:** o `.env.example` original não inclui `N8N_ENCRYPTION_KEY` nem `ALERTS_EMAIL_TO`; inclua ambos no `.env`. A chave do n8n deve ser mantida estável entre reinicializações para preservar credenciais armazenadas. Não compartilhe o `.env`, senhas, chaves ou tokens; nunca os envie ao Git.

**Configuração importante do Compose:** a API recebe `DB_HOST=postgres` e `DB_PORT=5432` dentro do contêiner. Já os comandos `uv run` executados no **Windows** devem utilizar `DB_HOST=127.0.0.1` e `DB_PORT=5433`. O arquivo `docker-compose.yml` anexado **não repassa `ALERTS_EMAIL_TO` ao serviço `api`**; para que o destinatário configurado no `.env` seja usado no envio, acrescente na seção `api.environment`:

```yaml
      ALERTS_EMAIL_TO: ${ALERTS_EMAIL_TO:?Configure ALERTS_EMAIL_TO no .env}
```

Sem esse ajuste, a API dentro do contêiner usa o padrão `operacoes@example.com`, definido em `config.py`. A alteração acima já foi aplicada ao Compose na versão revisada disponibilizada com este guia.

### 3. Instalar dependências Python

```powershell
uv python install 3.12
uv sync --frozen
```

Não é necessário ativar manualmente `.venv`: os comandos `uv run` usam o ambiente do projeto.

### 4. Subir PostgreSQL, API e n8n

Confirme que o Docker Desktop está iniciado:

```powershell
docker compose config
docker compose up -d --build
docker compose ps
docker compose logs --tail=60 postgres api n8n
```

Serviços: PostgreSQL `127.0.0.1:5433`, API `http://localhost:8000`, Swagger `http://localhost:8000/docs`, n8n `http://localhost:5678`.

> A API pode responder erro de banco até que as migrações sejam aplicadas. O Compose não executa o Alembic automaticamente.

### 5. Executar migrações Alembic no banco operacional

No **mesmo PowerShell**, carregue as variáveis de conexão para a instância operacional, sem expor a senha na saída:

```powershell
$env:DB_HOST = '127.0.0.1'
$env:DB_PORT = '5433'
$env:DB_NAME = 'logiflow'
$env:DB_USER = 'logiflow'
# DB_PASSWORD é lido automaticamente do .env pelo pydantic-settings.
uv run alembic upgrade head
uv run alembic current
```

**Nunca** execute `alembic downgrade base`, `docker compose down -v` ou migrações apontando acidentalmente para `logiflow_test` ou outro banco. O `migrations/env.py` utiliza as variáveis `DB_*` da aplicação, e não `DATABASE_URL`.

### 6. Inserir dados fictícios

```powershell
uv run python -m logiflow.scripts.seed_logistics
```

Na primeira execução, o script gera 20 clientes, 100 pedidos, 100 remessas, eventos de entrega e alguns incidentes iniciais. Em execuções posteriores, detecta o cliente de demonstração e não duplica a carga. **Importante:** como alguns incidentes já são criados pelo seed, um monitoramento posterior pode identificar atrasos sem criar incidentes ou notificações novas.

### 7. Criar as views analíticas

Execute os dois arquivos SQL contra o PostgreSQL operacional, pelo `psql` no contêiner. No PowerShell:

```powershell
Get-Content -Raw .\sql\analytics\001_observability_views.sql | docker compose exec -T postgres psql -v ON_ERROR_STOP=1 -U logiflow -d logiflow
Get-Content -Raw .\sql\analytics\002_detailed_analytics_views.sql | docker compose exec -T postgres psql -v ON_ERROR_STOP=1 -U logiflow -d logiflow
```

Se você personalizou `DB_USER` ou `DB_NAME`, substitua `logiflow` nos comandos. Para confirmar:

```powershell
docker compose exec -T postgres psql -U logiflow -d logiflow -c "SELECT * FROM analytics.notification_summary;"
```

O script `sql/security/001_powerbi_readonly_role.sql` é **opcional** e contém uma senha de placeholder: personalize-o antes de executar. Evite reutilizar credenciais de administração no Power BI.

### 8. Verificar a API e executar o monitoramento

```powershell
Invoke-RestMethod http://localhost:8000/
Invoke-RestMethod http://localhost:8000/api/v1/health
Invoke-RestMethod http://localhost:8000/api/v1/health/database
```

Para chamadas protegidas, a API exige o cabeçalho `X-API-Key`, cujo valor vem de `MONITORING_API_KEY`. Você também pode utilizar o botão **Authorize** em `http://localhost:8000/docs`.

```powershell
# Digite a chave localmente; ela não aparece no histórico do comando.
$secureKey = Read-Host 'MONITORING_API_KEY' -AsSecureString
$key = [System.Net.NetworkCredential]::new('', $secureKey).Password
$headers = @{ 'X-API-Key' = $key }
Invoke-RestMethod -Method Post -Uri 'http://localhost:8000/api/v1/monitoring/delays' -Headers $headers
Remove-Variable key, secureKey, headers
```

É esperado que `created_incidents = 0` quando todos os atrasos já têm incidentes abertos. Isso demonstra idempotência, não falha do endpoint.

### 9. Configurar o n8n do zero - monitoramento e notificações por Gmail

![Resultados Worflow n8n](docs/images/worflow-http.PNG)
![Resultados Worflow n8n](docs/images/workflow-email.PNG)
![Resultados Worflow n8n](docs/images/email-logiflow.PNG)

Esta seção descreve a configuração real dos arquivos `n8n/workflows/monitoring-delays.json` e `n8n/workflows/notification-outbox-worker.json`. O primeiro workflow executa a detecção de atrasos; o segundo reserva notificações no PostgreSQL via API, envia e-mails e registra o resultado.

> **Segurança:** faça os primeiros testes somente com dados fictícios e uma caixa de e-mail sua ou autorizada. Não publique `.env`, senhas de app, credenciais exportadas do n8n ou tokens de reserva. Não use o banco `logiflow_test` para a operação do n8n.

#### 9.1. Pré-requisitos e acesso

Na raiz do projeto, em PowerShell:

```powershell
docker compose up -d --build
docker compose ps
```

Confirme que `postgres`, `api` e `n8n` estão ativos e que as migrações e a carga inicial descritas nas etapas anteriores já foram executadas. Abra:

- **n8n:** http://localhost:5678
- **Swagger da API:** http://localhost:8000/docs

Conclua a criação da conta local do n8n, se solicitada. No Docker, o n8n deve chamar a API em `http://api:8000`, **não** em `http://localhost:8000`: `localhost` dentro do contêiner do n8n aponta para o próprio contêiner.

No `.env` local, confira a presença das variáveis (os valores abaixo são apenas exemplos, **não** credenciais reais):

```dotenv
MONITORING_API_KEY=coloque_uma_chave_local_forte
N8N_ENCRYPTION_KEY=coloque_uma_chave_estavel_e_forte
N8N_TIMEZONE=America/Sao_Paulo
ALERTS_EMAIL_TO=seu-email-de-teste@exemplo.com
```

`MONITORING_API_KEY` autentica os nós HTTP Request; `ALERTS_EMAIL_TO` define o destinatário das notificações criadas pelo monitoramento. Depois de alterar variáveis usadas pelos serviços Docker, recrie os serviços afetados para aplicar a configuração:

```powershell
docker compose up -d --force-recreate api n8n
```

Mantenha `N8N_ENCRYPTION_KEY` estável após criar as credenciais: alterá-la sem migrar adequadamente as credenciais pode impedir sua leitura.

#### 9.2. Importar os dois workflows

No n8n, abra **Workflows → Add workflow → menu `...` → Import from File** (o nome exato do menu pode variar com a versão). Importe, um por vez:

1. `n8n/workflows/monitoring-delays.json` — nome no arquivo: **LogiFlow  - API Key**. Apesar desse nome, é o workflow de monitoramento; você pode renomeá-lo para **LogiFlow  | Monitoring Delays**.
2. `n8n/workflows/notification-outbox-worker.json` — **LogiFlow  | Notification Outbox Worker**.

Salve os workflows, mas **não publique/ative os agendamentos** antes de concluir a configuração e os testes. A importação do JSON não garante que as credenciais locais estejam associadas aos nós.

#### 9.3. Criar e associar a credencial Header Auth

Acesse **Credentials → Add credential → Header Auth** e preencha:

| Campo da credencial | Valor |
|---|---|
| **Name** (nome do cabeçalho) | `X-API-Key` |
| **Value** | Valor real de `MONITORING_API_KEY` no seu `.env` |
| Nome de exibição da credencial | `LogiFlow  - API Key` |

**Atenção:** o valor não é o texto literal `MONITORING_API_KEY`; é o segredo correspondente. Não envie capturas de tela exibindo esse valor.

Em cada nó HTTP Request dos dois workflows, selecione **Authentication → Generic Credential Type → Header Auth → LogiFlow  - API Key**. No worker, isso inclui **Claim Notifications**, **Confirm Sent** e **Confirm Failed**.

#### 9.4. Workflow 1 — Monitoring Delays

O arquivo importado possui dois nós:

```text
Schedule Trigger (a cada 15 minutos, no JSON)
       |
       v
HTTP Request
POST http://api:8000/api/v1/monitoring/delays
```

Abra **HTTP Request** e confira:

| Parâmetro | Valor |
|---|---|
| Method | `POST` |
| URL | `http://api:8000/api/v1/monitoring/delays` |
| Authentication | `Generic Credential Type` |
| Generic Auth Type | `Header Auth` |
| Credential | `LogiFlow  - API Key` |

Clique em **Execute workflow** e examine o output do nó HTTP Request. Um resultado válido pode conter:

```json
{
  "status": "success",
  "delayed_shipments": 78,
  "created_incidents": 0,
  "existing_incidents": 78
}
```

Os números são ilustrativos de uma execução observada no projeto, **não são valores fixos**. `created_incidents = 0` não indica erro: significa que as remessas atrasadas já tinham incidentes abertos. A API usa uma regra de idempotência para não duplicá-los.

#### 9.5. Workflow 2 — Notification Outbox Worker

O worker importado possui este fluxo:

```text
Schedule Trigger
       |
       v
Claim Notifications
       |
       v
If -- false --> fim (nenhuma notificação elegível)
 |
true
 |
v
Split Out
       |
       v
Send an Email (Gmail SMTP)
       |                     |
   Success                  Error
       |                     |
       v                     v
Confirm Sent          Confirm Failed
```

**Nó `Claim Notifications`:**

| Parâmetro | Valor |
|---|---|
| Method | `POST` |
| URL | `http://api:8000/api/v1/notifications/claim` |
| Authentication | `Header Auth` com `LogiFlow  - API Key` |
| Send Body | Ativado |
| Body Content Type | `JSON` |
| JSON Body | `{"limit":1}` |

Esse endpoint **reserva** uma notificação elegível. Não clique repetidamente em **Execute step** apenas para testar: uma reserva altera o estado operacional e possui prazo de validade.

Se a resposta for:

```json
{"items":[],"total":0}
```

não há notificações disponíveis naquele instante. O nó **If** verifica a expressão `{{ Array.isArray($json.items) && $json.items.length > 0 }}`; quando ela é falsa, o fluxo termina normalmente, sem executar SMTP. Isso é esperado e não caracteriza erro.

**Nó `Split Out`:** configure **Fields To Split Out** como `items`. Cada item deve conter os campos necessários para o envio e a confirmação, como `id`, `recipient`, `subject`, `body` e `claim_token`. Confira o painel **Output** antes de continuar.

#### 9.6. Gmail SMTP — criar a credencial

Para usar uma conta Gmail de teste:

1. Acesse https://myaccount.google.com/security e habilite a verificação em duas etapas, se necessário.
2. Acesse https://myaccount.google.com/apppasswords e gere uma **senha de app** chamada, por exemplo, `LogiFlow  - n8n`. A opção pode não estar disponível em todas as contas.
3. No nó **Send an Email**, crie uma credencial SMTP e informe:

| Campo SMTP | Valor para Gmail |
|---|---|
| User | Seu endereço Gmail completo |
| Password | **Senha de app** do Google; não use a senha normal da conta |
| Host | `smtp.gmail.com` |
| Port | `465` |
| SSL/TLS | **Ativado** |
| Client Host Name | Em branco, se opcional |

Salve e utilize **Test connection**, se disponível. A mensagem **Connection tested successfully** confirma a conexão/autenticação SMTP, mas **não** comprova, por si só, que uma notificação chegou à caixa de entrada.

#### 9.7. Configurar o nó Send an Email

No nó **Send an Email**, configure:

| Campo | Valor |
|---|---|
| Credential | Sua credencial SMTP Gmail |
| Operation | `Send` |
| From Email | O **seu** Gmail autenticado |
| To Email | `{{ $json.recipient }}` |
| Subject | `{{ $json.subject }}` |
| Email Format | `Text` |
| Text | `{{ $json.body }}` |

O arquivo JSON importado contém um endereço de remetente usado no ambiente de desenvolvimento original. **Substitua-o pelo seu próprio Gmail** antes de testar. As expressões de destinatário, assunto e corpo dependem dos campos retornados pelo `Split Out`; confira-os no Output.

Para remover o rodapé padrão `This email was sent automatically with n8n`, procure a opção **Append n8n Attribution** nas opções do nó e desative-a, se disponível na versão instalada.

No nó **Settings → On Error**, selecione **Continue (using error output)**. Conecte a saída **Success** ao **Confirm Sent** e a saída **Error** ao **Confirm Failed**. O JSON do projeto já contém essas conexões, mas confirme-as após importar.

#### 9.8. Confirm Sent e Confirm Failed

Ambos os nós são HTTP Request autenticados com `X-API-Key`. **Não** envie a confirmação manualmente para uma notificação não reservada. O `claim_token` recebido no `Split Out` precisa ser preservado.

**Confirm Sent:**

- Method: `POST`
- URL (Expression):

```javascript
{{ 'http://api:8000/api/v1/notifications/' + $('Split Out').item.json.id + '/sent' }}
```

- Body JSON (Expression):

```javascript
{{ { "claim_token": $('Split Out').item.json.claim_token } }}
```

**Confirm Failed:**

- Method: `POST`
- URL (Expression):

```javascript
{{ 'http://api:8000/api/v1/notifications/' + $('Split Out').item.json.id + '/failed' }}
```

- Body JSON (Expression):

```javascript
{{ {
  "claim_token": $('Split Out').item.json.claim_token,
  "error_message": String($json.error?.message ?? "Falha no envio SMTP").slice(0, 1000)
} }}
```

Em ambos, habilite o envio de body como JSON e selecione a credencial **LogiFlow  - API Key**. As expressões acima são as utilizadas no JSON do projeto; não substitua o token por um valor fixo.

#### 9.9. Validar a execução de ponta a ponta

Antes do teste, confirme que `ALERTS_EMAIL_TO` corresponde a um endereço sob seu controle e que a API carregou essa configuração. Não reenvie notificações antigas com status `sent` nem reinicie manualmente o contador de tentativas das notificações `failed`.

1. Execute **Monitoring Delays** manualmente. Se não houver novos incidentes, a execução pode não criar notificações — comportamento correto.
2. Havendo uma **nova notificação elegível**, execute **Notification Outbox Worker** uma vez.
3. Confira o caminho verde `Schedule Trigger → Claim Notifications → If → Split Out → Send an Email → Confirm Sent`.
4. Confirme o recebimento na caixa Gmail autorizada.
5. Confira a persistência no PostgreSQL **operacional** (`127.0.0.1:5433`, banco `logiflow`):

```sql
SELECT
    id,
    incident_id,
    status,
    attempts,
    next_attempt_at,
    sent_at,
    last_error
FROM public.notification_outbox
ORDER BY id DESC
LIMIT 10;
```

Para validar uma ocorrência específica, filtre pelo `incident_id` informado no e-mail. O esperado após confirmação bem-sucedida é `status = 'sent'` e `sent_at` preenchido.

**Evidência já observada no projeto:** um e-mail do incidente `#60`, remessa `DEMO-2026-TRK-0010`, chegou ao Gmail de teste, e o n8n exibiu os nós **Send an Email** e **Confirm Sent** executados com sucesso. Isso demonstra o caminho de sucesso; não comprova, por si só, que o caminho **Confirm Failed** foi exercitado.

#### 9.10. Problemas comuns

| Sintoma | Causa provável | O que verificar |
|---|---|---|
| `401` ou `403` nos nós HTTP | Chave ausente/incorreta | `X-API-Key`, valor de `MONITORING_API_KEY` e credencial associada |
| Erro de conexão em `localhost:8000` | URL incorreta dentro do Docker | Usar `http://api:8000` no n8n |
| `items: []`, `total: 0` | Fila sem itens elegíveis | Consultar status e tentativas no PostgreSQL; não forçar reenvio |
| `created_incidents: 0` | Incidentes já existentes | Verificar idempotência e histórico de monitoramento |
| SMTP falha na autenticação | Senha normal ou configuração errada | Senha de app, `smtp.gmail.com`, porta `465`, SSL/TLS |
| E-mail não chegou | Destinatário, spam ou envio não confirmado | Conferir `recipient`, Gmail, saída do SMTP e `Confirm Sent` |
| `Confirm Sent` falha | ID/token ausente ou reserva inválida | Conferir `id` e `claim_token` do `Split Out` e a resposta da API |
| `Confirm Failed` não executa | Tratamento de erro não configurado | `On Error → Continue (using error output)` e conexão Error |
| Credenciais deixam de funcionar após recriação | Chave de criptografia alterada | Manter `N8N_ENCRYPTION_KEY` estável e preservar volume do n8n |

**Importante:** o padrão Outbox aqui usa processamento *at-least-once*. Se o Gmail aceitar um envio e a confirmação HTTP falhar, uma tentativa posterior poderá produzir e-mail duplicado. Não anuncie garantia de entrega exatamente uma vez.

#### 9.11. Ativar agendamentos depois dos testes

Depois de validar autenticação, destinatário, SMTP, tratamento de erros e persistência, salve e **publique/ative** os dois workflows na interface do n8n. O workflow de monitoramento importado usa intervalo de **15 minutos**. Confira o intervalo configurado no **Schedule Trigger** do worker antes de publicá-lo. Na versão do n8n exibida neste projeto, o botão de publicação aparece como **Publish**.

Se desejar registrar evidências no repositório, salve capturas **sem credenciais ou dados sensíveis** em `docs/images/`, mostrando o monitoramento, o caminho de sucesso do worker, o e-mail de teste e o histórico de execução.

### 10. Testar a aplicação com PostgreSQL isolado

**Não execute a suíte de integração contra `logiflow` na porta 5433.** Para uma instância descartável de testes, utilize outro contêiner:

```powershell
docker run -d --name logiflow-ci-postgres `
  -e POSTGRES_USER=logiflow_ci `
  -e POSTGRES_PASSWORD=ci_local_password `
  -e POSTGRES_DB=logiflow_test `
  -p 127.0.0.1:5434:5432 postgres:17
```

Se esse contêiner já existir, use `docker start logiflow-ci-postgres`. Aguarde ficar pronto:

```powershell
docker exec logiflow-ci-postgres pg_isready -U logiflow_ci -d logiflow_test
```

No **mesmo terminal**, defina explicitamente o destino das migrações e dos testes:

```powershell
$env:DB_HOST = '127.0.0.1'
$env:DB_PORT = '5434'
$env:DB_NAME = 'logiflow_test'
$env:DB_USER = 'logiflow_ci'
$env:DB_PASSWORD = 'ci_local_password'
$env:TEST_DATABASE_URL = 'postgresql+psycopg://logiflow_ci:ci_local_password@127.0.0.1:5434/logiflow_test'

uv run alembic upgrade head
uv run ruff check .
uv run pytest -ra -q
```

**Verifique `DB_PORT=5434` e `DB_NAME=logiflow_test` antes de executar o Alembic.** Ao terminar, feche esse terminal ou remova as variáveis de teste antes de voltar ao banco operacional. O teste local anterior do projeto registrou 91 testes aprovados, mas esse resultado não substitui uma nova execução no seu ambiente.

### 11. Power BI

Abra `dashboard/dashboard-logiflow.pbix` no Power BI Desktop. Ajuste a origem de dados para `127.0.0.1:5433`, banco `logiflow`, utilizando preferencialmente o usuário de leitura analítica. Execute os scripts `sql/analytics/` antes de atualizar o relatório. Os dados carregados no arquivo PBIX podem representar um snapshot anterior e não refletem automaticamente as alterações no banco.

### 12. Encerrar, reiniciar e diagnosticar

```powershell
# Parar serviços, preservando os volumes:
docker compose down
# Reiniciar serviços:
docker compose up -d
# Ver logs:
docker compose logs --tail=100 api postgres n8n
# Estado dos serviços:
docker compose ps
```

**Não use `docker compose down -v`**, pois isso remove os volumes persistentes do PostgreSQL e do n8n.

**Erros comuns:**

- **API responde 500/503 na conexão:** confira `docker compose ps`, logs e `uv run alembic current` com `DB_PORT=5433`.
- **Alembic tenta porta 5432 no Windows:** ajuste `DB_HOST=127.0.0.1`, `DB_PORT=5433` no PowerShell ou `.env`.
- **n8n retorna 401:** confira `X-API-Key` e `MONITORING_API_KEY` no Compose.
- **Workflow termina antes de SMTP:** confira `Claim Notifications`; fila vazia é um resultado válido.
- **E-mail destinado a `operacoes@example.com`:** configure `ALERTS_EMAIL_TO` e repasse-o em `api.environment` do Compose; depois recrie o serviço API com `docker compose up -d --build api`.
- **Testes falham por conexão:** confirme que o contêiner de testes está ativo em `5434` e que `TEST_DATABASE_URL` aponta para `logiflow_test`.
- **Conflito de portas:** verifique se 5433, 5434, 8000 e 5678 já estão ocupadas.

---

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

[Visualizar execuções do GitHub Actions](https://github.com/rafaelporfiriobarros/logiflow/actions)

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
logiflow/
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
│   └── logiflow/
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

O LogiFlow  foi desenvolvido como projeto de portfólio para demonstrar competências em:

**Engenharia de Dados, Analytics, SQL, Python, APIs REST, automação, modelagem de dados, testes, observabilidade, integração contínua e visualização de indicadores.**

O foco está na construção de uma solução integrada, com regras de negócio, rastreabilidade e práticas de desenvolvimento aplicáveis a ambientes corporativos.#   l o g i f l o w  
 