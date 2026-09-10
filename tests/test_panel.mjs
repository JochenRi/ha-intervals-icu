/**
 * Runs the panel web component in a stubbed DOM and checks what it renders
 * from payloads shaped like the live account's.
 */
const failures = [];
function check(label, got, expected) {
  const ok = JSON.stringify(got) === JSON.stringify(expected);
  console.log(`${ok ? "PASS" : "FAIL"}  ${label}: ${JSON.stringify(got)}` +
    (ok ? "" : `  (erwartet ${JSON.stringify(expected)})`));
  if (!ok) failures.push(label);
}

// --- minimal DOM ---------------------------------------------------------------
const registry = {};
globalThis.HTMLElement = class {
  attachShadow() {
    this.shadowRoot = {
      innerHTML: "",
      querySelectorAll: () => [],
      querySelector: () => null,
    };
    return this.shadowRoot;
  }
  dispatchEvent() {}
};
globalThis.customElements = {
  define: (name, cls) => { registry[name] = cls; },
  get: (name) => registry[name],
};
globalThis.Event = class { constructor(type) { this.type = type; } };

await import("./js/intervals-panel.mjs");
check("Element registriert", Object.keys(registry), ["intervals-icu-panel"]);

// --- payloads in the shape the WebSocket commands return ------------------------
const pmc = [];
for (let i = 0; i < 486; i += 1) {
  const d = new Date(Date.UTC(2025, 4, 13));
  d.setUTCDate(d.getUTCDate() + i);
  const ctl = 20 + i * 0.03;
  const atl = ctl * (i % 9 === 0 ? 1.4 : 0.8);
  pmc.push({ date: d.toISOString().slice(0, 10), ctl, atl, form: ctl - atl, load: i % 4 ? 0 : 93 });
}
const activities = [
  { id: "i184858441", start_date_local: "2026-09-09T11:07:27", type: "Walk",
    name: "Rehburg-Loccum Gehen", moving_time: 4250, distance: 5018.86,
    icu_training_load: 9, average_heartrate: 90,
    dfa: { secs_aerobic: 3400, secs_transition: 120, secs_anaerobic: 20,
           hr_at_threshold: 141.0, power_at_threshold: null, threshold_samples: 8 } },
  { id: "i183165529", start_date_local: "2026-09-04T09:00:00", type: "Ride",
    name: "volumen <script>", moving_time: 12503, distance: 71000,
    icu_training_load: 129, average_heartrate: 142, decoupling: 3.4,
    icu_weighted_avg_watts: 200, icu_average_watts: 169, trimp: 210,
    dfa: { secs_aerobic: 12360, secs_transition: 120, secs_anaerobic: 20,
           hr_at_threshold: 148.0, power_at_threshold: 192.0, threshold_samples: 140 } },
];
const calendar = [
  { uid: "1", summary: "volumen", start: "2026-09-04", end: "2026-09-05", type: "Ride",
    load: 136, moving_time: 10800, description: "DFa über 0,8", completed: true },
  { uid: "2", summary: "SweetSpot Erhalt 1x20", start: "2026-09-11", end: "2026-09-12",
    type: "Ride", load: 47, moving_time: 2400, description: "-20m 205w", completed: false },
];
const thresholds = [
  { date: "2026-08-12", activity_id: "a1", type: "Ride", hr: 145, power: 186, samples: 130 },
  { date: "2026-09-04", activity_id: "i183165529", type: "Ride", hr: 148, power: 192, samples: 140 },
  // one sample only - seen on a walk, must not bend the curve
  { date: "2026-09-09", activity_id: "i184858441", type: "Walk", hr: 90, power: null, samples: 1 },
];
const status = { activities: 238, wellness_days: 486, dfa_done: 56, dfa_pending: 0, importing: false };
const loadPayload = {
  weeks: [
    { week: "2026-W35", load: 420, days: 7, days_trained: 4, monotony: 1.2, strain: 504 },
    { week: "2026-W36", load: 380, days: 7, days_trained: 6, monotony: 2.4, strain: 912 },
  ],
  acwr: [
    { date: "2026-09-08", acute: 60, chronic: 55, ratio: 1.09 },
    { date: "2026-09-09", acute: 70, chronic: 55, ratio: 1.27 },
    { date: "2026-09-10", acute: 95, chronic: 55, ratio: 1.73 },
  ],
  acwr_latest: { date: "2026-09-10", acute: 95, chronic: 55, ratio: 1.73 },
  ramp_rate: -2.7,
  form: 13.9,
  form_percent: 41.5,
  form_zone: "fresh",
  intensity: { days: 90, sessions: 40, low: 81.2, middle: 6.1, high: 12.7, hours: 60.4 },
  dfa_distribution: { days: 90, sessions: 30, aerobic: 88.1, transition: 7.2, anaerobic: 4.7, hours: 44.0 },
  decoupling: [{ date: "2026-09-04", type: "Ride", decoupling: 3.4, load: 129, hours: 3.5 }],
  hrv: { series: [], latest: 4.1, baseline: 4.0, swc: 0.05, state: "above", baseline_days: 60,
         note: "overnight wearable HRV, not a morning supine recording" },
  thresholds: { acwr_low: 0.8, acwr_high: 1.3, acwr_risk: 1.5, monotony_watch: 2.0,
                decoupling_good: 5.0, polarized_low: 75.0, polarized_middle: 8.0 },
};

