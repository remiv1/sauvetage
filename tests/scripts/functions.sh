#! /usr/bin/env bash

run_alembic_with_retry() {
	local cfg="$1"
	local attempts=${2:-3}
	local delay=${3:-10}
	local i=1
	while :; do
		echo "🚀 Alembic: tentative $i/$attempts pour $cfg"
		set +e
		alembic -c "$cfg" upgrade head
		rc=$?
		set -e
		if [ $rc -eq 0 ]; then
			echo "✅ Alembic succeeded for $cfg"
			return 0
		fi
		if [ $i -ge $attempts ]; then
			echo "❌ Alembic failed for $cfg after $attempts attempts (rc=$rc)"
			return $rc
		fi
		echo "⚠️ Alembic failed (rc=$rc), attente $delay s avant nouvelle tentative..."
		sleep "$delay"
		i=$((i+1))
	done
}

check_pg_ready() {
	# 1) pg_isready if available
	if command -v pg_isready >/dev/null 2>&1; then
		PGHOST="$HOST" PGPORT="$PORT" pg_isready -h "$HOST" -p "$PORT" -U "$USER" >/dev/null 2>&1 && return 0 || return 1
	fi

	# 2) psql if available
	if command -v psql >/dev/null 2>&1; then
		PGPASSWORD="$PW" psql -h "$HOST" -p "$PORT" -U "$USER" -d "$DB" -c '\q' >/dev/null 2>&1 && return 0 || return 1
	fi

	# 3) TCP socket fallback (bash built-in /dev/tcp)
	if bash -c "</dev/tcp/$HOST/$PORT" >/dev/null 2>&1; then
		return 0
	fi

	return 1
}

# Detect and set a global compose command array `COMPOSE_CMD` based on
# the available container engine. Usage:
#   detect_compose_cmd <engine|auto>
# After call: `COMPOSE_CMD` (array) is available for use, and
# `COMPOSE_ENGINE` contains the chosen engine name.
detect_compose_cmd() {
	local engine_arg="${1:-auto}"
	declare -g COMPOSE_ENGINE
	declare -g -a COMPOSE_CMD
	COMPOSE_ENGINE=""

	if [ "$engine_arg" = "auto" ]; then
		if command -v docker >/dev/null 2>&1; then
			COMPOSE_ENGINE=docker
		elif command -v podman >/dev/null 2>&1; then
			COMPOSE_ENGINE=podman
		else
			return 1
		fi
	else
		COMPOSE_ENGINE="$engine_arg"
	fi

	if [ "$COMPOSE_ENGINE" = "docker" ]; then
		if docker compose version >/dev/null 2>&1; then
			COMPOSE_CMD=(docker compose)
		elif command -v docker-compose >/dev/null 2>&1; then
			COMPOSE_CMD=(docker-compose)
		else
			return 2
		fi
	elif [ "$COMPOSE_ENGINE" = "podman" ]; then
		if podman compose version >/dev/null 2>&1; then
			COMPOSE_CMD=(podman compose)
		elif command -v podman-compose >/dev/null 2>&1; then
			COMPOSE_CMD=(podman-compose)
		else
			return 2
		fi
	else
		return 3
	fi

	return 0
}


# Find the first existing compose file among candidates and print it.
# Usage: find_compose_file path1 path2 ...
# Returns: prints path to stdout and returns 0, or returns 1 if none found.
find_compose_file() {
	for p in "$@"; do
		if [ -n "$p" ] && [ -f "$p" ]; then
			printf '%s' "$p"
			return 0
		fi
	done
	return 1
}


