"""Versão enxuta do pipeline do repositório economic-indicators-etl.

Em produção, o pacote `bcb_etl` seria publicado num registry interno e
instalado na imagem do Airflow. Aqui ele foi simplificado para o projeto
rodar sozinho.
"""
from datetime import date, timedelta

import requests

BCB_URL = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{codigo}/dados"

SERIES = {
    # nome: (código SGS, faixa plausível de valores)
    "ipca": (433, (-5.0, 10.0)),
    "selic_meta": (432, (0.0, 50.0)),
    "dolar_ptax": (1, (0.5, 20.0)),
}

DATA_INICIAL_PADRAO = date(2015, 1, 1)
DIAS_REPROCESSAMENTO = 45
JANELA_MAXIMA_DIAS = 3650


def definir_inicio(ultima: date | None) -> date:
    return ultima - timedelta(days=DIAS_REPROCESSAMENTO) if ultima else DATA_INICIAL_PADRAO


def extrair(codigo: int, inicio: date, fim: date) -> list[dict]:
    registros, atual = [], inicio
    while atual <= fim:
        fim_janela = min(atual + timedelta(days=JANELA_MAXIMA_DIAS - 1), fim)
        resposta = requests.get(
            BCB_URL.format(codigo=codigo),
            params={
                "formato": "json",
                "dataInicial": atual.strftime("%d/%m/%Y"),
                "dataFinal": fim_janela.strftime("%d/%m/%Y"),
            },
            timeout=30,
        )
        if resposta.status_code != 404:  # 404 = sem dados no período
            resposta.raise_for_status()
            registros.extend(resposta.json())
        atual = fim_janela + timedelta(days=1)
    return registros


def transformar(nome: str, registros: list[dict]) -> list[tuple]:
    """Tipa e valida. Levanta ValueError se o dado não for confiável."""
    _, (minimo, maximo) = SERIES[nome]
    linhas, vistas = [], set()
    for r in registros:
        dia = date(int(r["data"][6:]), int(r["data"][3:5]), int(r["data"][:2]))
        valor = float(r["valor"])
        if dia in vistas:
            raise ValueError(f"{nome}: data duplicada {dia}")
        if not minimo <= valor <= maximo:
            raise ValueError(f"{nome}: valor {valor} fora da faixa [{minimo}, {maximo}] em {dia}")
        vistas.add(dia)
        linhas.append((nome, dia, valor))
    return linhas
