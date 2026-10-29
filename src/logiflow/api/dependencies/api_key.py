import os
import secrets
from pathlib import Path

from dotenv import dotenv_values
from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader

api_key_header = APIKeyHeader(
    name="X-API-Key",
    auto_error=False,
)


def get_expected_api_key() -> str | None:
    """Obtém a chave do ambiente ou do .env local."""

    key = os.getenv("MONITORING_API_KEY")

    if key is not None:
        return key.strip() or None

    # Projeto com layout src/, executado na raiz.
    env_file = Path.cwd() / ".env"

    if not env_file.is_file():
        return None

    value = dotenv_values(env_file).get("MONITORING_API_KEY")

    return value.strip() if value else None


def require_monitoring_api_key(
    provided_key: str | None = Security(api_key_header),
) -> None:
    expected_key = get_expected_api_key()

    if not expected_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Autenticação do monitoramento não configurada.",
        )

    if not provided_key or not secrets.compare_digest(
        provided_key,
        expected_key,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Chave de API inválida ou ausente.",
            headers={"WWW-Authenticate": "APIKey"},
        )
