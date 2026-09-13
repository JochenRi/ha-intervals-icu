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
    // Das Urteil kommt seit 0.45.0 aus dem Backend (derive.threshold_verdict)
    // und liegt unter `threshold` - die Karte rechnet es nicht mehr selbst.
    dfa: i % 5 ? { samples: 2000, secs_aerobic: 3000, secs_transition: 400,
                   secs_anaerobic: 200, hr_at_threshold: 151, power_at_threshold: 146,
                   threshold: { hr: 151, power: 146,
                                hr_windows: i % 2 ? 43 : 3, power_windows: i % 2 ? 43 : 3,
                                hr_usable: !!(i % 2), power_usable: !!(i % 2),
                                usable: !!(i % 2), failure: false,
                                reason: i % 2 ? null : "too_few_windows" } } : null,
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

/* 42 wellness days ending on TODAY, with two days simply absent - an archive
 * has gaps, and an axis that assumes it does not is wrong from the first one.
 * The newest seven rows carry the same dates, loads and states as `recent`. */
function historyDays() {
  const RECENT = [
    ["2026-09-05", 0, "slump"], ["2026-09-06", 0, "slump"],
    ["2026-09-07", 0, "recovering"], ["2026-09-08", 0, "recovering"],
    ["2026-09-09", 9, "rebound"], ["2026-09-10", 0, "rebound"],
    ["2026-09-11", 38, "ready"],
  ];
  const GAPS = new Set([20, 21]);          // days back from TODAY that are missing
  const out = [];
  for (let back = 7; out.length < 42 - RECENT.length; back++) {
    if (GAPS.has(back)) continue;
    const d = new Date(Date.parse(TODAY + "T00:00:00") - back * 864e5);
    const iso = d.toISOString().slice(0, 10);
    const load = back % 4 === 1 ? 60 + (back % 3) * 25 : (back % 7 === 3 ? 22 : 0);
    const state = back % 11 === 4 ? "slump" : back % 5 === 0 ? "strained" : "ready";
    out.push({ date: iso, load, state });
  }
  out.reverse();
  for (const [date, load, state] of RECENT) out.push({ date, load, state });
  return out;
}

