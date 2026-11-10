/* ============================================================
   Dashboard v2 · mapa interactivo + panel de partido
   SVG propio, sin librerías. Lee geo.json (lo genera src/generar_geo.py).
   index.html lo inicia con RSMapa.init(ctx) una vez cargado data.json.
   ============================================================ */
window.RSMapa = (() => {
"use strict";

const NS = "http://www.w3.org/2000/svg";
const VB = 1000; // tamaño del sistema de coordenadas del mapa
const CORTO = { "General Arenales": "Gral. Arenales", "Leandro N. Alem": "L. N. Alem", "General Pinto": "Gral. Pinto" };
const TIPO = { cabecera: "Ciudad cabecera", localidad: "Localidad", paraje: "Paraje" };
const nf0 = new Intl.NumberFormat("es-AR", { maximumFractionDigits: 0 });
const $ = (s, el = document) => el.querySelector(s);
const $$ = (s, el = document) => [...el.querySelectorAll(s)];
const reduce = () => matchMedia("(prefers-reduced-motion: reduce)").matches;
const sv = (tag, attrs = {}, parent) => {
  const e = document.createElementNS(NS, tag);
  for (const k in attrs) e.setAttribute(k, attrs[k]);
  if (parent) parent.appendChild(e);
  return e;
};
const id2 = y => `${String(y).slice(2)}/${String(y + 1).slice(2)}`;
const idFull = y => `${y}/${String(y + 1).slice(2)}`;
const ICON_BACK = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="M19 12H5M11 6l-6 6 6 6"/></svg>';

let C, G = null, K = null, rows = [], byP = {};
const S = { sel: null, tab: "camp" };
const E = {};
let proj, vb = [0, 0, VB, VB], raf = 0, shapes = {};

/* ---------------- Inicio ---------------- */
function init(ctx) {
  C = ctx;
  E.map = $("#mzMap"); E.panel = $("#mzPanel");
  if (!E.map || !E.panel) return;
  K = C.focus ? C.lastCut(C.focus) : null;
  rows = K ? C.P.map(p => ({ p, e: K.partidos[p], h: C.PH[p], d: C.pct(K.partidos[p], C.PH[p]), r: K.partidos_rango ? K.partidos_rango[p] : null })) : [];
  byP = Object.fromEntries(rows.map(r => [r.p, r]));
  buildMapShell();
  buildPanel();
  fetch("geo.json", { cache: "no-cache" })
    .then(r => { if (!r.ok) throw new Error("geo.json " + r.status); return r.json(); })
    .then(g => { G = g; drawMap(); })
    .catch(err => {
      console.error(err);
      E.stage.innerHTML = '<div class="empty">No se pudo cargar el mapa. Los datos de cada partido están en la lista.</div>';
    });
  let rz, last = "";
  new ResizeObserver(() => {
    const k = E.stage.clientWidth + "x" + E.stage.clientHeight;
    if (!G || k === last) { last = k; return; }
    last = k; clearTimeout(rz); rz = setTimeout(() => drawMap(), 120);
  }).observe(E.stage);
  document.addEventListener("keydown", e => {
    if (e.key === "Escape" && S.sel) { const p = S.sel; select(null); const g = shapes[p]; if (g) g.focus({ preventScroll: true }); }
  });
}

const campTxt = () => C.focus ? `campaña ${C.focus.id} · datos a ${K.label.toLowerCase()}` : "";

function fillFor(d) {
  const a = Math.abs(d);
  if (a <= C.FLAT) return "color-mix(in srgb, var(--neutral) 26%, var(--surface))";
  return `color-mix(in srgb, var(--${d > 0 ? "up" : "down"}) ${Math.round(24 + 34 * Math.min(1, a / 12))}%, var(--surface))`;
}
const signo = d => d > C.FLAT ? "▲ " : d < -C.FLAT ? "▼ " : "";

/* ---------------- Mapa ---------------- */
function buildMapShell() {
  const chips = [-12, -5, 0, 5, 12].map(d => `<i style="background:${fillFor(d)}"></i>`).join("");
  E.map.innerHTML = `
    <div class="mz-head"><h3>¿Cómo viene cada partido?</h3>
      <p class="desc">${K ? `Cada partido frente a su promedio histórico · ${C.esc(campTxt())}` : "El mapa se colorea con la primera estimación de la campaña."}</p></div>
    <div class="mz-stage" id="mzStage"><div class="skeleton"></div></div>
    <div class="mz-foot">
      <div class="mz-legend" aria-hidden="true"><span>Debajo de su promedio</span><span class="chips5">${chips}</span><span>Arriba</span></div>
      <span id="mzHint">Elegí un partido para ver el detalle</span>
    </div>`;
  E.stage = $("#mzStage");
}

function ringsPath(rings, pr = proj) {
  return rings.map(a => "M" + a.map(pt => { const q = pr(pt); return q[0].toFixed(1) + "," + q[1].toFixed(1); }).join("L") + "Z").join("");
}
function bboxOf(rings) {
  let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
  rings.forEach(a => a.forEach(pt => { const [x, y] = proj(pt); if (x < x0) x0 = x; if (x > x1) x1 = x; if (y < y0) y0 = y; if (y > y1) y1 = y; }));
  return [x0, y0, x1, y1];
}
function dentro([x, y], ring) {
  let c = false;
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
    const [x1, y1] = ring[i], [x2, y2] = ring[j];
    if ((y1 > y) !== (y2 > y) && x < (x2 - x1) * (y - y1) / (y2 - y1) + x1) c = !c;
  }
  return c;
}
function frame(b, pad) {
  const a = (E.stage.clientWidth || 1) / (E.stage.clientHeight || 1);
  let w = (b[2] - b[0]) * pad, h = (b[3] - b[1]) * pad;
  if (w / h < a) w = h * a; else h = w / a;
  return [(b[0] + b[2]) / 2 - w / 2, (b[1] + b[3]) / 2 - h / 2, w, h];
}
function setVB(v) {
  vb = v;
  E.svg.setAttribute("viewBox", v.map(n => n.toFixed(2)).join(" "));
  E.svg.style.setProperty("--u", (v[2] / (E.stage.clientWidth || VB)).toFixed(4));
}
function animateTo(target) {
  cancelAnimationFrame(raf);
  if (reduce() || document.hidden) { setVB(target); return; }
  const from = vb.slice(), t0 = performance.now(), dur = 850;
  const ease = t => t < .5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
  const step = now => {
    const t = Math.min(1, (now - t0) / dur), k = ease(t);
    setVB(from.map((v, i) => v + (target[i] - v) * k));
    if (t < 1) raf = requestAnimationFrame(step);
  };
  raf = requestAnimationFrame(step);
}

function drawMap() {
  // Proyección equirectangular centrada en la zona (suficiente a esta escala)
  let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
  G.partidos.forEach(p => p.anillos.forEach(a => a.forEach(([x, y]) => { if (x < x0) x0 = x; if (x > x1) x1 = x; if (y < y0) y0 = y; if (y > y1) y1 = y; })));
  const cx = (x0 + x1) / 2, cy = (y0 + y1) / 2, kx = Math.cos(cy * Math.PI / 180);
  const sc = VB / Math.max((x1 - x0) * kx, y1 - y0);
  proj = ([lon, lat]) => [VB / 2 + (lon - cx) * kx * sc, VB / 2 - (lat - cy) * sc];

  E.stage.innerHTML = `<button type="button" class="mz-back" id="mzBack" hidden>${ICON_BACK}Ver toda la zona</button>`;
  const narrow = E.stage.clientWidth < 430;
  const svg = E.svg = sv("svg", { class: "mz-svg", role: "group", "aria-label": "Mapa de la zona: General Arenales, Junín, Leandro N. Alem, Lincoln y General Pinto. Elegí un partido para ver su detalle." }, E.stage);
  const bg = sv("rect", { class: "mz-bg", x: -4 * VB, y: -4 * VB, width: 9 * VB, height: 9 * VB }, svg);
  bg.addEventListener("click", () => { if (S.sel) select(null); });

  // Vecinos: contexto en gris
  const gv = sv("g", { class: "mz-vec", "aria-hidden": "true" }, svg);
  G.vecinos.forEach(v => sv("path", { d: ringsPath(v.anillos) }, gv));
  gv.addEventListener("click", () => { if (S.sel) select(null); });

  // Partidos de la zona
  const gp = sv("g", { class: "mz-parts" }, svg);
  shapes = {};
  G.partidos.forEach(p => {
    const r = byP[p.nombre];
    const g = sv("g", { class: "mz-p", tabindex: "0", role: "button", "data-p": p.nombre, "aria-pressed": "false",
      "aria-label": r ? `${p.nombre}: rinde promedio estimado ${C.f1(r.e)} quintales por hectárea, ${C.fpct(r.d)} respecto de su promedio histórico. Enter para ver el detalle.` : p.nombre }, gp);
    p._d = ringsPath(p.anillos); p._bb = bboxOf(p.anillos); p._ring = p.anillos[0].map(proj);
    sv("path", { d: p._d, style: `fill:${r ? fillFor(r.d) : "var(--surface)"}` }, g);
    g.addEventListener("click", e => { if (S.sel !== p.nombre) select(p.nombre, { teclado: e.detail === 0 }); });
    g.addEventListener("keydown", e => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); select(p.nombre, { teclado: true }); } });
    g.addEventListener("pointermove", e => { if (e.pointerType === "mouse" && r && S.sel !== p.nombre) C.showTip(tipPartido(r), e.clientX, e.clientY); });
    g.addEventListener("pointerenter", () => hl(p.nombre, true));
    g.addEventListener("pointerleave", () => { C.hideTip(); hl(p.nombre, false); });
    shapes[p.nombre] = g;
  });
  E.ring = sv("path", { class: "mz-ring" }, svg);
  E.locs = sv("g", { class: "mz-locs" }, svg);

  // Etiquetas de partido (tamaño constante en pantalla gracias a --u)
  const gl = sv("g", { "aria-hidden": "true" }, svg);
  E.labels = {};
  G.partidos.forEach(p => {
    const r = byP[p.nombre], [x, y] = proj(p.centro), X = x.toFixed(1);
    const t = sv("text", { class: "mz-lbl", x: X, y: y.toFixed(1) }, gl);
    sv("tspan", { class: "n", x: X, dy: r ? "-0.15em" : "0.35em" }, t).textContent = narrow ? (CORTO[p.nombre] || p.nombre) : p.nombre;
    if (r) sv("tspan", { class: "v", x: X, dy: "1.3em" }, t).textContent = signo(r.d) + C.fpct(r.d);
    E.labels[p.nombre] = t;
  });

  // Mini mapa de ubicación en la provincia
  if (G.provincia && G.provincia.length > 3) {
    let a0 = Infinity, b0 = Infinity, a1 = -Infinity, b1 = -Infinity;
    G.provincia.forEach(([x, y]) => { if (x < a0) a0 = x; if (x > a1) a1 = x; if (y < b0) b0 = y; if (y > b1) b1 = y; });
    const km = Math.cos((b0 + b1) / 2 * Math.PI / 180), s = 76 / Math.max((a1 - a0) * km, b1 - b0);
    const ox = (80 - (a1 - a0) * km * s) / 2, oy = (80 - (b1 - b0) * s) / 2;
    const pm = ([lon, lat]) => [ox + (lon - a0) * km * s, oy + (b1 - lat) * s];
    const zona = G.partidos.map(p => ringsPath(p.anillos.map(a => a.filter((_, i) => i % 8 === 0)), pm)).join("");
    const mini = document.createElement("div");
    mini.className = "mz-mini"; mini.setAttribute("aria-hidden", "true");
    mini.innerHTML = `<svg viewBox="0 0 80 80"><path class="prov" d="${ringsPath([G.provincia], pm)}"/><path class="zona" d="${zona}"/></svg>Buenos Aires`;
    E.stage.appendChild(mini);
  }

  E.zoneBB = [Math.min(...G.partidos.map(p => p._bb[0])), Math.min(...G.partidos.map(p => p._bb[1])), Math.max(...G.partidos.map(p => p._bb[2])), Math.max(...G.partidos.map(p => p._bb[3]))];
  // Nombres de los vecinos: solo los que entran completos en la vista general
  if (!narrow) {
    const f = frame(E.zoneBB, 1.1), W = E.stage.clientWidth, H = E.stage.clientHeight, u = f[2] / W;
    G.vecinos.forEach(v => {
      const [x, y] = proj(v.centro), px = (x - f[0]) / u, py = (y - f[1]) / u, hw = v.nombre.length * 3 + 6;
      if (px - hw < 4 || px + hw > W - 4 || py < 14 || py > H - 8 || (px + hw > W - 100 && py > H - 110)) return;
      if ([-hw, 0, hw].some(dx => G.partidos.some(p => dentro([x + dx * u, y], p._ring)))) return; // tapado por la zona
      sv("text", { x: x.toFixed(1), y: y.toFixed(1) }, gv).textContent = v.nombre;
    });
  }
  E.back = $("#mzBack");
  E.back.addEventListener("click", () => { const p = S.sel; select(null); if (shapes[p]) shapes[p].focus({ preventScroll: true }); });
  setVB(frame(E.zoneBB, 1.1));
  if (S.sel) applySelection(false);
}

