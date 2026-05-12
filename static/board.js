const boardTable = document.getElementById("board-table");
const activeCountEl = document.getElementById("active-count");
const freshCountEl = document.getElementById("fresh-count");
const staleCountEl = document.getElementById("stale-count");
const oldCountEl = document.getElementById("old-count");
const footerActiveEl = document.getElementById("footer-active");
const footerFreshEl = document.getElementById("footer-fresh");
const footerStaleEl = document.getElementById("footer-stale");
const footerOldEl = document.getElementById("footer-old");

async function fetchState() {
  const response = await fetch("/api/state", { cache: "no-store" });
  if (!response.ok) {
    throw new Error(`State request failed: ${response.status}`);
  }
  return response.json();
}

function renderBoard(state) {
  const quotes = state.quotes || [];
  const language = state.language || {};
  const board = language.board || {};
  const freshMinutes = Number(board.fresh_minutes || 10);
  const oldMinutes = Number(board.old_minutes || 30);
  const hubs = getBoardHubs(language);
  const terms = getBoardTerms(board, quotes);
  const quoteMap = new Map(quotes.map((quote) => [quoteKey(quote.hub_code, quote.term_code), quote]));
  const counts = countAgeBuckets(quotes, freshMinutes, oldMinutes);

  activeCountEl.textContent = quotes.length;
  staleCountEl.textContent = counts.stale;
  oldCountEl.textContent = counts.old;
  freshCountEl.textContent = counts.fresh;
  footerActiveEl.textContent = quotes.length;
  footerFreshEl.textContent = counts.fresh;
  footerStaleEl.textContent = counts.stale;
  footerOldEl.textContent = counts.old;

  boardTable.innerHTML = `
    <thead>
      ${renderGroupHeader(hubs, board.groups || [])}
      ${renderHubHeader(hubs)}
      ${renderSideHeader(hubs)}
    </thead>
    <tbody>
      ${terms.map((term) => renderTermRow(term, hubs, quoteMap, freshMinutes, oldMinutes)).join("")}
    </tbody>
  `;
}

function getBoardHubs(language) {
  const groups = language.board?.groups || [];
  const groupRank = new Map(groups.map((group, index) => [group, index]));
  const hubs = Object.entries(language.hubs || {}).map(([code, hub]) => ({
    code,
    name: hub.name || code,
    group: hub.group || "Other",
    order: Number(hub.board_order || 999),
  }));

  hubs.sort((left, right) => {
    const leftGroup = groupRank.has(left.group) ? groupRank.get(left.group) : 999;
    const rightGroup = groupRank.has(right.group) ? groupRank.get(right.group) : 999;
    return leftGroup - rightGroup || left.order - right.order || left.code.localeCompare(right.code);
  });
  return hubs;
}

function getBoardTerms(board, quotes) {
  const configured = (board.terms || []).map((term) => ({
    code: String(term.code || "").toUpperCase(),
    label: term.label || term.code,
    subtitle: term.subtitle || "",
  }));
  const existing = new Set(configured.map((term) => term.code));
  const dynamic = [];

  for (const quote of quotes) {
    const code = String(quote.term_code || "").toUpperCase();
    if (!code || existing.has(code)) {
      continue;
    }
    dynamic.push({
      code,
      label: quote.term_code || code,
      subtitle: quote.term_text || "",
    });
    existing.add(code);
  }

  return configured.concat(dynamic);
}

function renderGroupHeader(hubs, configuredGroups) {
  const groups = [];
  let index = 0;
  while (index < hubs.length) {
    const group = hubs[index].group || "Other";
    let span = 0;
    while (index + span < hubs.length && hubs[index + span].group === group) {
      span += 1;
    }
    groups.push({ name: group, span: span * 3 });
    index += span;
  }

  return `
    <tr class="group-row">
      <th class="corner-cell"></th>
      ${groups.map((group) => `
        <th class="group-cell ${groupClass(group.name, configuredGroups)}" colspan="${group.span}">
          ${escapeHtml(group.name)}
        </th>
      `).join("")}
    </tr>
  `;
}

