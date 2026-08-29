"""API REST dos chamados — leitura e escrita (issue #9)."""

from extensions import db
from models import Chamado, Comentario


def _criar_chamado(**extra):
    dados = dict(
        usuario="Maria",
        setor="Financeiro",
        titulo="Computador não liga",
        descricao="Tela preta ao ligar",
        status="Aberto",
        prioridade="Alta",
    )
    dados.update(extra)
    chamado = Chamado(**dados)
    db.session.add(chamado)
    db.session.commit()
    return chamado


def _token_de(client, email="fulano@teste.com", senha="senha-de-teste"):
    """Loga e gera um token de API pela mesma tela que um usuário usaria."""
    client.post("/login", data={"email": email, "senha": senha})
    resposta = client.post("/meu-token")
    return resposta.get_data(as_text=True).split('<code>')[1].split('</code>')[0]


def _token_de_tecnico(client, criar_usuario, email="tecnico@teste.com"):
    """Cria um usuário Técnico e devolve o token dele — atalho para os testes
    de escrita, onde a maioria dos casos precisa passar pela checagem de perfil
    antes de chegar na regra que o teste quer exercitar."""
    criar_usuario(nome="Ana Técnica", email=email, tipo="Técnico")
    return _token_de(client, email=email)


def _cabecalho(token):
    return {"Authorization": f"Bearer {token}"}


# ==============================================================================
# AUTENTICAÇÃO
# ==============================================================================
def test_endpoint_exige_token(client):
    resposta = client.get("/api/v1/chamados")
    assert resposta.status_code == 401
    assert "erro" in resposta.get_json()


def test_token_invalido_e_recusado(client):
    resposta = client.get("/api/v1/chamados", headers=_cabecalho("token-que-nao-existe"))
    assert resposta.status_code == 401


def test_pagina_meu_token_gera_um_token_que_autentica(client, criar_usuario):
    criar_usuario()
    token = _token_de(client)

    resposta = client.get("/api/v1/chamados", headers=_cabecalho(token))
    assert resposta.status_code == 200


def test_gerar_novo_token_invalida_o_antigo(client, criar_usuario):
    criar_usuario()
    token_antigo = _token_de(client)
    token_novo = _token_de(client)

    assert token_novo != token_antigo
    assert client.get("/api/v1/chamados", headers=_cabecalho(token_antigo)).status_code == 401
    assert client.get("/api/v1/chamados", headers=_cabecalho(token_novo)).status_code == 200


# ==============================================================================
# LISTAGEM
# ==============================================================================
def test_lista_chamados_retorna_json(client, criar_usuario):
    criar_usuario()
    token = _token_de(client)
    _criar_chamado(titulo="Chamado um")
    _criar_chamado(titulo="Chamado dois", status="Resolvido", prioridade="Baixa")

    dados = client.get("/api/v1/chamados", headers=_cabecalho(token)).get_json()

    assert dados["total"] == 2
    assert {c["titulo"] for c in dados["chamados"]} == {"Chamado um", "Chamado dois"}
    # Ordem mais recente primeiro, igual à tela.
    assert dados["chamados"][0]["titulo"] == "Chamado dois"


def test_lista_chamados_filtra_por_status(client, criar_usuario):
    criar_usuario()
    token = _token_de(client)
    _criar_chamado(titulo="Aberto")
    _criar_chamado(titulo="Resolvido", status="Resolvido")

    dados = client.get(
        "/api/v1/chamados", query_string={"status": "Resolvido"}, headers=_cabecalho(token)
    ).get_json()

    assert dados["total"] == 1
    assert dados["chamados"][0]["titulo"] == "Resolvido"


def test_lista_chamados_recusa_status_invalido(client, criar_usuario):
    criar_usuario()
    token = _token_de(client)

    resposta = client.get(
        "/api/v1/chamados", query_string={"status": "Em chamas"}, headers=_cabecalho(token)
    )
    assert resposta.status_code == 400


def test_lista_chamados_pagina(client, criar_usuario):
    criar_usuario()
    token = _token_de(client)
    for i in range(3):
        _criar_chamado(titulo=f"Chamado {i}")

    dados = client.get(
        "/api/v1/chamados", query_string={"por_pagina": 2}, headers=_cabecalho(token)
    ).get_json()

    assert len(dados["chamados"]) == 2
    assert dados["total"] == 3
    assert dados["paginas"] == 2


# ==============================================================================
# DETALHE
# ==============================================================================
def test_detalhe_chamado_inclui_comentarios(client, criar_usuario):
    autor = criar_usuario()
    token = _token_de(client)
    chamado = _criar_chamado()
    db.session.add(Comentario(chamado_id=chamado.id, autor_id=autor.id, mensagem="Verificando"))
    db.session.commit()

    dados = client.get(f"/api/v1/chamados/{chamado.id}", headers=_cabecalho(token)).get_json()

    assert dados["id"] == chamado.id
    assert len(dados["comentarios"]) == 1
    assert dados["comentarios"][0]["mensagem"] == "Verificando"
    assert dados["comentarios"][0]["autor_nome"] == autor.nome


def test_detalhe_chamado_inexistente_retorna_404(client, criar_usuario):
    criar_usuario()
    token = _token_de(client)

    resposta = client.get("/api/v1/chamados/999", headers=_cabecalho(token))
    assert resposta.status_code == 404


