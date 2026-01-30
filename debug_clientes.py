import firebirdsql
import sys

# --- CONFIGURAÇÃO ---
DB_HOST = "192.168.10.160"
DB_PORT = 3050
DB_FILE = r"e:\Athenas\rps.fdb"
DB_USER = "SYSDBA"
DB_PASS = "masterkey"

def debug_clientes():
    print(f"🔌 Conectando em: {DB_HOST}/{DB_PORT}:{DB_FILE}")
    try:
        conn = firebirdsql.connect(
            host=DB_HOST,
            port=DB_PORT,
            database=DB_FILE,
            user=DB_USER,
            password=DB_PASS,
            charset='WIN1252'
        )
        cursor = conn.cursor()
        
        # 1. Verificar colunas da tabela TABEMPRESAS
        print("\n🔍 Estrutura da tabela TABEMPRESAS:")
        cursor.execute("SELECT FIRST 1 * FROM TABEMPRESAS")
        # Apenas para pegar o description (metadados)
        colunas = [desc[0] for desc in cursor.description]
        print(f"   Colunas encontradas: {colunas}")
        
        if 'FANTAISA' in colunas:
            print("   ⚠️ ACHOU: A coluna se chama 'FANTAISA' (com erro de digitação).")
        elif 'FANTASIA' in colunas:
            print("   ✅ ACHOU: A coluna se chama 'FANTASIA' (correto).")
        else:
            print("   ❌ ERRO: Não encontrei coluna de Fantasia.")

        # 2. Testar listagem simples
        print("\n🔍 Testando listagem de nomes:")
        # Usando * para garantir que não falha por nome de coluna errado
        cursor.execute("SELECT FIRST 5 CODIGO, NOME FROM TABEMPRESAS")
        rows = cursor.fetchall()
        for row in rows:
            print(f"   Cliente: {row}")

        conn.close()
        
    except Exception as e:
        print(f"❌ Erro: {e}")

if __name__ == "__main__":
    debug_clientes()