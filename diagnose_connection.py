from time import perf_counter

import psycopg

from logiflow.core.config import get_settings

settings = get_settings()

tests = [
    {
        "name": "Conexao padrao",
        "options": {},
    },
    {
        "name": "SSL desabilitado",
        "options": {
            "sslmode": "disable",
        },
    },
    {
        "name": "SSL e GSS desabilitados",
        "options": {
            "sslmode": "disable",
            "gssencmode": "disable",
        },
    },
]


for test in tests:
    start = perf_counter()

    try:
        with psycopg.connect(
            host=settings.db_host,
            port=settings.db_port,
            dbname=settings.db_name,
            user=settings.db_user,
            password=settings.db_password,
            connect_timeout=10,
            **test["options"],
        ) as conn, conn.cursor() as cursor:
            cursor.execute("SELECT 1")
            result = cursor.fetchone()

        elapsed = perf_counter() - start

        print(
            f"{test['name']}: "
            f"{elapsed:.3f}s | "
            f"Resultado: {result}"
        )

    except psycopg.Error as exc:
        elapsed = perf_counter() - start

        print(
            f"{test['name']}: "
            f"ERRO apos {elapsed:.3f}s | "
            f"{type(exc).__name__}"
        )