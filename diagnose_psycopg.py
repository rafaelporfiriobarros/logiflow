from time import perf_counter

import psycopg

from logiflow.core.config import get_settings

settings = get_settings()

start = perf_counter()

print("Conectando diretamente com Psycopg...")

with psycopg.connect(
    host=settings.db_host,
    port=settings.db_port,
    dbname=settings.db_name,
    user=settings.db_user,
    password=settings.db_password,
    connect_timeout=5,
) as conn:
    print(
        "Tempo de conexão:",
        round(perf_counter() - start, 3),
        "segundos",
    )

    with conn.cursor() as cursor:
        cursor.execute("SELECT 1")
        print("Resultado:", cursor.fetchone())