from __future__ import annotations
import firebirdsql
import time
from typing import Dict, Any, List, Optional
from datetime import datetime
from decimal import Decimal

from .data_provider import DataProvider


class DatabaseDataProvider(DataProvider):
    """
    Provider para Firebird/Athenas usando consulta direta em TABSALDOCONTABIL.
    
    Consulta as tabelas:
    - TABSALDOCONTABIL S: Saldos contábeis mensais (débito/crédito)
    - TABPLANOCONTAS P: Plano de contas (nome, tipo, natureza)
    - TABEMPRESAS E: Empresas
    - TABFILIAL F: Filiais
    
    Filtros aplicados:
    - S.INICIAL NOT IN (2, 4, 5): Exclui saldos iniciais específicos
    - Saldo calculado considerando natureza da conta:
        Devedora: DEBITO - CREDITO
        Credora: CREDITO - DEBITO
    
    Mapeamento de Contas:
    - 31*: Receita Bruta Operacional
    - 315*: Deduções de Vendas
    - 32*: Receitas Não Operacionais
    - 49*: Custos (CMV)
    - 53*: Despesas Administrativas
    - 57*: Despesas Financeiras
    - 58*: Resultados Não Operacionais
    - 59*: Provisões/Tributos sobre Lucro
    - 11*: Ativo Circulante
    - 12*: Ativo Não Circulante
    - 21*: Passivo Circulante
    - 22*: Passivo Não Circulante
    - 23*: Patrimônio Líquido
    """

    # Mapeamento completo de contas da VIEW (códigos de 14 dígitos)
    CONTAS = {
        # === ATIVO ===
        'ATIVO': '10000000000000',
        'ATIVO_CIRCULANTE': '11000000000000',
        'DISPONIVEL': '11010000000000',
        'CAIXA_GERAL': '11010100000000',
        'DEPOSITOS_BANCARIOS': '11010200000000',
        'APLICACOES_FINANCEIRAS': '11010300000000',
        'CREDITOS_VENDAS': '11020000000000',
        'CLIENTES': '11020200000000',
        'CREDITOS_DIVERSOS': '11030000000000',
        'ESTOQUES': '11040000000000',
        'DESPESAS_ANTECIPADAS': '11050000000000',
        'ATIVO_NAO_CIRCULANTE': '12000000000000',
        'REALIZAVEL_LONGO_PRAZO': '12010000000000',
        'IMOBILIZADO': '12030000000000',
        'INTANGIVEL': '12040000000000',
        
        # === PASSIVO ===
        'PASSIVO': '20000000000000',
        'PASSIVO_CIRCULANTE': '21000000000000',
        'FORNECEDORES': '21010000000000',
        'EMPRESTIMOS_FINANCIAMENTOS_CP': '21020000000000',
        'OBRIGACOES_TRABALHISTAS': '21030000000000',
        'OBRIGACOES_FISCAIS': '21040000000000',
        'OBRIGACOES_DIVERSAS': '21050000000000',
        'PROVISOES_DIVERSAS': '21060000000000',
        'PASSIVO_NAO_CIRCULANTE': '22000000000000',
        'EXIGIVEL_LONGO_PRAZO': '22010000000000',
        'PATRIMONIO_LIQUIDO': '23000000000000',
        'CAPITAL_SOCIAL': '23010000000000',
        'RESERVAS': '23020000000000',
        'LUCROS_PREJUIZOS_ACUMULADOS': '23040000000000',
        
        # === RECEITAS ===
        'RECEITAS': '30000000000000',
        'RECEITA_BRUTA_OPERACIONAL': '31000000000000',
        'VENDAS_PRODUTOS': '31010000000000',
        'REVENDA_MERCADORIAS': '31100000000000',
        'VENDAS_SERVICOS': '31150000000000',
        'SERVICO_TRANSPORTES': '31180000000000',
        'RECEITAS_OBRAS': '31200000000000',
        'RECEITAS_IMOBILIARIAS': '31220000000000',
        'RECEITAS_LOCACOES': '31250000000000',
        'CANCELAMENTOS_DEVOLUCOES': '31500000000000',
        'RECUPERACAO_ICMS_SUBSTITUTO': '31600000000000',
        'IMPOSTOS_SOBRE_VENDAS': '31800000000000',
        'RECEITAS_FINANCEIRAS': '31850000000000',
        'OUTRAS_RECEITAS_OPERACIONAIS': '31900000000000',
        'RECEITAS_NAO_OPERACIONAIS': '32000000000000',
        
        # === ENTRADAS E CUSTOS ===
        'ENTRADAS_CUSTOS': '40000000000000',
        'ENTRADAS_COMERCIAIS': '41000000000000',
        'COMPRAS_COMERCIALIZACAO': '41010000000000',
        'ENTRADAS_INDUSTRIAIS': '42000000000000',
        'CUSTOS_PRODUCAO': '44000000000000',
        'CUSTOS_SERVICOS_PRESTADOS': '46000000000000',
        'CUSTOS_VENDAS': '49000000000000',
        'CUSTO_INDUSTRIAL': '49010000000000',
        'CUSTO_COMERCIAL': '49050000000000',
        
        # === DESPESAS ===
        'DESPESAS': '50000000000000',
        'DESPESAS_ADMINISTRATIVAS': '53000000000000',
        'DESPESAS_PESSOAL': '53050000000000',
        'SERVICOS_TERCEIROS': '53100000000000',
        'ENCARGOS_SOCIAIS': '53120000000000',
        'TAXAS_CONTRIBUICOES': '53200000000000',
        'DESPESAS_GERAIS': '53350000000000',
        'DESPESAS_TRIBUTARIAS': '56000000000000',
        'DESPESAS_FINANCEIRAS': '57000000000000',
        'RESULTADOS_NAO_OPERACIONAIS': '58000000000000',
        'PROVISOES_PARTICIPACOES': '59000000000000',
        
        # === RESULTADO ===
        'RESULTADO_EXERCICIO': '60000000000000',
        
        # === ALIASES para compatibilidade ===
        'RECEITA_BRUTA': '31',  # Prefixo para pegar toda receita
        'DEDUCOES_VENDAS': '315',  # Cancelamentos + Impostos sobre vendas
        'CUSTOS_CMV': '49',  # Custos das vendas
        'DESPESAS_VENDAS': '53',  # Despesas administrativas (inclui vendas)
        'DESPESAS_ADMIN': '53',
        'RESULTADO_FINANCEIRO': '57',  # Despesas financeiras
        'OUTRAS_RECEITAS_DESPESAS': '58',  # Resultados não operacionais
        'TRIBUTOS_LUCRO': '59',  # Provisões sobre lucro
        
        # Detalhes para gráficos
        'CUSTOS_PESSOAL': '53050',
        'CUSTOS_ADMIN': '53350',
        'CUSTOS_TRIBUTARIO': '56',
    }

    def __init__(
        self,
        host: str = "192.168.10.160",
        port: int = 3050,
        database: str = r"e:\Athenas\rps.fdb",
        user: str = "SYSDBA",
        password: str = "masterkey",
    ) -> None:
        self.host = host
        self.port = port
        self.database = database
        self.user = user
        self.password = password

    def _get_connection(self, charset='WIN1252'):
        return firebirdsql.connect(
            host=self.host,
            port=self.port,
            database=self.database,
            user=self.user,
            password=self.password,
            charset=charset
        )

    def _fmt_brl(self, val: float) -> str:
        if val is None: 
            val = 0.0
        if isinstance(val, Decimal):
            val = float(val)
        return f"R$ {val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    def _row_to_dict(self, cursor, row) -> Dict[str, Any]:
        col_names = [col[0].lower() for col in cursor.description]
        return dict(zip(col_names, row))

    def listar_clientes(self) -> List[Dict[str, Any]]:
        """Lista todas as empresas disponíveis no sistema."""
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            try:
                cursor.execute("SELECT codigo, nome, fantaisa FROM tabempresas ORDER BY nome")
            except Exception:
                if conn: conn.rollback()
                cursor = conn.cursor()
                cursor.execute("SELECT codigo, nome, fantasia FROM tabempresas ORDER BY nome")
            
            rows = cursor.fetchall()
            clientes = [self._row_to_dict(cursor, row) for row in rows]
            for c in clientes:
                val = c.get('fantasia') or c.get('fantaisa') or ''
                c['fantasia'] = val
                c['fantaisa'] = val
            return clientes
        except Exception as e:
            print(f"❌ Erro listar clientes: {e}")
            return []
        finally:
            if conn: conn.close()

    def listar_filiais(self, codigo_empresa: int) -> List[Dict[str, Any]]:
        """
        Lista as filiais de uma empresa que possuem dados contábeis.
        Usa o mesmo padrão de JOIN da consulta principal
        (TABSALDOCONTABIL + TABEMPRESAS + TABFILIAL).
        """
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Busca filiais que possuem dados contábeis (mesma estrutura da consulta fornecida)
            sql = """
                SELECT DISTINCT
                    F.CODIGO,
                    F.NOME,
                    COALESCE(F.FANTASIA, F.NOME) AS FANTASIA
                FROM TABSALDOCONTABIL S
                JOIN TABEMPRESAS E 
                    ON E.CODIGO = S.CODIGOEMPRESA
                LEFT JOIN TABFILIAL F 
                    ON E.CODIGO = F.CODIGOEMPRESA
                WHERE S.CODIGOEMPRESA = ?
                  AND S.INICIAL NOT IN (2, 4, 5)
                  AND F.CODIGO IS NOT NULL
                ORDER BY F.CODIGO
            """
            cursor.execute(sql, (codigo_empresa,))
            rows = cursor.fetchall()
            
            filiais = []
            for row in rows:
                filiais.append({
                    'codigo': row[0],
                    'nome': row[1] or f'Filial {row[0]}',
                    'fantasia': row[2] or row[1] or f'Filial {row[0]}'
                })
            
            # Se não encontrou filiais, retorna pelo menos a matriz
            if not filiais:
                filiais.append({
                    'codigo': 0,
                    'nome': 'Matriz',
                    'fantasia': 'Matriz'
                })
                
            return filiais
            
        except Exception as e:
            print(f"❌ Erro listar filiais: {e}")
            return [{'codigo': 0, 'nome': 'Matriz', 'fantasia': 'Matriz'}]
        finally:
            if conn: conn.close()

    def _encontrar_ultimo_periodo_valido(self, conn, cliente_id: int, filiais: Optional[List[int]] = None):
        """
        Busca o último ano/mês que teve movimento em TABSALDOCONTABIL.
        Usa contas que começam com '31' (Receita Bruta) como referência.
        """
        cursor = conn.cursor()
        
        sql = """
            SELECT FIRST 1
                EXTRACT(YEAR FROM S.DATA) AS ANO,
                EXTRACT(MONTH FROM S.DATA) AS MES
            FROM TABSALDOCONTABIL S
            JOIN TABPLANOCONTAS P ON P.CODIGO = S.CODIGOCONTACONTABIL
            WHERE S.CODIGOEMPRESA = ?
              AND S.INICIAL NOT IN (2, 4, 5)
              AND SUBSTRING(S.CODIGOCONTACONTABIL FROM 1 FOR 2) = '31'
              AND (S.VALORDEBITO <> 0 OR S.VALORCREDITO <> 0)
        """
        params = [cliente_id]
        
        if filiais:
            placeholders = ",".join(["?" for _ in filiais])
            sql += f" AND S.CODIGOFILIAL IN ({placeholders})"
            params.extend(filiais)
            
        sql += " ORDER BY EXTRACT(YEAR FROM S.DATA) DESC, EXTRACT(MONTH FROM S.DATA) DESC"
        
        cursor.execute(sql, tuple(params))
        row = cursor.fetchone()
        
        if row:
            print(f"🔄 FALLBACK: Dados encontrados em {int(row[1])}/{int(row[0])}")
            return [int(row[0])], [int(row[1])]  # Retorna ([ano], [mes])
        return None, None

    def _carregar_saldos_view(
        self, 
        conn, 
        cliente_id: int, 
        filiais: Optional[List[int]] = None
    ) -> List[Dict[str, Any]]:
        """
        Carrega TODOS os saldos contábeis de TABSALDOCONTABIL sem filtro de período.
        O recorte por período é feito em Python (nas funções somar_conta / evolucao_mensal).
        
        Retorna lista de dicts com {conta, ano, mes, debito, credito, saldo, valor}
        """
        start = time.time()
        cursor = conn.cursor()
        
        # Query SEM filtro de período — traz TODOS os saldos da empresa
        sql = """
            SELECT
              S.CODIGOCONTACONTABIL AS COD_CONTA_CONTABIL,
              EXTRACT(YEAR FROM S.DATA) AS ANO,
              EXTRACT(MONTH FROM S.DATA) AS MES,
              SUM(CAST(S.VALORDEBITO AS DECIMAL(15, 2))) AS DEBITO,
              SUM(CAST(S.VALORCREDITO AS DECIMAL(15, 2))) AS CREDITO,
              CASE
                WHEN P.NATUREZA = 1 THEN 
                  SUM(CAST(S.VALORDEBITO AS DECIMAL(15, 2))) - SUM(CAST(S.VALORCREDITO AS DECIMAL(15, 2)))
                ELSE 
                  SUM(CAST(S.VALORCREDITO AS DECIMAL(15, 2))) - SUM(CAST(S.VALORDEBITO AS DECIMAL(15, 2)))
              END AS SALDO
            FROM
              TABSALDOCONTABIL S
            JOIN TABPLANOCONTAS P 
              ON P.CODIGO = S.CODIGOCONTACONTABIL
            WHERE
              S.INICIAL NOT IN (2, 4, 5)
              AND S.CODIGOEMPRESA = ?
        """
        params = [cliente_id]
        
        # Filtro de filiais (mantido no SQL — é um filtro de seleção, não de período)
        if filiais:
            filiais_str = ",".join(map(str, filiais))
            sql += f" AND S.CODIGOFILIAL IN ({filiais_str})"
            
        sql += """
            GROUP BY
              S.CODIGOCONTACONTABIL,
              EXTRACT(YEAR FROM S.DATA),
              EXTRACT(MONTH FROM S.DATA),
              P.NATUREZA
        """
        
        cursor.execute(sql, tuple(params))
        rows = cursor.fetchall()
        
        cache = []
        for r in rows:
            # r[0]: COD_CONTA_CONTABIL, r[1]: ANO, r[2]: MES, r[3]: DEBITO, r[4]: CREDITO, r[5]: SALDO
            debito = r[3]
            credito = r[4]
            saldo = r[5]
            if isinstance(debito, Decimal):
                debito = float(debito)
            if isinstance(credito, Decimal):
                credito = float(credito)
            if isinstance(saldo, Decimal):
                saldo = float(saldo)
            cache.append({
                'conta': str(r[0]).strip(),
                'ano': int(r[1]),
                'mes': int(r[2]),
                'debito': float(debito) if debito else 0.0,
                'credito': float(credito) if credito else 0.0,
                'saldo': float(saldo) if saldo else 0.0,
                'valor': float(saldo) if saldo else 0.0,  # alias para compatibilidade
            })
        
        elapsed = time.time() - start
        print(f"✅ Cache carregado: {len(cache)} registros em {elapsed:.2f}s")
        
        return cache

    def obter_contexto_dados(
        self, 
        cliente_id: int, 
        anos: List[int], 
        meses: List[int], 
        filiais: Optional[List[int]] = None
    ) -> Dict[str, Any]:
        """
        Gera o contexto de dados do relatório usando TABSALDOCONTABIL.
        
        Carrega TODOS os saldos contábeis da empresa (sem filtro de período no SQL).
        O recorte por ano/mês é aplicado em Python para preservar a integridade
        dos saldos acumulados.
        
        Parâmetros:
        - cliente_id: Código da empresa (COD_EMPRESA)
        - anos: Lista de anos para o recorte
        - meses: Lista de meses para o recorte
        - filiais: Lista de códigos de filiais (COD_FILIAL) - opcional
        """
        conn = None
        try:
            conn = self._get_connection()
            
            # 1. Nome da Empresa
            nome_cliente = f"Empresa {cliente_id}"
            try:
                cur = conn.cursor()
                cur.execute("SELECT NOME, FANTAISA FROM TABEMPRESAS WHERE CODIGO = ?", (cliente_id,))
                row = cur.fetchone()
                if row: 
                    nome_cliente = row[1] if row[1] and row[1].strip() else row[0]
            except: 
                pass

            # 2. Carregar TODOS os saldos contábeis (sem filtro de período)
            cache_dados = self._carregar_saldos_view(conn, cliente_id, filiais)
            
            # 3. Definir o recorte de período (filtro aplicado em Python)
            anos_set = set(anos)
            meses_set = set(meses)
            
            # Verificar se há dados para o período solicitado
            tem_dados_periodo = any(
                d['ano'] in anos_set and d['mes'] in meses_set
                for d in cache_dados
            )
            
            if not tem_dados_periodo and cache_dados:
                # Dados existem mas não para o período solicitado — fallback
                print(f"⚠️ Nenhum dado no período {meses}/{anos}. Buscando último período válido...")
                novos_anos, novos_meses = self._encontrar_ultimo_periodo_valido(conn, cliente_id, filiais)
                if novos_anos and novos_meses:
                    anos = novos_anos
                    meses = novos_meses
                    anos_set = set(anos)
                    meses_set = set(meses)
            elif not cache_dados:
                print(f"⚠️ Nenhum dado contábil encontrado para empresa {cliente_id}")
            
            # Define período para exibição
            meses_str = ','.join(map(str, meses))
            anos_str = ','.join(map(str, anos))
            periodo_display = f"{meses_str}/{anos_str}"

            # --- Helpers para cálculo (com recorte de período em Python) ---
            def _normalizar_codigo_conta(codigo: str) -> str:
                return ''.join(ch for ch in str(codigo) if ch.isdigit())

            def somar_conta(codigo_ou_prefixo: str) -> float:
                """
                Soma saldos de contas que começam com o código/prefixo especificado,
                filtrado pelo período selecionado (anos_set / meses_set).
                """
                total = 0.0
                prefixo_normalizado = _normalizar_codigo_conta(codigo_ou_prefixo)
                for d in cache_dados:
                    conta = _normalizar_codigo_conta(d['conta'])
                    if (conta.startswith(prefixo_normalizado) 
                            and d['ano'] in anos_set 
                            and d['mes'] in meses_set):
                        total += d['valor']
                return total

            def evolucao_mensal(codigo_ou_prefixo: str) -> List[float]:
                """
                Retorna lista de 12 valores (Jan-Dez) para evolução mensal,
                filtrado pelos anos selecionados.
                """
                meses_val = {m: 0.0 for m in range(1, 13)}
                prefixo_normalizado = _normalizar_codigo_conta(codigo_ou_prefixo)
                for d in cache_dados:
                    conta = _normalizar_codigo_conta(d['conta'])
                    if conta.startswith(prefixo_normalizado) and d['ano'] in anos_set:
                        meses_val[d['mes']] += d['valor']
                return [meses_val[m] for m in range(1, 13)]

            # --- 3. Cálculo de KPIs usando os códigos da VIEW ---
            
            # RECEITA BRUTA OPERACIONAL: Grupo 31 (todas as receitas operacionais)
            # Inclui: Vendas de Produtos (31010), Revenda Mercadorias (31100), Serviços (31150), etc.
            receita_bruta = abs(somar_conta('31100000000001'))
            
            # DEDUÇÕES: Cancelamentos (31500) + Impostos sobre vendas (31800)
            deducoes = abs(somar_conta('315')) + abs(somar_conta('318'))

            # CARGA TRIBUTÁRIA (Resumo Executivo): soma de contas específicas
            contas_carga_tributaria = [
                '31800000000005',
                '31800000000001',
                '31800000000006',
            ]
            carga_tributaria = sum(abs(somar_conta(codigo)) for codigo in contas_carga_tributaria)

            cancelamentos = abs(somar_conta('31500000000004'))
            
            # RECEITAS FINANCEIRAS: Conta 31850
            rec_financeiras = abs(somar_conta('3185'))
            
            # OUTRAS RECEITAS OPERACIONAIS: Conta 31900
            outras_rec_op = abs(somar_conta('319'))
            
            # RECEITAS NÃO OPERACIONAIS: Grupo 32
            rec_nao_op = abs(somar_conta('32'))
            
            # VENDAS LÍQUIDAS = Receita Bruta - Deduções
            vendas_liquidas = receita_bruta - cancelamentos

            # COMPRAS (Resumo Executivo): soma dos saldos de todas as contas iniciadas por 4
            custos = abs(somar_conta('4'))

            # DESPESAS ADMINISTRATIVAS - Grupo 53
            desp_admin = abs(somar_conta('53'))
            
            # DESPESAS TRIBUTÁRIAS - Grupo 56
            desp_tributarias = abs(somar_conta('56'))
            
            # DESPESAS FINANCEIRAS - Grupo 57
            desp_fin = abs(somar_conta('57'))
            
            # RESULTADOS NÃO OPERACIONAIS - Grupo 58
            result_nao_op = abs(somar_conta('58'))
            
            # PROVISÕES E PARTICIPAÇÕES - Grupo 59 (Impostos sobre o lucro)
            impostos = abs(somar_conta('59'))
            
            # Total de despesas operacionais
            desp_op = desp_admin + desp_tributarias

            # LUCRO LÍQUIDO
            # Lucro = Vendas Líquidas - Custos - Despesas Op - Desp Fin + Rec Fin - Outras Desp/Rec - Impostos
            lucro = vendas_liquidas - custos - desp_op - desp_fin + rec_financeiras + rec_nao_op - result_nao_op - impostos

            # --- BALANÇO PATRIMONIAL ---
            # Ativo Circulante - Grupo 11
            ativo_circ = abs(somar_conta('11'))
            # Ativo Não Circulante - Grupo 12
            ativo_n_circ = abs(somar_conta('12'))
            ativo_total = ativo_circ + ativo_n_circ
            
            # Passivo Circulante - Grupo 21
            passivo_circ = abs(somar_conta('21'))
            # Passivo Não Circulante - Grupo 22
            passivo_n_circ = abs(somar_conta('22'))
            passivo_total = passivo_circ + passivo_n_circ
            
            # Patrimônio Líquido - Grupo 23
            patrimonio_liquido = abs(somar_conta('23'))

            # --- INDICADORES ---
            ebitda = lucro + desp_fin + impostos
            
            liquidez_corrente = (ativo_circ / passivo_circ) if passivo_circ > 0 else 0
            margem_liquida = (lucro / vendas_liquidas * 100) if vendas_liquidas > 0 else 0
            endividamento = (passivo_total / ativo_total * 100) if ativo_total > 0 else 0

            # --- ESTUDO TRIBUTÁRIO ---
            # Lucro Real: IRPJ (15%) + Adicional (10% sobre excedente 20k/mês) + CSLL (9%)
            # Lucro Presumido: Base presumida * alíquotas
            
            lucro_mensal = lucro / len(meses) if len(meses) > 0 else lucro
            
            # Lucro Real
            irpj_real = lucro * 0.15
            adicional_irpj = max(0, (lucro_mensal - 20000) * len(meses)) * 0.10
            csll_real = lucro * 0.09
            total_lucro_real = irpj_real + adicional_irpj + csll_real
            
            # Lucro Presumido (8% para comércio/indústria, 32% para serviços)
            # Usando 8% como padrão - pode ser ajustado
            base_presumida_irpj = vendas_liquidas * 0.08
            base_presumida_csll = vendas_liquidas * 0.12
            
            irpj_presumido = base_presumida_irpj * 0.15
            adicional_presumido = max(0, (base_presumida_irpj / len(meses) - 20000) * len(meses)) * 0.10 if len(meses) > 0 else 0
            csll_presumido = base_presumida_csll * 0.09
            total_lucro_presumido = irpj_presumido + adicional_presumido + csll_presumido
            
            economia = total_lucro_real - total_lucro_presumido
            recomendacao = "Lucro Presumido" if economia > 0 else "Lucro Real"

            # --- DETALHES DE CUSTOS (para gráfico pizza) ---
            # Despesas com Pessoal - Grupo 53050
            custos_pessoal = abs(somar_conta('53050'))
            # Despesas Gerais - Grupo 53350
            custos_admin = abs(somar_conta('53350'))
            # Despesas Tributárias - Grupo 56
            custos_tributario = abs(somar_conta('56'))
            
            # Outros (para completar)
            outros = result_nao_op

            # Log de debug
            print(f"📊 Dados calculados para empresa {cliente_id}:")
            print(f"   Receita Bruta: {self._fmt_brl(receita_bruta)}")
            print(f"   Deduções: {self._fmt_brl(deducoes)}")
            print(f"   Vendas Líquidas: {self._fmt_brl(vendas_liquidas)}")
            print(f"   Custos: {self._fmt_brl(custos)}")
            print(f"   Lucro Líquido: {self._fmt_brl(lucro)}")

            return {
                "dados": {
                    "cliente_id": cliente_id,
                    "cliente_nome": nome_cliente,
                    "periodo": periodo_display,
                    "kpis": {
                        "vendas_liquidas": self._fmt_brl(vendas_liquidas),
                        "carga_tributaria": self._fmt_brl(carga_tributaria),
                        "compras": self._fmt_brl(custos),
                        "capex": self._fmt_brl(0),  # CAPEX não disponível na view contábil
                        "opex": self._fmt_brl(desp_admin),
                        "finex": self._fmt_brl(desp_fin),
                        "outros": self._fmt_brl(outros),
                        "lucro_liquido": self._fmt_brl(lucro),
                        "lucro_liquido_raw": lucro,
                    },
                    "indicadores": {
                        "ebitda": self._fmt_brl(ebitda),
                        "liquidez_corrente": f"{liquidez_corrente:.2f}" if liquidez_corrente > 0 else "N/A",
                        "margem_liquida": f"{margem_liquida:.1f}%",
                        "endividamento": f"{endividamento:.1f}%",
                    },
                    "estudo_tributario": {
                        "lucro_real_valor": self._fmt_brl(total_lucro_real),
                        "lucro_real_irpj": self._fmt_brl(irpj_real + adicional_irpj),
                        "lucro_real_csll": self._fmt_brl(csll_real),
                        "lucro_presumido_valor": self._fmt_brl(total_lucro_presumido),
                        "lucro_presumido_irpj": self._fmt_brl(irpj_presumido + adicional_presumido),
                        "lucro_presumido_csll": self._fmt_brl(csll_presumido),
                        "economia_mensal": self._fmt_brl(abs(economia) / len(meses)) if len(meses) > 0 else self._fmt_brl(0),
                        "economia_anual": self._fmt_brl(abs(economia) * (12 / len(meses))) if len(meses) > 0 else self._fmt_brl(0),
                        "recomendacao": recomendacao
                    },
                    "distribuicao_lucros": {
                        "total": self._fmt_brl(lucro if lucro > 0 else 0),
                        "socios": []  # Dados de sócios não disponíveis na view
                    },
                    "tabela_roe": []  # ROE histórico não implementado
                },
                "graficos_data": {
                    "vendas_evo": evolucao_mensal('31'),  # Receita Bruta Operacional
                    "custos_evo": evolucao_mensal('49'),  # Custos das Vendas
                    "ativos_evo": evolucao_mensal('1'),   # Todo grupo 1 (Ativo)
                    "pl_evo": evolucao_mensal('23'),      # Patrimônio Líquido
                    "composicao_ativo": [ativo_circ, ativo_n_circ],
                    "composicao_passivo": [passivo_circ, passivo_n_circ],
                    "custos_detalhe": [custos_pessoal, custos_admin, custos_tributario]
                }
            }

        except Exception as e:
            print(f"❌ Erro crítico no provider: {e}")
            import traceback
            traceback.print_exc()
            
            # Retorno de emergência completo
            return self._contexto_vazio(cliente_id)
            
        finally:
            if conn: 
                conn.close()

    def _contexto_vazio(self, cliente_id: int) -> Dict[str, Any]:
        """Retorna um contexto vazio para não quebrar a página em caso de erro."""
        return {
            "dados": {
                "cliente_id": cliente_id,
                "cliente_nome": "Erro Carregamento", 
                "periodo": "N/A",
                "kpis": {
                    "vendas_liquidas": "R$ 0,00",
                    "carga_tributaria": "R$ 0,00",
                    "compras": "R$ 0,00",
                    "capex": "R$ 0,00",
                    "opex": "R$ 0,00",
                    "finex": "R$ 0,00",
                    "outros": "R$ 0,00",
                    "lucro_liquido": "R$ 0,00",
                    "lucro_liquido_raw": 0
                }, 
                "indicadores": {
                    "ebitda": "R$ 0,00",
                    "liquidez_corrente": "0",
                    "margem_liquida": "0%",
                    "endividamento": "0%"
                },
                "estudo_tributario": {
                    "lucro_real_valor": "R$ 0,00",
                    "lucro_real_irpj": "R$ 0,00",
                    "lucro_real_csll": "R$ 0,00",
                    "lucro_presumido_valor": "R$ 0,00",
                    "lucro_presumido_irpj": "R$ 0,00",
                    "lucro_presumido_csll": "R$ 0,00",
                    "economia_mensal": "R$ 0,00",
                    "economia_anual": "R$ 0,00",
                    "recomendacao": "-"
                },
                "distribuicao_lucros": {
                    "total": "R$ 0,00", 
                    "socios": []
                },
                "tabela_roe": []
            },
            "graficos_data": {
                "vendas_evo": [0.0] * 12,
                "custos_evo": [0.0] * 12,
                "ativos_evo": [0.0] * 12,
                "pl_evo": [0.0] * 12,
                "composicao_ativo": [0, 0],
                "composicao_passivo": [0, 0],
                "custos_detalhe": [0, 0, 0]
            }
        }

    def encontrar_ultimo_periodo_balancete(self, cliente_id: int, filiais: Optional[List[int]] = None):
        """
        Busca o último ano/mês com dados em TABSALDOCONTABIL para usar como fallback.
        Retorna (ano, [1..mes]) — todos os meses do ano até o mês encontrado,
        para capturar contas de receita/despesa que acumulam ao longo do ano.
        """
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            sql = """
                SELECT FIRST 1
                    EXTRACT(YEAR FROM S.DATA) AS ANO,
                    EXTRACT(MONTH FROM S.DATA) AS MES
                FROM TABSALDOCONTABIL S
                WHERE S.CODIGOEMPRESA = ?
                    AND (S.VALORDEBITO <> 0 OR S.VALORCREDITO <> 0)
            """
            params = [cliente_id]
            
            if filiais:
                filiais_str = ",".join(map(str, filiais))
                sql += f" AND S.CODIGOFILIAL IN ({filiais_str})"
            
            sql += " ORDER BY S.DATA DESC"
            
            cursor.execute(sql, tuple(params))
            row = cursor.fetchone()
            
            if row:
                ano = int(row[0])
                mes = int(row[1])
                # Se apenas janeiro tem dados, provavelmente são saldos iniciais.
                # Buscar o ano anterior completo que terá receitas/despesas.
                if mes == 1:
                    # Verificar se o ano anterior tem dados
                    sql2 = """
                        SELECT FIRST 1
                            EXTRACT(YEAR FROM S.DATA) AS ANO
                        FROM TABSALDOCONTABIL S
                        WHERE S.CODIGOEMPRESA = ?
                            AND EXTRACT(YEAR FROM S.DATA) = ?
                            AND (S.VALORDEBITO <> 0 OR S.VALORCREDITO <> 0)
                    """
                    params2 = [cliente_id, ano - 1]
                    cursor.execute(sql2, tuple(params2))
                    row2 = cursor.fetchone()
                    if row2:
                        ano = ano - 1
                        mes = 12
                
                # Retorna todos os meses de 1 até o mês encontrado
                meses = list(range(1, mes + 1))
                print(f"🔄 FALLBACK balancete: Dados encontrados até {mes}/{ano} (meses {meses})")
                return ano, meses
            return None, None
        except Exception as e:
            print(f"❌ Erro ao buscar período fallback do balancete: {e}")
            return None, None
        finally:
            if conn:
                conn.close()

    def obter_balancete(
        self,
        cliente_id: int,
        anos: List[int],
        meses: List[int],
        filiais: Optional[List[int]] = None
    ) -> List[Dict[str, Any]]:
        """
        Retorna o balancete de verificação completo com débito, crédito e saldo de cada conta.
        
        Carrega TODOS os saldos da empresa (sem filtro de período no SQL).
        O recorte por ano/mês é aplicado em Python para preservar a integridade
        dos saldos acumulados.
        
        Processo:
        1. Busca TODOS os saldos das contas detalhadas (sem filtro de período)
        2. Filtra em Python pelo período solicitado (recorte)
        3. Busca todas as contas da TABPLANOCONTAS para obter nomes e hierarquia
        4. Agrega valores nos níveis superiores baseado no PREFIXO do código da conta
        
        Retorna lista de dicionários com:
        - codigo, nome, nivel, tipo, natureza, grupo, conta_mae
        - codigo_reduzido: Código reduzido da conta
        - debito, credito, saldo: Valores calculados
        """
        conn = None
        try:
            # Usa ISO8859_1 pois TABPLANOCONTAS pode conter bytes inválidos em WIN1252
            conn = self._get_connection(charset='ISO8859_1')
            cursor = conn.cursor()
            
            # ============================================================
            # PASSO 1: Buscar TODOS os saldos (sem filtro de período)
            # ============================================================
            anos_set = set(anos)
            meses_set = set(meses)
            
            # Query SEM filtro de período — traz TODOS os saldos da empresa
            sql_saldos = """
                SELECT
                  E.CODIGO AS COD_EMPRESA,
                  E.NOME AS NOME_EMPRESA,
                  F.CODIGO AS COD_FILIAL,
                  F.NOME AS NOME_FILIAL,
                  F.FANTASIA AS NOME_FANTASIA_FILIAL,
                  S.CODIGOCONTACONTABIL AS COD_CONTA_CONTABIL,
                  EXTRACT(YEAR FROM S.DATA) AS ANO,
                  EXTRACT(MONTH FROM S.DATA) AS MES,
                  MIN(S.INICIAL) AS SALDO_INICIAL,
                  P.NOME AS NOME_CONTA,
                  CASE
                    WHEN P.TIPO = 1 THEN 'Sintetica'
                    ELSE 'Analitica'
                  END AS TIPO_CONTA,
                  CASE
                    WHEN P.NATUREZA = 1 THEN 'Devedora'
                    ELSE 'Credora'
                  END AS NATUREZA,
                  SUBSTRING(S.CODIGOCONTACONTABIL FROM 1 FOR 1) AS COD_GRUPO,
                  SUM(CAST(S.VALORDEBITO AS DECIMAL(15, 2))) AS DEBITO,
                  SUM(CAST(S.VALORCREDITO AS DECIMAL(15, 2))) AS CREDITO,
                  CASE
                    WHEN P.NATUREZA = 1 THEN 
                      SUM(CAST(S.VALORDEBITO AS DECIMAL(15, 2))) - SUM(CAST(S.VALORCREDITO AS DECIMAL(15, 2)))
                    ELSE 
                      SUM(CAST(S.VALORCREDITO AS DECIMAL(15, 2))) - SUM(CAST(S.VALORDEBITO AS DECIMAL(15, 2)))
                  END AS SALDO,
                  P.CODIGOREDUZIDO AS COD_REDUZIDO
                FROM
                  TABSALDOCONTABIL S
                JOIN TABPLANOCONTAS P 
                  ON P.CODIGO = S.CODIGOCONTACONTABIL
                JOIN TABEMPRESAS E 
                  ON E.CODIGO = S.CODIGOEMPRESA 
                LEFT JOIN TABFILIAL F 
                  ON E.CODIGO = F.CODIGOEMPRESA
                WHERE
                  S.INICIAL NOT IN (2, 4, 5)
                  AND S.CODIGOEMPRESA = ?
            """
            params = [cliente_id]
            
            # Filtro de filiais (mantido no SQL — é filtro de seleção, não de período)
            if filiais:
                filiais_str = ",".join(map(str, filiais))
                sql_saldos += f" AND S.CODIGOFILIAL IN ({filiais_str})"
            
            sql_saldos += """
                GROUP BY
                  E.CODIGO,
                  E.NOME,
                  F.CODIGO,
                  F.NOME,
                  F.FANTASIA,
                  S.CODIGOCONTACONTABIL,
                  EXTRACT(YEAR FROM S.DATA),
                  EXTRACT(MONTH FROM S.DATA),
                  P.NOME,
                  P.TIPO,
                  P.NATUREZA,
                  SUBSTRING(S.CODIGOCONTACONTABIL FROM 1 FOR 1),
                  P.CODIGOREDUZIDO
            """
            
            cursor.execute(sql_saldos, tuple(params))
            rows_saldos = cursor.fetchall()
            
            # Armazenar contas detalhadas (com recorte de período em Python)
            contas_detalhadas = {}
            for row in rows_saldos:
                # Colunas da query:
                # 0: COD_EMPRESA, 1: NOME_EMPRESA, 2: COD_FILIAL, 3: NOME_FILIAL, 4: NOME_FANTASIA_FILIAL
                # 5: COD_CONTA_CONTABIL, 6: ANO, 7: MES, 8: SALDO_INICIAL, 9: NOME_CONTA
                # 10: TIPO_CONTA, 11: NATUREZA, 12: COD_GRUPO, 13: DEBITO, 14: CREDITO, 15: SALDO
                # 16: COD_REDUZIDO
                
                # Recorte de período — só acumula registros do período selecionado
                ano_reg = int(row[6]) if row[6] else 0
                mes_reg = int(row[7]) if row[7] else 0
                if ano_reg not in anos_set or mes_reg not in meses_set:
                    continue
                
                codigo = str(row[5]).strip() if row[5] else ''
                if not codigo:
                    continue
                
                debito = float(row[13]) if row[13] else 0.0
                credito = float(row[14]) if row[14] else 0.0
                saldo = float(row[15]) if row[15] else 0.0
                if isinstance(debito, Decimal):
                    debito = float(debito)
                if isinstance(credito, Decimal):
                    credito = float(credito)
                if isinstance(saldo, Decimal):
                    saldo = float(saldo)
                
                # Acumular valores (pode haver múltiplas linhas por mês/filial)
                if codigo in contas_detalhadas:
                    contas_detalhadas[codigo]['debito'] += debito
                    contas_detalhadas[codigo]['credito'] += credito
                    contas_detalhadas[codigo]['saldo'] += saldo
                else:
                    tipo_conta = str(row[10]).strip() if row[10] else 'Analitica'
                    natureza = str(row[11]).strip() if row[11] else 'Devedora'
                    codigo_reduzido = str(row[16]).strip() if row[16] else ''
                    
                    contas_detalhadas[codigo] = {
                        'codigo': codigo,
                        'nome': str(row[9]).strip() if row[9] else '',
                        'tipo': tipo_conta,
                        'natureza': natureza,
                        'grupo': str(row[12]).strip() if row[12] else (codigo[0] if codigo else ''),
                        'debito': debito,
                        'credito': credito,
                        'saldo': saldo,
                        'codigo_reduzido': codigo_reduzido,
                    }
            
            print(f"💰 Saldos carregados: {len(contas_detalhadas)} contas da consulta")
            
            # ============================================================
            # PASSO 2: Buscar TODAS as contas do plano de contas (para nomes e hierarquia)
            # ============================================================
            sql_plano = """
                SELECT
                    CODIGO,
                    NOME,
                    CODIGOCONTAMAE,
                    TIPO,
                    NATUREZA,
                    CODIGOREDUZIDO,
                    NIVEL
                FROM
                    TABPLANOCONTAS
                WHERE
                    CODIGOPLANOCONTAS = 11
                ORDER BY
                    CODIGO
            """
            cursor.execute(sql_plano)
            rows_plano = cursor.fetchall()
            
            # Montar dicionário de todas as contas do plano
            plano_contas = {}
            for row in rows_plano:
                codigo = str(row[0]).strip() if row[0] else ''
                if not codigo:
                    continue
                
                tipo = 'Sintetica' if row[3] == 1 else 'Analitica'
                natureza = 'Devedora' if row[4] == 1 else 'Credora'
                nivel = int(row[6]) if row[6] is not None else 1
                
                plano_contas[codigo] = {
                    'codigo': codigo,
                    'nome': str(row[1]).strip() if row[1] else '',
                    'conta_mae': str(row[2]).strip() if row[2] else None,
                    'tipo': tipo,
                    'natureza': natureza,
                    'codigo_reduzido': str(row[5]).strip() if row[5] else '',
                    'nivel': nivel,
                    'grupo': codigo[0] if codigo else '',
                }
            
            print(f"📊 Plano de contas carregado: {len(plano_contas)} contas")
            
            # ============================================================
            # PASSO 3: Agregar valores nos níveis superiores por PREFIXO
            # ============================================================
            # Para cada conta do plano, somamos todas as contas detalhadas 
            # que começam com o código dessa conta
            
            resultado_contas = {}
            
            for codigo_plano, info_plano in plano_contas.items():
                debito_total = 0.0
                credito_total = 0.0
                saldo_total = 0.0
                
                # Para cada conta detalhada, verificar se começa com este código
                for codigo_det, info_det in contas_detalhadas.items():
                    if codigo_det.startswith(codigo_plano):
                        debito_total += info_det['debito']
                        credito_total += info_det['credito']
                        saldo_total += info_det['saldo']
                
                # Só incluir contas que têm movimento
                if debito_total != 0.0 or credito_total != 0.0:
                    resultado_contas[codigo_plano] = {
                        'codigo': codigo_plano,
                        'nome': info_plano['nome'],
                        'nivel': info_plano['nivel'],
                        'tipo': info_plano['tipo'],
                        'natureza': info_plano['natureza'],
                        'grupo': info_plano['grupo'],
                        'conta_mae': info_plano['conta_mae'],
                        'codigo_reduzido': info_plano['codigo_reduzido'],
                        'debito': debito_total,
                        'credito': credito_total,
                        'saldo': saldo_total,
                    }
            
            # ============================================================
            # PASSO 4: Montar resultado final com saldo calculado no SQL
            # ============================================================
            # Saldo já vem calculado pela query considerando natureza:
            #   Devedora: DEBITO - CREDITO
            #   Credora: CREDITO - DEBITO
            balancete = []
            for codigo in sorted(resultado_contas.keys()):
                conta = resultado_contas[codigo]
                debito = conta['debito']
                credito = conta['credito']
                saldo = conta['saldo']
                
                balancete.append({
                    'codigo': codigo,
                    'nome': conta['nome'],
                    'nivel': conta['nivel'],
                    'tipo': conta['tipo'],
                    'natureza': conta['natureza'],
                    'grupo': conta['grupo'],
                    'conta_mae': conta['conta_mae'],
                    'codigo_reduzido': conta['codigo_reduzido'],
                    'debito': debito,
                    'credito': credito,
                    'saldo': saldo,
                    'debito_fmt': self._fmt_brl(debito),
                    'credito_fmt': self._fmt_brl(credito),
                    'saldo_fmt': self._fmt_brl(saldo)
                })
            
            print(f"📋 Balancete carregado: {len(balancete)} contas para empresa {cliente_id}")
            return balancete
            
        except Exception as e:
            print(f"❌ Erro ao obter balancete: {e}")
            import traceback
            traceback.print_exc()
            return []
        finally:
            if conn:
                conn.close()