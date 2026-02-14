#!/bin/bash
set -e

# Démarrer MongoDB avec la config
exec mongod --config /etc/mongod.conf
