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
/* laps WITH stream boundaries, plus a matching thinned stream: the indices
 * count in the original 1 Hz recording while the panel holds a 4 s stream,
 * which is exactly where a naive implementation cuts the wrong pieces. */
function lapsWithBounds(kind) {
  const secs = 4;
  const blocks = [
    ["Aufwärmen", 600, 118, 123, 1.30, false],
    ["WORK", 240, 259, 168, 0.88, true],
    ["Pause", 180, 91, 152, 1.05, false],
    ["WORK", 240, 251, 174, 0.78, true],
    ["Pause", 180, 91, 158, 0.95, false],
    ["WORK", 240, 250, 178, 0.64, true],
    ["Pause", 180, 89, 161, 0.90, false],
    ["WORK", 240, 249, 179, 0.59, true],
    ["Ausfahren", 300, 92, 147, 1.10, false],
  ];
  const laps = [];
  const watts = [], hr = [], dfa = [], time = [], cad = [];
  let clock = 0, n = 0;
  for (const [label, len, w, h, d, isWork] of blocks) {
    n += 1;
    laps.push({ n, label, type: isWork ? "WORK" : "RECOVERY",
      start_s: clock, end_s: clock + len, start_index: clock, end_index: clock + len,
      moving_time: len, avg_watts: w, avg_hr: h, dfa_a1: d, zone: isWork ? 5 : 1,
      ef: Math.round((w / h) * 100) / 100, avg_cadence: 78 });
    for (let s = 0; s < len; s += secs) {
      time.push(clock + s);
      // a couple of dropouts, because real recordings have them
      const drop = (clock + s) % 377 === 0;
      watts.push(drop ? 0 : w + ((s / secs) % 7) - 3);
      hr.push(drop ? 0 : h + ((s / secs) % 5) - 2);
      dfa.push(d + (((s / secs) % 9) - 4) / 100);
      cad.push(78);
    }
    clock += len;
  }
  if (kind === "einerunde") {
    return { laps: [laps[0]], seen_keys: ["start_index"], source: "icu_intervals",
             stream: { points: time.length, sample_secs: secs,
                       channels: { time, watts, heartrate: hr, dfa_a1: dfa, cadence: cad } } };
  }
  if (kind === "ohnegrenzen") {
    return { laps: laps.map(({ start_s, end_s, start_index, end_index, ...rest }) => rest),
             seen_keys: [], source: "laps",
             stream: { points: time.length, sample_secs: secs,
                       channels: { time, watts, heartrate: hr, dfa_a1: dfa } } };
  }
  if (kind === "nurhf") {
    return { laps, seen_keys: [], source: "icu_intervals",
             stream: { points: time.length, sample_secs: secs,
                       channels: { time, heartrate: hr } } };
  }
  return { laps, seen_keys: ["start_index", "end_index"], source: "icu_intervals",
           stream: { points: time.length, sample_secs: secs,
                     channels: { time, watts, heartrate: hr, dfa_a1: dfa, cadence: cad } } };
}

/* a steady ride with textbook cardiac drift: power flat, heart rate climbing */
function steadyStream(kind) {
  const secs = 4;
  const total = kind === "kurz" ? 12 * 60 : 75 * 60;
  const time = [], watts = [], hr = [], dfa = [], cad = [];
  // how far the heart rate climbs decides the decoupling grade
  const climb = kind === "stabil" ? 2 : kind === "hart" ? 38 : kind === "mittel" ? 12 : 9;
  for (let s = 0; s <= total; s += secs) {
    const frac = s / total;
    time.push(s);
    watts.push(158 + ((s / secs) % 5) - 2);
    hr.push(Math.round(139 + frac * climb + ((s / secs) % 3) - 1));
    dfa.push(0.82 - frac * 0.12 + (((s / secs) % 7) - 3) / 100);
    cad.push(84);
  }
  return { points: time.length, sample_secs: secs,
           channels: { time, watts, heartrate: hr, dfa_a1: dfa, cadence: cad } };
}

