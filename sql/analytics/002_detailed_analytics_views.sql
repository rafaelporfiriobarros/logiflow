
-- =========================================================
-- LOGIFLOW | ANALYTICS DETAIL LAYER
-- =========================================================

-- Uma linha por incidente.
CREATE OR REPLACE VIEW analytics.incident_details AS
SELECT
    i.id AS incident_id,
    i.shipment_id,
    s.order_id,
    s.tracking_code,
    s.status AS shipment_status,

    i.incident_type,
    i.severity,
    i.status AS incident_status,

    i.created_at AS incident_created_at,
    s.created_at AS shipment_created_at,
    s.expected_delivery_at,
    s.delivered_at,

    CASE
        WHEN i.status = 'open' THEN 1
        ELSE 0
    END AS is_open,

    CASE
        WHEN s.delivered_at IS NULL
             AND s.expected_delivery_at < CURRENT_TIMESTAMP
        THEN 1
        ELSE 0
    END AS is_currently_delayed,

    CASE
        WHEN s.delivered_at IS NOT NULL
             AND s.expected_delivery_at IS NOT NULL
             AND s.delivered_at > s.expected_delivery_at
        THEN 1
        ELSE 0
    END AS was_delivered_late

FROM public.incidents AS i
INNER JOIN public.shipments AS s
    ON s.id = i.shipment_id;


-- Uma linha por notificação.
CREATE OR REPLACE VIEW analytics.notification_details AS
SELECT
    n.id AS notification_id,
    n.incident_id,
    i.shipment_id,
    s.tracking_code,

    i.incident_type,
    i.severity AS incident_severity,

    n.channel,
    n.status AS notification_status,
    n.recipient,
    n.subject,

    n.attempts,
    n.next_attempt_at,
    n.locked_at,
    n.sent_at,
    n.last_error,

    n.created_at AS notification_created_at,
    n.updated_at AS notification_updated_at,

    CASE
        WHEN n.status = 'sent' THEN 1
        ELSE 0
    END AS is_sent,

    CASE
        WHEN n.status = 'failed' THEN 1
        ELSE 0
    END AS is_failed,

    CASE
        WHEN n.status = 'pending' THEN 1
        ELSE 0
    END AS is_pending,

    CASE
        WHEN n.sent_at IS NOT NULL
        THEN ROUND(
            EXTRACT(
                EPOCH FROM (
                    n.sent_at - n.created_at
                )
            )::numeric,
            3
        )
        ELSE NULL
    END AS delivery_latency_seconds

FROM public.notification_outbox AS n
INNER JOIN public.incidents AS i
    ON i.id = n.incident_id
INNER JOIN public.shipments AS s
    ON s.id = i.shipment_id;
