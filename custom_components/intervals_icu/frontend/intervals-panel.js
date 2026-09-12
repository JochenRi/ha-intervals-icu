/* Intervals.icu panel 0.9.0
 *
 * Design ground rules, each carried from published guidance:
 * - Inverted pyramid: the verdict sits centered on top, details below
 *   (dashboard layout research; Few, Information Dashboard Design).
 * - Status is never colour alone: every state carries word + own icon shape
 *   (WCAG 1.4.1; ~8% of men cannot separate red from green).
 * - No dual y-axes. Related series stack as small multiples on one shared
 *   x-axis with one crosshair (Datawrapper / policyviz guidance; the same
 *   pattern intervals.icu uses in its timeline).
 * - Panels expand independently; auto-collapse blocks comparing
 *   (accordion accessibility guidance). Native <details> everywhere.
 * - Gauges are replaced by a bullet graph for the load budget (Few).
 * - TrainingPeaks-style plan compliance: done / missed / future are
 *   separate states with icon + colour, body text stays high-contrast.
 */
"use strict";

/* ------------------------------------------------------------------ */
/* palette + iconography                                               */
/* ------------------------------------------------------------------ */
/* Palette — two registers that never mix.
 *
 * STATE (green/amber/red/grey) means a verdict and nothing else. It is never
 * used for a category or a data series.
 * DATA (blue/violet/cyan/magenta/slate/deep) carries categories and channels.
 * Inside any single view every data tone appears at most once; tests/design
 * checks both rules, because the same class of slip cost 0.7.0, 0.8.0 and
 * 0.9.0 a release each (two yellows, two blues, two reds).
 */
const C = {
  bg: "#0f151c", card: "#171f29", card2: "#1d2733", line: "#2a3644",
  tx: "#e8eef5", tx2: "#a6b4c4", tx3: "#6e8093",

  // state register
  green: "#34d399", amber: "#fbbf24", red: "#f87171", grey: "#6e8093",

  // data register
  blue: "#60a5fa", violet: "#a78bfa", cyan: "#22d3ee",
  magenta: "#e879f9", slate: "#94a3b8", deep: "#64748b",
};

/* Role assignments. Each maps to a data-register tone above — never to a
 * state tone. Within one view the assignments used must be distinct. */
const ROLE = {
  // fitness view
  ctl: C.blue, atl: C.violet, form: C.cyan, dayload: C.slate,
  // activity detail channels
  pow: C.violet, hr: C.magenta, dfa: C.cyan,
  cad: C.slate, vel: C.blue, alt: C.deep,
  // load + dfa views
  series: C.blue, second: C.violet,
};

const IC = {
  ok:   '<circle cx="12" cy="12" r="9"/><path d="M8.5 12.5l2.5 2.5 4.5-5.5"/>',
  warn: '<path d="M12 4l9 16H3z"/><path d="M12 10v4.5"/><circle cx="12" cy="17.4" r="0.4"/>',
  stop: '<circle cx="12" cy="12" r="9"/><path d="M9 9l6 6M15 9l-6 6"/>',
  na:   '<circle cx="12" cy="12" r="9"/><path d="M8 12h8"/>',
  bike: '<circle cx="5.8" cy="16.8" r="3.4"/><circle cx="18.2" cy="16.8" r="3.4"/><path d="M5.8 16.8L10 7.5h4.6M10 7.5l3.4 9.3 4.8-6.5h-6"/>',
  run:  '<circle cx="14.5" cy="4.8" r="1.9"/><path d="M8.5 21l2.6-5.2 3 1.8.9 3.4M7.5 12.5l3.4-3 3.6 1 2.8 2.6M12.4 9.9l-1.3 3.9"/>',
  walk: '<circle cx="13" cy="4.6" r="1.9"/><path d="M10 21l2.1-5.6M14.4 21l-1.4-5.6-.8-4M9 12.4l3.2-2.9 2.8 1 2.4 2.7"/>',
  swim: '<path d="M3 17.5c2-1.6 4-1.6 6 0s4 1.6 6 0 4-1.6 6 0"/><circle cx="16.4" cy="7.6" r="1.9"/><path d="M4.5 13.5l5.5-3.4 4 2.4"/>',
  gym:  '<path d="M4 10v4M7.2 8v8M16.8 8v8M20 10v4M7.2 12h9.6"/>',
  dot:  '<circle cx="12" cy="12" r="5"/>',
  moon: '<path d="M19.5 13.8A7.6 7.6 0 0 1 10.2 4.5 7.6 7.6 0 1 0 19.5 13.8z"/>',
  heart:'<path d="M12 20s-7-4.4-7-9.7A3.9 3.9 0 0 1 12 7.6a3.9 3.9 0 0 1 7 2.7C19 15.6 12 20 12 20z"/>',
  pulse:'<path d="M3 12h4l2-4.5 3.5 9L15 12h6"/>',
  steps:'<ellipse cx="9" cy="8.2" rx="2.3" ry="3.3"/><ellipse cx="15" cy="14.6" rx="2.3" ry="3.3"/>',
  gauge:'<path d="M4.5 16.5a7.5 7.5 0 0 1 15 0"/><path d="M12 16.5l3.6-4.6"/>',
  trend:'<path d="M3 17l5.5-5.5 3.5 3.5L20 7"/><path d="M20 12V7h-5"/>',
  wave: '<path d="M3 12c2-5 4-5 6 0s4 5 6 0 4-5 6 0"/>',
  user: '<circle cx="12" cy="8" r="3.4"/><path d="M5 20a7 7 0 0 1 14 0"/>',
  clock:'<circle cx="12" cy="12" r="8.5"/><path d="M12 7.5V12l3 2"/>',
  road: '<path d="M6 20L9.5 4M18 20L14.5 4M12 5v2.6M12 11v2.6M12 17v2.6"/>',
  mtn:  '<path d="M3 19l6-10 3.6 5.4L15 11l6 8z"/>',
  flame:'<path d="M12 3.5c.8 3.2-3.2 4.4-3.2 8a3.7 3.7 0 0 0 7.4 0c0-1.6-.9-2.8-.9-2.8s3.2 1.2 3.2 5a6.5 6.5 0 0 1-13 0c0-6 6.5-6.4 6.5-10.2z"/>',
  bolt: '<path d="M13 3L5 13.5h5L11 21l8-10.5h-5z"/>',
  cal:  '<rect x="4" y="5.5" width="16" height="14.5" rx="2"/><path d="M4 9.5h16M8.5 3.5v3.6M15.5 3.5v3.6"/>',
  chev: '<path d="M9.5 6.5l5.5 5.5-5.5 5.5"/>',
};

function ico(name, color, size) {
  const s = size || 18;
  const st = color ? ` style="color:${color}"` : "";
  return `<svg class="ic" width="${s}" height="${s}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"${st}>${IC[name] || IC.dot}</svg>`;
}

const ST = {
  green:   { word: "grün",       ic: "ok",   c: C.green },
  amber:   { word: "gelb",       ic: "warn", c: C.amber },
  red:     { word: "rot",        ic: "stop", c: C.red },
  unknown: { word: "keine Daten", ic: "na",  c: C.grey },
};
function badge(state, word) {
  const m = ST[state] || ST.unknown;
  return `<span class="bdg" style="color:${m.c};border-color:${m.c}44;background:${m.c}14">${ico(m.ic, m.c, 14)}<span>${word || m.word}</span></span>`;
}

const SPORT = {
  ride:  { c: C.blue,    ic: "bike", l: "Rad" },
  run:   { c: C.violet,  ic: "run",  l: "Lauf" },
  walk:  { c: C.cyan,    ic: "walk", l: "Gehen" },
  swim:  { c: C.magenta, ic: "swim", l: "Schwimmen" },
  gym:   { c: C.slate,   ic: "gym",  l: "Kraft" },
  other: { c: C.deep,    ic: "dot",  l: "Sonstiges" },
};
function groupKey(type) {
  const t = String(type || "");
  if (/Ride/.test(t)) return "ride";
  if (/Run/.test(t)) return "run";
  if (/Walk|Hike/.test(t)) return "walk";
  if (/Swim/.test(t)) return "swim";
  if (/Weight|Workout/.test(t)) return "gym";
  return "other";
}
function sportOf(groupOrType) {
  if (SPORT[groupOrType]) return SPORT[groupOrType];
  const t = String(groupOrType || "");
  if (/Ride/.test(t)) return SPORT.ride;
  if (/Run/.test(t)) return SPORT.run;
  if (/Walk|Hike/.test(t)) return SPORT.walk;
  if (/Swim/.test(t)) return SPORT.swim;
  if (/Weight|Workout/.test(t)) return SPORT.gym;
  return SPORT.other;
}

