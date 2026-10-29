from time import perf_counter

import psycopg

from logiflow.core.config import get_settings

settings = get_settings()

start = perf_counter()

with psycopg.connect(
    hostaddr="127.0.0.1",
    port=settings.db_port,
    dbname=settings.db_name,
    user=settings.db_user,
    password=settings.db_password,
    connect_timeout=3,
    sslmode="disable",
    gssencmode="disable",
) as conn:
    elapsed = perf_counter() - start

    with conn.cursor() as cursor:
        cursor.execute("SELECT 1")
        result = cursor.fetchone()

print(f"Tempo de conexão: {elapsed:.3f}s")
print(f"Resultado: {result}")