from __future__ import annotations
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import Dict, Any, List
from datetime import datetime

from .data_provider import DataProvider


class DatabaseDataProvider(DataProvider):
    """
    Implementação do DataProvider usando PostgreSQL.
    Conecta ao banco dw_athenas e busca dados reais das empresas.
    """

    def __init__(
        self,
        host: str = "192.168.10.46",
        port: int = 5433,
        database: str = "dw_athenas",
        user: str = "postgres",
        password: str = "admin",
    ) -> None:
        """
        Inicializa a conexão com o banco de dados PostgreSQL.
        
        Args:
            host: Host do banco de dados
            port: Porta do banco de dados
            database: Nome do banco de dados
            user: Usuário do banco de dados
            password: Senha do banco de dados
        """
        self.host = host
        self.port = port
        self.database = database
        self.user = user
        self.password = password
        self._connection = None
        self._empresas_cache = None

    def _get_connection(self):
        """Obtém ou cria uma conexão com o banco de dados."""
        if self._connection is None or self._connection.closed:
            self._connection = psycopg2.connect(
                host=self.host,
                port=self.port,
                database=self.database,
                user=self.user,
                password=self.password,
            )
        return self._connection

    def _fmt_brl(self, val: float) -> str:
        """Formata valor como BRL."""
        return f"R$ {val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    def listar_clientes(self) -> List[Dict[str, Any]]:
        """
        Retorna lista de empresas da tabela tabempresas com codigo, nome e fantasia.
        """
        if self._empresas_cache is not None:
            return self._empresas_cache

        try:
            conn = self._get_connection()
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(
                    "SELECT codigo, nome, fantaisa FROM tabempresas ORDER BY nome"
                )
                self._empresas_cache = cursor.fetchall()
                return self._empresas_cache
        except Exception as e:
            print(f"Erro ao listar clientes: {e}")
            return []

    def obter_contexto_dados(self, cliente_id: int, periodo: str) -> Dict[str, Any]:
        """
        Gera/retorna o contexto de DADOS do relatório.
        Por enquanto usa dados mock, mas a estrutura está pronta para integração real.
        """
        # Buscar dados da empresa
        empresas = self.listar_clientes()
        empresa = next((e for e in empresas if e["codigo"] == cliente_id), None)

        if empresa is None:
            # Fallback para empresa genérica
            cliente_nome = f"Empresa {cliente_id}"
        else:
            # Usar nome da empresa ou fantasia
            cliente_nome = empresa.get("fantaisa") or empresa.get("nome")

        # Dados básicos
        cliente_info = {
            "cliente_id": cliente_id,
            "cliente_nome": cliente_nome,
            "periodo": periodo or datetime.now().strftime("%B/%Y"),
        }

        # KPIs (ainda usando valores simulados, mas com nome real da empresa)
        import random
        vendas = random.uniform(500000, 1000000)
        impostos = vendas * 0.18
        compras = vendas * 0.40
        capex = vendas * 0.05
        opex = vendas * 0.15
        finex = vendas * 0.03
        outros = vendas * 0.02
        lucro = vendas - (impostos + compras + capex + opex + finex + outros)

        kpis = {
            "vendas_liquidas": self._fmt_brl(vendas),
            "carga_tributaria": self._fmt_brl(impostos),
            "compras": self._fmt_brl(compras),
            "capex": self._fmt_brl(capex),
            "opex": self._fmt_brl(opex),
            "finex": self._fmt_brl(finex),
            "outros": self._fmt_brl(outros),
            "lucro_liquido": self._fmt_brl(lucro),
            "lucro_liquido_raw": lucro,
        }

        indicadores = {
            "ebitda": self._fmt_brl(vendas * 0.15),
            "liquidez_corrente": "1.45",
            "margem_liquida": "12%",
            "endividamento": "45%",
            "roa": "8%",
            "ncg": self._fmt_brl(vendas * 0.1),
        }

        tabela_roe = [
            {"periodo": "3 M", "roe": 4.5, "cdi": 2.8, "delta": 1.7},
            {"periodo": "6 M", "roe": 8.2, "cdi": 5.5, "delta": 2.7},
            {"periodo": "12 M", "roe": 15.1, "cdi": 11.2, "delta": 3.9},
        ]

        return {
            "dados": {
                "cliente_id": cliente_id,
                "cliente_nome": cliente_info["cliente_nome"],
                "periodo": cliente_info["periodo"],
                "kpis": kpis,
                "indicadores": indicadores,
                "tabela_roe": tabela_roe,
            }
        }

    def close(self):
        """Fecha a conexão com o banco de dados."""
        if self._connection and not self._connection.closed:
            self._connection.close()

    def __del__(self):
        """Garante fechamento da conexão ao destruir o objeto."""
        self.close()
