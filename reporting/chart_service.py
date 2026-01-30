from __future__ import annotations
import io
import base64
from typing import List, Sequence

import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd


class ChartService:
    """
    Serviço de gráficos independente de Flask/Templates.
    Retorna imagens em base64 para incorporação no HTML.
    """

    def __init__(self, primary: str, secondary: str, tertiary: str, bg: str = "#fdfdfd") -> None:
        self.primary = primary
        self.secondary = secondary
        self.tertiary = tertiary
        self.bg = bg
        sns.set_theme(
            style="whitegrid",
            rc={
                "axes.edgecolor": "#e5e7eb",
                "grid.color": "#e5e7eb",
                "text.color": self.tertiary,
                "axes.labelcolor": self.tertiary,
                "xtick.color": self.tertiary,
                "ytick.color": self.tertiary,
                "figure.facecolor": self.bg,
                "axes.facecolor": self.bg,
            },
        )

    def _fig_to_b64(self, fig) -> str:
        buf = io.BytesIO()
        fig.savefig(buf, format="png", bbox_inches="tight", dpi=100, transparent=True)
        buf.seek(0)
        img = base64.b64encode(buf.read()).decode("utf-8")
        plt.close(fig)
        return img

    def barras_empilhadas(self, df: pd.DataFrame, cores: List[str], width: float = 0.6, legend_cols: int = 3) -> str:
        fig, ax = plt.subplots(figsize=(7, 3.5))
        
        # Validação de dados vazios
        if df.empty or df.sum().sum() == 0:
            self._render_placeholdear(ax)
            return self._fig_to_b64(fig)

        df.plot(kind="bar", stacked=True, ax=ax, color=cores, width=width)
        ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.25), ncol=legend_cols, frameon=False)
        sns.despine(left=True)
        return self._fig_to_b64(fig)
        
    def barras_horizontais(self, labels: List[str], values: List[float], color: str, title: str = "") -> str:
        """Gráfico de barras horizontais simples para rankings (Top 5)"""
        fig, ax = plt.subplots(figsize=(7, 3.5))
        
        # Sanitização e Validação
        clean_values = [v if pd.notna(v) else 0.0 for v in values]
        if sum(clean_values) == 0:
            self._render_placeholder(ax, title)
            return self._fig_to_b64(fig)

        sns.barplot(x=clean_values, y=labels, color=color, ax=ax, orient='h')
        if title:
            ax.set_title(title, fontsize=10, pad=10)
        sns.despine(left=True, bottom=True)
        return self._fig_to_b64(fig)

    def area_empilhada(self, df: pd.DataFrame, cores: List[str], alpha: float = 0.8, legend_cols: int = 2) -> str:
        fig, ax = plt.subplots(figsize=(7, 3.5))
        
        if df.empty or df.sum().sum() == 0:
            self._render_placeholder(ax)
            return self._fig_to_b64(fig)
            
        for i, col in enumerate(df.columns):
            ax.fill_between(df.index, df[col], step=None, alpha=alpha, color=cores[i], label=col)
        ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.15), ncol=legend_cols, frameon=False)
        sns.despine(left=True)
        return self._fig_to_b64(fig)

    def linhas_duplas(self, x: Sequence, y1: Sequence[float], y2: Sequence[float], label1: str, label2: str) -> str:
        fig, ax = plt.subplots(figsize=(7, 3.5))
        
        # Sanitização simples (linhas aceitam 0, mas evitamos NaNs que quebram plots)
        y1 = [v if pd.notna(v) else 0.0 for v in y1]
        y2 = [v if pd.notna(v) else 0.0 for v in y2]

        sns.lineplot(x=x, y=y1, marker="o", label=label1, ax=ax, color=self.tertiary)
        sns.lineplot(x=x, y=y2, marker="o", linestyle="--", label=label2, ax=ax, color=self.secondary)
        ax.legend(frameon=False)
        sns.despine()
        return self._fig_to_b64(fig)
        
    def linhas_simples(self, x: Sequence, y: Sequence[float], label: str, color: str = None) -> str:
        """Linha simples para evolução"""
        fig, ax = plt.subplots(figsize=(7, 3.5))
        
        y = [v if pd.notna(v) else 0.0 for v in y]
        
        sns.lineplot(x=x, y=y, marker="o", label=label, ax=ax, color=color or self.primary)
        ax.legend(frameon=False)
        sns.despine()
        return self._fig_to_b64(fig)

    def pizza(self, labels: List[str], values: List[float], donut: bool = False) -> str:
        fig, ax = plt.subplots(figsize=(4, 4))
        
        # Sanitização Crítica: Converter NaNs para 0 e verificar soma
        clean_values = [v if pd.notna(v) and v >= 0 else 0.0 for v in values]
        total = sum(clean_values)
        
        # Se total for 0, desenha placeholder para evitar erro de divisão por zero (NaN)
        if total <= 0:
            ax.text(0, 0, "Sem dados", ha='center', va='center', color=self.tertiary, fontsize=9)
            ax.axis('off')
            # Círculo cinza claro para indicar espaço do gráfico
            circle = plt.Circle((0, 0), 1, color='#f5f5f5')
            ax.add_artist(circle)
            if donut:
                center = plt.Circle((0, 0), 0.70, fc="white")
                ax.add_artist(center)
            
            # Ajustar limites para garantir que o círculo apareça
            ax.set_xlim(-1.1, 1.1)
            ax.set_ylim(-1.1, 1.1)
            ax.set_aspect('equal')
            
            return self._fig_to_b64(fig)

        colors = [self.primary, self.secondary, "#d8e2d8", self.tertiary]
        wedges, texts, autotexts = ax.pie(
            clean_values,
            labels=labels,
            autopct="%1.0f%%",
            startangle=90,
            colors=colors[: len(clean_values)],
            textprops={"fontsize": 9, "color": self.tertiary},
        )
        if donut:
            center = plt.Circle((0, 0), 0.70, fc="white")
            fig.gca().add_artist(center)
            
        return self._fig_to_b64(fig)

    def _render_placeholder(self, ax, title: str = ""):
        """Helper interno para renderizar estado vazio"""
        ax.text(0.5, 0.5, "Sem dados disponíveis", ha='center', va='center', color=self.tertiary)
        ax.axis('off')
        if title:
            ax.set_title(title, fontsize=10, pad=10)