import io
import os
import warnings
from datetime import datetime, timedelta
from typing import List

import matplotlib.pyplot as plt
from flask import Flask, render_template, make_response, request, redirect, url_for, send_file, jsonify
from weasyprint import HTML, CSS
from dotenv import load_dotenv

from reporting.database_data_provider import DatabaseDataProvider
from reporting.chart_service import ChartService
from reporting.report_service import ReportService

# Carregar variáveis de ambiente do arquivo .env
load_dotenv()

# Configurações Iniciais
warnings.simplefilter(action='ignore', category=FutureWarning)
warnings.simplefilter(action='ignore', category=DeprecationWarning)
plt.switch_backend('Agg')

app = Flask(__name__)

# --- CONFIGURAÇÃO DE CORES RPS ---
COLOR_PRIMARY = '#2d5a3d'
COLOR_SECONDARY = '#7fa88f'
COLOR_TERTIARY = '#1a1a1a'
COLOR_BG = '#fafbfa'

# --- DEPENDÊNCIAS DE DOMÍNIO ---
# Inicializar DatabaseDataProvider com credenciais do banco
data_provider = DatabaseDataProvider(
    host=os.getenv('DB_HOST', '192.168.10.46'),
    port=int(os.getenv('DB_PORT', '5433')),
    database=os.getenv('DB_NAME', 'dw_athenas'),
    user=os.getenv('DB_USER', 'postgres'),
    password=os.getenv('DB_PASSWORD', 'admin'),
)
chart_service = ChartService(primary=COLOR_PRIMARY, secondary=COLOR_SECONDARY, tertiary=COLOR_TERTIARY, bg=COLOR_BG)
report_service = ReportService(data_provider, chart_service)


@app.route('/')
def home():
    """Dashboard moderno com cards de clientes e estatísticas"""
    empresas = data_provider.listar_clientes()
    
    # Paginação
    page = request.args.get('page', 1, type=int)
    items_per_page = 15
    total_items = len(empresas)
    total_pages = (total_items + items_per_page - 1) // items_per_page
    
    # Garantir que page é válida
    if page < 1:
        page = 1
    elif page > total_pages and total_pages > 0:
        page = total_pages
    
    # Calcular índices
    start_idx = (page - 1) * items_per_page
    end_idx = start_idx + items_per_page
    empresas_page = empresas[start_idx:end_idx]
    
    # Gerar lista de IDs da página para o ZIP
    ids_pagina = ','.join(str(e['codigo']) for e in empresas_page)
    
    # Gerar períodos disponíveis (últimos 6 meses) em português
    meses_pt = {
        'January': 'Janeiro', 'February': 'Fevereiro', 'March': 'Março',
        'April': 'Abril', 'May': 'Maio', 'June': 'Junho',
        'July': 'Julho', 'August': 'Agosto', 'September': 'Setembro',
        'October': 'Outubro', 'November': 'Novembro', 'December': 'Dezembro'
    }
    periodos = []
    data_atual = datetime.now()
    for i in range(6):
        data = data_atual - timedelta(days=30*i)
        mes_en = data.strftime('%B')
        ano = data.strftime('%Y')
        mes_pt = meses_pt.get(mes_en, mes_en)
        periodos.append(f"{mes_pt}/{ano}")
    
    return render_template('dashboard.html', 
                         empresas=empresas_page,
                         periodos=periodos,
                         total_empresas=total_items,
                         current_page=page,
                         total_pages=total_pages,
                         items_per_page=items_per_page,
                         ids_pagina=ids_pagina)


@app.route('/report/view/<int:cliente_id>')
def report_view(cliente_id: int):
    """Visualização web do relatório com navegação entre páginas"""
    periodo = request.args.get('periodo') or datetime.now().strftime('%B/%Y')
    contexto = report_service.montar_contexto(cliente_id, periodo)
    return render_template('relatorio_full.html', **contexto)


@app.route('/report/pdf/<int:cliente_id>')
def report_pdf(cliente_id: int):
    """Geração de PDF com WeasyPrint"""
    periodo = request.args.get('periodo') or datetime.now().strftime('%B/%Y')
    contexto = report_service.montar_contexto(cliente_id, periodo)
    html_string = render_template('relatorio_full.html', **contexto)

    css_file = os.path.join(app.static_folder, 'style.css')
    pdf_bytes = HTML(string=html_string, base_url=app.root_path).write_pdf(
        stylesheets=[CSS(filename=css_file)]
    )

    response = make_response(pdf_bytes)
    response.headers['Content-Type'] = 'application/pdf'
    filename = f"RPS_Relatorio_{cliente_id}_{periodo.replace('/', '_')}.pdf"
    response.headers['Content-Disposition'] = f"attachment; filename={filename}"
    return response


