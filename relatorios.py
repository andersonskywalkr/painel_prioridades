import sys
import os
import sqlite3
import pandas as pd
from datetime import datetime
import locale
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                               QHBoxLayout, QLabel, QFrame, QPushButton,
                               QDateEdit, QTextEdit, QCalendarWidget)
from PySide6.QtGui import QFont
from PySide6.QtCore import Qt, QDate, QTimer

# --- CONFIGURAÇÃO DE CAMINHOS ---
# --- ALTERAÇÃO: Lógica para usar fonte de dados local ou online ---
USAR_LINK_ONLINE = False  # Mude para True para usar o link abaixo

LINK_PLANILHA_ONLINE = "COLE_SEU_LINK_DIRETO_AQUI"

if getattr(sys, 'frozen', False):
    script_dir = os.path.dirname(sys.executable)
else:
    script_dir = os.path.dirname(os.path.abspath(__file__))

CAMINHO_PASTA_DADOS = os.path.join(script_dir, "dados")

if USAR_LINK_ONLINE:
    CAMINHO_PLANILHA_STATUS = LINK_PLANILHA_ONLINE
    print(f"INFO: Usando planilha online do link.")
else:
    NOME_ARQUIVO_STATUS = "Status_dos_pedidos.xlsm"
    CAMINHO_PLANILHA_STATUS = os.path.join(CAMINHO_PASTA_DADOS, NOME_ARQUIVO_STATUS)
    print(f"INFO: Usando planilha local: {CAMINHO_PLANILHA_STATUS}")

NOME_ARQUIVO_BANCO_DE_DADOS = "producao.db"
CAMINHO_BANCO_DE_DADOS = os.path.join(CAMINHO_PASTA_DADOS, NOME_ARQUIVO_BANCO_DE_DADOS)


# --- ESTILO VISUAL (Reutilizado do painel principal) ---
STYLESHEET = """
    QMainWindow { background-color: #1C1C1C; } 
    QLabel { color: #E0E0E0; font-family: Inter; }
    #Header { background-color: #2E2E2E; border-bottom: 2px solid #FF6600; }
    #LogoLabel { padding: 5px; } 
    .SectionTitle { 
        color: #FF8C33; 
        font-size: 16px; 
        font-weight: bold; 
        margin-bottom: 5px;
    }
    QDateEdit {
        background-color: #2E2E2E;
        color: #E0E0E0;
        border: 1px solid #555;
        border-radius: 4px;
        padding: 5px;
        font-size: 14px;
        font-family: Inter;
    }
    QCalendarWidget {
        background-color: #2E2E2E;
        color: #E0E0E0;
        font-family: Inter;
    }
    QTextEdit {
        background-color: #252525;
        color: #E0E0E0;
        border: 1px solid #555;
        border-radius: 4px;
        font-size: 14px;
        font-family: Inter;
        padding: 10px;
    }
    QPushButton {
        background-color: #3498DB; 
        color: white; 
        border: none; 
        padding: 8px 12px; 
        border-radius: 4px; 
        font-weight: bold;
        font-size: 14px;
        font-family: Inter;
    }
    QPushButton:hover { background-color: #2980B9; }
    #CopyButton { background-color: #27AE60; }
    #CopyButton:hover { background-color: #229954; }
"""

