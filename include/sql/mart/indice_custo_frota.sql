-- Índice de custo de combustível da frota, nominal e real (descontado o IPCA).
--
-- Ideia: o preço do diesel subiu 20%. Mas se a inflação do período foi 15%,
-- o aumento "real" foi bem menor. Este é o número que interessa para orçamento.
--
-- Reconstruído inteiro a cada execução (a tabela é pequena), dentro de uma
-- transação: quem consulta nunca vê a tabela pela metade.

BEGIN;

DELETE FROM mart.indice_custo_frota;

WITH preco_mensal AS (
    SELECT
        t.ano_mes,
        p.nome_produto        AS produto,
        AVG(f.valor_venda)    AS preco_medio
    FROM dw.fato_preco_combustivel f
    JOIN dw.dim_tempo   t USING (data_sk)
    JOIN dw.dim_produto p USING (produto_sk)
    GROUP BY t.ano_mes, p.nome_produto
),
ipca AS (
    -- Número-índice: produto acumulado de (1 + variação mensal).
    -- EXP(SUM(LN(x))) é o jeito SQL de fazer um "produtório".
    SELECT
        TO_CHAR(data, 'YYYY-MM') AS ano_mes,
        valor                    AS ipca_mes_pct,
        EXP(SUM(LN(1 + valor / 100)) OVER (ORDER BY data)) AS indice_ipca
    FROM indicadores.serie_temporal
    WHERE serie = 'ipca'
),
base AS (
    SELECT p.*, i.ipca_mes_pct, i.indice_ipca
    FROM preco_mensal p
    JOIN ipca i USING (ano_mes)       -- só meses com preço E inflação conhecidos
),
com_preco_real AS (
    SELECT
        b.*,
        -- Traz todos os meses para R$ do mês mais recente
        b.preco_medio
          * LAST_VALUE(b.indice_ipca) OVER w_produto / b.indice_ipca AS preco_real,
        LAST_VALUE(b.ano_mes) OVER w_produto                        AS mes_base
    FROM base b
    WINDOW w_produto AS (
        PARTITION BY b.produto ORDER BY b.ano_mes
        ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING
    )
)
INSERT INTO mart.indice_custo_frota (
    ano_mes, produto, preco_medio_nominal, ipca_mes_pct, indice_ipca,
    preco_real, mes_base_preco_real, variacao_nominal_pct, variacao_real_pct
)
SELECT
    ano_mes,
    produto,
    ROUND(preco_medio, 3),
    ipca_mes_pct,
    ROUND(indice_ipca, 8),
    ROUND(preco_real, 3),
    mes_base,
    ROUND(100 * (preco_medio / FIRST_VALUE(preco_medio) OVER w - 1), 2),
    ROUND(100 * (preco_real  / FIRST_VALUE(preco_real)  OVER w - 1), 2)
FROM com_preco_real
WINDOW w AS (PARTITION BY produto ORDER BY ano_mes);

COMMIT;
