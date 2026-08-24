"""Configuration des tests E2E."""

from tests.front.conftest import (
	app,
	disable_migrations,
	ensure_mongo_patches,
	fake_mongo_logger,
	fastapi_test_client,
	init_test_sessions,
	patch_requests_to_fastapi,
)

__all__ = [
	"app",
	"disable_migrations",
	"ensure_mongo_patches",
	"fake_mongo_logger",
	"fastapi_test_client",
	"init_test_sessions",
	"patch_requests_to_fastapi",
]