function tipPartido(r) {
  return `<div class="tt">${C.esc(r.p)}</div>
    <div class="tr"><span>Rinde promedio estimado</span><b>${C.f1(r.e)} qq/ha</b></div>
    ${r.r ? `<div class="tr"><span>Puede variar entre</span><b>${C.f1(r.r[0])} y ${C.f1(r.r[1])}</b></div>` : ""}
    <div class="tr"><span>Promedio histórico</span><b>${C.f1(r.h)}</b></div>
    <div class="tr"><span>Diferencia</span><b>${C.fpct(r.d)}</b></div>`;
}
function hl(p, on) {
  if (shapes[p]) shapes[p].classList.toggle("hl", on);
  const row = $$(".mz-row", E.panel).find(b => b.dataset.p === p);
  if (row) row.classList.toggle("hl", on);
}

/* Localidades del partido elegido: solo contexto geográfico */
function buildLocs(gp, target) {
  E.locs.innerHTML = "";
  const W = E.stage.clientWidth, H = E.stage.clientHeight, u = target[2] / W;
  const px = pt => { const [x, y] = proj(pt); return [(x - target[0]) / u, (y - target[1]) / u, x, y]; };
  const R = { cabecera: 5, localidad: 3.2, paraje: 2 }, FS = { cabecera: 13, localidad: 11, paraje: 10 };
  const taken = [[0, 0, 190, 48], [W - 96, H - 104, W, H]]; // botón "Ver toda la zona" y mini mapa
  const pts = gp.localidades.map(l => ({ l, q: px([l.lon, l.lat]) })).filter(o => o.q[0] > 4 && o.q[0] < W - 4 && o.q[1] > 4 && o.q[1] < H - 4);
  pts.forEach(o => { const r = R[o.l.t] + 2; taken.push([o.q[0] - r, o.q[1] - r, o.q[0] + r, o.q[1] + r]); });
  const libre = b => b[0] > 3 && b[1] > 3 && b[2] < W - 3 && b[3] < H - 3 && !taken.some(t => b[0] < t[2] && b[2] > t[0] && b[1] < t[3] && b[3] > t[1]);
  pts.forEach(o => {
    const { l, q } = o, r = R[l.t], fs = FS[l.t], tw = l.n.length * fs * (l.t === "cabecera" ? .6 : .55) + 4, th = fs + 3;
    const g = sv("g", { class: "mz-loc t-" + l.t }, E.locs);
    sv("circle", { class: "d", cx: q[2].toFixed(1), cy: q[3].toFixed(1), r: (r * u).toFixed(2) }, g);
    const cand = [
      { b: [q[0] + r + 4, q[1] - th / 2, q[0] + r + 4 + tw, q[1] + th / 2], a: "start", dx: r + 5, dy: fs * .35 },
      { b: [q[0] - r - 4 - tw, q[1] - th / 2, q[0] - r - 4, q[1] + th / 2], a: "end", dx: -(r + 5), dy: fs * .35 },
      { b: [q[0] - tw / 2, q[1] - r - 3 - th, q[0] + tw / 2, q[1] - r - 3], a: "middle", dx: 0, dy: -(r + 5) },
      { b: [q[0] - tw / 2, q[1] + r + 3, q[0] + tw / 2, q[1] + r + 3 + th], a: "middle", dx: 0, dy: r + 4 + fs * .8 }
    ].find(c => libre(c.b));
    if (cand) {
      taken.push(cand.b);
      sv("text", { x: (q[2] + cand.dx * u).toFixed(1), y: (q[3] + cand.dy * u).toFixed(1), "text-anchor": cand.a }, g).textContent = l.n;
    }
    const h = sv("circle", { class: "h", cx: q[2].toFixed(1), cy: q[3].toFixed(1), r: (11 * u).toFixed(2) }, g);
    h.addEventListener("pointermove", e => C.showTip(`<div class="tt">${C.esc(l.n)}</div><div class="tx">${TIPO[l.t]} · partido de ${C.esc(gp.nombre)}</div>`, e.clientX, e.clientY));
    h.addEventListener("pointerleave", C.hideTip);
  });
}

