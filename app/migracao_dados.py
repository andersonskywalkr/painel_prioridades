import pandas as pd
import psycopg2
import os
from datetime import datetime

# --- FUNÇÃO DE CONEXÃO ATUALIZADA ---
def get_db_connection():
    """
    Cria e retorna uma conexão com o banco.
    Tenta usar a variável de ambiente DATABASE_URL (para rodar no Docker).
    Se não encontrar, usa as configurações locais (para rodar no seu PC).
    """
    database_url = os.environ.get('DATABASE_URL')

    if database_url:
        print("Conectando via DATABASE_URL (ambiente Docker)...")
        # Ajusta a URL para o formato que o psycopg2 espera
        conn_str = database_url.replace("postgresql://", "postgres://")
        return psycopg2.connect(conn_str)
    else:
        print("AVISO: DATABASE_URL não definida. Usando configuração local (localhost).")
        return psycopg2.connect(
            host="localhost",
            database="pedidos_db",
            user="postgres",
            password="2025",
            client_encoding='utf8'
        )

def migrar_dados_pedidos():
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # 1. Obter o ID do status "Aguardando Chegada"
        status_aguardando_chegada = "Aguardando Chegada"
        print(f"Buscando o ID para o status: '{status_aguardando_chegada}'...")
        cur.execute("SELECT id FROM public.status_td WHERE nome_status = %s;", (status_aguardando_chegada,))
        result = cur.fetchone()
        
        if result is None:
            print(f"Erro: O status '{status_aguardando_chegada}' não foi encontrado na tabela status_td.")
            print("Por favor, certifique-se de ter inserido este status no banco de dados primeiro.")
            return
            
        status_id = result[0]
        print(f"ID para '{status_aguardando_chegada}' encontrado: {status_id}")

        # 2. Ler os dados da planilha Excel
        print("Lendo dados da planilha Excel...")
        planilha_path = os.path.join("dados", "Status_dos_pedidos.xlsm")
        df_excel = pd.read_excel(planilha_path)

        # 3. Preparar e padronizar os nomes das colunas
        df_excel.columns = df_excel.columns.str.strip().str.lower().str.replace(' ', '_')

        # 4. Renomear colunas
        df_excel = df_excel.rename(columns={
            "pedido": "codigo_pedido",
            "equipamento": "equipamento",
            "pv": "pv",
            "servico": "descricao_servico",
            "data_status": "data_criacao",
            "qtd_maquinas": "quantidade"
        })

        df_excel['prioridade'] = range(1, len(df_excel) + 1)
        
        # 5. Inserir os dados na tabela pedidos_tb
        print("Inserindo dados na tabela pedidos_tb...")
        for index, row in df_excel.iterrows():
            data_criacao = datetime.now()
            perfil_altecao = "Importada Planilha"
            # CORREÇÃO: Define o status de urgência como False por padrão na importação
            status_urgente = False

            query = """
            INSERT INTO public.pedidos_tb (codigo_pedido, equipamento, pv, descricao_servico, status_id, data_criacao, quantidade, prioridade, perfil_alteracao, urgente)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (codigo_pedido) DO UPDATE
            SET
                equipamento = EXCLUDED.equipamento,
                pv = EXCLUDED.pv,
                descricao_servico = EXCLUDED.descricao_servico,
                status_id = EXCLUDED.status_id,
                data_criacao = EXCLUDED.data_criacao,
                quantidade = EXCLUDED.quantidade,
                prioridade = EXCLUDED.prioridade,
                perfil_alteracao = EXCLUDED.perfil_alteracao,
                urgente = EXCLUDED.urgente;
            """
            cur.execute(query, (
                row['codigo_pedido'], row['equipamento'], row['pv'],
                row['descricao_servico'], status_id, data_criacao,
                row['quantidade'], row['prioridade'], perfil_altecao,
                status_urgente  # Adiciona o valor False para a coluna 'urgente'
            ))

        conn.commit()
        print("Dados migrados com sucesso!")

    except psycopg2.Error as e:
        print(f"Erro no banco de dados: {e}")
        if conn:
            conn.rollback()
    except FileNotFoundError:
        print(f"Erro: O arquivo de planilha não foi encontrado. Verifique se o caminho '{planilha_path}' está correto.")
    except KeyError as e:
        print(f"Erro: A coluna {e} não foi encontrada. Verifique as colunas na planilha.")
    finally:
        if conn:
            cur.close()
            conn.close()

if __name__ == "__main__":
    migrar_dados_pedidos()

