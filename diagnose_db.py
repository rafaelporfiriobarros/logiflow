from time import perf_counter

from sqlalchemy import create_engine, text

from logiflow.core.config import get_settings

settings = get_settings()

engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    connect_args={"connect_timeout": 5},
)

start = perf_counter()

print("Iniciando conexão...")

with engine.connect() as connection:
    print(
        "Tempo para conectar:",
        round(perf_counter() - start, 3),
        "segundos",
    )

    query_start = perf_counter()

    result = connection.execute(
        text("SELECT 1")
    ).scalar_one()

    print("Resultado:", result)

    print(
        "Tempo da consulta:",
        round(perf_counter() - query_start, 3),
        "segundos",
    )

engine.dispose()