class GeradorRelatorios(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Gerador de Relatórios MTEC")
        self.setGeometry(200, 200, 700, 550)
        self.setStyleSheet(STYLESHEET)
        self.setup_ui()

    def setup_ui(self):
        # --- Layout Principal ---
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        main_layout = QVBoxLayout(self.central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # --- Cabeçalho ---
        header = QWidget()
        header.setObjectName("Header")
        header.setFixedHeight(60)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(20, 0, 20, 0)
        logo_label = QLabel("mtec.")
        logo_label.setObjectName("LogoLabel")
        logo_label.setFont(QFont("Inter", 22, QFont.Bold))
        header_layout.addWidget(logo_label)
        header_layout.addStretch()
        main_layout.addWidget(header)

        # --- Corpo da Aplicação ---
        body_widget = QWidget()
        body_layout = QVBoxLayout(body_widget)
        body_layout.setContentsMargins(20, 20, 20, 20)
        body_layout.setSpacing(15)
        main_layout.addWidget(body_widget, 1)

        # --- Seção de Seleção de Data ---
        date_section_label = QLabel("Selecione o Período")
        date_section_label.setProperty("class", "SectionTitle")
        body_layout.addWidget(date_section_label)

        date_layout = QHBoxLayout()
        self.start_date_edit = QDateEdit(calendarPopup=True)
        self.start_date_edit.setDate(QDate.currentDate())
        self.end_date_edit = QDateEdit(calendarPopup=True)
        self.end_date_edit.setDate(QDate.currentDate())
        
        date_layout.addWidget(QLabel("De:"))
        date_layout.addWidget(self.start_date_edit)
        date_layout.addWidget(QLabel("Até:"))
        date_layout.addWidget(self.end_date_edit)
        date_layout.addStretch()
        body_layout.addLayout(date_layout)

        # --- Botão de Gerar Relatório ---
        self.generate_button = QPushButton("Gerar Relatório")
        self.generate_button.clicked.connect(self.gerar_relatorio)
        body_layout.addWidget(self.generate_button, 0, Qt.AlignmentFlag.AlignLeft)

        # --- Seção do Relatório Gerado ---
        report_section_label = QLabel("Relatório Gerado")
        report_section_label.setProperty("class", "SectionTitle")
        body_layout.addWidget(report_section_label)

        self.report_text_edit = QTextEdit()
        self.report_text_edit.setReadOnly(True)
        body_layout.addWidget(self.report_text_edit, 1)

        # --- Botão de Copiar ---
        self.copy_button = QPushButton("Copiar Texto")
        self.copy_button.setObjectName("CopyButton")
        self.copy_button.clicked.connect(self.copiar_texto)
        body_layout.addWidget(self.copy_button, 0, Qt.AlignmentFlag.AlignRight)

    def buscar_dados_db(self, start_date, end_date):
        """Busca os dados no banco de dados SQLite dentro do intervalo de datas."""
        if not os.path.exists(CAMINHO_BANCO_DE_DADOS):
            return None, "Erro: Arquivo de banco de dados 'producao.db' não encontrado."

        try:
            conexao = sqlite3.connect(CAMINHO_BANCO_DE_DADOS)
            query = "SELECT * FROM concluidos WHERE date(data_conclusao) BETWEEN ? AND ?"
            
            start_date_str = start_date.toString("yyyy-MM-dd")
            end_date_str = end_date.toString("yyyy-MM-dd")

            df = pd.read_sql_query(query, conexao, params=(start_date_str, end_date_str))
            conexao.close()
            return df, None
        except Exception as e:
            return None, f"Erro ao conectar ou ler o banco de dados: {e}"

    def buscar_dados_backlog(self):
        """Busca todos os pedidos com status 'Aguardando Montagem' ou 'Em Montagem'."""
        try:
            # Lê diretamente do caminho, seja local ou online
            df = pd.read_excel(CAMINHO_PLANILHA_STATUS, engine='openpyxl')

            df.columns = df.columns.str.strip()
            
            status_backlog = ['Aguardando Montagem', 'Em Montagem']
            df_backlog = df[df['Status'].isin(status_backlog)].copy()
            
            return df_backlog, None
        except Exception as e:
            return None, f"Erro ao ler a planilha de status: {e}"

    def gerar_relatorio(self):
        """Função principal que é chamada ao clicar no botão."""
        start_date = self.start_date_edit.date()
        end_date = self.end_date_edit.date()

        df_concluidos, error_db = self.buscar_dados_db(start_date, end_date)
        df_backlog, error_backlog = self.buscar_dados_backlog()

        if error_db:
            self.report_text_edit.setText(error_db)
            return
        if error_backlog:
            self.report_text_edit.setText(error_backlog)
            return
        
        atividades_realizadas = []
        if not df_concluidos.empty:
            df_concluidos['pv'] = df_concluidos['pv'].astype(str)
            teravix_df = df_concluidos[df_concluidos['pv'].str.contains("TERAVIX", na=False)]
            pv_df = df_concluidos[~df_concluidos['pv'].str.contains("TERAVIX", na=False)]

            num_ops = len(teravix_df)
            unidades_ops = teravix_df['qtd_maquinas'].sum()
            num_pvs = len(pv_df)
            unidades_pvs = pv_df['qtd_maquinas'].sum()

            if num_pvs > 0:
                plural_pv = "'s" if num_pvs > 1 else ""
                atividades_realizadas.append(f"• {num_pvs} PV{plural_pv} com {unidades_pvs} unidades")
            if num_ops > 0:
                plural_op = "'s" if num_ops > 1 else ""
                atividades_realizadas.append(f"• {num_ops} OP{plural_op} com {unidades_ops} unidades de Teravix")
        
        atividades_backlog = []
        if not df_backlog.empty:
            df_backlog['PV'] = df_backlog['PV'].astype(str)
            teravix_backlog_df = df_backlog[df_backlog['PV'].str.contains("TERAVIX", na=False)]
            pv_backlog_df = df_backlog[~df_backlog['PV'].str.contains("TERAVIX", na=False)]

            num_ops_backlog = len(teravix_backlog_df)
            unidades_ops_backlog = teravix_backlog_df['Qtd Maquinas'].sum()
            num_pvs_backlog = len(pv_backlog_df)
            unidades_pvs_backlog = pv_backlog_df['Qtd Maquinas'].sum()

            if num_pvs_backlog > 0:
                plural_pv = "'s" if num_pvs_backlog > 1 else ""
                atividades_backlog.append(f"• {num_pvs_backlog} PV{plural_pv} com {unidades_pvs_backlog} unidades")
            if num_ops_backlog > 0:
                plural_op = "'s" if num_ops_backlog > 1 else ""
                atividades_backlog.append(f"• {num_ops_backlog} OP{plural_op} com {unidades_ops_backlog} unidades de Teravix")

        dias_semana = {
            'Monday': 'Segunda-feira', 'Tuesday': 'Terça-feira', 'Wednesday': 'Quarta-feira',
            'Thursday': 'Quinta-feira', 'Friday': 'Sexta-feira', 'Saturday': 'Sábado', 'Sunday': 'Domingo'
        }
        dia_en = start_date.toString("dddd")
        dia_pt = dias_semana.get(dia_en, dia_en)

        if start_date == end_date:
            data_titulo = f"{dia_pt}, dia {start_date.toString('dd/MM')}"
        else:
            data_titulo = f"período de {start_date.toString('dd/MM')} a {end_date.toString('dd/MM')}"
        
        titulo = f"Relatório de Atividades - {data_titulo}."

        corpo_realizadas = "Nenhuma atividade realizada no período."
        if atividades_realizadas:
            corpo_realizadas = "Atividades Realizadas:\n" + "\n".join(atividades_realizadas)
        
        corpo_backlog = "Backlog:\nNenhuma atividade futura na fila."
        if atividades_backlog:
            corpo_backlog = "Backlog:\n" + "\n".join(atividades_backlog)
        
        texto_final = f"{titulo}\n\n{corpo_realizadas}\n\n{corpo_backlog}"
        self.report_text_edit.setText(texto_final)

    def copiar_texto(self):
        """Copia o texto gerado para a área de transferência."""
        clipboard = QApplication.clipboard()
        clipboard.setText(self.report_text_edit.toPlainText())
        self.copy_button.setText("Copiado!")
        QTimer.singleShot(2000, lambda: self.copy_button.setText("Copiar Texto"))


if __name__ == '__main__':
    app = QApplication(sys.argv)
    try: 
        locale.setlocale(locale.LC_TIME, 'pt_BR.UTF-8')
    except locale.Error: 
        print("Aviso: Local 'pt_BR.UTF-8' não pôde ser definido.")
    
    window = GeradorRelatorios()
    window.show()
    sys.exit(app.exec())
