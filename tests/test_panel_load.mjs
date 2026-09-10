/**
 * Simulates how the browser loads the panel: one module URL, no second file,
 * DOM stubs only - the exact chain that reported "Unable to load custom panel".
 */
import { readFileSync, readdirSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const here = dirname(fileURLToPath(import.meta.url));
const frontend = join(here, "..", "custom_components", "intervals_icu", "frontend");
const failures = [];

function check(label, got, expected) {
  const ok = JSON.stringify(got) === JSON.stringify(expected);
  console.log(`${ok ? "PASS" : "FAIL"}  ${label}: ${JSON.stringify(got)}` +
    (ok ? "" : `  (erwartet ${JSON.stringify(expected)})`));
  if (!ok) failures.push(label);
}

// --- what the integration serves -------------------------------------------------
const files = readdirSync(frontend);
check("genau eine Datei im frontend-Ordner", files, ["intervals-panel.js"]);

const source = readFileSync(join(frontend, "intervals-panel.js"), "utf8");
check("keine relativen Importe mehr", /^\s*import\s/m.test(source), false);
check("kein Verweis auf die alte Hilfsdatei", source.includes("intervals-utils"), false);
check("Element wird registriert", source.includes('customElements.define("intervals-icu-panel"'), true);
check("Registrierung ist gegen Doppelladen geschuetzt",
  source.includes('customElements.get("intervals-icu-panel")'), true);

// --- load it the way a browser would ------------------------------------------------
const defined = {};
globalThis.HTMLElement = class {
  attachShadow() {
    this.shadowRoot = { innerHTML: "", querySelectorAll: () => [], querySelector: () => null };
    return this.shadowRoot;
  }
  dispatchEvent() {}
};
globalThis.customElements = {
  define: (name, cls) => { if (defined[name]) throw new Error("already defined"); defined[name] = cls; },
  get: (name) => defined[name],
};
globalThis.Event = class { constructor(type) { this.type = type; } };

await import(`data:text/javascript;base64,${Buffer.from(source).toString("base64")}`);
check("Modul laedt ohne Fehler", Object.keys(defined), ["intervals-icu-panel"]);

// loading it a second time must not throw - browsers do that on a hard reload
await import(`data:text/javascript;base64,${Buffer.from(source + "\n").toString("base64")}`);
check("zweites Laden wirft nicht", Object.keys(defined).length, 1);

// --- and it must render without a hass object -----------------------------------------
const panel = new defined["intervals-icu-panel"]();
panel.connectedCallback();
check("rendert vor dem ersten Datenabruf", panel.shadowRoot.innerHTML.includes("Lade Archiv"), true);

console.log("\nFEHLER:", failures.length ? failures : "keine");
process.exit(failures.length ? 1 : 0);
