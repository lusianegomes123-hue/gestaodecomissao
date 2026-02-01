import os

class Config:
    basedir = os.path.abspath(os.path.dirname(__file__))
    # BANCO DEFINITIVO: Não mudará de nome
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(basedir, 'comissoes_prod.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = os.getenv('SECRET_KEY', 'chave_secreta_padrao_desenvolvimento')
