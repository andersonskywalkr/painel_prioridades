<h1 align="center">📊 Painel de Produção MTEC</h1>

<p align="center">
  Um sistema completo para <strong>gerenciamento de ordens de produção</strong>, composto por:
</p>

<ul>
  <li>🖥️ <strong>Interface Web</strong> para CRUD de pedidos.</li>
  <li>📺 <strong>Painel de Visualização em tempo real</strong> para TVs, ideal para acompanhamento na linha de produção.</li>
</ul>

<hr>

<h2>🖼️ Telas do Projeto</h2>

<h3>🌐 Interface Web de Gerenciamento</h3>
<p>
  A interface web permite a criação, edição, exclusão e reordenação de pedidos de forma intuitiva e rápida.
</p>
<p align="center">[Insira a imagem do site de gerenciamento aqui]</p>
<p align="center"><em>Tela principal da interface web, mostrando a lista de pedidos em andamento com opções de filtro e edição.</em></p>

<h3>📺 Painel de Visualização (Dashboard para TV)</h3>
<p>
  O painel é otimizado para telas grandes e atualiza automaticamente, mostrando o status da produção em tempo real para toda a equipe.
</p>
<p align="center">[Insira a imagem do painel de TV aqui]</p>
<p align="center"><em>Dashboard de produção exibindo as prioridades, status e métricas de desempenho.</em></p>

<hr>

<h2>✨ Funcionalidades Principais</h2>

<ul>
  <li><strong>Gerenciamento Completo (CRUD):</strong> Crie, leia, atualize e delete pedidos através de uma interface web amigável.</li>
  <li><strong>Controle de Prioridade:</strong> Organize a fila de produção de forma interativa com botões para subir e descer a prioridade dos pedidos.</li>
  <li><strong>Status de Urgência:</strong> Destaque pedidos críticos para que sejam tratados com prioridade máxima.</li>
  <li><strong>Painel em Tempo Real:</strong> Dashboard com atualização automática para TVs, mostrando o status atual da produção.</li>
  <li><strong>Histórico de Alterações:</strong> Rastreie todas as mudanças de status de cada pedido.</li>
  <li><strong>Filtros e Pesquisa:</strong> Encontre pedidos rapidamente por OP/PV, mês ou ano.</li>
  <li><strong>Ambiente Dockerizado:</strong> Todo o sistema roda em contêineres Docker, garantindo fácil instalação e execução em qualquer máquina.</li>
</ul>

<hr>

<h2>🛠️ Tecnologias Utilizadas</h2>

<ul>
  <li><strong>Backend:</strong> Python com Flask</li>
  <li><strong>Banco de Dados:</strong> PostgreSQL</li>
  <li><strong>Frontend:</strong> HTML5, CSS3, JavaScript e Bootstrap 5</li>
  <li><strong>Painel (Dashboard TV):</strong> Python com PySide6 (Qt for Python)</li>
  <li><strong>Containerização:</strong> Docker e Docker Compose</li>
  <li><strong>Análise de Dados:</strong> Pandas</li>
</ul>

<hr>

<h2>🚀 Como Rodar o Projeto</h2>

<p>Graças ao Docker, colocar o projeto para rodar é muito simples. Você só precisa ter o <strong>Docker Desktop</strong> instalado e funcionando na sua máquina.</p>

<ol>
  <li><strong>Clone o Repositório:</strong></li>

bash
  git clone https://github.com/andersonskywalkr/painel_mtec.git
<li><strong>Navegue até a Pasta do Projeto:</strong></li>
bash
Copiar código
cd painel_mtec
<li><strong>Suba os Contêineres:</strong></li> <p>Este comando irá construir a imagem da aplicação, baixar a imagem do PostgreSQL e iniciar os dois serviços em segundo plano.</p>
bash
Copiar código
docker compose up -d --build
<li><strong>Acesse a Aplicação:</strong></li> <p>A interface web estará disponível em: <a href="http://localhost:5000" target="_blank">http://localhost:5000</a></p> <p>Credenciais padrão: <code>admin / admin</code></p> <li><strong>(Opcional) Importe os Dados Iniciais:</strong></li> <p>Se for a primeira vez rodando o projeto:</p>
bash
Copiar código
docker compose exec app python app/migracao_dados.py
<li><strong>Parar o Projeto:</strong></li>
bash
Copiar código
docker compose down
</ol> <hr> <h2>📂 Estrutura do Projeto</h2>
bash
Copiar código
.
├── app/
│   └── migracao_dados.py        # Script para importar dados da planilha Excel
├── dados/
│   └── Status_dos_pedidos.xlsm  # Planilha com os dados a serem importados
├── templates/
│   ├── index.html               # Frontend da aplicação web
│   └── login.html               # Tela de login
├── crud.py                      # Backend principal da aplicação Flask (APIs)
├── painel.py                    # Código do dashboard de visualização para TV
├── Dockerfile                   # Receita para construir a imagem da aplicação
├── docker-compose.yml           # Orquestra os serviços da aplicação e do banco
└── requirements.txt             # Lista de dependências Python
