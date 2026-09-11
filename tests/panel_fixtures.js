"use strict";
/* Synthetic payloads shaped exactly like the websocket commands answer. */

const TODAY = "2026-09-11";

function isoWeek(iso) {
  const d = new Date(iso + "T00:00:00");
  const t = new Date(d);
  t.setDate(d.getDate() + 3 - ((d.getDay() + 6) % 7));
  const first = new Date(t.getFullYear(), 0, 4);
  const week = 1 + Math.round(((t - first) / 864e5 - 3 + ((first.getDay() + 6) % 7)) / 7);
  return `${t.getFullYear()}-W${String(week).padStart(2, "0")}`;
}

function days(opts) {
  opts = opts || {};
  const out = { today: TODAY, max_week_load: 420, avg_week_load: 227, days: [], weeks: [] };
  let d = new Date("2026-06-15T00:00:00");
  for (let i = 0; i < 95; i++) {
    const iso = d.toISOString().slice(0, 10);
    const future = iso > TODAY;
    const holes = opts.holes && i % 7 === 3;
    out.days.push({
      date: iso, weekday: (d.getDay() + 6) % 7, week: isoWeek(iso),
      future, today: iso === TODAY,
      ctl: future ? null : 30 + i * 0.05,
      atl: future ? null : 26 + ((i * 7) % 14),
      form: future ? null : 4 - ((i * 7) % 14),
      load: future || i % 3 ? 0 : 70 + (i % 5) * 18,
      // the newest day deliberately has no wellness row yet: that is the
      // morning situation where every card would otherwise look current
      sleep_hours: future || holes || i === 94 - 1 ? null : 6.6 + (i % 4) * 0.35,
      hrv: future || holes || iso === TODAY ? null : 40 + (i % 14),
      resting_hr: future || holes || iso === TODAY ? null : 50 + (i % 6),
      steps: future ? null : 4200 + i * 15,
      activities: (!future && i % 3 === 0) ? [{
        id: "a" + i, name: "volumen", type: i % 6 === 0 ? "VirtualRide" : "Ride",
        group: "ride", sport: "Rad", moving_time: 4800 + i * 8, distance: 32000,
        load: 70 + (i % 5) * 18, intensity: 62, average_heartrate: 138,
        decoupling: i % 6 ? 3.1 : 8.4, zones: [70, 20, 10],
        dfa: i % 2 ? [82, 12, 6] : null,
      }] : [],
      planned: (i % 7 === 4) ? [{
        id: "p" + i, name: "SweetSpot 2x20", type: "Ride", group: "ride",
        load: 74, moving_time: 4100, description: "2x20min",
        // done only in the past: a future session that is already ticked off
        // would leave "next session" empty, which is a separate case below
        done: iso < TODAY && i % 14 === 4,
      }] : [],
    });
    d = new Date(d.getTime() + 864e5);
  }
  for (const w of new Set(out.days.map((x) => x.week))) {
    out.weeks.push({
      week: w, load: 230, seconds: 5 * 3600, distance: 120000, sessions: 3,
      planned_load: 74, ctl: 36, atl: 30, form: 6, hours: 5, km: 120, start: TODAY,
    });
  }
  return out;
}

