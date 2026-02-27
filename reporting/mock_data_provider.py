from __future__ import annotations
import random
from datetime import datetime
from typing import Dict, Any, List, Optional

from faker import Faker

from .data_provider import DataProvider


class MockDataProvider(DataProvider):
    """
    Implementação mock do DataProvider.
    """

    def __init__(self, locale: str = "pt_BR", seed: int | None = None) -> None:
        self.fake = Faker(locale)
        if seed is not None:
            random.seed(seed)
            Faker.seed(seed)
        # Clientes de exemplo
        self._clientes = [
            {"codigo": 1001, "nome": "Empresa Mock A", "fantasia": "Mock A"},
            {"codigo": 1002, "nome": "Empresa Mock B", "fantasia": "Mock B"},
        ]

    def listar_clientes(self) -> List[Dict[str, Any]]:
        return self._clientes

    def listar_filiais(self, cliente_id: int) -> List[Dict[str, Any]]:
        return [{"codigo": 1, "nome": "Matriz", "fantasia": "Matriz"}]

    def _fmt_brl(self, val: float) -> str:
        return f"R$ {val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    def obter_contexto_dados(
        self, 
        cliente_id: int, 
        anos: List[int], 
        meses: List[int], 
        filiais: Optional[List[int]] = None
    ) -> Dict[str, Any]:
        
        # Dados básicos
        cliente_nome = next((c["nome"] for c in self._clientes if c["codigo"] == cliente_id), "Cliente Mock")
        
        # Formatação do período
        str_meses = "/".join(map(str, meses))
        str_anos = "/".join(map(str, set(anos)))
        periodo_display = f"Meses: {str_meses} | Ano: {str_anos}"

        # KPIs (exemplo simples)
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
        
        estudo_tributario = {
            "lucro_real_valor": self._fmt_brl(lucro * 0.34),
            "lucro_presumido_valor": self._fmt_brl(vendas * 0.05),
            "recomendacao": "Lucro Presumido",
            "economia_anual": "R$ 50.000,00",
            "economia_mensal": "R$ 4.166,00"
        }
        
        distribuicao = {
            "total": self._fmt_brl(lucro),
            "socios": [{"nome": "Sócio 1", "participacao": "100%", "valor": self._fmt_brl(lucro)}]
        }

        # Mock de dados gráficos
        graficos_data = {
            "vendas_evo": [vendas] * 12,
            "custos_evo": [compras] * 12,
            "ativos_evo": [vendas * 2] * 12,
            "pl_evo": [vendas * 1.5] * 12,
            "composicao_ativo": [vendas, vendas],
            "composicao_passivo": [vendas * 0.5, vendas * 0.5],
            "custos_detalhe": [opex, finex, impostos]
        }

        return {
            "dados": {
                "cliente_id": cliente_id,
                "cliente_nome": cliente_nome,
                "periodo": periodo_display,
                "kpis": kpis,
                "indicadores": indicadores,
                "tabela_roe": tabela_roe,
                "estudo_tributario": estudo_tributario,
                "distribuicao_lucros": distribuicao
            },
            "graficos_data": graficos_data
        }

    def obter_balancete(
        self,
        cliente_id: int,
        anos: List[int],
        meses: List[int],
        filiais: Optional[List[int]] = None
    ) -> List[Dict[str, Any]]:
        """
        Retorna um balancete mock para testes.
        """
        contas_mock = [
            {"codigo": "10000000000000", "nome": "ATIVO", "nivel": 1, "tipo": "Sintetica", "natureza": "Devedora"},
            {"codigo": "11000000000000", "nome": "ATIVO CIRCULANTE", "nivel": 2, "tipo": "Sintetica", "natureza": "Devedora"},
            {"codigo": "12000000000000", "nome": "ATIVO NÃO CIRCULANTE", "nivel": 2, "tipo": "Sintetica", "natureza": "Devedora"},
            {"codigo": "20000000000000", "nome": "PASSIVO", "nivel": 1, "tipo": "Sintetica", "natureza": "Credora"},
            {"codigo": "21000000000000", "nome": "PASSIVO CIRCULANTE", "nivel": 2, "tipo": "Sintetica", "natureza": "Credora"},
            {"codigo": "23000000000000", "nome": "PATRIMÔNIO LÍQUIDO", "nivel": 2, "tipo": "Sintetica", "natureza": "Credora"},
            {"codigo": "31000000000000", "nome": "RECEITAS", "nivel": 1, "tipo": "Sintetica", "natureza": "Credora"},
            {"codigo": "50000000000000", "nome": "DESPESAS", "nivel": 1, "tipo": "Sintetica", "natureza": "Devedora"},
        ]
        
        balancete = []
        for conta in contas_mock:
            debito = random.uniform(10000, 500000) if conta["natureza"] == "Devedora" else random.uniform(0, 50000)
            credito = random.uniform(10000, 500000) if conta["natureza"] == "Credora" else random.uniform(0, 50000)
            saldo = debito - credito if conta["natureza"] == "Devedora" else credito - debito
            
            balancete.append({
                "codigo": conta["codigo"],
                "nome": conta["nome"],
                "nivel": conta["nivel"],
                "tipo": conta["tipo"],
                "natureza": conta["natureza"],
                "debito": debito,
                "credito": credito,
                "saldo": saldo,
                "debito_fmt": self._fmt_brl(debito),
                "credito_fmt": self._fmt_brl(credito),
                "saldo_fmt": self._fmt_brl(saldo)
            })
        
        return balancete