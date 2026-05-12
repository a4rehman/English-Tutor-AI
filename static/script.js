/**
 * English Vocabulary Extractor — Frontend Logic
 */

// ─── DOM Elements ───────────────────────────────
const $ = (sel) => document.querySelector(sel);
const youtubeUrl = $("#youtubeUrl");
const btnExtract = $("#btnExtract");
const btnClear = $("#btnClear");
const btnRetry = $("#btnRetry");
const btnSaveExcel = $("#btnSaveExcel");
const btnSaveEnglishUrdu = $("#btnSaveEnglishUrdu");
const btnDownloadCsv = $("#btnDownloadCsv");
const btnDownloadCsvEnUr = $("#btnDownloadCsvEnUr");
const chatForm = $("#chatForm");
const chatInput = $("#chatInput");
const chatMessages = $("#chatMessages");
const btnChatSend = $("#btnChatSend");
const searchInput = $("#searchInput");
const progressSection = $("#progressSection");
const errorSection = $("#errorSection");
const resultsSection = $("#resultsSection");
const inputSection = $("#inputSection");

let currentData = null; // Stores the latest vocabulary result

// ─── Background Particles ────────────────────────
(function initParticles() {
  const container = $("#bgParticles");
  for (let i = 0; i < 15; i++) {
    const p = document.createElement("div");
    p.className = "particle";
    const size = Math.random() * 200 + 60;
    p.style.cssText = `
      width:${size}px; height:${size}px;
      left:${Math.random() * 100}%; top:${Math.random() * 100}%;
      animation-delay:${Math.random() * 10}s;
      animation-duration:${15 + Math.random() * 20}s;
    `;
    container.appendChild(p);
  }
})();

// ─── URL Input Handling ──────────────────────────
btnClear.addEventListener("click", () => { youtubeUrl.value = ""; youtubeUrl.focus(); });

youtubeUrl.addEventListener("keydown", (e) => {
  if (e.key === "Enter") btnExtract.click();
});

// ─── Extract Vocabulary ──────────────────────────
btnExtract.addEventListener("click", async () => {
  const url = youtubeUrl.value.trim();
  if (!url) { youtubeUrl.focus(); return; }
  if (!isPlausibleHttpUrl(url)) {
    showError("Paste a full link from your browser (https://…). Search redirects like Bing are OK — we resolve them on the server.");
    return;
  }

  setLoading(true);
  showProgress();

  try {
    updateProgress(1, 33, "Fetching transcript from YouTube...");
    await sleep(400);
    updateProgress(2, 66, "AI is analyzing vocabulary...");

    const response = await fetch("/api/extract", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url }),
    });

    if (!response.ok) {
      const err = await response.json();
      throw new Error(err.detail || "Failed to extract vocabulary");
    }

    const data = await response.json();
    currentData = data;

    updateProgress(3, 100, "Done! Rendering results...");
    await sleep(500);

    renderResults(data);
    hideProgress();
    showResults();
    updateHeaderStats(data.vocab_count);
  } catch (err) {
    hideProgress();
    showError(err.message);
  } finally {
    setLoading(false);
  }
});

// ─── Retry ───────────────────────────────────────
btnRetry.addEventListener("click", () => {
  errorSection.classList.add("hidden");
  youtubeUrl.focus();
});