function applySelection(anim) {
  const p = S.sel, gp = p && G.partidos.find(x => x.nombre === p);
  E.svg.classList.toggle("zoomed", !!gp);
  Object.entries(shapes).forEach(([n, g]) => { g.classList.toggle("sel", n === p); g.setAttribute("aria-pressed", n === p); });
  Object.entries(E.labels).forEach(([n, t]) => t.classList.toggle("sel", n === p));
  E.back.hidden = !gp;
  const hint = $("#mzHint");
  if (hint) hint.textContent = gp ? "Las localidades son referencia geográfica: el rinde se estima por partido" : "Elegí un partido para ver el detalle";
  let target;
  if (gp) { target = frame(gp._bb, 1.22); E.ring.setAttribute("d", gp._d); buildLocs(gp, target); }
  else { target = frame(E.zoneBB, 1.1); E.ring.setAttribute("d", ""); E.locs.innerHTML = ""; }
  // Etiquetas de los otros partidos: se ocultan si quedan fuera de la vista o debajo del botón
  const W = E.stage.clientWidth, H = E.stage.clientHeight, u = target[2] / W;
  G.partidos.forEach(q => {
    const [x, y] = proj(q.centro), px = (x - target[0]) / u, py = (y - target[1]) / u;
    E.labels[q.nombre].classList.toggle("off", !!gp && q !== gp && (px < 55 || px > W - 55 || py < 22 || py > H - 26 || (px < 270 && py < 74) || (px > W - 140 && py > H - 120)));
  });
  if (anim) animateTo(target); else { cancelAnimationFrame(raf); setVB(target); }
}

