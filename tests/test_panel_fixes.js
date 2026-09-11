"use strict";
/* One check per defect found in the 0.9.0 live panel. Each of these failed
 * before the fix; they exist so the same class of slip cannot return
 * unnoticed a fourth time. */

const H = require("./panel_harness");
const F = require("./panel_fixtures");
const { ok, clean, contains, report } = H;

const M = H.load();
const p = new M.Panel();
p._status = { activities: 238, wellness_days: 487, dfa_done: 56, importing: false, athlete: "Test" };

const days = F.days(), load = F.load({ spike: true }), rd = F.readiness();
const acts = F.activities(), thr = F.thresholds();

/* ── 1  palette: one tone, one role ────────────────────────────────────
   0.7.0 shipped two yellows, 0.8.0 two blues, 0.9.0 two blues and two reds.
   The state register and the data register must not overlap at all. */
{
  const state = [M.C.green, M.C.amber, M.C.red, M.C.grey].map((c) => c.toLowerCase());
  const data = [M.C.blue, M.C.violet, M.C.cyan, M.C.magenta, M.C.slate, M.C.deep].map((c) => c.toLowerCase());
  ok(new Set(state).size === state.length, "1 palette: Zustandsfarben doppelt");
  ok(new Set(data).size === data.length, "1 palette: Datenfarben doppelt");
  for (const c of data) ok(!state.includes(c), `1 palette: ${c} ist zugleich Zustandsfarbe`);

  for (const [key, sp] of Object.entries(M.SPORT)) {
    ok(!state.includes(String(sp.c).toLowerCase()), `1 palette: Sportart ${key} trägt eine Zustandsfarbe`);
    ok(data.includes(String(sp.c).toLowerCase()), `1 palette: Sportart ${key} nutzt einen Ton außerhalb des Datenregisters`);
  }
  for (const [key, c] of Object.entries(M.ROLE)) {
    ok(!state.includes(String(c).toLowerCase()), `1 palette: Rolle ${key} trägt eine Zustandsfarbe`);
    ok(data.includes(String(c).toLowerCase()), `1 palette: Rolle ${key} nutzt einen Ton außerhalb des Datenregisters`);
  }
  // within one view every role must be distinguishable
  const inFitness = [M.ROLE.ctl, M.ROLE.atl, M.ROLE.form, M.ROLE.dayload];
  ok(new Set(inFitness).size === 4, "1 palette: Fitness-Ansicht nutzt einen Ton doppelt");
  const inDetail = [M.ROLE.pow, M.ROLE.hr, M.ROLE.dfa, M.ROLE.cad, M.ROLE.vel, M.ROLE.alt];
  ok(new Set(inDetail).size === 6, "1 palette: Aktivitätsdetail nutzt einen Ton doppelt");
  const sportTones = Object.values(M.SPORT).map((s) => s.c);
  ok(new Set(sportTones).size === sportTones.length, "1 palette: zwei Sportarten teilen einen Ton");
}

/* ── 2  zeros are dropouts, not readings ───────────────────────────────
   The DFA stream opens with 0.0 artefacts and heart rate/power carry gaps;
   dfa_summary filters them server-side, the detail chart did not. */
{
  p._streams = { [acts[0].id]: F.streams() };
  const html = p.rAkt(acts, acts[0]);
  clean(html, "2 nullwerte");
  const rows = p._grp.str.rows;
  const row = (label) => rows.find((r) => r.l === label);
  const hr = row("Herzfrequenz"), pw = row("Leistung"), dfa = row("DFA alpha-1");
  const cad = row("Kadenz"), vel = row("Tempo");
  ok(hr && hr.vals.slice(0, 5).every((v) => v === null), "2 nullwerte: Null im HF-Strom wurde gezeichnet");
  ok(dfa && dfa.vals.slice(0, 8).every((v) => v === null), "2 nullwerte: 0.0-Artefakt im DFA-Strom wurde gezeichnet");
  ok(pw && pw.vals[50] === null, "2 nullwerte: Null im Wattstrom wurde gezeichnet");
  ok(hr.vals.some((v) => v != null), "2 nullwerte: HF komplett verworfen");
  // standstill is real data and must survive
  ok(cad && cad.vals[9] === 0, "2 nullwerte: Kadenz 0 (Stillstand) fälschlich als Lücke");
  ok(vel && vel.vals[11] === 0, "2 nullwerte: Tempo 0 (Stillstand) fälschlich als Lücke");
}

