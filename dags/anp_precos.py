"""Carga mensal dos preços de combustíveis da ANP: download -> raw -> star schema.

Por padrão processa o mês anterior ao da execução. Para reprocessar um mês
específico, dispare a DAG manualmente com o parâmetro `ano_mes` (ex.: 2025-03).
"""
from datetime import date, datetime, timedelta
from pathlib import Path

from airflow.providers.common.sql.operators.sql import SQLExecuteQueryOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook
from airflow.sdk import Param, dag, get_current_context, task

from include import anp
from include.assets import PRECOS_ANP

CONN_ID = "warehouse"
SQL_DIR = Path(__file__).resolve().parents[1] / "include" / "sql"


@dag(
    schedule="0 6 10 * *",  # dia 10 de cada mês: a ANP já publicou o mês anterior
    start_date=datetime(2025, 1, 1),
    catchup=False,
    default_args={"retries": 2, "retry_delay": timedelta(minutes=30)},
    params={"ano_mes": Param(None, type=["null", "string"], pattern=r"^\d{4}-\d{2}$",
                             description="Mês a processar (AAAA-MM). Vazio = mês anterior.")},
    template_searchpath=[str(SQL_DIR)],
    tags=["frota", "ingestao", "anp"],
    doc_md=__doc__,
)
def anp_precos():

    @task
    def definir_mes() -> str:
        ctx = get_current_context()
        if ctx["params"].get("ano_mes"):
            return ctx["params"]["ano_mes"]
        execucao = ctx.get("logical_date") or datetime.now()
        return f"{anp.mes_de_referencia(execucao.date()):%Y-%m}"

    @task
    def baixar(ano_mes: str) -> str:
        return str(anp.baixar(date.fromisoformat(f"{ano_mes}-01")))

    @task
    def carregar_raw(caminho: str) -> int:
        conn = PostgresHook(postgres_conn_id=CONN_ID).get_conn()
        try:
            linhas = anp.carregar_raw(conn, Path(caminho))
        finally:
            conn.close()
        if linhas == 0:
            raise ValueError(f"{caminho} veio vazio: abortando antes de transformar")
        return linhas

    transformar = SQLExecuteQueryOperator(
        task_id="transformar_dw",
        conn_id=CONN_ID,
        sql="transform/load_dw.sql",
        outlets=[PRECOS_ANP],
    )

    carregar_raw(baixar(definir_mes())) >> transformar


anp_precos()
