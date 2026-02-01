from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from sqlalchemy import func, extract
from config import Config
from models import db, User, Vendas, Cobrancas, Consultas, Procedimentos
from datetime import datetime
from collections import defaultdict

app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.before_request
def create_tables():
    app.before_request_funcs[None].remove(create_tables)
    db.create_all()

# --- Rotas de Autenticação ---

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        full_name = request.form.get('full_name').strip()
        password = request.form.get('password')
        
        # Busca pelo Full Name (mapeado para username no DB)
        user = User.query.filter_by(username=full_name).first()
        
        if user and user.check_password(password):
            login_user(user, remember=True) # ATENÇÃO: remember=True mantém logado
            return redirect(url_for('home'))
            
        flash('Nome ou senha inválidos. Verifique se digitou o Nome Completo igual ao cadastro.')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        full_name = request.form.get('full_name').strip()
        password = request.form.get('password')
        
        if not full_name:
            flash('Por favor, digite seu Nome Completo.')
            return redirect(url_for('register'))

        # Verifica duplicidade
        if User.query.filter_by(username=full_name).first():
            flash('Este Nome já possui cadastro. Tente fazer login.')
            return redirect(url_for('register'))
            
        # Cria usuario (username = full_name)
        new_user = User(username=full_name, full_name=full_name)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()
        
        flash(f'Cadastro realizado para "{full_name}"! Agora faça login.')
        return redirect(url_for('login'))
        
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# --- Rotas da Aplicação ---

@app.route('/')
@login_required
def home():
    agora = datetime.now()
    return render_template('home.html', agora=agora)

@app.route('/geral')
@login_required
def relatorios():
    # 1. Total Geral Acumulado
    tv = db.session.query(func.sum(Vendas.comissao_calculada)).filter_by(user_id=current_user.id).scalar() or 0
    tcb = db.session.query(func.sum(Cobrancas.comissao_calculada)).filter_by(user_id=current_user.id).scalar() or 0
    tcs = db.session.query(func.sum(Consultas.comissao_calculada)).filter_by(user_id=current_user.id).scalar() or 0
    tp = db.session.query(func.sum(Procedimentos.comissao_calculada)).filter_by(user_id=current_user.id).scalar() or 0
    total_acumulado_geral = tv + tcb + tcs + tp

    # 2. Agrupamento por Mês
    historico = defaultdict(float)
    def agregar(model, date_col):
        # Solução compatível com SQLite e PostgreSQL (evita func.strftime)
        results = db.session.query(
            extract('year', date_col).label('ano'),
            extract('month', date_col).label('mes'),
            func.sum(model.comissao_calculada)
        ).filter_by(user_id=current_user.id).group_by(extract('year', date_col), extract('month', date_col)).all()
        
        for ano, mes, valor in results:
            if ano and mes:
                mes_ano = f"{int(ano)}-{int(mes):02d}"
                historico[mes_ano] += float(valor)

    agregar(Vendas, Vendas.data_venda)
    agregar(Cobrancas, Cobrancas.data_negociacao)
    agregar(Consultas, Consultas.data_consulta)
    agregar(Procedimentos, Procedimentos.data_procedimento)

    historico_ordenado = sorted(historico.items(), key=lambda x: x[0], reverse=True)
    
    lista_historico = []
    meses_nomes = {1:'Janeiro', 2:'Fevereiro', 3:'Março', 4:'Abril', 5:'Maio', 6:'Junho', 7:'Julho', 8:'Agosto', 9:'Setembro', 10:'Outubro', 11:'Novembro', 12:'Dezembro'}
    
    for ym, valor in historico_ordenado:
        ano, mes = map(int, ym.split('-'))
        lista_historico.append({
            'label': f"{meses_nomes[mes]}/{ano}",
            'total': valor,
            'mes': mes, 'ano': ano
        })

    # Filtro
    mes_filtro = request.args.get('mes', type=int)
    ano_filtro = request.args.get('ano', type=int)
    if not mes_filtro or not ano_filtro:
        agora = datetime.now()
        mes_filtro = agora.month
        ano_filtro = agora.year
    
    detalhes = {
        'vendas': Vendas.query.filter_by(user_id=current_user.id).filter(extract('month', Vendas.data_venda) == mes_filtro, extract('year', Vendas.data_venda) == ano_filtro).all(),
        'cobrancas': Cobrancas.query.filter_by(user_id=current_user.id).filter(extract('month', Cobrancas.data_negociacao) == mes_filtro, extract('year', Cobrancas.data_negociacao) == ano_filtro).all(),
        'consultas': Consultas.query.filter_by(user_id=current_user.id).filter(extract('month', Consultas.data_consulta) == mes_filtro, extract('year', Consultas.data_consulta) == ano_filtro).all(),
        'procedimentos': Procedimentos.query.filter_by(user_id=current_user.id).filter(extract('month', Procedimentos.data_procedimento) == mes_filtro, extract('year', Procedimentos.data_procedimento) == ano_filtro).all(),
    }
    
    total_mes_selecionado = historico.get(f"{ano_filtro:04d}-{mes_filtro:02d}", 0.0)

    return render_template('relatorios.html', 
                           total_acumulado_geral=total_acumulado_geral,
                           lista_historico=lista_historico,
                           detalhes=detalhes,
                           filtro={'mes': mes_filtro, 'ano': ano_filtro, 'total': total_mes_selecionado})

