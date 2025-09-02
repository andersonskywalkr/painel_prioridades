from flask import Flask, request, jsonify, render_template, redirect, url_for, session, flash
from flask_cors import CORS
from sqlalchemy import create_engine, text, Column, Integer, String, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker
from functools import wraps
import os
from datetime import datetime
import pytz
# Adicionado para hash de senha
from werkzeug.security import generate_password_hash, check_password_hash

# Definir fuso horário de Brasília
fuso_brasilia = pytz.timezone("America/Sao_Paulo")

app = Flask(__name__, template_folder='templates', static_folder='static')
CORS(app)

# --- Configurações de Sessão ---
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY') or os.urandom(24)
app.config['SESSION_TYPE'] = 'filesystem'
app.config['PERMANENT_SESSION_LIFETIME'] = 3600

# --- Conexão com o Banco de Dados ---
DATABASE_URL = os.environ.get('DATABASE_URL', 'postgresql+psycopg2://postgres:2025@localhost:5432/pedidos_db')
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# --- Definição das Tabelas (Modelos SQLAlchemy) ---
Base = declarative_base()

class UsuarioTb(Base):
    __tablename__ = 'usuario_tb'
    id = Column(Integer, primary_key=True)
    username = Column(String(80), unique=True, nullable=False)
    password_hash = Column(String(256), nullable=False)
    nome_completo = Column(String(120))
    nivel_acesso = Column(String(50), default='operador', nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class StatusTd(Base):
    __tablename__ = 'status_td'
    id = Column(Integer, primary_key=True)
    nome_status = Column(String, nullable=False, unique=True)

class ImagemTd(Base):
    __tablename__ = 'imagem_td'
    id = Column(Integer, primary_key=True)
    nome = Column(String, nullable=False, unique=True)

class PedidosTb(Base):
    __tablename__ = 'pedidos_tb'
    id = Column(Integer, primary_key=True)
    codigo_pedido = Column(String, unique=True)
    equipamento = Column(String)
    pv = Column(String)
    descricao_servico = Column(String)
    status_id = Column(Integer, ForeignKey('status_td.id'))
    imagem_id = Column(Integer, ForeignKey('imagem_td.id'))
    data_criacao = Column(DateTime(timezone=True), default=lambda: datetime.now(fuso_brasilia))
    data_conclusao = Column(DateTime(timezone=True))
    quantidade = Column(Integer)
    prioridade = Column(Integer)
    perfil_alteracao = Column(String)
    urgente = Column(Boolean, default=False)

class HistoricoStatusTb(Base):
    __tablename__ = 'historico_status_tb'
    id = Column(Integer, primary_key=True)
    pedido_id = Column(Integer, ForeignKey('pedidos_tb.id'))
    status_anterior = Column(Integer)
    status_alterado = Column(Integer)
    data_mudanca = Column(DateTime(timezone=True), default=lambda: datetime.now(fuso_brasilia))
    alterado_por = Column(String)

# --- FUNÇÃO PARA POPULAR DADOS INICIAIS ---
def popular_dados_iniciais(db_session):
    """Garante que as tabelas de lookup (status, imagem) tenham dados iniciais."""
    print("Verificando e populando dados iniciais...")
    
    status_iniciais = ["Aguardando Chegada", "Backlog", "Em Montagem", "Concluído", "Pendente", "Cancelado"]
    imagens_iniciais = ["W11 PRO", "W11 PRO ETQ", "Linux", "SLUI (SOLUÇÃO DE PROBLEMAS)", "FREEDOS"]

    try:
        if db_session.query(StatusTd).count() == 0:
            print("Populando a tabela 'status_td'...")
            for nome in status_iniciais:
                db_session.add(StatusTd(nome_status=nome))
            db_session.commit()
        if db_session.query(ImagemTd).count() == 0:
            print("Populando a tabela 'imagem_td'...")
            for nome in imagens_iniciais:
                db_session.add(ImagemTd(nome=nome))
            db_session.commit()
    except Exception as e:
        print(f"Erro ao popular dados iniciais: {e}")
        db_session.rollback()

with app.app_context():
    print("Verificando e criando tabelas, se necessário...")
    Base.metadata.create_all(engine)
    db_sess = SessionLocal()
    try:
        popular_dados_iniciais(db_sess)
    finally:
        db_sess.close()

# --- DECORATORS DE AUTENTICAÇÃO E AUTORIZAÇÃO ---
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('nivel_acesso') != 'admin':
            flash('Acesso restrito a administradores.', 'warning')
            return redirect(url_for('home'))
        return f(*args, **kwargs)
    return decorated_function

# --- Rotas ---
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        db_session = SessionLocal()
        try:
            user = db_session.query(UsuarioTb).filter_by(username=username).first()
            if user and user.check_password(password):
                session['logged_in'] = True
                session['username'] = user.username
                session['nivel_acesso'] = user.nivel_acesso
                return redirect(url_for('home'))
            else:
                flash("Credenciais inválidas.", "danger")
                return redirect(url_for('login'))
        finally:
            db_session.close()
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("Você saiu do sistema.", "success")
    return redirect(url_for('login'))

@app.route("/")
@login_required
def home():
    return render_template("index.html")

# --- ROTAS PARA GERENCIAMENTO DE USUÁRIOS ---
@app.route("/usuarios")
@login_required
@admin_required
def usuarios_page():
    return render_template("usuarios.html")

@app.route("/api/usuarios", methods=['GET'])
@login_required
@admin_required
def get_usuarios():
    db_session = SessionLocal()
    try:
        usuarios_db = db_session.query(UsuarioTb).order_by(UsuarioTb.id).all()
        usuarios = [{"id": u.id, "username": u.username, "nome_completo": u.nome_completo, "nivel_acesso": u.nivel_acesso} for u in usuarios_db]
        return jsonify(usuarios)
    finally:
        db_session.close()

@app.route('/api/usuarios', methods=['POST'])
@login_required
@admin_required
def create_usuario():
    data = request.get_json()
    # ... (código de criação de usuário) ...
    if not all([data.get('username'), data.get('nome_completo'), data.get('password'), data.get('nivel_acesso')]):
        return jsonify({'erro': 'Todos os campos são obrigatórios.'}), 400
    db_session = SessionLocal()
    try:
        if db_session.query(UsuarioTb).filter_by(username=data['username']).first():
            return jsonify({'erro': f'O username "{data["username"]}" já está em uso.'}), 409
        novo_usuario = UsuarioTb(
            username=data['username'],
            nome_completo=data['nome_completo'],
            nivel_acesso=data['nivel_acesso']
        )
        novo_usuario.set_password(data['password'])
        db_session.add(novo_usuario)
        db_session.commit()
        return jsonify({'mensagem': f'Usuário {data["username"]} criado com sucesso!'}), 201
    except Exception as e:
        db_session.rollback()
        return jsonify({'erro': 'Ocorreu um erro interno no servidor.'}), 500
    finally:
        db_session.close()

# --- ROTAS EXISTENTES ---
@app.route("/relatorios")
@login_required
def relatorios_page():
    return render_template("relatorio.html")

@app.route("/pedidos", methods=["GET"])
@login_required
def get_pedidos():
    # ... (código para obter pedidos) ...
    filtro_tab = request.args.get('filtro')
    busca_texto = request.args.get('busca')
    busca_mes = request.args.get('mes')
    busca_ano = request.args.get('ano')
    params = {}
    where_conditions = []

    if filtro_tab == 'concluido':
        where_conditions.append("p.status_id = 4")
    elif filtro_tab == 'cancelado':
        where_conditions.append("p.status_id = 6")
    else:
        where_conditions.append("p.status_id NOT IN (4, 6)")

    if busca_texto:
        where_conditions.append("p.pv ILIKE :busca")
        params['busca'] = f"%{busca_texto}%"
    
    coluna_data_filtro = "p.data_criacao"
    if filtro_tab in ['concluido', 'cancelado']:
        coluna_data_filtro = "p.data_conclusao"

    if busca_mes:
        where_conditions.append(f"EXTRACT(MONTH FROM {coluna_data_filtro} AT TIME ZONE 'America/Sao_Paulo') = :mes")
        params['mes'] = int(busca_mes)
    
    if busca_ano and busca_ano.isdigit() and len(busca_ano) == 4:
        where_conditions.append(f"EXTRACT(YEAR FROM {coluna_data_filtro} AT TIME ZONE 'America/Sao_Paulo') = :ano")
        params['ano'] = int(busca_ano)

    query_sql = """
        SELECT 
            p.*, s.nome_status as status, i.nome as imagem_nome,
            p.data_conclusao as data_finalizacao 
        FROM public.pedidos_tb p
        LEFT JOIN public.status_td s ON p.status_id = s.id 
        LEFT JOIN public.imagem_td i ON p.imagem_id = i.id
    """
    
    if where_conditions:
        query_sql += " WHERE " + " AND ".join(where_conditions)
    
    query_sql += " ORDER BY p.urgente DESC, p.prioridade ASC"

    with engine.connect() as conn:
        result = conn.execute(text(query_sql), params)
        pedidos = [dict(row._mapping) for row in result]
    return jsonify(pedidos)


@app.route("/pedidos", methods=["POST"])
@login_required
def add_pedido():
    # ... (código para adicionar pedido) ...
    data = request.json
    username = session.get('username', 'Desconhecido')
    data_criacao = datetime.now(fuso_brasilia)
    urgente = data.get('urgente', False)

    with engine.connect() as conn:
        with conn.begin():
            max_prioridade_result = conn.execute(text("SELECT COALESCE(MAX(prioridade), 0) FROM public.pedidos_tb")).scalar_one()
            nova_prioridade = max_prioridade_result + 1
            result = conn.execute(
                text("""INSERT INTO public.pedidos_tb (pv, equipamento, quantidade, descricao_servico, status_id, imagem_id, perfil_alteracao, data_criacao, urgente, prioridade) VALUES (:pv, :equipamento, :quantidade, :descricao_servico, :status_id, :imagem_id, :perfil_alteracao, :data_criacao, :urgente, :prioridade) RETURNING id"""),
                {"pv": data["pv"], "equipamento": data["equipamento"], "quantidade": data["quantidade"], "descricao_servico": data["descricao_servico"], "status_id": data["status_id"], "imagem_id": data["imagem_id"], "perfil_alteracao": username, "data_criacao": data_criacao, "urgente": urgente, "prioridade": nova_prioridade}
            )
            novo_pedido_id = result.scalar_one()
            conn.execute(
                text("INSERT INTO public.historico_status_tb (pedido_id, status_anterior, status_alterado, data_mudanca, alterado_por) VALUES (:pedido_id, NULL, :status_alterado, :data_mudanca, :alterado_por)"),
                {"pedido_id": novo_pedido_id, "status_alterado": data["status_id"], "data_mudanca": data_criacao, "alterado_por": username}
            )
    return jsonify({"mensagem": "Pedido adicionado com sucesso!"}), 201

# --- ROTAS DE API ADICIONADAS PARA CORRIGIR O ERRO ---

@app.route("/status", methods=["GET"])
@login_required
def get_status():
    with engine.connect() as conn:
        result = conn.execute(text("SELECT id, nome_status as nome FROM public.status_td ORDER BY id"))
        status_list = [dict(row._mapping) for row in result]
    return jsonify(status_list)

@app.route("/imagem", methods=["GET"])
@login_required
def get_imagens():
    with engine.connect() as conn:
        result = conn.execute(text("SELECT id, nome FROM public.imagem_td ORDER BY id"))
        imagens_list = [dict(row._mapping) for row in result]
    return jsonify(imagens_list)

@app.route("/pedidos/<int:pedido_id>", methods=["PUT"])
@login_required
def update_pedido(pedido_id):
    data = request.json
    username = session.get('username', 'Desconhecido')
    with engine.connect() as conn:
        with conn.begin():
            pedido_atual = conn.execute(text("SELECT status_id FROM public.pedidos_tb WHERE id = :id"), {"id": pedido_id}).fetchone()
            if not pedido_atual:
                return jsonify({"erro": "Pedido não encontrado"}), 404
            
            status_anterior_id = pedido_atual.status_id
            novo_status_id = int(data.get("status_id"))

            params = { "id": pedido_id, **data, "perfil_alteracao": username }
            
            query_update_sql = "UPDATE public.pedidos_tb SET pv=:pv, equipamento=:equipamento, quantidade=:quantidade, descricao_servico=:descricao_servico, status_id=:status_id, imagem_id=:imagem_id, perfil_alteracao=:perfil_alteracao, urgente=:urgente, prioridade=:prioridade"
            if novo_status_id in [4, 6] and status_anterior_id not in [4, 6]:
                query_update_sql += ", data_conclusao = :data_conclusao"
                params["data_conclusao"] = datetime.now(fuso_brasilia)
            
            query_update_sql += " WHERE id=:id"
            conn.execute(text(query_update_sql), params)

            if status_anterior_id != novo_status_id:
                conn.execute(
                    text("INSERT INTO public.historico_status_tb (pedido_id, status_anterior, status_alterado, data_mudanca, alterado_por) VALUES (:pedido_id, :status_anterior, :status_alterado, :data_mudanca, :alterado_por)"),
                    {"pedido_id": pedido_id, "status_anterior": status_anterior_id, "status_alterado": novo_status_id, "data_mudanca": datetime.now(fuso_brasilia), "alterado_por": username}
                )
    return jsonify({"mensagem": "Pedido atualizado!"})

@app.route("/pedidos/<int:pedido_id>", methods=["DELETE"])
@login_required
def delete_pedido(pedido_id):
    with engine.connect() as conn:
        with conn.begin():
            conn.execute(text("DELETE FROM public.historico_status_tb WHERE pedido_id=:id"), {"id": pedido_id})
            conn.execute(text("DELETE FROM public.pedidos_tb WHERE id=:id"), {"id": pedido_id})
    return jsonify({"mensagem": "Pedido deletado!"})

@app.route("/pedidos/<int:pedido_id>/historico", methods=["GET"])
@login_required
def get_historico_pedido(pedido_id):
    query = """
        SELECT h.data_mudanca, h.alterado_por,
               COALESCE(s_ant.nome_status, 'CRIADO') as nome_status_anterior,
               s_alt.nome_status as nome_status_alterado
        FROM public.historico_status_tb h
        LEFT JOIN public.status_td s_ant ON h.status_anterior = s_ant.id
        LEFT JOIN public.status_td s_alt ON h.status_alterado = s_alt.id
        WHERE h.pedido_id = :pedido_id ORDER BY h.data_mudanca ASC
    """
    with engine.connect() as conn:
        result = conn.execute(text(query), {"pedido_id": pedido_id})
        historico = [dict(row._mapping) for row in result]
    return jsonify(historico)

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)

