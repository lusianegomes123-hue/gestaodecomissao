import sqlite3
import os

dbs = [
    'comissoes_prod.db',
    'comissoes_v1.db',
    'comissoes_v1_restaurado.db',
    r'instance\comissoes.db',
    r'instance\comissoes_final.db',
    r'instance\comissoes_v2.db',
    r'instance\comissoes_v3.db'
]

for db_path in dbs:
    try:
        if not os.path.exists(db_path):
            continue
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        
        # Check if vendas exists
        c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='vendas'")
        if c.fetchone():
            c.execute("SELECT count(*), IFNULL(MAX(data_venda), 'N/A') FROM vendas")
            count, last_date = c.fetchone()
            print(f"[{db_path}] vendas: {count} rows. Last: {last_date}")
            
            # See if February data exists
            c.execute("SELECT COUNT(*) FROM vendas WHERE data_venda LIKE '2026-02%'")
            feb_count = c.fetchone()[0]
            if feb_count > 0:
                print(f"   ---> FOUND {feb_count} FEB RECORDS HERE!")
        else:
            print(f"[{db_path}] No vendas table")
        conn.close()
    except Exception as e:
        print(f"[{db_path}] Error: {e}")
