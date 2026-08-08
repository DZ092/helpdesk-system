# 🖥️ Help Desk System

Sistema web para gerenciamento de chamados técnicos, desenvolvido para simular um ambiente real de suporte de TI.

A aplicação possui controle de acesso por perfil de usuário, dashboard com indicadores, histórico de chamados com busca e filtros, definição de prioridades, atendimento técnico, comentários internos, notificações automáticas por e-mail, um painel administrativo para gerenciamento de usuários e testes automatizados.

Este projeto foi desenvolvido para compor meu portfólio durante os estudos no curso de **Análise e Desenvolvimento de Sistemas**.

---

## 📋 Funcionalidades

- **Abertura pública de chamados**  
  Qualquer pessoa pode registrar um problema técnico sem precisar possuir uma conta.

- **Autenticação de usuários**  
  Sistema de cadastro, login e logout com armazenamento seguro das senhas utilizando hash.

- **Perfis de acesso**  
  Controle de permissões para Usuário, Técnico e Administrador.

- **Dashboard**  
  Exibição de indicadores com a quantidade total de chamados:

  - Abertos
  - Em andamento
  - Resolvidos

- **Chamados recentes**  
  Listagem dos últimos chamados cadastrados diretamente no dashboard.

- **Histórico de chamados**  
  Visualização de todos os chamados registrados no sistema.

- **Busca e filtros**  
  Pesquisa por título e filtragem dos chamados por status.

- **Controle de prioridade**  
  Cada chamado pode possuir uma das seguintes prioridades:

  - Baixa
  - Média
  - Alta
  - Crítica

- **Atendimento técnico**  
  Técnicos e administradores podem assumir chamados e atualizar o status do atendimento. Ao assumir um chamado, o técnico ou administrador é automaticamente registrado como responsável.

- **Meus Chamados**  
  Técnicos e administradores possuem uma tela dedicada mostrando apenas os chamados sob sua responsabilidade.

- **Comentários internos**  
  Registro do histórico de atendimento, contendo mensagem, autor e data do comentário.

- **Notificação por e-mail**  
  Técnicos e administradores recebem uma notificação automática quando um novo chamado é aberto.

- **Painel administrativo**  
  Administradores podem visualizar todos os usuários cadastrados, alterar o perfil de acesso de cada um (Usuário, Técnico ou Administrador) e excluir contas. O sistema impede que um administrador remova o próprio acesso ou exclua a própria conta, e bloqueia a exclusão de usuários que já possuem chamados ou comentários registrados.

- **Controle de acesso**  
  Apenas Técnicos e Administradores podem assumir chamados, alterar status, adicionar comentários internos e acessar "Meus Chamados". Apenas Administradores podem acessar o painel administrativo.

- **Testes automatizados**  
  Suíte de testes com pytest cobrindo autenticação, controle de acesso por perfil e a lógica de responsável do chamado.

---

## 🛠️ Tecnologias utilizadas

- Python
- Flask
- Flask-SQLAlchemy
- Flask-Mail
- Flask-WTF
- Python-dotenv
- SQLite
- SQLAlchemy
- Werkzeug
- Jinja2
- HTML5
- CSS3
- Pytest

---

## 📁 Estrutura do projeto

```text
helpdesk-system/
│
├── app.py
├── chamados.db
├── requirements.txt
├── .env
├── .gitignore
├── README.md
│
├── static/
│   └── css/
│       └── style.css
│
├── templates/
│   ├── index.html
│   ├── login.html
│   ├── cadastro.html
│   ├── dashboard.html
│   ├── chamado.html
│   ├── chamados.html
│   ├── detalhe_chamado.html
│   ├── admin_usuarios.html
│   └── meus_chamados.html
│
└── tests/
    ├── conftest.py
    └── test_app.py
```

> O arquivo `chamados.db` é criado automaticamente quando o banco de dados é inicializado.

---

## 🚀 Como executar localmente

### 1. Clone o repositório

```bash
git clone https://github.com/DZ092/helpdesk-system.git
```

Entre na pasta do projeto:

```bash
cd helpdesk-system
```

---

### 2. Crie um ambiente virtual

```bash
python -m venv venv
```

#### Windows — Prompt de Comando

```bash
venv\Scripts\activate
```

#### Windows — PowerShell

```powershell
.\venv\Scripts\Activate.ps1
```

#### Linux ou macOS

```bash
source venv/bin/activate
```

---

### 3. Instale as dependências

```bash
pip install -r requirements.txt
```

---

### 4. Configure as variáveis de ambiente

Crie um arquivo chamado `.env` na raiz do projeto:

```env
SECRET_KEY=adicione-uma-chave-secreta-segura
MAIL_USERNAME=seu-email@gmail.com
MAIL_PASSWORD=sua-senha-de-aplicativo-do-gmail
```

Para gerar uma chave secreta segura, execute:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

Copie o resultado e adicione no arquivo `.env`:

```env
SECRET_KEY=resultado-gerado-pelo-comando
```

> Para utilizar o envio de e-mails pelo Gmail, gere uma **Senha de App** na sua Conta Google. Não utilize a senha normal da sua conta.

---

### 5. Inicialize o banco de dados

