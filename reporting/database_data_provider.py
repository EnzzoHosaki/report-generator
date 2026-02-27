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
                  E.CODIGO,
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
        def somar(prefixo: str) -> float:
            total = 0.0
            for conta in dados_contabeis:
                # Remove pontos/traços do código só por segurança
                cod_limpo = ''.join(c for c in conta['codigo'] if c.isdigit())
                if cod_limpo.startswith(prefixo):
                    total += conta['saldo']
            return total

        # --- KPIs extraídos diretamente da soma das contas ---
        vendas_liquidas = abs(somar('3110')) + abs(somar('3115')) - abs(somar('315'))
        custos = abs(somar('4'))
        desp_admin = abs(somar('53'))
        desp_tributarias = abs(somar('56'))
        desp_fin = abs(somar('57'))
        rec_financeiras = abs(somar('3185'))
        result_nao_op = abs(somar('58'))
        impostos = abs(somar('59'))

        lucro = vendas_liquidas - custos - desp_admin - desp_tributarias - desp_fin + rec_financeiras - result_nao_op - impostos
        ebitda = lucro + desp_fin + impostos

        ativo_circ = abs(somar('11'))
        ativo_n_circ = abs(somar('12'))
        passivo_circ = abs(somar('21'))
        passivo_n_circ = abs(somar('22'))
        
        liquidez_corrente = (ativo_circ / passivo_circ) if passivo_circ > 0 else 0
        margem_liquida = (lucro / vendas_liquidas * 100) if vendas_liquidas > 0 else 0
        endividamento = ((passivo_circ + passivo_n_circ) / (ativo_circ + ativo_n_circ) * 100) if (ativo_circ + ativo_n_circ) > 0 else 0

        carga_tributaria = sum(abs(somar(c)) for c in ['31800000000005', '31800000000001', '31800000000006'])

        # --- Estudo Tributário ---
        lucro_mensal = lucro / len(meses) if meses else lucro
        irpj_real = lucro * 0.15
        adicional_irpj = max(0, (lucro_mensal - 20000) * len(meses)) * 0.10 if meses else 0
        csll_real = lucro * 0.09
        total_lucro_real = irpj_real + adicional_irpj + csll_real
        
        base_presumida_irpj = vendas_liquidas * 0.08
        base_presumida_csll = vendas_liquidas * 0.12
        irpj_presumido = base_presumida_irpj * 0.15
        adicional_presumido = max(0, (base_presumida_irpj / len(meses) - 20000) * len(meses)) * 0.10 if meses else 0
        csll_presumido = base_presumida_csll * 0.09
        total_lucro_presumido = irpj_presumido + adicional_presumido + csll_presumido
        
        economia = total_lucro_real - total_lucro_presumido

        periodo_display = f"{','.join(map(str, meses))}/{','.join(map(str, anos))}" if meses and anos else "Todo o período"

        return {
            "dados": {
                "cliente_id": cliente_id,
                "cliente_nome": nome_cliente,
                "periodo": periodo_display,
                "kpis": {
                    "vendas_liquidas": self._fmt_brl(vendas_liquidas),
                    "carga_tributaria": self._fmt_brl(carga_tributaria),
                    "compras": self._fmt_brl(custos),
                    "capex": self._fmt_brl(0), 
                    "opex": self._fmt_brl(desp_admin),
                    "finex": self._fmt_brl(desp_fin),
                    "outros": self._fmt_brl(result_nao_op),
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
                    "lucro_real_irpj": self._fmt_brl(irpj_real + adicional_irpj),
                    "lucro_real_csll": self._fmt_brl(csll_real),
                    "lucro_presumido_valor": self._fmt_brl(total_lucro_presumido),
                    "lucro_presumido_irpj": self._fmt_brl(irpj_presumido + adicional_presumido),
                    "lucro_presumido_csll": self._fmt_brl(csll_presumido),
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
                # Como simplificamos para apenas uma consulta de totais, mantemos zero os gráficos temporais
                "vendas_evo": [0.0]*12, 
                "custos_evo": [0.0]*12,  
                "ativos_evo": [0.0]*12,   
                "pl_evo": [0.0]*12,      
                "composicao_ativo": [ativo_circ, ativo_n_circ],
                "composicao_passivo": [passivo_circ, passivo_n_circ],
                "custos_detalhe": [abs(somar('53050')), abs(somar('53350')), desp_tributarias]
            }
        }