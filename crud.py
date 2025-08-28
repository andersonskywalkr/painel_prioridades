from flask import Flask, request, jsonify, render_template, redirect, url_for, session
from flask_cors import CORS
from sqlalchemy import create_engine, text
from functools import wraps
import os
from datetime import datetime # Importa a biblioteca para trabalhar com datas

app = Flask(__name__, static_folder='static')
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
            session['username'] = username # Salva o nome do usuário na sessão
            return redirect(url_for('home'))
        else:
            return render_template("login.html", error="Credenciais inválidas.")

    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for('login'))

# --- Rotas Protegidas ---

@app.route("/")
@login_required
def home():
    return render_template("index.html")

@app.route("/pedidos", methods=["GET"])
@login_required
def get_pedidos():
    with engine.connect() as conn:
        # A consulta agora inclui as novas colunas
        result = conn.execute(
            text("SELECT p.*, s.nome_status as status, i.nome as imagem_nome FROM public.pedidos_tb p LEFT JOIN public.status_td s ON p.status_id = s.id LEFT JOIN public.imagem_td i ON p.imagem_id = i.id ORDER BY p.data_criacao DESC, p.prioridade")
        )
        pedidos = [dict(row._mapping) for row in result]
    return jsonify(pedidos)

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
    username = session.get('username', 'Desconhecido') # Pega o usuário logado
    data_criacao = datetime.now() # Pega a data e hora atuais
    with engine.connect() as conn:
        # A consulta de INSERT agora inclui as novas colunas
        conn.execute(
            text("INSERT INTO public.pedidos_tb (pv, equipamento, quantidade, descricao_servico, status_id, imagem_id, perfil_alteracao, data_criacao) VALUES (:pv, :equipamento, :quantidade, :descricao_servico, :status_id, :imagem_id, :perfil_alteracao, :data_criacao)"),
            {"pv": data["pv"], "equipamento": data["equipamento"], "quantidade": data["quantidade"], "descricao_servico": data["descricao_servico"], "status_id": data["status_id"], "imagem_id": data["imagem_id"], "perfil_alteracao": username, "data_criacao": data_criacao}
        )
        conn.commit()
    return jsonify({"mensagem": "Pedido adicionado com sucesso!"}), 201

@app.route("/pedidos/<int:pedido_id>", methods=["PUT"])
@login_required
def update_pedido(pedido_id):
    data = request.json
    username = session.get('username', 'Desconhecido') # Pega o usuário logado
    data_alteracao = datetime.now() # Pega a data e hora atuais
    with engine.connect() as conn:
        # A consulta de UPDATE também pode incluir as novas colunas
        conn.execute(
            text("UPDATE public.pedidos_tb SET pv=:pv, equipamento=:equipamento, quantidade=:quantidade, descricao_servico=:descricao_servico, status_id=:status_id, imagem_id=:imagem_id, perfil_alteracao=:perfil_alteracao, data_criacao=:data_criacao WHERE id=:id"),
            {"id": pedido_id, "pv": data["pv"], "equipamento": data["equipamento"], "quantidade": data["quantidade"], "descricao_servico": data["descricao_servico"], "status_id": data["status_id"], "imagem_id": data["imagem_id"], "perfil_alteracao": username, "data_criacao": data_alteracao}
        )
        conn.commit()
    return jsonify({"mensagem": "Pedido atualizado!"})

@app.route("/pedidos/<int:pedido_id>", methods=["DELETE"])
@login_required
def delete_pedido(pedido_id):
    with engine.connect() as conn:
        conn.execute(text("DELETE FROM public.pedidos_tb WHERE id=:id"), {"id": pedido_id})
        conn.commit()
    return jsonify({"mensagem": "Pedido deletado!"})

if __name__ == "__main__":
    app.run(host='0.0.0.0', debug=True)