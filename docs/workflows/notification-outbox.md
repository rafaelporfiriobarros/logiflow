# LogiFlow — Notification Outbox Worker

## Objetivo

Processar notificações persistidas no PostgreSQL, realizar tentativas de envio por e-mail e registrar os resultados de forma rastreável.

## Componentes

- Orquestração: n8n
- API: FastAPI
- Banco: PostgreSQL
- Protocolo de envio: SMTP
- Autenticação da API: `X-API-Key`

## Configuração do workflow

| Nó | Função |
|---|---|
| Schedule Trigger | Inicia a cada 5 minutos |
| Claim Notifications | Reserva notificações disponíveis |
| IF | Verifica se existem notificações |
| Split Out | Separa os itens retornados |
| Send an Email | Executa a tentativa SMTP |
| Confirm Sent | Confirma o envio na API |
| Confirm Failed | Registra uma tentativa com falha |

## Reserva de notificações

Endpoint:

`POST /api/v1/notifications/claim`

Corpo da requisição:

```json
{
  "limit": 1
}
```

O backend seleciona notificações elegíveis e utiliza bloqueio de linhas no PostgreSQL para evitar que dois workers reservem simultaneamente o mesmo registro.

A reserva possui um `claim_token` e um prazo de validade de 10 minutos.

## Processamento

1. O n8n consulta a fila de notificações.
2. A API reserva um registro elegível.
3. O IF verifica se a resposta contém itens.
4. O Split Out disponibiliza o item para processamento.
5. O nó Send an Email tenta realizar o envio por SMTP.
6. Em caso de sucesso, o worker chama o endpoint `/sent`.
7. Em caso de erro SMTP, o worker chama o endpoint `/failed`.

## Confirmação de sucesso

Endpoint:

`POST /api/v1/notifications/{id}/sent`

O corpo contém o token da reserva:

```json
{
  "claim_token": "<token-da-reserva>"
}
```

## Confirmação de falha

Endpoint:

`POST /api/v1/notifications/{id}/failed`

Exemplo de estrutura:

```json
{
  "claim_token": "<token-da-reserva>",
  "error_message": "Falha no envio SMTP"
}
```

## Reprocessamento

O backend controla as tentativas de processamento.

As notificações podem ser novamente elegíveis após uma falha ou expiração da reserva, respeitando o limite configurado de três tentativas.

## Concorrência e segurança

O mecanismo de reserva utiliza `FOR UPDATE SKIP LOCKED`, permitindo que workers concorrentes evitem selecionar a mesma linha bloqueada.

O token de reserva deve ser válido para que a confirmação seja aceita.

Confirmações com tokens inválidos ou expirados são rejeitadas.

## Garantia de processamento

A estratégia é de processamento *at-least-once*.

Isso significa que o sistema procura não perder notificações elegíveis, mas não garante que o destinatário receba o e-mail exatamente uma vez.

Se o servidor SMTP aceitar a mensagem e a confirmação posterior falhar, a notificação poderá ser reprocessada.

## Validação realizada

O fluxo foi validado com:

- Reserva de notificações.
- Envio SMTP.
- Confirmação de sucesso.
- Registro de falhas.
- Controle de tentativas.
- Persistência dos resultados no PostgreSQL.

## Limitações atuais

- O workflow processa um item por execução (`limit = 1`).
- O fluxo atual não foi preparado para aumentar esse limite sem revisar as expressões que recuperam o token do item.
- A confirmação `sent` não equivale à confirmação de entrega na caixa postal.
- Ainda não existe um mecanismo externo de deduplicação de e-mails aceitos pelo SMTP.
