SENHA_PADRAO = "senha-de-teste"


def cadastrar_usuario(client, nome="Fulano", email="fulano@teste.com", senha=SENHA_PADRAO, **extra):
    dados = {"nome": nome, "email": email, "senha": senha}
    dados.update(extra)
    return client.post("/cadastro", data=dados, follow_redirects=True)


def fazer_login(client, email="fulano@teste.com", senha=SENHA_PADRAO):
    return client.post(
        "/login",
        data={"email": email, "senha": senha},
        follow_redirects=True,
    )


def abrir_chamado(client, titulo="Computador não liga", prioridade="Alta"):
    return client.post(
        "/chamado",
        data={
            "usuario": "Maria",
            "setor": "Financeiro",
            "titulo": titulo,
            "descricao": "Tela preta ao ligar",
            "prioridade": prioridade,
        },
        follow_redirects=True,
    )


# ==============================================================================
# AUTENTICAÇÃO E ACESSO
# ==============================================================================
def test_dashboard_exige_login(client):
    resposta = client.get("/dashboard", follow_redirects=True)
    assert b"Login" in resposta.data


def test_cadastro_e_login(client):
    cadastrar_usuario(client)
    resposta = fazer_login(client)
    assert resposta.status_code == 200
    assert b"Dashboard" in resposta.data


def test_cadastro_envia_email_de_boas_vindas(client):
    """Não passa pela rota HTTP de propósito: o envio roda numa thread
    separada (ver emails.py), e testar via rota correria contra ela. Chamamos
    a função direto, no mesmo espírito dos outros testes de e-mail do projeto."""
    from emails import enviar_email_boas_vindas
    from extensions import mail
    from models import Usuario

    with client.application.app_context():
        client.application.config["MAIL_USERNAME"] = "helpdesk@teste.com"
        # O Flask-Mail guarda o remetente padrão num objeto interno montado na
        # inicialização do app (mail.init_app), não relido do config depois —
        # mesmo objeto que o conftest.py já mexe pra ligar o `suppress`.
        client.application.extensions["mail"].default_sender = "helpdesk@teste.com"
        usuario = Usuario(nome="Fulano", email="fulano@teste.com", senha="hash", tipo_usuario="Usuário")

        with mail.record_messages() as caixa_de_saida:
            enviar_email_boas_vindas(usuario)
            import time
            time.sleep(0.1)  # dá tempo da thread de envio rodar

        assert len(caixa_de_saida) == 1
        assert caixa_de_saida[0].recipients == ["fulano@teste.com"]


def test_login_com_senha_errada(client):
    cadastrar_usuario(client)
    resposta = fazer_login(client, senha="senha-errada")
    assert "inv".encode() in resposta.data.lower()


def test_tentativas_repetidas_de_login_bloqueiam(client):
    from constantes import MAX_TENTATIVAS_LOGIN

    email = "forca-login@teste.com"
    cadastrar_usuario(client, email=email)

    for _ in range(MAX_TENTATIVAS_LOGIN):
        fazer_login(client, email=email, senha="senha-errada")

    resposta = fazer_login(client, email=email, senha="senha-errada")
    assert "Tentativas demais".encode() in resposta.data

    # mesmo com a senha certa continua bloqueado
    assert "Tentativas demais".encode() in fazer_login(client, email=email).data


def test_senha_curta_e_recusada(client):
    resposta = cadastrar_usuario(client, senha="123")
    assert "pelo menos".encode() in resposta.data
    assert fazer_login(client, senha="123").status_code == 200
    assert b"Dashboard" not in fazer_login(client, senha="123").data


# ==============================================================================
# REGRESSÃO: escalação de privilégio no cadastro público
# ==============================================================================
def test_cadastro_ignora_tipo_usuario_enviado_no_formulario(client):
    """Antes, qualquer visitante criava a própria conta de Administrador."""
    from extensions import db
    from models import Usuario

    cadastrar_usuario(client, email="invasor@teste.com", tipo_usuario="Administrador")

    usuario = db.session.execute(
        db.select(Usuario).where(Usuario.email == "invasor@teste.com")
    ).scalar_one()
    assert usuario.tipo_usuario == "Usuário"

    fazer_login(client, email="invasor@teste.com")
    resposta = client.get("/admin/usuarios", follow_redirects=True)
    assert "Painel Administrativo".encode() not in resposta.data


def test_usuario_comum_nao_acessa_painel_admin(client, criar_usuario):
    criar_usuario(email="usuario@teste.com", tipo="Usuário")
    fazer_login(client, email="usuario@teste.com")

    resposta = client.get("/admin/usuarios", follow_redirects=True)
    assert "Painel Administrativo".encode() not in resposta.data
    assert "Dashboard Help Desk".encode() in resposta.data


