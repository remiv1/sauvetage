#!/bin/sh
set -eu

envsubst < /tmp/01_create_db_users.js.pattern | mongosh --quiet