// ─── Save to Excel ───────────────────────
btnSaveExcel.addEventListener("click", async () => {
  if (!currentData) return;
  btnSaveExcel.disabled = true;
  btnSaveExcel.textContent = "Saving...";

  try {
    const response = await fetch("/api/save-to-excel", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ vocabulary_data: currentData }),
    });

    if (!response.ok) {
      const err = await response.json();
      throw new Error(err.detail || "Failed to save");
    }

    const result = await response.json();
    showToast(
      "✅",
      "Saved to Excel!",
      `${result.saved} words saved, ${result.skipped} duplicates skipped.`
    );
  } catch (err) {
    showToast("❌", "Save Failed", err.message);
  } finally {
    btnSaveExcel.disabled = false;
    btnSaveExcel.innerHTML = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/><polyline points="10 9 9 9 8 9"/></svg> Save to Excel`;
  }
});

btnSaveEnglishUrdu.addEventListener("click", async () => {
  if (!currentData) return;
  btnSaveEnglishUrdu.disabled = true;
  const label = btnSaveEnglishUrdu.innerHTML;
  btnSaveEnglishUrdu.textContent = "Saving...";

  try {
    const response = await fetch("/api/save-english-urdu", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ vocabulary_data: currentData }),
    });

    if (!response.ok) {
      const err = await response.json();
      throw new Error(err.detail || "Failed to save");
    }

    const result = await response.json();
    showToast(
      "✅",
      "English + Urdu saved",
      `${result.saved} rows → sheet “${result.sheet}” in ${result.file}. ${result.skipped} duplicates skipped.`
    );
  } catch (err) {
    showToast("❌", "Save Failed", err.message);
  } finally {
    btnSaveEnglishUrdu.disabled = false;
    btnSaveEnglishUrdu.innerHTML = label;
  }
});

// ─── Download CSV ────────────────────────────────
btnDownloadCsv.addEventListener("click", () => {
  if (!currentData || !currentData.vocabulary) return;
  const headers = ["Movie Title", "English Word", "Urdu Meaning", "English Meaning", "Example Sentence", "Level"];
  const rows = currentData.vocabulary.map((v) => [
    currentData.movie_title, v.word, v.urdu_meaning, v.english_meaning, v.example_sentence, v.level,
  ]);

  // BOM for UTF-8 (Urdu support)
  let csv = "\uFEFF" + headers.join(",") + "\n";
  rows.forEach((row) => {
    csv += row.map((cell) => `"${(cell || "").replace(/"/g, '""')}"`).join(",") + "\n";
  });

  const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = `vocabulary_${currentData.movie_title || "export"}.csv`;
  link.click();
});

btnDownloadCsvEnUr.addEventListener("click", () => {
  if (!currentData || !currentData.vocabulary) return;
  const headers = ["English Word", "Urdu Meaning"];
  const rows = currentData.vocabulary.map((v) => [v.word, v.urdu_meaning]);

  let csv = "\uFEFF" + headers.join(",") + "\n";
  rows.forEach((row) => {
    csv += row.map((cell) => `"${(cell || "").replace(/"/g, '""')}"`).join(",") + "\n";
  });

  const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  const safe = (currentData.movie_title || "export").replace(/[/\\?%*:|"<>]/g, "-");
  link.download = `english_urdu_${safe}.csv`;
  link.click();
});

// ─── Video chat (transcript-backed) ──────────────
chatForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const sid = currentData?.chat_session_id;
  const text = chatInput.value.trim();
  if (!sid || !text) {
    if (!sid) showToast("⚠️", "Chat unavailable", "Extract vocabulary again to start a new chat session.");
    return;
  }

  appendChatBubble("user", text);
  chatInput.value = "";
  btnChatSend.disabled = true;

  try {
    const response = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ chat_session_id: sid, message: text }),
    });

    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new Error(err.detail || "Chat request failed");
    }

    const { reply } = await response.json();
    appendChatBubble("assistant", reply || "(No reply)");
  } catch (err) {
    appendChatBubble("assistant", `Sorry — ${err.message}`);
  } finally {
    btnChatSend.disabled = false;
    chatInput.focus();
  }
});

// ─── Filters ─────────────────────────────────────
document.querySelectorAll(".filter-chip").forEach((chip) => {
  chip.addEventListener("click", () => {
    document.querySelectorAll(".filter-chip").forEach((c) => c.classList.remove("active"));
    chip.classList.add("active");
    applyFilters();
  });
});

searchInput.addEventListener("input", () => applyFilters());

function applyFilters() {
  const search = searchInput.value.toLowerCase().trim();
  const level = document.querySelector(".filter-chip.active")?.dataset.level || "all";
  const rows = document.querySelectorAll("#vocabBody tr");
  let visible = 0;

  rows.forEach((row) => {
    const word = row.dataset.word || "";
    const meaning = row.dataset.meaning || "";
    const rowLevel = row.dataset.level || "";
    const matchSearch = !search || word.includes(search) || meaning.includes(search);
    const matchLevel = level === "all" || rowLevel === level;
    const show = matchSearch && matchLevel;
    row.style.display = show ? "" : "none";
    if (show) visible++;
  });

  const empty = $("#emptyState");
  const table = $("#vocabTable");
  if (visible === 0) { empty.classList.remove("hidden"); table.style.display = "none"; }
  else { empty.classList.add("hidden"); table.style.display = ""; }
}