/* the night after a session, as intervals_icu/night returns it */
/* how this session sits among comparable ones, as intervals_icu/context returns it */
/* goal profile and the plan it produces, as intervals_icu/goal returns it */
/* everything the Heute page needs, as intervals_icu/today returns it */
function today(kind) {
  if (kind === "leer") return { available: false };
  const sig = (key, label, unit, value, baseline, z, system, limit) =>
    ({ key, label, unit, value, baseline, z, system, limit,
       moved: Math.abs(z) >= 0.5,
       direction: z >= 0.5 ? "günstig" : z <= -0.5 ? "ungünstig" : "unauffällig" });
  const base = {
    available: true, date: "2026-09-11",
    capacity: "Alles möglich", capacity_text: "Nichts spricht gegen einen harten Reiz.",
    ceiling: 95, state: "ready", state_label: "Normalbereich",
    state_text: "Die Werte liegen im gewohnten Band.",
    tension: null,
    signals: [
      sig("hrv", "Herzratenvariabilität", "ms", 52, 49.2, 0.8, "Autonomes Nervensystem",
          "Nachtmessung der Uhr, nicht die validierte Morgenmessung im Liegen"),
      sig("rhr", "Ruhepuls", "bpm", 54, 56.4, 0.9, "Autonomes Nervensystem",
          "reagiert träger als die HRV, dafür stabiler"),
      sig("sleep", "Schlafdauer", "h", 7.6, 7.4, 0.2, "Verhalten",
          "Dauer aus der Uhr geschätzt; kein autonomer Messwert"),
    ],
    recent: [
      { date: "2026-09-05", load: 0, state: "slump" },
      { date: "2026-09-06", load: 0, state: "slump" },
      { date: "2026-09-07", load: 0, state: "recovering" },
      { date: "2026-09-08", load: 0, state: "recovering" },
      { date: "2026-09-09", load: 9, state: "rebound",
        sessions: [{ name: "Rehburg-Loccum Gehen", type: "Walk", minutes: 71 }] },
      { date: "2026-09-10", load: 0, state: "rebound" },
      { date: "2026-09-11", load: 38, state: "ready",
        sessions: [{ name: "volumen", type: "Ride", minutes: 60 }] },
    ],
    week_load: 47, rest_days: 5,
    bands: {
      hrv: { baseline: 48.2, noise: [44.6, 52.1], usual: [41.3, 56.3], slump: 34.8, unit: "ms" },
      rhr: { baseline: 56.4, noise: [55.1, 57.7], usual: [53.8, 59.0], slump: 61.6, unit: "bpm" },
      sleep: { baseline: 7.4, noise: [7.1, 7.7], usual: [6.8, 8.0], slump: 5.6, unit: "h" },
    },
    history: {
      hrv: Array.from({ length: 42 }, (_, i) => 48 + ((i * 7) % 9) - 4),
      rhr: Array.from({ length: 42 }, (_, i) => 56 + ((i * 5) % 6) - 3),
      sleep: Array.from({ length: 42 }, (_, i) => 7.2 + ((i * 3) % 5) / 10),
    },
    night: { available: true, headline: "Die Nacht sah aus wie sonst nach solchen Einheiten.",
             detail: "Verglichen mit 13 früheren Einheiten ähnlicher Last." },
    anchors: { aerobic_hr: 157, aerobic_watts: 158 },
    horizon: "Nur für heute. Was morgen geht, hängt an der Belastung außerhalb des Trainings, und die steht in keinen Daten.",
    method: "Bewusst KEIN Punktwert. Von vierzehn Bereitschaftswerten aus zehn Wearable-Häusern legt kein einziger seine Formel offen.",
  };
  if (kind === "einbruch") {
    return { ...base, capacity: "Ruhetag", capacity_text: "Heute nichts. Der Einbruch ist akut.",
      ceiling: 0, state: "slump", state_label: "Einbruch",
      signals: [
        sig("hrv", "Herzratenvariabilität", "ms", 30, 49.2, -2.7, "Autonomes Nervensystem", "Nachtmessung der Uhr"),
        sig("rhr", "Ruhepuls", "bpm", 66, 56.4, -3.7, "Autonomes Nervensystem", "reagiert träger"),
        sig("sleep", "Schlafdauer", "h", 6.1, 7.4, -1.4, "Verhalten", "Dauer geschätzt"),
      ] };
  }
  if (kind === "spannung") {
    return { ...base,
      tension: "Herzratenvariabilität liegt heute unter deiner Basislinie — aber weder weit genug noch lange genug für einen Einbruch. Die Regel entscheidet über das Mittel der letzten drei Tage.",
      signals: [
        sig("hrv", "Herzratenvariabilität", "ms", 42, 49.2, -1.4, "Autonomes Nervensystem", "Nachtmessung der Uhr"),
        sig("rhr", "Ruhepuls", "bpm", 56, 56.4, 0.1, "Autonomes Nervensystem", "reagiert träger"),
        sig("sleep", "Schlafdauer", "h", 7.5, 7.4, 0.1, "Verhalten", "Dauer geschätzt"),
      ] };
  }
  if (kind === "ohnenacht") return { ...base, night: { available: false } };
  return base;
}

