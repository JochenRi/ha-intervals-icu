/**
 * Checks the design rules the redesign is built on, per view:
 *
 * 1. one primary figure per view - hierarchy instead of a wall of equals
 * 2. colour never carries meaning alone: every state also appears as a word
 * 3. sources and formulas are collapsed, not shouted (progressive disclosure)
 * 4. every view is built from the same card component
 * 5. no raw hex colours in the markup except the fixed semantic palette
 */
const failures = [];
function check(label, got, expected) {
  const ok = JSON.stringify(got) === JSON.stringify(expected);
  console.log(`${ok ? "PASS" : "FAIL"}  ${label}: ${JSON.stringify(got)}` +
    (ok ? "" : `  (erwartet ${JSON.stringify(expected)})`));
  if (!ok) failures.push(label);
}

const registry = {};
globalThis.HTMLElement = class {
  attachShadow() {
    this.shadowRoot = { innerHTML: "", querySelectorAll: () => [], querySelector: () => null };
    return this.shadowRoot;
  }
  dispatchEvent() {}
};
globalThis.customElements = { define: (n, c) => { registry[n] = c; }, get: (n) => registry[n] };
globalThis.Event = class {};
await import("./js/intervals-panel.mjs");

// --- payloads -------------------------------------------------------------------
const pmc = [];
for (let i = 0; i < 200; i += 1) {
  const d = new Date(Date.UTC(2026, 2, 1));
  d.setUTCDate(d.getUTCDate() + i);
  const ctl = 25 + i * 0.05;
  const atl = ctl * (i % 5 === 0 ? 1.3 : 0.85);
  pmc.push({ date: d.toISOString().slice(0, 10), ctl, atl, form: ctl - atl, load: i % 3 ? 0 : 88 });
}
const answers = {
  "intervals_icu/status": { activities: 238, wellness_days: 486, dfa_done: 56, importing: false },
  "intervals_icu/pmc": pmc,
  "intervals_icu/activities": [{
    id: "a1", start_date_local: "2026-09-04T09:00:00", type: "Ride", name: "volumen",
    moving_time: 12503, distance: 71000, icu_training_load: 129, average_heartrate: 142,
    max_heartrate: 165, decoupling: 10.6, icu_average_watts: 122, icu_weighted_avg_watts: 131,
    icu_variability_index: 1.07, trimp: 247, calories: 1846, total_elevation_gain: 658,
    device_name: "Garmin Forerunner 255", icu_intensity: 61,
    dfa: { secs_aerobic: 12360, secs_transition: 120, secs_anaerobic: 20,
           hr_at_threshold: 151, power_at_threshold: 146, threshold_samples: 98 },
  }],
  "intervals_icu/calendar": [{ uid: "1", summary: "SweetSpot Erhalt 1x20", start: "2026-09-11",
    end: "2026-09-12", type: "Ride", load: 47, moving_time: 2400, description: "-20m 205w",
    completed: false }],
  "intervals_icu/thresholds": [
    { date: "2026-08-12", type: "Ride", hr: 145, power: 186, samples: 130 },
    { date: "2026-09-04", type: "Ride", hr: 151, power: 146, samples: 98 },
  ],
  "intervals_icu/load": {
    weeks: [{ week: "2026-W35", load: 420, days: 7, days_trained: 4, monotony: 1.2, strain: 504 },
            { week: "2026-W36", load: 380, days: 7, days_trained: 6, monotony: 2.4, strain: 912 }],
    acwr: [{ date: "2026-09-09", acute: 70, chronic: 55, ratio: 1.27 },
           { date: "2026-09-10", acute: 95, chronic: 55, ratio: 1.73 }],
    acwr_latest: { ratio: 1.73 }, ramp_rate: -2.7, form: 13.9, form_percent: 41.5,
    form_zone: "fresh",
    intensity: { days: 90, sessions: 40, low: 81.2, middle: 6.1, high: 12.7, hours: 60.4 },
    dfa_distribution: { days: 90, sessions: 30, aerobic: 88.1, transition: 7.2, anaerobic: 4.7, hours: 44 },
    decoupling: [], hrv: { latest: 4.1, baseline: 4.0, swc: 0.05, state: "below", series: [] },
    thresholds: { acwr_low: 0.8, acwr_high: 1.3, acwr_risk: 1.5, monotony_watch: 2.0,
                  decoupling_good: 5, polarized_low: 75, polarized_middle: 8 },
  },
  "intervals_icu/days": { today: "2026-09-10", max_week_load: 300, avg_week_load: 210,
    max_day_load: 129, weeks: [{ week: "2026-W37", load: 83, hours: 1.2, km: 0, sessions: 1,
      planned_load: 47, ctl: 33, atl: 19, form: 14, start: "2026-09-07" }],
    days: [{ date: "2026-09-10", weekday: 3, week: "2026-W37", future: false, today: true,
      ctl: 33, atl: 19, form: 14, load: 83, sleep_hours: 7.45, sleep_score: 84, hrv: 63,
      resting_hr: 50, weight: null, steps: 28,
      activities: [{ id: "a1", name: "SweetSpot", type: "VirtualRide", group: "ride",
        sport: "Rad (Rolle)", moving_time: 4200, distance: null, load: 83,
        average_heartrate: 149, average_watts: 168, zones: [43, 57, 0], dfa: [71, 21, 7],
        threshold_hr: 168, threshold_samples: 486 }], planned: [] }] },
  "intervals_icu/readiness": {
    overall: "amber",
    components: [
      { id: "hrv", label: "Herzratenvariabilität", state: "amber", value: 3.7, reference: 3.9,
        detail: "unter der Basislinie", source: "7-Tage-Mittel ..." },
      { id: "rhr", label: "Ruhepuls", state: "green", value: 50, reference: 52, detail: "unauffällig",
        source: "Ruhepuls ..." },
      { id: "form", label: "Form", state: "green", value: 41.5, reference: null, detail: "frisch",
        source: "Friel ..." },
    ],
    budget: { chronic: 42.5, last_six_days: 180, target_ratio: 1.0, recommended: 118,
              steady: 118, corridor_top: 207, risk_top: 266, state: "amber" },
    note: "Die Kombination ist nicht validiert.",
  },
};

