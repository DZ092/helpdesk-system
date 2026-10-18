"""Geometria dos gráficos SVG do dashboard (visual novo, Fase 1)."""

import math

import graficos

CIRCUNFERENCIA = 2 * math.pi * graficos.RAIO_DONUT


def test_barras_maior_valor_ocupa_100_por_cento():
    resultado = graficos.barras([("TI", 10), ("RH", 5)])

    assert resultado[0]["pct"] == 100
    assert resultado[1]["pct"] == 50
    assert resultado[1]["rotulo"] == "RH" and resultado[1]["valor"] == 5


def test_barras_com_tudo_zero_nao_divide_por_zero():
    assert [b["pct"] for b in graficos.barras([("TI", 0), ("RH", 0)])] == [0, 0]


def test_barras_lista_vazia():
    assert graficos.barras([]) == []


def test_donut_fatias_somam_a_circunferencia():
    fatias = graficos.donut([("Baixa", 1), ("Média", 2), ("Alta", 3), ("Crítica", 4)])

    assert math.isclose(sum(f["comprimento"] for f in fatias), CIRCUNFERENCIA, rel_tol=1e-9)


def test_donut_cada_fatia_comeca_onde_a_anterior_termina():
    fatias = graficos.donut([("Baixa", 1), ("Média", 3)])

    assert fatias[0]["dashoffset"] == "-0.00"
    assert float(fatias[1]["dashoffset"]) == -round(fatias[0]["comprimento"], 2)


def test_donut_com_uma_categoria_so_fecha_o_circulo():
    fatias = graficos.donut([("Baixa", 0), ("Média", 0), ("Alta", 5), ("Crítica", 0)])

    alta = fatias[2]
    assert math.isclose(alta["comprimento"], CIRCUNFERENCIA)
    assert alta["dasharray"] == f"{CIRCUNFERENCIA:.2f} 0.00"


def test_donut_total_zero_nao_divide_por_zero():
    assert [f["comprimento"] for f in graficos.donut([("Baixa", 0), ("Alta", 0)])] == [0, 0]


def test_linha_distribui_pontos_na_largura_e_inverte_o_eixo_y():
    resultado = graficos.linha([0, 5, 10], largura=600, altura=200, margem=24)

    assert resultado["marcas"] == [(24.0, 176.0), (300.0, 100.0), (576.0, 24.0)]
    assert resultado["pontos"] == "24.0,176.0 300.0,100.0 576.0,24.0"


def test_linha_com_valores_zerados_nao_divide_por_zero():
    resultado = graficos.linha([0, 0, 0])

    assert all(y == 176.0 for _, y in resultado["marcas"])


def test_linha_com_teto_compartilhado_usa_a_mesma_escala():
    resultado = graficos.linha([5], teto=10)

    assert resultado["marcas"] == [(24.0, 100.0)]
    assert [valor for _, valor in resultado["grade"]] == [0, 5, 10]


def test_empilhada_soma_100_por_cento():
    partes = graficos.empilhada([("Aberto", 1), ("Em andamento", 1), ("Resolvido", 2)])

    assert [p["x_pct"] for p in partes] == [0, 25, 50]
    assert math.isclose(sum(p["largura_pct"] for p in partes), 100)


def test_empilhada_total_zero():
    assert [p["largura_pct"] for p in graficos.empilhada([("Aberto", 0)])] == [0]
