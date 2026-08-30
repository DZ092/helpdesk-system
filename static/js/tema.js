/**
 * Alternância de tema claro/escuro (issue #44).
 *
 * Duas partes, de propósito separadas:
 *
 * 1. `aplicarTemaSalvo()` — roda inline, no <head>, ANTES do CSS carregar.
 *    Só ela decide qual tema pintar na tela logo de cara: sem isso, a página
 *    sempre nasceria escura (o :root de style.css) e só trocaria de cor um
 *    instante depois, quando este arquivo carregasse — um "flash" visível.
 *
 * 2. O resto deste arquivo — o botão de trocar tema e o listener de clique —
 *    só existe nas páginas que têm o botão (ver `configurarBotaoDeTema`).
 *    Páginas sem botão (login, cadastro, abertura pública de chamado) usam
 *    só a parte 1: o tema nasce certo, mas não dá pra trocar manualmente ali.
 *
 * Prioridade de decisão, em ordem: escolha manual salva > preferência do
 * sistema operacional > escuro (mesma prioridade nas duas partes).
 */

const CHAVE_TEMA = "tema-preferido";

function temaSalvo() {
    try {
        return localStorage.getItem(CHAVE_TEMA);
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

function alternarTema() {
    const novoTema = temaAtivo() === "dark" ? "light" : "dark";
    aplicarTema(novoTema);
    salvarTema(novoTema);
    atualizarIconeBotao(novoTema);
}

function atualizarIconeBotao(tema) {
    const botao = document.getElementById("botao-tema");
    if (!botao) {
        return;
    }
    // O ícone mostra o tema para o qual o clique vai levar, não o atual —
    // é a mesma convenção de qualquer switch de tema: a lua aparece enquanto
    // está claro (convida a escurecer), o sol aparece enquanto está escuro.
    botao.textContent = tema === "dark" ? "☀️" : "🌙";
    botao.setAttribute(
        "aria-label",
        tema === "dark" ? "Ativar tema claro" : "Ativar tema escuro"
    );
}

/** Chamada depois que o DOM carrega, só nas páginas que têm o botão. */
function configurarBotaoDeTema() {
    const botao = document.getElementById("botao-tema");
    if (!botao) {
        return;
    }
    atualizarIconeBotao(temaAtivo());
    botao.addEventListener("click", alternarTema);
}

document.addEventListener("DOMContentLoaded", configurarBotaoDeTema);
