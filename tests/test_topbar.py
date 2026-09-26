"""Topbar do layout novo (visual novo, Fase 1)."""

import re

SENHA = "senha-de-teste"


def _entrar(client, criar_usuario, tipo="Usuário", nome="Fulano"):
    email = f"{tipo.lower().replace('á', 'a').replace('é', 'e')}@teste.com"
    criar_usuario(nome=nome, email=email, tipo=tipo)
    client.post("/login", data={"email": email, "senha": SENHA})
    return client.get("/dashboard").get_data(as_text=True)


def test_dashboard_usa_a_topbar_com_a_aba_ativa(client, criar_usuario):
    html = _entrar(client, criar_usuario)

    assert 'class="topbar"' in html
    assert re.search(r'href="/dashboard"\s+aria-current="page"', html)
    assert not re.search(r'href="/chamados"\s+aria-current="page"', html)


def test_usuario_comum_nao_ve_abas_de_tecnico_nem_de_admin(client, criar_usuario):
    html = _entrar(client, criar_usuario, tipo="Usuário")

    assert ">Chamados</a>" in html
    assert ">Meus chamados</a>" not in html
    assert ">Admin</a>" not in html


def test_tecnico_ve_meus_chamados_mas_nao_admin(client, criar_usuario):
    html = _entrar(client, criar_usuario, tipo="Técnico")

    assert ">Meus chamados</a>" in html
    assert ">Admin</a>" not in html


def test_admin_ve_a_aba_admin(client, criar_usuario):
    html = _entrar(client, criar_usuario, tipo="Administrador")

    assert ">Meus chamados</a>" in html
    assert ">Admin</a>" in html


def test_topbar_tem_novo_chamado_menu_do_usuario_e_sair_com_csrf(client, criar_usuario):
    html = _entrar(client, criar_usuario)

    assert 'href="/chamado"' in html and "Novo chamado" in html
    assert 'href="/senha"' in html
    assert 'href="/meu-token"' in html
    assert re.search(r'<form method="POST" action="/logout">\s*<input type="hidden" name="csrf_token"', html)
    assert 'class="acoes"' not in html  # os botões antigos do rodapé do dashboard sumiram


def test_inicial_do_usuario_com_acento(client, criar_usuario):
    html = _entrar(client, criar_usuario, nome="Álvaro Souza")

    assert '<span class="menu-usuario-inicial" aria-hidden="true">Á</span>' in html


def test_script_de_tema_tem_nonce_e_ignora_tema_desconhecido(client, criar_usuario):
    """Quem tinha "ambar" salvo cai na preferência do sistema, não num tema sem estilo."""
    html = _entrar(client, criar_usuario)

    assert re.search(r'<script nonce="[^"]+">', html)
    assert 'if (tema !== "dark" && tema !== "light")' in html
    assert html.count('data-tema="') == 2
