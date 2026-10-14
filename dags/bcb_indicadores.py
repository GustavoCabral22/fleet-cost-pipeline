"""Carga diária e incremental dos indicadores do Banco Central.

Uma task por série, criadas dinamicamente (dynamic task mapping): para
incluir uma série nova basta adicioná-la em include/bcb.py.
"""
from datetime import date, datetime, timedelta

from airflow.providers.postgres.hooks.postgres import PostgresHook
from airflow.sdk import dag, task

from include import bcb
from include.assets import INDICADORES_BCB

CONN_ID = "warehouse"

UPSERT = """
    INSERT INTO indicadores.serie_temporal (serie, data, valor)
    VALUES (%s, %s, %s)
    ON CONFLICT (serie, data) DO UPDATE
        SET valor = EXCLUDED.valor, atualizado_em = now()
        WHERE indicadores.serie_temporal.valor IS DISTINCT FROM EXCLUDED.valor
"""


@dag(
    schedule="0 9 * * 1-5",  # dias úteis, 9h (UTC): depois da divulgação da PTAX do dia anterior
    start_date=datetime(2025, 1, 1),
    catchup=False,
    default_args={"retries": 3, "retry_delay": timedelta(minutes=10)},
    tags=["frota", "ingestao", "bcb"],
    doc_md=__doc__,
)
def bcb_indicadores():

    @task
    def listar_series() -> list[str]:
        return list(bcb.SERIES)

    @task
    def carregar_serie(nome: str) -> int:
        hook = PostgresHook(postgres_conn_id=CONN_ID)
        ultima = hook.get_first(
            "SELECT MAX(data) FROM indicadores.serie_temporal WHERE serie = %s", parameters=(nome,)
        )[0]
        inicio = bcb.definir_inicio(ultima)
        codigo, _ = bcb.SERIES[nome]

        registros = bcb.extrair(codigo, inicio, date.today())
        linhas = bcb.transformar(nome, registros)

        with hook.get_conn() as conn, conn.cursor() as cur:
            cur.executemany(UPSERT, linhas)
        print(f"{nome}: {len(linhas)} linhas processadas desde {inicio}")
        return len(linhas)

    @task(outlets=[INDICADORES_BCB])
    def publicar(linhas_por_serie: list[int]) -> None:
        """Só chega aqui se todas as séries carregaram. Avisa as DAGs que dependem do Asset."""
        print(f"Total processado: {sum(linhas_por_serie)} linhas")

    publicar(carregar_serie.expand(nome=listar_series()))


bcb_indicadores()
