"use strict";
/* Two things this file guards:
 *   1. the cursor - index mapping, edge clamping, gaps read as "–"
 *   2. the design rules the project committed to, expressed as assertions
 *      instead of good intentions (Cleveland & McGill ranking, WCAG 1.4.1,
 *      no dual axes, independent fold-outs, one lead figure per view).
 */

const H = require("./panel_harness");
const F = require("./panel_fixtures");
const { ok, contains, report } = H;

const M = H.load();
const p = new M.Panel();
p._status = { activities: 238, wellness_days: 487, dfa_done: 56, importing: false, athlete: "Test" };
// Pin "today". A window that asks the wall clock makes this suite go red on
// its own some months from now, and a test that fails for calendar reasons
// teaches nothing about the code.
p._nowIso = F.TODAY;
const days = F.days(), load = F.load(), rd = F.readiness(), thr = F.thresholds();
const acts = F.activities();

/* ── cursor ────────────────────────────────────────────────────────────── */
{
  p._grp.pmc = {
    n: 100, xl: (i) => "Tag " + i,
    rows: [
      { l: "Fitness", c: M.ROLE.ctl, vals: Array.from({ length: 100 }, (_, i) => 30 + i * 0.1) },
      { l: "Form", c: M.ROLE.form, vals: Array.from({ length: 100 }, (_, i) => (i % 9 ? 2 - i * 0.05 : null)) },
    ],
  };
  const svg = { dataset: { w: "880", padl: "48", padr: "14" },
                getBoundingClientRect: () => ({ left: 100, top: 50, width: 880, height: 230 }) };
  const lines = p.shadowRoot._lines;
  const g = { dataset: { grp: "pmc" }, querySelector: () => svg, querySelectorAll: () => lines };
  p._fillReadout("pmc", null);
  const strip = p.shadowRoot._strips.pmc;

  p._xhMove(g, { clientX: 100 + 48 + (880 - 48 - 14) * 0.5, clientY: 120 });
  ok(/Tag (49|50|51)/.test(strip._x.textContent), "cursor: Index falsch zugeordnet");
  contains(strip._v.innerHTML, "Fitness", "cursor");
  ok(lines[0]._a.opacity === "0.9", "cursor: Linie nicht sichtbar");

  p._xhMove(g, { clientX: 0, clientY: 120 });
  contains(strip._x.textContent, "Tag 0", "cursor links geklemmt");
  p._xhMove(g, { clientX: 5000, clientY: 120 });
  contains(strip._x.textContent, "Tag 99", "cursor rechts geklemmt");

  p._xhMove(g, { clientX: 100 + 48, clientY: 120 });
  ok(!strip._v.innerHTML.includes("NaN"), "cursor: NaN in der Leiste");
  contains(strip._v.innerHTML, "–", "cursor zeigt Lücke");

  p._xhHide();
  ok(lines[0]._a.opacity === "0", "cursor: Linie bleibt stehen");
  // an unknown group must not throw
  p._xhMove({ dataset: { grp: "gibtsnicht" }, querySelector: () => svg, querySelectorAll: () => lines },
            { clientX: 300, clientY: 120 });
}

/* ── one cursor across stacked panels, never a second axis ─────────────── */
{
  p._streams = { [acts[0].id]: F.streams() };
  const html = p.rAkt(acts, acts[0]);
  const groups = (html.match(/data-grp="str"/g) || []).length;
  ok(groups === 1, `gestaltung: ${groups} Cursor-Gruppen im Detail statt einer`);
  const panels = (html.match(/<svg class="ch"/g) || []).length;
  ok(panels >= 5, "gestaltung: Kanäle nicht als Kleinvielfache gestapelt");
  ok(p._grp.str.rows.length >= 5, "gestaltung: Ablesekasten deckt nicht alle Kanäle ab");

  const dfaHtml = p.rDfa(thr, "all");
  ok((dfaHtml.match(/data-grp="dfa"/g) || []).length === 1, "gestaltung: DFA ohne gemeinsame Zeitachse");
  contains(dfaHtml, "eigenes Feld statt zweiter Achse", "gestaltung");
}

/* ── state is never colour alone (WCAG 1.4.1) ──────────────────────────── */
{
  for (const [key, meta] of Object.entries(M.ST)) {
    ok(typeof meta.word === "string" && meta.word.length > 0, `barrierefreiheit: ${key} ohne Wort`);
    ok(typeof meta.ic === "string" && meta.ic.length > 0, `barrierefreiheit: ${key} ohne eigene Form`);
  }
  const shapes = Object.values(M.ST).map((m) => m.ic);
  ok(new Set(shapes).size === shapes.length, "barrierefreiheit: zwei Zustände teilen dieselbe Icon-Form");
  const html = p.rHeute(F.today());
  // The page now shows ONE situation at a time, so each traffic-light state is
  // driven through its own fixture and has to carry its word next to the colour.
  for (const [state, label, word] of [["ready", "Normalbereich", "grün"],
                                      ["slump", "Einbruch", "rot"],
                                      ["strained", "Beansprucht", "gelb"],
                                      ["unknown", "Keine Aussage", "keine Daten"]]) {
    const page = p.rHeute({ ...F.today(), state, state_label: label });
    contains(page, word, `barrierefreiheit: ${state} ohne Ampelwort`);
    ok(new RegExp(`class="tcard (red|amber|green|blue|grey)`).test(page),
       `barrierefreiheit: ${state} ohne Farbe`);
  }
  // every badge carries an icon next to its word
  const badges = (html.match(/<span class="bdg"/g) || []).length;
  const icons = (html.match(/<span class="bdg"[^>]*>\s*<svg/g) || []).length;
  ok(badges === icons, `barrierefreiheit: ${badges - icons} Badges ohne Form`);
}