def test_admin_acessa_painel_admin(client, criar_usuario):
    criar_usuario(email="admin@teste.com", tipo="Administrador")
    fazer_login(client, email="admin@teste.com")

    resposta = client.get("/admin/usuarios")
    assert resposta.status_code == 200
    assert "Painel Administrativo".encode() in resposta.data


# ==============================================================================
# REGRESSÃO: sessão desatualizada
# ==============================================================================
def test_rebaixar_perfil_vale_na_mesma_sessao(client, criar_usuario):
    """Antes, o perfil ficava congelado no cookie até o usuário deslogar."""
    from extensions import db

    tecnico = criar_usuario(email="tecnico@teste.com", tipo="Técnico")
    fazer_login(client, email="tecnico@teste.com")
    assert client.get("/meus-chamados").status_code == 200

    tecnico.tipo_usuario = "Usuário"
    db.session.commit()

    assert client.get("/meus-chamados").status_code == 302


def test_usuario_excluido_perde_a_sessao(client, criar_usuario):
    from extensions import db

    usuario = criar_usuario(email="some@teste.com")
    fazer_login(client, email="some@teste.com")
    assert client.get("/dashboard").status_code == 200

    db.session.delete(usuario)
    db.session.commit()

    assert client.get("/dashboard").status_code == 302


# ==============================================================================
# CHAMADOS
# ==============================================================================
def test_abrir_chamado_publico(client):
    resposta = abrir_chamado(client)
    assert resposta.status_code == 200
    assert "sucesso".encode() in resposta.data


def test_prioridade_invalida_vira_media(client):
    """Antes, qualquer texto enviado no formulário virava prioridade no banco."""
    from extensions import db
    from models import Chamado

    abrir_chamado(client, prioridade="XYZ-INVALIDA")

    chamado = db.session.execute(
        db.select(Chamado).order_by(Chamado.id.desc())
    ).scalars().first()
    assert chamado.prioridade == "Média"


def test_chamado_incompleto_e_recusado(client):
    from extensions import db
    from models import Chamado

    client.post("/chamado", data={"usuario": "  ", "setor": "TI", "titulo": "t", "descricao": "d"})
    total = db.session.execute(db.select(db.func.count(Chamado.id))).scalar_one()
    assert total == 0


def test_abrir_chamado_gera_codigo_de_acompanhamento(client):
    """A confirmação mostra um código, e é o único lugar onde ele existe em
    texto puro — o banco guarda só o hash (ver `gerar_codigo_acompanhamento`)."""
    from extensions import db
    from models import Chamado

    resposta = abrir_chamado(client)
    assert "código".encode() in resposta.data

    chamado = db.session.execute(
        db.select(Chamado).order_by(Chamado.id.desc())
    ).scalars().first()
    assert chamado.codigo_acompanhamento_hash is not None


def test_acompanhar_chamado_com_codigo_valido(client):
    from seguranca import gerar_codigo_acompanhamento
    from extensions import db
    from models import Chamado

    abrir_chamado(client, titulo="Monitor piscando")
    chamado = db.session.execute(
        db.select(Chamado).order_by(Chamado.id.desc())
    ).scalars().first()
    codigo = gerar_codigo_acompanhamento(chamado)

    resposta = client.post(
        "/chamado/acompanhar", data={"codigo": codigo}, follow_redirects=True
    )
    assert resposta.status_code == 200
    assert "Monitor piscando".encode() in resposta.data


def test_acompanhar_chamado_com_codigo_invalido_nao_vaza_dados(client):
    abrir_chamado(client, titulo="Computador não liga")

    resposta = client.post(
        "/chamado/acompanhar", data={"codigo": "codigo-que-nao-existe"}, follow_redirects=True
    )
    assert resposta.status_code == 200
    assert "Computador não liga".encode() not in resposta.data
    assert "inválido".encode() in resposta.data


def test_tecnico_assume_chamado_vira_responsavel(client, criar_usuario):
    criar_usuario(email="tecnico@teste.com", tipo="Técnico")
    fazer_login(client, email="tecnico@teste.com")

    abrir_chamado(client, titulo="Impressora sem tinta", prioridade="Baixa")
    client.post("/chamados/1/status", data={"status": "Em andamento"})

    resposta = client.get("/meus-chamados")
    assert resposta.status_code == 200
    assert "Impressora sem tinta".encode() in resposta.data


# ==============================================================================
# REGRESSÃO: filtros da listagem
# ==============================================================================
def test_filtro_responsavel_invalido_nao_quebra(client, criar_usuario):
    """Antes, /chamados?responsavel=abc devolvia erro 500."""
    criar_usuario(email="admin@teste.com", tipo="Administrador")
    fazer_login(client, email="admin@teste.com")

    assert client.get("/chamados?responsavel=abc").status_code == 200
    assert client.get("/chamados?status=invalido&prioridade=invalida").status_code == 200
    assert client.get("/chamados?data_inicio=nao-e-data").status_code == 200


