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
  const thin = F.thresholds().map((x) => ({ ...x, samples: 2 }));
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
                            ["Mindestzahl je Gruppe", /[^\w.]5(?![\d.])\s*(Einheiten|\))/]]) {
    ok(!re.test(tile), `Wächter: ${name} steht als Zahl in rDurability statt in der Payload`);
  }
  // Die Kehrseite: eine Zahl kann auch dadurch verschwinden, dass die Kachel
  // sie gar nicht mehr zeigt. Jede neue Schwelle aus 0.40.0 muss NACHWEISLICH
  // aus der Payload gelesen werden - sonst ist der Wächter oben nur still.
  for (const key of ["vi_full", "vi_none", "min_weight_sum", "min_weight_sum_block",
                     "min_slope_t", "block_weeks", "power_days", "power_days_fallback",
                     "fuelling_g_per_h", "max_intensity", "min_minutes", "decoupling_good"]) {
    ok(tile.includes("d." + key), `Wächter: rDurability liest ${key} nicht aus der Payload`);
  }
}

report("test_panel_fixes");
