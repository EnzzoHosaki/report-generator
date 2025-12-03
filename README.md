# RPS Report Generator (Web + PDF)

Aplicação Flask para gerar relatórios mensais padronizados com o princípio "Write Once, Render Everywhere": a mesma base HTML/CSS é usada para Web e PDF (WeasyPrint com CSS Paged Media).

## Rotas
- `GET /` – Lista de clientes de exemplo e links rápidos
- `GET /report/view/<cliente_id>` – Visualização Web (páginas A4 em tela)
- `GET /report/pdf/<cliente_id>` – Download do PDF (WeasyPrint)
- `GET /report/pdf-batch?ids=1001,1002` – ZIP com múltiplos PDFs

## Execução (WSL Ubuntu)
1. Instalar libs nativas do WeasyPrint (uma vez):
```bash
sudo apt-get update
sudo apt-get install -y libcairo2 libpango-1.0-0 libpangoft2-1.0-0 libgdk-pixbuf-2.0-0 libffi8 libjpeg-turbo8
```
2. Ambiente Python e dependências:
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```
3. Rodar o servidor:
```bash
python main.py
```
Abra `http://localhost:5000` no navegador.

## Estrutura
- `main.py`: app Flask + rotas /report/*
- `reporting/`: serviços de dados e gráficos (Repository Pattern)
- `templates/relatorio_full.html`: template HTML (7 páginas)
- `static/style.css`: estilos únicos para Web e PDF

## Notas
- O PDF usa o mesmo `static/style.css` (single source) via `WeasyPrint.CSS(filename=...)`.
- O `MockDataProvider` prepara terreno para PostgreSQL no futuro.