function renderHubHeader(hubs) {
  return `
    <tr class="hub-row">
      <th class="strip-head">Strip</th>
      ${hubs.map((hub) => `
        <th class="hub-head" colspan="3">
          <strong>${escapeHtml(hub.code)}</strong>
          <span>${escapeHtml(hub.name)}</span>
        </th>
      `).join("")}
    </tr>
  `;
}

function renderSideHeader(hubs) {
  return `
    <tr class="side-row">
      <th class="strip-subhead"></th>
      ${hubs.map(() => `
        <th>Bid</th>
        <th>Offer</th>
        <th>Done</th>
      `).join("")}
    </tr>
  `;
}

function renderTermRow(term, hubs, quoteMap, freshMinutes, oldMinutes) {
  return `
    <tr class="term-row">
      <th class="strip-cell">
        <strong>${escapeHtml(term.label)}</strong>
        <span>${escapeHtml(term.subtitle)}</span>
      </th>
      ${hubs.map((hub) => renderHubCells(quoteMap.get(quoteKey(hub.code, term.code)), freshMinutes, oldMinutes)).join("")}
    </tr>
  `;
}

function renderHubCells(quote, freshMinutes, oldMinutes) {
  if (!quote) {
    return `
      <td class="matrix-cell empty">-</td>
      <td class="matrix-cell empty">-</td>
      <td class="matrix-cell empty">-</td>
    `;
  }

  const ageClass = getAgeClass(quote, freshMinutes, oldMinutes);
  const warnClass = quote.confidence === "high" ? "" : " low-confidence";
  const title = escapeHtml([quote.raw, ...(quote.warnings || [])].filter(Boolean).join(" | "));
  const bid = quote.bid === null || quote.bid === undefined ? "-" : formatNumber(quote.bid);
  const offer = quote.offer === null || quote.offer === undefined ? "-" : formatNumber(quote.offer);
  const meta = renderQuoteMeta(quote);
  const doneText = quote.done || "";

  return `
    <td class="matrix-cell bid-cell ${ageClass}${warnClass}" title="${title}">
      <strong>${escapeHtml(bid)}</strong>
      ${meta}
    </td>
    <td class="matrix-cell offer-cell ${ageClass}${warnClass}" title="${title}">
      <strong>${escapeHtml(offer)}</strong>
    </td>
    <td class="matrix-cell done-cell ${ageClass}${warnClass}" title="${title}">
      ${doneText ? `<strong>${escapeHtml(doneText)}</strong>` : "-"}
    </td>
  `;
}

function renderQuoteMeta(quote) {
  const parts = [];
  if (quote.size_text) {
    parts.push(quote.size_text);
  }
  if (quote.confidence !== "high") {
    parts.push("Review");
  }
  if (!parts.length) {
    return "";
  }
  return `<span>${escapeHtml(parts.join(" | "))}</span>`;
}

function quoteKey(hubCode, termCode) {
  return `${String(hubCode || "").toUpperCase()}|${String(termCode || "").toUpperCase()}`;
}

function groupClass(groupName, configuredGroups) {
  const index = configuredGroups.indexOf(groupName);
  return index >= 0 ? `group-${index}` : "group-other";
}

function countAgeBuckets(quotes, freshMinutes, oldMinutes) {
  const counts = { fresh: 0, stale: 0, old: 0 };
  for (const quote of quotes) {
    counts[getAgeClass(quote, freshMinutes, oldMinutes)] += 1;
  }
  return counts;
}

function getAgeClass(quote, freshMinutes, oldMinutes) {
  const minutes = Number(quote.age_seconds || 0) / 60;
  if (minutes < freshMinutes) {
    return "fresh";
  }
  if (minutes < oldMinutes) {
    return "stale";
  }
  return "old";
}

function formatNumber(value) {
  const numeric = Number(value);
  if (Number.isInteger(numeric)) {
    return String(numeric);
  }
  return numeric.toFixed(4).replace(/0+$/, "").replace(/\.$/, "");
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

async function refresh() {
  try {
    const state = await fetchState();
    renderBoard(state);
  } catch (error) {
    boardTable.innerHTML = `<tbody><tr><td class="empty-row">Board offline</td></tr></tbody>`;
  }
}

refresh();
setInterval(refresh, 1000);
