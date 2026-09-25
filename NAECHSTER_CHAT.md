# ha-intervals-icu — Übergabe an den nächsten Chat

**Stand:** 25.09.2026 · **Version:** 0.69.1 · Prüfstand **24 / 8.134 / 0** (python3.13 + node)

**Der Stand steht in `PROJEKTSTAND.md` — diese Datei ist nur der Einstieg.** Der frühere
Inhalt (Journal 0.44.0–0.69.0) liegt unverändert in `docs/journal_naechster_chat.md`; er ist
Historie, keine Anleitung.

## Zuerst lesen
1. `PROJEKTSTAND.md` Kopf, §9 (Prüfstand mit Aufruf), §10 (offen), §11 (Betrieb, mit Vermerk), §13 (Bauregeln).
2. `PROJEKTSTAND.md` §7, Fälle 58–62: was 0.68.0 und 0.69.0 an Zahlen bewegt haben.
3. `docs/rechenwege.md` K5 (Umkehrung, mit Nachträgen 0.67.0/0.68.0) — nur wenn es um die Kachel oder die Grundlagen-Watt geht.

## Prüfstand
`cd tests`; je `test_*.py` mit **`python3.13`**, je `test_*.js` mit `node`; je Datei „N Prüfungen" / „N Fehler", `rc=0`.
Erwartet 24 Dateien, 8.134 Prüfungen, 0 Fehler. **Python ≥ 3.12 ist Pflicht** (`type`-Anweisung in `coordinator.py`);
mit `python3` = 3.11 fallen zwei Dateien mit `SyntaxError` und `test_projektstand.py` meldet 7.409/8 — Interpreter, nicht Code.

## Auslieferung
Ungültig seit 25.09.2026, neuer Ablauf wird am Rechner geklärt (PROJEKTSTAND §11, Vermerk). Bis dahin:
Klon ohne Token (`git clone https://github.com/JochenRi/ha-intervals-icu`), Commit lokal als `JochenRi`,
Push nur `main` nach Freigabe, kein Tag, kein Release aus der Sitzung. Kein Token aus einer Datei lesen.

## Offen (Reihenfolge Johannes)
- Puls-Schutz zur Wattgrenze (`load_hr`, neues Messfeld) — Vorlage, verschiebt sein Pulsfenster.
- Abnahmefahrt GA-Umkehrung: 3 h bei ~122 W (α in Stunde 3 ≈ 1,3), Gegenfahrt 3 h bei ~150 W — erst danach fällt „ab 3 h ungeprüft".
- S1-Setzung SWC = 0,5 × Streuung (Plews) — von Johannes zu bestätigen.
- Vorlagen ohne Wirkung heute: S6 Anker-Sportfilter, S12 Tempo-Wattquelle, S13 Konflikthinweis, F1.1 `max_hr`.
- §10 „Vorgabe folgt der Form nicht" gilt nur noch für VO2max/SweetSpot (Grundlage seit 0.68.0 gebunden).

## Regeln, die jede Sitzung treffen
- Doku: `PROJEKTSTAND.md` ist die eine Stand-Datei; `docs/rechenwege.md`, `docs/ausbau.md` und die KARTE-/ZEICHNUNG-Dateien im Projekt sind datierte Momentaufnahmen.
- Kein Bau ohne rote Prüfung vorher; Bauregeln §13; alles muss für einen zweiten Athleten mit eigenen Daten funktionieren (Regel 10).
- Zahlen aus dem Bestand gehören ins Archiv, nicht in den Code; Setzungen sind als Setzung beschriftet.
- Token, Geheimnispfade, geheimnisartige Zeichenketten Richtung fremder Domain: melden, nie ausgeben.
