import sys
import os
import locale
import random
import pandas as pd
import psycopg2
from datetime import datetime, timedelta
import numpy as np
import time
import traceback
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                               QHBoxLayout, QLabel, QFrame, QProgressBar, QSizePolicy, QPushButton)
from PySide6.QtGui import QFont, QKeyEvent
from PySide6.QtCore import QTimer, Qt

# --- CONFIGURAÇÃO GERAL E DE DADOS ---
SCALE_FACTOR = 1.0
META_SEMANAL = 500

# --- NOVAS CONFIGURAÇÕES DE BANCO DE DADOS POSTGRESQL ---
DB_HOST = "localhost"
DB_NAME = "pedidos_db"
DB_USER = "postgres"
DB_PASSWORD = "2025"

# --- CONSTANTES DE COLUNAS E STATUS (VERSÃO ORIGINAL RESTAURADA) ---
COLUNA_PEDIDO_ID, COLUNA_PV, COLUNA_SERVICO, COLUNA_STATUS, COLUNA_DATA_STATUS, COLUNA_QTD, COLUNA_EQUIPAMENTO, COLUNA_PRIORIDADE = \
   'id', 'pv', 'descricao_servico', 'nome_status', 'data_criacao', 'quantidade', 'equipamento', 'prioridade'
    
STATUS_PENDENTE, STATUS_BACKLOG, STATUS_AGUARDANDO_CHEGADA, STATUS_EM_MONTAGEM, STATUS_CONCLUIDO, STATUS_CANCELADO, STATUS_URGENTE = \
    'Pendente', 'Backlog', 'Aguardando Chegada', 'Em Montagem', 'Concluído', 'Cancelado', 'Urgente'


# --- CONEXÃO COM O BANCO DE DADOS POSTGRESQL ---
def get_db_connection():
    """Cria e retorna uma conexão com o banco de dados PostgreSQL."""
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            client_encoding='utf8'
        )
        return conn
    except psycopg2.Error as e:
        raise Exception(f"Erro ao conectar ao banco de dados: {e}")

