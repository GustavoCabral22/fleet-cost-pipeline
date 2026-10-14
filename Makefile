AIRFLOW_VERSION := 3.1.0
PYTHON_VERSION  := 3.12
CONSTRAINTS     := https://raw.githubusercontent.com/apache/airflow/constraints-$(AIRFLOW_VERSION)/constraints-$(PYTHON_VERSION).txt

.PHONY: up down reset logs setup test

up:      ## Sobe Airflow + bancos. Interface em http://localhost:8080
	@test -f .env || echo "AIRFLOW_UID=$$(id -u)" > .env
	docker compose up -d

down:
	docker compose down

reset:   ## Apaga os bancos e recomeça do zero
	docker compose down -v

logs:
	docker compose logs -f airflow

setup:   ## Ambiente local para rodar os testes
	python$(PYTHON_VERSION) -m venv .venv
	.venv/bin/pip install -r requirements-dev.txt -c $(CONSTRAINTS)

test:    ## Testes de DAG (sempre) e de SQL (se DATABASE_URL estiver definida)
	PYTHONPATH=. .venv/bin/pytest -v
