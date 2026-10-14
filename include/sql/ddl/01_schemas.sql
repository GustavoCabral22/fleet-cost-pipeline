-- Camadas do warehouse:
--   raw: dado exatamente como veio da ANP (tudo texto, nada se perde na carga)
--   dw : modelo dimensional (star schema) pronto para análise
CREATE SCHEMA IF NOT EXISTS raw;
CREATE SCHEMA IF NOT EXISTS dw;
