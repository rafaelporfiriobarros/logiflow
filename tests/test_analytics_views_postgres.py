
from pathlib import Path

import pytest
from sqlalchemy import text

SQL_FILE = (
    Path(__file__).resolve().parents[1]
    / "sql"
    / "analytics"
    / "001_observability_views.sql"
)


@pytest.fixture(scope="module")
def analytics_engine(postgres_test_session_factory):
    engine = postgres_test_session_factory.kw["bind"]

    if not SQL_FILE.is_file():
        pytest.fail(
            f"Arquivo SQL não encontrado: {SQL_FILE}"
        )

    sql_script = SQL_FILE.read_text(encoding="utf-8")

    # Divide o script nas instruções SQL.
    statements = [
        statement.strip()
        for statement in sql_script.split(";")
        if statement.strip()
    ]

    # Executa todas as instruções em uma transação.
    with engine.begin() as connection:
        for statement in statements:
            connection.exec_driver_sql(statement)

    return engine


def test_analytics_views_exist(analytics_engine):
    expected = {
        "incident_summary",
        "notification_summary",
        "monitoring_history",
    }

    with analytics_engine.connect() as connection:
        result = connection.execute(
            text("""
                SELECT table_name
                FROM information_schema.views
                WHERE table_schema = 'analytics'
            """)
        )

        existing = {row[0] for row in result}

    assert expected.issubset(existing)


def test_analytics_reconciliation(analytics_engine):
    with analytics_engine.connect() as connection:
        result = connection.execute(
            text("""
                SELECT
                    (
                        SELECT COUNT(*)
                        FROM public.incidents
                    ) = (
                        SELECT COALESCE(
                            SUM(total_incidents), 0
                        )
                        FROM analytics.incident_summary
                    ) AS incidents_ok,

                    (
                        SELECT COUNT(*)
                        FROM public.notification_outbox
                    ) = (
                        SELECT COALESCE(
                            SUM(total_notifications), 0
                        )
                        FROM analytics.notification_summary
                    ) AS notifications_ok,

                    (
                        SELECT COUNT(*)
                        FROM public.monitoring_runs
                    ) = (
                        SELECT COUNT(*)
                        FROM analytics.monitoring_history
                    ) AS monitoring_ok
            """)
        ).mappings().one()

    assert result["incidents_ok"]
    assert result["notifications_ok"]
    assert result["monitoring_ok"]


def test_monitoring_duration_is_valid(analytics_engine):
    with analytics_engine.connect() as connection:
        invalid_count = connection.scalar(
            text("""
                SELECT COUNT(*)
                FROM analytics.monitoring_history
                WHERE duration_seconds < 0
            """)
        )

    assert invalid_count == 0


def test_monitoring_run_ids_are_unique(analytics_engine):
    with analytics_engine.connect() as connection:
        duplicate_count = connection.scalar(
            text("""
                SELECT COUNT(*)
                FROM (
                    SELECT monitoring_run_id
                    FROM analytics.monitoring_history
                    GROUP BY monitoring_run_id
                    HAVING COUNT(*) > 1
                ) AS duplicates
            """)
        )

    assert duplicate_count == 0
