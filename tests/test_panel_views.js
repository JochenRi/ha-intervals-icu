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
  // 0.73.0 umgestellt: "HEUTE MÖGLICH" -> "Was dein Körper heute kann"; die Zeile
  // "Obergrenze 95" ist dem Wochenkasten gewichen (Skizze 0.73.0 §6).
  contains(html, "Was dein Körper heute kann", "heute: keine Leitaussage");
  contains(html, "Alles möglich", "heute: Kapazität fehlt");
  contains(html, "Wie viel die Woche noch trägt", "heute: keine Wochenlast");
  contains(html, "Noch 209 Last frei", "heute: das Wochenurteil fehlt");
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
  // The head is ONE line (0.70.0, A1: vorher zwei Kaesten) - no plan, no weeks, no warning.
  // The question of the day is which session to ride, not what week 7 looks like.
  contains(html, "Lange Fahrten durchstehen", "plan: Ziel nicht genannt");
  contains(html, "Durability", "plan: Zielgröße nicht genannt");
  contains(html, "4 Tage pro Woche", "plan: Zeitangabe fehlt");
  contains(html, "1 harte Einheit", "plan: Folge der Tageszahl fehlt");
  // 0.70.0 UMGESTELLT (A1): statt zweier Kaesten EINE Zeile mit zwei Knoepfen
  ok((html.match(/class="goalline"/g) || []).length === 1 && (html.match(/class="gline"/g) || []).length === 2,
     "plan: Kopf ist nicht EINE Zeile mit Ziel und Zeit");
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
  // 0.70.0 UMGESTELLT (B): die Herleitung ist in den Reiter Quellen umgezogen
  const herl = p._trainerSources();
  contains(herl, "Worauf diese Empfehlung beruht", "trainer: Herleitung fehlt (Quellen)");
  contains(herl, "alles außerhalb des Trainings", "trainer: Grenze der Empfehlung fehlt (Quellen)");
  ok(!/Worauf diese Empfehlung beruht/.test(html), "trainer: die Herleitung steht noch im Trainer");

  // the three separate bars became one axis with three dots: position on a
  // COMMON scale rather than three tracks that cannot be compared
  ok(!/class="zbar/.test(html), "trainer: getrennte Balken wieder da");
  // 0.71.0 UMGESTELLT: die drei Punkte stehen jetzt ZWEIMAL da - klein offen
  // (Mini-Streifen) und gross im Aufklapper; gezaehlt wird je Ort.
  const zgross = html.slice(html.indexOf('class="zplot"'));
  const zklein = html.slice(html.indexOf('class="zmini"'), html.indexOf('data-keep="trainer:zustand"'));
  ok((zgross.match(/class="zdot"/g) || []).length === 3 && (zklein.match(/class="zdot"/g) || []).length === 3,
     "trainer: nicht drei Punkte auf einer Achse (gross und klein)");
  ok(/class="zband"/.test(html), "trainer: Normalband fehlt");
  ok(/class="zzero"/.test(html), "trainer: Basislinie nicht markiert");
  // labels sit ON the rows now, not in a legend below - a legend forces the
  // eye between two places and the mapping into working memory
  ok((html.match(/class="zrow"/g) || []).length === 3, "trainer: nicht drei beschriftete Zeilen");
  ok((zgross.match(/class="zname"/g) || []).length === 3 && (zklein.match(/class="zname"/g) || []).length === 3,
     "trainer: Zeilen ohne Namen");
  ok((zgross.match(/class="zval/g) || []).length === 3 && (zklein.match(/class="zval/g) || []).length === 3,
     "trainer: Werte nicht beziffert");
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
  contains(html, "für heute bewertet", "einheiten");   // 0.70.0: Familien statt Liste
  // ONE per kind - not three base rides. The choice must be between different
  // KINDS of training, which is what makes it a choice at all.
  const families = ["Grundlage", "SweetSpot", "Tempo", "Schwelle", "VO2max", "Regeneration"];
  for (const family of families) contains(html, family, `einheiten: ${family} fehlt`);
  // 0.70.0 UMGESTELLT (A4): die Art steht in der Familienzeile, nicht mehr auf
  // der Karte - sechs Karten in drei Familien
  ok((html.match(/class="fgname"/g) || []).length === 3, "einheiten: nicht drei Familien");
  ok((html.match(/class="wocard/g) || []).length === 6, "einheiten: nicht sechs Karten");
  contains(html, "passt heute", "einheiten: kein Tagesurteil");
  // 0.69.1 (KARTE_4a W4a.1): der Listenkopf sagt, woher die Watt JE ART kommen -
  // Grundlage aus der Umkehrung, Bloecke aus dem Steuerwert, sonst FTP. "Watt aus
  // deiner FTP" pauschal war seit 0.68.0 falsch.
  // 0.70.0 UMGESTELLT (A4): der Listenkopf ist weg ("samt Kopftext"); die
  // Wattquelle steht jetzt JE FAMILIE in ihrer Zeile, die Pulsquelle im Hintergrund.
  {
    const qw = F.workouts();
    qw.workouts[0] = { ...qw.workouts[0], watt_source: "ga" };
    qw.workouts[4] = { ...qw.workouts[4], watt_source: "steering" };
    const keep = p._workouts; p._workouts = qw;
    const hq = String(p.rTrainer(F.coach("ready"), rdFix));
    p._workouts = keep;
    const zeilen = (hq.match(/<summary>[\s\S]*?<\/summary>/g) || []).filter((x) => /fgname/.test(x)).join(" ");
    ok(!/Watt aus deiner\s+FTP/.test(hq), "einheiten-kopf: sagt noch pauschal 'Watt aus deiner FTP'");
    ok(/Umkehrung/.test(zeilen) && /deine Vorgabe/.test(zeilen) && /FTP/.test(zeilen),
       "einheiten-kopf: die Familienzeilen nennen nicht alle drei Wattquellen (Umkehrung, Vorgabe, FTP)");
    contains(p.rHintergrund(F.coach("ready")), "Aerobe Schwelle", "einheiten-kopf: die Pulsquelle ist weg");
  }
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

  // L1 (0.69.0): DAS GELAENDER. Eine gruene Karte ueber der Obergrenze bleibt
  // die Empfehlung (die Art), traegt aber den Gelaender-Text aus der Payload -
  // auf der Karte UND in der Leitempfehlung, damit "Menge kuerzen" nicht erst
  // beim Aufklappen erscheint.
  const geländer = F.workouts();
  geländer.workouts[0] = { ...geländer.workouts[0], fits_budget: false,
                           stage: F.stageOf("ok", false, false),
                           guard: { over: true, load: 250, ceiling: 68, hours_fit: 1.5,
                                    text: "Geländer: Last 250 über der Obergrenze 68 — die Art bleibt, die Menge nicht. Bis ~1,5 h passt sie unter die Obergrenze." } };
  p._workouts = geländer;
  const gl = p.rTrainer(F.coach("ready"), F.readiness()).replace(/\s+/g, " ");
  ok((gl.match(/class="recflag"/g) || []).length === 1 && /recflag[\s\S]{0,1500}Geländer: Last 250/.test(gl),
     "L1: die gruene Karte ueber der Obergrenze ist nicht mehr die Empfehlung, oder traegt das Gelaender nicht");
  const glLead = gl.slice(gl.indexOf('class="leadrec"'), gl.indexOf('class="secname"'));
  contains(glLead, "Bis ~1,5 h passt sie", "L1: die Leitempfehlung verschweigt das Gelaender");
  ok(!/heute nicht/.test(glLead), "L1: die Leitempfehlung raet ab, obwohl der Zustand traegt");
  // 0.69.1 -> 0.72.2 umgestellt (Entscheidung Johannes 26.09.): das Etikett traegt
  // IMMER das Stufenwort ("passt heute"), die Menge steht als eigenes Zeichen
  // "Menge über Wochenlast" daneben; die Leitempfehlung nennt die passende Dauer aus guard().
  const glCard = gl.slice(gl.indexOf('class="wocard first"'), gl.indexOf('class="wocard', gl.indexOf('class="wocard first"') + 10));
  ok(/passt heute/.test(glCard), "L1 0.72.2: die Karte ueber der Obergrenze verliert das Stufenwort");
  contains(glCard, "Menge über Wochenlast", "L1 0.72.2: die Karte ueber der Obergrenze traegt das Mengen-Zeichen nicht");
  ok(!/Art bleibt, Menge kürzen</.test(glCard), "L1 0.72.2: das alte Ersatz-Etikett steht noch");
  contains(glLead, "heute ~1,5 h", "L1 0.69.1: die Leitempfehlung nennt die passende Dauer nicht");
  // Gegenprobe: gelb ueber der Obergrenze ebenso, und unter der Obergrenze bleibt "passt heute"
  const gelb = F.workouts();
  gelb.workouts[0] = { ...gelb.workouts[0], fits_budget: false, stage: F.stageOf("maybe", false, false),
                       guard: { over: true, load: 250, ceiling: 68, hours_fit: 1.5, text: "Geländer: Last 250 über der Obergrenze 68 — die Art bleibt, die Menge nicht. Bis ~1,5 h passt sie unter die Obergrenze." } };
  p._workouts = gelb;
  const gy = p.rTrainer(F.coach("ready"), F.readiness()).replace(/\s+/g, " ");
  const gyCard = gy.slice(gy.indexOf(gelb.workouts[0].title), gy.indexOf('class="wocard', gy.indexOf(gelb.workouts[0].title)));
  contains(gyCard, "Menge über Wochenlast", "L1 0.72.2 gelb: die Karte ueber der Obergrenze traegt das Mengen-Zeichen nicht");
  ok(/geht, kostet mehr</.test(gyCard), "L1 0.72.2 gelb: das Stufenwort fehlt ueber der Obergrenze");
  p._workouts = F.workouts();
  const under = p.rTrainer(F.coach("ready"), F.readiness()).replace(/\s+/g, " ");
  const underLead = under.slice(under.indexOf('class="leadrec"'), under.indexOf('class="secname"'));
  ok(/passt heute/.test(under.slice(0, under.indexOf("recflag") + 1800)), "L1 0.69.1 Gegenprobe: unter der Obergrenze fehlt 'passt heute'");
  ok(!/Menge über Wochenlast/.test(under) && !/heute ~/.test(underLead), "L1 0.72.2 Gegenprobe: Mengen-Zeichen oder Dauer ohne Ueberschreitung");
  // Gegenprobe: im Budget kein Gelaender-Text
  p._workouts = F.workouts();
  ok(!/Geländer:/.test(String(p.rTrainer(F.coach("ready"), F.readiness()))), "L1 Gegenprobe: Gelaender ohne Ueberschreitung");
  // Athlet B ohne Zustand: rot am Budget, und die Karte sagt, dass die Last entscheidet
  const ohneZustand = F.workouts();
  ohneZustand.workouts[0] = { ...ohneZustand.workouts[0], fits_budget: false,
                              stage: { ...F.stageOf("ok", false, false, true),
                                       detail: "Ohne Zustand (keine HRV-Basislinie) entscheidet die Last: über der Obergrenze — heute nicht." } };
  p._workouts = ohneZustand;
  const oz = p.rTrainer(F.coach("unknown"), F.readiness()).replace(/\s+/g, " ");
  // 0.72.0 UMGESTELLT: die empfohlene Karte einer Familie steht jetzt OBEN (Skizze
  // 0.72.0, 1) - die rote Karte ist nicht mehr die erste der Seite; gesucht wird sie
  // an ihrem Schluessel.
  const ozFirst = oz.split('class="wocard').find((k) => k.includes(`data-id="${ohneZustand.workouts[0].key}"`)) || "";
  ok(/heute nicht/.test(ozFirst) && !/recflag/.test(ozFirst), "L1 ohne Zustand: die rote Karte traegt die Empfehlung");
  contains(oz, "entscheidet die Last", "L1 ohne Zustand: die Beschriftung aus der Payload fehlt");
  p._workouts = F.workouts();

  // in a rebound the recommendation must move to a session that fits
  const rb = p.rTrainer(F.coach("rebound"), F.readiness());
  ok((rb.match(/class="recflag"/g) || []).length === 1,
     "einheiten rebound: Empfehlung fehlt oder mehrfach");
  ok(!/class="recflag"[\s\S]{0,400}heute nicht/.test(rb),
     "einheiten rebound: abgeratene Einheit als Empfehlung markiert");
  // 0.70.0 UMGESTELLT: der Kopftext ist weg - wer entscheidet, steht in Quellen
  // ("entschieden von dir"), die FTP als Herkunft in der Familienzeile.
  { const kg = p._goal; p._goal = F.goal();
    contains(p._trainerSources(), "entschieden von dir", "einheiten: Entscheidung nicht beim Athleten (Quellen)");
    p._goal = kg; }
  ok(/class="fgw tn">\d+ W · FTP/.test(html), "einheiten: FTP als Herkunft nicht genannt");
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

    // L2 (0.69.0): die Bewertung der Nacht steht im Block - Wort, beide
    // z-Werte, die Setzung und "nur Anzeige"; alles aus der Payload.
    p._night[acts[0].id] = F.night();
    const bew = nightPart(String(p.rAkt(acts, acts[0]))).replace(/\s+/g, " ");
    contains(bew, "zu viel — deutlich unter dem Band", "L2: die Bewertung fehlt im Nacht-Block");
    ok(/-1,5 SD/.test(bew) && /-0,2 SD/.test(bew), "L2: die z-Werte beider Nächte fehlen an der Bewertung");
    contains(bew, "Setzung: verdaut ab −0,5 SD", "L2: die Setzung steht nicht dabei");
    contains(bew, "der Trainer liest diese Bewertung nicht", "L2: 'nur Anzeige' fehlt");
    p._night[acts[0].id] = F.night("verdaut");
    const vd = nightPart(String(p.rAkt(acts, acts[0]))).replace(/\s+/g, " ");
    contains(vd, "verdaut — die Nacht danach lag in deinem Band", "L2: 'verdaut' fehlt");
    contains(vd, "zweite Nacht liegt noch nicht vor", "L2: die fehlende zweite Nacht wird nicht benannt");
    ok(!/undefined|null SD/.test(vd), "L2: ohne zweite Nacht steht undefined/null im Block");

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
  const thin = thr.map((x) => ({ ...x, hr_windows: 2, hr_usable: false, usable: false }));
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
  const solid = thr.slice(-10).find((x) => x.hr_usable);
  const weak = thr.slice(-10).find((x) => !x.hr_usable) || thr.find((x) => !x.hr_usable);
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
                                 hr: x.hr, power: x.power }));
  clean(q.rDfa(bare, "all"), "dfa ohne die neuen Felder");
}

