from app import app, db, User, Vendas, Cobrancas, Consultas, Procedimentos
import os

def check_db(db_name):
    print(f"\n--- Checking {db_name} ---")
    if not os.path.exists(db_name):
        print(f"File {db_name} does not exist.")
        return

    # Temporarily switch DB URI
    original_uri = app.config['SQLALCHEMY_DATABASE_URI']
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.abspath(db_name)}'
    
    with app.app_context():
        try:
            users = User.query.all()
            print(f"Users: {len(users)}")
            for u in users:
                print(f"  - ID: {u.id}, Name: {u.username}, FullName: {u.full_name}")
                vendas = Vendas.query.filter_by(user_id=u.id).count()
                print(f"    - Vendas: {vendas}")
                
            total_vendas = Vendas.query.count()
            print(f"Total Vendas in DB: {total_vendas}")
            
        except Exception as e:
            print(f"Error reading DB: {e}")
            
    # Restore
    app.config['SQLALCHEMY_DATABASE_URI'] = original_uri

check_db('comissoes_prod.db')
check_db('comissoes_v1_restaurado.db')