# ==============================================================================
# REGRESSÃO: CSRF
# ==============================================================================
def test_post_sem_token_csrf_e_bloqueado(client, criar_usuario):
    """Com CSRF ativo, um POST vindo de outro site não passa."""
    alvo = criar_usuario(email="vitima@teste.com", tipo="Usuário")
    criar_usuario(nome="Adm", email="admin@teste.com", tipo="Administrador")
    fazer_login(client, email="admin@teste.com")

    client.application.config["WTF_CSRF_ENABLED"] = True
    try:
        resposta = client.post(
            f"/admin/usuarios/{alvo.id}/tipo", data={"tipo_usuario": "Administrador"}
        )
        assert resposta.status_code == 400
        assert alvo.tipo_usuario == "Usuário"
    finally:
        client.application.config["WTF_CSRF_ENABLED"] = False


# ==============================================================================
# REGRESSÃO: XSS armazenado no painel administrativo
# ==============================================================================
def test_nome_com_aspas_nao_escapa_do_javascript(client, criar_usuario):
    """Antes, o nome era interpolado dentro de um confirm() em onsubmit."""
    criar_usuario(nome="');alert(1);//", email="xss@teste.com")
    criar_usuario(nome="Adm", email="admin@teste.com", tipo="Administrador")
    fazer_login(client, email="admin@teste.com")

    html = client.get("/admin/usuarios").get_data(as_text=True)

    # Não pode existir handler inline montado por interpolação de string.
    assert "onsubmit=" not in html
    # O payload só aparece escapado, dentro de um atributo de dados.
    assert 'data-nome="&#39;);alert(1);//"' in html
    assert "');alert(1);//" not in html


# ==============================================================================
# TROCA DE SENHA
# ==============================================================================
def trocar_senha(client, atual=SENHA_PADRAO, nova="NovaSenha#2026", confirmacao=None):
    return client.post(
        "/senha",
        data={
            "senha_atual": atual,
            "nova_senha": nova,
            "confirmacao": nova if confirmacao is None else confirmacao,
        },
        follow_redirects=True,
    )


def test_alterar_senha_exige_login(client):
    assert client.get("/senha").status_code == 302


def test_troca_de_senha_funciona(client, criar_usuario):
    criar_usuario(email="troca@teste.com")
    fazer_login(client, email="troca@teste.com")

    resposta = trocar_senha(client)
    assert "alterada com sucesso".encode() in resposta.data

    # a senha antiga não vale mais, a nova vale
    client.get("/logout")
    assert b"Dashboard" not in fazer_login(client, email="troca@teste.com").data
    assert b"Dashboard" in fazer_login(
        client, email="troca@teste.com", senha="NovaSenha#2026"
    ).data


def test_senha_atual_errada_nao_troca(client, criar_usuario):
    """Impede que uma sessão sequestrada tome a conta trocando a senha."""
    criar_usuario(email="alvo@teste.com")
    fazer_login(client, email="alvo@teste.com")

    resposta = trocar_senha(client, atual="chute-errado")
    assert "incorreta".encode() in resposta.data

    client.get("/logout")
    assert b"Dashboard" in fazer_login(client, email="alvo@teste.com").data


def test_confirmacao_diferente_nao_troca(client, criar_usuario):
    criar_usuario(email="c@teste.com")
    fazer_login(client, email="c@teste.com")

    resposta = trocar_senha(client, nova="NovaSenha#2026", confirmacao="OutraCoisa#99")
    assert "conferem".encode() in resposta.data


def test_nova_senha_igual_a_atual_e_recusada(client, criar_usuario):
    criar_usuario(email="igual@teste.com")
    fazer_login(client, email="igual@teste.com")

    resposta = trocar_senha(client, nova=SENHA_PADRAO)
    assert "diferente da atual".encode() in resposta.data


def test_senhas_fracas_sao_recusadas(client, criar_usuario):
    criar_usuario(nome="Joana Prado", email="joana@teste.com")
    fazer_login(client, email="joana@teste.com")

    casos = {
        "abc1": "pelo menos",          # curta
        "12345678": "comum",           # lista de proibidas
        "9876543210": "só números",    # apenas dígitos
        "abcdefghij": "número",        # apenas letras
        "aaaa1111": "repetidos",       # variedade baixa
        "joana2026!": "seu nome",      # contém o nome
        "joana@teste": "seu nome",     # derivada do nome/e-mail
    }
    for senha, trecho in casos.items():
        resposta = trocar_senha(client, nova=senha)
        assert trecho.encode() in resposta.data, f"{senha!r} deveria ser recusada"


