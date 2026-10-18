"""Leitura e saneamento de valores de filtro.

`campo_obrigatorio` existiu aqui enquanto as rotas liam formulários direto de
`request.form`; a migração para Flask-WTF (issues #15/#50/#51/#54/#55) tirou
essa responsabilidade das rotas e a função ficou sem nenhuma chamada — removida
nesta limpeza. `inteiro_ou_none` continua em uso (filtros de `/chamados`).
"""


def inteiro_ou_none(valor):
    try:
        return int(valor)
    except (TypeError, ValueError):
        return None