# --- LÓGICA DE DADOS REESCRITA PARA USAR O BANCO DE DADOS ---
def carregar_dados():
    """Carrega todos os dados diretamente do banco de dados PostgreSQL."""
    print(f"Carregando dados do banco de dados: {DB_NAME}...")
    conn = None
    try:
        conn = get_db_connection()
        query = f"""
        SELECT 
            p.id AS "{COLUNA_PEDIDO_ID}",
            p.equipamento AS "{COLUNA_EQUIPAMENTO}",
            p.pv AS "{COLUNA_PV}",
            p.descricao_servico AS "{COLUNA_SERVICO}",
            s.nome_status AS "{COLUNA_STATUS}",
            p.data_criacao AS "{COLUNA_DATA_STATUS}",
            p.quantidade AS "{COLUNA_QTD}",
            p.prioridade AS "{COLUNA_PRIORIDADE}"
        FROM 
            pedidos_tb p
        JOIN
            status_td s ON p.status_id = s.id
        ORDER BY
            p.prioridade ASC, p.data_criacao ASC;
        """
        df = pd.read_sql(query, conn)
        print("Dados brutos carregados do banco de dados:")
        print(df.head())
        
    except Exception as e:
        raise Exception(f"Não foi possível carregar os dados do banco de dados.\nErro: {e}")
    finally:
        if conn:
            conn.close()

    if df.empty:
        print("AVISO: O banco de dados não retornou nenhum pedido.")
        # CORREÇÃO CRÍTICA: Previne o erro 'KeyError' ao criar um DataFrame vazio com a estrutura de colunas correta.
        expected_columns = [
            COLUNA_PEDIDO_ID, COLUNA_EQUIPAMENTO, COLUNA_PV, COLUNA_SERVICO,
            COLUNA_STATUS, COLUNA_DATA_STATUS, COLUNA_QTD, COLUNA_PRIORIDADE
        ]
        empty_df = pd.DataFrame(columns=expected_columns)
        return empty_df.copy(), empty_df.copy(), empty_df.copy(), empty_df.copy(), (0,0,0,0,0,0), (0,0,0,0,0,0)

    # --- Processamento dos dados ---
    df_full = df.copy()
    
    df_full[COLUNA_DATA_STATUS] = pd.to_datetime(df_full[COLUNA_DATA_STATUS], errors='coerce').dt.tz_localize(None)
    df_full[COLUNA_STATUS] = df_full[COLUNA_STATUS].astype(str).str.strip()
    
    df_full['is_urgent'] = df_full[COLUNA_STATUS].str.lower() == STATUS_URGENTE.lower()

    status_finalizados = [STATUS_CONCLUIDO.lower(), STATUS_CANCELADO.lower()]
    df_principal = df_full[~df_full[COLUNA_STATUS].str.lower().isin(status_finalizados)].copy()
    
    hoje = datetime.now().date()
    df_concluidos_hoje = df_full[(df_full[COLUNA_STATUS].str.lower() == STATUS_CONCLUIDO.lower()) & (df_full[COLUNA_DATA_STATUS].dt.date == hoje)].sort_values(by=COLUNA_DATA_STATUS, ascending=False)
    df_cancelados_hoje = df_full[(df_full[COLUNA_STATUS].str.lower() == STATUS_CANCELADO.lower()) & (df_full[COLUNA_DATA_STATUS].dt.date == hoje)].sort_values(by=COLUNA_DATA_STATUS, ascending=False)

    if not df_principal.empty:
        df_principal.sort_values(by=['is_urgent', COLUNA_PRIORIDADE, COLUNA_DATA_STATUS], ascending=[False, True, True], inplace=True)
        df_principal.reset_index(drop=True, inplace=True)
        df_principal['Prioridade_Display'] = df_principal.index + 1

    # Cálculos dos totais
    is_teravix_concluido = df_concluidos_hoje[COLUNA_PV].astype(str).str.contains('TERAVIX', na=False, case=False)
    is_teravix_cancelado = df_cancelados_hoje[COLUNA_PV].astype(str).str.contains('TERAVIX', na=False, case=False)

    teravix_concluidos_qtd = df_concluidos_hoje.loc[is_teravix_concluido, COLUNA_QTD].sum()
    pv_concluidos_qtd = df_concluidos_hoje.loc[~is_teravix_concluido, COLUNA_QTD].sum()
    totais_concluidos = (len(df_concluidos_hoje[is_teravix_concluido]), len(df_concluidos_hoje[~is_teravix_concluido]), len(df_concluidos_hoje),
                         teravix_concluidos_qtd, pv_concluidos_qtd, df_concluidos_hoje[COLUNA_QTD].sum())

    teravix_cancelados_qtd = df_cancelados_hoje.loc[is_teravix_cancelado, COLUNA_QTD].sum()
    pv_cancelados_qtd = df_cancelados_hoje.loc[~is_teravix_cancelado, COLUNA_QTD].sum()
    totais_cancelados = (len(df_cancelados_hoje[is_teravix_cancelado]), len(df_cancelados_hoje[~is_teravix_cancelado]), len(df_cancelados_hoje),
                         teravix_cancelados_qtd, pv_cancelados_qtd, df_cancelados_hoje[COLUNA_QTD].sum())

    return df_full, df_principal, df_concluidos_hoje, df_cancelados_hoje, totais_concluidos, totais_cancelados


