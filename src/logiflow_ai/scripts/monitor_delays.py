from logiflow_ai.db.session import SessionLocal
from logiflow_ai.services.delay_monitor import detect_delivery_delays


def main() -> None:
    with SessionLocal() as db:
        try:
            result = detect_delivery_delays(db)
            db.commit()
        except Exception:
            db.rollback()
            raise

    print("LOGIFLOW AI | MONITORAMENTO DE ATRASOS")
    print("=" * 45)
    print(f"Remessas atrasadas: {result.delayed_shipments}")
    print(f"Incidentes criados: {result.created_incidents}")
    print(f"Incidentes existentes: {result.existing_incidents}")
    print("Monitoramento concluído.")


if __name__ == "__main__":
    main()
