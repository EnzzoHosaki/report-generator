# Implementação de Gráficos Interativos (tipo Power BI)

Para tornar os gráficos interativos na visualização web (mantendo os estáticos no PDF), você pode usar **Plotly**.

## Passos para Implementação

### 1. Instalar Plotly
```bash
pip install plotly kaleido
```

### 2. Criar um novo ChartService interativo

Crie `reporting/plotly_chart_service.py`:

```python
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from typing import List

class PlotlyChartService:
    """Serviço de gráficos interativos com Plotly"""
    
    def __init__(self, primary: str, secondary: str, tertiary: str):
        self.primary = primary
        self.secondary = secondary
        self.tertiary = tertiary
        self.config = {
            'displayModeBar': True,
            'displaylogo': False,
            'modeBarButtonsToRemove': ['pan2d', 'lasso2d', 'select2d']
        }
    
    def barras_empilhadas(self, df: pd.DataFrame, cores: List[str]) -> str:
        """Retorna HTML do gráfico interativo"""
        fig = go.Figure()
        
        for i, col in enumerate(df.columns):
            fig.add_trace(go.Bar(
                name=col,
                x=df.index,
                y=df[col],
                marker_color=cores[i]
            ))
        
        fig.update_layout(
            barmode='stack',
            template='plotly_white',
            height=350,
            margin=dict(l=40, r=40, t=40, b=40),
            legend=dict(orientation="h", yanchor="top", y=-0.2, xanchor="center", x=0.5),
            hovermode='x unified'
        )
        
        return fig.to_html(config=self.config, div_id=None, include_plotlyjs='cdn')
    
    def area_empilhada(self, df: pd.DataFrame, cores: List[str]) -> str:
        """Gráfico de área empilhada interativo"""
        fig = go.Figure()
        
        for i, col in enumerate(df.columns):
            fig.add_trace(go.Scatter(
                name=col,
                x=df.index,
                y=df[col],
                mode='lines',
                stackgroup='one',
                fillcolor=cores[i],
                line=dict(width=0.5, color=cores[i]),
                hovertemplate='%{y}<extra></extra>'
            ))
        
        fig.update_layout(
            template='plotly_white',
            height=350,
            margin=dict(l=40, r=40, t=40, b=40),
            legend=dict(orientation="h", yanchor="top", y=-0.2, xanchor="center", x=0.5),
            hovermode='x unified'
        )
        
        return fig.to_html(config=self.config, div_id=None, include_plotlyjs='cdn')
    
    def linhas_duplas(self, x: List, y1: List[float], y2: List[float], label1: str, label2: str) -> str:
        """Gráfico de linhas duplas interativo"""
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=x, y=y1,
            mode='lines+markers',
            name=label1,
            line=dict(color=self.tertiary, width=3),
            marker=dict(size=8)
        ))
        
        fig.add_trace(go.Scatter(
            x=x, y=y2,
            mode='lines+markers',
            name=label2,
            line=dict(color=self.secondary, width=3, dash='dash'),
            marker=dict(size=8)
        ))
        
        fig.update_layout(
            template='plotly_white',
            height=350,
            margin=dict(l=40, r=40, t=40, b=40),
            legend=dict(orientation="h", yanchor="top", y=-0.2, xanchor="center", x=0.5),
            hovermode='x unified'
        )
        
        return fig.to_html(config=self.config, div_id=None, include_plotlyjs='cdn')
    
    def pizza(self, labels: List[str], values: List[float], donut: bool = False) -> str:
        """Gráfico de pizza interativo"""
        colors = [self.primary, self.secondary, "#d8e2d8", self.tertiary]
        
        fig = go.Figure(data=[go.Pie(
            labels=labels,
            values=values,
            hole=0.7 if donut else 0,
            marker=dict(colors=colors[:len(values)]),
            textposition='inside',
            textinfo='percent+label',
            hovertemplate='<b>%{label}</b><br>%{value}<br>%{percent}<extra></extra>'
        )])
        
        fig.update_layout(
            template='plotly_white',
            height=350,
            margin=dict(l=20, r=20, t=20, b=20),
            showlegend=False
        )
        
        return fig.to_html(config=self.config, div_id=None, include_plotlyjs='cdn')
```

### 3. Modificar main.py para usar gráficos interativos na web

```python
from reporting.plotly_chart_service import PlotlyChartService

# Adicionar serviço Plotly
plotly_charts = PlotlyChartService(
    primary=COLOR_PRIMARY,
    secondary=COLOR_SECONDARY,
    tertiary=COLOR_TERTIARY
)

@app.route('/report/view/<int:cliente_id>')
def report_view(cliente_id: int):
    periodo = request.args.get('periodo') or datetime.now().strftime('%B/%Y')
    
    # Usar Plotly para versão web
    from reporting.report_service import ReportService
    plotly_report = ReportService(data_provider, plotly_charts)
    contexto = plotly_report.montar_contexto(cliente_id, periodo)
    
    return render_template('relatorio_full.html', **contexto)
```

### 4. Modificar o template para renderizar HTML dos gráficos

Em `relatorio_full.html`, altere:

```html
<!-- ANTES (imagem estática) -->
<div class="chart-container">
  <img class="chart-img" src="data:image/png;base64,{{ graficos.ativos_stack }}" alt="...">
</div>

<!-- DEPOIS (gráfico interativo) -->
<div class="chart-container plotly-chart">
  {{ graficos.ativos_stack|safe }}
</div>
```

### 5. Adicionar CSS para os gráficos Plotly

Em `static/style.css`:

```css
.plotly-chart {
  width: 100%;
  height: 100%;
}

.plotly-chart .plotly {
  width: 100% !important;
  height: 100% !important;
}

/* Esconder na versão PDF */
@media print {
  .plotly-chart .modebar {
    display: none !important;
  }
}
```

## Benefícios dos Gráficos Interativos

✅ **Hover** - Exibe valores ao passar o mouse
✅ **Zoom** - Amplia áreas específicas
✅ **Pan** - Navegação pelo gráfico
✅ **Download** - Exporta como PNG
✅ **Seleção** - Filtra dados visualmente
✅ **Responsivo** - Adapta-se ao tamanho da tela

## Manter PDF com Matplotlib

Para manter os PDFs com gráficos estáticos (mais leves e confiáveis), mantenha dois serviços:
- **Matplotlib** para PDF (rápido e leve)
- **Plotly** para visualização web (interativo)

```python
# PDF - Matplotlib
report_service_pdf = ReportService(data_provider, chart_service)

# Web - Plotly
report_service_web = ReportService(data_provider, plotly_charts)
```

## Configurações Avançadas

### Temas personalizados
```python
fig.update_layout(
    plot_bgcolor='rgba(0,0,0,0)',
    paper_bgcolor='rgba(0,0,0,0)',
    font=dict(family='Inter, sans-serif', size=10, color='#2b2d2f')
)
```

### Botões customizados
```python
config = {
    'displayModeBar': True,
    'modeBarButtonsToAdd': ['drawopenpath', 'eraseshape'],
    'toImageButtonOptions': {
        'format': 'png',
        'filename': 'grafico_rps',
        'height': 600,
        'width': 800,
        'scale': 2
    }
}
```

## Alternativa: Chart.js

Se preferir uma solução mais leve que Plotly, considere **Chart.js**:

```html
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<canvas id="myChart"></canvas>
<script>
  const ctx = document.getElementById('myChart');
  new Chart(ctx, {
    type: 'bar',
    data: {
      labels: {{ labels|tojson }},
      datasets: [...]
    }
  });
</script>
```

Chart.js é mais leve mas menos poderoso que Plotly.
