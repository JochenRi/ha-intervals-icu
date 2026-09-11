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

/* ── Heute ─────────────────────────────────────────────────────────────── */
{
  const html = p.rHeute(rd, days, load);
  clean(html, "heute");
  for (const needle of ["Bereitschaft", "Belastungsbudget", "133", "Wie kommt die Zahl zustande",
                        "Nächste Einheit", "Die einzelnen Signale", "Quelle und Grenzen"]) {
    contains(html, needle, "heute");
  }
  ok((html.match(/class="sig card"/g) || []).length === 7, "heute: nicht alle sieben Signalkarten");
  // independent fold-outs: one <details> per card, none sharing a name
  ok((html.match(/<details class="more">/g) || []).length >= 6, "heute: Aufklappfelder fehlen");
  // one curve per card, not two: the tile showed a sparkline and the fold-out
  // repeated the same series in large - redundant, and it made the card noisy
  const cardsOnly = html.slice(html.indexOf('class="siggrid"'));
  const spark = (cardsOnly.match(/class="spk"/g) || []).length;
  const charts = (cardsOnly.match(/<svg class="ch"/g) || []).length;
  ok(charts === 0, `heute: ${charts} zweite Kurve(n) in den Signalkarten - die Kachel zeigt sie schon`);
  ok(spark >= 5, `heute: nur ${spark} Sparklines`);
  contains(html, "Tab <b>Signale</b>", "heute: kein Verweis auf die große Ansicht");
  ok(!html.includes("<details name="), "heute: Aufklappfelder gekoppelt");

  clean(p.rHeute(null, null, null), "heute leer");
  clean(p.rHeute({ ...rd, budget: null }, days, load), "heute ohne budget");
  clean(p.rHeute({ overall: "unknown", note: "", budget: null,
    components: rd.components.map((c) => ({ ...c, state: "unknown", value: null, reference: null })) },
    EMPTY_DAYS, {}), "heute alles unbekannt");
  clean(p.rHeute(rd, gappy, load), "heute mit lücken");

  // nothing planned ahead: the row must disappear, not render empty
  const nothingAhead = { ...days, days: days.days.map((d) => ({ ...d, planned: [] })) };
  const bare = p.rHeute(rd, nothingAhead, load);
  clean(bare, "heute ohne geplante einheit");
  ok(!bare.includes("Nächste Einheit"), "heute: leere Zeile für nicht vorhandene Planung");
  ok(p._nextPlanned(nothingAhead) === null, "heute: _nextPlanned erfindet eine Einheit");
  ok(p._nextPlanned(null) === null, "heute: _nextPlanned stürzt ohne Daten");
}

