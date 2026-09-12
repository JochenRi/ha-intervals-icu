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
  contains(p.rHeute(F.today()), "bval", "gestaltung: Bullet-Graph fehlt");
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
  contains(heute, "Zielwahl je Ampelfarbe ist eine Setzung", "belege: Budget ohne Einschränkung");
  contains(p.rDfa(thr, "all"), "Rogers", "belege: DFA ohne Quelle");
}

/* ── die Auswahl trägt eine FORM, nicht nur eine Farbe ─────────────────── */
{
  const q = new M.Panel();
  q._nowIso = F.TODAY;
  q._win.dfa = { id: "all" };
  const pickId = (thr.slice(-10).find((x) => x.samples >= 5 && x.hr > 0) || {}).activity_id;
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

report("test_panel_design");
