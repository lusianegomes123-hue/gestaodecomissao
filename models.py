from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False) # Será o Full Name
    full_name = db.Column(db.String(200), nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Vendas(db.Model):
    __tablename__ = 'vendas'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    nome_cliente = db.Column(db.String(150), nullable=False)
    data_venda = db.Column(db.Date, nullable=False, default=datetime.utcnow)
    tipo_venda = db.Column(db.String(50), nullable=False)
    valor_total = db.Column(db.Numeric(10, 2), nullable=False)
    comissao_calculada = db.Column(db.Numeric(10, 2), nullable=False)

class Cobrancas(db.Model):
    __tablename__ = 'cobrancas'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    nome_cliente = db.Column(db.String(150), nullable=False)
    data_negociacao = db.Column(db.Date, nullable=False, default=datetime.utcnow)
    valor_negociado = db.Column(db.Numeric(10, 2), nullable=False)
    comissao_calculada = db.Column(db.Numeric(10, 2), nullable=False)

class Consultas(db.Model):
    __tablename__ = 'consultas'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    nome_cliente = db.Column(db.String(150), nullable=False)
    data_consulta = db.Column(db.Date, nullable=False, default=datetime.utcnow)
    status = db.Column(db.String(50), default='Realizada')
    comissao_calculada = db.Column(db.Numeric(10, 2), nullable=False)

class Procedimentos(db.Model):
    __tablename__ = 'procedimentos'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    nome_cliente = db.Column(db.String(150), nullable=False)
    data_procedimento = db.Column(db.Date, nullable=False, default=datetime.utcnow)
    tipo_procedimento = db.Column(db.String(100), default='Cirurgia')
    comissao_calculada = db.Column(db.Numeric(10, 2), nullable=False)
