from __future__ import annotations
from typing import Dict, Any
import pandas as pd

from .data_provider import DataProvider
from .chart_service import ChartService


class ReportService:
    """
    Serviço de relatório: compõe o contexto (dados + gráficos) esperado pelo template.
    """

    def __init__(self, data_provider: DataProvider, chart_service: ChartService) -> None:
        self.data_provider = data_provider
        self.charts = chart_service

    def montar_contexto(self, cliente_id: int, periodo: str) -> Dict[str, Any]:
        base = self.data_provider.obter_contexto_dados(cliente_id, periodo)
        dados = base["dados"]

        # Exemplos simples de dados tabulares/seriados para gráficos
        df_ativos = pd.DataFrame({
            "Mes": ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun"],
            "Caixa": [50, 55, 60, 58, 62, 65],
            "Estoques": [30, 32, 35, 33, 34, 36],
            "Imobilizado": [10, 10, 12, 12, 13, 13],
        }).set_index("Mes")

        df_passivos = pd.DataFrame({
            "Mes": ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun"],
            "Circulante": [40, 42, 45, 44, 46, 48],
            "Nao_Circulante": [60, 58, 55, 56, 54, 52],
        }).set_index("Mes")

        meses = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun"]
        rent_rps = [1, 1.5, 1.2, 1.8, 2, 1.9]
        rent_cdi = [0.8, 0.85, 0.9, 0.9, 0.95, 0.95]

        vendas_2024 = [100, 110, 105, 120, 125, 130]
        vendas_2023 = [90, 95, 92, 100, 105, 110]

        # Gráficos
        graficos = {
            "ativos_stack": self.charts.barras_empilhadas(
                df_ativos, cores=[self.charts.primary, self.charts.secondary, "#d1d9d0"], legend_cols=3
            ),
            "passivos_stack": self.charts.area_empilhada(
                df_passivos, cores=[self.charts.secondary, self.charts.tertiary], legend_cols=2
            ),
            "rentabilidade_line": self.charts.linhas_duplas(
                meses, rent_rps, rent_cdi, label1="RPS", label2="CDI"
            ),
            "vendas_line": self.charts.linhas_duplas(
                meses, vendas_2024, vendas_2023, label1="2024", label2="2023"
            ),
            "vendas_pie": self.charts.pizza(["Prod A", "Prod B", "Prod C", "Outros"], [40, 30, 20, 10], donut=False),
            "custos_pie": self.charts.pizza(["Pessoal", "Tributos", "Serviços", "Aluguel"], [50, 20, 15, 15], donut=True),
            "fornecedores_pie": self.charts.pizza(["Forn A", "Forn B", "Outros"], [60, 30, 10], donut=True),
            "equity_vs_ativos": self.charts.linhas_duplas(
                meses, [60, 62, 64, 66, 68, 70], [100, 105, 108, 112, 115, 118], label1="Patrimônio Líquido", label2="Ativos Totais"
            ),
        }

        return {"dados": dados, "graficos": graficos}
