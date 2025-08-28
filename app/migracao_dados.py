import pandas as pd
import psycopg2
import os

# Configurações de Conexão com o Banco de Dados
DB_HOST = "localhost"
DB_NAME = "pedidos_db"  # Substitua pelo nome do seu banco de dados
DB_USER = "postgres"
DB_PASSWORD = "2025"        # Substitua pela sua senha

def get_db_connection():
    """Cria e retorna uma conexão com o banco de dados."""
    return psycopg2.connect(
        host=DB_HOST,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        client_encoding='utf8'
    )

def migrar_dados_pedidos():
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # 1. Obter o ID do status "Aguardando Montagem" do banco de dados
        status_aguardando_montagem = "Aguardando montagem"
        print(f"Buscando o ID para o status: '{status_aguardando_montagem}'...")
        cur.execute("SELECT id FROM status_td WHERE nome_status = %s;", (status_aguardando_montagem,))
        result = cur.fetchone()
        
        if result is None:
            print(f"Erro: O status '{status_aguardando_montagem}' não foi encontrado na tabela status_td.")
            print("Por favor, certifique-se de ter inserido este status no banco de dados primeiro.")
            return
            
        status_id = result[0]
        print(f"ID para '{status_aguardando_montagem}' encontrado: {status_id}")

        # 2. Ler os dados da planilha Excel
        print("Lendo dados da planilha Excel...")
        planilha_path = os.path.join("dados", "Status_dos_pedidos.xlsm")
        df_excel = pd.read_excel(planilha_path)

        # 3. Preparar e padronizar os nomes das colunas
        df_excel.columns = df_excel.columns.str.strip().str.lower().str.replace(' ', '_')

        # 4. Renomear as colunas para o formato final esperado no banco de dados
        df_excel = df_excel.rename(columns={
            "pedido": "codigo_pedido",
            "equipamento": "equipamento",
            "pv": "pv",
            "servico": "descricao_servico",
            "data_status": "data_criacao",
            "qtd_maquinas": "quantidade"
        })

        # Adicionar a coluna de prioridade
        df_excel['prioridade'] = range(1, len(df_excel) + 1)
        
        # Opcional, mas útil para o erro 'NaT' se persistir:
        # Imprime a primeira linha para verificar o formato dos dados
        print("Dados da primeira linha (após o processamento):")
        print(df_excel.iloc[0])

        # 5. Inserir os dados na tabela pedidos_tb
        print("Inserindo dados na tabela pedidos_tb...")
        for index, row in df_excel.iterrows():
            # AQUI ESTÁ A NOVA CORREÇÃO:
            # Converte a data para um formato que o PostgreSQL entende
            # e lida com os valores NaT explicitamente
            try:
                data_criacao_valor = pd.to_datetime(row['data_criacao'])
                if pd.isna(data_criacao_valor):
                    data_criacao_valor = None
            except Exception:
                data_criacao_valor = None

            query = """
            INSERT INTO pedidos_tb (codigo_pedido, equipamento, pv, descricao_servico, status_id, data_criacao, quantidade, prioridade)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (codigo_pedido) DO UPDATE
            SET
                equipamento = EXCLUDED.equipamento,
                pv = EXCLUDED.pv,
                descricao_servico = EXCLUDED.descricao_servico,
                status_id = EXCLUDED.status_id,
                data_criacao = EXCLUDED.data_criacao,
                quantidade = EXCLUDED.quantidade,
                prioridade = EXCLUDED.prioridade;
            """
            cur.execute(query, (
                row['codigo_pedido'],
                row['equipamento'],
                row['pv'],
                row['descricao_servico'],
                status_id,
                data_criacao_valor,
                row['quantidade'],
                row['prioridade']
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
        print(f"Erro: A coluna {e} não foi encontrada no DataFrame. Verifique a ortografia das colunas na planilha.")
        print(f"Nomes das colunas do DataFrame após o processamento: {df_excel.columns.tolist()}")
    finally:
        if conn:
            cur.close()
            conn.close()

if __name__ == "__main__":
    migrar_dados_pedidos()