/* ── quantity by length on a common baseline, no pies, no gauges ───────── */
{
  const all = [p.rHeute(F.today()), p.rKalender(days), p.rFitness(F.pmc(days), 182),
               p.rBelastung(load), p.rDfa(thr, "all")].join("");
  ok(!/<path[^>]*A\s*[\d.]+\s+[\d.]+[^>]*Z/.test(all.replace(/class="ring"[\s\S]*?<\/svg>/g, "")),
     "gestaltung: Kreissegment außerhalb des Bereitschaftsrings");
  ok(!all.includes("Tacho") && !all.includes("gauge-needle"), "gestaltung: Tachoanzeige");
  // 0.73.0 umgestellt: der Bullet "Obergrenze" (bval) ist dem Summenbalken des
  // Wochenkastens gewichen - weiter Laenge auf gemeinsamer Grundlinie, Ist gegen Zielstrich.
  contains(p.rHeute(F.today()), "hwsumfill", "gestaltung: Bullet-Graph fehlt");
  contains(p.rHeute(F.today()), "hwgoal", "gestaltung: Bullet-Graph ohne Zielstrich");
}

/* ── fold-outs are independent ─────────────────────────────────────────── */
{
  const html = p.rHeute(F.today()) + p.rBelastung(load);
  ok(!html.includes("<details name="), "gestaltung: Aufklappfelder gekoppelt");
  ok(!html.includes("<details open"), "gestaltung: Aufklappfeld vorab geöffnet");
  const det = (html.match(/<details/g) || []).length;
  ok(det >= 6, `gestaltung: nur ${det} Aufklappfelder - Quellen stehen als Textwand daneben`);
  // the intent behind that number: METHOD text belongs behind a fold, never
  // loose on the page - the Heute rebuild is where this could slip
  const heutePage = p.rHeute(F.today());
  const loose = heutePage.slice(0, heutePage.indexOf("<details"));
  ok(!/vierzehn Bereitschaftswerten/.test(loose),
     "gestaltung: Methodik steht offen auf der Seite statt eingeklappt");
  ok(!/Belastung außerhalb des Trainings/.test(loose),
     "gestaltung: Horizont-Erklärung steht offen auf der Seite");
}

/* ── one lead figure per view ──────────────────────────────────────────── */
{
  const views = { dfa: p.rDfa(thr, "all"), heute: p.rHeute(F.today()) };
  ok((views.dfa.match(/lead1/g) || []).length === 1, "gestaltung: DFA ohne genau eine Leitzahl");
  // the lead figure is no longer a ring - it is the sentence that answers the
  // question, and there must be exactly one of it
  ok((views.heute.match(/class="tbig"/g) || []).length === 1,
     "gestaltung: Heute ohne genau eine Leitanzeige");
  ok(!/class="ring"/.test(views.heute), "gestaltung: Bereitschaftsring wieder da");
}

/* ── sources stay attached to every derived number ─────────────────────── */
{
  const bel = p.rBelastung(load);
  for (const src of ["Foster", "Gabbett", "Seiler", "Friel", "ln(rMSSD)"]) contains(bel, src, "belege");
  const heute = p.rHeute(F.today());
  // 0.73.0 umgestellt: die Einschraenkung steht jetzt in der Fusszeile des Wochenkastens.
  contains(heute, "eine Festlegung, keine Messung", "belege: Budget ohne Einschränkung");
  // F2.10 (0.67.3) -> 0.73.0 umgestellt: Grenze und Verbrauch getrennt. Der Verbrauch
  // steckt in "Zusammen N Last" (Fensterlast mit heute), die Grenze im Urteil;
  // deckelt der Zustand, stehen beide Zahlen da.
  {
    const tq = new M.Panel(); tq._nowIso = F.TODAY;
    const tt = F.today(); tt.week = F.week("zustand");
    const h2 = String(tq.rHeute(tt)).replace(/\s+/g, " ");
    contains(h2, "Die Woche hätte noch 86 frei", "heute: der Wochenrest steht nicht neben der Zustandsgrenze");
    contains(h2, "Heute höchstens 75 Last", "heute: die Obergrenze fehlt");
    contains(h2, "Zusammen 170 Last", "heute: der Verbrauch der Woche fehlt");
  }
  contains(p.rDfa(thr, "all"), "Rogers", "belege: DFA ohne Quelle");
  ok(!/Rogers und Gronwald(?! 2021a\/b)/.test(p.rDfa(thr, "all")), "belege: DFA-Quelle ohne Arbeit und Sportart");
  // Die zweite Stelle steht im Aktivitätsdetail (_dfaBlock), nicht im Reiter.
  const dfaBlock = p._dfaBlock({ samples: 100, secs_aerobic: 60, secs_transition: 30, secs_anaerobic: 10 });
  contains(dfaBlock, "Rogers und Gronwald", "belege Trefferzusicherung: der DFA-Block im Aktivitätsdetail ist nicht gerendert");
  ok(!/Rogers und Gronwald(?! 2021a\/b)/.test(dfaBlock), "belege: DFA-Block im Aktivitätsdetail ohne Arbeit und Sportart");
}

