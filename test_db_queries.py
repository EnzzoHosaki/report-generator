import firebirdsql
import sys
from datetime import datetime

# --- CONFIGURAÇÃO DO PRINT ---
DB_HOST = "192.168.10.160"
DB_PORT = 3050
DB_FILE = r"e:\Athenas\rps.fdb" # Caminho Windows
DB_USER = "SYSDBA"
DB_PASS = "masterkey" # Senha padrão Firebird (tente essa primeiro)

def get_connection():
    print(f"🔌 Tentando conectar em: {DB_HOST}/{DB_PORT}:{DB_FILE}")
    try:
        # Usando driver Pure Python (sem dependência de DLL/libfbclient)
        return firebirdsql.connect(
            host=DB_HOST,
            port=DB_PORT,
            database=DB_FILE,
            user=DB_USER,
            password=DB_PASS,
            charset='WIN1252'
        )
    except Exception as e:
        print(f"❌ Erro crítico de conexão: {e}")
        return None

def testar_view():
    conn = get_connection()
    if not conn: return

    print("\n🔍 Verificando se a View FAT_HIERARQUIA_SALDOS existe...")
    try:
        cursor = conn.cursor()
        # Firebird query para verificar tabelas/views
        cursor.execute("""
            SELECT RDB$RELATION_NAME 
            FROM RDB$RELATIONS 
            WHERE RDB$RELATION_NAME = 'FAT_HIERARQUIA_SALDOS'
        """)
        row = cursor.fetchone()
        
        if row:
            print("   ✅ SUCESSO: A view existe no banco de dados!")
            
            # --- OTIMIZAÇÃO: Buscar um cliente para filtrar ---
            print("\n🔍 Buscando uma empresa para teste (para evitar travamento)...")
            cursor.execute("SELECT FIRST 1 CODIGO, NOME FROM TABEMPRESAS")
            empresa = cursor.fetchone()
            
            if empresa:
                cod_empresa = empresa[0]
                nome_empresa = empresa[1]
                print(f"   Empresa encontrada: {cod_empresa} - {nome_empresa}")
                
                # Teste rápido de dados COM FILTRO
                print(f"\n🔍 Testando SELECT OTIMIZADO na View (Empresa {cod_empresa}, Ano 2024)...")
                
                query = """
                    SELECT FIRST 5 * FROM FAT_HIERARQUIA_SALDOS 
                    WHERE COD_EMPRESA = ? 
                    AND ANO IN (2024, 2025)
                """
                print(f"   Executando query filtrada...")
                cursor.execute(query, (cod_empresa,))
                
                rows = cursor.fetchall()
                if not rows:
                    print("   ⚠️ Nenhuma linha retornada para 2024/2025. Tentando sem filtro de ano...")
                    cursor.execute("SELECT FIRST 5 * FROM FAT_HIERARQUIA_SALDOS WHERE COD_EMPRESA = ?", (cod_empresa,))
                    rows = cursor.fetchall()

                col_names = [desc[0] for desc in cursor.description]
                print(f"   Colunas encontradas: {col_names}")
                print("   " + "-"*60)
                for r in rows:
                    print(f"   Row: {r}")
            else:
                print("   ⚠️ Nenhuma empresa encontrada em TABEMPRESAS.")

        else:
            print("   ❌ ERRO: A view FAT_HIERARQUIA_SALDOS não foi encontrada.")
            print("      Você precisa rodar o comando 'CREATE VIEW...' no DBeaver conectado a este banco.")

    except Exception as e:
        print(f"   ❌ Erro durante o teste: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    testar_view()