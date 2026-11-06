// Pequenos comportamentos de interface. O site funciona sem JavaScript.
document.addEventListener("DOMContentLoaded", () => {
  // Botões de impressão
  document.querySelectorAll("[data-imprimir]").forEach((botao) => {
    botao.addEventListener("click", () => window.print());
  });

  // Ajusta o texto de ajuda do campo de busca conforme o tipo escolhido
  const campo = document.querySelector("#q");
  const dicas = {
    todos: "Digite CPF, CNS ou nome do paciente…",
    cpf: "Digite o CPF (só números ou com pontos)",
    cns: "Digite os 15 números do Cartão SUS",
    nome: "Digite o nome completo do paciente",
  };
  document.querySelectorAll("input[name='tipo']").forEach((opcao) => {
    opcao.addEventListener("change", () => {
      if (campo) {
        campo.placeholder = dicas[opcao.value] || dicas.todos;
        campo.focus();
      }
    });
  });
});

// ---------------------------------------------------------------------------
// Acessibilidade: modo daltônico, tamanho da fonte e lupa
// ---------------------------------------------------------------------------
(() => {
  const raiz = document.documentElement;
  const salvar = (chave, valor) => { try { localStorage.setItem(chave, valor); } catch (e) {} };
  const NIVEL_MAX = 3;

  document.addEventListener("DOMContentLoaded", () => {
    // 1. Modo daltônico
    const btnDalt = document.getElementById("a11y-daltonico");
    const atualizarDalt = () => btnDalt.setAttribute("aria-pressed", raiz.hasAttribute("data-daltonico"));
    btnDalt?.addEventListener("click", () => {
      raiz.toggleAttribute("data-daltonico");
      salvar("a11y-daltonico", raiz.hasAttribute("data-daltonico") ? "1" : "0");
      atualizarDalt();
      lupa.recriar();
    });
    if (btnDalt) atualizarDalt();

    // 2. Tamanho da fonte (A− / A+)
    const btnMenos = document.getElementById("a11y-fonte-menos");
    const btnMais = document.getElementById("a11y-fonte-mais");
    const nivelAtual = () => parseInt(raiz.getAttribute("data-fonte") || "0", 10);
    const aplicarFonte = (nivel) => {
      nivel = Math.max(0, Math.min(NIVEL_MAX, nivel));
      if (nivel === 0) raiz.removeAttribute("data-fonte");
      else raiz.setAttribute("data-fonte", nivel);
      salvar("a11y-fonte", String(nivel));
      if (btnMenos) btnMenos.disabled = nivel === 0;
      if (btnMais) btnMais.disabled = nivel === NIVEL_MAX;
      lupa.recriar();
    };
    btnMenos?.addEventListener("click", () => aplicarFonte(nivelAtual() - 1));
    btnMais?.addEventListener("click", () => aplicarFonte(nivelAtual() + 1));
    aplicarFonte(nivelAtual());

    // 3. Lupa: copia a página e mostra ampliada num círculo que segue o mouse
    const btnLupa = document.getElementById("a11y-lupa");
    btnLupa?.addEventListener("click", () => lupa.alternar(btnLupa));
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape" && lupa.ligada) lupa.alternar(btnLupa);
    });
  });

  const lupa = {
    ligada: false,
    zoom: 2,
    el: null,
    conteudo: null,
    x: 0, y: 0,

    alternar(botao) {
      this.ligada = !this.ligada;
      botao.setAttribute("aria-pressed", this.ligada);
      raiz.classList.toggle("lupa-ligada", this.ligada);
      this.el = document.querySelector(".lupa");
      this.conteudo = this.el.querySelector(".lupa-conteudo");
      if (this.ligada) {
        this.recriar();
        this._mover = (e) => this.mover(e);
        this._sair = () => this.el.classList.remove("ativa");
        this._atualizar = () => this.recriarDepois();
        this._rolar = () => this.posicionar();
        window.addEventListener("scroll", this._rolar, { passive: true });
        document.addEventListener("mousemove", this._mover);
        document.addEventListener("mouseleave", this._sair);
        document.addEventListener("input", this._atualizar);
        window.addEventListener("resize", this._atualizar);
        document.addEventListener("toggle", this._atualizar, true); // <details> abrindo/fechando
      } else {
        this.el.classList.remove("ativa");
        this.conteudo.innerHTML = "";
        window.removeEventListener("scroll", this._rolar);
        document.removeEventListener("mousemove", this._mover);
        document.removeEventListener("mouseleave", this._sair);
        document.removeEventListener("input", this._atualizar);
        window.removeEventListener("resize", this._atualizar);
        document.removeEventListener("toggle", this._atualizar, true);
      }
    },

    // Cria uma cópia "somente leitura" da página dentro da lupa
    recriar() {
      if (!this.ligada || !this.conteudo) return;
      const estilo = getComputedStyle(document.body);
      const copia = document.createElement("div");
      Object.assign(copia.style, {
        width: document.documentElement.clientWidth + "px",
        minHeight: document.documentElement.scrollHeight + "px",
        display: estilo.display,
        flexDirection: estilo.flexDirection,
        fontFamily: estilo.fontFamily,
        fontSize: estilo.fontSize,
        lineHeight: estilo.lineHeight,
        color: estilo.color,
        background: estilo.backgroundColor,
      });
      const origem = Array.from(document.body.children)
        .filter((n) => !n.matches(".lupa, .acessibilidade, script"));
      origem.forEach((no) => {
        const clone = no.cloneNode(true);
        // Mantém o que o usuário digitou nos campos
        const camposOrig = no.querySelectorAll("input, select, textarea");
        clone.querySelectorAll("input, select, textarea").forEach((c, i) => {
          const o = camposOrig[i];
          if (!o) return;
          if (o.type === "checkbox" || o.type === "radio") c.checked = o.checked;
          else c.value = o.value;
        });
        clone.querySelectorAll("[id]").forEach((n) => n.removeAttribute("id"));
        if (clone.id) clone.removeAttribute("id");
        copia.appendChild(clone);
      });
      copia.setAttribute("inert", "");
      this.conteudo.replaceChildren(copia);
      this.conteudo.style.transform = "";
      this.posicionar();
    },

    recriarDepois() {
      clearTimeout(this._t);
      this._t = setTimeout(() => this.recriar(), 150);
    },

    mover(e) {
      this.x = e.clientX;
      this.y = e.clientY;
      // Não amplia a própria barra de acessibilidade
      const sobreBarra = e.target.closest && e.target.closest(".acessibilidade");
      this.el.classList.toggle("ativa", !sobreBarra);
      this.posicionar();
    },

    posicionar() {
      if (!this.el) return;
      const r = this.el.offsetWidth / 2 || 130;
      const z = this.zoom;
      const px = this.x + window.scrollX;
      const py = this.y + window.scrollY;
      this.el.style.left = this.x - r + "px";
      this.el.style.top = this.y - r + "px";
      this.conteudo.style.transform =
        `translate(${r - px * z}px, ${r - py * z}px) scale(${z})`;
    },
  };
})();