function select(p, o = {}) {
  if (p && !byP[p]) return;
  S.sel = p;
  C.hideTip();
  if (G && E.svg) applySelection(true);
  renderPanel();
  if (p) {
    if (innerWidth <= 980 && E.panel.getBoundingClientRect().top > innerHeight * .62)
      E.map.scrollIntoView({ behavior: reduce() ? "auto" : "smooth", block: "start" });
    if (o.teclado) { const d = $(".mz-det", E.panel); if (d) d.focus({ preventScroll: true }); }
  }
}

/* ---------------- Panel ---------------- */
function buildPanel() {
  const zona = $("#mzZona");
  const ov = document.createElement("div"); ov.id = "mzOverview";
  zona.parentNode.insertBefore(ov, zona); ov.appendChild(zona);
  if (rows.length) {
    const list = rows.slice().sort((a, b) => b.d - a.d).map(r => `
      <button type="button" class="mz-row" data-p="${C.esc(r.p)}" aria-label="${C.esc(r.p)}: estimación ${C.f1(r.e)} quintales por hectárea; promedio histórico ${C.f1(r.h)}; diferencia ${C.fpct(r.d)}. Ver detalle.">
        <span class="rn">${C.esc(r.p)}</span>
        <span class="re num"><small>estimado</small>${C.f1(r.e)}<small>qq/ha</small></span>
        <span class="rp num">histórico ${C.f1(r.h)} qq/ha</span>
        <span class="badge ${C.dirClass(r.d)}">${C.arrow(r.d)}<span class="num">${C.fpct(r.d)}</span></span>
        <svg class="chv" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="m9 6 6 6-6 6"/></svg>
      </button>`).join("");
    ov.insertAdjacentHTML("beforeend", `
      <h3 class="mz-list-h">Rinde estimado por partido ${C.info(C.PARTIDO_TIP + " «Histórico» es el promedio del partido desde 2000/01; el porcentaje compara la estimación con ese promedio.", "Rinde promedio del partido")}</h3>
      <div class="mz-list">${list}</div>`);
  }
  const det = document.createElement("div"); det.id = "mzDetalle"; det.hidden = true;
  E.panel.appendChild(det);
  E.ov = ov; E.det = det;
  E.panel.addEventListener("click", e => {
    const row = e.target.closest(".mz-row"); if (row) { select(row.dataset.p, { teclado: e.detail === 0 }); return; }
    if (e.target.closest(".mz-close")) { const p = S.sel; select(null); const b = $$(".mz-row", E.panel).find(x => x.dataset.p === p); if (b && e.detail === 0) b.focus(); return; }
    const tab = e.target.closest(".mz-tabs button"); if (tab) { S.tab = tab.dataset.t; renderTabs(); }
  });
  E.panel.addEventListener("pointerover", e => { const row = e.target.closest(".mz-row"); if (row) hl(row.dataset.p, true); });
  E.panel.addEventListener("pointerout", e => { const row = e.target.closest(".mz-row"); if (row && !row.contains(e.relatedTarget)) hl(row.dataset.p, false); });
}