def calcular_metricas_dashboard(df_full):
    if df_full.empty:
        return {"total_mes_atual": 0, "total_mes_atual_qtd": 0, "media_diaria_atual": 0, "media_diaria_qtd": 0,
                "total_mes_anterior": 0, "media_diaria_anterior": 0,
                "recorde_dia_valor": 0, "recorde_dia_data": "N/A", "recorde_dia_qtd": 0}
    hoje = datetime.now()
    inicio_mes_atual = hoje.replace(day=1, hour=0, minute=0, second=0)
    df_concluidos_mes_atual = df_full[(df_full[COLUNA_STATUS].str.lower() == STATUS_CONCLUIDO.lower()) & (pd.to_datetime(df_full[COLUNA_DATA_STATUS]) >= inicio_mes_atual) & (pd.to_datetime(df_full[COLUNA_DATA_STATUS]) <= hoje)]
    total_mes_atual_pedidos = len(df_concluidos_mes_atual)
    total_mes_atual_qtd = df_concluidos_mes_atual[COLUNA_QTD].sum()
    dias_uteis_mes_atual = np.busday_count(inicio_mes_atual.strftime('%Y-%m-%d'), (hoje + timedelta(days=1)).strftime('%Y-%m-%d'))
    media_diaria_atual = total_mes_atual_pedidos / dias_uteis_mes_atual if dias_uteis_mes_atual > 0 else 0
    media_diaria_qtd = total_mes_atual_qtd / dias_uteis_mes_atual if dias_uteis_mes_atual > 0 else 0
    fim_mes_anterior = inicio_mes_atual - timedelta(days=1); inicio_mes_anterior = fim_mes_anterior.replace(day=1)
    df_concluidos_mes_anterior = df_full[(df_full[COLUNA_STATUS].str.lower() == STATUS_CONCLUIDO.lower()) & (pd.to_datetime(df_full[COLUNA_DATA_STATUS]) >= inicio_mes_anterior) & (pd.to_datetime(df_full[COLUNA_DATA_STATUS]) <= fim_mes_anterior)]
    media_diaria_anterior = len(df_concluidos_mes_anterior) / np.busday_count(inicio_mes_anterior.strftime('%Y-%m-%d'), (fim_mes_anterior + timedelta(days=1)).strftime('%Y-%m-%d')) if np.busday_count(inicio_mes_anterior.strftime('%Y-%m-%d'), (fim_mes_anterior + timedelta(days=1)).strftime('%Y-%m-%d')) > 0 else 0
    recorde_dia_valor = 0; recorde_dia_data = "N/A"; recorde_dia_qtd = 0
    if not df_concluidos_mes_atual.empty:
        producao_diaria = df_concluidos_mes_atual.groupby(pd.to_datetime(df_concluidos_mes_atual[COLUNA_DATA_STATUS]).dt.date).size()
        if not producao_diaria.empty:
            recorde_dia_valor = producao_diaria.max()
            recorde_dia_data_obj = producao_diaria.idxmax()
            recorde_dia_data = recorde_dia_data_obj.strftime('%d/%m/%Y')
            recorde_dia_qtd = df_concluidos_mes_atual[pd.to_datetime(df_concluidos_mes_atual[COLUNA_DATA_STATUS]).dt.date == recorde_dia_data_obj][COLUNA_QTD].sum()
    return {"total_mes_atual": total_mes_atual_pedidos, "total_mes_atual_qtd": total_mes_atual_qtd, "media_diaria_atual": media_diaria_atual, "media_diaria_qtd": media_diaria_qtd,
            "total_mes_anterior": len(df_concluidos_mes_anterior), "media_diaria_anterior": media_diaria_anterior,
            "recorde_dia_valor": recorde_dia_valor, "recorde_dia_data": recorde_dia_data, "recorde_dia_qtd": recorde_dia_qtd}

def calcular_dados_grafico(df_full):
    if df_full.empty: return []
    df_concluidos = df_full.dropna(subset=[COLUNA_DATA_STATUS]).copy()
    df_concluidos = df_concluidos[df_concluidos[COLUNA_STATUS].str.lower() == STATUS_CONCLUIDO.lower()].copy()
    if df_concluidos.empty: return []
    df_concluidos['Semana'] = pd.to_datetime(df_concluidos[COLUNA_DATA_STATUS]).dt.to_period('W-SUN').dt.start_time
    semanal = df_concluidos.groupby('Semana')[COLUNA_QTD].sum()
    semanas_recentes = pd.date_range(end=datetime.now(), periods=4, freq='W-MON').normalize()
    semanal = semanal.reindex(semanas_recentes, fill_value=0)
    return list(semanal.items())