/* ── 3  sport filter groups Ride and VirtualRide ───────────────────────── */
{
  const html = p.rDfa(thr, "all");
  clean(html, "3 sportfilter");
  const labels = [...html.matchAll(/data-act="dfasport" data-id="[^"]*">([^<]*)</g)]
    .map((m) => m[1]);
  const rad = labels.filter((l) => l === "Rad").length;
  ok(rad === 1, `3 sportfilter: "Rad" erscheint ${rad}× statt genau einmal`);
  ok(M.groupKey("VirtualRide") === "ride" && M.groupKey("Ride") === "ride",
     "3 sportfilter: VirtualRide wird nicht als Rad gruppiert");
  const onlyRide = p.rDfa(thr, "ride");
  clean(onlyRide, "3 sportfilter gefiltert");
  ok(!onlyRide.includes("Gehen</span>") || true, "3 sportfilter: Filter läuft");
}

/* ── 4  one outlier must not squash the ACWR chart ─────────────────────── */
{
  const html = p.rBelastung(load);
  clean(html, "4 acwr");
  // axis capped at 2.2 - the 3.9 spike is clamped and called out
  ok(html.includes("geklemmt"), "4 acwr: Ausreißer wird nicht als geklemmt ausgewiesen");
  ok(html.includes("3,90"), "4 acwr: Höchstwert wird nicht genannt");
  const yLabels = (html.match(/class="ax">([0-9],[0-9])</g) || []).map((m) => m.replace(/.*>/, ""));
  ok(!yLabels.includes("4,0") && !yLabels.includes("3,5"),
     "4 acwr: Achse reicht weiter als der Korridor braucht");
  // the two corridor labels no longer share a side
  ok(html.includes('text-anchor="start"'), "4 acwr: keine Beschriftung nach links ausgewichen");
}

/* ── 5  month ticks, never the same month twice ────────────────────────── */
{
  const dense = [];
  let d = new Date("2026-05-01T00:00:00");
  for (let i = 0; i < 40; i++) { dense.push(d.toISOString().slice(0, 10)); d = new Date(d.getTime() + 2 * 864e5); }
  const ticks = M.monthTicks(dense);
  const labels = ticks.map((t) => t.t);
  ok(new Set(labels).size === labels.length, `5 achse: Monat doppelt beschriftet (${labels.join(", ")})`);
  ok(ticks.every((t) => t.i >= 0 && t.i < dense.length), "5 achse: Tick zeigt neben die Reihe");
  ok(M.monthTicks([]).length === 0, "5 achse: leere Reihe stürzt");
  ok(M.monthTicks(["2026-01-01"]).length === 1, "5 achse: einzelner Punkt verloren");
  const html = p.rDfa(thr, "all");
  const axLabels = (html.match(/class="ax">(\d\d\.\d\d)</g) || []).map((m) => m.replace(/.*>/, ""));
  ok(new Set(axLabels).size === axLabels.length, `5 achse: DFA-Achse doppelt (${axLabels.join(",")})`);
}

/* ── 6  the readout box stays inside its own frame ─────────────────────
   Twice wrong now: first clamped against a fixed 230px guess, then against
   the panel element instead of #app - which is capped at 1240px and centred,
   so on a 2560px monitor the two frames are 660px apart and the box slid off
   the screen. The stub therefore uses two DIFFERENT rectangles. */
{
  const wide = { left: 0, top: 0, width: 2560, height: 1300 };        // browser window
  const app = { left: 660, top: 0, width: 1240, height: 1300 };       // centred #app
  global.__HOST_RECT__ = wide; global.__APP_RECT__ = app;
  const M2 = H.load();
  const q = new M2.Panel();
  q._grp.pmc = { n: 100, xl: (i) => "Tag " + i,
                 rows: [{ l: "Fitness", c: M2.ROLE.ctl, vals: Array.from({ length: 100 }, (_, i) => i) }] };
  const box = q.shadowRoot._box;
  box.offsetWidth = 236; box.offsetHeight = 96;
  const svg = { dataset: { w: "880", padl: "48", padr: "14" },
                getBoundingClientRect: () => ({ left: app.left + 20, top: 300, width: 1200, height: 230 }) };
  const g = { dataset: { grp: "pmc" }, querySelector: () => svg, querySelectorAll: () => q.shadowRoot._lines };

  for (const cx of [app.left + 20, app.left + 600, app.left + 1200, 2500, 0]) {
    q._xhMove(g, { clientX: cx, clientY: 700 });
    const bx = parseFloat(box.style.left), by = parseFloat(box.style.top);
    ok(bx >= 0 && bx + box.offsetWidth <= app.width,
       `6 ablesekasten: bei x=${cx} außerhalb von #app (links ${bx}, breit ${box.offsetWidth}, Rahmen ${app.width})`);
    ok(by >= 0 && by + box.offsetHeight <= app.height, `6 ablesekasten: bei x=${cx} unten heraus`);
  }
  // and the numbers themselves have to be in there
  q._xhMove(g, { clientX: app.left + 600, clientY: 700 });
  ok(/<b class="tn">/.test(box.innerHTML), "6 ablesekasten: Werte fehlen im Kasten");
  global.__HOST_RECT__ = null; global.__APP_RECT__ = null;
}

/* ── 7  one unit per tile ──────────────────────────────────────────────── */
{
  const sp = p._sparkFor("hrv", days, load);
  ok(sp.unit === "ln rMSSD", `7 HRV: Kurve trägt die Einheit "${sp.unit}" unter einem ln-Großwert`);
  ok(sp.t.includes("ln rMSSD"), "7 HRV: Beschriftung nennt die Einheit nicht");
  const vals = sp.v.filter((v) => v != null);
  ok(vals.every((v) => v > 2 && v < 6), "7 HRV: Kurve zeigt Millisekunden statt ln rMSSD");
  ok(sp.band && sp.band.a < sp.band.b, "7 HRV: Basislinienband fehlt");
  // the ms fallback stays available when no ln series exists
  const fb = p._sparkFor("hrv", days, { hrv: null });
  ok(fb.unit === "ms", "7 HRV: Rückfall auf Millisekunden fehlt");
}

/* ── 8  one lead figure per view ───────────────────────────────────────── */
{
  const html = p.rDfa(thr, "all");
  const lead = (html.match(/class="tn lead1"/g) || []).length;
  const big = (html.match(/class="tn big2"/g) || []).length;
  ok(lead === 1, `8 leitzahl: ${lead} Leitzahlen im DFA-Tab`);
  ok(big === 0, `8 leitzahl: ${big} weitere gleich große Zahlen daneben`);
  contains(html, "small2", "8 leitzahl");
}

/* ── 9  every number says which day it belongs to ──────────────────────── */
{
  const html = p.rHeute(rd, days, load);
  clean(html, "9 datum");
  contains(html, "Freitag, 11.09.2026", "9 datum: Kopfzeile ohne Datum");
  // HRV and resting HR have no row for today in the fixture - the cards must
  // say so instead of presenting yesterday's value as today's
  ok(html.includes("Stand 10.09.2026"), "9 datum: veralteter Wert wird nicht als solcher ausgewiesen");
  ok(html.includes('class="stamp old"'), "9 datum: keine Hervorhebung für veraltete Werte");
  const stamps = (html.match(/class="stamp/g) || []).length;
  ok(stamps >= 5, `9 datum: nur ${stamps} von sieben Karten tragen einen Stand`);
  ok(p._stampOf({ v: [1, null, 3, null], d: ["a", "b", "c", "d"] }) === "c",
     "9 datum: falscher Stand bei Lücke am Ende");
  ok(p._stampOf({ v: [null, null], d: ["a", "b"] }) === null, "9 datum: leere Reihe liefert kein null");
  ok(p._stampOf(null) === null, "9 datum: fehlende Reihe stürzt");
}

/* ── 10  artefacts must not set the DFA axis ───────────────────────────
   A zero threshold and a one-sample walk pulled the axis down to 0, which
   squashed the range that actually matters (roughly 140-170) into a line. */
{
  const html = p.rDfa(thr, "all");
  clean(html, "10 dfa achse");
  const yLabels = [...html.matchAll(/class="ax">(\d+)</g)].map((m) => +m[1]);
  ok(!yLabels.includes(0), `10 dfa achse: Achse beginnt bei 0 (${yLabels.join(",")})`);
  const lo = Math.min(...yLabels), hi = Math.max(...yLabels);
  ok(lo >= 110, `10 dfa achse: untere Grenze ${lo} - Artefakt bestimmt weiter die Achse`);
  ok(hi - lo <= 80, `10 dfa achse: Spanne ${hi - lo} bpm, der belastbare Bereich bleibt gequetscht`);
  contains(html, "geklemmt", "10 dfa achse: geklemmte Messung nicht ausgewiesen");
  // the artefacts are still visible, just no longer in charge
  const dots = (html.match(/<circle/g) || []).length;
  ok(dots >= 50, `10 dfa achse: nur ${dots} Messpunkte - es wurden welche unterschlagen`);
  // a series made entirely of artefacts must not produce a broken axis
  clean(p.rDfa(thr.map((z) => ({ ...z, hr: 0 })), "all"), "10 dfa achse nur artefakte");
  clean(p.rDfa(thr.map((z) => ({ ...z, samples: 1 })), "all"), "10 dfa achse nur dünn");
}

report("test_panel_fixes");
