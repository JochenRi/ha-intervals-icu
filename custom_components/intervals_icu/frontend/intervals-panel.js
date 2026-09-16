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

  // state register - four grades since 0.42.0 (docs/ausbau.md I6). Orange sits
  // in NEITHER list below: four grades need a fourth tone of their own, not a
  // shade of amber, and borrowing a category tone would mix the registers.
  green: "#34d399", amber: "#fbbf24", orange: "#fb923c", red: "#f87171", grey: "#6e8093",

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
  // the stimulus grade needs its OWN outline: circle (ok), triangle (warn),
  // circle-cross (stop), circle-dash (na) - so a DIAMOND, distinguishable at
  // badge size without colour. `bolt` below belongs to the load category and
  // must not double as a grade.
  surge:'<path d="M12 3l9 9-9 9-9-9z"/><path d="M12 16.5v-8M9 11.5l3-3 3 3"/>',
  // the stimulus grade needs its OWN shape - four grades, four outlines
  bike: '<circle cx="5.8" cy="16.8" r="3.4"/><circle cx="18.2" cy="16.8" r="3.4"/><path d="M5.8 16.8L10 7.5h4.6M10 7.5l3.4 9.3 4.8-6.5h-6"/>',
  run:  '<circle cx="14.5" cy="4.8" r="1.9"/><path d="M8.5 21l2.6-5.2 3 1.8.9 3.4M7.5 12.5l3.4-3 3.6 1 2.8 2.6M12.4 9.9l-1.3 3.9"/>',
  walk: '<circle cx="13" cy="4.6" r="1.9"/><path d="M10 21l2.1-5.6M14.4 21l-1.4-5.6-.8-4M9 12.4l3.2-2.9 2.8 1 2.4 2.7"/>',
  swim: '<path d="M3 17.5c2-1.6 4-1.6 6 0s4 1.6 6 0 4-1.6 6 0"/><circle cx="16.4" cy="7.6" r="1.9"/><path d="M4.5 13.5l5.5-3.4 4 2.4"/>',
  gym:  '<path d="M4 10v4M7.2 8v8M16.8 8v8M20 10v4M7.2 12h9.6"/>',
  dot:  '<circle cx="12" cy="12" r="5"/>',
  /* Die sechs Zuordnungs-Familien (docs/ausbau.md P2a). Jede eine EIGENE
     Form, keine Variante einer anderen - und bewusst KEINE Kreis-, Dreieck-
     oder Rautengrundform: die gehoeren dem Urteilsregister (ok/warn/stop/na
     und surge). Die Farbe verstaerkt hier nur; getragen wird die Identitaet
     von Form UND Kuerzel, weil ROLE das Kategorienregister in genau dieser
     Ansicht bereits vollstaendig belegt. */
  famVo2:  '<path d="M12 3.5l8.2 6-3.1 9.6H6.9L3.8 9.5z"/>',
  famSst:  '<path d="M8 4h8l4 8-4 8H8l-4-8z"/>',
  famTmp:  '<path d="M5 5h14v14H5z"/>',
  famThr:  '<path d="M4 18h16M4 18a8 8 0 0 1 16 0"/>',
  famEnd:  '<path d="M8.5 7.5h7a4.5 4.5 0 0 1 0 9h-7a4.5 4.5 0 0 1 0-9z"/>',
  famLng:  '<path d="M9 5.5h11l-5 13H4z"/>',
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
  sync: '<path d="M20 12a8 8 0 1 1-2.3-5.6"/><path d="M20 3.5V8h-4.5"/>',
  tag:  '<path d="M4 5.5h6.8l8.7 8.7-6.3 6.3-8.7-8.7z"/><circle cx="8.2" cy="9.4" r="1.3"/>',
};

function ico(name, color, size) {
  const s = size || 18;
  const st = color ? ` style="color:${color}"` : "";
  return `<svg class="ic" width="${s}" height="${s}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"${st}>${IC[name] || IC.dot}</svg>`;
}

const ST = {
  green:    { word: "grün",       ic: "ok",    c: C.green },
  amber:    { word: "gelb",       ic: "warn",  c: C.amber },
  // the fourth grade: over budget, but the state carries and the last days
  // offered recovery. Own word, own shape, own tone - never a shade of amber.
  stimulus: { word: "Reiz",       ic: "surge", c: C.orange },
  red:      { word: "rot",        ic: "stop",  c: C.red },
  unknown:  { word: "keine Daten", ic: "na",   c: C.grey },
};
// The backend names its grades green/yellow/stimulus/red; the panel's register
// keys are green/amber/stimulus/red. ONE translation, here, so no view invents
// a second one - and no view derives a grade of its own.
const STAGE_TONE = { green: "green", yellow: "amber", stimulus: "stimulus", red: "red" };
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
/* Minuten als "4 h 20" bzw. "50 min" - die Schreibweise, in der ein Fahrer
   ueber Fahrtzeit spricht. Steht hier draussen und nicht in rDurability, damit
   die 60 nicht im Geltungsbereich des Quelltext-Waechters landet. */
