/**
 * Pequenos toques de movimento na vitrine pública (home, como funciona,
 * recursos): números que sobem contando quando entram na tela, um brilho
 * que acompanha o cursor nos grupos de cartão, e uma entrada mais elaborada
 * só no ponto mais importante de cada página.
 *
 * Um arquivo só serve as três páginas porque elas compartilham a mesma
 * estrutura (apresentacao.css). Cada função verifica se o elemento que
 * precisa existe antes de fazer qualquer coisa, então rodar isso numa
 * página que não tem, por exemplo, cartão de citação não quebra nada.
 *
 * Duas regras seguidas em tudo aqui:
 * - se `prefers-reduced-motion` estiver ligado no sistema, nada anima:
 *   os números aparecem prontos e os elementos do "momento de entrada"
 *   nunca ganham a classe que os esconde primeiro;
 * - sem JavaScript nenhum, a página inteira continua legível: as classes
 *   que escondem o estado inicial só existem porque este arquivo as
 *   adiciona; elas não estão no HTML nem no CSS de origem.
 */

(function () {
    "use strict";

    var reduzMovimento = window.matchMedia &&
        window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    // ---- Números que sobem contando ao entrar na tela ---------------------

    function contarAte(elemento) {
        var textoOriginal = elemento.textContent.trim();
        var valorFinal = parseInt(textoOriginal.replace(/[^\d]/g, ""), 10);
        if (isNaN(valorFinal)) {
            return;
        }
        var sufixo = textoOriginal.replace(/^[\d.,]+/, "");
        var duracaoMs = 900;
        var inicio = null;

        function passo(agora) {
            if (inicio === null) {
                inicio = agora;
            }
            var progresso = Math.min((agora - inicio) / duracaoMs, 1);
            var facilitado = 1 - Math.pow(1 - progresso, 3);
            elemento.textContent = Math.round(valorFinal * facilitado) + sufixo;
            if (progresso < 1) {
                window.requestAnimationFrame(passo);
            } else {
                elemento.textContent = textoOriginal;
            }
        }
        window.requestAnimationFrame(passo);
    }

    var numeros = document.querySelectorAll(".hero-regua-item .n, .numero-inline");
    if (numeros.length && "IntersectionObserver" in window && !reduzMovimento) {
        var observadorNumeros = new IntersectionObserver(function (entradas) {
            entradas.forEach(function (entrada) {
                if (entrada.isIntersecting) {
                    contarAte(entrada.target);
                    observadorNumeros.unobserve(entrada.target);
                }
            });
        }, { threshold: 0.6 });
        numeros.forEach(function (numero) {
            observadorNumeros.observe(numero);
        });
    }

    // ---- Brilho que acompanha o cursor nos grupos de cartão ---------------

    function ativarBrilho(seletorGrupo, seletorCartao) {
        var grupo = document.querySelector(seletorGrupo);
        if (!grupo || reduzMovimento) {
            return;
        }
        grupo.addEventListener("pointermove", function (evento) {
            var cartao = evento.target.closest(seletorCartao);
            if (!cartao || !grupo.contains(cartao)) {
                return;
            }
            var retangulo = cartao.getBoundingClientRect();
            cartao.style.setProperty("--brilho-x", (evento.clientX - retangulo.left) + "px");
            cartao.style.setProperty("--brilho-y", (evento.clientY - retangulo.top) + "px");
        });
    }
    ativarBrilho(".lista-recursos", ".recurso-apresentacao");
    ativarBrilho(".cartao-passos", ".passo-apresentacao");
    ativarBrilho(".grade-links-apresentacao", ".cartao-link-apresentacao");

    // ---- Um momento de entrada mais elaborado, só uma vez por página ------
    //
    // De propósito isso não roda em cada seção da página conforme ela entra
    // na tela — isso é o efeito de "revelar ao rolar" repetido demais que a
    // gente decidiu não usar. Em vez disso, cada página tem só UM elemento
    // (a citação, o cartão de destaque, ou o bloco dos 3 passos) que ganha
    // essa entrada, e só ele.

    var momento = document.querySelector(".citacao-cartao") ||
        document.querySelector(".recurso-destaque") ||
        document.querySelector(".cartao-passos");

    if (momento && "IntersectionObserver" in window && !reduzMovimento) {
        momento.classList.add("pronto-para-entrar");
        var observadorMomento = new IntersectionObserver(function (entradas) {
            entradas.forEach(function (entrada) {
                if (entrada.isIntersecting) {
                    entrada.target.classList.remove("pronto-para-entrar");
                    entrada.target.classList.add("em-cena");
                    observadorMomento.unobserve(entrada.target);
                }
            });
        }, { threshold: 0.35 });
        observadorMomento.observe(momento);
    }
})();
