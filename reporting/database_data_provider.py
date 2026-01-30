from __future__ import annotations
import firebirdsql
import time
from typing import Dict, Any, List, Optional
from datetime import datetime

from .data_provider import DataProvider

class DatabaseDataProvider(DataProvider):
    """
    Provider definitivo e OTIMIZADO para Firebird/Athenas.
    - Conexão robusta (Firebird Pure Python).
    - Cache em memória: Faz 1 consulta pesada em vez de 20.
    - FALLBACK AUTOMÁTICO: Se não achar dados na data escolhida, busca o último mês com movimento.
    """

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

    def _get_connection(self):
        return firebirdsql.connect(
            host=self.host,
            port=self.port,
            database=self.database,
            user=self.user,
            password=self.password,
            charset='WIN1252'
        )

    def _fmt_brl(self, val: float) -> str:
        if val is None: val = 0.0
        return f"R$ {val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    def _row_to_dict(self, cursor, row) -> Dict[str, Any]:
        col_names = [col[0].lower() for col in cursor.description]
        return dict(zip(col_names, row))

    def listar_clientes(self) -> List[Dict[str, Any]]:
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
        return [] 

    def _encontrar_ultimo_periodo_valido(self, conn, cliente_id):
        """
        Busca o último ano/mês que teve movimento de vendas (Grupo 3) para evitar relatórios zerados.
        """
        cursor = conn.cursor()
        # Busca o último ano/mês com saldo no grupo 3 (Resultado)
        sql = """
            SELECT FIRST 1 ANO, MES 
            FROM FAT_HIERARQUIA_SALDOS 
            WHERE COD_EMPRESA = ? 
            AND CAST(COD_CONTA_HIERARQUIA AS VARCHAR(50)) LIKE '3%'
            AND SALDO_MOVIMENTO <> 0
            ORDER BY ANO DESC, MES DESC
        """
        cursor.execute(sql, (cliente_id,))
        row = cursor.fetchone()
        if row:
            print(f"🔄 FALLBACK: Dados encontrados em {row[1]}/{row[0]}")
            return [row[0]], [row[1]] # Retorna ([ano], [mes])
        return None, None

    def _carregar_cache_analitico(self, conn, cliente_id, anos, meses, filiais=None):
        start = time.time()
        cursor = conn.cursor()
        
        anos_str = ",".join(map(str, anos))
        meses_str = ",".join(map(str, meses))
        
        # 1. Tenta carregar dados do período solicitado
        sql = f"""
            SELECT 
                CAST(COD_CONTA_HIERARQUIA AS VARCHAR(50)) as CONTA,
                MES,
                SUM(SALDO_MOVIMENTO) as VALOR
            FROM FAT_HIERARQUIA_SALDOS
            WHERE COD_EMPRESA = ?
              AND ANO IN ({anos_str})
              AND MES IN ({meses_str})
              AND TIPO_CONTA = 'Analitica'
        """
        params = [cliente_id]
        if filiais:
            filiais_str = ",".join(map(str, filiais))
            sql += f" AND COD_FILIAL IN ({filiais_str})"
        sql += " GROUP BY 1, 2"
        
        cursor.execute(sql, tuple(params))
        rows = cursor.fetchall()
        
        # 2. SE NÃO VEIO NADA, TENTA BUSCAR DADOS ANTERIORES (FALLBACK)
        if not rows:
            print(f"⚠️ Nenhum dado em {meses}/{anos}. Tentando buscar histórico...")
            novos_anos, novos_meses = self._encontrar_ultimo_periodo_valido(conn, cliente_id)
            
            if novos_anos and novos_meses:
                # Recarrega com a nova data
                return self._carregar_cache_analitico(conn, cliente_id, novos_anos, novos_meses, filiais), f"{novos_meses[0]}/{novos_anos[0]}"
            
        cache = []
        for r in rows:
            cache.append({
                'conta': str(r[0]),
                'mes': int(r[1]),
                'valor': float(r[2]) if r[2] else 0.0
            })
            
        return cache, None # None indica que usamos a data original

    def obter_contexto_dados(
        self, 
        cliente_id: int, 
        anos: List[int], 
        meses: List[int], 
        filiais: Optional[List[int]] = None
    ) -> Dict[str, Any]:
        
        conn = None
        try:
            conn = self._get_connection()
            
            # 1. Nome da Empresa
            nome_cliente = f"Empresa {cliente_id}"
            try:
                cur = conn.cursor()
                cur.execute("SELECT NOME, FANTAISA FROM TABEMPRESAS WHERE CODIGO = ?", (cliente_id,))
                row = cur.fetchone()
                if row: nome_cliente = row[1] if row[1] and row[1].strip() else row[0]
            except: pass

            # 2. Carregar Cache (Com Fallback Automático)
            cache_dados, periodo_real = self._carregar_cache_analitico(conn, cliente_id, anos, meses, filiais)
            
            # Se houve fallback, avisar na interface trocando o período exibido
            periodo_display = periodo_real if periodo_real else f"{','.join(map(str, meses))}/{','.join(map(str, anos))}"

            # --- Helpers em Memória ---
            def somar(prefixo: str) -> float:
                return sum(d['valor'] for d in cache_dados if d['conta'].startswith(prefixo))

            def evolucao(prefixo: str) -> List[float]:
                meses_val = {m: 0.0 for m in range(1, 13)}
                for d in cache_dados:
                    if d['conta'].startswith(prefixo):
                        meses_val[d['mes']] += d['valor']
                return list(meses_val.values())

            # --- 3. Cálculo de KPIs ---
            
            # Receita Bruta (311)
            receita_bruta = somar("311")
            
            # Se 311 vier zerado, tenta 3.01 (Outro padrão comum)
            if receita_bruta == 0:
                # print("⚠️ Receita 311 zerada. Tentando prefixo 301...")
                receita_bruta = somar("301")

            deducoes = somar("315")
            vendas_liquidas = abs(receita_bruta) - abs(deducoes)

            # print(f"💰 RESULTADO FINAL: Bruta={receita_bruta}, Liq={vendas_liquidas}")

            custos = abs(somar("32"))
            desp_op = abs(somar("33")) + abs(somar("34"))
            fin_val = somar("35")
            desp_fin = abs(fin_val) if fin_val < 0 else 0
            outros = abs(somar("36"))
            impostos = abs(somar("39"))
            lucro = vendas_liquidas - custos - desp_op + fin_val # Soma algébrica pois fin pode ser receita

            # Balanço
            ativo_circ = abs(somar("11"))
            ativo_n_circ = abs(somar("12"))
            passivo_circ = abs(somar("21"))
            passivo_n_circ = abs(somar("22"))

            return {
                "dados": {
                    "cliente_id": cliente_id,
                    "cliente_nome": nome_cliente,
                    "periodo": periodo_display, # Mostra a data REAL dos dados
                    "kpis": {
                        "vendas_liquidas": self._fmt_brl(vendas_liquidas),
                        "carga_tributaria": self._fmt_brl(impostos),
                        "compras": self._fmt_brl(custos),
                        "capex": self._fmt_brl(0),
                        "opex": self._fmt_brl(desp_op),
                        "finex": self._fmt_brl(desp_fin),
                        "outros": self._fmt_brl(outros),
                        "lucro_liquido": self._fmt_brl(lucro),
                        "lucro_liquido_raw": lucro,  # Necessário para lógica do template
                    },
                    "indicadores": {
                        "ebitda": self._fmt_brl(lucro + desp_fin + impostos),
                        "liquidez_corrente": f"{(ativo_circ / passivo_circ):.2f}" if passivo_circ > 0 else "N/A",
                        "margem_liquida": f"{(lucro/vendas_liquidas*100):.1f}%" if vendas_liquidas > 0 else "0%",
                        "endividamento": f"{((passivo_circ+passivo_n_circ)/(ativo_circ+ativo_n_circ)*100):.1f}%" if (ativo_circ+ativo_n_circ) > 0 else "0%",
                    },
                    "estudo_tributario": {
                        "lucro_real_valor": self._fmt_brl(lucro * 0.34),
                        "lucro_presumido_valor": self._fmt_brl(vendas_liquidas * 0.06),
                        "recomendacao": "Análise"
                    },
                    "distribuicao_lucros": {
                        "total": self._fmt_brl(lucro if lucro > 0 else 0),
                        "socios": []
                    },
                    "tabela_roe": []
                },
                "graficos_data": {
                    "vendas_evo": evolucao("311") if receita_bruta != 0 else evolucao("301"),
                    "custos_evo": evolucao("32"),
                    "ativos_evo": evolucao("1"),
                    "pl_evo": evolucao("23"),
                    "composicao_ativo": [ativo_circ, ativo_n_circ],
                    "composicao_passivo": [passivo_circ, passivo_n_circ],
                    "custos_detalhe": [abs(somar("331")), abs(somar("332")), abs(somar("333"))]
                }
            }

        except Exception as e:
            print(f"❌ Erro crítico no provider: {e}")
            # Retorno de emergência COMPLETO para não quebrar a página
            return {
                "dados": {
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
                        "lucro_presumido_valor": "R$ 0,00", 
                        "recomendacao": "-"
                    },
                    "distribuicao_lucros": {
                        "total": "R$ 0,00", 
                        "socios": []
                    },
                    "tabela_roe": []
                },
                "graficos_data": {} # O ReportService sabe lidar com isso vazio
            }
        finally:
            if conn: conn.close()