function goal(kind) {
  const goals = {
    long_ride: { label: "Lange Fahrten durchstehen", detail: "Sechs Stunden und mehr, ohne im letzten Drittel einzubrechen.", target: "Durability — Ermüdungswiderstand", why: "Maunder definiert sie als Zeitpunkt und Ausmaß der Verschlechterung physiologischer Merkmale während langer Belastung.", key_session: "der lange Tag" },
    ftp: { label: "Schwellenleistung heben", detail: "Mehr Watt über eine Stunde.", target: "FTP", why: "Schwellenarbeit plus SweetSpot.", key_session: "die Schwelleneinheit" },
    vo2max: { label: "Spitzenleistung heben", detail: "Die Pyramide oben breiter machen.", target: "VO2max", why: "Rønnestads 30/15.", key_session: "die VO2max-Einheit" },
    health: { label: "Fit bleiben", detail: "Form halten.", target: "Erhalt", why: "Gleichmäßige Grundlage.", key_session: "die Grundlageneinheit" },
  };
  const state = { longest_ride_hours: 3.5, weekly_load: 181, typical_hours: 8.5, typical_days: 3.1 };
  if (kind === "neu") {
    return { profile: { goal: null, hard_days: [] }, state, goals, plan: { ready: false, missing: ["goal"] } };
  }
  const week = (index, kindOf, hours, long, capped, phase) => ({
    index, start: "2026-09-" + (12 + 7 * (index - 1)), kind: kindOf,
    phase: phase || "base", phase_label: phase === "specific" ? "Spezifisch" : "Grundlage",
    phase_note: "Umfang und aerobe Basis.", weeks_left: 30 - index,
    hours, long_day_hours: long, long_day_capped: !!capped,
    sessions: [
      { role: "long", title: `Langer Tag — ${long} h`, workout: "z2_90",
        detail: phase === "specific" ? "Die letzten 30–40 Minuten mit 2×10 min zügig." : "Noch ohne harte Anteile.",
        why: "Lange Einheiten nahe unter der aeroben Schwelle bauen Fettoxidation.",
        fuel: "Durchgehend essen und trinken.", hours: long },
      { role: "quality", title: "SweetSpot 2×20", workout: "sweetspot_2x20",
        detail: "Die harte Einheit der Woche.", why: "Hält die Schwelle oben.", hours: 1.2 },
      { role: "endurance", title: "Grundlage — 1.4 h", workout: "z2_60",
        detail: "Gleichmäßig, DFA über 0,75.", why: "75–80 % der Einheiten.", hours: 1.4 },
    ],
  });
  const base = {
    profile: { goal: "long_ride", target_hours: 6.5, target_date: "2027-05-01",
      days_per_week: 4, hours_per_week: 11, longest_day_hours: 3.5, hard_days: ["Mo"],
      long_day: "Samstag", indoor_only: false, notes: "Schichtdienst" },
    state, goals,
    plan: {
      ready: true, goal: "long_ride", goal_label: "Lange Fahrten durchstehen",
      target: "Durability — Ermüdungswiderstand",
      why: "Maunder: Zeitpunkt und Ausmaß der Verschlechterung während langer Belastung.",
      key_session: "der lange Tag", pattern: "3:1", hard_per_week: 2,
      hard_note: "2 harte Einheiten pro Woche. Die 80/20-Verteilung zählt Einheiten, nicht Minuten. Einschränkung: ein Review von 2023 fand keinen Beleg, dass ein Modell immer gewinnt.",
      hours_source: "aus deinen letzten Wochen gerechnet",
      pattern_note: "Lastgleich verglichen fanden zwölf Wochen keinen Unterschied zwischen Block und traditionell.",
      longest_now: 3.5, target_hours: 6.5, gap_hours: 3.0, weeks_left: 33,
      budget_note: null,
      weeks: [week(1, "load", 11, 3.9), week(2, "load", 11, 4.4),
              week(3, "load", 11, 4.9, false, "specific"), week(4, "recovery", 7.2, 3.4)],
      caveat: "Der Zuwachs von rund 12 % je Belastungswoche ist eine Konvention, kein Studienergebnis. Ein Einbruch schlägt jeden Plan.",
    },
  };
  if (kind === "knapp") {
    return { ...base, plan: { ...base.plan,
      budget_note: { kind: "too_little_time", needed_hours: 11, have_hours: 8,
        reachable_long_day: 4.8,
        text: "Mit 8 Stunden pro Woche ist eine 6.5-Stunden-Fahrt nicht aufzubauen." },
      weeks: [week(1, "load", 8, 4.8, true), week(2, "load", 8, 4.8, true)] } };
  }
  return base;
}

