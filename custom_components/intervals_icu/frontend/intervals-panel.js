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
  let g = "";

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
        g += `<circle cx="${X(p.i)}" cy="${Y(p.v)}" r="${p.r || 3.4}" fill="${p.f === false ? "none" : (p.c || s.c)}" stroke="${p.c || s.c}" stroke-width="1.6" opacity="${p.op == null ? 1 : p.op}"/>`;
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
  for (const x of (o.xt || [])) {
    g += `<text x="${X(x.i)}" y="${h - 6}" text-anchor="middle" class="ax">${x.t}</text>`;
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
  ["heute", "Heute"], ["kalender", "Kalender"], ["fitness", "Fitness"],
  ["akt", "Aktivitäten"], ["belastung", "Belastung"], ["dfa", "DFA"], ["plan", "Plan"],
];
const VERDICT = {
  green: "grün — normal trainieren.",
  amber: "gelb — Umfang ja, Intensität dosieren.",
  red: "rot — heute leicht trainieren oder pausieren.",
  unknown: "noch zu wenige Daten für eine Einschätzung.",
};
const SIG_ICON = { hrv: "heart", rhr: "pulse", sleep: "moon", form: "gauge", acwr: "trend", monotony: "wave", subjective: "user" };
const SIG_UNIT = { hrv: "ln rMSSD", rhr: "bpm", sleep: "h", form: "%", acwr: "", monotony: "", subjective: "/ 4" };
const SIG_DEC = { hrv: 3, rhr: 0, sleep: 2, form: 1, acwr: 2, monotony: 2, subjective: 0 };

