import sqlite3
import os

db_path = 'comissoes_prod.db'

def add_column(cursor, table, column, current_date):
    try:
        cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} DATE")
        print(f"Added column {column} to {table}")
        # Update existing records to have a default date (today or stored timestamp if available)
        cursor.execute(f"UPDATE {table} SET {column} = '{current_date}' WHERE {column} IS NULL")
    except sqlite3.OperationalError as e:
        if 'duplicate column' in str(e):
            print(f"Column {column} already exists in {table}")
        else:
            print(f"Error adding {column} to {table}: {e}")

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

from datetime import datetime
today = datetime.now().strftime('%Y-%m-%d')

# Add columns if they don't exist
add_column(cursor, 'vendas', 'data_venda', today)
add_column(cursor, 'cobrancas', 'data_negociacao', today)
add_column(cursor, 'consultas', 'data_consulta', today)
add_column(cursor, 'procedimentos', 'data_procedimento', today)

conn.commit()
conn.close()
print("Migration completed.")
