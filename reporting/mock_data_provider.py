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
                    "vendas_liquidas_variacao": "+0.0%",
                    "vendas_liquidas_variacao_raw": 0.0,
                    "vendas_liquidas_receita_bruta": z,
                    "vendas_liquidas_cancelamentos": z,
                    "vendas_liquidas_impostos_vendas": z,
                    "carga_tributaria": z,
                    "compras": z,
                    "compras_comercializacao": z,
                    "compras_devolucoes": z,
                    "capex": z,
                    "capex_anterior": z,
                    "capex_variacao": "+0.0%",
                    "capex_variacao_raw": 0.0,
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
                    "lucro_real_detalhado": {
                        "resultado_liquido": z,
                        "provisoes_59": z,
                        "base_irpj": z,
                        "irpj_15": z,
                        "numero_meses": 0,
                        "limite_adicional": z,
                        "base_adicional_irpj": z,
                        "adicional_irpj_10": z,
                        "total_irpj": z,
                        "base_csll": z,
                        "csll_9": z,
                        "total_encargos": z,
                    },
                    "lucro_presumido_detalhado": {
                        "vendas_mercadorias_produtos": z,
                        "cancelamentos_devolucoes_vendas": z,
                        "receitas_financeiras": z,
                        "base_irpj": z,
                        "irpj_15": z,
                        "numero_meses": 0,
                        "limite_adicional": z,
                        "base_adicional_irpj": z,
                        "adicional_irpj_10": z,
                        "total_irpj": z,
                        "base_csll": z,
                        "csll_9": z,
                        "total_encargos": z,
                    },
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
