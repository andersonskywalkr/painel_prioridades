Painel de Produção MTEC
Um sistema completo para gerenciamento de ordens de produção, composto por uma interface web para CRUD de pedidos e um painel de visualização em tempo real para TVs, ideal para acompanhamento na linha de produção.

🖼️ Telas do Projeto
Interface Web de Gerenciamento
A interface web permite a criação, edição, exclusão e reordenação de pedidos de forma intuitiva e rápida.

[Insira a imagem do site de gerenciamento aqui]

Legenda: Tela principal da interface web, mostrando a lista de pedidos em andamento com opções de filtro e edição.

Painel de Visualização (Dashboard para TV)
O painel é otimizado para telas grandes e atualiza automaticamente, mostrando o status da produção em tempo real para toda a equipe.

[Insira a imagem do painel de TV aqui]

Legenda: Dashboard de produção exibindo as prioridades, status e métricas de desempenho.

✨ Funcionalidades Principais
Gerenciamento Completo (CRUD): Crie, leia, atualize e delete pedidos através de uma interface web amigável.

Controle de Prioridade: Organize a fila de produção de forma interativa com botões para subir e descer a prioridade dos pedidos.

Status de Urgência: Destaque pedidos críticos para que sejam tratados com prioridade máxima.

Painel em Tempo Real: Um dashboard com atualização automática para visualização em TVs, mostrando o status atual da produção.

Histórico de Alterações: Rastreie todas as mudanças de status de cada pedido.

Filtros e Pesquisa: Encontre pedidos rapidamente por OP/PV, mês ou ano.

Ambiente Dockerizado: Todo o sistema (aplicação + banco de dados) roda em contêineres Docker, garantindo uma instalação e execução fáceis e consistentes em qualquer máquina.

🛠️ Tecnologias Utilizadas
Backend: Python com Flask

Banco de Dados: PostgreSQL

Frontend: HTML5, CSS3, JavaScript e Bootstrap 5

Painel (Dashboard TV): Python com PySide6 (Qt for Python)

Containerização: Docker e Docker Compose

Análise de Dados (Scripts): Pandas

🚀 Como Rodar o Projeto
Graças ao Docker, colocar o projeto para rodar é muito simples. Você só precisa ter o Docker Desktop instalado e funcionando na sua máquina.

Clone o Repositório:

git clone [https://github.com/andersonskywalkr/painel_mtec.git](https://github.com/andersonskywalkr/painel_mtec.git)

Navegue até a Pasta do Projeto:

cd painel_mtec

Suba os Contêineres:
Este comando irá construir a imagem da aplicação, baixar a imagem do PostgreSQL e iniciar os dois serviços em segundo plano.

docker compose up -d --build

Acesse a Aplicação:

A interface web estará disponível no seu navegador em: http://localhost:5000

As credenciais de login padrão são: admin / admin

(Opcional) Importe os Dados Iniciais:
Se for a primeira vez rodando o projeto, você pode popular o banco de dados com os pedidos da planilha Excel.

docker compose exec app python app/migracao_dados.py

Para Parar o Projeto:
Quando quiser desligar os serviços, execute:

docker compose down

📂 Estrutura do Projeto
.
├── app/
│   └── migracao_dados.py   # Script para importar dados da planilha Excel.
├── dados/
│   └── Status_dos_pedidos.xlsm # Planilha com os dados a serem importados.
├── templates/
│   └── index.html          # Frontend da aplicação web.
│   └── login.html          # Tela de login.
├── crud.py                 # Backend principal da aplicação Flask (APIs).
├── painel.py               # Código do dashboard de visualização para TV.
├── Dockerfile              # Receita para construir a imagem da aplicação.
├── docker-compose.yml      # Orquestra os serviços da aplicação e do banco.
└── requirements.txt        # Lista de dependências Python.
