from app import app, db, User, Vendas
import os
import sys

# Disable print buffering
sys.stdout.reconfigure(line_buffering=True)

def check_db(db_name):
    print(f"\n--- Checking {db_name} ---", flush=True)
    if not os.path.exists(db_name):
        print(f"File {db_name} does not exist.", flush=True)
        return

    # Temporarily switch DB URI
    original_uri = app.config['SQLALCHEMY_DATABASE_URI']
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.abspath(db_name)}'
    
    with app.app_context():
        try:
            users = User.query.all()
            print(f"Users: {len(users)}", flush=True)
            for u in users:
                vendas_count = Vendas.query.filter_by(user_id=u.id).count()
                print(f"  - User: {u.full_name}, Vendas: {vendas_count}", flush=True)
        except Exception as e:
            print(f"Error reading DB: {e}", flush=True)
            
    # Restore
    app.config['SQLALCHEMY_DATABASE_URI'] = original_uri

if __name__ == "__main__":
    check_db('comissoes_prod.db')
    check_db('comissoes_v1_restaurado.db')
