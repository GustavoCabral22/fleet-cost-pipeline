-- Espelho do CSV da ANP. Colunas em texto de propósito: a conversão de tipos
-- acontece na transformação, onde um valor inválido pode ser tratado sem
-- derrubar a carga inteira.
CREATE TABLE IF NOT EXISTS raw.precos_combustiveis (
    regiao_sigla      TEXT,
    estado_sigla      TEXT,
    municipio         TEXT,
    revenda           TEXT,
    cnpj_revenda      TEXT,
    nome_rua          TEXT,
    numero_rua        TEXT,
    complemento       TEXT,
    bairro            TEXT,
    cep               TEXT,
    produto           TEXT,
    data_coleta       TEXT,
    valor_venda       TEXT,
    valor_compra      TEXT,
    unidade_medida    TEXT,
    bandeira          TEXT,
    arquivo_origem    TEXT,
    carregado_em      TIMESTAMPTZ DEFAULT now()
);