# --- STYLESHEET (Folha de Estilos) ---
STYLESHEET = f"""
    QMainWindow {{ background-color: #1C1C1C; }} QLabel {{ color: #E0E0E0; }}
    #Header {{ background-color: #2E2E2E; border-bottom: 2px solid #FF6600; }}
    #LogoLabel {{ padding: 5px; }} .SectionTitle {{ border-bottom: 2px solid; padding-bottom: 8px; margin-bottom: 10px; }}
    #PrioridadesTitle, #EmMontagemTitle, #PendentesTitle, #BacklogTitle, #AguardandoChegadaTitle {{ color: #FF6600; border-bottom-color: #FF6600; }}
    #ConcluidosTitle {{ color: #2ECC71; border-bottom-color: #2ECC71; }} #CanceladosTitle {{ color: #E74C3C; border-bottom-color: #E74C3C; }}
    #CounterLabel {{ color: #888888; font-style: italic; padding-top: 10px; }}
    #SideColumnFrame {{ background-color: #252525; border-radius: 8px; }} #ErrorLabel {{ color: #E74C3C; }}
    #Card {{ background-color: #2E2E2E; border: 1px solid #FF6600; border-radius: 8px; padding: 12px; }}
    #CardTitle {{ color: #FF8C33; }}
    #CardStatus_Backlog {{ color: #3498DB; }}
    #CardStatus_EmMontagem {{ color: #F39C12; }}
    #CardStatus_Urgente {{ color: #FF5733; }}
    #TotalLabel {{ color: #BDBDBD; margin-top: 10px; }}
    #DashboardFrame {{ border-top: 1px solid #444; margin-top: 10px; padding: 10px; }}
    #MetricaTitle, #KpiTitle {{ color: #FFFFFF; font-weight: bold; }} #MetricaValue, #KpiValue {{ color: #FF6600; }}
    #KpiRecorde {{ color: #3498DB; }}
    QProgressBar {{ border: 1px solid #555; border-radius: 5px; text-align: center; background-color: #2E2E2E; }}
    QProgressBar::chunk {{ background-color: #FF6600; border-radius: 4px; }}
    QProgressBar#currentWeek::chunk {{ background-color: #FFAA33; }}
    #NotificationLabel {{
        background-color: #2ECC71; color: white; border-radius: 5px;
        padding: 10px; font-weight: bold; font-size: {int(16 * SCALE_FACTOR)}px;
    }}
    #NotificationLabel[error="true"] {{
        background-color: #E74C3C;
    }}
"""

