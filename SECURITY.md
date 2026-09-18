# Política de Segurança

## Versões suportadas

Este é um projeto de portfólio com uma única linha de desenvolvimento — não
há versões antigas mantidas em paralelo. Correções de segurança são
aplicadas apenas na versão mais recente da branch `main`.

| Versão | Suportada |
| ------ | --------- |
| 1.2.x  | ✅        |
| < 1.2  | ❌        |

## Reportando uma vulnerabilidade

Se você encontrar uma vulnerabilidade de segurança neste projeto, por favor
**não abra uma issue pública**. Em vez disso, entre em contato diretamente:

- E-mail: eduardocoelhopro@gmail.com
- Ou pelo perfil do GitHub: [@DZ092](https://github.com/DZ092)

Ao reportar, inclua, se possível:

- Uma descrição do problema e o impacto potencial.
- Passos para reproduzir (endpoint, payload, condições necessárias).
- Versão ou commit afetado.

Este é um projeto pessoal mantido fora de horário de trabalho, então não há
um SLA formal de resposta — mas todo reporte é levado a sério e recebe
retorno assim que possível, normalmente em até alguns dias. Vulnerabilidades
confirmadas são corrigidas e, quando fizer sentido, documentadas no
changelog do projeto sem expor detalhes de exploração antes da correção
estar publicada.

## Escopo

Este projeto é uma aplicação de estudo/portfólio (Flask + SQLite/Postgres,
hospedada no Render). Vulnerabilidades relevantes incluem, por exemplo:

- Bypass de autenticação ou de controle de acesso por perfil (usuário,
  técnico, administrador).
- Injeção (SQL, template, comandos).
- Exposição de dados sensíveis (senhas, tokens de API, e-mails de outros
  usuários).
- CSRF, XSS ou open redirect.

Relatórios sobre configuração de infraestrutura de terceiros (Render,
provedor de e-mail, etc.) fora do código deste repositório estão fora de
escopo.