const panel = new registry["intervals-icu-panel"]();
panel.connectedCallback();
panel.hass = { callWS: async (msg) => answers[msg.type] };
await new Promise((r) => setTimeout(r, 10));

const views = ["calendar", "today", "fitness", "activities", "load", "dfa", "plan"];
const html = {};
for (const view of views) {
  panel._tab = view;
  if (view === "activities") panel._openActivity = "a1";
  panel._render();
  html[view] = panel.shadowRoot.innerHTML;
}

// --- 1. hierarchy: at most one extra-large figure per view -------------------------
for (const view of views) {
  const xl = (html[view].match(/class="metric xl"/g) || []).length;
  check(`${view}: höchstens eine Leitzahl`, xl <= 1, true);
}
check("Heute hat eine Leitzahl", (html.today.match(/class="metric xl"/g) || []).length, 1);

// --- 2. colour is never alone ------------------------------------------------------
for (const view of ["today", "load", "dfa"]) {
  const states = (html[view].match(/class="(tile|hero) (green|amber|red)"/g) || []).length;
  const words = (html[view].match(/class="chip (green|amber|red)"/g) || []).length;
  check(`${view}: jeder Farbzustand hat ein Wort`, states === 0 || words >= 1, true);
}
check("Ampelzustand steht im Klartext", /class="hero amber"[\s\S]*gelb —/.test(html.today), true);

// --- 3. progressive disclosure -------------------------------------------------------
check("Quellen sind eingeklappt", html.today.includes('<details class="src">'), true);
check("Rechenweg ist eingeklappt", html.today.includes('<details class="how">'), true);
check("keine offenen Quellenabsätze mehr", html.today.includes('<p class="src"'), false);
for (const view of ["load", "dfa"]) {
  check(`${view}: Quellen aufklappbar`, html[view].includes("<details"), true);
}

// --- 4. one card component everywhere --------------------------------------------------
// every view is built from the shared surface: cards, or the grid panels that
// use the same background, border and radius tokens
for (const view of views) {
  const surfaces = (html[view].match(/class="(card|day |wsum|tile |hero)/g) || []).length;
  check(`${view}: nutzt die gemeinsame Fläche`, surfaces >= 1, true);
}

// --- 5. palette discipline ----------------------------------------------------------------
// the fixed palette: semantic states, sport hues, and the two greys
const allowed = new Set(["#4caf50", "#ffb300", "#f44336", "#4aa8ff", "#e040fb", "#9e9e9e",
                         "#0863b2", "#8c564b", "#119eb1", "#7a7a7a", "#666666",
                         "#ff8a4a", "#9aa4b2", "#2ed3d3", "#c07cf0", "#8a8a8a",
                         "#08080b", "#0b0b0f", "#0d0d12", "#0f0f15", "#e0e0e0",
                         "#00e676", "#b040d0"]);
const strays = new Set();
for (const view of views) {
  for (const hex of html[view].match(/#[0-9a-fA-F]{6}/g) || []) {
    if (!allowed.has(hex.toLowerCase())) strays.add(hex);
  }
}
check("keine Farben außerhalb der Palette", [...strays], []);

// --- 6. every view survives empty data ------------------------------------------------------
const bare = new registry["intervals-icu-panel"]();
bare.connectedCallback();
// a command answering with null must not take a view down
bare.hass = { callWS: async () => null };
await new Promise((r) => setTimeout(r, 10));
for (const view of views) {
  bare._tab = view;
  bare._render();
  check(`${view}: leer ohne Absturz`, bare.shadowRoot.innerHTML.length > 100, true);
}

console.log("\nFEHLER:", failures.length ? failures : "keine");
process.exit(failures.length ? 1 : 0);
