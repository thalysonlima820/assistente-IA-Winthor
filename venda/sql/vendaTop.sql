WITH MOVIMENTOS AS (
    SELECT
        M.CODFILIAL,
        TRUNC(M.DTMOV) AS DATA_MOV,
        M.NUMNOTA,
        M.CODPROD,
        P.DESCRICAO AS PRODUTO,

        SUM(NVL(M.QT, 0)) AS QT_VENDIDA,

        SUM(
            NVL(M.QT, 0) * NVL(M.PUNIT, 0)
        ) AS VENDA_MOV,

        SUM(
            NVL(M.QT, 0) * NVL(M.CUSTOFIN, 0)
        ) AS CUSTO

    FROM PCMOV M

    INNER JOIN PCPRODUT P
        ON P.CODPROD = M.CODPROD

    WHERE M.DTMOV >= TO_DATE(
        :datainicio,
        'DD-MON-YYYY',
        'NLS_DATE_LANGUAGE=ENGLISH'
    )

    AND M.DTMOV < TO_DATE(
        :datafim,
        'DD-MON-YYYY',
        'NLS_DATE_LANGUAGE=ENGLISH'
    ) + 1

    AND M.CODOPER IN ('S', 'SB')

    GROUP BY
        M.CODFILIAL,
        TRUNC(M.DTMOV),
        M.NUMNOTA,
        M.CODPROD,
        P.DESCRICAO
),

TOTAL_MOV_NOTA AS (
    SELECT
        CODFILIAL,
        DATA_MOV,
        NUMNOTA,
        SUM(VENDA_MOV) AS TOTAL_MOV_NOTA

    FROM MOVIMENTOS

    GROUP BY
        CODFILIAL,
        DATA_MOV,
        NUMNOTA
),

NOTAS AS (
    SELECT
        P.CODFILIAL,
        TRUNC(P.DTSAIDA) AS DATA_SAIDA,
        P.NUMNOTA,
        SUM(NVL(P.VLTOTAL, 0)) AS VLTOTAL

    FROM PCNFSAID P

    WHERE P.DTSAIDA >= TO_DATE(
        :datainicio,
        'DD-MON-YYYY',
        'NLS_DATE_LANGUAGE=ENGLISH'
    )

    AND P.DTSAIDA < TO_DATE(
        :datafim,
        'DD-MON-YYYY',
        'NLS_DATE_LANGUAGE=ENGLISH'
    ) + 1

    AND P.DTCANCEL IS NULL
    AND P.CONDVENDA IN (1, 5, 7)

    GROUP BY
        P.CODFILIAL,
        TRUNC(P.DTSAIDA),
        P.NUMNOTA
),

BASE AS (
    SELECT
        M.CODFILIAL,
        M.DATA_MOV,
        M.NUMNOTA,
        M.CODPROD,
        M.PRODUTO,
        M.QT_VENDIDA,

        CASE
            WHEN NVL(TM.TOTAL_MOV_NOTA, 0) = 0 THEN 0
            ELSE
                (
                    M.VENDA_MOV /
                    TM.TOTAL_MOV_NOTA
                ) * N.VLTOTAL
        END AS VENDA,

        M.CUSTO

    FROM MOVIMENTOS M

    INNER JOIN TOTAL_MOV_NOTA TM
        ON TM.CODFILIAL = M.CODFILIAL
       AND TM.DATA_MOV = M.DATA_MOV
       AND TM.NUMNOTA = M.NUMNOTA

    INNER JOIN NOTAS N
        ON N.CODFILIAL = M.CODFILIAL
       AND N.DATA_SAIDA = M.DATA_MOV
       AND N.NUMNOTA = M.NUMNOTA
),

PRODUTOS AS (
    SELECT
        B.CODPROD,
        B.PRODUTO,

        ROUND(
            SUM(B.QT_VENDIDA),
            2
        ) AS QT_VENDIDA,

        COUNT(
            DISTINCT
            B.CODFILIAL || '-' ||
            TO_CHAR(B.DATA_MOV, 'YYYYMMDD') || '-' ||
            B.NUMNOTA
        ) AS NUMVENDAS,

        ROUND(
            SUM(B.VENDA),
            2
        ) AS VENDA,

        ROUND(
            SUM(B.CUSTO),
            2
        ) AS CUSTO,

        ROUND(
            SUM(B.VENDA) - SUM(B.CUSTO),
            2
        ) AS LUCRO,

        ROUND(
            SUM(B.VENDA) /
            NULLIF(SUM(B.QT_VENDIDA), 0),
            2
        ) AS PRECO_MEDIO,

        CASE
            WHEN SUM(B.VENDA) = 0 THEN 0
            ELSE ROUND(
                (
                    (
                        SUM(B.VENDA) -
                        SUM(B.CUSTO)
                    ) /
                    SUM(B.VENDA)
                ) * 100,
                2
            )
        END AS MARGEM

    FROM BASE B

    GROUP BY
        B.CODPROD,
        B.PRODUTO
),

RANKING AS (
    SELECT
        P.*,

        ROW_NUMBER() OVER (
            ORDER BY
                CASE
                    WHEN UPPER(:tipo) = 'MAIS' THEN P.VENDA
                END DESC,

                CASE
                    WHEN UPPER(:tipo) = 'MENOS' THEN P.VENDA
                END ASC,

                CASE
                    WHEN UPPER(:tipo) = 'MAIS' THEN P.QT_VENDIDA
                END DESC,

                CASE
                    WHEN UPPER(:tipo) = 'MENOS' THEN P.QT_VENDIDA
                END ASC,

                P.CODPROD
        ) AS POSICAO

    FROM PRODUTOS P
)

SELECT
    R.POSICAO,
    R.CODPROD,
    R.PRODUTO,
    R.QT_VENDIDA,
    R.NUMVENDAS,
    R.VENDA,
    R.CUSTO,
    R.LUCRO,
    R.PRECO_MEDIO,
    R.MARGEM

FROM RANKING R

WHERE R.POSICAO <= :top

ORDER BY
    R.POSICAO