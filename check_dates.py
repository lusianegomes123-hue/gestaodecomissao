from app import app, db, Vendas, Cobrancas, Consultas, Procedimentos
from sqlalchemy import text

def check_dates():
    with app.app_context():
        print("Checking for NULL dates or bad formats...")
        
        tables = [
            ('vendas', Vendas, 'data_venda'),
            ('cobrancas', Cobrancas, 'data_negociacao'),
            ('consultas', Consultas, 'data_consulta'),
            ('procedimentos', Procedimentos, 'data_procedimento')
        ]
        
        for table_name, model, col_name in tables:
            # Check for NULLs
            nulls = model.query.filter(getattr(model, col_name) == None).count()
            print(f"[{table_name}] NULL {col_name}: {nulls}")
            
            # Check for generic raw values to see format
            conn = db.session.connection()
            result = conn.execute(text(f"SELECT {col_name} FROM {table_name} LIMIT 5"))
            print(f"[{table_name}] Sample dates:")
            for row in result:
                print(f"  - {row[0]}")

if __name__ == "__main__":
    check_dates()
