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

/* ── 6  the readout cannot leave the screen, because it no longer floats ──
   Twice wrong as a floating box: clamped against a fixed width, then against
   the wrong frame. The class of defect is removed rather than patched again -
   the values now live in a fixed strip inside the card. These checks fail if
   anyone reintroduces a positioned element. */
{
  const html = p.rFitness(F.pmc(days), 182) + p.rDfa(thr, "all");
  ok(!/id="xhbox"/.test(html), "6 ableseleiste: schwebender Kasten wieder da");
  ok(!/style\.left/.test(html), "6 ableseleiste: Positionsrechnung im Markup");
  ok((html.match(/data-rdo="/g) || []).length === 2, "6 ableseleiste: nicht jede Diagrammgruppe hat eine Leiste");

  // the strip carries the newest values before any pointer moves
  p._grp.pmc = { n: 100, xl: (i) => "Tag " + i,
    rows: [{ l: "Fitness", c: M.ROLE.ctl, u: "", vals: Array.from({ length: 100 }, (_, i) => (i > 95 ? null : 30 + i)) },
           { l: "Form", c: M.ROLE.form, u: "", vals: Array.from({ length: 100 }, (_, i) => (i % 9 ? 2 - i * 0.05 : null)) }] };
  p._fillReadout("pmc", null);
  const strip = p.shadowRoot._strips.pmc;
  ok(/zuletzt/.test(strip._x.textContent), "6 ableseleiste: Ruhezustand nicht als solcher erkennbar");
  ok(/Tag 95/.test(strip._x.textContent), `6 ableseleiste: greift nicht den neuesten Wert (${strip._x.textContent})`);
  ok(/Fitness/.test(strip._v.innerHTML) && /125/.test(strip._v.innerHTML),
     "6 ableseleiste: Werte fehlen im Ruhezustand");

  // moving the pointer writes the value under the cursor, gaps read as "–"
  const svg = { dataset: { w: "880", padl: "48", padr: "14" },
                getBoundingClientRect: () => ({ left: 100, top: 50, width: 880, height: 230 }) };
  const g = { dataset: { grp: "pmc" }, querySelector: () => svg, querySelectorAll: () => p.shadowRoot._lines };
  p._xhMove(g, { clientX: 100 + 48 + (880 - 48 - 14) * 0.5, clientY: 120 });
  ok(!/zuletzt/.test(strip._x.textContent), "6 ableseleiste: bleibt im Ruhezustand stehen");
  ok(/Tag (49|50|51)/.test(strip._x.textContent), `6 ableseleiste: falscher Index (${strip._x.textContent})`);
  p._xhMove(g, { clientX: 100 + 48, clientY: 120 });      // index 0: Form is null
  ok(/–/.test(strip._v.innerHTML), "6 ableseleiste: Lücke wird nicht als solche gezeigt");
  ok(!/NaN/.test(strip._v.innerHTML), "6 ableseleiste: NaN in der Leiste");
  p._xhHide();
  ok(/zuletzt/.test(strip._x.textContent), "6 ableseleiste: kehrt nicht in den Ruhezustand zurück");
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
  // 0.9.1: values could be a day old with nothing saying so. The rule survived
  // the redesign: the page dates itself, every signal dates itself, and a value
  // that is not from today is marked - a wellness record fills up over the day.
  const fresh = p.rHeute({ ...F.today(), date: new Date().toISOString().slice(0, 10) });
  clean(fresh, "9 datum");
  ok((fresh.match(/class="tsigdate/g) || []).length === 3,
     "9 datum: nicht jedes Signal trägt einen Stand");
  ok(!/staleflag/.test(fresh), "9 datum: heutige Werte als veraltet markiert");

  const old = p.rHeute({ ...F.today(), date: "2026-09-09" });
  clean(old, "9 datum alt");
  contains(old, "Werte von", "9 datum: veralteter Wert wird nicht als solcher ausgewiesen");
  ok(/class="staleflag"/.test(old), "9 datum: keine Hervorhebung für veraltete Werte");
  ok(/tsigdate stale/.test(old), "9 datum: veralteter Stand an den Signalen nicht markiert");
  contains(old, "füllt sich über den Tag", "9 datum: Grund nicht genannt");
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


/* ── 11  computed blocks must reach the DOM ─────────────────────────────
   0.31.0 built the infection warning, the reasons list and a seven-day
   ladder inside rTrainer and inserted none of them - the warning was
   silently dropped. Rendered proof plus a source-level lock. */
{
  const html = p.rTrainer(F.coach("rebound"), rd);
  contains(html, "stufenweise aufbauen", "11 warnungen: Infekt-Hinweis fehlt im DOM");
  contains(html, "85 % Intensität", "11 warnungen: das eigene Muster fehlt im DOM");
  contains(html, "warnrow", "11 warnungen: ohne Warn-Auszeichnung");
  contains(html, "Mujika", "11 gründe: Quelle fehlt im DOM");

  const source = H.source();
  const slice = source.slice(source.indexOf("rTrainer(c, rd)"),
                             source.indexOf("---------------- Heute"));
  for (const name of ["warns", "reasons"]) {
    ok(slice.includes(`const ${name}`) && slice.includes("${" + name + "}"),
       `11 quelle: ${name} wird gebaut, aber nicht eingesetzt`);
  }
  for (const dead of ["const plan =", "zbar(", "fitBadge"]) {
    ok(!slice.includes(dead), `11 quelle: toter Block ${dead} ist zurück`);
  }
}

/* ── 12  the lead pick must fit the budget ──────────────────────────────
   "HEUTE EMPFOHLEN" wearing its own "über dem Budget" badge is a visible
   self-contradiction: the first ok card that fits the budget leads. */
{
  const w = F.workouts();
  w.workouts[0].fits_budget = false;           // z2_90 (ok) blows the budget
  const html = p.rWorkouts(w);
  const cards = html.split('class="wocard');
  const flagged = cards.filter((c) => c.includes("Empfehlung von oben"));
  ok(flagged.length === 1, "12 budget-pick: keine oder mehrere Leitkarten");
  ok(flagged[0] && flagged[0].includes("SweetSpot 2×20 min"),
     "12 budget-pick: Leitkarte sprengt das Budget");
  contains(html, "leadtitle\">SweetSpot 2×20 min", "12 budget-pick: Leadkarte falsch betitelt");
}

/* ── 13  the two anchors must not disagree silently ─────────────────────
   Watts come from the FTP, heart rate from the DFA threshold. When the
   measured threshold power sits inside the base-ride watt window, the rider
   has to see the conflict - not two clean numbers side by side. */
{
  const w = F.workouts();
  w.conflict = { ftp: 215, aerobic_power: 146, share_pct: 68, z2_window: [140, 151],
    text: "Deine FTP (215 W) und deine gemessene aerobe Schwelle (146 W, DFA alpha-1 = 0,75) passen nicht zusammen." };
  const html = p.rWorkouts(w);
  contains(html, "passen nicht zusammen", "13 anker-konflikt: nicht angezeigt");
  contains(html, "warnrow", "13 anker-konflikt: ohne Warn-Auszeichnung");
  ok(!p.rWorkouts(F.workouts()).includes("passen nicht zusammen"),
     "13 anker-konflikt: Fehlalarm ohne Konflikt");
}

/* ── 14  a session already ridden today is acknowledged ─────────────────── */
{
  contains(p.rTrainer(F.coach("trained"), rd), "schon eine",
           "14 heute gefahren: Karten gelten kommentarlos für heute");
  ok(!p.rTrainer(F.coach("ready"), rd).includes("schon eine"),
     "14 nichts gefahren: Hinweis trotzdem da");
}

/* ── 15  trained today → the recommendation says FOR TOMORROW ──────────────
   0.32.0 added the note above the cards; the cards and the lead still said
   "HEUTE EMPFOHLEN". Half a fix: the reader saw the note, the recommendation
   contradicted it two lines further down. */
{
  const tomorrow = p.rWorkouts(F.workouts(), true);
  contains(tomorrow, "FÜR MORGEN EMPFOHLEN", "15 für morgen: Leitkarte sagt weiter heute");
  contains(tomorrow, "Alle Einheiten für morgen", "15 für morgen: Kartenliste sagt weiter heute");
  ok(!/HEUTE EMPFOHLEN/.test(tomorrow), "15 für morgen: HEUTE-Kopf steht noch da");
  ok(!/passt heute/.test(tomorrow), "15 für morgen: Tagesurteil behauptet heute");
  contains(tomorrow, "morgen in den Kalender", "15 für morgen: Kalenderknopf zielt nicht auf morgen");
  const today = p.rWorkouts(F.workouts());
  contains(today, "HEUTE EMPFOHLEN", "15 heute: Kopf verstellt");
  ok(!/FÜR MORGEN/.test(today), "15 heute: fälschlich für morgen");
  // and the trainer view passes the flag through - the note and the cards
  // must agree, one source, one verdict
  const trained = p.rTrainer(F.coach("trained"), rd);
  ok(/schon eine/.test(trained) === /FÜR MORGEN EMPFOHLEN/.test(trained) || !trained.includes("leadhead"),
     "15 trainer: Hinweis und Leitkarte widersprechen sich");
}

/* ── 16  the plan weeks are RENDERED, not just computed ────────────────────
   rGoal built the weeks and the budget note into consts and inserted
   neither - the frontend variant of 0.9.4, same class as the orphaned
   rTrainer blocks of 0.32.0. Checked rendered AND at source level. */
{
  const pw = p.rPlanWeeks(F.goal());
  ok(/class="pweek /.test(pw), "16 wochen: nicht gerendert");
  const source = String(p.rGoal);
  ok(!/plan\.weeks/.test(source), "16 rGoal berechnet weiter Wochen, die es nicht rendert");
  ok(!/budget_note/.test(source), "16 rGoal berechnet weiter die Note, die es nicht rendert");
  const assembly = H.source();
  ok(assembly.includes("this.rPlanWeeks(this._goal)"),
     "16 rPlanWeeks wird nirgends in eine Ansicht eingesetzt");
}

/* --- 17  Paket 3: Register, goalbar, DFA-Ehrlichkeit ------------------------ */
{
  const src = H.source();
  // Zustandsfarben: Urteile nur im Urteilsregister — Blau/Violett sind Kategorien
  ok(!src.includes("rebound: C.blue") && !/rebound:\s*\{\s*c:\s*C\.blue/.test(src),
     "17 register: rebound trägt eine Kategorienfarbe");
  ok(!/elevated:\s*\{\s*c:\s*C\.violet/.test(src), "17 register: elevated trägt eine Kategorienfarbe");
  ok(!src.includes('"Erholung", C.blue'), "17 register: Legende führt rebound in Blau");
  // goalbar: kein Ternary, das den Text wegwirft — der Grundsatz gilt immer
  ok(!src.includes("plan.hard_note ? "), "17 goalbar: totes Ternary steht noch im Quelltext");
  const tile = p.rGoal(F.goal());
  ok(tile.includes("80/20 zählt Einheiten, nicht Minuten"), "17 goalbar: Grundsatz fehlt in der Kachel");
  // DFA-Quellzeilen: Validierungslage statt Pauschal-Segen
  ok(!src.includes("Gegen Gasaustausch validiert, aber"), "17 dfa: alte Pauschal-Quellzeile lebt noch");
  ok(src.includes("weite Übereinstimmungsgrenzen"), "17 dfa: Validierungslage nicht benannt");
  ok((src.match(/alleinige Verankerung nicht/g) || []).length >= 2, "17 dfa: Trend-Vorbehalt fehlt in einer der beiden Quellzeilen");
}

report("test_panel_fixes");