/* ── Paket M: ein Wert je Block, ueber die Zeit ──────────────────────────── */
{
  const q = new M.Panel();
  q._nowIso = F.TODAY;
  const b = F.blocks();
  const html = String(q.rBlocks(b));
  clean(html, "blockmessung");
  // Zeilenumbrueche im Template sind Formatierung, kein Inhalt.
  const flat = html.replace(/\s+/g, " ");

  // DIE GROSSE ZAHL IST DIE, DIE GILT. Bis 0.61.1 stand hier die
  // Verlaufsgroesse (erster Block, 262 W) - eine Zahl, nach der niemand faehrt.
  // Schalter AUS: die alte Rechnung, also der Median der letzten Einheit.
  ok(/252<\/b>\s*<span class="unit">W<\/span>/.test(html),
     "M: die grosse Zahl ist nicht die geltende (Median der letzten Einheit)");
  ok(!/262<\/b>\s*<span class="unit">W<\/span>/.test(html),
     "M: die Verlaufsgroesse steht wieder als Leitzahl da");
  // GEGENPROBE: mit Schalter zeigt dieselbe Kachel die VORGABE.
  const mitStg = String(q.rBlocks(F.blocks({ steering_on: true })));
  ok(/250<\/b>\s*<span class="unit">W<\/span>/.test(mitStg),
     "M: mit Schalter steht nicht die Vorgabe oben");
  ok(!/252<\/b>\s*<span class="unit">W<\/span>/.test(mitStg),
     "M: mit Schalter steht weiter die alte Zahl oben");
  // Die Steuerung ruht sichtbar auf ihren Einzelwerten - nicht geglaettet
  contains(html, "Die Steuerung ruht auf", "M: es steht nicht da, worauf die Steuerung ruht");
  ok(/0,45 und 0,41 und 0,38 und 0,40/.test(html) || /0,45 und 0,41/.test(html),
     "M: die Einzelblöcke fehlen");
  ok(/Median 0,410/.test(html), "M: der Median der Steuergröße fehlt");
  // Der Vorschlag, und dass er einer ist
  contains(html, "Das System schlägt vor, du entscheidest", "M: der Vorschlag wirkt wie eine Anweisung");
  ok(/im Korridor 0,20–0,50/.test(flat), "M: der Korridor wird nicht genannt");
  // Die Grenze: Rolle, nicht draußen
  contains(html, "nicht für dieselbe Familie draußen", "M: die Rolle-Grenze fehlt");
  ok(/40 W/.test(html), "M: der 40-Watt-Befund als Begründung fehlt");
  // Die verworfenen zwei Minuten stehen dabei
  ok(/ersten 2 Minuten verworfen/.test(flat), "M: das Verwerfen wird nicht benannt");

  // BELEGUNG: SweetSpot hat vier Einheiten -> keine Linie, aber der Satz.
  const ssTeil = flat.slice(flat.indexOf("SweetSpot"));
  // SATZ UND BILD GEHEN ZUSAMMEN (seit 0.62.2). Die Linie wird ab zwei
  // Punkten gezeichnet; die Schwelle 6 gilt fuer die AUSSAGEKRAFT.
  ok(/4 Einheiten<\/b> — die Richtung ist noch nicht gesichert/.test(ssTeil),
     "M: die dünne Belegung wird nicht benannt");
  ok(!/keine Verlaufslinie/.test(ssTeil),
     "M: der Satz behauptet, es werde keine Linie gezeichnet — sie steht aber da");
  ok(/Ab 6 Einheiten trägt sie/.test(ssTeil),
     "M: die Schwelle wird nicht mehr genannt");
  // KEIN SATZ OHNE BILD und kein Bild ohne Satz, solange die Belegung duenn
  // ist: der SweetSpot (4 Einheiten) traegt beides, VO2max (6) keines von
  // beiden Zeichen des Mangels.
  ok(/stroke-width="2.4"/.test(ssTeil),
     "M: die dünn belegte Familie bekommt gar keine Linie mehr");
  const ohneLinie = String(q.rBlocks(F.blocks({ steering: { ...b.steering,
    sweetspot: { ...b.steering.sweetspot, rows: b.steering.sweetspot.rows.slice(0, 1) } } })));
  const ssOhne = ohneLinie.replace(/\s+/g, " ");
  const teilOhne = ssOhne.slice(ssOhne.indexOf('data-grp="blk_sweetspot"'));
  ok(!/Verlauf — Watt ab Block 2/.test(teilOhne),
     "M: ein einzelner Punkt bekommt trotzdem einen Verlauf");
  ok(!/die Richtung ist noch nicht gesichert/.test(teilOhne),
     "M: der Satz zur Richtung steht da, obwohl gar kein Bild gezeichnet wurde");
  // GEGENFALL, gezaehlt und benannt: VO2max hat sechs -> Linie, kein Satz.
  const voTeil = flat.slice(flat.indexOf("VO2max"), flat.indexOf("SweetSpot"));
  ok(!/keine Verlaufslinie/.test(voTeil),
     "M: auch die getragene Familie bekommt den Dünn-Satz");
  ok(/stroke-width="2.4"/.test(voTeil), "M: die getragene Familie bekommt keine Linie");
  // Und die grosse Spanne wird benannt, statt geglättet zu werden
  const zwei = String(q.rBlocks(F.blocks({ families: { sweetspot: {
    ...b.families.sweetspot, latest: b.families.sweetspot.points[2] } } })));
  ok(/Spanne von 0,21 ist groß/.test(zwei.replace(/\s+/g, " ")),
     "M: eine große Spanne wird verschwiegen");

  // ── DER NEUE KACHELWERT (0.62.0): AUFBAU UND REIHENFOLGE ───────────────
  {
    const an = String(q.rBlocks(F.blocks({ steering_on: true }))).replace(/\s+/g, " ");
    const aus = String(q.rBlocks(F.blocks({ steering_on: false }))).replace(/\s+/g, " ");
    // Reihenfolge von oben: Schildchen, Familie, grosse Zahl, Toleranzzeile,
    // Streifen, Saetze, Verlauf, Rechenweg.
    const folge = ["class=\"state\"", "class=\"fam\"", "class=\"bigval\"", "class=\"tol\"",
                   "class=\"bstrip\"", "class=\"info\"", "Verlauf — Watt ab Block 2",
                   "mehr anzeigen"];
    // NUR INNERHALB EINER KARTE. Ueber beide Familien hinweg gesucht, faende
    // die Reihenfolge ihre Stuecke auch dann noch, wenn sie in der ersten
    // Karte vertauscht waeren - der Streifen der ZWEITEN Karte stuende ja
    // hinter der Toleranzzeile der ersten. Die Luecke ist beim Mutieren
    // aufgefallen, nicht beim Schreiben.
    const eineKarte = an.slice(an.indexOf('data-grp="blk_vo2max"'),
                               an.indexOf('data-grp="blk_sweetspot"'));
    ok(eineKarte.length > 200, "kachel: die erste Familienkarte ist nicht auffindbar");
    let pos = -1, heil = true;
    for (const stueck of folge) {
      const p2 = eineKarte.indexOf(stueck, pos + 1);
      if (p2 <= pos) heil = false;
      pos = p2;
    }
    ok(heil, "kachel: die Reihenfolge von oben nach unten stimmt nicht");
    // Die Toleranzzeile: Spanne, von-bis - und DANACH nicht mehr die Quote.
    // Bis 0.65.2 stand dort "8 von 10 Einheiten", ab drei Einheiten und ohne
    // Deckung. Jetzt sagt die Zeile, WIE das Band gebaut ist (0.66.0, C).
    ok(/± 4,1 W · <b class="tn">186 – 194 W<\/b> · t-Band über 4 Einheiten/.test(an),
       "kachel: die Toleranzzeile steht nicht in der verlangten Form");
    ok(!/8 von 10 Einheiten/.test(an),
       "kachel: die Quote '8 von 10' steht wieder da, obwohl sie an 4 Einheiten nicht pruefbar ist");
    // Der Bullet-Streifen: Balken, Marker, VIER Zahlen an der Achse
    const strip = an.slice(an.indexOf("bstrip"), an.indexOf("bleg"));
    ok(/class="brange"/.test(strip) && /class="bmark"/.test(strip),
       "kachel: Spanne oder Vorgabestrich fehlen im Streifen");
    ok((strip.match(/<i[^>]*>\d/g) || []).length === 4,
       "kachel: an der Achse stehen nicht genau vier Zahlen");
    ok(!/#fbbf24|#f87171|#34d399/.test(strip), "kachel: der Streifen benutzt Ampelfarben");
    // Die zwei Saetze - aus dem Modul, mit eingesetzten Zahlen
    ok(/Fahr die 190 W\./.test(an), "kachel: der Fahr-Satz fehlt oder rechnet falsch");
    ok(/zwischen 186 und 194 W/.test(an) && /2 von 3 Einheiten/.test(an) && /um 5 W/.test(an),
       "kachel: der Satz, wann sich die Vorgabe bewegt, fehlt");
    // ── DER AUFKLAPPTEIL (0.62.1): drei Teile statt Tabelle ──────────────
    ok(/<details class="more"> <summary>mehr anzeigen|<details class="more"><summary>mehr anzeigen/.test(an),
       "kachel: der Rechenweg ist nicht zugeklappt");
    // KEINE TABELLE mehr: sie brach im schmalen Container in Wortfetzen.
    const aufklapp = an.slice(an.indexOf("mehr anzeigen"), an.indexOf("</details>"));
    ok(!/<table/.test(aufklapp), "aufklapp: die Tabelle steht wieder da");
    ok(!/Einheiten seither<\/td>|Messfenster<\/td>|Streuung s<\/td>/.test(an),
       "aufklapp: Reste der alten Tabellenzeilen");
    // TEIL 1: EIN Satz, Zahlen fett im Fliesstext
    ok(/class="rsatz">Die Vorgabe ist der Startwert <b class="tn">190<\/b> W vom/.test(an),
       "aufklapp: der Herkunftssatz fehlt oder trägt die Zahl nicht fett");
    ok(/Seither sind <b class="tn">0<\/b> Einheiten dazugekommen/.test(an),
       "aufklapp: Zahl und Wortform der Einheiten stimmen nicht");
    ok(/daraus wurden <b class="tn">0<\/b> Bewegungen à 5 W/.test(an),
       "aufklapp: die Bewegungen fehlen im Satz");
    ok(/steht heute auf <b class="tn">190<\/b> W/.test(an),
       "aufklapp: der Satz endet nicht auf der geltenden Vorgabe");
    // SINGULAR und PLURAL - beide Formen, an derselben Kachel geprüft
    const eins = F.blocks({ steering_on: true });
    eins.steering.sweetspot = { ...eins.steering.sweetspot, n_since: 1, moves: 1 };
    const eHtml2 = String(q.rBlocks(eins)).replace(/\s+/g, " ");
    ok(/Seither ist <b class="tn">1<\/b> Einheit dazugekommen/.test(eHtml2),
       "aufklapp: bei einer Einheit steht der Plural");
    ok(/daraus wurde <b class="tn">1<\/b> Bewegung à/.test(eHtml2),
       "aufklapp: bei einer Bewegung steht der Plural");
    ok(!/1 Einheiten|1 Bewegungen/.test(eHtml2), "aufklapp: „1 Einheiten“ im Text");
    // TEIL 2: die Formelzeile - eine Kette, abgesetzt, nicht umbrechend
    ok(/class="formel">Spanne = 190 W ± <b>1,83<\/b> · <b>2,22 W<\/b> = <b>± 4,1 W<\/b>/.test(an),
       "aufklapp: die Formelzeile steht nicht als durchgehende Kette da");
    ok(/class="fcap">1,83 = t\(0,90; n−1\) · √\(1\+1\/n\) · Streuung 2,22 W aus den letzten 4 Einheiten/.test(an),
       "aufklapp: die Erklärzeile unter der Formel fehlt");
    // Die CSS-Regeln enthalten Platzhalter mit geschweiften Klammern
    // (${C.card2}), eine Zeichenklasse [^}] bricht daran ab - deshalb wird
    // der Regelblock ueber seine Grenzen ausgeschnitten.
    const cssQ = H.source();
    const regel = (name) => {
      const i = cssQ.indexOf("\n" + name + "{");
      return i < 0 ? "" : cssQ.slice(i, cssQ.indexOf("}\n", i) + 1);
    };
    const rFormel = regel(".formel");
    ok(rFormel.includes("white-space:nowrap") && rFormel.includes("overflow-x:auto"),
       "aufklapp: die Formelzeile darf umbrechen statt zu scrollen (schmaler Schirm)");
    ok(regel(".rchip").includes("white-space:nowrap"), "aufklapp: die Chips brechen mitten im Wort");
    ok(regel(".rchips").includes("flex-wrap:wrap"), "aufklapp: die Chips laufen aus dem Container");
    // TEIL 3: drei Chips
    const chipTeil = an.slice(an.indexOf('class="rchips"'), an.indexOf("</div>", an.indexOf('class="rchips"')));
    ok((chipTeil.match(/class="rchip"/g) || []).length === 3,
       "aufklapp: es sind nicht genau drei Chips");
    // Die erste Karte ist VO2max - dort stehen ihre Zahlen, nicht die des
    // SweetSpots.
    contains(chipTeil, "alpha 0,360 – 0,580 · Korridor 0,20 – 0,50", "aufklapp: der alpha-Chip stimmt nicht");
    contains(chipTeil, "Puls 178 – 189 bpm", "aufklapp: der Puls-Chip fehlt");
    contains(chipTeil, "Block 1 zählt nicht mit", "aufklapp: der Block-1-Chip fehlt");
    ok(!/Messrauschen/.test(an),
       "kachel: der Quotensatz ('Messrauschen ... 8 von 10') steht unterhalb der Schranke wieder da");
    ok(/t-Band über 4 Einheiten/.test(an),
       "kachel: unterhalb der Schranke fehlt der Satz, WIE das Band gebaut ist");
    // REIHENFOLGE im Aufklappteil: Satz, dann Formel, dann Chips.
    const rf = ["class=\"rsatz\"", "class=\"formel\"", "class=\"fcap\"", "class=\"rchips\""];
    let rp = -1, rheil = true;
    for (const t of rf) { const i2 = aufklapp.indexOf(t, rp + 1); if (i2 <= rp) rheil = false; rp = i2; }
    ok(rheil, "aufklapp: Satz, Formel und Chips stehen nicht in dieser Reihenfolge");
    // DIE ZAHLEN FOLGEN DER PAYLOAD - reaktiv geprüft statt nur im Quelltext
    // gesucht: eine andere Spanne muss in Zeile UND Formel durchschlagen.
    // Ein fester Wert im Template faellt hier auf, auch wenn er im
    // Zahlen-Waechter oben nicht gelistet ist (beim Mutieren aufgefallen).
    const anders = F.blocks({ steering_on: true });
    anders.compare.sweetspot = { ...anders.compare.sweetspot,
      new_band: { ...anders.compare.sweetspot.new_band, low: 180, high: 200, half: 9.9, sd: 5.4 } };
    const aHtml = String(q.rBlocks(anders)).replace(/\s+/g, " ");
    const ssAuf = aHtml.slice(aHtml.indexOf('data-grp="blk_sweetspot"'));
    ok(/± <b>1,83<\/b> · <b>5,40 W<\/b> = <b>± 9,9 W<\/b>/.test(ssAuf),
       "aufklapp: die Formelzeile folgt der Payload nicht");
    ok(/180 – 200 W/.test(ssAuf), "aufklapp: die Toleranzzeile folgt der Payload nicht");
    ok(!/± 4,1 W/.test(ssAuf), "aufklapp: die alte Spanne steht noch da (fester Wert im Template)");

    // HARTE REGEL: Schalter AUS zeigt die alte Rechnung - ohne Band, ohne
    // Rechenweg, mit dem Satz, wo man einschaltet.
    ok(!/class="bstrip"/.test(aus), "kachel aus: der Streifen zeigt ein Band, das nicht gilt");
    ok(!/mehr anzeigen/.test(aus), "kachel aus: der Rechenweg einer Rechnung, die nicht läuft");
    ok(!/186 – 194 W/.test(aus), "kachel aus: die Spanne der Steuerung steht da");
    contains(aus, "Woher die Zahlen kommen", "kachel aus: es steht nicht da, wo man einschaltet");
    contains(aus, "wie bisher", "kachel aus: das Schildchen nennt die Stellung nicht");
    contains(an, "mit Vorgabe", "kachel an: das Schildchen nennt die Stellung nicht");
    // Der alte Vorschlagssatz beschreibt die alte Rechnung - mit Schalter weg.
    ok(/Das System schlägt vor/.test(aus) && !/Das System schlägt vor/.test(an),
       "kachel: der alte Vorschlag steht auch mit Schalter noch da");
    // Der Verlauf traegt Band und Vorgabe nur, wenn sie gelten.
    ok(/gestrichelt = Vorgabe 250 W/.test(an), "kachel: der Verlauf nennt die Vorgabe nicht");
    ok(!/gestrichelt/.test(aus), "kachel aus: der Verlauf zeigt eine Vorgabe, die nicht gilt");

    // RANDFALL: zu wenige Einheiten -> „noch keine Toleranz“, kein Streifen
    const duenn = F.blocks({ steering_on: true });
    duenn.steering.sweetspot = { ...duenn.steering.sweetspot, band: null,
      band_note: "noch keine Toleranz", hr_band: null, hr_band_note: "noch keine Toleranz" };
    duenn.compare.sweetspot = { ...duenn.compare.sweetspot, new_band: null, new_hr_band: null };
    const dHtml = String(q.rBlocks(duenn)).replace(/\s+/g, " ");
    const ssTeil2 = dHtml.slice(dHtml.indexOf("SweetSpot"));
    contains(ssTeil2, "noch keine Toleranz", "randfall: die dünne Kachel sagt es nicht");
    ok(!/186 – 194 W/.test(ssTeil2), "randfall: sie zeigt trotzdem eine Spanne");
    ok(/Für eine Spanne braucht es 3 gemessene Einheiten/.test(ssTeil2),
       "randfall: der Satz zur fehlenden Spanne fehlt");

    // RANDFALL: Familie mit nur EINEM Block -> keine Zeilen, kein Verlauf
    const einer = F.blocks({ steering_on: true });
    einer.steering.sweetspot = { ...einer.steering.sweetspot, watts: 190, rows: [],
      n_units: 0, single_block: ["2026-08-24"], band: null, band_note: "noch keine Toleranz" };
    einer.compare.sweetspot = { ...einer.compare.sweetspot, new_band: null };
    const eHtml = String(q.rBlocks(einer)).replace(/\s+/g, " ");
    const ssTeil3 = eHtml.slice(eHtml.indexOf("SweetSpot"));
    ok(!/Verlauf — Watt ab Block 2[\s\S]{0,400}SweetSpot/.test(ssTeil3 + "SweetSpot")
       || !/svg/.test(ssTeil3.slice(0, 600)),
       "randfall: die Ein-Block-Familie bekommt trotzdem einen Verlauf");
    contains(ssTeil3, "190", "randfall: die Ein-Block-Familie zeigt ihre Vorgabe nicht");

    // KEINE ZAHL IM QUELLTEXT: die Bausteine tragen keine Wattwerte.
    const src = H.source();
    for (const name of ["_famValue", "_famTrend", "_famMore"]) {
      const baustein = (new RegExp(name + "\\(b, key\\) \\{[\\s\\S]*?\\n  \\}")).exec(src);
      ok(baustein !== null, `kachel: der Baustein ${name} ist im Quelltext nicht auffindbar`);
      ok(baustein && !/\b(?:186|190|194|235|250|265|252|262)\b/.test(baustein[0]),
         `kachel: in ${name} steht eine Wattzahl statt eines Werts aus der Payload`);
    }
  }

  // Leerer und rechnender Zustand
  const leer = String(q.rBlocks(F.blocks({ families: {} })));
  contains(leer, "Noch keine Einheit mit markierten", "M: der leere Fall sagt nichts");
  const rechnet = String(q.rBlocks(F.blocks({ families: {},
    progress: { done: 20, pending: 38, total: 58, batch: 25, importing: true } })));
  contains(rechnet, "nicht defekt", "M: der rechnende Zustand sagt nicht, dass er arbeitet");
}

/* ── S1 (0.69.0): EINE Basislinie, ueberall gleich beschriftet ─────────── */
// Drei HRV-Basislinien im Paket (Karte 4b, F4b.3) hiessen alle "±0,5 SD" und
// rechneten verschieden. Seit S1 rechnen Trainer, Ampel und Signale dasselbe
// Band (60 Naechte davor, gewichtet) - und die Beschriftung sagt es an allen
// drei Stellen mit demselben Satz.
{
  const q = new M.Panel();
  q._nowIso = F.TODAY;
  q._status = { athlete: "Test" };
  const satz = "60 Nächte davor";
  const bel = String(q.rBelastung(F.load())).replace(/\s+/g, " ");
  contains(bel, satz, "S1 Belastung: der HRV-Trend nennt das eine Band nicht");
  contains(bel, "gewichtet", "S1 Belastung: die Gewichtung fehlt an der Beschriftung");
  const sig = String(q.rSignals ? q.rSignals(F.signals ? F.signals() : null) : (q.rSignale ? q.rSignale(F.signals ? F.signals() : null) : "")).replace(/\s+/g, " ");
  contains(sig, satz, "S1 Signale: der Reiter nennt das eine Band nicht");
  contains(sig, "wie beim Trainer", "S1 Signale: der Gleichlauf mit dem Trainer steht nicht da");
}

/* ── L4: die Wattvorgabe kommt aus der Messung, und die Karte sagt es ───── */
// 0.68.0: die Grundlage liest Ziel und Grenze der Umkehrung (watt_source "ga"),
// nicht mehr die Ermuedungskurve ("curve" mit Anteil 0,90). Der Waechter zieht
// nach wie bei F1.6: die alte Karte ("aus deiner eigenen Messung", "90 % der
// gemessenen Schwelle", "Studienform" am Abschnitt) fror den Zustand VOR der
// Umkehrung ein; die Zahlen kommen weiter aus der Payload, nie aus dem Quelltext.
{
  const q = new M.Panel();
  q._nowIso = F.TODAY;
  const base = F.workouts().workouts[0];
  const ga = (extra) => ({ label: "gleichmäßig", watts: 143, target: 143, limit: 170,
    hour: 1, n: 18, load_w: 132, alpha: 1.21, mid: 90.6, target_alpha: 1.3, limit_alpha: 1.0,
    ...extra });
  const ausKurve = { ...base, watt_source: "ga", family: "long",
    // blocks_w spiegelt blocks Abschnitt fuer Abschnitt (so baut scaled() es);
    // die Fixture hatte bis 0.67.1 nur zwei Eintraege gegen drei Abschnitte.
    blocks_w: [[12, 118, "Einrollen"], [130, 143, "gleichmäßig", true], [8, 108, "Ausrollen"]],
    ga_blocks: [ga({ hour: 2, n: 12 })] };
  const opts = { toggleAct: "wodetail", ftp: 215 };
  const karte = String(q._sessionCard(ausKurve, opts));
  const flach0 = (x) => String(x).replace(/\s+/g, " ");
  // S4 (0.67.2, W4a.2 / F4a.4): der Balken liest blocks_w - dieselbe Zahl wie
  // die Schrittliste -, nicht FTP x Katalogprozent. Rot an 0.67.1.
  {
    const w = ausKurve.blocks_w.map((b) => b[1]);
    const tips = [...karte.matchAll(/class="wob"[^>]*title="([^"]*)"/g)].map((m) => m[1]);
    ok(tips.length === ausKurve.blocks_w.length, `S4 Balken: ${tips.length} Segmente gegen ${ausKurve.blocks_w.length} Abschnitte`);
    ok(tips.every((t, i) => new RegExp(`\\b${w[i]} W`).test(t)),
       `S4 Balken: die Tooltips tragen nicht die Watt der Schrittliste (${tips.join(" | ")})`);
    ok(!/% FTP/.test(karte), "S4 Balken: Prozent statt Watt");
    // ohne FTP (Wochenplan bis 0.67.1): dieselben Watt, kein Prozent
    const ohneFtp = String(q._sessionCard(ausKurve, { ...opts, ftp: undefined }));
    const tips2 = [...ohneFtp.matchAll(/class="wob"[^>]*title="([^"]*)"/g)].map((m) => m[1]);
    ok(tips2.every((t, i) => new RegExp(`\\b${w[i]} W`).test(t)) && !/% FTP/.test(ohneFtp),
       `S4 Balken ohne FTP: nicht die Watt der Schrittliste (${tips2.join(" | ")})`);
  }
  clean(karte, "einheit aus der umkehrung");
  // 0.68.0: die Karte sagt Ziel UND Grenze in einem Satz - "fahr ~X W, nicht
  // über Y W" - beide aus der Payload, und sie nennt die Ablesestelle.
  ok(/fahr ~143 W, nicht über 170 W/.test(flach0(karte)),
     "L4 (0.68.0): die Karte nennt nicht Ziel und Grenze der Umkehrung");
  ok(/Stunde 2/.test(karte) && /12 Fahrten/.test(karte), "L4: die Ablesestelle (Stunde, Fahrten) fehlt");
  contains(flach0(karte), "Setzung", "L4: die Umrechnung steht nicht als Setzung da");
  ok(!/Studienform/.test(karte) && !/gemessenen Schwelle/.test(karte),
     "L4 (0.68.0): die Karte spricht noch von der Ermüdungskurve");
  ok(/class="wsrc"[^>]*>Umkehrung</.test(karte),
     "L4: der Abschnitt aus der Umkehrung ist nicht als solcher gekennzeichnet");
  ok(!/ungeprüft/.test(karte), "L4: eine Stunde unter 3 h wird als ungeprüft ausgegeben");
  // Ab 3 h ist die Kette ungeprueft - die Abnahmefahrt (3 h bei ~122 W) steht
  // noch aus. Die Karte sagt es, aus dem Feld der Payload, nicht aus der Stunde
  // im Quelltext.
  const lang = { ...base, watt_source: "ga", family: "long",
    blocks_w: [[200, 122, "gleichmäßig", true]],
    ga_blocks: [ga({ watts: 122, target: 122, limit: 150, hour: 3, n: 4, unverified: true })] };
  const kl = flach0(q._sessionCard(lang, opts));
  ok(/fahr ~122 W, nicht über 150 W/.test(kl), "L4 lang: Ziel und Grenze fehlen");
  contains(kl, "ungeprüft — Abnahmefahrt offen", "L4 lang: ab 3 h fehlt der Hinweis auf die Abnahmefahrt");
  // Ohne Ziel (Athlet B ohne Ziel-alpha) traegt die Karte NUR die Grenze -
  // keine 1,3 aus dem Quelltext, kein "fahr ~".
  const nurGrenze = { ...base, watt_source: "ga", family: "long",
    blocks_w: [[130, 170, "gleichmäßig", true]],
    ga_blocks: [ga({ watts: 170, target: null, target_alpha: null })] };
  const kg = flach0(q._sessionCard(nurGrenze, opts));
  ok(/nicht über 170 W/.test(kg) && !/fahr ~/.test(kg), "L4 ohne Ziel: die Karte erfindet ein Ziel");
  contains(kg, "kein Ziel eingetragen", "L4 ohne Ziel: das fehlende Ziel wird nicht benannt");
  ok(!/1,3|1\.3/.test(kg), "L4 ohne Ziel: eine 1,3 aus dem Quelltext");
  // GEGENPROBE, gezaehlt und benannt: Ein- und Ausrollen tragen KEINE Marke -
  // sonst pruefte der Test nur, dass ueberhaupt eine erscheint.
  ok(!/Einrollen[^<]*<em>[^<]*<\/em><i class="wsrc"/.test(karte),
     "L4: auch Ein- und Ausrollen tragen eine Herkunftsmarke");
  // Und der Rückfall wird benannt, statt stillschweigend zu greifen.
  const rueckfall = { ...base, watt_source: "ftp", family: "long",
    blocks_w: [[12, 118, "Einrollen"]] };
  contains(String(q._sessionCard(rueckfall, opts)), "Rückfall auf die FTP",
           "L4: der Rückfall auf die FTP wird verschwiegen");
  // 0.68.0, Athlet B: die FEHLENDE EINGABE steht an der Karte - "kein
  // Stufentest -> Watt aus der FTP" -, der Grund kommt aus der Payload
  // (ga_missing), nicht aus dem Quelltext.
  const ohneTest = { ...rueckfall, ga_missing: "Kein markierter Stufentest — ohne ihn gibt es keine Umrechnung" };
  const kt = String(q._sessionCard(ohneTest, opts)).replace(/\s+/g, " ");
  contains(kt, "Kein markierter Stufentest", "L4 Athlet B: der Grund des Rückfalls (kein Stufentest) fehlt an der Karte");
  ok(!/Kein markierter Stufentest/.test(String(q._sessionCard(rueckfall, opts))),
     "L4 Athlet B Gegenprobe: der Grund erscheint auch ohne ga_missing");
  // Seit 0.49.0 ist der Rueckfall bei VO2max und SweetSpot eine echte
  // Auskunft: dort SOLL gemessen werden, und wenn es nicht reicht, gehoert es
  // gesagt. Fuer die uebrigen Familien gibt es nichts zurueckzufallen.
  // 0.51.0: Tempo und Schwelle HABEN jetzt eine eigene Messung - den
  // Stufentest. Der Rueckfall ist dort also eine echte Auskunft geworden, und
  // der Waechter dreht sich um: er verlangt sie, statt sie zu verbieten.
  const hart = { ...base, watt_source: "ftp", family: "threshold",
    blocks_w: [[10, 194, "1"]] };
  // Umbrueche im Template duerfen ueber einen Satz nicht entscheiden.
  const flach = (x) => String(x).replace(/\s+/g, " ");
  contains(flach(q._sessionCard(hart, opts)), "nicht gemessen",
           "L4: Schwelle verschweigt den Rückfall, obwohl es seit dem "
           + "Stufentest etwas zu messen gäbe");
  // Und fuer eine Familie, die WEITERHIN nichts zu messen hat, gibt es auch
  // weiterhin nichts zurueckzufallen - sonst stuende dort eine Warnung ohne
  // Gegenstand.
  const ohne = { ...base, watt_source: "ftp", family: "recovery",
    blocks_w: [[10, 120, "ruhig"]] };
  ok(!/Rückfall auf die FTP/.test(String(q._sessionCard(ohne, opts))),
     "L4: eine Familie ohne eigene Messung meldet einen Rückfall, den es nicht gibt");
  // Gegenprobe, gezaehlt und benannt: der Ausdruck FINDET den Satz dort, wo er
  // steht - sonst prueft die Zeile darueber nur, dass nie etwas gefunden wird.
  ok(/Rückfall auf die FTP/.test(String(q._sessionCard(rueckfall, opts))),
     "L4 Gegenprobe: der Ausdruck findet den Rückfall auch dort nicht, wo er "
     + "steht - der Wächter ist blind");
  const duenn = { ...base, watt_source: "ftp", family: "vo2max",
    blocks_w: [[4, 220, "1"]] };
  contains(String(q._sessionCard(duenn, opts)).replace(/\s+/g, " "),
           "noch zu wenige gemessene Einheiten",
           "0.49.0: der Rückfall bei den gemessenen Familien wird verschwiegen");
  // 0.69.2 (F1): gibt es eine Vorgabe (steering_source), gilt "noch zu wenige
  // Einheiten" nicht - der Absatz nennt den Satz der Steuerung (Bloecke ja, Saetze nein).
  const satz30 = { ...base, watt_source: "ftp", family: "vo2max", blocks_w: [[10, 210, "Satz 1"]],
    steering_source: { watts: 250, n_units: 7, anchor_w: 250, anchor_date: "2026-09-17", moves: 0,
                       note_blocks: "Kein Abschnitt dieser Einheit bekommt die gemessene Vorgabe — die Zahlen stehen auf der FTP." } };
  const satz30Html = String(q._sessionCard(satz30, opts)).replace(/\s+/g, " ");
  ok(!/noch zu wenige gemessene Einheiten/.test(satz30Html), "F1 30/30: 'noch zu wenige Einheiten' trotz Vorgabe");
  contains(satz30Html, "Kein Abschnitt dieser Einheit bekommt die gemessene Vorgabe", "F1 30/30: der Satz der Steuerung fehlt");
  contains(satz30Html, "250 W", "F1 30/30: die Vorgabe wird nicht genannt");
  // und die gesteuerte Einheit hat ihren eigenen Herkunftsabsatz (bis 0.69.1: keinen)
  const gesteuert = { ...base, watt_source: "steering", family: "sweetspot", blocks_w: [[20, 190, "Block 1"]],
    steering_source: { watts: 190, n_units: 6, anchor_w: 190, anchor_date: "2026-09-17", moves: 0,
                       band: { low: 186, high: 194, n: 4 }, hr_band: { low: 159, high: 174 }, note_blocks: null } };
  const gesteuertTxt = String(q._sourceText(gesteuert)).replace(/\s+/g, " ");
  ok(gesteuertTxt.length > 0 && /Vorgabe/.test(gesteuertTxt) && /190 W/.test(gesteuertTxt) && !/Rückfall/.test(gesteuertTxt),
     "F1 Steuerung: die gesteuerte Einheit hat keinen Herkunftsabsatz oder einen falschen");
  // Und die gemessene Einheit nennt beide Quellen samt Rolle-Grenze.
  const gemessen = { ...base, watt_source: "blocks", family: "vo2max",
    blocks_w: [[4, 250, "1"]],
    block_source: { date: "2026-09-01", alpha: 0.405, n_blocks: 4, watts: 250,
                    sessions: 15, from: "2026-06-03", to: "2026-09-01" },
    hr_source: { low: 171, high: 186, n: 15, source: "measured" } };
  const gm = String(q._sessionCard(gemessen, opts)).replace(/\s+/g, " ");
  contains(gm, "Watt und Puls kommen aus deiner Blockmessung",
           "0.49.0: die Herkunft fehlt an der Einheit");
  contains(gm, "Beide aus derselben Quelle", "0.49.0: es steht nicht da, dass beide Seiten mitwandern");
  contains(gm, "Gilt für diese Einheit auf der Rolle", "0.49.0: die Rolle-Grenze fehlt an der Einheit");
}

/* ── die Ermuedungskurve: Beleg und Setzung getrennt, im Bild UND im Text ─ */
{
  const q = new M.Panel();
  q._nowIso = F.TODAY;
  const fat = F.fatigue();
  const html = String(q.rFatigue(fat));
  clean(html, "ermuedungskurve");

  // Leitzahl mit Beleg - und die Beschriftung, die Paket L woertlich verlangt
  contains(html, "auf Intervals' eigener DFA-Fensterung", "L1: die Pflichtbeschriftung fehlt");
  ok(!/nach Andriolo gerechnet/.test(html), "L1: behauptet, nach Andriolo gerechnet zu haben");
  ok(html.includes(String(fat.anchor_n)), "L1: der Anker steht ohne Belegung da");

  // BELEG UND SETZUNG: im Bild unterscheidbar (gestrichelt + Band) ...
  ok(/stroke-dasharray/.test(html), "L1: die Studienform ist nicht gestrichelt vom Gemessenen getrennt");
  ok(/<path d="M[^"]*Z" fill="/.test(html), "L1: kein Unsicherheitsband gezeichnet");
  // ... und im Text
  contains(html, "gemessen", "L1: das Gemessene wird nicht als solches benannt");
  contains(html, "Studienform", "L1: die Setzung wird nicht als solche benannt");

  // BEIDE LESERICHTUNGEN
  ok(/h — wie viel Watt\?/.test(html), "L1: Leserichtung Zeit -> Watt fehlt");
  ok(/W — wie lange\?/.test(html), "L1: Leserichtung Watt -> Zeit fehlt");

  // Die namentliche Ausschlussliste, mit Grund und Zahl
  contains(html, "Tempo 2×20 min", "L1: ausgeschlossene Fahrt nicht namentlich");
  ok(/46[.,]0 %/.test(html), "L1: ausgeschlossene Fahrt ohne ihren Zahlenwert");
  ok(/Von 74 Einheiten zählen/.test(html.replace(/\s+/g, " ")),
     "L1: die Gesamtzahl fehlt - wie viel vom Bestand bleibt übrig");
  // Gezaehlt wird aus den Zaehlfeldern, nicht aus den Listen: die Fixture
  // fuehrt 45 no_dfa-Fahrten, zeigt aber nur zwei davon. Eine Karte, die aus
  // der gekappten Liste zaehlt, behauptet eine kleinere Luecke als der Bestand.
  ok(/<b>ohne DFA-Strom: 45<\/b>/.test(html),
     "L1: die Ausschlusszahl kommt aus der gekappten Liste (2) statt aus dem Zählfeld (45)");

  // GEGENPROBE: ohne Ausschluesse gibt es auch keine Liste
  const ohne = String(q.rFatigue(F.fatigue({ dropped: {}, dropped_counts: {} })));
  ok(!/über Zone 2/.test(ohne.split("Rechenweg")[1] || ""),
     "L1: Ausschlussliste erscheint auch ohne Ausschlüsse");

  // L1b: gleichwertiger Teil, aber als SETZUNG beschriftet - und die eigene
  // Messung daneben, damit "nicht wiederfindbar" eine eigene Zahl ist.
  contains(html, "gilt für den ausgeruhten Zustand", "L1b: die Einschränkung der HF-Zahl fehlt");
  contains(html, "ist Literatur, keine Messung", "L1b: die Setzung ist nicht als solche beschriftet");
  contains(html, "Stufentest, wo die Belastung kontrolliert ist", "L1b: der Grund für die Gegenrichtung fehlt");
  contains(html, "benannt statt", "L1b: die fehlende Temperatur wird nicht benannt");
  ok(/158 bpm/.test(html), "L1b: die eigene Messung steht nicht neben der Setzung");
  // GEGENPROBE: ohne eigenen HF-Anker wird nichts hochgerechnet
  const ohneHr = String(q.rFatigue(F.fatigue({ aerobic_hr: null, hr_drift_expected: [] })));
  ok(!/ausgeruhten Zustand/.test(ohneHr), "L1b: Hochrechnung ohne eigenen Anker");

  // 0.46.0: die Ehrlichkeitsregel, UEBERTRAGEN von der Wolke auf die Kurve.
  // Dort hiess sie "keine Trendgerade ohne gesicherte Steigung", hier: keine
  // durchgezogene Messlinie ueber Stunden, die sie nicht tragen.
  const dickeLinien = (html.match(/stroke-width="2\.6"/g) || []).length;
  ok(dickeLinien === 1, `L1: ${dickeLinien} durchgezogene Messlinien statt einer`);
  // Die Regel haengt seit B2 an der LEITZAHL, nicht mehr an den Stundenmedianen:
  // durchgezogen wird nur, was die Weglassprobe traegt.
  // Die zwei Saetze an der Kachel, beide aus der PAYLOAD.
  contains(html, "AUSWAHLSATZ AUS DER PAYLOAD",
           "L1: der Auswahleffekt der spaeten Stunden steht nicht an der Kachel");
  contains(html, "ACHSENSATZ AUS DER PAYLOAD",
           "L1: der Achsen-Vorbehalt steht nicht an der Kachel");
  // GEGENPROBE: ohne duenne Zone erscheint der Auswahlsatz NICHT - sonst
  // laese ihn der Athlet an einer Kurve, die ihn nicht hat.
  const ganzFest = String(q.rFatigue(F.fatigue({
    plan: F.fatigue().plan.map((r) => ({ ...r, band: "solid" })),
    plan_solid_until_hours: 3, plan_thin_until_hours: 3 })));
  ok(!/AUSWAHLSATZ AUS DER PAYLOAD/.test(ganzFest),
     "L1: der Auswahlsatz steht auch ohne duenne Zone da");
  ok(/ACHSENSATZ AUS DER PAYLOAD/.test(ganzFest),
     "L1: der Achsen-Vorbehalt faellt mit der duennen Zone weg - er gilt immer");

  // DIE LINIE BRICHT BEIM ERSTEN RISS AB, an einer Fixture MIT Luecke geprueft.
  // Ohne Luecke sind "bis zum Riss" und "alle festen Punkte" dieselbe Menge -
  // die Mutation kam daran mit 0 Fehlern vorbei (M35). Dieselbe Klasse wie der
  // Backend-Fall solid_until (§7).
  const luecke = String(q.rFatigue(F.fatigue({
    plan: [{ hours: 1, watts: 152.5, n: 26, step: null, step_n: null,
             loo_shift: 0.4, loo_ratio: 0.04, band: "solid" },
           { hours: 2, watts: 142.4, n: 23, step: -10.1, step_n: 9,
             loo_shift: 9.9, loo_ratio: 2.75, band: "thin" },
           { hours: 3, watts: 138.8, n: 5, step: -3.6, step_n: 8,
             loo_shift: 0.5, loo_ratio: 0.14, band: "solid" }],
    plan_solid_until_hours: 1, plan_thin_until_hours: 3 })));
  // Der dicke Zug darf die Luecke NICHT ueberspannen: mit einem einzigen
  // festen Punkt gibt es gar keinen Zug (ein Pfad braucht zwei Punkte).
  const dick = [...luecke.matchAll(/<path d="([^"]*)"[^>]*stroke-width="2\.6"/g)];
  ok(dick.length === 0,
     `L1: der durchgezogene Zug ueberspannt den Riss (${dick.length} Pfade)`);
  // Trefferzusicherung: die Fixture ERZEUGT wirklich eine Luecke.
  ok(/stroke-width="1\.6"/.test(luecke),
     "L1 Fixture-Beweis: die Luecken-Fixture zeichnet gar keinen duennen Zug");

  const nurDuenn = String(q.rFatigue(F.fatigue({
    plan: F.fatigue().plan.map((r) => ({ ...r, band: "thin", loo_ratio: 2.0 })),
    plan_solid_until_hours: null })));
  ok(!/stroke-width="2\.6"/.test(nurDuenn),
     "L1: durchgezogene Messlinie, obwohl keine Stunde sie traegt");

  // Der Historienbeginn als Grund fuer die duenne Belegung - im Hauptteil,
  // nicht im Rechenweg, wo ihn niemand sucht.
  contains(html.split("Rechenweg")[0], "keinen DFA-Strom tragen",
           "L1: die fehlenden Fahrten werden nicht erklärt");
  const mitLuecke = F.fatigue(), ohneZaehler = F.fatigue({ dropped_counts: { structured: 2 } });
  // Trefferzusicherung (0.50.0, §7 elfter Fall): der Gegenfall muss die Zahl,
  // um die es geht, wirklich entfernt haben - und die Ausgangslage muss sie
  // gehabt haben. Sonst prueft die Zeile darunter den Originalzustand.
  ok((mitLuecke.dropped_counts || {}).no_dfa > 0,
     "L1 Gegenprobe: schon die Ausgangs-Fixture kennt keine fehlenden Stroeme");
  ok(!(ohneZaehler.dropped_counts || {}).no_dfa,
     "L1 Gegenprobe: der Gegenfall traegt die Zahl immer noch - er greift nicht");
  const ohneLuecke = String(q.rFatigue(ohneZaehler));
  ok(!/keinen DFA-Strom tragen/.test(ohneLuecke),
     "L1 Gegenprobe: der Hinweis erscheint auch ohne fehlende Ströme");

  // Die zwei Zahlen im Haus: benannt statt unbemerkt
  contains(html, "Zwei Zahlen für dieselbe Sache", "L1: der bekannte Unterschied wird verschwiegen");

  // Der Zustand "rechnet noch" - mit Fortschritt, nicht als leerer Platz
  const rechnet = String(q.rFatigue(F.fatigue({
    measured: [], literature: [], anchor_watts: null, anchor_base: null,
    progress: { done: 25, pending: 33, total: 58, batch: 25, importing: true } })));
  clean(rechnet, "ermuedungskurve rechnet noch");
  contains(rechnet, "25", "rechnet noch: der Fortschritt fehlt");
  contains(rechnet, "58", "rechnet noch: die Gesamtzahl fehlt");
  contains(rechnet, "nicht defekt", "rechnet noch: es steht nicht da, dass die Kachel arbeitet");
  ok(/2 Durchgänge/.test(rechnet), "rechnet noch: die verbleibenden Abgleiche fehlen");

  // und ein Bestand ohne lange Fahrt behauptet nichts
  const leer = String(q.rFatigue(F.fatigue({
    measured: [], literature: [], anchor_watts: null, anchor_base: null,
    progress: { done: 58, pending: 0, total: 58, batch: 25, importing: false } })));
  clean(leer, "ermuedungskurve ohne lange Fahrt");
  ok(!/W<\/b>/.test(leer.split("Rechenweg")[0]), "leer: eine Zahl ohne Grundlage");
}

