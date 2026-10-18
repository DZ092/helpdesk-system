"""Paleta e temas do visual novo (Fase 1): contraste medido nos próprios tokens.

Os pares abaixo são texto × fundo que aparecem de verdade na interface. O
mínimo é 4.5:1 (texto normal, WCAG AA) — inclusive texto de botão.
"""

import colorsys
import re
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
CSS = (RAIZ / "static" / "css" / "style.css").read_text(encoding="utf-8")


def _bloco(seletor):
    inicio = CSS.index(seletor + " {")
    return CSS[inicio : CSS.index("}", inicio)]


def _tokens(seletor):
    return dict(re.findall(r"--([a-z0-9-]+):\s*(#[0-9A-Fa-f]{6})\s*;", _bloco(seletor)))


def _luminancia(hexa):
    canais = [int(hexa[i : i + 2], 16) / 255 for i in (1, 3, 5)]
    lineares = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in canais]
    return 0.2126 * lineares[0] + 0.7152 * lineares[1] + 0.0722 * lineares[2]


def contraste(a, b):
    claro, escuro = sorted((_luminancia(a), _luminancia(b)), reverse=True)
    return (claro + 0.05) / (escuro + 0.05)


ESCURO = _tokens(":root")
CLARO = {**ESCURO, **_tokens('[data-theme="light"]')}

PARES = [
    ("texto", "superficie"),
    ("texto-muted", "superficie"),
    ("texto-fraco", "superficie"),
    ("acento", "superficie"),
    ("acento", "superficie-alt"),
    ("texto-botao", "acento-solido"),
    ("aviso-texto", "superficie"),
    ("prioridade-alta-texto", "superficie"),
]
PARES_CLARO = PARES + [
    ("texto-muted", "bg"),
    ("texto-fraco", "bg"),
    ("sucesso-texto", "superficie"),
]


@pytest.mark.parametrize("texto, fundo", PARES)
def test_contraste_do_tema_escuro(texto, fundo):
    assert contraste(ESCURO[texto], ESCURO[fundo]) >= 4.5, (texto, fundo)


@pytest.mark.parametrize("texto, fundo", PARES_CLARO)
def test_contraste_do_tema_claro(texto, fundo):
    assert contraste(CLARO[texto], CLARO[fundo]) >= 4.5, (texto, fundo)


def test_css_nao_tem_mais_o_tema_ambar():
    assert 'data-theme="ambar"' not in CSS


def test_tema_js_so_conhece_escuro_e_claro():
    js = (RAIZ / "static" / "js" / "tema.js").read_text(encoding="utf-8")
    assert 'const TEMAS = ["dark", "light"];' in js
    assert "ambar" not in js


def test_nenhum_template_oferece_o_tema_ambar():
    for arquivo in sorted((RAIZ / "templates").glob("*.html")):
        assert 'data-tema="ambar"' not in arquivo.read_text(encoding="utf-8"), arquivo.name


def test_botoes_usam_acento_solido_como_fundo():
    """Branco sobre --acento (#2D8CF0) dá 3.43:1; botão usa --acento-solido."""
    for nome in ("style.css", "apresentacao.css"):
        css = (RAIZ / "static" / "css" / nome).read_text(encoding="utf-8")
        assert "background: var(--acento);" not in css, nome


def _matiz(hexa):
    """Matiz (0-360) do hex, via HLS — usado só para medir distância entre cores
    que já passam no contraste, não para julgar contraste em si."""
    r, g, b = (int(hexa[i : i + 2], 16) / 255 for i in (1, 3, 5))
    matiz, _, _ = colorsys.rgb_to_hls(r, g, b)
    return matiz * 360


@pytest.mark.parametrize("tokens", [ESCURO, CLARO], ids=["escuro", "claro"])
def test_prioridade_alta_tem_matiz_distante_do_aviso(tokens):
    """--aviso-texto (Média) e --prioridade-alta-texto (Alta) precisam se
    distinguir por matiz, não só por claridade, nos dois temas."""
    diferenca = abs(_matiz(tokens["aviso-texto"]) - _matiz(tokens["prioridade-alta-texto"]))
    assert diferenca >= 15


def test_contraste_cartao_hero_acento():
    """O cartão flutuante do hero da apresentação tem fundo fixo claro nos
    dois temas (não segue --acento); --cartao-hero-acento existe pra dar
    contraste ali mesmo quando o tema ativo é o escuro."""
    apresentacao = (RAIZ / "static" / "css" / "apresentacao.css").read_text(encoding="utf-8")
    cartao_hero_bg = re.search(r"--cartao-hero-bg:\s*(#[0-9A-Fa-f]{6})\s*;", apresentacao).group(1)
    assert contraste(ESCURO["cartao-hero-acento"], cartao_hero_bg) >= 4.5