def test_troca_de_senha_derruba_sessao_de_outro_dispositivo(client, criar_usuario):
    """A assinatura da sessão deriva do hash da senha, então trocar invalida."""
    criar_usuario(email="dois@teste.com")

    outro = client.application.test_client()
    fazer_login(outro, email="dois@teste.com")
    assert outro.get("/dashboard").status_code == 200

    fazer_login(client, email="dois@teste.com")
    trocar_senha(client)

    assert outro.get("/dashboard").status_code == 302   # sessão antiga morreu
    assert client.get("/dashboard").status_code == 200  # a que trocou continua


def test_tentativas_repetidas_bloqueiam(client, criar_usuario):
    from constantes import MAX_TENTATIVAS_SENHA

    criar_usuario(email="forca@teste.com")
    fazer_login(client, email="forca@teste.com")

    for _ in range(MAX_TENTATIVAS_SENHA):
        trocar_senha(client, atual="errada")

    resposta = trocar_senha(client, atual="errada")
    assert "Tentativas demais".encode() in resposta.data

    # mesmo com a senha certa continua bloqueado
    assert "Tentativas demais".encode() in trocar_senha(client).data

# ==============================================================================
# REDEFINIÇÃO DE SENHA POR E-MAIL
# ==============================================================================
def _token_de(client, email="fulano@teste.com"):
    """Extrai um token de redefinição válido para o usuário informado."""
    from models import Usuario
    from seguranca import gerar_token_redefinicao
    from extensions import db

    with client.application.test_request_context():
        usuario = db.session.execute(
            db.select(Usuario).where(Usuario.email == email)
        ).scalar_one()
        return gerar_token_redefinicao(usuario)


def test_esqueci_senha_responde_igual_para_email_desconhecido(client, criar_usuario):
    """A tela não pode virar um verificador de quem tem conta no sistema."""
    criar_usuario()

    conhecido = client.post("/esqueci-senha", data={"email": "fulano@teste.com"})
    desconhecido = client.post("/esqueci-senha", data={"email": "ninguem@teste.com"})

    assert conhecido.status_code == desconhecido.status_code == 200
    assert conhecido.get_data() == desconhecido.get_data()


def test_link_de_redefinicao_ignora_host_forjado_na_requisicao(client, criar_usuario, monkeypatch):
    """O link do e-mail de redefinição vem de HOST_CONFIAVEL, nunca do Host da
    requisição — um Host forjado não pode fazer a vítima abrir o link de
    redefinição num domínio malicioso (password-reset poisoning).
    """
    criar_usuario()
    client.application.config["HOST_CONFIAVEL"] = "helpdesk-system-cci1.onrender.com"

    links_enviados = []
    monkeypatch.setattr(
        "rotas.auth.enviar_email_redefinicao",
        lambda usuario, link: links_enviados.append(link),
    )

    resposta = client.post(
        "/esqueci-senha",
        data={"email": "fulano@teste.com"},
        headers={"Host": "site-malicioso.com"},
    )

    assert resposta.status_code == 200
    assert len(links_enviados) == 1
    assert links_enviados[0].startswith(
        "https://helpdesk-system-cci1.onrender.com/redefinir-senha/"
    )
    assert "site-malicioso.com" not in links_enviados[0]


def test_link_de_redefinicao_troca_a_senha(client, criar_usuario):
    criar_usuario(senha="senha-antiga-1")
    token = _token_de(client)

    resposta = client.post(
        f"/redefinir-senha/{token}",
        data={"nova_senha": "senha-nova-99", "confirmacao": "senha-nova-99"},
        follow_redirects=True,
    )
    assert resposta.status_code == 200

    # a antiga não entra mais, a nova entra
    assert b"inv" in client.post(
        "/login", data={"email": "fulano@teste.com", "senha": "senha-antiga-1"}
    ).get_data()
    entrada = client.post(
        "/login", data={"email": "fulano@teste.com", "senha": "senha-nova-99"}
    )
    assert entrada.status_code == 302


def test_token_so_serve_uma_vez(client, criar_usuario):
    """Trocar a senha muda o hash, e o hash é o que assina o token."""
    criar_usuario()
    token = _token_de(client)

    client.post(f"/redefinir-senha/{token}",
                data={"nova_senha": "senha-nova-99", "confirmacao": "senha-nova-99"})

    segunda = client.get(f"/redefinir-senha/{token}")
    assert "já foi usado" in segunda.get_data(as_text=True)


def test_token_adulterado_e_recusado(client, criar_usuario):
    criar_usuario()
    resposta = client.get("/redefinir-senha/token-inventado-por-mim")
    assert "não é válido" in resposta.get_data(as_text=True)


def test_token_expirado_e_recusado(client, criar_usuario):
    criar_usuario()
    token = _token_de(client)

    from seguranca import usuario_do_token

    with client.application.test_request_context():
        usuario, motivo = usuario_do_token(token, validade_segundos=-1)

    assert usuario is None
    assert motivo == "expirado"


