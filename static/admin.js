const rawInput = document.getElementById("raw-input");
const ingestButton = document.getElementById("ingest-button");
const sampleButton = document.getElementById("sample-button");
const saveHubButton = document.getElementById("save-hub-button");
const adminStatus = document.getElementById("admin-status");
const quoteBody = document.getElementById("admin-quote-body");
const editDialog = document.getElementById("edit-dialog");
const editForm = document.getElementById("edit-form");
const cancelEditButton = document.getElementById("cancel-edit-button");

let latestQuotes = [];

async function postJson(url, payload) {
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const body = await response.json();
  if (!response.ok) {
    throw new Error(body.error || `Request failed: ${response.status}`);
  }
  return body;
}

async function fetchState() {
  const response = await fetch("/api/state", { cache: "no-store" });
  if (!response.ok) {
    throw new Error(`State request failed: ${response.status}`);
  }
  return response.json();
}

async function refreshAdmin() {
  try {
    const state = await fetchState();
    latestQuotes = state.quotes || [];
    adminStatus.textContent = `${latestQuotes.length} active | stale after ${state.stale_minutes} min`;
    renderAdminQuotes(latestQuotes);
  } catch (error) {
    adminStatus.textContent = "Offline";
  }
}

function renderAdminQuotes(quotes) {
  if (!quotes.length) {
    quoteBody.innerHTML = `<tr><td colspan="6">No active quotes.</td></tr>`;
    return;
  }

  quoteBody.innerHTML = quotes.map((quote) => `
    <tr>
      <td>${escapeHtml(quote.hub_code || "UNK")}</td>
      <td>${escapeHtml(quote.term_text || quote.term_code || "Unknown")}</td>
      <td>${escapeHtml(quote.market_text || "--")}</td>
      <td>${escapeHtml(quote.size_text || "")}</td>
      <td class="raw-cell">${escapeHtml(quote.raw || "")}</td>
      <td class="action-cell">
        <button type="button" data-action="edit" data-id="${quote.id}" class="secondary">Edit</button>
        <button type="button" data-action="delete" data-id="${quote.id}" class="danger">Delete</button>
      </td>
    </tr>
  `).join("");
}

ingestButton.addEventListener("click", async () => {
  const raw = rawInput.value.trim();
  if (!raw) {
    return;
  }
  await postJson("/api/ingest", { raw });
  rawInput.value = "";
  await refreshAdmin();
});

sampleButton.addEventListener("click", () => {
  rawInput.value = "Jv27 HSC 22/21 1/2 day";
  rawInput.focus();
});

saveHubButton.addEventListener("click", async () => {
  const payload = {
    code: document.getElementById("hub-code").value,
    name: document.getElementById("hub-name").value,
    aliases: document.getElementById("hub-aliases").value,
    default_sign: document.getElementById("hub-sign").value,
  };
  await postJson("/api/language/hubs", payload);
  document.getElementById("hub-code").value = "";
  document.getElementById("hub-name").value = "";
  document.getElementById("hub-aliases").value = "";
  await refreshAdmin();
});

quoteBody.addEventListener("click", async (event) => {
  const button = event.target.closest("button[data-action]");
  if (!button) {
    return;
  }
  const quote = latestQuotes.find((item) => item.id === button.dataset.id);
  if (!quote) {
    return;
  }

  if (button.dataset.action === "edit") {
    openEditDialog(quote);
    return;
  }

  if (button.dataset.action === "delete") {
    await postJson("/api/quotes/delete", { id: quote.id });
    await refreshAdmin();
  }
});

function openEditDialog(quote) {
  document.getElementById("edit-id").value = quote.id;
  document.getElementById("edit-hub-code").value = quote.hub_code || "";
  document.getElementById("edit-hub-name").value = quote.hub_name || "";
  document.getElementById("edit-term-code").value = quote.term_code || "";
  document.getElementById("edit-term-text").value = quote.term_text || "";
  document.getElementById("edit-bid").value = quote.bid ?? "";
  document.getElementById("edit-offer").value = quote.offer ?? "";
  document.getElementById("edit-size").value = quote.size_text || "";
  document.getElementById("edit-display").value = quote.display || "";
  editDialog.showModal();
}

editForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const payload = {
    id: document.getElementById("edit-id").value,
    hub_code: document.getElementById("edit-hub-code").value.toUpperCase(),
    hub_name: document.getElementById("edit-hub-name").value,
    term_code: document.getElementById("edit-term-code").value.toUpperCase(),
    term_text: document.getElementById("edit-term-text").value,
    bid: toNumberOrNull(document.getElementById("edit-bid").value),
    offer: toNumberOrNull(document.getElementById("edit-offer").value),
    size_text: document.getElementById("edit-size").value,
    display: document.getElementById("edit-display").value,
    confidence: "high",
  };
  await postJson("/api/quotes/edit", payload);
  editDialog.close();
  await refreshAdmin();
});

cancelEditButton.addEventListener("click", () => {
  editDialog.close();
});

function toNumberOrNull(value) {
  if (value === "") {
    return null;
  }
  return Number(value);
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

refreshAdmin();
setInterval(refreshAdmin, 2000);
