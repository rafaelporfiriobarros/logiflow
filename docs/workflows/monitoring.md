# LogiFlow AI — Workflow de Monitoramento

## Objetivo

Automatizar a identificação de remessas atrasadas, criando incidentes e notificações pendentes de maneira controlada.

## Componentes

- Orquestrador: n8n
- API: FastAPI
- Persistência: PostgreSQL
- Autenticação: header `X-API-Key`

## Configuração do workflow

| Nó | Configuração |
|---|---|
| Schedule Trigger | Intervalo de 15 minutos |
| HTTP Request | Método POST |
| URL interna | `http://api:8000/api/v1/monitoring/delays` |
| Autenticação | Header Auth |

## Funcionamento

1. O Schedule Trigger inicia o workflow.
2. O HTTP Request aciona o endpoint de monitoramento.
3. A API consulta as remessas elegíveis.
4. O serviço identifica atrasos e verifica incidentes existentes.
5. Novos incidentes são persistidos no PostgreSQL.
6. As notificações correspondentes são registradas na tabela `notification_outbox`.
7. O resultado da execução é registrado em `monitoring_runs`.

## Regras de negócio

Uma remessa pode possuir incidentes de tipos diferentes.

Para evitar duplicidade de incidentes ativos do mesmo tipo, o PostgreSQL utiliza uma restrição de unicidade parcial para incidentes com status `open`.

A fila de notificações também possui restrição de unicidade por incidente e canal.

A execução repetida do monitoramento não deve criar novos registros quando os incidentes e notificações correspondentes já existem.

## Tratamento de erros

Erros na chamada HTTP devem ser investigados no histórico de execuções do n8n e nos registros da API.

O workflow não envia e-mails diretamente. O processamento das notificações é responsabilidade de outro workflow.

## Validação

O monitoramento foi validado com execuções automáticas, criação de incidentes e inserção de notificações na fila.

## Limitações

- O agendamento depende da disponibilidade do n8n.
- O endpoint depende da disponibilidade da API e do PostgreSQL.
- Alertas externos para falhas do workflow ainda são uma evolução planejada.