@app.route('/report/pdf-batch')
def report_pdf_batch():
    """Geração em lote de PDFs (ZIP)"""
    ids_str = request.args.get('ids', '')
    periodo = request.args.get('periodo') or datetime.now().strftime('%B/%Y')
    
    if not ids_str:
        return jsonify({"error": "Parâmetro 'ids' é obrigatório"}), 400
    
    try:
        ids: List[int] = [int(x) for x in ids_str.split(',') if x.strip()]
    except ValueError:
        return jsonify({"error": "Parâmetro 'ids' inválido"}), 400

    import zipfile
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
        for cid in ids:
            contexto = report_service.montar_contexto(cid, periodo)
            html_string = render_template('relatorio_full.html', **contexto)
            css_file = os.path.join(app.static_folder, 'style.css')
            pdf_bytes = HTML(string=html_string, base_url=app.root_path).write_pdf(
                stylesheets=[CSS(filename=css_file)]
            )
            filename = f"RPS_Relatorio_{cid}_{periodo.replace('/', '_')}.pdf"
            zf.writestr(filename, pdf_bytes)

    buf.seek(0)
    zip_name = f"RPS_Relatorios_{periodo.replace('/', '_')}.zip"
    return send_file(buf, as_attachment=True, download_name=zip_name, mimetype='application/zip')


@app.route('/api/clientes')
def api_clientes():
    """API REST para listar clientes"""
    empresas = data_provider.listar_clientes()
    return jsonify({
        "total": len(empresas),
        "clientes": [
            {
                "codigo": empresa['codigo'],
                "nome": empresa.get('nome', ''),
                "fantasia": empresa.get('fantaisa', '')
            }
            for empresa in empresas
        ]
    })


@app.route('/api/preview/<int:cliente_id>')
def api_preview(cliente_id: int):
    """API para prévia rápida dos KPIs de um cliente"""
    periodo = request.args.get('periodo') or datetime.now().strftime('%B/%Y')
    contexto = report_service.montar_contexto(cliente_id, periodo)
    
    return jsonify({
        "cliente_id": cliente_id,
        "periodo": periodo,
        "kpis": contexto['dados']['kpis'],
        "indicadores": contexto['dados']['indicadores']
    })


@app.route('/img/<path:filename>')
def serve_img(filename):
    """Servir imagens da pasta img"""
    img_folder = os.path.join(os.path.dirname(__file__), 'img')
    return send_file(os.path.join(img_folder, filename), mimetype='image/png')


# Rotas de compatibilidade com versão antiga
@app.route('/relatorio/<int:cliente_id>')
def visualizar_relatorio(cliente_id: int):
    return redirect(url_for('report_view', cliente_id=cliente_id))


@app.route('/pdf/<int:cliente_id>')
def baixar_pdf(cliente_id: int):
    return redirect(url_for('report_pdf', cliente_id=cliente_id))


# Error handlers
@app.errorhandler(404)
def not_found(error):
    return render_template('error.html', 
                         error_code=404,
                         error_message="Página não encontrada"), 404


@app.errorhandler(500)
def internal_error(error):
    return render_template('error.html',
                         error_code=500,
                         error_message="Erro interno do servidor"), 500


if __name__ == '__main__':
    debug = os.environ.get('DEBUG', '1') == '1'
    port = int(os.environ.get('PORT', '5000'))
    print(f"""
    ╔═══════════════════════════════════════════════════════╗
    ║   RPS REPORT SYSTEM - INICIANDO                       ║
    ╠═══════════════════════════════════════════════════════╣
    ║  Servidor: http://localhost:{port}                      ║
    ║  Modo: {'DEBUG' if debug else 'PRODUCTION'}                                          ║                    
    ║  WebPDF: WeasyPrint (A4 Landscape)                    ║
    ╚═══════════════════════════════════════════════════════╝
    """)
    app.run(debug=debug, port=port, host='0.0.0.0')