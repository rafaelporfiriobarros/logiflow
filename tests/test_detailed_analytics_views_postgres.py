
from pathlib import Path

import pytest
from sqlalchemy import text

SQL_FILE = (
    Path(__file__).resolve().parents[1]
    / "sql"
    / "analytics"
    / "002_detailed_analytics_views.sql"
)


@pytest.fixture(scope="module")
def detailed_analytics_engine(postgres_test_session_factory):
    engine = postgres_test_session_factory.kw["bind"]

    if not SQL_FILE.is_file():
        pytest.fail(f"Arquivo SQL não encontrado: {SQL_FILE}")

    sql_script = SQL_FILE.read_text(encoding="utf-8")

    statements = [
        statement.strip()
        for statement in sql_script.split(";")
        if statement.strip()
    ]

    # Aplica as views somente no banco logiflow_test.
    with engine.begin() as connection:
        connection.execute(
            text("CREATE SCHEMA IF NOT EXISTS analytics")
        )

        for statement in statements:
            connection.exec_driver_sql(statement)

    return engine


def test_detailed_views_exist(detailed_analytics_engine):
    expected = {
        "incident_details",
        "notification_details",
    }

    with detailed_analytics_engine.connect() as connection:
        rows = connection.execute(
            text("""
                SELECT table_name
                FROM information_schema.views
                WHERE table_schema = 'analytics'
            """)
        )

        existing = {row[0] for row in rows}

    assert expected.issubset(existing)


def test_incident_details_reconciliation(detailed_analytics_engine):
    with detailed_analytics_engine.connect() as connection:
        result = connection.execute(
            text("""
                SELECT
                    (SELECT COUNT(*) FROM public.incidents)
                        AS source_total,
                    (SELECT COUNT(*) FROM analytics.incident_details)
                        AS analytics_total
            """)
        ).one()

    assert result.source_total == result.analytics_total


def test_notification_details_reconciliation(detailed_analytics_engine):
    with detailed_analytics_engine.connect() as connection:
        result = connection.execute(
            text("""
                SELECT
                    (SELECT COUNT(*) FROM public.notification_outbox)
                        AS source_total,
                    (SELECT COUNT(*) FROM analytics.notification_details)
                        AS analytics_total
            """)
        ).one()

    assert result.source_total == result.analytics_total


def test_detailed_views_unique_ids(detailed_analytics_engine):
    with detailed_analytics_engine.connect() as connection:
        duplicates = connection.execute(
            text("""
                SELECT
                    (
                        SELECT COUNT(*)
                        FROM (
                            SELECT incident_id
                            FROM analytics.incident_details
                            GROUP BY incident_id
                            HAVING COUNT(*) > 1
                        ) AS duplicated_incidents
                    ) AS incident_duplicates,

                    (
                        SELECT COUNT(*)
                        FROM (
                            SELECT notification_id
                            FROM analytics.notification_details
                            GROUP BY notification_id
                            HAVING COUNT(*) > 1
                        ) AS duplicated_notifications
                    ) AS notification_duplicates
            """)
        ).one()

    assert duplicates.incident_duplicates == 0
    assert duplicates.notification_duplicates == 0


def test_notification_latency_non_negative(detailed_analytics_engine):
    with detailed_analytics_engine.connect() as connection:
        invalid_count = connection.scalar(
            text("""
                SELECT COUNT(*)
                FROM analytics.notification_details
                WHERE delivery_latency_seconds < 0
            """)
        )

    assert invalid_count == 0
