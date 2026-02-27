-- ============================================
-- VIEWS CONTÁBEIS PARA O REPORT GENERATOR
-- Baseadas na consulta do Power BI que traz os números corretos
-- ============================================

-- ============================================
-- 1. VIEW: VW_PLANO_CONTAS_RPS
-- Plano de contas simplificado
-- ============================================
CREATE OR ALTER VIEW VW_PLANO_CONTAS_RPS (
    CODIGO, 
    CODIGOREDUZIDO, 
    NIVEL, 
    TIPO, 
    NATUREZA, 
    NOME, 
    CODIGOCONTAMAE
)
AS
SELECT
    CODIGO AS cod_conta,
    CODIGOREDUZIDO AS cod_conta_reduzido,
    NIVEL AS nivel_conta,
    TIPO AS tipo_conta,
    NATUREZA AS natureza_conta,
    NOME AS nome_conta,
    CODIGOCONTAMAE AS cod_conta_mae
FROM
    TABPLANOCONTAS
WHERE
    CODIGOPLANOCONTAS = 11
ORDER BY CODIGO;


-- ============================================
-- 2. VIEW: VW_SALDOS_CONTABEIS_RPS
-- Saldos contábeis detalhados por conta (base do Power BI)
-- ============================================
CREATE OR ALTER VIEW VW_SALDOS_CONTABEIS_RPS (
    COD_EMPRESA, 
    COD_FILIAL, 
    "DATA", 
    COD_CONTA, 
    COD_CONTA_REDUZIDO, 
    NIVEL_CONTA, 
    TIPO_CONTA, 
    NATUREZA_CONTA, 
    NOME_CONTA, 
    COD_CONTA_MAE, 
    INICIAL, 
    VLR_DEBITO, 
    VLR_CREDITO, 
    COD_CENTRO_CUSTO, 
    COD_ATIVIDADE
)
AS
SELECT
    S.CODIGOEMPRESA AS cod_empresa,
    S.CODIGOFILIAL AS cod_filial,
    S.DATA,
    S.CODIGOCONTACONTABIL AS cod_conta,
    P.CODIGOREDUZIDO AS cod_conta_reduzido,
    P.NIVEL AS nivel_conta,
    P.TIPO AS tipo_conta,
    CASE
        P.NATUREZA 
        WHEN 1 THEN 'D'
        WHEN 2 THEN 'C'
    END AS natureza_conta,
    P.NOME AS nome_conta,
    P.CODIGOCONTAMAE AS cod_conta_mae,
    S.INICIAL,
    S.VALORDEBITO AS vlr_debito,
    S.VALORCREDITO AS vlr_credito,
    S.CODIGOCENTROCUSTO AS cod_centro_custo,
    S.CODIGOATIVIDADE AS cod_atividade
FROM
    TABSALDOCONTABIL S
JOIN VW_PLANO_CONTAS_RPS P ON
    P.CODIGO = S.CODIGOCONTACONTABIL
WHERE
    S.INICIAL <> 1;


-- ============================================
-- 3. VIEW: VW_BALANCETE_RPS
-- Balancete agregado por empresa/filial/conta/período
-- Esta é a view principal que o relatório deve usar
-- Baseada na consulta exata do Power BI
-- ============================================
CREATE OR ALTER VIEW VW_BALANCETE_RPS (
    COD_EMPRESA,
    NOME_EMPRESA,
    COD_FILIAL,
    NOME_FILIAL,
    NOME_FANTASIA_FILIAL,
    COD_CONTA,
    ANO,
    MES,
    SALDO_INICIAL,
    NOME_CONTA,
    TIPO_CONTA,
    NATUREZA,
    NATUREZA_COD,
    COD_GRUPO,
    NIVEL_CONTA,
    DEBITO,
    CREDITO,
    SALDO
)
AS
SELECT
    E.CODIGO AS COD_EMPRESA,
    E.NOME AS NOME_EMPRESA,
    COALESCE(F.CODIGO, 0) AS COD_FILIAL,
    COALESCE(F.NOME, 'Matriz') AS NOME_FILIAL,
    COALESCE(F.FANTASIA, F.NOME, 'Matriz') AS NOME_FANTASIA_FILIAL,
    S.CODIGOCONTACONTABIL AS COD_CONTA,
    EXTRACT(YEAR FROM S.DATA) AS ANO,
    EXTRACT(MONTH FROM S.DATA) AS MES,
    MIN(S.INICIAL) AS SALDO_INICIAL,
    P.NOME AS NOME_CONTA,
    CASE
        WHEN P.TIPO = 1 THEN 'Sintetica'
        ELSE 'Analitica'
    END AS TIPO_CONTA,
    CASE
        WHEN P.NATUREZA = 1 THEN 'Devedora'
        ELSE 'Credora'
    END AS NATUREZA,
    P.NATUREZA AS NATUREZA_COD,
    SUBSTRING(S.CODIGOCONTACONTABIL FROM 1 FOR 1) AS COD_GRUPO,
    P.NIVEL AS NIVEL_CONTA,
    SUM(CAST(S.VALORDEBITO AS DECIMAL(15, 2))) AS DEBITO,
    SUM(CAST(S.VALORCREDITO AS DECIMAL(15, 2))) AS CREDITO,
    -- Calcula o saldo considerando a natureza da conta
    CASE 
        WHEN P.NATUREZA = 1 THEN  -- Devedora: Débito - Crédito
            SUM(CAST(S.VALORDEBITO AS DECIMAL(15, 2))) - SUM(CAST(S.VALORCREDITO AS DECIMAL(15, 2)))
        ELSE  -- Credora: Crédito - Débito
            SUM(CAST(S.VALORCREDITO AS DECIMAL(15, 2))) - SUM(CAST(S.VALORDEBITO AS DECIMAL(15, 2)))
    END AS SALDO