/* ── der Historienbeginn: die DFA-Zahl traegt IHREN Zeitraum ───────────── */
{
  // Ein Bestand, dessen DFA-Daten SPAETER beginnen als die Aktivitaeten -
  // genau die Lage am lebenden System (58 Auswertungen ab 31.05. in einem
  // Bestand ueber 489 Tage). Die Kopfzeile stellte die 58 neben die 489 und
  // erzeugte damit den gegenteiligen Eindruck.
  const spaet = { activities: 240, wellness_days: 489, dfa_done: 58,
                  activities_from: "2025-05-12", dfa_from: "2026-05-31",
                  dfa_to: "2026-09-13", importing: false, decoupling_good: 5.0 };
  const kopf = M.dfaSpan(spaet);
  ok(/ab /.test(kopf), "historie: die DFA-Zahl nennt ihren eigenen Beginn nicht");
  ok(/106 Tage/.test(kopf), `historie: eigener Zeitraum falsch gerechnet (${kopf})`);
  ok(!/489/.test(kopf), "historie: die DFA-Zahl leiht sich den Wellness-Zeitraum");

  const q = new M.Panel();
  q._nowIso = F.TODAY;
  q._win.dfa = { id: "all" };
  q._status = spaet;
  const html = String(q.rDfa(thr, "all"));
  clean(html, "dfa mit spaetem Historienbeginn");
  contains(html, "Die DFA-Auswertung beginnt am", "historie: der Reiter weist den Beginn nicht aus");
  ok(/106 Tage/.test(html), "historie: der Reiter nennt den DFA-Zeitraum nicht");
  ok(/490 Tage zurückreicht/.test(html), "historie: der Reiter nennt den Bestandszeitraum nicht");

  // GEGENFALL, gezaehlt und benannt: decken sich beide Zeitraeume, gibt es
  // nichts zu sagen - ein Dauerhinweis stumpft ab und waere selbst wieder
  // eine Behauptung. Ohne diesen Fall prueft der Test oben nur, dass der Satz
  // ueberhaupt erzeugt werden kann.
  const deckt = { ...spaet, activities_from: "2026-05-31" };
  const q2 = new M.Panel();
  q2._nowIso = F.TODAY; q2._win.dfa = { id: "all" }; q2._status = deckt;
  ok(!/Die DFA-Auswertung beginnt am/.test(String(q2.rDfa(thr, "all"))),
     "historie: Hinweis auch bei deckungsgleichem Zeitraum");
  // und ein aelteres Backend ohne die Felder behauptet NICHTS
  const q3 = new M.Panel();
  q3._nowIso = F.TODAY; q3._win.dfa = { id: "all" };
  q3._status = { activities: 240, wellness_days: 489, dfa_done: 58 };
  ok(M.dfaSpan(q3._status) === "", "historie: ohne die Felder wird ein Zeitraum erfunden");
  clean(String(q3.rDfa(thr, "all")), "dfa ohne Historienfelder");
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
  // 0.73.3 umgestellt: bullet() ist entfernt (kein Aufrufer seit dem Heute-Kopf 0.73.0);
  // geprueft wird, dass es nicht zurueckkommt.
  ok(typeof M.bullet === "undefined", "bullet mini: bullet() ist wieder da, ohne Aufrufer");
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
  // 0.72.3: die Ueberschrift sagt, welche Nacht gemeint ist - das Etikett am Tag D
  // wirkt auf die Nacht, die am Morgen D endet, also den Abend D-1.
  const kopf = (d) => { q._ctxDlg = d; const h = q._ctxPopover();
    const m = h.match(/class="ctxhead"><b>([^<]*)<\/b>/); return { h, b: m ? m[1] : "" }; };
  const n26 = kopf("2026-09-26");
  ok(/Nacht zum 26\.09\.2026/.test(n26.b) && /Abend des 25\.09\.2026/.test(n26.b),
     `0.72.3: Ueberschrift nennt Nacht und Abend nicht: "${n26.b}"`);
  ok(!/Tag beschriften/.test(n26.h), "0.72.3: 'Tag beschriften' steht noch im Dialog");
  ok(/aria-label="Nacht beschriften"/.test(n26.h), "0.72.3: aria-label ist nicht 'Nacht beschriften'");
  for (const [d, abend] of [["2026-10-01", "30.09.2026"], ["2027-01-01", "31.12.2026"], ["2026-10-26", "25.10.2026"]]) {
    const k = kopf(d);
    ok(k.b.includes(`Nacht zum ${d.slice(8, 10)}.${d.slice(5, 7)}.${d.slice(0, 4)}`) && k.b.includes(`Abend des ${abend}`),
       `0.72.3: ${d} -> Abend des ${abend} erwartet, steht: "${k.b}"`);
  }
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

  // F1.6 · der Abgleich raeumt seit 0.66.3 auch Marken und Stufentests — und
  // sagt es vorher (Befund) und nachher (Vollzug). Rot an 0.66.2+F1.5.
  s._syncDlg = { state: "report", report: REP({ missing: [
    Object.assign({}, MISS[0], { marks: true, ramp: true }), MISS[1] ] }) };
  dlg = s._syncPopover();
  clean(dlg, "abgleich befund marken");
  contains(dlg, "Markierung", "abgleich befund: die Markierung der fehlenden Einheit wird nicht angesagt");
  contains(dlg, "Stufentest", "abgleich befund: der Stufentest der fehlenden Einheit wird nicht angesagt");
  s._syncDlg = { state: "done", report: REP({ applied: true,
                 removed: { activities: 2, dfa: 1, unavailable: 1, section_marks: 1, ramp_tests: 1, dfa_failed: 0 } }) };
  dlg = s._syncPopover();
  clean(dlg, "abgleich vollzug marken");
  contains(dlg, "Markierung", "abgleich vollzug: entfernte Markierungen nicht beziffert");
  contains(dlg, "Stufentest", "abgleich vollzug: entfernte Stufentests nicht beziffert");
  // Gegenprobe: ohne Marken/Stufentests kein Wort davon.
  s._syncDlg = { state: "done", report: REP({ applied: true,
                 removed: { activities: 2, dfa: 1, unavailable: 1, section_marks: 0, ramp_tests: 0, dfa_failed: 0 } }) };
  dlg = s._syncPopover();
  ok(!/Markierung|Stufentest/.test(dlg), "abgleich vollzug Gegenprobe: nennt Marken/Stufentests ohne Treffer");

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

    // 0.46.0: die Punktwolke ist als Hauptbild entfallen (PROJEKTSTAND §7,
    // "zwei Kacheln, eine Frage"). DREI Zusicherungen fallen mit dem Bild, weil
    // es das Bild nicht mehr gibt: die Zahl der gezeichneten Punkte, das
    // Gewicht als Groesse UND Deckkraft, und die Arbeits-x-Achse. Sie hatten
    // kein Gegenstueck an der neuen Kurve - dort gibt es keine Fahrtpunkte,
    // sondern Stundenmediane.
    // Die Ehrlichkeitsregel dagegen wird UEBERTRAGEN, nicht gestrichen: sie
    // steht jetzt an der Kurve (keine durchgezogene Messlinie ohne getragene
    // Belegung) und wird im Ermuedungskurven-Block geprueft.
    ok(!/<circle cx="[\d.]+" cy="[\d.]+" r="[\d.]+"[^>]*opacity=/.test(tileFlat),
       "durability: die Punktwolke wird immer noch gezeichnet");
    ok(!tileFlat.includes(M.C.violet),
       "durability: die Trendgerade der Wolke ist noch da");
    contains(tileFlat, "Streuung", "durability flach: sagt nicht, WORAN es liegt");
    ok(!/Bis etwa/.test(tileFlat), "durability flach: nennt trotzdem einen Kipppunkt");
    contains(tileFlat, String(flat.needed_sessions),
             "durability flach: sagt nicht, was die Messung voranbraechte");
    contains(tileClear, "Bis etwa", "durability klar: keine Leitzahl trotz gesicherter Steigung");
    ok(tileFlat !== tileClear, "durability: gesperrter und tragender Fall sind nicht unterscheidbar");

    // Die beiden Achsen: der Unterschied wird weiter benannt - aber im
    // RECHENWEG, nicht als laengster Absatz ueber vier Strichen (0.47.0).
    // 0.70.0 UMGESTELLT: die zwei Achsen stehen seit dem Umzug in zwei Reitern
    contains(tileFlat, "Zwei Achsen, mit Absicht getrennt",
             "durability: die zwei Achsen stehen unkommentiert nebeneinander");
    const rechenweg = tileFlat.slice(tileFlat.indexOf("Der Rechenweg"));
    contains(rechenweg, "kassiert", "durability: die Achsen-Begründung steht nicht im Rechenweg");
    ok(/Wie stark entkoppelt es\?/.test(tileFlat) && /Wird es besser\?/.test(tileFlat),
       "durability: die Abschnitte tragen keine eigenen Ueberschriften");

    // ZUGEKLAPPT, solange beide Abschnitte nichts sagen - mit einer Zeile, die
    // den Stand nennt. Und die DATENLAGE entscheidet, nicht der Code.
    const sumOf = (html) => (html.match(/<details class="more"( open)?><summary>([^<]*)</) || []);
    const flatSum = sumOf(tileFlat);
    ok(flatSum[1] === undefined, "durability flach: die tauben Abschnitte stehen offen");
    contains(flatSum[2] || "", "unter der", "durability flach: die Zusammenfassungszeile fehlt");
    contains(flatSum[2] || "", "kein Block trägt bisher einen Trend",
             "durability flach: der Blockstand fehlt in der Zeile");
    /* 0.50.0 Punkt 4: die doppelte Wertetabelle ist aufgeloest. Geblieben ist
       die im Rechenweg - sie traegt die Abweichungsspalte und steht dort, wo
       ohnehin nachgelesen wird. Die Bandbreite ist in die Ableseleiste
       gewandert, wo sie zur jeweiligen Stelle gehoert statt als Spalte fuer
       alle. */
    {
      const kachel = p.rFatigue(F.fatigue());
      const tabellen = (kachel.match(/<table class="dfatab">/g) || []).length;
      const rechenweg = kachel.slice(kachel.indexOf("<summary>Rechenweg</summary>"));
      ok(rechenweg.length > 0, "Punkt 4: der Rechenweg fehlt");
      ok(/<th>Abweichung<\/th>/.test(rechenweg),
         "Punkt 4: die verbliebene Tabelle traegt die Abweichungsspalte nicht");
      const oben = kachel.slice(0, kachel.indexOf("<summary>Rechenweg</summary>"));
      ok(!/<th>Band<\/th>/.test(oben),
         "Punkt 4: die obere Wertetabelle steht noch da");
      ok(!/<h4 class="subsec">Ablesen<\/h4>/.test(oben),
         "Punkt 4: die Ueberschrift der oberen Tabelle steht noch da");
      // Gegenprobe, gezaehlt und benannt: der Ausdruck findet eine
      // wiedereingebaute Tabelle auch - sonst prueft die Null oben nichts.
      ok(/<th>Band<\/th>/.test('<table><tr><th>Band</th></tr></table>'),
         "Punkt 4 Gegenprobe: eine wiedereingebaute obere Tabelle wird NICHT gefunden - blind");
      ok(tabellen >= 1, `Punkt 4: gar keine Wertetabelle mehr (${tabellen})`);
      // Und beide Leserichtungen stehen weiter im Hauptbild, nicht im Rechenweg.
      ok(/class="twoway"/.test(oben), "Punkt 4: die beiden Leserichtungen sind mitgefallen");
    }

    // GEGENPROBE, gezaehlt und benannt: sobald ein Block einen Trend traegt,
    // geht derselbe Abschnitt von selbst auf. Ohne diesen Fall pruefte die
    // Zusicherung oben nur, dass das Attribut nie gesetzt wird.
    const clearSum = sumOf(tileClear);
    ok(clearSum[1] === " open",
       "durability klar: der Abschnitt bleibt zu, obwohl ein Block einen Trend trägt");
    ok(/Blöcken trägt einen Trend/.test(clearSum[2] || ""),
       `durability klar: die Zeile nennt den Trend nicht (${clearSum[2]})`);
    // und ein reissendes Band oeffnet ihn ebenso - die zweite Bedingung, sonst
    // haengt die Automatik an einem einzigen Fall
    const laut = { ...flat, bins: flat.bins.map((b, i) => (i === 0 ? { ...b, median: flat.decoupling_good + 1 } : b)) };
    const lautSum = sumOf(String(p.rDurability(laut)));
    ok(lautSum[1] === " open",
       "durability: ein Band über der Marke öffnet den Abschnitt nicht");
    ok(/Arbeitsbändern über der/.test(lautSum[2] || ""),
       "durability: die Zeile nennt das reißende Band nicht");

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

    // Die Zeigergruppe haengt jetzt an der KURVE statt an der Wolke - umgehaengt,
    // nicht geloescht. Geprueft wird sie im Ermuedungskurven-Block.
    ok(p._grp.dur == null, "durability: die Zeigergruppe der Wolke lebt noch");
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

    /* 0.50.0 Punkt 1 und 2: der Kopf ist WEG. Zwei der drei Zeilen sind aus
       dem Graphen ablesbar, die dritte ist in den Wochenplan gewandert. Was
       hier stand, wird deshalb an ZWEI Orten geprueft - hier, dass es fort
       ist, und unten, dass es angekommen ist. Ein Umzug ohne beide Haelften
       ist eine Loeschung mit Absichtserklaerung. */
    ok(flat.blocked === "flat", "H Fixture-Beweis: der flache Fall ist doch nicht gesperrt");
    ok(!/<div class="durhead">/.test(tileFlat), "Punkt 1: der Kopfbereich steht noch da");
    for (const wort of ["WAS DU KANNST", "WIE WEIT DU GEKOMMEN BIST", "WAS ALS NÄCHSTES"]) {
      ok(!tileFlat.includes(wort), `Punkt 1: die Zeile "${wort}" steht noch im Kopf`);
    }
    // Gegenprobe, gezaehlt und benannt: die Ausdruecke finden einen
    // wiedereingebauten Kopf - sonst pruefen die Nullen oben gar nichts.
    ok(/<div class="durhead">/.test('<div class="durhead"><div class="dhcard">…'),
       "Punkt 1 Gegenprobe: ein wiedereingebauter Kopf wird NICHT gefunden - blind");

    // ERSATZLOS aufgegeben: Dauer, Datum und Leistung der laengsten Fahrt. Das
    // ist eine Entscheidung, kein Versehen - und sie steht im Rechenweg, sonst
    // sucht die Angabe in vier Wochen jemand.
    const rw = tileFlat.slice(tileFlat.indexOf("<summary>Der Rechenweg</summary>"));
    ok(rw.length > 0, "Punkt 1: der Rechenweg der Kachel fehlt");
    for (const satz of ["Ersatzlos aufgegeben", "Durchschnitt", "Schwellenleistung"]) {
      ok(rw.includes(satz), `Punkt 1: der Rechenweg sagt nicht, was mit dem Kopf geschah (${satz})`);
    }
    ok(!tileFlat.includes(M.dMed(pr.demonstrated.date)),
       "Punkt 1: das Datum der laengsten Fahrt steht noch in der Kachel");

    // Und die Zeile ist NICHT still in der Kachel geblieben - sonst gaebe es
    // sie zweimal, in der Kachel und im Wochenplan.
    for (const q of [tileFlat, tileClear]) {
      ok(!/Risikoknick/.test(q), "Punkt 2: die Progressionszeile steht noch in der Durability-Kachel");
      ok(!q.includes("keine Trainingsvorschrift"),
         "Punkt 2: die Grenze der Progressionsregel steht noch in der Kachel");
    }

    /* Angekommen: dieselbe Zeile im Wochenplan, mit allem, was zu ihr gehoert.
       Sie sagt, wie LANG die naechste Fahrt sein darf - deshalb steht sie
       dort, wo ueber Dauern entschieden wird. */
    // Umbruecke im Template duerfen ueber einen Satz nicht entscheiden.
    const eineZeile = (x) => String(x).replace(/\s+/g, " ");
    const plan = eineZeile(p.rPlanWeeks(F.goal(), pr));
    const planClear = eineZeile(p.rPlanWeeks(F.goal(), prc));
    clean(plan, "wochenplan mit Progressionszeile");
    contains(plan, M.hmn(pr.next_minutes), "Punkt 2: der naechste Schritt fehlt im Wochenplan");
    contains(plan, M.fmt(pr.factor, 2), "Punkt 2: der Faktor fehlt im Wochenplan");
    contains(plan, M.fmt((pr.factor - 1) * 100, 0) + " %",
             "Punkt 2: der Prozentsatz wird nicht aus dem Faktor gerechnet");
    contains(plan, "Läufern", "Punkt 2: die Grenze 'an Laeufern erhoben' fehlt");
    contains(plan, "keine Trainingsvorschrift", "Punkt 2: der Risikoknick wird als Vorschrift verkauft");
    contains(plan, M.dMed(pr.recent.date), "Punkt 2: die Bezugsfahrt wird nicht benannt");
    // Eine Zeile, keine Kachel.
    ok(!/dhcard|durhead/.test(plan), "Punkt 2: die Zeile ist als Kachel gebaut worden");

    // Der Rueckfall-Fall - kein Sonderzweig, sondern die Regel, sobald der
    // Schritt unter der belegten Faehigkeit liegt.
    ok(pr.below_demonstrated === true && prc.below_demonstrated === false,
       "H Fixture-Beweis: beide Faelle sind im Rueckfall gleich - der Zweig ist nicht pruefbar");
    contains(plan, "nicht deine Bestleistung", "Punkt 2: der Rueckfall-Satz fehlt");
    contains(plan, "was gerade in den Beinen steckt",
             "Punkt 2: der Rueckfall-Satz nennt den Grund nicht");
    ok(!/nicht deine Bestleistung/.test(planClear),
       "Punkt 2: der Rueckfall-Satz steht auch da, wo der Schritt UEBER der Bestleistung liegt");

    // Ausweitung des Bezugsfensters: nie still.
    ok(prc.recent.widened === true && pr.recent.widened === false,
       "H Fixture-Beweis: kein ausgeweiteter Fall in der Fixture");
    contains(planClear, "letzten " + M.fmt(prc.recent.days, 0) + " Tage",
             "Punkt 2: der ausgeweitete Zeitraum wird nicht genannt");
    contains(planClear, "deshalb der weitere Zeitraum",
             "Punkt 2: die Ausweitung geschieht still");
    ok(!/der weitere Zeitraum/.test(plan),
       "Punkt 2: der Ausweitungshinweis steht auch im nicht ausgeweiteten Fall");

    // Und sie verschwindet NICHT still, wenn der Plan noch nicht steht: sie
    // haengt am Bestand, nicht am Ziel (Fehlerklasse aus 0.42.1).
    const ohneZiel = eineZeile(p.rPlanWeeks({ plan: { ready: false, weeks: [] } }, pr));
    contains(ohneZiel, M.hmn(pr.next_minutes),
             "Punkt 2: ohne stehenden Plan faellt die Zeile still weg");
    ok(p.rPlanWeeks({ plan: { ready: false, weeks: [] } }, null) === "",
       "Punkt 2: ohne Progression bleibt trotzdem eine leere Karte stehen");

    const progHit = /<p class="hint">[^<]*<svg[\s\S]*?Trainingsvorschrift[\s\S]*?<\/p>/.exec(plan);
    ok(progHit !== null, "Punkt 2: die Progressionszeile ist im Wochenplan nicht auffindbar");
    const progLine = progHit ? progHit[0] : "";

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
    // 0.72.2: die Chips tragen das Stufenwort aus STAGES (vorher das Register-Wort)
    contains(weekBlocks[0], plan.stages[key].word.replace("{tag}", "heute"),
             `wochenplan: Stufe ${key} fehlt an den Chips`);
  }

  // aufgeklappt: Badge, Last, Budget, Zweck
  q._planOpen = "1";
  const open1 = q.rPlanWeeks(g);
  clean(open1, "wochenplan Woche 1");
  contains(open1, plan.stages.stimulus.word, "wochenplan: das Wort der Reiz-Stufe fehlt");
  contains(open1, "Last 159", "wochenplan: die hochgerechnete Last fehlt");
  // 0.67.3 (S5): die Zahl heisst Obergrenze - dieselbe wie im Heute-Reiter.
  contains(open1, "Obergrenze 95", "wochenplan: die Obergrenze steht nicht neben der Last");
  contains(open1, "Was das bringt", "wochenplan: die Wirkung der Einheit fehlt");

  // Die Karte ist dieselbe wie im Trainer-Reiter: Segmentbalken, Schritte in
  // Watt, Pulsfenster, Zweckzeile. Eine eigene, magerere Bauart für dieselbe
  // Sache wäre die Layout-Fassung einer zweiten Regel im Haus.
  contains(open1, 'class="wocard', "wochenplan: keine Sitzungskarte, sondern eigene Bauart");
  contains(open1, 'class="wosteps"', "wochenplan: die Schritte fehlen");
  contains(open1, "118 W", "wochenplan: die Wattzahlen der Segmente fehlen");
  contains(open1, "138–152 bpm", "wochenplan: das Pulsfenster fehlt");
  contains(open1, "Aerobe Basis", "wochenplan: die Zweckzeile fehlt");
  // gestreckt: EINE Dauer im Kopf, weil der Aufbau auf sie gebracht wurde
  contains(open1, "<b>195′</b> gleichmäßig", "wochenplan: der Aufbau wurde nicht auf die Dauer gestreckt");
  ok(!/Vorlage 95 min/.test(open1),
     "wochenplan: gestreckte Einheit nennt trotzdem zwei Dauern");
  // NICHT gestreckt (SweetSpot hat keinen dehnbaren Abschnitt): beide Dauern
  contains(open1, "geplant 1,2 h · Vorlage 70 min",
           "wochenplan: ungestreckte Einheit nennt nicht beide Dauern");

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

  // Beleg und Setzung stehen GETRENNT im aufklappbaren Teil: was die Literatur
  // hergibt (Aufwärmen absolut, Intervalle absolut) und was gesetzt ist (die
  // Differenz geht auf den gleichmäßigen Block). Zusammengezogen fängt die
  // Setzung an, als Befund durchzugehen.
  contains(deep, "Wie der Aufbau auf die Dauer kam", "streckung: der Hinweis fehlt in der Karte");
  contains(deep, "Less is more", "streckung: der Beleg zum Aufwärmen fehlt in der Karte");
  contains(deep, "absoluten Minuten", "streckung: die absolute Aufwärmdauer fehlt");
  contains(deep, "Setzung", "streckung: die Setzung wird in der Karte nicht benannt");
  const stretchBox = deep.slice(deep.indexOf("Wie der Aufbau auf die Dauer kam"));
  const evi = stretchBox.indexOf("<b>Beleg:</b>"), lim = stretchBox.indexOf("<b>Grenze:</b>");
  ok(evi > 0 && lim > evi, "streckung: Beleg und Grenze stehen nicht getrennt in der Karte");
  ok(!stretchBox.slice(evi, lim).includes("Setzung"),
     "streckung: die Setzung steht im Belegabschnitt der Karte");
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

  // 0.70.0 UMGESTELLT (B): Legende, Erholungsregel und "Wer hier entscheidet"
  // stehen im Reiter Quellen (_trainerSources) - dieselbe Payload (goal.plan).
  const qq0 = q._goal; q._goal = g;
  const quell = q._trainerSources();
  ok(!/Die vier Stufen/.test(folded) && !/Wer hier entscheidet/.test(folded), "wochenplan: die Legende steht noch im Wochenplan");
  contains(quell, "Die vier Stufen", "wochenplan: die Legende fehlt (Quellen)");
  for (const key of ["green", "yellow", "stimulus", "red"]) {
    contains(quell, plan.stages[key].detail, `wochenplan: Legende ohne Stufe ${key} (Quellen)`);
  }
  contains(quell, "Setzung", "wochenplan: die Erholungsregel wird nicht als Setzung beschriftet (Quellen)");

  // der Quellenblock: BEIDE Hälften des Javaloyes-Befunds
  contains(quell, "1 von 7", "wochenplan: die Nicht-Responder-Zahlen fehlen (Quellen)");
  contains(quell, "3 von 8", "wochenplan: die Vergleichszahl fehlt (Quellen)");
  contains(quell, "klein und unsicher", "wochenplan: die Grenze des Befunds fehlt (Quellen)");
  contains(quell, "fragt nicht nach kommenden Tagen",
           "wochenplan: die Regel, dass nicht vorab gefragt wird, fehlt (Quellen)");

  // eine Legende ohne Stufen in der Payload erfindet keine
  const bare = F.goal();
  delete bare.plan.stages;
  q._goal = bare;
  const noLegend = q._trainerSources();
  q._goal = qq0;
  ok(!/Die vier Stufen/.test(noLegend) && /Wer hier entscheidet/.test(noLegend),
     "wochenplan: die Legende wird ohne Payload erfunden (oder der Quellenblock fehlt ganz)");
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
  g2.plan.weeks[0].sessions[1].fit_reason = "Zwei harte Tage liegen schon in den sechs Tagen davor.";  // 0.73.2: Wortlaut wie workouts
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

