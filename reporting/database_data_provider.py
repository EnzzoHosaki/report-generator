from __future__ import annotations
import firebirdsql
from typing import Dict, Any, List, Optional
from decimal import Decimal

from .data_provider import DataProvider


class DatabaseDataProvider(DataProvider):
    """
    Provider para Firebird/Athenas.
    Mantém apenas a conexão com o banco e as variáveis dos indicadores
    necessários para a apresentação (todos zerados).
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

    # -- Conexão -------------------------------------------------------

    def _get_connection(self, charset='WIN1252'):
        return firebirdsql.connect(
            host=self.host,
            port=self.port,
            database=self.database,
            user=self.user,
            password=self.password,
            charset=charset
        )

    # -- Helpers --------------------------------------------------------

    def _fmt_brl(self, val: float) -> str:
        if val is None:
            val = 0.0
        if isinstance(val, Decimal):
            val = float(val)
        return f"R$ {val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    def _row_to_dict(self, cursor, row) -> Dict[str, Any]:
        col_names = [col[0].lower() for col in cursor.description]
        return dict(zip(col_names, row))

    # -- Listagens (alimentam o dashboard) -----------------------------

    def listar_clientes(self) -> List[Dict[str, Any]]:
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            try:
                cursor.execute("SELECT codigo, nome, fantaisa FROM tabempresas ORDER BY nome")
            except Exception:
                if conn:
                    conn.rollback()
                cursor = conn.cursor()
                cursor.execute("SELECT codigo, nome, fantasia FROM tabempresas ORDER BY nome")

            rows = cursor.fetchall()
            clientes = [self._row_to_dict(cursor, row) for row in rows]
            for c in clientes:
                val = c.get('fantasia') or c.get('fantaisa') or ''
                c['fantasia'] = val
                c['fantaisa'] = val
            return clientes
        except Exception as e:
            print(f"Erro listar clientes: {e}")
            return []
        finally:
            if conn:
                conn.close()

    def listar_filiais(self, codigo_empresa: int) -> List[Dict[str, Any]]:
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            sql = """
                SELECT
                    F.CODIGO,
                    F.NOME,
                    COALESCE(F.FANTASIA, F.NOME) AS FANTASIA
                FROM TABFILIAL F
                WHERE F.CODIGOEMPRESA = ?
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
                filiais.append({
                    'codigo': 0,
                    'nome': 'Matriz',
                    'fantasia': 'Matriz'
                })
            return filiais
        except Exception as e:
            print(f"Erro listar filiais: {e}")
            return [{'codigo': 0, 'nome': 'Matriz', 'fantasia': 'Matriz'}]
        finally:
            if conn:
                conn.close()

    # -- Contexto de dados (valores zerados) ---------------------------

    def obter_contexto_dados(
        self,
        cliente_id: int,
        anos: List[int],
        meses: List[int],
        filiais: Optional[List[int]] = None
    ) -> Dict[str, Any]:
        """
        Retorna o contexto de dados com todas as variáveis dos indicadores
        necessárias para a apresentação, porém com valores zerados.
        A conexão com o banco é usada apenas para obter o nome do cliente.
        """
        conn = None
        try:
            conn = self._get_connection()
            nome_cliente = f"Empresa {cliente_id}"
            try:
                cur = conn.cursor()
                cur.execute("SELECT NOME, FANTAISA FROM TABEMPRESAS WHERE CODIGO = ?", (cliente_id,))
                row = cur.fetchone()
                if row:
                    nome_cliente = row[1] if row[1] and row[1].strip() else row[0]
            except Exception:
                pass

            meses_sorted = sorted(meses)
            if len(meses_sorted) > 2:
                meses_str = f"{meses_sorted[0]} - {meses_sorted[-1]}"
            else:
                meses_str = ','.join(map(str, meses_sorted))
            anos_str = ','.join(map(str, anos))
            periodo_display = f"{meses_str}/{anos_str}"

            return self._contexto_zerado(cliente_id, nome_cliente, periodo_display)

        except Exception as e:
            print(f"Erro no provider: {e}")
            return self._contexto_zerado(cliente_id)
        finally:
            if conn:
                conn.close()

    # -- Estrutura zerada de indicadores -------------------------------

    def _contexto_zerado(
        self,
        cliente_id: int,
        nome_cliente: str = "Erro",
        periodo: str = "N/A"
    ) -> Dict[str, Any]:
        z = self._fmt_brl(0)
        return {
            "dados": {
                "cliente_id": cliente_id,
                "cliente_nome": nome_cliente,
                "periodo": periodo,
                "kpis": {
                    "vendas_liquidas": z,
                    "carga_tributaria": z,
                    "compras": z,
                    "capex": z,
                    "opex": z,
                    "finex": z,
                    "outros": z,
                    "lucro_liquido": z,
                    "lucro_liquido_raw": 0,
                },
                "indicadores": {
                    "ebitda": z,
                    "liquidez_corrente": "0",
                    "margem_liquida": "0%",
                    "endividamento": "0%",
                },
                "estudo_tributario": {
                    "lucro_real_valor": z,
                    "lucro_real_irpj": z,
                    "lucro_real_csll": z,
                    "lucro_presumido_valor": z,
                    "lucro_presumido_irpj": z,
                    "lucro_presumido_csll": z,
                    "economia_mensal": z,
                    "economia_anual": z,
                    "recomendacao": "-",
                },
                "distribuicao_lucros": {
                    "total": z,
                    "socios": [],
                },
                "tabela_roe": [],
            },
            "graficos_data": {
                "vendas_evo": [0.0] * 12,
                "custos_evo": [0.0] * 12,
                "ativos_evo": [0.0] * 12,
                "pl_evo": [0.0] * 12,
                "composicao_ativo": [0, 0],
                "composicao_passivo": [0, 0],
                "custos_detalhe": [0, 0, 0],
            },
        }
