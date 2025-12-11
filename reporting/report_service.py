from __future__ import annotations
from typing import Dict, Any
import pandas as pd
import numpy as np

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

        # --- DADOS PARA GRÁFICOS ---
        meses = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun"]

        # 1. Ativos
        # Evolução em R$ (Soma dos componentes)
        caixa = [50, 55, 60, 58, 62, 65]
        estoques = [30, 32, 35, 33, 34, 36]
        imob = [10, 10, 12, 12, 13, 13]
        total_ativos = [c + e + i for c, e, i in zip(caixa, estoques, imob)]
        
        # Composição em % (Normalizando para 100%)
        # Criamos DataFrame para facilitar
        df_ativos_raw = pd.DataFrame({
            "Caixa": caixa,
            "Estoques": estoques,
            "Imobilizado": imob
        }, index=meses)
        
        # Divide cada linha pela soma da linha para ter %
        df_ativos_perc = df_ativos_raw.div(df_ativos_raw.sum(axis=1), axis=0) * 100

        # 2. Passivos
        df_passivos = pd.DataFrame({
            "Mes": meses,
            "Não Circulante": [60, 58, 55, 56, 54, 52],
            "Circulante": [40, 42, 45, 44, 46, 48],
        }).set_index("Mes")

        # 3. Rentabilidade
        rent_rps = [1, 1.5, 1.2, 1.8, 2, 1.9]
        rent_cdi = [0.8, 0.85, 0.9, 0.9, 0.95, 0.95]

        # 4. Vendas (YoY)
        vendas_2024 = [100, 110, 105, 120, 125, 130]
        vendas_2023 = [90, 95, 92, 100, 105, 110]
        
        # 5. Top Produtos
        # Simulando dados brutos para processar lógica de Top 5
        produtos_raw = {
            "Prod A": {"fat": 50000, "qtd": 1000},
            "Prod B": {"fat": 35000, "qtd": 1500}, # Menos fat, mais qtd
            "Prod C": {"fat": 20000, "qtd": 800},
            "Prod D": {"fat": 15000, "qtd": 600},
            "Prod E": {"fat": 10000, "qtd": 400},
            "Prod F": {"fat": 5000,  "qtd": 200},
            "Prod G": {"fat": 2000,  "qtd": 100},
        }
        
        # Processar Top 5 Faturamento
        sorted_fat = sorted(produtos_raw.items(), key=lambda x: x[1]['fat'], reverse=True)
        top5_fat_labels = [k for k, v in sorted_fat[:5]]
        top5_fat_values = [v['fat'] for k, v in sorted_fat[:5]]
        
        if len(sorted_fat) > 5:
            outros_fat = sum(v['fat'] for k, v in sorted_fat[5:])
            top5_fat_labels.append("Outros")
            top5_fat_values.append(outros_fat)
            
        # Processar Top 5 Quantidade
        sorted_qtd = sorted(produtos_raw.items(), key=lambda x: x[1]['qtd'], reverse=True)
        top5_qtd_labels = [k for k, v in sorted_qtd[:5]]
        top5_qtd_values = [v['qtd'] for k, v in sorted_qtd[:5]]
        
        if len(sorted_qtd) > 5:
            outros_qtd = sum(v['qtd'] for k, v in sorted_qtd[5:])
            top5_qtd_labels.append("Outros")
            top5_qtd_values.append(outros_qtd)


        # --- GERAÇÃO DE IMAGENS ---
        graficos = {
            # Nova Análise de Ativos
            "ativos_evolucao_valor": self.charts.linhas_simples(
                meses, total_ativos, label="Total Ativos (R$)", color=self.charts.primary
            ),
            "ativos_composicao_perc": self.charts.barras_empilhadas(
                df_ativos_perc, cores=[self.charts.primary, self.charts.secondary, "#d1d9d0"], legend_cols=3
            ),
            
            "passivos_stack": self.charts.area_empilhada(
                df_passivos, cores=[self.charts.tertiary, self.charts.secondary], legend_cols=2
            ),
            "rentabilidade_line": self.charts.linhas_duplas(
                meses, rent_rps, rent_cdi, label1="RPS", label2="CDI"
            ),
            "vendas_line": self.charts.linhas_duplas(
                meses, vendas_2024, vendas_2023, label1="2024", label2="2023"
            ),
            
            # Novos Gráficos de Vendas
            "top_produtos_faturamento": self.charts.barras_horizontais(
                top5_fat_labels, top5_fat_values, color=self.charts.primary, title="Top 5 Faturamento (R$)"
            ),
            "top_produtos_quantidade": self.charts.barras_horizontais(
                top5_qtd_labels, top5_qtd_values, color=self.charts.secondary, title="Top 5 Quantidade (Unid.)"
            ),
            
            "custos_pie": self.charts.pizza(["Pessoal", "Tributos", "Serviços", "Aluguel"], [50, 20, 15, 15], donut=True),
            "fornecedores_pie": self.charts.pizza(["Forn A", "Forn B", "Outros"], [60, 30, 10], donut=True),
            "equity_vs_ativos": self.charts.linhas_duplas(
                meses, [60, 62, 64, 66, 68, 70], [100, 105, 108, 112, 115, 118], label1="Patrimônio Líquido", label2="Ativos Totais"
            ),
        }

        return {"dados": dados, "graficos": graficos}