/* ── N3: die Stufentest-Karte ───────────────────────────────────────────────
   Drei Zahlen, die dritte als Zusatz und nicht als Ersatz; der Leerzustand
   erklaert statt zu schweigen; die offene 40-Watt-Frage steht sichtbar in der
   Karte und nicht nur in der Spezifikation. */
{
  const q = new M.Panel();
  q._nowIso = F.TODAY;
  q._blocks = F.blocks();
  q._fatigue = F.fatigue();
  const eineZeile = (x) => String(x).replace(/\s+/g, " ");

  // --- 1 Leerzustand: kein leerer Platz ------------------------------------
  const leer = eineZeile(q.rRampTest({ tests: [], latest: null, sources: [] }));
  clean(leer, "Stufentest-Karte ohne Test");
  for (const [satz, was] of [["noch keinen Stufentest", "der Ausgangszustand"],
                             ["kein Fehler", "dass es kein Fehler ist"],
                             ["beide Schwellen", "was der Test liefern würde"],
                             ["denselben Bedingungen", "warum eine Fahrt besser ist"],
                             ["ändert sich <b>nichts</b>", "dass sich bis dahin nichts ändert"],
                             ["grünen Zustand", "dass er nur ausgeruht gefahren wird"]]) {
    contains(leer, satz, `N3 leer: ${was} fehlt`);
  }
  ok(!/–<\/b>/.test(leer), "N3 leer: es stehen Striche da, wo eine Erklärung stehen sollte");

  // --- 2 Die drei Zahlen ---------------------------------------------------
  const rt = { tests: [{ activity_id: "1", date: "2026-09-14" }],
    sources: ["Metaanalyse, Sports Med Open (2024): HRV-Schwellen allgemein, "
              + "DFA a1 das zweite auf sechs Studien."],
    latest: { date: "2026-09-14", result: {
      hrvt1: { alpha: 0.75, watts: 196, hr: 152 },
      hrvt2: { alpha: 0.5, watts: 248, hr: 171 },
      hrvt1_pers: { alpha: 0.95, watts: 172, hr: 142 },
      max_alpha_start: 1.4, pers_alpha: 0.95, reached_anaerobic: true,
      segment: { points: 1200, r2: 0.98 } } } };
  const voll = eineZeile(q.rRampTest(rt));
  clean(voll, "Stufentest-Karte mit Test");
  ok((voll.match(/class="stat"/g) || []).length === 3,
     "N3: es stehen nicht genau drei Zahlen da");
  for (const w of [196, 248, 172]) {
    contains(voll, String(w), `N3: die Zahl ${w} W fehlt in der Karte`);
  }
  contains(voll, "0,75", "N3: der alpha-Wert der ersten Schwelle fehlt");
  contains(voll, "0,50", "N3: der alpha-Wert der zweiten Schwelle fehlt");

  // --- 3 Die dritte Zahl ist ein ZUSATZ, kein Ersatz -----------------------
  contains(voll, "daneben, nicht anstelle", "N3: die dritte Zahl wird als Ersatz gezeigt");
  contains(voll, "umstritten", "N3: der umstrittene Nutzen wird verschwiegen");
  contains(voll, "0,67", "N3: die Korrelationen werden nicht genannt");
  contains(voll, "zweiter Hand", "N3: die Operationalisierung wird nicht als solche benannt");
  contains(voll, "Zeitfenster",
           "N3: der Unterschied zwischen den beiden Formulierungen fehlt");
  // Gegenprobe, gezaehlt und benannt: die Ausdruecke finden ihre Saetze auch
  // dort, wo sie NICHT stehen? Nein - im Leerzustand darf keiner davon stehen.
  ok(!/umstritten/.test(leer),
     "N3 Gegenprobe: der Satz zur dritten Zahl steht auch ohne Test da");

  // --- 4 Fehlende zweite Schwelle: Auskunft, kein Fehlversuch --------------
  const halb = eineZeile(q.rRampTest({ ...rt, latest: { date: "2026-09-14", result: {
    ...rt.latest.result, hrvt2: null, reached_anaerobic: false } } }));
  contains(halb, "nie stabil unter 0,5", "N3: die fehlende zweite Schwelle wird nicht erklärt");
  contains(halb, "nicht hochgerechnet", "N3: die Regel gegen das Hochrechnen fehlt");
  contains(halb, "kein Fehlversuch", "N3: der Abbruch wird als Fehlversuch dargestellt");
  ok(!/nie stabil/.test(voll),
     "N3 Gegenprobe: der Hinweis steht auch da, wo die Schwelle erreicht wurde");

  // --- 4b Widerspruch: unter 0,5 gemessen, HRVT2 trotzdem leer -------------
  const WID = "Unter 0,5 warst du — ab Sekunde 1900 mindestens 60 s lang. Die "
    + "Ausgleichsgerade durch den Abfall trifft 0,5 dort nur nicht, deshalb steht keine HRVT2.";
  const widFix = { ...rt.latest.result, hrvt2: null, reached_anaerobic: true,
    contradiction: { code: "reached_without_hrvt2", below_from_s: 1900, reason: WID } };
  ok(widFix.contradiction.reason === WID && widFix.reached_anaerobic === true,
     "N3 Widerspruch: die Fixture trägt das Feld nicht (Trefferzusicherung)");
  const wid = eineZeile(q.rRampTest({ ...rt, latest: { date: "2026-09-14", result: widFix } }));
  contains(wid, WID, "N3 Widerspruch: der Grund aus dem Ergebnis steht nicht in der Karte");
  contains(wid, "die Gerade trifft 0,5 nicht", "N3 Widerspruch: die Zelle der zweiten Schwelle bleibt ohne Hinweis");
  ok(!/nie stabil/.test(wid), "N3 Widerspruch: die Karte behauptet „nie stabil\", obwohl unter 0,5 gemessen wurde");
  ok(!/Ausgleichsgerade durch den Abfall trifft/.test(voll) && !/Ausgleichsgerade durch den Abfall trifft/.test(halb),
     "N3 Widerspruch Gegenprobe: der Satz steht auch ohne Widerspruch da");

  // --- 5 Der Rechenweg nennt Setzung und Verfahren -------------------------
  contains(voll, "gefittet", "N3 Rechenweg: dass gefittet wird, fehlt");
  contains(voll, "unsere Setzung", "N3 Rechenweg: die Segmentwahl wird nicht als Setzung benannt");
  // Belegtexte seit e1 (Quellen gelesen 16.09.2026): Rogers nach Augenschein,
  // Olieslagers' Handbestimmung offen, Ende am Lastende.
  contains(voll, "nach Augenschein", "N3 Rechenweg: wie Rogers den Abschnitt bestimmt, fehlt");
  contains(voll, "nicht nachgelesen", "N3 Rechenweg: die offene Handbestimmung bei Olieslagers wird behauptet statt beschriftet");
  contains(voll, "bis zum Lastende", "N3 Rechenweg: das Segment-Ende nach e1 fehlt");
  ok(!/flach unter 0,5 bleibt/.test(voll), "N3 Rechenweg: das alte Segment-Ende (vor e1) steht noch da");
  // §7 Fall 37: die Karte beschrieb einen „letzten Hochpunkt", der Code nimmt den höchsten Wert.
  contains(voll, "Die dritte Zahl steht daneben", "N3 Trefferzusicherung: der Absatz zur dritten Zahl ist nicht gerendert");
  contains(voll, "mittig zwischen dem höchsten Wert ab Rampenbeginn", "N3 dritte Zahl: der Hochpunkt ist nicht als höchster Wert ab Rampenbeginn beschrieben");
  contains(voll, "bei Gleichstand die späteste Stelle", "N3 Rechenweg: die Gleichstandsregel des Beginns fehlt");
  ok(!/letzte\s+Hochpunkt/.test(voll) && !/Hochpunkt am Beginn deines Abfalls/.test(voll),
     "N3: die Karte beschreibt eine Suche nach dem letzten Hochpunkt, die der Code nie gemacht hat");
  contains(voll, "Rogers 2021a/b (Laufband)", "N3 Rechenweg: Rogers ohne Arbeit und Sportart");
  // Variante B (§7 Fall 38): die Messung steht da und steuert noch nichts - das sagt die Karte.
  // 0.70.0 UMGESTELLT (C3): seit 0.68.0 steuert die Messung die Grundlage - das sagt die Karte.
  contains(voll, "Diese Messung steuert die Grundlage", "N3 B: die Karte sagt nicht, was die Messung steuert");
  contains(leer, "Stufentest", "N3 B Trefferzusicherung: die leere Karte ist nicht gerendert");
  ok(!/steuert die Grundlage/.test(leer), "N3 B Gegenprobe: der Satz steht auch ohne Messung da");
  // 0.70.0 UMGESTELLT (B): die Arbeiten stehen im Reiter Quellen (_rampSources)
  contains(q._rampSources(rt), "HRV-Schwellen allgemein",
           "N3 Rechenweg: die Einschränkung zur Metaanalyse fehlt (Quellen)");
  ok(!/r = 0,85 für DFA/.test(voll),
     "N3: die Metaanalyse wird als DFA-Beleg ausgegeben — sie gilt für alle "
     + "HRV-Verfahren zusammen");

  // --- 6 Die 40-Watt-Frage: ENTFERNT in 0.70.0 -----------------------------
  // rRampGap ("Die offene Frage: 56 Watt") ist nach Entscheidung (Skizze 0.70.0,
  // B) ersatzlos gestrichen - seit der Umkehrung (0.68.0) stehen die beiden
  // Zahlen nicht mehr gegeneinander. Die 13 Pruefungen dieses Abschnitts hielten
  // Inhalt einer Karte fest, die es nicht mehr gibt; dass sie nirgends mehr
  // steht, prueft der Abschnitt 0.70.0 (B, "56 W").
  // --- 7 Ohne Daten keine Karte -------------------------------------------
  ok(q.rRampTest(null) === "", "N3: ohne Payload wird eine Karte gebaut");
  // (0.70.0: die zwei rRampGap-Leerfaelle sind mit der Karte entfallen)
}


/* ── A2 · KEIN ROHSCHLÜSSEL IN DER AUSSCHLUSSLISTE ──────────────────────────
   Die markierte Auswahl vergibt `not_measured`; das Panel kannte dafür kein
   Wort und zeigte „not_measured: 1" (0.56.0, §7). Das Wort kommt jetzt aus
   der Payload. */
{
  const q = new M.Panel();
  const fahrt = [{ activity_id: "i9", date: "2026-06-04", name: "Volumen", above_z2: null, minutes: 90 }];
  const basis = { rides_used: 12, dropped: { not_measured: fahrt }, dropped_counts: { not_measured: 1 } };
  const mitWort = String(q._fatigueDropped({ ...basis,
    dropped_words: { not_measured: ["WORT AUS DER PAYLOAD", "SATZ AUS DER PAYLOAD"] } }));
  const ohneWort = String(q._fatigueDropped(basis));
  ok(/not_measured/.test(JSON.stringify(basis)),
     "A2 Fixture-Beweis: die Fixture trägt den Grund nicht");
  ok(/WORT AUS DER PAYLOAD/.test(mitWort) && /SATZ AUS DER PAYLOAD/.test(mitWort),
     "A2: das Wort aus der Payload wird nicht gezeigt");
  ok(!/not_measured/.test(mitWort), "A2: der Rohschlüssel steht in der Anzeige");
  // Auch wenn ein Wort fehlt, erscheint kein Rohschlüssel — sondern das Fehlen.
  ok(!/not_measured/.test(ohneWort) && /ohne Beschreibung/.test(ohneWort),
     "A2: ohne Wort erscheint der Rohschlüssel statt eines benannten Fehlens");
  ok(/Volumen/.test(mitWort), "A2: die Fahrt steht nicht namentlich da");
}

