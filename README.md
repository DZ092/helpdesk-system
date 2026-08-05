# 🖥️ Help Desk System

Sistema de gerenciamento de chamados técnicos desenvolvido para simular um ambiente real de suporte de TI, com controle de acesso por perfil de usuário, dashboard com indicadores, histórico com busca e filtros, prioridades e comentários internos de atendimento.

Projeto desenvolvido como parte do meu portfólio, durante meus estudos de Análise e Desenvolvimento de Sistemas.

---

## 📋 Funcionalidades

- **Abertura de chamados pública** — qualquer usuário pode reportar um problema técnico, sem precisar de conta
- **Login com perfis de acesso** — Usuário, Técnico e Administrador, cada um com permissões diferentes
- **Dashboard** — indicadores de chamados abertos, em andamento e resolvidos, com lista dos mais recentes
- **Histórico de chamados** — busca por título e filtro por status
- **Prioridade** — Baixa, Média, Alta e Crítica
- **Atendimento** — técnicos podem assumir, atualizar e resolver chamados
- **Comentários internos** — histórico de atualizações dentro de cada chamado, com autor e data
- **Notificação por e-mail** — técnicos e administradores recebem um e-mail automático sempre que um novo chamado é aberto
- **Controle de acesso** — apenas Técnicos e Administradores podem alterar status e comentar

## 🛠️ Tecnologias

- Python
- Flask
- Flask-SQLAlchemy
- Flask-Mail
- SQLite
- Jinja2
- HTML5 / CSS3

## 📁 Estrutura do projeto

helpdesk-system/
│
├── app.py
├── chamados.db
├── requirements.txt
│
├── static/
│   └── css/
│       └── style.css
│
└── templates/
    ├── index.html
    ├── login.html
    ├── cadastro.html
    ├── dashboard.html
    ├── chamado.html
    ├── chamados.html
    └── detalhe_chamado.html

## 🚀 Como rodar localmente

git clone https://github.com/DZ092/helpdesk-system.git
cd helpdesk-system

python -m venv venv
venv\Scripts\activate

pip install -r requirements.txt

Crie um arquivo .env na raiz do projeto com suas próprias credenciais:

SECRET_KEY=uma-chave-aleatoria-qualquer-aqui
MAIL_USERNAME=seu-email@gmail.com
MAIL_PASSWORD=sua-senha-de-app-do-gmail

Depois, rode:

python app.py

Acesse em http://127.0.0.1:5000

## 👤 Perfis de usuário

| Perfil | Permissões |
|---|---|
| Usuário | Abre chamados e visualiza o histórico, mas não pode alterar status nem comentar |
| Técnico | Visualiza todos os chamados, assume, altera status e adiciona comentários internos |
| Administrador | Mesmas permissões de Técnico |

## 🎥 Demonstração

**Usuário comum** — abre chamado e acompanha status:

https://github.com/user-attachments/assets/7660a055-f4c3-4855-9f9f-6203c0f05648

**Técnico** — atende, atualiza e resolve chamados:

https://github.com/user-attachments/assets/73b39249-7663-4c63-9df0-67f2d30e7677

**Administrador** — mesmas permissões de Técnico:

https://github.com/user-attachments/assets/cbdb6652-dc39-408b-9c74-736d42d47b45

## 🔧 Possíveis melhorias futuras

- Exportação de relatórios
- Anexo de arquivos nos chamados
- Deploy em produção

## 👨‍💻 Autor

**Eduardo Junior Coelho**
Estudante de Análise e Desenvolvimento de Sistemas — UniCesumar
