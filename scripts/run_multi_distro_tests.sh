#!/bin/bash
# Exécute les tests d'intégration sur plusieurs distributions

DISTROS=("ubuntu:22.04" "debian:12" "rockylinux:9")
for distro in "${DISTROS[@]}"; do
    echo "=== Testing on $distro ==="
    docker run --rm -v "$(pwd)":/app -w /app "$distro" bash -c "
        apt-get update && apt-get install -y curl python3 python3-pip sudo || yum install -y curl python3 python3-pip sudo;
        curl -sSL https://install.python-poetry.org | python3 -;
        export PATH=\$HOME/.local/bin:\$PATH;
        poetry install --no-interaction;
        poetry run pytest tests/integration -v
    "
done