@app.route('/vendas', methods=['GET', 'POST'])
@login_required
def vendas():
    if request.method == 'POST':
        tipo = request.form.get('tipo_venda')
        valor = float(request.form.get('valor_total'))
        cliente = request.form.get('nome_cliente')
        comissao = 0
        if tipo == 'Talão': comissao = valor * 0.50
        elif tipo == 'Cartão': comissao = valor * 0.05
        elif tipo == 'PIX': comissao = (valor / 12) * 0.20
        nova = Vendas(user_id=current_user.id, nome_cliente=cliente, tipo_venda=tipo, valor_total=valor, comissao_calculada=comissao)
        db.session.add(nova)
        db.session.commit()
        return redirect(url_for('vendas'))
    lista = Vendas.query.filter_by(user_id=current_user.id).order_by(Vendas.data_venda.desc()).all()
    total = db.session.query(func.sum(Vendas.comissao_calculada)).filter_by(user_id=current_user.id).scalar() or 0
    return render_template('vendas.html', vendas=lista, total_comissao=total)

@app.route('/cobrancas', methods=['GET', 'POST'])
@login_required
def cobrancas():
    if request.method == 'POST':
        valor = float(request.form.get('valor_negociado'))
        cliente = request.form.get('nome_cliente')
        comissao = valor * 0.03
        nova = Cobrancas(user_id=current_user.id, nome_cliente=cliente, valor_negociado=valor, comissao_calculada=comissao)
        db.session.add(nova)
        db.session.commit()
        return redirect(url_for('cobrancas'))
    lista = Cobrancas.query.filter_by(user_id=current_user.id).order_by(Cobrancas.data_negociacao.desc()).all()
    total = db.session.query(func.sum(Cobrancas.comissao_calculada)).filter_by(user_id=current_user.id).scalar() or 0
    return render_template('cobrancas.html', cobrancas=lista, total_comissao=total)

@app.route('/consultas', methods=['GET', 'POST'])
@login_required
def consultas():
    if request.method == 'POST':
        cliente = request.form.get('nome_cliente')
        nova = Consultas(user_id=current_user.id, nome_cliente=cliente, status='Realizada', comissao_calculada=20.00)
        db.session.add(nova)
        db.session.commit()
        return redirect(url_for('consultas'))
    lista = Consultas.query.filter_by(user_id=current_user.id).order_by(Consultas.data_consulta.desc()).all()
    total = db.session.query(func.sum(Consultas.comissao_calculada)).filter_by(user_id=current_user.id).scalar() or 0
    return render_template('consultas.html', consultas=lista, total_comissao=total)

@app.route('/procedimentos', methods=['GET', 'POST'])
@login_required
def procedimentos():
    if request.method == 'POST':
        tipo = request.form.get('tipo_procedimento')
        cliente = request.form.get('nome_cliente')
        nova = Procedimentos(user_id=current_user.id, nome_cliente=cliente, tipo_procedimento=tipo, comissao_calculada=200.00)
        db.session.add(nova)
        db.session.commit()
        return redirect(url_for('procedimentos'))
    lista = Procedimentos.query.filter_by(user_id=current_user.id).order_by(Procedimentos.data_procedimento.desc()).all()
    total = db.session.query(func.sum(Procedimentos.comissao_calculada)).filter_by(user_id=current_user.id).scalar() or 0
    return render_template('procedimentos.html', procedimentos=lista, total_comissao=total)

@app.route('/admin/users')
@login_required
def admin_users():
    # Verificação de segurança hardcoded para o admin
    if current_user.full_name.strip().lower() != "lusiane gomes simão":
        flash('Acesso negado. Esta área é restrita.')
        return redirect(url_for('home'))
    
    users = User.query.order_by(User.full_name).all()
    return render_template('admin_users.html', users=users)

from pyngrok import ngrok

if __name__ == '__main__':
    # Configuração de Porta
    port = 5003
    
    # Tenta abrir o túnel Ngrok (Link Público)
    try:
        # Garante que o Ngrok use o protocolo HTTP (que gera https gratuito)
        public_url = ngrok.connect(port, "http").public_url
        print("\n" + "="*60)
        print(f" 🚀 ACESSE SEU APP AQUI (EXTERNO): {public_url}")
        print("="*60 + "\n")
    except Exception as e:
        print(f"\n[!] Aviso: Não foi possível gerar Link Público Ngrok. Erro: {e}")
        print("    (Verifique sua conexão de internet)\n")

    print(f" 🏠 ACESSE SEU APP AQUI (LOCAL):   http://127.0.0.1:{port}\n")

    # Configuração GARANTIDA de Processo Único (Sem auto-open, sem reloader)
    app.run(debug=False, use_reloader=False, host='0.0.0.0', port=port)