function context(kind) {
  if (kind === "leer") return { available: false };
  const full = {
    available: true, group: "ride", peers: 18,
    window: { intensity: 61, minutes: 208 },
    metrics: {
      decoupling: { label: "Entkopplung", unit: "%", value: 10.6, median: 2.1,
        best: -0.6, worst: 16.9, p25: 0.9, p75: 5.4, n: 17, enough: true,
        rank: 94, good: "down", verdict: "schlechter als sonst" },
      ef: { label: "Watt pro Herzschlag", unit: "", value: 0.923, median: 0.695,
        best: 0.98, worst: 0.55, p25: 0.63, p75: 0.79, n: 17, enough: true,
        rank: 76, good: "up", verdict: "besser als sonst" },
      hr: { label: "Ø Herzfrequenz", unit: "bpm", value: 142, median: 139,
        best: 128, worst: 151, p25: 134, p75: 144, n: 17, enough: true,
        rank: 55, good: "down", verdict: "im üblichen Bereich" },
    },
    note: "Verglichen wird mit deinen eigenen früheren Einheiten derselben Sportart, deren Intensität um höchstens 10 Punkte und deren Dauer um höchstens 40 % abweicht. Der Prozentrang sagt, wie viele der Vergleichseinheiten schlechter lagen.",
  };
  if (kind === "duenn") {
    return { ...full, peers: 3, metrics: { decoupling: {
      label: "Entkopplung", unit: "%", value: 10.6, n: 3, enough: false } } };
  }
  return full;
}

function night(kind) {
  if (kind === "keine") return { available: false, reason: "no_wellness", night_date: "2026-09-02" };
  if (kind === "unbekannt") return { available: false, reason: "unknown_activity" };
  const base = {
    available: true, night_date: "2026-09-02", activity_date: "2026-09-01",
    load: 65, intensity: 91,
    night: {
      hrv: { label: "Herzratenvariabilität", unit: "ms", value: 38.5, baseline: 49.2, z: -1.54 },
      rhr: { label: "Ruhepuls", unit: "bpm", value: 60, baseline: 56.4, z: -1.3 },
      sleep: { label: "Schlafdauer", unit: "h", value: 7.2, baseline: 7.4, z: -0.46 },
    },
    reference: {
      hrv: { mean: -1.49, sd: 1.08, n: 12 },
      rhr: { mean: -1.26, sd: 0.86, n: 12 },
      sleep: { mean: 0.23, sd: 1.13, n: 12 },
    },
    state: "usual",
    headline: "Die Nacht sah aus wie sonst nach solchen Einheiten.",
    detail: "Verglichen mit 12 früheren Einheiten ähnlicher Last und Intensität.",
    caveat: "Die Nacht direkt nach einer Einheit ist die sauberste Messbedingung; der Zusammenhang zwischen Last und HRV-Änderung ist glockenförmig, nicht gerade. Und es bleibt die Nachtmessung der Uhr.",
  };
  if (kind === "hart") {
    return { ...base, state: "hard",
      headline: "Die Nacht fiel deutlich gedämpfter aus als sonst nach solchen Einheiten.",
      night: { ...base.night, hrv: { ...base.night.hrv, value: 28.1, z: -3.2 } } };
  }
  if (kind === "ohnereferenz") {
    return { ...base, reference: {}, state: "unknown", headline: "Kein Vergleich möglich.",
      detail: "Es liegen noch zu wenige frühere Einheiten ähnlicher Last vor." };
  }
  return base;
}

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

