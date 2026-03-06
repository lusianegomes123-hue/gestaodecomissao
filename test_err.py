import traceback
from app import app, db, Vendas
from sqlalchemy import func
import datetime, calendar

try:
    with app.app_context():
        _, last_day = calendar.monthrange(2026, 3)
        inicio = datetime.date(2026, 3, 1)
        fim = datetime.date(2026, 3, last_day)
        print(db.session.query(func.sum(Vendas.comissao_calculada)).filter_by(user_id=1).filter(Vendas.data_venda >= inicio, Vendas.data_venda <= fim).scalar())
except Exception as e:
    traceback.print_exc()
