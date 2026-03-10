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

import traceback
from sqlalchemy.exc import OperationalError

@app.errorhandler(Exception)
def handle_exception(e):
    error_str = str(e)
    if "Name or service not known" in error_str or "could not translate host name" in error_str:
        return """
        <div style="font-family: sans-serif; text-align: center; margin-top: 50px;">
            <h2>Aguarde um instante! ☕</h2>
            <p>O Banco de Dados do sistema no Render.com entrou em 'modo de economia de energia' por inatividade.</p>
            <p>Ele já está sendo reativado automaticamente. Isso pode levar cerca de <b>1 a 2 minutos</b>.</p>
            <p>Por favor, atualize esta página (F5) repetidamente até carregar.</p>
        </div>
        """, 503
    return f"<pre>{traceback.format_exc()}</pre>", 500

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

        # Verifica duplicidade (Ignorando Maiúsculas/Minúsculas)
        existing_user = User.query.filter(func.lower(User.username) == full_name.lower()).first()
        if existing_user:
            flash('Este Nome já possui cadastro. Tente fazer login ou recuperar senha.')
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
    mes_atual = agora.month
    ano_atual = agora.year
    
    # Datas de início e fim do mês
    _, last_day = calendar.monthrange(ano_atual, mes_atual)
    inicio_mes = datetime(ano_atual, mes_atual, 1).date()
    fim_mes = datetime(ano_atual, mes_atual, last_day).date()

    # Calcular Total do Mês Atual
    t_vendas = db.session.query(func.sum(Vendas.comissao_calculada)).filter_by(user_id=current_user.id).filter(Vendas.data_venda >= inicio_mes, Vendas.data_venda <= fim_mes).scalar() or 0
    t_cobrancas = db.session.query(func.sum(Cobrancas.comissao_calculada)).filter_by(user_id=current_user.id).filter(Cobrancas.data_negociacao >= inicio_mes, Cobrancas.data_negociacao <= fim_mes).scalar() or 0
    t_consultas = db.session.query(func.sum(Consultas.comissao_calculada)).filter_by(user_id=current_user.id).filter(Consultas.data_consulta >= inicio_mes, Consultas.data_consulta <= fim_mes).scalar() or 0
    t_procedimentos = db.session.query(func.sum(Procedimentos.comissao_calculada)).filter_by(user_id=current_user.id).filter(Procedimentos.data_procedimento >= inicio_mes, Procedimentos.data_procedimento <= fim_mes).scalar() or 0
    
    total_mes_atual = t_vendas + t_cobrancas + t_consultas + t_procedimentos

    return render_template('home.html', agora=agora, total_mes_atual=total_mes_atual)

