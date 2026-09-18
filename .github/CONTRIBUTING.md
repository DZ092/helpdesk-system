# Contribuindo com o Help Desk System

Obrigado por considerar contribuir com este projeto! Este documento explica como você pode ajudar.

## Como contribuir

1. **Abra uma issue primeiro**: antes de começar a trabalhar em uma mudança grande, abra uma issue descrevendo o problema ou a melhoria proposta. Isso evita retrabalho e alinha expectativas.
2. **Faça um fork do repositório** e crie uma branch a partir da `main`:
   ```bash
   git checkout -b minha-feature
   ```
3. **Siga o padrão de código existente**: o projeto usa Python, Flask e SQLAlchemy. Mantenha a formatação e a organização já usadas no repositório.
4. **Escreva mensagens de commit claras**, descrevendo o que foi alterado e por quê.
5. **Teste suas mudanças** localmente antes de abrir o pull request.
6. **Abra o Pull Request** para a branch `main`, preenchendo o template de PR com uma descrição do que foi feito.

## Reportando bugs

Use o template de issue de bug, incluindo:

- Passos para reproduzir o problema
- Comportamento esperado x comportamento observado
- Screenshots, se possível
- Ambiente (sistema operacional, versão do Python, etc.)

## Sugerindo melhorias

Use o template de feature request, explicando o problema que a melhoria resolve e, se possível, uma proposta de solução.

## Configurando o ambiente localmente

```bash
git clone https://github.com/DZ092/helpdesk-system.git
cd helpdesk-system
python -m venv venv
source venv/bin/activate  # ou venv\Scripts\activate no Windows
pip install -r requirements.txt
```

Configure as variáveis de ambiente necessárias (banco de dados PostgreSQL, chave secreta do Flask etc.) antes de rodar a aplicação.

## Código de Conduta

Ao participar deste projeto, você concorda em seguir o [Código de Conduta](CODE_OF_CONDUCT.md).

## Dúvidas

Se tiver dúvidas, abra uma issue com a tag `pergunta` ou entre em contato pelos canais listados no perfil do repositório.