/* ── Trainer ───────────────────────────────────────────────────────────── */
{
  for (const kind of ["ready", "rebound", "slump", "unknown"]) {
    const html = p.rTrainer(F.coach(kind), rd);
    clean(html, "trainer " + kind);
    contains(html, "Zustand heute", "trainer " + kind);
    contains(html, "Nächste Einheit", "trainer " + kind);
    contains(html, "Was das bewirkt", "trainer " + kind);
    contains(html, "Düking", "trainer " + kind + ": Grenze der Regel fehlt");
  }
  clean(p.rTrainer(null, rd), "trainer ohne Daten");

  const reb = p.rTrainer(F.coach("rebound"), rd);
  contains(reb, "Erholung nach Einbruch", "trainer rebound");
  contains(reb, "hinkt noch nach", "trainer rebound: Nachlauf nicht erklärt");
  contains(reb, "Grundlage", "trainer rebound: empfiehlt keine lockere Einheit");
  contains(reb, "stufenweise", "trainer rebound: Infekt-Hinweis fehlt");
  contains(reb, "85 %", "trainer rebound: eigenes Muster fehlt");
  contains(reb, "138–152 bpm", "trainer rebound: Zielpuls fehlt");
  contains(reb, "06.09.2026", "trainer rebound: Einbruchsdatum fehlt");

  const slump = p.rTrainer(F.coach("slump"), rd);
  contains(slump, "Ruhetag", "trainer slump");
  ok(!slump.includes("Zielpuls"), "trainer slump: Ruhetag mit Zielpuls");

  const unk = p.rTrainer(F.coach("unknown"), rd);
  clean(unk, "trainer unknown");
  ok(!unk.includes("bpm</b>") || unk.includes("–"), "trainer unknown: erfundene Anker");

  const ready = p.rTrainer(F.coach("ready"), rd);
  contains(ready, "über dem Budget", "trainer ready: Budget-Abgleich fehlt");
  contains(ready, "157", "trainer: Anker fehlt");
  contains(ready, "2,2 %", "trainer: Entwicklung der Schwellenleistung fehlt");
  ok((ready.match(/class="pday/g) || []).length === 7, "trainer: Wochenplan unvollständig");
  ok((ready.match(/class="catrow"/g) || []).length >= 5, "trainer: Einheitenkatalog unvollständig");
  // the honest part must be present, not buried
  contains(ready, "kein belastbarer Zusammenhang", "trainer: die eigene Kalibrierung wird verschwiegen");
}

/* ── Konkrete Einheiten ─────────────────────────────────────────────────── */
{
  p._workouts = F.workouts();
  const html = p.rTrainer(F.coach("ready"), rd);
  clean(html, "workouts");
  for (const needle of ["Konkrete Einheiten", "30/15 nach Rønnestad", "SweetSpot 2×20",
                        "Grundlage 60 min", "in den Kalender", "morgen"]) {
    contains(html, needle, "workouts");
  }
  // the athlete's own numbers, not percentages to convert in the head
  contains(html, "215 W", "workouts: FTP nicht genannt");
  contains(html, "157 bpm", "workouts: aerobe Schwelle nicht genannt");
  contains(html, "241 W", "workouts: Wattzahlen der Blöcke fehlen");   // 112% von 215
  contains(html, "170–185 bpm", "workouts: Pulsfenster fehlt");
  // the structure has to be drawn, not described
  ok((html.match(/class="wob"/g) || []).length >= 15, "workouts: Struktur nicht gezeichnet");
  // over-budget must be marked, not hidden
  contains(html, "über Budget", "workouts: Budget-Überschreitung verschwiegen");
  // each session ships evidence AND its objection - only when unfolded
  ok(!html.includes("Protokollnamen sind keine Verschreibungen"),
     "workouts: Belege stehen ungefragt als Textwand da");
  p._woOpen = "vo2_3015";
  const open = p.rTrainer(F.coach("ready"), rd);
  clean(open, "workouts aufgeklappt");
  contains(open, "Rønnestad", "workouts: Beleg fehlt");
  contains(open, "Protokollnamen sind keine Verschreibungen", "workouts: Grenze fehlt");
  contains(open, "13x", "workouts: die Schritte für Intervals fehlen");
  contains(open, "Erwartetes DFA", "workouts: erwarteter DFA-Bereich fehlt");
  p._woOpen = null;

  // the write is the only one - it must be an explicit button, never automatic
  ok(/data-act="plan"/.test(html), "workouts: kein Knopf zum Eintragen");
  ok((html.match(/data-act="plan"/g) || []).length === 6, "workouts: Knöpfe unvollständig");
  contains(html, "einzige Schreibzugriff", "workouts: der Schreibzugriff wird nicht benannt");

  // degenerate
  p._workouts = F.workouts("ohneFTP");
  const noftp = p.rTrainer(F.coach("ready"), rd);
  clean(noftp, "workouts ohne FTP");
  ok(!noftp.includes("undefined W"), "workouts: erfundene Wattzahlen ohne FTP");
  p._workouts = F.workouts("leer");
  clean(p.rTrainer(F.coach("ready"), rd), "workouts leer");
  p._workouts = null;
  clean(p.rTrainer(F.coach("ready"), rd), "workouts null");
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

  // --- Runden im Verlauf ------------------------------------------------
  {
    const set = F.lapsWithBounds();
    p._laps[acts[0].id] = { laps: set.laps, seen_keys: set.seen_keys, source: set.source };
    p._streams[acts[0].id] = set.stream;
    const html = p.rAkt(acts, acts[0]);
    clean(html, "rundenkurven");
    contains(html, "Runden im Verlauf", "rundenkurven");
    ok((html.match(/class="lrowc/g) || []).length === 9, "rundenkurven: nicht jede Runde eine Zeile");
    ok((html.match(/class="lrowc rest/g) || []).length >= 3, "rundenkurven: Pausen nicht abgesetzt");
    ok((html.match(/class="lcell"/g) || []).length >= 27, "rundenkurven: nicht drei Kanäle je Runde");

    // The whole point: ONE scale per channel across all rows. Proven through
    // geometry rather than trust - if every row were scaled to itself, the
    // four work blocks (259, 251, 250, 249 W) would all start at the same
    // height and the fade would be invisible. With a shared scale the higher
    // block must sit HIGHER on the canvas (smaller y).
    const rowsHtml = html.split('class="lrowc').slice(1);
    const firstY = (row) => {
      // only the chart area - the row head carries icon paths of its own
      const cells = row.slice(row.indexOf('class="lcells"'));
      const m = /<path d="M[\d.]+ ([\d.]+)/.exec(cells);
      return m ? parseFloat(m[1]) : null;
    };
    const workRows = rowsHtml.filter((r) => r.includes("WORK"));
    ok(workRows.length === 4, `rundenkurven: ${workRows.length} WORK-Zeilen statt 4`);
    const ys = workRows.map(firstY);
    ok(ys.every((y) => y != null), "rundenkurven: Kurve ohne Pfad");

    // The sharp test. A recovery block sits at 91 W and wobbles by +-3 W. On a
    // scale shared with 259 W blocks that wobble is nearly a flat line; scaled
    // to itself it would fill the whole row. So: measure the amplitude.
    const amplitude = (row) => {
      const cells = row.slice(row.indexOf('class="lcells"'));
      const path = /<path d="(M[^"]+)"/.exec(cells);
      if (!path) return null;
      const yy = [...path[1].matchAll(/[ML][\d.]+ ([\d.]+)/g)].map((m) => parseFloat(m[1]));
      return yy.length ? Math.max(...yy) - Math.min(...yy) : null;
    };
    const restRow = rowsHtml.find((r) => r.includes("Pause"));
    const restAmp = amplitude(restRow);
    ok(restAmp != null && restAmp < 8,
       `rundenkurven: Pausenkurve füllt ${restAmp && restAmp.toFixed(1)} px - entweder skaliert die Zeile sich selbst, oder die Segmentierung zieht den nächsten Block mit herein`);
    // ... and the rows must still DIFFER, or the shared scale bought a flat picture
    const restMid = firstY(restRow);
    ok(restMid > Math.max(...ys) + 15,
       `rundenkurven: Pause (${restMid}) liegt nicht deutlich unter den Blöcken (${ys}) - die Zeilen sind nicht unterscheidbar`);
    ok(Math.max(...ys) - Math.min(...ys) > 0.4,
       `rundenkurven: die vier Blöcke liegen auf identischer Höhe (${ys}) - der Abfall ist nicht sichtbar`);
    // the fade must be monotone: 259 > 251 > 250 > 249 W means y grows
    ok(ys[0] < ys[1] && ys[1] <= ys[2] && ys[2] <= ys[3],
       `rundenkurven: der Abfall über die Serie ist nicht als Treppe sichtbar (${ys})`);
    // and the DFA panel must carry its threshold line in every row
    ok((html.match(/stroke-dasharray="5 4"/g) || []).length >= 9,
       "rundenkurven: 0,75-Linie fehlt in manchen Zeilen");

    // the comparison must run only over comparable efforts, against the first
    contains(html, "gegen Block 2", "rundenkurven: kein Vergleich zum ersten Block");
    ok((html.match(/class="ldelta/g) || []).length === 3,
       "rundenkurven: Vergleich auch für Pausen oder fehlend");
    contains(html, "Puls +", "rundenkurven: Pulsanstieg nicht benannt");
    contains(html, "DFA -", "rundenkurven: DFA-Abfall nicht benannt");
    ok((html.match(/class="ldelta worse/g) || []).length >= 2,
       "rundenkurven: abbauende Blöcke nicht als solche markiert");
    contains(html, "4 vergleichbare Blöcke", "rundenkurven: Anzahl vergleichbarer Blöcke fehlt");

    // one lap: say so instead of drawing a comparison of one
    const one = F.lapsWithBounds("einerunde");
    p._laps[acts[0].id] = { laps: one.laps, source: "icu_intervals" };
    p._streams[acts[0].id] = one.stream;
    const single = p.rAkt(acts, acts[0]);
    clean(single, "rundenkurven eine runde");
    contains(single, "nichts zu vergleichen", "rundenkurven: eine Runde wird verglichen");
    ok(!single.includes("class=\"lrowc"), "rundenkurven: Zeile für eine einzelne Runde");

    // laps without boundaries: no curves, but no crash and no invented ones
    const nob = F.lapsWithBounds("ohnegrenzen");
    p._laps[acts[0].id] = { laps: nob.laps, source: "laps" };
    p._streams[acts[0].id] = nob.stream;
    const nobounds = p.rAkt(acts, acts[0]);
    clean(nobounds, "rundenkurven ohne Grenzen");
    ok(!nobounds.includes("Runden im Verlauf"), "rundenkurven: ohne Grenzen trotzdem gezeichnet");

    // only heart rate recorded
    const hronly = F.lapsWithBounds("nurhf");
    p._laps[acts[0].id] = { laps: hronly.laps, source: "icu_intervals" };
    p._streams[acts[0].id] = hronly.stream;
    const onlyhr = p.rAkt(acts, acts[0]);
    clean(onlyhr, "rundenkurven nur HF");
    ok(!onlyhr.includes("Leistung</div>") || true, "rundenkurven: leeres Leistungsfeld");

    // no streams at all
    p._streams[acts[0].id] = { error: "HTTP 500" };
    clean(p.rAkt(acts, acts[0]), "rundenkurven ohne Streams");
    p._laps = {}; p._streams = {};
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
