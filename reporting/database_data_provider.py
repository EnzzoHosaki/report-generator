from __future__ import annotations
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import Dict, Any, List, Optional
from datetime import datetime
import random
import re

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
        
        self.meses_map = {
            'janeiro': 1, 'fevereiro': 2, 'março': 3, 'marco': 3,
            'abril': 4, 'maio': 5, 'junho': 6,
            'julho': 7, 'agosto': 8, 'setembro': 9,
            'outubro': 10, 'novembro': 11, 'dezembro': 12,
            'january': 1, 'february': 2, 'march': 3,
            'april': 4, 'may': 5, 'june': 6,
            'july': 7, 'august': 8, 'september': 9,
            'october': 10, 'november': 11, 'december': 12
        }

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
        if val is None:
            val = 0.0
        return f"R$ {val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    def _parse_periodo(self, periodo: str) -> tuple[Optional[int], int]:
        """
        Converte string 'Janeiro/2024', 'January/2024' ou '01/2024' para (mes, ano).
        Retorna (mes_atual, ano_atual) se falhar.
        Se detectar 'Múltiplos meses/YYYY', retorna (None, YYYY).
        """
        if not periodo:
            now = datetime.now()
            return now.month, now.year
            
        try:
            if '/' in periodo:
                parts = periodo.split('/')
                
                if "Múltiplos meses" in parts[0]:
                    if len(parts) >= 2 and parts[1].strip().isdigit():
                         return None, int(parts[1])
                
                if parts[0].isdigit():
                    return int(parts[0]), int(parts[1])
            
            parts = periodo.split('/')
            if len(parts) == 2:
                mes_nome = parts[0].lower().strip()
                ano = int(parts[1])
                mes = self.meses_map.get(mes_nome)
                if mes:
                    return mes, ano
        except Exception as e:
            print(f"Erro ao fazer parse do período '{periodo}': {e}")
        
        print(f"Não foi possível interpretar o período '{periodo}'. Usando data atual.")
        now = datetime.now()
        return now.month, now.year

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

    def _calcular_vendas_liquidas(self, empresa_id: int, mes: Optional[int], ano: int) -> float:
        """
        Calcula as Vendas Líquidas consultando o banco de dados.
        Vendas Líquidas = Receita Bruta (31...) - Deduções (3150...)
        Se mes for None, calcula para todo o ano.
        """
        base_query = """
        SELECT sum(s.saldo_movimento_liquido) as total
        FROM bi.f_balancete_mensal s
        WHERE s.id_empresa = %s
          AND s.ano = %s
        """
        
        params = [empresa_id, ano]
        
        if mes is not None:
            base_query += " AND s.mes = %s"
            params.append(mes)
            
        base_query += """
          AND s.id_conta LIKE '31%%'
          AND s.id_conta NOT LIKE '3180%%'
          AND s.id_conta NOT LIKE '3185%%'
          AND s.id_conta NOT LIKE '3190%%'
        """
        
        try:
            conn = self._get_connection()
            with conn.cursor() as cursor:
                cursor.execute(base_query, tuple(params))
                row = cursor.fetchone()
                if row and len(row) > 0 and row[0] is not None:
                    return float(row[0]) * -1
                return 0.0
        except Exception as e:
            print(f"Erro ao calcular vendas líquidas para empresa {empresa_id} em {mes}/{ano}: {e}")
            return 0.0

    def obter_contexto_dados(self, cliente_id: int, periodo: str) -> Dict[str, Any]:
        """
        Gera/retorna o contexto de DADOS do relatório.
        """
        empresas = self.listar_clientes()
        empresa = next((e for e in empresas if e["codigo"] == cliente_id), None)

        if empresa is None:
            cliente_nome = f"Empresa {cliente_id}"
        else:
            cliente_nome = empresa.get("fantaisa") or empresa.get("nome")

        cliente_info = {
            "cliente_id": cliente_id,
            "cliente_nome": cliente_nome,
            "periodo": periodo or datetime.now().strftime("%B/%Y"),
        }
        
        mes, ano = self._parse_periodo(cliente_info["periodo"])
        print(f"Debug: Consultando DB para Cliente {cliente_id}, Mês {mes}, Ano {ano}")

        vendas = self._calcular_vendas_liquidas(cliente_id, mes, ano)
        
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
            "liquidez_corrente": "1.45" if vendas > 0 else "0.00",
            "margem_liquida": f"{(lucro/vendas*100):.1f}%" if vendas > 0 else "0.0%",
            "endividamento": "45%" if vendas > 0 else "0%",
            "roa": "8%" if vendas > 0 else "0%",
            "ncg": self._fmt_brl(vendas * 0.1),
        }

        tabela_roe = [
            {"periodo": "3 M", "roe": 4.5 if vendas > 0 else 0, "cdi": 2.8, "delta": 1.7 if vendas > 0 else -2.8},
            {"periodo": "6 M", "roe": 8.2 if vendas > 0 else 0, "cdi": 5.5, "delta": 2.7 if vendas > 0 else -5.5},
            {"periodo": "12 M", "roe": 15.1 if vendas > 0 else 0, "cdi": 11.2, "delta": 3.9 if vendas > 0 else -11.2},
        ]
        
        total_distribuido = lucro * 0.6 
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

        base_lucro_real = lucro
        irpj_real = base_lucro_real * 0.15
        if base_lucro_real > 60000:
            irpj_real += (base_lucro_real - 60000) * 0.10
        csll_real = base_lucro_real * 0.09
        imposto_real = irpj_real + csll_real
        
        base_presumida = vendas * 0.08
        irpj_presumido = base_presumida * 0.15
        csll_presumido = base_presumida * 0.09
        imposto_presumido = irpj_presumido + csll_presumido
        
        economia = imposto_real - imposto_presumido
        
        estudo_tributario = {
            "lucro_real_valor": self._fmt_brl(imposto_real),
            "lucro_real_irpj": self._fmt_brl(irpj_real),
            "lucro_real_csll": self._fmt_brl(csll_real),
            "lucro_presumido_valor": self._fmt_brl(imposto_presumido),
            "lucro_presumido_irpj": self._fmt_brl(irpj_presumido),
            "lucro_presumido_csll": self._fmt_brl(csll_presumido),
            "economia_anual": self._fmt_brl(economia * 12),
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