FROM
    TABSALDOCONTABIL S
JOIN TABPLANOCONTAS P 
    ON P.CODIGO = S.CODIGOCONTACONTABIL
JOIN TABEMPRESAS E 
    ON E.CODIGO = S.CODIGOEMPRESA 
LEFT JOIN TABFILIAL F 
    ON E.CODIGO = F.CODIGOEMPRESA AND F.CODIGO = S.CODIGOFILIAL
WHERE
    S.INICIAL NOT IN (2, 4, 5) -- Exclui os valores de INICIAL 2, 4 e 5
    AND P.CODIGOPLANOCONTAS = 11
GROUP BY
    E.CODIGO,
    E.NOME,
    COALESCE(F.CODIGO, 0),
    COALESCE(F.NOME, 'Matriz'),
    COALESCE(F.FANTASIA, F.NOME, 'Matriz'),
    S.CODIGOCONTACONTABIL,
    EXTRACT(YEAR FROM S.DATA),
    EXTRACT(MONTH FROM S.DATA),
    P.NOME,
    P.TIPO,
    P.NATUREZA,
    P.NIVEL,
    SUBSTRING(S.CODIGOCONTACONTABIL FROM 1 FOR 1);


-- ============================================
-- 4. VIEW: VW_TOTAIS_GRUPO_RPS
-- Totais agregados por grupo contábil (1-Ativo, 2-Passivo, etc)
-- Útil para KPIs e indicadores do relatório
-- ============================================
CREATE OR ALTER VIEW VW_TOTAIS_GRUPO_RPS (
    COD_EMPRESA,
    NOME_EMPRESA,
    COD_FILIAL,
    ANO,
    MES,
    COD_GRUPO,
    NOME_GRUPO,
    TOTAL_DEBITO,
    TOTAL_CREDITO,
    SALDO_GRUPO
)
AS
SELECT
    COD_EMPRESA,
    NOME_EMPRESA,
    COD_FILIAL,
    ANO,
    MES,
    COD_GRUPO,
    CASE COD_GRUPO
        WHEN '1' THEN 'ATIVO'
        WHEN '2' THEN 'PASSIVO'
        WHEN '3' THEN 'RECEITAS'
        WHEN '4' THEN 'CUSTOS/ENTRADAS'
        WHEN '5' THEN 'DESPESAS'
        WHEN '6' THEN 'RESULTADO'
        ELSE 'OUTROS'
    END AS NOME_GRUPO,
    SUM(DEBITO) AS TOTAL_DEBITO,
    SUM(CREDITO) AS TOTAL_CREDITO,
    SUM(SALDO) AS SALDO_GRUPO
FROM
    VW_BALANCETE_RPS
GROUP BY
    COD_EMPRESA,
    NOME_EMPRESA,
    COD_FILIAL,
    ANO,
    MES,
    COD_GRUPO;


-- ============================================
-- EXEMPLO DE USO
-- ============================================
-- 
-- Balancete completo de uma empresa:
-- SELECT * FROM VW_BALANCETE_RPS WHERE COD_EMPRESA = 1 AND ANO = 2024 AND MES = 1;
--
-- Totais por grupo:
-- SELECT * FROM VW_TOTAIS_GRUPO_RPS WHERE COD_EMPRESA = 1 AND ANO = 2024 AND MES = 1;
--
-- Receita Bruta (grupo 3):
-- SELECT SALDO_GRUPO FROM VW_TOTAIS_GRUPO_RPS WHERE COD_EMPRESA = 1 AND ANO = 2024 AND MES = 1 AND COD_GRUPO = '3';
--
-- ============================================
