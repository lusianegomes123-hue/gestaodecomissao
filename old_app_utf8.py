from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from sqlalchemy import func, extract
from config import Config
from models import db, User, Vendas, Cobrancas, Consultas, Procedimentos
from datetime import datetime
from collections import defaultdict
import calendar

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

# --- Rotas de Autentica├º├úo ---

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        full_name = request.form.get('full_name').strip()
        password = request.form.get('password')
        
        # Busca pelo Full Name (mapeado para username no DB)
        user = User.query.filter_by(username=full_name).first()
        
        if user and user.check_password(password):
            login_user(user, remember=True) # ATEN├ç├âO: remember=True mant├®m logado
            return redirect(url_for('home'))
            
        flash('Nome ou senha inv├ílidos. Verifique se digitou o Nome Completo igual ao cadastro.')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        full_name = request.form.get('full_name').strip()
        password = request.form.get('password')
        
        if not full_name:
            flash('Por favor, digite seu Nome Completo.')
            return redirect(url_for('register'))

        # Verifica duplicidade (Ignorando Mai├║sculas/Min├║sculas)
        existing_user = User.query.filter(func.lower(User.username) == full_name.lower()).first()
        if existing_user:
            flash('Este Nome j├í possui cadastro. Tente fazer login ou recuperar senha.')
            return redirect(url_for('register'))
            
        # Cria usuario (username = full_name)
        new_user = User(username=full_name, full_name=full_name)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()
        
        flash(f'Cadastro realizado para "{full_name}"! Agora fa├ºa login.')
        return redirect(url_for('login'))
        
    return render_template('register.html')

@app.route('/recover_password', methods=['GET', 'POST'])
def recover_password():
    if request.method == 'POST':
        full_name = request.form.get('full_name').strip()
        email = request.form.get('email', '').strip().lower()
        step = request.form.get('step')
        new_password = request.form.get('new_password')

        # 1. Busca Usu├írio (Case Insensitive)
        user = User.query.filter(func.lower(User.username) == full_name.lower()).first()

        if not user:
            flash('Usu├írio n├úo encontrado.')
            return render_template('recover_password.html', valid_user=None)

        # 2. Valida├º├úo L├│gica (Parte do nome no email)
        # Ex: Nome "Lusiane Gomes", Email "lusiane@..." -> Match
        # Ex: "123" no email n├úo conta, vamos exigir pelo menos 3 letras para evitar falso positivo f├ícil
        name_parts = [p.lower() for p in user.full_name.split() if len(p) > 2]
        
        # Regra: Pelo menos uma parte do nome (com >2 letras) deve estar no email
        match = any(part in email for part in name_parts)
        
        if not match:
            flash('O e-mail informado n├úo corresponde aos crit├®rios de seguran├ºa do nome cadastrado.')
            return render_template('recover_password.html', valid_user=None)

        # 3. Se for etapa de Reset
        if step == 'reset' and new_password:
            user.set_password(new_password)
            db.session.commit()
            flash('Senha redefinida com sucesso! Fa├ºa login.')
            return redirect(url_for('login'))

        # 4. Se passou valida├º├úo mas n├úo ├® reset ainda, mostra formul├írio de senha
        return render_template('recover_password.html', valid_user=user, email_attempt=email)

    return render_template('recover_password.html', valid_user=None)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# --- Rotas da Aplica├º├úo ---

@app.route('/')
@login_required
def home():
    agora = datetime.now()
    mes_atual = agora.month
    ano_atual = agora.year
    
    # Datas de in├¡cio e fim do m├¬s
    _, last_day = calendar.monthrange(ano_atual, mes_atual)
    inicio_mes = datetime(ano_atual, mes_atual, 1).date()
    fim_mes = datetime(ano_atual, mes_atual, last_day).date()

    # Calcular Total do M├¬s Atual
    t_vendas = db.session.query(func.sum(Vendas.comissao_calculada)).filter_by(user_id=current_user.id).filter(Vendas.data_venda >= inicio_mes, Vendas.data_venda <= fim_mes).scalar() or 0
    t_cobrancas = db.session.query(func.sum(Cobrancas.comissao_calculada)).filter_by(user_id=current_user.id).filter(Cobrancas.data_negociacao >= inicio_mes, Cobrancas.data_negociacao <= fim_mes).scalar() or 0
    t_consultas = db.session.query(func.sum(Consultas.comissao_calculada)).filter_by(user_id=current_user.id).filter(Consultas.data_consulta >= inicio_mes, Consultas.data_consulta <= fim_mes).scalar() or 0
    t_procedimentos = db.session.query(func.sum(Procedimentos.comissao_calculada)).filter_by(user_id=current_user.id).filter(Procedimentos.data_procedimento >= inicio_mes, Procedimentos.data_procedimento <= fim_mes).scalar() or 0
    
    total_mes_atual = t_vendas + t_cobrancas + t_consultas + t_procedimentos

    return render_template('home.html', agora=agora, total_mes_atual=total_mes_atual)

