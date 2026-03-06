import sys, traceback
from app import app, db, User

try:
    from app import relatorios
    with app.test_request_context('/geral'):
        u = User.query.first()
        from flask_login import login_user
        login_user(u)
        print("Starting relatorios call...")
        res = relatorios()
        print("Relatorios call succeeded!")
except Exception as e:
    print("Caught Exception in relatorios():")
    traceback.print_exc(file=sys.stdout)