class IntervalsIcuPanel extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._tab = "heute";
    this._grp = {};
    this._range = 182;
    this._weeks = 12;
    this._dfaSport = "all";
    this._streams = {};
    this._booted = false;
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
      const [status, rd, days, load] = await Promise.all([
        this._ws("status"), this._ws("readiness"),
        this._ws("days", { weeks: this._weeks }), this._ws("load"),
      ]);
      this._status = status; this._rd = rd; this._days = days; this._load = load;
      this._err = null;
    } catch (err) {
      this._err = String(err && err.message || err);
    }
    this._render();
  }

  async _need(what) {
    try {
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
    if (t === "fitness") await this._need("pmc");
    if (t === "akt") await this._need("akt");
    if (t === "dfa") await this._need("thr");
    if (t === "plan") await this._need("cal");
    this._render();
  }

  async _openAct(id) {
    this._tab = "akt";
    await this._need("akt");
    this._sel = (this._acts || []).find((a) => String(a.id) === String(id)) || null;
    this._render();
    if (this._sel && !this._streams[id]) {
      try {
        this._streams[id] = await this._ws("streams", { activity_id: String(id) });
      } catch (err) {
        this._streams[id] = { error: String(err && err.message || err) };
      }
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
    } else if (this._tab === "heute") html = this.rHeute(this._rd, this._days, this._load);
    else if (this._tab === "kalender") html = this.rKalender(this._days);
    else if (this._tab === "fitness") html = this.rFitness(this._pmc, this._range);
    else if (this._tab === "akt") html = this.rAkt(this._acts, this._sel);
    else if (this._tab === "belastung") html = this.rBelastung(this._load);
    else if (this._tab === "dfa") html = this.rDfa(this._thr, this._dfaSport);
    else if (this._tab === "plan") html = this.rPlan(this._cal, this._rd);
    this._view.innerHTML = html;
    // the strip must carry the newest values before anyone moves a mouse -
    // and on a touch screen nobody ever does
    for (const name of Object.keys(this._grp)) this._fillReadout(name, null);
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
    });
    root.addEventListener("pointermove", (e) => {
      const g = e.target.closest && e.target.closest("[data-grp]");
      if (!g) { this._xhHide(); return; }
      this._xhMove(g, e);
    });
    root.addEventListener("pointerleave", () => this._xhHide(), true);
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

  _xhMove(g, e) {
    const name = g.dataset.grp, meta = this._grp[name];
    if (!meta) return;
    const svg = g.querySelector("svg.ch");
    if (!svg) return;
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

  rHeute(rd, days, load) {
    if (!rd) return `<div class="card pad">Noch keine Bereitschafts-Daten — der erste Import läuft vermutlich noch.</div>`;
    const m = ST[rd.overall] || ST.unknown;
    const b = rd.budget;
    const next = this._nextPlanned(days);
    let nextRow = "";
    if (next) {
      const sp = sportOf(next.group || next.type);
      let fit = "";
      if (b && next.load != null) {
        fit = next.load <= b.recommended
          ? badge("green", "passt ins Budget")
          : (next.load <= b.corridor_top ? badge("amber", "über Budget") : badge("red", "deutlich über Budget"));
      }
      nextRow = `<div class="nextrow">${ico("cal", C.tx2, 16)}<span>Nächste Einheit</span>
        <b>${dShort(next.day)}</b><span class="sep">·</span>
        <span class="sp" style="color:${sp.c}">${ico(sp.ic, sp.c, 16)}${esc(next.name || sp.l)}</span>
        ${next.load != null ? `<span class="sep">·</span><span>Last <b class="tn">${fmt(next.load)}</b></span>` : ""}
        ${fit}</div>`;
    }
    let budgetHtml = "";
    if (b) {
      budgetHtml = `
        <div class="budhead">Belastungsbudget heute:
          <b class="tn" style="color:${m.c}">${fmt(b.recommended)} Punkte</b></div>
        ${bullet(b)}
        <details class="calc">
          <summary>Wie kommt die Zahl zustande?</summary>
          <p>Aus der ACWR-Definition nach heute aufgelöst:
          <span class="tn">7 × ${fmt(b.chronic, 1)}</span> (chronische Tageslast, 28-Tage-Mittel)
          <span class="tn">× ${fmt(b.target_ratio, 1)}</span> (Ziel-Verhältnis bei <b style="color:${m.c}">${m.word}</b>)
          <span class="tn">− ${fmt(b.last_six_days, 1)}</span> (Last der letzten sechs Tage)
          <span class="tn">= ${fmt(b.recommended)}</span>.
          Die Zielwahl je Ampelfarbe ist eine Setzung, kein Befund; der ACWR-Korridor selbst ist umstritten.</p>
        </details>`;
    }
    const cards = (rd.components || []).map((cItem) => {
      const stm = ST[cItem.state] || ST.unknown;
      const sp = this._sparkFor(cItem.id, days, load);
      const dec = SIG_DEC[cItem.id] != null ? SIG_DEC[cItem.id] : 1;
      const stamp = this._stampOf(sp);
      const today = (days && days.today) || new Date().toISOString().slice(0, 10);
      const stale = stamp && !sp.week && stamp < today;
      const stampHtml = stamp
        ? `<span class="stamp ${stale ? "old" : ""}">${sp.week ? "KW " + String(stamp).split("-W")[1] : (stale ? "Stand " + dMed(stamp) : "heute")}</span>`
        : `<span class="stamp old">kein Wert</span>`;
      const sparkHtml = sp && sp.v && sp.v.some((v) => v != null)
        ? spark(sp.v, { c: C.blue, last: stm.c, band: sp.band, hline: sp.hline, bars: sp.bars, zero: sp.zero }) +
          `<div class="spklbl">${sp.t}</div>`
        : `<div class="nospark">kein Verlauf verfügbar</div>`;
      const bigHtml = sp && sp.v && sp.v.filter((v) => v != null).length > 3
        ? this._bigTrend(sp, days) : "";
      return `<div class="sig card" style="border-left-color:${stm.c}">
        <div class="sighead">
          <span class="sigic" style="color:${stm.c}">${ico(SIG_ICON[cItem.id] || "dot", stm.c, 20)}</span>
          <span class="sigl">${esc(cItem.label)}</span>
          ${badge(cItem.state)}
        </div>
        <div class="sigval tn">${cItem.value != null ? fmt(cItem.value, dec) : "–"}
          <span class="unit">${SIG_UNIT[cItem.id] || ""}</span>
          ${stampHtml}
        </div>
        ${cItem.reference != null ? `<div class="sigref">Referenz ${fmt(cItem.reference, dec)} ${SIG_UNIT[cItem.id] || ""}</div>` : ""}
        <div class="sigsub">${esc(cItem.detail || "")}</div>
        ${sparkHtml}
        ${cItem.source || bigHtml ? `<details class="more"><summary>Verlauf &amp; Quelle</summary>${bigHtml}<p class="src">${esc(cItem.source || "")}</p></details>` : ""}
      </div>`;
    }).join("");
    return `
      <section class="hero card" style="border-color:${m.c}55">
        <div class="herowrap">
          <div class="ringbox">${ring(rd.components || [], rd.overall)}</div>
          <div class="heromain">
            <div class="kicker">Bereitschaft <span class="dstamp">${days && days.today ? dLong(days.today) : ""}</span></div>
            <div class="verdict">${badge(rd.overall)}<span>${VERDICT[rd.overall] || VERDICT.unknown}</span></div>
            ${budgetHtml}
            ${nextRow}
          </div>
        </div>
      </section>
      <h3 class="secname">Die einzelnen Signale <span class="hint">— jedes gegen deine eigenen Werte, nicht gegen eine Norm. Der Ring oben zeigt sie in gleicher Reihenfolge.</span></h3>
      <div class="siggrid">${cards}</div>
      <p class="note">${esc(rd.note || "")}</p>`;
  }

  _bigTrend(sp, days) {
    const vals = sp.v;
    const [y0, y1] = domainOf([{ v: vals }]);
    const mean = meanOf(vals);
    const past = (days && days.days || []).filter((d) => !d.future).slice(-42);
    const xt = [];
    for (let i = 0; i < vals.length; i += Math.max(1, Math.floor(vals.length / 4))) {
      if (past[i]) xt.push({ i, t: dShort(past[i].date) });
    }
    return chart({
      h: 170, n: vals.length, y0: sp.zero ? Math.min(y0, 0) : y0, y1, xt,
      bands: sp.band ? [{ a: sp.band.a, b: sp.band.b, c: C.blue, op: 0.1 }] : [],
      hl: [
        ...(mean != null ? [{ y: mean, c: C.tx3, d: 1, t: "Mittel" }] : []),
        ...(sp.hline != null ? [{ y: sp.hline, c: C.amber, d: 1 }] : []),
        ...(sp.zero ? [{ y: 0, c: C.tx3 }] : []),
      ],
      s: [sp.bars ? { t: "bars", v: vals, c: C.blue } : { t: "line", v: vals, c: C.blue, w: 2 }],
      yf: (v) => fmt(v, Math.abs(y1 - y0) < 8 ? 1 : 0),
    });
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
    return `${detail}
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
        <p class="src">Rogers und Gronwald: DFA alpha-1 0,75 ≈ aerobe Schwelle (VT1), 0,5 ≈ anaerobe (VT2). Gegen Gasaustausch validiert, aber empfindlich für Artefakte und Aufzeichnungsgerät.</p>
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
  rDfa(thr, sportFilter) {
    if (!thr) return `<div class="card pad">DFA-Daten werden geladen …</div>`;
    // Ride and VirtualRide are both "Rad" - filtering on the raw type listed
    // the same label twice and split the season in half.
    const groups = [];
    for (const x of thr) {
      const g = groupKey(x.type);
      if (g && !groups.includes(g)) groups.push(g);
    }
    const rows = thr.filter((x) => sportFilter === "all" || groupKey(x.type) === sportFilter);
    const solid = rows.filter((x) => (x.samples || 0) >= 5 && x.hr != null && x.hr > 0);
    if (!rows.length) return `<div class="card pad">Noch keine Schwellen-Messungen${sportFilter !== "all" ? " für diese Sportart" : ""}.</div>`;
    const n = rows.length;
    const hrVals = rows.map((x) => ((x.samples || 0) >= 5 && x.hr > 0) ? x.hr : null);
    const roll = rollMedian(hrVals, 5);
    const cur = median(solid.slice(-5).map((x) => x.hr));
    const first = median(solid.slice(0, 5).map((x) => x.hr));
    const curW = median(solid.slice(-5).map((x) => x.power).filter((v) => v != null));
    const avgAll = meanOf(solid.map((x) => x.hr));
    // A zero threshold is a recording artefact, and a single-sample reading
    // off a walk is not a threshold either: both used to stretch the axis
    // from 0 to 160 and squash the real range into a line. The axis follows
    // the readings that carry weight; the rest is clamped into view.
    const solidHr = solid.map((x) => x.hr).filter((v) => v != null && v > 0);
    let [y0a, y1a] = solidHr.length >= 2
      ? domainOf([{ v: solidHr }], 0.14)
      : domainOf([{ v: rows.map((x) => x.hr).filter((v) => v > 0) }]);
    if (!(y1a > y0a)) { y0a = 100; y1a = 180; }
    const xt = monthTicks(rows.map((x) => x.date));
    let clamped = 0;
    const pts = rows.map((x, i) => {
      if (x.hr == null || x.hr <= 0) return null;
      const solidPt = (x.samples || 0) >= 5;
      const v = Math.max(y0a, Math.min(y1a, x.hr));
      if (v !== x.hr) clamped++;
      return { i, v, c: solidPt ? ROLE.series : C.grey,
               f: solidPt, r: solidPt ? 4 : 3, op: solidPt ? 1 : 0.6 };
    }).filter(Boolean);
    const mainCh = chart({
      h: 260, n, y0: y0a, y1: y1a, xt, grp: "dfa",
      hl: avgAll != null ? [{ y: avgAll, c: C.tx3, d: 1, t: "Schnitt " + fmt(avgAll) }] : [],
      s: [{ t: "dots", p: pts, c: ROLE.series }, { t: "line", v: roll, c: ROLE.series, w: 2.4 }],
      label: "Schwellen-Herzfrequenz (bpm)", labelc: ROLE.series,
    }) + (clamped ? `<p class="hint">${ico("warn", C.amber, 13)} ${clamped} Messung(en) außerhalb des dargestellten Bereichs — an der Achse geklemmt, damit der belastbare Bereich lesbar bleibt.</p>` : "");
    const powRows = rows.map((x) => (x.samples || 0) >= 5 ? x.power : null);
    let powCh = "";
    if (powRows.some((v) => v != null)) {
      const [p0, p1] = domainOf([{ v: powRows }]);
      powCh = chart({
        h: 130, n, y0: p0, y1: p1, grp: "dfa",
        s: [
          { t: "dots", p: rows.map((x, i) => powRows[i] != null ? { i, v: powRows[i], c: ROLE.pow, r: 3.4 } : null).filter(Boolean), c: ROLE.pow },
          { t: "line", v: rollMedian(powRows, 5), c: ROLE.pow, w: 2 },
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
    const tableRows = rows.slice(-15).reverse().map((x) => {
      const weak = (x.samples || 0) < 5;
      const sp = sportOf(x.type);
      return `<div class="trow ${weak ? "weak" : ""}">
        <span>${dMed(x.date)}</span>
        <span style="color:${sp.c}">${ico(sp.ic, sp.c, 15)}${sp.l}</span>
        <span class="tn">${fmt(x.hr)} bpm</span>
        <span class="tn">${x.power ? fmt(x.power) + " W" : "–"}</span>
        <span>${weak ? badge("amber", x.samples + " Punkte — dünn") : badge("green", x.samples + " Punkte")}</span>
      </div>`;
    }).join("");
    return `
      <div class="card explain">
        <p><b>DFA alpha-1</b> beschreibt, wie geordnet dein Herzschlagmuster ist. Der Wert sinkt mit der Intensität:
        bei <b style="color:${C.green}">0,75</b> liegt die aerobe Schwelle, bei <b style="color:${C.red}">0,5</b> die anaerobe.
        Unten steht, bei welcher Herzfrequenz deine Kurve in jeder Einheit durch 0,75 fällt — deine aerobe Schwelle, aus dem Training selbst gemessen, ohne Labortest.</p>
        <details class="more"><summary>Quelle und Grenzen</summary><p class="src">Rogers und Gronwald: gegen Gasaustausch (Spiroergometrie) validiert. Empfindlich für Artefakte und Aufzeichnungsgerät — deshalb zählen nur Messungen mit genügend Punkten im Schwellenfenster voll (ausgefüllte Punkte); dünne Messungen sind hohl und grau.</p></details>
      </div>
      <div class="bar">
        <div class="chips">
          <button class="chipbtn ${sportFilter === "all" ? "on" : ""}" data-act="dfasport" data-id="all">Alle Sportarten</button>
          ${groups.map((g) => `<button class="chipbtn ${sportFilter === g ? "on" : ""}" data-act="dfasport" data-id="${esc(g)}">${SPORT[g].l}</button>`).join("")}
        </div>
      </div>
      <div class="statgrid card lead">
        <div class="stat wide"><small>Aktuelle aerobe Schwelle</small>
          <b class="tn lead1" style="color:${ROLE.series}">${cur ? fmt(cur) : "–"} <span class="unit">bpm</span></b>
          <span class="mut">Median der letzten 5 belastbaren Messungen</span></div>
        <div class="sidestats">
          <div class="stat"><small>bei Leistung</small><b class="tn small2">${curW ? fmt(curW) : "–"} <span class="unit">W</span></b></div>
          <div class="stat"><small>Veränderung</small><b class="tn small2">${cur != null && first != null ? sign(Math.round(cur - first)) : "–"} <span class="unit">bpm</span></b></div>
          <div class="stat"><small>Messungen</small><b class="tn small2">${solid.length}</b><span class="mut">belastbar · ${rows.length - solid.length} dünn</span></div>
        </div>
      </div>
      <div class="card pad0" data-grp="dfa">${readout("dfa")}${mainCh}${powCh}</div>
      <div class="card pad0"><div class="thead"><span>Datum</span><span>Sport</span><span>Schwelle</span><span>Leistung</span><span>Güte</span></div>${tableRows}</div>`;
  }

  /* ---------------- Plan ---------------- */
  rPlan(cal, rd) {
    if (!cal) return `<div class="card pad">Plan wird geladen …</div>`;
    const today = new Date().toISOString().slice(0, 10);
    const upcoming = cal.filter((p) => String(p.start).slice(0, 10) >= today);
    if (!upcoming.length) return `<div class="card pad">Keine geplanten Einheiten in den nächsten Wochen.</div>`;
    const budget = rd && rd.budget;
    const byDay = new Map();
    for (const p of upcoming) {
      const day = String(p.start).slice(0, 10);
      if (!byDay.has(day)) byDay.set(day, []);
      byDay.get(day).push(p);
    }
    const tomorrow = new Date(Date.now() + 86400000).toISOString().slice(0, 10);
    return [...byDay.entries()].map(([day, items]) => {
      const title = day === today ? "Heute" : day === tomorrow ? "Morgen" : `${dShort(day)} ${dMed(day).slice(3)}`;
      const rowsHtml = items.map((p) => {
        const sp = sportOf(p.type);
        let fit = "";
        if (day === today && budget && p.load != null && !p.completed) {
          fit = p.load <= budget.recommended ? badge("green", "passt ins Budget")
            : p.load <= budget.corridor_top ? badge("amber", "über Budget") : badge("red", "deutlich über Budget");
        }
        return `<div class="prow">
          <span class="aic" style="color:${sp.c}">${ico(sp.ic, sp.c, 20)}</span>
          <div class="pmain"><b>${esc(p.summary || sp.l)}</b>
            <small>${sp.l}${p.moving_time ? " · " + dur(p.moving_time) : ""}${p.intensity ? " · Intensität " + fmt(p.intensity) + " %" : ""}</small>
            ${p.description ? `<details class="more"><summary>Beschreibung</summary><p class="src pre">${esc(p.description)}</p></details>` : ""}
          </div>
          ${p.load != null ? `<span class="cl tn big3">${fmt(p.load)}</span>` : ""}
          ${p.completed ? badge("green", "erledigt") : fit}
        </div>`;
      }).join("");
      return `<h3 class="secname">${title}</h3><div class="card pad0">${rowsHtml}</div>`;
    }).join("");
  }

  /* ---------------- styles ---------------- */
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
.pl{font:12px ui-sans-serif,system-ui,sans-serif;font-weight:600}
.rdo{display:flex;align-items:center;gap:14px;flex-wrap:wrap;padding:7px 10px 8px;
  margin:2px 4px 6px;border-bottom:1px solid ${C.line};min-height:34px}
.rdox{color:${C.tx3};font-size:12.5px;min-width:132px;font-variant-numeric:tabular-nums}
.rdov{display:flex;gap:16px;flex-wrap:wrap;align-items:center}
.rv{display:inline-flex;align-items:center;gap:6px;font-size:13px;color:${C.tx2}}
.rv i{width:9px;height:9px;border-radius:3px;display:inline-block}
.rv b{color:${C.tx};font-size:14.5px}
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
