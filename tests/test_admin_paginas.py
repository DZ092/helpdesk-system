"""Páginas da administração no layout novo (visual novo, Fase 2)."""

import re

SENHA = "senha-de-teste"
SUB_ABAS = re.compile(r'<nav class="abas-secundarias".*?</nav>', re.S)


def _entrar_como_admin(client, criar_usuario):
    admin = criar_usuario(nome="Ana Admin", email="admin@teste.com", tipo="Administrador")
    client.post("/login", data={"email": "admin@teste.com", "senha": SENHA})
    return admin


def _sub_abas(html):
    bloco = SUB_ABAS.search(html)
    assert bloco, "sub-abas da administração não encontradas"
    return bloco.group(0)


def _layout_novo(html):
    assert 'class="topbar"' in html
    assert 'class="usuario-logado"' not in html
    assert 'style="' not in html
    assert "Voltar" not in html
    assert '<h1 class="pagina-titulo">Administração</h1>' in html


def test_usuarios_usa_o_layout_novo_com_a_sub_aba_ativa(client, criar_usuario):
    _entrar_como_admin(client, criar_usuario)

    html = client.get("/admin/usuarios").get_data(as_text=True)
    abas = _sub_abas(html)

    _layout_novo(html)
    assert re.search(r'href="/admin/usuarios"\s+aria-current="page">Usuários</a>', abas)
    assert re.search(r'href="/admin/logs"\s*>Logs</a>', abas)


def test_logs_usa_o_layout_novo_com_a_sub_aba_ativa(client, criar_usuario):
    _entrar_como_admin(client, criar_usuario)

    html = client.get("/admin/logs").get_data(as_text=True)
    abas = _sub_abas(html)

    _layout_novo(html)
    assert re.search(r'href="/admin/logs"\s+aria-current="page">Logs</a>', abas)
    assert re.search(r'href="/admin/usuarios"\s*>Usuários</a>', abas)
    assert "Mostrando 1 de 1 registro(s) — página 1 de 1" in html


def test_formularios_do_admin_nao_mudam(client, criar_usuario):
    admin = _entrar_como_admin(client, criar_usuario)
    outro = criar_usuario(nome="Bruno", email="bruno@teste.com", tipo="Usuário")

    html = client.get("/admin/usuarios").get_data(as_text=True)

    assert f'<form method="POST" action="/admin/usuarios/{outro.id}/tipo" class="form-tipo-usuario">' in html
    assert f'action="/admin/usuarios/{outro.id}/excluir"' in html
    assert 'data-nome="Bruno"' in html
    assert f'action="/admin/usuarios/{admin.id}/excluir"' not in html  # não se exclui
    assert re.search(r'<script nonce="[^"]+">\s*document\.querySelectorAll\("\.form-excluir"\)', html)


def test_trocar_perfil_pelo_painel_continua_funcionando(client, criar_usuario):
    _entrar_como_admin(client, criar_usuario)
    outro = criar_usuario(nome="Bruno", email="bruno@teste.com", tipo="Usuário")

    resposta = client.post(
        f"/admin/usuarios/{outro.id}/tipo",
        data={"tipo_usuario": "Técnico"},
        follow_redirects=True,
    )
    html = resposta.get_data(as_text=True)

    assert '<p class="sucesso">' in html  # a mensagem vem do base_app
    assert re.search(r'<option value="Técnico" selected>Técnico</option>', html)