/* ── DER QUELLEN-REITER ────────────────────────────────────────────────────
   ZWEI Schalter mit einer Sperre dazwischen. Die Abhängigkeitsrichtung ist nur
   zu sehen, wenn beide nebeneinander stehen — deshalb ein Reiter und keine
   Kachel. Geprüft wird an BEIDEN Stellungen, und die Fixture muss nachweisen,
   dass sie sich unterscheiden (§7, achtundzwanzigster Fall). */
{
  const q = new M.Panel();
  q._nowIso = F.TODAY;
  const marken = { marks: [
    { activity_id: "e1", marks: { endurance: [0] },
      measure: { endurance: { hours: [{ hour: 1, p075: 150 }] } } },
    { activity_id: "t1", marks: { tempo: [0] },
      measure: { tempo: { blocks: [{ start_index: 0, alpha: 0.9, watts: 180 }] } } },
    { activity_id: "t2", marks: { tempo: [0] }, measure: {} },
  ], min_for_source: 3 };
  q._smarks = marken;
  q._blocks = { families: {} };

  // Die Gegenstellung kommt aus der PAYLOAD (`plan_other`), nicht als Literal
  // aus dem Frontend — sonst stünde dort eine Zahl ohne Herkunft, die beim
  // ersten Umbau falsch wird.
  const gegen = [{ hours: 1, watts: 161.0 }, { hours: 2, watts: 133.0 },
                 { hours: 3, watts: 130.0 }];
  const aus = String(q.rQuellen(F.fatigue({ from_marks: false, plan_other: gegen,
    switch_note: "LESERICHTUNGSSATZ AUS DER PAYLOAD" }), q._blocks));
  q._smarks = marken;
  const an = String(q.rQuellen(F.fatigue({ from_marks: true, plan_other: gegen,
    switch_note: "LESERICHTUNGSSATZ AUS DER PAYLOAD" }), q._blocks));

  // TREFFERZUSICHERUNG: die beiden Stellungen rendern WIRKLICH Verschiedenes.
  ok(aus !== an, "quellen Fixture-Beweis: beide Stellungen rendern dasselbe");
  // EIN WORT, EINE BEDEUTUNG: "Grundlage" ist der Name einer Familie. Als
  // Beschriftung der Trägerzeile stand über dem Blockschalter "Grundlage:
  // VO2max: 0 von 3" — zwei Bedeutungen in einer Kachel.
  ok(!/<b>Grundlage:<\/b>/.test(aus) && !/<b>Grundlage:<\/b>/.test(an),
     "quellen: das Wort Grundlage steht als Beschriftung neben der Familie gleichen Namens");
  ok(/Worauf es steht:/.test(aus),
     "quellen: die Trägerzeile fehlt");

  // DIE KORRIDOR-GEGENÜBERSTELLUNG am Blockschalter. Keine Automatik: der
  // Bereich steht fest, das alpha ist gemessen, verglichen werden zwei Zahlen.
  const qk = new M.Panel();
  qk._smarks = { marks: [], families: Object.keys(M.FAM), min_for_source: 3,
    corridors: { tempo: [0.75, 1.0] },
    corridor_state: { tempo: { blocks: 3, outside: [{ date: "2026-09-13", alpha: 1.346 }] } },
    outside_note: "FOLGESATZ AUS DER PAYLOAD." };
  const mitK = String(qk.rQuellen(F.fatigue({ from_marks: true }), null));
  // TREFFERZUSICHERUNG: die Fixture trägt einen Block AUSSERHALB und einen
  // Bereich dazu - ohne beides prüft die Zeile nichts.
  ok(qk._smarks.corridor_state.tempo.outside.length === 1
     && qk._smarks.corridors.tempo[1] < qk._smarks.corridor_state.tempo.outside[0].alpha,
     "korridor Fixture-Beweis: die Fixture hat keinen Block außerhalb");
  ok(/1 von 3 Blöcken außerhalb des Bereichs/.test(mitK),
     "korridor: die Gegenüberstellung fehlt");
  ok(/alpha 1[.,]35/.test(mitK) && /0[.,]75–1[.,]00/.test(mitK),
     "korridor: die Zahlen oder der Bereich fehlen");
  ok(/FOLGESATZ AUS DER PAYLOAD\./.test(mitK),
     "korridor: der Satz ist im Frontend eingebaut statt aus der Payload");
  // KEIN VORWURFSTON an dieser Stelle.
  const kzeile = (/Im Bereich nachgesehen:[\s\S]{0,260}/.exec(mitK) || [""])[0];
  ok(kzeile !== "" && !/fehlerhaft|ungültig|falsch/i.test(kzeile),
     `korridor: die Zeile klingt nach Mangel (${kzeile.slice(0, 120)})`);
  // ZWEI REGISTER: die Gegenüberstellung trägt keine Urteilsfarbe. Geprüft
  // am gerenderten Absatz UND an der Regel, auf die seine Klasse zeigt —
  // eine umbenannte Klasse mit Amber-Rand bestünde sonst.
  const kAbsatz = (/<p class="([^"]*)">\s*<b>Im Bereich nachgesehen:/.exec(mitK) || [])[1];
  ok(kAbsatz !== undefined, "korridor: der Absatz ist nicht auffindbar");
  ok(kAbsatz !== undefined && !/\bwarn\b/.test(kAbsatz),
     `korridor: die Gegenüberstellung trägt die Urteilsklasse (${kAbsatz})`);
  const kCss = H.source();
  const kKlassen = String(kAbsatz || "").split(/\s+/).filter((k) => k && k !== "src");
  const kRegeln = kKlassen.map((k) => (new RegExp(`\\.src\\.${k}\\{[^}]*\\}`).exec(kCss) || [""])[0]);
  ok(kKlassen.length === 1 && kRegeln[0] !== "",
     `korridor: die Hinweisklasse hat keine eigene Regel (${kKlassen.join(",")})`);
  ok(kRegeln.every((r) => !/C\.(amber|green|red|orange)\b/.test(r)) && kRegeln.some((r) => /C\.(blue|violet|cyan|magenta|slate|deep)\b/.test(r)),
     `korridor: die Hinweisklasse nimmt keine Kategorienfarbe (${kRegeln.join(" ")})`);
  // Trefferzusicherung für die Farbprüfung: die Urteilsklasse FÄLLT durch sie.
  const warnRegel = (/\.src\.warn\{[^}]*\}/.exec(kCss) || [""])[0];
  ok(/C\.amber/.test(warnRegel), "korridor Fixture-Beweis: die Farbprüfung erkennt die Urteilsklasse nicht");
  // GEGENPROBE: ohne Block außerhalb steht die Zeile NICHT da.
  const qo = new M.Panel();
  qo._smarks = { marks: [], families: Object.keys(M.FAM), min_for_source: 3,
    corridors: { tempo: [0.75, 1.0] },
    corridor_state: { tempo: { blocks: 3, outside: [] } },
    outside_note: "FOLGESATZ AUS DER PAYLOAD." };
  ok(!/Im Bereich nachgesehen/.test(String(qo.rQuellen(F.fatigue({ from_marks: true }), null))),
     "korridor: die Zeile steht auch ohne Block außerhalb da");

  ok(/Ermüdungskurve/.test(aus) && /Arbeitsblöcke/.test(aus),
     "quellen: die beiden Schalter stehen nicht nebeneinander");
  // KEINE SPERRE MEHR (B2b-2). Sie hing an einer widerlegten Begründung (die
  // Kurve steuere das Pulsfenster), danach an „noch nicht gebaut". Gebaut ist er,
  // und eine Sperre hätte die Mischung „Marken / Namenserkennung" ohnehin nicht
  // verhindert: sie entsteht schon mit dem Kurvenschalter allein.
  ok(!/Noch gesperrt/.test(aus) && !/Noch gesperrt/.test(an),
     "quellen: der Blockschalter ist gesperrt, obwohl er gebaut ist");
  ok(!/Pulsfenster, an dem|noch nicht gebaut/.test(aus + an),
     "quellen: eine widerlegte Sperrbegründung steht wieder da");
  const knoepfeAus = (aus.match(/data-act="swblocks"/g) || []).length;
  const knoepfeAn = (an.match(/data-act="swblocks"/g) || []).length;
  ok(knoepfeAus === 1 && knoepfeAn === 1,
     `quellen: der Blockschalter ist nicht in beiden Stellungen bedienbar (${knoepfeAus} / ${knoepfeAn})`);

  // KEIN KNOPF OHNE HANDLER (§7, fünfundzwanzigster Fall, andersherum): jedes
  // data-act, das der Reiter in einer der beiden Stellungen rendert, hat einen
  // Zweig im Klick-Handler. Allgemein statt für swblocks allein — der nächste
  // Schalter kommt mit B2b-2.
  const handlerSrc = H.source();
  const ohneHandler = (html) => [...new Set((html.match(/data-act="([^"]+)"/g) || [])
    .map((m) => m.slice(10, -1)))].filter((a) => !handlerSrc.includes(`act === "${a}"`));
  ok(ohneHandler(aus + an).length === 0,
     `quellen: gerenderte Knöpfe ohne Handler: ${ohneHandler(aus + an).join(", ")}`);
  // Trefferzusicherung für den Prüfer selbst: ein erfundener Knopf WIRD gefunden.
  ok(ohneHandler('<button data-act="gibtesnicht">').length === 1,
     "quellen Fixture-Beweis: der Handler-Prüfer findet einen Knopf ohne Handler nicht");

  // KEIN LITERAL ALS RÜCKFALL für die Mindestzahl: ohne Payload-Zahl keine Zahl.
  q._smarks = { ...marken, min_for_source: undefined };
  const ohneMin = String(q.rQuellen(F.fatigue({ from_marks: true, plan_other: gegen }), q._blocks));
  q._smarks = { ...marken, min_for_source: 4 };
  const mitMin = String(q.rQuellen(F.fatigue({ from_marks: true, plan_other: gegen }), q._blocks));
  q._smarks = marken;
  ok(ohneMin !== mitMin, "quellen Fixture-Beweis: die Mindestzahl ändert nichts an der Anzeige");
  ok(!/von 3/.test(ohneMin), "quellen: ohne Mindestzahl in der Payload steht eine 3 aus dem Quelltext");
  ok(/von 4/.test(mitMin), "quellen: die Mindestzahl aus der Payload wird nicht gezeigt");

  // ── DIE FAHRTENLISTE unter dem Kurvenschalter ─────────────────────────
  // Welche Fahrten die Kurve tragen, klickbar, mit Abschnitten und Stunden —
  // und die markierten, die NICHT drinstehen, mit ihrem Wort aus der Payload.
  const fl = String(q.rQuellen(F.fatigue({ from_marks: true, plan_other: gegen,
    rides_used: 2,
    used: [{ activity_id: "u1", date: "2026-08-01", name: "Volumen <eins>",
             sections: [{ start_index: 0, seconds: 5400 }], hours_with_value: [1, 2] },
           { activity_id: "u2", date: "2026-08-02", name: "Volumen zwei",
             sections: [{ start_index: 3600, seconds: 1800 }], hours_with_value: [3] }],
    dropped: { remeasure_unknown: [{ activity_id: "d1", date: "2026-06-04", name: "Frühfahrt" }],
               measure_failed: [{ activity_id: "d2", date: "2026-06-05", name: "Ohne Strom",
                                  detail: "GRUND DER MESSUNG" }] },
    dropped_counts: { remeasure_unknown: 1, measure_failed: 1 },
    dropped_words: { remeasure_unknown: ["WORT UNBEKANNT", "SATZ UNBEKANNT"],
                     measure_failed: ["WORT OHNE ERGEBNIS", "SATZ OHNE ERGEBNIS"] },
  }), q._blocks));
  ok(/Welche Fahrten die Kurve tragen/.test(fl), "fahrtenliste: die Liste fehlt");
  ok(/data-act="gotoact"\s+data-id="u1"/.test(fl) && /data-act="gotoact"\s+data-id="u2"/.test(fl),
     "fahrtenliste: die tragenden Fahrten sind nicht klickbar");
  ok(/data-act="gotoact" data-id="d1"/.test(fl) && /data-act="gotoact" data-id="d2"/.test(fl),
     "fahrtenliste: die ausgeschlossenen Fahrten sind nicht klickbar");
  ok(/ab 1h00m, 30m/.test(fl), "fahrtenliste: Abschnittsbeginn und Dauer fehlen");
  ok(/mit Wert: <b class="tn">1, 2<\/b>/.test(fl) && /Stunde\s+mit Wert: <b class="tn">3<\/b>/.test(fl),
     "fahrtenliste: die Stunden mit Wert fehlen oder die Einzahl stimmt nicht");
  ok(/WORT UNBEKANNT/.test(fl) && /WORT OHNE ERGEBNIS/.test(fl) && /GRUND DER MESSUNG/.test(fl),
     "fahrtenliste: Wort oder Messgrund der ausgeschlossenen Fahrt fehlen");
  ok(!/remeasure_unknown|measure_failed/.test(fl.replace(/data-[a-z]+="[^"]*"/g, "")),
     "fahrtenliste: ein Rohschlüssel steht in der Anzeige");
  ok(!/<eins>/.test(fl) && /&lt;eins&gt;/.test(fl), "fahrtenliste: der Fahrtname ist nicht maskiert");
  // Die Zahl kommt aus dem ZÄHLFELD, nicht aus der Liste (sechste Bauregel):
  // ein Zählfeld, das von der Listenlänge abweicht, wird als Zählfeld gezeigt.
  const flZahl = String(q.rQuellen(F.fatigue({ from_marks: true, plan_other: gegen, rides_used: 7,
    used: [{ activity_id: "u1", date: "2026-08-01", name: "x", hours_with_value: [1] }] }), q._blocks));
  ok(/Welche Fahrten die Kurve tragen:\s*<b class="tn">7<\/b>/.test(flZahl),
     "fahrtenliste: die Zahl kommt aus der Liste statt aus dem Zählfeld");
  ok(q._curveRides(null) === "", "fahrtenliste: ohne Payload wird eine Liste gebaut");

  // ── DER BLOCKSCHALTER: Zahlen beider Stellungen, Satz, Tempo ohne Vorgabe ──
  const blk = (from_marks) => ({ from_marks, feeds_watts: ["sweetspot", "vo2max"],
    selection: { label: from_marks ? "AUSWAHL MARKEN" : "AUSWAHL NAMEN" },
    switch_note: from_marks ? "RUECKSATZ AUS DER PAYLOAD" : "UMLEGESATZ AUS DER PAYLOAD",
    families: { vo2max: { sessions: from_marks ? 6 : 15, source_ok: true,
                          latest: { median_watts: from_marks ? 251 : 250, first_watts: 257, first_alpha: 0.47 },
                          hr_window: from_marks ? { low: 176, high: 186 } : { low: 172, high: 186 } },
                tempo: { sessions: from_marks ? 2 : 1, source_ok: false, latest: { median_watts: 169 } } },
    other: { vo2max: { sessions: from_marks ? 15 : 6, watts: from_marks ? 250 : 251,
                       hr_low: from_marks ? 172 : 176, hr_high: 186 },
             tempo: { sessions: from_marks ? 1 : 2, watts: null } } });
  const bAus = String(q.rQuellen(F.fatigue({ from_marks: true, plan_other: gegen }), blk(false)));
  const bAn = String(q.rQuellen(F.fatigue({ from_marks: true, plan_other: gegen }), blk(true)));
  const bZeile = (html, label) => {
    const t = new RegExp(`<td>${label}<\\/td>\\s*<td class="tn">([^<]*)<\\/td>\\s*<td class="tn">([^<]*)<`)
      .exec(html.replace(/\s+/g, " "));
    return t ? [t[1].trim(), t[2].trim()] : null;   // Regex null-geprüft (§9)
  };
  const vAus = bZeile(bAus, "VO2max: Pulsfenster"), vAn = bZeile(bAn, "VO2max: Pulsfenster");
  ok(vAus !== null && vAn !== null, "blockschalter: die Pulsfenster-Zeile ist nicht ablesbar");
  // TREFFERZUSICHERUNG: die Fixture unterscheidet beide Stellungen an dieser Zeile.
  ok(vAus && vAus[0] !== vAus[1], "blockschalter Fixture-Beweis: beide Stellungen tragen dasselbe Fenster");
  ok(vAus && vAn && vAus[0] === vAn[0] && vAus[1] === vAn[1] && vAus[0] === "172–186" && vAus[1] === "176–186",
     `blockschalter: die Spalten folgen nicht der Stellung (${JSON.stringify([vAus, vAn])})`);
  ok(/UMLEGESATZ AUS DER PAYLOAD/.test(bAus) && /RUECKSATZ AUS DER PAYLOAD/.test(bAn),
     "blockschalter: der Satz beim Umlegen kommt nicht aus der Payload");
  ok(/VO2max: Vorgabe/.test(bAus) && !/Tempo: Vorgabe/.test(bAus),
     "blockschalter: Tempo zeigt eine Blockzahl als Vorgabe, oder VO2max keine");
  ok(/Tempo: Einheiten/.test(bAus), "blockschalter Fixture-Beweis: Tempo steht gar nicht in der Tabelle");
  const bohneQuelle = String(q.rQuellen(F.fatigue({ from_marks: true, plan_other: gegen }),
    { ...blk(false), feeds_watts: [] }));
  ok(!/VO2max: Vorgabe/.test(bohneQuelle), "blockschalter: die Vorgabe-Zeile hängt nicht an feeds_watts");
  ok(/data-act="swblocks"[^>]*data-on="1"/.test(bAus) && /data-act="swblocks"[^>]*data-on="0"/.test(bAn),
     "blockschalter: der Knopf schaltet nicht in die andere Stellung");

  // ── B2c · DIE KACHEL-ERKLÄRUNG ─────────────────────────────────────────
  const xe = { watt_source: "blocks", family: "vo2max", block_source: { watts: 250 },
    explain: { headline: { watts: 250, hr_low: 176, hr_high: 186 }, origin: "HERKUNFT AUS DER PAYLOAD",
      stage: "marks", units_count: 6, units_note: "",
      cycle: [{ key: "ftp", title: "STUFE-FTP", text: "t1", here: false },
              { key: "alpha", title: "STUFE-ALPHA", text: "t2", here: false },
              { key: "marks", title: "STUFE-MARKEN", text: "t3", here: true }],
      units: [{ activity_id: "e1", date: "2026-09-01", name: "VO2 <x>", detail: "250 W" }],
      steps: ["RECHENWEG-ZEILE"] } };
  const xh = String(q._explain(xe));
  const auf = xh.indexOf("<details");
  ok(auf > 0 && xh.indexOf("250 W · Puls 176–186") > -1 && xh.indexOf("250 W · Puls 176–186") < auf
     && xh.indexOf("HERKUNFT AUS DER PAYLOAD") > -1 && xh.indexOf("HERKUNFT AUS DER PAYLOAD") < auf,
     "B2c: zugeklappt stehen Zahl und Herkunft nicht vor dem Aufklappteil");
  const iK = xh.indexOf("Der Kreislauf"), iE = xh.indexOf("Gewertete Einheiten"), iR = xh.indexOf("Der Rechenweg");
  ok(auf < iK && iK < iE && iE < iR, `B2c: die Reihenfolge Kreislauf → Einheiten → Rechenweg stimmt nicht (${iK}/${iE}/${iR})`);
  ok((xh.match(/hier steht diese Einheit/g) || []).length === 1
     && xh.indexOf("hier steht diese Einheit") > xh.indexOf("STUFE-MARKEN"),
     "B2c: die eigene Stufe ist nicht genau einmal und an der richtigen Stelle markiert");
  ok(/data-act="gotoact" data-id="e1"/.test(xh) && /&lt;x&gt;/.test(xh), "B2c: Einheiten nicht klickbar oder unmaskiert");
  ok(/Gewertete Einheiten: 6/.test(xh) && /RECHENWEG-ZEILE/.test(xh), "B2c: Zählfeld oder Rechenweg fehlen");
  const xAlt = String(q._sourceText(xe));
  ok(xAlt.length > 0 && xh.includes(xAlt), "B2c: der bisherige Herkunftsabsatz fehlt im Rechenweg");
  ok(String(q._explain({ ...xe, explain: null })) === xAlt,
     "B2c: ohne Payload steht nicht der bisherige Absatz");

  // ── DIE 40-WATT-FRAGE nennt je Zahl ihre Auswahl: ENTFERNT in 0.70.0 (3
  // Pruefungen) - die Karte ist gestrichen (Skizze B), `_auswahl` mit ihr.

  // DIE ZAHLEN BEIDER STELLUNGEN, nebeneinander.
  // BEIDE Reihen stehen da, und die Fixture macht sie unterscheidbar.
  ok(/153/.test(aus) && /161/.test(aus),
     "quellen: die Zahlen beider Stellungen stehen nicht nebeneinander");
  ok(!/\b153\b|\b138\b|\b136\b/.test(H.source().replace(/\/\*[\s\S]*?\*\//g, "")
       .split("rQuellen(")[1].split("_setCurveSource")[0]),
     "quellen: eine Vergleichszahl steht als Literal im Quelltext");
  // DIE SPALTEN TAUSCHEN MIT DER STELLUNG. Die erste Fassung dieser Zeile hatte
  // ein `|| /161/.test(aus)` - ein ODER, das sie unbedingt wahr machte, und die
  // Mutation lief mit 0 Fehlern durch (M56). Eine Prüfung mit einem Ausweg ist
  // keine.
  const ersteZeile = (html) => {
    const t = /<td>1 h geplante Dauer<\/td>\s*<td class="tn">([^<]*)<\/td>\s*<td class="tn">([^<]*)</
      .exec(html.replace(/\s+/g, " "));
    return t ? [t[1].trim(), t[2].trim()] : null;   // Regex null-geprüft (§9)
  };
  const zAus = ersteZeile(aus), zAn = ersteZeile(an);
  ok(zAus !== null && zAn !== null,
     "quellen: die Zahlenzeile ist nicht ablesbar");
  ok(zAus && zAn && zAus[0] === zAn[1] && zAus[1] === zAn[0],
     `quellen: die Spalten tauschen nicht mit der Stellung (${JSON.stringify([zAus, zAn])})`);
  // Trefferzusicherung: die beiden Zahlen sind ÜBERHAUPT verschieden.
  ok(zAus && zAus[0] !== zAus[1],
     "quellen Fixture-Beweis: beide Spalten tragen dieselbe Zahl - der Tausch wäre unsichtbar");
  ok(/LESERICHTUNGSSATZ AUS DER PAYLOAD/.test(aus),
     "quellen: der Satz zur Leserichtung steht nicht da oder kommt aus dem Frontend");

  // WIE VIELE FAHRTEN DIE UMSTELLUNG TRÄGT, je Familie — und wo es nicht reicht.
  ok(/Tempo: 1 von 3 — noch 2/.test(aus),
     "quellen: die Familie sagt nicht, wie viele Fahrten ihr fehlen");
  // Trefferzusicherung: die Fixture trägt eine markierte OHNE Messung, sonst
  // prüft die Zählung nur, dass überhaupt gezählt wird.
  ok(marken.marks.some((m) => m.marks.tempo && !Object.keys(m.measure).length),
     "quellen Fixture-Beweis: keine markierte, ungemessene Fahrt in der Fixture");
  ok(/1 markierte Grundlagen-Fahrt|1 markierte Grundlagen-Fahrten/.test(aus),
     "quellen: die Grundlage sagt nicht, worauf die Umstellung ruht");
}

/* ── 0.64.0: die Kachel, umgekehrt gefragt ──────────────────────────────────
   Nicht "wo liegt meine Schwelle", sondern "bei wieviel Watt bleibe ich über
   alpha 1,0". Geprüft wird, was die Kachel behauptet: dass die Zahl aus der
   Payload kommt, dass die Formelzeile sie ergibt, dass unter der
   Mindestbelegung KEINE Spanne dasteht, dass sichtbar wenig und aufgeklappt
   viel steht - und dass ausgeschaltet alles bleibt, wie es war. */
{
  const q = new M.Panel();
  q._nowIso = F.TODAY;
  const an = F.fatigue({ v2: F.fatigueV2Block({ on: true }) });
  const rv = an.v2.reversal;
  const html = String(q.rFatigueV2(an, an.v2));
  clean(html, "umkehrung");

  // ── DER SCHALTER AUS: bitgenau wie 0.63.3.
  const aus = String(new M.Panel().rFatigue(F.fatigue({ v2: F.fatigueV2Block({ on: false }) })));
  const ohne = String(new M.Panel().rFatigue(F.fatigue({ v2: undefined })));
  ok(aus === ohne, "v2 aus: die Kachel ist nicht bitgenau die von 0.63.3");
  const mitAn = String(new M.Panel().rFatigue(an));
  ok(mitAn !== aus, "v2 Fixture-Beweis: an und aus liefern dieselbe Kachel");

  // ── SICHTBAR WENIG. Alles außer den sieben Stücken steckt in <details>.
  const SICHTBAR = ['class="state"', 'class="ldl"', 'class="tn ldv"', 'data-v2="tol"',
                    'data-v2="strip"', 'data-v2="satz"', 'class="trend"'];
  let pos = -1, gut = true, wo = "";
  for (const stueck of SICHTBAR) {
    const at = html.indexOf(stueck);
    if (at < 0 || at < pos) { gut = false; wo = stueck; break; }
    pos = at;
  }
  ok(gut, `Umkehrung Reihenfolge: "${wo}" steht nicht an seinem Platz`);
  const ersteKlappe = html.indexOf("<details");
  ok(ersteKlappe > html.indexOf('class="trend"'),
     "Umkehrung: ein Aufklappteil steht VOR dem Bild - sichtbar soll wenig sein");
  const KLAPPEN = ["Was die Zahl bedeutet", "Im Vergleich zur Studienform",
                   "Welche Fahrten zählen", "Wattzahlen aus anderen Messungen", "Rechenweg"];
  let kp = ersteKlappe, kgut = true, kwo = "";
  for (const k of KLAPPEN) {
    const at = html.indexOf(k);
    if (at < 0 || at < kp) { kgut = false; kwo = k; break; }
    kp = at;
  }
  ok(kgut, `Umkehrung Aufklappteile: "${kwo}" fehlt oder steht falsch`);
  ok((html.match(/<details class="more"/g) || []).length === KLAPPEN.length,
     `Umkehrung: ${(html.match(/<details class="more"/g) || []).length} Aufklappteile statt fünf`);

  // ── DIE ZAHLEN KOMMEN AUS DER PAYLOAD, reaktiv geprüft.
  const anders = F.fatigueV2Block({
    reversal: { ...rv, alpha_floor: 0.9, floor_step_watts: 12.5, slope_per_hour: -7.7,
      bridges: { ramp: 80.0, ladder: 100.0, mid: 90.0, spread: 20.0, sources: ["x"] },
      plan: [{ hours: 1, watts: 201.4, load_w: 150.0, alpha: 1.5, n: 9, form_watts: 201.4,
               observed: true, lower: null,
               band: { half: 12.3, from_spread: 12.0, from_bridge: 2.6, n: 9 } }],
      covered_until_hours: 1 } });
  const zweit = String(new M.Panel().rFatigueV2(F.fatigue({ v2: anders }), anders));
  ok(/>201</.test(zweit) && !/>173</.test(zweit),
     "Umkehrung: die Zahl steht fest im Template statt in der Payload");
  ok(/90,0 W je alpha/.test(zweit) && !/101,2 W je alpha/.test(zweit),
     "Umkehrung: die Umrechnung steht fest im Template");
  // Die Grenze muss auch IN DER FORMELZEILE aus der Payload kommen - dort ist
  // sie ein Operand, und ein Literal dort faellt keinem Zahlen-Waechter auf.
  ok(/−\s*0,9\)/.test(zweit) && !/−\s*1,0\)/.test(zweit),
     "Umkehrung: die Grenze steht fest in der Formelzeile statt in der Payload");
  ok(/alpha 0,9/.test(zweit), "Umkehrung: die Grenze fehlt im Satz");

  // ── DER ZEIGER: sechs Felder folgen mit.
  const felder = {};
  const mach = (n) => ({ set innerHTML(v) { felder[n] = v; }, get innerHTML() { return felder[n] || ""; },
                         set textContent(v) { felder[n] = v; }, get textContent() { return felder[n] || ""; },
                         style: {} });
  const box = { querySelector: (sel) => {
    if (/ldl/.test(sel)) return mach("ldl");
    if (/ldv/.test(sel)) return mach("ldv");
    if (/ldn/.test(sel)) return null;
    const m = /data-v2="(\w+)"/.exec(sel);
    return m ? mach(m[1]) : null;
  } };
  let sx = "", sv = "";
  const strip = { querySelector: (sel) => (/rdox/.test(sel)
    ? { set textContent(v) { sx = v; } } : { set innerHTML(v) { sv = v; } }) };
  const qz = new M.Panel(); qz._nowIso = F.TODAY;
  qz.rFatigueV2(an, an.v2);
  qz.shadowRoot.querySelector = (sel) => (/data-rdo="fatv2"/.test(sel) ? strip
    : (/data-lead="fatv2"/.test(sel) ? box : null));
  ok(qz._grp.fatv2.pts.length === rv.plan.length,
     `Umkehrung Zeiger: ${qz._grp.fatv2.pts.length} Rasterpunkte gegen ${rv.plan.length}`);
  // ── DER AUFBAU OHNE ZEIGERBEWEGUNG (0.67.1). Was der Kopf zeigt (Stunde 1,
  //    die bestbelegte), muessen Zustandszeile, Toleranz, Streifen, Satz,
  //    Rechenweg UND die Zeigerleiste zeigen - so, wie das Panel es nach dem
  //    Rendern und beim Verlassen des Zeigers selbst aufruft
  //    (_fillReadout(name, null)). Die Hover-Pruefung darunter deckte nur den
  //    Zustand NACH einer Bewegung ab; auf dem Handy bewegt niemand den Zeiger.
  qz._fillReadout("fatv2", null);
  const aufbau = { ...felder, rdox: sx, rdov: sv };
  ok(/1,00 h/.test(aufbau.ldl), `Aufbau: der Kopf steht nicht auf Stunde 1 (${aufbau.ldl})`);
  ok(/1,00 h/.test(aufbau.rdox), `Aufbau: die Zeigerleiste steht nicht auf der Stunde des Kopfs (${aufbau.rdox})`);
  ok(new RegExp(`${M.fmt(rv.plan[0].watts)}`).test(aufbau.rdov) && !new RegExp(`${M.fmt(rv.plan[rv.plan.length - 1].watts)}`).test(aufbau.rdov),
     `Aufbau: die Zeigerleiste traegt die Zahlen der letzten Stunde (${aufbau.rdov.replace(/<[^>]+>/g, " ")})`);
  ok(!aufbau.tol.includes(an.v2.estimate_words.state) && /±/.test(aufbau.tol),
     `Aufbau: die Zustandszeile gehoert zu einer fortgeschriebenen Stunde (${aufbau.tol})`);
  ok(aufbau.formel.startsWith("1 h ="), `Aufbau: der Rechenweg gehoert nicht zu Stunde 1 (${aufbau.formel.slice(0, 40)})`);
  ok(/1,00 h|Stunde 1|1 h/.test(aufbau.satz) || /gehalten haben/.test(aufbau.satz),
     `Aufbau: der Klartextsatz gehoert zu einer fortgeschriebenen Stunde (${aufbau.satz.slice(0, 60)})`);
  qz._fillReadout("fatv2", 0);
  const eins = { ...felder };
  qz._fillReadout("fatv2", 1);
  const zwei = { ...felder };
  for (const feld of ["ldl", "ldv", "tol", "strip", "satz", "formel"]) {
    ok(eins[feld] !== zwei[feld] && zwei[feld],
       `Umkehrung Zeiger: "${feld}" ändert sich nicht mit`);
  }
  // DIE FORMELZEILE WIRD NACHGERECHNET, nicht abgesucht.
  const p2 = rv.plan[1];
  const zahl = (t) => parseFloat(String(t).replace(/\./g, "").replace(",", "."));
  const teile = /=\s*([\d.,]+)\s*W\s*gehalten\s*\+\s*\(([\d.,]+)\s*−\s*([\d.,]+)\)\s*·\s*<b>([\d.,]+)\s*W<\/b>\s*=\s*<b>([\d.,]+)\s*W<\/b>/
    .exec(zwei.formel.replace(/\s+/g, " "));
  ok(teile != null, `Umkehrung Formel: die Zeile ist nicht lesbar (${zwei.formel})`);
  if (teile) {
    const gerechnet = zahl(teile[1]) + (zahl(teile[2]) - zahl(teile[3])) * zahl(teile[4]);
    ok(Math.abs(gerechnet - zahl(teile[5])) < 0.6,
       `Umkehrung Formel: ${teile[1]} + (${teile[2]} − ${teile[3]}) · ${teile[4]} = `
       + `${gerechnet.toFixed(1)}, die Zeile behauptet ${teile[5]}`);
    ok(Math.abs(zahl(teile[5]) - p2.watts) < 0.6,
       `Umkehrung Formel: die Zeile endet auf ${teile[5]}, oben steht ${M.fmt(p2.watts)}`);
  } else { ok(false, "x"); ok(false, "y"); }
  ok(Math.abs((p2.load_w + (p2.alpha - rv.alpha_floor) * rv.bridges.mid) - p2.watts) < 0.6,
     "Umkehrung Fixture-Beweis: die Kette der Fixture ist nicht nachrechenbar");

  // ── UNTER DER MINDESTBELEGUNG KEINE SPANNE.
  const iOhne = rv.plan.findIndex((r) => r.observed && !r.band);
  ok(iOhne >= 0 && rv.plan[iOhne].n < rv.min_rides_for_band,
     "Umkehrung Fixture-Beweis: keine Stunde unter der Mindestbelegung");
  qz._fillReadout("fatv2", iOhne);
  ok(felder.strip === "", `Umkehrung: der Streifen steht noch da ("${felder.strip}")`);
  ok(!/±/.test(felder.tol) && /keine Spanne/.test(felder.tol),
     `Umkehrung: die Toleranzzeile behauptet eine Spanne (${felder.tol})`);
  ok(felder.ldv === M.fmt(rv.plan[iOhne].watts),
     "Umkehrung: ohne Spanne fehlt auch die Zahl - das ist zuviel");
  qz._fillReadout("fatv2", 0);
  ok(felder.strip !== "" && /±/.test(felder.tol),
     "Umkehrung Gegenprobe: mit genug Fahrten bleibt die Spanne leer");
  // DIE QUOTE STEHT NUR DA, WO SIE NACHPRUEFBAR IST. Stunde 1 traegt 17
  // Fahrten und sagt sie an; Stunde 3 traegt vier und sagt, wie das Band
  // gebaut ist, statt eine Quote zu versprechen, die niemand nachzaehlen kann.
  ok(felder.tol.includes(an.v2.reversal_words.band_share),
     `Umkehrung Quote: bei 17 Fahrten fehlt die Quote (${felder.tol})`);
  const iQuote = rv.plan.findIndex((r) => r.band && !r.band.quote_shown);
  ok(iQuote >= 0, "Umkehrung Fixture-Beweis: keine Stunde mit Band ohne Quote");
  qz._fillReadout("fatv2", iQuote);
  ok(!felder.tol.includes(an.v2.reversal_words.band_share)
     && /t-Band über/.test(felder.tol),
     `Umkehrung Quote: bei wenigen Fahrten steht sie trotzdem da (${felder.tol})`);
  ok(/±/.test(felder.tol), "Umkehrung Quote: ohne Quote fehlt auch die Spanne");

  // ── JENSEITS DER MESSUNG.
  const iEst = rv.plan.findIndex((r) => !r.observed);
  ok(iEst > 0, "Umkehrung Fixture-Beweis: keine fortgeschriebene Stunde");
  qz._fillReadout("fatv2", iEst);
  ok(felder.tol.includes(an.v2.estimate_words.state) && !/±/.test(felder.tol),
     `Umkehrung fortgeschrieben: keine Zustandszeile (${felder.tol})`);
  ok(felder.strip === "", "Umkehrung fortgeschrieben: ein Streifen ohne Band");
  ok(felder.formel.includes(M.fmt(rv.slope_per_hour, 1))
     && felder.formel.includes(M.fmt(rv.plan[iEst].form_watts)),
     `Umkehrung fortgeschrieben: Steigung oder Studienform fehlen (${felder.formel})`);

  // ── DIE FAHRTENLISTE und die Setzungen.
  const traegt = rv.rides.filter((r) => r.carries).length;
  ok(new RegExp(`${traegt} Fahrten tragen den`).test(html.replace(/\s+/g, " ")),
     "Umkehrung: die Zahl der tragenden Fahrten stammt nicht aus der Liste");
  ok(html.includes("draußen") && html.includes("Rolle"),
     "Umkehrung: die Umgebung fehlt in der Fahrtenliste");
  const setz = (/<p class="setz">[\s\S]*?<\/p>/.exec(html) || [""])[0];
  let getroffen = 0;
  for (const satz of an.v2.settings) if (setz.includes(satz)) getroffen++;
  ok(getroffen === an.v2.settings.length,
     `Umkehrung Setzungen: ${getroffen} von ${an.v2.settings.length} stehen wörtlich da`);
  ok(html.includes(`${M.fmt(rv.floor_step, 1)} alpha ≈ ${M.fmt(rv.floor_step_watts)} W`),
     "Umkehrung: der Ausschlag der Grenze steht nicht auf der Kachel");

  // ── 0.67.0 · DAS UMRECHNUNGS-PAKET (rot an 0.66.3) ─────────────────────
  // U1/U2: der Rechenweg zeigt die Leiter als GEGENPROBE, verwendet den
  // Stufentest, und ein fehlender Stufentest laesst die Kachel den Verlauf in
  // alpha zeigen - mit dem Grund aus der Payload, nicht mit einer leeren Kachel.
  {
    const rw = an.v2.reversal_words || {};
    ok(/Gegenprobe/.test(html), "Umrechnung: die Leiter steht nicht als Gegenprobe im Rechenweg");
    ok(!/verwendet\s+<\/?b?>?\s*111/.test(html) && /verwendet[^<]*90,6/.test(html.replace(/<[^>]+>/g, "")),
       "Umrechnung: verwendet wird nicht der Stufentest (90,6)");
    ok(html.includes(rw.state || "SETZUNG") && !/aus gemessenem alpha/.test(html),
       "Umrechnung: die Kachel nennt die Umrechnung noch \"gemessen\"");
    ok(html.includes(rw.literature || "LITERATURSATZ"), "Umrechnung: der Literatursatz fehlt im Rechenweg");
    ok(html.includes(rw.ramp_note || rv.bridges.ramp_note || "RAMPENSATZ"), "Umrechnung: Datum/Rampe des Stufentests fehlen");
    // ohne Stufentest: Verlauf in alpha, Grund sichtbar, keine Wattzahl
    const ohneRampe = F.fatigueV2Block({ reversal: { ...rv,
      bridges: { ramp: null, ladder: 111.7, mid: null, spread: null, sources: [], missing: "GRUND: KEIN STUFENTEST",
                 ladder_note: rv.bridges.ladder_note, ramp_note: null, ramp_date: null },
      plan: rv.plan.filter((r) => r.observed).map((r) => ({ ...r, watts: null, band: null, form_watts: null })),
      slope_per_hour: null, floor_step_watts: null } });
    const oHtml = String(new M.Panel().rFatigueV2(F.fatigue({ v2: ohneRampe }), ohneRampe));
    clean(oHtml, "umkehrung ohne stufentest");
    ok(/GRUND: KEIN STUFENTEST/.test(oHtml), "Umrechnung ohne Stufentest: der Grund aus der Payload fehlt");
    ok(!/>170</.test(oHtml) && !/>17[0-9] W/.test(oHtml), "Umrechnung ohne Stufentest: es steht trotzdem eine Wattzahl da");
    ok(/alpha/.test(oHtml) && /1,3/.test(oHtml), "Umrechnung ohne Stufentest: der Verlauf in alpha fehlt");
  }
  // U5 Quellen-Reiter: unter dem Blockschalter steht, dass Tempo weiter
  // gemessen wird, aber nichts traegt - der Satz aus der Payload.
  {
    const qq = new M.Panel(); qq._smarks = { marks: [], families: ["vo2max", "sweetspot", "tempo"], stale_reason: {},
      min_for_source: 3, corridor_state: {}, corridors: {} };
    const bQ = F.blocks(); bQ.hidden_families = ["tempo"]; bQ.hidden_note = "TEMPO-SATZ AUS DEM MODUL.";
    const qHtml = String(qq.rQuellen(F.fatigue(), bQ));
    ok(/TEMPO-SATZ AUS DEM MODUL/.test(qHtml), "Quellen: der Satz zu Tempo ohne Kachel fehlt");
  }
  // U5: die Tempo-Kachel ist aus - die Familie bleibt in der Payload.
  {
    const bT = F.blocks();
    const tPt = { date: "2026-09-13", n_blocks: 2, block_alphas: [1.346, 0.868], block_watts: [172, 169],
                  block_watts_each: [172, 169], block_hr: [150, 152], block_minutes: [20, 20], activity_id: "t13",
                  median_watts: 170, median_alpha: 1.107, median_hr: 151, first_watts: 172, first_alpha: 1.346 };
    bT.families.tempo = { corridor: [0.75, 1.0], sessions: 1, spread: 0, trend: false, source_ok: false,
      points: [tPt], latest: tPt, hr_window: null, from: "a", to: "b", suggested_watts: null, step_pct: null };
    bT.steering = { ...bT.steering, tempo: { watts: null, no_target: true, note: null, rows: [], n_units: 1, band: null } };
    bT.hidden_families = ["tempo"]; bT.hidden_note = "TEMPO-SATZ AUS DEM MODUL.";
    const bHtml = String(new M.Panel().rBlocks(bT));
    clean(bHtml, "blocks ohne tempo-kachel");
    ok(!/Tempo/.test(bHtml.replace(/<!--[\s\S]*?-->/g, "")), "Tempo: die Kachel wird noch gezeichnet");
    ok(/SweetSpot/.test(bHtml) && /VO2max/.test(bHtml), "Tempo aus: die anderen Kacheln fehlen");
  }

  // ── DER LEERFALL.
  const leer = F.fatigueV2Block({ reversal: { ...rv, plan: [] } });
  const leerHtml = String(new M.Panel().rFatigueV2(F.fatigue({ v2: leer }), leer));
  ok(!/data-v2="tol"/.test(leerHtml) && /Ablesestelle/.test(leerHtml),
     "Umkehrung leer: die Kachel steht leer da, statt zu sagen, was fehlt");
}

