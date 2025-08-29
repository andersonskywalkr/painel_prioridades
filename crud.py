# Arquivo: crud.py (Atualizado com a lógica de data_conclusao)

from flask import Flask, request, jsonify, render_template, redirect, url_for, session
from flask_cors import CORS
from sqlalchemy import create_engine, text
from functools import wraps
import os
from datetime import datetime

app = Flask(__name__, template_folder='templates', static_folder='static')
CORS(app)

# --- Configurações de Sessão ---
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY') or os.urandom(24)
app.config['SESSION_TYPE'] = 'filesystem'
app.config['PERMANENT_SESSION_LIFETIME'] = 3600

# Configurações do banco de dados PostgreSQL
DB_USER = "postgres"
DB_PASS = "2025"
DB_HOST = "localhost"
DB_PORT = "5432"
DB_NAME = "pedidos_db"

engine = create_engine(f"postgresql+psycopg2://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}")

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# --- Rotas de Autenticação ---
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        if username == "admin" and password == "admin":
            session['logged_in'] = True
            session['username'] = username
            return redirect(url_for('home'))
        else:
            return render_template("login.html", error="Credenciais inválidas.")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for('login'))

# --- Rotas Principais ---
@app.route("/")
@login_required
def home():
    return render_template("index.html")

@app.route("/pedidos", methods=["GET"])
@login_required
def get_pedidos():
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
    
    # Usa a data de conclusão para filtrar nas abas de concluídos/cancelados
    coluna_data_filtro = "p.data_criacao"
    if filtro_tab in ['concluido', 'cancelado']:
        coluna_data_filtro = "p.data_conclusao" # Ajustado para a nova coluna

    if busca_mes:
        where_conditions.append(f"EXTRACT(MONTH FROM {coluna_data_filtro}) = :mes")
        params['mes'] = int(busca_mes)
    
    if busca_ano and busca_ano.isdigit() and len(busca_ano) == 4:
        where_conditions.append(f"EXTRACT(YEAR FROM {coluna_data_filtro}) = :ano")
        params['ano'] = int(busca_ano)

    # Renomeado data_finalizacao para data_conclusao para corresponder à coluna
    query_sql = """
        SELECT 
            p.*, 
            s.nome_status as status, 
            i.nome as imagem_nome,
            p.data_conclusao as data_finalizacao 
        FROM public.pedidos_tb p
        LEFT JOIN public.status_td s ON p.status_id = s.id 
        LEFT JOIN public.imagem_td i ON p.imagem_id = i.id
    """
    
    if where_conditions:
        query_sql += " WHERE " + " AND ".join(where_conditions)
    
    query_sql += " ORDER BY p.urgente DESC, p.prioridade ASC, p.data_criacao DESC"

    with engine.connect() as conn:
        result = conn.execute(text(query_sql), params)
        pedidos = [dict(row._mapping) for row in result]
    return jsonify(pedidos)

# Outras rotas (status, imagem, add_pedido) permanecem iguais
@app.route("/status", methods=["GET"])
@login_required
def get_status():
    with engine.connect() as conn:
        result = conn.execute(text("SELECT id, nome_status as nome FROM public.status_td ORDER BY id"))
        status = [dict(row._mapping) for row in result]
    return jsonify(status)

@app.route("/imagem", methods=["GET"])
@login_required
def get_imagens():
    with engine.connect() as conn:
        result = conn.execute(text("SELECT id, nome FROM public.imagem_td ORDER BY id"))
        imagens = [dict(row._mapping) for row in result]
    return jsonify(imagens)

@app.route("/pedidos", methods=["POST"])
@login_required
def add_pedido():
    data = request.json
    username = session.get('username', 'Desconhecido')
    data_criacao = datetime.now()
    urgente = data.get('urgente', False)

    with engine.connect() as conn:
        with conn.begin():
            result = conn.execute(
                text("INSERT INTO public.pedidos_tb (pv, equipamento, quantidade, descricao_servico, status_id, imagem_id, perfil_alteracao, data_criacao, urgente) VALUES (:pv, :equipamento, :quantidade, :descricao_servico, :status_id, :imagem_id, :perfil_alteracao, :data_criacao, :urgente) RETURNING id"),
                {"pv": data["pv"], "equipamento": data["equipamento"], "quantidade": data["quantidade"], "descricao_servico": data["descricao_servico"], "status_id": data["status_id"], "imagem_id": data["imagem_id"], "perfil_alteracao": username, "data_criacao": data_criacao, "urgente": urgente}
            )
            novo_pedido_id = result.scalar_one()
            
            conn.execute(
                text("INSERT INTO public.historico_status_tb (pedido_id, status_anterior, status_alterado, data_mudanca, alterado_por) VALUES (:pedido_id, NULL, :status_alterado, :data_mudanca, :alterado_por)"),
                {"pedido_id": novo_pedido_id, "status_alterado": data["status_id"], "data_mudanca": data_criacao, "alterado_por": username}
            )
            
    return jsonify({"mensagem": "Pedido adicionado com sucesso!"}), 201