@app.route('/geral')
@login_required
def relatorios():
    # 1. Total Geral Acumulado
    tv = db.session.query(func.sum(Vendas.comissao_calculada)).filter_by(user_id=current_user.id).scalar() or 0
    tcb = db.session.query(func.sum(Cobrancas.comissao_calculada)).filter_by(user_id=current_user.id).scalar() or 0
    tcs = db.session.query(func.sum(Consultas.comissao_calculada)).filter_by(user_id=current_user.id).scalar() or 0
    tp = db.session.query(func.sum(Procedimentos.comissao_calculada)).filter_by(user_id=current_user.id).scalar() or 0
    total_acumulado_geral = tv + tcb + tcs + tp

    # Totais Brutos (Volume Transacionado) - Onde aplic├ível
    tv_bruto = db.session.query(func.sum(Vendas.valor_total)).filter_by(user_id=current_user.id).scalar() or 0
    tcb_bruto = db.session.query(func.sum(Cobrancas.valor_negociado)).filter_by(user_id=current_user.id).scalar() or 0

    # Contagens Gerais
    qv = Vendas.query.filter_by(user_id=current_user.id).count()
    qcb = Cobrancas.query.filter_by(user_id=current_user.id).count()
    qcs = Consultas.query.filter_by(user_id=current_user.id).count()
    qp = Procedimentos.query.filter_by(user_id=current_user.id).count()
    total_itens_geral = qv + qcb + qcs + qp
    
    resumo_geral = {
        'vendas': {'qtd': qv, 'val': tv, 'bruto': tv_bruto},
        'cobrancas': {'qtd': qcb, 'val': tcb, 'bruto': tcb_bruto},
        'consultas': {'qtd': qcs, 'val': tcs, 'bruto': 0},
        'procedimentos': {'qtd': qp, 'val': tp, 'bruto': 0}
    }

    # 2. Agrupamento por M├¬s
    historico = defaultdict(float)
    def agregar(model, date_col):
        # Compatibilidade segura com SQLite (via strftime '%Y-%m') e Postgres via func.to_char ou alternativo se falhar
        engine_name = db.session.bind.dialect.name
        if engine_name == 'sqlite':
            results = db.session.query(
                func.strftime('%Y-%m', date_col).label('mes_ano'),
                func.sum(model.comissao_calculada)
            ).filter_by(user_id=current_user.id).group_by(func.strftime('%Y-%m', date_col)).all()
            for ma, valor in results:
                if ma:
                    historico[ma] += float(valor)
        else: # postgresql
            results = db.session.query(
                func.to_char(date_col, 'YYYY-MM').label('mes_ano'),
                func.sum(model.comissao_calculada)
            ).filter_by(user_id=current_user.id).group_by(func.to_char(date_col, 'YYYY-MM')).all()
            for ma, valor in results:
                if ma:
                    historico[ma] += float(valor)

    agregar(Vendas, Vendas.data_venda)
    agregar(Cobrancas, Cobrancas.data_negociacao)
    agregar(Consultas, Consultas.data_consulta)
    agregar(Procedimentos, Procedimentos.data_procedimento)

    historico_ordenado = sorted(historico.items(), key=lambda x: x[0], reverse=True)
    
    lista_historico = []
    meses_nomes = {1:'Janeiro', 2:'Fevereiro', 3:'Mar├ºo', 4:'Abril', 5:'Maio', 6:'Junho', 7:'Julho', 8:'Agosto', 9:'Setembro', 10:'Outubro', 11:'Novembro', 12:'Dezembro'}
    
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
    
    _, last_day = calendar.monthrange(ano_filtro, mes_filtro)
    inicio_filtro = datetime(ano_filtro, mes_filtro, 1).date()
    fim_filtro = datetime(ano_filtro, mes_filtro, last_day).date()

    detalhes = {
        'vendas': Vendas.query.filter_by(user_id=current_user.id).filter(Vendas.data_venda >= inicio_filtro, Vendas.data_venda <= fim_filtro).all(),
        'cobrancas': Cobrancas.query.filter_by(user_id=current_user.id).filter(Cobrancas.data_negociacao >= inicio_filtro, Cobrancas.data_negociacao <= fim_filtro).all(),
        'consultas': Consultas.query.filter_by(user_id=current_user.id).filter(Consultas.data_consulta >= inicio_filtro, Consultas.data_consulta <= fim_filtro).all(),
        'procedimentos': Procedimentos.query.filter_by(user_id=current_user.id).filter(Procedimentos.data_procedimento >= inicio_filtro, Procedimentos.data_procedimento <= fim_filtro).all(),
    }
    
    total_mes_selecionado = historico.get(f"{ano_filtro:04d}-{mes_filtro:02d}", 0.0)

    return render_template('relatorios.html', 
                           total_acumulado_geral=total_acumulado_geral,
                           total_itens_geral=total_itens_geral,
                           resumo_geral=resumo_geral,
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
        data_str = request.form.get('data_venda')
        
        data_venda = datetime.strptime(data_str, '%Y-%m-%d').date() if data_str else datetime.utcnow().date()

        comissao = 0
        if tipo == 'Tal├úo': comissao = valor * 0.50
        elif tipo == 'Cart├úo': comissao = valor * 0.05
        elif tipo == 'PIX': comissao = (valor / 12) * 0.20
        
        nova = Vendas(user_id=current_user.id, nome_cliente=cliente, tipo_venda=tipo, valor_total=valor, comissao_calculada=comissao, data_venda=data_venda)
        db.session.add(nova)
        db.session.commit()
        return redirect(url_for('vendas'))
    
    lista = Vendas.query.filter_by(user_id=current_user.id).order_by(Vendas.data_venda.desc()).all()
    total_val = db.session.query(func.sum(Vendas.comissao_calculada)).filter_by(user_id=current_user.id).scalar() or 0
    total_bruto = db.session.query(func.sum(Vendas.valor_total)).filter_by(user_id=current_user.id).scalar() or 0
    total_qtd = Vendas.query.filter_by(user_id=current_user.id).count()
    
    return render_template('vendas.html', vendas=lista, total_comissao=total_val, total_qtd=total_qtd, total_bruto=total_bruto)

@app.route('/vendas/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_venda(id):
    venda = Vendas.query.get_or_404(id)
    if venda.user_id != current_user.id:
        flash('Acesso negado.')
        return redirect(url_for('vendas'))

    if request.method == 'POST':
        venda.nome_cliente = request.form.get('nome_cliente')
        venda.tipo_venda = request.form.get('tipo_venda')
        venda.valor_total = float(request.form.get('valor_total'))
        data_str = request.form.get('data_venda')
        if data_str:
            venda.data_venda = datetime.strptime(data_str, '%Y-%m-%d').date()

        # Recalcular comiss├úo
        if venda.tipo_venda == 'Tal├úo': venda.comissao_calculada = venda.valor_total * 0.50
        elif venda.tipo_venda == 'Cart├úo': venda.comissao_calculada = venda.valor_total * 0.05
        elif venda.tipo_venda == 'PIX': venda.comissao_calculada = (venda.valor_total / 12) * 0.20
        
        db.session.commit()
        flash('Venda atualizada com sucesso!')
        return redirect(url_for('vendas'))
    
    return render_template('edit_venda.html', venda=venda)

@app.route('/vendas/delete/<int:id>')
@login_required
def delete_venda(id):
    venda = Vendas.query.get_or_404(id)
    if venda.user_id != current_user.id:
        flash('Acesso negado.')
        return redirect(url_for('vendas'))
    
    db.session.delete(venda)
    db.session.commit()
    flash('Venda exclu├¡da com sucesso!')
    return redirect(url_for('vendas'))

@app.route('/cobrancas', methods=['GET', 'POST'])
@login_required
def cobrancas():
    if request.method == 'POST':
        valor = float(request.form.get('valor_negociado'))
        cliente = request.form.get('nome_cliente')
        data_str = request.form.get('data_negociacao')
        
        data_negoc = datetime.strptime(data_str, '%Y-%m-%d').date() if data_str else datetime.utcnow().date()

        comissao = valor * 0.03
        nova = Cobrancas(user_id=current_user.id, nome_cliente=cliente, valor_negociado=valor, comissao_calculada=comissao, data_negociacao=data_negoc)
        db.session.add(nova)
        db.session.commit()
        return redirect(url_for('cobrancas'))
    
    lista = Cobrancas.query.filter_by(user_id=current_user.id).order_by(Cobrancas.data_negociacao.desc()).all()
    total_val = db.session.query(func.sum(Cobrancas.comissao_calculada)).filter_by(user_id=current_user.id).scalar() or 0
    total_bruto = db.session.query(func.sum(Cobrancas.valor_negociado)).filter_by(user_id=current_user.id).scalar() or 0
    total_qtd = Cobrancas.query.filter_by(user_id=current_user.id).count()

    return render_template('cobrancas.html', cobrancas=lista, total_comissao=total_val, total_qtd=total_qtd, total_bruto=total_bruto)

@app.route('/cobrancas/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_cobranca(id):
    item = Cobrancas.query.get_or_404(id)
    if item.user_id != current_user.id:
        flash('Acesso negado.')
        return redirect(url_for('cobrancas'))

    if request.method == 'POST':
        item.nome_cliente = request.form.get('nome_cliente')
        item.valor_negociado = float(request.form.get('valor_negociado'))
        data_str = request.form.get('data_negociacao')
        if data_str:
            item.data_negociacao = datetime.strptime(data_str, '%Y-%m-%d').date()

        # Recalcular
        item.comissao_calculada = item.valor_negociado * 0.03
        
        db.session.commit()
        flash('Cobran├ºa atualizada com sucesso!')
        return redirect(url_for('cobrancas'))
    
    return render_template('edit_cobranca.html', item=item)

@app.route('/cobrancas/delete/<int:id>')
@login_required
def delete_cobranca(id):
    item = Cobrancas.query.get_or_404(id)
    if item.user_id != current_user.id:
        flash('Acesso negado.')
        return redirect(url_for('cobrancas'))
    
    db.session.delete(item)
    db.session.commit()
    flash('Cobran├ºa exclu├¡da com sucesso!')
    return redirect(url_for('cobrancas'))

@app.route('/consultas', methods=['GET', 'POST'])
@login_required
def consultas():
    if request.method == 'POST':
        cliente = request.form.get('nome_cliente')
        data_str = request.form.get('data_consulta')
        
        data_cons = datetime.strptime(data_str, '%Y-%m-%d').date() if data_str else datetime.utcnow().date()

        nova = Consultas(user_id=current_user.id, nome_cliente=cliente, status='Realizada', comissao_calculada=20.00, data_consulta=data_cons)
        db.session.add(nova)
        db.session.commit()
        return redirect(url_for('consultas'))
    
    lista = Consultas.query.filter_by(user_id=current_user.id).order_by(Consultas.data_consulta.desc()).all()
    total_val = db.session.query(func.sum(Consultas.comissao_calculada)).filter_by(user_id=current_user.id).scalar() or 0
    total_qtd = Consultas.query.filter_by(user_id=current_user.id).count()

    return render_template('consultas.html', consultas=lista, total_comissao=total_val, total_qtd=total_qtd)

@app.route('/consultas/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_consulta(id):
    item = Consultas.query.get_or_404(id)
    if item.user_id != current_user.id:
        flash('Acesso negado.')
        return redirect(url_for('consultas'))

    if request.method == 'POST':
        item.nome_cliente = request.form.get('nome_cliente')
        data_str = request.form.get('data_consulta')
        if data_str:
            item.data_consulta = datetime.strptime(data_str, '%Y-%m-%d').date()

        # Comiss├úo fixa, n├úo precisa recalcular se n├úo mudar a regra
        
        db.session.commit()
        flash('Consulta atualizada com sucesso!')
        return redirect(url_for('consultas'))
    
    return render_template('edit_consulta.html', item=item)

@app.route('/consultas/delete/<int:id>')
@login_required
def delete_consulta(id):
    item = Consultas.query.get_or_404(id)
    if item.user_id != current_user.id:
        flash('Acesso negado.')
        return redirect(url_for('consultas'))
    
    db.session.delete(item)
    db.session.commit()
    flash('Consulta exclu├¡da com sucesso!')
    return redirect(url_for('consultas'))

@app.route('/procedimentos', methods=['GET', 'POST'])
@login_required
def procedimentos():
    if request.method == 'POST':
        tipo = request.form.get('tipo_procedimento')
        cliente = request.form.get('nome_cliente')
        data_str = request.form.get('data_procedimento')
        
        data_proc = datetime.strptime(data_str, '%Y-%m-%d').date() if data_str else datetime.utcnow().date()
        
        nova = Procedimentos(user_id=current_user.id, nome_cliente=cliente, tipo_procedimento=tipo, comissao_calculada=200.00, data_procedimento=data_proc)
        db.session.add(nova)
        db.session.commit()
        return redirect(url_for('procedimentos'))
    
    lista = Procedimentos.query.filter_by(user_id=current_user.id).order_by(Procedimentos.data_procedimento.desc()).all()
    total_val = db.session.query(func.sum(Procedimentos.comissao_calculada)).filter_by(user_id=current_user.id).scalar() or 0
    total_qtd = Procedimentos.query.filter_by(user_id=current_user.id).count()

    return render_template('procedimentos.html', procedimentos=lista, total_comissao=total_val, total_qtd=total_qtd)

@app.route('/procedimentos/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_procedimento(id):
    item = Procedimentos.query.get_or_404(id)
    if item.user_id != current_user.id:
        flash('Acesso negado.')
        return redirect(url_for('procedimentos'))

    if request.method == 'POST':
        item.nome_cliente = request.form.get('nome_cliente')
        item.tipo_procedimento = request.form.get('tipo_procedimento')
        data_str = request.form.get('data_procedimento')
        if data_str:
            item.data_procedimento = datetime.strptime(data_str, '%Y-%m-%d').date()

        # Comiss├úo fixa
        
        db.session.commit()
        flash('Procedimento atualizado com sucesso!')
        return redirect(url_for('procedimentos'))
    
    return render_template('edit_procedimento.html', item=item)

@app.route('/procedimentos/delete/<int:id>')
@login_required
def delete_procedimento(id):
    item = Procedimentos.query.get_or_404(id)
    if item.user_id != current_user.id:
        flash('Acesso negado.')
        return redirect(url_for('procedimentos'))
    
    db.session.delete(item)
    db.session.commit()
    flash('Procedimento exclu├¡do com sucesso!')
    return redirect(url_for('procedimentos'))

@app.route('/admin/users')
@login_required
def admin_users():
    # Verifica├º├úo de seguran├ºa hardcoded para o admin
    if current_user.full_name.strip().lower() != "lusiane gomes sim├úo":
        flash('Acesso negado. Esta ├írea ├® restrita.')
        return redirect(url_for('home'))
    
    users = User.query.order_by(User.full_name).all()
    return render_template('admin_users.html', users=users)

from pyngrok import ngrok

if __name__ == '__main__':
    # Configura├º├úo de Porta
    port = 5003
    
    # Tenta abrir o t├║nel Ngrok (Link P├║blico)
    # try:
    #     # Garante que o Ngrok use o protocolo HTTP (que gera https gratuito)
    #     public_url = ngrok.connect(port, "http").public_url
    #     print("\n" + "="*60)
    #     print(f" ­ƒÜÇ ACESSE SEU APP AQUI (EXTERNO): {public_url}")
    #     print("="*60 + "\n")
    # except Exception as e:
    #     print(f"\n[!] Aviso: N├úo foi poss├¡vel gerar Link P├║blico Ngrok. Erro: {e}")
    #     print("    (Verifique sua conex├úo de internet)\n")

    print(f" ­ƒÅá ACESSE SEU APP AQUI (LOCAL):   http://127.0.0.1:{port}\n")

    # Configura├º├úo GARANTIDA de Processo ├Ünico (Sem auto-open, sem reloader)
    app.run(debug=False, use_reloader=False, host='0.0.0.0', port=port)
