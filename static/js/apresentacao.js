/**
 * Único toque de movimento que restou na vitrine pública (home, como
 * funciona, recursos) depois do redesign "profissional": números que sobem
 * contando quando entram na tela. O brilho que seguia o cursor e a entrada
 * animada de cartão/citação saíram junto com o resto da animação decorativa
 * (ver comentário do topo de apresentacao.css) — não faz sentido manter o
 * JavaScript que só preparava um efeito que o CSS não desenha mais.
 *
 * Um arquivo só serve as três páginas porque elas compartilham a mesma
 * estrutura (apresentacao.css). A função verifica se existe elemento antes
 * de fazer qualquer coisa, então rodar isso numa página sem número nenhum
 * não quebra nada.
 *
 * Se `prefers-reduced-motion` estiver ligado no sistema, os números
 * aparecem prontos, sem contar. Sem JavaScript nenhum, a página inteira
 * continua legível — os números só não sobem, aparecem com o valor final
 * de cara, porque já vêm assim no HTML.
 */

(function () {
    "use strict";

    var reduzMovimento = window.matchMedia &&
        window.matchMedia("(prefers-reduced-motion: reduce)").matches;

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
})();