def test_redefinicao_recusa_senha_fraca(client, criar_usuario):
    criar_usuario()
    token = _token_de(client)

    resposta = client.post(f"/redefinir-senha/{token}",
                           data={"nova_senha": "12345678", "confirmacao": "12345678"})

    assert "comum demais" in resposta.get_data(as_text=True)
    # a senha original continua valendo
    assert client.post(
        "/login", data={"email": "fulano@teste.com", "senha": "senha-de-teste"}
    ).status_code == 302


# ==============================================================================
# CONFIGURAÇÃO DO BANCO
# ==============================================================================
def test_url_do_banco_corrige_o_esquema_do_postgres(monkeypatch):
    """Provedores entregam `postgres://`, esquema que o SQLAlchemy 2 removeu."""
    from app import _url_do_banco

    monkeypatch.setenv("DATABASE_URL", "postgres://usuario:senha@host/banco")
    assert _url_do_banco() == "postgresql://usuario:senha@host/banco"


def test_url_do_banco_nao_mexe_no_sqlite(monkeypatch):
    from app import _url_do_banco

    monkeypatch.delenv("DATABASE_URL", raising=False)
    assert _url_do_banco() == "sqlite:///chamados.db"


def test_migracoes_reproduzem_o_esquema_dos_modelos(tmp_path):
    """As migrações versionadas geram exatamente o esquema descrito em models.py.

    É o teste que pega o esquecimento clássico ao trabalhar com migrações: mexer
    num modelo e não gerar o arquivo de migração correspondente. Os outros
    testes não pegariam — eles criam as tabelas direto dos modelos, então
    passariam felizes. Quem quebraria seria a produção, onde o esquema vem
    exclusivamente das migrações.
    """
    from alembic.autogenerate import compare_metadata
    from alembic.migration import MigrationContext
    from flask_migrate import upgrade

    from app import create_app
    from extensions import db

    banco = tmp_path / "migracoes.db"
    aplicacao = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{banco}",
            "SECRET_KEY": "chave-de-teste",
        }
    )

    with aplicacao.app_context():
        upgrade()  # aplica a pasta migrations/ do zero neste banco temporário

        with db.engine.connect() as conexao:
            diferencas = compare_metadata(MigrationContext.configure(conexao), db.metadata)

    assert diferencas == [], (
        "O esquema dos modelos e o das migrações divergem: "
        f"{diferencas}. Gere a migração que falta com "
        '`flask db migrate -m "descreva a mudanca"` e versione o arquivo criado.'
    )


# ==============================================================================
# PERSISTÊNCIA DO LIMITE DE TENTATIVAS
# ==============================================================================
def _app_no_banco(caminho):
    """Uma aplicação apontada para um arquivo de banco, fazendo as vezes de processo."""
    from app import create_app

    return create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{caminho}",
            "SECRET_KEY": "chave-de-teste",
            "WTF_CSRF_ENABLED": False,
            "MAIL_SUPPRESS_SEND": True,
        }
    )


def test_bloqueio_sobrevive_ao_reinicio_do_processo(tmp_path):
    """O motivo de existir a tabela de tentativas.

    A aplicação roda num plano que hiberna depois de alguns minutos sem acesso.
    Enquanto a contagem morava na memória do processo, cada despertar zerava o
    bloqueio e devolvia ao atacante uma leva nova de tentativas — várias vezes
    por dia. A segunda aplicação abaixo é esse processo novo: mesmo banco,
    memória em branco.
    """
    from constantes import MAX_TENTATIVAS_LOGIN
    from extensions import db
    from seguranca import throttle_login

    banco = tmp_path / "tentativas.db"
    email = "alvo@teste.com"

    with _app_no_banco(banco).app_context():
        db.create_all()
        for _ in range(MAX_TENTATIVAS_LOGIN):
            throttle_login.registrar(email)
        assert throttle_login.segundos_de_bloqueio(email) > 0

    with _app_no_banco(banco).app_context():
        assert throttle_login.segundos_de_bloqueio(email) > 0


def test_tentativas_antigas_saem_da_janela(app):
    """Passada a janela, as tentativas param de contar e a próxima escrita as apaga."""
    from datetime import timedelta

    from constantes import JANELA_BLOQUEIO_LOGIN_SEGUNDOS, MAX_TENTATIVAS_LOGIN
    from extensions import db
    from models import TentativaAcesso, obter_data_utc
    from seguranca import throttle_login

    email = "antigo@teste.com"
    vencida = obter_data_utc() - timedelta(seconds=JANELA_BLOQUEIO_LOGIN_SEGUNDOS + 60)

    for _ in range(MAX_TENTATIVAS_LOGIN):
        db.session.add(TentativaAcesso(escopo="login", chave=email, criado_em=vencida))
    db.session.commit()

    assert throttle_login.segundos_de_bloqueio(email) == 0

    throttle_login.registrar(email)

    restantes = (
        db.session.execute(db.select(TentativaAcesso).where(TentativaAcesso.chave == email))
        .scalars()
        .all()
    )
    assert len(restantes) == 1


