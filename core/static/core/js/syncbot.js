(function () {
  function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== "") {
      const cookies = document.cookie.split(";");
      for (let i = 0; i < cookies.length; i++) {
        const c = cookies[i].trim();
        if (c.substring(0, name.length + 1) === name + "=") {
          cookieValue = decodeURIComponent(c.substring(name.length + 1));
          break;
        }
      }
    }
    return cookieValue;
  }

  document.addEventListener("DOMContentLoaded", function () {
    const tab = document.getElementById("syncbot-tab");
    const drawer = document.getElementById("syncbot-drawer");
    const closeBtn = document.getElementById("syncbot-close");
    const backdrop = document.getElementById("syncbot-backdrop");
    const sendBtn = document.getElementById("syncbot-send");
    const input = document.getElementById("syncbot-text");
    const messages = document.getElementById("syncbot-messages");

    if (!tab || !drawer) return; // si no está el widget, salimos

    const chatUrl = tab.dataset.chatUrl;
    const historyUrl = tab.dataset.historyUrl;

    let historyLoaded = false;

    function addBubble(text, who) {
      const div = document.createElement("div");
      div.className = "syncbot-bubble " + (who === "user" ? "user" : "bot");
      div.textContent = text;
      messages.appendChild(div);
      messages.scrollTop = messages.scrollHeight;
      return div;
    }

    function clearMessages() {
      messages.innerHTML = "";
    }

    async function loadHistory() {
      if (historyLoaded) return;
      historyLoaded = true;

      try {
        const res = await fetch(historyUrl);
        const data = await res.json();

        clearMessages();

        if (!res.ok) {
          addBubble(data.error || "No se pudo cargar el historial.", "bot");
          return;
        }

        if (!data.messages || data.messages.length === 0) {
          addBubble(
            "Hola 👋 Soy SyncBot. Pregúntame por itinerario, transporte, comida o actividades para este viaje.",
            "bot"
          );
          return;
        }

        data.messages.forEach((m) => {
          if (m.role === "user") addBubble(m.content, "user");
          else if (m.role === "assistant") addBubble(m.content, "bot");
        });
      } catch (e) {
        clearMessages();
        addBubble("Error cargando el historial.", "bot");
      }
    }

    async function openDrawer() {
      drawer.classList.add("open");
      drawer.setAttribute("aria-hidden", "false");
      backdrop.hidden = false;

      await loadHistory();
      setTimeout(() => input.focus(), 50);
    }

    function closeDrawer() {
      drawer.classList.remove("open");
      drawer.setAttribute("aria-hidden", "true");
      backdrop.hidden = true;
    }

    tab.addEventListener("click", openDrawer);
    closeBtn.addEventListener("click", closeDrawer);
    backdrop.addEventListener("click", closeDrawer);

    async function sendMessage() {
  const text = input.value.trim();
  if (!text) return;

  addBubble(text, "user");
  input.value = "";

  sendBtn.disabled = true;

  //burbuja “Escribiendo…” al final del chat
  const typingBubble = addBubble("Escribiendo…", "bot");
  typingBubble.classList.add("typing"); 

//Función para enviar el mensaje al servidor
  try {
    const res = await fetch(chatUrl, {
      method: "POST", // Usar POST para enviar datos
      headers: {
        "Content-Type": "application/json", //Indicar que enviamos JSON
        "X-CSRFToken": getCookie("csrftoken"), 
      },
      body: JSON.stringify({ message: text }),//Convertir el mensaje a JSON
    });

    const data = await res.json();

    typingBubble.remove();

    if (!res.ok) {
      addBubble(data.error || "Error desconocido", "bot");
    } else {
      addBubble(data.reply, "bot");
    }
  } catch (e) {
    typingBubble.remove();
    addBubble("Error de conexión.", "bot");
  } finally {
    sendBtn.disabled = false;
    messages.scrollTop = messages.scrollHeight;
    input.focus();
  }
}
    sendBtn.addEventListener("click", sendMessage);
    input.addEventListener("keydown", (e) => {
      if (e.key === "Enter") sendMessage();
      if (e.key === "Escape") closeDrawer();
    });
  });
})();
