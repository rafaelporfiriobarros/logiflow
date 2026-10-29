from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from logiflow.core.config import get_settings
from logiflow.models.monitoring_run import MonitoringRun
from logiflow.services.delay_monitor import (
    detect_delivery_delays,
)
from logiflow.services.notification_service import (
    enqueue_incident_notifications,
)


class MonitoringRunNotFoundError(Exception):
    pass


def execute_delay_monitoring(
    session_factory,
) -> MonitoringRun:
    """
    Executa o monitoramento e registra auditoria.

    Cada execução utiliza sua própria sessão,
    permitindo chamadas pela API ou por scripts.
    """

    # Primeira transação: registra o início.
    with session_factory() as db:
        run = MonitoringRun(
            started_at=datetime.now(UTC),
            status="running",
            delayed_shipments=0,
            created_incidents=0,
            existing_incidents=0,
        )

        db.add(run)
        db.commit()
        db.refresh(run)

        run_id = run.id

    # Segunda transação: detecção e conclusão.
    try:
        with session_factory() as db:
            result = detect_delivery_delays(db)

            if result.created_incident_ids:
                enqueue_incident_notifications(
                    db=db,
                    incident_ids=result.created_incident_ids,
                    recipient=get_settings().alerts_email_to,
                )

            run = db.get(MonitoringRun, run_id)

            run.delayed_shipments = result.delayed_shipments
            run.created_incidents = result.created_incidents
            run.existing_incidents = result.existing_incidents

            run.status = "success"
            run.finished_at = datetime.now(UTC)

            db.commit()
            db.refresh(run)

            return run

    except Exception as exc:
        # A transação anterior é revertida ao fechar
        # a sessão sem commit.
        #
        # Registramos a falha em uma nova transação.
        with session_factory() as db:
            run = db.get(MonitoringRun, run_id)

            if run is not None:
                run.status = "failed"
                run.finished_at = datetime.now(UTC)
                run.error_message = (f"{type(exc).__name__}: {exc}")[:1000]

                db.commit()

        raise


def list_monitoring_runs(
    db: Session,
    limit: int = 20,
    offset: int = 0,
) -> tuple[list[MonitoringRun], int]:
    total = db.scalar(select(func.count()).select_from(MonitoringRun)) or 0

    runs = db.scalars(
        select(MonitoringRun)
        .order_by(
            MonitoringRun.started_at.desc(),
            MonitoringRun.id.desc(),
        )
        .limit(limit)
        .offset(offset)
    ).all()

    return list(runs), total


def get_monitoring_run(
    db: Session,
    run_id: int,
) -> MonitoringRun:
    run = db.get(MonitoringRun, run_id)

    if run is None:
        raise MonitoringRunNotFoundError(f"Execução {run_id} não encontrada.")

    return run