function thresholds() {
  const out = [];
  // 56 readings in three-day steps ENDING on TODAY. Running them forward from
  // a fixed start date put the newest a month into the future - a threshold
  // measured tomorrow does not exist, and it made every relative window lie.
  let d = new Date(Date.parse(TODAY + "T00:00:00") - 55 * 3 * 864e5);
  for (let i = 0; i < 56; i++) {
    out.push({
      date: d.toISOString().slice(0, 10), activity_id: "act" + i,
      // Ride and VirtualRide are the same sport - the filter used to list
      // "Rad" twice because it grouped on the raw type
      type: i % 4 === 3 ? "Walk" : (i % 2 ? "Ride" : "VirtualRide"),
      hr: 150 + ((i * 9) % 22), power: i % 4 === 3 ? null : 135 + ((i * 5) % 25),
      // Belegung UND Urteil je Wert getrennt, wie sie das Backend liefert.
      // Eine Zahl je Wert, nicht eine fuer beide: das `or` von frueher hat
      // bei ausgefallenem Gurt die Watt-Belegung als HF-Belegung gemeldet.
      hr_windows: i % 5 ? 12 : 3, power_windows: i % 4 === 3 ? 0 : (i % 5 ? 12 : 3),
      hr_usable: !!(i % 5), power_usable: i % 4 === 3 ? false : !!(i % 5),
      usable: !!(i % 5), failure: false,
      reason: i % 5 ? null : "too_few_windows",
    });
    // Drei Faelle, die auseinandergezogen gehoeren (docs/ausbau.md Tests L):
    // ein AUSFALL gegen eine echte Messung, und eine Fahrt mit EINEM Fenster
    // gegen eine mit vielen. Beide stammen aus dem echten Konto und haben die
    // Achse von 0 bis 160 gezogen.
    if (i === 12) out[out.length - 1] = { ...out[out.length - 1],
      hr: 0, power: 163, hr_windows: 24, power_windows: 24,
      hr_usable: false, power_usable: true, usable: true,
      failure: true, reason: "hr_implausible" };
    if (i === 30) out[out.length - 1] = { ...out[out.length - 1], type: "Walk",
      hr: 90, power: null, hr_windows: 1, power_windows: 0,
      hr_usable: false, power_usable: false, usable: false,
      failure: false, reason: "too_few_windows" };
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
    // The named twin of `history`, index for index. Deliberately NOT 42
    // consecutive days: two wellness days are missing, which is what an
    // archive really looks like and what breaks any axis reconstructed from
    // "today minus n". The last seven rows are the same days as `recent`,
    // with the same loads - one way to the day's load, not two.
    history_days: historyDays(),
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
  const week = (index, kindOf, hours, long, big, phase) => ({
    index, start: "2026-09-" + String(7 + 7 * (index - 1)).padStart(2, "0"), kind: kindOf,
    phase: phase || "base", phase_label: phase === "specific" ? "Spezifisch" : "Grundlage",
    phase_note: "Umfang und aerobe Basis.", weeks_left: 30 - index,
    hours, long_day_hours: long, big_day: !!big,
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
  /* What rate_sessions copies over from the catalogue so BOTH views can build
   * the same card: steps in watts, the heart-rate window, the evidence. */
  const card = (key, familyLabel, purpose, minutes, blocks, hr, stretch) => ({
    key, family_label: familyLabel, purpose, minutes, blocks,
    template_minutes: stretch ? stretch.from : minutes,
    stretched: !!stretch,
    elastic_sections: stretch ? stretch.sections : [],
    // Beleg und Setzung getrennt, so wie workouts.py sie liefert
    stretch_note: stretch
      ? { rule: "Der Aufbau stammt aus der Vorlage und wurde auf die geplante Dauer gebracht.",
          evidence: "Belegt ist, dass das Einrollen NICHT mitwächst: Aufwärmen wird in absoluten Minuten verschrieben, und zu langes Aufwärmen ermüdet (J Appl Physiol 2011, „Less is more“).",
          limit: "Eine Setzung ist dagegen, dass die gesamte Differenz auf den gleichmäßigen Block geht — nicht gemessen." }
      : { rule: "Diese Vorlage hat keinen dehnbaren Abschnitt.",
          evidence: "Intervalle und ihre Pausen stehen in der Literatur absolut, nie als Anteil.",
          limit: "Deshalb wird hier nichts gedehnt, und beide Zahlen bleiben sichtbar." },
    blocks_w: blocks.map(([m, pct, l]) => [m, Math.round(215 * pct / 100), l]),
    text: "- 10m 55%", text_w: "- 10m 118w", hr_window: hr,
    dfa: "durchgehend über 0,75", evidence: "Dreizonenmodell (Seiler).",
    limit: "Expertenkonsens nennt 60–90 Minuten.",
  });

  /* Week 1 as the backend hands it over: graded sessions, the scaled loads,
   * and the ridden-against-planned block. The three sessions deliberately land
   * on three DIFFERENT grades, so a view that prints only one of them fails. */
  const ratedWeek = (w) => ({
    ...w, rated: true,
    done: { start: w.start, end: "2026-09-13", days_left: 2, sessions: 2, hours: 2.4,
            load: 142, paired: false,
            activities: [
              { date: "2026-09-08", name: "Feierabendrunde", sport: "Rad", group: "ride", hours: 1.2, load: 70, intensity: 68 },
              { date: "2026-09-10", name: "Runde zwei", sport: "Rad", group: "ride", hours: 1.2, load: 72, intensity: 69 },
            ],
            note: "Gefahren gegen vorgesehen — welche Fahrt welche geplante Einheit war, entscheidest du. Das Archiv führt Dauer und Last, kein Etikett; eine automatische Zuordnung wäre eine Behauptung, die hier niemand belegen kann." },
    sessions: [
      { ...w.sessions[0], ...card("z2_90", "Grundlage", "Aerobe Basis", 210,
          [[10, 55, "Einrollen"], [195, 68, "gleichmäßig"], [5, 50, "Ausrollen"]], [138, 152],
          { from: 95, sections: ["gleichmäßig"] }),
        family: "endurance", load: 159, catalogue_load: 72, catalogue_minutes: 95,
        fit: "ok", fit_reason: "", fits_budget: false, budget: 95,
        stage: stageOf("ok", false, true),
        purpose: "Aerobe Basis", effect: "Kapillarisierung, mitochondriale Dichte, Fettstoffwechsel." },
      { ...w.sessions[1], ...card("sweetspot_2x20", "SweetSpot", "SweetSpot", 70,
          [[12, 55, "Einrollen"], [20, 90, "Block 1"], [6, 55, "Pause"], [20, 90, "Block 2"], [8, 50, "Ausrollen"]],
          [160, 170]),
        family: "sweetspot", load: 80, catalogue_load: 78, catalogue_minutes: 70,
        fit: "maybe", fit_reason: "Beansprucht — Umfang ja, Intensität kostet heute mehr, als sie bringt.",
        fits_budget: true, budget: 95, stage: stageOf("maybe", true, true),
        purpose: "SweetSpot", effect: "Die meiste Schwellenanpassung pro investierter Stunde." },
      { ...w.sessions[2], ...card("z2_60", "Grundlage", "Aerobe Basis", 84,
          [[10, 55, "Einrollen"], [69, 68, "gleichmäßig"], [5, 50, "Ausrollen"]], [138, 152],
          { from: 60, sections: ["gleichmäßig"] }),
        family: "endurance", load: 63, catalogue_load: 45, catalogue_minutes: 60,
        fit: "ok", fit_reason: "", fits_budget: true, budget: 95,
        stage: stageOf("ok", true, true),
        purpose: "Aerobe Basis", effect: "Der Anteil, der im Dreizonenmodell 75–80 % ausmacht." },
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
      key_session: "der große Tag", pattern: "3:1", hard_per_week: 1,
      hard_note: "1 harte Einheit pro Woche. Die 80/20-Verteilung zählt Einheiten, nicht Minuten. Einschränkung: ein Review von 2023 fand keinen Beleg, dass ein Modell immer gewinnt.",
      hours_source: "aus deinen letzten Wochen gerechnet",
      pattern_note: "Lastgleich verglichen fanden zwölf Wochen keinen Unterschied zwischen Block und traditionell.",
      longest_now: 3.5, target_hours: 6.5, gap_hours: 3.0, weeks_left: 33,
      anchor: "2026-09-07", weeks_since_start: 0,
      budget_note: null,
      weeks: [ratedWeek(week(1, "load", 11, 3.5)), week(2, "load", 11, 3.5),
              week(3, "load", 11.4, 3.9, true, "specific"), week(4, "recovery", 7.2, 2.5)],
      // only the current week carries grades (docs/ausbau.md I3)
      no_verdict_note: "Bewertet wird erst in der Woche selbst. Das Lastbudget rechnet aus den letzten sechs Tagen, der Zustand aus den Werten von heute — Budget und Zustand von übernächstem Donnerstag kennt niemand, auch dieses Panel nicht.",
      stages: {
        green: { label: "grün", word: "passt", detail: "Zustand unauffällig, die Last passt ins Budget." },
        yellow: { label: "gelb", word: "geht, kostet aber", detail: "Der Zustand trägt nur bedingt." },
        stimulus: { label: "Reiz", word: "kostet Erholung, setzt aber den Reiz", detail: "Über dem Lastbudget, aber der Zustand trägt und die letzten Tage boten Erholung." },
        red: { label: "rot", word: "heute nicht", detail: "Zustand oder Budget sprechen dagegen." },
      },
      assessment: {
        state: "ready", state_label: "im Normalbereich", budget: 95, hard_days_last_7: 0,
        recovery: { offered: true, quiet_days: 2, max_hard_days_7: 0,
          recent_daily_load: 12.0, chronic_daily_load: 48.5, missing: [],
          note: "Erholung gilt als geboten, wenn der Zustand unauffällig ist, in den letzten sieben Tagen höchstens 0 harte Tage liegen und die Last der letzten 2 Tage unter deinem chronischen Tagesschnitt bleibt. Die Bestandteile sind belegt, diese Schwellen sind gewählt — eine Setzung, keine Messung." },
      },
      choice: {
        rule: "Am Tag, an dem trainiert werden soll, wählst du aus den Vorschlägen — bewertet nach Zustand und Lastbudget, entschieden von dir. Das Panel fragt nicht nach kommenden Tagen, Schichten oder Terminen.",
        evidence: "Bei Javaloyes hatte zustandsgeführtes Training deutlich weniger Nicht-Responder — 1 von 7 gegenüber 3 von 8 mit Leistungsverlust unter festem Plan.",
        limit: "Die Überlegenheit bei der Leistung selbst ist klein und unsicher.",
      },
      caveat: "Der große Tag alle paar Wochen mit rund 12 % Zuwachs je Schritt ist eine Konvention, kein Studienergebnis. Ein Einbruch schlägt jeden Plan.",
    },
  };
  if (kind === "knapp") {
    return { ...base, plan: { ...base.plan,
      budget_note: { kind: "big_day_exception", target_hours: 6.5, typical_hours: 8,
        cycle_weeks: 4, big_week_hours: 10.5,
        text: "Die 6,5-Stunden-Fahrt ist der einzelne große Tag: alle 4 Wochen einer, die Woche läuft dann auf bis zu 10,5 Stunden — als bewusste Ausnahme (Audax-Praxis, eine Konvention)." },
      weeks: [week(1, "load", 8, 4.0), week(2, "load", 8, 4.0),
              week(3, "load", 10.5, 6.5, true), week(4, "recovery", 5.2, 2.8)] } };
  }
  return base;
}

function context(kind) {
  if (kind === "leer") return { available: false };
  const full = {
    /* ab 0.39.0: "peers" gibt es nicht mehr - die Zahl war zweideutig, weil je
       Kennzahl unterschiedlich viele Einheiten einen Wert tragen. Geweitet wird
       gegen das n DER KENNZAHL, und die gegriffene Stufe steht bei der Zeile. */
    available: true, group: "ride", earlier: 18, min_peers: 6,
    stages: [0.2, 0.4, 0.6, 0.8, 1.0], widest_used: 0.4,
    sd_log_duration: 0.511, sd_intensity: 14.0, population: 137,
    window: { intensity: 61, minutes: 208 },
    metrics: {
      decoupling: { label: "Entkopplung", unit: "%", value: 10.6, median: 2.1,
        best: -0.6, worst: 16.9, p25: 0.9, p75: 5.4, n: 17, enough: true,
        rank: 94, good: "down", verdict: "schlechter als sonst",
        stage: 0.4, duration_low_pct: -18.5, duration_high_pct: 22.7, intensity_points: 5.6 },
      ef: { label: "Watt pro Herzschlag", unit: "", value: 0.923, median: 0.695,
        best: 0.98, worst: 0.55, p25: 0.63, p75: 0.79, n: 17, enough: true,
        rank: 76, good: "up", verdict: "besser als sonst",
        stage: 0.4, duration_low_pct: -18.5, duration_high_pct: 22.7, intensity_points: 5.6 },
      hr: { label: "Ø Herzfrequenz", unit: "bpm", value: 142, median: 139,
        best: 128, worst: 151, p25: 134, p75: 144, n: 17, enough: true,
        rank: 55, good: "down", verdict: "im üblichen Bereich",
        stage: 0.2, duration_low_pct: -9.7, duration_high_pct: 10.8, intensity_points: 2.8 },
    },
    note: "Verglichen wird mit deinen eigenen FRÜHEREN Einheiten derselben Sportart. Die Toleranz ist keine feste Prozentzahl, sondern ein Vielfaches deiner eigenen Streuung — bei der Dauer auf dem Logarithmus gerechnet. Die Streuung wandert mit dem Bestand.",
  };
  if (kind === "duenn") {
    /* Zwei Dünn-Gründe, zwei Sätze - der erste heilt mit der Zeit, der zweite
       nicht. Die Fixture führt beide, sonst prüft der Test nur einen davon. */
    return { ...full, earlier: 3, metrics: {
      decoupling: { label: "Entkopplung", unit: "%", value: 10.6, n: 2, enough: false,
        why: "too_early", say: "zu früh in deiner Historie — davor liegen erst 3 Einheiten mit diesem Wert" },
      ef: { label: "Watt pro Herzschlag", unit: "", value: 0.923, n: 4, enough: false,
        why: "too_few", say: "zu wenige vergleichbare Einheiten — auch auf der weitesten Stufe (1.0 SD) nur 4" },
    } };
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
    source: "Median der letzten fünf belastbaren DFA-Messungen (Rogers/Gronwald) — als Trend brauchbar, als alleinige Verankerung nicht" };
  /* Durability ab 0.40.0: eine Punktwolke ueber der Arbeit. Jede Zahl, die die
     Kachel zeigt, kommt aus dieser Payload - die Marke, die Filtergrenzen, die
     Gewichtsgrenzen, die Mindestbelegungen, das Steigungskriterium. Im Frontend
     darf keine davon ein zweites Mal stehen (Quelltext-Waechter).

     Dieser Fall ist der Livefall: Richtung vorhanden, Streuung zu gross - die
     Kachel verweigert die Leitzahl und sagt, woran es liegt. */
  const durabilityPoints = [
      { kj: 250, dec: 5.9, w: 1.0, vi: 1.05, date: "2026-01-01", id: "a0", minutes: 57, watts: 73 },
      { kj: 320, dec: -5.5, w: 1.0, vi: 1.05, date: "2026-01-02", id: "a1", minutes: 61, watts: 87 },
      { kj: 390, dec: 1.2, w: 0.55, vi: 1.14, date: "2026-01-03", id: "a2", minutes: 64, watts: 102 },
      { kj: 460, dec: -2.3, w: 0.2, vi: 1.21, date: "2026-01-04", id: "a3", minutes: 68, watts: 113 },
      { kj: 530, dec: 3.8, w: 0.85, vi: 1.08, date: "2026-02-05", id: "a4", minutes: 71, watts: 124 },
      { kj: 600, dec: 6.9, w: 1.0, vi: 1.05, date: "2026-02-06", id: "a5", minutes: 75, watts: 133 },
      { kj: 670, dec: -4.5, w: 1.0, vi: 1.05, date: "2026-02-07", id: "a6", minutes: 240, watts: 47 },
      { kj: 740, dec: 2.2, w: 0.55, vi: 1.14, date: "2026-02-08", id: "a7", minutes: 82, watts: 150 },
      { kj: 810, dec: -1.3, w: 0.2, vi: 1.21, date: "2026-03-09", id: "a8", minutes: 85, watts: 159 },
      { kj: 880, dec: 4.9, w: 0.85, vi: 1.08, date: "2026-03-10", id: "a9", minutes: 89, watts: 165 },
      { kj: 950, dec: 8.0, w: 1.0, vi: 1.05, date: "2026-03-11", id: "a10", minutes: 92, watts: 172 },
      { kj: 1020, dec: -3.4, w: 1.0, vi: 1.05, date: "2026-03-12", id: "a11", minutes: 96, watts: 177 },
      { kj: 1090, dec: 3.3, w: 0.55, vi: 1.14, date: "2026-04-13", id: "a12", minutes: 99, watts: 184 },
      { kj: 1160, dec: -0.2, w: 0.2, vi: 1.21, date: "2026-04-14", id: "a13", minutes: 103, watts: 188 },
      { kj: 1230, dec: 5.9, w: 0.85, vi: 1.08, date: "2026-04-15", id: "a14", minutes: 106, watts: 193 },
      { kj: 1300, dec: 9.0, w: 1.0, vi: 1.05, date: "2026-04-16", id: "a15", minutes: 110, watts: 197 },
      { kj: 1370, dec: -2.4, w: 1.0, vi: 1.05, date: "2026-05-17", id: "a16", minutes: 113, watts: 202 },
      { kj: 1440, dec: 4.3, w: 0.55, vi: 1.14, date: "2026-05-18", id: "a17", minutes: 117, watts: 205 },
      { kj: 1510, dec: 0.8, w: 0.2, vi: 1.21, date: "2026-05-19", id: "a18", minutes: 120, watts: 210 },
      { kj: 1580, dec: 6.9, w: 0.85, vi: 1.08, date: "2026-05-20", id: "a19", minutes: 124, watts: 212 },
      { kj: 1650, dec: 10.0, w: 1.0, vi: 1.05, date: "2026-06-21", id: "a20", minutes: 127, watts: 217 },
      { kj: 1720, dec: -1.4, w: 1.0, vi: 1.05, date: "2026-06-22", id: "a21", minutes: 131, watts: 219 },
      { kj: 1790, dec: 5.3, w: 0.55, vi: 1.14, date: "2026-06-23", id: "a22", minutes: 134, watts: 223 },
      { kj: 1860, dec: 1.8, w: 0.2, vi: 1.21, date: "2026-06-24", id: "a23", minutes: 138, watts: 225 },
      { kj: 1930, dec: 7.9, w: 0.85, vi: 1.08, date: "2026-07-25", id: "a24", minutes: 141, watts: 228 },
      { kj: 2000, dec: 11.0, w: 1.0, vi: 1.05, date: "2026-07-26", id: "a25", minutes: 110, watts: 303 },
  ];
  const durability = {
    n: 26, w_sum: 18.2, n_full: 11, n_partial: 15, n_zero: 0,
    points: durabilityPoints,
    max_kj: 2000,
    slope: 2.95, slope_se: 2.22, slope_t: 1.33, blocked: "flat",
    tipping_kj: null, tipping_hours: null,
    power: { watts: 136, days: 90, n: 18 }, power_pool: 86,
    needed_sessions: 128,
    headline: "Die Richtung stimmt — die Entkopplung steigt mit der Arbeit —, aber die Streuung ist zu groß für eine Aussage.",
    bins: [
      { from_kj: 0, to_kj: 400, n: 6, w: 4.2, median: -0.5, thin: false },
      { from_kj: 400, to_kj: 600, n: 5, w: 3.4, median: -0.1, thin: false },
      { from_kj: 600, to_kj: 800, n: 6, w: 4.1, median: 0.4, thin: false },
      { from_kj: 800, to_kj: 1100, n: 5, w: 3.6, median: 1.5, thin: false },
      { from_kj: 1100, to_kj: null, n: 4, w: 2.9, median: null, thin: true },
    ],
    blocks: [
      { start: "2026-01-01", end: "2026-03-26", n: 12, w: 9.1, max_kj: 900, tipping_kj: null,
        reason: "flat", need_w: null, need_n: 44, slope_t: 1.05 },
      { start: "2026-03-28", end: "2026-06-20", n: 4, w: 2.9, max_kj: 650, tipping_kj: null,
        reason: "thin", need_w: 5.1, need_n: null, slope_t: 3.30 },
      { start: "2026-06-22", end: "2026-09-11", n: 10, w: 6.2, max_kj: 2000, tipping_kj: null,
        reason: "thin", need_w: 1.8, need_n: null, slope_t: 2.4 },
    ],
    /* Der Kopf (H1/H2). Hier absichtlich der RUECKFALL-Fall: die belegte Dauer
       stammt von a6 (240 min, 47 W), der Bezug der letzten 30 Tage nur von
       a25 (110 min) - der naechste Schritt liegt also UNTER dem, was schon
       gefahren wurde. Und a6 ist NICHT die arbeitsreichste Fahrt (das ist a25
       mit 2000 kJ), seine 47 W sind NICHT der Pool-Median (136 W). Beide
       Verwechslungen waeren am Livebestand unsichtbar gewesen. */
    progression: {
      demonstrated: { minutes: 240, watts: 47, kj: 670, date: "2026-02-07", id: "a6" },
      recent: { minutes: 110, watts: 303, kj: 2000, date: "2026-07-26", id: "a25",
                days: 30, n: 3, widened: false },
      next_minutes: 120, below_demonstrated: true,
      factor: 1.10, round_minutes: 5, window_days: 30, windows_days: [30, 90, 365],
      today: "2026-08-20",
    },
    decoupling_good: 5.0, min_minutes: 45, max_intensity: 80,
    vi_full: 1.05, vi_none: 1.25,
    min_weight_sum: 20.0, min_weight_sum_block: 8.0, min_slope_t: 2.0,
    block_weeks: 12, bins_kj: [400.0, 600.0, 800.0, 1100.0],
    power_days: 90, power_days_fallback: 180, fuelling_g_per_h: 80,
    min_per_group: 5, min_sessions: 8,
    excluded_types: ["VirtualRide"],
    dropped: { short: 85, intense: 7, variable: 11, indoor: 38, no_activity: 0,
               no_power: 53, no_decoupling: 0, no_work: 0 },
    weight: { kg: 73.5, day: "2026-09-09" },
    source: "Setzung: die 5-%-Marke ist eine Trainerfaustregel (Friel), keine Studiengrenze.",
  };
  /* Derselbe Bestand, aber mit gesicherter Steigung: Leitzahl, Gerade, Stunden.
     Zwei unterscheidbare Faelle, sonst prueft der Test die Regeln nur dem
     Namen nach. */
  const durabilityClear = Object.assign({}, durability, {
    w_sum: 24.0, slope: 4.80, slope_se: 1.10, slope_t: 4.36, blocked: null,
    tipping_kj: 1400, tipping_hours: 2.86, needed_sessions: null,
    headline: "Bis etwa 1400 kJ bleibst du unter der 5-%-Marke — rund 2 h 52 bei deinen 136 W der letzten 3 Monate.",
    blocks: [
      { start: "2026-01-01", end: "2026-03-26", n: 12, w: 9.1, max_kj: 900, tipping_kj: 800,
        reason: null, need_w: null, need_n: null, slope_t: 4.1 },
      { start: "2026-06-22", end: "2026-09-11", n: 10, w: 9.4, max_kj: 2000, tipping_kj: 1400,
        reason: null, need_w: null, need_n: null, slope_t: 4.36 },
    ],
    /* Der Gegenfall zum Kopf oben: der Bezug musste AUSGEWEITET werden (in den
       letzten 30 Tagen stand nichts), und der naechste Schritt liegt UEBER der
       belegten Dauer. Zwei unterscheidbare Faelle, sonst prueft der Test die
       beiden Zweige nur dem Namen nach. */
    progression: {
      demonstrated: { minutes: 240, watts: 47, kj: 670, date: "2026-02-07", id: "a6" },
      recent: { minutes: 240, watts: 47, kj: 670, date: "2026-02-07", id: "a6",
                days: 365, n: 26, widened: true },
      next_minutes: 265, below_demonstrated: false,
      factor: 1.10, round_minutes: 5, window_days: 30, windows_days: [30, 90, 365],
      today: "2026-08-20",
    },
  });
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
      anchors, durability, durabilityClear, habit: { n: 6, median_intensity: 85, hard_share: 83 },
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
/* The four grades, shaped exactly as intervals_icu/workouts emits them
 * (docs/ausbau.md I3). This is TEST DATA, not the rule: workouts.stage()
 * decides, test_workouts.py proves it over the full truth table, and
 * test_panel_fixes guards that the four words here still match the four words
 * in workouts.py - a fixture that drifts from the backend tests nothing. */
const STAGE_WORDS = {
  green:    { label: "grün", word: "passt" },
  yellow:   { label: "gelb", word: "geht, kostet aber" },
  stimulus: { label: "Reiz", word: "kostet Erholung, setzt aber den Reiz" },
  red:      { label: "rot",  word: "heute nicht" },
};
function stageOf(fit, fitsBudget, recovery) {
  const over = fitsBudget === false;
  let key, blocked = null;
  if (fit === "no") { key = "red"; blocked = over ? "both" : "state"; }
  else if (over) {
    if (fit === "ok" && recovery) key = "stimulus";
    else { key = "red"; blocked = fit === "ok" ? "budget" : "both"; }
  } else if (fit === "maybe") key = "yellow";
  else key = "green";
  const out = { key, blocked_by: blocked, ...STAGE_WORDS[key], detail: "Begründung aus dem Backend." };
  if (key === "stimulus") out.evidence = "Funktionelles Überreichen, Meeusen 2013 — dosiert dazu.";
  return out;
}

function workouts(kind) {
  const mk = (key, family, familyLabel, title, minutes, load, intensity, blocks, text, hr, fit, reason) => ({
    key, family, family_label: familyLabel, title, purpose: familyLabel,
    minutes, load, intensity, blocks,
    blocks_w: blocks.map(([m, pct, l]) => [m, Math.round(215 * pct / 100), l]),
    text, text_w: text.replace(/(\d+)(-(\d+))?%/g, (m, a, b, c) => c ? Math.round(215*a/100)+"-"+Math.round(215*c/100)+"w" : Math.round(215*a/100)+"w"),
    hr_window: hr, fit, fit_reason: reason || "", fits_budget: load <= 95,
    stage: stageOf(fit, load <= 95, false),
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
/* The day_context read payload, mirroring websocket_day_context: entries,
 * the vocabulary, and the source-block texts (Auflage A/B). */
function dayContext(extra) {
  const days = Object.assign({
    "2026-09-10": { tag: "nachtschicht", weight: 0.0, note: "", set_at: "2026-09-10" },
    "2026-09-07": { tag: "alkohol", weight: 0.5, note: "", set_at: "2026-09-08" },
  }, extra || {});
  return {
    days,
    tags: {
      normal: { label: "Normal", weight: 1.0, read: "voller Beitrag zur Basislinie" },
      nachtschicht: { label: "Nachtschicht", weight: 0.0, read: "Tagschlaf ist eine andere Messbedingung" },
      spaetschicht: { label: "Spätschicht", weight: 0.5, read: "verschobener, aber nächtlicher Schlaf" },
      alkohol: { label: "Alkohol", weight: 0.5, read: "belegter akuter Stressor" },
      reise: { label: "Reise", weight: 0.5, read: "akuter Stressor" },
      krank: { label: "Krank", weight: 0.0, read: "für die Basislinie null — für die Warnlampe voll" },
      uhr_nicht_getragen: { label: "Uhr nicht getragen", weight: 0.0, read: "Messfehler, kein Zustand" },
    },
    valid_weights: [0, 0.25, 0.5, 0.75, 1],
    min_weight_sum: 30,
    sources: {
      belegt: [
        { text: "Etikettieren und bedingtes Vergleichen", source: "Altini/Plews, Sensors 2021, 21:7932" },
        { text: "Tagschlaf ist eine andere Messbedingung", source: "Boudreau/Boivin, PLOS ONE 2013; gestützt von van Amelsvoort 2001" },
      ],
      setzung: [
        "Die Gewichtszahlen je Etikett sind eine Setzung, keine Studienzahl.",
        "Die Schwelle Σw ≥ 30 ist eine Setzung.",
        "Die 15 Tage bis B4 sind eine Setzung.",
      ],
      fix: "Die saubere Lösung heißt B4. Zyklus fehlt noch als Etikett.",
      read: "Nach einer Nachtschicht sieht der Wert oft schlechter aus. Das ist die Messbedingung, nicht dein Zustand. „Erklärt“ heißt: gesehen, benannt, nicht verschwunden.",
    },
  };
}

module.exports = { STAGE_WORDS, stageOf, TODAY, days, load, readiness, activities, streams, thresholds, calendar, pmc, laps, lapsWithBounds, steadyStream, night, context, goal, today, coach, signals, workouts, dayContext };
