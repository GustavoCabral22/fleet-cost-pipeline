-- Camada de consumo: tabelas prontas para dashboard, sem joins.
CREATE SCHEMA IF NOT EXISTS mart;

CREATE TABLE IF NOT EXISTS mart.indice_custo_frota (
    ano_mes               CHAR(7)        NOT NULL,
    produto               TEXT           NOT NULL,
    preco_medio_nominal   NUMERIC(10, 3) NOT NULL,
    ipca_mes_pct          NUMERIC(8, 4)  NOT NULL,
    indice_ipca           NUMERIC(14, 8) NOT NULL,  -- base 1 no primeiro mês da série
    preco_real            NUMERIC(10, 3) NOT NULL,  -- em R$ do mês-base (o mais recente)
    mes_base_preco_real   CHAR(7)        NOT NULL,
    variacao_nominal_pct  NUMERIC(8, 2),            -- acumulada desde o primeiro mês
    variacao_real_pct     NUMERIC(8, 2),            -- acumulada, descontada a inflação
    atualizado_em         TIMESTAMPTZ    NOT NULL DEFAULT now(),
    PRIMARY KEY (ano_mes, produto)
);
