"use strict";
/* Loads the panel module outside a browser and hands back both the component
 * class and its module-level helpers, so every view can be rendered against
 * synthetic payloads without Home Assistant or a DOM. */

const fs = require("fs");
const path = require("path");

const PANEL = path.join(
  __dirname, "..", "custom_components", "intervals_icu", "frontend", "intervals-panel.js"
);

/* The panel element and #app are NOT the same box: #app is capped at 1240px
 * and centred, so on a wide screen it sits far from the window's left edge.
 * The stub reproduces that offset - with both boxes identical, a readout
 * clamped against the wrong frame still looked correct in the test. */
function stubElement(appRect) {
  const app = {
    getBoundingClientRect: () => appRect || { left: 0, top: 0, width: 1200, height: 800 },
  };
  const box = { innerHTML: "", hidden: true, style: {}, offsetWidth: 0, offsetHeight: 0 };
  const lines = [];
  const mkLine = () => { const a = {}; return { setAttribute: (k, v) => { a[k] = v; }, _a: a }; };
  for (let i = 0; i < 3; i++) lines.push(mkLine());
  return {
    innerHTML: "", _listeners: {}, _box: box, _lines: lines,
    getElementById: (id) => (id === "xhbox" ? box : (id === "app" ? app : { innerHTML: "", hidden: true, style: {} })),
    querySelectorAll: (sel) => (sel === ".xh" ? lines : []),
    querySelector: () => null,
    addEventListener(type, fn) { this._listeners[type] = fn; },
  };
}

function load() {
  global.HTMLElement = class {
    attachShadow() { this.shadowRoot = stubElement(global.__APP_RECT__); return this.shadowRoot; }
    getBoundingClientRect() { return global.__HOST_RECT__ || { left: 0, top: 0, width: 1200, height: 800 }; }
  };
  const defined = {};
  global.customElements = {
    define(name, cls) { defined[name] = cls; },
    get(name) { return defined[name]; },
  };
  const src = fs.readFileSync(PANEL, "utf8");
  const exported = {};
  // eslint-disable-next-line no-eval
  eval(src + `
    ;Object.assign(exported, {
      C, ROLE, SPORT, ST, chart, spark, ring, bullet, monthTicks, domainOf,
      tickVals, movAvg, rollMedian, median, meanOf, fmt, sign, dur, hhmm,
      dShort, dMed, dLong, groupKey, sportOf, esc,
    });`);
  return { Panel: defined["intervals-icu-panel"], ...exported };
}

/* --- assertions ------------------------------------------------------- */
let checks = 0, failures = [];

function ok(cond, label) {
  checks++;
  if (!cond) failures.push(label);
}
function clean(html, label) {
  ok(typeof html === "string" && html.length > 0, `${label}: leere Ausgabe`);
  for (const bad of ["undefined", "NaN", "[object", "Infinity"]) {
    const i = String(html).indexOf(bad);
    ok(i < 0, `${label}: enthält "${bad}" bei …${String(html).slice(Math.max(0, i - 60), i + 25)}…`);
  }
}
function contains(html, needle, label) {
  ok(String(html).includes(needle), `${label}: "${needle}" fehlt`);
}
function report(title) {
  console.log(`${title}: ${checks} Prüfungen, ${failures.length} Fehler`);
  for (const f of failures) console.log("   ✗ " + f);
  if (failures.length) process.exit(1);
  console.log("FEHLER: keine");
}

module.exports = { load, ok, clean, contains, report, stubElement };