# ==============================================================================
# ADMINISTRAÇÃO DE USUÁRIOS (admin.py)
# ==============================================================================
def test_alterar_tipo_com_valor_invalido_e_recusado(client, criar_usuario):
    criar_usuario(nome="Adm", email="admin@teste.com", tipo="Administrador")
    alvo = criar_usuario(email="alvo@teste.com", tipo="Usuário")
    fazer_login(client, email="admin@teste.com")

    resposta = client.post(
        f"/admin/usuarios/{alvo.id}/tipo",
        data={"tipo_usuario": "Superusuario"},
        follow_redirects=True,
    )
    assert "inválido".encode() in resposta.data
    assert alvo.tipo_usuario == "Usuário"


def test_admin_nao_remove_o_proprio_acesso_de_administrador(client, criar_usuario):
    admin = criar_usuario(email="admin@teste.com", tipo="Administrador")
    fazer_login(client, email="admin@teste.com")

    resposta = client.post(
        f"/admin/usuarios/{admin.id}/tipo",
        data={"tipo_usuario": "Usuário"},
        follow_redirects=True,
    )
    assert "não pode remover seu próprio acesso".encode() in resposta.data
    assert admin.tipo_usuario == "Administrador"


def test_alterar_tipo_com_sucesso_atualiza_banco_e_gera_log(client, criar_usuario):
    from extensions import db
    from models import LogAuditoria

    criar_usuario(nome="Adm", email="admin@teste.com", tipo="Administrador")
    alvo = criar_usuario(email="alvo@teste.com", tipo="Usuário")
    fazer_login(client, email="admin@teste.com")

    resposta = client.post(
        f"/admin/usuarios/{alvo.id}/tipo",
        data={"tipo_usuario": "Técnico"},
        follow_redirects=True,
    )
    assert "atualizado para".encode() in resposta.data
    assert alvo.tipo_usuario == "Técnico"

    log = db.session.execute(
        db.select(LogAuditoria).order_by(LogAuditoria.id.desc())
    ).scalars().first()
    assert log.acao == "Alteração de perfil"
    assert "Técnico" in log.detalhes
    assert alvo.nome in log.detalhes


def test_admin_nao_exclui_a_propria_conta(client, criar_usuario):
    admin = criar_usuario(email="admin@teste.com", tipo="Administrador")
    fazer_login(client, email="admin@teste.com")

    resposta = client.post(f"/admin/usuarios/{admin.id}/excluir", follow_redirects=True)
    assert "não pode excluir a própria conta".encode() in resposta.data

    from extensions import db
    from models import Usuario

    assert db.session.get(Usuario, admin.id) is not None


def test_excluir_usuario_com_chamado_associado_e_recusado(client, criar_usuario):
    from extensions import db
    from models import Chamado, Usuario

    criar_usuario(nome="Adm", email="admin@teste.com", tipo="Administrador")
    tecnico = criar_usuario(email="tecnico@teste.com", tipo="Técnico")

    chamado = Chamado(
        usuario="Maria",
        setor="TI",
        titulo="Impressora",
        descricao="Sem tinta",
        responsavel_id=tecnico.id,
    )
    db.session.add(chamado)
    db.session.commit()

    fazer_login(client, email="admin@teste.com")
    resposta = client.post(f"/admin/usuarios/{tecnico.id}/excluir", follow_redirects=True)

    assert "não pode ser".encode() in resposta.data
    assert db.session.get(Usuario, tecnico.id) is not None


def test_excluir_usuario_com_comentario_associado_e_recusado(client, criar_usuario):
    from extensions import db
    from models import Chamado, Comentario, Usuario

    criar_usuario(nome="Adm", email="admin@teste.com", tipo="Administrador")
    tecnico = criar_usuario(email="tecnico@teste.com", tipo="Técnico")

    chamado = Chamado(usuario="Maria", setor="TI", titulo="Impressora", descricao="Sem tinta")
    db.session.add(chamado)
    db.session.commit()

    comentario = Comentario(chamado_id=chamado.id, autor_id=tecnico.id, mensagem="Verificando.")
    db.session.add(comentario)
    db.session.commit()

    fazer_login(client, email="admin@teste.com")
    resposta = client.post(f"/admin/usuarios/{tecnico.id}/excluir", follow_redirects=True)

    assert "não pode ser".encode() in resposta.data
    assert db.session.get(Usuario, tecnico.id) is not None


