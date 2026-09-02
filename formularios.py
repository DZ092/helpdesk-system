"""Classes de formulário do Flask-WTF, uma por tela.

Cada classe substitui os `request.form.get(...)` que antes viviam na rota. O
CSRF é automático: o `CSRFProtect` em extensions.py cobre toda classe que
herda de FlaskForm, sem precisar de nada extra aqui ou no template.

`validar_forca_senha` (seguranca.py) também verifica se a senha contém o
nome/e-mail do usuário — checagem que depende de quem está logado e por isso
não dá para embutir como validator de campo. A rota continua chamando
`validar_forca_senha(form.nova_senha.data, usuario)` depois de `form.validate()`
e devolvendo o erro pelo mesmo caminho dos demais, via `form.nova_senha.errors`.
As classes abaixo só cobrem as regras que não dependem do usuário (tamanho,
senha comum, só números etc.), para o formulário já recusar isso sozinho.
"""

from flask_wtf import FlaskForm
from wtforms import EmailField, PasswordField, SelectField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Email, EqualTo, Length, ValidationError

from constantes import PRIORIDADES, STATUS_CHAMADO, TAMANHO_MINIMO_SENHA
from seguranca import validar_forca_senha


def _senha_forte(form, campo):
    """Regras de força que não dependem do usuário logado (ver docstring acima)."""
    problema = validar_forca_senha(campo.data)
    if problema:
        raise ValidationError(problema)


class FormularioCadastro(FlaskForm):
    nome = StringField(
        "Nome",
        validators=[DataRequired(message="Preencha nome e e-mail."), Length(max=100)],
    )
    email = EmailField(
        "E-mail",
        validators=[DataRequired(message="Preencha nome e e-mail."), Email(message="Preencha nome e e-mail."), Length(max=120)],
    )
    senha = PasswordField(
        "Senha",
        validators=[
            DataRequired(message=f"A senha precisa ter pelo menos {TAMANHO_MINIMO_SENHA} caracteres."),
            _senha_forte,
        ],
    )
    submit = SubmitField("Cadastrar")


class FormularioLogin(FlaskForm):
    email = EmailField("E-mail", validators=[DataRequired(), Email()])
    senha = PasswordField("Senha", validators=[DataRequired()])
    submit = SubmitField("Entrar")


class FormularioAlterarSenha(FlaskForm):
    # DataRequired aqui só cobre campo vazio: comprimento e regras de força
    # ficam inteiramente com `_senha_forte`, que chama `validar_forca_senha` —
    # duplicar `Length` faria o WTForms parar nele antes, com uma mensagem
    # genérica em vez de "pelo menos N caracteres".
    senha_atual = PasswordField("Senha atual", validators=[DataRequired(message="Senha atual incorreta.")])
    nova_senha = PasswordField("Nova senha", validators=[DataRequired(), _senha_forte])
    confirmacao = PasswordField(
        "Repita a nova senha",
        validators=[
            DataRequired(),
            EqualTo("nova_senha", message="A nova senha e a confirmação não conferem."),
        ],
    )
    submit = SubmitField("Alterar senha")


class FormularioEsqueciSenha(FlaskForm):
    email = EmailField("E-mail da conta", validators=[DataRequired(), Email()])
    submit = SubmitField("Enviar link de redefinição")


class FormularioRedefinirSenha(FlaskForm):
    nova_senha = PasswordField("Nova senha", validators=[DataRequired(), _senha_forte])
    confirmacao = PasswordField(
        "Confirme a nova senha",
        validators=[
            DataRequired(),
            EqualTo("nova_senha", message="A nova senha e a confirmação não conferem."),
        ],
    )
    submit = SubmitField("Redefinir senha")


class FormularioChamado(FlaskForm):
    """Abertura pública de chamado (rota `/chamado`).

    Sem `submit`/CSRF diferentes do padrão: o template já usa `csrf_token()`
    manual, que o `FlaskForm` também aceita — nenhuma mudança de template é
    necessária além de trocar os `name=` soltos pelos campos do form.
    """

    usuario = StringField(
        "Usuário",
        validators=[DataRequired(message="Preencha todos os campos do chamado."), Length(max=100)],
    )
    setor = StringField(
        "Setor",
        validators=[DataRequired(message="Preencha todos os campos do chamado."), Length(max=100)],
    )
    titulo = StringField(
        "Título do problema",
        validators=[DataRequired(message="Preencha todos os campos do chamado."), Length(max=200)],
    )
    descricao = TextAreaField(
        "Descrição",
        validators=[DataRequired(message="Preencha todos os campos do chamado.")],
    )
    # Sem `choices` restritas: um valor fora de `PRIORIDADES` (campo adulterado
    # no cliente, por exemplo) precisa continuar caindo no reaproveitamento
    # silencioso para "Média" que a rota já fazia, não virar erro de validação.
    prioridade = StringField("Prioridade")
    submit = SubmitField("Enviar chamado")


class FormularioStatusChamado(FlaskForm):
    """Atualização de status pelo técnico/administrador (`/chamados/<id>/status`)."""

    status = SelectField(
        "Status",
        choices=[(valor, valor) for valor in STATUS_CHAMADO],
        validators=[DataRequired(message="Status inválido.")],
    )
    submit = SubmitField("Atualizar status")


class FormularioComentarioChamado(FlaskForm):
    """Comentário interno de atendimento (`/chamados/<id>/comentarios`)."""

    mensagem = TextAreaField(
        "Adicionar atualização",
        validators=[DataRequired(message="A mensagem da atualização não pode ficar vazia.")],
    )
    submit = SubmitField("Adicionar atualização")
