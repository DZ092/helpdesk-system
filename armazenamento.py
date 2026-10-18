"""Upload de anexos de imagem para o Cloudinary (issue #6).

Isolado num módulo próprio pelo mesmo motivo de `emails.py`: a rota não
precisa saber que o armazenamento é o Cloudinary, só que existe uma função
que recebe um arquivo enviado e devolve uma URL — trocar de provedor no
futuro fica restrito a este arquivo.
"""

import os

import cloudinary
import cloudinary.uploader
from flask import current_app

# Apenas imagem: é o que o formulário e a tela de detalhe sabem exibir. Aceitar
# qualquer tipo de arquivo abriria a porta para hospedar executáveis ou PDFs
# enormes num plano gratuito pensado para fotos de tela e prints de erro.
EXTENSOES_PERMITIDAS = {"png", "jpg", "jpeg", "webp"}

# Teto por arquivo. Sem ele, um único anexo poderia consumir sozinho boa parte
# da cota gratuita do Cloudinary — a mesma lógica do LIMITE_EXPORTACAO em
# `rotas/chamados.py`, aplicada aqui à entrada em vez de à saída.
TAMANHO_MAXIMO_BYTES = 5 * 1024 * 1024

_configurado = False


def _configurar():
    """Aplica as credenciais do Cloudinary uma vez por processo.

    Não dá para configurar na importação do módulo: os testes e o
    desenvolvimento local sobem a aplicação depois que o `.env` já foi lido
    por `load_dotenv()` em `app.py`, mas a ordem de import não garante isso —
    ler o ambiente aqui dentro, sob demanda, evita depender dessa ordem.
    """
    global _configurado
    if _configurado:
        return
    cloudinary.config(
        cloud_name=os.environ.get("CLOUDINARY_CLOUD_NAME"),
        api_key=os.environ.get("CLOUDINARY_API_KEY"),
        api_secret=os.environ.get("CLOUDINARY_API_SECRET"),
        secure=True,
    )
    _configurado = True


def extensao_valida(nome_arquivo):
    """True se o nome do arquivo termina numa extensão de imagem aceita."""
    if "." not in nome_arquivo:
        return False
    return nome_arquivo.rsplit(".", 1)[1].lower() in EXTENSOES_PERMITIDAS


def _tamanho_excedido(arquivo):
    """True se o stream do upload passa de `TAMANHO_MAXIMO_BYTES`.

    `FileStorage` não expõe um tamanho pronto — o jeito confiável de medir sem
    carregar o arquivo inteiro na memória é ir até o fim do stream com
    `seek`/`tell` e voltar pro início, senão o Cloudinary (ou a gravação do
    `Anexo`) leria um stream já consumido.
    """
    arquivo.stream.seek(0, os.SEEK_END)
    tamanho = arquivo.stream.tell()
    arquivo.stream.seek(0)
    return tamanho > TAMANHO_MAXIMO_BYTES


def enviar_anexo(arquivo):
    """Sobe um `FileStorage` para o Cloudinary e devolve a URL segura.

    Devolve `None` (em vez de levantar) quando o Cloudinary não está
    configurado, o arquivo passa do tamanho máximo ou a chamada falha — para
    que a rota decida se isso é motivo de recusar o formulário inteiro ou só
    de seguir sem o anexo — ela quem sabe se o upload era obrigatório ou
    opcional naquele ponto.
    """
    if not os.environ.get("CLOUDINARY_CLOUD_NAME"):
        current_app.logger.warning("CLOUDINARY_CLOUD_NAME não configurado — upload ignorado.")
        return None

    if _tamanho_excedido(arquivo):
        current_app.logger.info(
            "Anexo '%s' descartado: acima do limite de %d bytes.",
            arquivo.filename,
            TAMANHO_MAXIMO_BYTES,
        )
        return None

    _configurar()

    try:
        resultado = cloudinary.uploader.upload(
            arquivo,
            folder="helpdesk-chamados",
            allowed_formats=list(EXTENSOES_PERMITIDAS),
        )
        return resultado["secure_url"]
    except Exception:
        current_app.logger.exception("Falha ao enviar anexo para o Cloudinary.")
        return None