function rangeHTML(r) {
  const vals = [r.e, r.h].concat(r.r || []);
  const lo = Math.floor(Math.min(...vals) - 2), hi = Math.ceil(Math.max(...vals) + 2), pos = v => (v - lo) / (hi - lo) * 100;
  return `<div class="vrange">
    <div class="vr-head">${r.r ? `Puede variar entre <b class="num">${C.f1(r.r[0])}</b> y <b class="num">${C.f1(r.r[1])} qq/ha</b> ${C.info(C.RANGE_TIP, "¿Por qué un rango?")}<span class="vr-avg"><i></i>Promedio histórico <b class="num">${C.f1(r.h)}</b></span>` : `Promedio histórico: <b class="num">${C.f1(r.h)} qq/ha</b>`}</div>
    <div class="vr-bar" aria-hidden="true"><div class="trk"></div>${r.r ? `<div class="bnd" style="left:${pos(r.r[0])}%;width:${pos(r.r[1]) - pos(r.r[0])}%"></div>` : ""}
      <div class="avg" style="left:${pos(r.h)}%" data-tip="Promedio histórico de ${C.esc(r.p)}: ${C.f1(r.h)} qq/ha"></div><div class="est" style="left:${pos(r.e)}%"></div></div>
  </div>`;
}

function renderPanel() {
  const r = S.sel && byP[S.sel];
  E.ov.hidden = !!r; E.det.hidden = !r;
  if (!r) { E.det.innerHTML = ""; return; }
  const det = (C.M.detalle_partidos || {})[r.p];
  const tabs = [["camp", "Campaña"]].concat(det && det.serie ? [["hist", "Historia"]] : [], det && det.sup_sembrada_ha ? [["sup", "Superficie"]] : [], [["prec", "Precisión"]]);
  if (!tabs.some(t => t[0] === S.tab)) S.tab = "camp";
  const txt = C.dirClass(r.d) === "up" ? "por encima de" : C.dirClass(r.d) === "down" ? "por debajo de" : "en línea con";
  E.det.innerHTML = `<div class="mz-det" tabindex="-1" style="outline:none">
    <div class="mz-det-top">
      <div><div class="eyebrow" style="margin:0">Partido · campaña ${C.esc(C.focus.id)} · ${C.esc(K.label.toLowerCase())}</div><h3 class="mz-name">${C.esc(r.p)}</h3></div>
      <button type="button" class="mz-close">${ICON_BACK}Toda la zona</button>
    </div>
    <div class="big"><span class="val num">${C.f1(r.e)}</span><span class="unit">qq/ha</span>${C.badge(r.d, "vs. su promedio")}${C.info(`Rinde promedio estimado con datos a ${K.label.toLowerCase()}: viene ${txt} lo habitual en el partido. ${C.PARTIDO_TIP}`, "Rinde promedio del partido")}</div>
    ${rangeHTML(r)}
    <div class="mz-tabs" role="tablist" aria-label="Más datos de ${C.esc(r.p)}">${tabs.map(t => `<button type="button" role="tab" data-t="${t[0]}" aria-selected="false">${t[1]}</button>`).join("")}</div>
    <div class="mz-tabpanel" role="tabpanel" id="mzTab"></div>
  </div>`;
  renderTabs();
}

