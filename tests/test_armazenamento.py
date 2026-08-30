"""Validação de extensão, tamanho e configuração do upload de anexos (issue #6).

`enviar_anexo` de verdade fala com o Cloudinary — isolado aqui só o que roda
sem rede: a checagem de extensão, o teto de tamanho e o comportamento sem
credenciais configuradas. A integração com a rota (o que acontece quando o
upload é bem-sucedido) é coberta em `test_rotas.py`, com `enviar_anexo`
substituído por monkeypatch.
"""

import io

from werkzeug.datastructures import FileStorage

from armazenamento import EXTENSOES_PERMITIDAS, TAMANHO_MAXIMO_BYTES, extensao_valida


def test_aceita_extensoes_de_imagem():
    for extensao in EXTENSOES_PERMITIDAS:
        assert extensao_valida(f"foto.{extensao}")


def test_aceita_extensao_maiuscula():
    assert extensao_valida("FOTO.PNG")


def test_recusa_extensao_fora_da_lista():
    assert not extensao_valida("documento.pdf")
    assert not extensao_valida("script.exe")


def test_recusa_nome_sem_extensao():
    assert not extensao_valida("semextensao")


def test_enviar_anexo_sem_credenciais_devolve_none(app, monkeypatch):
    """Sem CLOUDINARY_CLOUD_NAME no ambiente, o upload é ignorado, não quebra."""
    monkeypatch.delenv("CLOUDINARY_CLOUD_NAME", raising=False)

    from armazenamento import enviar_anexo

    with app.app_context():
        assert enviar_anexo(object()) is None


def test_enviar_anexo_acima_do_tamanho_maximo_devolve_none(app, monkeypatch):
    """Um arquivo maior que o teto é descartado antes de chamar o Cloudinary."""
    monkeypatch.setenv("CLOUDINARY_CLOUD_NAME", "conta-de-teste")

    from armazenamento import enviar_anexo

    conteudo_grande = b"x" * (TAMANHO_MAXIMO_BYTES + 1)
    arquivo = FileStorage(stream=io.BytesIO(conteudo_grande), filename="foto.png")

    with app.app_context():
        assert enviar_anexo(arquivo) is None


def test_enviar_anexo_no_limite_do_tamanho_nao_e_descartado_por_tamanho(app, monkeypatch):
    """No limite exato, a checagem de tamanho deixa passar — só falharia depois,
    na chamada real ao Cloudinary (que este teste não faz, de propósito)."""
    from armazenamento import _tamanho_excedido

    conteudo_no_limite = b"x" * TAMANHO_MAXIMO_BYTES
    arquivo = FileStorage(stream=io.BytesIO(conteudo_no_limite), filename="foto.png")

    assert not _tamanho_excedido(arquivo)
    # O stream volta pro início depois da medição, pronto para o upload de verdade.
    assert arquivo.stream.tell() == 0


def test_excluir_comentario_isolado_nao_apaga_o_anexo(app, criar_usuario):
    """`Anexo` tem dois relacionamentos (chamado e comentário) — só o do
    chamado carrega `cascade="all, delete-orphan"`. Repetir a cascade também
    no lado do comentário faria dois "donos" disputarem o mesmo `Anexo`:
    bastaria excluir um comentário isolado (algo que hoje nenhuma rota faz,
    mas que o modelo não deveria depender disso pra ficar correto) para
    apagar o anexo por baixo do pano, mesmo sem o chamado ser excluído.
    """
    from extensions import db
    from models import Anexo, Comentario, Chamado

    with app.app_context():
        usuario = criar_usuario(tipo="Administrador")
        chamado = Chamado(
            usuario="Rafael", setor="TI", titulo="Teste", descricao="desc",
            status="Aberto", prioridade="Alta",
        )
        db.session.add(chamado)
        db.session.commit()

        comentario = Comentario(chamado_id=chamado.id, autor_id=usuario.id, mensagem="oi")
        db.session.add(comentario)
        db.session.commit()

        anexo = Anexo(
            chamado_id=chamado.id, comentario_id=comentario.id,
            url="http://x/img.png", nome_original="img.png",
        )
        db.session.add(anexo)
        db.session.commit()

        db.session.delete(comentario)
        db.session.commit()

        assert db.session.execute(db.select(Anexo)).scalars().all() != []