/* ── die Auswahl trägt eine FORM, nicht nur eine Farbe ─────────────────── */
{
  const q = new M.Panel();
  q._nowIso = F.TODAY;
  q._win.dfa = { id: "all" };
  const pickId = (thr.slice(-10).find((x) => x.hr_usable && x.power_usable) || {}).activity_id;
  const plain = q.rDfa(thr, "all");
  q._dfaPick = pickId;
  const marked = q.rDfa(thr, "all");

  // WCAG 1.4.1: the mark may not rest on colour. It is a ring - an extra,
  // unfilled circle - plus a larger radius.
  ok(!/class="pickring"/.test(plain), "auswahl: Ring ohne Auswahl gezeichnet");
  ok(/class="pickring"[^>]*fill="none"/.test(marked), "auswahl: kein Ring als eigene Form");
  // BOTH fields carry the ring - HR and power. Counting instead of merely
  // asking "is there one" matters: with a single existence check, the ring in
  // the power field covered the loss of the ring in the HR field, and the
  // mutation slipped through.
  const rings = (String(marked).match(/class="pickring"/g) || []).length;
  ok(rings === 2, "auswahl: Ring nicht in beiden Feldern (" + rings + " statt 2)");
  const ringR = (String(marked).match(/class="pickring"[^>]*r="([\d.]+)"/) || [])[1];
  ok(+ringR > 6, "auswahl: Ring nicht größer als der Punkt (r=" + ringR + ")");
  const radii = (h) => (String(h).match(/<circle [^>]*data-dot="[^"]*"[^>]*r="([\d.]+)"/g) || []);
  ok(radii(marked).length > 0, "auswahl: keine markierbaren Punkte");
  ok(/r="6"/.test(marked), "auswahl: Treffer nicht vergrößert");
  // de-emphasis, not emphasis: the OTHERS get dimmer
  ok(/opacity="0.35"/.test(marked), "auswahl: übrige Punkte nicht abgedunkelt");
  ok(!/opacity="0.35"/.test(plain), "auswahl: Punkte ohne Auswahl abgedunkelt");
  // the ring uses the SAME colour as the point - colour carries nothing here
  const ringCol = (String(marked).match(/class="pickring"[^>]*stroke="([^"]*)"/) || [])[1];
  ok(ringCol === M.ROLE.series, "auswahl: Ring führt eine eigene Farbe ein");
  // and the row says it in words, not only in pixels
  contains(marked, "Ausgewählt:", "auswahl: nicht benannt");
}

/* ── aufgeklappt ist ein Diagramm und braucht eine Achse ───────────────── */
{
  const q = new M.Panel();
  q._nowIso = F.TODAY;
  const closed = q.rHeute(F.today());
  q._sigOpen = "hrv";
  const open = q.rHeute(F.today());
  // the sparkline may go without an axis; the diagram may not
  ok(!/class="ax">\d\d\.\d\d\.</.test(closed), "achse: Datumsachse schon in der Sparkline");
  ok(/class="ax">\d\d\.\d\d\.</.test(open), "achse: aufgeklappte Karte ohne Datumsachse");
  // fixed strip in the card head, never a floating box
  contains(open, 'data-rdo="tsig_hrv"', "achse: kein fester Ablesestreifen");
  ok(!/class="xhbox"/.test(open), "achse: schwebender Ablesekasten wieder da");
  // the event track keeps the two registers apart: training is a CATEGORY
  // (slate), a state is a JUDGMENT (amber/red) - and each state has its own
  // shape as well, so the track works without colour vision
  const track = (String(open).match(/<svg class="ch evtrack"[\s\S]*?<\/svg>/) || [""])[0];
  ok(track.includes(M.C.slate), "spur: Trainingstage nicht im Kategorienregister");
  ok(!track.includes(M.C.green), "spur: Urteilsgrün in der Kategorienspur");
  ok(/<path d="M[^"]*Z" fill="/.test(track) || /<rect [^>]*rx="1"/.test(track),
     "spur: Zustände ohne eigene Form");
  contains(open, "Trainingstag", "spur: keine Direktbeschriftung");
}

