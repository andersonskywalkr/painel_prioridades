Painel de Produção e Gerador de Relatórios MTEC
Este projeto contém dois programas principais:

prioridades.py: Um painel de visualização em tempo real para o status da produção.

relatorios.py: Uma ferramenta para gerar relatórios de atividades a partir dos dados de produção.

Instalação
Para garantir que os dois programas funcionem corretamente, você precisa instalar as seguintes bibliotecas Python.

Comando de Instalação
Abra o seu terminal (CMD, PowerShell, etc.) e execute o seguinte comando:

pip install pandas PySide6 numpy watchdog openpyxl

Detalhes das Bibliotecas
pandas: Utilizada para ler e manipular os dados da planilha Excel.

PySide6: A biblioteca principal para a criação de toda a interface gráfica dos programas.

numpy: Uma dependência do pandas, essencial para operações numéricas.

watchdog: Usada pelo painel principal para detectar automaticamente quando a planilha de status é modificada.

openpyxl: Necessária para que o pandas consiga ler e escrever em arquivos Excel (.xlsx, .xlsm).

Após a instalação, você poderá executar os dois scripts Python sem problemas.