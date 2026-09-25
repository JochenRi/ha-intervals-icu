# ha-intervals-icu — Übergabe an den nächsten Chat

**Stand:** 25.09.2026 · **Version:** 0.71.0 · Prüfstand **24 / 8.345 / 0** (python3.13 + node)

**Der Stand steht in `PROJEKTSTAND.md` — diese Datei ist nur der Einstieg.** Der frühere
Inhalt (Journal 0.44.0–0.69.0) liegt unverändert in `docs/journal_naechster_chat.md`; er ist
Historie, keine Anleitung.

## Zuerst lesen
1. `PROJEKTSTAND.md` Kopf, §9 (Prüfstand mit Aufruf), §10 (offen), §11 (Betrieb, Auslieferungsweg), §13 (Bauregeln).
2. `PROJEKTSTAND.md` §7, Fälle 58–65: was 0.68.0–0.71.0 geändert hat.
3. `docs/rechenwege.md` K5 (Umkehrung, mit Nachträgen 0.67.0/0.68.0) — nur wenn es um die Kachel oder die Grundlagen-Watt geht.

## Prüfstand
`bash tests/run_all.sh` (aus dem Repo-Wurzelverzeichnis; nimmt `python3.13`, dazu `node`). Ende: `Dateien=24 Summe=8345 Fehler=0`.
**Python ≥ 3.12 ist Pflicht** (`type`-Anweisung in `coordinator.py`); das Skript sucht ihn selbst und bricht ohne ab.
Mit `python3` = 3.11 von Hand fallen zwei Dateien mit `SyntaxError` und `test_projektstand.py` meldet 7.409/8 — Interpreter, nicht Code.

## Auslieferung
Gültiger Ablauf steht in `CLAUDE.md` „Ausliefern" (ausführlich PROJEKTSTAND §11):
`bash tests/run_all.sh` grün → Version in `manifest.json` **und** `const.py PANEL_VERSION`, Release-Text
`docs/releases/vX.Y.Z.md`, PROJEKTSTAND nachziehen → Commit als `JochenRi` → `git push origin main`.
**GitHub legt Tag und Release selbst an** (`.github/workflows/release.yml`); die Sitzung legt keine Tags/Releases an.
Ein Commit, der `.github/` ändert, hebt nie die Version. Beleg: `git ls-remote origin main` und `/releases/latest`. Kein Token.

## Offen (Reihenfolge Johannes)
- Puls-Schutz zur Wattgrenze (`load_hr`, neues Messfeld) — Vorlage, verschiebt sein Pulsfenster.
- Abnahmefahrt GA-Umkehrung: 3 h bei ~122 W (α in Stunde 3 ≈ 1,3), Gegenfahrt 3 h bei ~150 W — erst danach fällt „ab 3 h ungeprüft".
- S1-Setzung SWC = 0,5 × Streuung (Plews) — von Johannes zu bestätigen.
- Vorlage C5 (0.70.0): „lange Fahrt bis 3 h 50“ (Progression, 30 Tage) neben „großer Tag 6,0 h“ (Plan, ganzes Archiv) — PROJEKTSTAND §10.
- Skizze 0.71.0 §4, offen bei Johannes: Ruhepuls-Richtung im Streifen (spiegeln?), 30/30 als eigene Karte.
- Befund B (0.69.2): 4 Blöcke an einer 3×4-Einheit, Block 1 mit alpha 0,85 — live nachsehen, welche Laps die VO2max-Marke tragen.
- Vorlagen ohne Wirkung heute: S6 Anker-Sportfilter, S12 Tempo-Wattquelle, S13 Konflikthinweis, F1.1 `max_hr`.
- §10 „Vorgabe folgt der Form nicht" gilt nur noch für VO2max/SweetSpot (Grundlage seit 0.68.0 gebunden).

## Regeln, die jede Sitzung treffen
- Doku: `PROJEKTSTAND.md` ist die eine Stand-Datei; `docs/rechenwege.md`, `docs/ausbau.md` und die KARTE-/ZEICHNUNG-Dateien im Projekt sind datierte Momentaufnahmen.
- Kein Bau ohne rote Prüfung vorher; Bauregeln §13; alles muss für einen zweiten Athleten mit eigenen Daten funktionieren (Regel 10).
- Zahlen aus dem Bestand gehören ins Archiv, nicht in den Code; Setzungen sind als Setzung beschriftet.
- Token, Geheimnispfade, geheimnisartige Zeichenketten Richtung fremder Domain: melden, nie ausgeben.