function renderTabs() {
  const r = byP[S.sel]; if (!r) return;
  $$(".mz-tabs button", E.det).forEach(b => b.setAttribute("aria-selected", b.dataset.t === S.tab));
  const box = $("#mzTab"), det = (C.M.detalle_partidos || {})[r.p] || {};
  ({ camp: tabCamp, hist: tabHist, sup: tabSup, prec: tabPrec })[S.tab](box, r, det);
}

function tabCamp(box, r) {
  const c = C.focus, n = c.cortes.length, real = C.realP(c, r.p);
  box.innerHTML = `<p class="desc">${n > 1 ? `Cómo cambió la estimación de ${C.esc(r.p)} con cada actualización mensual.` : "Es la primera estimación de la campaña. La evolución se completa con cada actualización mensual."}</p>
    <div class="chart" id="mzC"></div>
    <div class="legend"><span><span class="sw" style="background:var(--primary)"></span>Estimación</span>
      ${r.r ? '<span><span class="sw bandsw"></span>Rango esperable</span>' : ""}
      <span><span class="sw dash"></span>Promedio del partido (${C.f1(r.h)})</span>
      ${real != null ? `<span><span class="sw" style="background:var(--text)"></span>Resultado real (${C.f1(real)})</span>` : ""}</div>`;
  const at = f => C.VENTANAS.map(w => { const k = c.cortes.find(x => x.ventana === w.v); return k ? f(k) : null; });
  C.lineChart($("#mzC"), {
    labels: C.VENTANAS.map(w => w.label.replace("Fin de ", "")), shortLabels: C.VENTANAS.map(w => w.short),
    series: [{ name: "Estimación", color: "var(--primary)", values: at(k => k.partidos[r.p]), width: 2.5 }],
    band: at(k => k.partidos_rango ? k.partidos_rango[r.p] : null),
    refs: [{ v: r.h, label: "Prom.", cls: "ref" }].concat(real != null ? [{ v: real, label: "Real", cls: "real" }] : []),
    height: 170, compact: true, pendingLabel: true
  });
}

function tabHist(box, r, det) {
  const years = Object.keys(det.serie).map(Number).sort((a, b) => a - b), vals = years.map(y => det.serie[y]);
  const iB = vals.indexOf(Math.max(...vals)), iW = vals.indexOf(Math.min(...vals));
  const fy = +C.focus.id.split("/")[0];
  const labels = years.map(id2), full = years.map(idFull), v = vals.slice(), est = [];
  // Campañas posteriores al último dato oficial: se muestran con su última estimación
  for (let y = years[years.length - 1] + 1; y <= fy; y++) {
    const c = C.camps.find(x => x.id === idFull(y)); if (!c || !c.cortes.length) continue;
    est.push(v.length); labels.push(id2(y)); full.push(c.id); v.push(C.lastCut(c).partidos[r.p]);
  }
  const conEst = est.length > 0;
  box.innerHTML = `<p class="desc">Rinde promedio del partido en cada campaña desde ${full[0]} · qq/ha</p>
    <div class="chart mz-bars" id="mzC"></div>
    <div class="mz-bw num"><span><i style="background:var(--up)"></i>Mejor: <b>${full[iB]}</b> · ${C.f1(vals[iB])} qq/ha</span><span><i style="background:var(--down)"></i>Peor: <b>${full[iW]}</b> · ${C.f1(vals[iW])} qq/ha</span></div>
    <div class="legend"><span><span class="sw dash"></span>Promedio histórico (${C.f1(r.h)})</span>${conEst ? `<span><span class="sw bandsw" style="box-shadow:inset 0 0 0 1px var(--primary)"></span>Estimación (sin resultado oficial todavía)</span>` : ""}</div>`;
  barChart($("#mzC"), {
    labels, values: v, ref: r.h, height: 150, ghost: est,
    fill: i => i === iB ? "var(--up)" : i === iW ? "var(--down)" : "color-mix(in srgb, var(--primary) 36%, var(--surface))",
    marks: { [iB]: C.f1(vals[iB]), [iW]: C.f1(vals[iW]) },
    tip: i => `<div class="tt">Campaña ${full[i]}</div><div class="tr"><span>${est.includes(i) ? "Estimación" : "Rinde oficial"}</span><b>${C.f1(v[i])} qq/ha</b></div><div class="tr"><span>vs. promedio histórico</span><b>${C.fpct(C.pct(v[i], r.h))}</b></div>${i === iB ? '<div class="tx">Mejor campaña de la serie</div>' : i === iW ? '<div class="tx">Peor campaña de la serie</div>' : ""}`
  });
}