// ─── Render Results ──────────────────────────────
function renderResults(data) {
  $("#movieTitle").textContent = data.movie_title || "Unknown";
  $("#metaWordCount").textContent = `${data.vocab_count || 0} words extracted`;
  $("#metaLanguage").textContent = `Language: ${data.transcript_language || "en"}`;
  $("#metaTranscriptLen").textContent = `${data.transcript_length || 0} word transcript`;

  resetChatUI();

  const tbody = $("#vocabBody");
  tbody.innerHTML = "";

  (data.vocabulary || []).forEach((item, i) => {
    const levelClass = `level-${(item.level || "intermediate").toLowerCase()}`;
    const tr = document.createElement("tr");
    tr.dataset.word = (item.word || "").toLowerCase();
    tr.dataset.meaning = (item.english_meaning || "").toLowerCase();
    tr.dataset.level = item.level || "Intermediate";

    tr.innerHTML = `
      <td class="td-num">${i + 1}</td>
      <td class="td-word">${esc(item.word)}</td>
      <td class="td-urdu">${esc(item.urdu_meaning)}</td>
      <td class="td-meaning">${esc(item.english_meaning)}</td>
      <td class="td-example">${esc(item.example_sentence)}</td>
      <td><span class="level-badge ${levelClass}">${esc(item.level)}</span></td>
    `;
    tbody.appendChild(tr);
  });
}

function resetChatUI() {
  chatMessages.innerHTML = "";
  const ph = document.createElement("p");
  ph.className = "chat-placeholder";
  ph.textContent = "Ask what happened in the video, what a line means, or anything else covered in the transcript.";
  chatMessages.appendChild(ph);
  chatInput.value = "";
}

function appendChatBubble(role, text) {
  const ph = chatMessages.querySelector(".chat-placeholder");
  if (ph) ph.remove();

  const div = document.createElement("div");
  div.className = `chat-msg ${role === "user" ? "user" : "assistant"}`;
  div.textContent = text;
  chatMessages.appendChild(div);
  chatMessages.scrollTop = chatMessages.scrollHeight;
}

// ─── Helpers ─────────────────────────────────────
function isPlausibleHttpUrl(url) {
  try {
    const u = new URL(url.trim());
    return u.protocol === "http:" || u.protocol === "https:";
  } catch {
    return false;
  }
}

function setLoading(on) {
  btnExtract.classList.toggle("loading", on);
  btnExtract.disabled = on;
}

function showProgress() {
  progressSection.classList.remove("hidden");
  errorSection.classList.add("hidden");
  resultsSection.classList.add("hidden");
}

function hideProgress() { progressSection.classList.add("hidden"); }

function showResults() { resultsSection.classList.remove("hidden"); }

function showError(msg) {
  errorSection.classList.remove("hidden");
  resultsSection.classList.add("hidden");
  $("#errorMessage").textContent = msg;
}

function updateProgress(step, pct, msg) {
  for (let i = 1; i <= 3; i++) {
    const el = $(`#step${i}`);
    el.classList.remove("active", "done");
    if (i < step) el.classList.add("done");
    else if (i === step) el.classList.add("active");
  }
  $("#progressBar").style.width = pct + "%";
  $("#progressMessage").textContent = msg;
}

function updateHeaderStats(count) {
  $(".stat-number").textContent = count || 0;
}

function showToast(icon, title, message) {
  const toast = $("#toast");
  $("#toastIcon").textContent = icon;
  $("#toastTitle").textContent = title;
  $("#toastMessage").textContent = message;
  toast.classList.remove("hidden");
  setTimeout(() => toast.classList.add("hidden"), 5000);
}

$("#toastClose").addEventListener("click", () => $("#toast").classList.add("hidden"));

function esc(str) {
  if (!str) return "";
  const d = document.createElement("div");
  d.textContent = str;
  return d.innerHTML;
}

function sleep(ms) { return new Promise((r) => setTimeout(r, ms)); }
