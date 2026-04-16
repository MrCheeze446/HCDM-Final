const searchForm = document.querySelector("#search-form");
const searchQuery = document.querySelector("#search-query");
const searchRegex = document.querySelector("#search-regex");
const status = document.querySelector("#status");
const logList = document.querySelector("#log-list");
const detailEmpty = document.querySelector("#detail-empty");
const detailView = document.querySelector("#detail-view");
const logName = document.querySelector("#log-name");
const logLanguage = document.querySelector("#log-language");
const summary = document.querySelector("#summary");
const crashTypes = document.querySelector("#crash-types");
const findings = document.querySelector("#findings");
const rawLogContent = document.querySelector("#raw-log-content");

let activeLogName = "";
let currentLogs = [];

loadLogs();

searchForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  await loadLogs();
});

searchQuery.addEventListener("input", async () => {
  await loadLogs();
});

searchRegex.addEventListener("change", async () => {
  await loadLogs();
});

async function loadLogs() {
  const params = new URLSearchParams();
  const query = searchQuery.value.trim();
  if (query) {
    params.set("query", query);
  }
  if (searchRegex.checked) {
    params.set("regex", "1");
  }

  const requestUrl = params.size > 0 ? `/api/logs?${params.toString()}` : "/api/logs";
  const response = await fetch(requestUrl);
  const payload = await response.json();

  if (!response.ok) {
    status.textContent = payload.error || "Failed to load example logs.";
    currentLogs = [];
    renderLogList(currentLogs);
    detailEmpty.hidden = false;
    detailView.hidden = true;
    return;
  }

  currentLogs = payload.logs;
  renderLogList(currentLogs);

  if (currentLogs.length === 0) {
    activeLogName = "";
    detailEmpty.hidden = false;
    detailView.hidden = true;
    status.textContent = query
      ? "No logs matched the current search."
      : "No example logs available.";
    return;
  }

  status.textContent = `${currentLogs.length} log${currentLogs.length === 1 ? "" : "s"} matched.`;
  const nextLogName = currentLogs.some((log) => log.name === activeLogName)
    ? activeLogName
    : currentLogs[0].name;
  if (nextLogName) {
    await fetchLogDetail(nextLogName, false);
  }
}

function renderLogList(logs) {
  logList.innerHTML = logs
    .map(
      (log) => `
        <button class="log-row${log.name === activeLogName ? " active" : ""}" data-log-name="${escapeAttribute(log.name)}" type="button">
          <span class="log-row-header">
            <strong>${escapeHtml(log.name)}</strong>
            <span class="log-row-language">${formatLabel(log.language)}</span>
          </span>
          <span class="log-row-summary">
            ${log.summary.crashes} crashes · ${log.summary.warnings} warnings
          </span>
          <span class="log-row-message">${escapeHtml(log.primary_message)}</span>
        </button>
      `,
    )
    .join("");

  logList.querySelectorAll(".log-row").forEach((button) => {
    button.addEventListener("click", async () => {
      const nextLogName = button.dataset.logName;
      if (!nextLogName) {
        return;
      }
      await loadLogDetail(nextLogName);
    });
  });
}

async function loadLogDetail(name) {
  await fetchLogDetail(name, true);
}

async function fetchLogDetail(name, refreshListStatus) {
  activeLogName = name;
  status.textContent = `Loading ${name}...`;

  const response = await fetch(`/api/logs/${encodeURIComponent(name)}`);
  const payload = await response.json();
  if (!response.ok) {
    status.textContent = payload.error || "Failed to load log details.";
    return;
  }

  renderResults(payload);
  renderLogList(currentLogs);
  if (refreshListStatus) {
    status.textContent = `Viewing ${name}.`;
  }
}

function renderResults(payload) {
  detailEmpty.hidden = true;
  detailView.hidden = false;
  logName.textContent = payload.name;
  logLanguage.textContent = formatLabel(payload.analysis.language);

  const cards = [
    { label: "Warnings", value: payload.analysis.summary.warnings },
    { label: "Crashes", value: payload.analysis.summary.crashes },
    { label: "Total", value: payload.analysis.summary.total_findings },
  ];

  summary.innerHTML = cards
    .map(
      (card) => `
        <article class="summary-card">
          <h2>${card.label}</h2>
          <strong>${card.value}</strong>
        </article>
      `,
    )
    .join("");

  const crashTypeEntries = Object.entries(payload.analysis.crash_types);
  if (crashTypeEntries.length > 0) {
    crashTypes.innerHTML = crashTypeEntries
      .map(([type, count]) => `<span class="chip">${formatLabel(type)}: ${count}</span>`)
      .join("");
  } else {
    crashTypes.innerHTML = "";
  }

  if (payload.analysis.findings.length === 0) {
    findings.innerHTML = `<article class="finding"><p class="finding-title">No warnings or crashes were detected.</p></article>`;
    rawLogContent.textContent = payload.content;
    return;
  }

  findings.innerHTML = payload.analysis.findings
    .map(
      (finding) => `
        <article class="finding" data-category="${finding.category}">
          <div class="finding-header">
            <h3 class="finding-title">${formatFindingTitle(finding)}</h3>
            <span class="finding-meta">${formatLineRange(finding)}</span>
          </div>
          <p class="finding-message">${escapeHtml(finding.message)}</p>
          <pre>${escapeHtml(finding.context)}</pre>
        </article>
      `,
    )
    .join("");

  rawLogContent.textContent = payload.content;
}

function formatLineRange(finding) {
  const endLineNumber = finding.end_line_number || finding.line_number;
  if (endLineNumber === finding.line_number) {
    return `Line ${finding.line_number}`;
  }
  return `Lines ${finding.line_number}-${endLineNumber}`;
}

function formatFindingTitle(finding) {
  if (finding.category === finding.type) {
    return formatLabel(finding.category);
  }
  return `${formatLabel(finding.category)}: ${formatLabel(finding.type)}`;
}

function formatLabel(value) {
  return value.replaceAll("_", " ").replaceAll("/", " / ");
}

function escapeHtml(value) {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");
}

function escapeAttribute(value) {
  return escapeHtml(value).replaceAll('"', "&quot;");
}