/* ── Etiketten-Chips: Kategorienregister, nie das Urteilsregister ────────── */
{
  // Etiketten sind Kategorien (Messbedingungen), keine Urteile. Ein
  // "krank"-Chip in Urteilsrot wäre eine Diagnose, wo nur eine Bedingung
  // gemeint ist. Die zwei Register mischen sich nie.
  const judgment = [M.C.green, M.C.amber, M.C.red];
  const cats = Object.entries(M.CTX_COLOR);
  // 0.72.1 UMGESTELLT: statt einer festen 7 gegen die Etiketten des Moduls
  // (day_context.TAGS) - jedes Etikett genau eine Farbe, keine uebrig.
  const dcSrc = require("fs").readFileSync(require("path").join(__dirname, "..", "custom_components",
    "intervals_icu", "day_context.py"), "utf8");
  const slugs = [...dcSrc.slice(dcSrc.indexOf("TAGS: dict"), dcSrc.indexOf("VALID_WEIGHTS"))
    .matchAll(/^    "(\w+)": \{"label"/gm)].map((m) => m[1]).sort();
  ok(slugs.length >= 8 && JSON.stringify(cats.map(([k]) => k).sort()) === JSON.stringify(slugs),
     `register: Etikettenfarben ${cats.map(([k]) => k).sort()} passen nicht zu den Etiketten ${slugs}`);
  for (const [slug, col] of cats) {
    ok(!judgment.includes(col), `register: Etikett ${slug} trägt eine Urteilsfarbe`);
  }
  ok(new Set(cats.map(([, c]) => c)).size === cats.length,
     "register: zwei Etiketten teilen sich eine Farbe");

  // Die Auswahl im Dialog trägt Form UND Wort neben der Farbe (WCAG 1.4.1,
  // dieselbe Regel wie überall sonst im Panel).
  const q = new M.Panel();
  q._nowIso = F.TODAY;
  q._dayctx = F.dayContext();
  q._ctxDlg = "2026-09-10";
  const dlg = q._ctxPopover();
  ok(/class="ctxchip on"/.test(dlg) && /gewählt/.test(dlg),
     "register: Auswahl ohne Wort neben der Farbe");
  ok(/class="csel"><svg/.test(dlg.replace(/\s+/g, "")) || /csel">\s*<svg/.test(dlg),
     "register: Auswahl ohne Form (Haken)");
  // und der Marker in den Tageszellen ist eine FORM (Etikett-Icon), kein Punkt
  const cell = q._dayCell({ date: "2026-09-10", weekday: 3, week: "2026-W37" }, F.TODAY);
  ok(/ctxmark[^>]*>\s*<svg/.test(cell), "register: Tagesmarker ohne eigene Form");
}

/* ── eingefrorene Referenz: chart() im Indexmodus ──────────────────────────
   chart() traegt vier Ansichten gleichzeitig (DFA, Fitness, Signalkarten,
   Streams). Als die stetige x-Achse fuer die Durability-Wolke dazukam, war die
   Gefahr nicht die neue Option, sondern die alte: eine Zeile im gemeinsamen
   Helfer reisst alles vier auf einmal auf. Die Hashes unten stammen aus dem
   Stand VOR dem Eingriff (0.39.0, git HEAD) - nicht aus dem neuen Code, sonst
   bewiese die Referenz nur sich selbst. Aendert sich hier eine Ziffer, ist es
   eine Entscheidung und keine Nebenwirkung. */
/* Option sets that between them touch every branch of chart(): bars, line,
   area, dots with ring/hollow/id, bands, marker lines on both sides, own y
   ticks, x ticks and labels, direct tags, crosshair group, padding overrides.
   If any of them moves, a shared helper has moved four views at once. */
const CHART_CASES = (C, ROLE) => [
  ["balken", { h: 120, n: 12, y0: 0, y1: 100, s: [{ t: "bars", v: [5, 20, null, 60, 80, 12, 0, 44, 91, 7, 33, 58], c: C.blue }] }],
  ["linie+flaeche", { h: 200, n: 10, y0: -5, y1: 25, label: "Last", labelc: ROLE.ctl,
    s: [{ t: "area", v: [1, 3, null, 8, 9, 12, 4, null, 6, 2], c: ROLE.ctl, w: 2.4 },
        { t: "line", v: [2, null, 4, 4, null, 9, null, 7, 7, 1], c: ROLE.form, d: "4 3", lop: 0.7 }] }],
  ["punkte", { h: 260, n: 8, y0: 100, y1: 180, grp: "dfa",
    s: [{ t: "dots", c: C.violet, p: [
      { i: 0, v: 120 }, { i: 1, v: 150, r: 5.4, op: 0.35, ring: true, id: "a1" },
      { i: 3, v: 133, f: false, c: C.cyan }, { i: 7, v: 171, id: "a2" }] }] }],
  ["baender+marken", { h: 150, n: 6, y0: 0, y1: 10, ym: 4,
    bands: [{ a: 0, b: 3, c: C.green }, { a: 8, b: 10, c: C.amber, op: 0.25 }],
    hl: [{ y: 5, c: C.tx3, d: 1, t: "Marke" }, { y: 2, c: C.blue, t: "links", side: "left" }],
    s: [{ t: "line", v: [1, 2, 3, 4, 5, 6], c: C.blue }] }],
  ["achsen+tags", { h: 180, n: 14, y0: 0, y1: 50, yticks: [0, 25, 50], padL: 60, padR: 30, padT: 14, padB: 28,
    xtick: [0, 7, 13], xt: [{ i: 0, t: "Mo" }, { i: 7, t: "Di" }],
    extra: `<rect x="0" y="0" width="10" height="10" fill="${C.slate}"/>`,
    tags: [{ i: 13, v: 40, c: C.magenta, t: "jetzt" }, { i: 5, v: null, c: C.blue, t: "leer" }],
    s: [{ t: "line", v: Array.from({ length: 14 }, (_, i) => (i === 3 ? null : i * 3)), c: C.magenta }] }],
  ["einzelpunkt", { h: 100, n: 5, y0: 0, y1: 4, s: [{ t: "line", v: [null, 2, null, null, null], c: C.cyan, w: 3 }] }],
  ["entartet", { h: 90, n: 2, y0: 0, y1: 0, s: [{ t: "bars", v: [0, 0], c: C.tx3 }] }],
];

const CHART_FROZEN = {
  "balken": "fc1847362004b490",
  "linie+flaeche": "6d27329449e3266a",
  "punkte": "2ebf764f5188790b",
  "baender+marken": "1675ce0e5cce397a",
  "achsen+tags": "02f3b31909f26373",
  "einzelpunkt": "979f81d9c497589d",
  "entartet": "424d00566c7e5e0a",
};
{
  const sha = (t) => require("crypto").createHash("sha256").update(t).digest("hex").slice(0, 16);
  const cases = CHART_CASES(M.C, M.ROLE);
  ok(cases.length === Object.keys(CHART_FROZEN).length,
     `chart-referenz: ${cases.length} Faelle gegen ${Object.keys(CHART_FROZEN).length} eingefrorene Hashes`);
  for (const [name, o] of cases) {
    const out = M.chart(o);
    ok(sha(out) === CHART_FROZEN[name],
       `chart-referenz "${name}": Ausgabe hat sich geaendert (${sha(out)} statt ${CHART_FROZEN[name]}, ${out.length} Zeichen)`);
    ok(!/data-x0/.test(out), `chart-referenz "${name}": xy-Attribute im Indexmodus`);
  }
}

/* ── die stetige x-Achse: nur wenn x0/x1 gesetzt sind ──────────────────── */
{
  const idx = M.chart({ h: 100, n: 3, y0: 0, y1: 10,
    s: [{ t: "dots", c: M.C.blue, p: [{ i: 0, v: 5 }, { i: 2, v: 5 }] }] });
  const xy = M.chart({ h: 100, n: 3, y0: 0, y1: 10, x0: 0, x1: 1000,
    s: [{ t: "dots", c: M.C.blue, p: [{ x: 0, v: 5 }, { x: 1000, v: 5 }] }] });
  const cx = (t) => [...String(t).matchAll(/<circle cx="([\d.]+)"/g)].map((m) => +m[1]);
  // Endpunkte identisch: die Achse ist dieselbe Flaeche, nur anders adressiert
  ok(JSON.stringify(cx(idx)) === JSON.stringify(cx(xy)),
     `stetige achse: Randpunkte liegen nicht auf denselben Stellen (${cx(idx)} gegen ${cx(xy)})`);
  // und ein Punkt bei einem Viertel der Arbeit liegt auf einem Viertel der
  // Flaeche - im Indexmodus waere er in der Mitte gelandet, weil er der
  // zweite von dreien ist. Genau dafuer gibt es den Modus.
  const q = M.chart({ h: 100, n: 3, y0: 0, y1: 10, x0: 0, x1: 1000,
    s: [{ t: "dots", c: M.C.blue, p: [{ x: 0, v: 5 }, { x: 250, v: 5 }, { x: 1000, v: 5 }] }] });
  const [a, b, c] = cx(q);
  ok(Math.abs((b - a) / (c - a) - 0.25) < 0.001,
     `stetige achse: Punktdichte wird nicht abgebildet (${((b - a) / (c - a)).toFixed(3)} statt 0.250)`);
  contains(xy, 'data-x0="0"', "stetige achse: x0 fehlt am svg");
  contains(xy, 'data-y1="10"', "stetige achse: y1 fehlt am svg");
}

/* ── Zeiger: die vier bestehenden Gruppen laufen unveraendert ──────────── */
{
  const mkG = (name) => {
    const svg = { dataset: { w: "880", padl: "48", padr: "14" },
                  getBoundingClientRect: () => ({ left: 100, top: 50, width: 880, height: 230 }) };
    return { dataset: { grp: name }, querySelector: () => svg, querySelectorAll: () => p.shadowRoot._lines };
  };
  for (const [name, n] of [["sig", 60], ["pmc", 100], ["str", 240], ["dfa", 8]]) {
    p._grp[name] = { n, xl: (i) => "P" + i,
      rows: [{ l: "x", c: M.C.blue, u: "", vals: Array.from({ length: n }, (_, i) => i) }] };
    const g = mkG(name);
    for (let k = 0; k <= 20; k++) {
      const localX = 48 + ((880 - 48 - 14) * k) / 20;
      const want = Math.max(0, Math.min(n - 1, Math.round((localX - 48) / (880 - 48 - 14) * (n - 1))));
      const got = p._xhMove(g, { clientX: 100 + localX, clientY: 120 });
      ok(got === want, `zeiger ${name}: Index ${got} statt ${want} bei ${k}/20 - der Indexpfad wurde angefasst`);
    }
  }
}

/* ── Zeiger in der Wolke: naechster Punkt in ZWEI Richtungen ───────────── */
{
  const svg = { dataset: { w: "880", padl: "48", padr: "14", padt: "8", padb: "22", h: "260",
                           x0: "0", x1: "1000", y0: "0", y1: "10" },
                getBoundingClientRect: () => ({ left: 100, top: 50, width: 880, height: 260 }) };
  const g = { dataset: { grp: "dur" }, querySelector: () => svg, querySelectorAll: () => p.shadowRoot._lines };
  // zwei Fahrten mit derselben Arbeit und verschiedener Entkopplung: ueber x
  // allein waeren sie nicht zu trennen
  p._grp.dur = { xy: true, n: 3, xl: (i) => "F" + i,
    pts: [{ x: 500, y: 1 }, { x: 500, y: 9 }, { x: 900, y: 5 }],
    rows: [{ l: "Entkopplung", c: M.C.blue, u: "%", vals: [1, 9, 5] }] };
  const PX = (v) => 48 + (v / 1000) * (880 - 48 - 14);
  const PY = (v) => 8 + (1 - v / 10) * (260 - 8 - 22);
  ok(p._xhMove(g, { clientX: 100 + PX(500), clientY: 50 + PY(1.2) }) === 0,
     "wolke: unterer von zwei Punkten auf derselben Arbeit nicht getroffen");
  ok(p._xhMove(g, { clientX: 100 + PX(500), clientY: 50 + PY(8.8) }) === 1,
     "wolke: oberer von zwei Punkten auf derselben Arbeit nicht getroffen");
  const strip = p.shadowRoot._strips.dur;
  ok(/F1/.test(strip._x.textContent), `wolke: Ableseleiste zeigt nicht den getroffenen Punkt (${strip._x.textContent})`);
  ok(/\b9\b/.test(strip._v.innerHTML), "wolke: Wert des getroffenen Punktes fehlt in der Leiste");
  ok(p._xhMove(g, { clientX: 100 + PX(880), clientY: 50 + PY(5) }) === 2,
     "wolke: rechter Punkt nicht getroffen");
}

/* ── Urteilsregister: VIER Stufen seit 0.42.0 (docs/ausbau.md I6) ──────────
   Vier Stufen heißt vier Wörter, vier Formen, vier Töne - nicht drei plus eine
   Schattierung. Und der vierte Ton darf in KEINEM der beiden Kategorienregister
   stehen, sonst ist die Trennung, die diese Datei seit 0.7.0 erzwingt, genau an
   der neuen Stelle aufgegeben. */
{
  const grades = ["green", "amber", "stimulus", "red"];
  const tones = grades.map((k) => M.ST[k] && M.ST[k].c);
  const words = grades.map((k) => M.ST[k] && M.ST[k].word);
  const shapes = grades.map((k) => M.ST[k] && M.ST[k].ic);

  ok(tones.every(Boolean), "urteilsregister: eine der vier Stufen fehlt");
  ok(new Set(tones).size === 4, "urteilsregister: zwei Stufen teilen sich einen Ton");
  ok(new Set(words).size === 4, "urteilsregister: zwei Stufen teilen sich ein Wort");
  ok(new Set(shapes).size === 4, "urteilsregister: zwei Stufen teilen sich eine Form");
  ok(M.ST.stimulus.word === "Reiz", "urteilsregister: die vierte Stufe heißt nicht Reiz");

  // Der vierte Ton steht in KEINEM Kategorienregister - weder in den
  // Datenrollen noch in den Sportfarben noch in den Etiketten.
  const categories = [
    ...Object.values(M.ROLE),
    ...Object.values(M.SPORT).map((s) => s.c),
    ...Object.values(M.CTX_COLOR),
  ];
  ok(!categories.includes(M.C.orange),
     "urteilsregister: der Reiz-Ton steht auch im Kategorienregister");
  for (const tone of tones) {
    ok(!categories.includes(tone), `urteilsregister: ${tone} ist zugleich eine Kategorie`);
  }
  // Gegenprobe: der Wächter muss einen echten Mischfall auch finden
  ok([...categories, M.C.orange].includes(M.C.orange),
     "urteilsregister Gegenprobe: ein eingebauter Mischfall wird NICHT gefunden — blind");

  // Die Form der Reiz-Stufe ist eine EIGENE, keine Variante des Last-Blitzes.
  // Ohne diese Prüfung greift beim nächsten Icon wieder jemand zum bolt, und
  // dann trägt ein Urteil die Form einer Kategorie.
  ok(M.ST.stimulus.ic !== "bolt", "urteilsregister: die Reiz-Stufe benutzt das Last-Icon");
  ok(M.IC[M.ST.stimulus.ic], "urteilsregister: die Form der Reiz-Stufe ist nicht definiert");
  ok(M.IC[M.ST.stimulus.ic] !== M.IC.bolt,
     "urteilsregister: die Reiz-Form ist mit dem Blitz identisch");
  // und sie ist auch keine Variante der drei anderen Urteilsformen
  for (const other of ["ok", "warn", "stop", "na"]) {
    ok(M.IC[M.ST.stimulus.ic] !== M.IC[other],
       `urteilsregister: die Reiz-Form ist eine Kopie von ${other}`);
  }
  // keine doppelten Schlüssel im Formenkatalog - ein zweites bolt: würde das
  // erste still überschreiben
  const keys = (H.source().match(/const IC = \{[\s\S]*?\n\};/) || [""])[0]
    .split("\n").map((line) => (line.match(/^\s{2}([a-z]+)\s*:/) || [])[1]).filter(Boolean);
  ok(new Set(keys).size === keys.length, "urteilsregister: doppelter Schlüssel im Formenkatalog");

  // Die Übersetzung Backend-Schlüssel -> Registerschlüssel steht EINMAL
  ok(Object.keys(M.STAGE_TONE).length === 4, "urteilsregister: STAGE_TONE hat nicht vier Einträge");
  ok(M.STAGE_TONE.yellow === "amber" && M.STAGE_TONE.stimulus === "stimulus",
     "urteilsregister: die Übersetzung stimmt nicht");
}

/* ── der Satz für spätere Wochen trägt KEIN Urteil ─────────────────────────
   Die Abwesenheit eines Urteils ist kein fünfter Zustand (docs/ausbau.md I3).
   Er darf deshalb weder eine Urteilsfarbe noch eine Urteilsform tragen. */
{
  const q = new M.Panel();
  q._nowIso = F.TODAY;
  q._planOpen = "3";
  const html = q.rPlanWeeks(F.goal());
  const start = html.indexOf("noverdict");
  ok(start > 0, "späte Wochen: der Satz fehlt ganz");
  const sentence = html.slice(start, start + 600);
  for (const grade of ["green", "amber", "orange", "red"]) {
    ok(!sentence.includes(M.C[grade]),
       `späte Wochen: der Satz trägt die Urteilsfarbe ${grade}`);
  }
  for (const shape of ["ok", "warn", "stop", "surge"]) {
    ok(!sentence.includes(M.IC[shape]),
       `späte Wochen: der Satz trägt die Urteilsform ${shape}`);
  }
}

/* ── E1: der Kalender bleibt im Bild ──────────────────────────────────────
   `1fr` ist `minmax(auto, 1fr)` - die Spalte darf NICHT unter ihre
   Inhaltsbreite schrumpfen, und ein langer Aktivitätsname schob damit das
   ganze Raster nach rechts aus dem Fenster. Drei Teile, keiner allein
   reicht (docs/ausbau.md E1). */
{
  const css = H.source();
  const grids = css.split("\n").filter((line) =>
    /^\.(wkrow|calhead|tweek)\{/.test(line.trim()) && /grid-template-columns/.test(line));
  ok(grids.length === 3, `kalender: ${grids.length} statt 3 Rasterregeln gefunden`);
  for (const rule of grids) {
    ok(/repeat\(7,\s*minmax\(0,\s*1fr\)\)/.test(rule),
       `kalender: ${rule.slice(0, 18)} schrumpft nicht unter die Inhaltsbreite`);
    ok(!/repeat\(7,\s*1fr\)/.test(rule),
       `kalender: ${rule.slice(0, 18)} benutzt weiter 1fr`);
  }
  // Gegenprobe: der Wächter muss ein wiedereingebautes 1fr auch finden
  ok(/repeat\(7,\s*1fr\)/.test(".wkrow{display:grid;grid-template-columns:190px repeat(7,1fr)}"),
     "kalender Gegenprobe: ein wiedereingebautes 1fr wird NICHT gefunden — der Wächter ist blind");

  // zweiter Teil: dieselbe Sperre eine Ebene tiefer
  for (const sel of [".wkrow>*", ".day{", ".chip{", ".chip .cn{"]) {
    const line = css.split("\n").find((l) => l.trim().startsWith(sel));
    ok(line && /min-width:\s*0/.test(line + (css.split(sel)[1] || "").slice(0, 160)),
       `kalender: ${sel} ohne min-width:0 — die Zelle wird von innen aufgeschoben`);
  }

  // dritter Teil: gekürzt, aber nicht verloren
  const q = new M.Panel();
  q._nowIso = F.TODAY;
  q._dayctx = F.dayContext();
  const longName = "Lange Ausfahrt über Steinhuder Meer und zurück mit Gegenwind";
  const cell = q._dayCell({
    date: "2026-09-10", weekday: 3, week: "2026-W37", load: 120,
    activities: [{ id: "x", name: longName, type: "Ride", moving_time: 7200, load: 120 }],
  }, F.TODAY);
  ok(/text-overflow/.test(css), "kalender: keine Kürzung mit Auslassungspunkten im CSS");
  contains(cell, `title="${longName}"`, "kalender: der volle Name fehlt im title-Attribut");
  contains(cell, longName, "kalender: der Name fehlt ganz");
  // Gegenprobe: ohne title wäre der gekürzte Name Informationsverlust
  ok(!/title="/.test('<span class="cn">x</span>'),
     "kalender Gegenprobe: ein fehlendes title wird NICHT bemerkt — der Wächter ist blind");
}

/* ── Die vier Zuordnungs-Familien (docs/ausbau.md P2a) ────────────────────
   FORM UND KUERZEL tragen die Identitaet, die Farbe verstaerkt. Der Grund
   steht am Code: ROLE belegt im Aktivitaetsdetail pow/hr/dfa/cad/vel/alt,
   also alle sechs Toene des Datenregisters. Eine Farbe allein koennte hier
   nichts tragen, was nicht schon vergeben waere - also muessen Form und
   Kuerzel eindeutig sein, und das wird hier erzwungen. */
{
  const fams = Object.entries(M.FAM);
  // VIER seit 15.09.2026: "Schwelle" und "lange Fahrt" sind stillgelegt
  // (section_marks.RETIRED). Die Zahl steht hier hart, damit eine fuenfte
  // Kachel nicht unbemerkt dazukommt.
  ok(fams.length === 4, `familien: ${fams.length} statt 4`);

  const judgment = [M.C.green, M.C.amber, M.C.orange, M.C.red];
  const categories = [M.C.blue, M.C.violet, M.C.cyan, M.C.magenta, M.C.slate, M.C.deep];
  for (const [key, f] of fams) {
    ok(!judgment.includes(f.c), `familien: ${key} trägt eine Urteilsfarbe`);
    ok(categories.includes(f.c), `familien: ${key} trägt keine Farbe des Kategorienregisters`);
    ok(typeof f.k === "string" && f.k.length >= 2 && f.k.length <= 4,
       `familien: ${key} hat kein Kürzel von zwei bis vier Zeichen (${f.k})`);
    ok(!!M.IC[f.ic], `familien: die Form von ${key} steht nicht im Katalog (${f.ic})`);
  }

  // Formen und Kuerzel PAARWEISE verschieden - und die Form keine Variante
  // einer anderen, auch keiner aus dem Urteilsregister.
  const shapes = fams.map(([, f]) => M.IC[f.ic]);
  const kurz = fams.map(([, f]) => f.k);
  ok(new Set(shapes).size === shapes.length, "familien: zwei Familien teilen sich eine Form");
  ok(new Set(kurz).size === kurz.length, "familien: zwei Familien teilen sich ein Kürzel");
  for (const grade of ["ok", "warn", "stop", "na", "surge"]) {
    for (const [key, f] of fams) {
      ok(M.IC[f.ic] !== M.IC[grade],
         `familien: die Form von ${key} ist mit der Urteilsform ${grade} identisch`);
    }
  }
  // Und sie sind keine Kreis-, Dreieck- oder Rautengrundform: die gehoeren
  // dem Urteilsregister, und eine Kategorie, die so aussieht, ist eine
  // Variante davon.
  for (const [key, f] of fams) {
    ok(!/<circle/.test(M.IC[f.ic]),
       `familien: die Form von ${key} benutzt die Kreisgrundform des Urteilsregisters`);
  }

  // GEGENPROBE, gezaehlt und benannt: eine eingebaute Dublette muss fallen.
  // Ohne sie prueft die Verschiedenheit oben nur, dass vier Werte vier
  // Werte sind.
  const dubForm = shapes.slice();
  dubForm[3] = dubForm[1];
  ok(dubForm[3] === dubForm[1], "familien Gegenprobe: die Dublette wurde gar nicht eingebaut");
  ok(new Set(dubForm).size !== dubForm.length,
     "familien Gegenprobe: eine doppelte Form wird NICHT gefunden — der Wächter ist blind");
  const dubK = kurz.slice();
  dubK[2] = dubK[0];
  ok(new Set(dubK).size !== dubK.length,
     "familien Gegenprobe: ein doppeltes Kürzel wird NICHT gefunden — der Wächter ist blind");
  const dubJudge = [M.C.green];
  ok(dubJudge.some((c) => judgment.includes(c)),
     "familien Gegenprobe: eine eingebaute Urteilsfarbe wird NICHT gefunden");

  // Welche Familien ueber Bloecke messen, steht an EINER Stelle und deckt
  // sich mit dem Register.
  for (const key of M.FAM_BLOCKS) {
    ok(!!M.FAM[key], `familien: FAM_BLOCKS nennt ${key}, das Register kennt es nicht`);
  }
  ok(M.FAM_BLOCKS.length === 3,
     `familien: ${M.FAM_BLOCKS.length} statt 3 Familien messen über Blöcke`);
  for (const key of ["endurance"]) {
    ok(!M.FAM_BLOCKS.includes(key),
       `familien: ${key} misst über den Stundenverlauf, nicht über Blöcke`);
  }
}

/* ── 0.73.3 · toter Code entfernt, die Leser rendern gleich (Skizze 0.73.3 §2) ── */
{
  const src = H.source();
  ok(!/^function bullet\(/m.test(src) && typeof M.bullet === "undefined", "0.73.3: function bullet(b) steht noch (kein Aufrufer)");
  for (const [re, name] of [[/^\.bullet\{/m, ".bullet"], [/^\.bband\{/m, ".bband"], [/^\.bval\{/m, ".bval"],
                            [/^\.bmark\{/m, ".bmark (ohne .bbar)"], [/^\.tstate\{display:flex/m, ".tstate{display:flex} (Trainer)"],
                            [/^\.tcard \.tstate\{display:block\}/m, ".tcard .tstate{display:block}"]]) {
    ok(!re.test(src), `0.73.3: CSS-Regel ${name} steht noch`);
  }
  ok(!/class="bval"|class="bband"|class="bullet"/.test(src), "0.73.3: ein Leser der entfernten Klassen ist aufgetaucht");
  // die Leser bleiben: .bbar .bmark regiert jede .bmark, die Grundregel des Heute-Zustands bleibt
  ok(/^\.bbar \.bmark\{position:absolute;top:-2px;bottom:-2px;width:3px;margin-left:-1\.5px;border-radius:2px;background:\$\{ROLE\.series\}\}$/m.test(src),
     "0.73.3: die Regel .bbar .bmark hat sich veraendert");
  ok(/^\.tstate\{border-left:1px solid \$\{C\.line\};padding-left:18px\}$/m.test(src), "0.73.3: die Grundregel .tstate des Heute-Kopfs fehlt");
  ok((src.match(/class="bmark"/g) || []).length === 2 && (src.match(/<div class="bbar">\s*<i class="brange"[^>]*>\s*<\/i>\s*<i class="bmark"/g) || []).length === 2,
     "0.73.3: eine .bmark steht nicht mehr in einer .bbar (dann gaelte keine Regel)");
  ok((src.match(/class="tstate"/g) || []).length === 1, "0.73.3: .tstate hat einen weiteren Leser (Trainer?)");
  // vorher/nachher gleiche HTML-Ausgabe der betroffenen Render-Funktionen (Stand 0.73.2)
  const crypto = require("crypto");
  const T = new M.Panel(); T._nowIso = "2026-09-26";
  const b = F.blocks({ steering_on: true });
  const snap = {
    heute: T.rHeute({ ...F.today(), week: F.week("voll") }),
    morgen: T.rHeute({ ...F.today(), week: F.week("morgen") }),
    fatigue: T.rFatigue(F.fatigue({ v2: F.fatigueV2Block() })),
    fam: Object.keys(b.families).map((k) => T._famValue(b, k)).join(""),
  };
  // 0.74.3 neu gesetzt (heute, morgen): gewollte Aenderung NUR im Nacht-Abschnitt und in der Unterzeile
  // "Woher das kommt" (SKIZZE_0.74.3 §3.2) - am 26.09. belegt: die Seiten aus 0.74.2 und 0.74.3 sind ohne
  // diese beiden Stellen bytegleich. Alt: heute c0e0160b2f28b892, morgen 37e1c5d4c152e165.
  // 0.74.4 neu gesetzt (heute, morgen): gewollte Aenderung NUR im Nacht-Abschnitt und in der Unterzeile
  // "Woher das kommt" (SKIZZE_0.74.4 §3.1) - am 26.09. belegt: die Seiten aus 0.74.3 und 0.74.4 sind ohne
  // diese beiden Stellen bytegleich. Alt: heute 89402e5e426ca50b, morgen 5a201f797dfbe231.
  const want = { heute: "17f4431d9ad8ca41", morgen: "1f0bc2dd6f25d768", fatigue: "47bfaad6a9fe54e0", fam: "5b827b517a726ee0" };
  for (const [k, v] of Object.entries(snap)) {
    ok(crypto.createHash("sha256").update(String(v)).digest("hex").slice(0, 16) === want[k],
       `0.73.3: ${k} rendert anders als in 0.73.2 (Momentaufnahme; bei gewollter Aenderung neu setzen)`);
  }
  ok((snap.fatigue.match(/class="bmark"/g) || []).length === 1 && (snap.fam.match(/class="bmark"/g) || []).length === 2,
     "0.73.3 Treffer: die .bmark-Leser (:1504/:1816) sind nicht in der Momentaufnahme");
}

report("test_panel_design");
