/**
 * Alternância de tema claro/escuro (issue #44). O terceiro tema, "fim de
 * tarde" (issue #79), saiu no visual novo (Fase 1): não combinava com o
 * acento azul. Quem tinha essa escolha salva cai na regra abaixo, como quem
 * nunca escolheu.
 *
 * Duas partes, de propósito separadas:
 *
 * 1. `aplicarTemaSalvo()` — roda inline, no <head>, ANTES do CSS carregar.
 *    Só ela decide qual tema pintar na tela logo de cara: sem isso, a página
 *    sempre nasceria escura (o :root de style.css) e só trocaria de cor um
 *    instante depois, quando este arquivo carregasse — um "flash" visível.
 *
 * 2. O resto deste arquivo — o seletor de tema e o listener de clique — só
 *    existe nas páginas que têm o seletor (ver `configurarSeletorDeTema`).
 *
 * Prioridade de decisão, em ordem: escolha manual salva > preferência do
 * sistema operacional > escuro (mesma prioridade nas duas partes). Valor
 * salvo que não está em TEMAS conta como "sem escolha".
 */

const CHAVE_TEMA = "tema-preferido";
const TEMAS = ["dark", "light"];

const ICONE_POR_TEMA = {
    dark: "🌙",
    light: "☀️",
};

const NOME_POR_TEMA = {
    dark: "Tema escuro",
    light: "Tema claro",
};

function temaSalvo() {
    try {
        const valor = localStorage.getItem(CHAVE_TEMA);
        return TEMAS.includes(valor) ? valor : null;
    } catch (erro) {
        // Navegador com localStorage bloqueado (modo privado restritivo,
        // política de cookies de terceiros etc.) — segue sem persistência
        // em vez de quebrar a página.
        return null;
    }
}

function salvarTema(tema) {
    try {
        localStorage.setItem(CHAVE_TEMA, tema);
    } catch (erro) {
        // Mesmo caso de acima: se não der para salvar, a troca ainda
        // funciona para a sessão atual, só não persiste na próxima visita.
    }
}

function temaPreferidoDoSistema() {
    const prefereClaro = window.matchMedia && window.matchMedia("(prefers-color-scheme: light)").matches;
    return prefereClaro ? "light" : "dark";
}

function temaAtivo() {
    return temaSalvo() || temaPreferidoDoSistema();
}

function aplicarTema(tema) {
    document.documentElement.setAttribute("data-theme", tema);
}

/** Chamada inline no <head>, antes do CSS. Ver aviso no topo do arquivo. */
function aplicarTemaSalvo() {
    aplicarTema(temaAtivo());
}

function escolherTema(tema) {
    aplicarTema(tema);
    salvarTema(tema);
    atualizarSeletor(tema);
}

/** Marca visualmente qual botão do seletor representa o tema ativo. */
function atualizarSeletor(tema) {
    const seletor = document.getElementById("seletor-tema");
    if (!seletor) {
        return;
    }
    seletor.querySelectorAll("[data-tema]").forEach((botao) => {
        const ativo = botao.getAttribute("data-tema") === tema;
        botao.classList.toggle("ativo", ativo);
        botao.setAttribute("aria-pressed", ativo ? "true" : "false");
    });
}

/** Limpa um valor de tema inválido salvo no localStorage (ex.: o terceiro
 * tema que existiu antes da Fase 1), pra páginas antigas não ficarem
 * guardando esse lixo pra sempre — a leitura em temaSalvo() já ignora esse
 * valor, isto só limpa o storage. */
function limparTemaInvalidoSalvo() {
    try {
        const valor = localStorage.getItem(CHAVE_TEMA);
        if (valor !== null && !TEMAS.includes(valor)) {
            localStorage.removeItem(CHAVE_TEMA);
        }
    } catch (erro) {
        // Sem localStorage não há o que limpar.
    }
}

/** Chamada depois que o DOM carrega, só nas páginas que têm o seletor. */
function configurarSeletorDeTema() {
    limparTemaInvalidoSalvo();
    aplicarTema(temaAtivo());
    const seletor = document.getElementById("seletor-tema");
    if (!seletor) {
        return;
    }
    seletor.querySelectorAll("[data-tema]").forEach((botao) => {
        const tema = botao.getAttribute("data-tema");
        botao.textContent = ICONE_POR_TEMA[tema] || "";
        botao.setAttribute("aria-label", NOME_POR_TEMA[tema] || tema);
        botao.addEventListener("click", () => escolherTema(tema));
    });
    atualizarSeletor(temaAtivo());
}

document.addEventListener("DOMContentLoaded", configurarSeletorDeTema);
