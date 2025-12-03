from __future__ import annotations
import random
from datetime import datetime
from typing import Dict, Any, List

from faker import Faker

from .data_provider import DataProvider


class MockDataProvider(DataProvider):
    """
    Implementação mock do DataProvider usando Faker e random para gerar dados
    sintéticos e reproduzíveis (opcionalmente via seed).
    """

    def __init__(self, locale: str = "pt_BR", seed: int | None = None) -> None:
        self.fake = Faker(locale)
        if seed is not None:
            random.seed(seed)
            Faker.seed(seed)
        # Clientes de exemplo
        self._clientes: List[int] = [1001, 1002, 1003]

    def listar_clientes(self) -> List[int]:
        return list(self._clientes)

    def _fmt_brl(self, val: float) -> str:
        return f"R$ {val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    def obter_contexto_dados(self, cliente_id: int, periodo: str) -> Dict[str, Any]:
        # Dados básicos
        cliente_info = {
            "cliente_id": cliente_id,
            "cliente_nome": self.fake.company(),
            "periodo": periodo or datetime.now().strftime("%B/%Y"),
        }

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