/* coach payloads, one per state the backend can report.
 * Shape since 0.32.0: ONE voice - the assessment. No recommendation, no
 * plan ladder, no session menu; the session list comes from workouts(). */
function coach(kind) {
  const anchors = { aerobic_hr: 157, aerobic_power: 158, n: 30,
    trend_power: { power_before: 155, power_now: 158, hr_before: 157, hr_now: 157,
                   power_change_pct: 2.2, hr_change: -0.4 },
    source: "Median der letzten fünf belastbaren DFA-Messungen (Rogers/Gronwald)" };
  const durability = { n: 73, short: 0.0, long: 0.4, verdict: "die aerobe Basis trägt auch lange Einheiten",
                       source: "Friel: bis 5 % Entkopplung" };
  const evidence = { rule: "Javaloyes 2019/2020, Vesterinen 2016 — HRV-gesteuerte Steuerung.",
                     limit: "Düking 2021: kleiner, nicht signifikanter Effekt auf die Spitzenleistung; dafür weniger Non-Responder (Manresa-Rocamora 2021).",
                     own_data: "Schwellen aus eigenen DFA-Messungen." };
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
    return { state: states.slump, layoff: { days: 0, phase: null, note: null },
      anchors, durability, habit: null, hard_days_last_7: 0, trained_today: false,
      reasons: [{ weil: "Einbruch", quelle: "Plews/Altini", text: "Werte außerhalb des Normalbereichs." }],
      warnings: [], evidence };
  }
  if (kind === "rebound") {
    return { state: states.rebound,
      layoff: { days: 7, last: "2026-09-04", phase: "wiedereinstieg",
                note: "Bis etwa zwei Wochen Pause kostet vor allem das Plasmavolumen Leistung." },
      anchors, durability, habit: { n: 6, median_intensity: 85, hard_share: 83 },
      hard_days_last_7: 0, trained_today: false,
      reasons: [{ weil: "Erholung nach Einbruch", quelle: "Plews", text: "Signal zum Wiedereinstieg, nicht zur Intensität." },
                { weil: "7 Tage ohne Einheit", quelle: "Mujika/Coyle; Rückkehr nach Infekt", text: "Plasmavolumen, kein Trainingsverlust." }],
      warnings: ["Nach einem Infekt gilt: stufenweise aufbauen und bei wiederkehrenden Symptomen abbrechen. Systemische Infektion plus harte Belastung ist die eine Kombination mit ernstem Risiko.",
                 "Dein eigenes Muster: nach 6 Pausen lag die erste Einheit im Median bei 85 % Intensität."],
      evidence };
  }
  if (kind === "unknown") {
    return { state: states.unknown, layoff: { days: null, phase: null, note: null },
      anchors: { aerobic_hr: null, aerobic_power: null, n: 1, trend_power: null,
                 source: "zu wenige belastbare DFA-Messungen" },
      durability: null, habit: null, hard_days_last_7: 0, trained_today: false,
      reasons: [], warnings: [], evidence };
  }
  if (kind === "trained") {
    return { state: states.ready, layoff: { days: 0, phase: null, note: null },
      anchors, durability, habit: null, hard_days_last_7: 1, trained_today: true,
      reasons: [{ weil: "im Normalbereich", quelle: "Javaloyes", text: "Ein harter Reiz ist möglich." }],
      warnings: [], evidence };
  }
  return { state: states.ready, layoff: { days: 1, phase: null, note: null },
    anchors, durability, habit: { n: 6, median_intensity: 85, hard_share: 83 },
    hard_days_last_7: 0, trained_today: false,
    reasons: [{ weil: "im Normalbereich", quelle: "Javaloyes", text: "Ein harter Reiz ist möglich." }],
    warnings: [], evidence };
}

/* the signal matrix as intervals_icu/signals returns it, including the real
 * September sequence: normal -> slump -> still down -> rebound */
