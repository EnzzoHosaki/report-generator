from __future__ import annotations
import firebirdsql
from typing import Dict, Any, List, Optional
from datetime import datetime
from decimal import Decimal

from .data_provider import DataProvider


class DatabaseDataProvider(DataProvider):
    """
    Provider para Firebird de forma "Bruta e Direta".
    Executa a consulta SQL exatamente como testada no banco de dados,
    sem lógicas complexas de hierarquia ou herança no Python.
    """

    def __init__(
        self,
        host: str = "192.168.10.160",
        port: int = 3050,
        database: str = r"e:\Athenas\rps.fdb",
        user: str = "SYSDBA",
        password: str = "masterkey",
    ) -> None:
        self.host = host
        self.port = port
        self.database = database
        self.user = user
        self.password = password

    def _get_connection(self, charset='ISO8859_1'):
        return firebirdsql.connect(
            host=self.host,
            port=self.port,
            database=self.database,
            user=self.user,
            password=self.password,
            charset=charset
        )

    def _fmt_brl(self, val: float) -> str:
        if val is None: 
            val = 0.0
        if isinstance(val, Decimal):
            val = float(val)
        return f"R$ {val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    def _row_to_dict(self, cursor, row) -> Dict[str, Any]:
        col_names = [col[0].lower() for col in cursor.description]
        return dict(zip(col_names, row))

    def listar_clientes(self) -> List[Dict[str, Any]]:
        conn = None
        try:
            conn = self._get_connection(charset='WIN1252')
            cursor = conn.cursor()
            try:
                cursor.execute("SELECT codigo, nome, fantaisa FROM tabempresas ORDER BY nome")
            except Exception:
                if conn: conn.rollback()
                cursor = conn.cursor()
                cursor.execute("SELECT codigo, nome, fantasia FROM tabempresas ORDER BY nome")
            
            rows = cursor.fetchall()
            clientes = [self._row_to_dict(cursor, row) for row in rows]
            for c in clientes:
                val = c.get('fantasia') or c.get('fantaisa') or ''
                c['fantasia'] = val
            return clientes
        except Exception as e:
            print(f"Erro ao listar clientes: {e}")
            return []
        finally:
            if conn: conn.close()

    def listar_filiais(self, codigo_empresa: int) -> List[Dict[str, Any]]:
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            sql = """
                SELECT DISTINCT
                    F.CODIGO,
                    F.NOME,
                    COALESCE(F.FANTASIA, F.NOME) AS FANTASIA
                FROM TABSALDOCONTABIL S
                JOIN TABEMPRESAS E ON E.CODIGO = S.CODIGOEMPRESA
                LEFT JOIN TABFILIAL F ON E.CODIGO = F.CODIGOEMPRESA
                WHERE S.CODIGOEMPRESA = ? AND S.INICIAL NOT IN (2, 4, 5) AND F.CODIGO IS NOT NULL
                ORDER BY F.CODIGO
            """
            cursor.execute(sql, (codigo_empresa,))
            rows = cursor.fetchall()
            
            filiais = []
            for row in rows:
                filiais.append({
                    'codigo': row[0],
                    'nome': row[1] or f'Filial {row[0]}',
                    'fantasia': row[2] or row[1] or f'Filial {row[0]}'
                })
            
            if not filiais:
                filiais.append({'codigo': 0, 'nome': 'Matriz', 'fantasia': 'Matriz'})
            return filiais
        except Exception as e:
            print(f"Erro ao listar filiais: {e}")
            return [{'codigo': 0, 'nome': 'Matriz', 'fantasia': 'Matriz'}]
        finally:
            if conn: conn.close()

    @staticmethod
    def calcular_capex(dados_filtrados: List[Dict[str, Any]]) -> float:
        """
        Calcula o CAPEX (Capital Expenditure) a partir de uma lista de contas
        já filtrada por período.

        Regras:
        - Apenas contas analíticas (TIPO_CONTA == 'Analitica')
        - Incluir contas que começam com 1.2.03 (Imobilizado) e 1.2.04 (Intangível)
        - Excluir contas redutoras: 1.2.03.10 (Depreciação) e 1.2.04.03 (Amortização)
        - Somar a coluna DEBITO das contas restantes
        """
        total = 0.0
        for conta in dados_filtrados:
            tipo = conta.get('tipo', '') or conta.get('tipo_conta', '')
            if tipo != 'Analitica':
                continue

            codigo = conta.get('codigo', '') or conta.get('cod_conta_contabil', '')
            cod_limpo = ''.join(c for c in codigo if c.isdigit())

            # Incluir: 1.2.03 -> '1203' e 1.2.04 -> '1204'
            if not (cod_limpo.startswith('1203') or cod_limpo.startswith('1204')):
                continue

            # Excluir redutoras: 1.2.03.10 -> '120310' e 1.2.04.03 -> '120403'
            if cod_limpo.startswith('120310') or cod_limpo.startswith('120403'):
                continue

            total += conta.get('debito', 0.0)

        return total

    @staticmethod
    def _determinar_periodo_anterior(
        anos: List[int], meses: List[int]
    ) -> Dict[str, List[int]]:
        """
        Determina o Período Anterior com base na seleção do usuário.

        - Ano inteiro (12 meses): período anterior = mesmo intervalo do ano anterior.
        - Mês único: período anterior = mês imediatamente anterior (com rollover de ano).
        - Outros casos: mesmos meses, ano anterior.
        """
        ano = anos[0] if anos else 2025

        if len(meses) == 12:
            # Seleção de ano inteiro
            return {"anos": [ano - 1], "meses": list(range(1, 13))}

        if len(meses) == 1:
            mes = meses[0]
            if mes == 1:
                return {"anos": [ano - 1], "meses": [12]}
            else:
                return {"anos": [ano], "meses": [mes - 1]}

        # Caso genérico (vários meses, mas não o ano inteiro)
        return {"anos": [ano - 1], "meses": meses}

    def obter_capex(
        self,
        cliente_id: int,
        anos: List[int],
        meses: List[int],
        filiais: Optional[List[int]] = None
    ) -> Dict[str, Any]:
        """
        Calcula o CAPEX do Período Atual e do Período Anterior.

        Retorna um dicionário com:
        - capex_atual: valor formatado como moeda
        - capex_anterior: valor formatado como moeda
        - capex_atual_raw: valor numérico
        - capex_anterior_raw: valor numérico
        - variacao_percentual: string com a variação % entre os períodos
        """
        # --- Período Atual ---
        dados_atual = self.obter_dados_brutos(cliente_id, anos, meses, filiais)
        capex_atual = self.calcular_capex(dados_atual)

        # --- Período Anterior ---
        periodo_ant = self._determinar_periodo_anterior(anos, meses)
        dados_anterior = self.obter_dados_brutos(
            cliente_id, periodo_ant["anos"], periodo_ant["meses"], filiais
        )
        capex_anterior = self.calcular_capex(dados_anterior)

        # --- Variação percentual ---
        if capex_anterior > 0:
            variacao = ((capex_atual - capex_anterior) / capex_anterior) * 100
        elif capex_atual > 0:
            variacao = 100.0
        else:
            variacao = 0.0

        return {
            "capex_atual": self._fmt_brl(capex_atual),
            "capex_anterior": self._fmt_brl(capex_anterior),
            "capex_atual_raw": capex_atual,
            "capex_anterior_raw": capex_anterior,
            "variacao_percentual": f"{variacao:+.1f}%",
            "variacao_raw": variacao,
        }

    def obter_ativos_evolucao(
        self,
        cliente_id: int,
        ano: int,
        filiais: Optional[List[int]] = None
    ) -> List[float]:
        """
        Retorna a evolução mensal (12 meses) dos ativos no ano informado.

        Regra de acumulação:
        - Base inicial (jan): soma de todos os saldos de contas de ativo (prefixo "1")
          com DATA anterior a 01/01 do ano filtrado.
        - Em cada mês do ano filtrado, soma apenas o movimento daquele mês,
          acumulando sobre o total do mês anterior.
        """
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            totais = [0.0] * 12
            movimentos_mensais = [0.0] * 12

            data_inicio_ano = datetime(ano, 1, 1)

            # 1) Base histórica: tudo que veio antes do ano filtrado
            sql_base = """
                SELECT
                  S.CODIGOCONTACONTABIL AS COD_CONTA,
                  P.NOME AS NOME_CONTA,
                  CASE
                    WHEN P.NATUREZA = 1 THEN
                      SUM(CAST(S.VALORDEBITO AS DECIMAL(15, 2))) - SUM(CAST(S.VALORCREDITO AS DECIMAL(15, 2)))
                    ELSE
                      SUM(CAST(S.VALORCREDITO AS DECIMAL(15, 2))) - SUM(CAST(S.VALORDEBITO AS DECIMAL(15, 2)))
                  END AS SALDO
                FROM TABSALDOCONTABIL S
                JOIN TABPLANOCONTAS P ON P.CODIGO = S.CODIGOCONTACONTABIL AND P.CODIGOPLANOCONTAS = 11
                WHERE S.INICIAL NOT IN (2, 4, 5)
                  AND S.CODIGOEMPRESA = ?
                  AND S.DATA < ?
                                    AND P.TIPO <> 1
                  AND SUBSTRING(S.CODIGOCONTACONTABIL FROM 1 FOR 1) = '1'
            """
            params_base = [cliente_id, data_inicio_ano]

            if filiais:
                filiais_str = ",".join(map(str, filiais))
                sql_base += f" AND S.CODIGOFILIAL IN ({filiais_str})"

            sql_base += """
                GROUP BY
                  S.CODIGOCONTACONTABIL,
                  P.NOME,
                  P.NATUREZA
            """

            cursor.execute(sql_base, tuple(params_base))
            rows_base = cursor.fetchall()

            saldo_base = 0.0
            for r in rows_base:
                nome_conta = str(r[1]).strip() if r[1] else ''
                saldo = float(r[2]) if r[2] else 0.0
                if nome_conta.startswith('(-)'):
                    saldo = -saldo
                saldo_base += saldo

            # 2) Movimentos por mês do ano filtrado
            sql_mov = """
                SELECT
                  EXTRACT(MONTH FROM S.DATA) AS MES,
                  S.CODIGOCONTACONTABIL AS COD_CONTA,
                  P.NOME AS NOME_CONTA,
                  CASE
                    WHEN P.NATUREZA = 1 THEN
                      SUM(CAST(S.VALORDEBITO AS DECIMAL(15, 2))) - SUM(CAST(S.VALORCREDITO AS DECIMAL(15, 2)))
                    ELSE
                      SUM(CAST(S.VALORCREDITO AS DECIMAL(15, 2))) - SUM(CAST(S.VALORDEBITO AS DECIMAL(15, 2)))
                  END AS SALDO
                FROM TABSALDOCONTABIL S
                JOIN TABPLANOCONTAS P ON P.CODIGO = S.CODIGOCONTACONTABIL AND P.CODIGOPLANOCONTAS = 11
                WHERE S.INICIAL NOT IN (2, 4, 5)
                  AND S.CODIGOEMPRESA = ?
                  AND EXTRACT(YEAR FROM S.DATA) = ?
                                    AND P.TIPO <> 1
                  AND SUBSTRING(S.CODIGOCONTACONTABIL FROM 1 FOR 1) = '1'
            """
            params_mov = [cliente_id, ano]

            if filiais:
                filiais_str = ",".join(map(str, filiais))
                sql_mov += f" AND S.CODIGOFILIAL IN ({filiais_str})"

            sql_mov += """
                GROUP BY
                  EXTRACT(MONTH FROM S.DATA),
                  S.CODIGOCONTACONTABIL,
                  P.NOME,
                  P.NATUREZA
                ORDER BY
                  EXTRACT(MONTH FROM S.DATA),
                  S.CODIGOCONTACONTABIL
            """

            cursor.execute(sql_mov, tuple(params_mov))
            rows_mov = cursor.fetchall()

            for r in rows_mov:
                mes = int(r[0]) if r[0] else 0
                if mes < 1 or mes > 12:
                    continue

                nome_conta = str(r[2]).strip() if r[2] else ''
                saldo = float(r[3]) if r[3] else 0.0
                if nome_conta.startswith('(-)'):
                    saldo = -saldo

                movimentos_mensais[mes - 1] += saldo

            # 3) Série acumulada: base histórica + incrementos mês a mês
            acumulado = saldo_base
            for i in range(12):
                acumulado += movimentos_mensais[i]
                totais[i] = acumulado

            return totais

        except Exception as e:
            print(f"Erro ao obter evolução dos ativos: {e}")
            return [0.0] * 12
        finally:
            if conn: conn.close()

    def obter_dados_brutos(
        self,
        cliente_id: int,
        anos: List[int],
        meses: List[int],
        filiais: Optional[List[int]] = None
    ) -> List[Dict[str, Any]]:
        """
        Executa o SELECT bruto agrupado diretamente no banco.
        Igual à consulta validada via DBeaver/Power BI.
        """
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            sql = """
                SELECT
                  S.CODIGOCONTACONTABIL AS COD_CONTA,
                  P.NOME AS NOME_CONTA,
                  CASE WHEN P.TIPO = 1 THEN 'Sintetica' ELSE 'Analitica' END AS TIPO_CONTA,
                  CASE WHEN P.NATUREZA = 1 THEN 'Devedora' ELSE 'Credora' END AS NATUREZA,
                  SUM(CAST(S.VALORDEBITO AS DECIMAL(15, 2))) AS DEBITO,
                  SUM(CAST(S.VALORCREDITO AS DECIMAL(15, 2))) AS CREDITO,
                  CASE
                    WHEN P.NATUREZA = 1 THEN 
                      SUM(CAST(S.VALORDEBITO AS DECIMAL(15, 2))) - SUM(CAST(S.VALORCREDITO AS DECIMAL(15, 2)))
                    ELSE 
                      SUM(CAST(S.VALORCREDITO AS DECIMAL(15, 2))) - SUM(CAST(S.VALORDEBITO AS DECIMAL(15, 2)))
                  END AS SALDO
                FROM TABSALDOCONTABIL S
                JOIN TABPLANOCONTAS P ON P.CODIGO = S.CODIGOCONTACONTABIL AND P.CODIGOPLANOCONTAS = 11
                WHERE S.INICIAL NOT IN (2, 4, 5) 
                  AND S.CODIGOEMPRESA = ?
            """
            params = [cliente_id]

            if filiais:
                filiais_str = ",".join(map(str, filiais))
                sql += f" AND S.CODIGOFILIAL IN ({filiais_str})"
                
            if anos:
                anos_str = ",".join(map(str, anos))
                sql += f" AND EXTRACT(YEAR FROM S.DATA) IN ({anos_str})"
                
            if meses:
                meses_str = ",".join(map(str, meses))
                sql += f" AND EXTRACT(MONTH FROM S.DATA) IN ({meses_str})"

            sql += """
                GROUP BY
                  S.CODIGOCONTACONTABIL,
                  P.NOME,
                  P.TIPO,
                  P.NATUREZA
                ORDER BY
                  S.CODIGOCONTACONTABIL
            """

            cursor.execute(sql, tuple(params))
            rows = cursor.fetchall()
            
            dados = []
            for r in rows:
                codigo = str(r[0]).strip() if r[0] else ''
                nome = str(r[1]).strip() if r[1] else ''
                saldo = float(r[6]) if r[6] else 0.0
                if nome.startswith('(-)'):
                    saldo = -saldo
                dados.append({
                    'codigo': codigo,
                    'nome': nome,
                    'tipo': str(r[2]).strip(),
                    'natureza': str(r[3]).strip(),
                    'debito': float(r[4]) if r[4] else 0.0,
                    'credito': float(r[5]) if r[5] else 0.0,
                    'saldo': saldo
                })
            
            return dados

        except Exception as e:
            print(f"Erro ao obter dados brutos: {e}")
            return []
        finally:
            if conn: conn.close()

    def obter_balancete(
        self,
        cliente_id: int,
        anos: List[int],
        meses: List[int],
        filiais: Optional[List[int]] = None
    ) -> List[Dict[str, Any]]:
        """
        Retorna os dados do balancete contábil conforme consulta SQL.
        Aplica os filtros de ano, meses e filiais selecionados no relatório.
        """
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            sql = """
                SELECT
                  E.CODIGO AS COD_EMPRESA,
                  E.NOME AS NOME_EMPRESA,
                  F.CODIGO AS COD_FILIAL,
                  F.NOME AS NOME_FILIAL,
                  F.FANTASIA AS NOME_FANTASIA_FILIAL,
                  S.CODIGOCONTACONTABIL AS COD_CONTA_CONTABIL,
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
                  SUBSTRING(S.CODIGOCONTACONTABIL FROM 1 FOR 1) AS COD_GRUPO,
                  SUM(CAST(S.VALORDEBITO AS DECIMAL(15, 2))) AS DEBITO,
                  SUM(CAST(S.VALORCREDITO AS DECIMAL(15, 2))) AS CREDITO,
                  CASE
                    WHEN P.NATUREZA = 1 THEN 
                      SUM(CAST(S.VALORDEBITO AS DECIMAL(15, 2))) - SUM(CAST(S.VALORCREDITO AS DECIMAL(15, 2)))
                    ELSE 
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
                  S.INICIAL NOT IN (2, 4, 5)
                  AND S.CODIGOEMPRESA = ?
            """
            params = [cliente_id]

            if filiais:
                filiais_str = ",".join(map(str, filiais))
                sql += f" AND S.CODIGOFILIAL IN ({filiais_str})"

            if anos:
                anos_str = ",".join(map(str, anos))
                sql += f" AND EXTRACT(YEAR FROM S.DATA) IN ({anos_str})"

            if meses:
                meses_str = ",".join(map(str, meses))
                sql += f" AND EXTRACT(MONTH FROM S.DATA) IN ({meses_str})"

            sql += """
                GROUP BY
                  E.CODIGO,\
                  E.NOME,
                  F.CODIGO,
                  F.NOME,
                  F.FANTASIA,
                  S.CODIGOCONTACONTABIL,
                  P.NOME,
                  P.TIPO,
                  P.NATUREZA,
                  SUBSTRING(S.CODIGOCONTACONTABIL FROM 1 FOR 1)
                ORDER BY
                  S.CODIGOCONTACONTABIL
            """

            cursor.execute(sql, tuple(params))
            rows = cursor.fetchall()

            balancete = []
            for r in rows:
                nome_conta = str(r[7]).strip() if r[7] else ''
                saldo = float(r[13]) if r[13] else 0.0
                if nome_conta.startswith('(-)'):
                    saldo = -saldo
                balancete.append({
                    'cod_empresa': r[0],
                    'nome_empresa': str(r[1]).strip() if r[1] else '',
                    'cod_filial': r[2],
                    'nome_filial': str(r[3]).strip() if r[3] else '',
                    'nome_fantasia_filial': str(r[4]).strip() if r[4] else '',
                    'cod_conta_contabil': str(r[5]).strip() if r[5] else '',
                    'saldo_inicial': float(r[6]) if r[6] else 0.0,
                    'nome_conta': nome_conta,
                    'tipo_conta': str(r[8]).strip() if r[8] else '',
                    'natureza': str(r[9]).strip() if r[9] else '',
                    'cod_grupo': str(r[10]).strip() if r[10] else '',
                    'debito': float(r[11]) if r[11] else 0.0,
                    'credito': float(r[12]) if r[12] else 0.0,
                    'saldo': saldo,
                })

            return balancete

        except Exception as e:
            print(f"Erro ao obter balancete: {e}")
            return []
        finally:
            if conn: conn.close()

    def obter_contexto_dados(
        self, 
        cliente_id: int, 
        anos: List[int], 
        meses: List[int], 
        filiais: Optional[List[int]] = None
    ) -> Dict[str, Any]:
        """
        Consome os dados brutos do SELECT e apenas soma os totais para o Dashboard.
        """
        nome_cliente = f"Empresa {cliente_id}"
        conn = None
        try:
            conn = self._get_connection()
            cur = conn.cursor()
            cur.execute("SELECT NOME FROM TABEMPRESAS WHERE CODIGO = ?", (cliente_id,))
            row = cur.fetchone()
            if row: nome_cliente = str(row[0]).strip()
        except:
            pass
        finally:
            if conn: conn.close()

        # 1. Puxa os dados 100% brutos da consulta
        dados_contabeis = self.obter_dados_brutos(cliente_id, anos, meses, filiais)
        
        # 2. Função "burra e direta" para somar pelo prefixo da conta
        def somar_em(dados: List[Dict[str, Any]], prefixo: str) -> float:
            total = 0.0
            for conta in dados:
                if conta.get('tipo') == 'Sintetica':
                    continue
                cod_limpo = ''.join(c for c in conta['codigo'] if c.isdigit())
                if cod_limpo.startswith(prefixo):
                    total += conta['saldo']
            return total

        def somar(prefixo: str) -> float:
            return somar_em(dados_contabeis, prefixo)

        # --- KPIs extraídos diretamente da soma das contas ---
        receita_bruta_3110 = abs(somar('3110'))
        cancelamentos_3150 = abs(somar('3150'))
        impostos_vendas_3180 = abs(somar('3180'))
        vendas_liquidas = receita_bruta_3110 - cancelamentos_3150 - impostos_vendas_3180

        periodo_ant = self._determinar_periodo_anterior(anos, meses)
        dados_contabeis_ant = self.obter_dados_brutos(
            cliente_id, periodo_ant["anos"], periodo_ant["meses"], filiais
        )
        vendas_liquidas_ant = (
            abs(somar_em(dados_contabeis_ant, '3110'))
            - abs(somar_em(dados_contabeis_ant, '3150'))
            - abs(somar_em(dados_contabeis_ant, '3180'))
        )
        if abs(vendas_liquidas_ant) > 0:
            vendas_liquidas_variacao_raw = ((vendas_liquidas - vendas_liquidas_ant) / abs(vendas_liquidas_ant)) * 100
        elif vendas_liquidas > 0:
            vendas_liquidas_variacao_raw = 100.0
        else:
            vendas_liquidas_variacao_raw = 0.0
        vendas_liquidas_variacao = f"{vendas_liquidas_variacao_raw:+.1f}%"
        compras_comercializacao_4101 = somar('4101')
        devolucoes_4140 = abs(somar('4140'))
        compras = compras_comercializacao_4101 - devolucoes_4140
        desp_admin = abs(somar('53'))
        desp_tributarias = abs(somar('56'))
        desp_fin = abs(somar('57'))
        rec_financeiras = abs(somar('3185'))
        outras_receitas_operacionais = abs(somar('3190'))
        receitas_nao_operacionais = abs(somar('32'))
        result_nao_op = abs(somar('58'))
        impostos = abs(somar('59'))
        outras_despesas = somar('5') - somar('53') - somar('57')
        carga_tributaria = somar('2104')

        lucro = (
            vendas_liquidas
            - abs(compras)
            - abs(desp_admin)
            - abs(desp_fin)
            - abs(outras_despesas)
            + abs(rec_financeiras)
            + abs(outras_receitas_operacionais)
            + abs(receitas_nao_operacionais)
        )
        ebitda = lucro + desp_fin + impostos

        ativo_circ = abs(somar('11'))
        ativo_n_circ = abs(somar('12'))
        passivo_circ = abs(somar('21'))
        passivo_n_circ = abs(somar('22'))
        
        liquidez_corrente = (ativo_circ / passivo_circ) if passivo_circ > 0 else 0
        margem_liquida = (lucro / vendas_liquidas * 100) if vendas_liquidas > 0 else 0
        endividamento = ((passivo_circ + passivo_n_circ) / (ativo_circ + ativo_n_circ) * 100) if (ativo_circ + ativo_n_circ) > 0 else 0

        # --- Estudo Tributário ---
        numero_meses_relatorio = len(meses) if meses else 1

        provisoes_lucro_real = abs(somar('59'))
        base_calculo_irpj_lucro_real = abs(lucro) + provisoes_lucro_real
        irpj_real = base_calculo_irpj_lucro_real * 0.15 if base_calculo_irpj_lucro_real > 0 else 0

        limite_adicional_irpj = numero_meses_relatorio * 20000
        base_calculo_adicional_irpj = (
            base_calculo_irpj_lucro_real - limite_adicional_irpj
            if base_calculo_irpj_lucro_real > limite_adicional_irpj
            else 0
        )
        adicional_irpj = base_calculo_adicional_irpj * 0.10

        total_irpj_lucro_real = irpj_real + adicional_irpj

        base_calculo_csll_lucro_real = abs(lucro) + provisoes_lucro_real
        csll_real = base_calculo_csll_lucro_real * 0.09 if base_calculo_csll_lucro_real > 0 else 0

        total_lucro_real = total_irpj_lucro_real + csll_real
        
        vendas_mercadorias_produtos = abs(somar('3110'))
        cancelamentos_devolucoes_vendas = abs(somar('3150'))
        receitas_financeiras_presumido = abs(somar('3185'))

        base_presumida_irpj = ((vendas_mercadorias_produtos - cancelamentos_devolucoes_vendas) * 0.08) + receitas_financeiras_presumido
        irpj_presumido = base_presumida_irpj * 0.15 if base_presumida_irpj > 0 else 0
        limite_adicional_presumido = numero_meses_relatorio * 20000
        base_calculo_adicional_presumido = (
            base_presumida_irpj - limite_adicional_presumido
            if base_presumida_irpj > limite_adicional_presumido
            else 0
        )
        adicional_presumido = base_calculo_adicional_presumido * 0.10
        base_presumida_csll = ((vendas_mercadorias_produtos - cancelamentos_devolucoes_vendas) * 0.12) + receitas_financeiras_presumido
        csll_presumido = base_presumida_csll * 0.09
        total_lucro_presumido = irpj_presumido + adicional_presumido + csll_presumido
        
        economia = total_lucro_real - total_lucro_presumido

        periodo_display = f"{','.join(map(str, meses))}/{','.join(map(str, anos))}" if meses and anos else "Todo o período"

        # --- CAPEX com comparação de período ---
        capex_data = self.obter_capex(cliente_id, anos, meses, filiais)
        ano_referencia = anos[0] if anos else datetime.now().year
        ativos_evo = self.obter_ativos_evolucao(cliente_id, ano_referencia, filiais)

        return {
            "dados": {
                "cliente_id": cliente_id,
                "cliente_nome": nome_cliente,
                "periodo": periodo_display,
                "kpis": {
                    "vendas_liquidas": self._fmt_brl(vendas_liquidas),
                    "vendas_liquidas_variacao": vendas_liquidas_variacao,
                    "vendas_liquidas_variacao_raw": vendas_liquidas_variacao_raw,
                    "vendas_liquidas_receita_bruta": self._fmt_brl(receita_bruta_3110),
                    "vendas_liquidas_cancelamentos": self._fmt_brl(cancelamentos_3150),
                    "vendas_liquidas_impostos_vendas": self._fmt_brl(impostos_vendas_3180),
                    "carga_tributaria": self._fmt_brl(carga_tributaria),
                    "compras": self._fmt_brl(compras),
                    "compras_comercializacao": self._fmt_brl(compras_comercializacao_4101),
                    "compras_devolucoes": self._fmt_brl(devolucoes_4140),
                    "capex": capex_data["capex_atual"],
                    "capex_anterior": capex_data["capex_anterior"],
                    "capex_variacao": capex_data["variacao_percentual"],
                    "capex_variacao_raw": capex_data["variacao_raw"],
                    "opex": self._fmt_brl(desp_admin),
                    "finex": self._fmt_brl(desp_fin),
                    "outros": self._fmt_brl(outras_despesas),
                    "lucro_liquido": self._fmt_brl(lucro),
                    "lucro_liquido_raw": lucro,
                },
                "indicadores": {
                    "ebitda": self._fmt_brl(ebitda),
                    "liquidez_corrente": f"{liquidez_corrente:.2f}",
                    "margem_liquida": f"{margem_liquida:.1f}%",
                    "endividamento": f"{endividamento:.1f}%",
                },
                "estudo_tributario": {
                    "lucro_real_valor": self._fmt_brl(total_lucro_real),
                    "lucro_real_irpj": self._fmt_brl(total_irpj_lucro_real),
                    "lucro_real_csll": self._fmt_brl(csll_real),
                    "lucro_presumido_valor": self._fmt_brl(total_lucro_presumido),
                    "lucro_presumido_irpj": self._fmt_brl(irpj_presumido + adicional_presumido),
                    "lucro_presumido_csll": self._fmt_brl(csll_presumido),
                    "lucro_real_detalhado": {
                        "resultado_liquido": self._fmt_brl(abs(lucro)),
                        "provisoes_59": self._fmt_brl(provisoes_lucro_real),
                        "base_irpj": self._fmt_brl(base_calculo_irpj_lucro_real),
                        "irpj_15": self._fmt_brl(irpj_real),
                        "numero_meses": numero_meses_relatorio,
                        "limite_adicional": self._fmt_brl(limite_adicional_irpj),
                        "base_adicional_irpj": self._fmt_brl(base_calculo_adicional_irpj),
                        "adicional_irpj_10": self._fmt_brl(adicional_irpj),
                        "total_irpj": self._fmt_brl(total_irpj_lucro_real),
                        "base_csll": self._fmt_brl(base_calculo_csll_lucro_real),
                        "csll_9": self._fmt_brl(csll_real),
                        "total_encargos": self._fmt_brl(total_lucro_real),
                    },
                    "lucro_presumido_detalhado": {
                        "vendas_mercadorias_produtos": self._fmt_brl(vendas_mercadorias_produtos),
                        "cancelamentos_devolucoes_vendas": self._fmt_brl(cancelamentos_devolucoes_vendas),
                        "receitas_financeiras": self._fmt_brl(receitas_financeiras_presumido),
                        "base_irpj": self._fmt_brl(base_presumida_irpj),
                        "irpj_15": self._fmt_brl(irpj_presumido),
                        "numero_meses": numero_meses_relatorio,
                        "limite_adicional": self._fmt_brl(limite_adicional_presumido),
                        "base_adicional_irpj": self._fmt_brl(base_calculo_adicional_presumido),
                        "adicional_irpj_10": self._fmt_brl(adicional_presumido),
                        "total_irpj": self._fmt_brl(irpj_presumido + adicional_presumido),
                        "base_csll": self._fmt_brl(base_presumida_csll),
                        "csll_9": self._fmt_brl(csll_presumido),
                        "total_encargos": self._fmt_brl(total_lucro_presumido),
                    },
                    "economia_mensal": self._fmt_brl(abs(economia) / len(meses)) if meses else self._fmt_brl(0),
                    "economia_anual": self._fmt_brl(abs(economia) * (12 / len(meses))) if meses else self._fmt_brl(0),
                    "recomendacao": "Lucro Presumido" if economia > 0 else "Lucro Real"
                },
                "distribuicao_lucros": {
                    "total": self._fmt_brl(lucro if lucro > 0 else 0),
                    "socios": []
                },
                "tabela_roe": []
            },
            "graficos_data": {
                # Ativos recebe série mensal real; demais séries temporais permanecem zeradas
                "vendas_evo": [0.0]*12, 
                "custos_evo": [0.0]*12,  
                "ativos_evo": ativos_evo,
                "pl_evo": [0.0]*12,      
                "composicao_ativo": [ativo_circ, ativo_n_circ],
                "composicao_passivo": [passivo_circ, passivo_n_circ],
                "custos_detalhe": [abs(somar('53050')), abs(somar('53350')), desp_tributarias]
            }
        }