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


def test_login_com_senha_errada(client):
    cadastrar_usuario(client)
    resposta = fazer_login(client, senha="senha-errada")
    assert "inv".encode() in resposta.data.lower()


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
    from app import Usuario, db

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
    from app import db

    tecnico = criar_usuario(email="tecnico@teste.com", tipo="Técnico")
    fazer_login(client, email="tecnico@teste.com")
    assert client.get("/meus-chamados").status_code == 200

    tecnico.tipo_usuario = "Usuário"
    db.session.commit()

    assert client.get("/meus-chamados").status_code == 302


def test_usuario_excluido_perde_a_sessao(client, criar_usuario):
    from app import db

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
    from app import Chamado, db

    abrir_chamado(client, prioridade="XYZ-INVALIDA")

    chamado = db.session.execute(
        db.select(Chamado).order_by(Chamado.id.desc())
    ).scalars().first()
    assert chamado.prioridade == "Média"


def test_chamado_incompleto_e_recusado(client):
    from app import Chamado, db

    client.post("/chamado", data={"usuario": "  ", "setor": "TI", "titulo": "t", "descricao": "d"})
    total = db.session.execute(db.select(db.func.count(Chamado.id))).scalar_one()
    assert total == 0


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
    from app import app as flask_app

    alvo = criar_usuario(email="vitima@teste.com", tipo="Usuário")
    criar_usuario(nome="Adm", email="admin@teste.com", tipo="Administrador")
    fazer_login(client, email="admin@teste.com")

    flask_app.config["WTF_CSRF_ENABLED"] = True
    try:
        resposta = client.post(
            f"/admin/usuarios/{alvo.id}/tipo", data={"tipo_usuario": "Administrador"}
        )
        assert resposta.status_code == 400
        assert alvo.tipo_usuario == "Usuário"
    finally:
        flask_app.config["WTF_CSRF_ENABLED"] = False


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
    from app import app as flask_app

    criar_usuario(email="dois@teste.com")

    outro = flask_app.test_client()
    fazer_login(outro, email="dois@teste.com")
    assert outro.get("/dashboard").status_code == 200

    fazer_login(client, email="dois@teste.com")
    trocar_senha(client)

    assert outro.get("/dashboard").status_code == 302   # sessão antiga morreu
    assert client.get("/dashboard").status_code == 200  # a que trocou continua


def test_tentativas_repetidas_bloqueiam(client, criar_usuario):
    from app import MAX_TENTATIVAS_SENHA, limpar_tentativas_senha

    usuario = criar_usuario(email="forca@teste.com")
    limpar_tentativas_senha(usuario.id)
    fazer_login(client, email="forca@teste.com")

    for _ in range(MAX_TENTATIVAS_SENHA):
        trocar_senha(client, atual="errada")

    resposta = trocar_senha(client, atual="errada")
    assert "Tentativas demais".encode() in resposta.data

    # mesmo com a senha certa continua bloqueado
    assert "Tentativas demais".encode() in trocar_senha(client).data
    limpar_tentativas_senha(usuario.id)