# Source a dotenv-like file into current shell safely.
# Keeps comments and blank lines ignored and quotes values; exported into environment.
# Usage: safe_source_env_file /path/to/.env
safe_source_env_file() {
	local env_file="$1"
	if [ -z "$env_file" ] || [ ! -f "$env_file" ]; then
		return 1
	fi
	set -a
	# shellcheck disable=SC2046,SC1090
	source <(awk '
		/^[[:space:]]*#/ { next }
		/^[[:space:]]*$/ { next }
		/^[A-Za-z_][A-Za-z0-9_]*=/ {
			split($0, a, "=");
			key=a[1];
			val=substr($0, length(key)+2);
			gsub(/\\/, "\\\\", val);
			gsub(/"/, "\\\"", val);
			print "export " key "=\"" val "\"";
		}
	' "$env_file")
	set +a
}


# Wrapper: call compose down -v using the detected COMPOSE_CMD array.
# Usage: compose_down_with_file /path/to/docker-compose.yml
compose_down_with_file() {
	local file="$1"
	if [ -z "$file" ]; then
		return 1
	fi
	if [ "${#COMPOSE_CMD[@]}" -eq 0 ]; then
		return 2
	fi
	"${COMPOSE_CMD[@]}" -f "$file" down -v
}


# Wrapper: build a service and bring it up detached.
# Usage: compose_build_and_up service_name /path/to/compose.yml
compose_build_and_up() {
	local service="$1"; shift
	local file="$1"
	if [ -z "$service" ] || [ -z "$file" ]; then
		return 1
	fi
	if [ "${#COMPOSE_CMD[@]}" -eq 0 ]; then
		return 2
	fi
	"${COMPOSE_CMD[@]}" -f "$file" build "$service"
	"${COMPOSE_CMD[@]}" -f "$file" up -d "$service"
}


# Prepare temporary test migrations directory copied from project migrations.
# This replicates logic used in tests to create a self-contained alembic env for tests.
# Usage: prepare_test_migrations /abs/path/project_root /abs/path/tmp_migr
prepare_test_migrations() {
	local project_root="$1"
	local tmp_migr="$2"
	if [ -z "$project_root" ] || [ -z "$tmp_migr" ]; then
		return 1
	fi

	rm -rf "$tmp_migr"
	mkdir -p "$tmp_migr/main/alembic/versions"
	mkdir -p "$tmp_migr/users/alembic/versions"

	# copy main
	cp -a "$project_root/migrations/main/alembic/versions/"*.py "$tmp_migr/main/alembic/versions/" || true
	cp "$project_root/migrations/main/alembic.ini" "$tmp_migr/main/alembic.ini"
	sed -i "s|^script_location\s*=.*|script_location = $tmp_migr/main/alembic|" "$tmp_migr/main/alembic.ini"

	local MAIN_ORIG_ENV="$project_root/migrations/main/alembic/env.py"
	local MAIN_TMP_ENV="$tmp_migr/main/alembic/env.py"
	printf "%s\n" "# Auto-generated env.py for tests" \
		"import os" \
		"import sys" \
		"from logging.config import fileConfig" \
		"from sqlalchemy import engine_from_config" \
		"from sqlalchemy import pool" \
		"from alembic import context" \
		"# project root injected by test script" \
		"project_root = os.getenv(\"TEST_PROJECT_ROOT\", \"$project_root\")" \
		"sys.path.insert(0, project_root)" > "$MAIN_TMP_ENV"
	sed '/sys.path.insert(0/ d' "$MAIN_ORIG_ENV" >> "$MAIN_TMP_ENV"

	# copy users
	cp -a "$project_root/migrations/users/alembic/versions/"*.py "$tmp_migr/users/alembic/versions/" || true
	cp "$project_root/migrations/users/alembic.ini" "$tmp_migr/users/alembic.ini"
	sed -i "s|^script_location\s*=.*|script_location = $tmp_migr/users/alembic|" "$tmp_migr/users/alembic.ini"
	local USERS_ORIG_ENV="$project_root/migrations/users/alembic/env.py"
	local USERS_TMP_ENV="$tmp_migr/users/alembic/env.py"
	printf "%s\n" "# Auto-generated env.py for tests" \
		"import os" \
		"import sys" \
		"from logging.config import fileConfig" \
		"from sqlalchemy import engine_from_config" \
		"from sqlalchemy import pool" \
		"from alembic import context" \
		"# project root injected by test script" \
		"project_root = os.getenv(\"TEST_PROJECT_ROOT\", \"$project_root\")" \
		"sys.path.insert(0, project_root)" > "$USERS_TMP_ENV"
	sed '/sys.path.insert(0/ d' "$USERS_ORIG_ENV" >> "$USERS_TMP_ENV"

	return 0
}
