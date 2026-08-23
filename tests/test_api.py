"""API REST somente leitura dos chamados (issue #9, primeira fatia)."""

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
