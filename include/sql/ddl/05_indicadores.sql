-- Mesma tabela do projeto economic-indicators-etl.
CREATE SCHEMA IF NOT EXISTS indicadores;

CREATE TABLE IF NOT EXISTS indicadores.serie_temporal (
    serie          TEXT           NOT NULL,
    data           DATE           NOT NULL,
    valor          NUMERIC(18, 6) NOT NULL,
    carregado_em   TIMESTAMPTZ    NOT NULL DEFAULT now(),
    atualizado_em  TIMESTAMPTZ    NOT NULL DEFAULT now(),
    PRIMARY KEY (serie, data)
);
