// PrepCast static demo — plain JS, no framework, no build step, no external requests.
// All numbers are read from precomputed web/data/*.json (written by `prepcast export`).
// Nothing is computed from a model in the browser.

(function () {
  "use strict";

  const state = { scenarios: null, dishes: null, prepList: null, savings: null, meta: null };
  const sortState = { key: "name", dir: 1 };

  // ---------- data loading ----------
  async function loadJSON(path) {
    const res = await fetch(path);
    if (!res.ok) throw new Error(`Failed to load ${path}`);
    return res.json();
  }

  async function init() {
    applyStoredTheme();
    wireTabs();
    wireThemeToggle();
    wirePrintButton();

    const [scenarios, dishes, prepList, savings, meta] = await Promise.all([
      loadJSON("data/scenarios.json"),
      loadJSON("data/dishes.json"),
      loadJSON("data/prep_list.json"),
      loadJSON("data/savings.json"),
      loadJSON("data/meta.json"),
    ]);
    state.scenarios = scenarios;
    state.dishes = dishes;
    state.prepList = prepList;
    state.savings = savings;
    state.meta = meta;

    renderForecast("normal");
    wireScenarioToggle();

    populateCategoryFilter(dishes);
    renderDishesTable();
    wireTableControls();

    renderPrepList(prepList);

    renderSavings(savings);
    wireBufferSlider(savings);
  }

  // ---------- theme ----------
  function applyStoredTheme() {
    const saved = localStorage.getItem("prepcast-theme");
    if (saved) document.documentElement.setAttribute("data-theme", saved);
  }

  function wireThemeToggle() {
    document.getElementById("theme-toggle").addEventListener("click", () => {
      const root = document.documentElement;
      const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
      const current = root.getAttribute("data-theme") || (prefersDark ? "dark" : "light");
      const next = current === "dark" ? "light" : "dark";
      root.setAttribute("data-theme", next);
      localStorage.setItem("prepcast-theme", next);
    });
  }

  // ---------- tabs (desktop top bar + mobile bottom bar share data-tab) ----------
  function wireTabs() {
    const buttons = document.querySelectorAll(".tab-btn");
    buttons.forEach((btn) => {
      btn.addEventListener("click", () => showTab(btn.dataset.tab));
    });
  }

  function showTab(name) {
    document.querySelectorAll(".panel").forEach((p) => {
      p.classList.toggle("hidden", p.id !== `panel-${name}`);
    });
    document.querySelectorAll(".tab-btn").forEach((btn) => {
      btn.setAttribute("aria-selected", String(btn.dataset.tab === name));
    });
  }

  // ---------- 1. Forecast chart ----------
  function wireScenarioToggle() {
    document.querySelectorAll(".scenario-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        document.querySelectorAll(".scenario-btn").forEach((b) => b.classList.remove("active"));
        btn.classList.add("active");
        renderForecast(btn.dataset.scenario);
      });
    });
  }

  function renderForecast(key) {
    const s = state.scenarios[key];
    const svg = document.getElementById("forecast-chart");
    const W = 760, H = 360, padL = 50, padR = 20, padT = 20, padB = 40;
    const plotW = W - padL - padR, plotH = H - padT - padB;

    const allVals = [...s.forecast_p90, ...s.actual, ...s.last_week_baseline, ...s.forecast_p10];
    const yMax = Math.max(...allVals) * 1.08;
    const yMin = Math.min(0, Math.min(...allVals) * 0.95);
    const n = s.dates.length;

    const x = (i) => padL + (plotW * i) / (n - 1);
    const y = (v) => padT + plotH - (plotH * (v - yMin)) / (yMax - yMin);

    const pathOf = (arr) => arr.map((v, i) => `${i === 0 ? "M" : "L"}${x(i).toFixed(1)},${y(v).toFixed(1)}`).join(" ");
    const bandPath = `${s.forecast_p90.map((v, i) => `${i === 0 ? "M" : "L"}${x(i).toFixed(1)},${y(v).toFixed(1)}`).join(" ")} ` +
      `${[...s.forecast_p10].reverse().map((v, i) => `L${x(n - 1 - i).toFixed(1)},${y(v).toFixed(1)}`).join(" ")} Z`;

    let gridLines = "";
    const nTicks = 5;
    for (let t = 0; t <= nTicks; t++) {
      const v = yMin + ((yMax - yMin) * t) / nTicks;
      const gy = y(v);
      gridLines += `<line x1="${padL}" y1="${gy.toFixed(1)}" x2="${W - padR}" y2="${gy.toFixed(1)}" stroke="var(--border)" stroke-width="1"/>`;
      gridLines += `<text x="${padL - 8}" y="${(gy + 4).toFixed(1)}" font-size="11" text-anchor="end" fill="var(--text-muted)">${Math.round(v)}</text>`;
    }

    let xLabels = "";
    s.dates.forEach((d, i) => {
      const label = new Date(d + "T00:00:00").toLocaleDateString(undefined, { weekday: "short" });
      xLabels += `<text x="${x(i).toFixed(1)}" y="${H - padB + 18}" font-size="11" text-anchor="middle" fill="var(--text-muted)">${label}</text>`;
    });

    const dots = (arr, cls) => arr.map((v, i) => `<circle cx="${x(i).toFixed(1)}" cy="${y(v).toFixed(1)}" r="3" class="${cls}"/>`).join("");

    svg.innerHTML = `
      <g>${gridLines}</g>
      <path d="${bandPath}" fill="var(--band)" opacity="0.55" stroke="none"/>
      <path d="${pathOf(s.last_week_baseline)}" fill="none" stroke="var(--baseline-line)" stroke-width="1.5" stroke-dasharray="5,4"/>
      <path d="${pathOf(s.forecast_p50)}" fill="none" stroke="var(--forecast-line)" stroke-width="2.5"/>
      <path d="${pathOf(s.actual)}" fill="none" stroke="var(--actual-line)" stroke-width="2.5"/>
      ${dots(s.forecast_p50, "")}
      ${dots(s.actual, "")}
      <g fill="var(--forecast-line)">${dots(s.forecast_p50, "")}</g>
      <g fill="var(--actual-line)">${dots(s.actual, "")}</g>
      ${xLabels}
    `.replace(/class=""/g, "");

    document.getElementById("scenario-caption").textContent =
      `Origin ${s.origin} → forecast for ${s.dates[0]} through ${s.dates[s.dates.length - 1]}. ` +
      `This is a real held-out week from the backtest, not a hypothetical.`;
  }

  // ---------- 2. Dishes table ----------
  function populateCategoryFilter(dishes) {
    const select = document.getElementById("category-filter");
    const cats = [...new Set(dishes.map((d) => d.category))].sort();
    cats.forEach((c) => {
      const opt = document.createElement("option");
      opt.value = c;
      opt.textContent = c.charAt(0).toUpperCase() + c.slice(1);
      select.appendChild(opt);
    });
  }

  function wireTableControls() {
    document.getElementById("category-filter").addEventListener("change", renderDishesTable);
    document.querySelectorAll("#dishes-table th[data-key]").forEach((th) => {
      th.addEventListener("click", () => {
        const key = th.dataset.key;
        if (sortState.key === key) sortState.dir *= -1;
        else { sortState.key = key; sortState.dir = 1; }
        renderDishesTable();
      });
    });
    document.getElementById("dishes-date").textContent = state.meta.tomorrow_date;
  }

  function renderDishesTable() {
    const filter = document.getElementById("category-filter").value;
    let rows = state.dishes.filter((d) => filter === "all" || d.category === filter);
    rows = rows.slice().sort((a, b) => {
      let av = sortState.key === "range" ? a.forecast_p90 - a.forecast_p10 : a[sortState.key];
      let bv = sortState.key === "range" ? b.forecast_p90 - b.forecast_p10 : b[sortState.key];
      if (typeof av === "string") return av.localeCompare(bv) * sortState.dir;
      return (av - bv) * sortState.dir;
    });
    const tbody = document.querySelector("#dishes-table tbody");
    tbody.innerHTML = rows.map((d) => {
      const diffCls = d.diff_vs_last_week > 0 ? "pos" : d.diff_vs_last_week < 0 ? "neg" : "";
      const sign = d.diff_vs_last_week > 0 ? "+" : "";
      return `<tr>
        <td>${d.name}</td>
        <td>${d.category}</td>
        <td class="num">${d.forecast_p50}</td>
        <td class="num">${d.forecast_p10}–${d.forecast_p90}</td>
        <td class="num"><strong>${d.recommended_prep}</strong></td>
        <td class="num">${d.last_week_method}</td>
        <td class="num ${diffCls}">${sign}${d.diff_vs_last_week}</td>
      </tr>`;
    }).join("");
  }

  // ---------- 3. Prep list ----------
  function renderPrepList(prepList) {
    document.getElementById("prep-sheet-date").textContent = `For: ${prepList.date}`;
    const byStation = {};
    prepList.items.forEach((item) => {
      (byStation[item.station] = byStation[item.station] || []).push(item);
    });
    const container = document.getElementById("prep-stations");
    container.innerHTML = Object.keys(byStation).sort().map((station) => {
      const items = byStation[station];
      const rows = items.map((it) => `<tr>
          <td>${it.name}</td>
          <td class="num">${it.carryover_portions}</td>
          <td class="num"><strong>${it.prep_portions}</strong></td>
          <td class="num">${it.prep_kg.toFixed(2)} kg</td>
          <td class="tick-col"><span class="tick-box"></span></td>
        </tr>`).join("");
      return `<div class="station-block">
        <h3>${station}</h3>
        <table>
          <thead><tr><th>Dish</th><th class="num">Carryover</th><th class="num">Prep today</th><th class="num">kg</th><th class="tick-col">✓</th></tr></thead>
          <tbody>${rows}</tbody>
        </table>
      </div>`;
    }).join("");
  }

  function wirePrintButton() {
    document.getElementById("print-btn").addEventListener("click", () => window.print());
  }

  // ---------- 4. Savings ----------
  function fmtSAR(v) {
    return `${Math.round(v).toLocaleString()} SAR`;
  }

  function renderSavings(savings) {
    const h = savings.headline;
    const kpiRow = document.getElementById("kpi-row");
    kpiRow.innerHTML = `
      <div class="kpi-card"><div class="kpi-value">${fmtSAR(h.net_cost_sar_saved)}/yr</div><div class="kpi-label">Net cost saved vs usual method</div></div>
      <div class="kpi-card"><div class="kpi-value">${fmtSAR(h.waste_sar_saved)}</div><div class="kpi-label">Waste saved (${h.waste_kg_saved.toLocaleString()} kg less binned)</div></div>
      <div class="kpi-card"><div class="kpi-value">${h.stockout_portions_avoided.toLocaleString()}</div><div class="kpi-label">Stockout portions avoided / yr</div></div>
    `;
  }

  function wireBufferSlider(savings) {
    const slider = document.getElementById("buffer-slider");
    const readout = document.getElementById("slider-readout");
    const chart = document.getElementById("slider-chart");
    const grid = savings.buffer_slider;
    const levels = Object.keys(grid).map((k) => parseInt(k.slice(1), 10)).sort((a, b) => a - b);

    function renderSliderChart(current) {
      const W = 760, H = 240, padL = 60, padR = 60, padT = 20, padB = 30;
      const plotW = W - padL - padR, plotH = H - padT - padB;
      const wasteVals = levels.map((p) => grid[`P${p}`].waste_sar);
      const stockoutVals = levels.map((p) => grid[`P${p}`].lost_margin_sar);
      const maxV = Math.max(...wasteVals, ...stockoutVals) * 1.1;
      const x = (p) => padL + (plotW * (p - levels[0])) / (levels[levels.length - 1] - levels[0]);
      const y = (v) => padT + plotH - (plotH * v) / maxV;
      const pathOf = (vals) => levels.map((p, i) => `${i === 0 ? "M" : "L"}${x(p).toFixed(1)},${y(vals[i]).toFixed(1)}`).join(" ");
      const curX = x(current);
      chart.innerHTML = `
        <path d="${pathOf(wasteVals)}" fill="none" stroke="var(--bad)" stroke-width="2.5"/>
        <path d="${pathOf(stockoutVals)}" fill="none" stroke="var(--forecast-line)" stroke-width="2.5"/>
        <line x1="${curX.toFixed(1)}" y1="${padT}" x2="${curX.toFixed(1)}" y2="${H - padB}" stroke="var(--text-muted)" stroke-width="1.5" stroke-dasharray="4,3"/>
        <text x="${padL}" y="${H - 6}" font-size="11" fill="var(--text-muted)">P${levels[0]}</text>
        <text x="${W - padR}" y="${H - 6}" font-size="11" text-anchor="end" fill="var(--text-muted)">P${levels[levels.length - 1]}</text>
        <text x="${padL}" y="14" font-size="11" fill="var(--bad)">— waste SAR/yr</text>
        <text x="${padL + 150}" y="14" font-size="11" fill="var(--forecast-line)">— lost margin (stockout) SAR/yr</text>
      `;
    }

    function render() {
      const p = parseInt(slider.value, 10);
      const row = grid[`P${p}`];
      readout.innerHTML = `
        <span>Service level: <b>P${p}</b></span>
        <span>Waste: <b>${fmtSAR(row.waste_sar)}/yr</b> (${row.waste_kg.toLocaleString()} kg)</span>
        <span>Stockout portions: <b>${row.stockout_portions.toLocaleString()}/yr</b></span>
        <span>Net cost: <b>${fmtSAR(row.net_cost_sar)}/yr</b></span>
        <span>Fill rate: <b>${(row.fill_rate * 100).toFixed(1)}%</b></span>
      `;
      renderSliderChart(p);
    }
    slider.addEventListener("input", render);
    render();
  }

  init().catch((err) => {
    document.getElementById("app").innerHTML = `<p style="color:red">Failed to load demo data: ${err.message}</p>`;
    console.error(err);
  });
})();