function load(opts) {
  opts = opts || {};
  const acwr = [];
  let d = new Date("2026-03-02T00:00:00");
  for (let i = 0; i < 193; i++) {
    const iso = d.toISOString().slice(0, 10);
    // one genuine outlier - the case that squashed the chart in 0.9.0
    const ratio = i < 28 ? null : (opts.spike && i === 80 ? 3.9 : 0.7 + ((i * 13) % 70) / 90);
    acwr.push({ date: iso, acute: i < 28 ? null : 20, chronic: i < 28 ? null : 24, ratio });
    d = new Date(d.getTime() + 864e5);
  }
  const hrv = [];
  d = new Date("2026-06-01T00:00:00");
  for (let i = 0; i < 100; i++) {
    hrv.push({ date: d.toISOString().slice(0, 10), ln_rmssd_7d: 3.7 + ((i * 7) % 22) / 100 });
    d = new Date(d.getTime() + 864e5);
  }
  const dcp = [];
  d = new Date("2026-07-20T00:00:00");
  for (let i = 0; i < 34; i++) {
    dcp.push({ date: d.toISOString().slice(0, 10), type: "Ride",
               decoupling: -1 + ((i * 17) % 9), load: 120, hours: 2.4 });
    d = new Date(d.getTime() + 4 * 864e5);
  }
  return {
    weeks: Array.from({ length: 26 }, (_, i) => ({
      week: `2026-W${String(10 + i).padStart(2, "0")}`, load: 150 + ((i * 37) % 150),
      days: 7, days_trained: i % 5 ? 4 : 2, monotony: i % 5 ? 1.4 : 2.3, strain: i % 5 ? 400 : 700,
    })),
    acwr, acwr_latest: { date: TODAY, acute: 18, chronic: 23, ratio: 0.78 },
    ramp_rate: 1.2, form: -6.9, form_percent: -18, form_zone: "grey",
    intensity: { days: 90, sessions: 24, low: 74, middle: 12, high: 14, hours: 60 },
    dfa_distribution: { days: 90, sessions: 20, aerobic: 85, transition: 10, anaerobic: 5, hours: 44 },
    decoupling: dcp,
    hrv: { series: hrv, latest: 3.733, baseline: 3.872, swc: 0.041, state: "below",
           baseline_days: 60, note: "Nachtmessung" },
    thresholds: { acwr_low: 0.8, acwr_high: 1.3, acwr_risk: 1.5, monotony_watch: 2,
                  decoupling_good: 5, polarized_low: 75, polarized_middle: 8 },
  };
}

function readiness() {
  return {
    overall: "red",
    components: [
      { id: "hrv", label: "Herzratenvariabilität", state: "red", value: 3.733, reference: 3.872, detail: "deutlich unter der Basislinie", source: "Q1" },
      { id: "rhr", label: "Ruhepuls", state: "green", value: 50, reference: 57, detail: "unauffällig", source: "Q2" },
      { id: "sleep", label: "Schlaf", state: "green", value: 7.45, reference: 7.7, detail: "im gewohnten Rahmen", source: "Q3" },
      { id: "form", label: "Form", state: "amber", value: 41.5, reference: null, detail: "Übergang", source: "Q4" },
      { id: "acwr", label: "Akut zu chronisch", state: "green", value: 0.78, reference: 1.3, detail: "unter dem Korridor", source: "Q5" },
      { id: "monotony", label: "Monotonie", state: "unknown", detail: "zu wenige Einheiten", source: "Q6" },
      { id: "subjective", label: "Eigene Einschätzung", state: "unknown", detail: "nicht erfasst", source: "Q7" },
    ],
    budget: { chronic: 24.1, last_six_days: 2.1, target_ratio: 0.8, recommended: 133,
              steady: 169, corridor_top: 222, risk_top: 258, state: "red" },
    note: "Die Bestandteile sind belegt, ihre Kombination nicht.",
  };
}

function activities(n) {
  return Array.from({ length: n || 40 }, (_, i) => ({
    id: "act" + i,
    start_date_local: `2026-08-${String(1 + (i % 28)).padStart(2, "0")}T09:00:00`,
    type: ["Ride", "VirtualRide", "Walk"][i % 3],
    name: ["volumen", "VO2max 3x4", "Rehburg-Loccum Gehen"][i % 3],
    moving_time: 3600 + i * 60, distance: i % 3 === 2 ? 5000 : 40000,
    total_elevation_gain: i % 3 ? 300 : null, icu_training_load: 9 + i * 3,
    icu_intensity: 26 + i, average_heartrate: 90 + i, max_heartrate: 150,
    icu_average_watts: i % 3 === 2 ? null : 120 + i,
    icu_weighted_avg_watts: i % 3 === 2 ? null : 130 + i,
    calories: 307, decoupling: i % 4 ? 2.1 : 10.6, icu_efficiency_factor: 0.92,
    average_cadence: i % 3 === 2 ? null : 79, device_name: "Garmin",
    dfa: i % 5 ? { samples: 2000, secs_aerobic: 3000, secs_transition: 400,
                   secs_anaerobic: 200, hr_at_threshold: 151, power_at_threshold: 146,
                   threshold_samples: i % 2 ? 43 : 3 } : null,
  }));
}

