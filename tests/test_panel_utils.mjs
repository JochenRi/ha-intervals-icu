// the merged file also defines the custom element, so the DOM stubs must exist
// before it is imported - exactly the order the browser uses
globalThis.HTMLElement = class { attachShadow() { return {}; } };
globalThis.customElements = { get: () => undefined, define: () => {} };
const u = await import("./js/intervals-panel.mjs");

const failures = [];
function check(label, got, expected) {
  const ok = JSON.stringify(got) === JSON.stringify(expected);
  console.log(`${ok ? "PASS" : "FAIL"}  ${label}: ${JSON.stringify(got)}` +
    (ok ? "" : `  (erwartet ${JSON.stringify(expected)})`));
  if (!ok) failures.push(label);
}

// --- formatting ---------------------------------------------------------------
check("Dauer 3h28m", u.fmtDuration(12503), "3h28m");
check("Dauer 40m", u.fmtDuration(2400), "40m");
check("Dauer leer", u.fmtDuration(null), "–");
check("Distanz 71 km", u.fmtDistance(71000), "71.0 km");
check("Distanz unter 1 km", u.fmtDistance(850), "850 m");
check("Datum", u.fmtDate("2026-09-11T00:00:00"), "11.09.2026");

// --- window -------------------------------------------------------------------
const series = [];
for (let i = 0; i < 400; i += 1) {
  const d = new Date(Date.UTC(2025, 7, 1));
  d.setUTCDate(d.getUTCDate() + i);
  series.push({ date: d.toISOString().slice(0, 10), ctl: 30 + i * 0.01, atl: 25, form: 5, load: i % 7 ? 0 : 90 });
}
check("42-Tage-Fenster", u.lastDays(series, 42).length, 42);
check("Jahresfenster", u.lastDays(series, 365).length, 365);
check("ohne Angabe alles", u.lastDays(series, null).length, 400);
check("Fenster endet am letzten Tag",
  u.lastDays(series, 42)[41].date, series[399].date);

// --- scaling ------------------------------------------------------------------
const range = u.extent(series, ["ctl", "atl"]);
check("Extremwerte umschliessen die Daten", range.min < 25 && range.max > 34, true);
check("y unten = Minimum", Math.round(u.scaleY(range.min, range, 10, 100)), 110);
check("y oben = Maximum", Math.round(u.scaleY(range.max, range, 10, 100)), 10);
check("x links", u.scaleX(0, 10, 40, 300), 40);
check("x rechts", u.scaleX(9, 10, 40, 300), 340);
check("konstante Reihe bekommt Spanne",
  u.extent([{ v: 5 }, { v: 5 }], ["v"]), { min: 4, max: 6 });

// --- paths --------------------------------------------------------------------
const box = { left: 40, top: 10, width: 300, height: 100, range: { min: 0, max: 100 } };
const gapped = [{ v: 10 }, { v: null }, { v: 30 }, { v: 40 }];
const path = u.linePath(gapped, "v", box);
check("Luecke bricht die Linie", (path.match(/M/g) || []).length, 2);
check("Pfad zeichnet die vorhandenen Punkte", (path.match(/[ML]/g) || []).length, 3);
check("leere Reihe ergibt leeren Pfad", u.linePath([{ v: null }], "v", box), "");
const bars = u.barPath([{ l: 0 }, { l: 90 }, { l: 0 }], "l", box);
check("nur Tage mit Last bekommen einen Balken", (bars.match(/M/g) || []).length, 1);

// --- DFA ----------------------------------------------------------------------
check("DFA-Anteile", u.dfaShares({ secs_aerobic: 12360, secs_transition: 120, secs_anaerobic: 20 }),
  { aerobic: 99, transition: 1, anaerobic: 0, total: 12500 });
check("DFA ohne Daten", u.dfaShares(null), null);
check("DFA leer", u.dfaShares({ secs_aerobic: 0, secs_transition: 0, secs_anaerobic: 0 }), null);
check("Schwelle: wenig Stichproben", u.thresholdConfidence(6), "low");
check("Schwelle: solide", u.thresholdConfidence(400), "high");
check("Schwelle: keine", u.thresholdConfidence(0), "none");

// --- escaping -------------------------------------------------------------------
check("HTML wird entschaerft", u.esc('<img src=x onerror="alert(1)">'),
  "&lt;img src=x onerror=&quot;alert(1)&quot;&gt;");

console.log("\nFEHLER:", failures.length ? failures : "keine");
process.exit(failures.length ? 1 : 0);