const readiness = {
  overall: "amber",
  components: [
    { id: "hrv", label: "Herzratenvariabilität", state: "amber", value: 3.733, reference: 3.872,
      detail: "unter der Basislinie", source: "7-Tage-Mittel von ln(rMSSD) ..." },
    { id: "rhr", label: "Ruhepuls", state: "green", value: 50, reference: 52.4,
      detail: "unauffällig (-2.4 bpm gegenüber 30-Tage-Mittel)", source: "Ruhepuls ..." },
    { id: "sleep", label: "Schlaf", state: "green", value: 7.45, reference: 7.2,
      detail: "im gewohnten Rahmen (+0.3 h)", source: "Schlaf ..." },
    { id: "form", label: "Form", state: "green", value: 41.5, reference: null,
      detail: "Übergang, lange ohne Reiz", source: "Zonen nach Joe Friel ..." },
    { id: "acwr", label: "Akut zu chronisch", state: "green", value: 0.78, reference: 1.3,
      detail: "unter dem Korridor — Luft nach oben", source: "Korridor 0,8–1,3 ..." },
    { id: "monotony", label: "Monotonie", state: "unknown",
      detail: "noch zu wenige Einheiten in dieser Woche", source: "Foster ..." },
    { id: "subjective", label: "Eigene Einschätzung", state: "unknown", detail: "nicht erfasst",
      source: "Der systematische Review von Saw und Kollegen zeigt ..." },
  ],
  budget: { chronic: 42.5, last_six_days: 180, target_ratio: 1.0, recommended: 118,
            steady: 118, corridor_top: 207, risk_top: 266, state: "amber" },
  note: "Die einzelnen Signale sind belegt, ihre Kombination ist es nicht: ... nicht unabhängig validiert.",
};

// week grid payload, shaped like analytics.calendar_days
const monday = new Date();
monday.setDate(monday.getDate() - ((monday.getDay() + 6) % 7));
const iso = (offset) => {
  const d = new Date(monday);
  d.setDate(d.getDate() + offset);
  return d.toISOString().slice(0, 10);
};
const daysPayload = {
  today: iso(0),
  max_week_load: 300, avg_week_load: 210, max_day_load: 129,
  weeks: [
    { week: "2026-W36", load: 248, hours: 6.2, km: 71, sessions: 3, planned_load: 0,
      ctl: 34, atl: 20, form: 14, start: iso(-7) },
    { week: "2026-W37", load: 83, hours: 1.2, km: 0, sessions: 1, planned_load: 47,
      ctl: 33, atl: 19, form: 14, start: iso(0) },
  ],
  days: [
    { date: iso(-7), weekday: 0, week: "2026-W36", future: false, today: false,
      ctl: 34, atl: 20, form: 14, load: 129, sleep_hours: 7.4, sleep_score: 84, hrv: 63,
      resting_hr: 50, weight: null, steps: 9931,
      activities: [{ id: "i183165529", name: "volumen", type: "Ride", group: "ride", sport: "Rad",
        moving_time: 12503, distance: 71000, load: 129, average_heartrate: 142,
        average_watts: 122, zones: [60, 25, 15], dfa: [99, 1, 0], threshold_hr: 151,
        threshold_samples: 98 }],
      planned: [] },
    { date: iso(0), weekday: new Date().getDay() === 0 ? 6 : new Date().getDay() - 1,
      week: "2026-W37", future: false, today: true,
      ctl: 33, atl: 19, form: 14, load: 83, sleep_hours: 7.45, sleep_score: 84, hrv: 63,
      resting_hr: 50, weight: null, steps: 28,
      activities: [{ id: "a2", name: "SweetSpot 2x20", type: "VirtualRide", group: "ride",
        sport: "Rad (Rolle)", moving_time: 4200, distance: null, load: 83,
        average_heartrate: 149, average_watts: 168, zones: [43, 57, 0], dfa: [71, 21, 7],
        threshold_hr: 168, threshold_samples: 486 }],
      planned: [] },
    { date: iso(1), weekday: 6, week: "2026-W37", future: true, today: false,
      ctl: null, atl: null, form: null, load: null, sleep_hours: null, sleep_score: null,
      hrv: null, resting_hr: null, weight: null, steps: null,
      activities: [],
      planned: [{ id: "p1", name: "SweetSpot Erhalt 1x20", type: "Ride", group: "ride",
        sport: "Rad", load: 47, moving_time: 2400, description: "-20m 205w", done: false }] },
  ],
};