@app.route('/geral')
@login_required
def relatorios():
    def base_query(model):
        return model.query.filter_by(user_id=current_user.id)

    def get_sum(model, col):
        q = db.session.query(func.sum(col)).filter(model.user_id == current_user.id)
        return q.scalar() or 0

    # 1. Total Geral Acumulado
    tv = get_sum(Vendas, Vendas.comissao_calculada)
    tcb = get_sum(Cobrancas, Cobrancas.comissao_calculada)
    tcs = get_sum(Consultas, Consultas.comissao_calculada)
    tp = get_sum(Procedimentos, Procedimentos.comissao_calculada)
    total_acumulado_geral = tv + tcb + tcs + tp

    # Totais Brutos (Volume Transacionado) - Onde aplicável
    tv_bruto = get_sum(Vendas, Vendas.valor_total)
    tcb_bruto = get_sum(Cobrancas, Cobrancas.valor_negociado)

    # Contagens Gerais
    qv = base_query(Vendas).count()
    qcb = base_query(Cobrancas).count()
    qcs = base_query(Consultas).count()
    qp = base_query(Procedimentos).count()
    total_itens_geral = qv + qcb + qcs + qp
    
    resumo_geral = {
        'vendas': {'qtd': qv, 'val': tv, 'bruto': tv_bruto},
        'cobrancas': {'qtd': qcb, 'val': tcb, 'bruto': tcb_bruto},
        'consultas': {'qtd': qcs, 'val': tcs, 'bruto': 0},
        'procedimentos': {'qtd': qp, 'val': tp, 'bruto': 0}
    }

    historico = defaultdict(float)
    def agregar(model, date_col):
        q = db.session.query(date_col, model.comissao_calculada).filter(model.user_id == current_user.id)
        results = q.all()
        for dt, valor in results:
            if dt:
                historico[f"{dt.year:04d}-{dt.month:02d}"] += float(valor)

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

    # Mês Atual Sempre Real (Para os Cards Gigantes do Topo)
    agora = datetime.now()
    mes_atual = agora.month
    ano_atual = agora.year
    _, last_day_atual = calendar.monthrange(ano_atual, mes_atual)
    inicio_atual = datetime(ano_atual, mes_atual, 1).date()
    fim_atual = datetime(ano_atual, mes_atual, last_day_atual).date()

    # Filtro do Histórico (Para exibir as Tabelas Detalhadas Embaixo)
    mes_filtro = request.args.get('mes', type=int)
    ano_filtro = request.args.get('ano', type=int)
    filtro_explicito = bool(mes_filtro and ano_filtro)
    
    if filtro_explicito:
        _, last_day_filtro = calendar.monthrange(ano_filtro, mes_filtro)
        inicio_filtro = datetime(ano_filtro, mes_filtro, 1).date()
        fim_filtro = datetime(ano_filtro, mes_filtro, last_day_filtro).date()
        detalhes = {
            'vendas': base_query(Vendas).filter(Vendas.data_venda >= inicio_filtro, Vendas.data_venda <= fim_filtro).all(),
            'cobrancas': base_query(Cobrancas).filter(Cobrancas.data_negociacao >= inicio_filtro, Cobrancas.data_negociacao <= fim_filtro).all(),
            'consultas': base_query(Consultas).filter(Consultas.data_consulta >= inicio_filtro, Consultas.data_consulta <= fim_filtro).all(),
            'procedimentos': base_query(Procedimentos).filter(Procedimentos.data_procedimento >= inicio_filtro, Procedimentos.data_procedimento <= fim_filtro).all(),
        }
    else:
        detalhes = { 'vendas': [], 'cobrancas': [], 'consultas': [], 'procedimentos': [] }

    # Calcula os valores exclusivamente para os cards do Mês Atual do topo
    qv_mes = base_query(Vendas).filter(Vendas.data_venda >= inicio_atual, Vendas.data_venda <= fim_atual).count()
    vv_mes = db.session.query(func.sum(Vendas.comissao_calculada)).filter(Vendas.user_id == current_user.id, Vendas.data_venda >= inicio_atual, Vendas.data_venda <= fim_atual).scalar() or 0
    bv_mes = db.session.query(func.sum(Vendas.valor_total)).filter(Vendas.user_id == current_user.id, Vendas.data_venda >= inicio_atual, Vendas.data_venda <= fim_atual).scalar() or 0

    qcb_mes = base_query(Cobrancas).filter(Cobrancas.data_negociacao >= inicio_atual, Cobrancas.data_negociacao <= fim_atual).count()
    vcb_mes = db.session.query(func.sum(Cobrancas.comissao_calculada)).filter(Cobrancas.user_id == current_user.id, Cobrancas.data_negociacao >= inicio_atual, Cobrancas.data_negociacao <= fim_atual).scalar() or 0
    bcb_mes = db.session.query(func.sum(Cobrancas.valor_negociado)).filter(Cobrancas.user_id == current_user.id, Cobrancas.data_negociacao >= inicio_atual, Cobrancas.data_negociacao <= fim_atual).scalar() or 0

    qcs_mes = base_query(Consultas).filter(Consultas.data_consulta >= inicio_atual, Consultas.data_consulta <= fim_atual).count()
    vcs_mes = db.session.query(func.sum(Consultas.comissao_calculada)).filter(Consultas.user_id == current_user.id, Consultas.data_consulta >= inicio_atual, Consultas.data_consulta <= fim_atual).scalar() or 0

    qp_mes = base_query(Procedimentos).filter(Procedimentos.data_procedimento >= inicio_atual, Procedimentos.data_procedimento <= fim_atual).count()
    vp_mes = db.session.query(func.sum(Procedimentos.comissao_calculada)).filter(Procedimentos.user_id == current_user.id, Procedimentos.data_procedimento >= inicio_atual, Procedimentos.data_procedimento <= fim_atual).scalar() or 0

    total_mes_atual = vv_mes + vcb_mes + vcs_mes + vp_mes
    
    resumo_mes_atual = {
        'vendas': {'qtd': qv_mes, 'val': vv_mes, 'bruto': bv_mes},
        'cobrancas': {'qtd': qcb_mes, 'val': vcb_mes, 'bruto': bcb_mes},
        'consultas': {'qtd': qcs_mes, 'val': vcs_mes, 'bruto': 0},
        'procedimentos': {'qtd': qp_mes, 'val': vp_mes, 'bruto': 0}
    }

    user_dict = {u.id: u.full_name for u in User.query.all()}

    return render_template('relatorios.html', 
                           total_acumulado_geral=total_acumulado_geral,
                           total_itens_geral=total_itens_geral,
                           resumo_geral=resumo_geral,
                           lista_historico=lista_historico,
                           detalhes=detalhes,
                           resumo_mes=resumo_mes_atual,
                           total_mes_atual=total_mes_atual,
                           mes_atual=mes_atual,
                           ano_atual=ano_atual,
                           filtro={'mes': mes_filtro, 'ano': ano_filtro},
                           filtro_explicito=filtro_explicito,
                           user_dict=user_dict)

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
        if tipo == 'Talão': comissao = valor * 0.50
        elif tipo == 'Cartão': comissao = valor * 0.05
        elif tipo == 'PIX': comissao = (valor / 12) * 0.20
        
        nova = Vendas(user_id=current_user.id, nome_cliente=cliente, tipo_venda=tipo, valor_total=valor, comissao_calculada=comissao, data_venda=data_venda)
        db.session.add(nova)
        db.session.commit()
        return redirect(url_for('vendas'))
    
    agora = datetime.now()
    mes_atual = agora.month
    ano_atual = agora.year
    
    _, last_day = calendar.monthrange(ano_atual, mes_atual)
    inicio_mes = datetime(ano_atual, mes_atual, 1).date()
    fim_mes = datetime(ano_atual, mes_atual, last_day).date()

    lista = Vendas.query.filter_by(user_id=current_user.id).filter(Vendas.data_venda >= inicio_mes, Vendas.data_venda <= fim_mes).order_by(Vendas.data_venda.desc()).all()
    total_val = db.session.query(func.sum(Vendas.comissao_calculada)).filter_by(user_id=current_user.id).filter(Vendas.data_venda >= inicio_mes, Vendas.data_venda <= fim_mes).scalar() or 0
    total_bruto = db.session.query(func.sum(Vendas.valor_total)).filter_by(user_id=current_user.id).filter(Vendas.data_venda >= inicio_mes, Vendas.data_venda <= fim_mes).scalar() or 0
    total_qtd = Vendas.query.filter_by(user_id=current_user.id).filter(Vendas.data_venda >= inicio_mes, Vendas.data_venda <= fim_mes).count()
    
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

        # Recalcular comissão
        if venda.tipo_venda == 'Talão': venda.comissao_calculada = venda.valor_total * 0.50
        elif venda.tipo_venda == 'Cartão': venda.comissao_calculada = venda.valor_total * 0.05
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
    flash('Venda excluída com sucesso!')
    return redirect(request.referrer or url_for('vendas'))

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
    
    agora = datetime.now()
    mes_atual = agora.month
    ano_atual = agora.year
    
    _, last_day = calendar.monthrange(ano_atual, mes_atual)
    inicio_mes = datetime(ano_atual, mes_atual, 1).date()
    fim_mes = datetime(ano_atual, mes_atual, last_day).date()

    lista = Cobrancas.query.filter_by(user_id=current_user.id).filter(Cobrancas.data_negociacao >= inicio_mes, Cobrancas.data_negociacao <= fim_mes).order_by(Cobrancas.data_negociacao.desc()).all()
    total_val = db.session.query(func.sum(Cobrancas.comissao_calculada)).filter_by(user_id=current_user.id).filter(Cobrancas.data_negociacao >= inicio_mes, Cobrancas.data_negociacao <= fim_mes).scalar() or 0
    total_bruto = db.session.query(func.sum(Cobrancas.valor_negociado)).filter_by(user_id=current_user.id).filter(Cobrancas.data_negociacao >= inicio_mes, Cobrancas.data_negociacao <= fim_mes).scalar() or 0
    total_qtd = Cobrancas.query.filter_by(user_id=current_user.id).filter(Cobrancas.data_negociacao >= inicio_mes, Cobrancas.data_negociacao <= fim_mes).count()

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
        flash('Cobrança atualizada com sucesso!')
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
    flash('Cobrança excluída com sucesso!')
    return redirect(request.referrer or url_for('cobrancas'))

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
    
    agora = datetime.now()
    mes_atual = agora.month
    ano_atual = agora.year
    
    _, last_day = calendar.monthrange(ano_atual, mes_atual)
    inicio_mes = datetime(ano_atual, mes_atual, 1).date()
    fim_mes = datetime(ano_atual, mes_atual, last_day).date()

    lista = Consultas.query.filter_by(user_id=current_user.id).filter(Consultas.data_consulta >= inicio_mes, Consultas.data_consulta <= fim_mes).order_by(Consultas.data_consulta.desc()).all()
    total_val = db.session.query(func.sum(Consultas.comissao_calculada)).filter_by(user_id=current_user.id).filter(Consultas.data_consulta >= inicio_mes, Consultas.data_consulta <= fim_mes).scalar() or 0
    total_qtd = Consultas.query.filter_by(user_id=current_user.id).filter(Consultas.data_consulta >= inicio_mes, Consultas.data_consulta <= fim_mes).count()

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

        # Comissão fixa, não precisa recalcular se não mudar a regra
        
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
    flash('Consulta excluída com sucesso!')
    return redirect(request.referrer or url_for('consultas'))

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
    
    agora = datetime.now()
    mes_atual = agora.month
    ano_atual = agora.year
    
    _, last_day = calendar.monthrange(ano_atual, mes_atual)
    inicio_mes = datetime(ano_atual, mes_atual, 1).date()
    fim_mes = datetime(ano_atual, mes_atual, last_day).date()

    lista = Procedimentos.query.filter_by(user_id=current_user.id).filter(Procedimentos.data_procedimento >= inicio_mes, Procedimentos.data_procedimento <= fim_mes).order_by(Procedimentos.data_procedimento.desc()).all()
    total_val = db.session.query(func.sum(Procedimentos.comissao_calculada)).filter_by(user_id=current_user.id).filter(Procedimentos.data_procedimento >= inicio_mes, Procedimentos.data_procedimento <= fim_mes).scalar() or 0
    total_qtd = Procedimentos.query.filter_by(user_id=current_user.id).filter(Procedimentos.data_procedimento >= inicio_mes, Procedimentos.data_procedimento <= fim_mes).count()

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

        # Comissão fixa
        
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
    flash('Procedimento excluído com sucesso!')
    return redirect(request.referrer or url_for('procedimentos'))

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
    # try:
    #     # Garante que o Ngrok use o protocolo HTTP (que gera https gratuito)
    #     public_url = ngrok.connect(port, "http").public_url
    #     print("\n" + "="*60)
    #     print(f" 🚀 ACESSE SEU APP AQUI (EXTERNO): {public_url}")
    #     print("="*60 + "\n")
    # except Exception as e:
    #     print(f"\n[!] Aviso: Não foi possível gerar Link Público Ngrok. Erro: {e}")
    #     print("    (Verifique sua conexão de internet)\n")

    print(f" 🏠 ACESSE SEU APP AQUI (LOCAL):   http://127.0.0.1:{port}\n")

    # Configuração GARANTIDA de Processo Único (Sem auto-open, sem reloader)
    app.run(debug=False, use_reloader=False, host='0.0.0.0', port=port)
