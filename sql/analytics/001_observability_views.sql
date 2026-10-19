
CREATE SCHEMA IF NOT EXISTS analytics;

-- 1. Resumo de incidentes por status.
CREATE OR REPLACE VIEW analytics.incident_summary AS
SELECT
    status,
    COUNT(*)::bigint AS total_incidents
FROM public.incidents
GROUP BY status;


-- 2. Resumo da fila de notificações.
CREATE OR REPLACE VIEW analytics.notification_summary AS
SELECT
    status,
    COUNT(*)::bigint AS total_notifications,
    COALESCE(SUM(attempts), 0)::bigint AS total_attempts,
    COUNT(*) FILTER (
        WHERE attempts >= 3
    )::bigint AS notifications_with_3_or_more_attempts
FROM public.notification_outbox
GROUP BY status;


-- 3. Histórico das execuções de monitoramento.
CREATE OR REPLACE VIEW analytics.monitoring_history AS
SELECT
    id AS monitoring_run_id,
    status,
    started_at,
    finished_at,
    delayed_shipments,
    created_incidents,
    existing_incidents,
    error_message,

    CASE
        WHEN finished_at IS NOT NULL
        THEN ROUND(
            EXTRACT(
                EPOCH FROM (finished_at - started_at)
            )::numeric,
            3
        )
        ELSE NULL
    END AS duration_seconds

FROM public.monitoring_runs;

