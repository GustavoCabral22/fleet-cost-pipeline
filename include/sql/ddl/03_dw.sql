-- Star schema. Grão da fato: um preço de venda coletado
-- por produto, por posto (revenda), por dia.

CREATE TABLE IF NOT EXISTS dw.dim_produto (
    produto_sk      SERIAL PRIMARY KEY,
    nome_produto    TEXT NOT NULL UNIQUE,
    unidade_medida  TEXT
);

CREATE TABLE IF NOT EXISTS dw.dim_localidade (
    localidade_sk   SERIAL PRIMARY KEY,
    regiao_sigla    TEXT NOT NULL,
    uf_sigla        CHAR(2) NOT NULL,
    municipio       TEXT NOT NULL,
    UNIQUE (uf_sigla, municipio)
);

-- SCD tipo 1: se o posto trocar de bandeira, sobrescrevemos o valor.
-- (Evolução possível: SCD tipo 2 para manter o histórico de bandeiras.)
CREATE TABLE IF NOT EXISTS dw.dim_revenda (
    revenda_sk      SERIAL PRIMARY KEY,
    cnpj            TEXT NOT NULL UNIQUE,
    nome_revenda    TEXT,
    bandeira        TEXT,
    bairro          TEXT,
    cep             TEXT
);

CREATE TABLE IF NOT EXISTS dw.dim_tempo (
    data_sk         INTEGER PRIMARY KEY,      -- formato AAAAMMDD
    data            DATE NOT NULL UNIQUE,
    ano             SMALLINT NOT NULL,
    semestre        SMALLINT NOT NULL,
    trimestre       SMALLINT NOT NULL,
    mes             SMALLINT NOT NULL,
    nome_mes        TEXT NOT NULL,
    ano_mes         CHAR(7) NOT NULL,         -- 'AAAA-MM', útil para agrupar
    dia             SMALLINT NOT NULL,
    dia_semana      SMALLINT NOT NULL,        -- 1 = segunda ... 7 = domingo
    fim_de_semana   BOOLEAN NOT NULL
);

CREATE TABLE IF NOT EXISTS dw.fato_preco_combustivel (
    data_sk         INTEGER NOT NULL REFERENCES dw.dim_tempo (data_sk),
    produto_sk      INTEGER NOT NULL REFERENCES dw.dim_produto (produto_sk),
    localidade_sk   INTEGER NOT NULL REFERENCES dw.dim_localidade (localidade_sk),
    revenda_sk      INTEGER NOT NULL REFERENCES dw.dim_revenda (revenda_sk),
    valor_venda     NUMERIC(10, 3) NOT NULL,
    valor_compra    NUMERIC(10, 3),
    PRIMARY KEY (data_sk, produto_sk, revenda_sk)
);

CREATE INDEX IF NOT EXISTS ix_fato_produto_data
    ON dw.fato_preco_combustivel (produto_sk, data_sk);
CREATE INDEX IF NOT EXISTS ix_fato_localidade
    ON dw.fato_preco_combustivel (localidade_sk);
