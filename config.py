import os

class Config:
    basedir = os.path.abspath(os.path.dirname(__file__))
    # Configuração do Banco de Dados: Forçando uso do SQLite Local devido ao vencimento do PostgreSQL no Render
    database_url = os.getenv('DATABASE_URL')
    if database_url and database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)
    
    # ATENÇÃO: Override de resgate de emergência para usar o DB que foi upado no github
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(basedir, 'comissoes_prod.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = os.getenv('SECRET_KEY', 'chave_secreta_padrao_desenvolvimento')
