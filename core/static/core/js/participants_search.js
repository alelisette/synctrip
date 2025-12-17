//-- Buscador en cliente con JavaScript -->

document.addEventListener("DOMContentLoaded", function () {
  const input = document.getElementById("search-participantes");
  const list = document.getElementById("lista-participantes");

  if (!input || !list) return;

  const items = list.querySelectorAll("li");

  input.addEventListener("input", function () {
    const q = input.value.toLowerCase().trim();

    items.forEach((li) => {
      const name = (li.dataset.name || "").toLowerCase();
      li.style.display = name.includes(q) ? "" : "none";
    });
  });
});
