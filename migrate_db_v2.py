import sqlite3
import os

# Use absolute path to avoid confusion
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'comissoes_prod.db')

print(f"Connecting to DB at: {DB_PATH}")

def add_column(cursor, table, column, current_date):
    try:
        # Check if column exists first
        cursor.execute(f"PRAGMA table_info({table})")
        columns = [info[1] for info in cursor.fetchall()]
        if column in columns:
             print(f"Column {column} already exists in {table}")
             return

        cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} DATE")
        print(f"Added column {column} to {table}")
        
        # Update existing records
        cursor.execute(f"UPDATE {table} SET {column} = '{current_date}' WHERE {column} IS NULL")
        print(f"Updated records in {table}")
        
    except Exception as e:
        print(f"Error acting on {table}: {e}")

if not os.path.exists(DB_PATH):
    print("DB FILE NOT FOUND!")
    exit(1)

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

from datetime import datetime
today = datetime.now().strftime('%Y-%m-%d')

add_column(cursor, 'vendas', 'data_venda', today)
add_column(cursor, 'cobrancas', 'data_negociacao', today)
add_column(cursor, 'consultas', 'data_consulta', today)
add_column(cursor, 'procedimentos', 'data_procedimento', today)

conn.commit()
conn.close()
print("Migration completed successfully.")
