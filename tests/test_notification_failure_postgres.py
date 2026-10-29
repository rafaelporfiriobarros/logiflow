import os
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from logiflow.models.notification_outbox import NotificationOutbox
from logiflow.services.notification_queue import (
    MAX_ATTEMPTS,
    claim_notifications,
    mark_notification_failed,
)

NOTIFICATION_ID = 1


@pytest.fixture
def engine():
    url = os.environ.get("TEST_DATABASE_URL")

    if not url:
        pytest.fail("TEST_DATABASE_URL não configurada.")

    parsed = make_url(url)

    if parsed.database != "logiflow_test":
        pytest.fail("Banco diferente de logiflow_test.")

    if not parsed.drivername.startswith("postgresql"):
        pytest.fail("Este teste exige PostgreSQL.")

    engine = create_engine(url, pool_pre_ping=True)

    try:
        with engine.connect() as connection:
            if connection.exec_driver_sql(
                "SELECT current_database()"
            ).scalar_one() != "logiflow_test":
                pytest.fail("Conexão fora do banco de testes.")

        yield engine
    finally:
        engine.dispose()


def test_notification_failure_and_retry(engine):
    base_time = datetime.now(UTC)

    with Session(engine) as db:
        notification = db.get(NotificationOutbox, NOTIFICATION_ID)

        assert notification is not None
        assert notification.recipient == "teste-logiflow@example.invalid"
        assert notification.status == "pending"
        assert notification.attempts == 0

        # A transação não será confirmada.
        # Ao final do teste, todas as alterações serão revertidas.

        for attempt in range(1, MAX_ATTEMPTS + 1):
            current_time = base_time + timedelta(hours=attempt)

            claimed = claim_notifications(
                db,
                limit=1,
                now=current_time,
                notification_id=NOTIFICATION_ID,
            )

            assert len(claimed) == 1

            notification = claimed[0]

            assert notification.status == "sending"
            assert notification.attempts == attempt
            assert notification.claim_token is not None

            token = notification.claim_token

            mark_notification_failed(
                db,
                notification_id=NOTIFICATION_ID,
                claim_token=token,
                error_message=f"Falha simulada {attempt}",
                now=current_time + timedelta(seconds=1),
            )

            db.flush()
            db.refresh(notification)

            assert notification.status == "failed"
            assert notification.attempts == attempt
            assert notification.claim_token is None
            assert notification.locked_at is None
            assert notification.last_error == f"Falha simulada {attempt}"

        # Após três tentativas, não pode haver uma quarta reserva.
        claimed_again = claim_notifications(
            db,
            limit=1,
            now=base_time + timedelta(days=2),
            notification_id=NOTIFICATION_ID,
        )

        assert claimed_again == []

        db.rollback()