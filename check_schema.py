import sqlite3

db_path = 'comissoes_prod.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

tables = ['vendas', 'cobrancas', 'consultas', 'procedimentos']

for t in tables:
    print(f"--- Schema for {t} ---")
    cursor.execute(f"PRAGMA table_info({t})")
    cols = cursor.fetchall()
    for c in cols:
        print(c)
        
conn.close()