def test_excluir_usuario_com_sucesso_remove_do_banco_e_zera_logs(client, criar_usuario):
    """A exclusão remove o usuário e não deixa nenhum log de auditoria com uma
    FK órfã apontando para um id que não existe mais.

    Um log fica com `usuario_id` do alvo quando a ação foi feita *pelo próprio
    alvo* (ex.: login dele) — não quando o admin age sobre ele, caso em que
    `registrar_log` grava o autor da ação (usuario_atual()), e o nome do alvo
    vira só texto em `detalhes`. Por isso o log com FK a zerar é o do login do
    próprio alvo, gerado antes da exclusão.
    """
    from extensions import db
    from models import LogAuditoria, Usuario

    criar_usuario(nome="Adm", email="admin@teste.com", tipo="Administrador")
    alvo = criar_usuario(nome="Vítima", email="vitima@teste.com", tipo="Usuário")
    alvo_id = alvo.id

    # login do próprio alvo gera um log com usuario_id apontando para ele
    outro_cliente = client.application.test_client()
    fazer_login(outro_cliente, email="vitima@teste.com")

    fazer_login(client, email="admin@teste.com")

    resposta = client.post(f"/admin/usuarios/{alvo_id}/excluir", follow_redirects=True)
    assert "excluído com sucesso".encode() in resposta.data
    assert db.session.get(Usuario, alvo_id) is None

    log_do_login = db.session.execute(
        db.select(LogAuditoria).where(
            LogAuditoria.usuario_nome == "Vítima", LogAuditoria.acao == "Login realizado"
        )
    ).scalars().first()
    assert log_do_login is not None
    assert log_do_login.usuario_id is None

    log_da_exclusao = db.session.execute(
        db.select(LogAuditoria).where(LogAuditoria.acao == "Exclusão de usuário")
    ).scalars().first()
    assert log_da_exclusao is not None
    assert "Vítima" in log_da_exclusao.detalhes


# ==============================================================================
# SEGURANÇA: HEADERS HTTP
# ==============================================================================
def test_resposta_tem_headers_de_seguranca(client):
    resposta = client.get("/login")
    assert resposta.headers["X-Frame-Options"] == "DENY"
    assert resposta.headers["X-Content-Type-Options"] == "nosniff"
    assert resposta.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"


def test_hsts_so_aparece_com_cookie_seguro_ligado(client):
    # CONFIG_DE_TESTE não liga SESSION_COOKIE_SECURE, então por padrão o
    # header não deve aparecer — pedir HTTPS sem estar servindo por HTTPS não
    # faz sentido.
    resposta = client.get("/login")
    assert "Strict-Transport-Security" not in resposta.headers

    client.application.config["SESSION_COOKIE_SECURE"] = True
    resposta = client.get("/login")
    assert resposta.headers["Strict-Transport-Security"] == "max-age=31536000; includeSubDomains"


def test_nao_forca_https_com_cookie_seguro_desligado(client):
    # Mesma flag do teste acima: sem SESSION_COOKIE_SECURE, a aplicação está
    # em desenvolvimento local, e `flask run` normalmente só serve HTTP — o
    # redirecionamento tem que ficar desligado, ou ninguém consegue rodar o
    # projeto localmente.
    resposta = client.get("/login")
    assert resposta.status_code == 200


def test_forca_https_quando_proxy_indica_http(client):
    # O Render entrega a requisição à aplicação como HTTP simples e anota o
    # esquema original do visitante em X-Forwarded-Proto — sem esse cabeçalho
    # dizendo "https", a aplicação trata a requisição como insegura.
    client.application.config["SESSION_COOKIE_SECURE"] = True
    resposta = client.get("/login", headers={"X-Forwarded-Proto": "http"})
    assert resposta.status_code == 308
    assert resposta.headers["Location"].startswith("https://")


def test_nao_redireciona_quando_proxy_ja_indica_https(client):
    client.application.config["SESSION_COOKIE_SECURE"] = True
    resposta = client.get("/login", headers={"X-Forwarded-Proto": "https"})
    assert resposta.status_code == 200


def test_redirect_https_ignora_host_forjado_na_requisicao(client):
    # O destino do redirect vem de HOST_CONFIAVEL (config), nunca do Host da
    # requisição — um cliente não consegue desviar o redirecionamento para um
    # domínio diferente só forjando esse cabeçalho (open redirect).
    client.application.config["SESSION_COOKIE_SECURE"] = True
    client.application.config["HOST_CONFIAVEL"] = "helpdesk-system-cci1.onrender.com"

    resposta = client.get(
        "/login",
        headers={"X-Forwarded-Proto": "http", "Host": "site-malicioso.com"},
    )

    assert resposta.status_code == 308
    assert resposta.headers["Location"] == "https://helpdesk-system-cci1.onrender.com/login"


def test_redirect_https_preserva_caminho_e_querystring(client):
    client.application.config["SESSION_COOKIE_SECURE"] = True
    client.application.config["HOST_CONFIAVEL"] = "helpdesk-system-cci1.onrender.com"

    resposta = client.get(
        "/chamados?status=Aberto",
        headers={"X-Forwarded-Proto": "http"},
        follow_redirects=False,
    )

    assert resposta.status_code == 308
    assert resposta.headers["Location"] == (
        "https://helpdesk-system-cci1.onrender.com/chamados?status=Aberto"
    )


