import sqlite3
import os

db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'comissoes_prod.db')
print(f"Fixing db at {db_path}")
conn = sqlite3.connect(db_path)
c = conn.cursor()
tables = ['vendas', 'cobrancas', 'consultas', 'procedimentos']
for t in tables:
    try:
        c.execute(f"DROP TABLE IF EXISTS {t}")
        print(f"Dropped {t}")
    except Exception as e:
        print(f"Could not drop {t}: {e}")
conn.commit()
conn.close()

from app import app, db
with app.app_context():
    db.create_all()
print("Tables recreated successfully with correct schema.")