/* streams with dropouts: zeros in heart rate, power and DFA are gaps in the
 * recording, zeros in cadence and speed are standstill and must survive */
function streams(n) {
  n = n || 600;
  const idx = (i) => i;
  return {
    points: n, sample_secs: 21,
    channels: {
      time: Array.from({ length: n }, (_, i) => i * 21),
      watts: Array.from({ length: n }, (_, i) => (i % 50 === 0 ? 0 : (i % 77 === 0 ? null : 100 + ((i * 13) % 90)))),
      heartrate: Array.from({ length: n }, (_, i) => (i < 5 ? 0 : 120 + ((i * 7) % 40))),
      dfa_a1: Array.from({ length: n }, (_, i) => (i < 8 ? 0.0 : 0.4 + ((i * 11) % 140) / 100)),
      cadence: Array.from({ length: n }, (_, i) => (i % 9 === 0 ? 0 : 60 + ((i * 3) % 40))),
      velocity_smooth: Array.from({ length: n }, (_, i) => (i % 11 === 0 ? 0 : 5 + ((i * 5) % 40) / 10)),
      altitude: Array.from({ length: n }, (_, i) => 40 + ((i * 2) % 300)),
    },
  };
}

function thresholds() {
  const out = [];
  let d = new Date("2026-05-01T00:00:00");
  for (let i = 0; i < 56; i++) {
    out.push({
      date: d.toISOString().slice(0, 10), activity_id: "act" + i,
      // Ride and VirtualRide are the same sport - the filter used to list
      // "Rad" twice because it grouped on the raw type
      type: i % 4 === 3 ? "Walk" : (i % 2 ? "Ride" : "VirtualRide"),
      hr: 150 + ((i * 9) % 22), power: i % 4 === 3 ? null : 135 + ((i * 5) % 25),
      samples: i % 5 ? 12 : 3,
    });
    // two artefacts from the real account: a zero threshold, and a walk read
    // off a single sample - both used to stretch the axis from 0 to 160
    if (i === 12) out[out.length - 1] = { ...out[out.length - 1], hr: 0, power: null, samples: 8 };
    if (i === 30) out[out.length - 1] = { ...out[out.length - 1], type: "Walk", hr: 90, power: null, samples: 1 };
    d = new Date(d.getTime() + 3 * 864e5);
  }
  return out;
}

function calendar() {
  return [
    { uid: "1", summary: "SweetSpot Erhalt 1x20", description: "1x20min @ 90%",
      start: "2026-09-11 17:00:00", end: "2026-09-11 17:40:00", all_day: false,
      category: "WORKOUT", type: "Ride", load: 47, moving_time: 2400, intensity: 80, completed: false },
    { uid: "2", summary: "volumen", description: null, start: "2026-09-13", end: "2026-09-14",
      all_day: true, category: "WORKOUT", type: "Ride", load: 45, moving_time: 3600,
      intensity: null, completed: false },
  ];
}

function pmc(daysObj) {
  return daysObj.days.filter((d) => !d.future)
    .map((d) => ({ date: d.date, ctl: d.ctl, atl: d.atl, form: d.form, load: d.load }));
}

/* laps as the panel receives them from intervals_icu/laps. The field names
 * on the API side are undocumented, so the normaliser accepts several - the
 * python side is tested separately; here the already-normalised shape is
 * used, including the awkward cases: rest laps without power, laps without
 * DFA, and a series whose efficiency factor fades (real fatigue signature). */
