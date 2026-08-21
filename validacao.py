"""Leitura e saneamento de campos de formulário.

Enquanto os formulários não forem classes do Flask-WTF, estes dois helpers
evitam repetir `request.form.get(...).strip()[:n]` em cada rota.
"""

from flask import request


def campo_obrigatorio(nome, tamanho_maximo):
    """Lê um campo do formulário, remove espaços e corta no tamanho da coluna."""
    valor = request.form.get(nome, "").strip()
    return valor[:tamanho_maximo]


def inteiro_ou_none(valor):
    try:
        return int(valor)
    except (TypeError, ValueError):
        return None