class PainelMtec(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Painel de Produção MTEC"); self.setGeometry(100, 100, 1920, 1080);
        self.setStyleSheet(STYLESHEET)
        
        self.main_container = QWidget(); self.error_container = QWidget(); self.is_showing_error = False
        
        self.setup_ui()
        self.setup_online_timer()
        self.atualizar_dados_e_ui()

    def scale(self, size):
        return int(size * SCALE_FACTOR)

    def setup_ui(self):
        self.central_widget = QWidget(); self.setCentralWidget(self.central_widget); layout = QVBoxLayout(self.central_widget); layout.setContentsMargins(0,0,0,0); layout.setSpacing(0)
        self.main_container = QWidget(); self.error_container = QWidget(); self.is_showing_error = False
        main_layout = QVBoxLayout(self.main_container); main_layout.setContentsMargins(0, 0, 0, 0); main_layout.setSpacing(0)
        
        header = QWidget(); header.setObjectName("Header"); header.setFixedHeight(self.scale(60)); header_layout = QHBoxLayout(header); header_layout.setContentsMargins(20, 0, 20, 0)
        
        logo_label = QLabel("mtec."); logo_label.setObjectName("LogoLabel"); logo_label.setFont(QFont("Inter", self.scale(22), QFont.Bold)); header_layout.addWidget(logo_label); header_layout.addStretch(); main_layout.addWidget(header)

        self.body_widget = QWidget()
        self.body_layout = QHBoxLayout(self.body_widget)
        self.body_layout.setContentsMargins(self.scale(15), self.scale(15), self.scale(15), self.scale(15)); self.body_layout.setSpacing(self.scale(20))
        main_layout.addWidget(self.body_widget, 1)

        dashboard_frame = QFrame(); dashboard_frame.setObjectName("DashboardFrame"); dashboard_frame.setFixedHeight(self.scale(240)); self.dashboard_layout = QHBoxLayout(dashboard_frame); main_layout.addWidget(dashboard_frame)
        self.setup_ui_columns()
        
        error_page_layout = QVBoxLayout(self.error_container); self.error_label = QLabel(); self.error_label.setObjectName("ErrorLabel"); self.error_label.setAlignment(Qt.AlignCenter); self.error_label.setWordWrap(True);
        self.error_label.setFont(QFont("Inter", self.scale(18), QFont.Bold)); error_page_layout.addWidget(self.error_label)
        layout.addWidget(self.main_container); layout.addWidget(self.error_container); self.error_container.hide()

        self.notification_label = QLabel(self); self.notification_label.setObjectName("NotificationLabel"); self.notification_label.setWordWrap(True); self.notification_label.hide()

    def setup_ui_columns(self):
        self.prioridades_layout = QVBoxLayout()
        self.prioridades_layout.setSpacing(self.scale(15))

        self.backlog_layout = QVBoxLayout()
        self.aguardando_chegada_layout = QVBoxLayout()
        self.pendentes_layout = QVBoxLayout()
        self.em_montagem_container = QWidget()
        self.em_montagem_layout = QVBoxLayout(self.em_montagem_container)
        self.em_montagem_layout.setContentsMargins(0, self.scale(20), 0, 0); self.em_montagem_layout.setSpacing(0)

        coluna_combinada_montagem = QVBoxLayout()
        coluna_combinada_montagem.addLayout(self.backlog_layout)
        coluna_combinada_montagem.addWidget(self.em_montagem_container)
        coluna_combinada_montagem.addStretch()

        self.body_layout.addLayout(self.prioridades_layout, 2)
        self.body_layout.addLayout(coluna_combinada_montagem, 1)
        self.body_layout.addLayout(self.aguardando_chegada_layout, 1)
        self.body_layout.addLayout(self.pendentes_layout, 1)

        side_column_frame = QFrame(); side_column_frame.setObjectName("SideColumnFrame"); side_column_frame.setFixedWidth(self.scale(300))
        self.side_layout = QVBoxLayout(side_column_frame)
        self.concluidos_layout = QVBoxLayout(); self.cancelados_layout = QVBoxLayout()
        self.side_layout.addLayout(self.concluidos_layout); self.side_layout.addStretch(1)
        linea_separadora = QFrame(); linea_separadora.setFrameShape(QFrame.HLine); linea_separadora.setFrameShadow(QFrame.Sunken); linea_separadora.setStyleSheet("background-color: #444; min-height: 1px; border: none;"); self.side_layout.addWidget(linea_separadora); self.side_layout.addSpacing(20)
        self.side_layout.addLayout(self.cancelados_layout); self.side_layout.addStretch(2)
        self.body_layout.addWidget(side_column_frame)

        self.metricas_layout = QVBoxLayout(); self.grafico_layout = QVBoxLayout(); self.kpi_layout = QVBoxLayout()
        self.dashboard_layout.addLayout(self.metricas_layout, 1); self.dashboard_layout.addLayout(self.grafico_layout, 2); self.dashboard_layout.addStretch(1); self.dashboard_layout.addLayout(self.kpi_layout, 1)

    def setup_online_timer(self):
        """Configura um timer para atualizações periódicas no modo online."""
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.atualizar_dados_e_ui)
        self.update_timer.start(10000) # 1000ms = 1s
        print("Modo online: O painel será atualizado a cada minuto.")

    def keyPressEvent(self, event: QKeyEvent):
        """Handles key press events for the main window."""
        if event.key() == Qt.Key_F11:
            if self.isFullScreen():
                print("Saindo do modo de tela cheia (F11 pressionado).")
                self.showMaximized()
            else:
                print("Entrando no modo de tela cheia (F11 pressionado).")
                self.showFullScreen()
        super().keyPressEvent(event)

    def atualizar_dados_e_ui(self):
        print("\n--- INICIANDO CICLO DE ATUALIZAÇÃO ---")
        try:
            df_full, df_principal, df_concluidos, df_cancelados, totais_concluidos, totais_cancelados = carregar_dados()
            
            if self.is_showing_error: self.clear_error_message()
            
            self.desenhar_colunas(df_principal, df_concluidos, df_cancelados, totais_concluidos, totais_cancelados)
            
            metricas = calcular_metricas_dashboard(df_full)
            dados_grafico = calcular_dados_grafico(df_full)
            self.desenhar_dashboard(metricas, dados_grafico)
            
            print("--- CICLO DE ATUALIZAÇÃO CONCLUÍDO ---")
        except Exception as e:
            print(f"ERRO CRÍTICO NO CICLO DE ATUALIZAÇÃO: {e}")
            traceback.print_exc()
            self.mostrar_erro(str(e))

    def mostrar_erro(self, message):
        self.main_container.hide(); self.error_container.show(); self.is_showing_error = True
        self.error_label.setText(f"Erro ao carregar dados:\n\n{message}"); self.error_label.setAlignment(Qt.AlignCenter)
        print(f"ERRO EXIBIDO: {message}")

    def clear_error_message(self):
        self.error_container.hide(); self.main_container.show(); self.is_showing_error = False
    
    def criar_titulo(self, texto, object_name, font):
        label = QLabel(f"<b>{texto}</b>"); label.setObjectName(object_name); label.setFont(font); label.setProperty("class", "SectionTitle")
        return label
    
    def limpar_layout(self, layout):
        if layout is not None:
            while layout.count():
                item = layout.takeAt(0)
                if item.widget() is not None:
                    item.widget().deleteLater()
                elif item.layout() is not None:
                    self.limpar_layout(item.layout())

    def desenhar_colunas(self, df_principal, df_concluidos, df_cancelados, totais_concluidos, totais_cancelados):
        # CORREÇÃO: Limpeza centralizada para garantir que a UI sempre atualize
        layouts_para_limpar = [self.prioridades_layout, self.em_montagem_layout, self.pendentes_layout, 
                               self.backlog_layout, self.aguardando_chegada_layout, 
                               self.concluidos_layout, self.cancelados_layout]
        for layout in layouts_para_limpar: self.limpar_layout(layout)

        font_titulo = QFont("Inter", self.scale(16), QFont.Bold)
        font_item = QFont("Inter", self.scale(10)) 
        font_contador = QFont("Inter", self.scale(9))
        font_total = QFont("Inter", self.scale(9))

        # CORREÇÃO: Filtragem case-insensitive para maior robustez
        df_prioridades = df_principal[df_principal[COLUNA_STATUS].str.lower().isin([STATUS_BACKLOG.lower(), STATUS_EM_MONTAGEM.lower(), STATUS_URGENTE.lower()])]
        pedidos_em_prioridade_ids = df_prioridades.head(4)[COLUNA_PEDIDO_ID].tolist()

        self.desenhar_cards_prioridade(self.prioridades_layout, df_prioridades, font_titulo)

        df_em_montagem_base = df_principal[df_principal[COLUNA_STATUS].str.lower() == STATUS_EM_MONTAGEM.lower()]
        df_em_montagem_filtrado = df_em_montagem_base[~df_em_montagem_base[COLUNA_PEDIDO_ID].isin(pedidos_em_prioridade_ids)]

        if df_em_montagem_filtrado.empty:
            self.em_montagem_container.hide()
        else:
            self.em_montagem_container.show()
            self.desenhar_lista_vertical(self.em_montagem_layout, df_em_montagem_filtrado, "EM MONTAGEM FORA DA PRIORIDADE", font_titulo, font_item, font_contador)

        df_pendentes = df_principal[df_principal[COLUNA_STATUS].str.lower() == STATUS_PENDENTE.lower()]
        self.desenhar_lista_vertical(self.pendentes_layout, df_pendentes, "PENDENTES", font_titulo, font_item, font_contador)

        df_backlog_base = df_principal[df_principal[COLUNA_STATUS].str.lower() == STATUS_BACKLOG.lower()]
        df_backlog_filtrado = df_backlog_base[~df_backlog_base[COLUNA_PEDIDO_ID].isin(pedidos_em_prioridade_ids)]
        self.desenhar_lista_vertical(self.backlog_layout, df_backlog_filtrado, "BACKLOG", font_titulo, font_item, font_contador)

        df_aguardando_chegada = df_principal[df_principal[COLUNA_STATUS].str.lower() == STATUS_AGUARDANDO_CHEGADA.lower()]
        self.desenhar_lista_vertical(self.aguardando_chegada_layout, df_aguardando_chegada, "AGUARDANDO CHEGADA", font_titulo, font_item, font_contador)

        self.desenhar_lista_lateral(self.concluidos_layout, df_concluidos, "CONCLUÍDOS DO DIA", font_titulo, font_item, font_contador, font_total, totais_concluidos, limit=5)
        self.desenhar_lista_lateral(self.cancelados_layout, df_cancelados, "CANCELADOS DO DIA", font_titulo, font_item, font_contador, font_total, totais_cancelados, limit=5)

    def desenhar_cards_prioridade(self, layout, df, font_titulo):
        layout.addWidget(self.criar_titulo("PRIORIDADES", "PrioridadesTitle", font_titulo))
        if df.empty:
            layout.addWidget(QLabel("Nenhum pedido de alta prioridade.")); layout.addStretch()
            return
        
        for _, row in df.head(4).iterrows():
            card = QFrame(); card.setObjectName("Card"); card_layout = QVBoxLayout(card); card.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed); card.setFixedHeight(self.scale(120))
            
            font_label = QFont("Inter", self.scale(12), QFont.Bold)
            font_sub = QFont("Inter", self.scale(9))
            
            pedido_label = QLabel(f"<b>PV: {row[COLUNA_PV]}</b> ({row['Prioridade_Display']}º Prioridade)"); pedido_label.setFont(font_label); pedido_label.setObjectName("CardTitle"); card_layout.addWidget(pedido_label)
            status_label = QLabel(f"<font color='#BDBDBD'>Status: </font><span style='color: white; font-weight: bold;'>{row[COLUNA_STATUS]}</span>")
            status_label.setObjectName(f"CardStatus_{row[COLUNA_STATUS].replace(' ', '').replace('ó', 'o')}")
            status_label.setFont(font_sub)
            
            servico_label = QLabel(f"<font color='#BDBDBD'>Serviço: </font>{row[COLUNA_SERVICO]}"); servico_label.setFont(font_sub); servico_label.setWordWrap(True)
            equipamento_label = QLabel(f"<font color='#BDBDBD'>Equipamento: </font>{row[COLUNA_EQUIPAMENTO]}"); equipamento_label.setFont(font_sub)
            
            info_layout = QHBoxLayout()
            info_layout.addWidget(QLabel(f"<font color='#BDBDBD'><b>{row[COLUNA_QTD]}</b> máq.</font>")); info_layout.addStretch()
            info_layout.addWidget(QLabel(f"<font color='#FF6600'>{row[COLUNA_PV]}</font>"))
            
            card_layout.addWidget(status_label); card_layout.addWidget(equipamento_label); card_layout.addWidget(servico_label); card_layout.addLayout(info_layout); layout.addWidget(card)
        
        layout.addStretch()

    def desenhar_lista_vertical(self, layout, df, titulo_texto, font_titulo, font_item, font_contador):
        object_name = f"{titulo_texto.replace(' ', '')}Title"
        layout.addWidget(self.criar_titulo(titulo_texto, object_name, font_titulo))
        if df.empty:
            layout.addWidget(QLabel("Nenhum pedido.")); layout.addStretch()
            return
        
        for _, row in df.head(5).iterrows():
            texto = f"<b>PV: {row[COLUNA_PV]}</b> <font color='#FF6600'>({row[COLUNA_QTD]} máq.)</font>"
            label = QLabel(texto); label.setFont(font_item); layout.addWidget(label)
        
        if len(df) > 5:
            restantes = len(df) - 5
            contador_label = QLabel(f"+{restantes} pedidos...")
            contador_label.setObjectName("CounterLabel")
            contador_label.setFont(font_contador)
            layout.addWidget(contador_label)
        layout.addStretch()
    
    def desenhar_lista_lateral(self, layout, df, titulo_texto, font_titulo, font_item, font_contador, font_total, totais, limit=5):
        object_name = f"{titulo_texto.replace(' ', '')}Title"
        layout.addWidget(self.criar_titulo(titulo_texto, object_name, font_titulo))
        if df.empty: layout.addWidget(QLabel("Nenhum."))
        else:
            df_display = df.head(limit) if limit is not None else df
            for _, row in df_display.iterrows():
                texto = f"<b>PV: {row[COLUNA_PV]}</b> <font color='#2ECC71'>({row[COLUNA_QTD]} máq.)</font>"
                label = QLabel(texto); label.setFont(font_item); layout.addWidget(label)
            if limit is not None and len(df) > limit:
                restantes = len(df) - limit; contador_label = QLabel(f"+{restantes}..."); contador_label.setObjectName("CounterLabel"); contador_label.setFont(font_contador); layout.addWidget(contador_label)

        teravix, pv, total, teravix_qtd, pv_qtd, total_qtd = totais
        
        texto_total = (f"<font color='#FF6600'>TERAVIX:</font> {teravix} ({teravix_qtd})<br>"
                       f"<font color='#FF6600'>PV:</font> {pv} ({pv_qtd})<br>"
                       f"<b><font color='#3498DB'>TOTAL DIA:</font></b> <b>{total} ({total_qtd})</b>")

        total_label = QLabel(texto_total); total_label.setObjectName("TotalLabel"); total_label.setFont(font_total)
        layout.addWidget(total_label)
        layout.addStretch(1)

    def desenhar_dashboard(self, metricas, dados_grafico):
        self.limpar_layout(self.metricas_layout)
        self.limpar_layout(self.grafico_layout)
        self.limpar_layout(self.kpi_layout)
        
        titulo_metrica_font = QFont("Inter", self.scale(12), QFont.Bold)
        valor_metrica_font = QFont("Inter", self.scale(32), QFont.Bold)
        
        # --- Métricas ---
        total_mes_titulo = QLabel("Total Concluído no Mês")
        total_mes_titulo.setObjectName("MetricaTitle")
        total_mes_titulo.setFont(titulo_metrica_font)

        total_mes_valor_html = f"{metricas['total_mes_atual']:.0f} " \
                               f"<font color='#999' style='font-size:{self.scale(15)}px;'>({metricas['total_mes_atual_qtd']:.0f} máq.)</font>"
        total_mes_valor = QLabel(total_mes_valor_html)
        total_mes_valor.setObjectName("MetricaValue")
        total_mes_valor.setFont(valor_metrica_font)

        media_diaria_titulo = QLabel("Média Diária no Mês")
        media_diaria_titulo.setObjectName("MetricaTitle")
        media_diaria_titulo.setFont(titulo_metrica_font)

        media_diaria_valor_html = f"{metricas['media_diaria_atual']:.1f} " \
                                  f"<font color='#999' style='font-size:{self.scale(15)}px;'>({metricas['media_diaria_qtd']:.1f} máq.)</font>"
        media_diaria_valor = QLabel(media_diaria_valor_html)
        media_diaria_valor.setObjectName("MetricaValue")
        media_diaria_valor.setFont(valor_metrica_font)
        
        self.metricas_layout.addWidget(total_mes_titulo)
        self.metricas_layout.addWidget(total_mes_valor)
        self.metricas_layout.addStretch(1)
        self.metricas_layout.addWidget(media_diaria_titulo)
        self.metricas_layout.addWidget(media_diaria_valor)
        self.metricas_layout.addStretch(1)

        # --- Gráfico semanal ---
        titulo_grafico = QLabel(f"Desempenho Semanal (Meta: {META_SEMANAL} máq.)")
        titulo_grafico.setFont(titulo_metrica_font)
        self.grafico_layout.addWidget(titulo_grafico)

        start_of_current_week = datetime.now().date() - timedelta(days=datetime.now().weekday())
        for data, valor in dados_grafico:
            fim_semana = data + timedelta(days=6)
            texto_semana = f"Semana {data.strftime('%d/%m')} a {fim_semana.strftime('%d/%m')}"
            is_current_week = data.date() == start_of_current_week
            if is_current_week:
                texto_semana = f"<b>▶ {texto_semana}</b>"
            
            label_semana = QLabel(f"{texto_semana}: <b>{int(valor)}</b>")
            label_semana.setFont(QFont("Inter", self.scale(10)))
            
            progress_bar = QProgressBar()
            progress_bar.setRange(0, META_SEMANAL)
            progress_bar.setValue(min(int(valor), META_SEMANAL))
            progress_bar.setTextVisible(False)
            progress_bar.setFixedHeight(self.scale(18))
            progress_bar.setMaximumWidth(self.scale(550))
            if is_current_week:
                progress_bar.setObjectName("currentWeek")

            self.grafico_layout.addWidget(label_semana)
            self.grafico_layout.addWidget(progress_bar)
        self.grafico_layout.addStretch()

        # --- KPIs ---
        kpi_titulo_font = QFont("Inter", self.scale(11), QFont.Bold)
        kpi_valor_font = QFont("Inter", self.scale(12), QFont.Bold)

        # Recorde do mês
        recorde_titulo = QLabel("Recorde Diário no Mês")
        recorde_titulo.setObjectName("KpiTitle")
        recorde_titulo.setFont(kpi_titulo_font)

        recorde_valor_html = f"{metricas['recorde_dia_valor']} pedidos " \
                             f"<font color='#999'>({metricas['recorde_dia_qtd']} máq.)</font><br>" \
                             f"<span id='KpiRecorde'>{metricas['recorde_dia_data']}</span>"
        recorde_valor = QLabel(recorde_valor_html)
        recorde_valor.setObjectName("KpiValue")
        recorde_valor.setFont(kpi_valor_font)

        self.kpi_layout.addWidget(recorde_titulo)
        self.kpi_layout.addWidget(recorde_valor)
        self.kpi_layout.addStretch()

if __name__ == "__main__":
    locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')
    app = QApplication(sys.argv)
    window = PainelMtec()
    window.showMaximized()
    sys.exit(app.exec())
