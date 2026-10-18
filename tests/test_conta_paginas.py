"""Token de API e troca de senha no layout novo (visual novo, Fase 2)."""

import re

SENHA = "senha-de-teste"


def _entrar(client, criar_usuario):
    criar_usuario(nome="Fulano", email="fulano@teste.com")
    client.post("/login", data={"email": "fulano@teste.com", "senha": SENHA})


def _layout_novo(html, titulo):
    assert 'class="topbar"' in html
    assert 'class="usuario-logado"' not in html
    assert 'style="' not in html
    assert "Voltar" not in html
    assert 'class="cartao cartao-estreito"' in html
    assert re.search(rf'<h1 class="pagina-titulo"[^>]*>{titulo}</h1>', html)


def test_meu_token_usa_o_layout_novo(client, criar_usuario):
    _entrar(client, criar_usuario)

    html = client.get("/meu-token").get_data(as_text=True)

    _layout_novo(html, "Meu token de API")
    assert "🔗" not in html
    assert "Você ainda não gerou nenhum token." in html
    assert ">Gerar token</button>" in html


def test_gerar_token_mostra_valor_e_scripts_com_nonce(client, criar_usuario):
    _entrar(client, criar_usuario)

    html = client.post("/meu-token").get_data(as_text=True)

    _layout_novo(html, "Meu token de API")
    assert 'id="botao-copiar-token"' in html
    assert 'id="botao-baixar-token"' in html
    assert re.search(r'<script nonce="[^"]+">\s*\(function \(\) \{\s*var botao = document\.getElementById\("botao-copiar-token"\)', html)


def test_quem_ja_tem_token_ve_gerar_novo(client, criar_usuario):
    _entrar(client, criar_usuario)
    client.post("/meu-token")

    html = client.get("/meu-token").get_data(as_text=True)

    assert "Você já tem um token gerado." in html
    assert ">Gerar novo token</button>" in html


def test_alterar_senha_usa_o_layout_novo(client, criar_usuario):
    _entrar(client, criar_usuario)

    html = client.get("/senha").get_data(as_text=True)

    _layout_novo(html, "Alterar senha")
    assert "🔑" not in html
    for nome in ("senha_atual", "nova_senha", "confirmacao"):
        assert f'name="{nome}"' in html


def test_alterar_senha_mostra_o_erro_no_cartao(client, criar_usuario):
    _entrar(client, criar_usuario)

    html = client.post(
        "/senha",
        data={"senha_atual": "errada-123", "nova_senha": "OutraSenha#2026", "confirmacao": "OutraSenha#2026"},
    ).get_data(as_text=True)

    assert '<p class="erro">Senha atual incorreta.</p>' in html
    _layout_novo(html, "Alterar senha")
