import sqlite3
import sqlalchemy as sa
from sqlalchemy.orm import sessionmaker
import urllib.parse
from datetime import datetime

# Supabase Connection
supa_url = 'postgresql://postgres:Lu22291606%40@db.lflsupfhnvcauusoenkl.supabase.co:5432/postgres'
engine = sa.create_engine(supa_url)

# Test connection and create tables
try:
    with engine.connect() as conn:
        print("Connected to Supabase successfully.")
except Exception as e:
    print("Failed to connect to Supabase:", e)
    exit(1)

# Import models to create tables
try:
    from models import db, User, Vendas, Cobrancas, Consultas, Procedimentos
    from flask import Flask
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = supa_url
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)
    with app.app_context():
        print("Creating tables in Supabase...")
        db.create_all()
        print("Tables created.")
        
        # Now, connect to the local SQLite DB and migrate data
        print("Connecting to local SQLite DB to fetch data...")
        import sqlite3
        db_path = 'comissoes_prod.db'
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        
        # Prepare Supabase session
        SupabaseSession = sessionmaker(bind=engine)
        supa_session = SupabaseSession()
        
        print("Migrating Users...")
        users = c.execute("SELECT id, username, full_name, password_hash FROM users").fetchall()
        for u in users:
            uid, uname, fname, phash = u[0], u[1], u[2], u[3]
            existing_user = supa_session.query(User).filter_by(id=uid).first()
            if not existing_user:
                new_user = User(id=uid, username=uname, full_name=fname, password_hash=phash)
                supa_session.add(new_user)
        supa_session.commit()
        
        print("Migrating Vendas...")
        vendas = c.execute("SELECT id, user_id, nome_cliente, data_venda, tipo_venda, valor_total, comissao_calculada FROM vendas").fetchall()
        for v in vendas:
            existing = supa_session.query(Vendas).filter_by(id=v[0]).first()
            if not existing:
                new_venda = Vendas(id=v[0], user_id=v[1], nome_cliente=v[2], data_venda=v[3], tipo_venda=v[4], valor_total=v[5], comissao_calculada=v[6])
                supa_session.add(new_venda)
        supa_session.commit()
        
        print("Migrating Cobrancas...")
        cobrancas = c.execute("SELECT id, user_id, nome_cliente, data_negociacao, valor_negociado, comissao_calculada FROM cobrancas").fetchall()
        for cob in cobrancas:
            existing = supa_session.query(Cobrancas).filter_by(id=cob[0]).first()
            if not existing:
                new_cob = Cobrancas(id=cob[0], user_id=cob[1], nome_cliente=cob[2], data_negociacao=cob[3], valor_negociado=cob[4], comissao_calculada=cob[5])
                supa_session.add(new_cob)
        supa_session.commit()
        
        print("Migrating Consultas...")
        consultas = c.execute("SELECT id, user_id, nome_cliente, data_consulta, status, comissao_calculada FROM consultas").fetchall()
        for c_row in consultas:
            existing = supa_session.query(Consultas).filter_by(id=c_row[0]).first()
            if not existing:
                new_cons = Consultas(id=c_row[0], user_id=c_row[1], nome_cliente=c_row[2], data_consulta=c_row[3], status=c_row[4], comissao_calculada=c_row[5])
                supa_session.add(new_cons)
        supa_session.commit()
        
        print("Migrating Procedimentos...")
        procedimentos = c.execute("SELECT id, user_id, nome_cliente, data_procedimento, tipo_procedimento, comissao_calculada FROM procedimentos").fetchall()
        for p in procedimentos:
            existing = supa_session.query(Procedimentos).filter_by(id=p[0]).first()
            if not existing:
                new_proc = Procedimentos(id=p[0], user_id=p[1], nome_cliente=p[2], data_procedimento=p[3], tipo_procedimento=p[4], comissao_calculada=p[5])
                supa_session.add(new_proc)
        supa_session.commit()
        
        print("Migration completed successfully!")
        
except Exception as e:
    print("Error during migration:", e)

