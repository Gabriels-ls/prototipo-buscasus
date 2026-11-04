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