def test_nao_redireciona_quando_o_cabecalho_de_proxy_esta_ausente(client):
    """Trava contra loop, do incidente de 16/09/2026.

    O Waitress apagava o X-Forwarded-Proto antes de a requisição chegar ao
    Flask (ver `opcoes_de_proxy` em serve.py). Sem o cabeçalho não há como
    saber o esquema de origem, e redirecionar assumindo HTTP fazia a aplicação
    apontar para a própria URL sem parar. Sem cabeçalho, serve a página.
    """
    client.application.config["SESSION_COOKIE_SECURE"] = True

    resposta = client.get("/login", environ_overrides={"wsgi.url_scheme": "http"})

    assert resposta.status_code == 200


def test_nao_redireciona_com_valor_inesperado_no_x_forwarded_proto(client):
    """Qualquer valor que não seja exatamente "http" serve a página.

    Em produção o Waitress já recusa com 400 o cabeçalho com múltiplos valores
    ("https, http"), então ele nunca chega até aqui — mas a regra restrita
    garante que nenhum valor inesperado vire redirecionamento em loop.
    """
    client.application.config["SESSION_COOKIE_SECURE"] = True

    resposta = client.get(
        "/login", headers={"X-Forwarded-Proto": "https, http"}
    )

    assert resposta.status_code == 200


def test_serve_confia_nos_cabecalhos_de_proxy_em_producao(monkeypatch):
    """Em produção o Waitress precisa preservar os X-Forwarded-*.

    Sem isso ele apaga o X-Forwarded-Proto e o `_forcar_https` entra em loop —
    foi o que derrubou a produção em 16/09/2026.
    """
    from serve import opcoes_de_proxy

    monkeypatch.setenv("SESSION_COOKIE_SECURE", "1")
    opcoes = opcoes_de_proxy()

    assert opcoes["trusted_proxy"] == "*"
    assert "x-forwarded-proto" in opcoes["trusted_proxy_headers"]


def test_serve_nao_confia_em_proxy_fora_de_producao(monkeypatch):
    """Sem a flag de produção não há proxy nenhum: o Waitress segue limpando."""
    from serve import opcoes_de_proxy

    monkeypatch.delenv("SESSION_COOKIE_SECURE", raising=False)

    assert opcoes_de_proxy() == {}


# ==============================================================================
# EXPORTAÇÃO DE RELATÓRIOS
# ==============================================================================
def test_excel_neutraliza_titulo_com_formula_maliciosa(app):
    """Injeção de fórmula (CSV/Excel injection).

    O título e o setor vêm de quem abre o chamado — inclusive sem login (ver
    `rotas/chamados.py`). Um valor como =HYPERLINK(...) gravado sem tratamento
    vira fórmula de verdade na planilha, executada quando um técnico ou
    administrador abre o relatório exportado.
    """
    import io

    from openpyxl import load_workbook

    from extensions import db
    from models import Chamado
    from relatorios import gerar_excel

    with app.app_context():
        chamado = Chamado(
            usuario="Anônimo",
            setor="=1+1",
            titulo='=HYPERLINK("https://malicioso.exemplo","clique")',
            descricao="Chamado de teste.",
        )
        db.session.add(chamado)
        db.session.commit()

        conteudo = gerar_excel([chamado])

    pasta = load_workbook(io.BytesIO(conteudo))
    aba = pasta.active
    linha = next(aba.iter_rows(min_row=2, max_row=2))
    celula_titulo, celula_setor = linha[1], linha[2]

    # Tipo "s" (string) grava como texto puro; tipo "f" seria uma fórmula real.
    assert celula_titulo.data_type == "s"
    assert celula_setor.data_type == "s"
    assert celula_titulo.value.startswith("'=")
    assert celula_setor.value.startswith("'=")


# ==============================================================================
# LOGOUT VIA POST (issue #114)
# ==============================================================================
def test_logout_via_get_e_rejeitado(client, criar_usuario):
    """Logout por GET permitia CSRF: um <img src="/logout"> em outro site
    derrubava a sessão da vítima sem ela clicar em nada. Agora só aceita POST,
    protegido pelo CSRF global do projeto (ver extensions.py)."""
    criar_usuario()
    fazer_login(client)

    resposta = client.get("/logout")

    assert resposta.status_code == 405


def test_logout_via_post_encerra_sessao(client, criar_usuario):
    criar_usuario()
    fazer_login(client)

    resposta = client.post("/logout", follow_redirects=True)

    assert resposta.status_code == 200
    assert b"Login" in resposta.data

    resposta_dashboard = client.get("/dashboard", follow_redirects=True)
    assert b"Login" in resposta_dashboard.data
