"""Detalhe do chamado no layout novo (visual novo, Fase 2)."""

import re
from datetime import datetime

from extensions import db
from models import Chamado

SENHA = "senha-de-teste"
EMOJIS_DE_STATUS = ("🔴", "🟡", "🟢")
ETAPA = re.compile(r'<li class="(etapa[^"]*)"( aria-current="step")?>')


def _entrar(client, criar_usuario, tipo="Usuário"):
    email = {"Usuário": "usuario@teste.com", "Técnico": "tecnico@teste.com"}[tipo]
    usuario = criar_usuario(nome=f"Pessoa {tipo}", email=email, tipo=tipo)
    client.post("/login", data={"email": email, "senha": SENHA})
    return usuario


def _chamado(status="Aberto", resolvido_em=None):
    chamado = Chamado(
        usuario="Maria",
        setor="Financeiro",
        titulo="Computador não liga",
        descricao="Tela preta ao ligar",
        status=status,
        prioridade="Crítica",
        resolvido_em=resolvido_em,
    )
    db.session.add(chamado)
    db.session.commit()
    return chamado


def _etapas(html):
    return [(classe, bool(atual)) for classe, atual in ETAPA.findall(html)]


def test_detalhe_usa_o_layout_novo(client, criar_usuario):
    _entrar(client, criar_usuario)
    chamado = _chamado()

    html = client.get(f"/chamados/{chamado.id}").get_data(as_text=True)

    assert 'class="topbar"' in html
    assert 'class="usuario-logado"' not in html
    assert 'style="' not in html
    assert "Voltar" not in html
    for emoji in EMOJIS_DE_STATUS:
        assert emoji not in html
    assert '<a href="/chamados">← Chamados</a>' in html
    assert f'<p class="pagina-rotulo">Chamado #{chamado.id}</p>' in html
    assert '<h1 class="pagina-titulo">Computador não liga</h1>' in html
    assert re.search(r'href="/chamados"\s+aria-current="page"', html)  # aba Chamados


def test_informacoes_mostram_badge_e_responsavel_pendente(client, criar_usuario):
    _entrar(client, criar_usuario)
    chamado = _chamado()

    html = client.get(f"/chamados/{chamado.id}").get_data(as_text=True)

    assert "<dt>Prioridade</dt><dd><span class=\"prioridade prioridade-critica\">Crítica</span></dd>" in html
    assert "<dt>Responsável</dt><dd>Aguardando atribuição</dd>" in html


def test_trilha_de_chamado_aberto_marca_a_primeira_etapa(client, criar_usuario):
    _entrar(client, criar_usuario)
    chamado = _chamado("Aberto")

    html = client.get(f"/chamados/{chamado.id}").get_data(as_text=True)

    assert _etapas(html) == [("etapa etapa-atual", True), ("etapa", False), ("etapa", False)]


def test_trilha_de_chamado_em_andamento_marca_a_segunda_etapa(client, criar_usuario):
    _entrar(client, criar_usuario)
    chamado = _chamado("Em andamento")

    html = client.get(f"/chamados/{chamado.id}").get_data(as_text=True)

    assert _etapas(html) == [
        ("etapa etapa-concluida", False),
        ("etapa etapa-atual", True),
        ("etapa", False),
    ]


def test_trilha_de_chamado_resolvido_mostra_a_data_de_resolucao(client, criar_usuario):
    _entrar(client, criar_usuario)
    chamado = _chamado("Resolvido", resolvido_em=datetime(2026, 3, 10, 15, 0))

    html = client.get(f"/chamados/{chamado.id}").get_data(as_text=True)

    assert _etapas(html) == [
        ("etapa etapa-concluida", False),
        ("etapa etapa-concluida", False),
        ("etapa etapa-atual", True),
    ]
    assert '<span class="etapa-data">10/03/2026 às 12:00</span>' in html  # UTC-3


def test_resolvido_em_antigo_nao_aparece_em_chamado_reaberto(client, criar_usuario):
    """Dado legado: status Aberto com resolvido_em preenchido não pode mostrar
    data na etapa Resolvido, que ainda não foi alcançada."""
    _entrar(client, criar_usuario)
    chamado = _chamado("Aberto", resolvido_em=datetime(2026, 3, 10, 15, 0))

    html = client.get(f"/chamados/{chamado.id}").get_data(as_text=True)

    assert "10/03/2026 às 12:00" not in html


def test_status_desconhecido_conta_como_resolvido_na_trilha(client, criar_usuario):
    _entrar(client, criar_usuario)
    chamado = _chamado("Cancelado")

    html = client.get(f"/chamados/{chamado.id}").get_data(as_text=True)

    assert _etapas(html)[2] == ("etapa etapa-atual", True)


def test_tecnico_ve_o_botao_de_atendimento_sem_emoji(client, criar_usuario):
    _entrar(client, criar_usuario, tipo="Técnico")
    aberto = _chamado("Aberto")
    andamento = _chamado("Em andamento")

    html_aberto = client.get(f"/chamados/{aberto.id}").get_data(as_text=True)
    html_andamento = client.get(f"/chamados/{andamento.id}").get_data(as_text=True)

    assert f'action="/chamados/{aberto.id}/status"' in html_aberto
    assert '<input type="hidden" name="status" value="Em andamento">' in html_aberto
    assert ">Iniciar atendimento</button>" in html_aberto
    assert '<input type="hidden" name="status" value="Resolvido">' in html_andamento
    assert ">Marcar como resolvido</button>" in html_andamento
    assert "▶" not in html_aberto
    assert "✓ Marcar" not in html_andamento


def test_sem_botao_de_atendimento_para_usuario_comum(client, criar_usuario):
    _entrar(client, criar_usuario)
    aberto = _chamado("Aberto")

    html = client.get(f"/chamados/{aberto.id}").get_data(as_text=True)

    assert "/status" not in html
    assert "/comentarios" not in html


def test_sem_botao_de_atendimento_em_chamado_resolvido(client, criar_usuario):
    _entrar(client, criar_usuario, tipo="Técnico")
    resolvido = _chamado("Resolvido")

    html = client.get(f"/chamados/{resolvido.id}").get_data(as_text=True)

    assert f'action="/chamados/{resolvido.id}/status"' not in html
    assert f'action="/chamados/{resolvido.id}/comentarios"' in html  # técnico ainda comenta


def test_historico_mostra_comentarios_e_formulario_do_tecnico(client, criar_usuario):
    _entrar(client, criar_usuario, tipo="Técnico")
    chamado = _chamado("Em andamento")

    vazio = client.get(f"/chamados/{chamado.id}").get_data(as_text=True)
    client.post(f"/chamados/{chamado.id}/comentarios", data={"mensagem": "Troquei o cabo de energia"})
    html = client.get(f"/chamados/{chamado.id}").get_data(as_text=True)

    assert "Ainda não há atualizações neste chamado." in vazio
    assert re.search(r'<li class="historico-item">.*Troquei o cabo de energia', html, re.S)
    assert f'action="/chamados/{chamado.id}/comentarios"' in html
    assert 'enctype="multipart/form-data"' in html
    assert 'name="mensagem"' in html and 'name="anexos"' in html


def test_resolver_pelo_detalhe_continua_funcionando(client, criar_usuario):
    _entrar(client, criar_usuario, tipo="Técnico")
    chamado = _chamado("Em andamento")

    client.post(f"/chamados/{chamado.id}/status", data={"status": "Resolvido"})
    html = client.get(f"/chamados/{chamado.id}").get_data(as_text=True)

    assert _etapas(html)[2] == ("etapa etapa-atual", True)
    assert html.count('class="etapa-data"') == 2
