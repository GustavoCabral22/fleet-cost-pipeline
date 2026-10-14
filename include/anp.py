"""Download e carga na camada raw dos arquivos mensais da ANP."""
import os
from datetime import date
from pathlib import Path

import requests

ANP_BASE_URL = os.environ.get(
    "ANP_BASE_URL",
    "https://www.gov.br/anp/pt-br/centrais-de-conteudo/dados-abertos/arquivos/shpc/dsas/ca",
)
PASTA_DADOS = Path(os.environ.get("DATA_DIR", "/opt/airflow/data"))

COLUNAS_RAW = (
    "regiao_sigla, estado_sigla, municipio, revenda, cnpj_revenda, nome_rua, numero_rua, "
    "complemento, bairro, cep, produto, data_coleta, valor_venda, valor_compra, "
    "unidade_medida, bandeira"
)


def mes_de_referencia(data_execucao: date) -> date:
    """A ANP publica o mês fechado: uma execução em outubro processa setembro."""
    primeiro_dia = data_execucao.replace(day=1)
    return (primeiro_dia.replace(year=primeiro_dia.year - 1, month=12)
            if primeiro_dia.month == 1
            else primeiro_dia.replace(month=primeiro_dia.month - 1))


def baixar(mes: date) -> Path:
    nome = f"ca-{mes:%Y-%m}.csv"
    destino = PASTA_DADOS / "anp" / nome
    destino.parent.mkdir(parents=True, exist_ok=True)
    with requests.get(f"{ANP_BASE_URL}/{nome}", stream=True, timeout=120) as resposta:
        resposta.raise_for_status()
        with destino.open("wb") as f:
            for bloco in resposta.iter_content(chunk_size=1 << 20):
                f.write(bloco)
    return destino


def carregar_raw(conn, arquivo: Path, encoding: str = "UTF8") -> int:
    """Substitui as linhas do arquivo na camada raw (idempotente) via COPY."""
    with conn.cursor() as cur:
        cur.execute("DELETE FROM raw.precos_combustiveis WHERE arquivo_origem = %s", (arquivo.name,))
        cur.execute(f"""
            CREATE TEMP TABLE carga ON COMMIT DROP AS
            SELECT {COLUNAS_RAW} FROM raw.precos_combustiveis WITH NO DATA
        """)
        with arquivo.open("r", encoding="utf-8" if encoding == "UTF8" else "latin-1") as f:
            cur.copy_expert(
                "COPY carga FROM STDIN WITH (FORMAT csv, HEADER true, DELIMITER ';')", f
            )
        cur.execute(
            f"INSERT INTO raw.precos_combustiveis ({COLUNAS_RAW}, arquivo_origem) "
            f"SELECT {COLUNAS_RAW}, %s FROM carga",
            (arquivo.name,),
        )
        linhas = cur.rowcount
    conn.commit()
    return linhas