function tabSup(box, r, det) {
  const years = Object.keys(det.sup_sembrada_ha).map(Number).sort((a, b) => a - b).filter(y => det.sup_sembrada_ha[y] != null);
  const ult = years.slice(-5), prom = f => ult.reduce((s, y) => s + f(y), 0) / ult.length;
  const semb = prom(y => det.sup_sembrada_ha[y]);
  const cos = prom(y => (det.sup_cosechada_ha || {})[y] != null ? det.sup_cosechada_ha[y] : det.sup_sembrada_ha[y]);
  const ha = x => nf0.format(Math.round(x / 100) * 100), ton = q => nf0.format(Math.round(cos * q / 10 / 1000) * 1000);
  const tipProd = `Cuenta simple: la superficie que se cosecha habitualmente (${ha(cos)} ha) por el rinde promedio estimado (${C.f1(r.e)} qq/ha, es decir ${String((r.e / 10).toFixed(2)).replace(".", ",")} t/ha). Sirve para dimensionar el volumen del partido; no reemplaza una estimación oficial de producción.`;
  box.innerHTML = `<div class="mz-kpis">
      <div class="t"><span>Superficie sembrada con soja</span><strong class="num">${ha(semb)}<small>ha</small></strong><em>promedio ${idFull(ult[0])}–${idFull(ult[ult.length - 1])}</em></div>
      <div class="t"><span>Producción orientativa ${C.info(tipProd, "Superficie × rinde")}</span><strong class="num">≈ ${ton(r.e)}<small>t</small></strong><em>${r.r ? `entre ${ton(r.r[0])} y ${ton(r.r[1])} t` : "superficie × rinde estimado"}</em></div>
    </div>
    <p class="desc" style="margin-top:12px">Superficie sembrada por campaña · miles de hectáreas (MAGyP)</p>
    <div class="chart mz-bars" id="mzC"></div>`;
  barChart($("#mzC"), {
    labels: years.map(id2), values: years.map(y => det.sup_sembrada_ha[y] / 1000), height: 120,
    fill: i => ult.includes(years[i]) ? "color-mix(in srgb, var(--primary) 70%, var(--surface))" : "color-mix(in srgb, var(--primary) 36%, var(--surface))",
    tip: i => `<div class="tt">Campaña ${idFull(years[i])}</div><div class="tr"><span>Superficie sembrada</span><b>${nf0.format(det.sup_sembrada_ha[years[i]])} ha</b></div>${(det.sup_cosechada_ha || {})[years[i]] != null ? `<div class="tr"><span>Superficie cosechada</span><b>${nf0.format(det.sup_cosechada_ha[years[i]])} ha</b></div>` : ""}`
  });
}

function tabPrec(box, r, det) {
  const hc = C.camps.filter(c => c.cortes.length && C.realP(c, r.p) != null);
  const v = det.validacion;
  const est = hc.map(c => C.bestCut(c).partidos[r.p]), real = hc.map(c => C.realP(c, r.p));
  const mae = v ? v.error_tipico : (hc.length ? est.reduce((s, e, i) => s + Math.abs(e - real[i]), 0) / hc.length : null);
  box.innerHTML = `<div class="mz-kpis">
      <div class="t"><span>Error típico en ${C.esc(r.p)} ${C.info("Diferencia promedio entre la estimación de fin de noviembre y el rinde oficial del partido, en las campañas de prueba.", "Error típico")}</span><strong class="num">${mae != null ? "±" + C.f1(mae) : "–"}<small>qq/ha</small></strong></div>
      ${v ? `<div class="t"><span>Acertó la tendencia ${C.info("Cuántas veces anticipó bien si el rinde iba a quedar por encima o por debajo de lo habitual en el partido.", "Acierto de tendencia")}</span><strong class="num">${v.aciertos_tendencia} de ${v.campanas}<small>campañas</small></strong></div>` : ""}
    </div>
    ${hc.length > 1 ? `<p class="desc" style="margin-top:10px">Estimado a fin de noviembre vs. rinde oficial · qq/ha</p>
    <div class="chart" id="mzC"></div>
    <div class="legend"><span><span class="sw" style="background:var(--primary)"></span>Estimado</span><span><span class="sw" style="background:var(--accent)"></span>Rinde oficial (MAGyP)</span></div>` : ""}`;
  if (hc.length > 1) C.lineChart($("#mzC"), {
    labels: hc.map(c => c.id), shortLabels: hc.map(c => c.id.slice(2)),
    series: [{ name: "Estimado en nov.", color: "var(--primary)", values: est, width: 2.5 }, { name: "Real", color: "var(--accent)", values: real, width: 2.5 }],
    height: 135, compact: true
  });
}