function laps(kind) {
  if (kind === "empty") return { laps: [], seen_keys: [], source: null };
  if (kind === "error") return { error: "HTTP 500" };
  if (kind === "noPower") {
    return { source: "laps", seen_keys: ["name"], laps: [
      { n: 1, label: "Runde 1", moving_time: 1800, avg_hr: 95 },
      { n: 2, label: "Runde 2", moving_time: 1500, avg_hr: 98 },
    ] };
  }
  // the VO2max session from the screenshots: EF fades 1.49 -> 1.37
  return { source: "icu_intervals", seen_keys: ["label", "moving_time", "average_watts"], laps: [
    { n: 1, label: "Aufwärmen", moving_time: 989, avg_watts: 118, avg_hr: 123, avg_cadence: 76, zone: "Z1", ef: 1.12, dfa_a1: 1.44 },
    { n: 2, label: "4x", moving_time: 237, avg_watts: 259, avg_hr: 170, avg_cadence: 88, zone: "Z5", ef: 1.49, dfa_a1: 0.85 },
    { n: 3, label: "Pause", moving_time: 185, avg_watts: 91, avg_hr: 155, avg_cadence: 70, zone: "Z1", ef: 0.84, dfa_a1: 0.97 },
    { n: 4, label: "4x", moving_time: 235, avg_watts: 251, avg_hr: 174, avg_cadence: 89, zone: "Z5", ef: 1.42, dfa_a1: 0.77 },
    { n: 5, label: "Pause", moving_time: 186, avg_watts: 91, avg_hr: 161, avg_cadence: 69, zone: "Z1", ef: 0.79, dfa_a1: 0.82 },
    { n: 6, label: "4x", moving_time: 235, avg_watts: 250, avg_hr: 178, avg_cadence: 88, zone: "Z5", ef: 1.38, dfa_a1: 0.64 },
    { n: 7, label: "Pause", moving_time: 184, avg_watts: 89, avg_hr: 164, avg_cadence: 68, zone: "Z1", ef: 0.76, dfa_a1: 0.58 },
    { n: 8, label: "4x", moving_time: 235, avg_watts: 249, avg_hr: 178, avg_cadence: 87, zone: "Z5", ef: 1.37, dfa_a1: 0.59 },
    { n: 9, label: "Ausfahren", moving_time: 487, avg_watts: 92, avg_hr: 149, avg_cadence: 65, zone: "Z1", ef: 0.73, dfa_a1: 0.90 },
    { n: 10, label: "Rollen", moving_time: 40, avg_hr: 120 },
  ] };
}

