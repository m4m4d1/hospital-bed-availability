// Hospital Bed & Puskesmas Availability dashboard. Talks to the API; when there is no
// API (the GitHub Pages demo) it reads the same responses from data/demo.json.
(function () {
  "use strict";
  var root = document.documentElement;
  var demo = null;
  var selected = null;
  var chart = null;
  var regionChart = null;

  // ---- language ---------------------------------------------------------
  try {
    var saved = localStorage.getItem("lang") || ((navigator.language || "").slice(0, 2) === "id" ? "id" : "en");
    root.dataset.lang = saved;
  } catch (e) {}
  document.querySelector(".lang").addEventListener("click", function () {
    root.dataset.lang = root.dataset.lang === "en" ? "id" : "en";
    try { localStorage.setItem("lang", root.dataset.lang); } catch (e) {}
  });

  function esc(s) { var d = document.createElement("div"); d.textContent = s == null ? "" : String(s); return d.innerHTML; }
  function t(en, id) { return '<span class="t-en">' + esc(en) + '</span><span class="t-id">' + esc(id) + "</span>"; }
  function fmt(v, digits) { return v == null ? "–" : Number(v).toFixed(digits == null ? 1 : digits); }
  function pct(v) { return v == null ? "–" : Number(v).toFixed(1) + "%"; }

  // ---- data -------------------------------------------------------------
  async function api(path) {
    if (!demo) {
      try {
        var res = await fetch("api/" + path);
        if (res.ok && (res.headers.get("content-type") || "").indexOf("json") !== -1) return res.json();
      } catch (e) {}
      var file = await fetch("data/demo.json");
      demo = await file.json();
      document.body.classList.add("is-demo");
    }
    return demo.api[path];
  }

  var WARDS = {
    icu: ["ICU", "ICU"], isolation: ["Isolation", "Isolasi"], general: ["General ward", "Rawat inap umum"],
    maternity: ["Maternity", "Kebidanan"], nicu: ["NICU", "NICU"], emergency: ["Emergency (ER)", "IGD"]
  };
  var TYPES = {
    A: ["Hospital, class A", "RS kelas A"], B: ["Hospital, class B", "RS kelas B"],
    C: ["Hospital, class C", "RS kelas C"], puskesmas: ["Puskesmas (inpatient)", "Puskesmas rawat inap"]
  };
  var WARD_COLORS = { icu: "#c8102e", isolation: "#7c5cff", general: "#2f7de1", maternity: "#d98a00", nicu: "#0e9aa7", emergency: "#4c9a2a" };
  var REGION_COLORS = ["#c2416b", "#2f7de1", "#1f9d6b", "#d98a00", "#7c5cff", "#0e9aa7", "#e46b1f", "#6b7a2a", "#8a4fbf"];

  // ---- rendering --------------------------------------------------------
  function statusTag(v) {
    return v ? '<span class="status s-' + v.status + '">' + t(v.status_label.en, v.status_label.id) + "</span>" : "–";
  }
  function bar(v) {
    return '<span class="bar s-' + v.status + '"><i style="width:' + Math.min(100, v.bor) + '%"></i></span>';
  }
  function ward(f, key) { return (f.wards || []).find(function (w) { return w.ward === key; }); }
  function css(name) { return getComputedStyle(root).getPropertyValue(name).trim(); }
  function timeLabel(ts) {
    return new Date(ts).toLocaleString(root.dataset.lang === "id" ? "id-ID" : "en-GB", { weekday: "short", hour: "2-digit", minute: "2-digit" });
  }

  function renderKpis(s) {
    var items = [
      ["var(--accent)", s.reporting + "/" + s.facilities, "Facilities reporting", "Fasilitas melapor"],
      ["var(--ideal)", pct(s.bor), "Overall occupancy (BOR)", "Keterisian total (BOR)"],
      ["var(--low)", s.free, "Free beds", "Tempat tidur kosong"],
      ["var(--full)", s.free_by_ward.icu + "/" + s.capacity_by_ward.icu, "Free ICU beds", "ICU kosong"],
      ["var(--high)", s.full_wards, "Wards full now", "Ruang penuh saat ini"],
      ["var(--muted)", s.alerts_24h, "Alerts (24 h)", "Peringatan (24 jam)"]
    ];
    document.getElementById("kpis").innerHTML = items.map(function (k) {
      return '<div class="kpi" style="--c:' + k[0] + '"><b>' + esc(k[1]) + "</b><span>" + t(k[2], k[3]) + "</span></div>";
    }).join("");
  }

  function renderTable(facilities) {
    var rows = facilities.slice().sort(function (a, b) {
      return (b.total ? b.total.bor : -1) - (a.total ? a.total.bor : -1);
    });
    document.getElementById("facility-rows").innerHTML = rows.map(function (f) {
      var tot = f.total || {};
      var icu = ward(f, "icu");
      var type = TYPES[f.type] || [f.type, f.type];
      return '<tr data-id="' + esc(f.id) + '"' + (f.id === selected ? ' class="selected"' : "") + ">" +
        "<td><b>" + esc(f.name) + "</b><small>" + t(type[0], type[1]) + " · " + esc(f.city) + "</small></td>" +
        "<td>" + esc(f.province) + "</td><td>" + statusTag(f.total) + "</td>" +
        '<td class="num"><b>' + pct(tot.bor) + "</b></td>" +
        '<td class="num">' + (tot.free == null ? "–" : tot.free) + "</td>" +
        "<td" + (icu && icu.free === 0 ? ' class="num bad"' : ' class="num"') + ">" + (icu ? icu.free + "/" + icu.capacity : "–") + "</td></tr>";
    }).join("");
  }

  async function renderDetail(f) {
    var type = TYPES[f.type] || [f.type, f.type];
    document.getElementById("d-name").textContent = f.name;
    document.getElementById("d-where").innerHTML = esc(f.city) + " · " + esc(f.province) + " · " + t(type[0], type[1]);
    document.getElementById("d-status").innerHTML = statusTag(f.total);
    document.getElementById("d-bor").textContent = f.total ? pct(f.total.bor) : "–";
    document.getElementById("d-wards").innerHTML = (f.wards || []).map(function (w) {
      var name = WARDS[w.ward] || [w.ward, w.ward];
      return '<div class="ward ' + w.status + '"><span>' + t(name[0], name[1]) + "</span>" +
        "<b>" + w.free + " <small>" + t("free of " + w.capacity, "kosong dari " + w.capacity) + "</small></b>" +
        bar(w) + "<small>" + pct(w.bor) + " · " + t(w.status_label.en, w.status_label.id) + "</small></div>";
    }).join("");

    var history = await api("facilities/" + f.id + "/history?hours=72") || [];
    var labels = history.map(function (h) { return timeLabel(h.timestamp); });
    var datasets = [{ label: "All wards", data: history.map(function (h) { return h.bor; }), borderColor: css("--accent"), borderWidth: 3 }];
    Object.keys(f.beds).forEach(function (w) {
      datasets.push({ label: WARDS[w] ? WARDS[w][root.dataset.lang === "id" ? 1 : 0] : w, borderColor: WARD_COLORS[w], borderWidth: 1.5,
        data: history.map(function (h) { return h.wards[w] == null ? null : h.wards[w]; }) });
    });
    datasets.push({ label: "85%", data: history.map(function () { return 85; }), borderColor: css("--high"), borderDash: [6, 4], borderWidth: 1 });
    datasets.forEach(function (d) { d.pointRadius = 0; d.tension = 0.3; });
    if (chart) chart.destroy();
    chart = new window.Chart(document.getElementById("d-chart"), {
      type: "line",
      data: { labels: labels, datasets: datasets },
      options: chartOptions()
    });
  }

  function chartOptions() {
    return {
      responsive: true, maintainAspectRatio: false, animation: false,
      interaction: { mode: "index", intersect: false },
      plugins: { legend: { labels: { boxWidth: 12, color: css("--muted") } } },
      scales: {
        x: { ticks: { maxTicksLimit: 6, color: css("--muted") }, grid: { display: false } },
        y: { min: 0, suggestedMax: 100, title: { display: true, text: "BOR %" }, ticks: { color: css("--muted") }, grid: { color: css("--line") } }
      }
    };
  }

  function renderRegions(regions) {
    document.getElementById("region-rows").innerHTML = regions.slice().sort(function (a, b) { return b.bor - a.bor; }).map(function (r) {
      var change = r.change_24h > 0 ? '<td class="num up">+' + fmt(r.change_24h) + "</td>" :
        '<td class="num' + (r.change_24h < 0 ? " down" : "") + '">' + fmt(r.change_24h) + "</td>";
      return "<tr><td><b>" + esc(r.province) + "</b><small>" + r.facilities + " " + t(r.facilities === 1 ? "facility" : "facilities", "fasilitas") + "</small></td>" +
        '<td class="num"><b>' + pct(r.bor) + "</b></td><td>" + bar(r) + "</td>" +
        '<td class="num">' + r.free + "</td>" + change + "</tr>";
    }).join("");

    var labels = (regions[0] ? regions[0].trend : []).map(function (p) { return timeLabel(p.timestamp); });
    var datasets = regions.map(function (r, i) {
      return { label: r.province, data: r.trend.map(function (p) { return p.bor; }), borderColor: REGION_COLORS[i % REGION_COLORS.length],
        borderWidth: 2, pointRadius: 0, tension: 0.3 };
    });
    var options = chartOptions();
    options.scales.y.min = undefined;
    options.scales.y.suggestedMax = undefined;
    if (regionChart) regionChart.destroy();
    regionChart = new window.Chart(document.getElementById("r-chart"), { type: "line", data: { labels: labels, datasets: datasets }, options: options });
  }

  // ---- wiring -----------------------------------------------------------
  var facilitiesCache = [];

  function select(id) {
    selected = id;
    var f = facilitiesCache.find(function (x) { return x.id === id; });
    if (!f) return;
    document.querySelectorAll("#facility-rows tr").forEach(function (tr) { tr.classList.toggle("selected", tr.dataset.id === id); });
    renderDetail(f);
    document.dispatchEvent(new CustomEvent("hb:selected", { detail: f }));
  }

  document.getElementById("facility-rows").addEventListener("click", function (e) {
    var tr = e.target.closest("tr");
    if (tr) select(tr.dataset.id);
  });
  document.addEventListener("hb:select", function (e) { select(e.detail); });

  async function refresh() {
    var results = await Promise.all([api("facilities"), api("summary"), api("regions?hours=72")]);
    facilitiesCache = results[0];
    renderKpis(results[1]);
    renderTable(facilitiesCache);
    renderRegions(results[2] || []);
    var latest = facilitiesCache.map(function (f) { return f.total && f.total.timestamp; }).filter(Boolean).sort().pop();
    document.getElementById("updated").textContent = latest ? new Date(latest).toLocaleString() : "–";
    if (!selected && results[1].busiest) selected = results[1].busiest.facility_id;
    select(selected);
    document.dispatchEvent(new CustomEvent("hb:data", { detail: { facilities: facilitiesCache, api: api } }));
  }

  refresh();
  setInterval(function () { if (!demo) refresh(); }, 60000);
})();
