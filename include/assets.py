"""Assets compartilhados entre as DAGs.

Uma DAG que atualiza um Asset "avisa" o Airflow; a DAG do índice só roda
quando os dois insumos foram atualizados (agendamento orientado a dados).
"""
from airflow.sdk import Asset

INDICADORES_BCB = Asset("postgres://warehouse/frota/indicadores/serie_temporal")
PRECOS_ANP = Asset("postgres://warehouse/frota/dw/fato_preco_combustivel")
INDICE_CUSTO_FROTA = Asset("postgres://warehouse/frota/mart/indice_custo_frota")