/* coach payloads, one per state the backend can report */
function coach(kind) {
  const anchors = { aerobic_hr: 157, aerobic_power: 158, n: 30,
    trend_power: { power_before: 155, power_now: 158, hr_before: 157, hr_now: 157,
                   power_change_pct: 2.2, hr_change: -0.4 },
    source: "Median der letzten fünf belastbaren DFA-Messungen (Rogers/Gronwald)" };
  const base = {
    plan: ["Grundlage, gleichmäßig", "Regeneration, ganz locker", "Grundlage, gleichmäßig",
           "Zügige Dauerfahrt", "Regeneration, ganz locker", "Grundlage, gleichmäßig",
           "SweetSpot / Schwelle"].map((title, i) => ({
      date: `2026-09-${String(11 + i).padStart(2, "0")}`,
      key: i === 6 ? "sweetspot" : (i % 2 ? "recovery" : "endurance"),
      title, minutes: [60, 120], hr_window: [138, 152],
      effect: "Reiz für Kapillarisierung und mitochondriale Dichte." })),
    sessions: {
      rest: { title: "Ruhetag", effect: "Anpassung passiert in der Erholung.", dfa: null, hr_window: null },
      recovery: { title: "Regeneration, ganz locker", effect: "Durchblutung ohne Reiz.", dfa: "über 1,0", hr_window: [113, 129] },
      endurance: { title: "Grundlage, gleichmäßig", effect: "Kapillarisierung, Mitochondrien, Fettstoffwechsel.", dfa: "0,75–1,0", hr_window: [138, 152] },
      tempo: { title: "Zügige Dauerfahrt", effect: "Schiebt die aerobe Schwelle nach oben.", dfa: "um 0,75", hr_window: [152, 160] },
      sweetspot: { title: "SweetSpot / Schwelle", effect: "Wirksamster Reiz für die Schwellenleistung.", dfa: "0,5–0,75", hr_window: [160, 173] },
      vo2max: { title: "VO2max-Intervalle", effect: "Stärkster Reiz auf die Sauerstoffaufnahme.", dfa: "unter 0,5", hr_window: [170, 188] },
    },
    evidence: { rule: "Javaloyes 2019/2020, Vesterinen 2016 — HRV-gesteuerte Steuerung.",
                limit: "Düking 2021: kleiner, nicht signifikanter Effekt auf die Spitzenleistung.",
                own_data: "Schwellen aus eigenen DFA-Messungen." },
  };
  const durability = { n: 73, short: 0.0, long: 0.4, verdict: "die aerobe Basis trägt auch lange Einheiten",
                       source: "Friel: bis 5 % Entkopplung" };
  const states = {
    ready: { state: "ready", label: "im Normalbereich", since: null, week_z: 0.3,
             recent_hrv_z: 0.4, recent_rhr_z: -0.2, confidence: "mittel",
             detail: "Das 7-Tage-Mittel liegt in deinem Normalband." },
    rebound: { state: "rebound", label: "Erholung nach Einbruch", since: "2026-09-06", week_z: -0.63,
               recent_hrv_z: 1.5, recent_rhr_z: -1.8, confidence: "mittel",
               detail: "Der Einbruch war vor 5 Tagen. Das 7-Tage-Mittel hinkt noch nach." },
    slump: { state: "slump", label: "Einbruch", since: "2026-09-11", week_z: -1.9,
             recent_hrv_z: -2.4, recent_rhr_z: 2.9, confidence: "hoch",
             detail: "Deine Werte sind heute deutlich außerhalb deines Normalbereichs." },
    unknown: { state: "unknown", label: "zu wenig Historie", since: null, week_z: null,
               recent_hrv_z: null, recent_rhr_z: null, confidence: "keine",
               detail: "unter drei Wochen Wellness-Daten" },
  };
  if (kind === "slump") {
    return { ...base, recommendation: { key: "rest", title: "Ruhetag", minutes: 0, hr_window: null,
      power_window: null, expected_dfa: null, effect: "Keine Anpassung, sondern die Bedingung dafür.",
      estimated_load: 0, fits_budget: null, state: states.slump, layoff: { days: 0, phase: null, note: null },
      anchors, durability, habit: null,
      reasons: [{ weil: "Einbruch", quelle: "Plews/Altini", text: "Werte außerhalb des Normalbereichs." }],
      warnings: [] } };
  }
  if (kind === "rebound") {
    return { ...base, recommendation: { key: "endurance", title: "Grundlage, gleichmäßig",
      minutes: [60, 120], hr_window: [138, 152], power_window: [139, 153], expected_dfa: "meist 0,75–1,0",
      effect: "Reiz für Kapillarisierung und mitochondriale Dichte.", estimated_load: 45,
      fits_budget: true, state: states.rebound,
      layoff: { days: 7, last: "2026-09-04", phase: "wiedereinstieg",
                note: "Bis etwa zwei Wochen Pause kostet vor allem das Plasmavolumen Leistung." },
      anchors, durability, habit: { n: 6, median_intensity: 85, hard_share: 83 },
      reasons: [{ weil: "7 Tage ohne Einheit", quelle: "Mujika/Coyle", text: "Plasmavolumen, kein Trainingsverlust." },
                { weil: "Erholung nach Einbruch", quelle: "Plews", text: "Signal zum Wiedereinstieg, nicht zur Intensität." }],
      warnings: ["Nach einem Infekt gilt: stufenweise aufbauen und bei wiederkehrenden Symptomen abbrechen.",
                 "Dein eigenes Muster: nach 6 Pausen lag die erste Einheit im Median bei 85 % Intensität."] } };
  }
  if (kind === "unknown") {
    return { ...base, plan: [], recommendation: { key: "endurance", title: "Grundlage, gleichmäßig",
      minutes: [60, 120], hr_window: null, power_window: null, expected_dfa: "meist 0,75–1,0",
      effect: "Reiz für Kapillarisierung.", estimated_load: null, fits_budget: null,
      state: states.unknown, layoff: { days: null, phase: null, note: null },
      anchors: { aerobic_hr: null, aerobic_power: null, n: 1, trend_power: null,
                 source: "zu wenige belastbare DFA-Messungen" },
      durability: null, habit: null, reasons: [], warnings: [] } };
  }
  return { ...base, recommendation: { key: "sweetspot", title: "SweetSpot / Schwelle",
    minutes: [45, 75], hr_window: [160, 173], power_window: [161, 174], expected_dfa: "0,5–0,75 in den Blöcken",
    effect: "Der wirksamste Reiz für die Leistung an der zweiten Schwelle.", estimated_load: 54,
    fits_budget: false, state: states.ready, layoff: { days: 1, phase: null, note: null },
    anchors, durability, habit: { n: 6, median_intensity: 85, hard_share: 83 },
    reasons: [{ weil: "im Normalbereich", quelle: "Javaloyes", text: "Ein harter Reiz ist möglich." }],
    warnings: [] } };
}

