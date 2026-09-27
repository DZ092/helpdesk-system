"""Lista geral e "Meus chamados" no layout novo (visual novo, Fase 2)."""

import re

from extensions import db
from models import Chamado

SENHA = "senha-de-teste"
EMOJIS_DE_STATUS = ("🔴", "🟡", "🟢")


def _entrar(client, criar_usuario, tipo="Usuário"):
    email = {"Usuário": "usuario@teste.com", "Técnico": "tecnico@teste.com"}[tipo]
    usuario = criar_usuario(nome=f"Pessoa {tipo}", email=email, tipo=tipo)
    client.post("/login", data={"email": email, "senha": SENHA})
    return usuario


def _chamado(titulo="Computador não liga", descricao="Tela preta ao ligar", status="Aberto", responsavel=None):
    chamado = Chamado(
        usuario="Maria",
        setor="Financeiro",
        titulo=titulo,
        descricao=descricao,
        status=status,
        prioridade="Alta",
        responsavel_id=responsavel.id if responsavel else None,
    )
    db.session.add(chamado)
    db.session.commit()
    return chamado


def _layout_novo(html):
    assert 'class="topbar"' in html
    assert 'class="usuario-logado"' not in html
    assert 'style="' not in html
    assert "Voltar" not in html
    for emoji in EMOJIS_DE_STATUS:
        assert emoji not in html


def test_lista_usa_o_layout_novo_com_titulo_e_descricao(client, criar_usuario):
    _entrar(client, criar_usuario)
    chamado = _chamado()

    html = client.get("/chamados").get_data(as_text=True)

    _layout_novo(html)
    assert '<h1 class="pagina-titulo">Chamados</h1>' in html
    assert f'<a class="chamado-titulo" href="/chamados/{chamado.id}">Computador não liga</a>' in html
    assert '<span class="chamado-descricao">Tela preta ao ligar</span>' in html
    assert '<span class="prioridade prioridade-alta">Alta</span>' in html
    assert '<span class="status status-aberto">Aberto</span>' in html


def test_lista_nao_repete_atalhos_que_estao_na_topbar(client, criar_usuario):
    _entrar(client, criar_usuario, tipo="Técnico")
    _chamado()

    html = client.get("/chamados").get_data(as_text=True)

    assert html.count("Novo chamado") == 1  # só o botão da topbar
    assert "Novo Chamado" not in html
    assert html.count('href="/meus-chamados"') == 1  # só a aba da topbar


def test_exportacao_so_para_tecnico_e_preserva_os_filtros(client, criar_usuario):
    _entrar(client, criar_usuario, tipo="Técnico")

    html = client.get("/chamados?status=Aberto").get_data(as_text=True)
    links = re.findall(r'href="(/chamados/exportar\?[^"]*)"', html)

    assert len(links) == 2
    assert all("status=Aberto" in link for link in links)
    assert any("formato=excel" in link for link in links)
    assert any("formato=pdf" in link for link in links)


def test_usuario_comum_nao_ve_exportacao(client, criar_usuario):
    _entrar(client, criar_usuario)

    html = client.get("/chamados").get_data(as_text=True)

    assert "/chamados/exportar" not in html
    assert "Exportar" not in html


def test_filtros_mantem_os_mesmos_campos_e_valores(client, criar_usuario):
    _entrar(client, criar_usuario)

    html = client.get("/chamados?busca=impressora&status=Resolvido").get_data(as_text=True)

    assert '<form method="GET" action="/chamados" class="filtros">' in html
    for nome in ("busca", "status", "prioridade", "setor", "responsavel", "data_inicio", "data_fim"):
        assert f'name="{nome}"' in html
    assert 'value="impressora"' in html
    assert '<option value="Resolvido" selected>' in html
    assert ">Aplicar</button>" in html
    assert 'href="/chamados" class="limpar-filtro"' in html


def test_paginacao_mantem_textos_e_marca_a_pagina_atual(client, criar_usuario):
    _entrar(client, criar_usuario)
    for i in range(16):  # 15 por página
        _chamado(titulo=f"Chamado {i}")

    pagina_1 = client.get("/chamados").get_data(as_text=True)
    pagina_2 = client.get("/chamados?pagina=2").get_data(as_text=True)

    assert "Mostrando 15 de 16 chamado(s) — página 1 de 2" in pagina_1
    assert "Próxima →" in pagina_1
    assert '<span class="pagina-atual" aria-current="page">1</span>' in pagina_1
    assert "← Anterior" in pagina_2
    assert "Mostrando 1 de 16 chamado(s) — página 2 de 2" in pagina_2


def test_lista_vazia_mostra_a_mensagem_sem_tabela(client, criar_usuario):
    _entrar(client, criar_usuario)

    html = client.get("/chamados?busca=nada-com-isso").get_data(as_text=True)

    assert "Nenhum chamado encontrado com os filtros selecionados." in html
    assert 'class="tabela-chamados"' not in html


def test_pagina_alem_do_fim_mantem_contagem_e_navegacao(client, criar_usuario):
    _entrar(client, criar_usuario)
    _chamado()

    resposta = client.get("/chamados?pagina=9")
    html = resposta.get_data(as_text=True)

    assert resposta.status_code == 200
    assert "Mostrando 0 de 1 chamado(s)" in html


def test_descricao_longa_continua_inteira_no_html(client, criar_usuario):
    _entrar(client, criar_usuario)
    descricao = "Linha de descrição comprida " * 20
    _chamado(descricao=descricao.strip())

    html = client.get("/chamados").get_data(as_text=True)

    assert descricao.strip() in html


def test_meus_chamados_usa_o_layout_novo(client, criar_usuario):
    tecnico = _entrar(client, criar_usuario, tipo="Técnico")
    _chamado(titulo="Meu chamado", descricao="Mouse sem resposta", responsavel=tecnico)
    _chamado(titulo="Chamado de outra pessoa")

    html = client.get("/meus-chamados").get_data(as_text=True)

    _layout_novo(html)
    assert '<h1 class="pagina-titulo">Meus chamados</h1>' in html
    assert '<span class="chamado-descricao">Mouse sem resposta</span>' in html
    assert "Chamado de outra pessoa" not in html
    assert "Exportar" not in html
    assert re.search(r'href="/meus-chamados"\s+aria-current="page"', html)


def test_meus_chamados_vazio_mostra_orientacao(client, criar_usuario):
    _entrar(client, criar_usuario, tipo="Técnico")

    html = client.get("/meus-chamados").get_data(as_text=True)

    assert "Você ainda não é responsável por nenhum chamado." in html
    assert 'class="tabela-chamados"' not in html
