.PHONY: help install test lint format clean build

help:
	@echo "Commandes disponibles:"
	@echo "  install    - Installer les dépendances"
	@echo "  test       - Lancer les tests"
	@echo "  lint       - Vérifier le code"
	@echo "  format     - Formater le code"
	@echo "  clean      - Nettoyer les fichiers temporaires"
	@echo "  build      - Construire le package"

install:
	poetry install

test:
	poetry run pytest

lint:
	poetry run ruff check .
	poetry run mypy soc_deploy

format:
	poetry run black .
	poetry run ruff check --fix .

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache .mypy_cache .coverage htmlcov dist build

build:
	poetry build
	