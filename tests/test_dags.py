"""Testes de integridade: pegam erro de import, ciclo e configuração antes do deploy."""
from pathlib import Path

import pytest
from airflow.models import DagBag

DAGS_DIR = Path(__file__).resolve().parents[1] / "dags"


@pytest.fixture(scope="module")
def dagbag():
    return DagBag(dag_folder=str(DAGS_DIR), include_examples=False)


def test_sem_erros_de_import(dagbag):
    assert dagbag.import_errors == {}


def test_dags_esperadas(dagbag):
    assert set(dagbag.dag_ids) == {"bcb_indicadores", "anp_precos", "indice_custo_frota"}


@pytest.mark.parametrize("dag_id", ["bcb_indicadores", "anp_precos", "indice_custo_frota"])
def test_boas_praticas(dagbag, dag_id):
    dag = dagbag.dags[dag_id]
    assert dag.tags, "toda DAG deve ter tags"
    assert not dag.catchup, "catchup desligado evita centenas de execuções acidentais"
    assert dag.doc_md, "toda DAG deve ter documentação"
    for t in dag.tasks:
        assert t.retries >= 1, f"{t.task_id} sem retry"


def test_indice_depende_dos_dois_insumos(dagbag):
    """A DAG do índice só pode rodar depois de preços E indicadores atualizados."""
    dag = dagbag.dags["indice_custo_frota"]
    uris = {asset.uri for _, asset in dag.timetable.asset_condition.iter_assets()}
    assert any("indicadores/serie_temporal" in u for u in uris)
    assert any("dw/fato_preco_combustivel" in u for u in uris)
