"""Monta o índice de custo de combustível da frota, nominal e real.

Não tem horário: roda sempre que os preços da ANP E os indicadores do BCB
forem atualizados (agendamento por Assets). Antes de publicar, checa a
qualidade do resultado; se a checagem falhar, a DAG falha e ninguém consome
um número errado.
"""
from datetime import datetime, timedelta
from pathlib import Path

from airflow.providers.common.sql.operators.sql import SQLCheckOperator, SQLExecuteQueryOperator
from airflow.sdk import dag

from include.assets import INDICADORES_BCB, INDICE_CUSTO_FROTA, PRECOS_ANP

CONN_ID = "warehouse"
SQL_DIR = Path(__file__).resolve().parents[1] / "include" / "sql"


@dag(
    schedule=(INDICADORES_BCB & PRECOS_ANP),
    start_date=datetime(2025, 1, 1),
    catchup=False,
    default_args={"retries": 1, "retry_delay": timedelta(minutes=5)},
    template_searchpath=[str(SQL_DIR)],
    tags=["frota", "mart"],
    doc_md=__doc__,
)
def indice_custo_frota():

    montar = SQLExecuteQueryOperator(
        task_id="montar_indice",
        conn_id=CONN_ID,
        sql="mart/indice_custo_frota.sql",
    )

    # SQLCheckOperator falha se qualquer valor da primeira linha for falso/zero.
    checar = SQLCheckOperator(
        task_id="checar_qualidade",
        conn_id=CONN_ID,
        sql="""
            SELECT
                COUNT(*) > 0                                  AS tem_linhas,
                COUNT(*) FILTER (WHERE preco_real <= 0) = 0   AS precos_positivos,
                COUNT(*) FILTER (WHERE indice_ipca <= 0) = 0  AS indice_valido,
                -- o preço real do mês-base tem que ser igual ao nominal
                COUNT(*) FILTER (
                    WHERE ano_mes = mes_base_preco_real
                      AND ABS(preco_real - preco_medio_nominal) > 0.001
                ) = 0                                         AS base_consistente
            FROM mart.indice_custo_frota
        """,
        outlets=[INDICE_CUSTO_FROTA],
    )

    montar >> checar


indice_custo_frota()
