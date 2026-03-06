import sqlalchemy as sa
supa_url = 'postgresql://postgres:Lu22291606%40@db.lflsupfhnvcauusoenkl.supabase.co:5432/postgres'
engine = sa.create_engine(supa_url)
tables = ['users', 'vendas', 'cobrancas', 'consultas', 'procedimentos']
if __name__ == "__main__":
    try:
        with engine.connect() as conn:
            for t in tables:
                max_id = conn.execute(sa.text(f"SELECT COALESCE(MAX(id), 0) FROM {t}")).scalar()
                print(f"{t} seq nextval should be: {max_id + 1}")
                conn.execute(sa.text(f"SELECT setval('{t}_id_seq', {max_id + 1}, false)"))
            conn.commit()
            print("Successfully updated all table sequences!")
    except Exception as e:
        print("Error updating sequences:", e)
