/**
 * Alternância de tema claro/escuro/âmbar (issue #44, ampliado na #79).
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
 *    Desde a #79 isso inclui a tela de login/cadastro e a abertura pública
 *    de chamado, não só as telas com usuário logado: quem ainda não fez
 *    login também pode preferir o tema âmbar em vez do claro/escuro padrão.
 *
 * Prioridade de decisão, em ordem: escolha manual salva > preferência do
 * sistema operacional > escuro (mesma prioridade nas duas partes).
 *
 * Três temas em vez de dois: em vez de um botão único que alterna entre dois
 * estados, o seletor mostra as três opções de uma vez (lua, sol, pôr do
 * sol) — com três estados um ciclo de cliques exigiria memorizar quantos
 * cliques faltam para o tema desejado.
 */

const CHAVE_TEMA = "tema-preferido";
const TEMAS = ["dark", "light", "ambar"];

const ICONE_POR_TEMA = {
    dark: "🌙",
    light: "☀️",
    ambar: "🌇",
};

const NOME_POR_TEMA = {
    dark: "Tema escuro",
    light: "Tema claro",
    ambar: "Tema âmbar (fim de tarde)",
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

/** Chamada depois que o DOM carrega, só nas páginas que têm o seletor. */
function configurarSeletorDeTema() {
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