/* the signal matrix as intervals_icu/signals returns it, including the real
 * September sequence: normal -> slump -> still down -> rebound */
function signals(kind) {
  const out = { days: [], swc: 0.5, bands: [],
    signals: {
      hrv: { label: "Herzratenvariabilität", unit: "ms", read: "Höher als deine Basislinie heißt meist erholt.",
             source: "Plews/Buchheit und Altini: 7-Tage-Mittel gegen ein 60-Tage-Band." },
      rhr: { label: "Ruhepuls", unit: "bpm", read: "Niedriger ist besser, die Kurve ist gespiegelt.",
             source: "Niederschwelliger Zusatzindikator, ersetzt die HRV nicht." },
      sleep: { label: "Schlaf", unit: "h", read: "Ein kurzer Schlaf sagt wenig, mehrere sind ein Signal.",
               source: "Dauer aus der Uhr geschätzt." },
      form: { label: "Form (TSB)", unit: "", read: "Fitness minus Ermüdung.",
              source: "Joe Friel; Faustregel, keine Wissenschaft." },
    },
    load_signals: {
      acwr: { label: "Akut zu chronisch", unit: "", read: "Korridor 0,8–1,3.",
              source: "Gabbett/Blanch, umstritten." },
      load: { label: "Tageslast", unit: "", read: "Farbe zeigt die gefahrenen DFA-Bereiche.",
              source: "Rogers/Gronwald." },
    } };
  if (kind === "leer") return { ...out, days: [] };
  const N = kind === "kurz" ? 6 : 120;
  let d = new Date("2026-05-15T00:00:00");
  for (let i = 0; i < N; i++) {
    const iso = d.toISOString().slice(0, 10);
    const last = N - i;
    let state = "ready", hrvZ = 0.2 + ((i * 7) % 9 - 4) / 10, rhrZ = 0.1, raw = { hrv: 50, rhr: 56, sleep: 7.4, form: 2 };
    if (last <= 7 && last > 4) { state = "slump"; hrvZ = -2.6; rhrZ = -1.9; raw = { hrv: 31, rhr: 64, sleep: 6.3, form: 8 }; }
    else if (last <= 4 && last > 2) { state = "recovering"; hrvZ = -0.4; rhrZ = 0.3; raw = { hrv: 46, rhr: 56, sleep: 10.1, form: 12 }; }
    else if (last <= 2) { state = "rebound"; hrvZ = 1.9; rhrZ = 2.1; raw = { hrv: 63, rhr: 51, sleep: 9.5, form: 13 }; }
    const holes = kind === "luecken" && i % 5 === 2;
    const hasSession = !holes && i % 3 === 0 && last > 7;
    out.days.push({
      date: iso, state,
      z: holes ? {} : { hrv: +hrvZ.toFixed(2), rhr: +rhrZ.toFixed(2), sleep: 0.3, form: -0.2 },
      raw: holes ? {} : raw,
      acwr: i < 28 ? null : 0.9 + ((i * 11) % 40) / 100,
      load: hasSession ? 60 + (i % 4) * 20 : 0,
      hard: hasSession && i % 9 === 0,
      activities: hasSession ? [{ id: "a" + i, name: "volumen", group: "ride", sport: "Rad",
        load: 60, intensity: i % 9 === 0 ? 88 : 62, minutes: 75,
        dfa_bands: kind === "ohnedfa" ? null : [82, 12, 6],
        hr: 140, watts: 135, decoupling: 1.2 }] : [],
    });
    d = new Date(d.getTime() + 864e5);
  }
  return out;
}

