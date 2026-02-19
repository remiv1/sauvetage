#! /bin/bash

podman compose down -v

podman system prune -a -f
