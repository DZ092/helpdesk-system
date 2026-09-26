"""Geometria dos gráficos SVG do dashboard (visual novo, Fase 1).

Só contas: nenhum acesso a banco e nenhum HTML. As macros de
templates/_graficos.html imprimem os valores prontos daqui como atributos SVG
(`width`, `points`, `stroke-dasharray`...) — nunca como `style="…"`, que o CSP
da aplicação (style-src sem 'unsafe-inline') bloquearia.
"""

import math

RAIO_DONUT = 40  # no viewBox 0 0 100 100, centro em 50,50


def barras(itens):
    """Barras horizontais: cada valor em % do maior valor da lista."""
    maior = max((valor for _, valor in itens), default=0)
    return [
        {"rotulo": rotulo, "valor": valor, "pct": round(valor * 100 / maior, 1) if maior else 0}
        for rotulo, valor in itens
    ]


def donut(itens, raio=RAIO_DONUT):
    """Fatias de um donut desenhado com stroke-dasharray num <circle>.

    Cada fatia é um traço de `comprimento` seguido de um vão do resto da
    circunferência; o dashoffset negativo empurra o traço para começar onde a
    fatia anterior terminou.
    """
    circunferencia = 2 * math.pi * raio
    total = sum(valor for _, valor in itens)
    fatias = []
    acumulado = 0.0
    for rotulo, valor in itens:
        comprimento = circunferencia * valor / total if total else 0
        fatias.append(
            {
                "rotulo": rotulo,
                "valor": valor,
                "comprimento": comprimento,
                "dasharray": f"{comprimento:.2f} {circunferencia - comprimento:.2f}",
                "dashoffset": f"{-acumulado:.2f}",
            }
        )
        acumulado += comprimento
    return fatias


def linha(valores, largura=600, altura=200, margem=24, teto=None):
    """Pontos de uma série num gráfico de linhas.

    `teto` é o valor que ocupa a altura útil inteira; passe o mesmo teto para
    duas séries dividirem a mesma escala. A grade traz 0, a metade (arredondada)
    e o teto, sem repetir valores.
    """
    teto = max(valores, default=0) if teto is None else teto
    teto = teto or 1
    largura_util = largura - 2 * margem
    altura_util = altura - 2 * margem
    passo = largura_util / (len(valores) - 1) if len(valores) > 1 else 0

    def y_de(valor):
        return round(altura - margem - (valor / teto) * altura_util, 1)

    marcas = [(round(margem + indice * passo, 1), y_de(valor)) for indice, valor in enumerate(valores)]
    niveis = sorted({0, round(teto / 2), teto})
    return {
        "pontos": " ".join(f"{x},{y}" for x, y in marcas),
        "marcas": marcas,
        "grade": [(y_de(nivel), nivel) for nivel in niveis],
    }


def empilhada(itens):
    """Barra única dividida em partes proporcionais (posição e largura em %)."""
    total = sum(valor for _, valor in itens)
    partes = []
    posicao = 0.0
    for rotulo, valor in itens:
        largura = valor * 100 / total if total else 0
        partes.append({"rotulo": rotulo, "valor": valor, "x_pct": round(posicao, 2), "largura_pct": round(largura, 2)})
        posicao += largura
    return partes
