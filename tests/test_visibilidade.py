"""Quem vê quais chamados: o perfil Usuário só os próprios, a equipe todos."""

from extensions import db
from models import Chamado, Usuario

SENHA = "senha-de-teste"


def _entrar(client, criar_usuario, email, tipo="Usuário"):
    usuario = criar_usuario(nome=email.split("@")[0].title(), email=email, tipo=tipo)
    client.post("/login", data={"email": email, "senha": SENHA})
    return usuario


def _chamado(titulo, autor=None, setor="Financeiro"):
    chamado = Chamado(
        usuario="Maria",
        setor=setor,
        titulo=titulo,
        descricao="Descrição do problema",
        status="Aberto",
        prioridade="Alta",
        autor_id=autor.id if autor else None,
    )
    db.session.add(chamado)
    db.session.commit()
    return chamado


def _token(client):
    resposta = client.post("/meu-token")
    return resposta.get_data(as_text=True).split("<code>")[1].split("</code>")[0]


def test_usuario_ve_na_lista_so_os_proprios_chamados(client, criar_usuario):
    outra = criar_usuario(nome="Outra", email="outra@teste.com")
    eu = _entrar(client, criar_usuario, "eu@teste.com")
    _chamado("Meu monitor piscando", autor=eu)
    _chamado("Impressora da outra", autor=outra, setor="Jurídico")
    _chamado("Aberto sem login")

    html = client.get("/chamados").get_data(as_text=True)

    assert "Meu monitor piscando" in html
    assert "Impressora da outra" not in html
    assert "Aberto sem login" not in html
    # O filtro de setor não entrega o setor dos chamados alheios.
    assert "Jurídico" not in html


def test_usuario_recebe_404_no_chamado_de_outra_pessoa(client, criar_usuario):
    outra = criar_usuario(nome="Outra", email="outra@teste.com")
    eu = _entrar(client, criar_usuario, "eu@teste.com")
    meu = _chamado("Meu chamado", autor=eu)
    alheio = _chamado("Chamado alheio", autor=outra)
    anonimo = _chamado("Chamado sem login")

    assert client.get(f"/chamados/{meu.id}").status_code == 200
    assert client.get(f"/chamados/{alheio.id}").status_code == 404
    assert client.get(f"/chamados/{anonimo.id}").status_code == 404


def test_dashboard_do_usuario_conta_so_os_proprios_chamados(client, criar_usuario):
    outra = criar_usuario(nome="Outra", email="outra@teste.com")
    eu = _entrar(client, criar_usuario, "eu@teste.com")
    _chamado("Meu chamado", autor=eu)
    for i in range(3):
        _chamado(f"Alheio {i}", autor=outra)

    html = client.get("/dashboard?periodo=tudo").get_data(as_text=True)

    assert "Meu chamado" in html
    assert "Alheio" not in html


def test_tecnico_continua_vendo_todos_os_chamados(client, criar_usuario):
    alguem = criar_usuario(nome="Alguém", email="alguem@teste.com")
    _entrar(client, criar_usuario, "tecnico@teste.com", tipo="Técnico")
    de_alguem = _chamado("Chamado de alguém", autor=alguem)
    anonimo = _chamado("Chamado sem login")

    html = client.get("/chamados").get_data(as_text=True)

    assert "Chamado de alguém" in html
    assert "Chamado sem login" in html
    assert client.get(f"/chamados/{de_alguem.id}").status_code == 200
    assert client.get(f"/chamados/{anonimo.id}").status_code == 200


def test_chamado_aberto_logado_fica_ligado_a_conta(client, criar_usuario):
    eu = _entrar(client, criar_usuario, "eu@teste.com")

    formulario = client.get("/chamado").get_data(as_text=True)
    assert f'value="{eu.nome}"' in formulario

    client.post(
        "/chamado",
        data={
            "usuario": eu.nome,
            "setor": "TI",
            "titulo": "Teclado sem resposta",
            "descricao": "Nenhuma tecla funciona",
            "prioridade": "Média",
        },
    )

    chamado = db.session.execute(
        db.select(Chamado).where(Chamado.titulo == "Teclado sem resposta")
    ).scalar_one()
    assert chamado.autor_id == eu.id


def test_chamado_aberto_sem_login_fica_sem_autor(client):
    client.post(
        "/chamado",
        data={
            "usuario": "Visitante",
            "setor": "TI",
            "titulo": "Mouse quebrado",
            "descricao": "O clique não funciona",
            "prioridade": "Média",
        },
    )

    chamado = db.session.execute(
        db.select(Chamado).where(Chamado.titulo == "Mouse quebrado")
    ).scalar_one()
    assert chamado.autor_id is None


def test_api_aplica_a_mesma_regra_do_usuario(client, criar_usuario):
    outra = criar_usuario(nome="Outra", email="outra@teste.com")
    eu = _entrar(client, criar_usuario, "eu@teste.com")
    cabecalho = {"Authorization": f"Bearer {_token(client)}"}
    meu = _chamado("Meu chamado", autor=eu)
    alheio = _chamado("Chamado alheio", autor=outra)

    lista = client.get("/api/v1/chamados", headers=cabecalho).get_json()
    assert [c["id"] for c in lista["chamados"]] == [meu.id]

    assert client.get(f"/api/v1/chamados/{meu.id}", headers=cabecalho).status_code == 200
    assert client.get(f"/api/v1/chamados/{alheio.id}", headers=cabecalho).status_code == 404

    criado = client.post(
        "/api/v1/chamados",
        headers=cabecalho,
        json={"usuario": "Eu", "setor": "TI", "titulo": "Via API", "descricao": "Teste"},
    ).get_json()
    assert criado["autor_id"] == eu.id


def test_admin_nao_exclui_quem_abriu_chamados(client, criar_usuario):
    autora = criar_usuario(nome="Autora", email="autora@teste.com")
    _chamado("Chamado da autora", autor=autora)
    _entrar(client, criar_usuario, "admin@teste.com", tipo="Administrador")

    client.post(f"/admin/usuarios/{autora.id}/excluir")

    assert db.session.get(Usuario, autora.id) is not None
