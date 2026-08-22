# 🖥️ Help Desk System

![tests](https://github.com/DZ092/helpdesk-system/actions/workflows/tests.yml/badge.svg)

Sistema web para gerenciamento de chamados técnicos, desenvolvido para simular um ambiente real de suporte de TI.

A aplicação possui controle de acesso por perfil de usuário, dashboard com indicadores, histórico de chamados com busca, filtros e paginação, definição de prioridades, atendimento técnico, comentários internos, notificações automáticas por e-mail, um painel administrativo para gerenciamento de usuários, registro de logs e auditoria, e testes automatizados.

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
  Visualização de todos os chamados registrados no sistema, com paginação (15 chamados por página).

- **Busca e filtros**  
  Pesquisa por título e filtragem dos chamados por status, prioridade, setor, responsável e período (data inicial/final).

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

- **Troca de senha pelo próprio usuário**  
  Tela dedicada onde o usuário informa a senha atual e define uma nova. A troca
  encerra automaticamente as sessões abertas em outros dispositivos.

- **Recuperação de senha por e-mail**  
  Quem esquece a senha pede um link pela tela de login. O e-mail chega com um
  endereço assinado que vale por 1 hora e só funciona uma vez: o token carrega
  um HMAC do hash da senha atual, então redefinir a senha invalida o próprio
  link usado e qualquer outro ainda parado na caixa de entrada. A tela responde
  a mesma coisa para e-mail cadastrado ou não, para não revelar quem tem conta,
  e aceita no máximo 3 pedidos por endereço a cada 15 minutos.

- **Redefinição de senha por linha de comando**  
  Script `redefinir_senha.py` para o caso clássico de suporte: o usuário esqueceu
  a senha e não consegue entrar para trocá-la sozinho.

- **Registro de logs e auditoria**  
  O sistema registra automaticamente ações importantes (cadastro de usuário, login, abertura de chamado, mudança de status, comentário adicionado, alteração de perfil e exclusão de usuário), com data/hora e autor de cada ação. Administradores podem consultar esse histórico em uma tela dedicada.

- **Controle de acesso**  
  Apenas Técnicos e Administradores podem assumir chamados, alterar status, adicionar comentários internos e acessar "Meus Chamados". Apenas Administradores podem acessar o painel administrativo e os logs de auditoria.

- **Interface responsiva**  
  Layout adaptado para uso em celular. Nas telas de dashboard, histórico de
  chamados, "Meus Chamados", painel administrativo e logs de auditoria, as
  tabelas se reorganizam em cartões empilhados (rótulo + valor) em vez de
  colunas apertadas; os filtros e formulários passam a ocupar a largura
  inteira em coluna única, e os botões de navegação ganham área de toque
  maior. As tabelas ficam dentro de um container que rola sozinho quando o
  conteúdo não cabe, então nenhuma tela empurra a página inteira para o lado.

- **Tema dark**  
  Interface escura em todas as telas. As cores ficam em variáveis CSS
  (`--bg`, `--superficie`, `--acento`, `--texto`, além das faixas de status)
  declaradas uma única vez no topo do `style.css`, que é o mesmo arquivo
  carregado por todas as páginas — então mudar uma cor ali repinta dashboard,
  histórico, painel administrativo e logs de uma vez, sem cor solta espalhada
  pelos templates.

- **Tratamento próprio para login e cadastro**  
  Essas duas telas carregam também o `auth.css`, com os extras que só fazem
  sentido nelas: cartão estreito e centralizado, glows desfocados ao fundo,
  animação de entrada e ícones dentro dos campos. As telas de dados ficam de
  fora desse tratamento de propósito — ali o brilho decorativo atrapalharia a
  leitura.

- **Testes automatizados**  
  Suíte com 64 testes em pytest cobrindo autenticação, controle de acesso por
  perfil, validação de formulários, proteção CSRF, troca de senha e a lógica de
  responsável do chamado. Boa parte deles são testes de regressão, escritos para
  que falhas já corrigidas não voltem despercebidas. Um segundo arquivo,
  `test_rotas.py`, cobre o outro lado: visita todas as telas e o ciclo completo
  de um chamado, pegando o tipo de quebra que uma refatoração causa sem violar
  nenhuma regra de negócio. A suíte roda sozinha no
  GitHub Actions a cada push e a cada pull request para o `main` — o selo no
  topo deste README mostra o resultado da última execução.

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
- Waitress
- GitHub Actions

---

## 📁 Estrutura do projeto

```text
helpdesk-system/
│
├── .github/
│   └── workflows/
│       └── tests.yml
│
├── app.py
├── auditoria.py
├── render.yaml
├── constantes.py
├── emails.py
├── extensions.py
├── models.py
├── promover_admin.py
├── redefinir_senha.py
├── seguranca.py
├── serve.py
├── validacao.py
├── requirements.txt
├── requirements-dev.txt
├── .env.example
├── .gitignore
├── README.md
│
├── instance/
│   └── chamados.db
│
├── rotas/
│   ├── __init__.py
│   ├── admin.py
│   ├── auth.py
│   └── chamados.py
│
├── static/
│   └── css/
│       ├── style.css
│       └── auth.css
│
├── templates/
│   ├── index.html
│   ├── login.html
│   ├── cadastro.html
│   ├── dashboard.html
│   ├── chamado.html
│   ├── chamados.html
│   ├── detalhe_chamado.html
│   ├── esqueci_senha.html
│   ├── redefinir_senha.html
│   ├── admin_usuarios.html
│   ├── admin_logs.html
│   ├── alterar_senha.html
│   └── meus_chamados.html
│
└── tests/
    ├── conftest.py
    ├── test_app.py
    └── test_rotas.py
```

> A pasta `instance/` e o arquivo `chamados.db` são criados automaticamente na
> primeira execução. Ambos ficam fora do controle de versão.

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

Copie o modelo `.env.example` para `.env` e preencha os valores:

```bash
cp .env.example .env      # Windows: copy .env.example .env
```

O conteúdo esperado é:

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

O `app.py` não cria a aplicação na importação: ele expõe a fábrica
`create_app()`, e quem precisa de uma instância a constrói — o `python app.py`,
o `serve.py` e a suíte de testes, cada um com a configuração que lhe cabe.

O modo debug fica **desligado** por padrão. Para ligá-lo durante o
desenvolvimento, defina `FLASK_DEBUG=1` no `.env`. Nunca ligue o debug em
produção: o debugger do Werkzeug permite execução remota de código.

> Com o debug desligado, o Jinja compila cada template uma única vez, na subida
> da aplicação. Isso significa que editar um `.html` não muda nada até reiniciar
> o servidor — ligar `FLASK_DEBUG=1` durante o desenvolvimento evita essa
> confusão, porque o servidor recarrega sozinho a cada arquivo salvo.

Acesse no navegador:

```text
http://127.0.0.1:5000
```

#### Rodando com um servidor de produção (opcional)

O `app.py` sobe o servidor embutido do Flask, que existe só para
desenvolvimento — ele avisa isso no terminal toda vez. Para ver a aplicação
como ela rodaria em produção, use o **Waitress**, um servidor WSGI multithread
que funciona bem no Windows:

```bash
python serve.py
```

Acesse `http://127.0.0.1:8000`. Host, porta e número de threads são ajustáveis
por `HOST`, `PORT` e `THREADS` no `.env`.

O Waitress não recarrega ao salvar arquivo: reinicie o processo a cada mudança,
ou volte ao `python app.py` enquanto estiver desenvolvendo.

---

### 7. Crie o primeiro administrador

O cadastro público sempre cria contas com o perfil **Usuário** — o formulário
não escolhe o perfil. Para promover a primeira conta a Administrador, use o
script auxiliar:

```bash
python promover_admin.py
```

A partir daí, os demais perfis são definidos pelo painel administrativo.

Se alguém esquecer a senha, use:

```bash
python redefinir_senha.py
```

---

### 8. Execute os testes automatizados (opcional)

```bash
pip install -r requirements-dev.txt
python -m pytest -v
```

Esperado: **64 passed**.

Os testes rodam sempre contra um banco SQLite em memória e nunca tocam o
`instance/chamados.db` de desenvolvimento — há inclusive uma trava que aborta a
suíte se detectar que a engine aponta para um arquivo real.

---

## ☁️ Deploy

A aplicação roda em produção com o **Waitress** (`serve.py`) e **PostgreSQL**,
sem mudança de código: o banco vem da variável `DATABASE_URL` e o restante da
configuração também sai do ambiente.

O `render.yaml` na raiz descreve o serviço — comando de build, comando de start
e as variáveis necessárias —, então a plataforma se configura sozinha ao
conectar o repositório. As variáveis sensíveis ficam marcadas como `sync: false`
e são preenchidas no painel, nunca no repositório:

| Variável | Para quê |
|---|---|
| `SECRET_KEY` | assina o cookie de sessão; sem ela a aplicação se recusa a subir |
| `DATABASE_URL` | conexão do PostgreSQL |
| `MAIL_USERNAME` e `MAIL_PASSWORD` | envio das notificações |
| `SESSION_COOKIE_SECURE=1` | cookie de sessão só trafega por HTTPS |

> A URL entregue pelos provedores começa com `postgres://`, esquema que o
> SQLAlchemy 2 não aceita mais. A função `_url_do_banco()` no `app.py` faz a
> troca para `postgresql://` — sem ela, a aplicação sobe e só quebra na
> primeira consulta.

> Em planos gratuitos o serviço hiberna após alguns minutos sem acesso, e o
> primeiro carregamento seguinte pode levar cerca de um minuto.

---

## 👤 Perfis de usuário

| Perfil | Permissões |
|---|---|
| **Usuário** | Visualiza o dashboard e o histórico de chamados e troca a própria senha, mas não pode assumir chamados, alterar status ou adicionar comentários internos |
| **Técnico** | Visualiza todos os chamados, assume atendimentos, altera status, adiciona comentários internos e acessa "Meus Chamados" |
| **Administrador** | Possui as mesmas permissões operacionais do Técnico e pode administrar usuários e consultar os logs de auditoria pelo painel administrativo |

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

## 🔒 Decisões de segurança

- **Perfil nunca vem do formulário.** O cadastro é público, então aceitar o
  campo `tipo_usuario` do cliente permitiria que qualquer visitante criasse a
  própria conta de Administrador. Toda conta nova nasce como Usuário.
- **CSRF em todos os formulários.** O Flask-WTF valida um token em cada POST,
  o que impede que outro site force ações na sessão de um usuário logado.
- **Perfil relido do banco a cada requisição.** O cookie de sessão guarda só o
  id do usuário; o perfil vem do banco, então rebaixar ou excluir uma conta
  passa a valer na hora, sem esperar o logout.
- **`SECRET_KEY` obrigatória.** Sem uma chave imprevisível é possível forjar o
  cookie de sessão, então a aplicação se recusa a subir sem ela em vez de usar
  um valor padrão conhecido.
- **Cookie de sessão endurecido:** `HttpOnly`, `SameSite=Lax`, expiração em 8
  horas e `Secure` quando `SESSION_COOKIE_SECURE=1`.
- **Nada de HTML montado por concatenação em JavaScript.** Valores vindos do
  banco vão para atributos `data-*` e são lidos pelo script, o que evita XSS
  armazenado via nome de usuário.
- **Trocar a senha derruba as outras sessões.** O cookie carrega uma assinatura
  HMAC derivada do hash da senha; ao trocar a senha o hash muda, a assinatura
  deixa de bater e os cookies antigos param de valer. Sem isso, trocar a senha
  porque ela vazou não adiantaria nada — quem já estivesse logado continuaria
  dentro.
- **Senha atual exigida para trocar de senha.** Impede que alguém com a sessão
  sequestrada — ou diante de um computador destravado — tome a conta.
- **Política de senha no servidor.** Mínimo de 8 caracteres, nunca só números
  nem só letras, bloqueio das senhas mais comuns e recusa de senhas que contenham
  o nome ou o e-mail do próprio usuário.
- **Limite de tentativas na troca de senha.** Cinco erros da senha atual
  bloqueiam a operação por 5 minutos, e cada tentativa vai para os logs.
- **Limite de tentativas de login.** Cinco senhas erradas para o mesmo e-mail
  bloqueiam novas tentativas de login por 5 minutos, dificultando força bruta
  contra uma conta.
- **Link de redefinição sem tabela de tokens.** O token é assinado com a
  `SECRET_KEY` e carrega o id do usuário mais um HMAC do hash da senha atual.
  Isso dá uso único de graça: a redefinição muda o hash, o HMAC deixa de bater
  e o link morre — sem precisar guardar, marcar como usado nem limpar tokens
  vencidos no banco.
- **A tela de recuperação não revela quem tem conta.** A resposta é idêntica
  para um e-mail cadastrado e para um desconhecido; a diferença fica só no log
  de auditoria, que é interno.
- **Redefinição não faz login automático.** Abrir o link permite escolher a
  senha, não entrar: quem redefine prova que sabe a senha nova usando-a no
  login.
- **Senhas com hash `scrypt`** (padrão do Werkzeug), nunca em texto puro.

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
venv/
.venv/
__pycache__/
*.pyc
.pytest_cache/
instance/
chamados.db
.vscode/
.env
*.7z
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
- API REST
- Migrações de banco com Flask-Migrate
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
- Registro de logs e auditoria das ações administrativas

---

## 👨‍💻 Autor

**Eduardo Junior Coelho**

Estudante de **Análise e Desenvolvimento de Sistemas** — UniCesumar

GitHub: [DZ092](https://github.com/DZ092)

---

## 📄 Licença

Este projeto foi desenvolvido para fins educacionais e para composição de portfólio.