function workouts(kind) {
  const mk = (key, family, familyLabel, title, minutes, load, intensity, blocks, text, hr, fit, reason) => ({
    key, family, family_label: familyLabel, title, purpose: familyLabel,
    minutes, load, intensity, blocks,
    blocks_w: blocks.map(([m, pct, l]) => [m, Math.round(215 * pct / 100), l]),
    text, text_w: text.replace(/(\d+)(-(\d+))?%/g, (m, a, b, c) => c ? Math.round(215*a/100)+"-"+Math.round(215*c/100)+"w" : Math.round(215*a/100)+"w"),
    hr_window: hr, fit, fit_reason: reason || "", fits_budget: load <= 95,
    dfa: "unter 0,5 in den Blöcken",
    effect: "Der Reiz, um den es bei dieser Art geht.",
    evidence: "Rønnestad: 3 Sätze à 13×30 s / 15 s, signifikant größere Zuwächse.",
    limit: "Protokollnamen sind keine Verschreibungen.",
    alternatives: [{ key: "vo2_5x4", title: "VO2max 5×4 min", load: 92 }],
  });
  if (kind === "leer") return { ftp: null, aerobic_hr: null, budget: null, state: "unknown", workouts: [] };
  const z2 = [[10, 55, "Einrollen"], [80, 68, "gleichmäßig"], [5, 50, "Ausrollen"]];
  const vo2 = [[15, 55, "Einrollen"], [4, 110, "1"], [4, 50, "Pause"], [4, 110, "2"],
               [4, 50, "Pause"], [4, 110, "3"], [4, 50, "Pause"], [4, 110, "4"], [11, 50, "Ausrollen"]];
  const ss = [[12, 55, "Einrollen"], [20, 90, "Block 1"], [6, 55, "Pause"], [20, 90, "Block 2"], [8, 50, "Ausrollen"]];
  if (kind === "ohneFTP") {
    const w = mk("z2_60", "endurance", "Grundlage", "Grundlage 60 min", 60, 45, 62,
      [[10, 55, "Einrollen"], [45, 68, "gleichmäßig"], [5, 50, "Ausrollen"]],
      "- 10m 55%", null, "ok");
    delete w.blocks_w; delete w.hr_window;
    return { ftp: null, aerobic_hr: null, budget: null, state: "ready", workouts: [w] };
  }
  const soft = kind === "einbruch";
  const why = "Die Erholung läuft, aber die letzten Tage tragen noch keinen harten Reiz.";
  return {
    ftp: 215, aerobic_hr: 157, budget: 95, state: soft ? "rebound" : "ready",
    workouts: [
      mk("z2_90", "endurance", "Grundlage", "Grundlage 90 min", 95, 72, 63, z2,
         "- 10m 55% 85rpm\n- 80m 65-70% 85rpm\n- 5m 50%", [138, 152], "ok"),
      mk("sweetspot_2x20", "sweetspot", "SweetSpot", "SweetSpot 2×20 min", 70, 78, 83, ss,
         "- 12m 55%\n\n2x\n- 20m 88-93%\n- 6m 55%\n\n- 8m 50%", [160, 170],
         soft ? "maybe" : "ok", soft ? why : ""),
      mk("tempo_2x20", "tempo", "Tempo", "Tempo 2×20 min", 65, 62, 75, ss,
         "- 12m 55%\n\n2x\n- 20m 78-82%\n- 5m 55%\n\n- 8m 50%", [152, 160],
         soft ? "maybe" : "ok", soft ? why : ""),
      mk("threshold_4x10", "threshold", "Schwelle", "Schwelle 4×10 min", 78, 78, 85, vo2,
         "- 15m 55%\n\n4x\n- 10m 95-100%\n- 5m 50%\n\n- 8m 50%", [163, 174],
         soft ? "no" : "ok", soft ? why : ""),
      mk("vo2_4x4", "vo2max", "VO2max", "VO2max 4×4 min", 58, 82, 89, vo2,
         "- 15m 55% 85rpm\n\n4x\n- 4m 106-110% 95rpm\n- 4m 50%\n\n- 11m 50%", [166, 180],
         soft ? "no" : "ok", soft ? why : ""),
      mk("recovery_40", "recovery", "Regeneration", "Regeneration 40 min", 40, 18, 45,
         [[40, 50, "ganz locker"]], "- 40m 45-55% 80rpm", [113, 129], "ok"),
    ],
  };
}

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
module.exports = { TODAY, days, load, readiness, activities, streams, thresholds, calendar, pmc, laps, lapsWithBounds, steadyStream, night, context, goal, today, coach, signals, workouts };
