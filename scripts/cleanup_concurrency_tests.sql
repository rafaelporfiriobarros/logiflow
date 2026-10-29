
BEGIN;

-- Bloqueia a execução fora do banco de testes.
DO $$
BEGIN
    IF current_database() <> 'logiflow_test' THEN
        RAISE EXCEPTION
            'Limpeza bloqueada fora de logiflow_test';
    END IF;
END
$$;

-- Identifica exclusivamente os registros históricos.
CREATE TEMP TABLE cleanup_targets
ON COMMIT DROP AS
SELECT
    n.id AS notification_id,
    i.id AS incident_id,
    s.id AS shipment_id,
    o.id AS order_id,
    c.id AS customer_id
FROM notification_outbox n
JOIN incidents i
    ON i.id = n.incident_id
JOIN shipments s
    ON s.id = i.shipment_id
JOIN orders o
    ON o.id = s.order_id
JOIN customers c
    ON c.id = o.customer_id
WHERE n.id <> 1
  AND n.status = 'sending'
  AND n.attempts = 1
  AND n.recipient = 'operacoes@example.com'
  AND o.order_number LIKE 'ORD-CONC-%'
  AND s.tracking_code LIKE 'TRK-CONC-%';

-- Mostra a quantidade encontrada.
SELECT
    COUNT(*) AS registros_identificados
FROM cleanup_targets;

-- Verificações obrigatórias antes de excluir.
DO $$
BEGIN
    IF (SELECT COUNT(*) FROM cleanup_targets) <> 15 THEN
        RAISE EXCEPTION
            'Quantidade inesperada de registros';
    END IF;

    -- Impede excluir clientes com outros pedidos.
    IF EXISTS (
        SELECT 1
        FROM orders o
        JOIN cleanup_targets t
            ON t.customer_id = o.customer_id
        WHERE NOT EXISTS (
            SELECT 1
            FROM cleanup_targets x
            WHERE x.order_id = o.id
        )
    ) THEN
        RAISE EXCEPTION
            'Cliente possui pedidos fora do escopo';
    END IF;

    -- Impede excluir pedidos com outras remessas.
    IF EXISTS (
        SELECT 1
        FROM shipments s
        JOIN cleanup_targets t
            ON t.order_id = s.order_id
        WHERE NOT EXISTS (
            SELECT 1
            FROM cleanup_targets x
            WHERE x.shipment_id = s.id
        )
    ) THEN
        RAISE EXCEPTION
            'Pedido possui remessas fora do escopo';
    END IF;

    -- Impede excluir remessas com outros incidentes.
    IF EXISTS (
        SELECT 1
        FROM incidents i
        JOIN cleanup_targets t
            ON t.shipment_id = i.shipment_id
        WHERE NOT EXISTS (
            SELECT 1
            FROM cleanup_targets x
            WHERE x.incident_id = i.id
        )
    ) THEN
        RAISE EXCEPTION
            'Remessa possui incidentes fora do escopo';
    END IF;

    -- Impede excluir incidentes com outras notificações.
    IF EXISTS (
        SELECT 1
        FROM notification_outbox n
        JOIN cleanup_targets t
            ON t.incident_id = n.incident_id
        WHERE NOT EXISTS (
            SELECT 1
            FROM cleanup_targets x
            WHERE x.notification_id = n.id
        )
    ) THEN
        RAISE EXCEPTION
            'Incidente possui notificações fora do escopo';
    END IF;
END
$$;

-- Exclui somente as notificações selecionadas.
DELETE FROM notification_outbox
WHERE id IN (
    SELECT notification_id FROM cleanup_targets
);

-- Exclui os incidentes correspondentes.
DELETE FROM incidents
WHERE id IN (
    SELECT incident_id FROM cleanup_targets
);

-- Exclui as remessas correspondentes.
DELETE FROM shipments
WHERE id IN (
    SELECT shipment_id FROM cleanup_targets
);

-- Exclui os pedidos correspondentes.
DELETE FROM orders
WHERE id IN (
    SELECT order_id FROM cleanup_targets
);

-- Exclui os clientes correspondentes.
DELETE FROM customers
WHERE id IN (
    SELECT customer_id FROM cleanup_targets
);

-- Mantenha ROLLBACK na primeira execução.
COMMIT;
