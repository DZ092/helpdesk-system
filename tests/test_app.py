def cadastrar_usuario(client, nome="Fulano", email="fulano@teste.com", senha="123456", tipo="Usuário"):
    return client.post(
        "/cadastro",
        data={"nome": nome, "email": email, "senha": senha, "tipo_usuario": tipo},
        follow_redirects=True,
    )


def fazer_login(client, email="fulano@teste.com", senha="123456"):
    return client.post(
        "/login",
        data={"email": email, "senha": senha},
        follow_redirects=True,
    )


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


def test_abrir_chamado_publico(client):
    resposta = client.post(
        "/chamado",
        data={
            "usuario": "Maria",
            "setor": "Financeiro",
            "titulo": "Computador não liga",
            "descricao": "Tela preta ao ligar",
            "prioridade": "Alta",
        },
        follow_redirects=True,
    )
    assert resposta.status_code == 200
    assert "sucesso".encode() in resposta.data


def test_usuario_comum_nao_acessa_painel_admin(client):
    cadastrar_usuario(client, email="usuario@teste.com", tipo="Usuário")
    fazer_login(client, email="usuario@teste.com")

    resposta = client.get("/admin/usuarios", follow_redirects=True)
    assert "Painel Administrativo".encode() not in resposta.data
    assert "Dashboard Help Desk".encode() in resposta.data


def test_admin_acessa_painel_admin(client):
    cadastrar_usuario(client, email="admin@teste.com", tipo="Administrador")
    fazer_login(client, email="admin@teste.com")

    resposta = client.get("/admin/usuarios")
    assert resposta.status_code == 200
    assert "Painel Administrativo".encode() in resposta.data


def test_tecnico_assume_chamado_vira_responsavel(client):
    cadastrar_usuario(client, email="tecnico@teste.com", tipo="Técnico")
    fazer_login(client, email="tecnico@teste.com")

    client.post(
        "/chamado",
        data={
            "usuario": "Maria",
            "setor": "Financeiro",
            "titulo": "Impressora sem tinta",
            "descricao": "Precisa trocar o cartucho",
            "prioridade": "Baixa",
        },
    )

    client.post("/chamados/1/status", data={"status": "Em andamento"})

    resposta = client.get("/meus-chamados")
    assert resposta.status_code == 200
    assert "Impressora sem tinta".encode() in resposta.data