function hmn(mins) {
  const m = Math.max(0, Math.round(+mins || 0));
  return m < 60 ? `${m} min` : `${Math.floor(m / 60)} h ${String(m % 60).padStart(2, "0")}`;
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

/* Der Zeitraum, ueber den DFA-Daten VORLIEGEN - immer neben der DFA-Zahl und
 * nie neben dem Wellness-Zeitraum. Fehlen die Felder (aelteres Backend), wird
 * NICHTS behauptet: lieber keine Angabe als eine geliehene. */
function dfaSpan(s) {
  if (!s || !s.dfa_done || !s.dfa_from || !s.dfa_to) return "";
  const days = Math.round((Date.parse(s.dfa_to) - Date.parse(s.dfa_from)) / 864e5) + 1;
  return ` <span class="mut">(ab ${dMed(s.dfa_from)}, ${fmt(days)} Tage)</span>`;
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
  // A continuous x axis is an OPTION, never a rebuild. Without x0/x1 every
  // existing caller takes the index path below - the same code, byte for byte,
  // which is what test_panel_design.js freezes: this helper carries four views
  // at once, so a silent change here tears open all four.
  const xy = o.x0 != null && o.x1 != null;
  const X = xy
    ? (v) => padL + ((v - o.x0) / ((o.x1 - o.x0) || 1)) * pw
    : (i) => padL + (i / (n - 1)) * pw;
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
        // index mode reads p.i, continuous mode reads p.x - one line apart, so
        // no caller has to learn a second helper
        const at = X(xy ? p.x : p.i);
        const r = p.r || 3.4, op = p.op == null ? 1 : p.op;
        // A point that carries an id can be brushed. The handlers reach it
        // through these attributes instead of rebuilding the view on every
        // pointer move - a re-render would fight the pointer it follows.
        const tag = p.id ? ` data-dot="${esc(String(p.id))}" data-r="${r}" data-op="${op}"` : "";
        g += `<circle cx="${at}" cy="${Y(p.v)}" r="${r}" fill="${p.f === false ? "none" : (p.c || s.c)}" stroke="${p.c || s.c}" stroke-width="1.6" opacity="${op}"${tag}/>`;
        // the ring is a shape, not a second colour - WCAG 1.4.1, and the same
        // rule that gives every state its own icon form
        if (p.ring) {
          g += `<circle class="pickring" cx="${at}" cy="${Y(p.v)}" r="${r + 4}" fill="none" stroke="${p.c || s.c}" stroke-width="1.8" opacity="0.95"/>`;
        }
      }
    } else if (s.t === "xyband") {
      // Das Unsicherheitsband: eine FLAECHE ZWISCHEN ZWEI KURVEN ueber der
      // stetigen Achse. Eigener Zweig, kein erweitertes `area` - `area` fuellt
      // gegen die Nulllinie und laeuft ueber den INDEX. Im Indexmodus ist
      // dieser Typ nicht erreichbar, die eingefrorene Referenz bleibt also
      // unberuehrt (dieselbe Vorsicht wie bei xyline).
      const pp = (s.p || []).filter((q) => q && q.lo != null && q.hi != null);
      if (pp.length > 1) {
        const up = pp.map((q, k) => `${k ? "L" : "M"}${X(q.x).toFixed(1)} ${Y(q.hi).toFixed(1)}`).join("");
        const down = [...pp].reverse().map((q) => `L${X(q.x).toFixed(1)} ${Y(q.lo).toFixed(1)}`).join("");
        g += `<path d="${up}${down}Z" fill="${s.c || C.tx3}" opacity="${s.op == null ? 0.14 : s.op}"/>`;
      }
    } else if (s.t === "xyline") {
      // Eine Gerade ueber der stetigen Achse. Eigener Zweig, weil die
      // Linienzuege unten ueber den INDEX laufen - im Indexmodus ist dieser
      // Typ nicht erreichbar, die eingefrorene Referenz bleibt unberuehrt.
      const pp = (s.p || []).filter((q) => q && q.v != null);
      if (pp.length > 1) {
        g += `<path d="${pp.map((q, k) => `${k ? "L" : "M"}${X(q.x).toFixed(1)} ${Y(q.v).toFixed(1)}`).join("")}"`
          + ` fill="none" stroke="${s.c || C.tx2}" stroke-width="${s.w || 2}"`
          + `${s.d ? ` stroke-dasharray="${s.d}"` : ""} opacity="${s.lop == null ? 1 : s.lop}"/>`;
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
    // The xy attributes are emitted ONLY in continuous mode: an extra
  // attribute on every chart would change the output of all four existing
  // views, which is exactly what the frozen reference forbids.
  const xyAttr = xy
    ? ` data-x0="${o.x0}" data-x1="${o.x1}" data-y0="${o.y0}" data-y1="${o.y1}" data-padt="${padT}" data-padb="${padB}" data-h="${h}"`
    : "";
  return `<svg class="ch" viewBox="0 0 ${w} ${h}" preserveAspectRatio="none" data-n="${n}" data-padl="${padL}" data-padr="${padR}" data-w="${w}"${xyAttr}>${g}${lbl}${xh}</svg>`;
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
// What _boot fetches up front. Named here so a failed boot can mark exactly
// those payloads as failed instead of leaving their views in a loading hint
// that never resolves.
const ROLE_LABEL = { long: "Lange Fahrt", quality: "Qualität", endurance: "Grundlage" };

const BOOT_KEYS = ["status", "readiness", "days", "load", "coach", "day_context", "ramp_tests"];

const TABS = [
  ["trainer", "Trainer"],
  ["signale", "Signale"],
  ["heute", "Heute"], ["kalender", "Kalender"], ["fitness", "Fitness"],
  ["akt", "Aktivitäten"], ["belastung", "Belastung"], ["dfa", "DFA"],
  ["quellen", "Quellen"],
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
/* Etiketten sind Kategorien, keine Urteile - sie tragen ausschließlich das
   Kategorienregister (Blau/Violett/Cyan/Magenta/Schiefer + deep/grey).
   Grün/Gelb/Rot bleiben den Zuständen vorbehalten; ein "krank"-Chip in Rot
   wäre ein Urteil, wo nur eine Messbedingung gemeint ist. */
const CTX_COLOR = {
  normal: C.slate, nachtschicht: C.violet, spaetschicht: C.blue,
  reise: C.cyan, alkohol: C.magenta, krank: C.deep, uhr_nicht_getragen: C.grey,
};

/* Die sechs Familien mit Abschnitts-Haken (docs/ausbau.md P2).

   FORM UND KUERZEL TRAGEN DIE IDENTITAET, die Farbe verstaerkt. Das ist keine
   Vorsicht, sondern am Code begruendet: ROLE belegt in GENAU DIESER Ansicht
   pow/hr/dfa/cad/vel/alt, also alle sechs Toene des Datenregisters, und die
   Rundenliste zeichnet den EF-Balken in ROLE.pow und den DFA-Balken in
   ROLE.dfa. Eine Farbe allein koennte hier nichts tragen, was nicht schon
   vergeben waere. Deshalb stehen die Haken zusaetzlich in einer EIGENEN
   Spalte mit Kopfzeile, nicht zwischen den rollengefaerbten Balken.

   Urteilsfarben kommen hier nicht vor - eine Familie ist eine Kategorie,
   kein Urteil. Ein Test erzwingt beides. */
/* VIER Familien, seit 15.09.2026. "Schwelle" und "lange Fahrt" sind
   stillgelegt, der Grund steht bei section_marks.RETIRED: die Schwelle misst
   nicht ueber Bloecke (ihr Wert kommt aus dem Stufentest), und die lange
   Fahrt rechnet mit der Grundlage identisch. Ein Bedienelement ohne Wirkung
   ist schlimmer als keines. Diese Liste wird NICHT gegen die Payload
   gepflegt - sie traegt Form, Kuerzel und Farbe, und das sind
   Gestaltungsentscheidungen; welche Familien das Backend annimmt, steht in
   `sm.families` und entscheidet der Schreibweg. */
const FAM = {
  vo2max:    { k: "VO2",  ic: "famVo2", c: C.magenta, l: "VO2max" },
  sweetspot: { k: "SST",  ic: "famSst", c: C.violet,  l: "SweetSpot" },
  tempo:     { k: "TMP",  ic: "famTmp", c: C.blue,    l: "Tempo" },
  endurance: { k: "GA",   ic: "famEnd", c: C.slate,   l: "Grundlage" },
};
/* Was in einer Familie steckt - in kurzen Saetzen, zum ENTSCHEIDEN, nicht zum
   Lernen der Methode. Drei Fragen je Familie, immer dieselben drei:
   womit fuettere ich sie, was wird daraus gerechnet, was aendert sich dadurch
   an meinen Wattvorgaben.

   DIE ZAHLEN STEHEN HIER NICHT. Sie kommen aus der Payload (`corridors`,
   `discard_s`, `min_for_source`) - eine Schwelle als Literal im Frontend
   waere eine zweite Wahrheit, und der Dublettenwaechter meldet sie zu Recht. */
const FAM_HELP = (key, sm) => {
  const c = ((sm && sm.corridors) || {})[key] || null;
  const discard = (sm && sm.discard_s) != null ? sm.discard_s : null;
  const min3 = (sm && sm.min_for_source) != null ? sm.min_for_source : null;
  // Die Sonderabfrage für die Schwelle ist mit der Familie gefallen. Sie stand
  // hier VOR dem Blockzweig, weil `FAM_BLOCKS` zwei Fragen beantwortete und
  // die zweite falsch (§7, dreiundzwanzigster Fall). Jetzt trägt die Liste
  // wieder EINE Bedeutung: wer darin steht, misst über Blöcke.
  if (FAM_BLOCKS.includes(key)) {
    return [
      ["Womit du sie fütterst",
       "Die Abschnitte, in denen du wirklich in diesem Bereich gefahren bist — "
       + "der harte Teil. Nicht das Einrollen davor, nicht die Pause danach."],
      ["Was daraus gerechnet wird",
       "Aus jedem angehakten Abschnitt wird ein DFA-a1-Wert genommen: ein Maß dafür, "
       + "wie gleichmäßig dein Herz in diesem Abschnitt geschlagen hat. Je härter du "
       + "fährst, desto kleiner wird er."
       + (discard != null
          ? ` Die ersten ${discard} Sekunden jedes Abschnitts zählen nicht mit — der Wert `
            + "pendelt sich dort erst ein." : "")],
      ["Was es an deinen Vorgaben ändert",
       (c
         ? `Für diese Familie soll der Wert zwischen ${fmt(c[0], 2)} und ${fmt(c[1], 2)} liegen. `
           + "Liegt er darüber, war es zu leicht und der Trainer schlägt mehr Watt vor. "
           + "Liegt er darunter, war es zu hart und er nimmt Watt weg."
         : "Der Zielbereich steht in den Einstellungen des Trainers.")
       + (min3 != null
          ? ` Ab ${min3} markierten Einheiten rechnet er mit deinen Werten statt mit einer Schätzung.`
          : "")],
    ];
  }
  return [
    ["Womit du sie fütterst",
     "Die ruhigen Teile einer Fahrt — die Abschnitte, in denen du gleichmäßig gefahren bist. "
     + "Harte Stücke mittendrin lässt du draußen."],
    ["Was daraus gerechnet wird",
     "Aus den angehakten Abschnitten entsteht ein bereinigter Verlauf. Darauf wird für jede "
     + "Fahrtstunde abgelesen, wie viel Leistung du zu diesem Zeitpunkt noch locker halten "
     + "konntest. Blöcke braucht es dafür nicht."],
    ["Was es an deinen Vorgaben ändert",
     "Die Watt für lange Einheiten — und wie stark sie mit jeder Stunde Fahrtzeit nachgeben."],
  ];
};

const RAMP_HELP = [
  ["Womit du sie fütterst",
   "Mit einer ganzen Fahrt, nicht mit einzelnen Abschnitten. Eine Stufenfahrt, bei der "
   + "die Leistung regelmäßig steigt, bis es nicht mehr geht."],
  ["Was daraus gerechnet wird",
   "Beide Schwellen aus einer Fahrt: die, ab der es anstrengend wird, und die, ab der "
   + "du nicht mehr lange durchhältst. Gemessen wird aus den ungedünnten Strömen."],
  ["Was es an deinen Vorgaben ändert",
   "Die Watt für Schwellen- und Tempoeinheiten. Diese Kachel misst beim Klick, "
   + "die vier anderen haken nur an."],
];

/* Welche Familien ueber BLOECKE messen und welche ueber den Stundenverlauf.
   Grundlage und lange Fahrt brauchen keine Bloecke - sie messen ueber
   `hours` (P2c, dritte Zeile). */
const FAM_BLOCKS = ["vo2max", "sweetspot", "tempo"];

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
    // Which payloads were ever REQUESTED, and which ones came back broken.
    // Without the first register a block whose data was never fetched looks
    // exactly like one that is still loading - which is how the goal payload
    // stayed missing from 0.20.0 to 0.42.0 without anyone noticing.
    this._asked = {};
    this._failed = {};
    this._psOpen = null;
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
    this._dayctx = null;   // Etiketten-Archiv + Vokabular + Quellenblock (B5/B6)
    this._ctxDlg = null;   // ISO-Datum, dessen Beschriftungsdialog offen ist
    this._syncDlg = null;  // Abgleich-Dialog: {state, report, msg}
    this._syncBusy = false;
    this._ctxErr = null;
    this._ctxBusy = false;
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

  /* Etikett eines Tages aus dem geladenen Archiv, mit Anzeigename aus dem
     Vokabular - EINE Quelle (der day_context-Leseweg), damit Chips, Marker
     und Titel nie auseinanderlaufen. */
  _ctxOf(date) {
    const dc = this._dayctx;
    const entry = dc && dc.days && dc.days[date];
    if (!entry) return null;
    const meta = (dc.tags || {})[entry.tag] || {};
    return { tag: entry.tag, weight: entry.weight,
             label: meta.label || entry.tag, note: entry.note || "" };
  }

  async _ctxWrite(date, tag) {
    if (!date || this._ctxBusy) return;
    this._ctxBusy = true;
    try {
      await this._ws("set_day_context", { date, tag });
      // Alles neu laden, was von Gewichten abhängt - und die Scroll-Lage
      // VOR dem Re-Render sichern: innerHTML wirft sie sonst mit den alten
      // Knoten weg, und die Ansicht springt unter der Hand nach oben
      // (die 0.9.x-Fehlerklasse, nur am Scroll statt am Ablesekasten).
      const scroll = this.scrollTop;
      const wanted = [
        this._ws("today"), this._ws("days", { weeks: this._weeks }),
        this._ws("day_context"), this._ws("coach"),
        this._signals ? this._ws("signals", { days: this._sigDays }) : null,
      ];
      const [today, days, dayctx, coachData, signals] = await Promise.all(wanted);
      this._today = today; this._days = days; this._dayctx = dayctx;
      this._coach = coachData;
      if (signals) this._signals = signals;
      this._ctxDlg = null; this._ctxErr = null;
      this._render();
      this.scrollTop = scroll;
    } catch (err) {
      this._ctxErr = String((err && err.message) || err);
      this._render();
    } finally { this._ctxBusy = false; }
  }

  /* "Wie lange trägt die Grundlage?" — Leitzahl oben, die beiden Gruppen als
     Beleg darunter, auf EINER Skala gegen die Marke. Ein Gruppenvergleich als
     Längendifferenz statt als Kopfrechnen; der Abstand zur Marke steht ohne
     Erklärung da. Jede Zahl hier kommt aus der Payload — Schwelle, Trennstelle,
     Mindestzahlen, Filtergrenzen. Keine davon steht in dieser Datei. */
  /* Die Durability-Kachel: eine Punktwolke ueber der Arbeit, keine zwei Balken.
     Zwei Balken bei 0,0 % und 1,4 % gegen eine 5er-Skala zeigen nichts, und die
     Zweiteilung beantwortet die Ueberschrift nicht - gefragt ist, wie lange es
     traegt und ob es besser wird (docs/ausbau.md G1).

     Die Punkte tragen das KATEGORIENregister, die Marke das Urteilsregister.
     Punkte nach "ueber/unter der Marke" einzufaerben waere genau die Mischung,
     die dieses Haus dreimal ein Release gekostet hat. */
  rDurability(d) {
    const mark = d.decoupling_good;
    const pts = (d.points || []);
    if (!pts.length) return "";
    // 0.46.0: die Punktwolke ist als HAUPTBILD entfallen. Sie zeigte die
    // Entkopplung ueber der Arbeit samt Trendgerade - und die Gerade durfte
    // ohnehin nicht gezeichnet werden, weil die Steigung nicht von null zu
    // unterscheiden ist. Was blieb, war ein Bild, das nichts traegt, neben
    // einer zweiten Kachel in einem anderen Reiter, die DIESELBE Frage mit
    // einer anderen Rechnung beantwortete (PROJEKTSTAND §7). Die Verweigerung
    // der Leitzahl steht weiter im Text, die Bins und Bloecke rechnen
    // unveraendert aus denselben Punkten - nur gezeichnet wird jetzt die
    // Ermuedungskurve. Der Ablesestreifen haengt an ihr statt an der Wolke.
    const band = (b) => `<span class="durband">
      <em>${b.to_kj == null ? "ab " + fmt(b.from_kj, 0) : fmt(b.from_kj, 0) + "–" + fmt(b.to_kj, 0)} kJ</span>
      <b class="tn">${b.median == null ? "–" : sign(b.median, 1) + " %"}</b>
      <span class="mut">${b.n} ${b.n === 1 ? "Einheit" : "Einheiten"}${b.thin ? ", zu dünn" : ""}</span></span>`;

    const blockRow = (b) => {
      const why = { thin: "zu dünn belegt", flat: "kein gesicherter Trend",
                    beyond: "Schnittpunkt jenseits des Blocks" }[b.reason] || "";
      return `<span class="durband">
        <em>${dMed(b.start)} – ${dMed(b.end)}</em>
        <b class="tn">${b.tipping_kj == null ? "–" : fmt(b.tipping_kj, 0) + " kJ"}</b>
        <span class="mut">${b.n} Einheiten, Gewicht ${fmt(b.w, 1)}${why ? " — " + why : ""}</span></span>`;
    };

    /* Ein Feld aus lauter Strichen, das nicht sagt, WORAUF es wartet, ist ein
       Feld, das man aufhoert zu lesen. Der juengste Block sagt es - aus seinen
       eigenen Zahlen, nicht aus einer Schaetzung ueber den ganzen Bestand. */
    const newest = (d.blocks || []).slice(-1)[0];
    const blockWait = !newest || newest.tipping_kj != null ? "" : (() => {
      if (newest.reason === "thin") {
        return `Der laufende Block trägt ${fmt(newest.w, 1)} von ${fmt(d.min_weight_sum_block, 0)}
          nötigen Gewichten — es fehlen rund ${fmt(newest.need_w, 1)}, also ein bis zwei gleichmäßige
          lange Fahrten.`;
      }
      if (newest.reason === "flat") {
        return `Im laufenden Block zeigt die Steigung in eine Richtung, aber nicht deutlich genug
          (${newest.slope_t == null ? "–" : fmt(newest.slope_t, 2)} statt ${fmt(d.min_slope_t, 1)}).${
          newest.need_n == null ? "" : ` Bei dieser Streuung bräuchte der Block rund
          ${fmt(newest.need_n, 0)} Einheiten statt ${fmt(newest.n, 0)}.`} Was am schnellsten hilft,
          sind Fahrten mit sehr unterschiedlicher Arbeit — gleich lange Fahrten schärfen nichts.`;
      }
      return `Im laufenden Block läge der Schnittpunkt jenseits seiner arbeitsreichsten Fahrt
        (${fmt(newest.max_kj, 0)} kJ). Er erscheint, sobald eine Fahrt darüber hinausgeht.`;
    })();

    const weight = d.weight
      ? ` Zum Einordnen: mit dem zuletzt gemessenen Gewicht (${fmt(d.weight.kg, 1)} kg vom ${dMed(d.weight.day)}) sind ${fmt(d.max_kj, 0)} kJ rund ${fmt(d.max_kj / d.weight.kg, 1)} kJ/kg — Nebeninformation, gerechnet wird in kJ.`
      : " Eine Umrechnung in kJ/kg steht nicht dabei: im Archiv liegt kein Gewicht.";

    /* Der Kopf (H1/H2) ist in 0.50.0 entfallen. Was er trug, steht anderswo
       oder ist bewusst aufgegeben - beides steht im Rechenweg, sonst sucht es
       in vier Wochen jemand. Die Progressionszeile ist die einzige der drei
       Angaben, die im Graphen nicht steht; sie sagt, wie LANG die naechste
       Fahrt sein darf, und gehoert damit dorthin, wo ueber Dauern entschieden
       wird: "Die naechsten Wochen". Die Grenze der Regel ist mitgewandert -
       sie gehoert zur Zahl. */
    const forward = d.needed_sessions
      ? `<p class="src"><b>Was die Messung voranbringt:</b> bei dieser Streuung
          bräuchte es rund ${fmt(d.needed_sessions, 0)} qualifizierte Einheiten statt ${fmt(d.n, 0)}.
          Lange Fahrten zählen dabei stärker als viele kurze — der Fehler der Steigung schrumpft mit der
          Spannweite der Arbeit, nicht nur mit der Stückzahl.</p>`
      : "";

    return `<h3 class="secname">Wie lange trägt die Grundlage?</h3>
      <div class="card pad" data-grp="fat">
        <p class="effect">${esc(d.headline)}</p>
        ${this.rFatigue(this._fatigue)}
        ${this.rBlocks(this._blocks)}
        ${(() => {
          /* Zwei Abschnitte, die auf diesem Bestand durchgehend NICHTS sagen:
             alle Bänder unter der Marke, kein Block mit Trend - eine halbe
             Bildschirmseite Striche unter dem längsten Erklärabsatz der Karte.
             Sie werden NICHT gelöscht, sie können wieder etwas sagen. Sie
             klappen zu, und darüber steht eine Zeile mit dem Stand.
             DIE DATENLAGE ENTSCHEIDET, NICHT DER CODE: sobald ein Band die
             Marke reißt oder ein Block einen Trend trägt, geht der Abschnitt
             von selbst auf. */
          const loud = (d.bins || []).filter((b) => b.median != null && b.median >= mark);
          const trend = (d.blocks || []).filter((b) => b.tipping_kj != null);
          const open = loud.length > 0 || trend.length > 0;
          const summary = [
            loud.length
              ? `${fmt(loud.length)} von ${fmt((d.bins || []).length)} Arbeitsbändern über der
                 ${fmt(mark, 0)}-%-Marke`
              : `Entkopplung in allen Arbeitsbändern unter der ${fmt(mark, 0)}-%-Marke`,
            trend.length
              ? `${fmt(trend.length)} von ${fmt((d.blocks || []).length)} Blöcken trägt einen Trend`
              : "kein Block trägt bisher einen Trend",
          ].join("; ");
          return `<details class="more"${open ? " open" : ""}><summary>${summary}</summary>
            <h4 class="subsec">Wie stark entkoppelt es?</h4>
            <p class="hint"><b>Mediane je Arbeitsband</b> — eine Beschreibung dessen, wo die Fahrten
              liegen, keine Vorhersage. Über einer <i>anderen Achse</i> als die Kurve oben; warum,
              steht im Rechenweg:</p>
            <div class="durbands">${d.bins.map(band).join("")}</div>
            <h4 class="subsec">Wird es besser?</h4>
            <p class="hint">Der Kipppunkt je ${fmt(d.block_weeks, 0)}-Wochen-Block.
              Ein Block, der eine der drei Regeln reißt, bleibt leer und wird nicht überbrückt:</p>
            <div class="durbands">${d.blocks.map(blockRow).join("")}</div>
            ${blockWait ? `<p class="hint">${blockWait}</p>` : ""}</details>`;
        })()}
        <p class="hint">${ico("bike", C.tx2, 13)} <b>Was das ausbaut:</b> Durability ist unabhängig von
          der VO2max trainierbar, und zwar durch niedrig- <i>und</i> hochintensives Ausdauertraining
          (Maunder 2023) — der Reiz entsteht durch Qualität unter bestehender Ermüdung, nicht durch mehr
          Kilometer. Im Trainer-Reiter steht dafür die Einheit mit dem Zweck „Durability, spezifisch“.</p>
        <details class="more"><summary>Der Rechenweg</summary>
          ${forward}
          <p class="src"><b>Zwei Achsen unter einer Überschrift, mit Absicht.</b> Die
            Schwellenleistung liest sich über die DAUER — die angesammelte Arbeit hängt an der
            Intensität und holte den Bergeffekt zurück, an dem eine frühere Messrunde scheiterte.
            Die Entkopplung liest sich über die ARBEIT — ein Zeitschnitt hielt hier nicht.
            <b>Beides ist am selben Bestand begründet</b>, und deshalb steht es getrennt statt
            vereinheitlicht: eine gemeinsame Achse hätte eine der beiden Begründungen kassiert,
            und zwar stillschweigend.</p>
          <p class="src"><b>Welche Einheiten zählen:</b> ab ${fmt(d.min_minutes, 0)} Minuten,
            Intensität unter ${fmt(d.max_intensity, 0)}, nicht auf der Rolle. Ausgelassen wurden
            ${d.dropped.short} zu kurze, ${d.dropped.intense} zu intensive,
            ${d.dropped.indoor} auf der Rolle, ${d.dropped.variable} zu wellige
            (Variabilitätsindex über ${fmt(d.vi_none, 2)}),
            ${d.dropped.no_power} <b>ohne Leistungsmessung</b> — über deren Gleichmäßigkeit ist nichts
            bekannt, sie sind deshalb nicht „wellig“, sondern unbekannt —,
            ${d.dropped.no_decoupling} ohne Entkopplungswert und ${d.dropped.no_work} ohne Arbeitswert.</p>
          <p class="src"><b>Worauf die Auswertung wirklich ruht:</b> ${fmt(d.n, 0)} Einheiten, davon
            ${fmt(d.n_full, 0)} mit vollem Gewicht, ${fmt(d.n_partial, 0)} anteilig und
            ${fmt(d.n_zero, 0)} mit Gewicht null. Zusammen ergibt das ein Gewicht von
            ${fmt(d.w_sum, 1)} — das ist die Zahl, die zählt, nicht die Stückzahl. Nötig für eine
            Leitzahl: ${fmt(d.min_weight_sum, 0)}, je Block ${fmt(d.min_weight_sum_block, 0)}.</p>
          <p class="src"><b>Warum Gleichmäßigkeit gewichtet und nicht ausgeschlossen wird:</b> ein
            Ausschluss ist eine Ja/Nein-Entscheidung über eine stufenlose Größe. Der
            Variabilitätsindex (normalisierte durch mittlere Leistung, aus den eigenen Feldern
            gerechnet) zählt bis ${fmt(d.vi_full, 2)} voll und ab ${fmt(d.vi_none, 2)} gar nicht,
            dazwischen anteilig. Die beiden Grenzen sind eine <b>Setzung</b>.</p>
          <p class="src"><b>Die Trendgerade und warum hier ${d.blocked ? "keine" : "eine"} Leitzahl
            steht:</b> gemessene Steigung ${d.slope == null ? "–" : sign(d.slope, 2) + " % je 1.000 kJ"},
            Standardfehler ${d.slope_se == null ? "–" : fmt(d.slope_se, 2)}, Verhältnis
            ${d.slope_t == null ? "–" : fmt(d.slope_t, 2)}. Erst ab dem ${fmt(d.min_slope_t, 1)}-fachen
            des eigenen Fehlers lässt sich eine Steigung von null unterscheiden — eine Setzung, und
            darunter wird weder eine Leitzahl genannt noch eine Gerade gezeichnet. Über die
            arbeitsreichste ausgewertete Fahrt (${fmt(d.max_kj, 0)} kJ) hinaus wird nie
            hochgerechnet.${weight}</p>
          <p class="src"><b>Womit Arbeit in Zeit umgerechnet wird:</b>
            ${d.power ? `${fmt(d.power.watts, 0)} W — der Median der qualifizierten Einheiten aus den
              letzten ${fmt(d.power.days, 0)} Tagen (${fmt(d.power.n, 0)} Einheiten). Der Median über den
              ganzen Bestand läge bei ${fmt(d.power_pool, 0)} W und stammte damit aus einer anderen
              Form; deshalb das nahe Fenster, das sich bei zu dünner Belegung sichtbar auf
              ${fmt(d.power_days_fallback, 0)} Tage weitet.`
              : `keine — im nahen Fenster stehen zu wenige Einheiten, auch nach der Weitung auf
              ${fmt(d.power_days_fallback, 0)} Tage. Es bleibt bei kJ.`}</p>
          <p class="src"><b>Die drei Formen, die Durability ausbauen:</b> negativ gesplittete Fahrt
            (die letzten 30–60 min zwischen aerober Schwelle und FTP) · Intervalle an den Anfang einer
            langen Fahrt, danach 1–2 h ruhig · späte Anstiege von 5–20 min, 6–8 Wochen vor einem Ziel.
            <b>Mit der Warnung, die dazugehört:</b> der Reiz soll aus der Anstrengung kommen, nicht aus
            dem Hungerast — schlecht gefütterte Fahrten sind kein Durability-Training (über
            ${fmt(d.fuelling_g_per_h, 0)} g Kohlenhydrate je Stunde).</p>
          <p class="src"><b>Warum Rollenfahrten nicht mitzählen:</b> eine Setzung, kein
            Studienergebnis. Belegt ist, dass die Entkopplung stark von der Umgebung abhängt, und bei
            fester Last ist auch das Belastungsmuster ein anderes — im eigenen Bestand liegt der
            Variabilitätsindex auf der Rolle bei 1,03 gegen 1,06 draußen.</p>
          <p class="src"><b>Warum über der Arbeit und nicht über der Dauer:</b> Durability wird in der
            Literatur über angesammelte Arbeit gemessen, nicht über die Uhr (Maunder 2021; Spragg
            trennt das Leistungsprofil bei 2000 kJ). Die <i>Achse</i> ist belegt.</p>
          <p class="src"><b>Was der Kopf dieser Karte trug, und wo es geblieben ist.</b>
            Bis 0.49.2 standen hier drei Kacheln. Der naechste Schritt — wie lang die naechste
            Fahrt sein darf — steht jetzt im Wochenplan unter „Die nächsten Wochen“, samt der
            Grenze, aus welcher Kohorte der Aufschlag stammt und was er nicht ist — sie gehört
            zur Zahl und ist mit ihr gewandert. <b>Ersatzlos aufgegeben ist die
            Angabe zur längsten gleichmäßigen Fahrt</b> (Dauer, Datum und Leistung DIESER Fahrt):
            die Dauer steht am rechten Ende der Kurve, und die Wattzahl war der Durchschnitt
            jener einen Fahrt und nicht die Schwellenleistung an dieser Stelle — zwei
            verschiedene Größen, und gefahren wird nach der zweiten. Die Angabe fehlt also
            nicht, sie ist gestrichen.</p>
        <p class="src"><b>Die Grenze:</b> ${esc(d.source)}</p>
        </details>
      </div>`;
  }

  /* Die 5-%-Marke gibt es im Haus genau einmal: in const.py. Hier kommt sie
     ausschließlich aus einer Payload — steht keine bereit, wird NICHT
     eingefärbt, statt die Zahl zu erfinden. Quelltext-Wächter dagegen in
     test_panel_fixes.js: eine Ziffer 5 neben "decoupling"/"drop" lässt die
     Suite fallen. */
  /* Der Historienbeginn, dort wo er gebraucht wird: WIE WEIT eine DFA-Aussage
   * ueberhaupt zurueckreicht. Der Satz erscheint nur, wenn die DFA-Daten
   * SPAETER beginnen als die Aktivitaeten - sonst gaebe es nichts zu sagen und
   * ein Dauerhinweis stumpft ab. Gleiche Klasse wie "welche Fahrten zaehlen
   * und welche nicht" (docs/ausbau.md, Historienbeginn). */
  _historyNote() {
    const s = this._status;
    if (!s || !s.dfa_from || !s.dfa_done) return "";
    if (!s.activities_from || s.activities_from >= s.dfa_from) return "";
    const days = Math.round((Date.parse(s.dfa_to || s.dfa_from) - Date.parse(s.dfa_from)) / 864e5) + 1;
    const span = Math.round((Date.parse(s.dfa_to || s.dfa_from) - Date.parse(s.activities_from)) / 864e5) + 1;
    return `<p class="hint">${ico("info", C.blue, 13)} Die DFA-Auswertung beginnt am
      <b>${dMed(s.dfa_from)}</b>: ${fmt(s.dfa_done)} Auswertungen über <b>${fmt(days)} Tage</b>,
      während der Bestand ${fmt(span)} Tage zurückreicht. Jede DFA-gestützte Aussage stützt
      sich auf den kürzeren Zeitraum.</p>`;
  }

  /* ── Die Ermuedungskurve der aeroben Schwelle (docs/ausbau.md L1) ───────
     Hausmuster: Leitzahl oben, Beleg darunter, aufklappbarer Rechenweg,
     BELEG UND SETZUNG GETRENNT - im Bild wie im Text. Gemessenes traegt das
     Serienregister und volle Deckkraft, Gesetztes ist gestrichelt und grau.
     Keine Zahl dieser Kachel steht hier: jede kommt aus der Payload. */
  rFatigue(f) {
    // Fehlt die Payload, SAGT die Kachel das. Die stille Luecke aus 0.42.1
    // (rGoal und rPlanWeeks rendern nichts, weil ihre Payload nie angefordert
    // wurde) darf sich nicht wiederholen - und sie wird ueber _need("fatigue")
    // im Trainer-Zweig angefordert, auf dem einen Weg, nicht daneben.
    if (!f) return this._dataGap("fatigue", "Die Ermüdungskurve");
    const pr = f.progress || {};
    // Nach einem Algorithmus-Bump ist das Archiv leer, bis die Stroeme neu
    // geholt sind. Ein leerer Platz sieht aus wie ein Defekt - also steht da,
    // was laeuft und wie weit es ist.
    if (!f.measured.length && pr.pending) {
      const done = pr.done || 0, total = pr.total || pr.pending;
      const syncs = Math.ceil((pr.pending || 0) / (pr.batch || 25));
      return `<div class="card pad"><h3 class="secname">Ermüdungskurve der aeroben Schwelle</h3>
        <p>Die Auswertung wird gerade neu gerechnet: <b class="tn">${fmt(done)} von ${fmt(total)}</b>
        Einheiten fertig. Die Ströme werden in Bändern von ${fmt(pr.batch)} je Abgleich geholt,
        es fehlen also noch rund ${fmt(syncs)} Durchgänge. Die Kachel füllt sich danach von
        selbst — sie ist nicht defekt.</p>
        <i class="dbar"><s style="width:${Math.round(done / Math.max(1, total) * 100)}%;background:${ROLE.series}"></s></i></div>`;
    }
    if (!f.measured.length) {
      return `<div class="card pad"><h3 class="secname">Ermüdungskurve der aeroben Schwelle</h3>
        <p>Noch keine Fahrt über ${fmt(f.min_minutes)} Minuten, die ihren Stundenverlauf hergibt.
        Ohne eine zweite Fahrtstunde gibt es keinen Verlauf zu lesen — die Karte zeigt deshalb
        weder Messung noch Schätzung.</p>${this._fatigueDropped(f)}</div>`;
    }

    const lit = f.literature || [];
    // DIE ACHSE IST DIE GEPLANTE DAUER. Die Leitzahl beantwortet "welche
    // Leistung halte ich über eine Fahrt von X Stunden" — nicht "was war in
    // Stunde X". Die ungepaarte Reihe (Median je Fahrtstunde, t = Stundenmitte)
    // ist eine ANDERE Größe auf einer anderen Achse; sie steht als
    // Gegenrechnung in der Tabelle und nicht mehr im Graphen. Zwei Kurven auf
    // einer Achse wären zwei Antworten auf eine Frage.
    const plan = f.plan || [];
    const xs = [...plan.map((r) => r.hours), ...lit.map((r) => r.t)];
    const lows = [...lit.map((r) => r.lo), ...plan.map((r) => r.watts)].filter((v) => v != null);
    const his = [...lit.map((r) => r.hi), ...plan.map((r) => r.watts)].filter((v) => v != null);
    const y0 = Math.floor(Math.min(...lows) / 10) * 10 - 5;
    const y1 = Math.ceil(Math.max(...his) / 10) * 10 + 5;
    const solid = f.plan_solid_until_hours, thin = f.plan_thin_until_hours;
    // WO DIE SETZUNG ANFÄNGT, STEHT IM FELD, nicht in der Zeichnung: `beyond`
    // kommt aus der Payload. Eine gestrichelte Linie ist eine Gestaltung; wer
    // die Grenze aus den Punkten zurückrechnet, führt eine zweite Wahrheit.
    const within = lit.filter((r) => !r.beyond);
    const litBeyond = lit.filter((r) => r.beyond);
    // Der Übergabepunkt gehört BEIDEN Linien, sonst klafft eine Lücke.
    const brueck = within.length ? [within[within.length - 1]] : [];

    const graph = chart({
      h: 300, n: 2, x0: Math.min(...xs), x1: Math.max(...xs), y0, y1, grp: "fat",
      yf: (v) => fmt(v), label: "Schwellenleistung (W) über der Fahrtdauer", labelc: ROLE.series,
      s: [
        // SETZUNG zuerst, damit sie hinter der Messung liegt
        { t: "xyband", p: lit.map((r) => ({ x: r.t, lo: r.lo, hi: r.hi })), c: C.slate, op: 0.13 },
        { t: "xyline", p: within.map((r) => ({ x: r.t, v: r.watts })), c: C.slate, w: 2, lop: 0.9 },
        { t: "xyline", p: [...brueck, ...litBeyond].map((r) => ({ x: r.t, v: r.watts })),
          c: C.slate, w: 2, d: "5 4", lop: 0.9 },
        // DIE LEITZAHL darüber, Punktgröße nach der Weglassprobe
        { t: "dots", c: ROLE.series, p: plan.map((r) => ({
            x: r.hours, v: r.watts, r: r.band === "solid" ? 5.4 : 3.8,
            op: r.band === "solid" ? 1 : 0.75 })) },
        // Durchgezogen nur bis zum ERSTEN Riss — eine Linie mit einem Loch,
        // die dahinter weitergeht, behauptet Sicherheit, die es nicht gibt.
        { t: "xyline", p: plan.filter((r) => r.hours <= (solid || 0)).map((r) => ({ x: r.hours, v: r.watts })),
          c: ROLE.series, w: 2.6 },
        { t: "xyline", p: plan.filter((r) => r.hours >= (solid || 0)).map((r) => ({ x: r.hours, v: r.watts })),
          c: ROLE.series, w: 1.6, d: "3 3", lop: 0.75 },
      ],
    });

    // Der Ablesestreifen: FESTE Leiste im Kartenkopf, kein schwebender Kasten
    // (die Fehlerklasse ist seit 0.9.3 raus). Der Zeiger laeuft ueber das
    // feine Literaturraster, damit er gleitet statt auf vier Stunden
    // einzurasten; die gemessenen Werte stehen an ihren Stunden und sind
    // sonst null - eine Luecke im Streifen ist die ehrliche Auskunft
    // "hier gibt es keine Messung".
    const grid = lit;
    // Der Zeiger liest die LEITZAHL, wo es eine gibt — sie steht auf den
    // vollen Stunden der geplanten Dauer, nicht auf jedem Rasterpunkt.
    const planAt = grid.map((q) => plan.find((r) => Math.abs(r.hours - q.t) < 0.01) || null);
    // Der Ruhezustand der Leitzahl ist eine EIGENE Rechnung, nicht der erste
    // Rasterpunkt: der Anker ist der Fit bei Dauer null, das Raster beginnt bei
    // der ersten Fahrtstunde. Beide bleiben deshalb beschriftet - sonst sieht
    // der Sprung zwischen ihnen wie ein Rundungsfehler aus.
    const baseNote = `gemessen: ${fmt(f.anchor_n)} Fahrten in Stunde 1, Repräsentantenmethode `
      + `nach Andriolo, auf Intervals' eigener DFA-Fensterung`;
    this._grp.fat = {
      xy: true, n: grid.length,
      pts: grid.map((q) => ({ x: q.t, y: q.watts })),
      xl: (i) => fmt(grid[i].t, 2) + " h geplante Dauer"
        + (planAt[i] == null ? " — Studienform, keine Messung" : ""),
      lead: {
        base: fmt(f.anchor_base), baseColor: ROLE.series,
        baseLabel: "Ausgeruht, bei Dauer null", baseNote,
        // DIE FRAGE, die die große Zahl beantwortet: was kann ich über eine
        // Fahrt dieser Länge treten, sodass es am ENDE noch trägt.
        label: (i) => "Leistung für eine Fahrt von " + fmt(grid[i].t, 2) + " h",
        val: (i) => fmt(planAt[i] == null ? grid[i].watts : planAt[i].watts),
        color: (i) => (planAt[i] == null ? C.slate : ROLE.series),
        // Der RECHENWEG steht daneben, nicht in der Zahl: der verkettete
        // Schritt mit seiner Belegung, und die Weglassprobe als das, was die
        // Grenze zwischen gemessen und dünn gezogen hat.
        note: (i) => {
          const q = planAt[i];
          if (q == null) return "Studienform, keine Messung";
          const schritt = q.step == null ? "Anfangswert"
            : `Schritt ${sign(q.step)} W aus ${fmt(q.step_n)} `
              + `${q.step_n === 1 ? "Fahrt" : "Fahrten"}`;
          const probe = q.loo_shift == null ? ""
            : ` · einzelne Fahrt verschiebt bis ${fmt(q.loo_shift, 1)} W`;
          return `${q.band === "solid" ? "gemessen" : "dünn"} · ${schritt}${probe}`
            + ` · Studienform ${fmt(grid[i].watts)} W`;
        },
      },
      rows: [
        { l: "Leitzahl", c: ROLE.series, u: "W", dec: 0,
          vals: planAt.map((q) => (q ? q.watts : null)) },
        { l: "Studienform", c: C.slate, u: "W", dec: 0, vals: grid.map((q) => q.watts) },
        // SPANNE, nicht Breite: "143-151 W" sagt, wo die Setzung liegt, "7 W"
        // nur, wie breit sie ist. Bis 0.49.2 stand die eine Zahl in der Leiste
        // und die andere in der Tabelle darunter - unter demselben Namen.
        { l: "Bandbreite", c: C.slate, u: "W",
          vals: grid.map((q) => (q.lo == null || q.hi == null ? null : fmt(q.lo) + "–" + fmt(q.hi))) },
        { l: "Schritt", c: C.tx2, u: "W", dec: 1,
          vals: planAt.map((q) => (q && q.step != null ? q.step : null)) },
        { l: "Belegung", c: C.tx2, u: "", dec: 0,
          vals: planAt.map((q) => (q ? (q.step_n == null ? q.n : q.step_n) : null)) },
      ],
    };

    const rows = f.measured.map((r) => {
      const l = lit.find((q) => q.hour === r.hour);
      const dev = l ? r.watts - l.watts : null;
      // Die Zeile zeigt auf denselben Rasterpunkt wie der Zeiger im Graphen.
      const gi = grid.findIndex((q) => q.hour != null && q.hour === r.hour);
      return `<tr${gi < 0 ? "" : ` data-rg="fat" data-ri="${gi}"`}><td>Stunde ${r.hour}</td><td class="tn">${fmt(r.watts)} W</td>
        <td class="tn">${l ? fmt(l.watts) + " W" : "–"}</td>
        <td class="tn">${dev == null ? "–" : sign(Math.round(dev)) + " W"}</td>
        <td>${badge(r.band === "solid" ? "green" : r.band === "thin" ? "amber" : "slate",
          r.n + (r.n === 1 ? " Fahrt" : " Fahrten"))}</td></tr>`;
    }).join("");

    // BEIDE LESERICHTUNGEN, und beide enden am Bestand.
    const letzte = f.measured[f.measured.length - 1];
    const ziel = f.measured[0].watts - (f.measured[0].watts - (letzte.watts || 0)) / 2;
    const wann = f.literature.find((r) => r.watts <= ziel);
    const wannGemessen = wann && wann.hour != null
      ? f.measured.find((r) => r.hour === wann.hour) : null;
    return `<div class="card pad"><h3 class="secname">Ermüdungskurve der aeroben Schwelle</h3>
      <div class="statgrid lead"><div class="stat wide" data-lead="fat">
        <small class="ldl">Ausgeruht, bei Dauer null</small>
        <b class="tn lead1"><span class="ldv" style="color:${ROLE.series}">${fmt(f.anchor_base)}</span>
          <span class="unit">W</span></b>
        <span class="mut ldn">${baseNote}</span></div></div>
      ${readout("fat")}
      ${graph}
      <p class="hint">${ico("info", C.blue, 13)} <b>Dick und farbig ist gemessen</b>, dünn und grau
        ist die Studienform nach Gallo, an deiner Zahl verankert — ab Stunde
        ${fmt((thin || 0) + 1)} gestrichelt, weil der Bestand dort endet.
        ${solid ? `Getragen wird die Aussage bis Stunde ${fmt(solid)}.` : ""}</p>
      ${this._fatigueHistory(f)}
      ${this._fatigueDoubt(f)}
      <div class="twoway">
        <p><b>${fmt(letzte.t)} h — wie viel Watt?</b> ${fmt(letzte.watts)} W
          (${fmt(letzte.n)} ${letzte.n === 1 ? "Fahrt" : "Fahrten"}).</p>
        <p><b>${fmt(Math.round(ziel))} W — wie lange?</b> ${wann
          ? `bis <b class="tn">${fmt(wann.t, 2)} h</b>${wannGemessen
              ? ` (gemessen, ${fmt(wannGemessen.n)} ${wannGemessen.n === 1 ? "Fahrt" : "Fahrten"})`
              : " — Studienform, keine Messung"}`
          : "länger als deine längste Fahrt — darüber sagt die Karte nichts"}.</p>
      </div>
      ${this._fatigueHr(f)}
      <details class="more"><summary>Rechenweg</summary>
        <table class="dfatab"><thead><tr><th></th><th>gemessen</th><th>Studienform</th>
          <th>Abweichung</th><th>Belegung</th></tr></thead><tbody>${rows}</tbody></table>
        <p class="src"><b>Anker gemessen, Form gesetzt.</b> Die Kurve wird NICHT gemessen: der
          erwartete Effekt je Stunde liegt unter der Streuung der Einzelmessungen, dafür
          bräuchte es ein Vielfaches an gepaarten Fahrten. Die Messung widerspricht der
          Literatur nicht — sie kann sie nur nicht bestätigen.</p>
        <p class="src"><b>Abweichungen von Andriolo</b> — deshalb nennt die Leitzahl oben die
          Fensterung und nicht das Verfahren: keine RR-Daten, die Fensterung
          ist Intervals' eigene und nicht dokumentiert; das Artefaktkriterium entfällt und wird
          durch den Anteil verworfener Punkte ERSETZT; das Dynamikkriterium wird als Kennzahl
          je Stunde ausgewiesen statt als Filter angewandt.</p>
        <p class="src"><b>Die Zeitachse ist die Bewegungszeit</b>, nicht die angesammelte Arbeit:
          die Belegung ist praktisch dieselbe, und eine Arbeitsachse koppelt an die Intensität
          und holt damit den Bergeffekt zurück.</p>
        ${f.plan_solid_until_hours && f.plan_thin_until_hours
            && f.plan_thin_until_hours > f.plan_solid_until_hours && f.selection_note
          // DER AUSWAHLEFFEKT DER SPÄTEN STUNDEN, an der Kachel und nicht nur
          // in der Spezifikation. Er steht nur dort, wo es eine dünne Zone
          // GIBT — sonst läse ihn der Athlet an einer Kurve, die ihn nicht
          // hat, und er verlöre seine Schärfe.
          ? `<p class="src warn"><b>Ab ${fmt(f.plan_solid_until_hours + 1)} Stunden wird die
             Zahl dünn.</b> ${esc(f.selection_note)}</p>` : ""}
        ${f.axis_note
          ? `<p class="src"><b>Was diese Achse nicht kennt.</b> ${esc(f.axis_note)}</p>` : ""}
        <p class="src"><b>Zwei Zahlen für dieselbe Sache, und das ist bekannt.</b> Der Trainer
          verankert seine Einheiten auf der Schwellenleistung aus dem Anker-Median
          (${f.aerobic_power != null ? fmt(f.aerobic_power) + " W" : "eigene Rechnung"}), diese
          Karte auf ${fmt(f.anchor_base)} W. Es sind verschiedene Rechnungen: dort das Mittel
          aller Messpunkte im Schwellenfenster über die GANZE Fahrt, über die letzten fünf
          Fahrten; hier der Fit bei genau alpha 0,75 auf der ERSTEN Stunde, über alle
          unstrukturierten Fahrten. Methodisch ist der Fit der sauberere Weg, und die erste
          Stunde ist der unermüdete Zustand — die Zusammenführung steht an, ist aber ein
          eigener Schritt, weil der Anker heute die Einheiten steuert. <b>Bis dahin: ein
          bekannter Unterschied, kein unbemerkter.</b></p>
        <p class="src"><b>Das Unsicherheitsband</b> ist die publizierte Streuung des
          −5-%-Zeitpunkts (${fmt(f.t5_published)} ± ${fmt(f.t5_published_sd)} min), auf den
          Verlust gerechnet. Diese Form erreicht −5 % nach ${fmt(f.t5_minutes)} min.</p>
        ${this._fatigueDropped(f)}
      </details></div>`;
  }

  /* Warum die Belegung so dünn ist: nicht weil zu wenig gefahren wurde,
     sondern weil der alpha-Strom erst ab einem bestimmten Datum existiert. Wer
     das nicht sieht, hält die dünne Kurve für einen Fehler. */
  _fatigueHistory(f) {
    const miss = (f.dropped_counts || {}).no_dfa || 0;
    if (!miss) return "";
    const list = (f.dropped || {}).no_dfa || [];
    const lang = list.filter((x) => (x.minutes || 0) >= f.min_minutes).length;
    return `<p class="hint">${ico("info", C.blue, 13)} <b>${fmt(miss)} Fahrten fehlen dieser Kurve,
      weil sie keinen DFA-Strom tragen</b>${lang ? `, davon ${fmt(lang)} über ${fmt(f.min_minutes)}
      Minuten` : ""} — sie liegen vor dem Beginn der DFA-Aufzeichnung. Es sind genau die langen
      ruhigen Fahrten, die die Kurve tragen würden. <b>Die dünne Belegung ist kein Fehler der
      Auswertung, sondern der Zuschnitt der Daten.</b></p>`;
  }

  /* Was an der gemessenen Reihe ZWEIFELHAFT ist, steht im Hauptbild - nicht im
     Rechenweg, wo es niemand sucht. Zwei Dinge koennen sie kippen, und beide
     haben dieselbe Wurzel: die Stundenwerte stammen aus VERSCHIEDENEN Fahrten. */
  _fatigueDoubt(f) {
    const out = [];
    const rising = f.occupancy_rising || [];
    if (rising.length) {
      const r = rising[0];
      out.push(`<p class="hint">${ico("warn", C.amber, 13)} <b>Die Belegung steigt, wo sie fallen
        müsste:</b> Stunde ${fmt(r.hour)} trägt ${fmt(r.n)} Fahrten, Stunde ${fmt(r.hour - 1)}
        nur ${fmt(r.previous)}. Jede Fahrt mit einer späteren Stunde hat auch die frühere — also
        liefern nicht alle Fahrten in der frühen Stunde einen Wert. Der Grund ist die Regel gegen
        Hochrechnung: abgelesen wird nur, wo die Schwelle im tatsächlich gefahrenen Bereich lag,
        und ausgeruht ist das nur bei den härteren Fahrten der Fall. <b>Die frühe Stunde steht
        damit auf einer anderen Auswahl als die späte</b>, und ein Teil des Abfalls ist diese
        Auswahl, nicht Ermüdung.</p>`);
    }
    const pair = (f.paired || []).find((q) => q.from_hour === 1);
    if (pair) {
      const un = (f.measured || []).length > 1
        ? f.measured[0].watts - f.measured[1].watts : null;
      const gp = -pair.delta;
      if (!pair.enough) {
        out.push(`<p class="hint">${ico("info", C.blue, 13)} Gepaart gerechnet — nur Fahrten, die
          beide Stunden selbst befüllen — stehen ${fmt(pair.n)} Paare zur Verfügung, nötig sind
          ${fmt(f.min_pairs)}. <b>Es wird deshalb keine gepaarte Zahl gezeigt</b>, statt eine auf
          einer Handvoll Fahrten zu behaupten.</p>`);
      } else if (un != null && Math.abs(un - gp) >= Math.max(2, Math.abs(un) * 0.25)) {
        out.push(`<p class="hint">${ico("warn", C.amber, 13)} <b>Gepaart fällt die Reihe anders:</b>
          ${sign(Math.round(un))} W ungepaart gegen ${sign(Math.round(gp))} W über ${fmt(pair.n)}
          Paare, bei denen jede Fahrt ihre eigene Kontrolle ist. <b>Die gepaarte Zahl ist die
          belastbarere.</b> Laufen beide auseinander, misst die ungepaarte Reihe zum Teil den
          Unterschied zwischen Fahrten und nicht den Verlauf innerhalb einer.</p>`);
      } else if (un != null) {
        out.push(`<p class="hint">${ico("ok", C.green, 13)} Gepaart und ungepaart liegen nah
          beieinander (${sign(Math.round(un))} W gegen ${sign(Math.round(gp))} W über
          ${fmt(pair.n)} Paare) — es gibt keinen Hinweis auf einen Auswahlfehler.</p>`);
      }
    }
    return out.join("");
  }

  /* Paket M - ein Wert je Block, ueber die Zeit. Je Familie eine Karte:
     Leitzahl oben (die Leistung im ersten eingeschwungenen Block), darunter
     der Verlauf, dann der Vorschlag. NICHTS greift automatisch. */
  rBlocks(b) {
    if (!b) return this._dataGap("blocks", "Die Blockmessung");
    const fam = b.families || {};
    const keys = Object.keys(fam);
    const pr = b.progress || {};
    if (!keys.length) {
      if (pr.pending) {
        const done = pr.done || 0, total = pr.total || pr.pending;
        return `<div class="card pad"><h3 class="secname">Leistung je Block</h3>
          <p>Die Auswertung wird gerade neu gerechnet: <b class="tn">${fmt(done)} von
          ${fmt(total)}</b> Einheiten fertig. Die Kachel füllt sich danach von selbst —
          sie ist nicht defekt.</p>
          <i class="dbar"><s style="width:${Math.round(done / Math.max(1, total) * 100)}%;background:${ROLE.series}"></s></i></div>`;
      }
      return `<div class="card pad"><h3 class="secname">Leistung je Block</h3>
        <p>Noch keine Einheit mit markierten Arbeitsabschnitten und DFA-Aufzeichnung.
        Gemessen wird je Block, nachdem die ersten ${fmt((b.discarded_s || 0) / 60, 0)} Minuten
        verworfen sind — vorher ist der Kreislauf nicht eingeschwungen.</p></div>`;
    }
    const NAME = { vo2max: "VO2max", sweetspot: "SweetSpot", tempo: "Tempo" };
    const karten = keys.map((key) => {
      const f = fam[key];
      const l = f.latest;
      const punkte = f.points || [];
      const lo = f.corridor[0], hi = f.corridor[1];
      // Die Belegung entscheidet, was gezeigt wird - nichts wird geglättet.
      const wenig = !f.trend;
      // Eigene Zeigergruppe je Familie. Sie liegt INNERHALB der Gruppe der
      // Ermuedungskurve - `closest` nimmt die naechste, also diese. Ohne sie
      // fing der aeussere Wrapper den Zeiger ab und schrieb einen Wert der
      // Kurve in ihre Leiste (PROJEKTSTAND §7, zehnter Fall).
      const grp = "blk_" + key;
      if (punkte.length > 1) {
        this._grp[grp] = {
          n: punkte.length,
          xl: (i) => (punkte[i].name || "ohne Namen") + " · " + dMed(punkte[i].date),
          rows: [
            // Aufgetragen ist der ERSTE eingeschwungene Block - also steht hier
            // sein eigener alpha, nicht der Median. Verlaufsgroesse gegen
            // Steuergroesse: derselbe Unterschied, den test_blocks.py erzwingt.
            { l: "erster Block", c: ROLE.series, u: "W", dec: 0, vals: punkte.map((q) => q.first_watts) },
            { l: "alpha dort", c: ROLE.series, u: "", dec: 2, vals: punkte.map((q) => q.first_alpha) },
            { l: "Median alpha", c: C.tx2, u: "", dec: 3, vals: punkte.map((q) => q.median_alpha) },
            { l: "Blöcke", c: C.tx2, u: "", dec: 0, vals: punkte.map((q) => q.n_blocks) },
          ],
          // KEIN `lead`: die Leitzahl dieser Karte ist die Leistung im ersten
          // eingeschwungenen Block und bleibt stehen, waehrend der Zeiger
          // ueber die Punkte faehrt. Sie ist eine Steuergroesse, keine
          // Ablesung - anders als in der Ermuedungskachel, und das ist
          // zugesichert statt zufaellig.
        };
      }
      const graph = punkte.length > 1 ? chart({
        h: 170, n: punkte.length, grp,
        y0: Math.floor(Math.min(...punkte.map((p) => p.first_watts)) / 10) * 10 - 10,
        y1: Math.ceil(Math.max(...punkte.map((p) => p.first_watts)) / 10) * 10 + 10,
        xt: punkte.map((p, i) => ({ i, t: dShort(p.date) })),
        label: "Leistung im ersten eingeschwungenen Block (W)", labelc: ROLE.series,
        s: [
          ...(f.trend ? [{ t: "line", v: punkte.map((p) => p.first_watts), c: ROLE.series, w: 2.4 }] : []),
          { t: "dots", c: ROLE.series, p: punkte.map((p, i) => ({ i, v: p.first_watts, r: 4.2 })) },
        ],
      }) : "";
      const zeilen = punkte.slice(-8).reverse().map((p) => `<tr>
        <td>${dMed(p.date)}</td>
        <td class="tn">${fmt(p.first_watts)} W</td>
        <td class="tn">${fmt(p.median_alpha, 3)}</td>
        <td class="mut">${p.block_alphas.map((a) => fmt(a, 2)).join(" · ")}</td>
        <td>${p.step_pct === 0
          ? badge("green", "im Korridor")
          : badge("amber", (p.step_pct > 0 ? "+" : "") + fmt(p.step_pct) + " %")}</td></tr>`).join("");
      return `<div class="card pad" data-grp="${grp}">
        <h4 class="subsec">${NAME[key] || key}</h4>
        <div class="statgrid lead"><div class="stat wide">
          <small>Leistung im ersten eingeschwungenen Block</small>
          <b class="tn lead1" style="color:${ROLE.series}">${fmt(l.first_watts)} <span class="unit">W</span></b>
          <span class="mut">bei alpha ${fmt(l.first_alpha, 2)} · ${dMed(l.date)} ·
            ${fmt(f.sessions)} ${f.sessions === 1 ? "Einheit" : "Einheiten"} von
            ${dMed(f.from)} bis ${dMed(f.to)}</span></div></div>
        ${f.first_is_weak ? `<p class="hint">${ico("warn", C.amber, 13)} <b>Der erste
          Arbeitsabschnitt dieser Einheit trägt weniger Leistung als die folgenden</b> — das
          Gerät hat dort vermutlich einen lockeren Abschnitt als Arbeit etikettiert. Die
          Leitzahl nimmt trotzdem den ersten; getauscht wird erst, wenn die Auswahl nach
          Leistung entschieden ist.</p>` : ""}
        ${(f.order_conflicts || []).length ? `<p class="hint">${ico("warn", C.amber, 13)}
          <b>${fmt(f.order_conflicts.length)} Einheit(en) widersprechen der Gegenprobe:</b>
          dort läuft unsere Reihenfolge der Blockwerte anders als die von Intervals selbst
          berechnete. <b>Das ist noch kein Fehler.</b> Intervals mittelt jeden Block samt
          Anlauf, wir verwerfen ihn — der Unterschied ist systematisch, und bei eng
          beieinanderliegenden Blöcken entscheiden schon zwei Hundertstel über die Richtung.
          <b>Die Prüfung schlägt derzeit auch bei sauberen Ausschnitten an</b>; ihre Toleranz
          wird noch an den Daten bestimmt. Bis dahin: ein Hinweis zum Nachsehen, keine
          Fehlermeldung.</p>` : ""}
        ${graph ? readout(grp) : ""}
        ${graph}
        ${wenig ? `<p class="hint">${ico("info", C.blue, 13)} <b>${fmt(f.sessions)}
          ${f.sessions === 1 ? "Einheit" : "Einheiten"}</b> — unter ${fmt(f.min_for_trend)} wird
          keine Verlaufslinie gezeichnet. ${f.sessions < 3
            ? "Zwei Messungen sind kein Verlauf."
            : "Die Zahl steht, die Richtung nicht."}</p>` : ""}
        <p class="hint">${ico("info", C.blue, 13)} <b>Vorschlag fürs nächste Mal:
          ${fmt(l.suggested_watts)} W</b>${l.step_pct === 0
            ? ` — unverändert, dein alpha lag mit ${fmt(l.median_alpha, 3)} im Korridor
                ${fmt(lo, 2)}–${fmt(hi, 2)}.`
            : ` (${l.step_pct > 0 ? "+" : ""}${fmt(l.step_pct)} %) — dein alpha lag mit
                ${fmt(l.median_alpha, 3)} ${l.step_where === "above" ? "über" : "unter"} dem
                Korridor ${fmt(lo, 2)}–${fmt(hi, 2)}, um ${fmt(l.step_gap, 3)}.`}
          <b>Das System schlägt vor, du entscheidest</b> — und misst beim nächsten Mal ohnehin,
          was du tatsächlich gefahren bist.</p>
        <p class="hint">Die Steuerung ruht auf <b>${fmt(l.n_blocks)}
          ${l.n_blocks === 1 ? "Block" : "Blöcken"}</b>: ${l.block_alphas.map((a) => fmt(a, 2)).join(" und ")},
          Median ${fmt(l.median_alpha, 3)}${l.alpha_span >= 0.15
            ? ` — die Spanne von ${fmt(l.alpha_span, 2)} ist groß, der Median mittelt hier zwischen
                zwei weit auseinanderliegenden Werten.` : "."}</p>
        <details class="more"><summary>Die letzten Einheiten</summary>
          <table class="dfatab"><thead><tr><th>Datum</th><th>erster Block</th>
            <th>Median alpha</th><th>Blöcke</th><th>Schritt</th></tr></thead>
            <tbody>${zeilen}</tbody></table></details>
      </div>`;
    }).join("");
    return `<h3 class="secname">Leistung je Block</h3>
      ${karten}
      <p class="hint">${ico("warn", C.amber, 13)} <b>Diese Zahlen gelten für diese Einheiten auf
        der Rolle</b>, nicht für dieselbe Familie draußen: derselbe alpha-Wert steht je nach
        Zusammenhang für eine andere Leistung — am eigenen Bestand liegen zwischen beiden
        rund 40 W. Gemessen wird je Block, nachdem die ersten
        ${fmt((b.discarded_s || 0) / 60, 0)} Minuten verworfen sind (Rogers: vorher ist der
        Kreislauf nicht im Gleichgewicht).</p>`;
  }

  /* L1b - die HF-Korrektur. GLEICHWERTIGER Teil der Karte, aber vollständig
     als SETZUNG beschriftet: die eigene Messung findet den Anstieg nicht, und
     der Grund steht dabei. Die gemessene Spalte kommt aus denselben Fahrten
     wie die Kurve darüber, damit "nicht wiederfindbar" eine eigene Zahl ist
     und kein Zitat aus einer Studie. */
  _fatigueHr(f) {
    if (!f.aerobic_hr || !(f.hr_drift_expected || []).length) return "";
    const rows = f.hr_drift_expected.map((e) => {
      const m = (f.measured || []).find((r) => r.hour === e.hour);
      const dev = m && m.hr != null ? m.hr - e.bpm : null;
      return `<tr><td>Stunde ${e.hour}</td><td class="tn">${fmt(e.bpm)} bpm</td>
        <td class="tn">${m && m.hr != null ? fmt(m.hr) + " bpm" : "–"}</td>
        <td class="tn">${dev == null ? "–" : sign(Math.round(dev)) + " bpm"}</td>
        <td class="mut">${m && m.hr_n ? fmt(m.hr_n) + (m.hr_n === 1 ? " Fahrt" : " Fahrten") : "–"}</td></tr>`;
    }).join("");
    return `<details class="more"><summary>Die Herzfrequenz zur Schwelle — und warum sie steigt</summary>
      <p>Das Panel nennt <b class="tn">${fmt(f.aerobic_hr)} bpm</b> als aerobe Schwelle.
        <b>Das gilt für den ausgeruhten Zustand.</b> Nach Stevenson steigt die Schwellen-HF
        mit der Dauer, während die Leistung fällt — wer sich nach Stunden noch an die
        ausgeruhte Zahl hält, fährt zu hart.</p>
      <table class="dfatab"><thead><tr><th></th><th>erwartet (Setzung)</th>
        <th>am eigenen Bestand</th><th>Abweichung</th><th>Belegung</th></tr></thead>
        <tbody>${rows}</tbody></table>
      <p class="src"><b>Die linke Spalte ist Literatur, keine Messung.</b> Stevenson misst
        ${fmt(f.hr_drift_source_rest)} bpm ausgeruht gegen ${fmt(f.hr_drift_source_2h)} bpm
        nach zwei Stunden; übertragen wird nur der prozentuale Anstieg
        (${fmt(f.hr_drift_per_hour_pct, 2)} % je Stunde), auf deine eigene ausgeruhte Zahl.</p>
      <p class="src"><b>Warum die rechte Spalte das nicht bestätigt.</b> Stevenson misst im
        standardisierten Stufentest, wo die Belastung kontrolliert ist. Im Feld ist sie das
        nie: dort folgt die HF-Änderung fast vollständig der Leistungsänderung — gemessen
        wird dann nicht die Ermüdungsverschiebung, sondern dass in der zweiten Stunde eine
        andere Leistung getreten wurde. Die Aussage bleibt richtig, sie ist an
        Alltagsfahrten nur nicht prüfbar.</p>
      <p class="src">Die Temperatur fehlt in den Daten und wird hier <b>benannt statt
        nachgerüstet</b> — ein zusätzliches Feld löst einen Vollabruf aus, und die Leistung
        ist ohnehin der stärkere Störer.</p></details>`;
  }

  /* Welche Fahrten NICHT zählen - namentlich, mit Grund und mit ihrer Zahl.
     Ohne die Namen sucht der Athlet in zwei Wochen, warum eine Fahrt fehlt,
     an die er sich erinnert. */
  _fatigueDropped(f) {
    const d = f.dropped || {};
    const words = {
      structured: ["strukturiert", `mehr als ${fmt(f.max_above_z2)} % der Zeit über Zone 2 — der Block läge in Stunde 1 und das Ausfahren in Stunde 2, das sähe aus wie Ermüdung`],
      short: ["zu kurz", `unter ${fmt(f.min_minutes)} Minuten — ohne zweite Stunde kein Verlauf`],
      variable: ["zu ungleichmäßig", "die Leistung schwankt zu stark, um eine Schwelle abzulesen"],
      no_zones: ["ohne Zonenzeiten", "ohne sie ist nicht entscheidbar, ob die Einheit strukturiert war"],
      no_dfa: ["ohne DFA-Strom", "die Uhr hat für diese Fahrt kein alpha-1 aufgezeichnet"],
      no_activity: ["unbrauchbar", "kein verwertbarer Datensatz"],
      // Die Gründe der MARKIERTEN Auswahl vergibt fatigue.py, und von dort
      // kommen auch ihre Wörter. In 0.56.0 fehlte hier eines, und die Kachel
      // zeigte den Rohschlüssel.
      ...(f.dropped_words || {}),
    };
    // Gezaehlt wird aus den ZAEHLFELDERN, nicht aus den Listen: die Listen
    // koennen gekappt sein, die Zahl darf es nie. Sonst behauptet die Karte
    // eine kleinere Luecke, als der Bestand hat.
    const counts = f.dropped_counts || {};
    const countOf = (reason, items) => (counts[reason] != null ? counts[reason] : items.length);
    const total = Object.keys(d).reduce((sum, reason) => sum + countOf(reason, d[reason]), 0);
    if (!total) return "";
    const blocks = Object.entries(d).map(([reason, items]) => {
      const shown = countOf(reason, items);
      // Kein Rohschlüssel in der Anzeige: fehlt ein Wort, steht das da.
      const [label, why] = words[reason] || ["ohne Beschreibung", ""];
      // Jede Fahrt ist KLICKBAR (derselbe Weg wie aus der DFA-Liste) und nennt,
      // wo es sie gibt, ihre markierten Abschnitte und den Grund der Messung.
      const list = items.slice(-8).reverse().map((x) =>
        `<li><a class="lnk" data-act="gotoact" data-id="${esc(x.activity_id)}">${
          esc(x.name || "ohne Namen")}</a> vom ${dMed(x.date)}${this._sectionText(x.sections)}${
          x.above_z2 != null
          ? ` — <b class="tn">${fmt(x.above_z2, 1)} %</b> über Zone 2` : ""}${
          reason === "short" ? ` — <b class="tn">${fmt(x.minutes)} min</b>` : ""}${
          x.detail ? ` — ${esc(x.detail)}` : ""}</li>`).join("");
      return `<p class="src"><b>${esc(label)}: ${fmt(shown)}</b> — ${esc(why)}</p>
        <ul class="droplist">${list}${shown > 8
          ? `<li class="mut">… und ${fmt(shown - 8)} weitere</li>` : ""}</ul>`;
    }).join("");
    return `<p class="src"><b>Von ${fmt(total + (f.rides_used || 0))} Einheiten zählen
      ${fmt(f.rides_used)}</b> — ${fmt(total)} bleiben draußen:</p>${blocks}`;
  }

  /* Die markierten Abschnitte einer Fahrt als Text: Beginn in der Fahrt und
     Dauer, aus dem Anker. `start_index` zählt Sekunden im 1-Hz-Strom. Ohne
     Abschnitte (Namenserkennung) steht nichts da. */
  _sectionText(sections) {
    const rows = (sections || []).filter((x) => x && x.start_index != null);
    if (!rows.length) return "";
    return " — " + rows.map((x) => `ab ${dur(x.start_index)}`
      + (x.seconds != null ? `, ${dur(x.seconds)}` : "")).join(" · ");
  }

  /* DIE FAHRTENLISTE: welche Fahrten die Kurve tragen, und welche markierten
     nicht, mit Grund. Ohne sie ist der Kurvenschalter nicht nachprüfbar —
     die Kachel nennt eine Zahl, und niemand sieht, ob es die richtigen sind.
     Die Zahl kommt aus dem Zählfeld (`rides_used`), die Gründe mit ihren
     Wörtern aus der Payload. */
  _curveRides(f) {
    if (!f) return "";
    const used = f.used || [];
    const rows = used.slice().reverse().map((x) => `<li><a class="lnk" data-act="gotoact"
        data-id="${esc(x.activity_id)}">${esc(x.name || "ohne Namen")}</a> vom ${dMed(x.date)}${
        this._sectionText(x.sections)} — Stunde${(x.hours_with_value || []).length === 1 ? "" : "n"}
        mit Wert: <b class="tn">${(x.hours_with_value || []).map((h) => fmt(h)).join(", ")}</b></li>`).join("");
    return `<details class="ridelist"><summary>Welche Fahrten die Kurve tragen:
        <b class="tn">${fmt(f.rides_used || 0)}</b></summary>
      ${rows ? `<ul class="droplist">${rows}</ul>` : `<p class="src">Noch keine Fahrt mit Wert.</p>`}
      ${this._fatigueDropped(f)}</details>`;
  }

  _decGood() {
    const a = this._status && this._status.decoupling_good;
    if (a != null) return a;
    const b = this._load && this._load.thresholds && this._load.thresholds.decoupling_good;
    if (b != null) return b;
    const c = this._coach && this._coach.durability && this._coach.durability.decoupling_good;
    return c != null ? c : null;
  }

  /* Abgleich mit Intervals. Zwei Gänge: erst zeigen, was verschwinden würde,
     dann auf Bestätigung ausführen - und der zweite Gang schickt genau die
     IDs mit, die im ersten angezeigt wurden. Hat sich der Befund zwischen
     Anzeige und Klick geändert, führt das Backend NICHTS aus und sagt das.
     Es gibt keinen Weg, eine einzelne Einheit zu löschen: der Abgleich hat
     immer nur ein Ergebnis, Gleichstand mit Intervals. */
  async _syncOpen() {
    if (this._syncBusy) return;
    this._syncBusy = true;
    this._syncDlg = { state: "load", what: "Frage Intervals nach der ganzen Historie …" };
    this._render();
    try {
      this._syncDlg = { state: "report", report: await this._ws("reconcile") };
      // Der Handler hat den Coordinator neu geladen. Beides hier hält Events:
      // ohne das Verwerfen zeigt der offene Tab die Liste vom Öffnen weiter,
      // auch wenn die geplante Einheit drüben längst gelöscht ist.
      // _cal wird faul nachgeladen (_need prüft auf null), _days NICHT - der
      // Kalender-Reiter bekommt es nur beim Start und beim Wochenwechsel. Ohne
      // den ausdrücklichen Nachzug stünde er leer da.
      this._cal = null;
      this._days = await this._ws("days", { weeks: this._weeks });
    } catch (err) {
      this._syncDlg = { state: "error", msg: String((err && err.message) || err) };
    } finally {
      this._syncBusy = false;
    }
    this._render();
  }

  async _syncRun() {
    const dlg = this._syncDlg;
    if (!dlg || dlg.state !== "report" || this._syncBusy) return;
    const ids = (dlg.report && dlg.report.removable) || [];
    if (!ids.length) return;
    this._syncBusy = true;
    // Scroll-Lage VOR dem ersten Re-Render sichern - innerHTML wirft sie mit
    // den alten Knoten weg (dieselbe Fehlerklasse wie beim Etikett), und
    // schon die Lade-Anzeige ist ein Re-Render.
    const scroll = this.scrollTop;
    this._syncDlg = { state: "load", what: "Gleiche ab …" };
    this._render();
    try {
      const res = await this._ws("reconcile", { confirm: ids });
      this._syncDlg = res.applied
        ? { state: "done", report: res }
        : { state: "report", report: res, stale: !!res.stale };
      if (res.applied) {
        // Alles wegwerfen, was aus den Aktivitäten gerechnet wird - sonst
        // zeigt der Kopf 238 und die Liste weiter 239.
        this._acts = null; this._thr = null; this._fatigue = null; this._blocks = null; this._pmc = null; this._today = null;
        this._coach = null; this._load = null; this._cal = null; this._signals = null;
        const [status, days] = await Promise.all([
          this._ws("status"), this._ws("days", { weeks: this._weeks })]);
        this._status = status; this._days = days;
        await this._setTab(this._tab);
      }
    } catch (err) {
      this._syncDlg = { state: "error", msg: String((err && err.message) || err) };
    } finally {
      this._syncBusy = false;
    }
    this._render();
    this.scrollTop = scroll;
  }

  /* Was der Abgleich geprüft hat, in Worten. Die Aufschlüsselung kommt aus dem
     Bericht (checked_activities / checked_unavailable / checked_dfa) und wird
     NICHT aus dem Kopfbereich zusammengerechnet - das wäre eine zweite
     Wahrheit über denselben Vorgang (docs/ausbau.md D6a). */
  _syncWhat(rep) {
    const parts = [];
    const add = (n, one, many) => { if (n) parts.push(`<b>${fmt(n)}</b> ${n === 1 ? one : many}`); };
    add(rep.checked_activities, "gefahrene Einheit", "gefahrene Einheiten");
    add(rep.checked_unavailable, "Platzhalter", "Platzhalter");
    add(rep.checked_dfa, "DFA-Auswertung ohne Einheit", "DFA-Auswertungen ohne Einheit");
    if (!parts.length) return `<b>${fmt(rep.checked || 0)}</b> archivierte Einträge`;
    return parts.length === 1 ? parts[0]
      : parts.slice(0, -1).join(", ") + " und " + parts[parts.length - 1];
  }

  _syncRow(item) {
    const sport = SPORT[item.type] || null;
    const when = item.date ? dMed(item.date) : "ohne Datum";
    const what = item.kind === "unavailable" ? "Strava-Platzhalter"
      : item.kind === "dfa" ? "DFA-Rest ohne Einheit"
      : (item.name || (sport ? sport.l : "Einheit"));
    return `<li class="syncrow">
      ${sport ? ico(sport.ic, sport.c, 15) : ico("na", C.tx3, 15)}
      <b>${esc(when)}</b><span class="cn">${esc(what)}</span>
      ${item.dfa ? `<em class="tn">inkl. DFA</em>` : ""}</li>`;
  }

  _syncPopover() {
    const dlg = this._syncDlg;
    const head = `<div class="ctxhead"><b>Mit Intervals abgleichen</b>
      <button class="ctxx" data-act="syncclose" title="schließen">${ico("stop", C.tx2, 18)}</button></div>`;
    let body = "";
    if (dlg.state === "load") {
      body = `<p class="ctxcur"><span class="pulse">${esc(dlg.what || "einen Moment …")}</span></p>`;
    } else if (dlg.state === "error") {
      body = `<div class="ctxerr">${ico("warn", C.amber, 15)}<span>${esc(dlg.msg)}</span></div>
        <p class="ctxwhy">Es wurde nichts entfernt. Der Abgleich fasst das Archiv erst an,
        wenn die Antwort vollständig und fehlerfrei vorliegt.</p>`;
    } else if (dlg.state === "done") {
      const r = dlg.report.removed || {};
      const n = (r.activities || 0) + (r.dfa || 0) + (r.unavailable || 0);
      body = n
        ? `<p class="ctxcur">${ico("ok", C.green, 15)} Entfernt: <b>${fmt(r.activities || 0)}</b>
             ${r.activities === 1 ? "Einheit" : "Einheiten"}, <b>${fmt(r.dfa || 0)}</b> DFA-Auswertungen,
             <b>${fmt(r.unavailable || 0)}</b> Platzhalter.</p>
           <p class="ctxwhy">Das Archiv steht jetzt auf Gleichstand mit Intervals.</p>`
        : `<p class="ctxcur">${ico("ok", C.green, 15)} Nichts zu tun - das Archiv war bereits im Gleichstand.</p>`;
    } else {
      const rep = dlg.report || {};
      const missing = rep.missing || [];
      const pct = Math.round((rep.share || 0) * 1000) / 10;
      const scope = rep.full_history
        ? `die ganze Historie (${esc(rep.oldest || "")} bis ${esc(rep.newest || "")})`
        : `den Zeitraum ${esc(rep.oldest || "")} bis ${esc(rep.newest || "")}`;
      if (dlg.stale) {
        body += `<div class="ctxerr">${ico("warn", C.amber, 15)}<span>Der Befund hat sich seit
          der Anzeige geändert - es wurde nichts entfernt. Bitte neu ansehen.</span></div>`;
      }
      if (!missing.length) {
        body += `<p class="ctxcur">${ico("ok", C.green, 15)} Gleichstand: ${this._syncWhat(rep)}
          ${rep.checked === 1 ? "ist" : "sind"} in Intervals vorhanden.</p>`;
      } else if (rep.capped) {
        body += `<div class="ctxerr">${ico("warn", C.amber, 15)}<span><b>${fmt(missing.length)}</b>
          von ${fmt(rep.checked || 0)} Einheiten fehlen drüben (${String(pct).replace(".", ",")} %).
          Das ist mehr als ${Math.round((rep.cap_limit || 0.2) * 100)} % - <b>es wurde nichts
          entfernt</b>. So sieht kein Aufräumen aus, sondern ein fehlgeschlagener Abruf.</span></div>`;
      } else {
        body += `<p class="ctxcur"><b>${fmt(missing.length)}</b>
          ${missing.length === 1 ? "Einheit ist" : "Einheiten sind"} in Intervals nicht mehr
          vorhanden. Geprüft wurde ${scope}.</p>`;
      }
      if (missing.length) {
        body += `<ul class="synclist">${missing.map((m) => this._syncRow(m)).join("")}</ul>`;
      }
      if (missing.length && !rep.capped) {
        body += `<button class="ctxchip syncgo" style="--cc:${C.amber}" data-act="syncgo">
          ${ico("sync", C.amber, 15)}<span class="cn">Jetzt abgleichen</span>
          <span class="cw tn">entfernt genau diese ${fmt(missing.length)} aus dem Archiv</span></button>`;
      }
      body += `<p class="ctxwhy">Der Abgleich liest nur. Nach Intervals geht dabei nichts -
        was dort steht, kann hier nicht verschwinden.</p>`;
      // Was NICHT geprüft wurde. Ohne diesen Satz klingt eine wahre Aussage
      // über das Archiv wie eine Aussage über den Kalender (docs/ausbau.md D6).
      body += `<p class="ctxwhy">Geprüft wird das <b>Archiv</b> — gefahrene Einheiten und
        Platzhalter. <b>Geplante Einheiten gehören nicht dazu:</b> sie stehen im Kalender von
        Intervals und werden bei jedem Abruf neu geholt, nicht archiviert. Eine drüben gelöschte
        Planung verschwindet deshalb von selbst; dieser Knopf stößt den Abruf mit an.</p>`;
    }
    return `<div class="ctxback" data-act="syncclose"></div>
      <div class="ctxdlg" role="dialog" aria-modal="true" aria-label="Mit Intervals abgleichen">
        ${head}${body}</div>`;
  }

  async _boot() {
    this.shadowRoot.innerHTML = this._skeleton();
    this._view = this.shadowRoot.getElementById("view");
    this._attach();
    try {
      const [status, rd, days, load, coachData, dayctx, rtests, smarks] = await Promise.all([
        this._ws("status"), this._ws("readiness"),
        this._ws("days", { weeks: this._weeks }), this._ws("load"), this._ws("coach"),
        this._ws("day_context"), this._ws("ramp_tests"), this._ws("section_marks"),
      ]);
      this._dayctx = dayctx;
      this._rtests = rtests;
      this._smarks = smarks;
      this._status = status; this._rd = rd; this._days = days; this._load = load;
      this._coach = coachData;
      for (const key of BOOT_KEYS) { this._asked[key] = true; delete this._failed[key]; }
      this._err = null;
    } catch (err) {
      this._err = String(err && err.message || err);
      for (const key of BOOT_KEYS) { this._asked[key] = true; this._failed[key] = this._err; }
    }
    // Paint the frame first so the panel is not blank while the tab's own
    // payloads travel, THEN build the tab the one way tabs are built. Until
    // 0.42.1 _boot rendered directly and never went through _setTab, so the
    // first paint of the trainer tab silently skipped `goal` - the payload
    // only _setTab asks for. Every tab now takes the same path.
    this._render();
    await this._setTab(this._tab);
    this._routeFromHash();
  }

  async _need(what) {
    this._asked[what] = true;
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
      if (what === "fatigue" && !this._fatigue) this._fatigue = await this._ws("fatigue");
      if (what === "smarks" && !this._smarks) this._smarks = await this._ws("section_marks");
      if (what === "blocks" && !this._blocks) this._blocks = await this._ws("blocks");
      if (what === "cal" && !this._cal) this._cal = await this._ws("calendar");
      delete this._failed[what];
    } catch (err) {
      this._err = String(err && err.message || err);
      this._failed[what] = this._err;
    }
  }

  async _setTab(t) {
    this._tab = t;
    // parallel, not one after the other: three round trips in sequence is the
    // difference between "instant" and "why is this still loading"
    if (t === "trainer") {
      await Promise.all([this._need("coach"), this._need("workouts"), this._need("goal"),
                         this._need("fatigue"), this._need("blocks")]);
    }
    if (t === "heute") await this._need("today");
    if (t === "signale") await this._need("signals");
    if (t === "fitness") await this._need("pmc");
    if (t === "akt") await this._need("akt");
    if (t === "dfa") await this._need("thr");
    if (t === "quellen") {
      await Promise.all([this._need("fatigue"), this._need("blocks"),
                         this._need("smarks")]);
    }
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
        <button class="syncbtn" data-act="sync"
          title="Prüfen, ob Einheiten in Intervals gelöscht wurden - liest nur">
          ${ico("sync", C.tx2, 15)}<span>Abgleichen</span></button>
      </header>
      <nav id="tabs"></nav>
      <div id="view"><div class="card pad">Lade Daten …</div></div>
    </div>`;
  }

  /* What a block says when its data is not there.

     Until 0.42.1 two blocks answered that question with an empty string and
     one with a loading hint that never resolved - so a payload that was NEVER
     REQUESTED looked exactly like one still in flight, and `goal` went
     unfetched on first paint from 0.20.0 to 0.42.0 without a single symptom.
     That is the same error class as the silent window widening in H2: a thing
     that does not happen has to SAY that it did not happen.

     Three states, three different sentences - and "never requested" is a bug
     in the panel, not an empty archive, so it says so. */
  _dataGap(key, label) {
    if (this._failed[key]) {
      return `<div class="card pad err">Nicht geladen: ${label} —
        ${esc(this._failed[key])}</div>`;
    }
    if (this._asked[key]) {
      return `<div class="card pad">Wird noch geladen: ${label} …</div>`;
    }
    return `<div class="card pad err">Nie angefordert: ${label}. `
      + `Das ist ein Fehler im Panel, kein leerer Bestand — bitte den Reiter neu `
      + `wählen und, wenn es bleibt, melden.</div>`;
  }

  _render() {
    const tabs = this.shadowRoot.getElementById("tabs");
    tabs.innerHTML = TABS.map(([id, l]) =>
      `<button class="tab ${this._tab === id ? "on" : ""}" data-act="tab" data-id="${id}">${l}</button>`
    ).join("");
    const hs = this.shadowRoot.getElementById("hstat");
    const s = this._status;
    // Die DFA-Zahl traegt IHREN Zeitraum, nicht den der Wellness-Tage. Bis
    // 0.44.0 stand "58 DFA" direkt neben "489 Tage" und legte nahe, die 58
    // verteilten sich darueber - sie liegen alle in den letzten 105 Tagen.
    // Keine fehlende Angabe, sondern eine irrefuehrende Nachbarschaft.
    hs.innerHTML = s
      ? `${s.importing ? '<span class="pulse">Import läuft …</span> · ' : ""}${fmt(s.activities)} Einheiten · ${fmt(s.wellness_days)} Tage · ${fmt(s.dfa_done)} DFA${dfaSpan(s)}${s.athlete ? " · " + esc(s.athlete) : ""}`
      : "";
    this._grp = {};
    let html = "";
    if (this._err && !this._rd) {
      html = `<div class="card pad err">Daten konnten nicht geladen werden: ${esc(this._err)}</div>`;
    } else if (this._tab === "trainer") {
      html = this.rGoal(this._goal) + this.rTrainer(this._coach, this._rd)
        + this.rPlanWeeks(this._goal, ((this._coach || {}).durability || {}).progression);
    }
    else if (this._tab === "signale") html = this.rSignale(this._signals);
    else if (this._tab === "heute") html = this.rHeute(this._today);
    else if (this._tab === "kalender") html = this.rKalender(this._days);
    else if (this._tab === "fitness") html = this.rFitness(this._pmc, this._range);
    else if (this._tab === "akt") html = this.rAkt(this._acts, this._sel);
    else if (this._tab === "belastung") html = this.rBelastung(this._load);
    else if (this._tab === "dfa") html = this.rDfa(this._thr, this._dfaSport);
    else if (this._tab === "quellen") html = this.rQuellen(this._fatigue, this._blocks);
    if (this._ctxDlg) html += this._ctxPopover();
    if (this._syncDlg) html += this._syncPopover();
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
      else if (act === "daylabel") {
        // nur Vergangenheit und heute - ein Etikett beschreibt eine Messung,
        // die es gibt, keinen Plan
        if (id && id <= this._now()) { this._ctxDlg = id; this._ctxErr = null; this._render(); }
      }
      else if (act === "ctxclose") { this._ctxDlg = null; this._ctxErr = null; this._render(); }
      else if (act === "sync") this._syncOpen();
      else if (act === "syncclose") { this._syncDlg = null; this._render(); }
      else if (act === "syncgo") this._syncRun();
      else if (act === "ctxset") this._ctxWrite(this._ctxDlg, id);
      else if (act === "ctxdel") this._ctxWrite(this._ctxDlg, null);
      else if (act === "rtset") this._rtWrite(id, true);
      else if (act === "rtdel") this._rtWrite(id, false);
      else if (act === "famsel") {
        // Dieselbe Kachel noch einmal hebt die Wahl auf - sonst gaebe es
        // keinen Weg zurueck in "keine Familie gewaehlt".
        this._famSel = this._famSel === id ? null : id;
        const scroll = this.scrollTop;
        this._render();
        this.scrollTop = scroll;
      }
      else if (act === "fammore") {
        this._famOpen = this._famOpen || {};
        this._famOpen[id] = !this._famOpen[id];
        const scroll = this.scrollTop;
        this._render();
        this.scrollTop = scroll;
      }
      else if (act === "swcurve") this._setCurveSource(el.dataset.on === "1");
      else if (act === "smmeasure") this._smMeasure(id);
      else if (act === "smconf") this._smConfirm(id);
      else if (act === "smark") {
        this._smWrite(id, el.dataset.fam, Number(el.dataset.idx),
                      el.dataset.on !== "1");
      }
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
      // the same card in the week view - its own open-state, because the same
      // session key can appear in more than one week
      else if (act === "psdetail") {
        this._psOpen = (this._psOpen === id ? null : id); this._render();
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
      // Die ZWEITE Ablesestelle: eine Zeile der Wertetabelle zeigt auf dieselbe
      // Stelle wie der Zeiger im Graphen und schreibt dieselbe Leiste. Eine
      // eigene Rechnung daneben waere eine zweite Fassung derselben Mechanik.
      const cell = e.target.closest && e.target.closest("[data-ri]");
      if (cell) { this._fillReadout(cell.dataset.rg, +cell.dataset.ri); return; }
      const g = e.target.closest && e.target.closest("[data-grp]");
      if (!g) { this._xhHide(); this._brush(null); return; }
      const idx = this._xhMove(g, e);
      if (idx == null) { if (!this._drag) { this._xhHide(); this._brush(null); } return; }
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
     pointer leaves - the values to go back to travel on the element itself.

     It marks, and it does NOTHING else. docs/ausbau.md asks for the matching
     row to be pulled into view here; on the live panel that was wrong. The
     host itself is the scrolling box (:host{overflow-y:auto}) and the table
     sits below the charts, so pulling the row into view moved the whole page
     and carried the chart out of the window - the view fled from the pointer
     that was reading it. A transient mark must never move the page it is drawn
     on. The row carries its bar; whoever wants to read it goes there, and a
     fixed pick names the session in the bar above the charts anyway. */
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
    if (!meta) return;
    let i = idx;
    if (i == null) {
      i = meta.n - 1;
      const first = meta.rows[0];
      if (first) while (i > 0 && first.vals[i] == null) i--;
    }
    const strip = this.shadowRoot.querySelector(`[data-rdo="${name}"]`);
    if (strip) {
      const xs = strip.querySelector(".rdox"), vs = strip.querySelector(".rdov");
      if (xs) xs.textContent = meta.xl(i) + (idx == null ? " (zuletzt)" : "");
      if (vs) {
        vs.innerHTML = meta.rows.map((r) => {
          const v = r.vals[i];
          // Eine Zeile darf eine SPANNE tragen statt einer Zahl. Die Bandbreite
          // stand bis 0.49.2 als Breite in der Leiste und als Spanne in der
          // Tabelle - zwei verschiedene Zahlen unter einem Namen.
          const shown = v == null ? "–"
            : (typeof v === "string" ? esc(v) : fmt(r.mul ? v * r.mul : v, r.dec || 0));
          return `<span class="rv"><i style="background:${r.c}"></i>${esc(r.l)}
            <b class="tn">${shown}${v != null && r.u ? " " + r.u : ""}</b></span>`;
        }).join("");
      }
    }
    this._fillLead(name, idx == null ? null : i);
  }

  /* Die grosse Zahl folgt dem Zeiger - aber NUR, wo die Kachel es ansagt.
     Die Ermuedungskurve sagt es an: dort ist die Leitzahl eine Ablesung und der
     Ausgangswert nur ihr Ruhezustand. Die Block-Karten sagen es NICHT an: dort
     ist die Leitzahl die Leistung im ersten eingeschwungenen Block, und die
     soll stehenbleiben, waehrend der Zeiger ueber die Punkte faehrt. Zwei
     Verhaltensweisen, EINE Mechanik - wer sie trennt, bekommt zwei Fassungen.
     Eine Gruppe ohne `lead` ruehrt hier nachweislich nichts an. */
  _fillLead(name, i) {
    const ld = (this._grp[name] || {}).lead;
    if (!ld) return;
    const box = this.shadowRoot.querySelector(`[data-lead="${name}"]`);
    if (!box) return;
    const put = (sel, txt, col) => {
      const el = box.querySelector(sel);
      if (!el) return;
      el.textContent = txt;
      if (col && el.style) el.style.color = col;
    };
    put(".ldl", i == null ? ld.baseLabel : ld.label(i));
    put(".ldv", i == null ? ld.base : ld.val(i), i == null ? ld.baseColor : ld.color(i));
    put(".ldn", i == null ? ld.baseNote : ld.note(i));
  }

  /* Returns the index under the pointer, so brushing and range dragging read
     the same position as the cursor line instead of computing their own. */
  _xhMove(g, e) {
    const name = g.dataset.grp, meta = this._grp[name];
    if (!meta) return null;
    const svg = g.querySelector("svg.ch");
    if (!svg) return null;
    const rect = svg.getBoundingClientRect();
    // Die Leiste gehoert zum DIAGRAMM, nicht zur ganzen Karte. Bis 0.49.2 fing
    // der Gruppen-Wrapper JEDE Zeigerbewegung ab - auch ueber Text, Tabellen
    // und den Rechenweg - und schrieb dafuer einen Index in die Leiste. In der
    // Durability-Kachel liegen die Block-Karten im selben Wrapper: ueber einer
    // Block-Kurve stand deshalb ein Wert der ERMUEDUNGSKURVE in der Leiste
    // (PROJEKTSTAND §7, zehnter Fall). Ausserhalb des Diagramms gibt es nichts
    // abzulesen, und dann wird auch nichts geschrieben.
    // Geprueft wird die SENKRECHTE Achse, und nur sie: dort sitzt der Fehler,
    // weil der Wrapper ueber die ganze Kartenhoehe reicht, das Diagramm aber
    // nicht. Waagerecht bleibt es beim Klemmen - ein Zeiger links neben der
    // Achsenbeschriftung meint den ersten Punkt und nicht "nichts", und das
    // ist seit 0.9.3 zugesichert.
    const bottom = rect.bottom != null ? rect.bottom : rect.top + rect.height;
    if (e.clientY < rect.top || e.clientY > bottom) return null;
    const W = +svg.dataset.w, padL = +svg.dataset.padl, padR = +svg.dataset.padr;
    const localX = (e.clientX - rect.left) * (W / rect.width);
    const pw = W - padL - padR;
    let idx, px;
    if (meta.xy) {
      // A scatter has no columns: over a continuous axis the nearest point is
      // the nearest in BOTH directions. Picking the nearest x alone would hand
      // back a point the pointer is nowhere near whenever two rides carry the
      // same work and different decoupling - which is the whole point of the
      // cloud.
      const H = +svg.dataset.h, padT = +svg.dataset.padt, padB = +svg.dataset.padb;
      const x0 = +svg.dataset.x0, x1 = +svg.dataset.x1;
      const y0 = +svg.dataset.y0, y1 = +svg.dataset.y1;
      const ph = H - padT - padB;
      const localY = (e.clientY - rect.top) * (H / rect.height);
      const PX = (v) => padL + ((v - x0) / ((x1 - x0) || 1)) * pw;
      const PY = (v) => padT + (1 - (v - y0) / ((y1 - y0) || 1)) * ph;
      let best = null;
      (meta.pts || []).forEach((p, i) => {
        if (p == null || p.x == null || p.y == null) return;
        const dx = PX(p.x) - localX, dy = PY(p.y) - localY;
        const d = dx * dx + dy * dy;
        if (best == null || d < best.d) best = { d, i, px: PX(p.x) };
      });
      if (best == null) return null;
      idx = best.i; px = best.px;
    } else {
      idx = Math.round(((localX - padL) / pw) * (meta.n - 1));
      idx = Math.max(0, Math.min(meta.n - 1, idx));
      px = padL + (idx / (meta.n - 1)) * pw;
    }
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
    // EINE RAMPE WIRD ALS RAMPE GEZEICHNET (0.51.1). Vorher standen drei flach
    // gleich hohe Bloecke da und der Text nannte EINEN Wert - einen Mittelwert
    // fuer einen Abschnitt, dessen ganzer Sinn das Ansteigen ist. Wer das
    // ansieht, sieht nicht, dass die Leistung waechst.
    const rs = entry.ramp_segment;
    const hFor = (pct) => Math.max(14, Math.min(100, pct * 0.78));
    let x = 0;
    const segs = blocks.map(([min, pct, label], i) => {
      const w = (min / total) * 100;
      let s;
      if (rs && i === rs.index) {
        // In Scheiben, mit linear wachsender Hoehe: keine CSS-Kunststuecke,
        // und es bleibt lesbar, wenn eine davon nicht rendert.
        const n = 14;
        s = Array.from({ length: n }, (_, k) => {
          const t = (k + 0.5) / n;
          const pc = rs.start_pct + (rs.end_pct - rs.start_pct) * t;
          return `<i class="wob" style="left:${x + (w * k) / n}%;width:${Math.max(0.4, w / n - 0.05)}%;
            height:${hFor(pc)}%;background:${colFor(pc)}"
            title="${esc(label)} · ${min} min · ${rs.start_w}\u2013${rs.end_w} W"></i>`;
        }).join("");
      } else {
        s = `<i class="wob" style="left:${x}%;width:${Math.max(0.6, w - 0.25)}%;
          height:${hFor(pct)}%;background:${colFor(pct)}"
          title="${esc(label)} · ${min} min · ${ftp ? Math.round(ftp * pct / 100) + " W" : pct + " % FTP"}"></i>`;
      }
      x += w;
      return s;
    }).join("");
    return `<div class="wobar">${segs}</div>`;
  }

  /* Which explanations are shared by SEVERAL sessions of the same list.

     A state warning belongs to the state, not to the session - printed on
     every card it is the same sentence three times, and nobody reads it the
     third time. It goes above the list ONCE; only a reason that belongs to a
     single session stays on its card (docs/ausbau.md I10). */
  _sharedReasons(list) {
    const seen = new Map();
    for (const entry of list || []) {
      const reason = (entry || {}).fit_reason;
      if (reason) seen.set(reason, (seen.get(reason) || 0) + 1);
    }
    return new Set([...seen.entries()].filter(([, n]) => n > 1).map(([r]) => r));
  }

  _reasonRow(reason, tone) {
    return `<div class="warnrow">${ico(tone === "red" ? "warn" : "info",
      tone === "red" ? C.red : C.amber, 16)} <span>${esc(reason)}</span></div>`;
  }

  /* ONE session card, for both views.

     The trainer tab and the week view show the same thing - a session, what it
     is made of, and what it costs today. Until 0.42.2 the week view had its
     own, poorer shape: no segment bar, no heart-rate window, no purpose line,
     five paragraphs of prose instead. A second, thinner rendering of the same
     object is the layout version of a second rule in the house.

     `o` carries what differs, and only that: whether the card is open, what it
     may print in its head, which reasons were already said above, and whether
     the calendar buttons belong here (they need a DATE, which a planned week
     does not have). */
  _sessionCard(entry, o) {
    const opts = o || {};
    const st = entry.stage || {};
    const tone = STAGE_TONE[st.key] || "unknown";
    const word = st.key === "stimulus" && opts.budget != null
      ? `${st.word} (über dem Budget von ${fmt(opts.budget)})`
      : `${st.word}${st.key === "green" && opts.todayWord ? " heute" : ""}`;
    const hrw = entry.hr_window;
    const blocks = entry.blocks_w || entry.blocks;
    const planned = opts.plannedHours;
    // Where the catalogue marks a section elastic, the backend fitted the
    // sections to the planned duration and one number is enough. Where it does
    // not, BOTH stand there - the template's minutes and the planned hours -
    // because hiding either would be the half-truth the load bug was made of.
    const dur = !planned ? `${entry.minutes} min`
      : entry.stretched ? `${fmt(planned, 1)} h`
      : `geplant ${fmt(planned, 1)} h · Vorlage ${entry.template_minutes || entry.minutes} min`;
    const loadTxt = `Last ${fmt(entry.load)}${opts.budget != null ? ` · Budget ${fmt(opts.budget)}` : ""}`;
    const openKey = opts.openKey || entry.key;

    return `<div class="wocard ${opts.recommended ? "first" : ""}">
      ${opts.recommended ? `<div class="recflag">${ico("ok", C.green, 14)}
        das ist die Empfehlung von oben</div>` : ""}
      <div class="wohead">
        <div>
          <div class="wofam">${esc(entry.family_label || "")}</div>
          <div class="wotitle">${esc(entry.title)}</div>
          <div class="wometa">${esc(entry.purpose || "")} · ${dur} · ${loadTxt}${
            hrw ? ` · ${hrw[0]}–${hrw[1]} bpm` : ""}</div>
          ${entry.hr_note ? `<div class="wometa hint">${esc(entry.hr_note)}</div>` : ""}
        </div>
        ${st.key ? badge(tone, word) : ""}
      </div>
      ${this._woBar(entry, opts.ftp)}
      <div class="wosteps">${(blocks || []).map(([min, val, label]) => {
        // Woher DIESE Zahl kommt, steht an DIESEM Abschnitt. Eine Vorgabe für
        // die vierte Stunde ist Studienform mit dem Namen des Athleten darauf -
        // das muss in der Einheit stehen, nicht nur in der Kachel.
        const cb = (entry.curve_blocks || []).find((c) => c.label === label);
        const mark = cb
          ? (cb.source === "measured"
              ? `<i class="wsrc" title="gemessen: ${fmt(cb.n)} ${cb.n === 1 ? "Fahrt" : "Fahrten"} in Stunde ${fmt(cb.hour)}">gemessen</i>`
              : `<i class="wsrc lit" title="jenseits des gemessenen Bereichs - Studienform">Studienform</i>`)
          : "";
        // Bei der Rampe nennt die Beschriftung START UND ENDE. Ein einzelner
        // Wert waere dort ein Mittelwert, und ein Mittelwert ist keine Rampe.
        const rsg = entry.ramp_segment;
        const zahl = rsg && rsg.label === label
          ? `${rsg.start_w}\u2013${rsg.end_w} W`
          : (entry.blocks_w ? val + " W" : val + " % FTP");
        return `<span><b>${min}′</b> ${esc(label)} <em>${zahl}</em>${mark}</span>`;
      }).join("")}</div>
      ${entry.watt_source === "blocks"
        ? `<p class="fitwhy">${ico("info", C.blue, 14)} <b>Watt und Puls kommen aus deiner
            Blockmessung</b> — ${fmt((entry.block_source || {}).watts)} W bei alpha
            ${fmt((entry.block_source || {}).alpha, 3)}, gemessen am
            ${dMed((entry.block_source || {}).date)} über
            ${fmt((entry.block_source || {}).n_blocks)} Blöcke; das Pulsfenster aus
            ${fmt((entry.hr_source || {}).n)} Einheiten
            (${dMed((entry.block_source || {}).from)}–${dMed((entry.block_source || {}).to)}).
            <b>Beide aus derselben Quelle</b>, damit sie gemeinsam wandern.
            ${ico("warn", C.amber, 13)} <b>Gilt für diese Einheit auf der Rolle</b>, nicht
            für dieselbe Familie draußen — derselbe alpha-Wert steht dort für eine andere
            Leistung. Ein- und Ausrollen bleiben Prozent der FTP.</p>`
        : entry.watt_source === "curve"
        ? `<p class="fitwhy">${ico("info", C.blue, 14)} <b>Die Watt kommen aus deiner eigenen
            Messung</b>, nicht mehr aus der FTP — gestaffelt nach Fahrtdauer, deshalb trägt
            dieselbe Einheit andere Zahlen als früher. Gefahren wird
            <b>${fmt((entry.curve_share || 0) * 100, 0)} %</b> der gemessenen Schwelle
            (${entry.curve_blocks && entry.curve_blocks[0]
              ? fmt(entry.curve_blocks[0].threshold) + " W" : "–"} in diesem Abschnitt) —
            eine Grundlageneinheit gehört unter die Schwelle, nicht auf sie. Abschnitte ohne
            Kennzeichnung sind Ein- und Ausrollen und bleiben Prozent der FTP.</p>`
        : entry.watt_source === "ramp_hrvt2" || entry.watt_source === "ramp_hrvt1"
        ? `<p class="fitwhy">${ico("info", C.blue, 14)} <b>Watt und Puls kommen aus deinem
            Stufentest</b> — ${fmt((entry.ramp_source || {}).watts)} W bei alpha
            ${fmt((entry.ramp_source || {}).alpha, 2)} und
            ${fmt((entry.ramp_source || {}).hr)} bpm, gemessen am
            ${dMed((entry.ramp_source || {}).date)}.
            ${(entry.ramp_source || {}).share === 1
              ? `Die Leistung an der zweiten Schwelle ist dieselbe Größe wie die Leistung im
                 ersten eingeschwungenen Block — sie wird deshalb direkt übernommen.`
              : `Gefahren wird <b>${fmt(((entry.ramp_source || {}).share || 0) * 100, 0)} %</b>
                 davon: an der ersten Schwelle ist die Zahl eine SCHWELLE, und eine
                 Grundlageneinheit gehört darunter — dieselbe Regel wie bei der
                 Ermüdungskurve.`}
            <b>Beide Seiten aus demselben Messpunkt</b>, damit sie gemeinsam wandern.
            ${ico("warn", C.amber, 13)} Der Puls ist ein <b>Punkt</b> und kein Fenster: eine
            Breite dazuzuerfinden wäre eine Setzung, die niemand belegen kann. Ein- und
            Ausrollen bleiben Prozent der FTP.</p>`
        : entry.watt_source === "ftp" && (entry.family === "tempo" || entry.family === "threshold")
        ? `<p class="fitwhy">${ico("warn", C.amber, 14)} <b>Rückfall auf die FTP — nicht
            gemessen.</b> Für Tempo und Schwelle gibt es keine eigene Messung außer dem
            Stufentest; solange keiner vorliegt, bleibt die FTP die Grundlage.</p>`
        : entry.watt_source === "ftp" && (entry.family === "endurance" || entry.family === "long")
          ? `<p class="fitwhy">${ico("warn", C.amber, 14)} <b>Rückfall auf die FTP — nicht gemessen.</b> Für diese
              Einheit liegt keine tragfähige eigene Messung vor.</p>`
          : entry.watt_source === "ftp" && (entry.family === "vo2max" || entry.family === "sweetspot")
            ? `<p class="fitwhy">${ico("warn", C.amber, 14)} <b>Rückfall auf die FTP — nicht gemessen:</b> noch zu
                wenige gemessene Einheiten dieser Familie — bis dahin bleibt die alte Vorgabe
                stehen, statt halb umgestellt zu werden.</p>`
            : ""}
      ${entry.effect ? `<p class="effect"><b>Was das bringt:</b> ${esc(entry.effect)}</p>` : ""}
      ${entry.fit_reason && !(opts.saidAbove || new Set()).has(entry.fit_reason)
        ? `<p class="fitwhy">${ico(st.key === "red" ? "warn" : "info",
            st.key === "red" ? C.red : C.amber, 14)} ${esc(entry.fit_reason)}</p>` : ""}

      <div class="worow">
        ${opts.planDates ? `<button class="planbtn" data-act="plan" data-id="${esc(entry.key)}"
          data-when="${opts.planDates[0]}">${ico("cal", null, 15)} heute in den Kalender</button>
        <button class="planbtn ghost" data-act="plan" data-id="${esc(entry.key)}"
          data-when="${opts.planDates[1]}">morgen</button>` : ""}
        <button class="chipbtn" data-act="${opts.toggleAct}" data-id="${esc(openKey)}">
          ${opts.open ? "weniger" : "Aufbau, Beleg und Rechenweg"}</button>
      </div>
      ${opts.open ? `<div class="wodetail">
        <div class="kv2"><small>Schritte, wie sie in Intervals landen</small>
          <pre>${esc(entry.text_w || entry.text || "")}</pre>
          ${entry.text_w ? "" : `<p class="src">Ohne hinterlegte FTP bleiben Prozente stehen —
            erfundene Wattzahlen wären schlimmer als ehrliche Prozente.</p>`}</div>
        ${entry.dfa ? `<div class="kv2"><small>Erwartetes DFA alpha-1</small><p>${esc(entry.dfa)}</p></div>` : ""}
        ${entry.detail ? `<div class="kv2"><small>Wozu sie in dieser Woche steht</small>
          <p>${esc(entry.detail)}</p>${entry.why ? `<p class="src">${esc(entry.why)}</p>` : ""}</div>` : ""}
        ${entry.fuel ? `<div class="kv2"><small>Verpflegung</small><p>${esc(entry.fuel)}</p></div>` : ""}
        ${(entry.derivation || []).length ? `<div class="kv2"><small>Rechenweg</small>
          <ul class="src dtsteps">${entry.derivation.map((line) => `<li>${esc(line)}</li>`).join("")}</ul></div>` : ""}
        ${(entry.standard || []).length ? `<div class="kv2"><small>Zu standardisieren</small>
          <ul class="src dtsteps">${entry.standard.map((line) => `<li>${esc(line)}</li>`).join("")}</ul></div>` : ""}
        ${entry.catalogue_load != null && entry.load !== entry.catalogue_load
          ? `<div class="kv2"><small>Rechenweg der Last</small>
            <p class="src">Die Vorlage ${esc(entry.key)} trägt Last ${fmt(entry.catalogue_load)} bei
            ${entry.catalogue_minutes} min. Geplant sind ${fmt(planned, 1)} h — bei gleicher
            Intensität wächst die Last linear mit der Dauer, also ${fmt(entry.load)}.
            Nach der Vorlage allein wären es ${fmt(entry.catalogue_load)}, und genau diese
            Verwechslung hat die lange Fahrt bis 0.42.0 zu freundlich bewertet.</p></div>` : ""}
        ${(entry.stretch_note || {}).rule ? `<div class="kv2"><small>${entry.stretched
          ? "Wie der Aufbau auf die Dauer kam" : "Warum der Aufbau so bleibt"}</small>
          <p>${esc(entry.stretch_note.rule)}${entry.stretched && (entry.elastic_sections || []).length
            ? ` Gedehnt wurde: ${esc(entry.elastic_sections.join(", "))} — aus ${
                entry.template_minutes} min Vorlage wurden ${entry.minutes} min.` : ""}</p>
          <p class="src"><b>Beleg:</b> ${esc(entry.stretch_note.evidence || "")}</p>
          <p class="src"><b>Grenze:</b> ${esc(entry.stretch_note.limit || "")}</p></div>` : ""}
        ${entry.evidence ? `<div class="kv2"><small>Beleg</small><p class="src">${esc(entry.evidence)}</p></div>` : ""}
        ${entry.limit ? `<div class="kv2"><small>Grenze</small><p class="src">${esc(entry.limit)}</p></div>` : ""}
        ${st.evidence ? `<div class="kv2"><small>Zur Stufe „${esc(st.label)}"</small>
          <p class="src">${esc(st.evidence)}</p></div>` : ""}
      </div>` : ""}
    </div>`;
  }

  rWorkouts(w, forTomorrow) {
    if (!w) return this._dataGap("workouts", "Die Einheiten");
    const list = w.workouts || [];
    if (!list.length) return "";
    const today = new Date();
    const iso = (d) => new Date(today.getTime() + d * 86400000).toISOString().slice(0, 10);

    // One logic, not two. The list IS the recommendation: the first card that
    // fits today carries the mark, instead of a second block above computing
    // its own answer that could quietly disagree with this one.
    let pick = list.findIndex((e) => (e.stage || {}).key === "green");
    if (pick < 0) pick = list.findIndex((e) => (e.stage || {}).key === "stimulus");

    const shared = this._sharedReasons(list);
    const cards = list.map((entry, index) => this._sessionCard(entry, {
      open: this._woOpen === entry.key, budget: w.budget, ftp: w.ftp,
      recommended: index === pick, todayWord: !forTomorrow, saidAbove: shared,
      planDates: [iso(0), iso(1)], toggleAct: "wodetail",
    })).join("");

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
    // said once, above the list, instead of on every card
    const reasons = [...shared].map((r) => this._reasonRow(r, "amber")).join("");

    return `${conflict}${leadCard}<h3 class="secname">Alle Einheiten für ${forTomorrow ? "morgen" : "heute"}
      <span class="hint">— eine je Art, jede ${forTomorrow
        ? "nach dem heutigen Zustand bewertet" : "für heute bewertet"}. Watt aus deiner
      FTP${w.ftp ? ` (${fmt(w.ftp)} W)` : ""}, Puls aus deiner gemessenen aeroben
      Schwelle${w.aerobic_hr ? ` (${w.aerobic_hr} bpm)` : ""}. Was du machst, entscheidest du —
      hier steht, was es heute kostet.</span></h3>
      ${reasons}
      <div class="wogrid">${cards}</div>
      <p class="note">Ein Klick legt die Einheit als geplantes Workout in deinen
      Intervals-Kalender — mit allen Schritten, direkt auf die Uhr übertragbar. Das ist der
      einzige Schreibzugriff dieser Integration, er passiert nur auf diesen Knopf.</p>`;
  }

  /* Termin 2 des Durability-Protokolls (docs/ausbau.md K1).

     Der ermüdete Termin steht NICHT im Katalog, wenn kein frischer Test
     gemessen ist: seine Zielleistung ist 80 % der frischen
     20-Minuten-Leistung, und ohne die gibt es keine Form, die man zeigen
     könnte. Was stattdessen dasteht, ist der GRUND plus der Knopf, der
     Termin 1 in den Kalender legt — die Bauart von "Was das ausbaut" (G5),
     nicht eine ausgegraute Karte.

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
    if (!g) return this._dataGap("goal", "Dein Ziel");
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
  rPlanWeeks(g, prog) {
    // no payload is a DEFECT and says so; a goal that is simply not set yet is
    // not - rGoal already shows the form for that, and a second notice next to
    // it would be noise
    if (!g) return this._dataGap("goal", "Die nächsten Wochen");
    const plan = g.plan || {};
    /* 0.50.0 Punkt 2: die Progressionszeile aus dem Kopf der Durability-Kachel.
       Hier steht sie richtig - dies ist die Ansicht, in der ueber DAUERN
       entschieden wird, und die Zeile sagt, wie lang die naechste Fahrt sein
       darf, nicht wie viel Watt. Eine Zeile, keine Kachel. Jede Zahl kommt aus
       der Payload, auch der Prozentsatz: er wird aus dem Faktor gerechnet. */
    const progLine = !prog || prog.next_minutes == null ? "" : `<p class="hint">${
      ico("clock", C.tx2, 13)} <b>Die lange Fahrt darf bis ${hmn(prog.next_minutes)} gehen.</b>
      ${fmt(prog.recent.minutes, 0)} min × ${fmt(prog.factor, 2)}, auf ${fmt(prog.round_minutes, 0)}
      Minuten gerundet. Bezug ist die längste gleichmäßige Fahrt ${prog.recent.days == null
        ? "deines ganzen Bestands" : `der letzten ${fmt(prog.recent.days, 0)} Tage`} (${
        dMed(prog.recent.date)})${prog.recent.widened
        ? `; in den letzten ${fmt(prog.window_days, 0)} Tagen stand nichts Qualifiziertes, deshalb
           der weitere Zeitraum` : ""}.${prog.below_demonstrated
        ? ` Der Schritt liegt unter dem, was du schon gefahren bist — der Bezug ist bewusst dieser
           Zeitraum und nicht deine Bestleistung: riskant ist der Sprung gegen das, was gerade in
           den Beinen steckt.` : ""} <b>Die ${fmt((prog.factor - 1) * 100, 0)} %</b> sind der
      gemessene Risikoknick aus einer Kohortenstudie an <b>Läufern</b>, keine
      Trainingsvorschrift — die Zeile sagt, was ohne erhöhtes Risiko geht, nicht was nötig ist.</p>`;
    // Ein Plan, der noch nicht steht, darf die Zeile nicht MITNEHMEN: sie
    // haengt am Bestand, nicht am Ziel. Sonst verschwaende sie still - genau
    // die Luecke aus 0.42.1, nur andersherum.
    if (!plan.ready || !(plan.weeks || []).length) {
      return progLine ? `<h3 class="secname">Die nächsten Wochen</h3>
        <div class="card pad">${progLine}</div>` : "";
    }

    const note = plan.budget_note;
    const choice = plan.choice || {};
    const weeks = plan.weeks.map((w) => {
      const open = this._planOpen === String(w.index);
      const rated = w.rated === true;
      return `<div class="pweek ${w.kind}${w.big_day ? " bigday" : ""}${rated ? " now" : ""}"
          data-act="planweeks" data-id="${w.index}">
        <div class="pwhead">
          <span class="pwno">W${w.index}</span>
          <span class="pwphase">${esc(w.phase_label)}${w.kind === "recovery" ? " · Entlastung" : ""}${
            w.big_day ? " · großer Tag" : ""}${rated ? " · diese Woche" : ""}</span>
          <span class="pwh tn">${fmt(w.hours, 1)} h</span>
          ${w.long_day_hours ? `<span class="pwlong tn">${w.big_day ? "großer Tag" : "langer Tag"} ${
            fmt(w.long_day_hours, 1)} h${w.big_day ? " <em>(die Ausnahme, die wächst)</em>" : ""}</span>` : ""}
        </div>
        ${rated ? this._weekDone(w) : ""}
        ${open ? `<div class="pwbody">
          <p class="hint">${esc(w.phase_note)}</p>
          ${rated ? this._weekReasons(w) : `<p class="hint noverdict">${ico("clock", C.tx3, 14)} ${
            esc(plan.no_verdict_note || "")}</p>`}
          <div class="wogrid">${(w.sessions || []).map((s) => this._sessionCard(
            // A week without a grade shows the SAME card, only without a
            // verdict - not a different, poorer shape. The role stands in for
            // the family label the catalogue would give it.
            rated ? s : { ...s, stage: null, minutes: null,
                          family_label: ROLE_LABEL[s.role] || "Einheit" },
            { open: this._psOpen === `${w.index}:${s.title}`,
              openKey: `${w.index}:${s.title}`, toggleAct: "psdetail",
              budget: rated ? s.budget : null, ftp: (plan.assessment || {}).ftp,
              saidAbove: rated ? this._sharedReasons(w.sessions) : null,
              plannedHours: s.hours })).join("")}</div>
        </div>` : `<div class="pwsess">${(w.sessions || []).map((s) =>
          `<span class="ptag ${s.role}">${esc(s.title)}${
            rated && (s.stage || {}).key ? ` ${this._stageDot(s.stage)}` : ""}</span>`).join("")}</div>`}
      </div>`;
    }).join("");

    return `<h3 class="secname">Die nächsten Wochen
        <span class="hint">— ${esc(plan.pattern)} an Kalenderwochen verankert; der große Tag
        wächst, die Wochen dazwischen bleiben gewöhnlich</span></h3>
      ${progLine}
      ${note ? `<div class="warnrow">${ico("info", C.amber, 16)} <span>${esc(note.text)}</span></div>` : ""}
      <div class="pweeks">${weeks}</div>
      ${this._stageLegend(plan)}
      <p class="src">${esc(plan.caveat || "")}</p>
      ${choice.rule ? `<div class="kv2 choicebox"><small>Wer hier entscheidet</small>
        <p>${esc(choice.rule)}</p>
        <p class="src">${esc(choice.evidence || "")}</p>
        <p class="src"><b>Grenze:</b> ${esc(choice.limit || "")}</p></div>` : ""}`;
  }

  /* The grade, straight from the payload. No view derives one: the only thing
     that happens here is looking up the register entry for the key the backend
     sent (docs/ausbau.md I3, I5). */
  _stageBadge(s) {
    const st = s.stage || {};
    if (!st.key) return "";
    const word = st.key === "stimulus" && s.budget != null
      ? `${st.word} (über dem Budget von ${fmt(s.budget)})`
      : st.word;
    return badge(STAGE_TONE[st.key] || "unknown", word);
  }

  /* The state warnings of a week, said ONCE above its sessions.

     They belong to the state, not to the session: printed per card they were
     the same sentence three times in a row, and the third one is not read
     (docs/ausbau.md I10). A reason that belongs to a single session stays on
     that session's card - `_sessionCard` skips only what was said here. */
  _weekReasons(w) {
    const shared = [...this._sharedReasons(w.sessions)];
    if (!shared.length) return "";
    const worst = (w.sessions || []).some((s) => (s.stage || {}).key === "red") ? "red" : "amber";
    return shared.map((r) => this._reasonRow(r, worst)).join("");
  }

  _stageDot(st) {
    const m = ST[STAGE_TONE[st.key] || "unknown"];
    return `<span class="pstage" style="color:${m.c}">${ico(m.ic, m.c, 12)}${esc(m.word)}</span>`;
  }

  /* Four grades, four words, four shapes, four tones - stated once, from the
     register the backend sent, so the legend cannot drift from the badges. */
  _stageLegend(plan) {
    const stages = plan.stages || {};
    const order = ["green", "yellow", "stimulus", "red"];
    const rows = order.filter((k) => stages[k]).map((k) => {
      const m = ST[STAGE_TONE[k]];
      return `<div class="stagerow">${ico(m.ic, m.c, 15)}
        <b style="color:${m.c}">${esc(stages[k].label)}</b>
        <span>${esc(stages[k].detail)}</span></div>`;
    }).join("");
    if (!rows) return "";
    const rec = ((plan.assessment || {}).recovery) || {};
    return `<div class="stagelegend">
      <small>Die vier Stufen — nur für die laufende Woche</small>
      ${rows}
      ${rec.note ? `<p class="src">${esc(rec.note)}</p>` : ""}
      ${(rec.missing || []).length && rec.offered === false
        ? `<p class="src">Heute nicht erfüllt: ${esc(rec.missing.join("; "))}.</p>` : ""}
    </div>`;
  }

  /* Ridden against planned - and nothing paired. The archive holds duration
     and load, no label saying which planned session a ride was meant to be;
     pairing them automatically would be a claim nobody here can back up
     (docs/ausbau.md I2). */
  _weekDone(w) {
    const d = w.done;
    if (!d) return "";
    const sessions = (w.sessions || []).length;
    const hours = (w.sessions || []).reduce((sum, s) => sum + (Number(s.hours) || 0), 0);
    return `<div class="pwdone">
      <div class="pwdrow"><span class="pwdlab">gefahren</span>
        <b>${fmt(d.sessions)} ${d.sessions === 1 ? "Einheit" : "Einheiten"}</b>
        <span class="tn">${fmt(d.hours, 1)} h · Last ${fmt(d.load)}</span></div>
      <div class="pwdrow"><span class="pwdlab">vorgesehen</span>
        <b>${fmt(sessions)} ${sessions === 1 ? "Einheit" : "Einheiten"}</b>
        <span class="tn">${fmt(hours, 1)} h${d.days_left != null
          ? ` · noch ${d.days_left} ${d.days_left === 1 ? "Tag" : "Tage"} in der Woche` : ""}</span></div>
      <p class="src">${esc(d.note || "")}</p>
    </div>`;
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
    if (!sig) return this._dataGap("signals", "Die Signale");
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
  /* Die Stufentest-Karte (docs/ausbau.md N3).

     Sie zeigt DREI Zahlen, nicht zwei: die beiden Schwellen und daneben die
     personalisierte erste. Letztere ist KEIN Ersatz - ihr Nutzen ist
     umstritten, und ihre Rechenvorschrift stammt aus zweiter Hand. Beides
     steht in der Karte und nicht nur in der Spezifikation.

     Und sie zeigt die Frage, die der Test beantworten soll: die beiden
     eigenen Messungen widersprechen sich um rund 40 Watt, und bisher gab es
     nichts, was zwischen ihnen entscheidet. */
  rRampTest(rt) {
    if (!rt) return "";
    const letzter = rt.latest || null;
    const r = letzter && letzter.result;
    const anz = (rt.tests || []).length;

    const zelle = (node, titel, unten) => `<div class="stat">
      <small>${titel}</small>
      <b class="tn" style="color:${node ? ROLE.series : C.tx3}">${node && node.watts != null
        ? fmt(node.watts, 0) : "–"} <span class="unit">W</span></b>
      <span class="mut">${node
        ? `alpha ${fmt(node.alpha, 2)}${node.hr != null ? " · " + fmt(node.hr, 0) + " bpm" : ""}`
        : esc(unten)}</span></div>`;

    // Ohne Test steht hier kein leerer Platz, sondern was er liefern wuerde.
    // Eine Kachel, die nichts sagt, ist die Luecke aus 0.42.1 in huebsch.
    const leer = `<div class="card pad">
      <p class="effect">Du hast noch keinen Stufentest gefahren — deshalb stehen hier keine
        Zahlen. Das ist kein Fehler, sondern der Ausgangszustand.</p>
      <p>Der Test misst in <b>einer Fahrt</b> beide Schwellen: die erste, unter der eine
        Grundlageneinheit bleiben soll, und die zweite, an der die harten Blöcke liegen.
        Beide unter <b>denselben Bedingungen</b>, am selben Tag, mit demselben Gurt — das
        ist der Unterschied zu Zahlen, die aus verschiedenen Fahrten über Monate
        zusammenkommen.</p>
      <p>Solange er fehlt, ändert sich <b>nichts</b> an deinen Vorgaben: jede Einheit nennt
        weiterhin die Quelle, aus der ihre Watt kommen, und fällt auf die FTP zurück, wo es
        keine gibt.</p>
      <p class="src">Zu finden im Katalog unter <b>Stufentest</b>. Er wird nur im grünen
        Zustand vorgeschlagen — ein müder Test misst die Müdigkeit.</p></div>`;

    const zahlen = !r ? "" : `
      <div class="statgrid">
        ${zelle(r.hrvt1, "Erste Schwelle (HRVT1)", "")}
        ${zelle(r.hrvt2, "Zweite Schwelle (HRVT2)",
                r.reached_anaerobic ? "" : "nie stabil unter 0,5 — nicht erreicht")}
        ${zelle(r.hrvt1_pers, "Erste, personalisiert", "")}
      </div>
      <p class="src"><b>Die dritte Zahl steht daneben, nicht anstelle der ersten.</b>
        Sie liegt mittig zwischen dem Hochpunkt am Beginn deines Abfalls
        (alpha ${fmt(r.max_alpha_start, 2)}) und 0,5, hier also alpha
        ${fmt(r.pers_alpha, 2)}. <b>Ihr Nutzen ist umstritten:</b> eine Arbeit berichtet
        bessere Übereinstimmung als der feste Wert, aber nur Korrelationen zwischen 0,67
        und 0,70; eine zweite findet auch für sie nur triviale bis mittlere Zusammenhänge.
        Und die Rechenvorschrift ist eine <b>Operationalisierung aus zweiter Hand</b>:
        die Urarbeit spricht vom „Maximum während der frühen Rampe“, die Umsetzung vom
        „höchsten Wert am Beginn des linearen Abfalls“ — ein Maximum in einem Zeitfenster
        ist etwas anderes als eines an einem Kurvenpunkt. Gebaut ist die zweite Fassung,
        weil nur sie sich rechnen lässt.</p>
      ${r.reached_anaerobic ? "" : `<p class="hint">${ico("info", C.amber, 13)}
        <b>Die zweite Schwelle fehlt.</b> Dein alpha war nie stabil unter 0,5 — der Abbruch
        kam vorher. Das ist eine Auskunft und kein Fehlversuch; die erste Schwelle steht
        trotzdem. Über das Gemessene hinaus wird nicht hochgerechnet.</p>`}`;

    // DIE QUELLEN STEHEN AUSSERHALB DES TERNAERS. Bis 0.51.0 lagen sie im
    // `r ?`-Zweig - also erst sichtbar, NACHDEM der Test gefahren war. Genau
    // dann nicht, wenn jemand entscheidet, ob er eine Stunde investiert. Fuenf
    // Arbeiten, eigens herausgesucht, und niemand kam an sie heran.
    const quellen = (rt.sources || []).length ? `<details class="card pad">
      <summary>Worauf das beruht — ${(rt.sources || []).length} Arbeiten</summary>
      <p class="src">Die erste Schwelle (alpha 0,75) stammt vom <b>Laufband</b>, die
        Übertragung auf das Rad ist nicht dieselbe Messung. Die zweite (alpha 0,5) hält
        durchgängig besser. Das steht hier, BEVOR du den Test fährst — nicht erst
        danach.</p>
      <p class="src">${(rt.sources || []).map((q) => `<br>· ${esc(q)}`).join("")}</p>
    </details>` : "";

    return `<h3 class="secname">Stufentest
      <span class="hint">— beide Schwellen aus einer Fahrt${anz
        ? `, ${anz} ${anz === 1 ? "Test" : "Tests"} markiert` : ""}</span></h3>
      ${r ? `<div class="card pad">
        <p class="effect">Gemessen am ${dMed(letzter.date)}.</p>
        ${zahlen}
        <details><summary>Der Rechenweg</summary>
          <p class="src">Die Schwelle wird <b>nicht abgelesen, sondern gefittet</b>: durch
            den nahezu linearen Abfall von DFA a1 läuft eine Ausgleichsgerade, und die
            Schwelle ist deren Schnittpunkt mit 0,75 beziehungsweise 0,5. Ein einzelner
            Ausreißer entscheidet damit nichts — dafür entscheidet die Wahl des Abschnitts
            alles.</p>
          <p class="src"><b>Diese Wahl ist unsere Setzung.</b> In beiden Arbeiten wird der
            Abschnitt von Hand am Diagramm bestimmt. Hier läuft er vom letzten Hochpunkt vor
            dem Abfall bis zu der Stelle, ab der die Kurve flach unter 0,5 bleibt — beides
            aus der geglätteten Kurve, gerechnet wird auf den ungeglätteten Werten.
            ${r.segment ? `Für diesen Test: ${fmt(r.segment.points, 0)} Punkte,
            Bestimmtheitsmaß ${fmt(r.segment.r2, 2)}.` : ""}</p>
          <p class="src"><b>Ein- und Ausrollen gehören zur Messung.</b> Die Dauern sind die
            einzigen festen Zahlen des Tests; alle Leistungen kommen aus deinen eigenen
            Werten. Für das Ausrollen gibt es keine Protokollvorgabe — gesetzt ist es, weil
            sich in den ersten Minuten nach der Belastung messbar etwas erholt.</p>
        </details></div>` : leer}
      ${quellen}`;
  }

  /* Die 40-Watt-Frage (docs/ausbau.md N3). Zwei eigene Messungen widersprechen
     sich, und bisher gab es nichts, was zwischen ihnen entscheidet. Das steht
     sichtbar in der Karte und nicht nur in der Spezifikation - eine offene
     Frage, die nur im Dokument steht, ist für den, der fährt, keine. */
  rRampGap(blocks, curve, rt) {
    const fam = ((blocks || {}).families || {}).sweetspot
      || ((blocks || {}).families || {}).vo2max;
    const l = fam && fam.latest;
    const p = curve && (curve.measured || []).find((q) => q.hour === 1);
    if (!l || !p) return "";
    const diff = Math.round(l.first_watts - p.watts);
    if (!diff) return "";
    const r = ((rt || {}).latest || {}).result;
    return `<div class="card pad">
      <h4 class="subsec">Die offene Frage: ${fmt(Math.abs(diff), 0)} Watt</h4>
      <p>Deine beiden eigenen Messungen sagen etwas Verschiedenes. In deinen Blöcken liegt
        alpha bei <b>${fmt(l.first_alpha, 2)}</b> und die Leistung bei
        <b>${fmt(l.first_watts, 0)} W</b>. Deine Ermüdungskurve setzt alpha 0,75 bei
        <b>${fmt(p.watts, 0)} W</b> an. Das sind
        <b>${fmt(Math.abs(diff), 0)} Watt</b> Unterschied bei fast demselben alpha-Wert.</p>
      <p>Beide Zahlen sind gemessen, keine ist falsch — sie kommen nur aus
        <b>verschiedenen Situationen</b>: die eine aus kurzen Blöcken in harten Einheiten,
        die andere aus langen gleichmäßigen Abschnitten über viele Fahrten und Monate.
        Welche von beiden näher an deiner tatsächlichen ersten Schwelle liegt, konnte bisher
        nichts entscheiden.</p>
      ${r && r.hrvt1
        ? `<p class="effect">Der Stufentest sagt dazu: <b>${fmt(r.hrvt1.watts, 0)} W</b> an
            der ersten Schwelle, an einem Tag und unter gleichen Bedingungen gemessen.
            <b>Das ist ein Hinweis und kein Urteil</b> — eine dritte Messung, die näher an
            der einen oder der anderen liegt, entscheidet die Frage nicht, sie verschiebt
            sie. Belastbar wird es erst, wenn sich derselbe Test über die Monate
            wiederholt.</p>`
        : `<p class="hint">${ico("info", C.blue, 13)} <b>Genau dafür ist der Stufentest da.</b>
            Er misst beide Schwellen an einem Tag, unter gleichen Bedingungen, und liefert
            damit eine dritte Zahl neben diesen beiden. Sie entscheidet die Frage nicht
            allein — aber sie ist die erste, die unter denselben Bedingungen entsteht wie
            die Frage selbst.</p>`}</div>`;
  }

  rTrainer(c, rd) {
    if (!c) return this._dataGap("coach", "Der Trainer");
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

      ${dur ? this.rDurability(dur) : ""}
      ${this.rRampTest(this._rtests)}
      ${this.rRampGap(this._blocks, this._fatigue, this._rtests)}

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
    if (!t) return this._dataGap("today", "Der Tag");
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
                xl: (i) => `${dMed(dts[i])}${(track[i] || {}).load ? " · Training" : ""}${
                  (track[i] || {}).context
                    ? " · Etikett: " + ((this._ctxOf(dts[i]) || {}).label || track[i].context.tag)
                    : ""}`,
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
            // Ebene 1 sichtbar gemacht: Tage mit Gewicht 0 zählen nicht in
            // die Basislinie, bleiben aber gezeichnet - als HOHLE Punkte.
            // Form statt Farbe (WCAG 1.4.1, dieselbe Regel wie beim Auswahlring).
            const hollow = track.map((r, i) =>
              (r && r.context && r.context.weight === 0 && series[i] != null)
                ? { i, v: series[i], f: false, r: 4 } : null).filter(Boolean);
            const plot = chart({ h: 200, n: Math.max(2, series.length), y0: lo, y1: hi,
              yf: (v) => fmt(v, dec), bands, hl: lines,
              grp: dts.length ? grp : null,
              xt: ax.labels, xtick: ax.ticks,
              s: [{ t: "line", v: series, c: scol, w: 2 },
                  ...(hollow.length ? [{ t: "dots", c: scol, p: hollow }] : [])] });
            if (!dts.length) return plot;
            return `<div data-grp="${grp}">${readout(grp)}${plot}${this._eventTrack(track, grp)}${
              hollow.length ? `<p class="src">Hohle Punkte sind etikettierte Tage mit
                Gewicht 0 — sie zählen nicht in die Basislinie, bleiben aber
                gezeichnet und lösen die Warnung weiter aus.</p>` : ""}</div>`;
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
      const dctx = this._ctxOf(d.date);
      return `<div class="tday ${isToday ? "now" : ""}" data-act="daylabel" data-id="${esc(d.date)}"
          title="${esc(dMed(d.date))}: Last ${d.load}${
            names.length ? " · " + esc(names.join(", ")) : " · kein Training"}${
            state ? " · " + esc(state) : ""}${
            dctx ? " · Etikett: " + esc(dctx.label) : ""} · klicken zum Beschriften">
        <span class="tbarbox"><i style="height:${height.toFixed(0)}%;background:${dcol}"></i></span>
        <span class="tdate">${esc(dShort(d.date))}${
          dctx ? `<span class="ctxmark" style="color:${CTX_COLOR[dctx.tag] || C.slate}">${ico("tag", CTX_COLOR[dctx.tag] || C.slate, 11)}</span>` : ""}</span>
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
      ${t.context_note ? `<div class="ctxnote">${ico("info", C.tx2, 15)}
        <span>${esc(t.context_note)}</span></div>` : ""}

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

  /* Beschriftungsdialog: ein FESTER, zentrierter Kasten mit Backdrop.
     Bewusst kein am Klickpunkt schwebender Kasten - drei Releases (0.9.1
     bis 0.9.3) haben an schwebender Positionierung gedreht, bis der feste
     Platz die Fehlerklasse beendet hat. Chips, Texte und Quellen kommen
     komplett aus dem day_context-Leseweg: eine Quelle, kein Drift. */
  _ctxPopover() {
    const date = this._ctxDlg;
    const dc = this._dayctx || {};
    const tags = dc.tags || {};
    const cur = (dc.days || {})[date] || null;
    const srcs = dc.sources || {};
    const wfmt = (w) => String(w == null ? 1 : w).replace(".", ",");
    const chips = Object.entries(tags).map(([slug, meta]) => {
      const on = !!(cur && cur.tag === slug);
      const col = CTX_COLOR[slug] || C.slate;
      // Auswahl trägt Form UND Wort UND Farbe: Ring, Haken, "gewählt"
      return `<button class="ctxchip ${on ? "on" : ""}" style="--cc:${col}"
          data-act="ctxset" data-id="${esc(slug)}" title="${esc(meta.read || "")}">
        ${ico("tag", col, 15)}<span class="cn">${esc(meta.label || slug)}</span>
        <span class="cw tn">Gewicht ${wfmt(meta.weight)}</span>
        ${on ? `<span class="csel">${ico("ok", col, 14)} gewählt</span>` : ""}
      </button>`;
    }).join("");
    const belegt = (srcs.belegt || []).map((b) =>
      `<li>${esc(b.text)} <em class="qq">${esc(b.source)}</em></li>`).join("");
    const setz = (srcs.setzung || []).map((s) => `<li>${esc(s)}</li>`).join("");
    return `<div class="ctxback" data-act="ctxclose"></div>
      <div class="ctxdlg" role="dialog" aria-modal="true" aria-label="Tag beschriften">
        <div class="ctxhead"><b>Tag beschriften — ${esc(dMed(date))}</b>
          <button class="ctxx" data-act="ctxclose" title="schließen">${ico("stop", C.tx2, 18)}</button></div>
        ${cur ? `<p class="ctxcur">Aktuell: <b>${esc((tags[cur.tag] || {}).label || cur.tag)}</b>
          · Gewicht ${wfmt(cur.weight)}</p>` : ""}
        <div class="ctxchips">${chips}</div>
        ${cur ? `<button class="ctxremove" data-act="ctxdel">
          <span class="cn"><b>Etikett entfernen</b> — Rücknahme, keine Aussage: der Tag
          rechnet danach, als wäre er nie beschriftet worden.</span></button>` : ""}
        ${this._ctxErr ? `<div class="ctxerr">${ico("warn", C.amber, 15)}<span>${esc(this._ctxErr)}</span></div>` : ""}
        ${srcs.read ? `<p class="ctxwhy">${esc(srcs.read)}</p>` : ""}
        <details class="more"><summary>Belegt oder Setzung — woher die Regeln kommen</summary>
          <div class="src">
            <p><b>Belegt:</b></p><ul>${belegt}</ul>
            <p><b>Setzung:</b></p><ul>${setz}</ul>
            <p>${esc(srcs.fix || "")}</p>
          </div></details>
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
    if (!days) return this._dataGap("days", "Der Kalender");
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
    const dctx = this._ctxOf(d.date);
    const wln = [];
    if (d.sleep_hours != null) wln.push(`<span title="Schlaf">${ico("moon", C.tx3, 13)}${fmt(d.sleep_hours, 1)}</span>`);
    if (d.hrv != null) wln.push(`<span title="HRV">${ico("heart", C.tx3, 13)}${fmt(d.hrv)}</span>`);
    if (d.resting_hr != null) wln.push(`<span title="Ruhepuls">${ico("pulse", C.tx3, 13)}${fmt(d.resting_hr)}</span>`);
    if (d.steps != null) wln.push(`<span title="Schritte">${ico("steps", C.tx3, 13)}${fmt(Math.round(d.steps / 100) / 10, 1)}k</span>`);
    const chips = (d.activities || []).map((a) => this._chip(a)).join("") +
      (d.planned || []).map((p) => this._planChip(p, d, today)).join("");
    return `<div class="day ${d.today ? "is-today" : ""} ${d.future ? "is-fut" : ""}"${
        d.future ? "" : ` data-act="daylabel" data-id="${esc(d.date)}" title="klicken zum Beschriften"`}>
      <div class="dhead"><span>${dShort(d.date)}${
        dctx ? `<span class="ctxmark" title="Etikett: ${esc(dctx.label)}">${ico("tag", CTX_COLOR[dctx.tag] || C.slate, 12)}</span>` : ""}</span>${
        d.load ? `<span class="dload tn" title="Tageslast">${fmt(d.load)}</span>` : ""}</div>
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
      <span class="cn" title="${esc(a.name || sp.l)}">${esc(a.name || sp.l)}</span>
      <span class="cd tn">${dur(a.moving_time)}</span>
      ${a.load != null ? `<span class="cl tn">${fmt(a.load)}</span>` : ""}
      ${zb}</button>`;
  }

  _planChip(p, d, today) {
    const sp = sportOf(p.group || p.type);
    const missed = !p.done && d.date < today;
    const stateIc = p.done ? ico("ok", C.green, 15) : missed ? ico("stop", C.red, 15) : ico("cal", C.tx3, 15);
    return `<div class="chip plan ${p.done ? "done" : ""} ${missed ? "missed" : ""}" style="--sc:${sp.c}" title="${
      esc(p.name || sp.l)} — ${p.done ? "erledigt" : missed ? "ausgelassen" : "geplant"}">
      ${stateIc}
      <span class="cn" title="${esc(p.name || sp.l)}">${esc(p.name || sp.l)}</span>
      ${p.moving_time ? `<span class="cd tn">${dur(p.moving_time)}</span>` : ""}
      ${p.load != null ? `<span class="cl tn">${fmt(p.load)}</span>` : ""}
    </div>`;
  }

  /* ---------------- Fitness ---------------- */
  rFitness(pmc, rangeDays) {
    if (!pmc) return this._dataGap("pmc", "Die Fitness-Kurve");
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
    if (!list) return this._dataGap("akt", "Die Aktivitäten");
    if (!list.length) return `<div class="card pad">Noch keine Aktivitäten im Archiv.</div>`;
    const miss = !sel && this._aktMiss
      ? `<div class="card pad err">Die Einheit <b>${esc(this._aktMiss)}</b> liegt nicht in den
         zuletzt geladenen ${fmt(list.length)} Einheiten — sie ist älter als der geladene Bereich.
         Die Schwellenmessung dazu steht weiterhin im DFA-Reiter.</div>` : "";
    const detail = sel ? this._aktDetail(sel) : "";
    const decGood = this._decGood();
    const rows = list.slice(0, 120).map((a) => {
      const sp = sportOf(a.type);
      const dfaShares = this._dfaShares(a.dfa);
      const zb = dfaShares
        ? `<i class="zb w"><s style="width:${dfaShares[0]}%;background:${C.green}"></s><s style="width:${dfaShares[1]}%;background:${C.amber}"></s><s style="width:${dfaShares[2]}%;background:${C.red}"></s></i>`
        : `<span class="mut">–</span>`;
      const dec = a.decoupling;
      const decCls = (dec == null || decGood == null) ? "mut" : dec > decGood ? "warncol" : "okcol";
      const thr = a.dfa && a.dfa.hr_at_threshold
        ? `${fmt(a.dfa.hr_at_threshold)} bpm${(a.dfa.threshold || {}).hr_usable ? "" : " ⚠"}` : "–";
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
        <span class="amk">${this._markCell(a.id)}</span>
      </button>`;
    }).join("");
    return `${miss}${detail}
      <div class="card pad0">
        <div class="ahead">
          <span></span><span>Einheit</span><span>Dauer</span><span>Distanz</span><span>Last</span><span>Ø HF</span><span>Entkopplung</span><span>DFA-Verteilung</span><span>Schwelle</span><span>Zuordnung</span>
        </div>
        ${rows}
      </div>`;
  }

  /* Die Markenspalte der Aktivitaetenliste (docs/ausbau.md P5).

     LEER HEISST: NOCH NICHT ANGEFASST - und genau das ist die Aussage, die
     die Spalte liefern soll. Eine markierte Fahrt ohne Familie gibt es nicht,
     weil der Eintrag dann faellt (P3d).

     KEIN DRIFTZEICHEN, und das ist eine Entscheidung, keine Auslassung. Der
     Driftbefund ist nur gegen die LIVE geholten Laps zu haben; die sind nicht
     archiviert, und fuer eine Liste mit dreihundert Fahrten waeren das
     dreihundert Abrufe. Ein GESPEICHERTER Stand ("beim letzten Oeffnen sass
     sie noch") waere nicht bloss ungenau, sondern systematisch falsch herum:
     Drift entsteht, wenn in Intervals neu unterteilt wird - also NACH dem
     letzten Oeffnen. Er zeigte "in Ordnung" fuer genau die Fahrten, die
     gerade gedriftet sind. Eine leere Zelle sagt nichts, ein gruenes Zeichen
     sagt "geprueft und in Ordnung"; das zweite ist der stille Ausstieg (§7,
     erster Fall). Geprueft wird die Drift dort, wo die Laps ohnehin vorliegen:
     im Aktivitaetsdetail und auf dem Messweg.

     WAS DIE SPALTE STATTDESSEN TRAEGT, ist der MESSZUSTAND - der steht im
     Archiv und ist kein Stellvertreter. Blass heisst markiert und noch nicht
     gemessen. */
  _markCell(id) {
    const row = (this._smarks && (this._smarks.marks || [])
      .find((m) => String(m.activity_id) === String(id))) || null;
    if (!row) return "";
    const keys = Object.keys(FAM).filter(
      (key) => ((row.marks || {})[key] || []).length);
    if (!keys.length) return "";
    // JE FAMILIE, nicht je Fahrt. Seit B2b-0 misst der Knopf jede Familie
    // einzeln, und an der 20.08.2026 hängen drei an einer Fahrt - ein Haken
    // für die ganze Fahrt wäre dort in zwei von drei Fällen gelogen. Ein
    // Sammelhaken müsste "alle fertig" heißen und stünde beim Durcharbeiten
    // fast nie.
    const fertig = (key) => {
      const got = ((row.measure || {})[key]) || null;
      if (!got) return false;
      return !!((got.hours && got.hours.length) || (got.blocks && got.blocks.length));
    };
    // DAS ZEICHEN IST EINE FORM, KEINE FARBE. Grün ist das Urteilsregister
    // (gut/mittel/schlecht); "fertig gemessen" ist ein Zustand und kein Urteil,
    // und eine gemessene Fahrt ist weder besser noch schlechter als eine
    // offene. Der Haken trägt deshalb die FAMILIENfarbe - dasselbe Register,
    // in dem das Kürzel schon steht - und unterscheidet sich durch das
    // Zeichen, nicht durch den Ton. Die Sättigung allein war beim Scrollen
    // nicht zu sehen.
    return keys.map((key) => `<i class="smk ${fertig(key) ? "done" : "todo"}"
      style="--fc:${FAM[key].c}" title="${esc(FAM[key].l)}${fertig(key)
        ? " — gemessen" : " — markiert, noch nicht gemessen"}"
      >${ico(FAM[key].ic, FAM[key].c, 10)}${FAM[key].k}${
        fertig(key) ? `<b class="smkok">✓</b>` : ""}</i>`).join("");
  }

  /* DER QUELLEN-REITER.

     WARUM EIN REITER UND KEINE KACHEL: es sind ZWEI Schalter mit einer Sperre
     dazwischen, und die Abhaengigkeitsrichtung ist nur zu sehen, wenn beide
     NEBENEINANDER stehen - in zwei Kacheln sieht niemand, dass einer den
     anderen freigibt. Dazu: ein Schalter, den man einmal umlegt und dann
     vergisst, gehoert nicht in eine Kachel, die man taeglich ansieht, und er
     muss wiederzufinden sein.

     Der Einwand "dort bedienen, wo man die Folge sieht" ist nicht verworfen,
     sondern anders geloest: der Reiter ZEIGT die Folge, mit den Zahlen beider
     Stellungen nebeneinander.

     Die Gruppe ist eine Liste, keine feste Zahl - ein dritter Schalter kommt
     dazu, ohne dass jemand die Struktur anfasst. Gebaut wird er erst, wenn es
     ihn gibt. */
  _switchRow(cfg) {
    const an = !!cfg.on;
    const gesperrt = !!cfg.lockedBy;
    return `<div class="swrow${gesperrt ? " locked" : ""}">
      <div class="swhead">
        <b>${esc(cfg.title)}</b>
        <span class="swnow">${esc(an ? cfg.onLabel : cfg.offLabel)}</span>
      </div>
      <p class="src">${esc(cfg.what)}</p>
      ${cfg.numbers && cfg.numbers.length ? `<table class="swnum"><tr>
        <th></th><th>${esc(cfg.offLabel)}</th><th>${esc(cfg.onLabel)}</th></tr>
        ${cfg.numbers.map((r) => `<tr><td>${esc(r.l)}</td>
          <td class="tn">${esc(r.off)}</td><td class="tn">${esc(r.on)}</td></tr>`).join("")}
      </table>` : ""}
      ${cfg.note ? `<p class="src">${esc(cfg.note)}</p>` : ""}
      ${/* NICHT "Grundlage": das ist der Name einer FAMILIE, und über dem
             Blockschalter stand dann "Grundlage: VO2max: 0 von 3". Ein Wort,
             das in derselben Kachel zwei Dinge bedeutet, ist eines zu viel. */
        cfg.basis ? `<p class="src"><b>Worauf es steht:</b> ${esc(cfg.basis)}</p>` : ""}
      ${/* KATEGORIENREGISTER, nicht Urteil: die Gegenüberstellung vergleicht
             zwei Zahlen und entscheidet nichts. `.src.warn` ist Amber, also
             Urteilsfarbe — so stand die Zeile bis zum Merge da, während ihr
             Text „kein Urteil" sagte (§6, zwei Register). */
        (cfg.outside || []).length ? `<p class="src info">
        <b>Im Bereich nachgesehen:</b> ${(cfg.outside || []).map(esc).join(" · ")}.
        ${esc(cfg.outsideNote || "")}</p>` : ""}
      ${gesperrt
        // DIE SPERRE SAGT WARUM, nicht nur DASS. Eine gesperrte Schaltflaeche
        // ohne Grund ist eine Sackgasse mit Rahmen.
        ? `<p class="src warn"><b>Noch gesperrt.</b> ${esc(cfg.lockedBy)}</p>`
        : `<button class="smrunbtn${an ? " ok" : ""}" data-act="${esc(cfg.act)}"
             data-on="${an ? "0" : "1"}">${esc(an ? cfg.backLabel : cfg.goLabel)}</button>`}
    </div>`;
  }

  rQuellen(f, b) {
    const sm = this._smarks || {};
    const marks = sm.marks || [];
    const zaehl = (fam, mitMessung) => marks.filter((m) => {
      if (!(((m.marks || {})[fam] || []).length)) return false;
      if (!mitMessung) return true;
      const got = ((m.measure || {})[fam]) || null;
      return !!(got && ((got.hours || []).length || (got.blocks || []).length));
    }).length;
    const famStand = ["vo2max", "sweetspot", "tempo"].map((fam) => {
      const n = zaehl(fam, true);
      // Die Mindestzahl kommt aus der Payload oder gar nicht — kein Literal
      // als Rückfall (fünfte Bauregel).
      const min = sm.min_for_source;
      if (min == null) return `${(FAM[fam] || {}).l || fam}: ${fmt(n)}`;
      return `${(FAM[fam] || {}).l || fam}: ${fmt(n)} von ${fmt(min)}`
        + (n >= min ? "" : ` — noch ${fmt(min - n)}`);
    }).join(" · ");
    // DIE KORRIDOR-GEGENÜBERSTELLUNG. Keine Automatik: der Bereich steht fest,
    // das alpha ist gemessen, verglichen werden zwei Zahlen. Kein Wort, das
    // nach Mangel klingt — nur die Zahl und die FOLGE, und beides aus der
    // Payload.
    const korr = sm.corridor_state || {};
    const grenzen = sm.corridors || {};
    const draussen = ["vo2max", "sweetspot", "tempo"].map((fam) => {
      const box = korr[fam];
      const g = grenzen[fam];
      if (!box || !(box.outside || []).length || !g) return "";
      const werte = box.outside.map((o) => fmt(o.alpha, 2)).join(" · ");
      return `${(FAM[fam] || {}).l || fam}: ${fmt(box.outside.length)} von `
        + `${fmt(box.blocks)} Blöcken außerhalb des Bereichs `
        + `(alpha ${werte}, Bereich ${fmt(g[0], 2)}–${fmt(g[1], 2)})`;
    }).filter(Boolean);

    const plan = (f || {}).plan || [];
    const other = (f || {}).plan_other || [];
    const kurveAn = !!(f || {}).from_marks;
    // KEINE ZAHL IM QUELLTEXT. Beide Reihen kommen aus der Payload — die eine
    // ist die gerechnete Gegenstellung (`plan_other`), und welche davon links
    // steht, entscheidet die aktuelle Stellung, nicht eine feste Spalte.
    const paare = plan.map((r) => {
      const gegen = other.find((o) => o.hours === r.hours);
      if (!gegen) return null;
      return { l: `${fmt(r.hours)} h geplante Dauer`,
               off: `${fmt(kurveAn ? gegen.watts : r.watts)} W`,
               on: `${fmt(kurveAn ? r.watts : gegen.watts)} W` };
    }).filter(Boolean);
    const zahlen = paare;

    return `<div class="card pad"><h3 class="secname">Woher die Zahlen kommen</h3>
      <p class="src">Jeder Schalter sagt, was sich ändert — mit den Zahlen beider
        Stellungen. Umgelegt wird die QUELLE der Auswahl, nicht der Bestand:
        Markierungen und Messungen bleiben unberührt, und jeder Schalter lässt
        sich zurückstellen.</p>

      ${this._switchRow({
        title: "Ermüdungskurve", act: "swcurve", on: kurveAn,
        offLabel: "Namenserkennung", onLabel: "meine Markierungen",
        goLabel: "auf meine Markierungen umstellen",
        backLabel: "zurück auf Namenserkennung",
        what: kurveAn
          ? "Die Kurve liest deine markierten Abschnitte. Fahrten ohne Marke kommen "
            + "nicht vor; markierte ohne Messung stehen namentlich in der Kachel."
          : "Die Kurve liest heute jede Fahrt, die lang genug ist und nicht als "
            + "strukturierte Einheit erkannt wurde — die Auswahl trifft die "
            + "Namenserkennung, nicht du.",
        numbers: zahlen, note: (f || {}).switch_note,
        basis: `${fmt(((f || {}).rides_used) || 0)} Fahrten tragen die Kurve heute · `
          + `${fmt(zaehl("endurance", true))} markierte Grundlagen-Fahrten sind gemessen`,
      })}
      ${this._curveRides(f)}

      ${this._switchRow({
        title: "Arbeitsblöcke", act: "swblocks", on: false,
        offLabel: "Namenserkennung", onLabel: "meine Markierungen",
        goLabel: "auf meine Markierungen umstellen",
        backLabel: "zurück auf Namenserkennung",
        what: "VO2max, SweetSpot und Tempo messen über deine Arbeitsblöcke. Heute "
          + "wählt diese Messung ihre Blöcke selbst, an deinen Marken vorbei.",
        basis: famStand,
        outside: draussen, outsideNote: sm.outside_note,
        // DIE SPERRE MIT DEM GRUND, DER AM CODE TRÄGT. Bis 0.56.0 hieß es, die
        // Kurve liefere die Schwellenzahl für das Pulsfenster der Blockfamilien
        // — falsch: aerobic_hr kommt aus coach.anchors, VO2max und SweetSpot
        // nehmen ihr Fenster aus den eigenen Blöcken. Und bei umgelegter Kurve
        // fiel die Sperre und hinterließ einen Knopf ohne Handler (§7). Der
        // wahre Grund ist schlicht: der Schalter ist noch nicht gebaut.
        lockedBy: "Dieser Schalter ist noch nicht gebaut. Bis er kommt, wählt "
          + "die Blockmessung ihre Blöcke selbst, und deine Marken an VO2max, "
          + "SweetSpot und Tempo wirken auf keine Wattvorgabe.",
      })}
    </div>`;
  }

  async _setCurveSource(on) {
    if (this._swBusy) return;
    this._swBusy = true;
    try {
      await this._ws("set_curve_source", { from_marks: !!on });
      // Beide Bauteile neu holen: die Kurve rechnet anders, und der Reiter
      // zeigt ihre Zahlen.
      this._fatigue = null;
      await this._need("fatigue");
    } finally {
      this._swBusy = false;
      this._render();
    }
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
      ${this._marksBlock(a)}
      ${this._lapBlock(a)}
      ${this._lapCompare(a)}
      ${this._ctxBlock(a)}
      ${this._nightBlock(a)}
      <h3 class="secname">Verlauf <span class="hint">— gestapelte Felder, eine Zeitachse, ein Cursor: so siehst du, wie sich HF und DFA zur Leistung verhalten.</span></h3>
      ${streamsHtml}
      ${this._dfaBlock(a.dfa)}
    </section>`;
  }

  /* DIE ZUORDNUNG (docs/ausbau.md P2). Sieben Kacheln, eine Reihe, ein Ort.

     Der bisherige `_rampBlock` ist HIER AUFGEGANGEN. Er sass zwischen
     `_ctxBlock` und `_nightBlock` und trug woertlich die Begruendung, die
     jetzt fuer alles gilt ("du markierst, das System erkennt nicht") - nur an
     einem anderen Ort als die neuen Kacheln. Zwei Bedienelemente fuer dieselbe
     Frage war der Fehler aus 0.46.0. Eine Reihe, eine Frage, ein Ort.

     ZWEI VERHALTEN IN EINER REIHE, und das steht AN DER KACHEL: die sechs
     Familien HAKEN nur - gemessen wird auf "uebernehmen" (P2b, weil das
     Aktivitaetsdetail mindestens vier Ausgaenge hat und keiner ueber den
     Close-Handler laeuft). Der Stufentest MISST beim Klick, weil er es seit
     0.51.1 so tut und ein Umbau dieses Weges Risiko ohne Gewinn waere.
     Sieben gleich aussehende Bedienelemente mit zwei Verhalten sind sonst
     genau die Klasse, gegen die diese Reihe gebaut ist. */
  _marksBlock(a) {
    const sm = this._smarks;
    if (!sm) return "";
    const cur = (sm.marks || []).find((m) => String(m.activity_id) === String(a.id)) || null;
    const busy = this._smBusy === String(a.id);
    const err = this._smErr && this._smErr.id === String(a.id) ? this._smErr.msg : null;
    const msBusy = this._msBusy === String(a.id);
    const msErr = this._msErr && this._msErr.id === String(a.id) ? this._msErr.msg : null;
    const msOk = this._msOk === String(a.id);
    const cfBusy = this._cfBusy === String(a.id);
    const cfErr = this._cfErr && this._cfErr.id === String(a.id) ? this._cfErr.msg : null;
    const sel = this._famSel || null;

    // ZWEI Datenzustaende, nicht drei (docs/ausbau.md, Streichung 5): ein
    // leeres Archiv-Dict ist von "nie abgerufen" ohnehin nicht zu
    // unterscheiden, und ein Knopf "nochmal holen" holte fuer viele Fahrten
    // dasselbe Nichts.
    const dfa = a.dfa || null;
    const hasBlocks = !!(dfa && (dfa.blocks || []).length);
    const off = (key) => !dfa || (FAM_BLOCKS.includes(key) && !hasBlocks);

    // EIN Abschnitt ist kein Mangel, sondern der Normalfall einer
    // Rolleneinheit: sie IST die ganze Fahrt. "1 Abschnitt" klaenge nach einem
    // Ausschnitt aus etwas Groesserem und saet damit einen Zweifel, den es
    // nicht gibt. Der Hinweis auf Unterteilen kommt nur, wenn Intervals GAR
    // KEINE Abschnitte liefert - das entscheidet der Schreibweg, nicht diese
    // Zeile.
    const lapCount = ((this._laps[a.id] || {}).laps || []).length;
    const tiles = Object.keys(FAM).map((key) => {
      const f = FAM[key], n = ((cur && cur.marks && cur.marks[key]) || []).length;
      const ganz = n === 1 && lapCount === 1;
      const dis = off(key);
      return `<div class="famtile ${sel === key ? "on" : ""} ${dis ? "off" : ""}"
        style="--fc:${f.c}">
        <button class="famhit" data-act="famsel" data-id="${key}" ${dis ? "disabled" : ""}>
          <span class="famic">${ico(f.ic, f.c, 18)}</span>
          <b class="famk">${f.k}</b>
          <span class="famn">${esc(f.l)}</span>
          <span class="famcnt">${!n ? "—"
            : (ganz ? "die ganze Fahrt" : `${n} Abschnitt${n === 1 ? "" : "e"}`)}</span>
          ${sel === key ? `<em class="famon">gewählt</em>` : ""}
        </button>
        ${this._famHelp(key, FAM_HELP(key, sm))}
      </div>`;
    }).join("");

    const rt = this._rtests;
    const test = (rt && (rt.tests || []).find((t) => String(t.activity_id) === String(a.id))) || null;
    const rtBusy = this._rtBusy === String(a.id);
    const rtErr = this._rtErr && this._rtErr.id === String(a.id) ? this._rtErr.msg : null;
    const r = test && test.result;
    const rampTile = !rt ? "" : `<div class="famtile ramp ${test ? "on" : ""}"
      style="--fc:${C.tx2}">
      <button class="famhit" data-act="rtset" data-id="${esc(a.id)}" ${rtBusy ? "disabled" : ""}>
        <span class="famic">${ico("gauge", C.tx2, 18)}</span>
        <b class="famk">STUF</b>
        <span class="famn">Stufentest</span>
        <span class="famcnt">ganze Fahrt</span>
        <em class="famwarn">misst beim Klick: holt die Ströme und wertet aus</em>
        ${test ? `<em class="famon">markiert</em>` : ""}
      </button>
      ${this._famHelp("ramp", RAMP_HELP)}
    </div>`;

    const zahl = (node, label) => !node
      ? `<span class="durband"><em>${label}</em><b class="tn">–</b>
          <span class="mut">nicht erreicht</span></span>`
      : `<span class="durband"><em>${label}</em>
          <b class="tn">${node.watts == null ? "–" : fmt(node.watts, 0) + " W"}</b>
          <span class="mut">alpha ${fmt(node.alpha, 2)}${node.hr == null
            ? "" : " · " + fmt(node.hr, 0) + " bpm"}</span></span>`;
    // Eine Markierung OHNE Messwerte ist eine Markierung, kein stiller
    // Ausstieg: der Grund steht daneben (0.42.1).
    const gemessen = !test ? "" : (r
      ? `<div class="durbands">
           ${zahl(r.hrvt1, "erste Schwelle")}
           ${zahl(r.hrvt2, "zweite Schwelle")}
           ${zahl(r.hrvt1_pers, "erste, personalisiert")}
         </div>
         <p class="src">Gemessen aus den ungedünnten Strömen: eine Gerade durch den
           Abfall von DFA a1, die Schwelle ist ihr Schnittpunkt. Abgelesen über
           ${fmt(r.read_window_s, 0)} Sekunden.${r.reached_anaerobic
             ? "" : " Die zweite Schwelle fehlt, weil der alpha-Wert nie stabil unten war —"
                    + " das ist eine Auskunft, kein Fehler."}</p>
         <button class="ctxremove" data-act="rtdel" data-id="${esc(a.id)}"
           ${rtBusy ? "disabled" : ""}>Stufentest-Markierung zurücknehmen</button>`
      : `<p class="src"><b>Keine Werte.</b> ${esc(test.reason || "")}
         </p><button class="ctxremove" data-act="rtdel" data-id="${esc(a.id)}"
           ${rtBusy ? "disabled" : ""}>Stufentest-Markierung zurücknehmen</button>`);

    // Der Satz zum ausgegrauten Zustand sagt AUCH, dass der Archivstand nur
    // ein Stellvertreter ist - das Markieren holt die Ströme live (§7, erster
    // Fall: `stream_types` sagt, was in der Datei lag, nicht was die
    // Schnittstelle liefert).
    const lage = !dfa
      ? `<p class="mut pad">Für diese Fahrt liegt keine DFA-Auswertung im Archiv — an ihren
          Abschnitten ist nichts zu messen. Der Archivstand ist dabei nur ein Stellvertreter:
          gemessen wird aus den Strömen, die beim Übernehmen live geholt werden.</p>`
      : (!hasBlocks
        ? `<p class="mut pad">Diese Fahrt führt keine ausgewerteten Abschnitte — Grundlage und
            lange Fahrt bleiben trotzdem wählbar, sie messen über den Stundenverlauf und nicht
            über Blöcke.</p>`
        : "");

    // DIE QUITTUNG. Der Haken misst nicht - also muss etwas anderes sagen, dass
    // er ANGEKOMMEN ist, sonst klickt der Athlet ins Leere und merkt es erst,
    // wenn eine Zahl fehlt. Gezeigt wird, was WIRKLICH im Archiv steht: die
    // Zahl der Marken, ueber wie viele Familien, und wann gesetzt. Und
    // darunter der Grund aus der PAYLOAD - nicht noch einmal derselbe Satz aus
    // dem Frontend daneben (fuenfte Bauregel).
    const smTotal = Object.values((cur && cur.marks) || {})
      .reduce((sum, list) => sum + ((list || []).length), 0);
    const smFams = Object.keys((cur && cur.marks) || {}).length;
    // WIE VIELE STUNDEN TRAGEN EINEN WERT - eine Zeile, keine Tabelle. Die
    // Einzelwerte stehen ohnehin in der Trainer-Kachel; hier ist die Frage,
    // OB gemessen wurde und worauf. Zwei Orte fuer dieselbe Tabelle waeren
    // 0.46.0, und die kurze Zeile ist der Preis dafuer, dass der
    // Driftzustand mit in dieselbe Auslieferung passt.
    // JE FAMILIE EINE ZEILE. Der Knopf misst alles, was markiert ist, und die
    // Quittung sagt je Familie, was dabei herauskam — oder warum nichts.
    // Eine Sammelmeldung („gemessen") verschwiege, dass VO2max ging und die
    // Grundlage nicht.
    const mess = (cur && cur.measure) || {};
    const mitte = (v) => {
      const a = v.slice().sort((x, y) => x - y);
      if (!a.length) return null;
      const h = a.length >> 1;
      return a.length % 2 ? a[h] : (a[h - 1] + a[h]) / 2;
    };
    const famZeile = (key) => {
      const got = mess[key];
      const l = (FAM[key] || {}).l || key;
      if (!got) return `<li><b>${esc(l)}</b> — noch nicht gemessen.</li>`;
      let satz = "";
      if (key === "endurance") {
        const hs = got.hours || [];
        // Ein Fahrtende ist keine Fahrtstunde: ausdrücklich null zugelassene
        // Sekunden zählen nicht mit, fehlt das Feld, ist nichts bekannt.
        const voll = hs.filter((h) => (h || {}).points !== 0);
        const wert = hs.filter((h) => (h || {}).p075 != null).length;
        satz = hs.length
          ? `${voll.length} Fahrtstunde${voll.length === 1 ? "" : "n"}, ${wert} mit Wert`
            + (hs.length > voll.length
               ? " — die letzte angefangene Stunde war ein Fahrtende und zählt nicht mit." : ".")
          : "";
      } else {
        const bl = got.blocks || [];
        const w = mitte(bl.map((b) => (b || {}).watts).filter((v) => v != null));
        const a = mitte(bl.map((b) => (b || {}).alpha).filter((v) => v != null));
        // DER REST NACH DEM ANLAUF, je Block: ein Abschnitt, von dem nach den
        // ersten zwei Minuten 35 Sekunden bleiben, zählt sonst so viel wie
        // einer mit achtzehn Minuten — und niemand sieht es.
        const rest = bl.map((b) => (b || {}).points).filter((v) => v != null);
        satz = bl.length
          ? `${bl.length} Block${bl.length === 1 ? "" : "öcke"}`
            + (a == null ? "" : `, alpha-Median ${fmt(a, 2)}`)
            + (w == null ? "" : `, ${fmt(w)} W`)
            + (rest.length ? ` · nach dem Anlauf ${rest.map((v) => fmt(v)).join(" · ")} s` : "")
          : "";
      }
      const grund = got.reason ? `<span class="err">${esc(got.reason)}</span>` : "";
      return `<li><b>${esc(l)}</b>${satz ? " — " + satz : ""} ${grund}</li>`;
    };
    // VEREINIGUNG aus markiert UND gemessen, nicht nur markiert: ein Ergebnis,
    // dessen Marke inzwischen weg ist, verschwände sonst lautlos aus der
    // Quittung — und lautlos ist genau das, was hier nie passieren soll.
    const famListe = Object.keys(FAM).filter(
      (key) => (((cur && cur.marks) || {})[key] || []).length || mess[key]);

    const alleStd = ((mess.endurance || {}).hours || []);
    const gemStd = alleStd.filter((h) => (h || {}).p075 != null).length;
    // EIN FAHRTENDE IST KEIN VERSAGEN. Die 12.08.-Fahrt ist 2h54 lang; ihre
    // vierte Stunde trägt 25 Sekunden und stand als leere Zeile da. Solche
    // Reste zählen nicht als Fahrtstunde — gezählt wird, was zugelassene
    // Sekunden trug, und der Rest wird BENANNT statt weggelassen.
    // Ein Rest ist eine Stunde mit AUSDRÜCKLICH null zugelassenen Sekunden.
    // Fehlt das Feld, ist nichts bekannt — dann zählt die Stunde, statt sie
    // auf Verdacht wegzuwerfen.
    const gemAlle = alleStd.filter((h) => (h || {}).points !== 0).length;
    const reste = alleStd.length - gemAlle;

    // DIE ZWEI AUSSAGEN, und sie kommen BEIDE aus der Payload. "Noch nicht
    // gemessen" und "Auswahl geaendert" sind verschiedene Saetze: wer schon
    // gemessen hat, soll nach einem Umhaken nicht lesen, sein Klick sei nie
    // angekommen. Unterschieden wird an `measured_at` - der Zustand steht in
    // Feldern, der Satz kommt aus dem Leseweg (0.53.1).
    const etwasGemessen = famListe.some((key) => mess[key]);
    // Und seit 0.57: WARUM eine Messung fort ist, steht als Feld `lost` im
    // Eintrag. Ohne Feld, aber mit measured_at, ist der Grund UNBEKANNT — die
    // Kachel sagte bis dahin „Auswahl geändert", auch wo niemand umgehakt hatte.
    const lostText = sm.lost_text || {};
    const offen = !cur ? "" : (cur.reason
      ? esc(cur.reason)
      : esc((cur.measured_at
          ? (lostText[cur.lost] || lostText.unknown || sm.remeasure)
          : sm.not_measured) || ""));

    // DIE MARKIERUNGEN WIRKEN NOCH NICHT, und das steht da, solange es so
    // ist - unabhaengig davon, ob an DIESER Fahrt schon etwas markiert ist,
    // denn gelesen wird der Satz beim Markieren. Zwei Saetze, keiner:
    // die Blockfamilien MESSEN bereits und gehen an den Marken vorbei, die
    // Kurve misst die Marken schon und liest sie noch nicht. Beides aus der
    // Payload.
    const na = sm.not_active || {};
    // Die Überschrift folgt der LAGE: steht nur noch der Blocksatz da, wirken
    // die Grundlagen-Marken bereits (Kurvenschalter an), und ein pauschales
    // „die Markierungen" wäre falsch.
    const nochNicht = (na.blocks || na.curve) ? `<p class="src warn">
        <b>${na.curve ? "Die Markierungen wirken noch nicht."
                      : "Die Blockmarkierungen wirken noch nicht."}</b>
        ${esc(na.blocks || "")} ${esc(na.curve || "")}</p>` : "";

    const stand = !cur ? "" : `<p class="src">
        <b>Im Archiv:</b> ${smTotal} Marke${smTotal === 1 ? "" : "n"} über
        ${smFams} Familie${smFams === 1 ? "" : "n"}${cur.set_at
          ? `, zuletzt gesetzt am ${esc(cur.set_at)}` : ""}.
        ${etwasGemessen
          ? `Gemessen${cur.measured_at ? ` am ${esc(cur.measured_at)}` : ""}:
             <ul class="smfam">${famListe.map(famZeile).join("")}</ul>
             ${gemStd === 0 && (mess.endurance || {}).hours ? esc(sm.no_value || "") : ""}`
          // Ein ECHTER Grund aus dem Archiv (gescheiterte Messung,
          // Versionswechsel) gewinnt; sonst der Satz aus dem Leseweg. Er steht
          // seit 0.53.1 nicht mehr im Eintrag, weil ein gespeicherter
          // Anzeigetext mit dem naechsten Umbau veraltet.
          : offen}</p>`;

    // DER DRIFTZUSTAND UND SEIN AUSWEG STEHEN AN DERSELBEN STELLE. Der Befund
    // kommt mit den Runden (nur gegen sie ist er zu haben), und der Knopf
    // steht daneben statt in einem Menue: ein Zustand, aus dem der Weg heraus
    // woanders liegt, ist einer, aus dem man nicht herauskommt. Genau das war
    // `confirm_section_marks` drei Releases lang - gebaut und nie bedienbar.
    const stale = ((this._laps[a.id] || {}).marks_stale) || null;
    const drift = !(cur && stale) ? "" : `<div class="err pad">
        <b>Die Zuordnung sitzt nicht mehr.</b>
        ${esc((sm.stale_reason || {})[stale] || "")}
        ${cfErr ? `<br>${esc(cfErr)}` : ""}
        <br><button class="ctxremove" data-act="smconf" data-id="${esc(a.id)}"
          ${cfBusy || busy ? "disabled" : ""}>Zuordnung auf den neuen Stand
          setzen — die Marken bleiben, die Messung fällt</button></div>`;

    // DER KNOPF MISST NUR, WAS MARKIERT IST. Er hakt nichts an, schlaegt
    // nichts vor, ergaenzt nichts. Ohne Marke gibt es nichts zu messen, und
    // waehrend die Fahrt driftet, waere jede Messung eine auf verschobenen
    // Abschnitten - beides sperrt ihn, und die Sperre sagt warum.
    const messen = !cur ? "" : `<div class="smrun">
        <button class="smrunbtn${msOk ? " ok" : ""}" data-act="smmeasure"
          data-id="${esc(a.id)}" ${msBusy || busy || stale ? "disabled" : ""}>
          ${msBusy ? "misst …" : (msOk ? "✓ gemessen" : "übernehmen und messen")}
        </button>
        ${msErr ? `<span class="err">${esc(msErr)}</span>` : ""}</div>`;

    return `<h3 class="secname">Zuordnung
      <span class="hint">— du ordnest zu, das System erkennt nicht. Familie wählen, dann die
      Abschnitte in der Rundenliste anhaken.</span></h3>
      <div class="ctxbox dtbox">
        <div class="famrow">${tiles}${rampTile}</div>
        ${lage}
        ${sel ? `<p class="src">Gewählt: <b>${esc(FAM[sel].l)}</b> — hake die Abschnitte in der
          Spalte „Zuordnung“ der Rundenliste an. Der Haken misst nicht.</p>` : ""}
        ${busy ? `<div class="loading"><span class="spin"></span> Abschnitte werden geholt …</div>` : ""}
        ${err ? `<div class="err pad">${esc(err)}</div>` : ""}
        ${rtBusy ? `<div class="loading"><span class="spin"></span> Ströme werden geholt und gemessen …</div>` : ""}
        ${rtErr ? `<div class="err pad">${esc(rtErr)}</div>` : ""}
        ${nochNicht}
        ${drift}
        ${stand}
        ${messen}
        ${gemessen}
      </div>`;
  }

  /* Die Aufklappung je Kachel.

     KEIN natives <details>: die Familienwahl loest ein Re-Render aus, und
     innerHTML wirft den offenen Zustand mit den alten Knoten weg. Der Athlet
     klappt auf, waehlt eine Familie - und die Erklaerung ist wieder zu. Also
     ein eigener Zustand, der das Re-Render ueberlebt.

     Die Reihe steht auf `align-items:flex-start`: eine wachsende Kachel
     schiebt ihre Nachbarn nicht nach unten, und die gewaehlte bleibt da, wo
     sie war. */
  _famHelp(key, rows) {
    const open = (this._famOpen || {})[key];
    return `<button class="fammore" data-act="fammore" data-id="${key}"
      aria-expanded="${open ? "true" : "false"}">${open ? "weniger" : "mehr anzeigen"}</button>
      ${open ? `<div class="famexp">${rows.map(
        ([titel, text]) => `<p><b>${esc(titel)}</b><br>${esc(text)}</p>`).join("")}</div>` : ""}`;
  }

  /* Eine Marke setzen oder zuruecknehmen.

     Die Scroll-Lage wird VOR dem Re-Render gesichert: innerHTML wirft sie
     sonst mit den alten Knoten weg, und der Athlet haekt in der Rundenliste,
     also weit unten (dieselbe Regel wie bei _ctxWrite und _rtWrite).

     DIE DREI GRUENDE KOMMEN IM KLARTEXT AN. Das Backend schickt sie als Satz;
     hier wird nichts zu "Fehler beim Markieren" zusammengefasst - der
     haeufigste Fall ist "in Intervals unterteilen", und der ist nur als
     eigener Satz brauchbar. */
  async _smWrite(id, family, index, mark) {
    if (!id || !family || this._smBusy || this._msBusy) return;
    this._smBusy = String(id);
    this._smErr = null;
    // Die Quittung der letzten Messung gilt nicht mehr: `hours` faellt mit
    // jeder Aenderung, und ein gruener Knopf darueber waere schlicht falsch.
    this._msOk = null;
    this._msErr = null;
    this._render();
    try {
      await this._ws("set_section_mark", {
        activity_id: String(id), family, start_index: index, mark: !!mark,
      });
      const scroll = this.scrollTop;
      this._smarks = await this._ws("section_marks");
      this._smBusy = null;
      this._render();
      this.scrollTop = scroll;
    } catch (err) {
      const scroll = this.scrollTop;
      this._smBusy = null;
      this._smErr = { id: String(id), msg: String((err && err.message) || err) };
      this._render();
      this.scrollTop = scroll;
    }
  }

  /* "Uebernehmen und messen".

     ER MISST NUR, WAS MARKIERT IST - gehakt wird hier nichts, vorgeschlagen
     auch nichts. GRUEN bei Erfolg, ROT mit dem Grund im KLARTEXT: das Backend
     schickt fuer jede der fuenf Lagen einen eigenen Satz (Stroeme nicht
     abrufbar · Stroeme da, Abschnitte nicht · keine Abschnitte mehr ·
     Zuordnung verschoben · kein auswertbares alpha), und hier wird nichts zu
     "Messung fehlgeschlagen" zusammengefasst. Der haeufigste Fall ist
     "in Intervals unterteilen", und der ist nur als eigener Satz brauchbar.

     Eine Messung, die ohne Zahlen zurueckkommt, ist KEIN Erfolg: das Backend
     legt den Grund dann im Archiv ab (Sachbefund), und die Kachel zeigt ihn
     rot - sonst faerbte sich der Knopf gruen ueber einer Fahrt, an der nichts
     gemessen wurde (0.42.1).

     Die Scroll-Lage wird VOR dem Re-Render gesichert, wie bei _smWrite. */
  async _smMeasure(id) {
    if (!id || this._msBusy || this._smBusy) return;
    this._msBusy = String(id);
    this._msErr = null;
    this._msOk = null;
    this._render();
    try {
      const res = await this._ws("measure_section_marks", { activity_id: String(id) });
      const scroll = this.scrollTop;
      this._smarks = await this._ws("section_marks");
      this._msBusy = null;
      // GRÜN nur, wenn KEINE Familie einen Grund trägt. Eine Fahrt, an der
      // VO2max gemessen hat und die Grundlage nicht, ist kein Erfolg —
      // sonst färbte sich der Knopf über einem halben Ergebnis.
      const fams = (res && res.families) || {};
      const gruende = Object.keys(fams)
        .map((k) => (fams[k] || {}).reason).filter(Boolean);
      if (gruende.length) this._msErr = { id: String(id), msg: gruende.join(" ") };
      else this._msOk = String(id);
      this._render();
      this.scrollTop = scroll;
    } catch (err) {
      const scroll = this.scrollTop;
      this._msBusy = null;
      this._msErr = { id: String(id), msg: String((err && err.message) || err) };
      this._render();
      this.scrollTop = scroll;
    }
  }

  /* Die verschobene Zuordnung ausdruecklich bestaetigen.

     Der Knopf steht dort, wo der Befund gemeldet wird, und nirgends sonst.
     Danach werden die Runden NEU geholt: der Driftbefund haengt an ihnen, und
     ohne den zweiten Abruf staende die alte Meldung weiter da, obwohl sie
     erledigt ist - ein Zustand, der sich nicht aufloest, sieht aus wie einer,
     der nicht behoben wurde. */
  async _smConfirm(id) {
    if (!id || this._cfBusy) return;
    this._cfBusy = String(id);
    this._cfErr = null;
    this._render();
    try {
      await this._ws("confirm_section_marks", { activity_id: String(id) });
      const scroll = this.scrollTop;
      this._smarks = await this._ws("section_marks");
      this._laps[id] = await this._ws("laps", { activity_id: String(id) });
      this._cfBusy = null;
      this._msOk = null;
      this._render();
      this.scrollTop = scroll;
    } catch (err) {
      const scroll = this.scrollTop;
      this._cfBusy = null;
      this._cfErr = { id: String(id), msg: String((err && err.message) || err) };
      this._render();
      this.scrollTop = scroll;
    }
  }

  async _rtWrite(id, mark) {
    if (!id || this._rtBusy) return;
    this._rtBusy = String(id);
    this._rtErr = null;
    this._render();
    try {
      const res = await this._ws("set_ramp_test", { activity_id: String(id), mark });
      // Scroll-Lage VOR dem Re-Render sichern: innerHTML wirft sie sonst mit
      // den alten Knoten weg (dieselbe Regel wie bei _ctxWrite).
      const scroll = this.scrollTop;
      this._rtests = await this._ws("ramp_tests");
      if (res && res.reason) this._toast(res.reason);
      this._rtBusy = null;
      this._render();
      this.scrollTop = scroll;
    } catch (err) {
      this._rtBusy = null;
      this._rtErr = { id: String(id), msg: String((err && err.message) || err) };
      this._render();
    }
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
    // DIE ZUORDNUNGSSPALTE. Sie steht fuer sich, mit eigener Kopfzeile, und
    // NICHT zwischen den rollengefaerbten Balken: die Rundenliste zeichnet den
    // EF-Balken in ROLE.pow und den DFA-Balken in ROLE.dfa, und ein
    // violetter SweetSpot-Haken zwei Spalten neben einem violetten
    // Leistungsbalken waere dieselbe Registervermischung, nur innerhalb des
    // Kategorienregisters (docs/ausbau.md P2a).
    // NICHT `entry` nennen: ein Waechter in test_workouts haelt jedes
    // `entry.<feld>` im Panel gegen die Payload der Einheitenkarte. Er hat
    // beim ersten Lauf zu Recht angeschlagen - und die Aufloesung ist, die
    // Kollision zu beseitigen, nicht den Waechter um eine Ausnahme zu
    // erweitern (§9, dritte Bauregel: ein gelockerter Waechter ist keiner).
    const smRow = (this._smarks && (this._smarks.marks || [])
      .find((m) => String(m.activity_id) === String(a.id))) || null;
    const famSel = this._famSel || null;
    const marksAt = (index) => Object.keys(FAM).filter(
      (key) => ((smRow && smRow.marks && smRow.marks[key]) || []).includes(index));

    const rows = laps.map((l) => {
      const rest = (l.avg_watts || 0) <= 0 || (l.moving_time || 0) < 60;
      // Der Schluessel ist start_index, NIE die laufende Nummer (P3a). Ein
      // Abschnitt ohne ihn ist nicht zuzuordnen, und das steht da, statt still
      // zu fehlen.
      const idx = l.start_index;
      const here = idx == null ? [] : marksAt(idx);
      const on = famSel && here.includes(famSel);
      const zuordnung = idx == null
        ? `<span class="mut" title="Dieser Abschnitt trägt keinen Startpunkt im Strom — er ist nicht zuzuordnen.">–</span>`
        : `${here.map((key) => `<i class="smk" style="--fc:${FAM[key].c}"
             title="${esc(FAM[key].l)}">${ico(FAM[key].ic, FAM[key].c, 11)}${FAM[key].k}</i>`).join("")}
           ${famSel ? `<button class="smbox ${on ? "on" : ""}" data-act="smark"
             data-id="${esc(a.id)}" data-fam="${famSel}" data-idx="${idx}"
             data-on="${on ? "1" : "0"}" style="--fc:${FAM[famSel].c}"
             title="${on ? "Marke zurücknehmen" : "Als " + esc(FAM[famSel].l) + " markieren"}"
             >${on ? ico(FAM[famSel].ic, FAM[famSel].c, 13) : ""}</button>` : ""}`;
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
        <span class="lmk">${zuordnung}</span>
      </div>`;
    }).join("");
    return `<h3 class="secname">Runden <span class="hint">— ${laps.length} Abschnitte${data.source ? `, Feld „${esc(data.source)}"` : ""}</span></h3>
      ${verdict}
      <div class="card2 pad0">
        <div class="lhead"><span>#</span><span>Abschnitt</span><span>Dauer</span><span>Ø Watt</span>
          <span>Ø HF</span><span>Kadenz</span><span>EF (W/Schlag)</span><span>DFA a1</span>
          <span>Zuordnung</span></div>
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
      const mark = this._decGood();
      tone = (mark != null && drop > mark) ? "worse" : "held";
      const grade = mark == null
        ? "die Einordnung braucht die Marke aus dem Archiv-Status — sie steht gerade nicht bereit"
        : drop <= 3 ? "unter 3 % — das ist das Niveau, das trainierte Fahrer halten"
        : drop <= mark ? `unter ${fmt(mark, 0)} % — Friels Richtwert, eine Trainerfaustregel und keine Studiengrenze`
        : drop <= 10 ? `zwischen ${fmt(mark, 0)} und 10 % — der Bereich, in dem Freizeitfahrer typischerweise liegen`
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
          <span class="ctxsay">${esc(m.say || `nur ${m.n} vergleichbare Einheiten — zu wenig für eine Einordnung`)}</span>
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
          <em>Median ${fmt(m.median, 2)}${esc(m.unit)} · ${m.n} Einheiten<br>
          ${fmt(m.stage, 1)} SD: Dauer ${sign(m.duration_low_pct, 0)} % bis ${sign(m.duration_high_pct, 0)} %,
          Intensität ±${fmt(m.intensity_points, 1)}</em></span>
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
      <span class="hint">— gegen deine ${c.earlier} früheren Einheiten derselben Sportart; die Toleranz
      weitet sich je Kennzahl, bis mindestens ${c.min_peers} Vergleichswerte zusammenkommen</span></h3>
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
    // Das Urteil kommt aus der Payload (derive.threshold_verdict), nicht aus
    // einem Vergleich hier - sonst steht die Regel zum fuenften Mal im Haus.
    const thr = s.threshold || {};
    const weak = !thr.hr_usable;
    return `<h3 class="secname">DFA alpha-1 dieser Einheit</h3>
      <div class="dfabox">${rowsHtml}
        ${thr.hr != null ? `<div class="dfathr">Aerobe Schwelle abgelesen bei
          <b class="tn">${fmt(s.hr_at_threshold)} bpm</b>
          ${s.power_at_threshold ? `· <b class="tn">${fmt(s.power_at_threshold)} W</b>` : ""}
          ${badge(thr.failure ? "red" : weak ? "amber" : "green",
            thr.failure ? `Ausfall — keine Messung`
              : `${thr.hr_windows} Messpunkte${weak ? " — dünn" : ""}`)}
        </div>` : ""}
        <p class="src">Rogers und Gronwald: DFA alpha-1 0,75 ≈ aerobe Schwelle (VT1), 0,5 ≈ anaerobe (VT2). Die Validierungslage ist gemischt: gegen Spiroergometrie stimmt VT1 nur schwach überein (weite Übereinstimmungsgrenzen, bei Fitteren wird die Schwelle eher unterschätzt); VT2 ist robuster. Als Trend am eigenen Körper brauchbar, als alleinige Verankerung nicht — dazu empfindlich für Artefakte und Aufzeichnungsgerät.</p>
      </div>`;
  }

  /* ---------------- Belastung ---------------- */
  rBelastung(load) {
    if (!load) return this._dataGap("load", "Die Belastungsdaten");
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
      const mark = (load.thresholds || {}).decoupling_good;
      const pts = dcp.map((x, i) => ({
        i, v: x.decoupling,
        c: (mark != null && x.decoupling > mark) ? C.amber : x.decoupling <= 0 ? C.green : ROLE.series, r: 4,
      }));
      const xt = monthTicks(dcp.map((x) => x.date));
      dcpHtml = chart({
        h: 190, n: dcp.length, y0: d0, y1: d1, xt, yf: (v) => fmt(v, 0) + " %",
        hl: [...(mark != null ? [{ y: mark, c: C.amber, d: 1, t: `${fmt(mark, 0)} %-Marke` }] : []),
             { y: 0, c: C.tx3 }],
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
    if (!thr) return this._dataGap("thr", "Die DFA-Daten");
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

    // EIN Urteil, im Backend gefaellt (derive.threshold_verdict) und hier nur
    // gelesen. Bis 0.44.0 stand die Regel hier - und die Leistungskurve unten
    // las eine ANDERE, sodass sie eine Fahrt behielt, die die HF-Kurve verwarf.
    const isSolid = (x) => x.hr_usable === true;
    const powSolid = (x) => x.power_usable === true;
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
      const solidPt = isSolid(x);
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

    const powRows = rows.map((x) => (powSolid(x) ? x.power : null));
    let powCh = "";
    if (powRows.some((v) => v != null)) {
      const [p0, p1] = domainOf([{ v: all.map((x) => (powSolid(x) ? x.power : null)) }]);
      powCh = chart({
        h: 130, n, y0: p0, y1: p1, grp: "dfa",
        s: [
          { t: "dots", p: rows.map((x, i) => (powRows[i] != null
              ? { i, v: powRows[i], c: ROLE.pow, r: pick && x.activity_id === pick ? 5.4 : 3.4,
                  op: pick ? (x.activity_id === pick ? 1 : 0.35) : 1,
                  ring: !!pick && x.activity_id === pick,
                  id: powSolid(x) ? x.activity_id : null } : null)).filter(Boolean), c: ROLE.pow },
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
        { l: "Messpunkte", c: C.tx2, vals: rows.map((x) => x.hr_windows) },
      ],
    };

    // TRAP 4: the list follows the window, or A1 breaks - a point in the
    // graph without a row. Capped at 50 with the cap SPOKEN: a list that
    // stops at fifteen without saying so was half the trap, and one that
    // silently renders four hundred rows is the other half.
    const CAP = 50;
    const shown = rows.slice(-CAP).reverse();
    const capped = w.kept > CAP;
    const decGood = this._decGood();
    const tableRows = shown.map((x) => {
      const weak = !isSolid(x);
      const sp = sportOf(x.type);
      const base = rollBy[x.activity_id];
      const dev = (!weak && x.hr != null && base != null) ? x.hr - base : null;
      const devCls = dev == null ? "mut" : Math.abs(dev) >= 3 ? "warncol" : "okcol";
      const dec = x.decoupling;
      const decCls = (dec == null || decGood == null) ? "mut" : dec > decGood ? "warncol" : "okcol";
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
        <span>${x.failure ? badge("red", "Ausfall — keine Messung")
          : x.hr_windows == null ? badge("amber", "Belegung unbekannt")
          : weak ? badge("amber", x.hr_windows + " Punkte — dünn")
          : badge("green", x.hr_windows + " Punkte")}</span>
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
      ${this._historyNote()}
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
/* Abgleich mit Intervals (Paket D) */
.syncbtn{display:inline-flex;align-items:center;gap:6px;margin-left:12px;padding:5px 10px;
  border-radius:9px;background:#0005;border:1px solid ${C.line};color:${C.tx2};
  font-family:inherit;font-size:12.5px;cursor:pointer;white-space:nowrap}
.syncbtn:hover{background:#0008;color:${C.tx}}
.synclist{list-style:none;margin:10px 0;padding:0;max-height:38vh;overflow-y:auto;
  border:1px solid ${C.line};border-radius:10px}
.syncrow{display:flex;align-items:center;gap:8px;padding:7px 11px;font-size:13.5px;
  border-bottom:1px solid ${C.line}}
.syncrow:last-child{border-bottom:none}
.syncrow .cn{flex:1;color:${C.tx2}}
.syncgo{width:100%;margin-top:4px}
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
/* minmax(0,1fr), nicht 1fr: 1fr ist minmax(auto,1fr), und auto laesst die
   Spalte nicht unter ihre Inhaltsbreite schrumpfen - ein langer Name in einer
   Tageszelle schob damit das ganze Raster aus dem Bild (docs/ausbau.md E1). */
.calhead{display:grid;grid-template-columns:190px repeat(7,minmax(0,1fr));gap:8px;padding:0 2px 6px;
  color:${C.tx3};font-size:12.5px;font-weight:600;letter-spacing:.06em}
.calhead span{text-align:left;padding-left:8px}
.wkrow{display:grid;grid-template-columns:190px repeat(7,minmax(0,1fr));gap:8px;margin-bottom:8px}
/* dieselbe Sperre eine Ebene tiefer: Grid- und Flex-Kinder haben min-width:auto */
.wkrow>*,.calhead>*{min-width:0}
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
.day{background:${C.card};border:1px solid ${C.line};border-radius:10px;padding:8px;min-height:96px;
  min-width:0;overflow:hidden}
.day.is-fut{background:${C.bg};border-style:dashed}
.day.is-today{border-color:${C.blue};box-shadow:0 0 0 1px ${C.blue}}
.day.off{background:none;border:none}
.dhead{display:flex;justify-content:space-between;align-items:baseline;font-size:13.5px;font-weight:650;margin-bottom:4px}
.is-fut .dhead{color:${C.tx3}}
.dload{color:${C.blue};font-size:14px}
.wln{display:flex;gap:8px;flex-wrap:wrap;color:${C.tx3};font-size:12px;margin-bottom:6px}
.wln span{display:inline-flex;align-items:center;gap:2.5px}
.chip{position:relative;display:flex;align-items:center;gap:6px;width:100%;min-width:0;text-align:left;
  background:${C.card2};border:1px solid ${C.line};border-left:3px solid var(--sc);border-radius:8px;
  padding:6px 8px 8px;margin-top:5px;color:${C.tx};font:inherit;font-size:13px;cursor:pointer}
.chip:hover{border-color:var(--sc)}
.chip .cn{flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-weight:600}
.chip .cd{color:${C.tx2}}
.chip .cl{background:#0009;border-radius:6px;padding:1px 6px;font-weight:700;font-size:12.5px}
.chip.plan{border-left-style:dashed;border-style:dashed;cursor:default;color:${C.tx2}}
.chip.plan.done{border-style:solid;color:${C.tx}}
.chip.plan.missed .cn{color:${C.red}}
.zb{position:absolute;left:8px;right:8px;bottom:3px;height:3px;display:flex;border-radius:2px;overflow:hidden}
.zb s{display:block;height:100%}
.zb.w{position:static;width:74px;height:8px;border-radius:3px}
/* Aktivitäten */
.ahead,.arow{display:grid;grid-template-columns:36px minmax(160px,1.4fr) 76px 86px 60px 60px 96px 92px 96px 112px;
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
.lhead,.lrow{display:grid;grid-template-columns:34px minmax(120px,1.2fr) 74px 78px 82px 62px 1.1fr 1.1fr 118px;
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
/* Zuordnung (P2): Kachelreihe, Marken, Haken-Spalte.
   Die AKTIVE Kachel traegt Rahmen, Form UND das Wort "gewählt" - nicht nur
   eine Saettigungsstufe. Wer die aktive Kachel nicht sieht, hakt in die
   falsche Familie, und das ist ein Fehler ohne Fehlermeldung. */
.famrow{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:8px;align-items:flex-start}
.famtile{min-width:132px;max-width:236px;padding:8px 10px;
  background:${C.card2};border:2px solid ${C.line};border-radius:10px;
  color:${C.tx};text-align:left;font:inherit}
.famhit{display:grid;grid-template-columns:auto auto;grid-auto-rows:min-content;
  gap:2px 8px;align-items:center;width:100%;padding:0;cursor:pointer;
  background:none;border:0;color:inherit;text-align:left;font:inherit}
.famhit:disabled{cursor:not-allowed}
.fammore{margin-top:6px;padding:0;background:none;border:0;cursor:pointer;
  color:${C.tx3};font:inherit;font-size:11.5px;text-decoration:underline}
.fammore:hover{color:var(--fc)}
.famexp{margin-top:6px;border-top:1px solid ${C.line};padding-top:6px;
  font-size:12px;line-height:1.45;color:${C.tx2}}
.famexp p{margin:0 0 6px}
.famexp p:last-child{margin-bottom:0}
.famexp b{color:${C.tx}}
.famtile:hover{border-color:var(--fc)}
.famtile.on{border-color:var(--fc);background:color-mix(in srgb,var(--fc) 14%,${C.card2});
  box-shadow:0 0 0 2px color-mix(in srgb,var(--fc) 35%,transparent)}
.famtile.off{opacity:.4;cursor:not-allowed}
.famic{grid-row:span 2;display:flex}
.famk{font-size:13px;letter-spacing:.06em;color:var(--fc)}
.famn{font-size:13px;color:${C.tx2};grid-column:2}
.famcnt{grid-column:2;font-size:11.5px;color:${C.tx3}}
.famon{grid-column:1/-1;font-style:normal;font-size:11.5px;font-weight:700;color:var(--fc)}
.famwarn{grid-column:1/-1;font-style:normal;font-size:11.5px;color:${C.tx3};max-width:190px}
.lmk{display:flex;align-items:center;gap:5px;flex-wrap:wrap}
.smk{display:inline-flex;align-items:center;gap:3px;font-style:normal;font-size:11px;
  font-weight:700;letter-spacing:.04em;color:var(--fc);
  border:1px solid color-mix(in srgb,var(--fc) 45%,transparent);
  border-radius:6px;padding:1px 5px 1px 3px}
.amk{display:flex;align-items:center;gap:4px;flex-wrap:wrap}
.smk.todo{opacity:.5}
/* Familienfarbe, nicht Urteilston: der Haken sagt "fertig", nicht "gut". */
.smkok{font-style:normal;font-weight:700;font-size:10px;margin-left:1px;color:var(--fc)}
.smbox{width:22px;height:22px;display:inline-flex;align-items:center;justify-content:center;
  border:2px solid ${C.line};border-radius:6px;background:none;cursor:pointer;padding:0}
.smbox:hover{border-color:var(--fc)}
.swrow{border:1px solid ${C.line};border-radius:10px;padding:10px 12px;margin:10px 0}
.swrow.locked{opacity:.75}
.swhead{display:flex;align-items:baseline;gap:8px;flex-wrap:wrap}
.swnow{font-size:12px;color:${C.tx2}}
.swnum{border-collapse:collapse;margin:6px 0;font-size:12px}
.swnum th,.swnum td{padding:2px 10px 2px 0;text-align:left;color:${C.tx2}}
.smfam{margin:4px 0 0;padding-left:16px}
.smfam li{margin:2px 0}
.smrun{display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin-top:6px}
.smrun .err{font-size:12px}
/* Eigene Klasse statt ctxremove: der wuchs auf die volle Breite und blieb in
   jedem Zustand grau - am Erfolg war nur der Text zu erkennen. */
.smrunbtn{display:inline-flex;align-items:center;width:auto;align-self:flex-start;
  margin:6px 0 2px;padding:6px 13px;border-radius:8px;cursor:pointer;
  border:1.5px solid ${C.tx3};background:none;color:${C.tx2};
  font-family:inherit;font-size:13px;text-align:left}
.smrunbtn:hover:not(:disabled){border-color:${C.tx2};color:${C.tx}}
.smrunbtn:disabled{opacity:.45;cursor:default}
/* Der Erfolg traegt den Zustandston, nicht nur ein anderes Wort. */
.smrunbtn.ok{border-color:${C.green};color:${C.green};background:${C.green}1f}
.src.warn{border-left:2px solid ${C.amber};padding-left:9px}
.src.info{border-left:2px solid ${C.slate};padding-left:9px}
.lnk{color:${C.blue};cursor:pointer;text-decoration:underline;text-underline-offset:2px}
.ridelist{margin-top:10px}.ridelist>summary{cursor:pointer;color:${C.tx2};font-size:13.5px}
.smbox.on{border-color:var(--fc);background:color-mix(in srgb,var(--fc) 16%,transparent)}
/* Tagesbeschriftung (B5): fester Dialog, Kategorien-Chips, Marker */
.tday[data-act]{cursor:pointer}
.day[data-act]{cursor:pointer}
.ctxmark{display:inline-flex;margin-left:4px;vertical-align:middle;opacity:.9}
.ctxnote{display:flex;gap:8px;align-items:flex-start;margin:10px 2px 0;padding:9px 12px;
  background:#0006;border:1px solid ${C.line};border-radius:9px;color:${C.tx2};font-size:13px}
.ctxback{position:fixed;inset:0;background:#000a;z-index:40}
.ctxdlg{position:fixed;left:50%;top:50%;transform:translate(-50%,-50%);z-index:41;
  width:min(560px,calc(100vw - 28px));max-height:min(82vh,700px);overflow-y:auto;
  background:${C.card};border:1px solid ${C.line};border-radius:14px;padding:16px 18px;
  box-shadow:0 18px 60px #000c}
.ctxhead{display:flex;align-items:center;justify-content:space-between;gap:10px;margin-bottom:6px}
.ctxhead b{font-size:15.5px}
.ctxx{background:none;border:none;cursor:pointer;padding:4px;display:inline-flex;opacity:.8}
.ctxx:hover{opacity:1}
.ctxcur{margin:2px 0 8px;color:${C.tx2};font-size:13.5px}
.ctxchips{display:grid;grid-template-columns:repeat(auto-fill,minmax(230px,1fr));gap:8px;margin:8px 0}
.ctxchip{display:flex;align-items:center;gap:8px;padding:9px 11px;border-radius:10px;
  background:#0005;border:1px solid ${C.line};border-left:3px solid var(--cc);
  color:${C.tx};font-family:inherit;font-size:13.5px;cursor:pointer;text-align:left}
.ctxchip:hover{background:#0008}
.ctxchip .cn{flex:1;font-weight:600}
.ctxchip .cw{color:${C.tx3};font-size:12px}
.ctxchip.on{outline:2px solid var(--cc);outline-offset:1px;background:#0008}
.ctxchip .csel{display:inline-flex;align-items:center;gap:4px;font-size:12px;font-weight:700}
/* Entfernen ist RÜCKNAHME, keine Kategorie: gestrichelt, ohne Kategorienfarbe,
   eigene Zeile - sichtbar etwas anderes als der normal-Chip */
.ctxremove{display:flex;width:100%;align-items:flex-start;gap:8px;margin:6px 0 2px;
  padding:10px 12px;border-radius:10px;background:none;border:1.5px dashed ${C.tx3};
  color:${C.tx2};font-family:inherit;font-size:13px;cursor:pointer;text-align:left}
.ctxremove:hover{border-color:${C.tx2};color:${C.tx}}
.ctxerr{display:flex;gap:8px;align-items:flex-start;margin:8px 0;padding:9px 12px;
  background:#0006;border:1px solid ${C.amber}66;border-radius:9px;color:${C.tx2};font-size:13px}
.ctxwhy{margin:10px 0 6px;color:${C.tx2};font-size:13.5px;line-height:1.55}
@media(max-width:980px){
  .lhead{display:none}
  .lrow{grid-template-columns:30px 1fr 70px 74px;}
  /* Die neunte Spalte gehoert ausdruecklich in die Ausblendliste - sonst
     rutscht die Zuordnung auf dem Telefon in die vier sichtbaren und
     verdraengt eine Kennzahl. Ob sie dort spaeter SICHTBAR werden soll, ist
     eine eigene Entscheidung (docs/ausbau.md, offene Mobilfrage). */
  .lrow>*:nth-child(5),.lrow>*:nth-child(6),.lrow>*:nth-child(7),.lrow>*:nth-child(8),
  .lrow>*:nth-child(9){display:none}
}
/* Abgleich mit Intervals (Paket D) */
.syncbtn{display:inline-flex;align-items:center;gap:6px;margin-left:12px;padding:5px 10px;
  border-radius:9px;background:#0005;border:1px solid ${C.line};color:${C.tx2};
  font-family:inherit;font-size:12.5px;cursor:pointer;white-space:nowrap}
.syncbtn:hover{background:#0008;color:${C.tx}}
.synclist{list-style:none;margin:10px 0;padding:0;max-height:38vh;overflow-y:auto;
  border:1px solid ${C.line};border-radius:10px}
.syncrow{display:flex;align-items:center;gap:8px;padding:7px 11px;font-size:13.5px;
  border-bottom:1px solid ${C.line}}
.syncrow:last-child{border-bottom:none}
.syncrow .cn{flex:1;color:${C.tx2}}
.syncgo{width:100%;margin-top:4px}
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
.tweek{display:grid;grid-template-columns:repeat(7,minmax(0,1fr));gap:8px}
.tweek>*{min-width:0}
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
.pweek.now{border-color:${C.tx3}}
.pwdone{display:grid;gap:4px;padding:8px 10px;border-top:1px dashed ${C.line}}
.pwdrow{display:flex;gap:8px;align-items:baseline;flex-wrap:wrap}
.pwdlab{color:${C.tx3};font-size:12px;min-width:74px;text-transform:uppercase;letter-spacing:.04em}
.pshead{display:flex;gap:8px;align-items:center;justify-content:space-between;flex-wrap:wrap}
.psload{color:${C.tx2};font-size:12.5px;margin:2px 0}
.pstage{display:inline-flex;gap:3px;align-items:center;font-size:11px;margin-left:4px}
.noverdict{display:flex;gap:6px;align-items:flex-start}
.stagelegend{margin:10px 0;padding:10px 12px;background:${C.card};border:1px solid ${C.line};border-radius:10px}
.stagelegend small{color:${C.tx3};text-transform:uppercase;letter-spacing:.04em;font-size:11.5px}
.stagerow{display:flex;gap:8px;align-items:flex-start;margin-top:6px;font-size:13px;color:${C.tx2}}
.stagerow b{white-space:nowrap}
.choicebox{margin-top:10px}
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
.dtbox .ctxchips{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin-bottom:8px}
.dtpair{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin-top:6px}
.dtsteps{margin:4px 0 0 16px;padding:0}
.dtsteps li{margin:3px 0}
.protoblock{border-color:var(--divider-color,#3336)}
.protowhy{margin:0 0 6px;display:flex;gap:8px;align-items:flex-start}
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
.durhead{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:10px;
  margin:2px 0 12px}
.dhcard{background:${C.card2};border:1px solid ${C.line};border-radius:11px;padding:12px 14px}
.dhlab{color:${C.tx3};font-size:10.5px;letter-spacing:.09em;font-weight:600}
.dhbig{display:flex;align-items:baseline;gap:7px;margin:6px 0 7px;flex-wrap:wrap;
  font-size:28px;font-weight:650;color:${C.tx};line-height:1.05}
.dhbig small{font-size:13px;font-weight:400;color:${C.tx2}}
.dhfoot{color:${C.tx3};font-size:11.5px;line-height:1.45}
.dhfoot b{color:${C.tx2};font-weight:600}
.wsrc{font-size:10px;padding:1px 5px;border-radius:6px;background:var(--c-line);color:var(--c-tx2);margin-left:5px}
.wsrc.lit{font-style:italic;opacity:.75}
.durbands{display:flex;flex-wrap:wrap;gap:6px 18px;margin:4px 0 10px}
.durband{display:flex;flex-direction:column;font-size:13px;color:${C.tx1};min-width:150px}
.durband em{font-style:normal;font-size:11px;color:${C.tx3}}
.durband .mut{font-size:11px;color:${C.tx3}}
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
  .arow>*:nth-child(4),.arow>*:nth-child(6),.arow>*:nth-child(7),.arow>*:nth-child(8),.arow>*:nth-child(9),.arow>*:nth-child(10){display:none}
}`;
  }
}

if (!customElements.get("intervals-icu-panel")) {
  customElements.define("intervals-icu-panel", IntervalsIcuPanel);
}