Caso o projeto ainda não possua o arquivo `chamados.db`, execute:

```bash
python
```

Dentro do terminal interativo do Python, execute:

```python
from app import app, db

with app.app_context():
    db.create_all()
```

Depois, encerre o terminal:

```python
exit()
```

---

### 6. Execute a aplicação

```bash
python app.py
```

Acesse no navegador:

```text
http://127.0.0.1:5000
```

---

### 7. Execute os testes automatizados (opcional)

```bash
python -m pytest -v
```

---

## 👤 Perfis de usuário

| Perfil | Permissões |
|---|---|
| **Usuário** | Visualiza o dashboard e o histórico de chamados, mas não pode assumir chamados, alterar status ou adicionar comentários internos |
| **Técnico** | Visualiza todos os chamados, assume atendimentos, altera status, adiciona comentários internos e acessa "Meus Chamados" |
| **Administrador** | Possui as mesmas permissões operacionais do Técnico e pode administrar usuários pelo painel administrativo |

---

## 🔄 Status dos chamados

Os chamados podem possuir os seguintes status:

| Status | Descrição |
|---|---|
| **Aberto** | Chamado criado e aguardando atendimento |
| **Em andamento** | Chamado sendo analisado ou atendido por um técnico |
| **Resolvido** | Problema solucionado e atendimento finalizado |

---

## ⚠️ Prioridades

| Prioridade | Descrição |
|---|---|
| **Baixa** | Problema sem impacto significativo nas atividades |
| **Média** | Problema com impacto moderado |
| **Alta** | Problema que prejudica atividades importantes |
| **Crítica** | Problema urgente que impede a continuidade das operações |

---

## 📧 Configuração de e-mail

O sistema utiliza o servidor SMTP do Gmail para enviar notificações:

```python
MAIL_SERVER = "smtp.gmail.com"
MAIL_PORT = 587
MAIL_USE_TLS = True
```

As credenciais devem ser carregadas por variáveis de ambiente:

```python
MAIL_USERNAME = os.getenv("MAIL_USERNAME")
MAIL_PASSWORD = os.getenv("MAIL_PASSWORD")
```

Nunca adicione credenciais reais diretamente no código ou no repositório.

---

## 📦 Exemplo de `requirements.txt`

```text
Flask
Flask-Mail
Flask-SQLAlchemy
Flask-WTF
python-dotenv
SQLAlchemy
Werkzeug
pytest
```

Para gerar uma lista com as versões instaladas no seu ambiente:

```bash
pip freeze > requirements.txt
```

---

## 🔐 Exemplo de `.gitignore`

```gitignore
# Ambiente virtual
venv/
.venv/

# Variáveis de ambiente
.env

# Banco de dados local
*.db

# Cache do Python
__pycache__/
*.py[cod]

# Cache do pytest
.pytest_cache/

# Arquivos de IDE
.vscode/
.idea/

# Sistema operacional
.DS_Store
Thumbs.db
```

---

## 🎥 Demonstração

### Usuário comum

O usuário abre um chamado e acompanha o andamento do atendimento:

https://github.com/user-attachments/assets/7660a055-f4c3-4855-9f9f-6203c0f05648

### Técnico

O técnico visualiza, assume, atualiza e resolve os chamados:

https://github.com/user-attachments/assets/73b39249-7663-4c63-9df0-67f2d30e7677

### Administrador

O administrador possui as mesmas permissões operacionais do Técnico:

https://github.com/user-attachments/assets/cbdb6652-dc39-408b-9c74-736d42d47b45

**Notificação por e-mail** — login, abertura de um novo chamado e notificação automática chegando por e-mail. No vídeo também aparece um retorno de erro (bounce) de um dos destinatários de teste com endereço inválido — mostra que, quando o e-mail não pode ser entregue, o próprio provedor avisa sobre a falha:

https://github.com/user-attachments/assets/11be8267-3dad-4315-901a-92702644da3b

---

## 🔧 Melhorias futuras

- Exportação de relatórios em PDF ou Excel
- Upload de anexos nos chamados
- Recuperação de senha por e-mail
- Paginação da lista de chamados
- Filtros por prioridade, setor, responsável e período
- Registro de logs e auditoria
- API REST
- Responsividade para dispositivos móveis
- Deploy em ambiente de produção
- Utilização de PostgreSQL em produção
- Integração com serviços de armazenamento em nuvem

---

## 🔒 Segurança

As seguintes práticas são aplicadas ou recomendadas no projeto:

- Senhas armazenadas com hash
- Credenciais mantidas em variáveis de ambiente
- Controle de acesso baseado em perfil
- Validação de sessão nas rotas protegidas
- Proteção contra CSRF nos formulários
- Arquivo `.env` ignorado pelo Git
- Uso de uma chave secreta segura
- Senha de aplicativo específica para envio de e-mails

---

## 👨‍💻 Autor

**Eduardo Junior Coelho**

Estudante de **Análise e Desenvolvimento de Sistemas** — UniCesumar

GitHub: [DZ092](https://github.com/DZ092)

---

## 📄 Licença

Este projeto foi desenvolvido para fins educacionais e para composição de portfólio.