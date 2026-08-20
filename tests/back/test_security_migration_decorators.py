"""Tests des composants backend de sécurité et de démarrage."""

import importlib
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from app_back.config import security
import app_back.migration as migration
from app_back.migration import _build_dsn, _run_alembic, ensure_vat
import app_back.utils.decorators as decorators


def test_get_security_token_requires_configured_token(monkeypatch) -> None:
    """Un token interne absent doit empêcher la sécurisation d'une route."""
    monkeypatch.delenv("SECURITY_TOKEN", raising=False)

    with pytest.raises(ValueError, match="n'est pas défini"):
        security.get_security_token()


def test_get_security_token_returns_configured_token(monkeypatch) -> None:
    """Le token interne configuré doit être retourné sans transformation."""
    monkeypatch.setenv("SECURITY_TOKEN", "token-de-test")

    assert security.get_security_token() == "token-de-test"


def test_build_dsn_encodes_migration_credentials(monkeypatch) -> None:
    """La DSN de migration encode les caractères réservés des identifiants."""
    monkeypatch.setenv("POSTGRES_USER_MIGR", "migration@user")
    password = "pass" + " word/#"
    monkeypatch.setenv("POSTGRES_PASSWORD_MIGR", password)
    monkeypatch.setenv("POSTGRES_HOST", "postgres")
    monkeypatch.setenv("POSTGRES_PORT", "5433")
    monkeypatch.setenv("POSTGRES_DB_MAIN", "sauvetage")

    expected_dsn = "postgresql://migration%40user:" + "pass%20word%2F%23@postgres:5433/sauvetage"
    assert _build_dsn() == expected_dsn


def test_run_alembic_returns_subprocess_result() -> None:
    """Une commande Alembic réussie retourne son code et ses sorties."""
    process = SimpleNamespace(returncode=0, stdout="ok", stderr="")

    with patch("app_back.migration.subprocess.run", return_value=process):
        assert _run_alembic(["alembic", "upgrade"], timeout=12) == (0, "ok", "")


def test_run_alembic_handles_subprocess_error() -> None:
    """Une erreur de sous-processus est convertie en résultat d'échec."""
    with patch(
        "app_back.migration.subprocess.run",
        side_effect=__import__("subprocess").TimeoutExpired("alembic", 12),
    ):
        code, stdout, stderr = _run_alembic(["alembic"], timeout=12)

    assert code == 255
    assert stdout == ""
    assert "timed out" in stderr


def test_run_startup_tasks_migrates_when_lock_is_obtained() -> None:
    """Le détenteur du verrou lance les migrations et initialise les TVA."""
    importlib.reload(migration)
    cursor = MagicMock()
    cursor.fetchone.return_value = (True,)
    connection = MagicMock()
    connection.cursor.return_value = cursor
    session = MagicMock()
    context = MagicMock()
    context.__enter__.return_value = session
    context.__exit__.return_value = None

    with patch("app_back.migration.psycopg2.connect", return_value=connection), patch(
        "app_back.migration._run_alembic", return_value=(0, "", "")
    ) as run_alembic, patch(
        "app_back.migration.db_config.main_session_ctx", return_value=context
    ), patch("app_back.migration.ensure_vat") as ensure:
        migration.run_startup_tasks(timeout=12)

    assert run_alembic.call_count == 2
    ensure.assert_called_once_with(session)
    connection.close.assert_called_once()


def test_run_startup_tasks_falls_back_when_postgres_lock_fails() -> None:
    """Une panne du verrou PostgreSQL déclenche les migrations de secours."""
    importlib.reload(migration)
    session = MagicMock()
    context = MagicMock()
    context.__enter__.return_value = session
    context.__exit__.return_value = None

    with patch(
        "app_back.migration.psycopg2.connect",
        side_effect=__import__("psycopg2").OperationalError("postgres indisponible"),
    ), patch("app_back.migration._run_alembic", return_value=(0, "", "")) as run_alembic, patch(
        "app_back.migration.db_config.main_session_ctx", return_value=context
    ), patch("app_back.migration.ensure_vat") as ensure:
        migration.run_startup_tasks(timeout=12)

    assert run_alembic.call_count == 2
    ensure.assert_called_once_with(session)


def test_ensure_vat_adds_only_missing_rates() -> None:
    """Les taux absents sont ajoutés, tandis que les taux présents sont conservés."""
    existing_rate = SimpleNamespace(code=10)
    scalars = MagicMock()
    scalars.all.return_value = [existing_rate]
    execution = MagicMock()
    execution.scalars.return_value = scalars
    session = MagicMock()
    session.execute.return_value = execution

    ensure_vat(session)

    assert session.add.call_count == 3
    session.commit.assert_called_once()


def test_access_control_validates_token_and_ip(monkeypatch) -> None:
    """Le décorateur interne accepte le bon token et l'adresse IP autorisée."""

    monkeypatch.setattr(decorators, "INTERNAL_TOKEN", "token-de-test")
    request = SimpleNamespace(
        headers={"X-Internal-Token": "token-de-test"},
        client=SimpleNamespace(host="127.0.0.1"),
    )

    assert decorators.access_control(restrict_ip=True)(request) is True # type: ignore


@pytest.mark.parametrize(
    "internal_request, restrict_ip, status_code",
    [
        (SimpleNamespace(headers={"X-Internal-Token": "incorrect"}, client=None), False, 403),
        (SimpleNamespace(headers={"X-Internal-Token": "token-de-test"}, client=None), True, 400),
        (
            SimpleNamespace(
                headers={"X-Internal-Token": "token-de-test"},
                client=SimpleNamespace(host="192.0.2.1"),
            ),
            True,
            403,
        ),
    ],
)
def test_access_control_rejects_invalid_requests(
    monkeypatch,
    internal_request,
    restrict_ip,
    status_code,
) -> None:
    """Le décorateur interne refuse un token ou une adresse IP non autorisés."""

    monkeypatch.setattr(decorators, "INTERNAL_TOKEN", "token-de-test")

    protected_route = decorators.access_control(restrict_ip=restrict_ip)
    with pytest.raises(HTTPException) as exception:
        protected_route(internal_request)

    assert exception.value.status_code == status_code
