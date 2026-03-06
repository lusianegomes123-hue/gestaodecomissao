import sqlite3
import os

db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'comissoes_prod.db')
print(f"Fixing db at {db_path}")
conn = sqlite3.connect(db_path)
c = conn.cursor()
tables = ['vendas', 'cobrancas', 'consultas', 'procedimentos']
for t in tables:
    try:
        c.execute(f"ALTER TABLE {t} ADD COLUMN user_id INTEGER DEFAULT 1 REFERENCES users(id)")
        print(f"Added user_id to {t}")
    except Exception as e:
        print(f"Could not add user_id to {t}: {e}")
conn.commit()
conn.close()
print("Done")