# --- ROTA UPDATE_PEDIDO MODIFICADA ---
@app.route("/pedidos/<int:pedido_id>", methods=["PUT"])
@login_required
def update_pedido(pedido_id):
    data = request.json
    username = session.get('username', 'Desconhecido')
    urgente_novo_estado = data.get('urgente', False)
    novo_status_id = int(data.get("status_id"))

    with engine.connect() as conn:
        with conn.begin():
            # Busca o status atual para registrar no histórico
            pedido_atual = conn.execute(text("SELECT status_id FROM public.pedidos_tb WHERE id = :id"), {"id": pedido_id}).fetchone()
            if not pedido_atual:
                return jsonify({"erro": "Pedido não encontrado"}), 404
            status_anterior_id = pedido_atual.status_id

            # Monta a query de atualização base
            query_update_sql = """
                UPDATE public.pedidos_tb 
                SET pv=:pv, equipamento=:equipamento, quantidade=:quantidade, 
                    descricao_servico=:descricao_servico, status_id=:status_id, 
                    imagem_id=:imagem_id, perfil_alteracao=:perfil_alteracao,
                    urgente=:urgente
            """
            params = {
                "id": pedido_id, "pv": data["pv"], "equipamento": data["equipamento"], 
                "quantidade": data["quantidade"], "descricao_servico": data["descricao_servico"], 
                "status_id": novo_status_id, "imagem_id": data["imagem_id"], 
                "perfil_alteracao": username, "urgente": urgente_novo_estado
            }

            # CONDIÇÃO: Se o novo status for "Concluído" (ID 4), adiciona a data de conclusão
            if novo_status_id == 4 or 6:
                query_update_sql += ", data_conclusao = :data_conclusao"
                params["data_conclusao"] = datetime.now()

            query_update_sql += " WHERE id=:id"

            # 1. Executa a atualização do pedido
            conn.execute(text(query_update_sql), params)

            # 2. Registra no histórico se o status mudou
            if status_anterior_id != novo_status_id:
                conn.execute(
                    text("INSERT INTO public.historico_status_tb (pedido_id, status_anterior, status_alterado, data_mudanca, alterado_por) VALUES (:pedido_id, :status_anterior, :status_alterado, :data_mudanca, :alterado_por)"),
                    {"pedido_id": pedido_id, "status_anterior": status_anterior_id, "status_alterado": novo_status_id, "data_mudanca": datetime.now(), "alterado_por": username}
                )

    return jsonify({"mensagem": "Pedido atualizado!"})


@app.route("/pedidos/<int:pedido_id>", methods=["DELETE"])
@login_required
def delete_pedido(pedido_id):
    with engine.connect() as conn:
        conn.execute(text("DELETE FROM public.historico_status_tb WHERE pedido_id=:id"), {"id": pedido_id})
        conn.execute(text("DELETE FROM public.pedidos_tb WHERE id=:id"), {"id": pedido_id})
        conn.commit()
    return jsonify({"mensagem": "Pedido deletado!"})


@app.route("/pedidos/<int:pedido_id>/historico", methods=["GET"])
@login_required
def get_historico_pedido(pedido_id):
    query = """
        SELECT 
            h.data_mudanca,
            h.alterado_por,
            COALESCE(s_ant.nome_status, 'CRIADO') as nome_status_anterior,
            s_alt.nome_status as nome_status_alterado
        FROM public.historico_status_tb h
        LEFT JOIN public.status_td s_ant ON h.status_anterior = s_ant.id
        LEFT JOIN public.status_td s_alt ON h.status_alterado = s_alt.id
        WHERE h.pedido_id = :pedido_id
        ORDER BY h.data_mudanca ASC
    """
    with engine.connect() as conn:
        result = conn.execute(text(query), {"pedido_id": pedido_id})
        historico = [dict(row._mapping) for row in result]
    return jsonify(historico)


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)