# ==============================================================================
# ABERTURA — pública na tela, sem exigir perfil aqui também
# ==============================================================================
def test_abre_chamado_com_usuario_comum(client, criar_usuario):
    """Abrir chamado não é ação restrita — um usuário comum com token abre normal."""
    criar_usuario()
    token = _token_de(client)

    resposta = client.post(
        "/api/v1/chamados",
        json={
            "usuario": "Rafael",
            "setor": "TI",
            "titulo": "Monitor piscando",
            "descricao": "A tela pisca a cada poucos minutos.",
            "prioridade": "Alta",
        },
        headers=_cabecalho(token),
    )

    assert resposta.status_code == 201
    dados = resposta.get_json()
    assert dados["titulo"] == "Monitor piscando"
    assert dados["status"] == "Aberto"
    assert dados["prioridade"] == "Alta"
    total = db.session.execute(db.select(db.func.count(Chamado.id))).scalar_one()
    assert total == 1


def test_abre_chamado_recusa_campo_faltando(client, criar_usuario):
    criar_usuario()
    token = _token_de(client)

    resposta = client.post(
        "/api/v1/chamados",
        json={"usuario": "Rafael", "setor": "TI", "titulo": "", "descricao": "x"},
        headers=_cabecalho(token),
    )

    assert resposta.status_code == 400
    total = db.session.execute(db.select(db.func.count(Chamado.id))).scalar_one()
    assert total == 0


def test_abre_chamado_com_prioridade_invalida_cai_para_media(client, criar_usuario):
    criar_usuario()
    token = _token_de(client)

    resposta = client.post(
        "/api/v1/chamados",
        json={
            "usuario": "Rafael",
            "setor": "TI",
            "titulo": "Chamado qualquer",
            "descricao": "Descrição qualquer",
            "prioridade": "Urgentíssima",
        },
        headers=_cabecalho(token),
    )

    assert resposta.get_json()["prioridade"] == "Média"


def test_abre_chamado_exige_token(client):
    resposta = client.post("/api/v1/chamados", json={"titulo": "x"})
    assert resposta.status_code == 401


# ==============================================================================
# STATUS — restrita a Técnico/Administrador, igual à tela
# ==============================================================================
def test_atualiza_status_como_tecnico(client, criar_usuario):
    token = _token_de_tecnico(client, criar_usuario)
    chamado = _criar_chamado()

    resposta = client.post(
        f"/api/v1/chamados/{chamado.id}/status",
        json={"status": "Em andamento"},
        headers=_cabecalho(token),
    )

    assert resposta.status_code == 200
    dados = resposta.get_json()
    assert dados["status"] == "Em andamento"

    db.session.refresh(chamado)
    assert chamado.status == "Em andamento"
    # Primeiro técnico a mexer no chamado vira o responsável, igual na tela.
    assert chamado.responsavel_id is not None


def test_atualiza_status_recusa_usuario_comum(client, criar_usuario):
    """Mesma regra da tela: só Técnico/Administrador muda status."""
    criar_usuario()
    token = _token_de(client)
    chamado = _criar_chamado()

    resposta = client.post(
        f"/api/v1/chamados/{chamado.id}/status",
        json={"status": "Em andamento"},
        headers=_cabecalho(token),
    )

    assert resposta.status_code == 403
    db.session.refresh(chamado)
    assert chamado.status == "Aberto"


def test_atualiza_status_invalido_e_recusado(client, criar_usuario):
    token = _token_de_tecnico(client, criar_usuario)
    chamado = _criar_chamado()

    resposta = client.post(
        f"/api/v1/chamados/{chamado.id}/status",
        json={"status": "Cancelado"},
        headers=_cabecalho(token),
    )

    assert resposta.status_code == 400


def test_atualiza_status_de_chamado_inexistente_retorna_404(client, criar_usuario):
    token = _token_de_tecnico(client, criar_usuario)

    resposta = client.post(
        "/api/v1/chamados/999/status",
        json={"status": "Resolvido"},
        headers=_cabecalho(token),
    )

    assert resposta.status_code == 404


# ==============================================================================
# COMENTÁRIOS — restrita a Técnico/Administrador, igual à tela
# ==============================================================================
def test_adiciona_comentario_como_tecnico(client, criar_usuario):
    token = _token_de_tecnico(client, criar_usuario)
    chamado = _criar_chamado()

    resposta = client.post(
        f"/api/v1/chamados/{chamado.id}/comentarios",
        json={"mensagem": "Verificando o problema."},
        headers=_cabecalho(token),
    )

    assert resposta.status_code == 201
    dados = resposta.get_json()
    assert dados["mensagem"] == "Verificando o problema."
    assert dados["autor_nome"] == "Ana Técnica"
    total = db.session.execute(
        db.select(db.func.count(Comentario.id)).where(Comentario.chamado_id == chamado.id)
    ).scalar_one()
    assert total == 1


def test_adiciona_comentario_recusa_usuario_comum(client, criar_usuario):
    criar_usuario()
    token = _token_de(client)
    chamado = _criar_chamado()

    resposta = client.post(
        f"/api/v1/chamados/{chamado.id}/comentarios",
        json={"mensagem": "Não deveria valer."},
        headers=_cabecalho(token),
    )

    assert resposta.status_code == 403
    total = db.session.execute(
        db.select(db.func.count(Comentario.id)).where(Comentario.chamado_id == chamado.id)
    ).scalar_one()
    assert total == 0


def test_adiciona_comentario_vazio_e_recusado(client, criar_usuario):
    token = _token_de_tecnico(client, criar_usuario)
    chamado = _criar_chamado()

    resposta = client.post(
        f"/api/v1/chamados/{chamado.id}/comentarios",
        json={"mensagem": "   "},
        headers=_cabecalho(token),
    )

    assert resposta.status_code == 400


def test_adiciona_comentario_em_chamado_inexistente_retorna_404(client, criar_usuario):
    token = _token_de_tecnico(client, criar_usuario)

    resposta = client.post(
        "/api/v1/chamados/999/comentarios",
        json={"mensagem": "x"},
        headers=_cabecalho(token),
    )

    assert resposta.status_code == 404
