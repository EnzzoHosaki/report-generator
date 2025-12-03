import io
import os
import warnings
from datetime import datetime
from typing import List

import matplotlib.pyplot as plt
from flask import Flask, render_template, make_response, request, redirect, url_for, send_file
from weasyprint import HTML, CSS

from reporting.mock_data_provider import MockDataProvider
from reporting.chart_service import ChartService
from reporting.report_service import ReportService

# Configurações Iniciais
a = warnings.simplefilter
try:
    a(action='ignore', category=FutureWarning)
    a(action='ignore', category=DeprecationWarning)
except Exception:
    pass
plt.switch_backend('Agg')

app = Flask(__name__)

# --- CONFIGURAÇÃO DE CORES RPS ---
COLOR_PRIMARY = '#829871'
COLOR_SECONDARY = '#a7baa6'
COLOR_TERTIARY = '#262123'
COLOR_BG = '#fdfdfd'

# --- DEPENDÊNCIAS DE DOMÍNIO ---
data_provider = MockDataProvider(locale='pt_BR')
chart_service = ChartService(primary=COLOR_PRIMARY, secondary=COLOR_SECONDARY, tertiary=COLOR_TERTIARY, bg=COLOR_BG)
report_service = ReportService(data_provider, chart_service)


@app.route('/')
def home():
    clientes = data_provider.listar_clientes()
    links = ''.join([
        f"<li><a href='/report/view/{cid}'>Cliente {cid} (Visualizar)</a> | "
        f"<a href='/report/pdf/{cid}'>PDF</a></li>" for cid in clientes
    ])
    return f"""
    <h1 style='font-family: sans-serif; color: {COLOR_PRIMARY};'>Sistema de Relatórios RPS</h1>
    <ul>{links}</ul>
    <p><a href='/report/pdf-batch?ids={','.join(map(str, clientes))}'>Baixar ZIP em lote</a></p>
    """


@app.route('/report/view/<int:cliente_id>')
def report_view(cliente_id: int):
    periodo = request.args.get('periodo') or datetime.now().strftime('%B/%Y')
    contexto = report_service.montar_contexto(cliente_id, periodo)
    # Usa o template completo (7 páginas)
    return render_template('relatorio_full.html', **contexto)


@app.route('/report/pdf/<int:cliente_id>')
def report_pdf(cliente_id: int):
    periodo = request.args.get('periodo') or datetime.now().strftime('%B/%Y')
    contexto = report_service.montar_contexto(cliente_id, periodo)
    html_string = render_template('relatorio_full.html', **contexto)

    css_file = os.path.join(app.static_folder, 'style.css')
    pdf_bytes = HTML(string=html_string, base_url=app.root_path).write_pdf(
        stylesheets=[CSS(filename=css_file)]
    )

    response = make_response(pdf_bytes)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f"attachment; filename=RPS_Relatorio_{cliente_id}.pdf"
    return response


@app.route('/report/pdf-batch')
def report_pdf_batch():
    ids_str = request.args.get('ids', '')
    if not ids_str:
        return "Parâmetro 'ids' é obrigatório. Ex: /report/pdf-batch?ids=1001,1002", 400
    try:
        ids: List[int] = [int(x) for x in ids_str.split(',') if x.strip()]
    except ValueError:
        return "Parâmetro 'ids' inválido.", 400

    import zipfile
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
        for cid in ids:
            periodo = datetime.now().strftime('%B/%Y')
            contexto = report_service.montar_contexto(cid, periodo)
            html_string = render_template('relatorio_full.html', **contexto)
            css_file = os.path.join(app.static_folder, 'style.css')
            pdf_bytes = HTML(string=html_string, base_url=app.root_path).write_pdf(
                stylesheets=[CSS(filename=css_file)]
            )
            zf.writestr(f"RPS_Relatorio_{cid}.pdf", pdf_bytes)

    buf.seek(0)
    return send_file(buf, as_attachment=True, download_name='relatorios.zip', mimetype='application/zip')


# Compatibilidade com rotas antigas do app.py original
@app.route('/relatorio/<int:cliente_id>')
def visualizar_relatorio(cliente_id: int):
    return redirect(url_for('report_view', cliente_id=cliente_id))


@app.route('/pdf/<int:cliente_id>')
def baixar_pdf(cliente_id: int):
    return redirect(url_for('report_pdf', cliente_id=cliente_id))


if __name__ == '__main__':
    debug = os.environ.get('DEBUG', '1') == '1'
    port = int(os.environ.get('PORT', '5000'))
    app.run(debug=debug, port=port)
