from __future__ import annotations
from typing import Dict, Any, List, Optional

from .data_provider import DataProvider


class MockDataProvider(DataProvider):
    """
    Implementação mock do DataProvider.
    Valores zerados para apresentação.
    """

    def __init__(self) -> None:
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

        cliente_nome = next(
            (c["nome"] for c in self._clientes if c["codigo"] == cliente_id),
            "Cliente Mock",
        )

        str_meses = "/".join(map(str, meses))
        str_anos = "/".join(map(str, set(anos)))
        periodo_display = f"Meses: {str_meses} | Ano: {str_anos}"

        z = self._fmt_brl(0)

        return {
            "dados": {
                "cliente_id": cliente_id,
                "cliente_nome": cliente_nome,
                "periodo": periodo_display,
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
