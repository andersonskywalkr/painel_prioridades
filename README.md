# 📊 Painel de Produção MTEC

Um sistema completo para **gerenciamento de ordens de produção**, composto por:  
- **Interface Web** para CRUD de pedidos.  
- **Painel de Visualização em tempo real** para TVs, ideal para acompanhamento na linha de produção.  

---

## 🖼️ Telas do Projeto

### 🌐 Interface Web de Gerenciamento
A interface web permite a criação, edição, exclusão e reordenação de pedidos de forma intuitiva e rápida.  

![Interface Web](link-da-imagem-aqui)  
*Legenda: Tela principal da interface web, mostrando a lista de pedidos em andamento com opções de filtro e edição.*

---

### 📺 Painel de Visualização (Dashboard para TV)
O painel é otimizado para telas grandes e atualiza automaticamente, mostrando o status da produção em tempo real para toda a equipe.  

![Painel TV](link-da-imagem-aqui)  
*Legenda: Dashboard de produção exibindo as prioridades, status e métricas de desempenho.*

---

## ✨ Funcionalidades Principais

- **Gerenciamento Completo (CRUD):** Crie, leia, atualize e delete pedidos através de uma interface web amigável.  
- **Controle de Prioridade:** Organize a fila de produção de forma interativa com botões para subir e descer a prioridade dos pedidos.  
- **Status de Urgência:** Destaque pedidos críticos para que sejam tratados com prioridade máxima.  
- **Painel em Tempo Real:** Dashboard com atualização automática para TVs.  
- **Histórico de Alterações:** Rastreie todas as mudanças de status de cada pedido.  
- **Filtros e Pesquisa:** Encontre pedidos rapidamente por OP/PV, mês ou ano.  
- **Ambiente Dockerizado:** Aplicação + banco de dados rodando em contêineres Docker para fácil instalação e execução.  

---

## 🛠️ Tecnologias Utilizadas

- **Backend:** Python (Flask)  
- **Banco de Dados:** PostgreSQL  
- **Frontend:** HTML5, CSS3, JavaScript, Bootstrap 5  
- **Painel (Dashboard TV):** Python (PySide6 - Qt for Python)  
- **Containerização:** Docker e Docker Compose  
- **Análise de Dados:** Pandas  

---

## 🚀 Como Rodar o Projeto

Com **Docker**, rodar o projeto é muito simples. Basta ter o **Docker Desktop** instalado e funcionando.  

### 1. Clone o repositório
```bash
git clone https://github.com/andersonskywalkr/painel_mtec.git
