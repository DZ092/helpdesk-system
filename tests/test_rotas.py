"""Cobertura de fumaça: toda rota responde, e o ciclo do chamado atravessa o sistema.

A suíte de `test_app.py` verifica regras — quem pode o quê, o que é recusado.
Estes testes cobrem o outro lado: se cada tela ainda *carrega*. É o tipo de
falha que uma refatoração introduz e nenhum teste de regra percebe, porque o
template quebra sem que nenhuma regra mude.
"""

import pytest

SENHA = "senha-de-teste"

# Rotas que qualquer visitante alcança.
ROTAS_PUBLICAS = ["/login", "/cadastro", "/chamado", "/esqueci-senha"]

# Rotas que exigem sessão. O perfil mínimo de cada uma está anotado ao lado.
ROTAS_INTERNAS = [
    "/dashboard",
    "/chamados",
    "/meus-chamados",
    "/senha",
    "/admin/usuarios",
    "/admin/logs",
]

# Combinações de filtro e paginação da listagem — o ponto onde um `url_for`
# desatualizado ou um parâmetro inesperado costuma derrubar a página.
CONSULTAS = [
    "?pagina=1",
    "?pagina=999",
    "?status=Aberto",
    "?prioridade=Crítica",
    "?setor=Financeiro",
    "?responsavel=nenhum",
    "?responsavel=abacaxi",
    "?busca=impressora",
    "?data_inicio=2020-01-01&data_fim=2030-12-31",
]


def entrar(client, email, senha=SENHA):
    return client.post("/login", data={"email": email, "senha": senha})


def entrar_como_admin(client, criar_usuario):
    criar_usuario(nome="Ana Admin", email="admin@teste.com", tipo="Administrador")
    entrar(client, "admin@teste.com")


def abrir_chamado(client, titulo="Impressora não imprime"):
    return client.post(
        "/chamado",
        data={
            "usuario": "Rafael Souza",
            "setor": "Financeiro",
            "titulo": titulo,
            "descricao": "A impressora aceita o trabalho mas nada sai.",
            "prioridade": "Alta",
        },
    )


@pytest.mark.parametrize("rota", ROTAS_PUBLICAS)
def test_pagina_publica_responde(client, rota):
    assert client.get(rota).status_code == 200


def test_raiz_redireciona_para_o_dashboard(client):
    resposta = client.get("/")
    assert resposta.status_code == 302
    assert resposta.headers["Location"].endswith("/dashboard")


@pytest.mark.parametrize("rota", ROTAS_INTERNAS)
def test_rota_interna_exige_sessao(client, rota):
    """Sem login, toda tela interna devolve para o login."""
    resposta = client.get(rota, follow_redirects=True)
    assert b"Login" in resposta.data


@pytest.mark.parametrize("rota", ROTAS_INTERNAS)
def test_rota_interna_responde_para_admin(client, criar_usuario, rota):
    entrar_como_admin(client, criar_usuario)
    assert client.get(rota).status_code == 200


@pytest.mark.parametrize("consulta", CONSULTAS)
def test_listagem_aguenta_filtros_e_paginacao(client, criar_usuario, consulta):
    entrar_como_admin(client, criar_usuario)
    abrir_chamado(client)
    assert client.get(f"/chamados{consulta}").status_code == 200


def test_detalhe_de_chamado_inexistente_devolve_404(client, criar_usuario):
    entrar_como_admin(client, criar_usuario)
    assert client.get("/chamados/9999").status_code == 404


def test_ciclo_do_chamado_atravessa_o_sistema(client, criar_usuario):
    """Abertura pública, atendimento, comentário e resolução — ponta a ponta."""
    entrar_como_admin(client, criar_usuario)
    abrir_chamado(client, titulo="Notebook não conecta na VPN")

    detalhe = client.get("/chamados/1")
    assert detalhe.status_code == 200
    assert "Notebook não conecta na VPN" in detalhe.get_data(as_text=True)

    client.post("/chamados/1/status", data={"status": "Em andamento"})
    client.post("/chamados/1/comentarios", data={"mensagem": "Certificado reinstalado."})
    client.post("/chamados/1/status", data={"status": "Resolvido"})

    depois = client.get("/chamados/1").get_data(as_text=True)
    assert "Certificado reinstalado." in depois
    assert "Resolvido" in depois

    # O chamado atendido passa a aparecer na tela do responsável.
    assert "Notebook" in client.get("/meus-chamados").get_data(as_text=True)


def test_logs_registram_o_que_aconteceu(client, criar_usuario):
    """A trilha de auditoria é a única tela que nenhum outro teste visita."""
    entrar_como_admin(client, criar_usuario)
    abrir_chamado(client)
    client.post("/chamados/1/status", data={"status": "Em andamento"})

    logs = client.get("/admin/logs").get_data(as_text=True)
    assert "Login realizado" in logs
    assert "Abertura de chamado" in logs


def test_telas_de_autenticacao_carregam_os_dois_css(client):
    """O auth.css vale só no login e no cadastro; o style.css, em tudo."""
    for rota in ("/login", "/cadastro"):
        html = client.get(rota).get_data(as_text=True)
        assert "css/style.css" in html
        assert "css/auth.css" in html


def test_telas_de_dados_nao_carregam_o_auth_css(client, criar_usuario):
    entrar_como_admin(client, criar_usuario)
    html = client.get("/dashboard").get_data(as_text=True)
    assert "css/style.css" in html
    assert "css/auth.css" not in html