/* concrete sessions as intervals_icu/workouts returns them */
function workouts(kind) {
  const mk = (key, title, purpose, minutes, load, blocks, text, hr, fits) => ({
    key, title, purpose, minutes, load, blocks,
    blocks_w: blocks.map(([m, p, l]) => [m, Math.round(215 * p / 100), l]),
    text, hr_window: hr, fits_budget: fits,
    dfa: "unter 0,5 in den Blöcken", intensity: 90,
    effect: "Hält dich länger nahe der maximalen Sauerstoffaufnahme.",
    evidence: "Rønnestad: 3 Sätze à 13×30 s / 15 s, signifikant größere Zuwächse.",
    limit: "Protokollnamen sind keine Verschreibungen.",
  });
  if (kind === "leer") return { ftp: null, aerobic_hr: null, budget: null, state: "unknown", workouts: [] };
  if (kind === "ohneFTP") {
    const w = mk("z2_60", "Grundlage 60 min", "Aerobe Basis", 60, 45,
      [[10, 55, "Einrollen"], [45, 68, "gleichmäßig"], [5, 50, "Ausrollen"]],
      "- 10m 55%\n- 45m 65-70%\n- 5m 50%", null, null);
    delete w.blocks_w;
    return { ftp: null, aerobic_hr: null, budget: null, state: "ready", workouts: [w] };
  }
  return {
    ftp: 215, aerobic_hr: 157, budget: 90, state: "ready",
    workouts: [
      mk("vo2_3015", "30/15 nach Rønnestad", "Maximale Sauerstoffaufnahme", 62, 98,
         [[15, 55, "Einrollen"], [10, 112, "Satz 1"], [3, 45, "Satzpause"], [10, 112, "Satz 2"],
          [3, 45, "Satzpause"], [10, 112, "Satz 3"], [8, 50, "Ausrollen"]],
         "- 15m 55% 85rpm\n\n3x\n13x\n- 30s 110-115% 95rpm\n- 15s 55%\n\n- 3m 45%\n\n- 8m 50%",
         [170, 185], false),
      mk("sweetspot_2x20", "SweetSpot 2×20 min", "Schwellenleistung", 70, 78,
         [[12, 55, "Einrollen"], [20, 90, "Block 1"], [6, 55, "Pause"], [20, 90, "Block 2"], [8, 50, "Ausrollen"]],
         "- 12m 55% 85rpm\n\n2x\n- 20m 88-93% 88rpm\n- 6m 55%\n\n- 8m 50%", [160, 170], true),
      mk("z2_60", "Grundlage 60 min", "Aerobe Basis", 60, 45,
         [[10, 55, "Einrollen"], [45, 68, "gleichmäßig"], [5, 50, "Ausrollen"]],
         "- 10m 55% 85rpm\n- 45m 65-70% 85rpm\n- 5m 50%", [138, 152], true),
    ],
  };
}

module.exports = { TODAY, days, load, readiness, activities, streams, thresholds, calendar, pmc, laps, coach, signals, workouts };
