from __future__ import annotations
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import Dict, Any, List
from datetime import datetime
import random

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

    def listar_filiais(self, codigo_empresa: int) -> List[Dict[str, Any]]:
        """
        Lista as filiais de uma empresa específica.
        
        Args:
            codigo_empresa: Código da empresa (codigoempresa na tabfilial)
            
        Returns:
            Lista de dicionários com informações das filiais
        """
        try:
            conn = self._get_connection()
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(
                    """
                    SELECT codigo, nome, fantasia 
                    FROM tabfilial 
                    WHERE codigoempresa = %s 
                    ORDER BY codigo
                    """,
                    (codigo_empresa,)
                )
                filiais = cursor.fetchall()
                return filiais
        except Exception as e:
            print(f"Erro ao listar filiais: {e}")
            return []

    def obter_contexto_dados(self, cliente_id: int, periodo: str) -> Dict[str, Any]:
        """
        Gera/retorna o contexto de DADOS do relatório.
        Inclui dados simulados para as novas páginas solicitadas.
        """
        # Buscar dados da empresa
        empresas = self.listar_clientes()
        empresa = next((e for e in empresas if e["codigo"] == cliente_id), None)

        if empresa is None:
            cliente_nome = f"Empresa {cliente_id}"
        else:
            cliente_nome = empresa.get("fantaisa") or empresa.get("nome")

        # Dados básicos
        cliente_info = {
            "cliente_id": cliente_id,
            "cliente_nome": cliente_nome,
            "periodo": periodo or datetime.now().strftime("%B/%Y"),
        }

        # KPIs simulados
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
        
        # --- NOVOS DADOS SIMULADOS PARA NOVAS PÁGINAS ---

        # 1. Distribuição de Lucros
        total_distribuido = lucro * 0.6 # Exemplo: 60% do lucro distribuído
        socios = [
            {"nome": "Sócio Fundador A", "perc": 50, "valor": total_distribuido * 0.50},
            {"nome": "Sócio Diretor B", "perc": 30, "valor": total_distribuido * 0.30},
            {"nome": "Sócio Investidor C", "perc": 20, "valor": total_distribuido * 0.20},
        ]
        distribuicao_lucros = {
            "total": self._fmt_brl(total_distribuido),
            "socios": [
                {
                    "nome": s["nome"],
                    "participacao": f"{s['perc']}%",
                    "valor": self._fmt_brl(s["valor"])
                } for s in socios
            ]
        }

        # 2. Estudo Tributário (Comparativo Presumido vs Real)
        # Simulação: Lucro Presumido geralmente paga menos se margem real > presunção
        # Aqui simulamos que o Real seria mais caro para justificar o planejamento
        
        # Cálculo Lucro Real (sobre lucro contábil efetivo)
        base_lucro_real = lucro  # Lucro contábil efetivo
        irpj_real = base_lucro_real * 0.15  # IRPJ 15%
        if base_lucro_real > 60000:  # Adicional de 10% sobre o que exceder R$ 60k
            irpj_real += (base_lucro_real - 60000) * 0.10
        csll_real = base_lucro_real * 0.09  # CSLL 9%
        imposto_real = irpj_real + csll_real
        
        # Cálculo Lucro Presumido (sobre presunção de receita)
        # Presunção de 8% para serviços ou 32% para comércio - usando 8% aqui
        base_presumida = vendas * 0.08
        irpj_presumido = base_presumida * 0.15  # IRPJ 15%
        csll_presumido = base_presumida * 0.09  # CSLL 9%
        imposto_presumido = irpj_presumido + csll_presumido
        
        economia = imposto_real - imposto_presumido
        
        estudo_tributario = {
            "lucro_real_valor": self._fmt_brl(imposto_real),
            "lucro_real_irpj": self._fmt_brl(irpj_real),
            "lucro_real_csll": self._fmt_brl(csll_real),
            "lucro_presumido_valor": self._fmt_brl(imposto_presumido),
            "lucro_presumido_irpj": self._fmt_brl(irpj_presumido),
            "lucro_presumido_csll": self._fmt_brl(csll_presumido),
            "economia_anual": self._fmt_brl(economia * 12), # Projeção anual
            "economia_mensal": self._fmt_brl(economia),
            "recomendacao": "Lucro Presumido" if imposto_presumido < imposto_real else "Lucro Real"
        }

        return {
            "dados": {
                "cliente_id": cliente_id,
                "cliente_nome": cliente_info["cliente_nome"],
                "periodo": cliente_info["periodo"],
                "kpis": kpis,
                "indicadores": indicadores,
                "tabela_roe": tabela_roe,
                "distribuicao_lucros": distribuicao_lucros,
                "estudo_tributario": estudo_tributario
            }
        }

    def close(self):
        if self._connection and not self._connection.closed:
            self._connection.close()

    def __del__(self):
        self.close()