/* ---------------- Gráfico de barras (SVG puro) ---------------- */
function barChart(el, o) {
  const W = Math.max(240, el.clientWidth || 300), H = o.height || 180;
  const m = { t: 18, r: 4, b: 20, l: 28 }, iw = W - m.l - m.r, ih = H - m.t - m.b, n = o.values.length;
  const max = Math.max(...o.values, o.ref || 0), raw = max / 3.5, pw = Math.pow(10, Math.floor(Math.log10(raw)));
  const step = [1, 2, 5, 10].map(k => k * pw).find(s => s >= raw), hi = Math.ceil(max * 1.04 / step) * step;
  const bw = iw / n, gap = Math.min(3, Math.max(1.5, bw * .22)), y = v => m.t + ih - v / hi * ih, x = i => m.l + i * bw;
  let s = `<svg viewBox="0 0 ${W} ${H}" height="${H}" role="img" aria-label="Gráfico de barras por campaña">`;
  for (let t = 0; t <= hi + 1e-9; t += step) s += `<line class="gl" x1="${m.l}" x2="${W - m.r}" y1="${y(t)}" y2="${y(t)}"/><text x="${m.l - 5}" y="${y(t) + 3.5}" text-anchor="end">${nf0.format(t)}</text>`;
  o.values.forEach((v, i) => {
    const h = Math.max(1, y(0) - y(v)), ghost = (o.ghost || []).includes(i);
    s += `<rect class="b" x="${(x(i) + gap / 2).toFixed(1)}" y="${(y(0) - h).toFixed(1)}" width="${(bw - gap).toFixed(1)}" height="${h.toFixed(1)}" rx="${Math.min(3, (bw - gap) / 2).toFixed(1)}" ${ghost ? 'fill="var(--band)" stroke="var(--primary)" stroke-width="1.2" stroke-dasharray="3 2"' : `fill="${o.fill(i)}"`}/>`;
  });
  if (o.ref) s += `<line x1="${m.l}" x2="${W - m.r}" y1="${y(o.ref)}" y2="${y(o.ref)}" stroke="var(--ref)" stroke-width="1.5" stroke-dasharray="5 4" opacity=".9"/>`;
  Object.entries(o.marks || {}).forEach(([i, txt]) => {
    const cx = Math.max(m.l + 14, Math.min(W - m.r - 14, x(+i) + bw / 2));
    s += `<text class="mk" x="${cx.toFixed(1)}" y="${(y(o.values[i]) - 5).toFixed(1)}" text-anchor="middle">${txt}</text>`;
  });
  const every = Math.max(1, Math.ceil(n * 36 / iw));
  o.labels.forEach((lb, i) => { if (i % every === 0 && (i === n - 1 || n - 1 - i >= every * .7) || i === n - 1) s += `<text x="${(x(i) + bw / 2).toFixed(1)}" y="${H - 5}" text-anchor="middle">${lb}</text>`; });
  o.values.forEach((_, i) => { s += `<rect class="hitc" data-i="${i}" x="${x(i).toFixed(1)}" y="0" width="${bw.toFixed(1)}" height="${H}"/>`; });
  el.innerHTML = s + "</svg>";
  const bars = $$("rect.b", el);
  const over = e => { const i = +e.target.dataset.i; bars.forEach((b, j) => b.style.opacity = j === i ? 1 : .55); C.showTip(o.tip(i), e.clientX, e.clientY); };
  $$(".hitc", el).forEach(h => { h.addEventListener("pointermove", over); h.addEventListener("pointerdown", over); });
  el.firstChild.addEventListener("pointerleave", () => { bars.forEach(b => b.style.opacity = 1); C.hideTip(); });
}

/* ---------------- Redibujar (cambio de ancho) ---------------- */
function redraw() {
  if (!C || !E.stage) return;
  if (G) drawMap();
  if (S.sel) renderTabs();
}

return { init, redraw, select };
})();
