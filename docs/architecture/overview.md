# LogiFlow AI — Arquitetura Técnica

## 1. Visão geral

O LogiFlow AI é uma plataforma de automação e monitoramento operacional de logística, desenvolvida para identificar atrasos em remessas, registrar incidentes, automatizar notificações e disponibilizar indicadores para análise.

O projeto utiliza Python, FastAPI, PostgreSQL, SQLAlchemy, n8n, Docker e Power BI.

## 2. Objetivos

- Identificar automaticamente remessas com atrasos.
- Registrar incidentes com rastreabilidade.
- Evitar a criação duplicada de incidentes ativos do mesmo tipo para uma remessa.
- Gerenciar notificações por meio de uma fila persistente.
- Controlar tentativas de envio e falhas.
- Disponibilizar indicadores operacionais e de observabilidade.
- Validar regras de negócio por meio de testes automatizados.

## 3. Componentes

### FastAPI

Responsável por disponibilizar os endpoints de monitoramento, notificações e observabilidade.

Principais endpoints:

- `POST /api/v1/monitoring/delays`
- `POST /api/v1/notifications/claim`
- `POST /api/v1/notifications/{id}/sent`
- `POST /api/v1/notifications/{id}/failed`
- `GET /api/v1/observability/summary`

### PostgreSQL

Banco de dados relacional utilizado para persistência de remessas, incidentes, notificações e histórico das execuções.

A camada analítica é disponibilizada pelo schema `analytics`.

### n8n

Responsável pela orquestração dos workflows:

**Workflow de monitoramento:** executa periodicamente a identificação de atrasos por meio da API.

**Notification Outbox Worker:** reserva notificações elegíveis, realiza o envio por SMTP e informa à API o resultado da tentativa.

### Power BI

Responsável pela visualização dos indicadores operacionais, utilizando views PostgreSQL e uma conta dedicada de leitura.

## 4. Fluxo operacional

1. O n8n aciona o endpoint de monitoramento.
2. A API identifica remessas elegíveis para incidentes de atraso.
3. O PostgreSQL armazena novos incidentes e registros de notificação.
4. O worker do n8n consulta a fila de notificações.
5. A API reserva registros para processamento.
6. O worker tenta realizar o envio por SMTP.
7. A API recebe a confirmação de sucesso ou falha.
8. O histórico fica disponível para consultas analíticas e observabilidade.

## 5. Confiabilidade

O sistema implementa mecanismos de confiabilidade, incluindo:

- Restrição de unicidade para evitar incidentes ativos duplicados do mesmo tipo por remessa.
- Fila de notificações persistente.
- Reserva de notificações por token.
- Controle de tentativas de envio.
- Recuperação de reservas expiradas.
- Testes automatizados de integração e regras de negócio.

A entrega de notificações segue uma abordagem de processamento *at-least-once*. Portanto, existe possibilidade de duplicação do e-mail caso o SMTP aceite o envio, mas a confirmação posterior não seja registrada.

## 6. Segurança

- Autenticação dos endpoints protegidos por chave de API.
- Credenciais configuráveis por variáveis de ambiente.
- Usuário PostgreSQL exclusivo para consultas analíticas.
- Separação entre permissões operacionais e permissões de leitura.
- Banco de testes isolado do banco operacional.

## 7. Analytics

O schema `analytics` disponibiliza:

- `incident_summary`
- `incident_details`
- `notification_summary`
- `notification_details`
- `monitoring_history`

Os dashboards desenvolvidos no Power BI são:

1. Visão Geral
2. Monitoramento
3. Incidentes
4. Notificações

## 8. Qualidade

O projeto utiliza Ruff e pytest.

Na última execução validada, a suíte apresentou **91 testes aprovados**. A análise estática foi aprovada anteriormente, restando confirmar a correção automática dos imports do último arquivo de testes.

## 9. Limitações e próximas evoluções

- Implementar monitoramento proativo de falhas e acúmulo na fila.
- Ampliar os testes de segurança e autorização.
- Criar pipeline de integração contínua.
- Definir políticas de retenção de dados.
- Documentar procedimentos de recuperação.
- Revisar a segurança dos campos expostos nas views analíticas.
- Preparar a implantação em ambiente de produção.
