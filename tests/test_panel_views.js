"use strict";
/* Every view against full, empty, gappy and degenerate payloads. The panel
 * has to render something honest in each case - never "undefined", never a
 * blank page, never a crash. */

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
  ok((html.match(/class="tday /g) || []).length === 7, "heute: nicht sieben Tage");
  contains(html, "Last in sieben Tagen", "heute: Wochenlast fehlt");
  // the days must show what was actually ridden - reading the load from the
  // wellness row reported "0 load in seven days" on a week with a ride and a walk
  contains(html, "volumen", "heute: Einheit des Tages fehlt im Wochenbalken");
  contains(html, "Rehburg-Lo", "heute: zweite Einheit fehlt");
  // every day gets the same four rows, so the bars share one baseline and the
  // labels line up. Cells of differing height pushed the bars upwards before.
  ok((html.match(/class="tdayn"/g) || []).length === 7, "heute: nicht jeder Tag beschriftet");
  ok((html.match(/class="tbarbox"/g) || []).length === 7, "heute: Balken ohne gemeinsame Grundlinie");
  ok((html.match(/class="tdate"/g) || []).length === 7, "heute: Datumszeile unvollständig");
  ok((html.match(/class="tload/g) || []).length === 7, "heute: Lastzeile unvollständig");
  contains(html, "frei", "heute: Ruhetage nicht als solche benannt");
  ok(/class="tday now"/.test(html) || !/2026-09-11/.test(new Date().toISOString()),
     "heute: heutiger Tag nicht hervorgehoben");
  // bar heights are percentages of the box, never pixels - a pixel height in a
  // flex row is what let them drift off the baseline
  ok(!/height:\d+px;background/.test(html), "heute: Balkenhöhe wieder in Pixeln");
  ok(/height:100(\.\d+)?%;background/.test(html), "heute: höchster Balken füllt die Box nicht");

  // a signal card opens into a full-width view with its curve and its meaning
  ok((html.match(/data-act="sigopen"/g) || []).length === 3, "heute: Karten nicht anklickbar");
  ok(!/class="tsigbig"/.test(html), "heute: große Ansicht ohne Klick offen");
  p._sigOpen = "hrv";
  const opened = p.rHeute(F.today());
  clean(opened, "heute signal offen");
  ok(/class="tsig[^"]*big"/.test(opened), "heute: Karte wird nicht groß");
  ok((opened.match(/class="tsigbig"/g) || []).length === 1, "heute: mehr als eine Karte offen");
  ok(/<svg class="ch"/.test(opened), "heute: große Ansicht ohne Kurve");
  contains(opened, "Worüber dieser Wert etwas sagt", "heute: große Ansicht ohne Erklärung");
  contains(opened, "kleinste bedeutsame Änderung", "heute: Rauschgrenze nicht erklärt");
  contains(opened, "Basislinie", "heute: Bezugslinie fehlt in der Kurve");
  // the bands come from the athlete's OWN 60-day distribution and are drawn in
  // the signal's own unit - a rider recognises 41 ms, not -1.5 SD
  ok((opened.match(/<rect[^>]*opacity="0\.(08|14)"/g) || []).length >= 2,
     "heute: keine Bereiche aus der eigenen Verteilung");
  contains(opened, "Basislinie 48", "heute: Basislinie nicht in echter Einheit");
  contains(opened, "Einbruch ab 35", "heute: Einbruchsschwelle nicht eingezeichnet");
  contains(opened, "Die Bereiche:", "heute: Bereiche nicht erklärt");
  contains(opened, "aus deinen letzten 60 Tagen gerechnet", "heute: Herkunft der Bereiche fehlt");
  // for the resting heart rate the threshold points the OTHER way
  p._sigOpen = "rhr";
  const rhrOpen = p.rHeute(F.today());
  clean(rhrOpen, "heute ruhepuls offen");
  contains(rhrOpen, "auffällig hoch 62", "heute: Ruhepuls-Schwelle falsch herum");
  ok(!/Einbruch ab/.test(rhrOpen.slice(rhrOpen.indexOf("tsigbig"))),
     "heute: Ruhepuls als Einbruch beschriftet");
  p._sigOpen = "hrv";
  p._sigOpen = null;
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
  // The head is TWO tiles and nothing else - no plan, no weeks, no warning.
  // The question of the day is which session to ride, not what week 7 looks like.
  contains(html, "Lange Fahrten durchstehen", "plan: Ziel nicht genannt");
  contains(html, "Durability", "plan: Zielgröße nicht genannt");
  contains(html, "4 Tage pro Woche", "plan: Zeitangabe fehlt");
  contains(html, "1 harte Einheit", "plan: Folge der Tageszahl fehlt");
  ok((html.match(/class="gtile"/g) || []).length === 2,
     "plan: Kopf ist nicht auf zwei Kacheln reduziert");
  ok(!/class="pweek /.test(html), "plan: Wochenplan steht wieder oben");
  ok(!/Die nächsten Wochen/.test(html), "plan: Wochenvorschau steht wieder oben");
  ok(!/Zeitbudget trägt/.test(html), "plan: Budgetwarnung steht wieder oben");
  ok(html.length < 1400, `plan: Kopf zu umfangreich (${html.length} Zeichen)`);

  p._goal = null;
  clean(p.rGoal(null), "ziel ohne Daten");

  // The weeks live BELOW the trainer, in their own section - visible again
  // after living as computed-but-never-rendered dead code in rGoal.
  p._goal = F.goal();
  const pw = p.rPlanWeeks(p._goal);
  clean(pw, "wochen");
  ok(/class="pweek /.test(pw), "wochen: Wochenliste fehlt");
  contains(pw, "Die nächsten Wochen", "wochen: Abschnitt ohne Titel");
  contains(pw, "Kalenderwochen verankert", "wochen: Kalenderanker nicht benannt");
  // the big day is marked as the exception, and it grows
  contains(pw, "großer Tag", "wochen: großer Tag nicht ausgewiesen");
  contains(pw, "die Ausnahme, die wächst", "wochen: Ausnahme-Charakter fehlt");
  ok(/pweek load bigday/.test(pw), "wochen: Woche des großen Tages nicht markiert");
  // the caveat travels with the weeks: convention, not finding
  contains(pw, "kein Studienergebnis", "wochen: Konvention nicht als solche benannt");
  // the recovery week is visible as such
  contains(pw, "Entlastung", "wochen: Entlastungswoche nicht benannt");
  // tight budget: the note explains the exception instead of demanding hours
  const knapp = p.rPlanWeeks(F.goal("knapp"));
  contains(knapp, "bewusste Ausnahme", "wochen: Budget-Note erklärt die Ausnahme nicht");
  ok(!/nicht aufzubauen/.test(knapp), "wochen: alte Unmöglichkeits-Botschaft ist zurück");
  // no plan, no section - and no crash on empty input
  ok(p.rPlanWeeks(F.goal("neu")) === "", "wochen: Sektion trotz fehlendem Plan");
  // Diese Zusicherung hieß bis 0.42.0 "ohne Daten kein Abschnitt" - und hat
  // damit genau den Fehler festgeschrieben, der den Zielblock von 0.20.0 bis
  // 0.42.0 unsichtbar gemacht hat. Fehlende Daten sind jetzt eine Aussage.
  ok(p.rPlanWeeks(null) !== "", "wochen: fehlende Daten verschwinden still");
  p._goal = null;
}

/* ── Trainer: Kopf, Empfehlung, Zustand ───────────────────────────────── */
{
  p._workouts = F.workouts();
  const html = p.rTrainer(F.coach("ready"), F.readiness());
  clean(html, "trainer");
  // the page answers TODAY - no week preview, no catalogue, no "next session"
  // that was never chosen
  ok(!/nächsten sieben Tage/.test(html), "trainer: Wochenvorschau wieder da");
  ok(!/Einheitenkatalog/.test(html), "trainer: Katalog wieder da");
  ok(!/Nächste Einheit/.test(html), "trainer: spricht von einer gewählten Einheit");
  // ONE logic: the list is the recommendation. A second block above with its
  // own answer could quietly disagree with the cards below it.
  ok(!/class="card rec"/.test(html), "trainer: zweiter Empfehlungsblock wieder da");
  contains(html, "Worauf diese Empfehlung beruht", "trainer: Herleitung fehlt");
  contains(html, "alles außerhalb des Trainings", "trainer: Grenze der Empfehlung fehlt");

  // the three separate bars became one axis with three dots: position on a
  // COMMON scale rather than three tracks that cannot be compared
  ok(!/class="zbar/.test(html), "trainer: getrennte Balken wieder da");
  ok((html.match(/class="zdot"/g) || []).length === 3, "trainer: nicht drei Punkte auf einer Achse");
  ok(/class="zband"/.test(html), "trainer: Normalband fehlt");
  ok(/class="zzero"/.test(html), "trainer: Basislinie nicht markiert");
  // labels sit ON the rows now, not in a legend below - a legend forces the
  // eye between two places and the mapping into working memory
  ok((html.match(/class="zrow"/g) || []).length === 3, "trainer: nicht drei beschriftete Zeilen");
  ok((html.match(/class="zname"/g) || []).length === 3, "trainer: Zeilen ohne Namen");
  ok((html.match(/class="zval/g) || []).length === 3, "trainer: Werte nicht beziffert");
  ok(!/class="zleg"/.test(html), "trainer: getrennte Legende wieder da");
  contains(html, "±0,5 = Rauschen", "trainer: Normalband nicht erklärt");
  contains(html, "7-Tage-Mittel HRV", "trainer: Signal nicht benannt");
}

/* ── Einheiten für heute ──────────────────────────────────────────────── */
{
  const rdFix = F.readiness();
  p._workouts = F.workouts();
  const html = p.rTrainer(F.coach("ready"), rdFix);
  clean(html, "einheiten");
  contains(html, "Einheiten für heute", "einheiten");
  // ONE per kind - not three base rides. The choice must be between different
  // KINDS of training, which is what makes it a choice at all.
  const families = ["Grundlage", "SweetSpot", "Tempo", "Schwelle", "VO2max", "Regeneration"];
  for (const family of families) contains(html, family, `einheiten: ${family} fehlt`);
  ok((html.match(/class="wofam"/g) || []).length === 6, "einheiten: nicht sechs Arten");
  ok((html.match(/class="wocard/g) || []).length === 6, "einheiten: nicht sechs Karten");
  contains(html, "passt heute", "einheiten: kein Tagesurteil");
  // exactly one card carries the recommendation, and it is a fitting one
  ok((html.match(/class="recflag"/g) || []).length === 1,
     "einheiten: nicht genau eine Empfehlung markiert");
  // the recommendation must be VISIBLE as a lead, not a line on a card
  contains(html, "HEUTE EMPFOHLEN", "einheiten: keine sichtbare Empfehlung");
  contains(html, "aus deinem Zustand, den letzten Tagen und deinem Ziel",
           "einheiten: Herkunft der Empfehlung fehlt");
  ok((html.match(/class="leadrec"/g) || []).length === 1, "einheiten: nicht genau eine Leitempfehlung");
  const leadBox = html.slice(html.indexOf('class="leadrec"'), html.indexOf('class="secname"'));
  ok(/data-act="plan"/.test(leadBox), "einheiten: Empfehlung ohne Kalenderknopf");
  ok(/\d+ W/.test(leadBox) || /\d+ bpm/.test(leadBox), "einheiten: Empfehlung ohne Zielwerte");
  contains(html, "das ist die Empfehlung von oben", "einheiten: Karte nicht mit der Leitaussage verknüpft");
  // the marked card must be one that fits - never one that is advised against
  const flaggedCard = html.slice(html.indexOf("recflag")).split('class="wocard')[0];
  ok(!/heute nicht/.test(flaggedCard), "einheiten: abgeratene Einheit als Empfehlung markiert");
  ok(/passt heute/.test(html.slice(0, html.indexOf("recflag") + 1800)),
     "einheiten: Empfehlung ohne passendes Urteil");
  // the decisive case: when the FIRST card is advised against, the mark has to
  // move down the list - taking index 0 would recommend exactly what the state
  // forbids
  const flipped = F.workouts();
  flipped.workouts[0] = { ...flipped.workouts[0], fit: "no",
                          stage: F.stageOf("no", true, false),
                          fit_reason: "Heute nicht, der Einbruch ist akut." };
  p._workouts = flipped;
  const moved = p.rTrainer(F.coach("ready"), F.readiness());
  const firstCard = moved.slice(moved.indexOf('class="wocard')).split('class="wocard').slice(0, 2).join("");
  ok(!/recflag/.test(firstCard),
     "einheiten: abgeratene erste Einheit trägt die Empfehlung");
  ok((moved.match(/class="recflag"/g) || []).length === 1,
     "einheiten: Empfehlung verschwunden statt verschoben");
  p._workouts = F.workouts();

  // in a rebound the recommendation must move to a session that fits
  const rb = p.rTrainer(F.coach("rebound"), F.readiness());
  ok((rb.match(/class="recflag"/g) || []).length === 1,
     "einheiten rebound: Empfehlung fehlt oder mehrfach");
  ok(!/class="recflag"[\s\S]{0,400}heute nicht/.test(rb),
     "einheiten rebound: abgeratene Einheit als Empfehlung markiert");
  contains(html, "Was du machst, entscheidest du", "einheiten: Entscheidung nicht beim Athleten");
  contains(html, "215 W", "einheiten: FTP nicht genannt");
  contains(html, "237 W", "einheiten: Wattzahlen der Blöcke fehlen");   // 110 % von 215
  contains(html, "166–180 bpm", "einheiten: Pulsfenster fehlt");
  ok((html.match(/class="wob"/g) || []).length >= 20, "einheiten: Struktur nicht gezeichnet");
  ok((html.match(/data-act="plan"/g) || []).length === 14,
     "einheiten: Kalenderknöpfe unvollständig");   // 6 Karten + Leitempfehlung, je heute/morgen

  // In a rebound the hard kinds must stay VISIBLE, marked and explained.
  // Filtering them away leaves three base rides and no decision to make -
  // that was the defect this release exists to fix.
  p._workouts = F.workouts("einbruch");
  const rebound = p.rTrainer(F.coach("rebound"), rdFix);
  clean(rebound, "einheiten rebound");
  for (const family of families) contains(rebound, family, `einheiten rebound: ${family} verschwunden`);
  contains(rebound, "heute nicht", "einheiten rebound: kein abratendes Urteil");
  contains(rebound, F.STAGE_WORDS.yellow.word, "einheiten rebound: keine Zwischenstufe");
  contains(rebound, "tragen noch keinen harten Reiz", "einheiten rebound: Urteil ohne Begründung");
  ok((rebound.match(/class="wocard/g) || []).length === 6,
     "einheiten rebound: Auswahl wurde gefiltert statt bewertet");

  ok(!html.includes("Protokollnamen sind keine Verschreibungen"),
     "einheiten: Belege stehen ungefragt als Textwand da");
  p._woOpen = "vo2_4x4";
  const open = p.rTrainer(F.coach("ready"), rdFix);
  clean(open, "einheiten aufgeklappt");
  contains(open, "Protokollnamen sind keine Verschreibungen", "einheiten: Grenze fehlt");
  contains(open, "Erwartetes DFA", "einheiten: erwarteter DFA-Bereich fehlt");
  // the steps shown must be the ones that go to Intervals - in WATTS. This is
  // where the percentages survived three releases: the panel printed
  // entry.text while the backend had already computed entry.text_w.
  const steps = open.slice(open.indexOf("Schritte, wie sie in Intervals landen"));
  const block = steps.slice(0, steps.indexOf("</pre>"));
  ok(!/%/.test(block), `einheiten: Schritte tragen Prozente statt Watt (${block.slice(-90)})`);
  ok(/\d+w/.test(block), "einheiten: Schritte ohne Wattwerte");
  p._woOpen = null;

  p._workouts = F.workouts("ohneFTP");
  const noftp = p.rTrainer(F.coach("ready"), rdFix);
  clean(noftp, "einheiten ohne FTP");
  ok(!noftp.includes("undefined W"), "einheiten: erfundene Wattzahlen ohne FTP");
  p._workouts = F.workouts("leer");
  clean(p.rTrainer(F.coach("ready"), rdFix), "einheiten leer");
  p._workouts = null;
  clean(p.rTrainer(F.coach("ready"), rdFix), "einheiten null");
  p._workouts = F.workouts();
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
    contains(html, "gegen deine 18 früheren Einheiten", "einordnung: Vergleichsgruppe nicht benannt");
    contains(html, "bis mindestens 6 Vergleichswerte", "einordnung: die Weitung wird verschwiegen");
    // Die gegriffene Stufe steht bei der Zeile, und die Dauerspanne NIE als
    // symmetrisches ± - der Log-Caliper ist in Prozent unsymmetrisch, ein
    // einzelnes ± wäre in einer Richtung gelogen.
    contains(html, "0,4 SD", "einordnung: gegriffene Stufe nicht ausgewiesen");
    contains(html, "-19 % bis +23 %", "einordnung: Dauerspanne nicht mit beiden Zahlen");
    ok(!/±\s*\d+(,\d+)?\s*%/.test(html), "einordnung: Dauerspanne als symmetrisches ± ausgewiesen");
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
    // Zwei Gründe, zwei Sätze. Der Anfangsfall heilt mit der Zeit, der andere
    // nicht - sie dürfen nicht dieselbe Formulierung bekommen.
    contains(thin, "zu früh in deiner Historie", "einordnung: Anfangsfall ohne eigenen Satz");
    contains(thin, "zu wenige vergleichbare Einheiten", "einordnung: dünner Fall ohne eigenen Satz");
    ok(thin.indexOf("zu früh in deiner Historie") !== thin.indexOf("zu wenige vergleichbare"),
       "einordnung: die beiden Dünn-Gründe sind im Panel nicht unterscheidbar");
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

/* ── A2  Zeitfenster: vier Fallen, jede einzeln ────────────────────────── */
{
  const WINS = ["42d", "3m", "6m", "12m", "all"];
  const render = (win, pick) => {
    const q = new M.Panel();
    q._nowIso = F.TODAY;
    q._win.dfa = win;
    if (pick) q._dfaPick = pick;
    return q.rDfa(thr, "all");
  };
  const lead = (h) => (String(h).match(/lead1[^>]*>([^<]*)</) || [])[1] || "";
  const rowsOf = (h) => (String(h).match(/data-act="dfapick"/g) || []).length;
  // only the Y labels: they are the ones that must not move. The X labels are
  // month ticks and OF COURSE change with the window - matching them too made
  // this check fail for the right reason at the wrong place.
  const yAxis = (h) => (String(h).match(/text-anchor="end" class="ax">[^<]*</g) || []).join(",");

  // the picker itself
  const base = render({ id: "3m" });
  clean(base, "dfa fenster");
  contains(base, 'role="radiogroup"', "fenster: keine Radiogruppe");
  for (const label of ["42 T", "3 M", "6 M", "12 M", "alles", "eigener Zeitraum"]) {
    contains(base, ">" + label + "<", "fenster: Chip " + label);
  }
  contains(base, "verschiebt sich täglich", "fenster: relativ nicht als relativ gekennzeichnet");
  ok(/\d+ von \d+ Einheiten im Fenster/.test(base), "fenster: Zähler n von N fehlt");
  ok(/aria-checked="true"[\s\S]{0,90}data-id="3m"/.test(base), "fenster: 3 M nicht vorausgewählt");

  // FALLE 1 - the headline must not depend on the window.
  // Relative windows all END at now, so their last five solid readings are
  // the SAME five - comparing only those cannot show the defect. A frozen
  // range that ends in the past can, and that is the case that decides it.
  const PAST = { id: "custom", from: "2026-04-01", to: "2026-06-01" };
  const leads = WINS.map((id) => lead(render({ id }))).concat(lead(render(PAST)));
  ok(new Set(leads).size === 1 && leads[0].trim() !== "",
     "FALLE 1: Leitzahl ändert sich mit dem Fenster (" + leads.join(" | ") + ")");
  // the same for the power and the change beside it
  const side = (h) => (String(h).match(/small2[^>]*>([^<]*)</g) || []).join("|");
  ok(new Set(WINS.concat([0]).map((id, i) => side(render(i === WINS.length ? PAST : { id })))
       .map((s) => s.split("|").slice(0, 2).join("|"))).size === 1,
     "FALLE 1: Schwellenleistung oder Veränderung hängen am Fenster");
  // and the contrast: the count of readings SHOULD follow the window, or the
  // card would claim a sample size it is not showing
  ok(/belastbar im Fenster/.test(base), "FALLE 1: Messungszahl nicht als Fensterzahl gekennzeichnet");
  contains(base, "über den gesamten Bestand, nicht über das Fenster",
           "FALLE 1: Quellzeile sagt nicht, worüber gerechnet wird");
  contains(base, "Median der letzten 5 belastbaren Messungen",
           "FALLE 1: Rechenweg der Leitzahl nicht benannt");
  // the sport DOES move it - and the source line has to say which sport
  contains(p.rDfa(thr, "ride"), "Rad", "FALLE 1: Sportart nicht in der Quellzeile");

  // FALLE 2 - no median line under five solid readings, left out not thinned
  const thin = thr.map((x) => ({ ...x, samples: 2 }));
  const thinHtml = (() => { const q = new M.Panel(); q._nowIso = F.TODAY; q._win.dfa = { id: "all" }; return q.rDfa(thin, "all"); })();
  clean(thinHtml, "dfa dünn im Fenster");
  contains(thinHtml, "keine Medianlinie gezeichnet", "FALLE 2: dünne Lage ohne Hinweis");
  ok((String(thinHtml).match(/<path d="M[^"]*" fill="none"/g) || []).length === 0,
     "FALLE 2: Medianlinie trotz unter fünf belastbaren Messungen gezeichnet");
  ok(!render({ id: "all" }).includes("keine Medianlinie gezeichnet"),
     "FALLE 2: Hinweis auch bei ausreichender Lage");
  ok((String(render({ id: "all" })).match(/<path d="M[^"]*" fill="none"/g) || []).length > 0,
     "FALLE 2: keine Medianlinie bei ausreichender Lage");

  // FALLE 3 - the y axis is scaled over the stock, not per window.
  // The plain fixture cannot show this defect: its thresholds cycle through
  // the same 150-171 band, so every window has the same span and a per-window
  // axis looks identical. A test that cannot fail is not a test - so this one
  // runs against a series that TRENDS, where early and late differ by 55 bpm.
  const trending = thr.map((x, i) => ({ ...x, hr: 130 + i, power: 140 + i, samples: 12 }));
  const trendAxis = (id) => {
    const q = new M.Panel();
    q._nowIso = F.TODAY;
    q._win.dfa = { id };
    return yAxis(q.rDfa(trending, "all"));
  };
  const axes = WINS.map(trendAxis);
  ok(new Set(axes).size === 1 && axes[0].length > 0,
     "FALLE 3: Y-Achse wird je Fenster neu skaliert (" + axes.map((a) => a.length).join(",") + ")");
  // and the axis really does span the whole stock, not just the newest window.
  // Checked on the LOWEST tick actually drawn, not on a label that happens to
  // exist: tickVals picks round steps, so "there is a 130 somewhere" can be
  // false while the axis is perfectly correct. Inside 42 T the readings start
  // at 171 - an axis scaled per window could not reach down to 160.
  const trendHtml = (id) => {
    const q = new M.Panel();
    q._nowIso = F.TODAY;
    q._win.dfa = { id };
    return String(q.rDfa(trending, "all"));
  };
  const lowTick = (id) => {
    const vals = (trendHtml(id).match(/text-anchor="end" class="ax">([\d.]+)</g) || [])
      .map((s) => parseFloat(s.replace(/.*>/, "")));
    return vals.length ? Math.min(...vals) : NaN;
  };
  ok(lowTick("42d") <= 160,
     "FALLE 3: enges Fenster reicht auf der Achse nicht unter seine eigenen Werte (tiefster Tick "
     + lowTick("42d") + ", das Fenster selbst beginnt bei 171)");
  ok(lowTick("42d") === lowTick("all"),
     "FALLE 3: tiefster Tick unterscheidet sich zwischen engem und vollem Fenster");
  // the flat fixture must not move either, for the same reason
  ok(new Set(WINS.map((id) => yAxis(render({ id })))).size === 1,
     "FALLE 3: Y-Achse wandert schon bei gleichförmiger Lage");

  // FALLE 4 - the list follows the window
  const counts = WINS.map((id) => rowsOf(render({ id })));
  ok(counts.every((c, i) => i === 0 || c >= counts[i - 1]),
     "FALLE 4: Liste folgt dem Fenster nicht (" + counts.join(",") + ")");
  ok(counts[0] < counts[counts.length - 1], "FALLE 4: enges und weites Fenster gleich lang");
  ok(counts[0] > 0, "FALLE 4: engstes Fenster leer");

  // a frozen range says so, and an empty one speaks instead of showing nothing
  const cu = render({ id: "custom", from: "2026-06-01", to: "2026-07-01" });
  clean(cu, "dfa eigener zeitraum");
  contains(cu, "eingefroren", "fenster: eigener Zeitraum nicht als eingefroren benannt");
  ok(rowsOf(cu) > 0 && rowsOf(cu) < rowsOf(render({ id: "all" })),
     "fenster: eigener Zeitraum filtert nicht");
  const none = render({ id: "custom", from: "2020-01-01", to: "2020-02-01" });
  clean(none, "dfa leeres fenster");
  contains(none, "Keine Messung in diesem Zeitraum", "fenster: leeres Fenster schweigt");

  // capped, and the cap is spoken
  const many = Array.from({ length: 200 }, (_, i) => ({
    date: `2026-0${1 + (i % 9)}-${String(1 + (i % 28)).padStart(2, "0")}`,
    activity_id: "m" + i, type: "Ride", hr: 150 + (i % 10), power: 140, samples: 12,
  }));
  const capped = (() => { const q = new M.Panel(); q._nowIso = F.TODAY; q._win.dfa = { id: "all" }; return q.rDfa(many, "all"); })();
  clean(capped, "dfa gekappt");
  ok(rowsOf(capped) === 50, "Kappung: nicht auf 50 Zeilen gekappt (" + rowsOf(capped) + ")");
  contains(capped, "Zeilen gezeigt", "Kappung: schweigt über die Kappung");

  // window filtering is pure: same input, same answer
  ok(JSON.stringify(M.winApply(thr, { id: "3m" }, F.TODAY).rows)
     === JSON.stringify(M.winApply(thr, { id: "3m" }, F.TODAY).rows), "fenster: Filter nicht deterministisch");
  // relative windows have NO upper bound - a reading dated tomorrow stays
  const future = thr.concat([{ date: "2099-01-01", activity_id: "future", type: "Ride",
                               hr: 152, power: 150, samples: 12 }]);
  ok(M.winApply(future, { id: "42d" }, F.TODAY).rows.some((r) => r.activity_id === "future"),
     "fenster: zukunftsdatierte Messung verschwindet wortlos");
}

/* ── A1  Brushing & Linking: ein Auswahlzustand, beide Richtungen ──────── */
{
  // pick from the NEWEST readings: the list is capped at 50, so the oldest
  // entries have a point but no row - which is correct, and would make this
  // check fail for a reason that has nothing to do with brushing
  const solid = thr.slice(-10).find((x) => x.samples >= 5 && x.hr > 0);
  const weak = thr.slice(-10).find((x) => x.samples < 5) || thr.find((x) => x.samples < 5);
  const q = new M.Panel();
  q._nowIso = F.TODAY;
  q._win.dfa = { id: "all" };
  const plain = q.rDfa(thr, "all");
  q._dfaPick = solid.activity_id;
  const marked = q.rDfa(thr, "all");
  clean(marked, "dfa mit Auswahl");

  // graph side: every pickable point carries its activity_id
  ok((String(plain).match(/data-dot="/g) || []).length > 0, "A1: kein Punkt trägt eine activity_id");
  contains(plain, `data-dot="${solid.activity_id}"`, "A1: belastbarer Punkt nicht markierbar");
  ok(!String(plain).includes(`data-dot="${weak.activity_id}"`),
     "A1: dünne Messung ist markierbar, obwohl sie hohl gezeichnet ist");
  // list side: the row carries the same key, and the key is the activity_id -
  // not the index and not the date, because one day can hold two sessions
  contains(plain, `data-aid="${solid.activity_id}"`, "A1: Zeile trägt keine activity_id");
  ok(!String(plain).includes('data-aid=""'), "A1: Zeile ohne Schlüssel");
  // fixed selection is rendered, and it is undoable
  ok(String(marked).includes("brushed"), "A1: feste Auswahl wird nicht gerendert");
  ok(!String(plain).includes("brushed"), "A1: Markierung ohne Auswahl");
  contains(marked, "Auswahl aufheben", "A1: kein Weg aus der Auswahl");
  contains(marked, 'data-act="dfaclear"', "A1: Aufheben ohne Handler");
  // and the selected session is named, not just highlighted
  contains(marked, "Ausgewählt:", "A1: Auswahl nicht benannt");
  // a selection that no longer exists in the window must not break the view
  q._dfaPick = "gibtesnicht";
  clean(q.rDfa(thr, "all"), "dfa Auswahl ohne Treffer");
  q._dfaPick = null;
}

/* ── A3/A4  Spalten und Sprung in die Einheit ──────────────────────────── */
{
  const q = new M.Panel();
  q._nowIso = F.TODAY;
  const html = q.rDfa(thr, "all");
  for (const col of ["Δ Median", "Dauer", "Last", "Ø HF", "Entkopplung", "Güte"]) {
    contains(html, ">" + col + "<", "A3: Spalte " + col);
  }
  // the deviation is the number the tab is about - in bpm, with a sign
  ok(/[+-]\d+ bpm/.test(html), "A3: keine Abweichung mit Vorzeichen in bpm");
  // A4: the row offers the jump, and the jump carries the activity_id
  contains(html, 'data-act="gotoact"', "A4: kein Sprung in die Einheit");
  ok(/data-act="gotoact" data-id="act\d+"/.test(html), "A4: Sprung ohne activity_id");
  // a payload from an older backend has none of the new fields - the columns
  // must read "–" rather than "undefined"
  const bare = thr.map((x) => ({ date: x.date, activity_id: x.activity_id, type: x.type,
                                 hr: x.hr, power: x.power, samples: x.samples }));
  clean(q.rDfa(bare, "all"), "dfa ohne die neuen Felder");
}

/* ── A5  die aufgeklappte Signalkarte bekommt eine Achse ───────────────── */
{
  const q = new M.Panel();
  q._nowIso = F.TODAY;
  const closed = q.rHeute(F.today());
  clean(closed, "heute zugeklappt");
  ok(!String(closed).includes("evtrack"), "A5: Ereignisspur auch zugeklappt");
  q._sigOpen = "hrv";
  const open = q.rHeute(F.today());
  clean(open, "heute aufgeklappt");
  contains(open, "evtrack", "A5: keine Ereignisspur in der aufgeklappten Karte");
  contains(open, 'data-rdo="tsig_hrv"', "A5: keine feste Ableseleiste");
  ok(/class="ax">\d\d\.\d\d\.</.test(open), "A5: keine Datumsbeschriftung mit Monat");
  contains(open, "Trainingstag", "A5: Spur ohne Direktbeschriftung");
  // degrade honestly: without dates, no axis and no track - never an invented one
  const noDates = { ...F.today() };
  delete noDates.history_days;
  const bare = q.rHeute(noDates);
  clean(bare, "heute ohne history_days");
  ok(!String(bare).includes("evtrack"), "A5: Spur ohne Datumsquelle gezeichnet");
  ok(!String(bare).includes('data-rdo="tsig_hrv"'), "A5: leere Ableseleiste ohne Datumsquelle");
  q._sigOpen = null;
}

/* ── dayAxis: die Regel selbst ─────────────────────────────────────────── */
{
  const days = Array.from({ length: 42 }, (_, i) =>
    new Date(Date.parse("2026-09-11T00:00:00Z") - (41 - i) * 864e5).toISOString().slice(0, 10));
  const ax = M.dayAxis(days);
  ok(ax.ticks.includes(41), "dayAxis: der neueste Tag trägt keinen Tick");
  ok(ax.ticks.length >= 6, "dayAxis: zu wenige Ticks (" + ax.ticks.length + ")");
  ok(ax.labels.length < ax.ticks.length, "dayAxis: jeder Tick beschriftet");
  ok(ax.labels.some((l) => /^\d\d\.\d\d\.$/.test(l.t)), "dayAxis: kein Monatswechsel beschriftet");
  // a month change is always labelled, even off the 14-day grid
  const crossing = ["2026-07-30", "2026-07-31", "2026-08-01", "2026-08-02"];
  const cax = M.dayAxis(crossing, { every: 3, label: 99 });
  ok(cax.labels.some((l) => l.t === "01.08."), "dayAxis: Monatswechsel ohne Beschriftung");
  ok(M.dayAxis([]).ticks.length === 0, "dayAxis: leere Liste erzeugt Ticks");
  ok(M.dayAxis(null).ticks.length === 0, "dayAxis: null erzeugt Ticks");
  ok(M.dayAxis(["kaputt", "2026-09-11"]).ticks.length >= 1, "dayAxis: Schrottdatum wirft");
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

/* ── Tagesbeschriftung (Paket B5): Chips, Marker, Dialog ────────────────── */
{
  const q = new M.Panel();
  q._nowIso = F.TODAY;
  q._dayctx = F.dayContext();

  // Heute: jede Tagesspalte ist klickbar, beschriftete Tage tragen den Marker
  const page = q.rHeute(F.today());
  clean(page, "beschriftung heute");
  ok((page.match(/class="tday [^"]*" data-act="daylabel"/g) || []).length === 7,
     "beschriftung: nicht jede Tagesspalte klickbar");
  contains(page, "klicken zum Beschriften", "beschriftung: keine Einladung im Titel");
  contains(page, "Etikett: Nachtschicht", "beschriftung: Etikett fehlt im Tagestitel");
  ok((page.match(/class="ctxmark"/g) || []).length >= 1,
     "beschriftung: beschrifteter Tag ohne Marker");

  // Rückfall-Hinweis: nur wenn das Backend ihn liefert, und dann mit Zahlen
  const note = "Basislinie auf ungewichtet zurückgefallen — nur 25 belastbare Tage von 30 nötigen, 6 Tage sind etikettiert";
  const withNote = q.rHeute({ ...F.today(), context_note: note });
  contains(withNote, "25 belastbare", "beschriftung: Hinweis ohne Zahlen");
  ok(/class="ctxnote"/.test(withNote), "beschriftung: Hinweiszeile fehlt");
  ok(!/class="ctxnote"/.test(page), "beschriftung: Hinweis ohne Anlass");

  // Kalender: Vergangenheit klickbar, Zukunft nicht, Marker in der Kopfzeile
  const cellPast = q._dayCell({ date: "2026-09-10", weekday: 3, week: "2026-W37" }, F.TODAY);
  ok(/data-act="daylabel"/.test(cellPast), "beschriftung: Kalenderzelle nicht klickbar");
  ok(/class="ctxmark"/.test(cellPast), "beschriftung: Kalendermarker fehlt");
  contains(cellPast, "Etikett: Nachtschicht", "beschriftung: Markertitel ohne Etikettname");
  const cellFut = q._dayCell({ date: "2026-09-20", weekday: 6, week: "2026-W38", future: true }, F.TODAY);
  ok(!/data-act="daylabel"/.test(cellFut),
     "beschriftung: Zukunftstag klickbar — ein Etikett beschreibt eine Messung, keinen Plan");

  // Der Dialog: fest zentriert, Chips aus dem Vokabular, Entfernen ist anders
  q._ctxDlg = "2026-09-10";
  const dlg = q._ctxPopover();
  clean(dlg, "beschriftung dialog");
  ok((dlg.match(/class="ctxchip[ "]/g) || []).length === 7,
     "beschriftung: nicht alle sieben Etiketten als Chip");
  for (const lbl of ["Normal", "Nachtschicht", "Spätschicht", "Alkohol", "Reise", "Krank", "Uhr nicht getragen"]) {
    contains(dlg, lbl, `beschriftung: Chip „${lbl}“ fehlt`);
  }
  ok((dlg.match(/data-act="ctxset"/g) || []).length === 7, "beschriftung: Chips ohne Schreibweg");
  contains(dlg, "Gewicht 0,5", "beschriftung: Chip ohne Gewichtsangabe");
  // Auswahl trägt Form UND Wort: Klasse on, Haken, "gewählt"
  ok(/class="ctxchip on"/.test(dlg), "beschriftung: aktueller Chip nicht markiert");
  contains(dlg, "gewählt", "beschriftung: Auswahl ohne Wort");
  // Entfernen: eigene Zeile, eigener Schreibweg, als Rücknahme erklärt
  ok(/class="ctxremove"/.test(dlg) && /data-act="ctxdel"/.test(dlg),
     "beschriftung: kein Löschweg");
  contains(dlg, "Etikett entfernen", "beschriftung: Löschweg unbenannt");
  contains(dlg, "Rücknahme, keine Aussage", "beschriftung: Löschen nicht von „normal“ unterschieden");
  ok(!/ctxremove[^>]*--cc/.test(dlg),
     "beschriftung: Entfernen trägt eine Kategorienfarbe — es ist keine Kategorie");
  // Quellenblock nach Auflage A: belegt, Setzung, B4 — und der Erklärtext (Auflage B)
  contains(dlg, "Sensors 2021", "beschriftung: Altini/Plews fehlt");
  contains(dlg, "PLOS ONE 2013", "beschriftung: Boudreau/Boivin fehlt");
  contains(dlg, "Setzung", "beschriftung: Setzungen nicht als Setzung benannt");
  contains(dlg, "B4", "beschriftung: die saubere Lösung ist nicht benannt");
  contains(dlg, "Messbedingung, nicht dein Zustand", "beschriftung: Erklärtext fehlt");
  contains(dlg, "gesehen, benannt", "beschriftung: was „erklärt“ heißt, fehlt");
  // ohne Eintrag: kein Löschweg, nichts vorgewählt
  q._ctxDlg = "2026-09-09";
  const dlg2 = q._ctxPopover();
  ok(!/ctxremove/.test(dlg2), "beschriftung: Löschweg ohne Eintrag");
  ok(!/class="ctxchip on"/.test(dlg2), "beschriftung: Vorauswahl ohne Eintrag");
  q._ctxDlg = null;

  // fester Dialog, kein am Klickpunkt schwebender Kasten (0.9.x-Klasse):
  // keine Inline-Koordinaten am Dialog, Position kommt aus dem Stylesheet
  ok(!/ctxdlg" style=/.test(dlg), "beschriftung: Dialog mit Inline-Position");
  const css = H.source();
  ok(/\.ctxdlg\{position:fixed/.test(css), "beschriftung: Dialog nicht fest positioniert");
  ok(/\.ctxback\{position:fixed/.test(css), "beschriftung: kein Backdrop");
  ok(/\.ctxremove\{[^}]*dashed/.test(css), "beschriftung: Entfernen nicht sichtbar anders (gestrichelt)");
  // Zukunftssperre sitzt im Klickweg
  ok(/id <= this\._now\(\)/.test(css), "beschriftung: Zukunftssperre fehlt im Klickweg");

  // Hohle Punkte: w=0-Tage bleiben gezeichnet, zählen sichtbar nicht
  const t = F.today();
  const hd = t.history_days.slice();
  hd[hd.length - 2] = { ...hd[hd.length - 2], context: { tag: "nachtschicht", weight: 0 } };
  const tCtx = { ...t, history_days: hd };
  q._sigOpen = "hrv";
  const open = q.rHeute(tCtx);
  ok(/fill="none" stroke="[^"]+" stroke-width="1.6"/.test(open),
     "beschriftung: w=0-Tag nicht hohl gezeichnet");
  contains(open, "Hohle Punkte", "beschriftung: Hohlpunkte unerklärt");
  contains(open, "zählen nicht in die Basislinie", "beschriftung: Bedeutung der Hohlpunkte fehlt");
  const xl = q._grp.tsig_hrv && q._grp.tsig_hrv.xl;
  ok(xl && xl(hd.length - 2).includes("Etikett: Nachtschicht"),
     "beschriftung: Ablesestreifen nennt das Etikett nicht");
  ok(xl && !xl(0).includes("Etikett"), "beschriftung: Ablesestreifen etikettiert unbeschriftete Tage");
  q._sigOpen = null;
}

/* ── Schreibweg: Scroll-Erhalt, Neuladen, Fehlerweg (async) ─────────────── */
(async () => {
  const q = new M.Panel();
  q._nowIso = F.TODAY;
  q._weeks = 8;
  q._sigDays = 120;
  q._dayctx = F.dayContext();

  let scroll = 640, renders = 0;
  Object.defineProperty(q, "scrollTop", { get: () => scroll, set: (v) => { scroll = v; } });
  const calls = [];
  q._ws = async (type, extra) => {
    calls.push([type, extra || null]);
    if (type === "set_day_context") return { date: extra.date, entry: extra.tag ? { tag: extra.tag } : null };
    if (type === "day_context") return F.dayContext();
    if (type === "days") return F.days();
    if (type === "today") return F.today();
    if (type === "coach") return F.coach();
    if (type === "signals") return F.signals();
    return {};
  };
  // innerHTML wirft die Scroll-Lage mit den alten Knoten weg — genau das
  // simuliert der Render-Stummel, und der Schreibweg muss sie restaurieren.
  q._render = () => { renders++; scroll = 0; };

  q._ctxDlg = "2026-09-10";
  await q._ctxWrite("2026-09-10", "krank");
  ok(scroll === 640, `beschriftung schreiben: Scroll-Lage verloren (${scroll} statt 640)`);
  ok(renders === 1, "beschriftung schreiben: kein Re-Render");
  ok(q._ctxDlg === null, "beschriftung schreiben: Dialog bleibt offen");
  const sent = calls.find(([t]) => t === "set_day_context");
  ok(!!sent && sent[1].date === "2026-09-10" && sent[1].tag === "krank",
     "beschriftung schreiben: falscher Schreibaufruf");
  for (const need of ["today", "days", "day_context", "coach"]) {
    ok(calls.some(([t]) => t === need), `beschriftung schreiben: ${need} nicht neu geladen`);
  }
  ok(!calls.some(([t]) => t === "signals"),
     "beschriftung schreiben: signals geladen, obwohl der Reiter nie offen war");

  // mit geladenen Signalen wird auch die Signale-Ansicht aufgefrischt
  calls.length = 0; q._signals = F.signals(); q._ctxDlg = "2026-09-07";
  await q._ctxWrite("2026-09-07", null);
  const del = calls.find(([t]) => t === "set_day_context");
  ok(!!del && del[1].tag === null, "beschriftung löschen: tag=null wird nicht gesendet");
  ok(calls.some(([t]) => t === "signals"), "beschriftung löschen: Signale nicht aufgefrischt");

  // Fehlerweg: Dialog bleibt offen, Fehler wird gezeigt, nichts stürzt
  calls.length = 0; renders = 0; scroll = 300;
  q._ws = async () => { throw new Error("unbekanntes Etikett: 'erfunden'"); };
  q._ctxDlg = "2026-09-10";
  await q._ctxWrite("2026-09-10", "erfunden");
  ok(q._ctxDlg === "2026-09-10", "beschriftung fehler: Dialog verschwindet mit dem Fehler");
  ok(String(q._ctxErr || "").includes("unbekanntes Etikett"),
     "beschriftung fehler: Meldung erreicht den Dialog nicht");
  ok(renders === 1, "beschriftung fehler: Fehlanzeige ohne Re-Render");

  // Sperre gegen Doppelklick: während busy wird nicht erneut geschrieben
  let writes = 0;
  q._ws = async (type) => { if (type === "set_day_context") writes++; return {}; };
  q._ctxBusy = true;
  await q._ctxWrite("2026-09-10", "krank");
  ok(writes === 0, "beschriftung: Doppelklick schreibt doppelt");
  q._ctxBusy = false;

  /* ── Abgleich mit Intervals (Paket D) ─────────────────────────────────── */
  const REP = (over) => Object.assign({
    oldest: "2025-05-13", newest: F.TODAY, full_history: true, checked: 240,
    remote: 239, missing: [], share: 0, capped: false, cap_limit: 0.2,
    removable: [], applied: false,
  }, over || {});
  const MISS = [
    { id: "i1", kind: "activity", date: "2026-09-04", name: "Feierabendrunde", type: "Ride", dfa: true },
    { id: "i2", kind: "activity", date: "2026-08-30", name: "Lauf", type: "Run", dfa: false },
    { id: "i3", kind: "unavailable", date: null, name: "", type: "", dfa: false },
  ];

  const s = new M.Panel();
  s._nowIso = F.TODAY;

  // 1 - Gleichstand: keine Liste, kein Vollzugsknopf
  s._syncDlg = { state: "report", report: REP() };
  let dlg = s._syncPopover();
  clean(dlg, "abgleich gleichstand");
  contains(dlg, "Gleichstand", "abgleich: Gleichstand wird nicht gesagt");
  ok(!dlg.includes('data-act="syncgo"'), "abgleich: Vollzugsknopf ohne Befund");

  // 2 - Befund: erst anzeigen, was verschwinden würde
  s._syncDlg = { state: "report", report: REP({ missing: MISS, share: 3 / 240,
                                                removable: ["i1", "i2", "i3"] }) };
  dlg = s._syncPopover();
  clean(dlg, "abgleich befund");
  ok((dlg.match(/class="syncrow"/g) || []).length === 3, "abgleich: nicht jede Einheit gezeigt");
  contains(dlg, "Feierabendrunde", "abgleich: Name aus dem Archiv fehlt");
  contains(dlg, "Strava-Platzhalter", "abgleich: der Platzhalter wird nicht benannt");
  contains(dlg, "inkl. DFA", "abgleich: die mitgehende DFA-Auswertung wird verschwiegen");
  contains(dlg, 'data-act="syncgo"', "abgleich: kein Vollzugsknopf trotz Befund");
  contains(dlg, "liest nur", "abgleich: die Einbahnstraße wird nicht gesagt");

  // 3 - Deckelung: gemeldet, aber kein Vollzug
  s._syncDlg = { state: "report", report: REP({ missing: MISS, share: 0.5, capped: true,
                                                removable: [] }) };
  dlg = s._syncPopover();
  clean(dlg, "abgleich deckelung");
  ok(!dlg.includes('data-act="syncgo"'), "abgleich deckelung: Vollzug trotz Deckelung angeboten");
  contains(dlg, "nichts", "abgleich deckelung: es fehlt die Aussage, dass nichts entfernt wurde");
  contains(dlg, "50 %", "abgleich deckelung: der Anteil wird nicht beziffert");
  ok((dlg.match(/class="syncrow"/g) || []).length === 3,
     "abgleich deckelung: der Befund wird nicht gezeigt");

  // 4 - Fehler und Zwischenstand sagen beide: es wurde nichts entfernt
  s._syncDlg = { state: "error", msg: "server error 502 on /activities" };
  dlg = s._syncPopover();
  clean(dlg, "abgleich fehler");
  contains(dlg, "502", "abgleich fehler: die Meldung erreicht den Dialog nicht");
  contains(dlg, "nichts entfernt", "abgleich fehler: die Unversehrtheit wird nicht zugesichert");
  s._syncDlg = { state: "report", stale: true, report: REP({ missing: MISS, removable: [] }) };
  dlg = s._syncPopover();
  contains(dlg, "geändert", "abgleich zwischenstand: die Abweichung wird nicht benannt");

  // 5 - Vollzug: das Ergebnis nennt alle drei Aufräumstellen
  s._syncDlg = { state: "done", report: REP({ applied: true,
                 removed: { activities: 2, dfa: 1, unavailable: 1 } }) };
  dlg = s._syncPopover();
  clean(dlg, "abgleich vollzug");
  contains(dlg, "DFA-Auswertungen", "abgleich vollzug: DFA-Stelle nicht beziffert");
  contains(dlg, "Platzhalter", "abgleich vollzug: unavailable-Stelle nicht beziffert");

  // 6 - der Schreibweg am simulierten Ereignis, nicht am Quelltext
  const r = new M.Panel();
  r._nowIso = F.TODAY;
  r._weeks = 8;
  let rscroll = 520, rrenders = 0;
  Object.defineProperty(r, "scrollTop", { get: () => rscroll, set: (v) => { rscroll = v; } });
  const rcalls = [];
  r._render = () => { rrenders++; rscroll = 0; };
  r._setTab = async () => {};
  r._acts = acts; r._thr = thr; r._pmc = pmc; r._coach = F.coach();
  r._ws = async (type, extra) => {
    rcalls.push([type, extra || null]);
    if (type === "reconcile" && !extra) return REP({ missing: MISS, removable: ["i1", "i2", "i3"] });
    if (type === "reconcile") return REP({ applied: true, missing: MISS,
      removed: { activities: 2, dfa: 1, unavailable: 1 },
      stats: { activities: 237, wellness_days: 489, dfa_done: 56 } });
    if (type === "status") return { activities: 237, wellness_days: 489, dfa_done: 56 };
    if (type === "days") return F.days();
    return {};
  };

  await r._syncOpen();
  const asked = rcalls.find(([t]) => t === "reconcile");
  ok(!!asked && asked[1] === null, "abgleich: die Vorschau schickt eine Bestätigung mit");
  ok(r._syncDlg && r._syncDlg.state === "report", "abgleich: die Vorschau öffnet den Dialog nicht");

  rcalls.length = 0; rrenders = 0; rscroll = 520;
  await r._syncRun();
  const done = rcalls.find(([t, e]) => t === "reconcile" && e && e.confirm);
  ok(!!done, "abgleich: der Vollzug schickt keine Bestätigung");
  ok(done && done[1].confirm.join(",") === "i1,i2,i3",
     "abgleich: der Vollzug schickt andere IDs als angezeigt");
  ok(rscroll === 520, `abgleich: Scroll-Lage verloren (${rscroll} statt 520)`);
  ok(r._acts === null && r._thr === null && r._pmc === null && r._coach === null,
     "abgleich: die aus Aktivitäten gerechneten Ansichten bleiben auf altem Stand");
  ok(rcalls.some(([t]) => t === "status"), "abgleich: der Kopfzähler wird nicht neu geholt");
  ok(r._status && r._status.activities === 237, "abgleich: der Kopf zeigt weiter die alte Zahl");
  ok(r._syncDlg && r._syncDlg.state === "done", "abgleich: das Ergebnis wird nicht gezeigt");

  // Deckelung: nichts freigegeben, also darf der Vollzug gar nicht erst gehen
  rcalls.length = 0;
  r._syncDlg = { state: "report", report: REP({ missing: MISS, capped: true, removable: [] }) };
  await r._syncRun();
  ok(!rcalls.some(([t]) => t === "reconcile"), "abgleich deckelung: der Vollzug wurde trotzdem gesendet");

  // Doppelklick
  rcalls.length = 0;
  r._syncDlg = { state: "report", report: REP({ missing: MISS, removable: ["i1"] }) };
  r._syncBusy = true;
  await r._syncRun();
  ok(!rcalls.some(([t]) => t === "reconcile"), "abgleich: Doppelklick löst zwei Abgleiche aus");
  r._syncBusy = false;

  // Fehlerweg: Dialog bleibt stehen und sagt, dass nichts geschah
  r._ws = async () => { throw new Error("server error 502 on /activities"); };
  await r._syncOpen();
  ok(r._syncDlg && r._syncDlg.state === "error", "abgleich fehler: der Dialog fällt zurück");
  ok(String(r._syncDlg.msg || "").includes("502"), "abgleich fehler: die Meldung geht verloren");

  /* ── Durability-Kachel 0.40.0: die Wolke, und was sie verschweigt ───────
     Die Kachel rechnete seit 0.39.0 das Richtige und zeigte es nicht: zwei
     Balken bei 0,0 % und 1,4 % gegen eine Skala bis 5 %. Jetzt eine
     Punktwolke ueber der Arbeit - mit drei Regeln, die eine Leitzahl
     verhindern duerfen, und der Pflicht zu sagen, WELCHE gegriffen hat. */
  {
    const flat = F.coach("slump").durability;
    const clear = F.coach("rebound").durabilityClear;
    const tileFlat = p.rDurability(flat);
    const tileClear = p.rDurability(clear);
    clean(tileFlat, "durability flach");
    clean(tileClear, "durability klar");

    const dots = [...tileFlat.matchAll(/<circle cx="([\d.]+)" cy="([\d.]+)" r="([\d.]+)"[^>]*opacity="([\d.]+)"/g)];
    ok(dots.length === flat.points.length,
       `durability: ${dots.length} Punkte gezeichnet, ${flat.points.length} in der Payload`);
    // Das Gewicht muss SICHTBAR sein - sonst sieht man nicht, worauf der Trend
    // ruht, und die Gewichtung bliebe eine reine Backend-Behauptung.
    ok(new Set(dots.map((m) => m[3])).size > 1 && new Set(dots.map((m) => m[4])).size > 1,
       "durability: Gewicht ist im Bild nicht zu sehen (eine Groesse, eine Deckkraft)");
    // Die Punkte liegen nach ARBEIT, nicht nach Reihenfolge.
    const xs = dots.map((m) => +m[1]), kj = flat.points.map((q) => q.kj);
    const span = (xs[xs.length - 1] - xs[0]) / (kj[kj.length - 1] - kj[0]);
    ok(Math.abs((xs[1] - xs[0]) / (kj[1] - kj[0]) - span) < 0.01,
       "durability: die x-Achse laeuft ueber den Index statt ueber die Arbeit");

    // Regel 2 im Bild: ohne gesicherte Steigung KEINE Gerade.
    ok(!tileFlat.includes(M.C.violet),
       "durability flach: es wird eine Trendgerade gezeichnet, obwohl keine Leitzahl erlaubt ist");
    ok(tileClear.includes(M.C.violet), "durability klar: die gesicherte Trendgerade fehlt");
    contains(tileFlat, "Streuung", "durability flach: sagt nicht, WORAN es liegt");
    ok(!/Bis etwa/.test(tileFlat), "durability flach: nennt trotzdem einen Kipppunkt");
    contains(tileFlat, String(flat.needed_sessions),
             "durability flach: sagt nicht, was die Messung voranbraechte");
    contains(tileClear, "Bis etwa", "durability klar: keine Leitzahl trotz gesicherter Steigung");
    ok(tileFlat !== tileClear, "durability: gesperrter und tragender Fall sind nicht unterscheidbar");

    // Zwei Farbregister, die sich nie mischen: die Marke darf urteilen, die
    // Punkte nicht.
    const dotColour = /<circle[^>]*fill="([^"]+)"/.exec(tileFlat)[1].toLowerCase();
    for (const judge of [M.C.green, M.C.amber, M.C.red]) {
      ok(dotColour !== String(judge).toLowerCase(),
         `durability: die Punkte tragen mit ${judge} eine Urteilsfarbe`);
    }
    ok(tileFlat.includes(`stroke="${M.C.amber}"`),
       "durability: die Marke ist nicht im Urteilsregister gezeichnet");

    // Baender und Bloecke sagen, warum sie schweigen.
    ok(flat.bins.some((b) => b.thin) && /zu dünn/.test(tileFlat),
       "durability: zu duenn besetztes Arbeitsband nicht als solches ausgewiesen");
    contains(tileFlat, "kein gesicherter Trend", "durability: Block ohne Trend nennt seinen Grund nicht");
    contains(tileFlat, "zu dünn belegt", "durability: zu duenn belegter Block nennt seinen Grund nicht");
    // Ein tragender Block steht jetzt im KLAREN Fall - im flachen reisst jeder
    // Block eine der drei Regeln, und genau das ist der Livebefund.
    contains(tileClear, M.fmt(clear.blocks[1].tipping_kj, 0) + " kJ",
             "durability: der Kipppunkt eines tragenden Blocks fehlt");
    ok(flat.blocks.every((b) => b.tipping_kj == null),
       "durability Fixture-Beweis: der flache Fall enthaelt doch einen tragenden Block");

    // Die ehrliche Buchhaltung aus G3: "26 Einheiten" waere falsch, wenn ein
    // Teil davon fast nichts beitraegt.
    for (const needle of [String(flat.n_full), String(flat.n_partial),
                          M.fmt(flat.w_sum, 1), String(flat.dropped.no_power)]) {
      contains(tileFlat, needle, `durability Rechenweg: ${needle} fehlt`);
    }
    contains(tileFlat, "ohne Leistungsmessung",
             "durability: Fahrten ohne Leistung werden wieder als 'wellig' verkauft");
    contains(tileFlat, "Durability, spezifisch", "durability: der Verweis auf die Einheit fehlt (G5)");
    contains(tileFlat, "Hungerast", "durability: die Warnung zum Fuettern fehlt (G5)");

    ok(p._grp.dur && p._grp.dur.xy === true && p._grp.dur.pts.length === flat.points.length,
       "durability: die Wolke ist nicht als xy-Gruppe fuer den Zeiger angemeldet");
  }

  /* ── Paket H: der Kopfbereich ───────────────────────────────────────────
     Drei Zeilen, gross, in der BAUART der Signalkarten - Aufbau und
     Typografie, ausdruecklich nicht deren Farblogik. Die erste Zeile ist
     demonstrierte Faehigkeit: sie darf nie aus einem Modell kommen und nie
     verschwinden, weil die Statistik nicht traegt. */
  {
    const flat = F.coach("slump").durability;
    const clear = F.coach("rebound").durabilityClear;
    const tileFlat = p.rDurability(flat);
    const tileClear = p.rDurability(clear);
    const pr = flat.progression, prc = clear.progression;

    // H1 Zeile 1: steht da, OBWOHL der Kachelkoerper gesperrt ist.
    ok(flat.blocked === "flat", "H Fixture-Beweis: der flache Fall ist doch nicht gesperrt");
    contains(tileFlat, "WAS DU KANNST", "H1: die belegte Faehigkeit fehlt im Kopf");
    contains(tileFlat, M.hmn(pr.demonstrated.minutes),
             "H1: die belegte Dauer wird nicht genannt");
    contains(tileFlat, M.fmt(pr.demonstrated.watts, 0) + " W",
             "H1: die Leistung DIESER Fahrt fehlt");
    contains(tileFlat, M.dMed(pr.demonstrated.date), "H1: das Datum der belegten Fahrt fehlt");

    // Die Falle, die am Livebestand unsichtbar waere: die Zeile-1-Wattzahl
    // ist NICHT der Pool-Median aus der Umrechnung. Faende der Test beide
    // gleich, pruefte er die Unterscheidung ueberhaupt nicht.
    ok(pr.demonstrated.watts !== flat.power.watts,
       "H1 Fixture-Beweis: Fahrt-Leistung und Pool-Median sind in der Fixture identisch - " +
       "eine Verwechslung waere unsichtbar");
    // Faellt der Kopf ganz weg, soll der Test das ZAEHLEN und BENENNEN statt
    // am null-Treffer abzustuerzen - ein Absturz ueberspringt alles Folgende.
    const headHit = /<div class="durhead">[\s\S]*?\n    <\/div>/.exec(tileFlat);
    ok(headHit !== null, "H1: der Kopfbereich fehlt vollstaendig");
    const headFlat = headHit ? headHit[0] : "";
    ok(!headFlat.includes(M.fmt(flat.power.watts, 0) + " W"),
       "H1: im Kopf steht der Pool-Median statt der Leistung der Fahrt selbst");

    // Und die zweite: laengste Fahrt (nach ZEIT) ist nicht die
    // arbeitsreichste (nach kJ). Beide Superlative sind beschriftet.
    const heaviest = flat.points.reduce((a, b) => (b.kj > a.kj ? b : a));
    const longest = flat.points.reduce((a, b) => (b.minutes > a.minutes ? b : a));
    ok(heaviest.id !== longest.id,
       "H Fixture-Beweis: laengste und arbeitsreichste Fahrt sind dieselbe - " +
       "der Widerspruch waere nicht pruefbar");
    ok(longest.minutes === pr.demonstrated.minutes && longest.kj === pr.demonstrated.kj,
       "H1: der Kopf zeigt nicht die laengste Fahrt des Pools");
    ok(/<b>längste<\/b>/.test(headFlat), "H1: 'laengste' ist nicht als Zeitmass ausgewiesen");
    contains(tileFlat, "arbeitsreichste", "H1: die Arbeitsgroesse ist nicht als solche beschriftet");

    // H1 Zeile 2 und die Zusicherung: der Bezug kann die belegte Dauer nie
    // uebersteigen - beide stammen aus derselben Liste.
    contains(tileFlat, "WIE WEIT DU GEKOMMEN BIST", "H1: die zweite Zeile fehlt");
    for (const q of [pr, prc]) {
      ok(q.recent.minutes <= q.demonstrated.minutes,
         "H1: der Bezug uebersteigt die belegte Dauer - zwei verschiedene Grundgesamtheiten");
    }

    // H2: der naechste Schritt, der Faktor und die Grenzen der Regel.
    contains(tileFlat, "WAS ALS NÄCHSTES", "H2: die dritte Zeile fehlt");
    contains(tileFlat, M.hmn(pr.next_minutes), "H2: der naechste Schritt wird nicht genannt");
    contains(tileFlat, M.fmt(pr.factor, 2), "H2: der Faktor steht nicht in der Kachel");
    contains(tileFlat, "Läufern", "H2: die Grenze 'an Laeufern erhoben' fehlt");
    contains(tileFlat, "keine Trainingsvorschrift", "H2: der Risikoknick wird als Vorschrift verkauft");
    contains(tileFlat, M.fmt((pr.factor - 1) * 100, 0) + " %",
             "H2: der Prozentsatz wird nicht aus dem Faktor gerechnet");

    // Der Rueckfall-Fall - kein Sonderzweig, sondern die Regel, sobald Zeile 3
    // unter Zeile 1 liegt. Am Livebestand trifft das heute zu.
    ok(pr.below_demonstrated === true && prc.below_demonstrated === false,
       "H Fixture-Beweis: beide Faelle sind im Rueckfall gleich - der Zweig ist nicht pruefbar");
    contains(tileFlat, "nicht deine Bestleistung", "H2: der Rueckfall-Satz fehlt");
    contains(tileFlat, "was gerade in den Beinen steckt",
             "H2: der Rueckfall-Satz nennt den Grund nicht");
    ok(!/nicht deine Bestleistung/.test(tileClear),
       "H2: der Rueckfall-Satz steht auch da, wo der Schritt UEBER der Bestleistung liegt");

    // Ausweitung des Bezugsfensters: nie still.
    ok(prc.recent.widened === true && pr.recent.widened === false,
       "H Fixture-Beweis: kein ausgeweiteter Fall in der Fixture");
    contains(tileClear, "letzten " + M.fmt(prc.recent.days, 0) + " Tage",
             "H2: der ausgeweitete Zeitraum wird nicht genannt");
    contains(tileClear, "deshalb der weitere Zeitraum",
             "H2: die Ausweitung geschieht still");
    ok(!/deshalb der weitere Zeitraum/.test(tileFlat),
       "H2: der Ausweitungshinweis steht auch im nicht ausgeweiteten Fall");

    // Zwei Farbregister, die sich nie mischen. Der Kopf traegt KEINS davon:
    // "was du kannst" ist eine Tatsache, "was als Naechstes" eine
    // Risikoaussage - kein Ampelzustand, und das Datenregister ist in dieser
    // Ansicht schon an Wolke und Gerade vergeben.
    for (const judge of [M.C.green, M.C.amber, M.C.red]) {
      ok(!headFlat.toLowerCase().includes(String(judge).toLowerCase()),
         `H1: der Kopf traegt mit ${judge} eine Urteilsfarbe`);
    }
    for (const data of [M.C.blue, M.C.violet, M.C.cyan, M.C.magenta]) {
      ok(!headFlat.toLowerCase().includes(String(data).toLowerCase()),
         `H1: der Kopf greift mit ${data} in das Datenregister der Wolke`);
    }

    // H3: die Stueckzahl ist Beleg, nicht Botschaft - sie steht im Rechenweg.
    const cut = tileFlat.indexOf('<details class="more">');
    ok(cut > 0, "H3: der Rechenweg fehlt");
    contains(tileFlat.slice(cut), String(flat.needed_sessions),
             "H3: die Stueckzahl steht nicht im Rechenweg");
    ok(!tileFlat.slice(0, cut > 0 ? cut : undefined).includes(String(flat.needed_sessions)),
       "H3: die Stueckzahl steht weiterhin als Botschaft ueber dem Rechenweg");

    // Ein Feld aus Strichen sagt, worauf es wartet.
    contains(tileFlat, "laufende Block", "H3: das Blockfeld sagt nicht, worauf es wartet");
    contains(tileFlat, M.fmt(flat.blocks[2].need_w, 1),
             "H3: das Blockfeld nennt das fehlende Gewicht nicht");
    ok(!/laufende Block/.test(tileClear),
       "H3: die Wartezeile steht auch da, wo der juengste Block traegt");
  }

  /* ── Wochenplan: Stufen nur in der laufenden Woche (docs/ausbau.md I2/I3) ──
   Die Ansicht ist seit 0.33.0 da; neu ist, dass die LAUFENDE Woche bewertet
   wird und die späteren einen Satz tragen statt einer Stufe. Beides wird hier
   gegeneinander geprüft - eine Prüfung, die nur die Stufen sucht, würde eine
   Ansicht durchlassen, die sie über alle acht Wochen druckt. */
{
  const q = new M.Panel();
  q._nowIso = F.TODAY;
  const g = F.goal();
  const plan = g.plan;

  // eingeklappt: die laufende Woche trägt Stufen an den Chips, die anderen nicht
  const folded = q.rPlanWeeks(g);
  clean(folded, "wochenplan");
  contains(folded, "diese Woche", "wochenplan: die laufende Woche ist nicht markiert");
  const weekBlocks = folded.split('class="pweek ').slice(1);
  ok(weekBlocks.length === 4, `wochenplan: ${weekBlocks.length} Wochen statt 4`);
  ok(/class="pstage"/.test(weekBlocks[0]), "wochenplan: laufende Woche ohne Stufe");
  for (let i = 1; i < weekBlocks.length; i++) {
    ok(!/class="pstage"/.test(weekBlocks[i]),
       `wochenplan: Woche ${i + 1} trägt eine Stufe — das ist die verbotene Prognose`);
  }

  // alle drei Stufen der laufenden Woche erscheinen, jede mit Wort UND Form
  for (const key of ["stimulus", "yellow", "green"]) {
    contains(weekBlocks[0], plan.stages[key].label,
             `wochenplan: Stufe ${key} fehlt an den Chips`);
  }

  // aufgeklappt: Badge, Last, Budget, Zweck
  q._planOpen = "1";
  const open1 = q.rPlanWeeks(g);
  clean(open1, "wochenplan Woche 1");
  contains(open1, plan.stages.stimulus.word, "wochenplan: das Wort der Reiz-Stufe fehlt");
  contains(open1, "Last 159", "wochenplan: die hochgerechnete Last fehlt");
  contains(open1, "Budget 95", "wochenplan: das Budget steht nicht neben der Last");
  contains(open1, "Was das bringt", "wochenplan: die Wirkung der Einheit fehlt");

  // Die Karte ist dieselbe wie im Trainer-Reiter: Segmentbalken, Schritte in
  // Watt, Pulsfenster, Zweckzeile. Eine eigene, magerere Bauart für dieselbe
  // Sache wäre die Layout-Fassung einer zweiten Regel im Haus.
  contains(open1, 'class="wocard', "wochenplan: keine Sitzungskarte, sondern eigene Bauart");
  contains(open1, 'class="wosteps"', "wochenplan: die Schritte fehlen");
  contains(open1, "118 W", "wochenplan: die Wattzahlen der Segmente fehlen");
  contains(open1, "138–152 bpm", "wochenplan: das Pulsfenster fehlt");
  contains(open1, "Aerobe Basis", "wochenplan: die Zweckzeile fehlt");
  contains(open1, "Vorlage 95 min", "wochenplan: die Dauer der Vorlage fehlt neben der geplanten");
  contains(open1, "geplant 3,5 h", "wochenplan: die geplante Dauer fehlt");

  // Die HERLEITUNG der Last gehört in den Rechenweg, nicht in die Kopfzeile:
  // die Zahl muss nachweisbar bleiben, nicht dauerhaft sichtbar.
  const head1 = open1.slice(open1.indexOf('class="wometa"'), open1.indexOf('class="wosteps"'));
  ok(!/Katalogeinheit/.test(head1),
     "wochenplan: die Hochrechnung steht in der Kopfzeile statt im Rechenweg");
  q._psOpen = "1:Langer Tag — 3.5 h";
  const deep = q.rPlanWeeks(g);
  contains(deep, "Rechenweg der Last", "wochenplan: der Rechenweg fehlt im aufgeklappten Teil");
  contains(deep, "Last 72", "wochenplan: die Kataloglast wird im Rechenweg nicht genannt");
  contains(deep, "linear mit der Dauer", "wochenplan: die Hochrechnung wird nicht begründet");
  contains(deep, "Meeusen", "wochenplan: der Beleg der Reiz-Stufe reist nicht mit");
  contains(deep, "Verpflegung", "wochenplan: die Verpflegung fehlt im aufgeklappten Teil");
  q._psOpen = null;
  ok(!/noverdict/.test(open1.slice(open1.indexOf('class="pweek '), open1.indexOf('data-id="2"'))),
     "wochenplan: die laufende Woche trägt den Satz für spätere Wochen");

  // aufgeklappt: eine spätere Woche - Satz statt Stufe, und KEINE Lastzahl
  q._planOpen = "3";
  const open3 = q.rPlanWeeks(g);
  clean(open3, "wochenplan Woche 3");
  contains(open3, "Woche selbst", "wochenplan: der Satz für spätere Wochen fehlt");
  const body3 = open3.slice(open3.indexOf('data-id="3"'), open3.indexOf('data-id="4"'));
  ok(!/class="bdg"/.test(body3), "wochenplan: spätere Woche trägt ein Urteilsabzeichen");
  ok(!/Last \d/.test(body3), "wochenplan: spätere Woche druckt eine Last, die niemand kennt");
  contains(body3, "Langer Tag", "wochenplan: spätere Woche zeigt ihre Einheiten nicht");
  contains(body3, "aerobe", "wochenplan: spätere Woche ohne Begründung der Einheit");

  // gefahren gegen vorgesehen - und NICHTS gepaart
  contains(folded, "gefahren", "wochenplan: der Ist-Stand fehlt");
  contains(folded, "vorgesehen", "wochenplan: der Soll-Stand fehlt");
  contains(folded, "2 Einheiten", "wochenplan: die gefahrenen Einheiten fehlen");
  contains(folded, "Last 142", "wochenplan: die gefahrene Last fehlt");
  contains(folded, "3 Einheiten", "wochenplan: die vorgesehenen Einheiten fehlen");
  contains(folded, "noch 2 Tage", "wochenplan: die Resttage fehlen");
  contains(folded, "entscheidest du", "wochenplan: die Grenze der Zuordnung fehlt");
  // eine Paarung wäre eine Behauptung: keine gefahrene Einheit darf neben
  // einem Plantitel stehen
  const doneBlock = folded.slice(folded.indexOf('class="pwdone"'),
                                 folded.indexOf('class="pwsess"'));
  ok(!doneBlock.includes("SweetSpot"), "wochenplan: eine Fahrt wird einer Plan-Einheit zugeordnet");

  // die Legende: vier Stufen, aus der Payload, plus die Setzung dahinter
  contains(folded, "Die vier Stufen", "wochenplan: die Legende fehlt");
  for (const key of ["green", "yellow", "stimulus", "red"]) {
    contains(folded, plan.stages[key].detail, `wochenplan: Legende ohne Stufe ${key}`);
  }
  contains(folded, "Setzung", "wochenplan: die Erholungsregel wird nicht als Setzung beschriftet");

  // der Quellenblock: BEIDE Hälften des Javaloyes-Befunds
  contains(folded, "1 von 7", "wochenplan: die Nicht-Responder-Zahlen fehlen");
  contains(folded, "3 von 8", "wochenplan: die Vergleichszahl fehlt");
  contains(folded, "klein und unsicher", "wochenplan: die Grenze des Befunds fehlt");
  contains(folded, "fragt nicht nach kommenden Tagen",
           "wochenplan: die Regel, dass nicht vorab gefragt wird, fehlt");

  // eine Legende ohne Stufen in der Payload erfindet keine
  const bare = F.goal();
  delete bare.plan.stages;
  const noLegend = q.rPlanWeeks(bare);
  ok(!/Die vier Stufen/.test(noLegend),
     "wochenplan: die Legende wird ohne Payload erfunden");
  // und eine Woche ohne Bewertung zeigt keine Stufe, auch wenn die Sitzungen
  // noch eine tragen
  const unrated = F.goal();
  unrated.plan.weeks[0].rated = false;
  ok(!/class="pstage"/.test(q.rPlanWeeks(unrated)),
     "wochenplan: Stufen erscheinen ohne rated-Marke");
}

/* ── kein Block verschwindet still (0.42.1) ───────────────────────────────
   Der Fehler, den diese Prüfungen gefunden hätten: `goal` wurde beim ERSTEN
   Aufbau nie geholt, weil _boot direkt rendert und nur _setTab die Payload
   anfordert. rPlanWeeks stieg mit "" aus, rGoal blieb in einem Ladehinweis,
   der nie auflöst - beides ohne Fehlermeldung, von 0.20.0 bis 0.42.0. Die
   alten Tests riefen die Renderer IMMER mit vorhandener Fixture auf, "" war
   damit ein gültiges Ergebnis, und der Fall kam nie vor. */
{
  const q = new M.Panel();
  q._nowIso = F.TODAY;

  // 1 - nie angefordert: das ist ein Defekt und muss als solcher dastehen
  for (const [fn, arg] of [["rGoal", null], ["rPlanWeeks", null], ["rWorkouts", null]]) {
    const out = q[fn](arg);
    ok(out && out.trim().length > 0, `leerfall: ${fn} liefert einen Leerstring`);
    contains(out, "Nie angefordert", `leerfall: ${fn} sagt nicht, dass nichts geholt wurde`);
    contains(out, "Fehler im Panel", `leerfall: ${fn} gibt den Defekt als leeren Bestand aus`);
  }

  // 2 - unterwegs: ein Ladehinweis, aber nur wenn wirklich geladen wird
  q._asked.goal = true;
  contains(q.rGoal(null), "Wird noch geladen", "leerfall: kein Ladehinweis trotz laufendem Abruf");
  ok(!/Nie angefordert/.test(q.rGoal(null)),
     "leerfall: laufender Abruf wird als Defekt gemeldet");

  // 3 - fehlgeschlagen: der Grund steht dran, nicht nur "geht nicht"
  q._failed.goal = "WebSocket timeout";
  const failed = q.rPlanWeeks(null);
  contains(failed, "Nicht geladen", "leerfall: gescheiterter Abruf sieht aus wie ein laufender");
  contains(failed, "WebSocket timeout", "leerfall: der Grund des Fehlschlags fehlt");

  // 4 - ein Ziel, das schlicht noch nicht gesetzt ist, ist KEIN Defekt:
  //     rGoal zeigt dafür das Formular, ein zweiter Hinweis wäre Lärm
  const unset = F.goal("neu");
  ok(q.rPlanWeeks(unset) === "", "leerfall: ungesetztes Ziel wird als Defekt gemeldet");
  contains(q.rGoal(unset), "Worauf trainierst du", "leerfall: ungesetztes Ziel zeigt kein Formular");

  // 5 - und die Boot-Ansichten, die dieselbe Klasse tragen
  for (const [fn, label] of [["rKalender", "Der Kalender"], ["rBelastung", "Die Belastungsdaten"],
                             ["rHeute", "Der Tag"], ["rSignale", "Die Signale"],
                             ["rFitness", "Die Fitness-Kurve"], ["rDfa", "Die DFA-Daten"]]) {
    const out = q[fn](null);
    ok(out && out.includes(label), `leerfall: ${fn} benennt nicht, was fehlt`);
    contains(out, "Nie angefordert", `leerfall: ${fn} verschweigt den nie erfolgten Abruf`);
  }
  // rTrainer trägt denselben Hinweis, nur mit zwei Argumenten
  contains(q.rTrainer(null, null), "Nie angefordert", "leerfall: rTrainer verschweigt den Ausfall");
}

/* ── eine Zustandswarnung, einmal — nicht je Einheit (docs/ausbau.md I10) ──
   Sie gilt dem ZUSTAND, nicht der Einheit. Dreimal untereinander liest sie
   beim dritten Mal niemand. Das galt in BEIDEN Ansichten, also wird es in
   beiden geprüft - der Fehler war eine Klasse, kein Ort. */
{
  const q = new M.Panel();
  q._nowIso = F.TODAY;
  const count = (html, needle) => html.split(needle).length - 1;

  // 1 - Wochenansicht: dieselbe Begründung an allen drei Einheiten
  const g = F.goal();
  const shared = "Infektmuster in den Signalen: erst mehrere lockere Einheiten.";
  for (const s of g.plan.weeks[0].sessions) s.fit_reason = shared;
  q._planOpen = "1";
  const week = q.rPlanWeeks(g);
  ok(count(week, shared) === 1,
     `warnung: die Zustandswarnung steht ${count(week, shared)}× in der Woche statt einmal`);
  // und sie steht ÜBER den Karten, nicht in der ersten
  ok(week.indexOf(shared) < week.indexOf('class="wocard'),
     "warnung: die gemeinsame Warnung steht in einer Karte statt über ihnen");

  // 2 - eine Begründung, die nur EINE Einheit betrifft, bleibt an ihr
  const g2 = F.goal();
  g2.plan.weeks[0].sessions[1].fit_reason = "Zwei harte Tage liegen schon in dieser Woche.";
  const week2 = q.rPlanWeeks(g2);
  contains(week2, "Zwei harte Tage", "warnung: die einzelne Begründung verschwindet");
  ok(week2.indexOf("Zwei harte Tage") > week2.indexOf('class="wocard'),
     "warnung: eine einzelne Begründung wird nach oben gezogen");

  // 3 - Trainer-Reiter: dieselbe Klasse, derselbe Test
  const w = F.workouts("einbruch");
  const many = "Die Erholung läuft, aber die letzten Tage tragen noch keinen harten Reiz.";
  ok((w.workouts.filter((e) => e.fit_reason === many) || []).length >= 2,
     "warnung: die Fixture trägt die Begründung nicht mehrfach — Fall untauglich");
  const trainer = q.rWorkouts(w);
  ok(count(trainer, many) === 1,
     `warnung: die Zustandswarnung steht ${count(trainer, many)}× im Trainer-Reiter statt einmal`);
  ok(trainer.indexOf(many) < trainer.indexOf('class="wocard'),
     "warnung: im Trainer-Reiter steht die gemeinsame Warnung in einer Karte");

  // 4 - Gegenprobe für den Sammler selbst: zwei gleiche Gründe gelten als
  //     gemeinsam, ein einzelner nicht
  ok(q._sharedReasons([{ fit_reason: "a" }, { fit_reason: "a" }]).has("a"),
     "warnung: zwei gleiche Gründe werden nicht als gemeinsam erkannt");
  ok(!q._sharedReasons([{ fit_reason: "a" }, { fit_reason: "b" }]).has("a"),
     "warnung: ein einzelner Grund wird nach oben gezogen");
  ok(q._sharedReasons([]).size === 0, "warnung: leere Liste erfindet einen Grund");
  ok(q._sharedReasons([{}, {}]).size === 0, "warnung: Einheiten ohne Grund erzeugen einen");
}

report("test_panel_views");
})();
