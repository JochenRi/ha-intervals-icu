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

module.exports = { TODAY, days, load, readiness, activities, streams, thresholds, calendar, pmc };