/* ── 0.70.0 · Trainer-Reiter nach der Skizze (Fassung 2) ─────────────────
   A: Reihenfolge der Seite · B: Umzuege · C1–C4: Fehler. Jede Pruefung ist
   vor dem Bau rot gelaufen (Bericht 0.70.0). */
{
  const T = new M.Panel();
  T._nowIso = F.TODAY;
  const z = (h) => String(h).replace(/\s+/g, " ");
  const vor = (h, a, b) => h.indexOf(a) >= 0 && h.indexOf(b) >= 0 && h.indexOf(a) < h.indexOf(b);
  const faltung = (h, id) => {
    // der Inhalt EINES Aufklappers mit data-keep="id" (verschachtelte details mitgezaehlt)
    const at = h.indexOf(`data-keep="${id}"`);
    if (at < 0) return null;
    const start = h.lastIndexOf("<details", at);
    let tiefe = 0, i = start;
    const re = /<details\b|<\/details>/g;
    re.lastIndex = start;
    let m;
    while ((m = re.exec(h))) {
      tiefe += m[0] === "</details>" ? -1 : 1;
      if (tiefe === 0) { i = m.index + m[0].length; break; }
    }
    return h.slice(start, i);
  };
  const zu = (h, id) => { const f = faltung(h, id); return f != null && !/^<details[^>]*\sopen[\s>]/.test(f); };
  const rt = { tests: [{ activity_id: "1", date: "2026-09-16" }],
    sources: ["QUELLE EINS (2021)", "QUELLE ZWEI (2024)"],
    latest: { date: "2026-09-16", result: {
      hrvt1: { alpha: 0.75, watts: 213, hr: 160 }, hrvt2: { alpha: 0.5, watts: 233, hr: 172 },
      hrvt1_pers: { alpha: 0.92, watts: 183, hr: 150 }, max_alpha_start: 1.34, pers_alpha: 0.92,
      reached_anaerobic: true, segment: { points: 900, r2: 0.97 } } } };
  T._workouts = F.workouts("voll");
  T._rtests = rt;
  T._goal = F.goal();
  T._blocks = F.blocks({ steering_on: true });
  T._fatigue = F.fatigue();
  T._coach = F.coach("ready");

  // A1 · Kopf: EINE schmale Zeile statt zweier Kaesten
  const kopf = z(T.rGoal(T._goal));
  ok((kopf.match(/class="goalline"/g) || []).length === 1, "A1: der Kopf ist nicht EINE Zeile (goalline)");
  ok(!/class="goalbar"/.test(kopf) && !/class="gtile"/.test(kopf), "A1: die zwei Kaesten stehen noch da");
  ok(vor(kopf, "Lange Fahrten durchstehen", "4 Tage pro Woche"), "A1: Ziel · Zeit nicht in dieser Reihenfolge");

  // A2 · Zustand: eine Zeile, Balken und Begruendungen zugeklappt
  const tr = z(T.rTrainer(T._coach, F.readiness()));
  clean(tr, "0.70.0 trainer");
  ok(/class="card tline"/.test(tr), "A2: die Zustandszeile fehlt");
  const zeile = tr.slice(tr.indexOf('class="card tline"'), tr.indexOf('data-keep="trainer:zustand"'));
  ok(/im Normalbereich/.test(zeile) && /harter Reiz möglich/.test(zeile), "A2: Wort und Satz stehen nicht in der Zeile");
  const zBody = faltung(tr, "trainer:zustand") || "";
  // 0.71.0 UMGESTELLT: offen stehen jetzt die Mini-Streifen (Skizze 0.71.0, 1);
  // der GROSSE zplot mit Skala bleibt nur im Aufklapper.
  ok(/class="zplot"/.test(zBody) && !/class="zplot"/.test(tr.replace(zBody, "")), "A2: die grossen Balken stehen nicht (nur) im Aufklapper");
  ok(zu(tr, "trainer:zustand"), "A2: der Zustands-Aufklapper ist nicht zugeklappt");
  ok(/Javaloyes|Normalband/.test(zBody), "A2: die Begruendung steht nicht im Aufklapper");

  // A3 · Empfehlung: Art + passende Dauer aus guard(), "für morgen" statt des Archivsatzes
  const gw = F.workouts("voll");
  gw.workouts[1] = { ...gw.workouts[1], fits_budget: false, stage: F.stageOf("ok", false, false),
    guard: { over: true, load: 175, ceiling: 68, hours_fit: 1.5, text: "Geländer: Last 175 über der Obergrenze 68 — die Art bleibt, die Menge nicht. Bis ~1,5 h passt sie unter die Obergrenze." } };
  gw.workouts[0] = { ...gw.workouts[0], stage: F.stageOf("maybe", true, false) };
  T._workouts = gw;
  const lead = z(T.rTrainer(T._coach, F.readiness()));
  const lk = lead.slice(lead.indexOf('class="leadrec"'), lead.indexOf('data-keep="fam:'));
  ok(/Lange Fahrt 3,5 h mit Endblock — heute ~1,5 h/.test(lk), "A3: die Empfehlung nennt nicht Art + passende Dauer");
  const morgen = z(T.rTrainer({ ...T._coach, trained_today: true }, F.readiness()));
  ok(!/Heute liegt schon eine\s+Einheit im Archiv/.test(morgen), "A3: der Archivsatz steht noch da");
  const mk2 = morgen.slice(morgen.indexOf('class="leadrec"'), morgen.indexOf('data-keep="fam:'));
  ok(/class="leadsub"[^>]*>[^<]*für morgen/.test(mk2), "A3: die Unterzeile 'für morgen' fehlt in der Empfehlung");
  T._workouts = F.workouts("voll");

  // A4 · Drei Familien, je ein Aufklapper; "Alle Einheiten für heute" ist weg
  const fam = z(T.rTrainer(T._coach, F.readiness()));
  ok(!/Alle Einheiten für/.test(fam), "A4: der Block 'Alle Einheiten für heute' steht noch da");
  const ids = (fam.match(/data-keep="fam:[a-z0-9]+"/g) || []).map((x) => x.slice(15, -1));
  ok(JSON.stringify(ids) === JSON.stringify(["grundlage", "schwelle", "vo2max"]),
     `A4: nicht genau drei Familien in der Reihenfolge der Skizze (${ids.join(",")})`);
  const fg = faltung(fam, "fam:grundlage") || "", fs = faltung(fam, "fam:schwelle") || "", fv = faltung(fam, "fam:vo2max") || "";
  ok(/Grundlage 90 min/.test(fg) && /Lange Fahrt 3,5 h/.test(fg) && /Regeneration 40 min/.test(fg), "A4: Grundlage traegt nicht Grundlage · Lange · Regeneration");
  ok(/SweetSpot 2×20/.test(fs) && /Tempo 2×20/.test(fs) && /Schwelle 4×10/.test(fs), "A4: SweetSpot & Schwelle unvollstaendig");
  ok(/VO2max 4×4/.test(fv) && /30\/30|5×4/.test(fv), "A4: VO2max nennt die Varianten nicht");
  ok(!/data-id="ramp_test"/.test(fg + fs + fv), "A4: der Stufentest steht in einer Familie");
  for (const [n, f] of [["grundlage", fg], ["schwelle", fs], ["vo2max", fv]]) {
    ok(zu(fam, "fam:" + n), `A4: ${n} ist nicht zugeklappt`);
    const sum = f.slice(0, f.indexOf("</summary>"));
    ok(/class="bdg"/.test(sum), `A4: ${n}: kein Etikett in der zugeklappten Zeile`);
    ok(/\d+ W/.test(sum) && /(Umkehrung|deine Vorgabe|FTP|Blockmessung|Stufentest)/.test(sum), `A4: ${n}: Watt ohne Kurzherkunft`);
    ok(/class="fgvar"/.test(sum) && /class="fguse"/.test(sum), `A4: ${n}: empfohlene Variante oder Nutzen fehlt`);
    ok(!/class="wocard/.test(sum), `A4: ${n}: Karten in der zugeklappten Zeile`);
  }
  ok(/Kurve im Hintergrund/.test(fg) && /Kachel im Hintergrund/.test(fv), "A4: der Verweis auf Kurve/Kachel im Hintergrund fehlt");
  // gekuerzte Karte: kein Familienname, kein "Was das bringt" offen; die Aufklapper bleiben
  const karte = fs.slice(fs.indexOf('class="wocard'));
  ok(!/class="wofam"/.test(karte) && !/class="effect"/.test(karte.split("Aufbau, Beleg und Rechenweg")[0]),
     "A4: die Variantenkarte ist nicht gekuerzt");
  ok(/Aufbau, Beleg und Rechenweg/.test(karte), "A4: der Aufklapper 'Aufbau, Beleg und Rechenweg' fehlt");

  // A5 · Test, eine Zeile: Stufentest, aufklappbar mit Karte und drei Schwellen
  const test = z(T.rRampTest(rt));
  ok(zu(test, "trainer:test"), "A5: der Stufentest ist kein zugeklappter Aufklapper");
  const tsum = test.slice(0, test.indexOf("</summary>"));
  ok(/Stufentest/.test(tsum) && /alle paar Monate/.test(tsum) && /zuletzt/.test(tsum), "A5: die Zeile nennt nicht Stufentest · alle paar Monate · zuletzt");
  ok(/data-id="ramp_test"/.test(test), "A5: die Stufentest-Karte steht nicht im Aufklapper");
  for (const w of [213, 233, 183]) ok(test.includes(String(w)), `A5: die Schwelle ${w} W fehlt`);
  const rw = test.slice(test.indexOf("Der Rechenweg"));
  ok(/umstritten/.test(rw) && !/umstritten/.test(test.slice(0, test.indexOf("Der Rechenweg"))), "A5: der Text zur dritten Zahl steht nicht im Rechenweg");

  // A6 · Wochen: zugeklappt nur DIESE Woche, W2–W8 im Aufklapper, Erklaertexte im Rechenweg
  const wo = z(T.rPlanWeeks(F.goal("knapp"), (T._coach.durability || {}).progression));
  const w2 = faltung(wo, "trainer:weeks") || "";
  ok(/W1/.test(wo.replace(w2, "")) && !/W2/.test(wo.replace(w2, "")), "A6: ausserhalb des Aufklappers steht mehr als diese Woche");
  ok(/W2/.test(w2) && zu(wo, "trainer:weeks"), "A6: W2 ff. stehen nicht im zugeklappten Aufklapper");
  const wr = faltung(wo, "trainer:weeksrw") || "";
  ok(/bewusste Ausnahme/.test(wr) && /Konvention/.test(wr), "A6: Budget-Satz und Konvention stehen nicht im Rechenweg");
  ok(!/bewusste Ausnahme/.test(wo.replace(wr, "")), "A6: der Budget-Satz steht noch offen");

  // A7 · Hintergrund ganz unten, zu: Anker, Kurve, Leistung je Block
  const hg = z(typeof T.rHintergrund === "function" ? T.rHintergrund(T._coach) : "");
  ok(zu(hg, "trainer:hintergrund"), "A7: der Hintergrund ist nicht zugeklappt");
  ok(/Deine gemessenen Anker/.test(hg) && /Wie lange trägt die Grundlage/.test(hg) && /Leistung je Block/.test(hg),
     "A7: Anker, Kurve oder Blockkachel fehlen im Hintergrund");
  ok(!/Wie stark entkoppelt/.test(hg), "A7: die Entkopplung steht noch im Trainer");
  // die ganze Seite in der Reihenfolge der Skizze
  T._tab = "trainer"; T._view = { innerHTML: "" }; T._rd = F.readiness();
  T._render();
  const seite = z(T._view.innerHTML);
  const folge = ['class="goalline"', 'class="card tline"', 'class="leadrec"', 'data-keep="fam:grundlage"',
                 'data-keep="trainer:test"', "Die nächsten Wochen", 'data-keep="trainer:hintergrund"'];
  ok(folge.every((x, i) => i === 0 || vor(seite, folge[i - 1], x)), "A7: die Seite steht nicht in der Reihenfolge A1–A7");

  // B · Umzuege: nichts davon im Trainer, alles im Ziel-Reiter
  for (const [was, re] of [["Kalendersatz", /einzige Schreibzugriff/], ["Entkopplung", /Wie stark entkoppelt/],
                           ["Wird es besser", /Wird es besser/], ["5 Arbeiten", /Worauf das beruht/],
                           ["56 W", /offene Frage/], ["Empfehlungsgrenze", /Worauf diese Empfehlung beruht/],
                           ["vier Stufen", /Die vier Stufen/], ["Wer entscheidet", /Wer hier entscheidet/]]) {
    ok(!re.test(seite.replace(/title="[^"]*"/g, "")), `B: ${was} steht noch im Trainer`);
  }
  ok(/title="[^"]*Intervals-Kalender[^"]*einzige[^"]*"/.test(seite), "B: der Kalendersatz ist nicht Tooltip am Kalenderknopf");
  const knoepfe = seite.match(/<button[^>]*data-act="plan"[^>]*>/g) || [];
  ok(knoepfe.length >= 4 && knoepfe.every((k) => /title="[^"]*einzige Schreibzugriff/.test(k)),
     `B: nicht jeder Kalenderknopf traegt den Tooltip (${knoepfe.filter((k) => !/einzige/.test(k)).length} ohne)`);
  ok(/class="bdg"[^>]*title="[^"]+"/.test(seite), "B: das Etikett traegt keinen Tooltip");
  T._pmc = F.pmc(F.days()); T._tab = "fitness"; T._render();
  const fit = z(T._view.innerHTML);
  ok(/Wie stark entkoppelt/.test(fit) && /Wird es besser/.test(fit) && /Was das ausbaut/.test(fit), "B: die Entkopplung ist nicht im Fitness-Reiter");
  T._smarks = { marks: [], families: ["vo2max", "sweetspot", "tempo"], stale_reason: {}, min_for_source: 3, corridor_state: {}, corridors: {} };
  T._tab = "quellen"; T._render();
  const qu = z(T._view.innerHTML);
  ok(/Worauf das beruht/.test(qu) && /QUELLE EINS/.test(qu), "B: die 5 Arbeiten stehen nicht in Quellen");
  ok(/Worauf diese Empfehlung beruht/.test(qu), "B: 'Worauf diese Empfehlung beruht' steht nicht in Quellen");
  ok(/Die vier Stufen/.test(qu) && /Erholung gilt als geboten/.test(qu), "B: Stufen-Legende und Erholungsregel stehen nicht in Quellen");
  ok(/Wer hier entscheidet/.test(qu), "B: 'Wer hier entscheidet' steht nicht in Quellen");
  ok(!/offene Frage/.test(qu + fit) && typeof T.rRampGap !== "function", "B: die 56-W-Frage ist nicht ersatzlos gestrichen");

  // C1 · Stufentest-Karte: eigener Text, nicht der Steuerungszweig mit Strichen
  const rk = z(faltung(test, "trainer:test"));
  ok(!/Startwert\s+–\s+W/.test(rk) && !/aus\s+0\s+Einheiten/.test(rk), "C1: die Stufentest-Karte traegt den leeren Steuerungstext");
  ok(/Start 142 W/.test(rk) && /Ende 300 W/.test(rk) && /Umkehrung/.test(rk) && /VO2max-Vorgabe/.test(rk),
     "C1: die Stufentest-Karte nennt Start und Ende mit ihrer Herkunft nicht");
  // Gegenprobe: eine echte Steuerungskarte behaelt ihren Text
  const echt = { ...F.workouts().workouts[4], watt_source: "steering",
                 steering_source: { watts: 250, anchor_w: 250, anchor_date: "2026-09-17", moves: 0, n_units: 6 } };
  ok(/Startwert 250 W/.test(z(T._sourceText(echt))), "C1 Gegenprobe: die Steuerungskarte verliert ihren Text");

  // C2 · Blockkachel: die Steuerung zaehlt ab Block 2
  // der Livefall 25.09.: Block 1 bei 0,85, gezaehlt ab Block 2 (Median 0,347)
  const live = (an) => {
    const b = F.blocks({ steering_on: an });
    const l = { ...b.families.vo2max.latest, n_blocks: 4, block_alphas: [0.85, 0.63, 0.35, 0.30],
                median_alpha: 0.49, alpha_span: 0.55 };
    b.families.vo2max = { ...b.families.vo2max, latest: l, points: [...b.families.vo2max.points.slice(0, -1), l] };
    const rows = b.steering.vo2max.rows.slice();
    rows[rows.length - 1] = { ...rows[rows.length - 1], date: l.date, alpha: 0.347 };
    b.steering = { ...b.steering, vo2max: { ...b.steering.vo2max, rows } };
    return b;
  };
  const bk = z(T.rBlocks(live(true)));
  ok(!/ruht auf <b>4 Blöcken<\/b>/.test(bk) && !/Median 0,490/.test(bk), "C2: die Kachel zaehlt Block 1 zur Steuerung");
  ok(/markiert, nicht gezählt \(Anlauf, Rogers\)/.test(bk) && /0,85/.test(bk), "C2: Block 1 steht nicht als 'markiert, nicht gezählt' daneben");
  ok(/ruht auf <b>3 Blöcken<\/b>/.test(bk) && /Median 0,347/.test(bk), "C2: die gezaehlten Bloecke und der Median der Steuerung fehlen");
  // Gegenprobe: Schalter aus - die alte Kette zaehlt alle Bloecke, der Satz bleibt
  const vo = { n_blocks: 4 };
  const bkAus = z(T.rBlocks(live(false)));
  ok(new RegExp(`ruht auf <b>${vo.n_blocks} Blöcken</b>`).test(bkAus), "C2 Gegenprobe: ohne Steuerung verschwindet der alte Satz");

  // C3 · "steuert noch keine Vorgabe" ist seit 0.68.0 falsch
  ok(!/steuert noch keine Vorgabe/.test(test), "C3: der Stufentest sagt noch, er steuere nichts");
  ok(/steuert die Grundlage/.test(test) && /Umkehrung/.test(test), "C3: der Stufentest sagt nicht, dass er die Grundlage steuert");

  // Aufklapper ueberleben das Neuzeichnen: toggle merkt, _fold schreibt "open"
  const K = new M.Panel(); K._nowIso = F.TODAY; K._workouts = F.workouts("voll");
  K._attach();   // wie in _boot: die Hoerer am Schatten-Wurzelknoten
  const zu0 = z(K.rWorkouts(K._workouts, false));
  ok(zu(zu0, "fam:schwelle"), "Aufklapper: ohne Klick ist die Familie offen");
  const tog = K.shadowRoot._listeners.toggle;
  ok(typeof tog === "function", "Aufklapper: kein toggle-Hoerer am Schatten-Wurzelknoten");
  if (tog) tog({ target: { dataset: { keep: "fam:schwelle" }, open: true } });
  const auf1 = z(K.rWorkouts(K._workouts, false));
  ok(!zu(auf1, "fam:schwelle") && zu(auf1, "fam:grundlage"), "Aufklapper: die geoeffnete Familie klappt beim Neuzeichnen wieder zu (oder die falsche geht auf)");
  if (tog) tog({ target: { dataset: { keep: "fam:schwelle" }, open: false } });
  ok(zu(z(K.rWorkouts(K._workouts, false)), "fam:schwelle"), "Aufklapper: Zuklappen wird nicht gemerkt");
  if (tog) tog({ target: { dataset: {}, open: true } });
  ok(Object.keys(K._keep || {}).length === 1, "Aufklapper: ein details ohne data-keep landet im Gedaechtnis");

  // C4 · die Legende in Quellen kommt aus der Payload, nicht aus dem Panel
  const g4 = F.goal(); g4.plan.stages.green.detail = "LEGENDE GRUEN AUS DEM BACKEND";
  T._goal = g4; T._render();
  ok(/LEGENDE GRUEN AUS DEM BACKEND/.test(z(T._view.innerHTML)), "C4: die Legende in Quellen liest nicht die Payload");
  T._goal = F.goal();
}

/* ── 0.71.0 · Skizze Fassung 0.71.0, Abschnitte 1–3 ──────────────────────
   1 Mini-Streifen immer sichtbar, EINE Funktion mit dem grossen zplot
   2 Familienkoepfe im zugeklappten Hintergrund, aus denselben Daten wie die Kacheln
   3 _gaText mit umschliessendem Element. Vor dem Bau rot (Bericht 0.71.0). */
{
  const P = new M.Panel(); P._nowIso = F.TODAY;
  const z = (h) => String(h).replace(/\s+/g, " ");
  const bis = (h, marke) => h.slice(0, h.indexOf(marke) < 0 ? h.length : h.indexOf(marke));
  const ab = (h, marke) => h.slice(Math.max(0, h.indexOf(marke)));
  const lagen = (h) => [...h.matchAll(/class="zdot" style="left:([\d.]+)%;background:([^"]+)"/g)].map((m) => [m[1], m[2]]);
  const fall = (w, h3, r3) => {
    const c = F.coach("ready");
    return { ...c, state: { ...c.state, week_z: w, recent_hrv_z: h3, recent_rhr_z: r3 } };
  };
  const FAELLE = [["heute", -0.02, -0.07, 0.21], ["einbruch", -1.4, -2.1, 1.2], ["grenzfall", -0.5, 3.8, null]];
  for (const [name, w, h3, r3] of FAELLE) {
    const html = z(P.rTrainer(fall(w, h3, r3), F.readiness()));
    const oben = bis(html, 'data-keep="trainer:zustand"');
    const falt = ab(html, 'data-keep="trainer:zustand"');
    // 1a · die Zeile steht offen, unter der Kopfzeile, vor dem Aufklapper
    ok(/class="zmini"/.test(oben), `1 ${name}: die Mini-Streifen stehen nicht offen unter der Kopfzeile`);
    const mini = oben.slice(oben.indexOf('class="zmini"'));
    ok((mini.match(/class="zrow zs"/g) || []).length === 3, `1 ${name}: nicht drei Mini-Streifen`);
    ok(/HRV 7 T/.test(mini) && /HRV 3 T/.test(mini) && /Ruhepuls 3 T/.test(mini), `1 ${name}: Kurznamen fehlen`);
    // 1b · Werte mit Vorzeichen, echte Zahl auch ausserhalb ±3; fehlend = "keine Daten", kein Punkt
    for (const v of [w, h3, r3]) {
      if (v == null) continue;
      ok(mini.includes(M.sign(v, 2)), `1 ${name}: der Wert ${M.sign(v, 2)} fehlt im Mini-Streifen`);
    }
    const nNull = [w, h3, r3].filter((v) => v == null).length;
    ok(lagen(mini).length === 3 - nNull, `1 ${name}: ${lagen(mini).length} Punkte statt ${3 - nNull}`);
    ok((mini.match(/keine Daten/g) || []).length === nNull, `1 ${name}: fehlender Wert nicht als 'keine Daten'`);
    // 1c · GLEICHE Lage und Farbe wie im grossen zplot (eine Funktion, eine Positionsformel)
    const gross = lagen(falt.slice(falt.indexOf('class="zplot"')));
    const klein = lagen(mini);
    ok(gross.length === klein.length && gross.every((g, i) => g[0] === klein[i][0] && g[1] === klein[i][1]),
       `1 ${name}: Mini-Streifen und grosser zplot liegen verschieden (${JSON.stringify(klein)} / ${JSON.stringify(gross)})`);
    // 1d · Aufklapper bleibt: grosse Streifen mit Skala
    ok(/class="zscale"/.test(falt) && !/class="zscale"/.test(oben), `1 ${name}: die Skala steht nicht (nur) im Aufklapper`);
  }
  // Clipping am Rand: +3,8 steht bei 100 %, −0,5 genau am Bandrand (41,7 %)
  {
    const html = z(P.rTrainer(fall(-0.5, 3.8, null), F.readiness()));
    const mini = bis(html, 'data-keep="trainer:zustand"');
    const l = lagen(mini.slice(mini.indexOf('class="zmini"')));
    ok(l[0] && l[0][0] === "41.7" && l[1] && l[1][0] === "100.0", `1 Grenzfall: Lage ${JSON.stringify(l)} statt 41.7 / 100.0`);
    ok(mini.includes("+3,80"), "1 Grenzfall: die echte Zahl +3,80 steht nicht da");
  }
  // 1e · EINE Stelle: die Positionsformel steht einmal im Quelltext, der grosse zplot nutzt dieselbe Funktion
  {
    const src = H.source();
    ok((src.match(/\+ 3\) \/ 6 \* 100/g) || []).length === 1, "1 eine Stelle: die Positionsformel steht nicht genau einmal im Quelltext");
    ok(/_zRow\(/.test(src.slice(src.indexOf("  rTrainer(c, rd) {"), src.indexOf("  rHintergrund(c) {"))),
       "1 eine Stelle: rTrainer baut die Streifen nicht ueber _zRow");
  }
  // 1f · die Doppelung im Aufklapper: der Zustandssatz steht einmal
  {
    const c = F.coach("ready");
    const same = { ...c, reasons: [{ weil: "im Normalbereich", quelle: "Javaloyes", text: c.state.detail }] };
    const html = z(P.rTrainer(same, F.readiness()));
    ok(html.split(c.state.detail).length - 1 === 1, "1 Doppelung: der Zustandssatz steht zweimal im Aufklapper");
    const anders = { ...c, reasons: [{ weil: "x", quelle: "y", text: "EIN ANDERER GRUND." }] };
    const h2 = z(P.rTrainer(anders, F.readiness()));
    ok(h2.includes(c.state.detail) && h2.includes("EIN ANDERER GRUND."), "1 Doppelung Gegenprobe: ein anderer Grund verdraengt den Zustandssatz");
  }

  // 2 · Koepfe im ZUGEKLAPPTEN Hintergrund, aus denselben Daten wie die Kacheln
  {
    const Q = new M.Panel(); Q._nowIso = F.TODAY;
    Q._blocks = F.blocks({ steering_on: true });
    const v2 = F.fatigueV2Block();
    Q._fatigue = F.fatigue({ v2 });
    const hg = z(Q.rHintergrund(F.coach("ready")));
    ok(!/data-keep="trainer:hintergrund"[^>]*\sopen/.test(hg), "2: der Hintergrund ist nicht zugeklappt");
    const sum = hg.slice(0, hg.indexOf("</summary>"));
    ok(/class="bgheads"/.test(sum), "2: die Koepfe stehen nicht in der zugeklappten Zeile");
    const r0 = (v2.reversal || v2).plan[0];
    ok(new RegExp(`Grundlage <b class="tn">${M.fmt(r0.watts)} W</b> \\(${M.fmt(r0.hours)} h, ±${M.fmt(r0.band.half)} W · Umkehrung\\)`).test(sum),
       `2: Grundlage-Kopf nicht aus der Kachel (${sum.slice(sum.indexOf("bgheads"), sum.indexOf("bgheads") + 260)})`);
    const b = Q._blocks;
    for (const [key, nm] of [["sweetspot", "SweetSpot"], ["vo2max", "VO2max"]]) {
      const c = b.compare[key];
      ok(sum.includes(`${nm} <b class="tn">${M.fmt(c.new_watts)} W</b> (${M.fmt(c.new_band.low)}–${M.fmt(c.new_band.high)} · Vorgabe)`),
         `2: ${nm}-Kopf nicht aus der Kachel`);
    }
    // Gegenprobe Rechenschalter aus (alte Kurve): Kopf = erste Stunde der Kurve, ohne Spanne
    Q._fatigue = F.fatigue();
    const f1 = F.fatigue().plan[0];
    ok(z(Q.rHintergrund(F.coach("ready"))).includes(`Grundlage <b class="tn">${M.fmt(f1.watts)} W</b> (${M.fmt(f1.hours)} h · Kurve)`),
       "2: mit der alten Kurve passt der Grundlage-Kopf nicht zur Kachel");
    Q._fatigue = F.fatigue({ v2 });
    // reaktiv: eine andere Zahl in der Kachel schlaegt im Kopf durch
    Q._blocks = F.blocks({ steering_on: true });
    Q._blocks.compare = { ...Q._blocks.compare, vo2max: { ...Q._blocks.compare.vo2max, new_watts: 263 } };
    ok(/VO2max <b class="tn">263 W<\/b>/.test(z(Q.rHintergrund(F.coach("ready")))), "2: der Kopf rechnet selbst statt die Kachel zu lesen");
    // Schalter aus: der Kopf sagt, was die Kachel sagt (letzte Einheit, kein Band)
    Q._blocks = F.blocks({ steering_on: false });
    const aus = z(Q.rHintergrund(F.coach("ready")));
    ok(aus.includes(`VO2max <b class="tn">${M.fmt(Q._blocks.compare.vo2max.old_watts)} W</b> (letzte Einheit)`), "2: Schalter aus: Kopf passt nicht zur Kachel");
    // Gegenprobe ohne Kachel: keine Zahl, "noch keine Kachel"
    const leer = new M.Panel(); leer._nowIso = F.TODAY;
    const bl = F.blocks({ steering_on: true }); delete bl.families.vo2max; delete bl.compare.vo2max; delete bl.steering.vo2max;
    leer._blocks = bl; leer._fatigue = null;
    const lh = z(leer.rHintergrund(F.coach("ready")));
    const ls = lh.slice(0, lh.indexOf("</summary>"));
    ok(/Grundlage noch keine Kachel/.test(ls) && /VO2max noch keine Kachel/.test(ls) && /SweetSpot <b class="tn">190 W<\/b>/.test(ls),
       "2 Gegenprobe: ohne Kachel steht eine Zahl oder der Hinweis fehlt");
    // Trefferzusicherung fuer den Familien-Check allein: die Kachel fehlt (keine
    // Familie, oder ausgeblendet), die Vergleichszahl steht aber noch in der Payload
    const nurVgl = new M.Panel(); nurVgl._nowIso = F.TODAY;
    const bv = F.blocks({ steering_on: true }); delete bv.families.vo2max;
    nurVgl._blocks = bv; nurVgl._fatigue = null;
    ok(/VO2max noch keine Kachel/.test(z(nurVgl.rHintergrund(F.coach("ready")))), "2 Gegenprobe: ohne Kachel, aber mit Vergleichszahl steht eine Zahl");
    const bh = F.blocks({ steering_on: true }); bh.hidden_families = ["sweetspot"];
    nurVgl._blocks = bh;
    ok(/SweetSpot noch keine Kachel/.test(z(nurVgl.rHintergrund(F.coach("ready")))), "2 Gegenprobe: eine ausgeblendete Kachel bekommt einen Kopf");
    // die Zeile in der aufgeklappten Familie bleibt
    const W = new M.Panel(); W._blocks = F.blocks({ steering_on: true }); W._workouts = F.workouts("voll");
    ok(/Kachel VO2max: <b class="tn">250 W<\/b> \(Vorgabe\)/.test(z(W.rWorkouts(W._workouts, false))), "2: die Kachelzeile in der Familie fehlt");
  }

  // 3 · _gaText: der Herkunftsabsatz der Grundlage hat EIN umschliessendes Element
  {
    const e = { watt_source: "ga", ga_blocks: [{ label: "gleichmäßig", watts: 142, target: 142, limit: 169, hour: 1, n: 6,
                load_w: 139.6, alpha: 1.327, mid: 90.6 }] };
    const g = z(P._gaText(e));
    ok(/^<p class="fitwhy"> ?<svg[\s\S]*?<\/svg> ?<span>[\s\S]*<\/span><\/p>$/.test(g.trim()),
       "3: _gaText steht ohne umschliessendes Element im Flex-Absatz");
    ok(/fahr ~142 W, nicht über 169 W/.test(g), "3 Gegenprobe: der Inhalt ging verloren");
  }
}

/* ── 0.72.0 · 1 jede Variante als Karte · 4 der Deckel im Rechenweg ───── */
{
  const P = new M.Panel(); P._nowIso = F.TODAY;
  const z = (h) => String(h).replace(/\s+/g, " ");
  const falte = (h, id) => {
    const at = h.indexOf(`data-keep="${id}"`); if (at < 0) return "";
    const start = h.lastIndexOf("<details", at); let t = 0; const re = /<details\b|<\/details>/g; re.lastIndex = start; let m;
    while ((m = re.exec(h))) { t += m[0] === "</details>" ? -1 : 1; if (t === 0) return h.slice(start, m.index + 10); }
    return h.slice(start);
  };
  const karten = (f) => f.split('class="wocard').slice(1);
  const w = F.workouts("voll");
  P._workouts = w;
  const html = z(P.rWorkouts(w, false));
  const fv = falte(html, "fam:vo2max");
  const vo = w.workouts.find((e) => e.family === "vo2max");
  // 1a · jede Variante eine eigene Karte, mit Kalenderknopf
  for (const e of [vo, ...vo.variants]) {
    ok(new RegExp(`data-act="plan" data-id="${e.key}"`).test(fv), `1: ${e.key} steht nicht als Karte in der Familie`);
  }
  ok(karten(fv).length === 1 + vo.variants.length, `1: VO2max hat ${karten(fv).length} Karten statt ${1 + vo.variants.length}`);
  ok(!/Weitere Varianten/.test(html), "1: die Zeile 'Weitere Varianten' steht noch da");
  // 1b · die empfohlene steht oben und ist markiert
  const erste = karten(fv)[0];
  ok(erste.includes(`data-id="${vo.key}"`) && /class="(famflag|recflag)"/.test(erste), "1: die empfohlene Variante steht nicht oben oder ist nicht markiert");
  ok(karten(fv).slice(1).every((k) => !/class="(famflag|recflag)"/.test(k)), "1: eine weitere Variante traegt die Marke");
  // 1c · jede Variante mit IHREM Urteil aus der Payload (kein zweiter Rechenweg)
  const k54 = karten(fv).find((k) => k.includes('data-id="vo2_5x4"')) || "";
  // 0.72.2 umgestellt: Stufenwort + Mengen-Zeichen statt des Ersatz-Etiketts
  ok(/passt heute</.test(k54) && k54.includes("Menge über Wochenlast") && /title="VARIANTE UEBER DER GRENZE\."/.test(k54) && /Geländer: Last 92 über der Obergrenze 80 — VARIANTE/.test(k54),
     "1: die Variante traegt nicht ihr eigenes Etikett/Gelaender aus der Payload");
  const k30 = karten(fv).find((k) => k.includes('data-id="vo2_3030"')) || "";
  ok(/passt heute/.test(k30) && !/Geländer/.test(k30), "1 Gegenprobe: die Variante im Budget traegt ein Gelaender");
  // reaktiv: ein anderes Wort in der Payload schlaegt auf der Karte durch
  const w2 = F.workouts("voll"); const vo2b = w2.workouts.find((e) => e.family === "vo2max");
  vo2b.variants[1] = { ...vo2b.variants[1], stage: { ...vo2b.variants[1].stage, key: "red", word: "WORT AUS DER PAYLOAD" } };
  ok(/WORT AUS DER PAYLOAD/.test(falte(z(P.rWorkouts(w2, false)), "fam:vo2max")), "1: das Urteil der Variante kommt nicht aus der Payload");
  // 1d · die zugeklappte Zeile bleibt unveraendert (gewaehlte Variante der Familie)
  const sum = fv.slice(0, fv.indexOf("</summary>"));
  ok(sum.includes(vo.title) && !sum.includes("5×4") && !/class="wocard/.test(sum), "1: die zugeklappte Familienzeile hat sich veraendert");
  // Trefferzusicherung fuer die Reihenfolge: die empfohlene ist NICHT die erste der
  // Payload (Grundlage 90 gelb, Lange Fahrt gruen) - sie muss trotzdem oben stehen.
  const wr = F.workouts("voll");
  wr.workouts[0] = { ...wr.workouts[0], stage: F.stageOf("maybe", true, false) };
  const fgr = falte(z(P.rWorkouts(wr, false)), "fam:grundlage");
  ok(karten(fgr)[0].includes('data-id="z2_210_late"') && /class="(famflag|recflag)"/.test(karten(fgr)[0]),
     "1: die empfohlene Variante steht nicht oben, wenn sie nicht die erste der Payload ist");
  // 1e · Gegenprobe: Familie mit einer Variante - genau eine Karte je Familie
  const fg = falte(html, "fam:grundlage");
  ok((fg.match(/data-act="plan" data-id="recovery_40"/g) || []).length === 2, "1 Gegenprobe: die Regeneration erscheint nicht genau einmal (zwei Knoepfe)");
  const fs = falte(html, "fam:schwelle");
  ok(/data-id="threshold_4x16"/.test(fs), "1: die SweetSpot-Variante 4x16 fehlt in ihrer Familie");

  // 4 · der Deckel im Rechenweg des Wochenplans - beide Zahlen
  const g = F.goal();
  g.plan.big_day_cap = { hours: 3.8, from_minutes: 210, from_date: "2026-09-10", factor: 1.1, applied: true };
  const wp = z(P.rPlanWeeks(g, (F.coach("ready").durability || {}).progression));
  const rw = falte(wp, "trainer:weeksrw");
  ok(/gedeckelt durch die Progression/.test(rw) && /3,8 h/.test(rw) && /3 h 30/.test(rw), "4: der Rechenweg nennt den Deckel mit beiden Zahlen nicht");
  g.plan.big_day_cap = { ...g.plan.big_day_cap, hours: 10, applied: false };
  const wp2 = falte(z(P.rPlanWeeks(g)), "trainer:weeksrw");
  ok(!/gedeckelt durch/.test(wp2) && /über dem großen Tag/.test(wp2), "4 Gegenprobe: die Grenze ueber dem grossen Tag wird als Deckel gemeldet");
  delete g.plan.big_day_cap;
  ok(!/Progression aus deiner längsten Fahrt/.test(falte(z(P.rPlanWeeks(g)), "trainer:weeksrw")), "4 Gegenprobe: ohne Deckel steht ein Deckelsatz");
}

/* ── 0.72.1 · die Nachtbewertung liest das Tagesetikett ───────────────── */
{
  const P = new M.Panel(); P._nowIso = F.TODAY;
  const z = (h) => String(h).replace(/\s+/g, " ");
  const GRUND = "Nacht zum 04.09. mit Etikett Alkohol, Gewicht 0,5 — sie misst nicht nur die Einheit";
  const n = { available: true, night_date: "2026-09-04", state: "unrated",
    headline: `Nicht bewertbar: ${GRUND}.`, detail: "Die Werte der Nacht stehen darunter.",
    night: { hrv: { label: "Herzratenvariabilität", unit: "ms", value: 40.4, baseline: 47.6, z: -1.59 } },
    reference: { hrv: { mean: -1.47, sd: 1.24, n: 24 } }, caveat: "x",
    verdict: { key: "nicht_bewertbar", label: `nicht bewertbar — ${GRUND}`, reason: GRUND,
               z_hrv: -1.59, z_hrv_next: -0.34, rule: "Setzung: …", note: null } };
  P._night = { a1: n };
  const h = z(P._nightBlock({ id: "a1" }));
  ok(h.includes(GRUND), "0.72.1: der Grund steht nicht an der Nacht");
  ok(/-1,6 SD|−1,6 SD|-1,59/.test(h) && /40/.test(h), "0.72.1: die Rohwerte der Nacht sind nicht sichtbar");
  ok(!h.includes(`stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" style="color:${M.C.green}"`),
     "0.72.1: 'nicht bewertbar' traegt das gruene Haekchen (ein Urteil)");
  ok(/class="(cmpverdict|nverdict) unrated"/.test(h), "0.72.1: 'nicht bewertbar' hat keinen eigenen, neutralen Ton");
  // Gegenprobe: ein bewertetes 'verdaut' behaelt sein Haekchen
  const g = z(P._nightVerdict({ key: "verdaut", label: "verdaut", z_hrv: 0.1, z_hrv_next: 0.2, rule: "r" }));
  ok(g.includes(`style="color:${M.C.green}"`), "0.72.1 Gegenprobe: 'verdaut' verliert sein Haekchen");
  // 3 · Cannabis hat eine eigene Etikettenfarbe aus dem Kategorienregister
  ok(M.CTX_COLOR.cannabis && M.CTX_COLOR.cannabis !== M.CTX_COLOR.alkohol && M.CTX_COLOR.cannabis !== M.CTX_COLOR.normal,
     "0.72.1 3: Cannabis hat keine eigene Etikettenfarbe");
}

/* ── 0.72.2 · Stufenwort immer, Menge als eigenes Zeichen ─────────────── */
{
  const P = new M.Panel(); P._nowIso = F.TODAY;
  const z = (h) => String(h).replace(/\s+/g, " ");
  const karte = (h, key) => h.split('class="wocard').find((k) => k.includes(`data-id="${key}"`)) || "";
  const MENGE = "Menge über Wochenlast";
  const w = F.workouts("voll");
  // Grundlage 90 green UEBER der Grenze (Obergrenze 0), SweetSpot stimulus ueber der Grenze,
  // Schwelle rot, Regeneration green (ausgenommen -> fits_budget true)
  w.workouts[0] = { ...w.workouts[0], fits_budget: false, stage: F.stageOf("ok", false, false),
    guard: { over: true, load: 72, ceiling: 0, hours_fit: null, text: "Geländer: Last 72 über der Obergrenze 0." } };
  const iSS = w.workouts.findIndex((e) => e.family === "sweetspot");
  w.workouts[iSS] = { ...w.workouts[iSS], fits_budget: false, stage: F.stageOf("ok", false, true) };
  const iTh = w.workouts.findIndex((e) => e.family === "threshold");
  w.workouts[iTh] = { ...w.workouts[iTh], stage: F.stageOf("no", true, false) };
  const iRc = w.workouts.findIndex((e) => e.family === "recovery");
  w.workouts[iRc] = { ...w.workouts[iRc], fits_budget: true, stage: F.stageOf("ok", true, false) };
  const h = z(P.rWorkouts(w, false));
  const g = karte(h, "z2_90");
  ok(/passt heute/.test(g) && g.includes(MENGE), "0.72.2: green ueber der Grenze zeigt nicht 'passt heute' + Mengen-Zeichen");
  ok(!/Art bleibt, Menge kürzen</.test(h), "0.72.2: das Stufenwort wird noch ersetzt");
  const u = karte(h, "tempo_2x20");
  ok(/passt heute/.test(u) && !u.includes(MENGE), "0.72.2 Gegenprobe: unter der Grenze nicht nur 'passt heute'");
  const st = karte(h, "sweetspot_2x20");
  ok(/gewollter Überreiz/.test(st) && !st.includes(MENGE) && !/über der Obergrenze von/.test(st), "0.72.2 Gegenprobe: stimulus mit Mengen-Zeichen oder altem Zusatz");
  const r = karte(h, "threshold_4x10");
  ok(/heute nicht/.test(r) && !r.includes(MENGE), "0.72.2 Gegenprobe: rot mit Mengen-Zeichen");
  const rc = karte(h, "recovery_40");
  ok(/passt heute/.test(rc) && !rc.includes(MENGE), "0.72.2 Gegenprobe: Regeneration bei Obergrenze 0 mit Zeichen");
  ok(!/heute heute|morgen morgen|\{tag\}/.test(h), "0.72.2: doppelte Anhaengung oder Platzhalter sichtbar");
  // Morgen-Modus
  const m = z(P.rWorkouts(w, true));
  ok(/passt morgen/.test(karte(m, "tempo_2x20")) && /morgen nicht/.test(karte(m, "threshold_4x10")) && !/passt heute|heute nicht/.test(m.replace(/title="[^"]*"/g, "")),
     "0.72.2: Morgen-Modus sagt nicht 'passt morgen'/'morgen nicht'");
  // 3 · alle fuenf Leser: Karte (oben), Familienzeile, Empfehlung, Wochenplan-Chips, Legende Quellen
  const fam = h.slice(h.indexOf('data-keep="fam:grundlage"'));
  const famSum = fam.slice(0, fam.indexOf("</summary>"));
  ok(/passt heute/.test(famSum), "0.72.2 3: die Familienzeile liest das Stufenwort nicht");
  const lw = F.workouts(); lw.workouts[0] = { ...lw.workouts[0], fits_budget: false, stage: F.stageOf("ok", false, false),
    guard: { over: true, load: 72, ceiling: 40, hours_fit: 1.0, text: "Geländer." } };
  const lead = z(P.rWorkouts(lw, false));
  const leadBox = lead.slice(lead.indexOf('class="leadrec"'), lead.indexOf("Die Familien"));
  ok(/passt heute/.test(leadBox) && leadBox.includes(MENGE), "0.72.2 3: die Empfehlung oben zeigt Stufenwort + Mengen-Zeichen nicht");
  // Woche: z2_90 stimulus, SweetSpot gelb, z2_60 gruen - dazu z2_60 gruen UEBER der Grenze
  const gw = F.goal(); const wk = gw.plan.weeks.find((x) => x.rated === true);
  wk.sessions[2] = { ...wk.sessions[2], fits_budget: false, stage: F.stageOf("ok", false, false) };
  const wp = z(P.rPlanWeeks(gw));
  const chips = wp.slice(wp.indexOf('class="pwsess"'));
  ok(/passt heute/.test(chips) && chips.includes(MENGE) && /geht, kostet mehr/.test(chips), "0.72.2 3: die Wochenplan-Chips lesen die Stufenworte nicht");
  ok(!/über der Obergrenze von/.test(wp), "0.72.2 3: '(über der Obergrenze von X)' steht noch im Wochenplan");
  ok(!z(P.rPlanWeeks(F.goal())).includes(MENGE), "0.72.2 3 Gegenprobe: Wochenplan unter der Grenze / stimulus mit Mengen-Zeichen");
  P._goal = F.goal();
  const leg = z(P._trainerSources());
  ok(/passt heute/.test(leg) && /geht, kostet mehr/.test(leg) && /gewollter Überreiz/.test(leg) && /heute nicht/.test(leg),
     "0.72.2 3: die Legende im Reiter Quellen zeigt die Stufenworte nicht");
  // reaktiv: ein anderes Wort in der Payload schlaegt in allen Lesern durch
  const g2 = F.goal(); g2.plan.stages.green.word = "WORT-{tag}";
  P._goal = g2;
  ok(/WORT-heute/.test(z(P._trainerSources())), "0.72.2 3: die Legende liest nicht die Payload");
  // Tooltip = Stufen-Satz, nicht der Mengen-Satz
  ok(/class="bdg" title="Begründung aus dem Backend\."/.test(g), "0.72.2: der Tooltip ist nicht der Stufen-Satz");
}

/* ── 0.73.0 · Heute-Kopf Variante C (Skizze §6) ─────────────────────── */
{
  // 0.73.1: "heute" ist der 26.09. - das Fenster der Fixture (So 20.-Sa 26.) ist das von heute
  const P = new M.Panel(); P._nowIso = "2026-09-26";
  const z = (h) => String(h).replace(/\s+/g, " ");
  const vis = (h) => z(h).replace(/title="[^"]*"/g, "").replace(/aria-label="[^"]*"/g, "");
  const H = (k, o) => z(P.rHeute({ ...F.today(), week: F.week(k), ...(o || {}) }));
  const box = (h) => h.slice(h.indexOf('class="hwbox"'), h.indexOf('class="tstate"'));
  const side = (h) => h.slice(h.indexOf('class="tstate"'), h.indexOf('class="tsig'));
  const pct = (v, m) => (v / m * 100).toFixed(1) + "%";
  const { C, FAM } = M;

  // Kopf: Koerper oben
  const v = H("voll");
  clean(v, "0.73.0 heute voll");
  contains(v, "Was dein Körper heute kann", "0.73.0 §6: Augenbraue des Koerpers fehlt");
  contains(v, "Alles möglich", "0.73.0 §6: Wort aus CAPACITY fehlt");
  ok(/class="tbig"[^>]*>Alles möglich</.test(v), "0.73.0 §6: das Koerperwort ist nicht die Leitanzeige");
  // der Kasten
  const b = box(v);
  // 0.73.1 umgestellt (2.4): die Spanne statt "letzte 7 Tage"
  contains(b, "Wie viel die Woche noch trägt · So 20.–Sa 26.", "0.73.1 2.4: Augenbraue der Woche ohne Datumsspanne");
  contains(b, ">Woche voll<", "0.73.0 §6 Fall Rest 0: 'Woche voll' fehlt");
  // 0.73.1 umgestellt (2.3): "fällt aus dem Fenster" statt "Morgen wird Platz"
  contains(b, "Heute ist keine Last mehr frei. Ab morgen fällt die Fahrt vom So 20. (90) aus dem Fenster.", "0.73.1 2.3: Satz 'Ab morgen' falsch");
  ok(!/Morgen wird Platz/.test(b), "0.73.1 2.3: 'Morgen wird Platz' steht noch");
  const l0 = box(H("leer0"));
  ok(/Heute ist keine Last mehr frei\.</.test(l0) && !/aus dem Fenster/.test(l0), "0.73.1 2.3: Satz ohne Fenstertag mit Last");
  const fr = box(H("frei"));
  ok(/>Noch 116 Last frei</.test(fr) && fr.includes("So viel verträgt die Woche heute noch."), "0.73.0 §6 Fall Rest > 0 falsch");
  const zu = box(H("zustand"));
  ok(/>Heute höchstens 75 Last</.test(zu) && zu.includes("Die Woche hätte noch 86 frei, aber dein Zustand bremst."), "0.73.0 §6 Fall bound_by state falsch");
  ok(!/Noch 86 Last frei/.test(zu), "0.73.0 §6: bound_by state zeigt das Wochenurteil");
  // Morgen-Modus
  const mo = H("morgen");
  contains(mo, "Was dein Körper morgen kann", "0.73.0 §6: Morgen-Augenbraue fehlt");
  ok(/>Noch 86 Last frei</.test(box(mo)) && box(mo).includes("So viel verträgt die Woche morgen noch."), "0.73.0 §6: Morgen-Satz falsch");
  const mv = z(P.rHeute({ ...F.today(), week: { ...F.week("voll"), mode: "tomorrow" } }));
  // 0.73.1 umgestellt (2.3): der Satz steht in BEIDEN Modi
  ok(box(mv).includes("Morgen ist keine Last mehr frei. Ab morgen fällt die Fahrt vom So 20. (90) aus dem Fenster.") && !/Morgen wird Platz/.test(mv),
     "0.73.1 2.3: Morgen-Modus ohne 'fällt aus dem Fenster'");
  ok(/>Morgen höchstens 75 Last</.test(z(P.rHeute({ ...F.today(), week: { ...F.week("zustand"), mode: "tomorrow" } }))), "0.73.0 §6: Morgen-Modus bound_by state");

  // vier Zeilen je Gruppe, Reihenfolge, Breite auf gemeinsamer Skala max(Ziel, Summe)
  const rows = (h) => [...box(h).matchAll(/class="hwrow( [a-z]+)?"[^>]*>\s*<span class="hwname">([^<]+)<\/span>\s*<div class="hwtrack"><span class="hwfill( hatch)?"[^>]*style="width:([\d.]+)%[^"]*"><\/span><\/div>\s*<span class="hwn tn">([^<]+)<\/span>/g)]
    .map((m) => ({ name: m[2], hatch: !!m[3], w: m[4] + "%", n: m[5] }));
  const rv = rows(v);
  ok(JSON.stringify(rv.map((r) => r.name)) === JSON.stringify(["Grundlage", "SweetSpot &amp; Schwelle", "VO2max", "nicht zugeordnet"]),
     `0.73.0 §6: Zeilen/Reihenfolge ${JSON.stringify(rv.map((r) => r.name))}`);
  ok(rv.length === 4 && rv[0].n === "0" && rv[0].w === "0.0%", "0.73.0 §6: Gruppe mit 0 bleibt nicht als leerer Balken stehen");
  ok(rv.length === 4 && rv[2].w === pct(75, 260) && rv[3].w === pct(185, 260) && rv[3].n === "185", "0.73.0 §6: Breite nicht Last/max(Ziel, Summe)");
  ok(rv.length === 4 && rv[3].hatch && !rv[2].hatch, "0.73.0 §6: 'nicht zugeordnet' nicht schraffiert");
  const rf = rows(H("frei"));
  ok(rf.length === 5 && rf[3].name === "andere Sportarten" && rf[3].n === "20" && rf[4].name === "nicht zugeordnet" && rf[0].w === pct(60, 256),
     "0.73.0: andere Sportart als eigene Zeile (nur wenn > 0), Skala = Ziel bei Summe < Ziel");
  ok(rows(v).every((r) => r.name !== "andere Sportarten"), "0.73.0: Zeile andere Sportarten ohne Last");
  // Farben: nur aus FAM/C, keine Zustandsfarben fuer Familien
  const fills = [...box(v).matchAll(/class="hwfill"[^>]*style="width:[\d.]+%;background:([^"]+)"/g)].map((m) => m[1]);
  ok(JSON.stringify(fills) === JSON.stringify([FAM.endurance.c, FAM.sweetspot.c, FAM.vo2max.c]), `0.73.0 §6: Gruppenfarben ${JSON.stringify(fills)}`);
  ok(![C.green, C.amber, C.red, C.orange].some((c) => fills.includes(c)), "0.73.0 §6: Zustandsfarbe an einer Familie");
  // Summenbalken: vier Baender, Fuellung = Summe, Zielstrich + "Ziel 256", Worte ohne Zahlen
  const mx = Math.max(295, 260) * 1.05;
  // 0.73.1 umgestellt (2.2): drei Flaechen am Ziel statt vier fester Baender
  ok((box(v).match(/class="hwband"/g) || []).length === 3, "0.73.1 2.2: nicht drei Flaechen");
  ok(box(v).includes(`class="hwsumfill" style="width:${pct(260, mx)}"`), "0.73.0 §6: Fuellung nicht = Summe");
  ok(box(v).includes(`class="hwgoal" style="left:${pct(256, mx)}"`) && />Ziel 256</.test(box(v)), "0.73.0 §6: Zielstrich/Ziel-Beschriftung");
  const zones = (box(v).match(/class="hwzones">(.*?)<\/div>/) || ["", ""])[1];
  ok(["passt", "über Ziel", "zu viel"].every((w) => zones.includes(`>${w}<`)) && !/>wenig</.test(zones) && !/>viel</.test(zones) && !/\d/.test(zones.replace(/style="[^"]*"/g, "")),
     "0.73.0 §6: Bandworte fehlen oder Zahlen an den Grenzen");
  // Zielstrich je Ampel (x1,0 / x0,8) aus dem Payload
  ok(box(H("gelb")).includes(`class="hwgoal" style="left:${pct(197, mx)}"`) && />Ziel 197</.test(box(H("gelb"))), "0.73.0: Zielstrich gelb nicht x1,0");
  ok(box(H("rot")).includes(`class="hwgoal" style="left:${pct(157, mx)}"`), "0.73.0: Zielstrich rot nicht x0,8");
  contains(box(H("gelb")), "Das Ziel ist das 1,0-Fache", "0.73.0: Faktor gelb in der Fusszeile");
  // Ueberlauf ueber die Risikogrenze
  const ue = box(H("ueber")); const mx2 = 380 * 1.05;
  ok(ue.includes(`class="hwsumfill" style="width:${pct(380, mx2)}"`) && ue.includes(`class="hwgoal" style="left:${pct(256, mx2)}"`), "0.73.0: Ueberlauf skaliert nicht mit");
  // Fusszeile woertlich
  // 0.73.1 umgestellt (2.2): mit dem Zustandswort
  contains(b, "Zusammen 260 Last. Das Ziel ist das 1,3-Fache deines Durchschnitts der letzten 4 Wochen, weil dein Zustand „Normalbereich“ ist – eine Festlegung, keine Messung.",
           "0.73.0 §6: Fusszeile nicht woertlich");
  // entfallen: "nicht verdaust", "Obergrenze ... davon ... gefahren"
  ok(!/nicht verdaust/.test(v) && !/davon [\d]+ gefahren/.test(v) && !/class="tceil"/.test(v), "0.73.0 §6: alter Bullet/Satz steht noch");
  // Budget None
  const nb = H("ohnebudget");
  ok(box(nb).includes("Die Wochenlast braucht 28 Tage Verlauf.") && !/hwrow|hwband|Ziel \d/.test(box(nb)), "0.73.0 §6: Budget None zeigt mehr als den Satz");
  ok((side(nb).match(/class="hwli"/g) || []).length === 3, "0.73.0 §7 Regel 10: ohne Budget fehlt die Liste");

  // rechte Spalte: Zustand, dann die Fahrten = Legende
  const sd = side(v);
  ok(/class="tlabel">Zustand</.test(sd) && /class="tlabel[^"]*">Deine Fahrten in diesem Fenster</.test(sd), "0.73.0 §6: Augenbrauen rechts");
  ok(sd.indexOf("Zustand<") < sd.indexOf("Deine Fahrten"), "0.73.0 §6: Zustand steht nicht ueber den Fahrten");
  const li = [...sd.matchAll(/class="hwli">\s*<span class="hwchip( hatch)?" style="([^"]*)" title="([^"]*)"><\/span>\s*<span class="d">([^<]+)<\/span>\s*<span class="nm" title="([^"]*)">([^<]+)<\/span>\s*<span class="ld tn">([^<]+)<\/span>\s*<span class="fam">([^<]+)<\/span>/g)]
    .map((m) => ({ hatch: !!m[1], style: m[2], src: m[3], d: m[4], full: m[5], nm: m[6], ld: m[7], fam: m[8] }));
  ok(li.length === F.week("voll").sessions.length, `0.73.0 §6: Liste = Legende (${li.length} Zeilen)`);
  ok(li.length === 3 && li[0].d === "So 20." && li[0].ld === "90" && li[0].fam === "nicht zugeordnet" && li[0].hatch, "0.73.0 §6: Zeile So 20.");
  ok(li.length === 3 && li[0].full === "SweetSpot 2x20 am Deich mit Gegenwind", "0.73.0 §6: voller Name nicht als title");
  ok(li.length === 3 && li[2].fam === "VO2max" && li[2].style.includes(FAM.vo2max.c) && !li[2].hatch, "0.73.0 §6: VO2max-Zeile ohne Familienfarbe");
  ok(li.length === 3 && /Pendelfahrt/.test(li[1].src) && !/Pendelfahrt/.test(vis(sd)), "0.73.0 §6: Pendelfahrt nur als title am Chip");
  ok(!/Marken|gepaart|Plan\b/.test(vis(sd).replace(/Deine Fahrten/, "")), "0.73.0 §6: Quellenworte in der Anzeige");
  const lf = [...side(H("frei")).matchAll(/class="hwli">\s*<span class="hwchip( hatch)?" style="([^"]*)"[\s\S]*?<span class="nm" title="[^"]*">([^<]+)<\/span>[\s\S]*?<span class="fam">([^<]+)<\/span>/g)]
    .map((m) => ({ hatch: !!m[1], style: m[2], nm: m[3], fam: m[4] }));
  ok(lf.length === 4 && lf[0].fam === "Grundlage" && lf[0].style.includes(FAM.endurance.c) && lf[1].style.includes(FAM.sweetspot.c),
     "0.73.0 §6: Grundlage/Schwelle-Chips ohne FAM-Farbe");
  ok(lf.length === 4 && lf[2].fam === "Lauf" && lf[2].style.includes(C.cyan), "0.73.0 §6: andere Sportart nicht cyan mit Sportwort");
  ok(lf.length === 4 && lf[3].nm === "ohne Einheit" && lf[3].hatch && lf[3].fam === "nicht zugeordnet", "0.73.0 §5.2: Rest 'ohne Einheit' nicht als Zeile");
  ok([C.green, C.amber, C.red].every((c) => lf.every((x) => !x.style.includes(c))), "0.73.0 §6: Zustandsfarbe an einem Chip");
  // Name fehlt -> Sportwort
  const nn = { ...F.week("frei") }; nn.sessions = nn.sessions.map((x, i) => (i === 0 ? { ...x, name: null } : x));
  ok(/<span class="nm" title="Rad">Rad</.test(side(z(P.rHeute({ ...F.today(), week: nn })))), "0.73.0 §8: Name fehlt -> Sportwort");
  // leeres Fenster
  // 0.73.2 umgestellt (T3): "Keine Fahrt in diesem Fenster." statt "in den letzten 7 Tagen"
  ok(side(H("leer")).includes("Keine Fahrt in diesem Fenster.") && !/class="hwli"/.test(side(H("leer"))), "0.73.2 T3: leeres Fenster");
  // Schraffur: eigene Regel im Stil, Farbe nie allein (Wort daneben)
  ok(/\.hatch\{[^}]*repeating-linear-gradient/.test(String(P._css())), "0.73.0 §6: Schraffur fehlt im Stil");
  // unter 760 px rutscht die rechte Spalte unter den Kasten
  ok(/@media\(max-width:760px\)\{\s*\.tcard\{grid-template-columns:1fr\}/.test(String(P._css())), "0.73.0 §6: Umbruch unter 760 px");
  // kein Rechnen im Panel ausser Pixelbreiten: frei/Summe/Gruppen kommen aus dem Payload
  const wx = F.week("frei"); wx.budget = { ...wx.budget, window_free: 777 }; wx.groups = { ...wx.groups, grundlage: 555 }; wx.total = 999;
  const hx = box(z(P.rHeute({ ...F.today(), week: wx })));
  ok(/>Noch 777 Last frei</.test(hx) && />555</.test(hx) && /Zusammen 999 Last/.test(hx), "0.73.0: das Panel rechnet frei/Gruppen/Summe selbst");
  // stale-Tag: der Kasten steht trotzdem
  ok(/class="hwbox"/.test(z(P.rHeute({ ...F.today(), date: "2026-09-09", week: F.week("voll") }))), "0.73.0 §8: stale-Tag ohne Wochenkasten");
}

/* ── 0.73.1 · Baender am Ziel, "faellt aus dem Fenster", Fenster beschriftet ── */
{
  const P = new M.Panel(); P._nowIso = "2026-09-26";
  const z = (h) => String(h).replace(/\s+/g, " ");
  const H = (w, o) => z(P.rHeute({ ...F.today(), week: w, ...(o || {}) }));
  const box = (h) => h.slice(h.indexOf('class="hwbox"'), h.indexOf('class="tstate"'));
  const pct = (v, m) => (v / m * 100).toFixed(1) + "%";
  const { C } = M;
  const bands = (h) => [...box(h).matchAll(/class="hwband" style="left:([\d.]+)%;width:([\d.]+)%;background:([^"]+)"/g)]
    .map((m) => ({ l: m[1] + "%", w: m[2] + "%", c: m[3] }));
  // 2.2 drei Flaechen: [0, Ziel) passt · [Ziel, Risiko) ueber Ziel · [Risiko, max) zu viel
  const wv = F.week("voll"); const mx = Math.max(295, 260) * 1.05;
  const bv = bands(H(wv));
  ok(bv.length === 3 && bv[0].l === "0.0%" && bv[0].w === pct(256, mx) && bv[1].l === pct(256, mx) && bv[2].l === pct(295, mx),
     `0.73.1 2.2: Flaechen nicht am Ziel ${JSON.stringify(bv)}`);
  ok(bv.length === 3 && bv[0].c.startsWith(C.green) && bv[1].c.startsWith(C.amber) && bv[2].c.startsWith(C.red), "0.73.1 2.2: Farben passt/ueber Ziel/zu viel");
  // der Abnahme-Fall: Faktor 0,8, Ziel 180, Summe 278 -> liegt in "ueber Ziel"
  const r = F.week("rot"); r.budget = { ...r.budget, window_allowed: 180, window_bands: { low: 180, steady: 225, top: 293, risk: 338 } };
  r.total = 278; const mr = 338 * 1.05;
  const br = bands(H(r));
  const fill = (box(H(r)).match(/class="hwsumfill" style="width:([\d.]+)%"/) || [])[1];
  ok(br.length === 3 && br[1].l === pct(180, mr) && parseFloat(fill) > parseFloat(br[1].l) && parseFloat(fill) < parseFloat(br[2].l),
     "0.73.1 2.2: Summe 278 bei Ziel 180 steht nicht in 'über Ziel'");
  ok(br.length === 3 && box(H(r)).includes(`class="hwgoal" style="left:${pct(180, mr)}"`), "0.73.1 2.2: das Ziel ist nicht die Grenze passt|über Ziel");
  // Randfall: Ziel >= Risiko -> nur zwei Flaechen
  const rr = F.week("voll"); rr.budget = { ...rr.budget, window_allowed: 300 };
  const b2 = bands(H(rr));
  ok(b2.length === 2 && b2[0].c.startsWith(C.green) && b2[1].c.startsWith(C.red), `0.73.1 2.2 Randfall: Ziel >= Risiko -> zwei Flaechen (${b2.length})`);
  ok(!/>über Ziel</.test(box(H(rr))), "0.73.1 2.2 Randfall: 'über Ziel' ohne Flaeche");
  // Fusszeile mit dem Zustandswort von rechts oben (state_label)
  contains(box(H(wv, { state_label: "beansprucht" })), "weil dein Zustand „beansprucht“ ist – eine Festlegung, keine Messung.", "0.73.1 2.2: Zustandswort nicht aus state_label");
  // 2.3 "Ab {Wochentag}", wenn leaves_on nicht morgen ist
  const f = F.week("frei"); f.budget = { ...f.budget, window_free: 0 };
  ok(box(H(f)).includes("Ab Montag fällt die Fahrt vom Mo 21. (60) aus dem Fenster."), "0.73.1 2.3: 'Ab {Wochentag}' falsch");
  ok(!/Ab morgen/.test(box(H(f))), "0.73.1 2.3: 'Ab morgen' obwohl leaves_on nicht morgen ist");
  const mo = F.week("morgen"); mo.budget = { ...mo.budget, window_free: 0 };
  ok(box(H(mo)).includes("Morgen ist keine Last mehr frei. Ab Dienstag fällt die Fahrt vom Di 22. (95) aus dem Fenster."), "0.73.1 2.3: Morgen-Modus 'Ab Dienstag'");
  ok(!/aus dem Fenster/.test(box(H(F.week("frei")))), "0.73.1 2.3: der Satz steht auch ohne 'Woche voll'");
  // 2.4 Fenster beschriftet: Modus morgen mit eigener Spanne und Hinweis
  const bm = box(H(F.week("morgen")));
  ok(bm.includes("Wie viel die Woche morgen trägt · Mo 21.–So 27.") && !/So 20\.–Sa 26\./.test(bm), "0.73.1 2.4: Morgen-Spanne falsch");
  ok(bm.includes("Du bist heute schon gefahren, deshalb zählt das Fenster ab morgen. Die Fahrt vom So 20. ist dann nicht mehr drin."), "0.73.1 2.4: Hinweissatz im Morgen-Modus fehlt");
  const m0 = F.week("morgen"); m0.budget = { ...m0.budget, window_before: { date: "2026-09-20", load: 0 } };
  ok(box(H(m0)).includes("deshalb zählt das Fenster ab morgen.") && !/nicht mehr drin/.test(box(H(m0))), "0.73.1 2.4: zweiter Satz ohne Last des Tages");
  ok(!/Du bist heute schon gefahren/.test(box(H(wv))), "0.73.1 2.4: Hinweissatz im Heute-Modus");
  ok(z(P.rHeute({ ...F.today(), week: F.week("ohnebudget") })).includes("Wie viel die Woche noch trägt · So 20.–Sa 26."), "0.73.1 2.4: Spanne ohne Budget");
  // Liste rechts: "Deine Fahrten in diesem Fenster" in beiden Modi
  ok(/Deine Fahrten in diesem Fenster/.test(H(F.week("morgen"))) && !/letzte 7 Tage|letzten 7 Tagen/.test(H(F.week("morgen"))),
     "0.73.1 2.4: Listen-/Kastenbeschriftung sagt noch 'letzte 7 Tage'");
  // das Panel liest nur window_allowed und window_bands.risk
  const q = F.week("voll"); q.budget = { ...q.budget, window_bands: { low: 1, steady: 2, top: 3, risk: 295 } };
  ok(JSON.stringify(bands(H(q))) === JSON.stringify(bv), "0.73.1 2.2: das Panel liest low/steady/top");
}

/* ── 0.73.2 · Heute-Kopf morgen-Augenbraue, leeres Fenster, Wochenplan-Zeile ── */
{
  const P = new M.Panel(); P._nowIso = "2026-09-26";
  const z = (h) => String(h).replace(/\s+/g, " ");
  // T3 Augenbraue: morgen mit Zusatz, heute unveraendert
  const mo = z(P.rHeute({ ...F.today(), week: F.week("morgen") }));
  ok(/class="tlabel">Was dein Körper morgen kann · nach dem Zustand von heute </.test(mo), "0.73.2 T3: Morgen-Augenbraue ohne 'nach dem Zustand von heute'");
  const he = z(P.rHeute({ ...F.today(), week: F.week("voll") }));
  ok(/class="tlabel">Was dein Körper heute kann </.test(he) && !/nach dem Zustand von heute/.test(he), "0.73.2 T3 Gegenprobe: heute-Augenbraue veraendert");
  // T3 leeres Fenster in beiden Modi
  const leerM = F.week("leer"); leerM.mode = "tomorrow";
  ok(z(P.rHeute({ ...F.today(), week: leerM })).includes("Keine Fahrt in diesem Fenster."), "0.73.2 T3: leeres Fenster im morgen-Modus");
  // T4 Wochenplan, laufende Woche: eine Zeile, Modus wie die Stufenworte
  const line = (w) => `Bewertet für ${w}: jede Einheit so, als wäre sie deine nächste Fahrt. Welche du an welchem Tag fährst, entscheidest du.`;
  P._coach = { ...F.coach("ready"), trained_today: false };
  const wh = z(P.rPlanWeeks(F.goal()));
  const cur = wh.split('class="pweek ').slice(1).find((x) => /^[a-z]+[^"]* now"/.test(x)) || "";
  const now = cur;
  ok(now.includes(line("heute")), "0.73.2 T4: Zeile 'Bewertet für heute' fehlt in der laufenden Woche");
  ok((wh.match(/Bewertet für (heute|morgen)/g) || []).length === 1, "0.73.2 T4: die Zeile steht nicht genau einmal (nur laufende Woche)");
  ok(now.indexOf("Bewertet für") < now.indexOf('class="pwsess"'), "0.73.2 T4: die Zeile steht nicht ueber den Einheiten");
  P._coach = { ...F.coach("ready"), trained_today: true };
  const wm = z(P.rPlanWeeks(F.goal()));
  ok(wm.includes(line("morgen")) && !wm.includes(line("heute")), "0.73.2 T4: Zeile 'Bewertet für morgen' nach dem Training fehlt");
  // derselbe Modus wie die Stufenworte an den Chips
  ok(/passt morgen/.test(wm) && /passt heute/.test(wh), "0.73.2 T4: Stufenworte und Zeile folgen nicht demselben Modus");
  // aufgeklappt: die Zeile steht ueber den Karten
  P._planOpen = "1";
  const wo = z(P.rPlanWeeks(F.goal()));
  ok(wo.includes(line("morgen")) && wo.indexOf("Bewertet für") < wo.indexOf('class="wogrid"'), "0.73.2 T4: aufgeklappt fehlt die Zeile ueber den Karten");
}

report("test_panel_views");
})();
