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
- **Controle de acesso** — apenas Técnicos e Administradores podem alterar status e comentar

## 🛠️ Tecnologias

- Python
- Flask
- Flask-SQLAlchemy
- SQLite
- Jinja2
- HTML5 / CSS3

## 📁 Estrutura do projeto

```
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
```

## 🚀 Como rodar localmente

```bash
git clone https://github.com/DZ092/helpdesk-system.git
cd helpdesk-system

python -m venv venv
venv\Scripts\activate

pip install -r requirements.txt

python app.py
```

Acesse em `http://127.0.0.1:5000`

## 👤 Perfis de usuário

| Perfil | Permissões |
|---|---|
| Usuário | Abre chamados, visualiza o próprio histórico |
| Técnico | Visualiza todos os chamados, altera status, adiciona comentários |
| Administrador | Mesmas permissões de Técnico |

## 📸 Prints do sistema

*(adicionar aqui: tela de login, dashboard, abertura de chamado, histórico e detalhe do chamado)*

## 🔧 Possíveis melhorias futuras

- Notificações por e-mail
- Exportação de relatórios
- Anexo de arquivos nos chamados
- Deploy em produção

## 👨‍💻 Autor

**Eduardo Junior Coelho**
Estudante de Análise e Desenvolvimento de Sistemas — UniCesumar