/* ------------------------------------------------------------------ */
/* formatting                                                          */
/* ------------------------------------------------------------------ */
function esc(s) {
  return String(s == null ? "" : s).replace(/[&<>"']/g, (ch) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  }[ch]));
}
function fmt(v, dec) {
  if (v == null || v === "" || Number.isNaN(+v)) return "–";
  return (+v).toLocaleString("de-DE", {
    minimumFractionDigits: dec || 0, maximumFractionDigits: dec || 0,
  });
}
function sign(v, dec) {
  if (v == null || Number.isNaN(+v)) return "–";
  return (v > 0 ? "+" : "") + fmt(v, dec);
}
function dur(secs) {
  if (!secs && secs !== 0) return "–";
  const s = Math.round(+secs), h = Math.floor(s / 3600), m = Math.round((s % 3600) / 60);
  return h ? `${h}h${String(m).padStart(2, "0")}m` : `${m}m`;
}
function kmf(m) { return m == null ? "–" : fmt(m / 1000, 1) + " km"; }
function hhmm(secs) {
  const s = Math.max(0, Math.round(+secs || 0));
  return `${Math.floor(s / 3600)}:${String(Math.floor((s % 3600) / 60)).padStart(2, "0")}`;
}
const WD = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"];
const WDL = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"];
function dLong(iso) {
  if (!iso) return "";
  const d = new Date(iso + "T00:00:00");
  return `${WDL[(d.getDay() + 6) % 7]}, ${dMed(iso)}`;
}
function dShort(iso) {
  const d = new Date(iso + "T00:00:00");
  return `${WD[(d.getDay() + 6) % 7]} ${String(d.getDate()).padStart(2, "0")}.`;
}
function dMed(iso) {
  if (!iso) return "–";
  const p = String(iso).slice(0, 10).split("-");
  return `${p[2]}.${p[1]}.${p[0]}`;
}
function median(arr) {
  const a = arr.filter((v) => v != null).slice().sort((x, y) => x - y);
  if (!a.length) return null;
  const m = Math.floor(a.length / 2);
  return a.length % 2 ? a[m] : (a[m - 1] + a[m]) / 2;
}
function meanOf(arr) {
  const a = arr.filter((v) => v != null);
  return a.length ? a.reduce((s, v) => s + v, 0) / a.length : null;
}

/* ------------------------------------------------------------------ */
/* chart building blocks (plain SVG, no library)                       */
/* ------------------------------------------------------------------ */
function tickVals(a, b, m) {
  m = m || 4;
  const span = (b - a) || 1;
  let step = Math.pow(10, Math.floor(Math.log10(span / m)));
  const err = span / m / step;
  step *= err >= 7.5 ? 10 : err >= 3 ? 5 : err >= 1.5 ? 2 : 1;
  const out = [];
  for (let v = Math.ceil(a / step) * step; v <= b + step / 1e6; v += step) {
    out.push(+v.toFixed(6));
  }
  return out;
}
/* Day axis for a short window (six weeks), where month boundaries alone leave
 * one or two labels on the whole axis. Anchored on the NEWEST day, because
 * that is the one a reader looks for first - counting from the left would put
 * the tick anywhere as soon as the series grows by a day.
 *
 * Tick every `every` days, label every `label` days, and a month change is
 * always labelled with its month: "12." without a month is not a date. Gaps in
 * the archive are counted as positions, not as calendar days - the dates are
 * the ones that exist, which is exactly why they travel with the values. */
function dayAxis(dates, o) {
  o = o || {};
  const every = o.every || 7, label = o.label || 14;
  const ticks = [], labels = [];
  const list = dates || [];
  const last = list.length - 1;
  for (let i = last; i >= 0; i--) {
    const iso = String(list[i] || "");
    if (iso.length < 10) continue;
    const k = last - i;
    const prev = String(list[i - 1] || "");
    const newMonth = i > 0 && prev.length >= 7 && prev.slice(0, 7) !== iso.slice(0, 7);
    const isTick = k % every === 0 || newMonth;
    if (!isTick) continue;
    ticks.push(i);
    if (k % label === 0 || newMonth) {
      const p = iso.slice(0, 10).split("-");
      labels.push({ i, t: newMonth || k === 0 ? `${p[2]}.${p[1]}.` : `${p[2]}.` });
    }
  }
  ticks.reverse();
  labels.reverse();
  return { ticks, labels };
}

/* x ticks on calendar month boundaries. Spacing by point index put two ticks
 * inside the same month whenever the series was denser there - the axis then
 * read "05.2026  05.2026". Returns at most `max` labels, thinned evenly. */
function monthTicks(dates, max) {
  const out = [];
  let last = null;
  for (let i = 0; i < dates.length; i++) {
    const d = String(dates[i] || "").slice(0, 7);
    if (!d || d === last) continue;
    last = d;
    out.push({ i, t: d.slice(5) + "." + d.slice(2, 4) });
  }
  const cap = max || 7;
  if (out.length <= cap) return out;
  const step = Math.ceil(out.length / cap);
  return out.filter((_, k) => k % step === 0);
}

function domainOf(seriesList, pad) {
  let lo = Infinity, hi = -Infinity;
  for (const s of seriesList) {
    for (const v of (s.v || [])) {
      if (v == null) continue;
      if (v < lo) lo = v;
      if (v > hi) hi = v;
    }
    for (const p of (s.p || [])) {
      if (p.v == null) continue;
      if (p.v < lo) lo = p.v;
      if (p.v > hi) hi = p.v;
    }
  }
  if (lo === Infinity) { lo = 0; hi = 1; }
  if (lo === hi) { lo -= 1; hi += 1; }
  const pd = (hi - lo) * (pad == null ? 0.08 : pad);
  return [lo - pd, hi + pd];
}

/* chart(): one x-index-based panel. Options:
 * w,h,padL,padR,padT,padB, n (point count), y0,y1, yf(v) tick format,
 * bands [{a,b,c,op}] horizontal tint bands, hl [{y,c,d,t}] reference lines,
 * s: series [{t:'line'|'area'|'bars'|'dots', v|p, c, w, d, op, r}],
 * xt [{i,t}] x tick labels, grp: crosshair group name, first: top panel flag
 */
function chart(o) {
  const w = o.w || 880, h = o.h, padL = o.padL == null ? 48 : o.padL;
  const padR = o.padR == null ? 14 : o.padR, padT = o.padT == null ? 8 : o.padT;
  const padB = o.padB == null ? (o.xt ? 22 : 6) : o.padB;
  const pw = w - padL - padR, ph = h - padT - padB;
  const n = Math.max(2, o.n || 2);
  const X = (i) => padL + (i / (n - 1)) * pw;
  const Y = (v) => padT + (1 - (v - o.y0) / ((o.y1 - o.y0) || 1)) * ph;
  // `extra` is painted first: context behind the data, never on top of it.
  // Used for the state bands, which have to sit behind every stacked field
  // so one glance answers "what was going on that week".
  let g = o.extra || "";

  for (const b of (o.bands || [])) {
    const y1 = Y(Math.min(o.y1, Math.max(o.y0, b.b)));
    const y2 = Y(Math.min(o.y1, Math.max(o.y0, b.a)));
    g += `<rect x="${padL}" y="${y1}" width="${pw}" height="${Math.max(0, y2 - y1)}" fill="${b.c}" opacity="${b.op == null ? 0.1 : b.op}"/>`;
  }
  const yt = o.yticks || tickVals(o.y0, o.y1, o.ym || 3);
  for (const v of yt) {
    if (v < o.y0 || v > o.y1) continue;
    g += `<line x1="${padL}" x2="${w - padR}" y1="${Y(v)}" y2="${Y(v)}" stroke="${C.line}" stroke-width="1" opacity="0.55"/>`;
    g += `<text x="${padL - 7}" y="${Y(v) + 3.5}" text-anchor="end" class="ax">${(o.yf || fmt)(v)}</text>`;
  }
  for (const l of (o.hl || [])) {
    if (l.y < o.y0 || l.y > o.y1) continue;
    g += `<line x1="${padL}" x2="${w - padR}" y1="${Y(l.y)}" y2="${Y(l.y)}" stroke="${l.c}" stroke-width="1.2" ${l.d ? 'stroke-dasharray="5 4"' : ""} opacity="0.8"/>`;
    if (l.t) {
      // Two labels on nearby lines used to sit on top of each other; each line
      // can now claim the left or the right end of its own row.
      const left = l.side === "left";
      g += `<text x="${left ? padL + 3 : w - padR - 3}" y="${Y(l.y) - 4}" text-anchor="${left ? "start" : "end"}" class="ax" fill="${l.c}">${l.t}</text>`;
    }
  }
  for (const s of (o.s || [])) {
    if (s.t === "bars") {
      const bw = Math.max(1.4, (pw / n) * 0.68);
      for (let i = 0; i < n; i++) {
        const v = s.v[i];
        if (v == null || v <= o.y0) continue;
        g += `<rect x="${X(i) - bw / 2}" y="${Y(v)}" width="${bw}" height="${Math.max(0.8, Y(Math.max(o.y0, 0)) - Y(v))}" rx="1" fill="${s.c}" opacity="${s.op == null ? 0.85 : s.op}"/>`;
      }
    } else if (s.t === "dots") {
      for (const p of (s.p || [])) {
        if (p.v == null) continue;
        const r = p.r || 3.4, op = p.op == null ? 1 : p.op;
        // A point that carries an id can be brushed. The handlers reach it
        // through these attributes instead of rebuilding the view on every
        // pointer move - a re-render would fight the pointer it follows.
        const tag = p.id ? ` data-dot="${esc(String(p.id))}" data-r="${r}" data-op="${op}"` : "";
        g += `<circle cx="${X(p.i)}" cy="${Y(p.v)}" r="${r}" fill="${p.f === false ? "none" : (p.c || s.c)}" stroke="${p.c || s.c}" stroke-width="1.6" opacity="${op}"${tag}/>`;
        // the ring is a shape, not a second colour - WCAG 1.4.1, and the same
        // rule that gives every state its own icon form
        if (p.ring) {
          g += `<circle class="pickring" cx="${X(p.i)}" cy="${Y(p.v)}" r="${r + 4}" fill="none" stroke="${p.c || s.c}" stroke-width="1.8" opacity="0.95"/>`;
        }
      }
    } else {
      const col = s.c || C.tx2;
      let dPath = "", seg = 0, singles = "";
      let firstX = null, lastX = null, sx = 0, sy = 0;
      for (let i = 0; i < n; i++) {
        const v = s.v[i];
        if (v == null) {
          if (seg === 1) singles += `<circle cx="${sx}" cy="${sy}" r="${(s.w || 2) * 0.9}" fill="${col}"/>`;
          seg = 0; continue;
        }
        sx = +X(i).toFixed(1); sy = +Y(v).toFixed(1);
        dPath += `${seg ? "L" : "M"}${sx} ${sy}`;
        if (firstX == null) firstX = X(i);
        lastX = X(i);
        seg++;
      }
      if (seg === 1) singles += `<circle cx="${sx}" cy="${sy}" r="${(s.w || 2) * 0.9}" fill="${col}"/>`;
      if (!dPath) continue;
      if (s.t === "area") {
        const base = Y(Math.max(o.y0, 0)).toFixed(1);
        g += `<path d="${dPath}L${lastX.toFixed(1)} ${base}L${firstX.toFixed(1)} ${base}Z" fill="${col}" opacity="${s.op == null ? 0.13 : s.op}"/>`;
      }
      g += `<path d="${dPath}" fill="none" stroke="${col}" stroke-width="${s.w || 2}" ${s.d ? `stroke-dasharray="${s.d}"` : ""} opacity="${s.lop == null ? 1 : s.lop}" stroke-linejoin="round" stroke-linecap="round"/>${singles ? `<g opacity="${s.lop == null ? 1 : s.lop}">${singles}</g>` : ""}`;
    }
  }
  // short marks on the baseline: a label every other tick reads as a scale,
  // a label on every tick reads as a wall of numbers
  for (const i of (o.xtick || [])) {
    g += `<line x1="${X(i)}" x2="${X(i)}" y1="${padT + ph}" y2="${padT + ph + 4}" stroke="${C.line}" stroke-width="1"/>`;
  }
  for (const x of (o.xt || [])) {
    g += `<text x="${X(x.i)}" y="${h - 6}" text-anchor="middle" class="ax">${x.t}</text>`;
  }
  // Direct labels sit ON the line they name. A legend forces the eye to travel
  // between two places and hold the mapping in memory; putting the name where
  // the data is removes that search entirely.
  for (const tag of (o.tags || [])) {
    if (tag.v == null) continue;
    const tx = Math.min(X(tag.i), w - padR - 4);
    g += `<text x="${tx}" y="${(Y(tag.v) + (tag.dy || -5)).toFixed(1)}" text-anchor="end"
      class="tag" fill="${tag.c}">${tag.t}</text>`;
  }
  const xh = o.grp ? `<line class="xh" x1="-9" x2="-9" y1="${padT}" y2="${padT + ph}" stroke="${C.tx2}" stroke-width="1" stroke-dasharray="3 3" opacity="0"/>` : "";
  const lbl = o.label ? `<text x="${padL + 2}" y="${padT + 12}" class="pl" fill="${o.labelc || C.tx2}">${o.label}</text>` : "";
  return `<svg class="ch" viewBox="0 0 ${w} ${h}" preserveAspectRatio="none" data-n="${n}" data-padl="${padL}" data-padr="${padR}" data-w="${w}">${g}${lbl}${xh}</svg>`;
}

/* sparkline: tiny inline trend, nulls become gaps */
function spark(vals, o) {
  o = o || {};
  const w = o.w || 240, h = o.h || 46, pad = 4;
  const clean = vals.filter((v) => v != null);
  if (clean.length < 2) return `<div class="nospark">kein Verlauf verfügbar</div>`;
  let lo = Math.min(...clean), hi = Math.max(...clean);
  if (o.zero) { lo = Math.min(lo, 0); hi = Math.max(hi, 0); }
  if (lo === hi) { lo -= 1; hi += 1; }
  const sp = (hi - lo) * 0.1; lo -= sp; hi += sp;
  const n = vals.length;
  const X = (i) => pad + (i / (n - 1)) * (w - 2 * pad);
  const Y = (v) => pad + (1 - (v - lo) / (hi - lo)) * (h - 2 * pad);
  let g = "";
  if (o.band) {
    const a = Math.max(lo, o.band.a), b = Math.min(hi, o.band.b);
    if (b > a) g += `<rect x="${pad}" y="${Y(b)}" width="${w - 2 * pad}" height="${Y(a) - Y(b)}" fill="${C.blue}" opacity="0.12"/>`;
  }
  if (o.hline != null && o.hline >= lo && o.hline <= hi) {
    g += `<line x1="${pad}" x2="${w - pad}" y1="${Y(o.hline)}" y2="${Y(o.hline)}" stroke="${C.tx3}" stroke-dasharray="3 3" stroke-width="1"/>`;
  }
  if (o.bars) {
    const bw = Math.max(1.2, ((w - 2 * pad) / n) * 0.6);
    for (let i = 0; i < n; i++) {
      if (vals[i] == null) continue;
      g += `<rect x="${X(i) - bw / 2}" y="${Y(vals[i])}" width="${bw}" height="${Math.max(1, Y(Math.max(lo, 0)) - Y(vals[i]))}" fill="${o.c || C.blue}" opacity="0.8"/>`;
    }
  } else {
    let dPath = "", seg = 0, singles = "", sx = 0, sy = 0;
    for (let i = 0; i < n; i++) {
      const v = vals[i];
      if (v == null) {
        if (seg === 1) singles += `<circle cx="${sx}" cy="${sy}" r="1.7" fill="${o.c || C.blue}"/>`;
        seg = 0; continue;
      }
      sx = +X(i).toFixed(1); sy = +Y(v).toFixed(1);
      dPath += `${seg ? "L" : "M"}${sx} ${sy}`;
      seg++;
    }
    if (seg === 1) singles += `<circle cx="${sx}" cy="${sy}" r="1.7" fill="${o.c || C.blue}"/>`;
    g += `<path d="${dPath}" fill="none" stroke="${o.c || C.blue}" stroke-width="1.8" stroke-linejoin="round"/>${singles}`;
  }
  let li = n - 1; while (li >= 0 && vals[li] == null) li--;
  if (li >= 0 && !o.bars) g += `<circle cx="${X(li)}" cy="${Y(vals[li])}" r="3" fill="${o.last || o.c || C.blue}"/>`;
  return `<svg class="spk" viewBox="0 0 ${w} ${h}" preserveAspectRatio="none">${g}</svg>`;
}

/* Fixed readout strip above a chart group. A floating box next to the cursor
 * went wrong twice - first clamped against a fixed width, then against the
 * wrong frame - and it covers the very data it describes. A fixed strip has
 * no frame to get wrong: it sits in the card, updates in place, and holds
 * still while the eye moves. intervals.icu itself reads out the same way. */
function readout(group) {
  return `<div class="rdo" data-rdo="${group}">
    <span class="rdox">—</span><span class="rdov"></span>
  </div>`;
}

/* ------------------------------------------------------------------ */
/* Time window - a component, not a DFA special case. Fitness and       */
/* Belastung want the same picker, and a second copy of this logic      */
/* would be a second way to answer "which readings am I looking at".    */
/*                                                                      */
/* The pattern is Grafana's: a handful of relative quick ranges plus one */
/* explicit range in YYYY-MM-DD. Relative is not absolute, and the card  */
/* says so - a chip means "now minus three months", and that moves every */
/* night, while a typed range is frozen.                                 */
/* ------------------------------------------------------------------ */
const WIN_VERSION = "v1";                       // bump when the shape changes
const WIN_DEFAULT = "3m";
const WINDOWS = [
  { id: "42d", label: "42 T", days: 42, word: "die letzten 42 Tage" },
  { id: "3m", label: "3 M", days: 91, word: "die letzten drei Monate" },
  { id: "6m", label: "6 M", days: 182, word: "die letzten sechs Monate" },
  { id: "12m", label: "12 M", days: 365, word: "die letzten zwölf Monate" },
  { id: "all", label: "alles", days: null, word: "der gesamte Bestand" },
  { id: "custom", label: "eigener Zeitraum", days: null, word: "ein fester Zeitraum" },
];
function winDef(id) {
  return WINDOWS.find((w) => w.id === id) || WINDOWS.find((w) => w.id === WIN_DEFAULT);
}
function isoMinus(iso, days) {
  const t = Date.parse(String(iso).slice(0, 10) + "T00:00:00Z");
  if (Number.isNaN(t)) return null;
  return new Date(t - days * 864e5).toISOString().slice(0, 10);
}
/* The bounds of a window. Relative windows have NO upper bound on purpose: a
   reading dated tomorrow - a watch with a wrong clock - would otherwise drop
   out of every view without a word, and silent disappearance is the defect
   that cost 0.30.0 a release. */
function winRange(win, nowIso) {
  const def = winDef(win && win.id);
  if (def.id === "custom") return { from: (win && win.from) || null, to: (win && win.to) || null };
  if (def.days == null) return { from: null, to: null };
  return { from: isoMinus(nowIso, def.days), to: null };
}
/* Filter rows (each with a .date) to the window. Returns the kept rows plus
   the counts, because "14 von 49" is what makes a filtered list honest. */
function winApply(rows, win, nowIso) {
  const list = rows || [];
  const { from, to } = winRange(win, nowIso);
  const kept = list.filter((r) => {
    const d = String((r && r.date) || "").slice(0, 10);
    if (!d) return false;
    if (from && d < from) return false;
    if (to && d > to) return false;
    return true;
  });
  return { rows: kept, from, to, kept: kept.length, total: list.length };
}
/* localStorage is a convenience, never a requirement: Safari's private mode
   throws on WRITE, a panel rendered outside a browser has no localStorage at
   all, and neither may take the view down with it. */
function winRemember(view, win) {
  try {
    if (typeof localStorage === "undefined" || !localStorage) return;
    localStorage.setItem(`intervals_icu.window.${WIN_VERSION}.${view}`, JSON.stringify(win));
  } catch (err) { /* nothing remembered, everything still works */ }
}
function winRecall(view) {
  try {
    if (typeof localStorage === "undefined" || !localStorage) return null;
    const raw = localStorage.getItem(`intervals_icu.window.${WIN_VERSION}.${view}`);
    if (!raw) return null;
    const win = JSON.parse(raw);
    return win && winDef(win.id).id === win.id ? win : null;
  } catch (err) { return null; }
}
/* Radio group, not six buttons: one tab stop, arrows move the choice. That is
   what a set of mutually exclusive options is, and screen readers read it as
   one control instead of six unrelated ones. */
function winChips(view, win, nowIso) {
  const cur = winDef(win && win.id);
  const { from, to } = winRange(win, nowIso);
  const chips = WINDOWS.map((w) => `<button role="radio" class="chipbtn ${w.id === cur.id ? "on" : ""}"
      aria-checked="${w.id === cur.id}" tabindex="${w.id === cur.id ? 0 : -1}"
      data-act="win" data-view="${esc(view)}" data-id="${w.id}">${w.label}</button>`).join("");
  const note = cur.id === "custom"
    ? `fester Zeitraum ${from ? dMed(from) : "offen"} – ${to ? dMed(to) : "offen"}, eingefroren`
    : cur.days == null
      ? "der gesamte Bestand"
      : `${cur.word}, also ab ${dMed(from)} — relativ, verschiebt sich täglich`;
  const fields = cur.id === "custom"
    ? `<span class="winfields">
        <input type="date" class="wind" data-act="winfrom" data-view="${esc(view)}" value="${from || ""}">
        <span class="mut">bis</span>
        <input type="date" class="wind" data-act="winto" data-view="${esc(view)}" value="${to || ""}">
      </span>` : "";
  return `<div class="winpick">
    <div class="chips" role="radiogroup" aria-label="Zeitraum" data-winview="${esc(view)}">${chips}</div>
    ${fields}
    <span class="winnote">${esc(note)}</span>
  </div>`;
}

/* moving average that ignores nulls, window win */
function movAvg(vals, win) {
  if (win <= 1) return vals.slice();
  const out = new Array(vals.length).fill(null);
  for (let i = 0; i < vals.length; i++) {
    let s = 0, k = 0;
    for (let j = Math.max(0, i - win + 1); j <= i; j++) {
      if (vals[j] != null) { s += vals[j]; k++; }
    }
    out[i] = k ? s / k : null;
  }
  return out;
}
function rollMedian(vals, win) {
  const out = new Array(vals.length).fill(null);
  for (let i = 0; i < vals.length; i++) {
    const chunk = [];
    for (let j = Math.max(0, i - win + 1); j <= i; j++) {
      if (vals[j] != null) chunk.push(vals[j]);
    }
    out[i] = chunk.length >= 2 ? median(chunk) : vals[i];
  }
  return out;
}

/* readiness ring: one arc segment per signal, coloured by its state */
function ring(components, overall) {
  const size = 200, cx = 100, cy = 100, r = 80, sw = 15;
  const m = ST[overall] || ST.unknown;
  const nSeg = components.length || 1;
  const gap = 7, span = (360 - nSeg * gap) / nSeg;
  const P = (ang) => {
    const a = (ang - 90) * Math.PI / 180;
    return [cx + r * Math.cos(a), cy + r * Math.sin(a)];
  };
  let segs = "";
  components.forEach((cItem, i) => {
    const a0 = i * (span + gap) + gap / 2, a1 = a0 + span;
    const [x0, y0] = P(a0), [x1, y1] = P(a1);
    const col = (ST[cItem.state] || ST.unknown).c;
    segs += `<path d="M${x0.toFixed(1)} ${y0.toFixed(1)} A${r} ${r} 0 ${span > 180 ? 1 : 0} 1 ${x1.toFixed(1)} ${y1.toFixed(1)}" fill="none" stroke="${col}" stroke-width="${sw}" stroke-linecap="round" opacity="${cItem.state === "unknown" ? 0.35 : 0.95}"><title>${esc(cItem.label)}: ${(ST[cItem.state] || ST.unknown).word}</title></path>`;
  });
  return `<svg class="ring" viewBox="0 0 ${size} ${size}" role="img" aria-label="Bereitschaft: ${m.word}">
    <circle cx="${cx}" cy="${cy}" r="${r}" fill="none" stroke="${C.line}" stroke-width="${sw}" opacity="0.35"/>
    ${segs}
    <g transform="translate(${cx - 16},${cy - 30})"><svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="${m.c}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">${IC[m.ic]}</svg></g>
    <text x="${cx}" y="${cy + 22}" text-anchor="middle" class="ringword" fill="${m.c}">${m.word}</text>
    <text x="${cx}" y="${cy + 42}" text-anchor="middle" class="ringsub" fill="${C.tx3}">${components.filter((s) => s.state !== "unknown").length} von ${nSeg} Signalen</text>
  </svg>`;
}

/* bullet graph for the load budget (Few's gauge replacement) */
function bullet(b) {
  const w = 880, h = 92, padL = 8, padR = 16, y = 30, bh = 18;
  const top = Math.max(b.risk_top * 1.12, b.recommended * 1.15, 10);
  const X = (v) => padL + (Math.min(v, top) / top) * (w - padL - padR);
  const stc = (ST[b.state] || ST.unknown).c;
  const zone = (a, bb, col, op) =>
    `<rect x="${X(a)}" y="${y}" width="${Math.max(0, X(bb) - X(a))}" height="${bh}" fill="${col}" opacity="${op}"/>`;
  const mark = (v, label, col) => `
    <line x1="${X(v)}" x2="${X(v)}" y1="${y - 8}" y2="${y + bh + 8}" stroke="${col || C.tx2}" stroke-width="2"/>
    <text x="${X(v)}" y="${y + bh + 24}" text-anchor="middle" class="ax" fill="${col || C.tx2}">${label} ${fmt(v)}</text>`;
  return `<svg class="ch" viewBox="0 0 ${w} ${h}" preserveAspectRatio="none" role="img" aria-label="Belastungsbudget heute: ${fmt(b.recommended)} Punkte">
    ${zone(0, b.corridor_top, C.tx3, 0.14)}
    ${zone(b.corridor_top, b.risk_top, C.amber, 0.14)}
    ${zone(b.risk_top, top, C.red, 0.14)}
    <rect x="${X(0)}" y="${y + 3}" width="${Math.max(2, X(b.recommended) - X(0))}" height="${bh - 6}" rx="2" fill="${stc}"/>
    <text x="${Math.min(X(b.recommended) + 8, w - 90)}" y="${y + bh - 4}" class="bval" fill="${stc}">${fmt(b.recommended)}</text>
    ${mark(b.steady, "gleichbleibend", C.tx2)}
    ${mark(b.corridor_top, "Korridor bis", C.amber)}
    ${mark(b.risk_top, "Risiko ab", C.red)}
  </svg>`;
}

/* ------------------------------------------------------------------ */
/* the panel                                                           */
/* ------------------------------------------------------------------ */
const TABS = [
  ["trainer", "Trainer"],
  ["signale", "Signale"],
  ["heute", "Heute"], ["kalender", "Kalender"], ["fitness", "Fitness"],
  ["akt", "Aktivitäten"], ["belastung", "Belastung"], ["dfa", "DFA"],
];
const VERDICT = {
  green: "grün — normal trainieren.",
  amber: "gelb — Umfang ja, Intensität dosieren.",
  red: "rot — heute leicht trainieren oder pausieren.",
  unknown: "noch zu wenige Daten für eine Einschätzung.",
};
const FIELD_LABEL = {
  goal: "das Ziel", days_per_week: "Tage pro Woche", hours_per_week: "Stunden pro Woche",
  target_hours: "die Zieldauer",
};
const STATE_WORD = {
  slump: "Einbruch", recovering: "noch im Einbruch", rebound: "Erholung nach Einbruch",
  strained: "beansprucht", ready: "Normalbereich", unknown: "keine Daten",
};
const SIG_ICON = { hrv: "heart", rhr: "pulse", sleep: "moon", form: "gauge", acwr: "trend", monotony: "wave", subjective: "user" };
const SIG_UNIT = { hrv: "ln rMSSD", rhr: "bpm", sleep: "h", form: "%", acwr: "", monotony: "", subjective: "/ 4" };
const SIG_DEC = { hrv: 3, rhr: 0, sleep: 2, form: 1, acwr: 2, monotony: 2, subjective: 0 };

class IntervalsIcuPanel extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._tab = "trainer";
    this._grp = {};
    this._range = 182;
    this._weeks = 12;
    this._dfaSport = "all";
    this._streams = {};
    this._laps = {};
    this._sigDays = 180;
    this._sigMode = "stack";
    this._sigFocus = null;
    this._woOpen = null;
    this._cmpFocus = null;
    this._night = {};
    this._goal = null;
    this._today = null;
    this._sigOpen = null;
    this._goalEdit = false;
    this._goalDraft = null;
    this._ctx = {};
    this._booted = false;
    // one window state per view, so Fitness and Belastung can join later
    this._win = { dfa: winRecall("dfa") || { id: WIN_DEFAULT } };
    this._dfaPick = null;    // fixed selection (click)
    this._dfaHover = null;   // transient selection (pointer)
    this._nowIso = null;     // tests pin "today"; production reads the clock
  }

  /* One "now" for the whole panel. The tests pin it, because a window that
     asks the wall clock makes the suite go red on its own some months from
     now - and a test that fails for calendar reasons teaches nothing. */
  _now() {
    return this._nowIso || new Date().toISOString().slice(0, 10);
  }

  set hass(h) {
    this._hass = h;
    if (!this._booted) { this._booted = true; this._boot(); }
  }
  get hass() { return this._hass; }

  _ws(type, extra) {
    return this._hass.connection.sendMessagePromise(
      Object.assign({ type: `intervals_icu/${type}` }, extra || {})
    );
  }

  async _boot() {
    this.shadowRoot.innerHTML = this._skeleton();
    this._view = this.shadowRoot.getElementById("view");
    this._attach();
    try {
      const [status, rd, days, load, coachData] = await Promise.all([
        this._ws("status"), this._ws("readiness"),
        this._ws("days", { weeks: this._weeks }), this._ws("load"), this._ws("coach"),
      ]);
      this._ws("workouts").then((w) => { this._workouts = w; if (this._tab === "trainer") this._render(); });
      this._status = status; this._rd = rd; this._days = days; this._load = load;
      this._coach = coachData;
      this._err = null;
    } catch (err) {
      this._err = String(err && err.message || err);
    }
    this._render();
    this._routeFromHash();
  }

  async _need(what) {
    try {
      if (what === "coach" && !this._coach) this._coach = await this._ws("coach");
      if (what === "workouts" && !this._workouts) this._workouts = await this._ws("workouts");
      if (what === "goal" && !this._goal) this._goal = await this._ws("goal");
      if (what === "today" && !this._today) this._today = await this._ws("today");
      if (what === "signals" && !this._signals) {
        this._signals = await this._ws("signals", { days: this._sigDays });
      }
      if (what === "pmc" && !this._pmc) this._pmc = await this._ws("pmc");
      if (what === "akt" && !this._acts) this._acts = await this._ws("activities", { limit: 300 });
      if (what === "thr" && !this._thr) this._thr = await this._ws("thresholds");
      if (what === "cal" && !this._cal) this._cal = await this._ws("calendar");
    } catch (err) {
      this._err = String(err && err.message || err);
    }
  }

  async _setTab(t) {
    this._tab = t;
    // parallel, not one after the other: three round trips in sequence is the
    // difference between "instant" and "why is this still loading"
    if (t === "trainer") {
      await Promise.all([this._need("coach"), this._need("workouts"), this._need("goal")]);
    }
    if (t === "heute") await this._need("today");
    if (t === "signale") await this._need("signals");
    if (t === "fitness") await this._need("pmc");
    if (t === "akt") await this._need("akt");
    if (t === "dfa") await this._need("thr");
    this._render();
  }

  async _openAct(id) {
    this._tab = "akt";
    await this._need("akt");
    this._sel = (this._acts || []).find((a) => String(a.id) === String(id)) || null;
    // The activity list reaches 300 sessions back; a threshold reading can be
    // older. Silently landing on an unfiltered list would look like the click
    // did nothing - say what happened instead.
    this._aktMiss = this._sel ? null : String(id);
    this._render();
    if (this._sel && !this._streams[id]) {
      const [st, lp, ni, cx] = await Promise.allSettled([
        this._ws("streams", { activity_id: String(id) }),
        this._ws("laps", { activity_id: String(id) }),
        this._ws("night", { activity_id: String(id) }),
        this._ws("context", { activity_id: String(id) }),
      ]);
      this._streams[id] = st.status === "fulfilled"
        ? st.value : { error: String(st.reason && st.reason.message || st.reason) };
      this._laps[id] = lp.status === "fulfilled"
        ? lp.value : { error: String(lp.reason && lp.reason.message || lp.reason) };
      this._night[id] = ni.status === "fulfilled"
        ? ni.value : { available: false, reason: String(ni.reason && ni.reason.message || ni.reason) };
      this._ctx[id] = cx.status === "fulfilled" ? cx.value : { available: false };
      if (this._sel && String(this._sel.id) === String(id)) this._render();
    }
  }

  /* ---------------- shell ---------------- */
  _skeleton() {
    return `<style>${this._css()}</style>
    <div id="app">
      <header>
        <div class="brand">Intervals.icu</div>
        <div id="hstat" class="hstat"></div>
      </header>
      <nav id="tabs"></nav>
      <div id="view"><div class="card pad">Lade Daten …</div></div>
    </div>`;
  }

  _render() {
    const tabs = this.shadowRoot.getElementById("tabs");
    tabs.innerHTML = TABS.map(([id, l]) =>
      `<button class="tab ${this._tab === id ? "on" : ""}" data-act="tab" data-id="${id}">${l}</button>`
    ).join("");
    const hs = this.shadowRoot.getElementById("hstat");
    const s = this._status;
    hs.innerHTML = s
      ? `${s.importing ? '<span class="pulse">Import läuft …</span> · ' : ""}${fmt(s.activities)} Einheiten · ${fmt(s.wellness_days)} Tage · ${fmt(s.dfa_done)} DFA${s.athlete ? " · " + esc(s.athlete) : ""}`
      : "";
    this._grp = {};
    let html = "";
    if (this._err && !this._rd) {
      html = `<div class="card pad err">Daten konnten nicht geladen werden: ${esc(this._err)}</div>`;
    } else if (this._tab === "trainer") {
      html = this.rGoal(this._goal) + this.rTrainer(this._coach, this._rd) + this.rPlanWeeks(this._goal);
    }
    else if (this._tab === "signale") html = this.rSignale(this._signals);
    else if (this._tab === "heute") html = this.rHeute(this._today);
    else if (this._tab === "kalender") html = this.rKalender(this._days);
    else if (this._tab === "fitness") html = this.rFitness(this._pmc, this._range);
    else if (this._tab === "akt") html = this.rAkt(this._acts, this._sel);
    else if (this._tab === "belastung") html = this.rBelastung(this._load);
    else if (this._tab === "dfa") html = this.rDfa(this._thr, this._dfaSport);
    this._view.innerHTML = html;
    // the strip must carry the newest values before anyone moves a mouse -
    // and on a touch screen nobody ever does
    for (const name of Object.keys(this._grp)) this._fillReadout(name, null);
    // innerHTML threw the marks away with the old nodes; the FIXED selection
    // has to survive a re-render, or clicking a row would clear the very
    // mark the click just set.
    this._dfaHover = null;
    this._paintDfa();
  }

  /* ---------------- events ---------------- */
  _attach() {
    const root = this.shadowRoot;
    root.addEventListener("click", (e) => {
      const el = e.target.closest("[data-act]");
      if (!el) return;
      const act = el.dataset.act, id = el.dataset.id;
      if (act === "tab") this._setTab(id);
      else if (act === "range") { this._range = +id; this._render(); }
      else if (act === "weeks") {
        this._weeks = +id; this._days = null;
        this._ws("days", { weeks: this._weeks }).then((d) => { this._days = d; this._render(); });
        this._render();
      }
      else if (act === "act") this._openAct(id);
      else if (act === "close") { this._sel = null; this._render(); }
      else if (act === "dfasport") { this._dfaSport = id; this._render(); }
      else if (act === "sigdays") {
        this._sigDays = +id; this._signals = null;
        this._ws("signals", { days: this._sigDays }).then((s) => { this._signals = s; this._render(); });
        this._render();
      }
      else if (act === "sigmode") { this._sigMode = id; this._render(); }
      else if (act === "plan") {
        const when = el.dataset.when;
        el.disabled = true;
        const before = el.textContent;
        el.textContent = "wird eingetragen …";
        this._ws("plan_workout", { workout: id, date: when, sport: "Ride" })
          .then((r) => { el.textContent = `im Kalender: ${dShort(r.date)}`; el.classList.add("done"); })
          .catch((e) => {
            el.disabled = false;
            el.textContent = before;
            this._toast(`Eintragen fehlgeschlagen: ${String(e && e.message || e)}`);
          });
      }
      else if (act === "wodetail") {
        this._woOpen = (this._woOpen === id ? null : id); this._render();
      }
      else if (act === "goaledit") {
        this._goalDraft = {};   // start clean: two questions, not a filled form
        this._goalEdit = true; this._render();
      }
      else if (act === "goalcancel") { this._goalEdit = false; this._render(); }
      else if (act === "goalpick") {
        this._goalDraft = { ...(this._goalDraft || {}), goal: id || null }; this._render();
      }
      else if (act === "goaldays") {
        this._goalDraft = { ...(this._goalDraft || {}), days_per_week: Number(id) };
        this._render();
      }
      else if (act === "goalsave") {
        const draft = { ...(this._goalDraft || {}) };
        if (!draft.goal || !draft.days_per_week) return;
        el.disabled = true; el.textContent = "wird erstellt …";
        this._ws("set_goal", { profile: draft })
          .then((r) => {
            this._goal = { ...(this._goal || {}), ...r };
            this._goalEdit = false; this._workouts = null; this._render();
            this._ws("workouts").then((w) => { this._workouts = w; this._render(); });
          })
          .catch((e) => { el.disabled = false; this._toast(`Speichern fehlgeschlagen: ${String(e && e.message || e)}`); });
      }
      else if (act === "planweeks") { this._planOpen = (this._planOpen === id ? null : id); this._render(); }
      else if (act === "sigopen") {
        this._sigOpen = (this._sigOpen === id ? null : id); this._render();
      }
      else if (act === "cmpzoom") {
        this._cmpFocus = (this._cmpFocus === id ? null : id); this._render();
      }
      else if (act === "sigfocus") {
        this._sigFocus = (this._sigFocus === id ? null : id); this._render();
      }
      else if (act === "win") this._setWin(el.dataset.view, { id });
      // A fixed pick is a toggle, and it is undoable: the known weakness of
      // brushing is that the selection is purely visual and the way out is
      // not discoverable, so the card also carries a visible "Auswahl
      // aufheben".
      else if (act === "dfapick") {
        this._dfaPick = (this._dfaPick === id ? null : id);
        this._render();
      }
      else if (act === "dfaclear") { this._dfaPick = null; this._render(); }
      else if (act === "gotoact") this._goActivity(id);
    });
    // typed range: the input event carries the value, not a data-id
    root.addEventListener("change", (e) => {
      const el = e.target.closest && e.target.closest("[data-act]");
      if (!el) return;
      const view = el.dataset.view;
      if (el.dataset.act === "winfrom" || el.dataset.act === "winto") {
        const cur = this._win[view] || { id: WIN_DEFAULT };
        const next = { id: "custom", from: cur.from || null, to: cur.to || null };
        next[el.dataset.act === "winfrom" ? "from" : "to"] = el.value || null;
        this._setWin(view, next);
      }
    });
    // arrow keys inside the radio group - that is what a radio group is
    root.addEventListener("keydown", (e) => {
      const group = e.target.closest && e.target.closest("[role=radiogroup][data-winview]");
      if (!group) return;
      const step = e.key === "ArrowRight" || e.key === "ArrowDown" ? 1
        : e.key === "ArrowLeft" || e.key === "ArrowUp" ? -1 : 0;
      if (!step) return;
      e.preventDefault();
      const view = group.dataset.winview;
      const cur = WINDOWS.findIndex((w) => w.id === winDef((this._win[view] || {}).id).id);
      const next = WINDOWS[(cur + step + WINDOWS.length) % WINDOWS.length];
      this._setWin(view, { id: next.id });
    });
    root.addEventListener("pointermove", (e) => {
      // a row under the pointer brushes its point in the graph
      const row = e.target.closest && e.target.closest("[data-aid]");
      if (row) { this._brush(row.dataset.aid); return; }
      const g = e.target.closest && e.target.closest("[data-grp]");
      if (!g) { this._xhHide(); this._brush(null); return; }
      const idx = this._xhMove(g, e);
      if (g.dataset.grp === "dfa") {
        if (this._drag) this._dragTo(g, idx);
        else this._brush(this._dfaIdToIdx(idx));
      }
    });
    root.addEventListener("pointerleave", () => { this._xhHide(); this._brush(null); }, true);
    // Dragging a range in the graph is the cheapest route to a free window and
    // needs no date-picker widget. Double click puts it back.
    root.addEventListener("pointerdown", (e) => {
      const g = e.target.closest && e.target.closest('[data-grp="dfa"]');
      if (!g) return;
      const idx = this._xhMove(g, e);
      if (idx == null) return;
      this._drag = { from: idx, to: idx };
      this._dragTo(g, idx);
    });
    root.addEventListener("pointerup", () => {
      const drag = this._drag;
      this._drag = null;
      if (!drag || Math.abs(drag.to - drag.from) < 2) { this._dragPaint(null); return; }
      const rows = this._dfaRows || [];
      const a = rows[Math.min(drag.from, drag.to)], b = rows[Math.max(drag.from, drag.to)];
      if (!a || !b) { this._dragPaint(null); return; }
      this._setWin("dfa", { id: "custom", from: a.date, to: b.date });
    });
    root.addEventListener("dblclick", (e) => {
      const g = e.target.closest && e.target.closest('[data-grp="dfa"]');
      if (g) this._setWin("dfa", { id: WIN_DEFAULT });
    });
    // the back button and a shared link, for one listener
    try {
      if (typeof window !== "undefined" && window && window.addEventListener) {
        window.addEventListener("hashchange", () => this._routeFromHash());
      }
    } catch (err) { /* no browser, no routing - the panel still works */ }
  }

  _setWin(view, win) {
    if (!view) return;
    this._win[view] = win;
    winRemember(view, win);
    this._render();
  }

  /* transient selection: DOM only, never a re-render. A pointer move that
     rebuilds the view would fight the pointer it is following. */
  _brush(id) {
    if (this._dfaHover === id) return;
    this._dfaHover = id;
    this._paintDfa();
  }

  _dfaIdToIdx(idx) {
    const rows = this._dfaRows || [];
    const row = idx == null ? null : rows[idx];
    // a reading without a usable value is drawn hollow and stays unpickable
    return row && row.pickable ? row.activity_id : null;
  }

  /* Transient marking only. The FIXED pick is rendered (see rDfa), so this
     handles the hover and puts everything back to the rendered state when the
     pointer leaves - the values to go back to travel on the element itself. */
  _paintDfa() {
    const root = this.shadowRoot;
    if (!root || !root.querySelectorAll) return;
    const mark = this._dfaHover;
    const dots = root.querySelectorAll("[data-dot]");
    (dots.forEach ? dots : []).forEach((el) => {
      const rendered = { r: el.dataset.r || "4", op: el.dataset.op || "1" };
      const hit = mark && el.dataset.dot === mark;
      el.setAttribute("opacity", !mark ? rendered.op : (hit ? "1" : "0.35"));
      el.setAttribute("r", hit ? String(+rendered.r + 2) : rendered.r);
      el.setAttribute("stroke-width", hit ? "2.6" : "1.6");
    });
    const rows = root.querySelectorAll("[data-aid]");
    (rows.forEach ? rows : []).forEach((el) => {
      const hit = mark && el.dataset.aid === mark;
      if (el.classList) el.classList.toggle("hovered", !!hit);
      if (hit && el.scrollIntoView) el.scrollIntoView({ block: "nearest" });
    });
  }

  _dragTo(g, idx) {
    if (!this._drag || idx == null) return;
    this._drag.to = idx;
    this._dragPaint(this._drag);
  }

  _dragPaint(drag) {
    const root = this.shadowRoot;
    if (!root || !root.querySelectorAll) return;
    const sels = root.querySelectorAll(".dragsel");
    (sels.forEach ? sels : []).forEach((el) => {
      if (!drag) { el.setAttribute("opacity", "0"); return; }
      const n = Math.max(2, (this._dfaRows || []).length);
      const padL = 48, padR = 14, w = 880, pw = w - padL - padR;
      const x1 = padL + (Math.min(drag.from, drag.to) / (n - 1)) * pw;
      const x2 = padL + (Math.max(drag.from, drag.to) / (n - 1)) * pw;
      el.setAttribute("x", String(x1));
      el.setAttribute("width", String(Math.max(0, x2 - x1)));
      el.setAttribute("opacity", "0.18");
    });
  }

  /* A hash route costs one state variable and buys the back button plus a
     shareable link; Kalender and Heute can use the same road later. */
  _goActivity(id) {
    try {
      if (typeof location !== "undefined" && location) location.hash = `#activities/${id}`;
    } catch (err) { /* no browser - the call below still opens the tab */ }
    this._openAct(id);
  }

  _routeFromHash() {
    try {
      if (typeof location === "undefined" || !location) return;
      const m = /^#activities\/(.+)$/.exec(location.hash || "");
      if (m) this._openAct(decodeURIComponent(m[1]));
    } catch (err) { /* nothing to route */ }
  }

  _xhHide() {
    if (!this._xhOn) return;
    this._xhOn = false;
    this.shadowRoot.querySelectorAll(".xh").forEach((l) => l.setAttribute("opacity", "0"));
    // fall back to the newest value, so the strip is never empty
    for (const name of Object.keys(this._grp || {})) this._fillReadout(name, null);
  }

  /* Write one group's values into its strip. idx null means "latest". */
  _fillReadout(name, idx) {
    const meta = this._grp[name];
    const strip = this.shadowRoot.querySelector(`[data-rdo="${name}"]`);
    if (!meta || !strip) return;
    let i = idx;
    if (i == null) {
      i = meta.n - 1;
      const first = meta.rows[0];
      if (first) while (i > 0 && first.vals[i] == null) i--;
    }
    const xs = strip.querySelector(".rdox"), vs = strip.querySelector(".rdov");
    if (xs) xs.textContent = meta.xl(i) + (idx == null ? " (zuletzt)" : "");
    if (vs) {
      vs.innerHTML = meta.rows.map((r) => {
        const v = r.vals[i];
        return `<span class="rv"><i style="background:${r.c}"></i>${esc(r.l)}
          <b class="tn">${v == null ? "–" : fmt(r.mul ? v * r.mul : v, r.dec || 0)}${r.u ? " " + r.u : ""}</b></span>`;
      }).join("");
    }
  }

  /* Returns the index under the pointer, so brushing and range dragging read
     the same position as the cursor line instead of computing their own. */
  _xhMove(g, e) {
    const name = g.dataset.grp, meta = this._grp[name];
    if (!meta) return null;
    const svg = g.querySelector("svg.ch");
    if (!svg) return null;
    const rect = svg.getBoundingClientRect();
    const W = +svg.dataset.w, padL = +svg.dataset.padl, padR = +svg.dataset.padr;
    const localX = (e.clientX - rect.left) * (W / rect.width);
    const pw = W - padL - padR;
    let idx = Math.round(((localX - padL) / pw) * (meta.n - 1));
    idx = Math.max(0, Math.min(meta.n - 1, idx));
    const px = padL + (idx / (meta.n - 1)) * pw;
    g.querySelectorAll(".xh").forEach((l) => {
      l.setAttribute("x1", px); l.setAttribute("x2", px); l.setAttribute("opacity", "0.9");
    });
    this._fillReadout(name, idx);
    this._xhOn = true;
    return idx;
  }

  _toast(text) {
    const view = this._view;
    if (!view) return;
    const box = document.createElement("div");
    box.className = "toast";
    box.textContent = text;
    view.appendChild(box);
    setTimeout(() => box.remove(), 6000);
  }

  /* A session is a shape, not a word. The bar below draws the actual blocks
     to scale, so "30/15" and "2x20" look as different as they are - and the
     numbers underneath are this athlete's watts, not percentages to convert
     in your head. */
  _woBar(entry, ftp) {
    const blocks = entry.blocks || [];
    const total = blocks.reduce((sum, b) => sum + b[0], 0) || 1;
    const colFor = (pct) => pct < 60 ? C.slate : pct < 76 ? C.cyan
      : pct < 90 ? C.blue : pct < 101 ? C.violet : C.magenta;
    let x = 0;
    const segs = blocks.map(([min, pct, label]) => {
      const w = (min / total) * 100;
      const s = `<i class="wob" style="left:${x}%;width:${Math.max(0.6, w - 0.25)}%;
        height:${Math.max(14, Math.min(100, pct * 0.78))}%;background:${colFor(pct)}"
        title="${esc(label)} · ${min} min · ${ftp ? Math.round(ftp * pct / 100) + " W" : pct + " % FTP"}"></i>`;
      x += w;
      return s;
    }).join("");
    return `<div class="wobar">${segs}</div>`;
  }

  rWorkouts(w, forTomorrow) {
    if (!w) return "";
    const list = w.workouts || [];
    if (!list.length) return "";
    const ftp = w.ftp;
    const today = new Date();
    const iso = (d) => new Date(today.getTime() + d * 86400000).toISOString().slice(0, 10);

    // One logic, not two. The list IS the recommendation: the first card that
    // fits today carries the mark, instead of a second block above computing
    // its own answer that could quietly disagree with this one. And it must
    // fit the BUDGET too - a lead card wearing "über dem Budget" as its own
    // badge would contradict itself on screen.
    let pick = list.findIndex((e) => e.fit === "ok" && e.fits_budget !== false);
    if (pick < 0) pick = list.findIndex((e) => e.fit === "ok");
    const cards = list.map((entry, index) => {
      const open = this._woOpen === entry.key;
      // trained today -> the verdicts speak for tomorrow, from today's state
      const FIT = forTomorrow
        ? { ok: ["green", "passt"], maybe: ["amber", "möglich, kostet aber"],
            no: ["red", "eher nicht"] }
        : { ok: ["green", "passt heute"], maybe: ["amber", "möglich, kostet aber"],
            no: ["red", "heute nicht"] };
      let [fitTone, fitWord] = FIT[entry.fit] || FIT.maybe;
      // the budget is part of the same verdict, not a second one next to it
      if (entry.fit === "ok" && entry.fits_budget === false) {
        fitTone = "amber";
        fitWord = `über dem Budget (${fmt(w.budget)})`;
      }
      const fit = badge(fitTone, fitWord);
      const hrw = entry.hr_window;
      const recommended = index === pick;
      return `<div class="wocard ${recommended ? "first" : ""}">
        ${recommended ? `<div class="recflag">${ico("ok", C.green, 14)}
          das ist die Empfehlung von oben</div>` : ""}
        <div class="wohead">
          <div>
            <div class="wofam">${esc(entry.family_label || "")}</div>
            <div class="wotitle">${esc(entry.title)}</div>
            <div class="wometa">${esc(entry.purpose)} · ${entry.minutes} min · Last ${fmt(entry.load)}${
              hrw ? ` · ${hrw[0]}–${hrw[1]} bpm` : ""}</div>
          </div>
          ${fit}
        </div>
        ${this._woBar(entry, ftp)}
        <div class="wosteps">${(entry.blocks_w || entry.blocks).map(([min, val, label]) =>
          `<span><b>${min}′</b> ${esc(label)} <em>${entry.blocks_w ? val + " W" : val + " % FTP"}</em></span>`).join("")}</div>
        <p class="effect"><b>Was das bringt:</b> ${esc(entry.effect)}</p>
        <p class="evi"><b>Beleg:</b> ${esc(entry.evidence)}</p>
        ${entry.fit_reason ? `<p class="fitwhy">${ico(entry.fit === "no" ? "warn" : "info",
          entry.fit === "no" ? C.red : C.amber, 14)} ${esc(entry.fit_reason)}</p>` : ""}

        <div class="worow">
          <button class="planbtn" data-act="plan" data-id="${esc(entry.key)}" data-when="${iso(0)}">
            ${ico("cal", null, 15)} heute in den Kalender</button>
          <button class="planbtn ghost" data-act="plan" data-id="${esc(entry.key)}" data-when="${iso(1)}">
            morgen</button>
          <button class="chipbtn" data-act="wodetail" data-id="${esc(entry.key)}">
            ${open ? "weniger" : "Aufbau, DFA und Beleg"}</button>
        </div>
        ${open ? `<div class="wodetail">
          <div class="kv2"><small>Schritte, wie sie in Intervals landen</small>
            <pre>${esc(entry.text_w || entry.text)}</pre>
            ${entry.text_w ? "" : `<p class="src">Ohne hinterlegte FTP bleiben Prozente stehen —
              erfundene Wattzahlen wären schlimmer als ehrliche Prozente.</p>`}</div>
          <div class="kv2"><small>Erwartetes DFA alpha-1</small><p>${esc(entry.dfa)}</p></div>
          <div class="kv2"><small>Beleg</small><p class="src">${esc(entry.evidence)}</p></div>
          <div class="kv2"><small>Grenze</small><p class="src">${esc(entry.limit)}</p></div>
        </div>` : ""}
      </div>`;
    }).join("");

    const lead = pick >= 0 ? list[pick] : null;
    const leadCard = lead ? `<div class="leadrec">
      <div class="leadhead">${ico("ok", C.green, 16)}
        <span>${forTomorrow
          ? "FÜR MORGEN EMPFOHLEN — heute ist schon trainiert; bewertet nach dem Zustand von heute"
          : "HEUTE EMPFOHLEN — aus deinem Zustand, den letzten Tagen und deinem Ziel"}</span></div>
      <div class="leadtitle">${esc(lead.title)}</div>
      <div class="leadmeta">${esc(lead.family_label)} · ${lead.minutes} min · Last ${fmt(lead.load)}${
        lead.hr_window ? ` · ${lead.hr_window[0]}–${lead.hr_window[1]} bpm` : ""}${
        lead.blocks_w ? ` · ${Math.min(...lead.blocks_w.map((b) => b[1]))}–${
          Math.max(...lead.blocks_w.map((b) => b[1]))} W` : ""}</div>
      <p class="leadwhy">${esc(lead.effect)}</p>
      <div class="worow">
        <button class="planbtn${forTomorrow ? " ghost" : ""}" data-act="plan" data-id="${esc(lead.key)}" data-when="${iso(0)}">
          ${ico("cal", null, 15)} heute in den Kalender</button>
        <button class="planbtn${forTomorrow ? "" : " ghost"}" data-act="plan" data-id="${esc(lead.key)}" data-when="${iso(1)}">${
          forTomorrow ? `${ico("cal", null, 15)} morgen in den Kalender` : "morgen"}</button>
      </div>
      <p class="src">Warum diese: von allen Arten unten ist sie die erste, die zu deinem
      heutigen Zustand passt. Die anderen stehen darunter — mit dem, was sie heute kosten
      würden. Entscheiden tust du.</p>
    </div>` : "";

    const conflict = w.conflict ? `<div class="warnrow">${ico("warn", C.amber, 16)}
      <span>${esc(w.conflict.text)}</span></div>` : "";

    return `${conflict}${leadCard}<h3 class="secname">Alle Einheiten für ${forTomorrow ? "morgen" : "heute"}
      <span class="hint">— eine je Art, jede ${forTomorrow
        ? "nach dem heutigen Zustand bewertet" : "für heute bewertet"}. Watt aus deiner
      FTP${w.ftp ? ` (${fmt(w.ftp)} W)` : ""}, Puls aus deiner gemessenen aeroben
      Schwelle${w.aerobic_hr ? ` (${w.aerobic_hr} bpm)` : ""}. Was du machst, entscheidest du —
      hier steht, was es heute kostet.</span></h3>
      <div class="wogrid">${cards}</div>
      <p class="note">Ein Klick legt die Einheit als geplantes Workout in deinen
      Intervals-Kalender — mit allen Schritten, direkt auf die Uhr übertragbar. Das ist der
      einzige Schreibzugriff dieser Integration, er passiert nur auf diesen Knopf.</p>`;
  }

  /* Goal, constraints, and the weeks that follow from them.

     The coach was paused because it recommended sessions without knowing what
     they were for. This asks, once: what do you want to be able to do, how
     many days do you have, how many hours, and what cannot move. Everything
     below follows from those answers and from what the archive already knows.

     The honest parts are built in: a weekly budget that cannot carry the
     target ride says so instead of printing a number it will not deliver,
     and the fact that block periodization is NOT better than traditional -
     load-matched, twelve weeks, no difference - is stated where someone might
     otherwise assume blocks are the secret. */
  rGoal(g) {
    if (!g) return `<div class="card pad">Ziel wird geladen …</div>`;
    const profile = g.profile || {};
    const state = g.state || {};
    if (this._goalEdit || !profile.goal) return this._goalForm(g);

    const plan = g.plan || {};
    const goalInfo = (g.goals || {})[profile.goal] || {};
    if (!plan.ready) {
      return `<div class="card pad">
        <h3 class="secname">Dein Ziel</h3>
        <p>Es fehlen noch Angaben: ${(plan.missing || []).map((m) => esc(FIELD_LABEL[m] || m)).join(", ")}.</p>
        <button class="planbtn" data-act="goaledit">Angaben ergänzen</button></div>`;
    }

    return `
      <div class="goalbar">
        <button class="gtile" data-act="goaledit">
          <small>ZIEL</small><b>${esc(goalInfo.label || plan.goal_label)}</b>
          <em>${esc(plan.target)}</em></button>
        <button class="gtile" data-act="goaledit">
          <small>ZEIT</small><b>${fmt(profile.days_per_week)} Tage pro Woche</b>
          <em>${plan.hard_per_week} harte ${plan.hard_per_week === 1 ? "Einheit" : "Einheiten"}
            · 80/20 zählt Einheiten, nicht Minuten</em></button>
      </div>`;
  }

  /* The weeks themselves. They live BELOW the day's question, not above it:
     the trainer head answers "what do I ride today", this answers "where is
     this going". The big day is marked as the exception it is, and the
     budget note explains the rhythm instead of demanding weekly hours the
     athlete does not have. */
  rPlanWeeks(g) {
    if (!g) return "";
    const plan = g.plan || {};
    if (!plan.ready || !(plan.weeks || []).length) return "";

    const note = plan.budget_note;
    const weeks = plan.weeks.map((w) => {
      const open = this._planOpen === String(w.index);
      return `<div class="pweek ${w.kind}${w.big_day ? " bigday" : ""}" data-act="planweeks" data-id="${w.index}">
        <div class="pwhead">
          <span class="pwno">W${w.index}</span>
          <span class="pwphase">${esc(w.phase_label)}${w.kind === "recovery" ? " · Entlastung" : ""}${
            w.big_day ? " · großer Tag" : ""}</span>
          <span class="pwh tn">${fmt(w.hours, 1)} h</span>
          ${w.long_day_hours ? `<span class="pwlong tn">${w.big_day ? "großer Tag" : "langer Tag"} ${
            fmt(w.long_day_hours, 1)} h${w.big_day ? " <em>(die Ausnahme, die wächst)</em>" : ""}</span>` : ""}
        </div>
        ${open ? `<div class="pwbody">
          <p class="hint">${esc(w.phase_note)}</p>
          ${(w.sessions || []).map((s) => `<div class="psess ${s.role}">
            <b>${esc(s.title)}</b>
            <p>${esc(s.detail)}</p>
            <p class="src">${esc(s.why)}</p>
            ${s.fuel ? `<p class="src"><b>Verpflegung:</b> ${esc(s.fuel)}</p>` : ""}
          </div>`).join("")}
        </div>` : `<div class="pwsess">${(w.sessions || []).map((s) =>
          `<span class="ptag ${s.role}">${esc(s.title)}</span>`).join("")}</div>`}
      </div>`;
    }).join("");

    return `<h3 class="secname">Die nächsten Wochen
        <span class="hint">— ${esc(plan.pattern)} an Kalenderwochen verankert; der große Tag
        wächst, die Wochen dazwischen bleiben gewöhnlich</span></h3>
      ${note ? `<div class="warnrow">${ico("info", C.amber, 16)} <span>${esc(note.text)}</span></div>` : ""}
      <div class="pweeks">${weeks}</div>
      <p class="src">${esc(plan.caveat || "")}</p>`;
  }

  _goalForm(g) {
    const d = this._goalDraft || {};
    const goals = g.goals || {};
    const state = g.state || {};
    const picked = d.goal;

    const known = [
      state.typical_hours ? `${fmt(state.typical_hours, 1)} h pro Woche` : null,
      state.typical_days ? `${fmt(state.typical_days, 1)} Fahrtage` : null,
      state.longest_ride_hours ? `längste Fahrt ${fmt(state.longest_ride_hours, 1)} h` : null,
    ].filter(Boolean).join(" · ");

    if (!picked) {
      return `<div class="card pad">
        <h3 class="secname" style="margin-top:0">Worauf trainierst du?</h3>
        <p class="hint">Eine Frage, dann noch eine — mehr braucht es nicht.
          ${known ? `Den Rest lese ich aus deinen Daten: ${esc(known)}.` : ""}</p>
        <div class="goalpick">
          ${Object.entries(goals).map(([key, info]) => `<button
            class="gopt" data-act="goalpick" data-id="${key}">
            <b>${esc(info.label)}</b><span>${esc(info.detail)}</span></button>`).join("")}
        </div>
        ${g.profile && g.profile.goal ? `<button class="chipbtn" data-act="goalcancel">abbrechen</button>` : ""}
      </div>`;
    }

    const info = goals[picked] || {};
    return `<div class="card pad">
      <h3 class="secname" style="margin-top:0">An wie vielen Tagen pro Woche fährst du?</h3>
      <p class="hint">Ziel: <b>${esc(info.label)}</b> — trainiert wird ${esc(info.target || "")}.
        <button class="linkbtn" data-act="goalpick" data-id="">anderes Ziel</button></p>
      <div class="daypick">
        ${[2, 3, 4, 5, 6, 7].map((n) => `<button class="dopt ${d.days_per_week === n ? "on" : ""}"
          data-act="goaldays" data-id="${n}"><b>${n}</b><span>Tage</span>
          <em>${n <= 4 ? "1 hart" : n <= 6 ? "2 hart" : "3 hart"}</em></button>`).join("")}
      </div>
      <p class="hint">Die harte Einheit pro Woche folgt aus der Tageszahl: die 80/20-Verteilung
        zählt Einheiten, nicht Minuten. Bis vier Fahrtage eine harte, die übrigen locker;
        zwei harte sind der Standard für Wochen von 8 bis 14 Stunden.</p>
      <div class="worow">
        <button class="planbtn" data-act="goalsave" ${d.days_per_week ? "" : "disabled"}>
          ${d.days_per_week ? "Plan erstellen" : "Tage wählen"}</button>
        ${g.profile && g.profile.goal ? `<button class="chipbtn" data-act="goalcancel">abbrechen</button>` : ""}
      </div>
    </div>`;
  }

  _stateBands(days, opts) {
    const COL = { slump: C.red, recovering: C.amber, rebound: C.amber,
                  strained: C.amber, ready: C.green, unknown: C.grey };
    const OP = { slump: 0.18, recovering: 0.10, rebound: 0.10, strained: 0.07,
                 ready: 0.0, unknown: 0.0 };
    const n = days.length, w = opts.w, padL = opts.padL, padR = opts.padR;
    const pw = w - padL - padR;
    let out = "", run = null;
    const flush = (end) => {
      if (!run || !OP[run.state]) return;
      const x0 = padL + (run.start / Math.max(1, n - 1)) * pw;
      const x1 = padL + (end / Math.max(1, n - 1)) * pw;
      out += `<rect x="${x0.toFixed(1)}" y="0" width="${Math.max(1.5, x1 - x0).toFixed(1)}"
        height="${opts.h}" fill="${COL[run.state]}" opacity="${OP[run.state]}"/>`;
    };
    days.forEach((d, i) => {
      if (!run || run.state !== d.state) { flush(i); run = { state: d.state, start: i }; }
    });
    flush(n - 1);
    return out;
  }

  rSignale(sig) {
    if (!sig) return `<div class="card pad">Signale werden geladen …</div>`;
    const days = sig.days || [];
    if (days.length < 10) return `<div class="card pad">Noch zu wenig Historie für den Signalvergleich.</div>`;
    const n = days.length;
    const swc = sig.swc || 0.5;
    const KEYS = [
      ["hrv", C.blue], ["rhr", ROLE.hr], ["sleep", C.cyan], ["form", C.violet],
    ];
    const labelOf = (k) => ((sig.signals || {})[k] || {}).label || k;
    const series = {};
    for (const [key] of KEYS) series[key] = days.map((d) => (d.z || {})[key] ?? null);
    const acwr = days.map((d) => d.acwr ?? null);
    const loads = days.map((d) => d.load || 0);

    const xt = monthTicks(days.map((d) => d.date));
    const bandOpts = { w: 880, padL: 48, padR: 14 };

    // one field per signal: same zero line, same scale, one cursor
    const field = (key, colour, h) => {
      const vals = series[key];
      if (!vals.some((v) => v != null)) return "";
      const dim = this._sigFocus && this._sigFocus !== key;
      const bands = this._stateBands(days, { ...bandOpts, h });
      return `<div class="sigfield ${dim ? "dim" : ""}" data-act="sigfocus" data-id="${key}">
        <div class="sflab" style="color:${colour}">${esc(labelOf(key))}
          <span class="sfu">${esc(((sig.signals || {})[key] || {}).unit || "")}</span></div>
        ${chart({
          h, n, y0: -3, y1: 3, grp: "sig", padB: 4,
          yticks: [-2, 0, 2], yf: (v) => (v > 0 ? "+" : "") + fmt(v, 0),
          bands: [{ a: -swc, b: swc, c: C.tx3, op: 0.10 }],
          hl: [{ y: 0, c: C.tx3 }],
          s: [{ t: "line", v: vals, c: colour, w: 2, lop: dim ? 0.25 : 1 }],
          extra: bands,
        })}
      </div>`;
    };

    let body = "";
    if (this._sigMode === "overlay") {
      const bandsBg = this._stateBands(days, { ...bandOpts, h: 300 });
      body = `<div class="sigfield">
        ${chart({ h: 300, n, y0: -3, y1: 3, grp: "sig", xt,
          yticks: [-2, -1, 0, 1, 2], yf: (v) => (v > 0 ? "+" : "") + fmt(v, 0),
          bands: [{ a: -swc, b: swc, c: C.tx3, op: 0.10 }],
          hl: [{ y: 0, c: C.tx3, t: "deine Basislinie" }],
          s: KEYS.filter(([k]) => series[k].some((v) => v != null))
                 .map(([k, c]) => ({ t: "line", v: series[k], c,
                   w: this._sigFocus === k ? 2.6 : 1.8,
                   lop: this._sigFocus && this._sigFocus !== k ? 0.18 : 0.9 })),
          extra: bandsBg })}
      </div>`;
    } else {
      body = KEYS.map(([k, c]) => field(k, c, 86)).join("");
    }

    // load bar coloured by the DFA bands actually ridden
    const maxLoad = Math.max(1, ...loads);
    const barW = Math.max(1.6, (880 - 62) / n * 0.7);
    let bars = "";
    days.forEach((d, i) => {
      if (!d.load) return;
      const x = 48 + (i / Math.max(1, n - 1)) * (880 - 62);
      const total = d.load / maxLoad * 74;
      const act = (d.activities || []).find((a) => a.dfa_bands);
      const parts = act ? act.dfa_bands : null;
      if (!parts) {
        bars += `<rect x="${(x - barW / 2).toFixed(1)}" y="${(80 - total).toFixed(1)}"
          width="${barW.toFixed(1)}" height="${total.toFixed(1)}" fill="${C.slate}" opacity="0.75"/>`;
      } else {
        let y = 80;
        [[parts[2], C.red], [parts[1], C.amber], [parts[0], C.green]].forEach(([share, col]) => {
          const seg = total * (share / 100);
          y -= seg;
          if (seg > 0.4) bars += `<rect x="${(x - barW / 2).toFixed(1)}" y="${y.toFixed(1)}"
            width="${barW.toFixed(1)}" height="${seg.toFixed(1)}" fill="${col}" opacity="0.9"/>`;
        });
      }
      if (d.hard) bars += `<circle cx="${x.toFixed(1)}" cy="4" r="2.6" fill="${C.amber}"/>`;
    });
    const loadField = `<div class="sigfield">
      <div class="sflab" style="color:${C.tx2}">Training <span class="sfu">Tageslast, gefärbt nach gefahrenen DFA-Bereichen</span></div>
      <svg class="ch" viewBox="0 0 880 96" preserveAspectRatio="none" data-n="${n}" data-padl="48" data-padr="14">
        ${this._stateBands(days, { ...bandOpts, h: 96 })}
        <line x1="48" x2="866" y1="80" y2="80" stroke="${C.line}"/>
        ${bars}
        ${xt.map((tk) => `<text x="${48 + (tk.i / Math.max(1, n - 1)) * (880 - 62)}" y="93"
           text-anchor="middle" class="ax">${tk.t}</text>`).join("")}
        <line class="xh" x1="-9" x2="-9" y1="0" y2="84" stroke="${C.tx2}" stroke-width="1" stroke-dasharray="3 3" opacity="0"/>
      </svg></div>`;

    // the readout carries raw units, not z-scores - that is what one recognises
    this._grp.sig = {
      n,
      xl: (i) => `${dMed(days[i].date)} · ${STATE_WORD[days[i].state] || days[i].state}`,
      rows: [
        ...KEYS.filter(([k]) => series[k].some((v) => v != null)).map(([k, c]) => ({
          l: labelOf(k), c, u: ((sig.signals || {})[k] || {}).unit || "",
          dec: k === "sleep" ? 1 : 0,
          vals: days.map((d) => (d.raw || {})[k] ?? null),
        })),
        { l: "Akut : chronisch", c: C.slate, dec: 2, vals: acwr },
        { l: "Tageslast", c: C.tx2, vals: loads },
      ],
    };

    const legend = KEYS.map(([k, c]) =>
      `<button class="lgbtn ${this._sigFocus === k ? "on" : ""}" data-act="sigfocus" data-id="${k}">
        <i style="background:${c}"></i>${esc(labelOf(k))}</button>`).join("");
    const statelegend = [["slump", "Einbruch", C.red], ["recovering", "noch im Einbruch", C.amber],
                         ["rebound", "Erholung", C.amber], ["strained", "beansprucht", C.amber],
                         ["ready", "Normalbereich", C.green]]
      .map(([, w, c]) => `<span class="lg"><i class="swb" style="background:${c}"></i>${w}</span>`).join("");

    const explain = Object.entries(sig.signals || {}).concat(Object.entries(sig.load_signals || {}))
      .map(([key, meta]) => `<details class="more expl"><summary>${esc(meta.label)}${
        meta.unit ? ` <span class="mut">in ${esc(meta.unit)}</span>` : ""}</summary>
        <p class="readas">Zu lesen als: ${esc(meta.read || "")}</p>
        <p class="src">${esc(meta.source || "")}</p></details>`).join("");

    return `
      <div class="bar">
        <div class="legend">${legend}</div>
        <div class="chips">
          <button class="chipbtn ${this._sigMode === "stack" ? "on" : ""}" data-act="sigmode" data-id="stack">gestapelt</button>
          <button class="chipbtn ${this._sigMode === "overlay" ? "on" : ""}" data-act="sigmode" data-id="overlay">überlagert</button>
          ${[[42, "42 T"], [90, "3 M"], [180, "6 M"], [365, "1 J"]].map(([d, l]) =>
            `<button class="chipbtn ${this._sigDays === d ? "on" : ""}" data-act="sigdays" data-id="${d}">${l}</button>`).join("")}
        </div>
      </div>
      <p class="hint pad">Alle Signale in derselben Einheit: Abstand von <b>deiner eigenen</b>
      Basislinie in Standardabweichungen. Die graue Zone ist ±0,5 — die kleinste bedeutsame
      Änderung; was darin liegt, ist Rauschen. Der Ruhepuls ist gespiegelt, damit „oben"
      überall günstig heißt. Hintergrundfarbe = Zustand laut Trainer.</p>
      <div class="card pad0" data-grp="sig">
        ${readout("sig")}
        ${body}
        ${this._sigMode === "stack" ? loadField : loadField}
      </div>
      <div class="bar"><div class="legend">${statelegend}
        <span class="lg"><i class="swb" style="background:${C.green}"></i>aerob</span>
        <span class="lg"><i class="swb" style="background:${C.amber}"></i>Übergang</span>
        <span class="lg"><i class="swb" style="background:${C.red}"></i>anaerob</span>
        <span class="lg">${ico("dot", C.amber, 12)} harte Einheit</span></div></div>

      <h3 class="secname">Was die einzelnen Werte bedeuten <span class="hint">— und woher die Regel kommt</span></h3>
      <div class="card">${explain}</div>`;
  }

  /* ---------------- Trainer ----------------
     The verdict first, then what to ride, then why - and the limits of the
     rule sit next to it rather than in a footnote. Every number here is
     either measured from this athlete or carries the study it comes from.

     One voice: the session recommendation lives in rWorkouts (the first
     card that fits today IS the recommendation). This block carries the
     state, its reasons, and the warnings. Every string built here is
     inserted below - a computed block that never reaches the DOM is the
     bug that silently dropped the infection warning in 0.31.0, and
     test_panel_fixes now proves these render. */
  rTrainer(c, rd) {
    if (!c) return `<div class="card pad">Trainer wird geladen …</div>`;
    const st = c.state || {};
    const STATE_LOOK = {
      // Judgment states use the judgment register ONLY - blue and violet
      // belong to categories. The word and the icon shape carry the
      // distinction between the three amber states.
      ready:      { c: C.green,  ic: "ok",    w: "im Normalbereich" },
      rebound:    { c: C.amber,  ic: "trend", w: "Erholung nach Einbruch" },
      strained:   { c: C.amber,  ic: "warn",  w: "beansprucht" },
      recovering: { c: C.amber,  ic: "warn",  w: "noch im Einbruch" },
      slump:      { c: C.red,    ic: "stop",  w: "Einbruch" },
      elevated:   { c: C.amber,  ic: "wave",  w: "auffällig hoch" },
      unknown:    { c: C.grey,   ic: "na",    w: "keine Einschätzung" },
    };
    const look = STATE_LOOK[st.state] || STATE_LOOK.unknown;
    const anc = c.anchors || {};
    const dur = c.durability;
    const trend = anc.trend_power;

    const warns = (c.warnings || []).map((w) =>
      `<div class="warnrow">${ico("warn", C.amber, 16)}<span>${esc(w)}</span></div>`).join("");
    const reasons = (c.reasons || []).length ? `<ul class="reasons">${(c.reasons || []).map((x) =>
      `<li><b>${esc(x.weil)}</b>
        <span class="src">${esc(x.text)}</span>
        <em class="qq">${esc(x.quelle)}</em></li>`).join("")}</ul>` : "";

    return `
      <section class="card hero" style="border-color:${look.c}55">
        <div class="tstate">
          <span class="tsic" style="color:${look.c}">${ico(look.ic, look.c, 30)}</span>
          <div>
            <div class="kicker">Zustand heute</div>
            <div class="tslabel" style="color:${look.c}">${esc(st.label || "–")}</div>
          </div>
          <div class="tsz">
            ${(() => {
              // One axis, three dots - not three separate bars. Position on a
              // COMMON scale is the most accurately read encoding there is;
              // three bars with their own tracks force a comparison across
              // separate scales, which is exactly what it should not be.
              const pts = [
                ["7-Tage-Mittel HRV", st.week_z, C.blue],
                ["letzte 3 Tage HRV", st.recent_hrv_z, ROLE.series],
                ["letzte 3 Tage Ruhepuls", st.recent_rhr_z, ROLE.hr],
              ].filter(([, v]) => v != null);
              if (!pts.length) return "";
              const pos = (z) => ((Math.max(-3, Math.min(3, z)) + 3) / 6 * 100).toFixed(1);
              // One row per signal, name on the LEFT, value on the RIGHT of the
              // same row - no legend to look up. A legend forces the eye between
              // two places and the mapping into memory. The band and zero line
              // run behind every row, so all three still read on one scale.
              return `<div class="zplot">
                ${pts.map(([label, z, col]) => `<div class="zrow">
                  <span class="zname">${esc(label)}</span>
                  <span class="ztrack">
                    <i class="zband"></i><i class="zzero"></i>
                    <i class="zdot" style="left:${pos(z)}%;background:${col}"></i>
                  </span>
                  <b class="zval tn" style="color:${col}">${sign(z, 2)}</b>
                </div>`).join("")}
                <div class="zscale"><span>−3 SD</span><span>±0,5 = Rauschen</span><span>+3 SD</span></div>
              </div>`;
            })()}
          </div>
        </div>
        <p class="tdetail">${esc(st.detail || "")}</p>
        ${st.since ? `<p class="hint">Einbruch erkannt am ${dMed(st.since)} — solange er im
          7-Tage-Fenster steckt, zieht er das Mittel nach unten, auch wenn die letzten Tage
          längst wieder darüber liegen.</p>` : ""}
        ${warns}
        ${reasons}
      </section>

      ${c.trained_today ? `<p class="note">${ico("ok", C.green, 14)} Heute liegt schon eine
        Einheit im Archiv — die Karten unten gelten damit eher für morgen.</p>` : ""}

      ${this.rWorkouts(this._workouts, !!c.trained_today)}

      <h3 class="secname">Deine gemessenen Anker <span class="hint">— keine Prozente einer Maximalherzfrequenz</span></h3>
      <div class="card ancgrid">
        <div class="stat"><small>Aerobe Schwelle (DFA 0,75)</small>
          <b class="tn lead1" style="color:${ROLE.series}">${anc.aerobic_hr ? fmt(anc.aerobic_hr) : "–"} <span class="unit">bpm</span></b>
          <span class="mut">${esc(anc.source || "")}</span></div>
        <div class="sidestats">
          <div class="stat"><small>bei Leistung</small><b class="tn small2">${anc.aerobic_power ? fmt(anc.aerobic_power) + " W" : "–"}</b></div>
          <div class="stat"><small>Messungen</small><b class="tn small2">${fmt(anc.n || 0)}</b></div>
          ${trend ? `<div class="stat"><small>Entwicklung</small>
            <b class="tn small2" style="color:${trend.power_change_pct >= 0 ? C.green : C.amber}">${sign(trend.power_change_pct, 1)} %</b>
            <span class="mut">${trend.power_before} → ${trend.power_now} W bei ${trend.hr_before} → ${trend.hr_now} bpm</span></div>` : ""}
        </div>
      </div>
      ${trend ? `<p class="note">${trend.power_change_pct > 0
        ? `Mehr Leistung bei praktisch gleicher Herzfrequenz an der aeroben Schwelle — das ist die Anpassung, auf die Grundlagentraining zielt.`
        : `Die Leistung an der aeroben Schwelle hat sich nicht verbessert.`}</p>` : ""}

      ${dur ? `<h3 class="secname">Wie lange trägt die Grundlage?</h3>
      <div class="card">
        <div class="durrow">
          <div class="stat"><small>unter 90 min</small><b class="tn small2">${dur.short != null ? fmt(dur.short,1) + " %" : "–"}</b></div>
          <div class="stat"><small>ab 90 min</small><b class="tn small2">${dur.long != null ? fmt(dur.long,1) + " %" : "–"}</b></div>
          <div class="stat"><small>Einheiten</small><b class="tn small2">${dur.n}</b></div>
        </div>
        <p class="effect">${esc(dur.verdict)}</p>
        <details class="more"><summary>Quelle und Grenzen</summary><p class="src">${esc(dur.source)} — Entkopplung ist nur auf gleichmäßigen Einheiten aussagekräftig; Intervalle sind hier ausgeschlossen.</p></details>
      </div>` : ""}

      <div class="card pad">
        <details class="more"><summary>Worauf diese Empfehlung beruht — und was sie nicht kann</summary>
          <p class="src">Zustand aus HRV und Ruhepuls gegen deine eigene Basislinie, Last der
          letzten sieben Tage, gemessene Anker aus deinen DFA-Einheiten, dazu dein Ziel.
          Was sie nicht kennt: alles außerhalb des Trainings — Arbeit, Schlafqualität,
          Stress. Deshalb ist sie ein Vorschlag für heute und keine Vorschrift.</p>
        </details>
      </div>`;
  }

  /* ---------------- Heute ---------------- */
  _sparkFor(id, days, load) {
    const past = (days && days.days || []).filter((d) => !d.future).slice(-42);
    const dts = past.map((d) => d.date);
    const pick = (k) => past.map((d) => d[k] == null ? null : +d[k]);
    if (id === "hrv") {
      // The card's headline value is ln(rMSSD) against its baseline, so the
      // curve has to be that same quantity - it used to plot raw ms below a
      // logarithmic headline, two units in one tile.
      const ser = (load && load.hrv && load.hrv.series || []).slice(-42);
      if (ser.length > 2) {
        const band = load.hrv.baseline != null && load.hrv.swc != null
          ? { a: load.hrv.baseline - load.hrv.swc, b: load.hrv.baseline + load.hrv.swc } : null;
        return { v: ser.map((x) => x.ln_rmssd_7d), d: ser.map((x) => x.date), unit: "ln rMSSD",
                 t: "ln rMSSD, 7-Tage-Mittel · 6 Wochen (Band: Basislinie ± SWC)", band };
      }
      return { v: pick("hrv"), d: dts, unit: "ms", t: "HRV in ms · 6 Wochen" };
    }
    if (id === "rhr") return { v: pick("resting_hr"), d: dts, unit: "bpm", t: "Ruhepuls in bpm · 6 Wochen" };
    if (id === "sleep") return { v: pick("sleep_hours"), d: dts, unit: "h", t: "Schlaf in h · 6 Wochen" };
    if (id === "form") return { v: pick("form"), d: dts, unit: "%", t: "Form · 6 Wochen", zero: true };
    if (id === "acwr" && load) {
      const a = (load.acwr || []).slice(-42);
      return { v: a.map((x) => x.ratio), d: a.map((x) => x.date), unit: "",
               t: "Akut : chronisch · 6 Wochen", band: { a: 0.8, b: 1.3 } };
    }
    if (id === "monotony" && load) {
      const w = (load.weeks || []).slice(-12);
      return { v: w.map((x) => x.monotony), d: w.map((x) => x.week), unit: "", week: true,
               t: "Monotonie je Woche · 12 Wochen", bars: true, hline: 2 };
    }
    return null;
  }

  /* Event track under an enlarged signal curve: one short stroke per training
     day, height by load, plus a marker on the days the trainer called a slump.
     That puts "HRV falls two days after the long ride" on one screen instead
     of behind a tab change.

     Two registers, kept apart: training is a CATEGORY and gets slate, the
     state is a JUDGMENT and gets amber/red - and each state carries its own
     shape as well as its colour, so the track survives without colour vision.
     Geometry is the chart's (880 / 48 / 14), or the cursor would sit next to
     the stroke it names instead of on it. */
  _eventTrack(track, grp) {
    const w = 880, padL = 48, padR = 14, h = 34, base = 22;
    const rows = track || [];
    const n = Math.max(2, rows.length);
    const X = (i) => padL + (i / (n - 1)) * (w - padL - padR);
    const maxLoad = Math.max(1, ...rows.map((r) => (r && r.load) || 0));
    let g = "";
    rows.forEach((r, i) => {
      const load = (r && r.load) || 0;
      if (load > 0) {
        const hgt = 3 + (load / maxLoad) * 11;
        g += `<line x1="${X(i).toFixed(1)}" x2="${X(i).toFixed(1)}" y1="${base}"
          y2="${(base - hgt).toFixed(1)}" stroke="${C.slate}" stroke-width="2.2" opacity="0.95"/>`;
      }
      const st = r && r.state;
      if (st === "slump") {
        // triangle: the shape says "slump" even where the red does not
        const x = X(i);
        g += `<path d="M${(x - 3.2).toFixed(1)} ${base + 8}L${(x + 3.2).toFixed(1)} ${base + 8}L${x.toFixed(1)} ${base + 2.6}Z" fill="${C.red}"/>`;
      } else if (st === "recovering" || st === "rebound" || st === "strained") {
        g += `<rect x="${(X(i) - 2.4).toFixed(1)}" y="${base + 3.4}" width="4.8" height="4.8" rx="1" fill="${C.amber}"/>`;
      }
    });
    return `<svg class="ch evtrack" viewBox="0 0 ${w} ${h}" preserveAspectRatio="none"
        data-n="${n}" data-w="${w}" data-padl="${padL}" data-padr="${padR}">
      <line x1="${padL}" x2="${w - padR}" y1="${base}" y2="${base}" stroke="${C.line}"/>
      ${g}
      <line class="xh" x1="-9" x2="-9" y1="2" y2="${h - 2}" stroke="${C.tx2}" stroke-width="1" stroke-dasharray="3 3" opacity="0"/>
    </svg>
    <p class="hint evleg"><i class="evb" style="background:${C.slate}"></i>Trainingstag (Höhe = Last)
      <i class="evt" style="border-bottom-color:${C.red}"></i>Einbruch
      <i class="evs" style="background:${C.amber}"></i>beansprucht / Erholung</p>`;
  }

  /* date of the newest actual value in a series - a wellness row fills up
     over the day, so a card's number is often yesterday's. Saying which day
     it belongs to is the difference between a reading and a guess. */
  _stampOf(sp) {
    if (!sp || !sp.v || !sp.d) return null;
    for (let i = sp.v.length - 1; i >= 0; i--) {
      if (sp.v[i] != null) return sp.d[i] || null;
    }
    return null;
  }

  /* What is possible today.

     Rebuilt against the criticism of readiness scores rather than around one.
     Two findings drive the shape:

     - READINESS IS NOT RECOVERY. Recovery describes what happened in response
       to past stress; readiness is what can be tolerated right now. A single
       number collapses them, and a low score from a short night looks exactly
       like a low score from a starting infection while demanding the opposite
       response. Of fourteen commercial scores across ten manufacturers, none
       publishes its formula and few offer any validation.
     - THE USEFUL MOVE IS TO TREAT SUCH DATA AS A PROMPT, NOT A VERDICT: what
       changed, which system is driving it, how does that fit recent training.

     So: one sentence about today and a ceiling, then the signals kept apart
     and labelled by the system they report on - and where the signals and the
     verdict disagree, the page says why instead of hiding it. Nothing reaches
     past today, because the load outside training is in no data. */
  rHeute(t) {
    if (!t) return `<div class="card pad">Wird geladen …</div>`;
    const stale = !!(t.available && t.date && t.date !== new Date().toISOString().slice(0, 10));
    if (!t.available) return `<div class="card pad">Noch keine Wellness-Daten.</div>`;

    const TONE = { slump: "red", recovering: "amber", rebound: "blue",
                   strained: "amber", ready: "green", elevated: "amber", unknown: "grey" };
    const tone = TONE[t.state] || "grey";
    const col = { red: C.red, amber: C.amber, blue: C.blue, green: C.green, grey: C.tx3 }[tone];

    // Colour never alone: the traffic-light word and its own icon shape ride
    // along, because roughly 8% of men cannot separate red from green.
    const WORD = { red: "rot", amber: "gelb", blue: "blau", green: "grün", grey: "keine Daten" };
    const head = `<div class="tcard ${tone}">
      <div class="tmain">
        <div class="tlabel">HEUTE MÖGLICH ${badge(tone, WORD[tone])}</div>
        <div class="tbig" style="color:${col}">${esc(t.capacity)}</div>
        <p class="tsay">${esc(t.capacity_text)}</p>
        ${t.ceiling != null ? (() => {
          // Bullet graph, not a gauge: actual against a target range is what it
          // was designed for, and it reads on position rather than on an angle.
          const doneToday = (t.recent || []).slice(-1)[0];
          const done = doneToday ? doneToday.load : 0;
          const scale = Math.max(t.ceiling * 1.4, done * 1.1, 10);
          return `<div class="tceil">
            <span>Obergrenze</span><b class="tn">${fmt(t.ceiling)} Last</b>
            <div class="bullet"><i class="bband" style="width:${(t.ceiling / scale * 100).toFixed(1)}%"></i>
              <i class="bval" style="width:${(done / scale * 100).toFixed(1)}%"></i>
              <i class="bmark" style="left:${(t.ceiling / scale * 100).toFixed(1)}%"></i></div>
            <em>heute gefahren: ${fmt(done)} · darüber wird es ein Reiz, den du heute nicht
            verdaust. Die Zielwahl je Ampelfarbe ist eine Setzung, kein Befund.</em></div>`;
        })() : ""}
      </div>
      <div class="tstate">
        <div class="tlabel">ZUSTAND</div>
        <div class="tstateword" style="color:${col}">${esc(t.state_label || STATE_WORD[t.state] || t.state)}</div>
        <p class="hint">${esc(t.state_text || "")}</p>
      </div>
    </div>`;

    const signals = (t.signals || []).map((s) => {
      const scol = s.direction === "günstig" ? C.green
        : s.direction === "ungünstig" ? C.amber : C.tx3;
      const width = Math.min(50, Math.abs(s.z) / 3 * 50);
      const left = s.z < 0 ? 50 - width : 50;
      const dec = s.unit === "h" ? 1 : 0;
      const big = this._sigOpen === s.key;
      return `<div class="tsig ${s.moved ? "moved" : ""} ${big ? "big" : ""}"
          data-act="sigopen" data-id="${esc(s.key)}" title="${big ? "kleiner" : "größer"}">
        <div class="tsighead"><b>${esc(s.label)}</b>
          <span class="tsigsys">${esc(s.system)}</span></div>
        <div class="tsignum"><b class="tn" style="color:${scol}">${fmt(s.value, dec)}</b>
          <small>${esc(s.unit)}</small>
          <span class="tsigbase">Basislinie ${fmt(s.baseline, dec)}</span></div>
        <div class="tsigdate ${stale ? "stale" : ""}">Stand ${esc(dMed(t.date))}${
          stale ? " — nicht von heute; ein Wellness-Datensatz füllt sich über den Tag" : ""}</div>
        <div class="tsigbar"><i class="tsigband"></i>
          <i class="tsigfill" style="left:${left.toFixed(1)}%;width:${Math.max(1, width).toFixed(1)}%;background:${scol}"></i></div>
        <div class="tsigfoot"><span style="color:${scol}">${sign(s.z, 1)} SD · ${esc(s.direction)}</span>
          <em>${esc(s.limit)}</em></div>
        ${big ? `<div class="tsigbig">
          <div class="tsigbignum"><b class="tn" style="color:${scol}">${fmt(s.value, dec)}</b>
            <small>${esc(s.unit)}</small>
            <span>gegen deine Basislinie von ${fmt(s.baseline, dec)} ${esc(s.unit)}</span></div>
          ${(() => {
            const band = (t.bands || {})[s.key];
            const series = (t.history && t.history[s.key]) || [s.baseline, s.value];
            const vals = series.filter((v) => v != null);
            // The small curve is a sparkline and may go without an axis. Once
            // it opens up it is a diagram, and a diagram needs one. The dates
            // come from the payload: these are the wellness days that exist,
            // not 42 consecutive ones, so "today minus n" would be wrong from
            // the first gap.
            const track = (t.history_days || []);
            const dts = track.length === series.length ? track.map((r) => r.date) : [];
            const ax = dayAxis(dts);
            const grp = `tsig_${s.key}`;
            if (dts.length) {
              this._grp[grp] = {
                n: series.length,
                xl: (i) => `${dMed(dts[i])}${(track[i] || {}).load ? " · Training" : ""}`,
                rows: [
                  { l: s.label, c: scol, u: s.unit, dec, vals: series },
                  { l: "Tageslast", c: C.tx2, vals: track.map((r) => r.load || 0) },
                ],
              };
            }
            // the axis has to CONTAIN the threshold line, or it is drawn
            // outside the plot and silently disappears
            const marks = band ? [band.slump, band.usual[0], band.usual[1], band.baseline] : [s.baseline];
            const lo = Math.min(...vals, ...marks) * 0.96;
            const hi = Math.max(...vals, ...marks) * 1.04;
            // bands from the athlete's own 60-day distribution, drawn in the
            // signal's own unit: noise, ordinary spread, and the line where a
            // drop stops being noise
            const bands = band ? [
              { a: band.usual[0], b: band.usual[1], c: C.tx3, op: 0.08 },
              { a: band.noise[0], b: band.noise[1], c: C.tx3, op: 0.14 },
            ] : [];
            const lines = band ? [
              { y: band.baseline, c: C.tx3, d: 1, t: `Basislinie ${fmt(band.baseline, dec)}` },
              { y: band.slump, c: C.amber, d: 1, t: `${s.key === "rhr" ? "auffällig hoch" : "Einbruch ab"} ${fmt(band.slump, dec)}` },
            ] : [{ y: s.baseline, c: C.tx3, d: 1, t: "Basislinie" }];
            const plot = chart({ h: 200, n: Math.max(2, series.length), y0: lo, y1: hi,
              yf: (v) => fmt(v, dec), bands, hl: lines,
              grp: dts.length ? grp : null,
              xt: ax.labels, xtick: ax.ticks,
              s: [{ t: "line", v: series, c: scol, w: 2 }] });
            if (!dts.length) return plot;
            return `<div data-grp="${grp}">${readout(grp)}${plot}${this._eventTrack(track, grp)}</div>`;
          })()}
          ${(t.bands || {})[s.key] ? `<p class="src"><b>Die Bereiche:</b> das dunkle Band ist
            ±0,5 Standardabweichungen um deine Basislinie — was darin liegt, ist Rauschen.
            Das hellere ist deine gewohnte Schwankung (±1 SD). Die gelbe Linie markiert
            ${s.key === "rhr" ? "den Wert, ab dem der Ruhepuls auffällig hoch ist"
                              : "den Wert, ab dem ein Abfall kein Rauschen mehr ist"}
            (2 SD). Alles aus deinen letzten 60 Tagen gerechnet.</p>` : ""}
          <p class="src"><b>Worüber dieser Wert etwas sagt:</b> ${esc(s.system)}.
            ${esc(s.limit)}. Die graue Zone ist ±0,5 SD — die kleinste bedeutsame Änderung;
            was darin liegt, ist Rauschen und kein Signal.</p>
        </div>` : ""}
      </div>`;
    }).join("");

    const maxLoad = Math.max(1, ...(t.recent || []).map((d) => d.load));
    const bars = (t.recent || []).map((d) => {
      const height = d.load ? Math.max(8, (d.load / maxLoad) * 100) : 3;
      const dcol = { slump: C.red, recovering: C.amber, rebound: C.amber,
                     strained: C.amber }[d.state] || C.slate;
      // A fixed grid, not a flex row: every bar grows from THE SAME baseline,
      // and the rows below it line up across all seven days. Cells of differing
      // height pushed the bars upwards, which is exactly what destroys a length
      // comparison on a common baseline.
      const names = (d.sessions || []).map((s) => s.name || s.type).filter(Boolean);
      const isToday = d.date === new Date().toISOString().slice(0, 10);
      const state = STATE_WORD[d.state] || "";
      return `<div class="tday ${isToday ? "now" : ""}"
          title="${esc(dMed(d.date))}: Last ${d.load}${
            names.length ? " · " + esc(names.join(", ")) : " · kein Training"}${
            state ? " · " + esc(state) : ""}">
        <span class="tbarbox"><i style="height:${height.toFixed(0)}%;background:${dcol}"></i></span>
        <span class="tdate">${esc(dShort(d.date))}</span>
        <b class="tload tn">${d.load || "–"}</b>
        <em class="tdayn">${names.length ? esc(names[0].slice(0, 12)) + (
          names.length > 1 ? " +" + (names.length - 1) : "") : "frei"}</em>
      </div>`;
    }).join("");

    const night = t.night && t.night.available ? `<div class="tnight">
      <div class="tlabel">DIE NACHT NACH DER LETZTEN EINHEIT — Erholung, nicht Bereitschaft</div>
      <p class="tnhead">${esc(t.night.headline)}</p>
      <p class="hint">${esc(t.night.detail)}</p></div>` : "";

    return `
      <div class="thead">${esc(dLong(t.date))}${
        stale ? ` <span class="staleflag">Werte von ${esc(dMed(t.date))}</span>` : ""}</div>
      ${head}
      ${t.tension ? `<div class="tnote">${ico("info", C.tx2, 16)}<span>${esc(t.tension)}</span></div>` : ""}

      <h3 class="secname">Was sich bewegt hat
        <span class="hint">— jedes Signal einzeln, mit dem System, über das es etwas aussagt</span></h3>
      <div class="tsigs">${signals}</div>

      <h3 class="secname">Woher das kommt
        <span class="hint">— die letzten sieben Tage und die Nacht nach der letzten Einheit</span></h3>
      <div class="card pad">
        <div class="tweek">${bars}</div>
        <div class="tweeksum">${fmt(t.week_load)} Last in sieben Tagen · ${t.rest_days}
          ${t.rest_days === 1 ? "Tag" : "Tage"} ohne Training</div>
        ${night}
      </div>

      <div class="card pad">
        <details class="more"><summary>Warum hier kein Punktwert steht</summary>
          <p class="src">${esc(t.method)}</p></details>
        <details class="more"><summary>Warum nur heute und nicht die Woche</summary>
          <p class="src">${esc(t.horizon)}</p></details>
      </div>`;
  }

  _nextPlanned(days) {
    if (!days) return null;
    for (const d of days.days || []) {
      if (d.date < days.today) continue;
      for (const p of d.planned || []) {
        if (!p.done) return Object.assign({ day: d.date }, p);
      }
    }
    return null;
  }

  /* ---------------- Kalender ---------------- */
  rKalender(days) {
    if (!days) return `<div class="card pad">Kalender wird geladen …</div>`;
    const byWeek = new Map();
    for (const d of days.days || []) {
      if (!byWeek.has(d.week)) byWeek.set(d.week, new Array(7).fill(null));
      byWeek.get(d.week)[d.weekday] = d;
    }
    const weekSum = new Map((days.weeks || []).map((w) => [w.week, w]));
    const order = [...byWeek.keys()].sort().reverse();
    const avg = days.avg_week_load || 0;
    const rows = order.map((wk) => {
      const cells = byWeek.get(wk).map((d) => this._dayCell(d, days.today)).join("");
      return `<div class="wkrow">${this._weekCell(weekSum.get(wk), days.max_week_load, avg)}${cells}</div>`;
    }).join("");
    const legend = `
      <div class="legend">
        ${Object.entries(SPORT).slice(0, 5).map(([, s]) => `<span class="lg" style="color:${s.c}">${ico(s.ic, s.c, 15)}${s.l}</span>`).join("")}
        <span class="lg">${ico("cal", C.tx3, 15)}<i class="dashdemo"></i> geplant</span>
        <span class="lg" style="color:${C.green}">${ico("ok", C.green, 15)} erledigt</span>
        <span class="lg" style="color:${C.red}">${ico("stop", C.red, 15)} ausgelassen</span>
      </div>`;
    return `
      <div class="bar">
        ${legend}
        <div class="chips">
          <button class="chipbtn ${this._weeks === 12 ? "on" : ""}" data-act="weeks" data-id="12">12 Wochen</button>
          <button class="chipbtn ${this._weeks === 26 ? "on" : ""}" data-act="weeks" data-id="26">26 Wochen</button>
        </div>
      </div>
      <div class="calhead"><span></span>${WD.map((w) => `<span>${w}</span>`).join("")}</div>
      ${rows}`;
  }

  _weekCell(w, maxLoad, avg) {
    if (!w) return `<div class="wksum card"></div>`;
    const kw = w.week.split("-W");
    const pct = maxLoad ? Math.min(100, (w.load / maxLoad) * 100) : 0;
    const delta = avg ? w.load - avg : null;
    return `<div class="wksum card">
      <div class="wkkw">KW ${+kw[1]} <span class="yr">${kw[0]}</span></div>
      <div class="wkload tn">${fmt(w.load)}
        ${delta != null ? `<span class="wkdelta ${delta >= 0 ? "up" : "down"}">${sign(Math.round(delta))}</span>` : ""}</div>
      ${w.planned_load ? `<div class="wkplan">+ ${fmt(w.planned_load)} geplant</div>` : ""}
      <div class="wkbar"><i style="width:${pct}%"></i></div>
      <div class="wkmeta">
        <span>${ico("clock", C.tx3, 13)}${fmt(w.hours, 1)} h</span>
        <span>${ico("road", C.tx3, 13)}${fmt(w.km, 1)} km</span>
        <span>${ico("dot", C.tx3, 13)}${w.sessions}×</span>
      </div>
      ${w.ctl != null ? `<div class="wkfit">Fitness ${fmt(w.ctl)} · Form ${sign(Math.round(w.form || 0))}</div>` : ""}
    </div>`;
  }

  _dayCell(d, today) {
    if (!d) return `<div class="day off"></div>`;
    const wln = [];
    if (d.sleep_hours != null) wln.push(`<span title="Schlaf">${ico("moon", C.tx3, 13)}${fmt(d.sleep_hours, 1)}</span>`);
    if (d.hrv != null) wln.push(`<span title="HRV">${ico("heart", C.tx3, 13)}${fmt(d.hrv)}</span>`);
    if (d.resting_hr != null) wln.push(`<span title="Ruhepuls">${ico("pulse", C.tx3, 13)}${fmt(d.resting_hr)}</span>`);
    if (d.steps != null) wln.push(`<span title="Schritte">${ico("steps", C.tx3, 13)}${fmt(Math.round(d.steps / 100) / 10, 1)}k</span>`);
    const chips = (d.activities || []).map((a) => this._chip(a)).join("") +
      (d.planned || []).map((p) => this._planChip(p, d, today)).join("");
    return `<div class="day ${d.today ? "is-today" : ""} ${d.future ? "is-fut" : ""}">
      <div class="dhead"><span>${dShort(d.date)}</span>${d.load ? `<span class="dload tn" title="Tageslast">${fmt(d.load)}</span>` : ""}</div>
      ${wln.length ? `<div class="wln tn">${wln.join("")}</div>` : ""}
      ${chips}
    </div>`;
  }

  _chip(a) {
    const sp = sportOf(a.group || a.type);
    const shares = a.dfa || a.zones;
    const zb = shares
      ? `<i class="zb"><s style="width:${shares[0]}%;background:${C.green}"></s><s style="width:${shares[1]}%;background:${C.amber}"></s><s style="width:${shares[2]}%;background:${C.red}"></s></i>`
      : "";
    return `<button class="chip" style="--sc:${sp.c}" data-act="act" data-id="${esc(a.id)}" title="${esc(a.name || sp.l)} öffnen">
      ${ico(sp.ic, sp.c, 16)}
      <span class="cn">${esc(a.name || sp.l)}</span>
      <span class="cd tn">${dur(a.moving_time)}</span>
      ${a.load != null ? `<span class="cl tn">${fmt(a.load)}</span>` : ""}
      ${zb}</button>`;
  }

  _planChip(p, d, today) {
    const sp = sportOf(p.group || p.type);
    const missed = !p.done && d.date < today;
    const stateIc = p.done ? ico("ok", C.green, 15) : missed ? ico("stop", C.red, 15) : ico("cal", C.tx3, 15);
    return `<div class="chip plan ${p.done ? "done" : ""} ${missed ? "missed" : ""}" style="--sc:${sp.c}" title="${p.done ? "erledigt" : missed ? "ausgelassen" : "geplant"}">
      ${stateIc}
      <span class="cn">${esc(p.name || sp.l)}</span>
      ${p.moving_time ? `<span class="cd tn">${dur(p.moving_time)}</span>` : ""}
      ${p.load != null ? `<span class="cl tn">${fmt(p.load)}</span>` : ""}
    </div>`;
  }

  /* ---------------- Fitness ---------------- */
  rFitness(pmc, rangeDays) {
    if (!pmc) return `<div class="card pad">Fitness-Kurve wird geladen …</div>`;
    const rows = pmc.slice(-rangeDays);
    if (rows.length < 3) return `<div class="card pad">Noch zu wenig Historie.</div>`;
    const n = rows.length;
    const ctl = rows.map((r) => r.ctl), atl = rows.map((r) => r.atl);
    const form = rows.map((r) => r.form), loadV = rows.map((r) => r.load || 0);
    const xt = [];
    for (const tick of monthTicks(rows.map((r) => r.date))) xt.push(tick);
    const [p0, p1] = domainOf([{ v: ctl }, { v: atl }]);
    const main = chart({
      h: 230, n, y0: Math.max(0, p0), y1: p1, grp: "pmc",
      s: [
        { t: "area", v: ctl, c: ROLE.ctl, op: 0.12 },
        { t: "line", v: ctl, c: ROLE.ctl, w: 2.4 },
        { t: "line", v: atl, c: ROLE.atl, w: 1.6 },
      ],
    });
    const loadMax = Math.max(1, ...loadV);
    const bars = chart({
      h: 86, n, y0: 0, y1: loadMax * 1.08, yticks: [Math.round(loadMax / 2), Math.round(loadMax)], grp: "pmc",
      s: [{ t: "bars", v: loadV, c: ROLE.dayload }], label: "Tageslast", labelc: C.tx3,
    });
    const [f0, f1] = domainOf([{ v: form }]);
    const fy0 = Math.min(f0, -32), fy1 = Math.max(f1, 22);
    const formCh = chart({
      h: 150, n, y0: fy0, y1: fy1, xt, grp: "pmc",
      bands: [
        { a: fy0, b: -30, c: C.red, op: 0.13 },
        { a: -30, b: -5, c: C.green, op: 0.12 },
        { a: -5, b: 10, c: C.tx3, op: 0.07 },
        { a: 10, b: 20, c: C.blue, op: 0.1 },
        { a: 20, b: fy1, c: C.amber, op: 0.12 },
      ],
      hl: [{ y: 0, c: C.tx3 }],
      s: [{ t: "line", v: form, c: ROLE.form, w: 2 }],
      label: "Form (Friel-Zonen: rot Risiko · grün optimal · grau neutral · blau frisch · gelb Übergang)", labelc: C.tx3,
    });
    this._grp.pmc = {
      n, xl: (i) => dMed(rows[i].date),
      rows: [
        { l: "Fitness (CTL)", c: ROLE.ctl, vals: ctl },
        { l: "Ermüdung (ATL)", c: ROLE.atl, vals: atl },
        { l: "Form", c: ROLE.form, vals: form },
        { l: "Tageslast", c: ROLE.dayload, vals: loadV },
      ],
    };
    const ranges = [[42, "42 T"], [91, "3 M"], [182, "6 M"], [365, "1 J"]];
    const last = rows[n - 1];
    return `
      <div class="bar">
        <div class="legend">
          <span class="lg" style="color:${ROLE.ctl}"><i class="sw" style="background:${ROLE.ctl}"></i>Fitness ${fmt(last.ctl)}</span>
          <span class="lg" style="color:${ROLE.atl}"><i class="sw" style="background:${ROLE.atl}"></i>Ermüdung ${fmt(last.atl)}</span>
          <span class="lg" style="color:${ROLE.form}"><i class="sw" style="background:${ROLE.form}"></i>Form ${sign(Math.round(last.form || 0))}</span>
        </div>
        <div class="chips">${ranges.map(([d, l]) => `<button class="chipbtn ${this._range === d ? "on" : ""}" data-act="range" data-id="${d}">${l}</button>`).join("")}</div>
      </div>
      <div class="card pad0" data-grp="pmc">${readout("pmc")}${main}${bars}${formCh}</div>
      <p class="hint pad">Mit der Maus über die Kurven fahren: alle drei Felder teilen sich eine Zeitachse und einen Ablese-Cursor.</p>`;
  }

  /* ---------------- Aktivitäten ---------------- */
  rAkt(list, sel) {
    if (!list) return `<div class="card pad">Aktivitäten werden geladen …</div>`;
    if (!list.length) return `<div class="card pad">Noch keine Aktivitäten im Archiv.</div>`;
    const miss = !sel && this._aktMiss
      ? `<div class="card pad err">Die Einheit <b>${esc(this._aktMiss)}</b> liegt nicht in den
         zuletzt geladenen ${fmt(list.length)} Einheiten — sie ist älter als der geladene Bereich.
         Die Schwellenmessung dazu steht weiterhin im DFA-Reiter.</div>` : "";
    const detail = sel ? this._aktDetail(sel) : "";
    const rows = list.slice(0, 120).map((a) => {
      const sp = sportOf(a.type);
      const dfaShares = this._dfaShares(a.dfa);
      const zb = dfaShares
        ? `<i class="zb w"><s style="width:${dfaShares[0]}%;background:${C.green}"></s><s style="width:${dfaShares[1]}%;background:${C.amber}"></s><s style="width:${dfaShares[2]}%;background:${C.red}"></s></i>`
        : `<span class="mut">–</span>`;
      const dec = a.decoupling;
      const decCls = dec == null ? "mut" : dec > 5 ? "warncol" : "okcol";
      const thr = a.dfa && a.dfa.hr_at_threshold
        ? `${fmt(a.dfa.hr_at_threshold)} bpm${a.dfa.threshold_samples < 5 ? " ⚠" : ""}` : "–";
      return `<button class="arow ${sel && String(sel.id) === String(a.id) ? "on" : ""}" data-act="act" data-id="${esc(a.id)}">
        <span class="aic" style="color:${sp.c}">${ico(sp.ic, sp.c, 20)}</span>
        <span class="anm"><b>${esc(a.name || sp.l)}</b><small>${dMed(a.start_date_local)} · ${sp.l}</small></span>
        <span class="tn">${dur(a.moving_time)}</span>
        <span class="tn">${a.distance ? kmf(a.distance) : "–"}</span>
        <span class="tn al">${a.icu_training_load != null ? fmt(a.icu_training_load) : "–"}</span>
        <span class="tn">${a.average_heartrate ? fmt(a.average_heartrate) : "–"}</span>
        <span class="tn ${decCls}">${dec != null ? fmt(dec, 1) + " %" : "–"}</span>
        <span>${zb}</span>
        <span class="tn">${thr}</span>
      </button>`;
    }).join("");
    return `${miss}${detail}
      <div class="card pad0">
        <div class="ahead">
          <span></span><span>Einheit</span><span>Dauer</span><span>Distanz</span><span>Last</span><span>Ø HF</span><span>Entkopplung</span><span>DFA-Verteilung</span><span>Schwelle</span>
        </div>
        ${rows}
      </div>`;
  }

  _dfaShares(s) {
    if (!s) return null;
    const total = (s.secs_aerobic || 0) + (s.secs_transition || 0) + (s.secs_anaerobic || 0);
    if (!total) return null;
    return [
      Math.round((s.secs_aerobic || 0) / total * 100),
      Math.round((s.secs_transition || 0) / total * 100),
      Math.round((s.secs_anaerobic || 0) / total * 100),
    ];
  }

  _aktDetail(a) {
    const sp = sportOf(a.type);
    const st = this._streams[a.id];
    const stat = (icon, label, val) => val == null || val === "–" ? "" :
      `<div class="kv">${ico(icon, C.tx3, 16)}<small>${label}</small><b class="tn">${val}</b></div>`;
    const kcal = a.calories, np = a.icu_weighted_avg_watts;
    const stats = [
      stat("clock", "Dauer", dur(a.moving_time)),
      stat("road", "Distanz", a.distance ? kmf(a.distance) : null),
      stat("mtn", "Höhenmeter", a.total_elevation_gain ? fmt(a.total_elevation_gain) + " m" : null),
      stat("flame", "Kalorien", kcal ? fmt(kcal) : null),
      stat("bolt", "Last", a.icu_training_load != null ? fmt(a.icu_training_load) : null),
      stat("gauge", "Intensität", a.icu_intensity ? fmt(a.icu_intensity) + " %" : null),
      stat("heart", "Ø / max Puls", a.average_heartrate ? `${fmt(a.average_heartrate)} / ${fmt(a.max_heartrate)} bpm` : null),
      stat("bolt", "Ø / NP Watt", a.icu_average_watts ? `${fmt(a.icu_average_watts)} / ${np ? fmt(np) : "–"} W` : null),
      stat("wave", "Entkopplung", a.decoupling != null ? fmt(a.decoupling, 1) + " %" : null),
      stat("trend", "EF", a.icu_efficiency_factor ? fmt(a.icu_efficiency_factor, 2) : null),
      stat("dot", "Kadenz", a.average_cadence ? fmt(a.average_cadence) + " rpm" : null),
      stat("user", "RPE / Gefühl", a.icu_rpe ? `${fmt(a.icu_rpe)}${a.feel ? " / " + fmt(a.feel) : ""}` : null),
    ].join("");
    let streamsHtml;
    if (!st) streamsHtml = `<div class="loading"><span class="spin"></span> Verlauf wird von Intervals geladen …</div>`;
    else if (st.error) streamsHtml = `<div class="err pad">Verlauf konnte nicht geladen werden: ${esc(st.error)}</div>`;
    else if (!st.points) streamsHtml = `<div class="mut pad">Für diese Einheit gibt es keine aufgezeichneten Datenströme.</div>`;
    else streamsHtml = this._streamPanels(st);
    return `<section class="card det">
      <div class="dethead">
        <span class="aic big" style="color:${C.tx2}">${ico(sp.ic, C.tx2, 26)}</span>
        <div><h2>${esc(a.name || sp.l)}</h2>
          <div class="detsub">${dMed(a.start_date_local)} · ${sp.l}${a.device_name ? " · " + esc(a.device_name) : ""}</div></div>
        <button class="chipbtn" data-act="close">Schließen</button>
      </div>
      <div class="kvgrid">${stats}</div>
      ${this._lapBlock(a)}
      ${this._lapCompare(a)}
      ${this._ctxBlock(a)}
      ${this._nightBlock(a)}
      <h3 class="secname">Verlauf <span class="hint">— gestapelte Felder, eine Zeitachse, ein Cursor: so siehst du, wie sich HF und DFA zur Leistung verhalten.</span></h3>
      ${streamsHtml}
      ${this._dfaBlock(a.dfa)}
    </section>`;
  }

  _streamPanels(st) {
    const ch = st.channels, secs = st.sample_secs || 1, n = st.points;
    const timeArr = ch.time || null;
    const tAt = (i) => timeArr && timeArr[i] != null ? timeArr[i] : i * secs;
    // A zero is a dropout in some channels and a real reading in others:
    // heart rate and DFA never legitimately reach zero, and a zero in the
    // power stream is a gap in the recording (the same zeros dfa_summary
    // filters server-side). Cadence and speed DO hit zero when standing
    // still, and altitude at sea level - those keep their zeros.
    const defs = [
      { k: "watts", l: "Leistung", u: "W", c: ROLE.pow, avg: 30, zeroIsGap: true },
      { k: "heartrate", l: "Herzfrequenz", u: "bpm", c: ROLE.hr, zeroIsGap: true },
      { k: "dfa_a1", l: "DFA alpha-1", u: "", c: ROLE.dfa, dec: 2, dfa: true, zeroIsGap: true },
      { k: "cadence", l: "Kadenz", u: "rpm", c: ROLE.cad },
      { k: "velocity_smooth", l: "Tempo", u: "km/h", c: ROLE.vel, mul: 3.6, dec: 1 },
      { k: "altitude", l: "Höhe", u: "m", c: ROLE.alt, area: true },
    ].filter((d) => ch[d.k] && ch[d.k].some((v) => d.zeroIsGap ? (v != null && v > 0) : v != null));
    if (!defs.length) return `<div class="mut pad">Keine darstellbaren Kanäle.</div>`;
    const xt = [];
    for (let i = 0; i < n; i += Math.max(1, Math.floor(n / 6))) xt.push({ i, t: hhmm(tAt(i)) });
    const rowsMeta = [];
    const panels = defs.map((d, idx) => {
      let vals = ch[d.k].map((v) => {
        if (v == null) return null;
        if (d.zeroIsGap && v <= 0) return null;
        return d.mul ? v * d.mul : v;
      });
      const series = [];
      let y0, y1;
      if (d.dfa) {
        y0 = 0.2; y1 = Math.max(1.6, ...vals.filter((v) => v != null)) * 1.05;
        series.push({ t: "line", v: vals, c: d.c, w: 1.6 });
      } else {
        [y0, y1] = domainOf([{ v: vals }]);
        if (d.k === "watts" || d.k === "cadence" || d.k === "velocity_smooth") y0 = 0;
        if (d.avg) {
          const win = Math.max(1, Math.round(d.avg / secs));
          series.push({ t: "line", v: vals, c: d.c, w: 1, lop: 0.3 });
          series.push({ t: "line", v: movAvg(vals, win), c: d.c, w: 2.2 });
        } else if (d.area) {
          series.push({ t: "area", v: vals, c: d.c, op: 0.3 });
          series.push({ t: "line", v: vals, c: d.c, w: 1.4 });
        } else {
          series.push({ t: "line", v: vals, c: d.c, w: 1.8 });
        }
      }
      rowsMeta.push({ l: d.l, c: d.c, u: d.u, vals, dec: d.dec || 0 });
      return chart({
        h: d.dfa ? 118 : 92, n, y0, y1, grp: "str",
        xt: idx === defs.length - 1 ? xt : null,
        bands: d.dfa ? [
          { a: 0.75, b: y1, c: C.green, op: 0.1 },
          { a: 0.5, b: 0.75, c: C.amber, op: 0.1 },
          { a: y0, b: 0.5, c: C.red, op: 0.1 },
        ] : [],
        hl: d.dfa ? [
          { y: 0.75, c: C.green, d: 1, t: "aerobe Schwelle 0,75" },
          { y: 0.5, c: C.red, d: 1, t: "anaerobe 0,5" },
        ] : [],
        s: series, label: `${d.l}${d.u ? " (" + d.u + ")" : ""}`, labelc: d.c,
        yf: (v) => fmt(v, d.dec || 0),
      });
    }).join("");
    this._grp.str = { n, xl: (i) => hhmm(tAt(i)) + " h", rows: rowsMeta };
    return `<div class="card2 pad0" data-grp="str">${readout("str")}${panels}</div>`;
  }

  /* Laps. The point of the table is not the single lap but the trend across
     a series: watts per heartbeat falling from one interval to the next is
     the body giving out, at constant external load. Hence EF and DFA get a
     bar each, scaled within this activity, and the drop is stated in words. */
  _lapBlock(a) {
    const data = this._laps[a.id];
    if (!data) return `<h3 class="secname">Runden</h3>
      <div class="loading"><span class="spin"></span> Runden werden geladen …</div>`;
    if (data.error) return `<h3 class="secname">Runden</h3>
      <div class="err pad">Runden konnten nicht geladen werden: ${esc(data.error)}</div>`;
    const laps = data.laps || [];
    if (!laps.length) return `<h3 class="secname">Runden</h3>
      <div class="mut pad">Für diese Einheit liefert Intervals keine Runden.</div>`;

    // Comparing warm-up against cool-down produces a nonsense "34% drop".
    // A verdict over a series is only allowed across COMPARABLE efforts:
    // the hard blocks, at similar power and similar duration. Everything
    // else - warm-up, recoveries, roll-outs - is excluded from the verdict
    // but still shown in the table.
    const powered = laps.filter((l) => (l.avg_watts || 0) > 0 && (l.moving_time || 0) >= 60);
    const peak = Math.max(0, ...powered.map((l) => l.avg_watts || 0));
    let work = powered.filter((l) => (l.avg_watts || 0) >= peak * 0.85);
    const durs = work.map((l) => l.moving_time || 0);
    const medDur = median(durs) || 0;
    work = work.filter((l) => medDur > 0 && Math.abs((l.moving_time || 0) - medDur) <= medDur * 0.35);
    const efs = work.map((l) => l.ef).filter((v) => v != null);
    const efMax = Math.max(1e-9, ...efs);
    const dfas = laps.map((l) => l.dfa_a1).filter((v) => v != null);
    const dfaMax = Math.max(1e-9, ...dfas);
    let verdict = "";
    if (efs.length >= 3) {
      const drop = (efs[0] - efs[efs.length - 1]) / efs[0] * 100;
      const st = drop > 8 ? "red" : drop > 3 ? "amber" : "green";
      verdict = `<div class="lapverdict">${badge(st, `${sign(-Math.round(drop * 10) / 10, 1)} % Watt pro Herzschlag über ${efs.length} vergleichbare Abschnitte`)}
        <span class="mut">${drop > 3
          ? "die Leistung je Herzschlag fällt — bei gleicher äußerer Last ist das Ermüdung"
          : "die Leistung je Herzschlag bleibt stehen — die Serie war verkraftbar"}</span></div>`;
    }
    const rows = laps.map((l) => {
      const rest = (l.avg_watts || 0) <= 0 || (l.moving_time || 0) < 60;
      const bar = (v, max, col) => v == null ? `<span class="mut">–</span>`
        : `<i class="lbar"><s style="width:${Math.max(3, Math.min(100, v / max * 100))}%;background:${col}"></s></i><b class="tn">${fmt(v, 2)}</b>`;
      return `<div class="lrow ${rest ? "rest" : ""}">
        <span class="tn ln">${l.n}</span>
        <span class="llbl">${esc(l.label || (rest ? "Pause" : "Intervall"))}${l.zone ? ` <em>${esc(l.zone)}</em>` : ""}</span>
        <span class="tn">${dur(l.moving_time)}</span>
        <span class="tn">${l.avg_watts != null ? fmt(l.avg_watts) + " W" : "–"}</span>
        <span class="tn">${l.avg_hr != null ? fmt(l.avg_hr) + " bpm" : "–"}</span>
        <span class="tn">${l.avg_cadence != null ? fmt(l.avg_cadence) : "–"}</span>
        <span class="lb">${bar(l.ef, efMax, ROLE.pow)}</span>
        <span class="lb">${bar(l.dfa_a1, dfaMax, ROLE.dfa)}</span>
      </div>`;
    }).join("");
    return `<h3 class="secname">Runden <span class="hint">— ${laps.length} Abschnitte${data.source ? `, Feld „${esc(data.source)}"` : ""}</span></h3>
      ${verdict}
      <div class="card2 pad0">
        <div class="lhead"><span>#</span><span>Abschnitt</span><span>Dauer</span><span>Ø Watt</span>
          <span>Ø HF</span><span>Kadenz</span><span>EF (W/Schlag)</span><span>DFA a1</span></div>
        ${rows}
      </div>`;
  }

  /* Comparing the blocks of an interval session.

     The first attempt put every lap in its own row. That is juxtaposition,
     and Gleicher's review names its weakness precisely: it leaves the work of
     relating the objects to the viewer. Worse, a scale shared across rows
     turns each individual curve into a flat line - comparable, and unreadable.

     So this uses the other two strategies instead, which is what the
     literature recommends when the objects ARE similar enough to share a
     space - four work blocks of equal length are exactly that:

     1. SUPERPOSITION: the work blocks laid over each other on a common
        "seconds into the block" axis, one line each, lightness encoding the
        order. Four lines stay well under the clutter limit where line charts
        start losing discriminability.
     2. EXPLICIT ENCODING via INDEXING (Bertin): every measure as a percentage
        of the first block, so power, heart rate and DFA - three units - fit
        one axis and all start at 100. In a controlled comparison indexing
        produced significantly fewer errors than either juxtaposition on a
        linear scale or superimposition on a log scale.

     Recoveries are not overlaid: their job is a different one, and they get
     their own number - how far the heart rate came back down. */
  /* The deviation table, as a general tool.

     It works on any ordered list of segments: the work blocks of an interval
     session, or the quarters of a steady ride. Rows are measures, columns are
     segments, and every bar is the deviation from the FIRST segment - length
     on a common baseline, which is the most accurately read encoding there
     is, with the number in its own unit next to it.

     This replaces the overlaid curves. Four noisy lines in one field is
     exactly the clutter that makes line charts lose their discriminability;
     aggregating into segments keeps the comparison and drops the knot. */
  _devTable(segments, measures, opts) {
    opts = opts || {};
    if (segments.length < 2) return "";
    const base = segments[0];
    const rest = segments.slice(1);
    const devs = measures.map((m) => rest.map((s) => {
      const v = m.get(s), b = m.get(base);
      return (v == null || b == null || !b) ? null : (v - b) / b * 100;
    }));
    const flat = devs.flat().filter((v) => v != null);
    if (!flat.length) return "";
    const span = Math.max(6, ...flat.map((v) => Math.abs(v))) * 1.15;

    const head = `<div class="devrow devhead2"><span></span><span class="devbars">
      ${rest.map((s) => `<span class="devcell colhead">${esc(s.label)}</span>`).join("")}
      </span></div>`;

    // A bar without a scale is an ordering, not a measurement: you can see
    // which is longer, but not by how much. The full half-width equals the
    // largest deviation in the whole table, so one tick set serves every row.
    const edge = Math.round(span);
    const foot = `<div class="devrow devfoot"><span></span><span class="devbars">
      ${rest.map(() => `<span class="devcell"><i class="devscale">
        <u style="left:2%">-${edge} %</u><u style="left:50%;transform:translateX(-50%)">0</u>
        <u style="right:2%">+${edge} %</u></i></span>`).join("")}
      </span></div>`;

    const rows = measures.map((m, k) => {
      const bars = rest.map((s, i) => {
        const v = devs[k][i];
        if (v == null) return `<span class="devcell"><i class="devbar"></i></span>`;
        const better = m.good === "up" ? v > 0 : v < 0;
        const col = Math.abs(v) < 1.5 ? C.tx3 : (better ? C.green : C.amber);
        const w = Math.min(46, Math.abs(v) / span * 46);
        const left = v < 0 ? 50 - w : 50;
        const side = v < 0 ? `right:${(50 + w + 2).toFixed(1)}%` : `left:${(50 + w + 2).toFixed(1)}%`;
        const absDelta = m.get(s) - m.get(base);
        return `<span class="devcell" title="${esc(s.label)}: ${sign(Math.round(v * 10) / 10, 1)} % gegenüber ${esc(base.label)}">
          <i class="devbar"><s style="left:${left}%;width:${w}%;background:${col}"></s>
            <b class="tn" style="${side};color:${col}">${sign(absDelta, m.dec)}${m.u}</b></i></span>`;
      }).join("");
      const values = segments.map((s) => m.get(s)).filter((v) => v != null);
      return `<div class="devrow">
        <span class="devlab"><i class="sw" style="background:${m.c}"></i>
          <span><b>${esc(m.l)}</b><em>${m.good === "up" ? "höher ist besser" : "niedriger ist besser"}${
            m.hint ? " · " + esc(m.hint) : ""}</em>
          ${values.length ? `<u class="devbase">${esc(base.label)}: ${fmt(m.get(base), m.dec)}${m.u}</u>` : ""}</span></span>
        <span class="devbars">${bars}</span></div>`;
    }).join("");

    return `<div class="devbox">
      <div class="devhead">Abweichung gegenüber <b>${esc(base.label)}</b>
        <span class="hint">— ${esc(opts.note || "die Zahl in ihrer eigenen Einheit, die Balkenlänge normiert, damit die Zeilen vergleichbar bleiben. Rechts heißt mehr, links weniger; grün günstig, gelb ungünstig.")}</span></div>
      ${head}${rows}${foot}</div>`;
  }

  /* Segment analysis for one activity.

     Two cases, one mechanism:
       - interval session: the work blocks are the segments
       - steady ride: the ride itself is cut into equal quarters

     The second case is the classic decoupling test made visible. Cardiac
     drift - heart rate rising at constant power - is the WHAT; whether watts
     per heartbeat held together is the SO WHAT. Friel's 5% is the working
     benchmark, trained riders often hold under 3%, recreational riders land
     at 5-10%. Cutting into quarters instead of halves adds the one thing the
     single number cannot say: WHEN it started. */
  _lapCompare(a) {
    const data = this._laps[a.id], st = this._streams[a.id];
    if (!st || st.error || !st.points) return "";
    const ch = st.channels || {}, time = ch.time || [];
    if (!time.length) return "";
    const at = (sec) => {
      let lo = 0, hi = time.length - 1;
      while (lo < hi) { const mid = (lo + hi) >> 1; if (time[mid] < sec) lo = mid + 1; else hi = mid; }
      return lo;
    };
    const stat = (key, i0, i1, zeroGap) => {
      const vals = (ch[key] || []).slice(i0, i1).filter((v) => v != null && (!zeroGap || v > 0));
      return vals.length ? vals.reduce((s, v) => s + v, 0) / vals.length : null;
    };
    const hrrAfter = (endSec) => {
      const iEnd = at(endSec), i60 = at(endSec + 60);
      if (!(ch.heartrate || []).length || i60 <= iEnd) return null;
      const tail = ch.heartrate.slice(Math.max(0, iEnd - 4), iEnd + 1).filter((v) => v > 0);
      const after = ch.heartrate[Math.min(i60, ch.heartrate.length - 1)];
      return (tail.length && after > 0) ? Math.max(...tail) - after : null;
    };

    const laps = ((data && data.laps) || []).filter((l) => l.start_s != null && l.end_s != null);
    const powered = laps.filter((l) => (l.avg_watts || 0) > 0 && (l.moving_time || 0) >= 60);
    const peak = Math.max(0, ...powered.map((l) => l.avg_watts || 0));
    let work = powered.filter((l) => (l.avg_watts || 0) >= peak * 0.85);
    const medDur = median(work.map((l) => l.moving_time || 0)) || 0;
    work = work.filter((l) => medDur > 0 && Math.abs((l.moving_time || 0) - medDur) <= medDur * 0.35);
    const isInterval = work.length >= 2 && work.length < laps.length;

    let segments, title, note, intro;
    if (isInterval) {
      segments = work.map((l) => ({
        label: "Block " + l.n,
        watts: l.avg_watts, hr: l.avg_hr, dfa: l.dfa_a1, ef: l.ef,
        hrr: hrrAfter(l.end_s),
      }));
      title = "Blockvergleich";
      intro = `${work.length} gleichartige Blöcke, jeder gegen den ersten gestellt`;
      note = "die Zahl in ihrer eigenen Einheit, die Balkenlänge normiert; grün günstig, gelb ungünstig.";
    } else {
      // steady ride: quarters of the moving time, warm-up minutes excluded
      const total = time[time.length - 1] - time[0];
      if (total < 20 * 60) return "";
      const startAt = time[0] + Math.min(600, total * 0.12);
      const usable = time[time.length - 1] - startAt;
      const parts = 4;
      segments = [];
      for (let k = 0; k < parts; k++) {
        const s0 = startAt + (k / parts) * usable, s1 = startAt + ((k + 1) / parts) * usable;
        const i0 = at(s0), i1 = at(s1);
        if (i1 - i0 < 3) continue;
        const w = stat("watts", i0, i1, true), hr = stat("heartrate", i0, i1, true);
        segments.push({
          label: `${k + 1}. Viertel`,
          watts: w, hr, dfa: stat("dfa_a1", i0, i1, true),
          ef: (w && hr) ? w / hr : null, hrr: null,
        });
      }
      title = "Wie sich die Fahrt entwickelt hat";
      intro = "die Fahrt in vier gleich lange Abschnitte geteilt, jeder gegen den ersten gestellt";
      note = "so wird sichtbar, WANN sich etwas ändert — die übliche Entkopplung vergleicht nur zwei Hälften und verschweigt den Zeitpunkt.";
    }
    if (segments.length < 2) return "";

    const measures = [
      { l: "Leistung", u: " W", dec: 0, c: ROLE.pow, get: (s) => s.watts, good: "up" },
      { l: "Herzfrequenz", u: " bpm", dec: 0, c: ROLE.hr, get: (s) => s.hr, good: "down" },
      { l: "DFA alpha-1", u: "", dec: 2, c: ROLE.dfa, get: (s) => s.dfa, good: "up" },
      { l: "Watt pro Herzschlag", u: "", dec: 2, c: C.blue, get: (s) => s.ef, good: "up" },
      { l: "Puls-Erholung", u: " bpm", dec: 0, c: C.magenta, get: (s) => s.hrr, good: "up",
        hint: "Abfall in den ersten 60 s der Pause danach" },
    ].filter((m) => m.get(segments[0]) != null && segments.some((s) => m.get(s) != null));
    if (!measures.length) return "";

    const base = segments[0], last = segments[segments.length - 1];
    const def = base.ef && last.ef ? (last.ef - base.ef) / base.ef * 100 : null;
    const dh = base.hr != null && last.hr != null ? last.hr - base.hr : null;
    const dd = base.dfa != null && last.dfa != null ? last.dfa - base.dfa : null;
    const dw = base.watts && last.watts ? (last.watts - base.watts) / base.watts * 100 : null;

    // the verdict, graded against the published benchmarks
    let head, body, tone;
    const drop = def == null ? null : -def;
    if (drop == null) {
      tone = "held"; head = "Kein Urteil möglich.";
      body = "Für Watt pro Herzschlag fehlen die Daten.";
    } else if (isInterval) {
      tone = drop > 3 ? "worse" : "held";
      head = drop > 3 ? "Die Serie hat abgebaut." : "Die Serie hat gehalten.";
      body = `Vom ersten zum letzten Block: ${dw != null ? `Leistung ${sign(Math.round(dw * 10) / 10, 1)} %` : ""}${
        dh != null ? ` · Puls ${sign(dh)} Schläge` : ""}${dd != null ? ` · DFA ${sign(dd, 2)}` : ""}${
        ` · Watt pro Herzschlag ${sign(Math.round(def * 10) / 10, 1)} %`}. ${
        drop > 3 ? "Mehr Puls für weniger Leistung bei gleicher Vorgabe — das ist Ermüdung über die Serie."
                 : "Leistung je Herzschlag praktisch unverändert — die Serie war verkraftbar."}`;
    } else {
      tone = drop > 5 ? "worse" : "held";
      const grade = drop <= 3 ? "unter 3 % — das ist das Niveau, das trainierte Fahrer halten"
        : drop <= 5 ? "unter 5 % — Friels Richtwert für eine tragende Grundlage"
        : drop <= 10 ? "zwischen 5 und 10 % — der Bereich, in dem Freizeitfahrer typischerweise liegen"
        : "über 10 % — die Einheit lag wahrscheinlich über der aeroben Schwelle, oder die Grundlage trägt diese Dauer noch nicht";
      head = `Entkopplung über die Fahrt: ${fmt(drop, 1)} %`;
      body = `${grade}. ${dh != null ? `Der Puls stieg um ${sign(dh)} Schläge` : ""}${
        dw != null ? ` bei ${sign(Math.round(dw * 10) / 10, 1)} % Leistung` : ""}. ` +
        "Ein steigender Puls bei gleicher Leistung ist die kardiale Drift — normal und bei " +
        "trainierten Fahrern schwächer ausgeprägt. Die Frage ist nicht, ob der Puls steigt, " +
        "sondern ob die Leistung je Herzschlag zusammenhält.";
    }

    const verdict = `<div class="cmpverdict ${tone}">
      ${ico(tone === "worse" ? "warn" : "ok", tone === "worse" ? C.amber : C.green, 18)}
      <div><b>${esc(head)}</b><span>${esc(body)}</span></div></div>`;

    const rests = laps.filter((l) => !work.includes(l) && (l.moving_time || 0) >= 60);
    let restBlock = "";
    if (isInterval && rests.length) {
      const rows = rests.map((r) => `<div class="restrow">
        <b>${r.n}</b><span>${esc(r.label || "Pause")}</span>
        <span class="tn">${dur(r.moving_time)}</span>
        <span class="tn">${r.avg_hr != null ? fmt(r.avg_hr) + " bpm" : "–"}</span>
        <span class="tn">${r.avg_watts != null ? fmt(r.avg_watts) + " W" : "–"}</span>
        <span class="tn">${r.dfa_a1 != null ? fmt(r.dfa_a1, 2) : "–"}</span>
      </div>`).join("");
      restBlock = `<details class="more"><summary>Übrige Abschnitte (${rests.length}) — Aufwärmen, Pausen, Ausfahren</summary>
        <div class="restgrid"><div class="restrow head"><b>#</b><span>Abschnitt</span>
          <span>Dauer</span><span>Ø HF</span><span>Ø Watt</span><span>DFA</span></div>${rows}</div></details>`;
    }

    return `<h3 class="secname">${title} <span class="hint">— ${esc(intro)}</span></h3>
      ${verdict}
      ${this._devTable(segments, measures, { note })}
      ${restBlock}`;
  }

  /* The night after the session.

     Sleep is the cleanest measurement condition available - no daily life in
     the way - and the night directly after a session is where the response
     shows: nocturnal heart rate up, ln(rMSSD) down, returning to resting
     values over minutes up to a full day depending mainly on intensity.

     Never read as "more damping means it was harder". The relation between
     load and HRV change is bell-shaped, so the comparison is always against
     THIS athlete's own usual answer to sessions of the same size. A night at
     -1.5 SD can be perfectly ordinary if that is what this rider always does
     after a session like this one. */
  /* Where this session sits among the rider's own comparable ones.

     A decoupling of 11.4% means nothing by itself. Friel's 5% is a population
     benchmark; what actually answers "is that a lot FOR ME" is the spread of
     this rider's own comparable rides. Drawn as a bullet-style range: the
     middle half of past sessions as a band, the median as a tick, this
     session as a dot - position on a common scale, the most accurately read
     encoding, with the percentile spelled out in words underneath. */
  _ctxBlock(a) {
    const c = this._ctx[a.id];
    if (!c || !c.available) return "";
    const entries = Object.entries(c.metrics || {});
    if (!entries.length) return "";

    const rows = entries.map(([key, m]) => {
      if (!m.enough) {
        return `<div class="ctxrow thin">
          <span class="ctxlab"><b>${esc(m.label)}</b></span>
          <span class="ctxval tn">${fmt(m.value, 2)}<small>${esc(m.unit)}</small></span>
          <span class="ctxbar"></span>
          <span class="ctxsay">nur ${m.n} vergleichbare Einheiten — zu wenig für eine Einordnung</span>
        </div>`;
      }
      const lo = Math.min(m.best, m.worst, m.value);
      const hi = Math.max(m.best, m.worst, m.value);
      const pad = (hi - lo) * 0.08 || 1;
      const pos = (v) => ((v - (lo - pad)) / ((hi + pad) - (lo - pad))) * 100;
      const band = [pos(Math.min(m.p25, m.p75)), pos(Math.max(m.p25, m.p75))];
      const good = m.verdict === "besser als sonst";
      const bad = m.verdict === "schlechter als sonst";
      const col = good ? C.green : bad ? C.amber : C.tx2;
      const share = m.good === "up" ? m.rank : 100 - m.rank;
      return `<div class="ctxrow">
        <span class="ctxlab"><b>${esc(m.label)}</b>
          <em>Median ${fmt(m.median, 2)}${esc(m.unit)} · ${m.n} Einheiten</em></span>
        <span class="ctxval tn" style="color:${col}">${fmt(m.value, 2)}<small>${esc(m.unit)}</small></span>
        <span class="ctxbar" title="mittlere Hälfte deiner Vergleichseinheiten: ${fmt(m.p25, 2)} bis ${fmt(m.p75, 2)}">
          <i class="ctxband" style="left:${band[0].toFixed(1)}%;width:${Math.max(1, band[1] - band[0]).toFixed(1)}%"></i>
          <i class="ctxmed" style="left:${pos(m.median).toFixed(1)}%"></i>
          <i class="ctxdot" style="left:${pos(m.value).toFixed(1)}%;background:${col}"></i>
        </span>
        <span class="ctxsay" style="color:${col}">${esc(m.verdict)}
          <em>${good || !bad ? "besser" : "schlechter"} als ${fmt(good || !bad ? share : 100 - share, 0)} % deiner Vergleichseinheiten</em></span>
      </div>`;
    }).join("");

    return `<h3 class="secname">Wie diese Einheit dasteht
      <span class="hint">— gegen ${c.peers} eigene Einheiten derselben Sportart, ähnlicher Intensität und Dauer</span></h3>
      <div class="ctxbox">
        <div class="ctxscale"><span>schlechter</span><span>mittlere Hälfte</span><span>besser</span></div>
        ${rows}
        <details class="more"><summary>Wie die Vergleichsgruppe gebildet wird</summary>
          <p class="src">${esc(c.note)}</p></details>
      </div>`;
  }

  _nightBlock(a) {
    const n = this._night[a.id];
    if (!n) return "";
    if (!n.available) {
      const why = n.reason === "no_wellness"
        ? "Für die Nacht danach liegen keine Wellness-Werte vor."
        : "Die Nacht danach lässt sich für diese Einheit nicht auswerten.";
      return `<h3 class="secname">Die Nacht danach</h3><p class="hint pad">${esc(why)}</p>`;
    }
    const TONE = { hard: "worse", costly: "worse", usual: "held", easy: "held", unknown: "held" };
    const tone = TONE[n.state] || "held";
    const rows = Object.entries(n.night || {}).map(([key, entry]) => {
      const ref = (n.reference || {})[key];
      const delta = ref && ref.sd > 0 ? (entry.z - ref.mean) / ref.sd : null;
      const col = delta == null ? C.tx3 : delta <= -1 ? C.amber : delta >= 1 ? C.green : C.tx3;
      const dec = entry.unit === "h" ? 1 : 0;
      const usual = ref ? `üblich nach solchen Einheiten ${sign(ref.mean, 1)} SD`
                        : "zu wenige Vergleichsnächte";
      return `<div class="nrow">
        <span class="nlab"><b>${esc(entry.label)}</b>
          <em>deine Basislinie ${fmt(entry.baseline, dec)} ${esc(entry.unit)}</em></span>
        <span class="nval tn">${fmt(entry.value, dec)}<small>${esc(entry.unit)}</small></span>
        <span class="nz tn" style="color:${col}">${sign(entry.z, 1)} SD</span>
        <span class="nref">${esc(usual)}${
          delta != null ? ` · diese Nacht ${sign(Math.round(delta * 10) / 10, 1)} SD davon` : ""}</span>
      </div>`;
    }).join("");

    return `<h3 class="secname">Die Nacht danach
      <span class="hint">— ${esc(n.night_date || "")}, gegen deine eigene übliche Antwort auf Einheiten dieser Größe</span></h3>
      <div class="cmpverdict ${tone}">
        ${ico(tone === "worse" ? "warn" : "ok", tone === "worse" ? C.amber : C.green, 18)}
        <div><b>${esc(n.headline || "")}</b><span>${esc(n.detail || "")}</span></div></div>
      <div class="nightbox">${rows}
        <details class="more"><summary>Wie das zu lesen ist</summary>
          <p class="src">${esc(n.caveat || "")}</p></details></div>`;
  }

  _dfaBlock(s) {
    if (!s || !s.samples) return "";
    const shares = this._dfaShares(s) || [0, 0, 0];
    const rowsHtml = [
      ["aerob (über 0,75)", shares[0], C.green, s.secs_aerobic],
      ["Übergang", shares[1], C.amber, s.secs_transition],
      ["anaerob (unter 0,5)", shares[2], C.red, s.secs_anaerobic],
    ].map(([l, p, col, secs]) => `<div class="dfar">
        <span>${l}</span>
        <i class="dbar"><s style="width:${p}%;background:${col}"></s></i>
        <b class="tn">${p} %</b><small class="tn">${dur(secs)}</small>
      </div>`).join("");
    const weak = (s.threshold_samples || 0) < 5;
    return `<h3 class="secname">DFA alpha-1 dieser Einheit</h3>
      <div class="dfabox">${rowsHtml}
        ${s.hr_at_threshold ? `<div class="dfathr">Aerobe Schwelle abgelesen bei
          <b class="tn">${fmt(s.hr_at_threshold)} bpm</b>
          ${s.power_at_threshold ? `· <b class="tn">${fmt(s.power_at_threshold)} W</b>` : ""}
          ${badge(weak ? "amber" : "green", `${s.threshold_samples} Messpunkte${weak ? " — dünn" : ""}`)}
        </div>` : ""}
        <p class="src">Rogers und Gronwald: DFA alpha-1 0,75 ≈ aerobe Schwelle (VT1), 0,5 ≈ anaerobe (VT2). Die Validierungslage ist gemischt: gegen Spiroergometrie stimmt VT1 nur schwach überein (weite Übereinstimmungsgrenzen, bei Fitteren wird die Schwelle eher unterschätzt); VT2 ist robuster. Als Trend am eigenen Körper brauchbar, als alleinige Verankerung nicht — dazu empfindlich für Artefakte und Aufzeichnungsgerät.</p>
      </div>`;
  }

  /* ---------------- Belastung ---------------- */
  rBelastung(load) {
    if (!load) return `<div class="card pad">Belastungsdaten werden geladen …</div>`;
    const sec = (icon, title, readAs, body, source) => `
      <section class="card">
        <div class="sechead">${ico(icon, C.tx2, 20)}<h3>${title}</h3></div>
        <p class="readas">Zu lesen als: ${readAs}</p>
        ${body}
        <details class="more"><summary>Quelle und Grenzen</summary><p class="src">${source}</p></details>
      </section>`;

    /* weekly load */
    const weeks = (load.weeks || []).slice(-20);
    let weeklyHtml = `<p class="mut">Noch keine Wochen im Archiv.</p>`;
    if (weeks.length) {
      const loads = weeks.map((w) => w.load);
      const avg = meanOf(loads);
      const maxL = Math.max(1, ...loads);
      const xt = weeks.map((w, i) => i % Math.ceil(weeks.length / 8) === 0 ? { i, t: "KW " + (+w.week.split("-W")[1]) } : null).filter(Boolean);
      const dots = weeks.map((w, i) => (w.monotony != null && w.monotony >= (load.thresholds || {}).monotony_watch)
        ? { i, v: w.load + maxL * 0.06, c: C.amber, r: 4 } : null).filter(Boolean);
      weeklyHtml = chart({
        h: 200, n: weeks.length, y0: 0, y1: maxL * 1.16, xt,
        hl: avg != null ? [{ y: avg, c: C.tx2, d: 1, t: "Mittel " + fmt(avg) }] : [],
        s: [{ t: "bars", v: loads, c: ROLE.series, op: 0.8 }, { t: "dots", p: dots, c: C.amber }],
      }) + `<p class="hint">${ico("warn", C.amber, 13)} Punkt über dem Balken = Monotonie ≥ 2 (Woche ohne echten Ruhetag).</p>`;
    }

    /* ACWR */
    const acwr = load.acwr || [];
    let acwrHtml = `<p class="mut">Noch kein volles 28-Tage-Fenster.</p>`;
    if (acwr.some((x) => x.ratio != null)) {
      const raw = acwr.map((x) => x.ratio);
      // A single spike used to stretch the axis to 4.0 and squash the whole
      // corridor into the bottom sliver. Cap the axis just above the corridor,
      // clamp what sticks out and mark it, so the readable range stays readable.
      const hi = 2.2;
      const vals = raw.map((v) => v == null ? null : Math.min(v, hi));
      const over = raw.map((v, i) => (v != null && v > hi) ? { i, v: hi, c: C.red, r: 4.4 } : null).filter(Boolean);
      const xt = monthTicks(acwr.map((x) => x.date));
      const la = load.acwr_latest;
      const laState = la ? (la.ratio > 1.5 ? "red" : la.ratio > 1.3 ? "amber" : "green") : "unknown";
      acwrHtml = `<div class="statrow">
          <b class="tn big2">${la ? fmt(la.ratio, 2) : "–"}</b>
          ${badge(laState, la ? (la.ratio > 1.5 ? "deutlich über dem Korridor" : la.ratio > 1.3 ? "über dem Korridor" : la.ratio < 0.8 ? "unter dem Korridor — Luft" : "im Korridor") : undefined)}
        </div>` + chart({
        h: 210, n: acwr.length, y0: 0.3, y1: hi, xt, yf: (v) => fmt(v, 1),
        bands: [
          { a: 0.8, b: 1.3, c: C.green, op: 0.11 },
          { a: 1.3, b: 1.5, c: C.amber, op: 0.12 },
          { a: 1.5, b: hi, c: C.red, op: 0.12 },
        ],
        hl: [
          { y: 0.8, c: C.green, d: 1, t: "Korridor ab 0,8", side: "left" },
          { y: 1.3, c: C.green, d: 1, t: "Korridor bis 1,3" },
          { y: 1.5, c: C.red, d: 1, t: "erhöht ab 1,5", side: "left" },
        ],
        s: [
          { t: "line", v: vals, c: ROLE.series, w: 2.2 },
          { t: "dots", p: over, c: C.red },
        ],
      }) + (over.length ? `<p class="hint">${ico("warn", C.amber, 13)} ${over.length} Tag(e) über ${fmt(hi, 1)} — für die Lesbarkeit an der Achse geklemmt, Höchstwert ${fmt(Math.max(...raw.filter((v) => v != null)), 2)}.</p>` : "");
    }

    /* intensity */
    const iBar = (d, labels) => {
      if (!d) return `<p class="mut">keine Daten</p>`;
      const parts = labels.map(([k, col]) => [d[k], col]);
      let x = 0;
      const segs = parts.map(([p, col]) => {
        const s = `<div class="iseg" style="left:${x}%;width:${p}%;background:${col}"><span>${fmt(p, 0)} %</span></div>`;
        x += p; return s;
      }).join("");
      return `<div class="ibar">${segs}<i class="iref" style="left:75%" title="Elite-Referenz: 75 % locker"></i><i class="iref" style="left:83%" title="75 + 8 %"></i></div>`;
    };
    const intHtml = `
      <div class="ilbl">Nach Trainingszonen (${(load.intensity || {}).days || 90} Tage, ${(load.intensity || {}).sessions || 0} Einheiten, ${fmt((load.intensity || {}).hours, 1)} h)</div>
      ${iBar(load.intensity, [["low", C.green], ["middle", C.amber], ["high", C.red]])}
      <div class="ilbl">Nach DFA alpha-1 gemessen (${(load.dfa_distribution || {}).days || 90} Tage, ${(load.dfa_distribution || {}).sessions || 0} Einheiten)</div>
      ${iBar(load.dfa_distribution, [["aerobic", C.green], ["transition", C.amber], ["anaerobic", C.red]])}
      <div class="legend" style="margin-top:8px">
        <span class="lg" style="color:${C.green}"><i class="sw" style="background:${C.green}"></i>locker / aerob</span>
        <span class="lg" style="color:${C.amber}"><i class="sw" style="background:${C.amber}"></i>Schwelle / Übergang</span>
        <span class="lg" style="color:${C.red}"><i class="sw" style="background:${C.red}"></i>hart / anaerob</span>
        <span class="lg">| Striche: Elite-Referenz 75 / 8 / 17</span>
      </div>`;

    /* HRV */
    const hrv = load.hrv;
    let hrvHtml = `<p class="mut">Unter 14 HRV-Tagen — noch kein Trend.</p>`;
    if (hrv && hrv.series && hrv.series.length > 2) {
      const seriesArr = hrv.series.slice(-120);
      const vals = seriesArr.map((x) => x.ln_rmssd_7d);
      const [h0, h1] = domainOf([{ v: vals }, { v: [hrv.baseline - hrv.swc * 1.4, hrv.baseline + hrv.swc * 1.4] }]);
      const xt = monthTicks(seriesArr.map((x) => x.date));
      const hst = hrv.state === "below" ? "amber" : "green";
      hrvHtml = `<div class="statrow"><b class="tn big2">${fmt(hrv.latest, 3)}</b>
          ${badge(hst, hrv.state === "below" ? "unter der Basislinie" : hrv.state === "above" ? "über der Basislinie" : "im Normalbereich")}
          <span class="mut">Basislinie ${fmt(hrv.baseline, 3)} ± ${fmt(hrv.swc, 3)}</span></div>` +
        chart({
          h: 200, n: seriesArr.length, y0: h0, y1: h1, xt, yf: (v) => fmt(v, 2),
          bands: [{ a: hrv.baseline - hrv.swc, b: hrv.baseline + hrv.swc, c: C.blue, op: 0.14 }],
          hl: [{ y: hrv.baseline, c: C.tx2, d: 1, t: "Basislinie" }],
          s: [{ t: "line", v: vals, c: ROLE.series, w: 2.2 }],
        });
    }

    /* decoupling */
    const dcp = load.decoupling || [];
    let dcpHtml = `<p class="mut">Keine ausreichend langen, ruhigen Einheiten.</p>`;
    if (dcp.length) {
      const vals = dcp.map((x) => x.decoupling);
      const [d0, d1] = domainOf([{ v: vals }, { v: [-2, 8] }]);
      const pts = dcp.map((x, i) => ({
        i, v: x.decoupling,
        c: x.decoupling > 5 ? C.amber : x.decoupling <= 0 ? C.green : ROLE.series, r: 4,
      }));
      const xt = monthTicks(dcp.map((x) => x.date));
      dcpHtml = chart({
        h: 190, n: dcp.length, y0: d0, y1: d1, xt, yf: (v) => fmt(v, 0) + " %",
        hl: [{ y: 5, c: C.amber, d: 1, t: "5 %-Marke" }, { y: 0, c: C.tx3 }],
        s: [{ t: "dots", p: pts, c: ROLE.series }],
      });
    }

    const T = load.thresholds || {};
    return sec("bolt", "Wochenlast, Monotonie, Strain",
        "Balkenhöhe = Wochensumme der Last; der gelbe Punkt markiert eintönige Wochen.",
        weeklyHtml,
        "Foster: Monotonie = Wochenmittel der Tageslast geteilt durch ihre Streuung, Strain = Wochenlast × Monotonie. Unter drei Trainingstagen sagt der Wert nichts — die Ruhetage bestimmen dann die Streuung.")
      + sec("trend", "Akute zu chronischer Last (ACWR)",
        `im grünen Band ${fmt(T.acwr_low, 1)}–${fmt(T.acwr_high, 1)} unauffällig, ab ${fmt(T.acwr_risk, 1)} erhöht.`,
        acwrHtml,
        "Gabbett/Blanch. Die Belege sind korrelativ und mathematisch gekoppelt; eine formelle Richtigstellung wurde beantragt, eine randomisierte Studie fand keinen Nutzen. Als Indikator lesen, nie als Urteil.")
      + sec("gauge", "Intensitätsverteilung",
        "zwei Sichten auf dieselbe Frage — geplante Zonen oben, gemessene DFA-Bänder darunter. Große Abweichung zwischen beiden heißt: die Zonen passen nicht zu deiner Physiologie.",
        intHtml,
        "Dreizonenmodell nach Seiler; Elite-Ausdauersportler liegen etwa bei 75/8/17. Polarisiert liegt beim VO2peak knapp vorn und wird bestritten. Die DFA-Sicht braucht keine Schwellen-Einstellungen, ist aber artefaktempfindlich.")
      + sec("heart", "HRV-Trend",
        "die Linie soll im blauen Band (Basislinie ± kleinste bedeutsame Änderung) bleiben; darunter = erhöhte Beanspruchung.",
        hrvHtml,
        "7-Tage-Mittel von ln(rMSSD) gegen Mittelwert ± 0,5 SD der Basisperiode (HRV-gesteuerte Trainingssteuerung). Dein Wert kommt aus der Nachtmessung der Uhr, nicht aus der validierten Morgenmessung im Liegen — als Trend brauchbar, als Absolutwert nicht.")
      + sec("wave", "Entkopplung",
        "Punkte über der 5 %-Marke bei ruhigen, langen Einheiten deuten auf eine dünne aerobe Basis; Werte um oder unter null sind gut.",
        dcpHtml,
        "Joe Friel: ≤ 5 % auf gleichmäßigen aeroben Einheiten heißt, die Grundlage steht. Nur bei gleichmäßiger Fahrt aussagekräftig — kurze oder spitzige Einheiten sind hier bereits herausgefiltert (min. 45 min).");
  }

  /* ---------------- DFA ---------------- */
  /* The DFA tab: a scatter of threshold readings over a graph, the same
     readings as a table below, and ONE selection state across both.

     Four traps sit in the time window, and all four are the same mistake in
     different clothes - letting the view change a number it must not change:
     the headline stays window-independent, a median line needs five solid
     readings or it is not drawn, the y axis is scaled over the whole stock
     rather than per window, and the list follows the window or a point in
     the graph has no row. */
  rDfa(thr, sportFilter) {
    if (!thr) return `<div class="card pad">DFA-Daten werden geladen …</div>`;
    // Ride and VirtualRide are both "Rad" - filtering on the raw type listed
    // the same label twice and split the season in half.
    const groups = [];
    for (const x of thr) {
      const g = groupKey(x.type);
      if (g && !groups.includes(g)) groups.push(g);
    }
    const sportName = sportFilter === "all" ? "alle Sportarten" : (SPORT[sportFilter] || {}).l || sportFilter;
    // The sport is a different axis from the window, and it MAY move the
    // headline - the aerobic threshold on foot is not the one on the bike.
    // What must not happen is that it moves it silently, so the source line
    // below names the sport it was computed from.
    const all = thr.filter((x) => sportFilter === "all" || groupKey(x.type) === sportFilter);
    if (!all.length) return `<div class="card pad">Noch keine Schwellen-Messungen${sportFilter !== "all" ? " für diese Sportart" : ""}.</div>`;

    const isSolid = (x) => (x.samples || 0) >= 5 && x.hr != null && x.hr > 0;
    const solidAll = all.filter(isSolid);
    // TRAP 1: the headline is computed over the whole stock, never over the
    // window. Otherwise the aerobic threshold changes because somebody
    // zoomed - two ways to answer one question, the defect class that has
    // cost this project four releases.
    const cur = median(solidAll.slice(-5).map((x) => x.hr));
    const first = median(solidAll.slice(0, 5).map((x) => x.hr));
    const curW = median(solidAll.slice(-5).map((x) => x.power).filter((v) => v != null));
    // the deviation column reads against a rolling median over the whole
    // stock as well, for the same reason
    const rollAll = rollMedian(all.map((x) => (isSolid(x) ? x.hr : null)), 5);
    const rollBy = {};
    all.forEach((x, i) => { rollBy[x.activity_id] = rollAll[i]; });

    const win = this._win.dfa || { id: WIN_DEFAULT };
    const w = winApply(all, win, this._now());
    const rows = w.rows;
    const solid = rows.filter(isSolid);
    const n = rows.length;
    const winLabel = `${fmt(w.kept)} von ${fmt(w.total)} Einheiten im Fenster`;
    const picker = winChips("dfa", win, this._now());

    if (!n) {
      return `${this._dfaExplain()}
        ${this._dfaBar(groups, sportFilter, picker)}
        <div class="card pad">Keine Messung in diesem Zeitraum — von ${fmt(w.total)} insgesamt.
        Ein anderes Fenster wählen oder auf den Graphen doppelklicken.</div>`;
    }

    const avgAll = meanOf(solid.map((x) => x.hr));
    // TRAP 3: the y axis is built from the SOLID readings of the whole stock,
    // not of the window - otherwise every window looks equally dramatic. A
    // zero threshold is a recording artefact and a single-sample reading off
    // a walk is not a threshold either: both used to stretch the axis from 0
    // to 160 and squash the real range into a line.
    const solidHr = solidAll.map((x) => x.hr).filter((v) => v != null && v > 0);
    let [y0a, y1a] = solidHr.length >= 2
      ? domainOf([{ v: solidHr }], 0.14)
      : domainOf([{ v: all.map((x) => x.hr).filter((v) => v > 0) }]);
    if (!(y1a > y0a)) { y0a = 100; y1a = 180; }
    const xt = monthTicks(rows.map((x) => x.date));
    let clamped = 0;
    // The fixed pick is part of the RENDER, the hover is not. That is the
    // flüchtig/fest split of the pattern, and it means the marked state
    // survives a re-render and can be checked without a browser.
    // De-emphasis beats emphasis at fifty points: dim the others rather than
    // brighten the hit - and the ring is a SHAPE, so the mark does not rest
    // on colour alone.
    const pick = this._dfaPick;
    const pts = rows.map((x, i) => {
      if (x.hr == null || x.hr <= 0) return null;
      const solidPt = (x.samples || 0) >= 5;
      const v = Math.max(y0a, Math.min(y1a, x.hr));
      if (v !== x.hr) clamped++;
      const hit = !!pick && x.activity_id === pick;
      const baseR = solidPt ? 4 : 3;
      const baseOp = solidPt ? 1 : 0.6;
      // hollow points carry no usable reading and stay unpickable
      return { i, v, c: solidPt ? ROLE.series : C.grey,
               f: solidPt, r: hit ? baseR + 2 : baseR,
               op: pick ? (hit ? 1 : 0.35) : baseOp,
               ring: hit,
               id: solidPt ? x.activity_id : null };
    }).filter(Boolean);
    // the row list the pointer handlers index into - same order as the graph
    this._dfaRows = rows.map((x) => ({
      date: x.date, activity_id: x.activity_id, pickable: isSolid(x),
    }));

    // TRAP 2: a median line needs five solid readings. A trend through three
    // points is the 0.13.0 mistake in new clothes - and it is LEFT OUT, not
    // drawn thin: a faint wrong line is still a wrong line.
    const enoughForMedian = solid.length >= 5;
    const roll = enoughForMedian
      ? rollMedian(rows.map((x) => (isSolid(x) ? x.hr : null)), 5) : null;
    const series = [{ t: "dots", p: pts, c: ROLE.series }];
    if (roll) series.push({ t: "line", v: roll, c: ROLE.series, w: 2.4 });

    const mainCh = chart({
      h: 260, n, y0: y0a, y1: y1a, xt, grp: "dfa",
      extra: `<rect class="dragsel" x="0" y="0" width="0" height="100%" fill="${ROLE.series}" opacity="0"/>`,
      hl: avgAll != null ? [{ y: avgAll, c: C.tx3, d: 1, t: "Schnitt " + fmt(avgAll) }] : [],
      s: series,
      label: "Schwellen-Herzfrequenz (bpm)", labelc: ROLE.series,
    })
      + (enoughForMedian ? "" : `<p class="hint">${ico("warn", C.amber, 13)} Nur ${solid.length} belastbare Messung(en) in diesem Fenster — unter fünf wird keine Medianlinie gezeichnet.</p>`)
      + (clamped ? `<p class="hint">${ico("warn", C.amber, 13)} ${clamped} Messung(en) außerhalb des dargestellten Bereichs — an der Achse geklemmt, damit der belastbare Bereich lesbar bleibt.</p>` : "");

    const powRows = rows.map((x) => ((x.samples || 0) >= 5 ? x.power : null));
    let powCh = "";
    if (powRows.some((v) => v != null)) {
      const [p0, p1] = domainOf([{ v: all.map((x) => (isSolid(x) ? x.power : null)) }]);
      powCh = chart({
        h: 130, n, y0: p0, y1: p1, grp: "dfa",
        s: [
          { t: "dots", p: rows.map((x, i) => (powRows[i] != null
              ? { i, v: powRows[i], c: ROLE.pow, r: pick && x.activity_id === pick ? 5.4 : 3.4,
                  op: pick ? (x.activity_id === pick ? 1 : 0.35) : 1,
                  ring: !!pick && x.activity_id === pick,
                  id: isSolid(x) ? x.activity_id : null } : null)).filter(Boolean), c: ROLE.pow },
          ...(enoughForMedian ? [{ t: "line", v: rollMedian(powRows, 5), c: ROLE.pow, w: 2 }] : []),
        ],
        label: "Schwellen-Leistung (W) — eigenes Feld statt zweiter Achse", labelc: ROLE.pow,
      });
    }
    this._grp.dfa = {
      n, xl: (i) => dMed(rows[i].date),
      rows: [
        { l: "Schwelle", c: C.blue, vals: rows.map((x) => x.hr), u: "bpm" },
        { l: "Leistung", c: ROLE.pow, vals: rows.map((x) => x.power), u: "W" },
        { l: "Messpunkte", c: C.tx2, vals: rows.map((x) => x.samples) },
      ],
    };

    // TRAP 4: the list follows the window, or A1 breaks - a point in the
    // graph without a row. Capped at 50 with the cap SPOKEN: a list that
    // stops at fifteen without saying so was half the trap, and one that
    // silently renders four hundred rows is the other half.
    const CAP = 50;
    const shown = rows.slice(-CAP).reverse();
    const capped = w.kept > CAP;
    const tableRows = shown.map((x) => {
      const weak = (x.samples || 0) < 5;
      const sp = sportOf(x.type);
      const base = rollBy[x.activity_id];
      const dev = (!weak && x.hr != null && base != null) ? x.hr - base : null;
      const devCls = dev == null ? "mut" : Math.abs(dev) >= 3 ? "warncol" : "okcol";
      const dec = x.decoupling;
      const decCls = dec == null ? "mut" : dec > 5 ? "warncol" : "okcol";
      const marked = this._dfaPick === x.activity_id;
      return `<button class="trow ${weak ? "weak" : ""} ${marked ? "brushed" : ""}"
          data-aid="${esc(x.activity_id)}" data-act="dfapick" data-id="${esc(x.activity_id)}"
          title="${esc(x.name || sportOf(x.type).l)} — klicken markiert, Doppelpfeil öffnet die Einheit">
        <span>${dMed(x.date)}</span>
        <span style="color:${sp.c}">${ico(sp.ic, sp.c, 15)}${sp.l}</span>
        <span class="tn">${fmt(x.hr)} bpm</span>
        <span class="tn ${devCls}">${dev == null ? "–" : sign(Math.round(dev)) + " bpm"}</span>
        <span class="tn">${x.power ? fmt(x.power) + " W" : "–"}</span>
        <span class="tn">${dur(x.moving_time)}</span>
        <span class="tn">${x.load != null ? fmt(x.load) : "–"}</span>
        <span class="tn">${x.avg_hr ? fmt(x.avg_hr) + " bpm" : "–"}</span>
        <span class="tn ${decCls}">${dec != null ? fmt(dec, 1) + " %" : "–"}</span>
        <span>${weak ? badge("amber", x.samples + " Punkte — dünn") : badge("green", x.samples + " Punkte")}</span>
        <span class="gobox"><i class="go" data-act="gotoact" data-id="${esc(x.activity_id)}"
          title="Einheit öffnen">${ico("chev", C.tx2, 16)}</i></span>
      </button>`;
    }).join("");

    const pickRow = this._dfaPick ? all.find((x) => x.activity_id === this._dfaPick) : null;
    const clearBar = pickRow
      ? `<div class="bar pickbar">${ico("dot", ROLE.series, 12)}
          <span>Ausgewählt: <b>${esc(pickRow.name || sportOf(pickRow.type).l)}</b> vom ${dMed(pickRow.date)}</span>
          <button class="chipbtn" data-act="dfaclear">Auswahl aufheben</button>
          <button class="chipbtn" data-act="gotoact" data-id="${esc(pickRow.activity_id)}">Einheit öffnen</button>
        </div>` : "";

    return `
      ${this._dfaExplain()}
      ${this._dfaBar(groups, sportFilter, picker)}
      <div class="statgrid card lead">
        <div class="stat wide"><small>Aktuelle aerobe Schwelle</small>
          <b class="tn lead1" style="color:${ROLE.series}">${cur ? fmt(cur) : "–"} <span class="unit">bpm</span></b>
          <span class="mut">Median der letzten 5 belastbaren Messungen · ${esc(sportName)} · über den gesamten Bestand, nicht über das Fenster</span></div>
        <div class="sidestats">
          <div class="stat"><small>bei Leistung</small><b class="tn small2">${curW ? fmt(curW) : "–"} <span class="unit">W</span></b></div>
          <div class="stat"><small>Veränderung</small><b class="tn small2">${cur != null && first != null ? sign(Math.round(cur - first)) : "–"} <span class="unit">bpm</span></b></div>
          <div class="stat"><small>Messungen</small><b class="tn small2">${solid.length}</b><span class="mut">belastbar im Fenster · ${n - solid.length} dünn</span></div>
        </div>
      </div>
      ${clearBar}
      <div class="card pad0" data-grp="dfa">${readout("dfa")}${mainCh}${powCh}
        <p class="hint pad">${winLabel}. Ziehen im Graphen wählt einen eigenen Zeitraum, Doppelklick setzt zurück.</p></div>
      <div class="card pad0">
        <div class="thead dfahead"><span>Datum</span><span>Sport</span><span>Schwelle</span>
          <span title="Abweichung gegen den rollierenden Median über den gesamten Bestand">Δ Median</span>
          <span>Leistung</span><span>Dauer</span><span>Last</span><span>Ø HF</span>
          <span>Entkopplung</span><span>Güte</span><span></span></div>
        ${tableRows}
        ${capped ? `<p class="hint pad">${fmt(CAP)} von ${fmt(w.kept)} Zeilen gezeigt — die neuesten. Ein engeres Fenster zeigt den Rest.</p>` : ""}
      </div>`;
  }

  _dfaExplain() {
    return `<div class="card explain">
        <p><b>DFA alpha-1</b> beschreibt, wie geordnet dein Herzschlagmuster ist. Der Wert sinkt mit der Intensität:
        bei <b style="color:${C.green}">0,75</b> liegt die aerobe Schwelle, bei <b style="color:${C.red}">0,5</b> die anaerobe.
        Unten steht, bei welcher Herzfrequenz deine Kurve in jeder Einheit durch 0,75 fällt — deine aerobe Schwelle, aus dem Training selbst gemessen, ohne Labortest.</p>
        <details class="more"><summary>Quelle und Grenzen</summary><p class="src">Rogers und Gronwald, gegen Spiroergometrie geprüft: die Übereinstimmung an der aeroben Schwelle ist schwach (weite Grenzen, fitnessabhängiger Bias), an der anaeroben robuster — als Trend brauchbar, als alleinige Verankerung nicht. Empfindlich für Artefakte und Aufzeichnungsgerät — deshalb zählen nur Messungen mit genügend Punkten im Schwellenfenster voll (ausgefüllte Punkte); dünne Messungen sind hohl und grau.</p></details>
      </div>`;
  }

  _dfaBar(groups, sportFilter, picker) {
    return `<div class="bar">
        <div class="chips">
          <button class="chipbtn ${sportFilter === "all" ? "on" : ""}" data-act="dfasport" data-id="all">Alle Sportarten</button>
          ${groups.map((g) => `<button class="chipbtn ${sportFilter === g ? "on" : ""}" data-act="dfasport" data-id="${esc(g)}">${SPORT[g].l}</button>`).join("")}
        </div>
      </div>
      <div class="bar">${picker}</div>`;
  }

  /* ---------------- Plan ---------------- */
  _css() {
    return `
:host{display:block;height:100%;overflow-y:auto;background:${C.bg};color:${C.tx};
  font:15px/1.45 ui-sans-serif,system-ui,"Segoe UI",Roboto,sans-serif;
  -webkit-font-smoothing:antialiased}
*{box-sizing:border-box}
#app{max-width:1240px;margin:0 auto;padding:14px 18px 60px;position:relative}
.tn{font-variant-numeric:tabular-nums}
header{display:flex;align-items:baseline;justify-content:space-between;gap:12px;padding:4px 2px 10px}
.brand{font-size:19px;font-weight:700;letter-spacing:.04em}
.hstat{color:${C.tx3};font-size:13px}
.pulse{color:${C.blue};animation:pl 1.4s ease-in-out infinite}
@keyframes pl{50%{opacity:.4}}
nav{display:flex;gap:4px;flex-wrap:wrap;border-bottom:1px solid ${C.line};margin-bottom:16px}
.tab{background:none;border:none;border-bottom:2px solid transparent;color:${C.tx2};
  font:inherit;font-size:15px;font-weight:600;padding:9px 14px;cursor:pointer}
.tab:hover{color:${C.tx}}
.tab.on{color:${C.tx};border-bottom-color:${C.blue}}
.card{background:${C.card};border:1px solid ${C.line};border-radius:12px;padding:16px;margin-bottom:14px}
.card2{background:${C.card2};border:1px solid ${C.line};border-radius:10px;margin:10px 0}
.pad{padding:16px}.pad0{padding:8px 6px}
.err{color:${C.red}}
.mut{color:${C.tx3}}
.okcol{color:${C.green}}.warncol{color:${C.amber}}
.hint{color:${C.tx3};font-size:13px;font-weight:400}
.note{color:${C.tx3};font-size:13px;max-width:860px;margin:6px 4px}
.secname{font-size:16px;margin:20px 4px 10px;font-weight:700}
.ic{vertical-align:-3px}
.bdg{display:inline-flex;align-items:center;gap:5px;border:1px solid;border-radius:999px;
  padding:2px 10px 2px 7px;font-size:12.5px;font-weight:600;white-space:nowrap}
.chipbtn{background:${C.card2};border:1px solid ${C.line};color:${C.tx2};border-radius:999px;
  padding:5px 13px;font:inherit;font-size:13px;cursor:pointer}
.chipbtn:hover{color:${C.tx};border-color:${C.tx3}}
.chipbtn.on{color:${C.tx};border-color:${C.blue};background:${C.blue}1c}
.bar{display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap;margin:2px 2px 12px}
.chips{display:flex;gap:6px;flex-wrap:wrap}
.legend{display:flex;gap:14px;flex-wrap:wrap;align-items:center;font-size:13px;color:${C.tx2}}
.lg{display:inline-flex;align-items:center;gap:5px}
.sw{width:14px;height:4px;border-radius:2px;display:inline-block}
.dashdemo{width:16px;height:10px;border:1.5px dashed ${C.tx3};border-radius:3px;display:inline-block}
details.more summary,details.calc summary{cursor:pointer;color:${C.tx2};font-size:13.5px;margin-top:8px}
details.more summary:hover,details.calc summary:hover{color:${C.tx}}
.src{color:${C.tx2};font-size:13.5px;line-height:1.55;max-width:760px}
.src.pre{white-space:pre-wrap}
svg.ch{display:block;width:100%;height:auto}
.ax{font:11.5px ui-sans-serif,system-ui,sans-serif;fill:${C.tx3}}
svg.evtrack{margin-top:-2px}
.evleg{display:flex;align-items:center;gap:7px;flex-wrap:wrap;margin:2px 0 8px;padding:0 10px}
.evleg i{display:inline-block;margin-left:10px}
.evleg i:first-child{margin-left:0}
.evb{width:3px;height:11px;border-radius:1px}
.evs{width:8px;height:8px;border-radius:2px}
.evt{width:0;height:0;border-left:5px solid transparent;border-right:5px solid transparent;
  border-bottom-width:8px;border-bottom-style:solid}
.pl{font:12px ui-sans-serif,system-ui,sans-serif;font-weight:600}
.rdo{display:flex;align-items:center;gap:14px;flex-wrap:wrap;padding:7px 10px 8px;
  margin:2px 4px 6px;border-bottom:1px solid ${C.line};min-height:34px}
.rdox{color:${C.tx3};font-size:12.5px;min-width:132px;font-variant-numeric:tabular-nums}
.rdov{display:flex;gap:16px;flex-wrap:wrap;align-items:center}
.rv{display:inline-flex;align-items:center;gap:6px;font-size:13px;color:${C.tx2}}
.rv i{width:9px;height:9px;border-radius:3px;display:inline-block}
.rv b{color:${C.tx};font-size:14.5px}
/* Zustand: ein Punktdiagramm statt dreier Balken */
.zplot{min-width:300px}
.zrow{display:grid;grid-template-columns:150px 1fr 52px;gap:10px;align-items:center;padding:3px 0}
.zname{font-size:12.5px;color:${C.tx2}}
.ztrack{position:relative;height:20px;background:#0006;border-radius:4px;display:block}
.zband{position:absolute;left:41.7%;width:16.6%;top:0;bottom:0;background:${C.tx3};opacity:.2;border-radius:3px}
.zzero{position:absolute;left:50%;top:0;bottom:0;width:1.5px;background:${C.tx3};opacity:.65}
.zdot{position:absolute;top:4px;width:12px;height:12px;border-radius:3px;margin-left:-6px}
.zval{font-size:14px;text-align:right}
.zscale{display:grid;grid-template-columns:150px 1fr 52px;gap:10px;color:${C.tx3};font-size:10.5px}
.zscale span:nth-child(1){grid-column:2;text-align:left}
.zscale span:nth-child(2){grid-column:2;text-align:center;margin-top:-13px}
.zscale span:nth-child(3){grid-column:2;text-align:right;margin-top:-13px}
.evi{font-size:12.5px;color:${C.tx3};margin:4px 0 0;line-height:1.45}

/* Heute */
.hero{border-width:1.5px;padding:20px}
.herowrap{display:flex;gap:28px;align-items:center;flex-wrap:wrap;justify-content:center}
.ringbox{flex:0 0 210px}
.ring{width:210px;height:210px}
.ringword{font:700 21px ui-sans-serif,system-ui,sans-serif;text-transform:uppercase;letter-spacing:.05em}
.ringsub{font:12px ui-sans-serif,system-ui,sans-serif}
.heromain{flex:1 1 520px;min-width:320px}
.kicker{color:${C.tx3};font-size:13px;text-transform:uppercase;letter-spacing:.12em;margin-bottom:4px}
.verdict{display:flex;align-items:center;gap:10px;font-size:19px;font-weight:650;margin-bottom:14px;flex-wrap:wrap}
.budhead{font-size:14.5px;color:${C.tx2};margin-bottom:2px}
.budhead b{font-size:19px}
.bval{font:700 17px ui-sans-serif,system-ui,sans-serif}
details.calc p{color:${C.tx2};font-size:13.5px;max-width:760px}
.nextrow{display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin-top:12px;padding:10px 12px;
  background:${C.card2};border-radius:9px;font-size:14.5px}
.nextrow .sp{display:inline-flex;align-items:center;gap:5px;font-weight:600}
.sep{color:${C.tx3}}
.siggrid{display:grid;grid-template-columns:repeat(auto-fill,minmax(310px,1fr));gap:12px}
.sig{border-left:3px solid ${C.line};margin-bottom:0;padding:14px}
.sighead{display:flex;align-items:center;gap:9px;margin-bottom:6px}
.sigl{font-weight:650;flex:1;font-size:15.5px}
.sigval{font-size:27px;font-weight:700;line-height:1.15}
.sigval .unit{font-size:13px;color:${C.tx3};font-weight:500}
.sigval .stamp{font-size:12px;color:${C.tx3};font-weight:500;margin-left:9px;
  border:1px solid ${C.line};border-radius:999px;padding:2px 8px;vertical-align:3px}
.sigval .stamp.old{color:${C.amber};border-color:${C.amber}55;background:${C.amber}12}
.sigref{font-size:13px;color:${C.tx3};margin-top:1px}
.dstamp{color:${C.tx2};letter-spacing:0;text-transform:none;font-weight:600}
.statgrid.lead{display:grid;grid-template-columns:minmax(260px,1fr) 2fr;gap:22px;align-items:center}
.stat.wide .lead1{font-size:46px;line-height:1.05;display:block}
.sidestats{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:16px}
.small2{font-size:19px}
.sigsub{color:${C.tx2};font-size:13.5px;margin:3px 0 9px;min-height:1.2em}
.spk{display:block;width:100%;height:46px}
.spklbl{color:${C.tx3};font-size:11.5px;margin-top:2px}
.nospark{color:${C.tx3};font-size:12.5px;padding:12px 0;border-top:1px dashed ${C.line}}
/* Kalender */
.calhead{display:grid;grid-template-columns:190px repeat(7,1fr);gap:8px;padding:0 2px 6px;
  color:${C.tx3};font-size:12.5px;font-weight:600;letter-spacing:.06em}
.calhead span{text-align:left;padding-left:8px}
.wkrow{display:grid;grid-template-columns:190px repeat(7,1fr);gap:8px;margin-bottom:8px}
.wksum{margin:0;padding:12px}
.wkkw{font-weight:700;font-size:14.5px}
.yr{color:${C.tx3};font-weight:500;font-size:12px}
.wkload{font-size:25px;font-weight:700;margin:2px 0}
.wkdelta{font-size:12.5px;font-weight:600;margin-left:5px}
.wkdelta.up{color:${C.amber}}.wkdelta.down{color:${C.tx3}}
.wkplan{color:${C.blue};font-size:12.5px}
.wkbar{height:5px;background:${C.line};border-radius:3px;margin:7px 0}
.wkbar i{display:block;height:100%;background:${C.blue};border-radius:3px}
.wkmeta{display:flex;gap:10px;color:${C.tx2};font-size:12.5px;flex-wrap:wrap}
.wkmeta span{display:inline-flex;align-items:center;gap:3px}
.wkfit{color:${C.tx3};font-size:12px;margin-top:5px}
.day{background:${C.card};border:1px solid ${C.line};border-radius:10px;padding:8px;min-height:96px}
.day.is-fut{background:${C.bg};border-style:dashed}
.day.is-today{border-color:${C.blue};box-shadow:0 0 0 1px ${C.blue}}
.day.off{background:none;border:none}
.dhead{display:flex;justify-content:space-between;align-items:baseline;font-size:13.5px;font-weight:650;margin-bottom:4px}
.is-fut .dhead{color:${C.tx3}}
.dload{color:${C.blue};font-size:14px}
.wln{display:flex;gap:8px;flex-wrap:wrap;color:${C.tx3};font-size:12px;margin-bottom:6px}
.wln span{display:inline-flex;align-items:center;gap:2.5px}
.chip{position:relative;display:flex;align-items:center;gap:6px;width:100%;text-align:left;
  background:${C.card2};border:1px solid ${C.line};border-left:3px solid var(--sc);border-radius:8px;
  padding:6px 8px 8px;margin-top:5px;color:${C.tx};font:inherit;font-size:13px;cursor:pointer}
.chip:hover{border-color:var(--sc)}
.chip .cn{flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-weight:600}
.chip .cd{color:${C.tx2}}
.chip .cl{background:#0009;border-radius:6px;padding:1px 6px;font-weight:700;font-size:12.5px}
.chip.plan{border-left-style:dashed;border-style:dashed;cursor:default;color:${C.tx2}}
.chip.plan.done{border-style:solid;color:${C.tx}}
.chip.plan.missed .cn{color:${C.red}}
.zb{position:absolute;left:8px;right:8px;bottom:3px;height:3px;display:flex;border-radius:2px;overflow:hidden}
.zb s{display:block;height:100%}
.zb.w{position:static;width:74px;height:8px;border-radius:3px}
/* Aktivitäten */
.ahead,.arow{display:grid;grid-template-columns:36px minmax(160px,1.4fr) 76px 86px 60px 60px 96px 92px 96px;
  gap:10px;align-items:center;padding:9px 12px}
.ahead{color:${C.tx3};font-size:12px;font-weight:600;letter-spacing:.05em;border-bottom:1px solid ${C.line}}
.arow{width:100%;text-align:left;background:none;border:none;border-bottom:1px solid ${C.line}55;
  color:${C.tx};font:inherit;font-size:13.5px;cursor:pointer}
.arow:hover{background:${C.card2}}
.arow.on{background:${C.blue}14}
.arow .anm b{display:block;font-size:14px}
.arow .anm small{color:${C.tx3};font-size:12px}
.al{font-weight:700}
.det{border-color:${C.blue}66}
.dethead{display:flex;align-items:center;gap:14px;margin-bottom:12px}
.dethead h2{margin:0;font-size:20px}
.dethead .chipbtn{margin-left:auto}
.detsub{color:${C.tx3};font-size:13.5px}
.aic.big{flex:0 0 auto}
.kvgrid{display:grid;grid-template-columns:repeat(auto-fill,minmax(160px,1fr));gap:8px;margin-bottom:6px}
.kv{background:${C.card2};border-radius:9px;padding:9px 11px;display:grid;grid-template-columns:20px 1fr;gap:2px 7px;align-items:center}
.kv small{color:${C.tx3};font-size:11.5px;grid-column:2}
.kv b{font-size:15.5px;grid-column:2}
.kv .ic{grid-row:1/3}
.loading{display:flex;align-items:center;gap:10px;color:${C.tx2};padding:22px}
.spin{width:16px;height:16px;border:2px solid ${C.line};border-top-color:${C.blue};border-radius:50%;
  animation:sp 0.9s linear infinite;display:inline-block}
@keyframes sp{to{transform:rotate(360deg)}}
.lapverdict{display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin:0 4px 8px;font-size:13.5px}
.lhead,.lrow{display:grid;grid-template-columns:34px minmax(120px,1.2fr) 74px 78px 82px 62px 1.1fr 1.1fr;
  gap:10px;align-items:center;padding:7px 12px;font-size:13.5px}
.lhead{color:${C.tx3};font-size:12px;font-weight:600;border-bottom:1px solid ${C.line}}
.lrow{border-bottom:1px solid ${C.line}44}
.lrow.rest{opacity:.55}
.lrow .ln{color:${C.tx3}}
.llbl{overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-weight:600}
.llbl em{font-style:normal;color:${C.tx3};font-weight:500;font-size:12px}
.lb{display:flex;align-items:center;gap:7px}
.lbar{flex:1;height:8px;background:#0006;border-radius:4px;overflow:hidden;display:block;min-width:34px}
.lbar s{display:block;height:100%}
@media(max-width:980px){
  .lhead{display:none}
  .lrow{grid-template-columns:30px 1fr 70px 74px;}
  .lrow>*:nth-child(5),.lrow>*:nth-child(6),.lrow>*:nth-child(7),.lrow>*:nth-child(8){display:none}
}
/* Zustand: ein Punktdiagramm statt dreier Balken */
.zplot{min-width:300px}
.zrow{display:grid;grid-template-columns:150px 1fr 52px;gap:10px;align-items:center;padding:3px 0}
.zname{font-size:12.5px;color:${C.tx2}}
.ztrack{position:relative;height:20px;background:#0006;border-radius:4px;display:block}
.zband{position:absolute;left:41.7%;width:16.6%;top:0;bottom:0;background:${C.tx3};opacity:.2;border-radius:3px}
.zzero{position:absolute;left:50%;top:0;bottom:0;width:1.5px;background:${C.tx3};opacity:.65}
.zdot{position:absolute;top:4px;width:12px;height:12px;border-radius:3px;margin-left:-6px}
.zval{font-size:14px;text-align:right}
.zscale{display:grid;grid-template-columns:150px 1fr 52px;gap:10px;color:${C.tx3};font-size:10.5px}
.zscale span:nth-child(1){grid-column:2;text-align:left}
.zscale span:nth-child(2){grid-column:2;text-align:center;margin-top:-13px}
.zscale span:nth-child(3){grid-column:2;text-align:right;margin-top:-13px}
.evi{font-size:12.5px;color:${C.tx3};margin:4px 0 0;line-height:1.45}

/* Heute */
.thead{font-size:14px;color:${C.tx2};margin:0 2px 8px}
.staleflag{color:${C.amber};font-size:12.5px;margin-left:6px}
.tsigdate{color:${C.tx3};font-size:11px;margin-bottom:6px}
.tsigdate.stale{color:${C.amber}}
.bullet{position:relative;height:14px;background:#0006;border-radius:3px;flex-basis:100%;margin:6px 0 2px}
.bband{position:absolute;left:0;top:0;bottom:0;background:${C.slate};opacity:.45;border-radius:3px}
.bval{position:absolute;left:0;top:4px;bottom:4px;background:${C.tx};border-radius:2px}
.bmark{position:absolute;top:-2px;bottom:-2px;width:2px;background:${C.tx2}}
.tcard{display:grid;grid-template-columns:1.4fr 1fr;gap:18px;background:${C.card};
  border:1px solid ${C.line};border-left-width:4px;border-radius:12px;padding:18px 20px;margin-bottom:12px}
.tcard.red{border-left-color:${C.red}}
.tcard.amber{border-left-color:${C.amber}}
.tcard.blue{border-left-color:${C.blue}}
.tcard.green{border-left-color:${C.green}}
.tcard.grey{border-left-color:${C.tx3}}
.tlabel{color:${C.tx3};font-size:11px;text-transform:uppercase;letter-spacing:.07em;margin-bottom:4px}
.tbig{font-size:34px;font-weight:700;line-height:1.1}
.tsay{font-size:15px;color:${C.tx2};margin:6px 0 0}
.tceil{display:flex;align-items:baseline;gap:9px;flex-wrap:wrap;margin-top:12px;
  background:${C.card2};border-radius:9px;padding:8px 12px}
.tceil span{color:${C.tx3};font-size:12px}
.tceil b{font-size:19px}
.tceil em{font-style:normal;color:${C.tx3};font-size:11.5px;flex-basis:100%}
.tstate{border-left:1px solid ${C.line};padding-left:18px}
.tstateword{font-size:19px;font-weight:650;margin-bottom:4px}
.tnote{display:flex;gap:9px;align-items:flex-start;background:${C.card2};border-radius:10px;
  padding:11px 14px;font-size:13.5px;color:${C.tx2};margin-bottom:4px;line-height:1.5}
.tsigs{display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:10px}
.tsig{background:${C.card};border:1px solid ${C.line};border-radius:11px;padding:12px 14px;
  opacity:.72;cursor:zoom-in}
.tsig:hover{border-color:${C.tx3}66}
.tsig.big{grid-column:1 / -1;opacity:1;cursor:zoom-out}
.tsigbig{margin-top:12px;border-top:1px solid ${C.line};padding-top:12px}
.tsigbignum{display:flex;align-items:baseline;gap:8px;flex-wrap:wrap;margin-bottom:6px}
.tsigbignum b{font-size:40px;line-height:1}
.tsigbignum small{font-size:15px;color:${C.tx3}}
.tsigbignum span{color:${C.tx2};font-size:13px;margin-left:auto}
.tdayn{display:block;font-style:normal;color:${C.tx3};font-size:10px;margin-top:1px}
.tsig.moved{opacity:1;border-color:${C.line}}
.tsighead{display:flex;justify-content:space-between;align-items:baseline;gap:8px}
.tsighead b{font-size:14.5px}
.tsigsys{color:${C.tx3};font-size:11px;text-align:right}
.tsignum{display:flex;align-items:baseline;gap:5px;margin:6px 0 8px;flex-wrap:wrap}
.tsignum b{font-size:26px}
.tsignum small{color:${C.tx3};font-size:12.5px}
.tsigbase{color:${C.tx3};font-size:11.5px;margin-left:auto}
.tsigbar{position:relative;height:12px;background:#0006;border-radius:3px}
.tsigband{position:absolute;left:41.7%;width:16.6%;top:0;bottom:0;background:${C.tx3};opacity:.22;border-radius:2px}
.tsigfill{position:absolute;top:2px;bottom:2px;border-radius:2px}
.tsigfoot{display:flex;justify-content:space-between;gap:10px;margin-top:6px;font-size:12px}
.tsigfoot em{font-style:normal;color:${C.tx3};font-size:11px;text-align:right;max-width:60%}
.tweek{display:grid;grid-template-columns:repeat(7,1fr);gap:8px}
.tday{display:grid;grid-template-rows:64px auto auto auto;justify-items:center;gap:2px;
  padding:4px 2px 5px;border-radius:8px}
.tday.now{background:${C.card2};outline:1px solid ${C.line}}
.tbarbox{display:flex;align-items:flex-end;justify-content:center;width:100%;height:64px;
  border-bottom:1px solid ${C.line}}
.tbarbox i{width:78%;max-width:44px;border-radius:3px 3px 0 0;display:block;opacity:.9}
.tdate{color:${C.tx3};font-size:11px}
.tload{font-size:14px;color:${C.tx}}
.tdayn{font-style:normal;color:${C.tx3};font-size:10px;text-align:center;line-height:1.2}
.tweeksum{color:${C.tx2};font-size:13px;margin-top:10px;padding-top:10px;border-top:1px solid ${C.line}}
.tnight{margin-top:12px;padding-top:12px;border-top:1px solid ${C.line}}
.tnhead{font-size:15px;font-weight:600;margin:2px 0 2px}
@media(max-width:820px){
  .tcard{grid-template-columns:1fr}
  .tstate{border-left:none;border-top:1px solid ${C.line};padding:12px 0 0}
}

/* Ziel und Plan */
.goalbar{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:10px}
.gtile{text-align:left;background:${C.card};border:1px solid ${C.line};border-radius:11px;
  padding:11px 14px;color:${C.tx};font:inherit;cursor:pointer}
.gtile:hover{border-color:${ROLE.series}66}
.gtile small{display:block;color:${C.tx3};font-size:10.5px;letter-spacing:.07em}
.gtile b{display:block;font-size:17px;margin:2px 0}
.gtile em{font-style:normal;color:${C.tx2};font-size:12px}
.planfold{margin-bottom:10px}
@media(max-width:700px){.goalbar{grid-template-columns:1fr}}
.daypick{display:grid;grid-template-columns:repeat(auto-fit,minmax(88px,1fr));gap:10px;margin:14px 0}
.dopt{background:${C.card2};border:1px solid ${C.line};border-radius:10px;padding:12px 6px;
  color:${C.tx};font:inherit;cursor:pointer;text-align:center}
.dopt:hover{border-color:${ROLE.series}66}
.dopt.on{border-color:${ROLE.series};background:${ROLE.series}18}
.dopt b{display:block;font-size:24px;font-weight:700;line-height:1.1}
.dopt span{display:block;color:${C.tx3};font-size:11.5px}
.dopt em{display:block;font-style:normal;color:${C.tx2};font-size:11.5px;margin-top:4px}
.linkbtn{background:none;border:none;color:${ROLE.series};font:inherit;font-size:13px;
  cursor:pointer;text-decoration:underline;padding:0 0 0 6px}
.goalhead{display:flex;justify-content:space-between;align-items:flex-start;gap:14px}
.goaltitle{font-size:24px;margin:2px 0 4px;font-weight:700}
.goalsub{color:${C.tx2};font-size:14px;margin:0 0 10px}
.goalgrid{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px;margin:10px 0}
.gcell{background:${C.card2};border-radius:9px;padding:9px 12px}
.gcell small{display:block;color:${C.tx3};font-size:11px;text-transform:uppercase;letter-spacing:.05em}
.gcell b{font-size:17px}
.goalpick{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:10px;margin:12px 0}
.gopt{text-align:left;background:${C.card2};border:1px solid ${C.line};border-radius:10px;
  padding:11px 13px;color:${C.tx};font:inherit;cursor:pointer}
.gopt:hover{border-color:${ROLE.series}66}
.gopt.on{border-color:${ROLE.series};background:${ROLE.series}18}
.gopt b{display:block;font-size:15px;margin-bottom:2px}
.gopt span{color:${C.tx2};font-size:12.5px}
.gfields{display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:12px;margin:14px 0}
.gfield{display:block}
.gfield span{display:block;font-size:13.5px;margin-bottom:4px}
.gfield input{width:100%;box-sizing:border-box;background:${C.card2};border:1px solid ${C.line};
  border-radius:8px;padding:8px 10px;color:${C.tx};font:inherit;font-size:14px}
.gfield input:focus{outline:none;border-color:${ROLE.series}}
.gfield em{font-style:normal;display:block;color:${C.tx3};font-size:11.5px;margin-top:3px}
.gcheck{display:flex;align-items:center;gap:8px;font-size:13.5px;margin:4px 0 10px}
.gdays{display:flex;align-items:center;gap:10px;flex-wrap:wrap;font-size:13.5px;margin-bottom:12px}
.gdays>span{color:${C.tx2}}
.gday{display:flex;align-items:center;gap:4px;color:${C.tx2}}
.pweeks{display:grid;gap:8px}
.pweek{background:${C.card};border:1px solid ${C.line};border-radius:10px;padding:10px 13px;cursor:pointer}
.pweek:hover{border-color:${ROLE.series}55}
.pweek.recovery{background:${C.card2};border-style:dashed}
.pweek.bigday{border-color:${ROLE.series}88}
.pwhead{display:flex;align-items:baseline;gap:12px;flex-wrap:wrap}
.pwno{color:${C.tx3};font-size:12.5px;font-weight:700;min-width:26px}
.pwphase{font-size:14.5px;font-weight:650}
.pwh{color:${C.tx2};font-size:13.5px}
.pwlong{color:${ROLE.series};font-size:13.5px}
.pwlong em{font-style:normal;color:${C.tx3};font-size:11.5px}
.pwsess{display:flex;gap:6px;flex-wrap:wrap;margin-top:7px}
.ptag{font-size:11.5px;padding:2px 8px;border-radius:999px;background:${C.card2};color:${C.tx2}}
.ptag.long{background:${ROLE.series}22;color:${C.tx}}
.ptag.quality{background:${C.violet}22;color:${C.tx}}
.pwbody{margin-top:10px;border-top:1px solid ${C.line};padding-top:10px;display:grid;gap:10px}
.psess{background:${C.card2};border-radius:9px;padding:10px 12px}
.psess.long{border-left:3px solid ${ROLE.series}}
.psess.quality{border-left:3px solid ${C.violet}}
.psess b{font-size:14.5px}
.psess p{margin:4px 0 0;font-size:13.5px;color:${C.tx2}}

/* Wie diese Einheit dasteht */
.ctxbox{background:${C.card2};border-radius:10px;padding:10px 14px}
.ctxscale{display:grid;grid-template-columns:1fr 92px minmax(160px,1.4fr) minmax(190px,1fr);gap:12px;
  color:${C.tx3};font-size:11px;text-transform:uppercase;letter-spacing:.05em}
.ctxscale span:nth-child(1){grid-column:3;text-align:left}
.ctxscale span:nth-child(2){grid-column:3;text-align:center;margin-top:-14px}
.ctxscale span:nth-child(3){grid-column:3;text-align:right;margin-top:-14px}
.ctxrow{display:grid;grid-template-columns:1fr 92px minmax(160px,1.4fr) minmax(190px,1fr);gap:12px;
  align-items:center;padding:10px 0;border-bottom:1px solid ${C.line}44}
.ctxrow:last-of-type{border-bottom:none}
.ctxlab b{font-size:14px;display:block}
.ctxlab em{font-style:normal;color:${C.tx3};font-size:11.5px}
.ctxval{font-size:19px;text-align:right}
.ctxval small{font-size:12px;color:${C.tx3};margin-left:3px}
.ctxbar{position:relative;height:18px;background:#0006;border-radius:4px;display:block}
.ctxband{position:absolute;top:3px;bottom:3px;background:${C.slate};opacity:.5;border-radius:3px}
.ctxmed{position:absolute;top:1px;bottom:1px;width:2px;background:${C.tx2}}
.ctxdot{position:absolute;top:2px;width:9px;height:14px;border-radius:3px;margin-left:-4px}
.ctxsay{font-size:13.5px}
.ctxsay em{font-style:normal;display:block;color:${C.tx3};font-size:11.5px}
.ctxrow.thin .ctxsay{color:${C.tx3};font-size:12.5px}
@media(max-width:900px){
  .ctxscale{display:none}
  .ctxrow{grid-template-columns:1fr 84px}
  .ctxbar,.ctxsay{grid-column:1 / -1}
}

/* Die Nacht danach */
.nightbox{background:${C.card2};border-radius:10px;padding:6px 14px 10px}
.nrow{display:grid;grid-template-columns:1fr 92px 78px minmax(200px,1.2fr);gap:12px;
  align-items:baseline;padding:9px 0;border-bottom:1px solid ${C.line}44}
.nrow:last-of-type{border-bottom:none}
.nlab b{font-size:14px}
.nlab em{font-style:normal;display:block;color:${C.tx3};font-size:11.5px}
.nval{font-size:19px;text-align:right}
.nval small{font-size:12px;color:${C.tx3};margin-left:3px}
.nz{font-size:14.5px;text-align:right}
.nref{color:${C.tx2};font-size:12.5px}
@media(max-width:860px){.nrow{grid-template-columns:1fr 80px 70px}.nref{grid-column:1 / -1;margin-top:-4px}}

/* Blockvergleich */
.cmppanel{cursor:zoom-in}
.cmppanel.big{grid-column:1 / -1;cursor:zoom-out}
.cmppanel:hover{outline:1px solid ${C.line}}
.zoomhint{float:right;color:${C.tx3};font-weight:400;font-size:11.5px;margin-right:8px}
.devbox{background:${C.card2};border-radius:10px;padding:12px 14px}
.devhead{font-size:13.5px;color:${C.tx2};margin-bottom:10px}
.devrow{display:grid;grid-template-columns:210px 1fr;gap:14px;align-items:center;
  padding:7px 0;border-top:1px solid ${C.line}44}
.devrow:first-of-type{border-top:none}
.devlab{font-size:13.5px;display:flex;align-items:center;gap:7px;flex-wrap:wrap}
.devlab em{font-style:normal;color:${C.tx3};font-size:11.5px}
.devbars{display:flex;gap:14px;flex-wrap:wrap}
.devcell{display:grid;grid-template-columns:1fr;gap:2px;min-width:120px;flex:1 1 120px}
.devbar{position:relative;display:block;height:14px;background:#0006;border-radius:3px}
.devbar::before{content:"";position:absolute;left:50%;top:-2px;bottom:-2px;width:1.5px;background:${C.tx3}}
.devbar s{position:absolute;top:2px;bottom:2px;border-radius:2px;display:block}
.devbar b{position:absolute;top:-2px;font-size:13px;white-space:nowrap;line-height:18px}
.devcell{min-height:22px}
.devcell em{font-style:normal;color:${C.tx3};font-size:11px}
.devcell.colhead{display:block;text-align:center;color:${C.tx2};font-size:12.5px;font-weight:600;min-width:120px}
.devcell.colhead em{display:block;font-weight:400;font-size:11px}
.devfoot{border-top:1px solid ${C.line}44;padding-top:6px;margin-top:2px}
.devscale{position:relative;display:block;height:13px}
.devscale u{position:absolute;top:0;text-decoration:none;color:${C.tx3};font-size:10.5px}
.devrow.devhead2{border-top:none;padding-bottom:2px}
.devlab{align-items:flex-start}
.devlab b{display:block;font-size:13.5px}
.devlab em{display:block;max-width:200px;line-height:1.35}
.cmpverdict{display:flex;gap:11px;align-items:flex-start;border-radius:10px;padding:11px 13px;
  margin:0 2px 12px;font-size:14px;line-height:1.5}
.cmpverdict.worse{background:${C.amber}12;border:1px solid ${C.amber}44}
.cmpverdict.held{background:${C.green}12;border:1px solid ${C.green}44}
.cmpverdict b{display:block;margin-bottom:2px}
.cmpverdict span{color:${C.tx2};font-size:13.5px}
.cmpgrid{display:grid;grid-template-columns:repeat(auto-fit,minmax(290px,1fr));gap:12px}
.cmppanel{background:${C.card2};border-radius:10px;padding:8px 6px 4px}
.cmplab{font-size:13px;font-weight:650;margin:0 0 2px 10px}
.cmplab .sfu{color:${C.tx3};font-weight:400;font-size:11.5px}
.cmplegend{display:flex;gap:14px;flex-wrap:wrap;align-items:center;font-size:12.5px;
  color:${C.tx2};padding:8px 10px}
.subname{font-size:15px;margin:20px 4px 8px;font-weight:650}
.restgrid{margin-top:6px}
.restrow{display:grid;grid-template-columns:34px 1fr 76px 84px 84px 60px;gap:10px;
  padding:5px 8px;font-size:13px;border-bottom:1px solid ${C.line}44}
.restrow.head{color:${C.tx3};font-size:11.5px;font-weight:600}
.restrow b{color:${C.tx3}}
@media(max-width:980px){
  .cmpgrid{grid-template-columns:1fr}
  .restrow{grid-template-columns:28px 1fr 64px 70px}
  .restrow>*:nth-child(5),.restrow>*:nth-child(6){display:none}
}

/* Workouts */
.wogrid{display:grid;gap:12px}
.wocard{background:${C.card};border:1px solid ${C.line};border-radius:12px;padding:14px}
.wocard.first{border-color:${ROLE.series}66;box-shadow:0 0 0 1px ${ROLE.series}22}
.leadrec{background:${C.card};border:1px solid ${C.green}55;border-left:4px solid ${C.green};
  border-radius:12px;padding:16px 18px;margin-bottom:14px}
.leadhead{display:flex;align-items:center;gap:8px;color:${C.green};font-size:11.5px;
  font-weight:650;letter-spacing:.05em;margin-bottom:6px}
.leadtitle{font-size:26px;font-weight:700;line-height:1.15}
.leadmeta{color:${C.tx2};font-size:13.5px;margin:3px 0 8px}
.leadwhy{font-size:14px;color:${C.tx};margin:0 0 10px}
.recflag{display:flex;align-items:center;gap:6px;color:${C.green};font-size:12px;
  font-weight:650;margin:-2px 0 6px}
.wofam{color:${C.tx3};font-size:11px;text-transform:uppercase;letter-spacing:.06em}
.fitwhy{display:flex;gap:7px;align-items:flex-start;font-size:13px;color:${C.tx2};
  margin:6px 0 0;line-height:1.45}
.wohead{display:flex;justify-content:space-between;align-items:flex-start;gap:12px;flex-wrap:wrap}
.wotitle{font-size:19px;font-weight:700}
.wometa{color:${C.tx2};font-size:13px;margin-top:2px}
.wobar{position:relative;height:56px;background:#0006;border-radius:8px;margin:11px 0 8px;overflow:hidden}
.wob{position:absolute;bottom:0;border-radius:2px 2px 0 0;opacity:.92}
.wosteps{display:flex;gap:12px;flex-wrap:wrap;font-size:12.5px;color:${C.tx3};margin-bottom:8px}
.wosteps b{color:${C.tx2}}
.wosteps em{font-style:normal;color:${C.tx2}}
.worow{display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin-top:6px}
.planbtn{display:inline-flex;align-items:center;gap:7px;background:${ROLE.series}1e;
  border:1px solid ${ROLE.series}66;color:${C.tx};border-radius:999px;padding:7px 14px;
  font:inherit;font-size:13.5px;font-weight:600;cursor:pointer}
.planbtn:hover{background:${ROLE.series}30}
.planbtn.ghost{background:none;border-color:${C.line};color:${C.tx2};font-weight:500}
.planbtn.done{background:${C.green}22;border-color:${C.green}66;color:${C.green}}
.planbtn:disabled{opacity:.7;cursor:default}
.wodetail{margin-top:10px;border-top:1px solid ${C.line};padding-top:10px;display:grid;gap:10px}
.kv2 small{display:block;color:${C.tx3};font-size:11.5px;text-transform:uppercase;letter-spacing:.06em;margin-bottom:3px}
.kv2 pre{margin:0;background:${C.card2};border-radius:8px;padding:10px 12px;font-size:12.5px;
  white-space:pre-wrap;color:${C.tx2};font-family:ui-monospace,SFMono-Regular,Menlo,monospace}
.kv2 p{margin:0;font-size:13.5px;color:${C.tx2}}
.toast{position:fixed;left:50%;bottom:28px;transform:translateX(-50%);background:${C.card2};
  border:1px solid ${C.red}66;color:${C.tx};border-radius:10px;padding:11px 16px;font-size:14px;z-index:99;
  box-shadow:0 8px 26px #0009;max-width:min(560px,90vw)}

/* Signale */
.sigfield{position:relative;margin:0 2px 2px;transition:opacity .15s}
.sigfield.dim{opacity:.45}
.sflab{position:absolute;left:52px;top:4px;font-size:12.5px;font-weight:650;pointer-events:none;z-index:2}
.sflab .sfu{color:${C.tx3};font-weight:400;font-size:11.5px;margin-left:6px}
.lgbtn{display:inline-flex;align-items:center;gap:6px;background:none;border:1px solid transparent;
  border-radius:999px;padding:3px 10px;color:${C.tx2};font:inherit;font-size:13px;cursor:pointer}
.lgbtn:hover{color:${C.tx}}
.lgbtn.on{border-color:${C.line};background:${C.card2};color:${C.tx}}
.lgbtn i{width:12px;height:4px;border-radius:2px;display:inline-block}
.swb{width:12px;height:12px;border-radius:3px;display:inline-block;opacity:.85}
.expl summary{font-size:14.5px;font-weight:600;color:${C.tx};padding:7px 0}
.expl{border-bottom:1px solid ${C.line}44}
.expl .readas{margin:2px 0 6px}

/* Trainer */
.tstate{display:flex;align-items:center;gap:18px;flex-wrap:wrap}
.tsic{flex:0 0 auto}
.tslabel{font-size:27px;font-weight:700;line-height:1.1}
.tsz{flex:1 1 340px;min-width:280px;display:grid;gap:5px}
.zrow{display:grid;grid-template-columns:160px 1fr 74px;gap:10px;align-items:center;font-size:12.5px;color:${C.tx2}}
.tdetail{color:${C.tx};font-size:15px;margin:12px 2px 0;max-width:900px}
.effect{color:${C.tx2};font-size:14px;line-height:1.55;max-width:900px;margin:4px 0 8px}
.warnrow{display:flex;gap:9px;align-items:flex-start;background:${C.amber}12;border:1px solid ${C.amber}33;
  border-radius:9px;padding:9px 11px;margin:8px 0;font-size:13.5px;color:${C.tx2}}
.reasons{margin:6px 0 0;padding-left:18px;color:${C.tx2};font-size:13.5px}
.reasons li{margin-bottom:7px}
.reasons .src{display:block}
.qq{display:block;color:${C.tx3};font-size:12px;font-style:normal}
.ancgrid{display:grid;grid-template-columns:minmax(250px,1fr) 2fr;gap:22px;align-items:center}
.durrow{display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:14px;margin-bottom:6px}
.catrow{display:grid;grid-template-columns:190px 110px 190px 1fr;gap:12px;align-items:baseline;
  padding:10px 14px;border-bottom:1px solid ${C.line}44;font-size:13px}
@media(max-width:980px){
  .ancgrid{grid-template-columns:1fr}
  .catrow{grid-template-columns:1fr;gap:3px}
  .zrow{grid-template-columns:120px 1fr 64px}
}
.dfabox{background:${C.card2};border-radius:10px;padding:13px 15px}
.dfar{display:grid;grid-template-columns:150px 1fr 52px 62px;gap:10px;align-items:center;font-size:13.5px;padding:3px 0}
.dbar{height:9px;background:#0006;border-radius:4px;overflow:hidden;display:block}
.dbar s{display:block;height:100%}
.dfathr{margin-top:10px;font-size:14.5px;display:flex;align-items:center;gap:8px;flex-wrap:wrap}
/* Belastung */
.sechead{display:flex;align-items:center;gap:9px;margin-bottom:2px}
.sechead h3{margin:0;font-size:16.5px}
.readas{color:${C.tx2};font-size:13.5px;margin:4px 0 12px}
.statrow{display:flex;align-items:center;gap:12px;flex-wrap:wrap;margin-bottom:8px}
.big2{font-size:26px}.big3{font-size:19px}
.ilbl{color:${C.tx2};font-size:13px;margin:10px 0 5px}
.ibar{position:relative;height:30px;background:#0006;border-radius:7px;overflow:hidden}
.iseg{position:absolute;top:0;bottom:0;display:flex;align-items:center;justify-content:center;min-width:0}
.iseg span{font-size:12.5px;font-weight:700;color:#0d1117;white-space:nowrap;overflow:hidden}
.iref{position:absolute;top:-2px;bottom:-2px;width:2.5px;background:${C.tx};opacity:.9}
/* DFA */
.explain p{margin:2px 0;max-width:900px}
.statgrid{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:14px}
.stat small{display:block;color:${C.tx3};font-size:12px;text-transform:uppercase;letter-spacing:.07em;margin-bottom:3px}
.stat .unit{font-size:13px;color:${C.tx3}}
.stat .mut{display:block;font-size:12px;margin-top:2px}
.thead,.trow{display:grid;grid-template-columns:110px 140px 110px 110px 1fr;gap:10px;align-items:center;padding:8px 14px;font-size:13.5px}
.thead.dfahead,.card .trow{grid-template-columns:92px 116px 92px 88px 86px 78px 62px 84px 100px 1fr 28px;gap:8px}
.winpick{display:flex;align-items:center;gap:12px;flex-wrap:wrap;width:100%}
.winnote{color:${C.tx3};font-size:12.5px}
.winfields{display:inline-flex;align-items:center;gap:7px}
.wind{background:${C.bg2};color:${C.tx};border:1px solid ${C.line};border-radius:7px;
  padding:4px 7px;font:inherit;font-size:12.5px}
.pickbar{gap:10px;align-items:center}
/* An INNER bar, not a border: a border adds its own width and shifts the row
   sideways the moment it is marked. */
.trow.brushed{background:${C.bg2};box-shadow:inset 3px 0 0 0 ${ROLE.series}}
.trow.hovered{background:${C.bg2}88;box-shadow:inset 3px 0 0 0 ${C.tx3}}
.trow{border:0;width:100%;text-align:left;background:none;color:inherit;
  font-family:inherit;font-size:13.5px;cursor:pointer}
.gobox{display:flex;justify-content:flex-end}
.go{display:inline-flex;opacity:.55}
.trow:hover .go{opacity:1}
.thead{color:${C.tx3};font-size:12px;font-weight:600;border-bottom:1px solid ${C.line}}
.trow{border-bottom:1px solid ${C.line}44}
.trow.weak{opacity:.55}
.trow span{display:inline-flex;align-items:center;gap:5px}
/* Plan */
.prow{display:flex;align-items:flex-start;gap:13px;padding:12px 14px;border-bottom:1px solid ${C.line}55}
.prow .pmain{flex:1}
.prow .pmain b{font-size:15.5px}
.prow .pmain small{display:block;color:${C.tx3};font-size:13px;margin-top:1px}
.prow .cl{background:#0009;border-radius:7px;padding:3px 9px;font-weight:700}
@media(max-width:980px){
  .wkrow,.calhead{grid-template-columns:1fr;}
  .calhead span{display:none}
  .ahead{display:none}
  .arow{grid-template-columns:36px 1fr 76px 60px;}
  .arow>*:nth-child(4),.arow>*:nth-child(6),.arow>*:nth-child(7),.arow>*:nth-child(8),.arow>*:nth-child(9){display:none}
}`;
  }
}

if (!customElements.get("intervals-icu-panel")) {
  customElements.define("intervals-icu-panel", IntervalsIcuPanel);
}
