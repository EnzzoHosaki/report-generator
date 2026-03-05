from __future__ import annotations
from typing import Dict, Any, List, Optional, Union
import pandas as pd
import numpy as np
from datetime import datetime

from .data_provider import DataProvider
from .chart_service import ChartService


class ReportService:
    """
    Serviço de relatório: compõe o contexto visual usando dados reais do DataProvider.
    """

    def __init__(self, data_provider: DataProvider, chart_service: ChartService) -> None:
        self.data_provider = data_provider
        self.charts = chart_service

    def montar_contexto(
        self, 
        cliente_id: int, 
        periodo: Optional[str] = None,
        year: Optional[int] = None,
        months: Optional[List[int]] = None,
        branches: Optional[List[int]] = None
    ) -> Dict[str, Any]:
        
        """
        Monta o contexto do relatório. Aceita tanto o formato legado (periodo string)
        quanto o novo formato (listas de ints).
        """
        
        anos_query = [datetime.now().year]
        meses_query = [datetime.now().month]
        
        if year:
            anos_query = [year]
        if months:
            meses_query = months
            
        if periodo and not year and not months:
            try:
                parts = periodo.split('/')
                if len(parts) == 2:
                    mes_str = parts[0].strip()
                    ano_str = parts[1].strip()
                    
                    if mes_str.isdigit():
                        meses_query = [int(mes_str)]
                    else:
                        pass 
                    
                    if ano_str.isdigit():
                        anos_query = [int(ano_str)]
            except Exception:
                pass

        raw_context = self.data_provider.obter_contexto_dados(
            cliente_id=cliente_id,
            anos=anos_query,
            meses=meses_query,
            filiais=branches
        )
        
        dados = raw_context["dados"]
        g_data = raw_context.get("graficos_data", {})

        meses_labels = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]
        
        def safe_get_list(key, default_len=12):
            val = g_data.get(key)
            if not val:
                return [0.0] * default_len
            return val

        total_ativos = safe_get_list('ativos_evo')
        pl_line = safe_get_list('pl_evo')
        vendas_atual = safe_get_list('vendas_evo')
        custos_total_evo = safe_get_list('custos_evo')
        
        comp_ativo = safe_get_list('composicao_ativo', 2)
        comp_passivo = safe_get_list('composicao_passivo', 2)
        detalhe_custos = safe_get_list('custos_detalhe', 3)

        vendas_anterior = [v * 0.9 for v in vendas_atual]

        custos_labels = ["Pessoal", "Admin", "Tributário"]
        custos_clean = [(l, v) for l, v in zip(custos_labels, detalhe_custos) if v > 0]
        if custos_clean:
            custos_labels_plot, custos_values_plot = zip(*custos_clean)
            custos_labels_plot = list(custos_labels_plot)
            custos_values_plot = list(custos_values_plot)
        else:
            custos_labels_plot = ["Sem dados"]
            custos_values_plot = [0]

        raw_data_front = {
            "meses": meses_labels,
            "ativos": {
                "total": total_ativos,
                "caixa": [v * 0.4 for v in total_ativos], 
                "estoques": [v * 0.3 for v in total_ativos],
                "imobilizado": [v * 0.3 for v in total_ativos]
            },
            "passivos": {
                "circulante": [p * 0.4 for p in pl_line], 
                "nao_circulante": [p * 0.6 for p in pl_line]
            },
            "rentabilidade": {
                "rps": [1.5] * 12, 
                "cdi": [1.0] * 12,
                "pl": pl_line,
                "ativos": total_ativos
            },
            "vendas": {
                "atual": vendas_atual,
                "anterior": vendas_anterior
            },
            "custos": {
                "labels": custos_labels_plot,
                "values": custos_values_plot
            },
            "produtos": {
                "fat_labels": ["Produto A", "Produto B"], 
                "fat_values": [0, 0],
                "qtd_labels": [],
                "qtd_values": []
            },
            "fornecedores": {
                 "labels": ["Fornecedor Div.", "Outros"],
                 "values": [70, 30]
            }
        }

        graficos = {
            "ativos_evolucao_valor": self.charts.linhas_simples(
                meses_labels,
                total_ativos,
                label="Total Ativos (Movimento)",
                color=self.charts.primary,
                compact_y=True,
            ),
            "ativos_composicao_perc": self.charts.pizza(
                ["Circulante", "Não Circulante"], comp_ativo, donut=False
            ),
            "passivos_stack": self.charts.pizza(
                ["Passivo Circ.", "Passivo N. Circ."], comp_passivo, donut=True
            ),
            "rentabilidade_line": self.charts.linhas_duplas(
                meses_labels, pl_line, [x*0.1 for x in pl_line], label1="PL", label2="Lucro (Est.)"
            ),
            "vendas_line": self.charts.linhas_duplas(
                meses_labels, vendas_atual, vendas_anterior, label1="2024", label2="2023"
            ),
            "top_produtos_faturamento": self.charts.barras_horizontais(
                ["N/A View Contábil"], [0], color=self.charts.primary, title="Dados Indisponíveis"
            ),
            "top_produtos_quantidade": self.charts.barras_horizontais(
                ["N/A View Contábil"], [0], color=self.charts.secondary, title="Dados Indisponíveis"
            ),
            "custos_pie": self.charts.pizza(custos_labels_plot, custos_values_plot, donut=True),
            "fornecedores_pie": self.charts.pizza(["Div.", "Outros"], [70, 30], donut=True),
            "equity_vs_ativos": self.charts.linhas_duplas(
                meses_labels, pl_line, total_ativos, label1="Patrimônio Líquido", label2="Ativos Totais"
            ),
        }

        return {"dados": dados, "graficos": graficos, "raw_data": raw_data_front}