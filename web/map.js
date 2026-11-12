// Facility map, nearest free bed finder and alerts panel. Listens to the dashboard's events from app.js.
(function () {
  "use strict";
  var COLORS = { low: "--low", ideal: "--ideal", high: "--high", full: "--full" };
  var LABELS = {
    low: ["Below ideal (<60%)", "Di bawah ideal (<60%)"], ideal: ["Ideal (60-85%)", "Ideal (60-85%)"],
    high: ["High (>85%)", "Tinggi (>85%)"], full: ["Full", "Penuh"]
  };
  var WARDS = {
    icu: ["ICU", "ICU"], isolation: ["Isolation", "Isolasi"], general: ["General ward", "Rawat inap umum"],
    maternity: ["Maternity", "Kebidanan"], nicu: ["NICU", "NICU"], emergency: ["Emergency (ER)", "IGD"]
  };
  var RADIUS = { A: 11, B: 9, C: 8, puskesmas: 6 };
  var map = null;
  var markers = {};
  var origin = null;
  var api = null;
  var names = {};
  var custom = null;

  function esc(s) { var d = document.createElement("div"); d.textContent = s == null ? "" : String(s); return d.innerHTML; }
  function t(en, id) { return '<span class="t-en">' + esc(en) + '</span><span class="t-id">' + esc(id) + "</span>"; }
  function color(status) { return getComputedStyle(document.documentElement).getPropertyValue(COLORS[status] || "--muted").trim(); }
  function isDemo() { return document.body.classList.contains("is-demo"); }
  function wardName(w) { var n = WARDS[w] || [w, w]; return t(n[0], n[1]); }
  function when(ts) { return new Date(ts).toLocaleString([], { weekday: "short", hour: "2-digit", minute: "2-digit" }); }
  function select(id) { document.dispatchEvent(new CustomEvent("hb:select", { detail: id })); }

  function drawMap(facilities) {
    if (!window.L) return;
    if (!map) {
      map = window.L.map("map", { scrollWheelZoom: false }).setView([-3, 112], 5);
      window.L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        maxZoom: 15, attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
      }).addTo(map);
      map.fitBounds(facilities.map(function (f) { return [f.lat, f.lon]; }), { padding: [24, 24] });
      document.getElementById("legend").innerHTML = Object.keys(LABELS).map(function (k) {
        return '<span class="status s-' + k + '">' + t(LABELS[k][0], LABELS[k][1]) + "</span>";
      }).join("");
      map.on("click", function (e) {
        if (isDemo()) return;
        custom = { lat: +e.latlng.lat.toFixed(4), lon: +e.latlng.lng.toFixed(4) };
        var sel = document.getElementById("f-from");
        var opt = sel.querySelector('option[value="custom"]');
        if (!opt) { opt = document.createElement("option"); opt.value = "custom"; sel.appendChild(opt); }
        opt.textContent = "Map point / Titik peta: " + custom.lat + ", " + custom.lon;
        sel.value = "custom";
        find();
      });
    }
    facilities.forEach(function (f) {
      var tot = f.total;
      var c = color(tot ? tot.status : null);
      var icu = (f.wards || []).find(function (w) { return w.ward === "icu"; });
      var popup = "<b>" + esc(f.name) + "</b><br>" + esc(f.city) + " · " + esc(f.province) +
        (tot ? "<br>BOR <b>" + tot.bor.toFixed(1) + "%</b> · " + t(tot.status_label.en, tot.status_label.id) +
          "<br>" + t("Free beds: ", "Tempat tidur kosong: ") + "<b>" + tot.free + "</b>" +
          (icu ? " · ICU " + icu.free + "/" + icu.capacity : "") : "");
      if (markers[f.id]) {
        markers[f.id].setStyle({ color: c, fillColor: c }).setPopupContent(popup);
      } else {
        markers[f.id] = window.L.circleMarker([f.lat, f.lon], { radius: RADIUS[f.type] || 8, color: c, fillColor: c, fillOpacity: 0.75, weight: 2 })
          .bindPopup(popup).addTo(map)
          .on("click", function () { select(f.id); });
      }
    });
  }

  // ---- nearest free bed -------------------------------------------------
  async function setupFinder() {
    var meta = await api("meta") || {};
    var wardSel = document.getElementById("f-ward");
    wardSel.innerHTML = Object.keys(WARDS).map(function (w) {
      var n = WARDS[w];
      return '<option value="' + w + '">' + esc(n[0] === n[1] ? n[0] : n[0] + " / " + n[1]) + "</option>";
    }).join("");
    var fromSel = document.getElementById("f-from");
    fromSel.innerHTML = (meta.presets || []).map(function (p) {
      return '<option value="' + esc(p.id) + '" data-lat="' + p.lat + '" data-lon="' + p.lon + '">' + esc(p.name) + "</option>";
    }).join("");
    wardSel.addEventListener("change", find);
    fromSel.addEventListener("change", find);
    find();
  }

  async function find() {
    var ward = document.getElementById("f-ward").value;
    var opt = document.getElementById("f-from").selectedOptions[0];
    if (!ward || !opt) return;
    var point = opt.value === "custom" ? custom : { lat: Number(opt.dataset.lat), lon: Number(opt.dataset.lon) };
    var body = await api("nearest?lat=" + point.lat + "&lon=" + point.lon + "&ward=" + ward);
    var list = document.getElementById("results");
    if (map && window.L) {
      if (origin) origin.remove();
      origin = window.L.circleMarker([point.lat, point.lon], { radius: 6, color: "#201419", fillColor: "#ffffff", fillOpacity: 1, weight: 3 }).addTo(map);
    }
    if (!body) {
      list.innerHTML = '<li class="empty">' + t("Not available in the demo: pick a listed place.", "Tidak tersedia di demo: pilih tempat dari daftar.") + "</li>";
      return;
    }
    if (!body.results.length) {
      list.innerHTML = '<li class="empty">' + t("No facility has a free bed in this ward right now.", "Tidak ada fasilitas dengan tempat tidur kosong di ruang ini saat ini.") + "</li>";
      return;
    }
    list.innerHTML = body.results.map(function (r) {
      return '<li data-id="' + esc(r.facility_id) + '"><span><b>' + esc(r.name) + "</b><br><small>" + esc(r.city) + " · " +
        r.free + " " + t("free of " + r.capacity, "kosong dari " + r.capacity) + " · " + wardName(r.ward) + "</small></span>" +
        '<span class="dist">' + r.distance_km.toFixed(1) + " km</span></li>";
    }).join("");
  }

  document.getElementById("results").addEventListener("click", function (e) {
    var li = e.target.closest("li[data-id]");
    if (li) select(li.dataset.id);
  });

  // ---- alerts -----------------------------------------------------------
  function drawAlerts(alerts) {
    document.getElementById("alert-count").textContent = alerts.length;
    var list = document.getElementById("alerts");
    if (!alerts.length) {
      list.innerHTML = '<li class="empty">' + t("No ward above 85% or full in the last 24 hours.", "Tidak ada ruang di atas 85% atau penuh dalam 24 jam terakhir.") + "</li>";
      return;
    }
    list.innerHTML = alerts.slice(0, 80).map(function (a) {
      var where = a.ward ? wardName(a.ward) : t("All wards", "Semua ruang");
      var status = a.level === "full" ? "full" : "high";
      return '<li data-id="' + esc(a.facility_id) + '"><span class="when">' + esc(when(a.start)) + " – " + esc(when(a.end)) +
        (a.ongoing ? ' · <span class="live">' + t("ongoing", "berlangsung") + "</span>" : "") + "</span>" +
        "<span><b>" + esc(names[a.facility_id] || a.facility_id) + "</b> · " + where + ' <span class="status s-' + status + '">' +
        t(a.level_label.en, a.level_label.id) + "</span></span>" +
        '<span class="what">' + t("Peak BOR ", "BOR tertinggi ") + a.peak_bor.toFixed(1) + "% · " +
        t("fewest free beds: ", "tempat tidur kosong paling sedikit: ") + a.min_free + "/" + a.capacity + "</span></li>";
    }).join("");
  }

  document.getElementById("alerts").addEventListener("click", function (e) {
    var li = e.target.closest("li[data-id]");
    if (li) select(li.dataset.id);
  });

  document.addEventListener("hb:data", async function (e) {
    var first = !api;
    api = e.detail.api;
    e.detail.facilities.forEach(function (f) { names[f.id] = f.name; });
    drawMap(e.detail.facilities);
    if (first) await setupFinder(); else find();
    drawAlerts(await api("alerts?hours=24&level=high") || []);
  });

  document.addEventListener("hb:selected", function (e) {
    var m = markers[e.detail.id];
    if (m && map) { map.panTo(m.getLatLng()); m.openPopup(); }
  });
})();
