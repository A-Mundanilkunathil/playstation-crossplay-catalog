const state = { games: [], search: "", genre: "", view: "", strict: false };

const $search = document.getElementById("search");
const $genre = document.getElementById("genre");
const $view = document.getElementById("view");
const $toggleLabels = document.getElementById("toggle-labels");
const $strict = document.getElementById("toggle-strict");
const $count = document.getElementById("count");

async function init() {
  try {
    const resp = await fetch("games.json", { cache: "no-cache" });
    state.games = await resp.json();
  } catch (e) {
    document.body.insertAdjacentHTML(
      "beforeend",
      `<p class="subtle" style="padding:2rem">Couldn't load games.json — run <code>make refresh</code> first.</p>`
    );
    return;
  }
  populateGenres();
  populateViews();
  render();
}

function populateGenres() {
  const all = new Set();
  for (const g of state.games) for (const x of g.genres || []) all.add(x);
  for (const name of [...all].sort()) {
    const opt = document.createElement("option");
    opt.value = name;
    opt.textContent = name;
    $genre.appendChild(opt);
  }
}

function populateViews() {
  // Fixed order that matches the user-facing taxonomy (FPS / TPS / Top-Down /
  // Side-Scroller / Fixed Camera / VR), only showing options present in data.
  const ORDER = [
    "First-Person",
    "Third-Person",
    "Top-Down/Isometric",
    "Side-Scroller/2D",
    "Fixed Camera",
    "VR",
  ];
  const present = new Set();
  for (const g of state.games) for (const v of g.view_types || []) present.add(v);
  for (const name of ORDER) {
    if (!present.has(name)) continue;
    const opt = document.createElement("option");
    opt.value = name;
    opt.textContent = name;
    $view.appendChild(opt);
  }
}

function passesFilters(g) {
  if (state.strict && g.confidence !== "high") return false;
  if (state.search && !g.title.toLowerCase().includes(state.search)) return false;
  if (state.genre && !(g.genres || []).includes(state.genre)) return false;
  if (state.view && !(g.view_types || []).includes(state.view)) return false;
  return true;
}

function matchesSection(g, section) {
  const extraOnly = section.dataset.extraOnly === "true";
  if (extraOnly && !g.in_extra) return false;
  const required = section.dataset.required.split(",");
  const cp = new Set(g.crossplay_platforms || []);
  return required.every(p => cp.has(p));
}

function card(g) {
  const el = document.createElement("a");
  el.className = "card";
  el.href = `https://www.google.com/search?tbm=isch&q=${encodeURIComponent(g.title + " gameplay")}`;
  el.target = "_blank";
  el.rel = "noopener noreferrer";
  const cover = document.createElement("div");
  cover.className = "cover";
  if (g.background_image) cover.style.backgroundImage = `url("${g.background_image}")`;
  el.appendChild(cover);

  if (g.in_extra) {
    const flag = document.createElement("span");
    flag.className = "extra-flag";
    flag.textContent = "PS+ Extra";
    el.appendChild(flag);
  }

  const body = document.createElement("div");
  body.className = "body";

  const title = document.createElement("div");
  title.className = "title";
  title.textContent = g.title;
  body.appendChild(title);

  if (g.release_year) {
    const yr = document.createElement("div");
    yr.className = "year";
    yr.textContent = g.release_year;
    body.appendChild(yr);
  }

  if (g.confidence === "medium") {
    const hint = document.createElement("div");
    hint.className = "hint";
    hint.title = `Inferred from: ${(g.sources || []).join(", ")}`;
    hint.textContent = "· likely crossplay";
    body.appendChild(hint);
  }

  const labels = document.createElement("div");
  labels.className = "labels";
  if (g.players) labels.appendChild(badge("players", `${g.players} players`));
  if (g.online_coop) labels.appendChild(badge("online", "Online co-op"));
  if (g.splitscreen) labels.appendChild(badge("splitscr", "Splitscreen"));
  for (const p of g.crossplay_platforms || []) labels.appendChild(badge("plat", p));
  for (const v of g.view_types || []) labels.appendChild(badge("view", v));
  for (const genre of (g.genres || []).slice(0, 5)) labels.appendChild(badge("genre", genre));
  body.appendChild(labels);

  el.appendChild(body);
  return el;
}

function badge(variant, text) {
  const b = document.createElement("span");
  b.className = `badge ${variant}`;
  b.textContent = text;
  return b;
}

function render() {
  const sections = document.querySelectorAll(".combo");
  let totalVisible = 0;
  for (const sec of sections) {
    const visible = state.games.filter(
      g => passesFilters(g) && matchesSection(g, sec)
    );
    const grid = sec.querySelector(".grid");
    const empty = sec.querySelector(".empty");
    const count = sec.querySelector(".count");
    grid.innerHTML = "";
    for (const g of visible) grid.appendChild(card(g));
    count.textContent = `(${visible.length})`;
    empty.hidden = visible.length > 0;
    totalVisible += visible.length;
  }
  $count.textContent = `${state.games.length} total crossplay titles in catalog`;
}

$search.addEventListener("input", e => {
  state.search = e.target.value.trim().toLowerCase();
  render();
});
$genre.addEventListener("change", e => {
  state.genre = e.target.value;
  render();
});
$view.addEventListener("change", e => {
  state.view = e.target.value;
  render();
});
$toggleLabels.addEventListener("change", e => {
  document.body.classList.toggle("labels-on", e.target.checked);
});
$strict.addEventListener("change", e => {
  state.strict = e.target.checked;
  render();
});

init();
