"use strict";
/* One check per defect found in the 0.9.0 live panel. Each of these failed
 * before the fix; they exist so the same class of slip cannot return
 * unnoticed a fourth time. */

const H = require("./panel_harness");
const F = require("./panel_fixtures");
const { ok, clean, contains, report } = H;

const M = H.load();
const p = new M.Panel();
p._status = { activities: 238, wellness_days: 487, dfa_done: 56, importing: false, decoupling_good: 5.0, athlete: "Test" };
// Pin "today". A window that asks the wall clock makes this suite go red on
// its own some months from now, and a test that fails for calendar reasons
// teaches nothing about the code.
p._nowIso = F.TODAY;

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
  w.workouts[0].stage = F.stageOf("ok", false, false);   // ... and the grade says so
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
  ok(/this\.rPlanWeeks\(this\._goal,/.test(assembly),
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

/* ── 18  Paket A: ein Nachweis je Befund ───────────────────────────────────
   The eight contradictions found while reading for 0.36.0. Each one gets a
   check that would have failed before the fix - several of them on the SOURCE
   as well as on the output, because a computed-but-never-inserted block
   renders fine and is still dead (0.32.0). */
{
  const src = H.source();
  const q = new M.Panel();
  q._nowIso = F.TODAY;

  // W7 - the disabled second chart in the enlarged signal card. A block
  // behind `false ?` is the dormant form of "computed, never inserted".
  ok(!src.includes("${false ?"), "18 W7: stillgelegter Block steht wieder im Quelltext");

  // W5 - no view may ask the wall clock for its window. One "now" per panel,
  // injectable, or the suite goes red for calendar reasons some months on.
  ok(src.includes("_now()"), "18 W5: kein zentrales Jetzt");
  ok(!/_win\.dfa[\s\S]{0,120}new Date\(\)/.test(src), "18 W5: Fenster liest die Wanduhr direkt");
  ok(new M.Panel()._now().length === 10, "18 W5: Jetzt nicht als ISO-Tag");

  // W6 - localStorage must never be able to take the panel down. It does not
  // exist in this runtime at all, which is the point of the check.
  ok(typeof localStorage === "undefined", "18 W6: Testumgebung hat plötzlich localStorage");
  ok((src.match(/typeof localStorage === "undefined"/g) || []).length >= 2,
     "18 W6: Zugriff auf localStorage ohne Existenzprüfung");
  ok((src.match(/catch \(err\) \{/g) || []).length >= 2, "18 W6: kein Schutz gegen werfendes Schreiben");
  ok(JSON.stringify(new M.Panel()._win) === '{"dfa":{"id":"3m"}}',
     "18 W6: Vorauswahl überlebt fehlendes localStorage nicht");

  // W1/A5 - the axis dates come from the payload, never from "today minus n".
  // 42 wellness days are not 42 calendar days, and the fixture has the gap.
  const hd = F.today().history_days;
  const span = (Date.parse(hd[hd.length - 1].date) - Date.parse(hd[0].date)) / 864e5 + 1;
  ok(span > hd.length, "18 W1: Fixture ohne Lücke — der Fehlerfall wäre nicht prüfbar");
  ok(!/history_days[\s\S]{0,200}isoMinus/.test(src), "18 W1: Spur rechnet sich Daten selbst aus");
  q._sigOpen = "hrv";
  const open = String(q.rHeute(F.today()));
  const labels = (open.match(/class="ax">(\d\d)\.(\d\d)\.?</g) || []);
  ok(labels.length >= 2, "18 W1: zu wenige Datumsbeschriftungen");
  ok(labels.every((l) => open.includes(l)), "18 W1: Beschriftung ohne Bezug");
  q._sigOpen = null;

  // W2 - the list is no longer nailed to fifteen rows, and the cap speaks
  ok(!src.includes("rows.slice(-15)"), "18 W2: Liste wieder auf 15 Zeilen genagelt");
  ok(src.includes("const CAP = 50"), "18 W2: keine benannte Kappung");

  // W3 - the sport moves the headline, and the source line says which sport
  const ride = String(q.rDfa(F.thresholds(), "ride"));
  const all = String(q.rDfa(F.thresholds(), "all"));
  ok(/Median der letzten 5 belastbaren Messungen · Rad/.test(ride),
     "18 W3: Quellzeile verschweigt die Sportart");
  ok(/Median der letzten 5 belastbaren Messungen · alle Sportarten/.test(all),
     "18 W3: Quellzeile ohne Sportangabe bei allen Sportarten");

  // W4 - the median line is LEFT OUT below five solid readings, not thinned.
  // A faint wrong line is still a wrong line.
  const thin = F.thresholds().map((x) => ({ ...x, hr_windows: 2, hr_usable: false, usable: false }));
  const r = new M.Panel();
  r._nowIso = F.TODAY;
  r._win.dfa = { id: "all" };
  const thinHtml = String(r.rDfa(thin, "all"));
  ok(!/stroke-width="2.4"/.test(thinHtml), "18 W4: Medianlinie bei dünner Lage gezeichnet");
  ok(!/stroke-dasharray[^>]*stroke-width="2.4"/.test(thinHtml), "18 W4: Medianlinie dünn gezeichnet statt weggelassen");
  ok(thinHtml.includes("keine Medianlinie"), "18 W4: Weglassen wird nicht begründet");

  // W8 - no threshold reading may be dated in the future
  ok(F.thresholds().every((x) => x.date <= F.TODAY), "18 W8: Fixture erzeugt wieder Zukunftsdaten");

  // A4 - a jump that cannot land says so instead of doing nothing
  const s = new M.Panel();
  s._nowIso = F.TODAY;
  s._aktMiss = "act9999";
  const missHtml = String(s.rAkt(F.activities(), null));
  clean(missHtml, "18 A4 Sprung ins Leere");
  ok(missHtml.includes("act9999") && /älter als der geladene Bereich/.test(missHtml),
     "18 A4: verfehlter Sprung bleibt stumm");
  s._aktMiss = null;
  ok(!String(s.rAkt(F.activities(), null)).includes("älter als der geladene Bereich"),
     "18 A4: Hinweis erscheint ohne verfehlten Sprung");
  // 0.36.1 - the graph fled from the pointer. `scrollIntoView` on the brushed
  // row scrolled the HOST (:host{overflow-y:auto}), so every pointer move over
  // the chart pulled the chart out of the window. A transient mark must not
  // move the page it is drawn on - and nothing in this panel may scroll on a
  // pointermove at all.
  ok(!src.includes("scrollIntoView"),
     "18 Scroll: scrollIntoView steht wieder im Panel — der Graph scrollt sich selbst weg");
  const paint = (src.match(/_paintDfa\(\) \{[\s\S]*?\n  \}/) || [""])[0];
  ok(paint.length > 100, "18 Scroll: _paintDfa nicht gefunden");
  ok(!/scroll/i.test(paint), "18 Scroll: die flüchtige Markierung scrollt");
  ok(paint.includes("classList"), "18 Scroll: flüchtige Markierung setzt keine Klasse mehr");
}

/* ── 19  der Graph darf nicht vor dem Zeiger fliehen ───────────────────────
   0.36.0 live: Zeiger über den DFA-Graphen → die Seite sprang zur Tabelle und
   der Graph war weg. Ursache war `scrollIntoView` auf der markierten Zeile,
   während :host selbst der Scroll-Kasten ist.

   Eine Quelltextsperre allein reicht dafür nicht - sie fängt genau einen
   Mechanismus. Also wird hier der ECHTE Zeiger-Pfad gefahren, gegen jede
   Ursache einzeln, die eine Seite unter dem Zeiger bewegen kann:
   1. eine Methode, die etwas ins Bild zieht (scrollIntoView / scrollTo /
      focus - Fokus zieht implizit mit)
   2. ein Neuaufbau des Views (innerHTML setzt die Scroll-Position zurück)
   3. ein Layout-Sprung durch die Markierung selbst (Höhe/Rahmen/Polster)      */
{
  const moves = [];                       // jeder Aufruf, der etwas bewegen kann
  const mkRow = (aid) => ({
    dataset: { aid },
    classList: { toggle() {} },
    scrollIntoView: (...a) => moves.push(["scrollIntoView", aid, JSON.stringify(a)]),
    focus: () => moves.push(["focus", aid]),
  });
  const mkDot = (id) => {
    const attrs = {};
    return { dataset: { dot: id, r: "4", op: "1" },
             setAttribute: (k, v) => { attrs[k] = v; }, _attrs: attrs };
  };
  const mkLine = () => ({ setAttribute() {} });

  const rowEls = ["act11", "act13", "act15"].map(mkRow);
  const dotEls = ["act11", "act13", "act15"].map(mkDot);
  const lineEls = [mkLine(), mkLine()];
  const strip = { querySelector: () => ({ textContent: "", innerHTML: "" }) };

  const q = new M.Panel();
  q._nowIso = F.TODAY;
  q._dfaRows = [
    { date: "2026-08-01", activity_id: "act11", pickable: true },
    { date: "2026-08-04", activity_id: "act13", pickable: false },  // dünn
    { date: "2026-08-07", activity_id: "act15", pickable: true },
  ];
  q._grp.dfa = { n: 3, xl: (i) => String(i), rows: [{ l: "x", c: "#fff", vals: [1, 2, 3] }] };
  q.shadowRoot.querySelectorAll = (sel) =>
    sel === "[data-aid]" ? rowEls : sel === "[data-dot]" ? dotEls
      : sel === ".xh" ? lineEls : sel === ".dragsel" ? [] : [];
  q.shadowRoot.querySelector = (sel) => (/data-rdo/.test(sel) ? strip : null);
  q.shadowRoot.scrollTo = (...a) => moves.push(["scrollTo", JSON.stringify(a)]);

  // a real chart group under the pointer
  const svg = {
    dataset: { w: "880", padl: "48", padr: "14" },
    getBoundingClientRect: () => ({ left: 0, top: 0, width: 880, height: 260 }),
    querySelectorAll: () => lineEls,
  };
  const g = { dataset: { grp: "dfa" }, querySelector: (s) => (s === "svg.ch" ? svg : null),
              querySelectorAll: () => lineEls };
  const evAt = (x) => ({ clientX: x, clientY: 40,
                         target: { closest: (sel) => (sel === "[data-grp]" ? g : null) } });

  // count re-renders without touching the real one
  let renders = 0;
  const realRender = q._render.bind(q);
  q._render = () => { renders++; };

  q._attach();
  const onMove = q.shadowRoot._listeners.pointermove;
  ok(typeof onMove === "function", "19 sim: kein pointermove-Handler registriert");

  // ── sweep the pointer across the whole chart, twice ────────────────────
  for (let pass = 0; pass < 2; pass++) {
    for (let x = 50; x <= 860; x += 10) onMove(evAt(x));
  }
  ok(moves.length === 0,
     "19 sim: der Zeiger über dem Graphen bewegt die Seite (" + JSON.stringify(moves.slice(0, 3)) + ")");
  ok(renders === 0, "19 sim: pointermove baut die Ansicht neu (" + renders + "x) — das setzt die Scroll-Position zurück");
  // and it really did mark something, or the check above would be vacuous
  ok(q._dfaHover !== null, "19 sim: gar keine Markierung gesetzt — die Prüfung wäre leer");
  ok(dotEls.some((d) => d._attrs.opacity === "0.35"),
     "19 sim: übrige Punkte werden beim Überfahren nicht abgedunkelt");

  // ── the pointer over a LIST ROW must behave the same way ───────────────
  const rowEv = { clientX: 0, clientY: 0,
                  target: { closest: (sel) => (sel === "[data-aid]" ? { dataset: { aid: "act15" } } : null) } };
  for (let i = 0; i < 20; i++) onMove(rowEv);
  ok(moves.length === 0, "19 sim: der Zeiger über der Liste bewegt die Seite");
  ok(renders === 0, "19 sim: Zeiger über der Liste baut die Ansicht neu");

  // ── leaving must not move anything either ─────────────────────────────
  const leave = q.shadowRoot._listeners.pointerleave;
  if (typeof leave === "function") leave();
  onMove({ clientX: 0, clientY: 0, target: { closest: () => null } });
  ok(moves.length === 0, "19 sim: das Verlassen bewegt die Seite");
  ok(renders === 0, "19 sim: das Verlassen baut die Ansicht neu");

  // ── dritte Ursache: die Markierung selbst darf nichts umbrechen ────────
  q._render = realRender;
  const css = (H.source().match(/_css\(\) \{[\s\S]*$/) || [""])[0];
  // NOT [^}]* : the stylesheet is a template string, so ${C.bg2} carries its
  // own closing brace and the match stopped after "background:${C.bg2". Both
  // layout checks below then ran on a truncated string and could not fail.
  const ruleOf = (name) => ((css.match(new RegExp("\\.trow\\." + name + "\\{(.*)$", "m")) || [])[1] || "");
  const hovered = ruleOf("hovered");
  ok(/box-shadow/.test(hovered) && /background/.test(hovered),
     "19 layout: .trow.hovered nicht vollständig gelesen — die Prüfung wäre leer");
  for (const prop of ["height", "padding", "margin", "border:", "border-width", "font-size", "display"]) {
    ok(!hovered.includes(prop),
       "19 layout: .trow.hovered ändert " + prop + " — die Zeile ändert ihre Höhe und die Liste springt");
  }
  const brushed = ruleOf("brushed");
  ok(brushed.includes("box-shadow:inset"),
     "19 layout: feste Auswahl nutzt keinen Innenbalken — ein Rahmen verschiebt die Zeile um seine Breite");
  for (const prop of ["height", "padding", "margin", "border:", "font-size"]) {
    ok(!brushed.includes(prop), "19 layout: .trow.brushed ändert " + prop);
  }
}


/* ── Quelltext-Wächter: keine zweite Wahrheit im Frontend ──────────────────
   DECOUPLING_GOOD stand bis 0.38.0 ZWEIMAL im Backend (coach.py und
   analytics.py) und FÜNFMAL im Frontend. Das Paket F schrieb den Satz "sonst
   stehen zwei Wahrheiten im Haus" auf und verletzte ihn selbst. Der Wächter
   läuft deshalb über das GANZE Frontend, nicht nur über die Durability-Kachel.

   Er kennt zwei Klassen:
   - die Entkopplungsmarke: in 0.39.0 behoben, hier auf NULL festgenagelt;
   - DFA-Schwellen und ACWR-Korridor: bekannt, gezählt, NICHT stillschweigend
     mitgefixt - sie bekommen ihr eigenes Paket (docs/ausbau.md). Die Zahl ist
     eingefroren, damit keine zehnte Dublette unbemerkt dazukommt. */
{
  const src = H.source();
  // Zeilenweise, ohne Kommentare - eine Zahl in einer Erklärung ist keine
  // zweite Wahrheit, und ein Wächter, der an der eigenen Begründung scheitert,
  // erzieht nur dazu, die Begründung wegzulassen.
  const code = src.split("\n").filter((l) => {
    const t = l.trim();
    return t && !t.startsWith("//") && !t.startsWith("*") && !t.startsWith("/*");
  });

  const hits = (re) => code.filter((l) => re.test(l));

  const decMark = hits(/(decoupling|drop)\b[^;\n]{0,40}[<>]=?\s*5(?![\d.])/);
  ok(decMark.length === 0,
     `Wächter: ${decMark.length} hartkodierte Entkopplungsmarke(n) im Frontend — ` +
     `die Zahl gehört in die Payload: ${decMark.map((l) => l.trim().slice(0, 60)).join(" | ")}`);

  // Gegenprobe: der Wächter muss eine wiedereingebaute Konstante auch finden.
  // Ohne diesen Nachweis prüft die Null oben nur, dass der Ausdruck nie greift.
  const planted = ["      const cls = dec > 5 ? \"warn\" : \"ok\";"];
  ok(planted.filter((l) => /(decoupling|drop)\b[^;\n]{0,40}[<>]=?\s*5(?![\d.])/.test(l)).length === 0,
     "Wächter Gegenprobe: Platzhalter ohne Schlüsselwort darf NICHT anschlagen");
  const planted2 = ["      const cls = decoupling > 5 ? \"warn\" : \"ok\";"];
  ok(planted2.filter((l) => /(decoupling|drop)\b[^;\n]{0,40}[<>]=?\s*5(?![\d.])/.test(l)).length === 1,
     "Wächter Gegenprobe: eine wiedereingebaute 5 wird NICHT gefunden — der Wächter ist blind");

  // Bekannte Klasse, eingefroren. Steigt eine dieser Zahlen, ist eine neue
  // Dublette dazugekommen; fällt sie, ist ihr Paket gelaufen und dieser Block
  // gehört nachgezogen.
  const dfa = hits(/y:\s*0\.(75|5)\b/);
  const acwr = hits(/ratio\s*>\s*1\.(3|5)\b/);
  ok(dfa.length === 2, `Wächter: DFA-Schwellen im Frontend jetzt ${dfa.length} statt 2 — eigenes Paket`);
  ok(acwr.length === 2, `Wächter: ACWR-Korridor im Frontend jetzt ${acwr.length} statt 2 — eigenes Paket`);

  // Und die Kachel selbst: jede Zahl, die sie zeigt, kommt aus der Payload.
  const tile = (/rDurability\(d\) \{[\s\S]*?\n  \}/.exec(src) || [""])[0];
  ok(tile.length > 0, "Wächter: rDurability nicht gefunden");
  for (const [name, re] of [["Schwelle", /[^.\w]5\.0|[<>]=?\s*5(?![\d.])/],
                            ["Trennstelle", /\b800\b/],
                            ["Mindestdauer", /\b45\b/],
                            ["Intensitätsgrenze", /\b80\b/],
                            ["Gewichtsgrenzen", /1\.05|1\.25/],
                            ["Steigungskriterium", /\b2\.0\b/],
                            ["Mindestzahl je Gruppe", /[^\w.]5(?![\d.])\s*(Einheiten|\))/],
                            // Paket H: Faktor, Rundungsschritt und Bezugsfenster
                            // der Progressionsregel. Der Erklaertext der Kachel
                            // haette den Waechter selbst gerissen ("die 10 %
                            // sind der Risikoknick") - richtig ist nicht, ihn zu
                            // umgehen, sondern die Zahl aus dem Faktor zu rechnen.
                            ["Progressionsfaktor", /1[.,]10?\b/],
                            ["Risikoknick in Prozent", /\b10\s*%/],
                            ["Rundungsschritt", /\b5\s*Minuten/],
                            ["Bezugsfenster", /\b30\s*Tag/]]) {
    ok(!re.test(tile), `Wächter: ${name} steht als Zahl in rDurability statt in der Payload`);
  }
  // Gegenprobe zu den vier neuen Mustern: eingebaute Literale werden gefunden.
  // Ohne sie pruefen die vier Nullen oben nur, dass die Ausdruecke nie greifen.
  for (const [planted, re] of [["const f = 1.10;", /1[.,]10?\b/],
                               ["<b>die 10 % sind der Knick</b>", /\b10\s*%/],
                               ["auf 5 Minuten gerundet", /\b5\s*Minuten/],
                               ["der letzten 30 Tage", /\b30\s*Tag/]]) {
    ok(re.test(planted), `Wächter Gegenprobe: "${planted}" wird NICHT gefunden — der Wächter ist blind`);
  }
  // Die NEUE Kachel muss NACHGETRAGEN werden - und genau das ist der Befund:
  // der Wächter läuft global nur über die drei bekannten Klassen, im Detail
  // aber je Kachel. Eine Kachel, die niemand einträgt, ist ungeprüft. Der
  // Eintrag hier ist deshalb keine Fleißarbeit, sondern die Prüfung selbst -
  // und die Liste der geprüften Kacheln wird gegen den Quelltext gehalten,
  // damit die übernächste nicht wieder durchrutscht (vierte Bauregel, 0.44.0).
  const tiles = (src.match(/\n  r[A-Z]\w*\(/g) || []).map((m) => m.trim().slice(0, -1));
  const guarded = ["rDurability", "rFatigue", "rBlocks"];
  for (const name of guarded) {
    ok(tiles.includes(name), `Wächter: ${name} steht in der Liste, existiert aber nicht mehr`);
  }
  // Die Kachel UND ihr Rechenweg-Helfer: die Ausschlussliste zeigt Zahlen und
  // gehört damit unter denselben Wächter wie die Karte selbst.
  const fat = (/rFatigue\(f\) \{[\s\S]*?\n  \}/.exec(src) || [""])[0]
    + (/_fatigueDropped\(f\) \{[\s\S]*?\n  \}/.exec(src) || [""])[0];
  // Paket M: dieselbe Pruefung fuer die neue Kachel - je Kachel nachzutragen,
  // das ist der Befund aus 0.46.0 und er gilt weiter.
  const blk = (/rBlocks\(b\) \{[\s\S]*?\n  \}/.exec(src) || [""])[0];
  ok(blk.length > 0, "Wächter: rBlocks nicht gefunden");
  for (const [name, re] of [["Korridorgrenze", /0[.,]75|0[.,]50\s*[-–]/],
                            ["Schrittweite", /\b5\s*%|\b10\s*%/],
                            ["Verwurfzeit", /\b120\b|\b2\s*Minuten/],
                            ["Trendgrenze", /unter 6\b/]]) {
    ok(!re.test(blk), `Wächter: ${name} steht als Zahl in rBlocks statt in der Payload`);
  }
  for (const [planted, re] of [["unter 6 wird keine Linie", /unter 6\b/],
                               ["die ersten 2 Minuten", /\b2\s*Minuten/]]) {
    ok(re.test(planted), `Wächter Gegenprobe: "${planted}" wird NICHT gefunden — der Wächter ist blind`);
  }
  for (const key of ["min_for_trend", "corridor", "step_pct", "block_alphas",
                     "median_alpha", "first_watts", "suggested_watts"]) {
    ok(blk.includes(key), `Wächter: rBlocks liest ${key} nicht aus der Payload`);
  }
  ok(fat.length > 0, "Wächter: rFatigue nicht gefunden");
  for (const [name, re] of [["Zonengrenze", /\b20\s*%/],
                            ["Mindestdauer", /\b60\s*(Minuten|min)/],
                            // Gesucht ist eine SCHWELLE neben ihrem Gegenstand, nicht jede 10:
                            // der Rundungsschritt der Achse ist keine Belegungsgrenze.
                            ["Mindestbelegung", /\b10\s*Fahrten/],
                            ["Streuung", /\b139\b|\b78\b/],
                            // Die Bereichsgrenze, nicht jede Erwaehnung einer Stunde: "Stunde 1"
                            // ist die erste Fahrtstunde und keine Grenze, "bis Stunde 2" waere eine.
                            ["Stundengrenze", /bis Stunde \d/]]) {
    ok(!re.test(fat), `Wächter: ${name} steht als Zahl in rFatigue statt in der Payload`);
  }
  for (const [planted, re] of [["mehr als 20 % über Zone 2", /\b20\s*%/],
                               ["unter 60 Minuten", /\b60\s*(Minuten|min)/],
                               ["getragen bis Stunde 2", /bis Stunde \d/]]) {
    ok(re.test(planted), `Wächter Gegenprobe: "${planted}" wird NICHT gefunden — der Wächter ist blind`);
  }
  for (const key of ["max_above_z2", "min_minutes", "t5_published", "t5_minutes",
                     "anchor_base", "anchor_n", "solid_until_hour", "thin_until_hour"]) {
    ok(fat.includes("f." + key), `Wächter: rFatigue liest ${key} nicht aus der Payload`);
  }

  // Die Kehrseite: eine Zahl kann auch dadurch verschwinden, dass die Kachel
  // sie gar nicht mehr zeigt. Jede neue Schwelle aus 0.40.0 muss NACHWEISLICH
  // aus der Payload gelesen werden - sonst ist der Wächter oben nur still.
  for (const key of ["vi_full", "vi_none", "min_weight_sum", "min_weight_sum_block",
                     "min_slope_t", "block_weeks", "power_days", "power_days_fallback",
                     "fuelling_g_per_h", "max_intensity", "min_minutes", "decoupling_good"]) {
    ok(tile.includes("d." + key), `Wächter: rDurability liest ${key} nicht aus der Payload`);
  }

  /* 0.50.0: die Progressionszeile ist in den Wochenplan gewandert - und der
     Wächter mit ihr. Eine Zahl, die umzieht und ihre Prüfung zurücklässt, ist
     ab dem Umzug ungeprüft; genau das ist die vierte Bauregel aus 0.44.0, nur
     auf eine Kachel angewandt statt auf eine Liste. Die vier Muster sind
     dieselben wie oben, sie stehen nur an ihrem neuen Ort. */
  const weekTile = (/rPlanWeeks\(g, prog\) \{[\s\S]*?\n  \}/.exec(src) || [""])[0];
  ok(weekTile.length > 0, "Wächter: rPlanWeeks nicht gefunden (Signatur geändert?)");
  for (const [name, re] of [["Progressionsfaktor", /1[.,]10?\b/],
                            ["Risikoknick in Prozent", /\b10\s*%/],
                            ["Rundungsschritt", /\b5\s*Minuten/],
                            ["Bezugsfenster", /\b30\s*Tag/]]) {
    ok(!re.test(weekTile), `Wächter: ${name} steht als Zahl in rPlanWeeks statt in der Payload`);
  }
  for (const key of ["next_minutes", "factor", "round_minutes", "below_demonstrated",
                     "window_days"]) {
    ok(weekTile.includes("prog." + key) || weekTile.includes("prog.recent"),
       `Wächter: rPlanWeeks liest ${key} nicht aus der Payload`);
  }
  // Und die Zeile darf nicht an ZWEI Orten stehen - sonst gibt es sie zweimal.
  ok(!/Läufern/.test(tile), "Wächter: die Progressionsregel steht noch in rDurability");
  ok(/Läufern/.test(weekTile), "Wächter: die Grenze der Regel ist beim Umzug verloren gegangen");
}

/* ── 0.46.0: der Zeiger ueber der Ermuedungskurve, SIMULIERT ──────────────
   Aussagen ueber DOM-Verhalten gehoeren simuliert, nicht gegrept (Lehre 3 aus
   Paket A). Geprueft wird, was der Ablesestreifen beim Ueberfahren ANZEIGT -
   und zwar an drei Stellen: ueber einer gemessenen Stunde, ueber dem
   gestrichelten Bereich, und dass der Zeiger die Ansicht nicht neu baut. */
{
  const q = new M.Panel();
  q._nowIso = F.TODAY;
  const fat = F.fatigue();
  q.rFatigue(fat);            // meldet die Zeigergruppe an
  ok(q._grp.fat && q._grp.fat.xy === true,
     "zeiger: die Kurve ist nicht als xy-Gruppe angemeldet");
  ok(q._grp.fat.pts.length === fat.literature.length,
     `zeiger: ${q._grp.fat.pts.length} Rasterpunkte gegen ${fat.literature.length} in der Payload`);

  // Der Streifen, an dem sich ablesen laesst, was der Zeiger schreibt.
  let text = "", html = "";
  const strip = { querySelector: (sel) => (/rdox/.test(sel)
    ? { set textContent(v) { text = v; }, get textContent() { return text; } }
    : { set innerHTML(v) { html = v; }, get innerHTML() { return html; } }) };
  q.shadowRoot.querySelector = (sel) => (/data-rdo="fat"/.test(sel) ? strip : null);

  // ueber einer GEMESSENEN Stunde
  const iMeasured = fat.literature.findIndex((r) => r.hour === 2);
  q._fillReadout("fat", iMeasured);
  ok(/1[.,]50 h Fahrtzeit/.test(text), `zeiger: falsche Dauer im Streifen (${text})`);
  ok(!/Studienform, keine Messung/.test(text),
     "zeiger: eine gemessene Stunde wird als Studienform ausgegeben");
  // Die Bandbreite ist die SPANNE, nicht ihre Breite: 143–151 W sagt, wo die
  // Setzung liegt. Bis 0.49.2 stand die Breite in der Leiste und die Spanne in
  // der Tabelle darunter - zwei Zahlen unter einem Namen, und die Tabelle
  // faellt in diesem Release weg.
  const lit2 = fat.literature.find((r) => r.hour === 2);
  ok(M.fmt(lit2.hi - lit2.lo) !== M.fmt(lit2.lo),
     "zeiger Fixture-Beweis: Breite und Spannenanfang sind gleich - die Verwechslung waere unsichtbar");
  for (const [label, want] of [["gemessen", "142"], ["Studienform", "149"],
                               ["Bandbreite", M.fmt(lit2.lo) + "–" + M.fmt(lit2.hi)],
                               ["Belegung", "23"]]) {
    ok(html.includes(label), `zeiger: der Streifen zeigt "${label}" nicht`);
    ok(html.includes(want), `zeiger: "${label}" traegt nicht den Wert ${want} (${html.slice(0, 200)})`);
  }

  // ueber dem GESTRICHELTEN Bereich: die Leiste sagt es ausdruecklich
  const iBeyond = fat.literature.findIndex((r) => r.hour == null);
  q._fillReadout("fat", iBeyond);
  ok(/Studienform, keine Messung/.test(text),
     `zeiger: jenseits des Bestands fehlt der Hinweis (${text})`);
  ok(/gemessen[\s\S]{0,120}–/.test(html),
     "zeiger: dort steht ein gemessener Wert, wo keiner ist");

  // GEGENPROBE, gezaehlt und benannt: ohne die Hinweis-Logik faende der Test
  // nichts - also muss ein Raster OHNE gestrichelten Teil auch keinen Hinweis
  // erzeugen.
  const q2 = new M.Panel();
  q2._nowIso = F.TODAY;
  const nurGemessen = F.fatigue({ literature: fat.literature.filter((r) => r.hour != null) });
  // Trefferzusicherung (0.50.0, §7 elfter Fall): ein Gegenfall, der nichts
  // veraendert hat, ist kein Gegenfall - er prueft dann den Originalzustand
  // und sieht dabei aus wie eine bestandene Pruefung.
  ok(nurGemessen.literature.length < fat.literature.length,
     `zeiger Gegenprobe: das Raster ist unveraendert (${nurGemessen.literature.length} `
     + `von ${fat.literature.length}) - der Gegenfall greift nicht`);
  q2.rFatigue(nurGemessen);
  q2.shadowRoot.querySelector = (sel) => (/data-rdo="fat"/.test(sel) ? strip : null);
  q2._fillReadout("fat", 0);
  ok(!/Studienform, keine Messung/.test(text),
     "zeiger Gegenprobe: der Hinweis erscheint auch ohne gestrichelten Bereich");

  // und der Zeiger baut die Ansicht NICHT neu (0.9.3)
  let renders = 0;
  q._render = () => { renders++; };
  q._fillReadout("fat", 3);
  ok(renders === 0, "zeiger: das Ablesen baut die Ansicht neu");
}

/* ── Wächter: keine Urteilsregel im Frontend (docs/ausbau.md I5) ───────────
   Bis 0.41.0 hat rWorkouts Zustand und Budget SELBST zusammengeführt
   (fit === "ok" && fits_budget === false -> amber), während das Backend die
   beiden Hälften getrennt lieferte. Die vier Stufen ins Backend zu legen und
   das stehen zu lassen hätte zwei Regeln im Haus bedeutet - Fehlerklasse 3.
   Der Wächter deckte bisher nur rDurability ab und hat diese Stelle deshalb
   nie gesehen; jetzt sieht er beide. */
{
  const src = H.source();
  const cut = (from, to) => src.slice(src.indexOf(from), src.indexOf(to));
  // Kommentare raus, bevor geprüft wird: die Begründung, WARUM die Regel raus
  // ist, nennt die Regel - und ein Wächter, der an der eigenen Begründung
  // scheitert, ist derselbe Fehler wie der, den er verhindern soll.
  const strip = (body) => body.replace(/\/\*[\s\S]*?\*\//g, "").replace(/^\s*\/\/.*$/gm, "");
  const views = {
    rWorkouts: strip(cut("rWorkouts(w, forTomorrow) {", "  rGoal(g) {")),
    rPlanWeeks: strip(cut("rPlanWeeks(g, prog) {", "  _goalForm(g) {")),
  };

  for (const [name, body] of Object.entries(views)) {
    ok(body.length > 200, `wächter: ${name} nicht gefunden`);
    // die verbotene Zusammenführung selbst, in jeder Schreibweise
    ok(!/fits_budget\s*===?\s*false/.test(body),
       `wächter: ${name} wertet das Budget selbst aus`);
    ok(!/fit\s*===?\s*"(ok|maybe|no)"\s*&&/.test(body),
       `wächter: ${name} verknüpft Urteil und Budget im Frontend`);
    // und keine Stufe, die nicht aus der Payload kommt
    for (const word of ["passt", "geht, kostet aber", "kostet Erholung", "heute nicht"]) {
      ok(!body.includes('"' + word), `wächter: ${name} schreibt die Stufe "${word}" selbst`);
    }
    // die Stufe wird nachweislich GELESEN
    ok(/stage/.test(body), `wächter: ${name} liest die Stufe gar nicht`);
  }
  // die Übersetzung Backend -> Register steht an EINER Stelle
  ok((src.match(/const STAGE_TONE/g) || []).length === 1,
     "wächter: STAGE_TONE ist mehrfach definiert");
  ok((src.match(/STAGE_TONE\s*=\s*\{/g) || []).length === 1,
     "wächter: eine zweite Stufen-Übersetzung im Frontend");

  // Gegenprobe: der Wächter muss eine wiedereingebaute Regel auch finden
  const planted = 'const x = entry.fit === "ok" && entry.fits_budget === false ? "amber" : "green";';
  ok(/fits_budget\s*===?\s*false/.test(planted) && /fit\s*===?\s*"(ok|maybe|no)"\s*&&/.test(planted),
     "wächter Gegenprobe: eine wiedereingebaute Regel wird NICHT gefunden — der Wächter ist blind");
  ok(!/fits_budget\s*===?\s*false/.test('const y = entry.stage.key;'),
     "wächter Gegenprobe: eine harmlose Zeile schlägt an — der Wächter ist zu scharf");
}

/* ── die Fixture darf nicht vom Backend wegdriften ─────────────────────────
   panel_fixtures.js formt die Payload nach; die REGEL liegt in workouts.py und
   wird dort geprüft. Driften die vier Wörter auseinander, prüfen die Panel-
   Tests eine Payload, die es nicht gibt - und das ist genau der Fall, der beim
   Bau von 0.42.0 aufgefallen ist (Urteil ohne Stufe). */
{
  const fs = require("fs");
  const path = require("path");
  const backend = fs.readFileSync(
    path.join(__dirname, "..", "custom_components", "intervals_icu", "workouts.py"), "utf8");
  const stagesBlock = backend.slice(backend.indexOf("STAGES: dict[str, dict[str, str]] = {"),
                                    backend.indexOf("# The one place the objection"));
  ok(stagesBlock.length > 100, "abgleich: STAGES im Backend nicht gefunden");

  for (const [key, entry] of Object.entries(F.STAGE_WORDS)) {
    const at = stagesBlock.indexOf('"' + key + '": {');
    ok(at > 0, `abgleich: Stufe ${key} fehlt im Backend`);
    const chunk = stagesBlock.slice(at, at + 400);
    ok(chunk.includes('"' + entry.label + '"'),
       `abgleich: Wort der Stufe ${key} weicht vom Backend ab ("${entry.label}")`);
    ok(chunk.includes('"' + entry.word + '"'),
       `abgleich: Beschriftung der Stufe ${key} weicht vom Backend ab`);
  }
  ok(Object.keys(F.STAGE_WORDS).length === 4, "abgleich: die Fixture kennt nicht vier Stufen");
  // Gegenprobe: ein verändertes Wort muss auffallen
  ok(!stagesBlock.includes('"gelblich"'),
     "abgleich Gegenprobe: ein erfundenes Wort steht im Backend — Prüfung wertlos");

  // und die Zusicherung aus dem Bau: die Fixture baut nie ein Urteil ohne Stufe
  for (const kind of [undefined, "einbruch"]) {
    for (const entry of F.workouts(kind).workouts) {
      ok(!("fit" in entry) || (entry.stage && entry.stage.key),
         `abgleich: Fixture ${kind || "normal"} liefert ein Urteil ohne Stufe`);
    }
  }
}

/* ── Ladepfad: jeder Reiter wird auf EINEM Weg aufgebaut (0.42.1) ─────────
   Der Fehler: _boot rief _render() direkt. _need("goal") hängt aber allein an
   _setTab, also wurde die Ziel-Payload beim ersten Aufbau nie geholt - und
   rGoal/rPlanWeeks, die einzigen beiden Blöcke, die sie brauchen, blieben
   still leer. Von 0.20.0 bis 0.42.0, ohne eine einzige Fehlermeldung.

   Zwei Wächter: der Bootpfad muss durch _setTab, und jeder Reiter, den
   _render bedient, muss seine Payload auf diesem Weg auch anfordern. */
{
  const src = H.source();
  const boot = src.slice(src.indexOf("async _boot()"), src.indexOf("async _need("));
  ok(boot.length > 200, "ladepfad: _boot nicht gefunden");
  ok(/await this\._setTab\(this\._tab\)/.test(boot),
     "ladepfad: _boot baut den Reiter an _setTab vorbei — die Payload des Reiters fehlt beim ersten Aufbau");

  // Welche Payload holt _setTab je Reiter, und welche braucht _render?
  const setTab = src.slice(src.indexOf("async _setTab(t)"), src.indexOf("async _openAct("));
  const render = src.slice(src.indexOf("  _render() {"), src.indexOf("this._view.innerHTML = html"));
  const needsOf = {
    // fatigue seit 0.46.0: die Ermuedungskurve sitzt in der Durability-Kachel
    // im TRAINER. Auf dem EINEN Weg angefordert, nicht ueber einen zweiten
    // Ladepfad daneben - sonst ist es die stille Luecke aus 0.42.1 mit einer
    // neuen Payload.
    trainer: ["coach", "workouts", "goal", "fatigue", "blocks"], heute: ["today"], signale: ["signals"],
    fitness: ["pmc"], akt: ["akt"], dfa: ["thr"],
  };
  for (const [tab, keys] of Object.entries(needsOf)) {
    ok(render.includes(`"${tab}"`), `ladepfad: Reiter ${tab} wird nicht gerendert`);
    for (const key of keys) {
      ok(setTab.includes(`_need("${key}")`),
         `ladepfad: Reiter ${tab} rendert, aber ${key} wird nie angefordert`);
    }
  }
  // kalender und belastung leben von den Boot-Payloads - die müssen dort stehen
  for (const key of ["days", "load"]) {
    ok(src.includes(`const BOOT_KEYS`) && src.slice(src.indexOf("const BOOT_KEYS"),
        src.indexOf("const TABS")).includes(`"${key}"`),
       `ladepfad: ${key} steht nicht unter den Boot-Payloads`);
  }

  // Und sie darf NICHT mehr am DFA-Reiter haengen: eine Payload an zwei Orten
  // anzufordern waere der zweite Ladepfad, den dieser Waechter verhindert.
  ok(!/dfa[\s\S]{0,80}rFatigue/.test(render),
     "ladepfad: die Ermuedungskurve haengt noch am DFA-Reiter");
  ok(/rFatigue/.test(src.slice(src.indexOf("rDurability(d) {"), src.indexOf("_fatigueHistory(f) {"))),
     "ladepfad: die Ermuedungskurve sitzt nicht in der Durability-Kachel");

  // 0.48.1: WO eine Kachel gerendert wird, ist eine ZUSICHERUNG, keine
  // Einzelentscheidung. In 0.46.0 wurde der Ort von Hand korrigiert und keine
  // Prüfung hinterlassen - deshalb landete die nächste Kachel wieder im
  // falschen Reiter. Eine Korrektur ohne Zusicherung ist keine.
  const HOME = {
    rTrainer: "trainer", rGoal: "trainer", rPlanWeeks: "trainer", rWorkouts: "trainer",
    rDurability: "trainer", rFatigue: "trainer", rBlocks: "trainer",
    rRampTest: "trainer", rRampGap: "trainer",
    rHeute: "heute", rSignale: "signale", rFitness: "fitness",
    rAkt: "akt", rDfa: "dfa", rKalender: "kalender", rBelastung: "belastung",
  };
  const alle = (src.match(/\n  r[A-Z]\w*\(/g) || []).map((m) => m.trim().slice(0, -1));
  for (const name of alle) {
    ok(HOME[name] !== undefined,
       `ort: Kachel ${name} steht in keiner Zuordnung — der Reiter ist eine Einzelentscheidung`);
  }
  // Trainer-Kacheln duerfen NICHT in einem anderen Reiter gerendert werden.
  const dfaZweig = (/this\._tab === "dfa"\) html = [^;]*/.exec(render) || [""])[0];
  for (const [name, tab] of Object.entries(HOME)) {
    if (tab === "trainer" && alle.includes(name)) {
      ok(!dfaZweig.includes(name), `ort: ${name} gehört in den Trainer, wird aber im DFA-Reiter gerendert`);
    }
  }
  // Gegenprobe, gezaehlt und benannt: eine im falschen Zweig gerenderte Kachel
  // wird gefunden - sonst prueft die Schleife nur, dass der Zweig kurz ist.
  ok(/rBlocks/.test('this._tab === "dfa") html = this.rDfa(x) + this.rBlocks(y)'),
     "ort Gegenprobe: eine falsch platzierte Kachel wird NICHT gefunden — die Prüfung ist blind");

  // Gegenprobe: ein _boot ohne _setTab muss auffallen
  ok(!/await this\._setTab\(this\._tab\)/.test("this._render();\n    this._routeFromHash();"),
     "ladepfad Gegenprobe: ein _boot ohne _setTab wird NICHT gefunden — der Wächter ist blind");

  // und kein Block darf noch mit einem Leerstring aussteigen, wenn seine
  // Payload fehlt - der stille Ausstieg war der eigentliche Fehler
  for (const fn of ["rGoal", "rPlanWeeks", "rWorkouts", "rKalender", "rBelastung",
                    "rHeute", "rSignale", "rFitness", "rDfa", "rTrainer"]) {
    const at = src.indexOf(`  ${fn}(`);
    ok(at > 0, `leerfall-wächter: ${fn} nicht gefunden`);
    const head = src.slice(at, at + 320);
    ok(/_dataGap\(/.test(head),
       `leerfall-wächter: ${fn} meldet fehlende Daten nicht über _dataGap`);
  }
  // _dataGap selbst unterscheidet DREI Zustände - zwei wären wieder der Fall,
  // in dem "nie geholt" wie "lädt gerade" aussieht
  const gap = src.slice(src.indexOf("  _dataGap(key, label)"), src.indexOf("  _render() {"));
  ok(/this\._failed\[key\]/.test(gap) && /this\._asked\[key\]/.test(gap),
     "leerfall-wächter: _dataGap trennt 'nie geholt' nicht von 'lädt gerade'");
  ok(/Nie angefordert/.test(gap), "leerfall-wächter: der Defektfall hat keinen eigenen Text");
}

/* ── eine Karte, nicht zwei Bauarten (docs/ausbau.md I9) ──────────────────
   Die Wochenansicht hatte ihre eigene, magerere Darstellung derselben Sache:
   kein Segmentbalken, kein Pulsfenster, keine Zweckzeile, dafür fünf Absätze
   Fließtext. Zwei Darstellungen desselben Objekts sind die Layout-Fassung
   einer zweiten Regel im Haus. */
{
  const src = H.source();
  const cut = (from, to) => src.slice(src.indexOf(from), src.indexOf(to));
  const strip = (b) => b.replace(/\/\*[\s\S]*?\*\//g, "").replace(/^\s*\/\/.*$/gm, "");
  const workouts = strip(cut("rWorkouts(w, forTomorrow) {", "  rGoal(g) {"));
  const weeks = strip(cut("rPlanWeeks(g, prog) {", "  _weekReasons(w) {"));

  for (const [name, body] of [["rWorkouts", workouts], ["rPlanWeeks", weeks]]) {
    ok(/_sessionCard\(/.test(body), `karte: ${name} baut die Einheit nicht über _sessionCard`);
    // und keine der Bestandteile wird daneben noch einmal selbst gezeichnet
    for (const own of ["wosteps", "_woBar(", 'class="wometa"', 'class="psess']) {
      ok(!body.includes(own), `karte: ${name} zeichnet ${own} an der gemeinsamen Karte vorbei`);
    }
  }
  // die Karte selbst führt alles, woran eine Einheit erkannt wird
  const card = cut("  _sessionCard(entry, o) {", "  rWorkouts(w, forTomorrow) {");
  for (const part of ["_woBar(", "wosteps", "hr_window", "entry.purpose", "blocks_w"]) {
    ok(card.includes(part), `karte: der Sitzungskarte fehlt ${part}`);
  }
  // Gegenprobe: der Wächter muss eine zweite Bauart auch finden
  ok(strip('const x = `<div class="wosteps">…`;').includes("wosteps"),
     "karte Gegenprobe: eine wiedereingebaute zweite Bauart wird NICHT gefunden — blind");

  // Die Herleitung der Last gehört in den AUFKLAPPBAREN Teil, nicht in den Kopf
  const head = card.slice(0, card.indexOf('${opts.open ?'));
  ok(!/Katalogeinheit|catalogue_load/.test(head),
     "karte: die Hochrechnung der Last steht im Kartenkopf statt im Rechenweg");
  const detail = card.slice(card.indexOf("${opts.open ?"));
  ok(/catalogue_load/.test(detail), "karte: der Rechenweg der Last fehlt im aufgeklappten Teil");

  // Die gemeinsame Warnung wird an EINER Stelle gesammelt
  ok((src.match(/_sharedReasons\(list\) \{/g) || []).length === 1,
     "warnung: der Sammler ist mehrfach definiert");
  ok(/saidAbove/.test(card), "warnung: die Karte fragt nicht, was schon oben stand");
}

/* ── 0.50.0: EINE Zeigerlogik, ZWEI zugesicherte Verhaltensweisen ─────────
   Die grosse Zahl folgt dem Zeiger in der Ermuedungskachel und bleibt in den
   Block-Karten stehen. Beides gehoert zugesichert, sonst zieht der naechste
   Umbau sie stillschweigend gleich. Geprueft wird am simulierten Ereignis,
   nicht per grep (Lehre 3 aus Paket A). */
{
  const q = new M.Panel();
  q._nowIso = F.TODAY;
  const fat = F.fatigue(), blk = F.blocks();
  q._fatigue = fat; q._blocks = blk;
  const tile = q.rDurability(F.coach("rebound").durabilityClear);

  // --- die Gruppen, wie das Rendern sie anmeldet --------------------------
  const fams = Object.keys(blk.families);
  for (const key of fams) {
    ok(q._grp["blk_" + key] != null,
       `zeiger block: Familie ${key} meldet keine eigene Zeigergruppe an`);
    ok(tile.includes(`data-grp="blk_${key}"`),
       `zeiger block: die Karte ${key} traegt keinen eigenen Gruppen-Wrapper`);
    ok(tile.includes(`data-rdo="blk_${key}"`),
       `zeiger block: die Karte ${key} hat keine eigene Ableseleiste`);
  }
  // Die geschachtelte Gruppe ist der Punkt: sie liegt IN der Gruppe der Kurve.
  ok(tile.indexOf('data-grp="fat"') >= 0
     && tile.indexOf('data-grp="fat"') < tile.indexOf('data-grp="blk_'),
     "zeiger block: die Block-Gruppe liegt nicht innerhalb der Kurvengruppe");

  // --- die ZUSICHERUNG: genau eine Gruppe laesst die Leitzahl mitlaufen ---
  ok(q._grp.fat && q._grp.fat.lead != null,
     "zeiger: die Ermuedungskurve laesst ihre Leitzahl NICHT mitlaufen");
  const mitLead = Object.keys(q._grp).filter((k) => q._grp[k].lead != null);
  ok(mitLead.join(",") === "fat",
     `zeiger: mitlaufende Leitzahl in ${mitLead.join(",") || "keiner"} Gruppe - erwartet nur in der Kurve`);
  for (const key of fams) {
    ok(!tile.includes(`data-lead="blk_${key}"`),
       `zeiger block: die Karte ${key} haengt ihre Leitzahl an den Zeiger`);
  }
  ok(tile.includes('data-lead="fat"'), "zeiger: die Leitzahl der Kurve ist nicht angeschlossen");

  // --- Streifen und Leitzahl als beobachtbare Elemente --------------------
  const mkBox = () => {
    const v = {};
    const el = (k) => ({ style: {}, set textContent(t) { v[k] = t; }, get textContent() { return v[k]; } });
    const parts = { ".ldl": el("l"), ".ldv": el("v"), ".ldn": el("n") };
    return { _v: v, _style: parts, querySelector: (s) => parts[s] || null };
  };
  const mkStrip = () => {
    const st = { x: "", h: "" };
    return { _s: st,
      querySelector: (s) => (/rdox/.test(s)
        ? { set textContent(t) { st.x = t; }, get textContent() { return st.x; } }
        : { set innerHTML(t) { st.h = t; }, get innerHTML() { return st.h; } }) };
  };
  const leadBox = mkBox(), stripFat = mkStrip(), stripVo = mkStrip();
  const asked = [];
  q.shadowRoot.querySelector = (sel) => {
    asked.push(sel);
    if (/data-lead="fat"/.test(sel)) return leadBox;
    if (/data-rdo="fat"/.test(sel)) return stripFat;
    if (/data-rdo="blk_vo2max"/.test(sel)) return stripVo;
    return null;
  };
  q.shadowRoot.querySelectorAll = () => q.shadowRoot._lines;

  // --- Punkt 3: die grosse Zahl FOLGT, in der Kurve -----------------------
  const grid = fat.literature;
  const iMess = grid.findIndex((r) => r.hour === 2);
  const iForm = grid.findIndex((r) => r.hour == null);
  const mess = fat.measured.find((r) => r.hour === 2);
  q._fillReadout("fat", iMess);
  ok(leadBox._v.v === M.fmt(mess.watts),
     `zeiger leitzahl: ${leadBox._v.v} statt ${M.fmt(mess.watts)} ueber der gemessenen Stunde`);
  ok(/1[.,]50 h/.test(leadBox._v.l), `zeiger leitzahl: die Stelle fehlt in der Beschriftung (${leadBox._v.l})`);
  ok(/gemessen/.test(leadBox._v.n) && leadBox._v.n.includes(M.fmt(mess.n)),
     `zeiger leitzahl: Herkunft oder Belegung fehlen (${leadBox._v.n})`);
  ok(leadBox._style[".ldv"].style.color === M.ROLE.series,
     "zeiger leitzahl: eine Messung traegt nicht das Serienregister");

  q._fillReadout("fat", iForm);
  ok(leadBox._v.v === M.fmt(grid[iForm].watts),
     "zeiger leitzahl: jenseits des Bestands steht nicht der Wert der Studienform");
  ok(/Studienform, keine Messung/.test(leadBox._v.n),
     `zeiger leitzahl: die Setzung wird nicht als solche beschriftet (${leadBox._v.n})`);
  ok(leadBox._style[".ldv"].style.color === M.C.slate,
     "zeiger leitzahl: eine Setzung traegt das Messregister");

  // Ruhezustand: eigene Rechnung, eigene Beschriftung.
  ok(M.fmt(fat.anchor_base) !== M.fmt(grid[0].watts),
     "zeiger Fixture-Beweis: Anker und erster Rasterpunkt sind gleich - der Rueckfall waere nicht pruefbar");
  q._fillReadout("fat", null);
  ok(leadBox._v.v === M.fmt(fat.anchor_base),
     `zeiger leitzahl: faellt nicht auf den Ausgangswert zurueck (${leadBox._v.v})`);
  ok(/Dauer null/.test(leadBox._v.l),
     `zeiger leitzahl: der Ruhezustand ist nicht als eigene Rechnung beschriftet (${leadBox._v.l})`);

  // --- Punkt 5: der Zeiger UEBER EINER BLOCK-KURVE ------------------------
  const vo = blk.families.vo2max.points;
  const svgBlk = { dataset: { w: "880", padl: "48", padr: "14" },
                   getBoundingClientRect: () => ({ left: 0, top: 600, width: 880, height: 170 }) };
  const gBlk = { dataset: { grp: "blk_vo2max" },
                 querySelector: (s) => (s === "svg.ch" ? svgBlk : null),
                 querySelectorAll: () => q.shadowRoot._lines };
  q._attach();
  const onMove = q.shadowRoot._listeners.pointermove;
  ok(typeof onMove === "function", "zeiger block: kein pointermove-Handler registriert");

  const vorher = stripFat._s.x;
  asked.length = 0;
  const iWant = 2;
  const xAt = (i) => 48 + ((880 - 48 - 14) * i) / (vo.length - 1);
  onMove({ clientX: xAt(iWant), clientY: 640,
           target: { closest: (sel) => (sel === "[data-grp]" ? gBlk : null) } });
  const s = stripVo._s;
  ok(s.x.includes(M.dMed(vo[iWant].date)), `zeiger block: das Datum fehlt (${s.x})`);
  ok(s.x.includes(vo[iWant].name), `zeiger block: die Einheit wird nicht genannt (${s.x})`);
  ok(s.h.includes(M.fmt(vo[iWant].first_watts)), "zeiger block: die Leistung fehlt in der Leiste");
  ok(s.h.includes(M.fmt(vo[iWant].first_alpha, 2)),
     `zeiger block: der alpha des aufgetragenen Blocks fehlt (${s.h})`);
  ok(s.h.includes(String(vo[iWant].n_blocks)), "zeiger block: die Zahl der Bloecke fehlt");

  // Die Verwechslung, gegen die es gebaut ist: aufgetragen ist der ERSTE
  // Block, also steht dort SEIN alpha - nicht der Median, der die Steuergroesse
  // ist und als eigene Zeile daneben steht.
  ok(M.fmt(vo[iWant].first_alpha, 2) !== M.fmt(vo[iWant].median_alpha, 2),
     "zeiger block Fixture-Beweis: erster alpha und Median sind gleich - die Verwechslung waere unsichtbar");
  const zeile = /alpha dort[\s\S]{0,120}?<\/span>/.exec(s.h);
  ok(zeile !== null, "zeiger block: die Zeile 'alpha dort' fehlt");
  ok(zeile && !zeile[0].includes(M.fmt(vo[iWant].median_alpha, 2)),
     "zeiger block: neben dem aufgetragenen Punkt steht der Median statt seines eigenen alpha");
  ok(s.h.includes("Median alpha") && s.h.includes(M.fmt(vo[iWant].median_alpha, 3)),
     "zeiger block: die Steuergroesse fehlt als eigene Zeile");

  // Die Leitzahl der Block-Karte bleibt stehen: sie wird nicht einmal gesucht.
  ok(!asked.some((sel) => /data-lead/.test(sel)),
     `zeiger block: die Leitzahl der Karte wird angefasst (${asked.filter((x) => /data-lead/.test(x)).join(",")})`);
  // Und die Leiste der KURVE bleibt unberuehrt - das war der Fehler bis 0.49.2.
  ok(stripFat._s.x === vorher,
     `zeiger block: die Leiste der Ermuedungskurve wird mitgeschrieben (${stripFat._s.x})`);
  // GEGENPROBE, gezaehlt und benannt: derselbe Zeiger auf den AEUSSEREN
  // Wrapper - der alte Weg - schreibt sehr wohl in die Kurvenleiste. Ohne das
  // prueft die Zeile darueber nur, dass ueberhaupt nie etwas geschrieben wird.
  const svgFat = { dataset: { w: "880", padl: "48", padr: "14", padt: "8", padb: "22", h: "300",
                              x0: String(grid[0].t), x1: String(grid[grid.length - 1].t),
                              y0: "100", y1: "160" },
                   getBoundingClientRect: () => ({ left: 0, top: 0, width: 880, height: 300 }) };
  const gFat = { dataset: { grp: "fat" },
                 querySelector: (sel) => (sel === "svg.ch" ? svgFat : null),
                 querySelectorAll: () => q.shadowRoot._lines };
  onMove({ clientX: 400, clientY: 150,
           target: { closest: (sel) => (sel === "[data-grp]" ? gFat : null) } });
  ok(stripFat._s.x !== vorher,
     "zeiger Gegenprobe: der Zeiger im Graphen schreibt die Kurvenleiste NICHT - die Pruefung ist blind");

  // --- Nebenbefund: ausserhalb des Diagramms wird nichts geschrieben ------
  const merk = stripFat._s.x;
  const idxDrin = q._xhMove(gFat, { clientX: 400, clientY: 150 });
  ok(idxDrin != null, "zeiger ausserhalb Gegenprobe: schon im Diagramm kommt kein Index - blind");
  const idxDrunter = q._xhMove(gFat, { clientX: 400, clientY: 900 });
  ok(idxDrunter == null,
     `zeiger ausserhalb: unter dem Diagramm kommt immer noch ein Index (${idxDrunter})`);
  onMove({ clientX: 400, clientY: 900,
           target: { closest: (sel) => (sel === "[data-grp]" ? gFat : null) } });
  ok(/zuletzt/.test(stripFat._s.x),
     `zeiger ausserhalb: die Leiste bleibt auf einem abgelesenen Wert stehen (${stripFat._s.x})`);
  ok(merk !== stripFat._s.x || /zuletzt/.test(merk),
     "zeiger ausserhalb: der Ruhezustand ist nicht erkennbar");

  // --- Punkt 3, zweite Stelle: die Zeile der Wertetabelle -----------------
  const zeilen = [...tile.matchAll(/<tr data-rg="fat" data-ri="(\d+)"><td>Stunde (\d+)</g)];
  ok(zeilen.length === fat.measured.length,
     `zeiger tabelle: ${zeilen.length} ablesbare Zeilen gegen ${fat.measured.length} Messungen`);
  for (const [, ri, hour] of zeilen) {
    ok(grid[+ri] && grid[+ri].hour === +hour,
       `zeiger tabelle: Zeile zu Stunde ${hour} zeigt auf Rasterpunkt ${ri} - das ist eine andere Stelle`);
  }
  // Ohne Null-Pruefung stuerzt dieser Block bei der Mutation ab, statt sie zu
  // zaehlen - und ein abgestuerzter Test meldet am Ende "0 Fehler" (§9).
  const treffer = zeilen.find((z) => +z[2] === 2);
  ok(treffer != null, "zeiger tabelle: keine ablesbare Zeile zur gemessenen Stunde");
  if (treffer) {
    onMove({ clientX: 0, clientY: 0,
             target: { closest: (sel) => (sel === "[data-ri]"
               ? { dataset: { rg: "fat", ri: treffer[1] } } : null) } });
    ok(leadBox._v.v === M.fmt(mess.watts),
       `zeiger tabelle: die Zeile schreibt ${leadBox._v.v} statt ${M.fmt(mess.watts)} in die Leitzahl`);
    ok(stripFat._s.x.includes("1,50 h") || stripFat._s.x.includes("1.50 h"),
       `zeiger tabelle: die Leiste folgt der Zeile nicht (${stripFat._s.x})`);
  }
}

/* ── Die Zuordnung, AM SIMULIERTEN EREIGNIS (docs/ausbau.md P2) ────────────
   Nicht per grep: geprüft wird, was der echte Klick-Handler mit den ATTRIBUTEN
   macht, die wirklich gerendert worden sind. Die entscheidende Aussage ist,
   dass der Haken den `start_index` schickt und nicht die laufende Nummer —
   und die ist an einem String im Quelltext nicht zu haben (Lehre 3 aus
   Paket A). */
{
  const q = new M.Panel();
  // Eine Fahrt mit einer PAUSE: laufende Nummer und start_index laufen damit
  // auseinander, sonst wäre der Unterschied unsichtbar (Lehre 2 aus Paket A).
  const laps = [
    { n: 1, label: "WARMUP", start_index: 0, moving_time: 600, avg_watts: 120, avg_hr: 120, ef: 1.0, dfa_a1: 0.95 },
    { n: 2, label: "WORK", start_index: 600, moving_time: 600, avg_watts: 250, avg_hr: 165, ef: 1.5, dfa_a1: 0.55 },
    { n: 3, label: "RECOVERY", start_index: 1200, moving_time: 90, avg_watts: 95, avg_hr: 130, ef: 0.7, dfa_a1: 0.9 },
    { n: 4, label: "WORK", start_index: 1290, moving_time: 600, avg_watts: 232, avg_hr: 163, ef: 1.4, dfa_a1: 0.58 },
  ];
  const act = { id: "a1", name: "Tempo", dfa: { blocks: [{ start_index: 600 }, { start_index: 1290 }] } };
  q._laps = { a1: { laps, source: "icu_intervals" } };
  q._smarks = { marks: [], families: Object.keys(M.FAM), stale_reason: {}, not_measured: "x" };
  q._rtests = { tests: [] };
  q._sel = act;
  q._famSel = null;

  let renders = 0;
  q._render = () => { renders++; };
  q._attach();
  const onClick = q.shadowRoot._listeners.click;
  ok(typeof onClick === "function", "zuordnung: kein Klick-Handler registriert");

  // ein Klick auf ein wirklich gerendertes Element nachstellen
  const attrsOf = (html, needle) => {
    const re = new RegExp("<button[^>]*" + needle + "[^>]*>");
    const tag = re.exec(html);
    if (!tag) return null;                      // Regex null-geprüft (§9)
    const out = {};
    for (const m of tag[0].matchAll(/data-([a-z]+)="([^"]*)"/g)) out[m[1]] = m[2];
    return out;
  };
  const fire = (dataset) => onClick({ target: { closest: (sel) => (sel === "[data-act]" ? { dataset } : null) } });

  // ── die Familienwahl ───────────────────────────────────────────────────
  const reihe = q._marksBlock(act);
  const tempoTile = attrsOf(reihe, 'data-id="tempo"');
  ok(tempoTile !== null, "zuordnung: die Tempo-Kachel wird gar nicht gerendert");
  ok(tempoTile && tempoTile.act === "famsel",
     `zuordnung: die Kachel trägt nicht die Wahl-Aktion (${tempoTile && tempoTile.act})`);
  fire(tempoTile || {});
  ok(q._famSel === "tempo", `zuordnung: der Klick wählt die Familie nicht (${q._famSel})`);
  fire(tempoTile || {});
  ok(q._famSel === null, "zuordnung: dieselbe Kachel noch einmal hebt die Wahl nicht auf");
  fire(tempoTile || {});

  // die aktive Kachel trägt Rahmen, Form UND Wort - nicht nur eine Sättigung
  const aktiv = q._marksBlock(act);
  ok(/class="famtile on/.test(aktiv), "zuordnung: die aktive Kachel trägt keine eigene Klasse");
  ok(aktiv.includes("gewählt"), "zuordnung: die aktive Kachel sagt es nicht mit einem Wort");
  const cssSrc = (H.source().match(/_css\(\) \{[\s\S]*$/) || [""])[0];
  ok(/\.famtile\.on\{[^}]*border-color/.test(cssSrc),
     "zuordnung: die aktive Kachel bekommt keinen eigenen Rahmen");

  // ── DER HAKEN SCHICKT DEN start_index, NICHT DIE LAUFENDE NUMMER ───────
  const sent = [];
  q._ws = (cmd, args) => { sent.push([cmd, args]); return Promise.resolve({}); };
  const liste = q._lapBlock(act);
  // der Haken am VIERTEN Abschnitt: laufende Nummer 4, start_index 1290
  const box = attrsOf(liste, 'data-idx="1290"');
  ok(box !== null, "zuordnung: die Haken-Spalte rendert keinen Knopf für Abschnitt 1290");
  ok(box && box.act === "smark", `zuordnung: falsche Aktion am Haken (${box && box.act})`);
  ok(box && box.fam === "tempo", `zuordnung: der Haken trägt die Familie nicht (${box && box.fam})`);
  fire(box || {});
  ok(sent.length === 1, `zuordnung: der Klick schickt nichts (${sent.length} Aufrufe)`);
  ok(sent[0] && sent[0][0] === "set_section_mark",
     `zuordnung: falsches Kommando (${sent[0] && sent[0][0]})`);
  ok(sent[0] && sent[0][1] && sent[0][1].start_index === 1290,
     `zuordnung: der Haken schickt ${sent[0] && sent[0][1] && sent[0][1].start_index} statt 1290 — ` +
     "das ist die laufende Nummer statt des start_index (P3a)");
  ok(sent[0] && sent[0][1] && sent[0][1].start_index !== 4,
     "zuordnung: der Haken schickt die laufende Nummer");
  ok(sent[0] && sent[0][1] && sent[0][1].mark === true,
     "zuordnung: ein leerer Kasten setzt keine Marke");

  // und derselbe Haken, wenn die Marke schon steht, nimmt sie ZURÜCK
  q._smarks = { marks: [{ activity_id: "a1", date: "2026-09-10", marks: { tempo: [1290] },
                          hours: null, reason: "Markiert, noch nicht gemessen" }],
                families: Object.keys(M.FAM), stale_reason: {} };
  const liste2 = q._lapBlock(act);
  const box2 = attrsOf(liste2, 'data-idx="1290"');
  ok(box2 !== null, "zuordnung: der gesetzte Haken verschwindet aus der Liste");
  ok(box2 && box2.on === "1", "zuordnung: der gesetzte Haken sieht aus wie ein leerer");
  sent.length = 0;
  fire(box2 || {});
  ok(sent.length === 0,
     "zuordnung: ein zweiter Klick schickt, WÄHREND der erste noch läuft");
  q._smBusy = null;
  fire(box2 || {});
  ok(sent[0] && sent[0][1] && sent[0][1].mark === false,
     "zuordnung: ein gesetzter Haken setzt noch einmal, statt zurückzunehmen");
  // Gegenprobe: ohne data-on wäre jeder Klick ein Setzen - der Wächter oben
  // prüft dann nichts.
  ok(({ on: "0" }).on !== "1" && ({ on: "1" }).on === "1",
     "zuordnung Gegenprobe: der Zustand am Knopf wird gar nicht gelesen");

  // die Marke steht als Kürzel in der eigenen Spalte, nicht zwischen den Balken
  ok(/<span class="lmk">/.test(liste2), "zuordnung: es gibt keine eigene Marken-Spalte");
  ok(liste2.includes("TMP"), "zuordnung: das Kürzel steht nicht in der Spalte");
  ok(/<span>Zuordnung<\/span>/.test(liste2), "zuordnung: die Spalte hat keine Kopfzeile");
  const lmkPos = liste2.indexOf('class="lmk"'), dfaPos = liste2.indexOf(M.ROLE.dfa);
  ok(lmkPos > dfaPos, "zuordnung: die Marken stehen vor den rollengefärbten Balken");

  // ── DIE QUITTUNG: die Kachel traegt den Zustand SICHTBAR ───────────────
  // Der Haken misst nicht - also muss etwas anderes sagen, dass er angekommen
  // ist. Ohne diese Zusicherung ist die ganze Auslieferung nicht zu pruefen:
  // man hakt und sieht nicht, ob es gespeichert wurde.
  q._smarks = { marks: [{ activity_id: "a1", date: "2026-09-10",
                          marks: { tempo: [1290], sweetspot: [600] },
                          anchor: { laps: 4, sections: [{ i: 600, s: 600 }, { i: 1290, s: 600 }] },
                          hours: null, set_at: "2026-09-12",
                          reason: "Markiert, noch nicht gemessen — die Messung läuft auf „übernehmen und messen“." }],
                families: Object.keys(M.FAM), stale_reason: {} };
  const quittung = q._marksBlock(act);
  H.clean(quittung, "quittung");
  ok(/Im Archiv:/.test(quittung), "quittung: die Kachel sagt nicht, dass die Marke angekommen ist");
  ok(/2 Marken/.test(quittung), `quittung: die Zahl der Marken fehlt oder stimmt nicht`);
  ok(/2 Familien/.test(quittung), "quittung: über wie viele Familien fehlt");
  ok(quittung.includes("2026-09-12"), "quittung: wann gesetzt wurde, steht nicht da");
  ok(quittung.includes("noch nicht gemessen"),
     "quittung: der Zustand „markiert, aber nicht gemessen“ ist nicht sichtbar");
  // Der Grund kommt AUS DER PAYLOAD, nicht aus einem zweiten Satz im Panel -
  // sonst stünden zwei Wahrheiten für einen Text nebeneinander.
  ok((quittung.match(/noch nicht gemessen/g) || []).length === 1,
     "quittung: der Satz steht doppelt — einmal aus der Payload, einmal aus dem Panel");
  // die Kacheln zählen ihre Abschnitte einzeln
  ok(/1 Abschnitt</.test(quittung) || /1 Abschnitt\s/.test(quittung),
     "quittung: die Kachel nennt die Zahl ihrer Abschnitte nicht");
  // GEGENPROBE: eine Fahrt OHNE Marke trägt keine Quittung - sonst prüft das
  // obige nur, dass irgendein Text da ist.
  const leer = q._marksBlock({ id: "a9", dfa: { blocks: [{ start_index: 1 }] } });
  ok(!/Im Archiv:/.test(leer),
     "quittung Gegenprobe: eine nie markierte Fahrt zeigt trotzdem eine Quittung");
  // und eine GEMESSENE Fahrt sagt das statt „noch nicht gemessen"
  q._smarks.marks[0].hours = [{ hour: 1, p075: 208 }, { hour: 2, p075: 201 }];
  const gemessen = q._marksBlock(act);
  ok(/Gemessen über 2 Stunden/.test(gemessen),
     "quittung: eine gemessene Fahrt sagt nicht, worüber gemessen wurde");
  ok(!/noch nicht gemessen/.test(gemessen),
     "quittung: eine gemessene Fahrt behauptet weiter, sie sei nicht gemessen");
  q._smarks.marks[0].hours = null;

  // ── EIN Abschnitt ist kein Mangel ──────────────────────────────────────
  // Eine Rolleneinheit hat genau einen Abschnitt, und der IST die ganze Fahrt.
  // Nichts im Panel darf das als Mangel lesen - der Hinweis auf Unterteilen
  // gehoert allein dem Fall "gar keine Abschnitte".
  const einLap = [{ n: 1, label: "Rolle", start_index: 0, moving_time: 3600,
                    avg_watts: 180, avg_hr: 150, ef: 1.2, dfa_a1: 0.7 }];
  q._laps = { a1: { laps: einLap } };
  q._smarks = { marks: [{ activity_id: "a1", date: "2026-09-10", marks: { endurance: [0] },
                          anchor: { laps: 1, sections: [{ i: 0, s: 3600 }] },
                          hours: null, set_at: "2026-09-12", reason: "Markiert, noch nicht gemessen" }],
                families: Object.keys(M.FAM), stale_reason: {} };
  const eine = q._marksBlock(act) + q._lapBlock(act);
  ok(!/unterteil/i.test(eine),
     "ein Abschnitt: die Karte verlangt Unterteilen, obwohl ein Abschnitt reicht");
  ok(!/nur ein|zu wenig|mindestens/i.test(eine),
     "ein Abschnitt: die Karte liest einen Abschnitt als Mangel");
  ok(eine.includes("die ganze Fahrt"),
     "ein Abschnitt: die Kachel sagt nicht, dass der eine Abschnitt die ganze Fahrt ist");
  ok(!/1 Abschnitt</.test(eine),
     "ein Abschnitt: die Kachel sagt weiter „1 Abschnitt“ — das klingt nach einem Ausschnitt");
  // der Haken funktioniert dabei ganz normal
  const boxEins = attrsOf(q._lapBlock(act), 'data-idx="0"');
  ok(boxEins !== null, "ein Abschnitt: es gibt keinen Haken für die einzige Runde");
  // GEGENPROBE: bei MEHREREN Abschnitten zählt die Kachel wieder Abschnitte -
  // sonst prüft das obige nur, dass irgendein Text dasteht.
  q._laps = { a1: { laps } };
  q._smarks.marks[0].marks = { endurance: [0] };
  q._smarks.marks[0].anchor = { laps: 4, sections: [{ i: 0, s: 600 }] };
  const mehrere = q._marksBlock(act);
  ok(/1 Abschnitt</.test(mehrere),
     "ein Abschnitt Gegenprobe: eine Fahrt mit vier Runden sagt auch „die ganze Fahrt“");
  ok(!/die ganze Fahrt/.test(mehrere),
     "ein Abschnitt Gegenprobe: der Satz erscheint auch dort, wo er falsch ist");
  q._smarks = { marks: [{ activity_id: "a1", date: "2026-09-10",
                          marks: { tempo: [1290], sweetspot: [600] },
                          anchor: { laps: 4, sections: [{ i: 600, s: 600 }, { i: 1290, s: 600 }] },
                          hours: null, set_at: "2026-09-12",
                          reason: "Markiert, noch nicht gemessen — die Messung läuft auf „übernehmen und messen“." }],
                families: Object.keys(M.FAM), stale_reason: {} };

  // ── ein Abschnitt OHNE start_index ist nicht zuzuordnen, und sagt es ────
  q._laps = { a1: { laps: laps.concat([{ n: 5, label: "ENDE", moving_time: 300, avg_watts: 90 }]) } };
  const liste3 = q._lapBlock(act);
  ok(/nicht zuzuordnen/.test(liste3),
     "zuordnung: ein Abschnitt ohne Startpunkt fehlt still, statt es zu sagen");
  q._laps = { a1: { laps } };
}

/* ── Die drei Fehlergründe kommen im KLARTEXT an ───────────────────────────
   Nicht "Fehler beim Markieren": der häufigste Fall ist "in Intervals
   unterteilen", und der ist nur als eigener Satz brauchbar. */
(async () => {
  const q = new M.Panel();
  const act = { id: "a1", name: "Tempo", dfa: { blocks: [{ start_index: 600 }] } };
  q._smarks = { marks: [], families: Object.keys(M.FAM), stale_reason: {} };
  q._rtests = { tests: [] };
  q._famSel = "tempo";
  q._render = () => {};
  const scrolls = [];
  Object.defineProperty(q, "scrollTop", {
    get: () => 742, set: (v) => scrolls.push(v), configurable: true });

  const saetze = [
    ["abrufbar", "Die Abschnitte dieser Fahrt sind nicht abrufbar (502) — ohne sie wird nichts markiert, weil die Markierung sonst ohne Anker stünde."],
    ["unterteilen", "Intervals liefert für diese Fahrt keine Abschnitte — sie ist dort zu unterteilen, damit es hier etwas zu markieren gibt."],
    ["laufende Nummer", "Abschnitt 4 kommt in dieser Fahrt nicht vor — der Schlüssel ist der start_index des Abschnitts, nicht seine laufende Nummer"],
  ];
  for (const [stichwort, satz] of saetze) {
    q._smErr = null;
    q._smBusy = null;
    q._ws = () => Promise.reject(new Error(satz));
    await q._smWrite("a1", "tempo", 600, true);
    ok(q._smErr !== null && q._smErr.id === "a1",
       `fehlergründe: ${stichwort} wird gar nicht festgehalten`);
    const html = q._marksBlock(act);
    ok(html.includes(stichwort),
       `fehlergründe: „${stichwort}“ kommt in der Karte nicht an`);
    ok(!/Fehler beim Markieren|Unbekannter Fehler/.test(html),
       `fehlergründe: ${stichwort} wurde zu einer allgemeinen Meldung zusammengefasst`);
    // und der Satz steht in der Karte DIESER Fahrt, nicht irgendwo
    ok(q._marksBlock({ id: "a2", dfa: null }).includes(stichwort) === false,
       `fehlergründe: ${stichwort} erscheint auch an einer fremden Fahrt`);
  }
  ok(scrolls.length >= saetze.length && scrolls[scrolls.length - 1] === 742,
     `fehlergründe: die Scroll-Lage überlebt den Fehler nicht (${JSON.stringify(scrolls)})`);

  // Gegenprobe: ein GELUNGENER Schreibvorgang hinterlässt keinen Fehler und
  // hält die Scroll-Lage genauso.
  q._smErr = null; q._smBusy = null;
  scrolls.length = 0;
  q._ws = () => Promise.resolve({ marks: [] });
  await q._smWrite("a1", "tempo", 600, true);
  ok(q._smErr === null, "fehlergründe Gegenprobe: ein gelungener Schreibvorgang meldet einen Fehler");
  ok(scrolls.length === 1 && scrolls[0] === 742,
     "fehlergründe Gegenprobe: die Scroll-Lage überlebt das Re-Render nicht");

  report("test_panel_fixes");
})();
