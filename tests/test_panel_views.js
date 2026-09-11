"use strict";
/* Every view against full, empty, gappy and degenerate payloads. The panel
 * has to render something honest in each case - never "undefined", never a
 * blank page, never a crash. */

const H = require("./panel_harness");
const F = require("./panel_fixtures");
const { ok, clean, contains, report } = H;

const M = H.load();
const p = new M.Panel();
p._status = { activities: 238, wellness_days: 487, dfa_done: 56, importing: false, athlete: "Test" };

const days = F.days(), gappy = F.days({ holes: true });
const load = F.load(), rd = F.readiness(), acts = F.activities();
const thr = F.thresholds(), cal = F.calendar(), pmc = F.pmc(days);

const EMPTY_DAYS = { today: F.TODAY, days: [], weeks: [], max_week_load: 0, avg_week_load: 0 };
const EMPTY_LOAD = { weeks: [], acwr: [], acwr_latest: null, intensity: null,
                     dfa_distribution: null, decoupling: [], hrv: null, thresholds: {} };

/* ── Heute ────────────────────────────────────────────────────────────── */
{
  const html = p.rHeute(F.today());
  clean(html, "heute");
  // 1 - the answer first: what is possible, and a ceiling
  contains(html, "HEUTE MÖGLICH", "heute: keine Leitaussage");
  contains(html, "Alles möglich", "heute: Kapazität fehlt");
  contains(html, "Obergrenze", "heute: keine Obergrenze");
  contains(html, "95", "heute: Lastdecke fehlt");
  // 2 - the signals, each with the SYSTEM it reports on - never averaged
  ok((html.match(/class="tsig /g) || []).length === 3, "heute: nicht jedes Signal einzeln");
  contains(html, "Autonomes Nervensystem", "heute: System nicht benannt");
  contains(html, "Verhalten", "heute: Schlaf nicht als Verhalten eingeordnet");
  contains(html, "Basislinie", "heute: eigene Basislinie fehlt");
  // every signal must carry what it CANNOT do
  contains(html, "nicht die validierte Morgenmessung", "heute: Messgrenze der HRV fehlt");
  contains(html, "kein autonomer Messwert", "heute: Grenze des Schlafwerts fehlt");
  // 3 - where it comes from
  contains(html, "Woher das kommt", "heute: Herkunft fehlt");
  ok((html.match(/class="tday"/g) || []).length === 7, "heute: nicht sieben Tage");
  contains(html, "Last in sieben Tagen", "heute: Wochenlast fehlt");
  contains(html, "Erholung, nicht Bereitschaft", "heute: Nacht nicht als Erholung eingeordnet");
  // the removed things must STAY removed
  ok(!/Monotonie/.test(html), "heute: Monotonie wieder da");
  ok(!/class="ring"/.test(html), "heute: Ring wieder da");   // Icons dürfen Kreise haben, die Leitanzeige nicht
  ok(!/\d+ von 7 Signalen/.test(html), "heute: Punktwert wieder da");
  // and the reason for that has to be stated
  contains(html, "Warum hier kein Punktwert steht", "heute: Methodik nicht erklärt");
  contains(html, "Warum nur heute", "heute: Horizont nicht erklärt");
  contains(html, "kein einziger seine Formel offen", "heute: Kritik an Punktwerten fehlt");

  // a slump must read as one, in colour AND word
  const slump = p.rHeute(F.today("einbruch"));
  clean(slump, "heute einbruch");
  contains(slump, "Ruhetag", "heute: Einbruch nicht als Ruhetag");
  ok(/class="tcard red/.test(slump), "heute: Einbruch nicht rot");
  contains(slump, "Einbruch", "heute: Zustand nicht benannt");

  // where signals and verdict disagree, the page must say why
  const tension = p.rHeute(F.today("spannung"));
  clean(tension, "heute spannung");
  contains(tension, "weder weit genug noch lange genug", "heute: Widerspruch nicht erklärt");
  ok(/class="tnote"/.test(tension), "heute: Hinweis nicht als solcher gezeigt");
  ok(!/class="tnote"/.test(html), "heute: Hinweis ohne Widerspruch gezeigt");

  clean(p.rHeute(F.today("ohnenacht")), "heute ohne Nacht");
  ok(!p.rHeute(F.today("ohnenacht")).includes("Erholung, nicht Bereitschaft"),
     "heute: Nachtblock ohne Daten gezeigt");
  clean(p.rHeute(F.today("leer")), "heute leer");
  clean(p.rHeute(null), "heute null");
}

/* ── Ziel und Plan ─────────────────────────────────────────────────────── */
{
  // Two questions and nothing else. Everything the archive already knows must
  // NOT be asked for again - every extra field is a chance to get it wrong.
  p._goal = F.goal("neu");
  p._goalDraft = null;
  const fresh = p.rGoal(p._goal);
  clean(fresh, "ziel neu");
  contains(fresh, "Worauf trainierst du", "ziel: keine Frage gestellt");
  for (const needle of ["Lange Fahrten durchstehen", "Schwellenleistung heben",
                        "Spitzenleistung heben", "Fit bleiben"]) {
    contains(fresh, needle, "ziel: Auswahl unvollständig");
  }
  // what the data already holds is shown, not demanded
  contains(fresh, "Den Rest lese ich aus deinen Daten", "ziel: bekannte Werte nicht genutzt");
  contains(fresh, "längste Fahrt 3,5 h", "ziel: bekannte längste Fahrt nicht gezeigt");
  ok(!/data-field="hours_per_week"/.test(fresh), "ziel: fragt nach Stunden, die im Archiv stehen");
  ok(!/data-field="longest_day_hours"/.test(fresh), "ziel: fragt nach der längsten Fahrt");
  ok(!/data-field="target_date"/.test(fresh), "ziel: fragt nach einem Zieldatum");
  ok(!/data-field=/.test(fresh), `ziel: Formularfelder statt zwei Fragen`);

  // second question: days per week, and it says what follows from each answer
  p._goalDraft = { goal: "long_ride" };
  const step2 = p.rGoal(p._goal);
  clean(step2, "ziel schritt 2");
  contains(step2, "An wie vielen Tagen", "ziel: zweite Frage fehlt");
  ok((step2.match(/data-act="goaldays"/g) || []).length === 6, "ziel: Tagesauswahl unvollständig");
  contains(step2, "1 hart", "ziel: Folge der Tageszahl nicht gezeigt");
  contains(step2, "2 hart", "ziel: Folge der Tageszahl nicht gezeigt");
  contains(step2, "zählt Einheiten, nicht Minuten", "ziel: 80/20-Regel nicht erklärt");
  // no plan can be created before the second answer
  ok(/data-act="goalsave" disabled/.test(step2), "ziel: Plan ohne Tagesangabe erzeugbar");
  p._goalDraft = { goal: "long_ride", days_per_week: 4 };
  ok(!/data-act="goalsave" disabled/.test(p.rGoal(p._goal)), "ziel: Plan trotz Angabe nicht erzeugbar");
  p._goalDraft = null;

  // a stored goal: the plan
  p._goal = F.goal();
  p._goalEdit = false;
  const html = p.rGoal(p._goal);
  clean(html, "ziel gesetzt");
  contains(html, "Lange Fahrten durchstehen", "plan: Ziel nicht genannt");
  contains(html, "Durability", "plan: Zielgröße nicht genannt");
  contains(html, "keinen Beleg", "plan: Einschränkung der 80/20-Regel fehlt");
  // the head is two tiles, nothing more - everything else folds away
  contains(html, "4 Tage pro Woche", "plan: Zeitangabe fehlt");
  ok((html.match(/class="gtile"/g) || []).length === 2,
     "plan: Kopf ist nicht auf zwei Kacheln reduziert");
  contains(html, "2 harte Einheiten", "plan: Folge der Tageszahl fehlt");
  contains(html, "aus deinen letzten Wochen gerechnet", "plan: Herkunft der Stunden fehlt");
  contains(html, "noch 3,0 h bis zur Zielfahrt", "plan: Lücke zum Ziel fehlt");
  // the weekly plan is present but folded - it is not the point of the page
  ok(/class="more planfold"/.test(html), "plan: Wochenplan nicht eingeklappt");
  ok(!/<details class="more planfold" open/.test(html), "plan: Wochenplan vorab geöffnet");
  ok((html.match(/class="pweek /g) || []).length === 4, "plan: nicht alle Wochen");
  contains(html, "Entlastung", "plan: Entlastungswoche nicht markiert");
  contains(html, "langer Tag", "plan: langer Tag fehlt");
  // the sources travel with it, folded
  contains(html, "keinen Unterschied", "plan: Blockperiodisierung falsch dargestellt");
  contains(html, "Konvention, kein Studienergebnis", "plan: Wachstumsregel nicht eingeordnet");
  contains(html, "Einbruch schlägt jeden Plan", "plan: Vorrang des Zustands fehlt");

  // opening a week shows the sessions with their reasons
  ok(!html.includes("Durchgehend essen"), "plan: Details ungefragt ausgebreitet");
  p._planOpen = "1";
  const open = p.rGoal(p._goal);
  clean(open, "plan Woche offen");
  contains(open, "Durchgehend essen", "plan: Verpflegungshinweis fehlt");
  contains(open, "Fettoxidation", "plan: Begründung der langen Einheit fehlt");
  p._planOpen = null;

  // a weekly budget that cannot carry the goal must SAY so
  p._goal = F.goal("knapp");
  const tight = p.rGoal(p._goal);
  clean(tight, "plan knapp");
  contains(tight, "Das Zeitbudget trägt dieses Ziel nicht", "plan: Warnung fehlt");
  contains(tight, "nicht aufzubauen", "plan: Rechnung nicht genannt");
  contains(tight, "vom Wochenbudget gedeckelt", "plan: Deckelung nicht markiert");
  ok(/class="cmpverdict worse/.test(tight), "plan: Warnung nicht als Warnung gezeigt");
  p._goal = null;
  clean(p.rGoal(null), "ziel ohne Daten");
}

/* ── Signale ───────────────────────────────────────────────────────────── */
{
  const html = p.rSignale(F.signals());
  clean(html, "signale");
  for (const needle of ["Herzratenvariabilität", "Ruhepuls", "Schlaf", "Form",
                        "Standardabweichungen", "gestapelt", "überlagert",
                        "Einbruch", "aerob", "harte Einheit"]) {
    contains(html, needle, "signale");
  }
  // the mirrored resting heart rate must be explained, not silently flipped
  contains(html, "gespiegelt", "signale: Spiegelung des Ruhepulses nicht erklärt");
  // one cursor group for the whole stack, not one per field
  ok((html.match(/data-grp="sig"/g) || []).length === 1,
     "signale: mehr als eine Cursor-Gruppe");
  ok(p._grp.sig && p._grp.sig.rows.length >= 5, "signale: Ableseleiste unvollständig");
  // the readout must carry RAW units - a z-score is not something you recognise
  const hrvRow = p._grp.sig.rows.find((r) => /Herzraten/.test(r.l));
  ok(hrvRow && hrvRow.u === "ms", `signale: Ableseleiste zeigt keine echten Einheiten (${hrvRow && hrvRow.u})`);
  ok(hrvRow.vals.some((v) => v > 20), "signale: Ableseleiste zeigt z-Werte statt Millisekunden");
  // state bands must be painted behind the fields
  ok(/opacity="0\.18"/.test(html), "signale: Einbruchsband fehlt im Hintergrund");
  // every signal ships its source
  ok((html.match(/class="more expl"/g) || []).length >= 5,
     "signale: nicht jedes Signal hat Erklärung und Quelle");
  contains(html, "Gabbett", "signale: Quelle des ACWR fehlt");
  contains(html, "Plews", "signale: Quelle der HRV-Regel fehlt");

  // overlay mode
  p._sigMode = "overlay";
  const over = p.rSignale(F.signals());
  clean(over, "signale überlagert");
  ok((over.match(/<svg class="ch"/g) || []).length === 2,
     "signale überlagert: nicht in ein Feld zusammengelegt");
  p._sigMode = "stack";

  // focus dims the others instead of opening a window
  p._sigFocus = "hrv";
  const focus = p.rSignale(F.signals());
  clean(focus, "signale fokus");
  ok((focus.match(/class="sigfield dim"/g) || []).length >= 2,
     "signale: Fokus blendet die anderen nicht ab");
  p._sigFocus = null;

  // degenerate inputs
  clean(p.rSignale(F.signals("luecken")), "signale mit Lücken");
  clean(p.rSignale(F.signals("ohnedfa")), "signale ohne DFA");
  clean(p.rSignale(F.signals("kurz")), "signale zu kurz");
  contains(p.rSignale(F.signals("kurz")), "zu wenig Historie", "signale kurz");
  clean(p.rSignale(F.signals("leer")), "signale leer");
  clean(p.rSignale(null), "signale null");
}

/* ── Kalender ──────────────────────────────────────────────────────────── */
{
  const html = p.rKalender(days);
  clean(html, "kalender");
  for (const needle of ["KW", "geplant", "erledigt", "ausgelassen", "SweetSpot", "volumen"]) {
    contains(html, needle, "kalender");
  }
  clean(p.rKalender(EMPTY_DAYS), "kalender leer");
  clean(p.rKalender(null), "kalender null");
  clean(p.rKalender(gappy), "kalender mit lücken");
}

/* ── Fitness ───────────────────────────────────────────────────────────── */
{
  const html = p.rFitness(pmc, 182);
  clean(html, "fitness");
  for (const needle of ["Fitness", "Ermüdung", "Form", "Tageslast", "Friel"]) contains(html, needle, "fitness");
  ok(p._grp.pmc && p._grp.pmc.rows.length === 4, "fitness: Cursor-Gruppe unvollständig");
  clean(p.rFitness(pmc.slice(0, 2), 42), "fitness zu kurz");
  clean(p.rFitness(null, 42), "fitness null");
  clean(p.rFitness(pmc.map((r) => ({ ...r, load: 0 })), 42), "fitness ohne last");
}

/* ── Aktivitäten ───────────────────────────────────────────────────────── */
{
  clean(p.rAkt(acts, null), "aktivitäten liste");
  p._streams = {};
  clean(p.rAkt(acts, acts[0]), "detail lädt");
  p._streams[acts[0].id] = { error: "HTTP 500" };
  clean(p.rAkt(acts, acts[0]), "detail fehler");
  p._streams[acts[0].id] = { points: 0, sample_secs: 1, channels: {} };
  clean(p.rAkt(acts, acts[0]), "detail ohne ströme");
  p._streams[acts[0].id] = F.streams();
  const html = p.rAkt(acts, acts[0]);
  clean(html, "detail voll");
  for (const needle of ["Leistung", "Herzfrequenz", "DFA alpha-1", "Kadenz", "Höhe", "aerobe Schwelle"]) {
    contains(html, needle, "detail");
  }
  ok(p._grp.str.n === 600, "detail: Cursor-Gruppe falsch dimensioniert");
  // a walk has no power channel at all
  p._streams.walkX = { points: 200, sample_secs: 4, channels: {
    time: Array.from({ length: 200 }, (_, i) => i * 4),
    heartrate: Array.from({ length: 200 }, () => 95) } };
  const walk = p.rAkt(acts, { ...acts[2], id: "walkX" });
  clean(walk, "detail gehen");
  ok(!walk.includes("Leistung (W)"), "detail: leeres Leistungsfeld gezeichnet");
  // --- Runden -----------------------------------------------------------
  p._laps = {};
  clean(p.rAkt(acts, acts[0]), "runden laden");
  ok(p.rAkt(acts, acts[0]).includes("Runden werden geladen"), "runden: kein Ladehinweis");

  p._laps[acts[0].id] = F.laps("error");
  clean(p.rAkt(acts, acts[0]), "runden fehler");
  contains(p.rAkt(acts, acts[0]), "HTTP 500", "runden fehler");

  p._laps[acts[0].id] = F.laps("empty");
  const noLaps = p.rAkt(acts, acts[0]);
  clean(noLaps, "runden leer");
  contains(noLaps, "keine Runden", "runden leer");

  p._laps[acts[0].id] = F.laps("noPower");
  const noPow = p.rAkt(acts, acts[0]);
  clean(noPow, "runden ohne Leistung");
  ok(!noPow.includes("Watt pro Herzschlag über die Serie"),
     "runden: Urteil ohne Leistungsdaten behauptet");

  p._laps[acts[0].id] = F.laps();
  const full = p.rAkt(acts, acts[0]);
  clean(full, "runden voll");
  for (const needle of ["Runden", "Aufwärmen", "Z5", "EF (W/Schlag)", "DFA a1", "259 W", "170 bpm"]) {
    contains(full, needle, "runden");
  }
  ok((full.match(/class="lrow/g) || []).length === 10, "runden: nicht alle Abschnitte gezeigt");
  ok((full.match(/class="lrow rest/g) || []).length === 1, "runden: Pause/Rollen nicht abgesetzt");
  // the fading series must be named as such, with the right sign
  contains(full, "Watt pro Herzschlag über 4 vergleichbare Abschnitte", "runden urteil");
  ok(/-8[,.]/.test(full) || /−8/.test(full), `runden: Abfall falsch beziffert`);
  ok(full.includes("Ermüdung"), "runden: fallende Serie nicht als Ermüdung benannt");
  // a stable series must NOT be called fatigue
  p._laps[acts[0].id] = { source: "x", laps: [
    { n: 1, label: "4x", moving_time: 240, avg_watts: 250, avg_hr: 170, ef: 1.47 },
    { n: 2, label: "4x", moving_time: 240, avg_watts: 250, avg_hr: 171, ef: 1.46 },
    { n: 3, label: "4x", moving_time: 240, avg_watts: 250, avg_hr: 170, ef: 1.47 },
  ] };
  const steady = p.rAkt(acts, acts[0]);
  clean(steady, "runden stabil");
  ok(!steady.includes("ist das Ermüdung"), "runden: stabile Serie als Ermüdung gemeldet");
  contains(steady, "über 3 vergleichbare Abschnitte", "runden stabil zählung");
  contains(steady, "verkraftbar", "runden stabil");
  p._laps = {};

  // --- Blockvergleich (Intervalleinheit) ---------------------------------
  {
    const set = F.lapsWithBounds();
    p._laps[acts[0].id] = { laps: set.laps, seen_keys: set.seen_keys, source: set.source };
    p._streams[acts[0].id] = set.stream;
    const html = p.rAkt(acts, acts[0]);
    clean(html, "blockvergleich");
    contains(html, "Blockvergleich", "blockvergleich");
    contains(html, "4 gleichartige Blöcke", "blockvergleich: Anzahl fehlt");

    // the overlaid curves are gone - four noisy lines in one field were the
    // clutter that makes line charts lose discriminability
    ok(!html.includes('class="cmppanel'),
       "blockvergleich: überlagerte Kurven noch da");
    ok(!html.includes("Jede Linie trägt ihren Namen"),
       "blockvergleich: Hinweis auf die entfernte Überlagerung noch da");

    // the table carries it all: five measures, three comparison columns
    ok((html.match(/class="devrow"/g) || []).length === 5,
       "blockvergleich: nicht fünf Kennzahlen");
    ok((html.match(/class="devrow devhead2"/g) || []).length === 1,
       "blockvergleich: keine Kopfzeile mit den Blocknamen");
    ok((html.match(/class="devcell colhead"/g) || []).length === 3,
       "blockvergleich: keine Blockspalten");
    // a bar without a scale is an ordering, not a measurement
    ok((html.match(/class="devscale"/g) || []).length === 3,
       "blockvergleich: keine Skala unter den Balken");
    ok(/devfoot/.test(html), "blockvergleich: Skalenzeile fehlt");
    contains(html, "Block 4", "blockvergleich: Spalte fehlt");
    contains(html, "Puls-Erholung", "blockvergleich: Puls-Erholung fehlt");
    // the reference value itself must be visible, not only the deviation
    ok((html.match(/class="devbase"/g) || []).length >= 4,
       "blockvergleich: Bezugswert des ersten Blocks fehlt");
    contains(html, "-10 W", "blockvergleich: Leistungsabweichung nicht in Watt");
    contains(html, "+11 bpm", "blockvergleich: Pulsabweichung nicht in Schlägen");

    // direction encoded by colour, and the two directions must differ
    const devBox = html.slice(html.indexOf('class="devbox"'));
    const powerRow = devBox.slice(devBox.indexOf("Leistung"), devBox.indexOf("Herzfrequenz"));
    const hrRow = devBox.slice(devBox.indexOf("Herzfrequenz"), devBox.indexOf("DFA"));
    ok(/#fbbf24/.test(powerRow), "blockvergleich: fallende Leistung nicht als ungünstig markiert");
    ok(/#fbbf24/.test(hrRow), "blockvergleich: steigender Puls nicht als ungünstig markiert");

    contains(html, "Die Serie hat abgebaut", "blockvergleich: fallende Serie nicht benannt");
    contains(html, "Übrige Abschnitte (5)", "blockvergleich: übrige Abschnitte fehlen");

    // a session that held must NOT be called fatigue
    const steady = JSON.parse(JSON.stringify(set));
    steady.laps.forEach((l) => { if (l.type === "WORK") { l.avg_watts = 255; l.avg_hr = 170; l.dfa_a1 = 0.85; l.ef = 1.5; } });
    p._laps[acts[0].id] = { laps: steady.laps, source: "icu_intervals" };
    const held = p.rAkt(acts, acts[0]);
    clean(held, "blockvergleich stabil");
    contains(held, "Die Serie hat gehalten", "blockvergleich: stabile Serie als Abbau gemeldet");
  }

  // --- Dieselbe Tabelle für eine Fahrt OHNE Intervalle --------------------
  {
    const steadyRide = F.steadyStream();
    p._laps[acts[0].id] = { laps: [], source: "none" };
    p._streams[acts[0].id] = steadyRide;
    const html = p.rAkt(acts, acts[0]);
    clean(html, "grundlagenfahrt");
    contains(html, "Wie sich die Fahrt entwickelt hat", "grundlage: keine Segmentanalyse");
    contains(html, "vier gleich lange Abschnitte", "grundlage: Einteilung nicht erklärt");
    ok((html.match(/class="devcell colhead"/g) || []).length === 3,
       "grundlage: nicht drei Vergleichsspalten");
    contains(html, "2. Viertel", "grundlage: Abschnitte nicht benannt");
    contains(html, "Entkopplung über die Fahrt", "grundlage: kein Entkopplungsurteil");
    // The verdict must GRADE against the published benchmarks, and grade
    // differently for different rides - otherwise it is a number with a
    // sentence glued to it. Trained riders hold under 3%, Friel's benchmark
    // is 5%, recreational riders sit at 5-10%, above that the effort was
    // likely over threshold.
    const grades = [
      ["stabil", /unter 3 %/, "eine fast driftfreie Fahrt"],
      ["", /unter 5 %/, "eine Fahrt im Richtwert"],
      ["mittel", /zwischen 5 und 10 %/, "eine Fahrt im Freizeitbereich"],
      ["hart", /über 10 %/, "eine Fahrt über der Schwelle"],
    ];
    for (const [kind, pattern, label] of grades) {
      p._streams[acts[0].id] = F.steadyStream(kind);
      const graded = p.rAkt(acts, acts[0]);
      clean(graded, "grundlage " + (kind || "normal"));
      ok(pattern.test(graded), `grundlage: ${label} wird falsch eingeordnet`);
    }
    // the worst case must also read as a warning, not as a neutral note
    p._streams[acts[0].id] = F.steadyStream("hart");
    ok(/class="cmpverdict worse/.test(p.rAkt(acts, acts[0])),
       "grundlage: starke Entkopplung nicht als Warnung gezeigt");
    p._streams[acts[0].id] = F.steadyStream("stabil");
    ok(/class="cmpverdict held/.test(p.rAkt(acts, acts[0])),
       "grundlage: driftfreie Fahrt als Warnung gezeigt");
    p._streams[acts[0].id] = steadyRide;
    contains(html, "kardiale Drift", "grundlage: Drift nicht erklärt");
    // heart rate recovery makes no sense without rests - it must be absent
    ok(!html.includes("Puls-Erholung"), "grundlage: Puls-Erholung ohne Pausen behauptet");
    // and a short ride must not be cut into quarters at all
    p._streams[acts[0].id] = F.steadyStream("kurz");
    const short = p.rAkt(acts, acts[0]);
    clean(short, "grundlage kurz");
    ok(!short.includes("Wie sich die Fahrt entwickelt hat"),
       "grundlage: zu kurze Fahrt trotzdem geviertelt");
    p._laps = {}; p._streams = {};
  }

  // --- Wie diese Einheit dasteht -----------------------------------------
  {
    p._laps[acts[0].id] = { laps: [], source: "none" };
    p._streams[acts[0].id] = F.steadyStream();
    p._ctx[acts[0].id] = F.context();
    const html = p.rAkt(acts, acts[0]);
    clean(html, "einordnung");
    contains(html, "Wie diese Einheit dasteht", "einordnung");
    contains(html, "gegen 18 eigene Einheiten", "einordnung: Vergleichsgruppe nicht benannt");
    // the number alone says nothing - the rider's own median must be there
    contains(html, "Median 2,10", "einordnung: eigener Median fehlt");
    contains(html, "17 Einheiten", "einordnung: Umfang der Vergleichsgruppe fehlt");
    // range, median tick and this session's dot - position on a common scale
    ok((html.match(/class="ctxband"/g) || []).length === 3, "einordnung: keine Streuungsbänder");
    ok((html.match(/class="ctxmed"/g) || []).length === 3, "einordnung: keine Medianmarken");
    ok((html.match(/class="ctxdot"/g) || []).length === 3, "einordnung: dieser Wert nicht verortet");
    // the verdict has to differ per metric - and the direction must be respected
    contains(html, "schlechter als sonst", "einordnung: schlechte Entkopplung nicht benannt");
    contains(html, "besser als sonst", "einordnung: guter EF-Wert nicht benannt");
    contains(html, "im üblichen Bereich", "einordnung: mittlerer Wert falsch eingestuft");
    // a LOW decoupling is good, a HIGH one bad - the rank must be read that way
    // scoped to the context block - the segment verdict above also mentions
    // "Entkopplung" and carries its own colour, which would mask the defect
    const box = html.slice(html.indexOf('class="ctxbox"'));
    const decRow = box.slice(box.indexOf("Entkopplung"), box.indexOf("Watt pro Herzschlag"));
    ok(/#fbbf24/.test(decRow), "einordnung: schlechte Entkopplung nicht als ungünstig gefärbt");
    ok(!/#34d399/.test(decRow),
       "einordnung: hohe Entkopplung als günstig gefärbt - die Richtung wird ignoriert");
    const efRow = box.slice(box.indexOf("Watt pro Herzschlag"), box.indexOf("Ø Herzfrequenz"));
    ok(/#34d399/.test(efRow), "einordnung: guter Wert nicht als günstig gefärbt");
    ok(!/#fbbf24/.test(efRow), "einordnung: guter Wert als ungünstig gefärbt");

    // too few comparable sessions: say so, do not rank against three rides
    p._ctx[acts[0].id] = F.context("duenn");
    const thin = p.rAkt(acts, acts[0]);
    clean(thin, "einordnung dünn");
    contains(thin, "zu wenig für eine Einordnung", "einordnung: Urteil trotz dünner Basis");
    ok(!thin.includes("ctxband"), "einordnung: Streuungsband ohne Datenbasis gezeichnet");

    p._ctx[acts[0].id] = F.context("leer");
    clean(p.rAkt(acts, acts[0]), "einordnung leer");
    ok(!p.rAkt(acts, acts[0]).includes("Wie diese Einheit dasteht"),
       "einordnung: leerer Block gezeigt");
    p._ctx = {}; p._laps = {}; p._streams = {};
  }

  // --- Die Nacht danach ---------------------------------------------------
  {
    p._laps[acts[0].id] = { laps: [], source: "none" };
    p._streams[acts[0].id] = F.steadyStream();
    p._night[acts[0].id] = F.night();
    const html = p.rAkt(acts, acts[0]);
    clean(html, "nacht");
    contains(html, "Die Nacht danach", "nacht");
    contains(html, "wie sonst nach solchen Einheiten", "nacht: Urteil fehlt");
    // all three measured values with their own baseline
    for (const needle of ["Herzratenvariabilität", "Ruhepuls", "Schlafdauer",
                          "deine Basislinie", "49", "-1,5 SD"]) {
      contains(html, needle, "nacht");
    }
    // the reference - what this athlete usually does after sessions like this
    contains(html, "üblich nach solchen Einheiten", "nacht: eigene Referenz fehlt");
    // a night at -1.5 SD that is NORMAL for this athlete must not be a warning.
    // Checked INSIDE the night section - the segment analysis renders a verdict
    // of its own further up and would mask the defect.
    const nightPart = (page) => page.slice(page.indexOf("Die Nacht danach"));
    ok(/class="cmpverdict held/.test(nightPart(html)),
       "nacht: übliche Reaktion als Warnung gezeigt - genau der Fehlalarm, den die Referenz verhindert");
    ok(!/class="cmpverdict worse/.test(nightPart(html)),
       "nacht: Warnfarbe trotz üblicher Reaktion");
    // the bell-shaped caveat must travel with it
    contains(html, "glockenförmig", "nacht: Glockenform nicht genannt");

    // an unusually damped night IS a warning
    p._night[acts[0].id] = F.night("hart");
    const hard = p.rAkt(acts, acts[0]);
    clean(hard, "nacht hart");
    ok(/class="cmpverdict worse/.test(nightPart(hard)), "nacht: starke Dämpfung nicht als Warnung");
    contains(hard, "deutlich gedämpfter", "nacht: Urteil fehlt");

    // without a reference, no verdict is invented
    p._night[acts[0].id] = F.night("ohnereferenz");
    const noref = p.rAkt(acts, acts[0]);
    clean(noref, "nacht ohne Referenz");
    contains(noref, "Kein Vergleich möglich", "nacht: Urteil trotz fehlender Referenz");
    contains(noref, "zu wenige Vergleichsnächte", "nacht: fehlende Referenz nicht benannt");

    // missing data says so instead of showing an empty block
    p._night[acts[0].id] = F.night("keine");
    const none = p.rAkt(acts, acts[0]);
    clean(none, "nacht ohne Daten");
    contains(none, "keine Wellness-Werte", "nacht: fehlende Daten nicht benannt");
    p._night = {}; p._laps = {}; p._streams = {};
  }

  clean(p.rAkt([], null), "aktivitäten leer");
  clean(p.rAkt(null, null), "aktivitäten null");
}

/* ── Belastung ─────────────────────────────────────────────────────────── */
{
  const html = p.rBelastung(load);
  clean(html, "belastung");
  for (const needle of ["Wochenlast", "ACWR", "Intensitätsverteilung", "HRV-Trend",
                        "Entkopplung", "Quelle und Grenzen", "Zu lesen als"]) {
    contains(html, needle, "belastung");
  }
  ok((html.match(/Zu lesen als/g) || []).length === 5, "belastung: nicht jeder Abschnitt erklärt");
  clean(p.rBelastung(EMPTY_LOAD), "belastung leer");
  clean(p.rBelastung(null), "belastung null");
  clean(p.rBelastung({ ...load, hrv: { series: [], latest: null, baseline: null, swc: null, state: "unknown" } }),
        "belastung ohne hrv");
}

/* ── DFA ───────────────────────────────────────────────────────────────── */
{
  const html = p.rDfa(thr, "all");
  clean(html, "dfa");
  for (const needle of ["Aktuelle aerobe Schwelle", "bpm", "eigenes Feld", "dünn"]) contains(html, needle, "dfa");
  clean(p.rDfa(thr, "walk"), "dfa gefiltert");
  clean(p.rDfa(thr, "swim"), "dfa filter ohne treffer");
  clean(p.rDfa([], "all"), "dfa leer");
  clean(p.rDfa(null, "all"), "dfa null");
  clean(p.rDfa(thr.map((x) => ({ ...x, samples: 2 })), "all"), "dfa nur dünne messungen");
  clean(p.rDfa(thr.map((x) => ({ ...x, power: null })), "all"), "dfa ohne leistung");
}

/* ── Plan ──────────────────────────────────────────────────────────────── */
{
  const html = p.rPlan(cal, rd);
  clean(html, "plan");
  contains(html, "SweetSpot Erhalt", "plan");
  clean(p.rPlan([], rd), "plan leer");
  clean(p.rPlan(null, null), "plan null");
  clean(p.rPlan(cal, null), "plan ohne budget");
}

/* ── Bausteine an den Rändern ──────────────────────────────────────────── */
{
  clean(M.ring([], "unknown"), "ring leer");
  clean(M.bullet({ chronic: 1, last_six_days: 0, target_ratio: 1, recommended: 0,
                   steady: 5, corridor_top: 7, risk_top: 9, state: "green" }), "bullet mini");
  clean(M.spark([null, null, null]), "spark nur nullen");
  clean(M.spark([5, 5, 5, 5]), "spark konstant");
  clean(M.chart({ h: 100, n: 10, y0: 0, y1: 10,
                  s: [{ t: "line", v: [null, 1, null, null, 4, 5, null, 7, null, null], c: "#fff" }] }),
        "chart mit lücken");
  // isolated points between gaps must still be drawn (0.9.0 regression)
  const iso = M.chart({ h: 100, n: 5, y0: 0, y1: 10,
                        s: [{ t: "line", v: [null, 4, null, 7, null], c: "#fff", w: 2 }] });
  ok((iso.match(/<circle/g) || []).length === 2, "chart: einzelne Messpunkte zwischen Lücken unsichtbar");
  for (const v of [[42], [1e9, 2e9], [-90, -20, null, -50]]) {
    const vv = v.filter((x) => x != null);
    clean(M.chart({ h: 100, n: Math.max(2, v.length), y0: Math.min(...vv, 0) - 1, y1: Math.max(...vv) + 1,
                    s: [{ t: "line", v, c: "#fff" }] }), "chart extremwerte " + v.join(","));
  }
}

/* ── Formatierung, deutsch ─────────────────────────────────────────────── */
{
  ok(M.dur(0) === "0m" && M.dur(null) === "–" && M.dur(4100) === "1h08m", "format: dur");
  ok(M.fmt(null) === "–" && M.fmt(1234.5, 1) === "1.234,5", "format: fmt de-DE");
  ok(M.hhmm(5400) === "1:30", "format: hhmm");
  ok(M.sign(3) === "+3" && M.sign(-2) === "-2", "format: sign");
  ok(M.dShort("2026-09-09") === "Mi 09.", "format: dShort");
  ok(M.dMed("2026-09-04T07:57:00") === "04.09.2026", "format: dMed");
  ok(M.dLong("2026-09-11") === "Freitag, 11.09.2026", "format: dLong");
  ok(M.dLong(null) === "", "format: dLong ohne Datum");
  ok(M.median([3, 1, 2]) === 2 && M.median([]) === null, "format: median");
  ok(JSON.stringify(M.movAvg([1, null, 3], 2)) === "[1,1,3]", "format: movAvg über Lücken");
  ok(M.esc('<b>&"') === "&lt;b&gt;&amp;&quot;", "format: esc");
}

report("test_panel_views");
