-- A dimensão tempo é gerada, não carregada: cobre de 2004 (início da série
-- da ANP) até o fim de 2030.
INSERT INTO dw.dim_tempo
SELECT
    TO_CHAR(d, 'YYYYMMDD')::INTEGER                       AS data_sk,
    d::DATE                                               AS data,
    EXTRACT(YEAR FROM d)::SMALLINT                        AS ano,
    CASE WHEN EXTRACT(MONTH FROM d) <= 6 THEN 1 ELSE 2 END AS semestre,
    EXTRACT(QUARTER FROM d)::SMALLINT                     AS trimestre,
    EXTRACT(MONTH FROM d)::SMALLINT                       AS mes,
    (ARRAY['janeiro','fevereiro','março','abril','maio','junho','julho',
           'agosto','setembro','outubro','novembro','dezembro'])
        [EXTRACT(MONTH FROM d)]                           AS nome_mes,
    TO_CHAR(d, 'YYYY-MM')                                 AS ano_mes,
    EXTRACT(DAY FROM d)::SMALLINT                         AS dia,
    EXTRACT(ISODOW FROM d)::SMALLINT                      AS dia_semana,
    EXTRACT(ISODOW FROM d) IN (6, 7)                      AS fim_de_semana
FROM GENERATE_SERIES('2004-01-01'::DATE, '2030-12-31'::DATE, INTERVAL '1 day') AS d
ON CONFLICT (data_sk) DO NOTHING;
