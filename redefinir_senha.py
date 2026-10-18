"""Redefine a senha de um usuário pela linha de comando.

Serve para o caso clássico de suporte: o usuário esqueceu a senha e não
consegue entrar para trocá-la pela tela de "Alterar senha".

Como a assinatura da sessão deriva do hash da senha, redefinir aqui também
derruba automaticamente todas as sessões abertas daquela conta.

Uso:
    python redefinir_senha.py
"""

from getpass import getpass

from werkzeug.security import generate_password_hash

from app import create_app
from extensions import db
from models import Usuario
from seguranca import validar_forca_senha


def pedir_senha(usuario):
    """Pede a senha duas vezes, sem exibir na tela, e valida a força."""
    while True:
        senha = getpass("Nova senha (não aparece enquanto você digita): ")

        problema = validar_forca_senha(senha, usuario)
        if problema:
            print(f"{problema}\n")
            continue

        if senha != getpass("Repita a nova senha: "):
            print("As senhas não conferem. Tente de novo.\n")
            continue

        return senha


def main():
    email = input("E-mail do usuário: ").strip().lower()

    if not email:
        print("Nenhum e-mail informado. Saindo.")
        return

    app = create_app()

    with app.app_context():
        usuario = db.session.execute(
            db.select(Usuario).where(Usuario.email == email)
        ).scalar_one_or_none()

        if usuario is None:
            print(f"\nNenhuma conta encontrada com '{email}'.")
            print("Contas cadastradas:")
            for u in db.session.execute(db.select(Usuario).order_by(Usuario.nome)).scalars():
                print(f"  - {u.email}  ({u.tipo_usuario})")
            return

        print(f"\nRedefinindo a senha de {usuario.nome} ({usuario.tipo_usuario}).")
        senha = pedir_senha(usuario)

        usuario.senha = generate_password_hash(senha)
        db.session.commit()

        print(f"\nSenha de {usuario.nome} redefinida.")
        print("As sessões abertas dessa conta foram encerradas.")


if __name__ == "__main__":
    main()