const answers = {
  "intervals_icu/status": status,
  "intervals_icu/pmc": pmc,
  "intervals_icu/activities": activities,
  "intervals_icu/calendar": calendar,
  "intervals_icu/thresholds": thresholds,
  "intervals_icu/load": loadPayload,
  "intervals_icu/readiness": readiness,
  "intervals_icu/days": daysPayload,
};

function makePanel(hass) {
  const panel = new registry["intervals-icu-panel"]();
  panel.connectedCallback();
  panel.hass = hass;
  return panel;
}

const hass = { callWS: async (msg) => answers[msg.type] };
const panel = makePanel(hass);
check("zeigt zuerst einen Ladehinweis", panel.shadowRoot.innerHTML.includes("Lade Archiv"), true);

await new Promise((resolve) => setTimeout(resolve, 10));
let html = panel.shadowRoot.innerHTML;

// --- header and fitness view ------------------------------------------------------
check("Kopfzeile zeigt den Archivstand", html.includes("238 Einheiten · 486 Tage · 56 DFA"), true);
check("sieben Reiter", (html.match(/data-tab=/g) || []).length, 7);
check("Kalender ist der Startreiter", html.includes('data-tab="calendar" class="on"'), true);

// --- Kalender: Wochenraster ------------------------------------------------------------
check("Wochenzeilen gezeichnet", (html.match(/class="wrow"/g) || []).length, 2);
check("sieben Tagesspalten je Woche", (html.match(/class="day /g) || []).length >= 14, true);
check("heute hervorgehoben", html.includes("is-today"), true);
check("Zukunft erkennbar", html.includes("is-future"), true);
check("Wochensumme mit Last", html.includes(">248<") && html.includes(">83<"), true);
check("Wellness-Werte im Tag", html.includes("7.45 h") && html.includes("50"), true);
check("Einheit als Kachel", html.includes("SweetSpot 2x20"), true);
check("Sportfarbe als Kategorie", html.includes("--hue:#4aa8ff"), true);
check("Zonenbalken auf gemeinsamer Grundlinie", (html.match(/class="strip"/g) || []).length >= 2, true);
check("geplante Einheit gestrichelt", html.includes('class="ses plan"'), true);
check("Symbole statt nur Text", html.includes('class="gl"'), true);
check("Legende erklärt Farben", html.includes("gestrichelt = geplant"), true);
check("Kalendereinheiten sind anklickbar", html.includes('data-id="a2"'), true);

panel._tab = "today"; panel._render();
html = panel.shadowRoot.innerHTML;
check("Heute-Reiter aktiv nach Wechsel", html.includes('data-tab="today" class="on"'), true);
check("Ampel gezeichnet", html.includes('class="hero amber"'), true);
check("Urteil im Klartext", html.includes("gelb — Heute eher zurückhaltend trainieren."), true);
check("Lastbudget genannt", html.includes(">118<"), true);
check("Korridorrand genannt", html.includes(">207<"), true);
check("Rechenweg aufklappbar", html.includes("Wie kommt die Zahl zustande"), true);
check("Formel mit echten Zahlen", html.includes("7 × 42.5 × 1 − 180 = 118"), true);
check("geplantes Workout abgeglichen", html.includes("Nächste geplante Einheit") && html.includes(">passt<"), true);
check("alle sieben Signale als Kacheln", (html.match(/class="tile /g) || []).length, 7);
check("fehlende Selbsteinschaetzung als unbekannt", html.includes('class="tile unknown"'), true);
check("Zustand steht als Wort da, nicht nur als Farbe", html.includes(">gelb<") || html.includes(">grün<"), true);
check("Quellen sind eingeklappt", (html.match(/<details class="src">/g) || []).length >= 5, true);
check("Quelle je Signal", html.includes("Saw und Kollegen"), true);
check("Grenzen der Kombination", html.includes("nicht unabhängig validiert"), true);

panel._tab = "fitness"; panel._render();
html = panel.shadowRoot.innerHTML;
check("Fitness-Reiter aktiv nach Wechsel", html.includes('data-tab="fitness" class="on"'), true);
check("Diagramm gezeichnet", html.includes("<svg") && html.includes('class="ctl"'), true);
check("Tagesbelastung als Balken", html.includes('class="load"'), true);
check("Kennzahlen mit Rangfolge", html.includes('class="metric l"') && html.includes("Fitness") && html.includes("Ermüdung"), true);
check("Legende erklaert die Linien", html.includes("über 42 Tage gemittelt"), true);
check("Zonentabelle mit Wertebereichen", html.includes("−30 bis −5"), true);
check("Form-Zonenbaender gezeichnet", (html.match(/<rect[^>]*fill="#[0-9a-f]{6}20"/g) || []).length >= 4, true);
check("aktive Form-Zone markiert", html.includes('class="zrow on"'), true);
check("Aktivitaetspunkte im Diagramm", (html.match(/class="act"/g) || []).length, 2);
check("Quellenangabe zu den Zonen", html.includes("Joe Friel"), true);
check("Form-Umschalter vorhanden", html.includes('id="formmode"'), true);
check("Datumsachse mit Tagen bei kurzem Zeitraum",
  /class="axis mid">\d{2}\.\d{2}\./.test(html), true);

// 365-day window must not draw all 486 points
panel._days = 365; panel._render();
html = panel.shadowRoot.innerHTML;
const points = (html.match(/[ML]\d/g) || []).length;
console.log(`       (Jahresfenster: ${points} Pfadbefehle im SVG)`);
// 365 Tage x 3 Linien + Lastbalken - alles in einem einzigen Pfad je Reihe
check("Jahresfenster zeichnet genau ein Jahr", points > 1000 && points < 1400, true);

panel._days = 42; panel._render();
const short = (panel.shadowRoot.innerHTML.match(/[ML]\d/g) || []).length;
check("42-Tage-Fenster zeichnet weniger", short < points, true);

// --- activities ---------------------------------------------------------------------
panel._tab = "activities"; panel._render();
html = panel.shadowRoot.innerHTML;
check("Aktivitaet gelistet", html.includes("Rehburg-Loccum Gehen"), true);
check("Dauer formatiert", html.includes("3h28m"), true);
check("Distanz formatiert", html.includes("71.0 km"), true);
check("Schwellenleistung angezeigt", html.includes("192 W"), true);
check("DFA-Balken gezeichnet", html.includes('class="dfa"'), true);
check("Fremdtext entschaerft", html.includes("<script>"), false);
check("Fremdtext sichtbar als Text", html.includes("&lt;script&gt;"), true);
check("Zeilen sind anklickbar", html.includes('class="row '), true);
check("Entkopplung als Spalte", html.includes("Entkopplung"), true);

panel._openActivity = "i183165529"; panel._render();
const detail = panel.shadowRoot.innerHTML;
check("Detailansicht geoeffnet", detail.includes('class="card detail"'), true);
check("Detail nach Themen gruppiert", detail.includes("Umfang") && detail.includes("Belastung") && detail.includes("Leistung"), true);
check("Detail zeigt Kennzahlen", detail.includes("Normalisiert") && detail.includes("TRIMP"), true);
check("Detail bewertet die Entkopplung", detail.includes("Leistung zu Puls") && detail.includes("3.4 %") && detail.includes(">solide<"), true);
check("Detail nennt die DFA-Schwelle", detail.includes("148 bpm"), true);
check("schwache Schwelle nicht in der Liste",
  panel.shadowRoot.innerHTML.includes("141 bpm"), false);
panel._openActivity = null;

// --- load ---------------------------------------------------------------------------
panel._tab = "load"; panel._render();
html = panel.shadowRoot.innerHTML;
check("Wochenbalken gezeichnet", (html.match(/class="wbar/g) || []).length, 2);
check("Bezugslinie im Balkendiagramm", html.includes('class="refline"'), true);
check("laufende Woche hervorgehoben", html.includes('class="wbar now"'), true);
check("ACWR-Korridor hinterlegt", html.includes('class="corridor"'), true);
check("Risikolinie beschriftet", html.includes("erhöhtes Risiko"), true);
check("ACWR bewertet", html.includes("deutlich über dem Korridor"), true);
check("Kritik an ACWR benannt", html.includes("Richtigstellung") && html.includes("randomisierte Studie"), true);
check("Intensitaetsverteilung als Balken", html.includes("81.2 %") && html.includes("12.7 %"), true);
check("Muster erkannt", html.includes("polarisiert"), true);
check("Wochenbalken beschriftet", html.includes("W35") || html.includes("W36"), true);
check("DFA-Verteilung ergaenzt", html.includes("88.1 / 7.2 / 4.7 %"), true);
check("HRV-Lage", html.includes("über der Basislinie"), true);
check("HRV-Messmethode eingeordnet", html.includes("Nachtmessung"), true);
check("monotone Woche markiert", html.includes('class="warnrow"'), true);
check("Foster benannt", html.includes("Foster"), true);

// --- calendar -------------------------------------------------------------------------
panel._tab = "plan"; panel._render();
html = panel.shadowRoot.innerHTML;
check("kommende Einheit gelistet", html.includes("SweetSpot Erhalt 1x20"), true);
check("vergangene Einheit ausgeblendet", html.includes(">volumen<"), false);

// --- dfa ------------------------------------------------------------------------------
panel._tab = "dfa"; panel._render();
html = panel.shadowRoot.innerHTML;
check("Schwellenkurve gezeichnet", html.includes('class="dot"'), true);
check("Guete ausgewiesen", html.includes("140 Messpunkte · belastbar"), true);
check("Schwellen-HF gelistet", html.includes("148 bpm"), true);
check("Sportfilter angeboten", html.includes('data-sport="Ride"'), true);
check("Quelle der Schwellenwerte", html.includes("VT1"), true);
panel._sportFilter = "Walk"; panel._render();
check("Filter greift", panel.shadowRoot.innerHTML.includes("Keine belastbare Schwellenmessung"), true);
panel._sportFilter = "all";
check("schwache Messung in der Tabelle markiert", html.includes('class="weak"'), true);
check("schwache Messung nicht in der Kurve",
  (html.match(/class="dot"/g) || []).length, 2);
check("schwache Messung trotzdem sichtbar", html.includes("90 bpm"), true);

// --- empty archive ----------------------------------------------------------------------
const leer = makePanel({ callWS: async (msg) =>
  ({ "intervals_icu/status": { activities: 0, wellness_days: 0, dfa_done: 0, importing: true },
     "intervals_icu/pmc": [], "intervals_icu/activities": [],
     "intervals_icu/calendar": [], "intervals_icu/thresholds": [],
     "intervals_icu/readiness": null, "intervals_icu/days": null })[msg.type] });
await new Promise((resolve) => setTimeout(resolve, 10));
check("leeres Archiv: Kalender meldet fehlende Tage",
  leer.shadowRoot.innerHTML.includes("Noch keine Tagesdaten"), true);
leer._tab = "today"; leer._render();
check("leeres Archiv: Ampel meldet fehlende Daten",
  leer.shadowRoot.innerHTML.includes("Noch keine Bereitschaftsdaten"), true);
leer._tab = "fitness"; leer._render();
check("leeres Archiv stuerzt nicht ab", leer.shadowRoot.innerHTML.includes("Keine Daten"), true);
check("laufender Import wird gemeldet", leer.shadowRoot.innerHTML.includes("Import läuft"), true);

// --- one command fails, the rest keeps working ------------------------------------------
// 0.5.0 asked for everything with Promise.all: a single failing command blanked
// every view with "Unknown error".
const teilweise = makePanel({
  callWS: async (msg) => {
    if (msg.type === "intervals_icu/load") throw new Error("Unknown error");
    return answers[msg.type];
  },
});
await new Promise((resolve) => setTimeout(resolve, 10));
teilweise._tab = "fitness"; teilweise._render();
check("Fitness bleibt trotz Ausfall sichtbar",
  teilweise.shadowRoot.innerHTML.includes('class="ctl"'), true);
check("Ausfall wird benannt", teilweise.shadowRoot.innerHTML.includes("load"), true);
teilweise._tab = "load"; teilweise._render();
check("betroffene Ansicht meldet leer",
  teilweise.shadowRoot.innerHTML.includes("Noch keine Belastungsdaten"), true);

// --- backend error ------------------------------------------------------------------------
const kaputt = makePanel({ callWS: async () => { throw new Error("not_found"); } });
await new Promise((resolve) => setTimeout(resolve, 10));
check("Totalausfall wird als Fehler gezeigt",
  kaputt.shadowRoot.innerHTML.includes("keine Verbindung zur Integration"), true);

console.log("\nFEHLER:", failures.length ? failures : "keine");
process.exit(failures.length ? 1 : 0);
