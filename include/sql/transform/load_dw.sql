-- Transforma raw -> dw. Idempotente: pode rodar várias vezes sobre os mesmos
-- dados sem duplicar nada (ON CONFLICT em todas as tabelas).

BEGIN;

-- 1. Staging tipada: limpa e converte uma vez, reaproveita em todas as cargas.
CREATE TEMP TABLE stg_precos ON COMMIT DROP AS
SELECT
    UPPER(TRIM(regiao_sigla))                                  AS regiao_sigla,
    UPPER(TRIM(estado_sigla))                                  AS uf_sigla,
    UPPER(TRIM(municipio))                                     AS municipio,
    TRIM(revenda)                                              AS nome_revenda,
    REGEXP_REPLACE(cnpj_revenda, '\D', '', 'g')                AS cnpj,
    TRIM(bairro)                                               AS bairro,
    REGEXP_REPLACE(cep, '\D', '', 'g')                         AS cep,
    UPPER(TRIM(produto))                                       AS produto,
    TO_DATE(data_coleta, 'DD/MM/YYYY')                         AS data_coleta,
    NULLIF(REPLACE(TRIM(valor_venda), ',', '.'), '')::NUMERIC  AS valor_venda,
    NULLIF(REPLACE(TRIM(valor_compra), ',', '.'), '')::NUMERIC AS valor_compra,
    TRIM(unidade_medida)                                       AS unidade_medida,
    UPPER(TRIM(bandeira))                                      AS bandeira
FROM raw.precos_combustiveis
WHERE data_coleta ~ '^\d{2}/\d{2}/\d{4}$'
  AND NULLIF(TRIM(valor_venda), '') IS NOT NULL;

-- 2. Dimensões
INSERT INTO dw.dim_produto (nome_produto, unidade_medida)
SELECT DISTINCT ON (produto) produto, unidade_medida
FROM stg_precos
ORDER BY produto, data_coleta DESC
ON CONFLICT (nome_produto) DO UPDATE
    SET unidade_medida = EXCLUDED.unidade_medida;

INSERT INTO dw.dim_localidade (regiao_sigla, uf_sigla, municipio)
SELECT DISTINCT regiao_sigla, uf_sigla, municipio
FROM stg_precos
ON CONFLICT (uf_sigla, municipio) DO NOTHING;

-- Para cada CNPJ fica o cadastro mais recente (SCD tipo 1).
INSERT INTO dw.dim_revenda (cnpj, nome_revenda, bandeira, bairro, cep)
SELECT DISTINCT ON (cnpj) cnpj, nome_revenda, bandeira, bairro, cep
FROM stg_precos
ORDER BY cnpj, data_coleta DESC
ON CONFLICT (cnpj) DO UPDATE
    SET nome_revenda = EXCLUDED.nome_revenda,
        bandeira     = EXCLUDED.bandeira,
        bairro       = EXCLUDED.bairro,
        cep          = EXCLUDED.cep;

-- 3. Fato. DISTINCT ON garante uma linha por chave mesmo se a ANP
--    publicar a mesma coleta duas vezes.
INSERT INTO dw.fato_preco_combustivel
    (data_sk, produto_sk, localidade_sk, revenda_sk, valor_venda, valor_compra)
SELECT DISTINCT ON (t.data_sk, p.produto_sk, r.revenda_sk)
    t.data_sk, p.produto_sk, l.localidade_sk, r.revenda_sk,
    s.valor_venda, s.valor_compra
FROM stg_precos s
JOIN dw.dim_tempo      t ON t.data = s.data_coleta
JOIN dw.dim_produto    p ON p.nome_produto = s.produto
JOIN dw.dim_localidade l ON l.uf_sigla = s.uf_sigla AND l.municipio = s.municipio
JOIN dw.dim_revenda    r ON r.cnpj = s.cnpj
ORDER BY t.data_sk, p.produto_sk, r.revenda_sk
ON CONFLICT (data_sk, produto_sk, revenda_sk) DO UPDATE
    SET valor_venda  = EXCLUDED.valor_venda,
        valor_compra = EXCLUDED.valor_compra;

COMMIT;
