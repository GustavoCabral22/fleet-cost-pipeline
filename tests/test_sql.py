"""Testes de integração do SQL num PostgreSQL real.

Rodam no CI (que sobe um PostgreSQL) e localmente com DATABASE_URL definida.
Cobrem a regra de negócio mais importante do projeto: o cálculo do preço real.
"""
import math
import os
from pathlib import Path

import psycopg2
import pytest

from include import anp

RAIZ = Path(__file__).resolve().parents[1]
SQL = RAIZ / "include" / "sql"
AMOSTRA = RAIZ / "tests" / "fixtures" / "anp_amostra_sintetica.csv"

# IPCA de janeiro a junho de 2025 (% ao mês)
IPCA = {"2025-01-01": 0.16, "2025-02-01": 1.31, "2025-03-01": 0.56,
        "2025-04-01": 0.43, "2025-05-01": 0.26, "2025-06-01": 0.24}


def executar_arquivo(conn, caminho: Path):
    with conn.cursor() as cur:
        cur.execute(caminho.read_text())
    conn.commit()


@pytest.fixture(scope="module")
def conn():
    url = os.environ.get("DATABASE_URL")
    if not url:
        pytest.skip("DATABASE_URL não definida: pulando testes de integração")
    c = psycopg2.connect(url)
    with c.cursor() as cur:
        cur.execute("DROP SCHEMA IF EXISTS raw, dw, indicadores, mart CASCADE")
    c.commit()
    for ddl in sorted((SQL / "ddl").glob("*.sql")):
        executar_arquivo(c, ddl)

    anp.carregar_raw(c, AMOSTRA)
    executar_arquivo(c, SQL / "transform" / "load_dw.sql")
    with c.cursor() as cur:
        cur.executemany(
            "INSERT INTO indicadores.serie_temporal (serie, data, valor) VALUES ('ipca', %s, %s)",
            list(IPCA.items()),
        )
    c.commit()
    executar_arquivo(c, SQL / "mart" / "indice_custo_frota.sql")
    yield c
    c.close()


def consultar(conn, sql, params=None):
    with conn.cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchall()


def test_carga_raw_e_idempotente(conn):
    antes = consultar(conn, "SELECT COUNT(*) FROM raw.precos_combustiveis")[0][0]
    anp.carregar_raw(conn, AMOSTRA)
    depois = consultar(conn, "SELECT COUNT(*) FROM raw.precos_combustiveis")[0][0]
    assert antes == depois == 832


def test_indice_tem_um_registro_por_mes_e_produto(conn):
    linhas = consultar(conn, "SELECT COUNT(*), COUNT(DISTINCT ano_mes) FROM mart.indice_custo_frota")
    total, meses = linhas[0]
    assert meses == 6            # só meses com preço E IPCA
    assert total == 6 * 4        # 4 produtos


def test_preco_real_no_mes_base_e_igual_ao_nominal(conn):
    linhas = consultar(conn, """
        SELECT preco_medio_nominal, preco_real FROM mart.indice_custo_frota
        WHERE ano_mes = mes_base_preco_real
    """)
    assert linhas and all(nominal == real for nominal, real in linhas)


def test_preco_real_desconta_a_inflacao(conn):
    nominal_jan, real_jan = consultar(conn, """
        SELECT preco_medio_nominal, preco_real FROM mart.indice_custo_frota
        WHERE produto = 'DIESEL' AND ano_mes = '2025-01'
    """)[0]
    # Inflação acumulada de fevereiro a junho: o preço de janeiro corrigido
    fator = math.prod(1 + v / 100 for d, v in IPCA.items() if d != "2025-01-01")
    assert float(real_jan) == pytest.approx(float(nominal_jan) * fator, abs=0.002)


def test_reprocessar_o_indice_nao_duplica(conn):
    executar_arquivo(conn, SQL / "mart" / "indice_custo_frota.sql")
    assert consultar(conn, "SELECT COUNT(*) FROM mart.indice_custo_frota")[0][0] == 24
