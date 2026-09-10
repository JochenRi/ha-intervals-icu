# ha-intervals-icu — Projektstand

**Stand:** 10.09.2026 · **Version:** 0.9.0 · **Status:** läuft produktiv auf HEIMDALL

Eine eigene Home-Assistant-Integration, die Trainingsdaten von Intervals.icu
lokal archiviert, auswertet und in einem eigenen Seitenleisten-Panel darstellt.
Später als kostenloses HACS-Repository für andere gedacht.

**Was 0.9.0 gegenüber 0.8.0 ändert:** das Panel ist vollständig neu gebaut —
größere Schrift, mittige Hauptanzeige, Verlaufskurven je Aktivität, einzeln
aufklappbare Karten. Dazu ein neuer WebSocket-Befehl, der die Rohdaten einer
Einheit live holt. Das Backend ist bis auf diesen Zusatz unverändert.

---

## 1. Was das Ding tut

| Ebene | Inhalt |
|---|---|
| API-Client | Holt Wellness, Aktivitäten, Kalender und Streams von Intervals.icu |
| Archiv | Vollständige Historie lokal in `.storage`, ~300 kB, keine Datenbank |
| Entitäten | 49 Sensoren + Kalender-Entität für Automationen und Langzeitstatistik |
| Auswertung | Trainingslast, DFA alpha-1, Bereitschaftsampel, Lastbudget |
| Panel | Eigener Eintrag „Intervals" in der Seitenleiste, sieben Ansichten |

**Aktueller Datenbestand (Konto i123456):**
486 Wellness-Tage · 238 Aktivitäten (13.05.2025 – 09.09.2026) · 56 DFA-Auswertungen ·
1 nicht abrufbare Strava-Aktivität

---

## 2. Aufbau

```
custom_components/intervals_icu/
├── api.py            REST-Client: Basic Auth, Drosselung, Wiederholung bei 429/5xx
├── config_flow.py    Einrichtung nur mit API-Key, Reauth bei abgelaufenem Schlüssel
├── coordinator.py    Abruf im Takt, Auth-Fehler → Reauth, Archiv-Synchronisation
├── store.py          Archiv über die offizielle HA-Storage-Schnittstelle
├── importer.py       Import- und Zusammenführ-Logik, versioniert
├── derive.py         Parselogik (HA-frei, damit simulierbar)
├── analytics.py      Trainingsauswertung (HA-frei, damit simulierbar)
├── sensor.py         49 Entitäten
├── calendar.py       Kalender-Entität mit geplanten Workouts
├── websocket.py      11 Kommandos für das Panel (322 Zeilen)
└── frontend/
    └── intervals-panel.js   Panel, eine einzige Datei ohne Abhängigkeiten (1.482 Zeilen)
```

**Rund 5.100 Zeilen Code, davon ~1.500 Frontend.**

### Warum so und nicht anders

- **Kein zweites Repository für die Karte.** Panel und Hilfsfunktionen liegen in
  einer Datei. Eine zweite Datei ist eine zweite Sache, die beim Kopieren
  verlorengehen kann — und der Browser meldet nie, *welcher* Import fehlte.
- **Archiv statt Recorder.** HA löscht Rohzustände nach ~10 Tagen und erzeugt
  Statistiken nicht rückwirkend. Aktivitäten gehören nicht in die State-Machine;
  das Panel liest die WebSocket-Schnittstelle.
- **Streams bewusst nicht im Archiv.** Ein Jahr Sekundendaten hat auf der Platte
  nichts verloren. Der Befehl `intervals_icu/streams` holt sie beim Öffnen einer
  Einheit live, dünnt sie auf höchstens 900 Punkte aus (Eimer werden gemittelt,
  Lücken bleiben Lücken) und schickt sie durch. Nichts davon wird gespeichert.
- **HA-freie Kernlogik.** `derive.py` und `analytics.py` importieren nichts von
  Home Assistant. Dadurch lässt sich jede Rechnung außerhalb von HA gegen echte
  Datensätze durchspielen.

---

## 3. Verifizierte Erkenntnisse über die Intervals-API

Alles am eigenen Konto geprüft, nicht aus Dokumentation übernommen.

| Erkenntnis | Bedeutung |
|---|---|
| Auth ist **HTTP Basic** mit dem literalen Benutzernamen `API_KEY` | Bearer-Token funktioniert nicht — der häufigste 403-Grund |
| Athlete-IDs tragen meist ein führendes `i` (`i123456`) | nur früh registrierte Strava-Nutzer haben reine Zahlen |
| CTL/ATL heißen im Wellness-Datensatz **`ctl`/`atl`** | nicht `icu_ctl`, wie im Forum behauptet |
| `fields=` funktioniert | ganzer Jahresbestand in einer Anfrage statt 200 Feldern je Einheit |
| Zonenzeiten kommen in **zwei Formaten** | Puls: Zahlenliste · Leistung: Objekte mit `secs` |
| Strava-Aktivitäten liefert die API **nicht** aus | Platzhalter mit `_note`, müssen übersprungen werden |
| `/activity/<id>/streams.json` liefert eine **Liste** von Stream-Objekten | kein Mapping — `derive.streams_to_dict` macht daraus `name → daten` |
| `dfa_a1` liegt sekundengenau in den Streams | bei 56 von 238 Einheiten, abhängig von der Aufzeichnung |
| DFA-Streams enthalten `0.0`-Artefakte am Anfang | zählt sonst fälschlich als anaerob |
| Puls- und Wattströme enthalten Nullen (Aussetzer, Rollen) | verfälschen sonst die Schwellenablesung |
| Gewicht 73,5 kg ist **nicht gemessen** | `icu_weight_sync: NONE`, Wert stammt aus der Aktivitätsdatei (`tempWeight: true`) |
| VO2max kommt nur an Trainingstagen | Garmin rechnet ihn nur nach passenden Einheiten neu |

---

## 4. Auswertungen und ihre Belege

Jede Kennzahl im Panel trägt Quelle und Grenzen sichtbar mit sich.

| Kennzahl | Quelle | Grenze |
|---|---|---|
| Form-Zonen | Joe Friel; Intervals rechnet relativ zur Fitness | Faustregel, „keine Wissenschaft" — sagt der Entwickler selbst |
| Akut zu chronisch (7:28) | Gabbett/Blanch, Korridor 0,8–1,3, Risiko ab 1,5 | korrelativ, mathematisch gekoppelt, formelle Richtigstellung beantragt, RCT ohne Nutzen |
| Monotonie / Strain | Foster: Wochenmittel ÷ Streuung; Strain = Last × Monotonie | erst ab drei Trainingstagen aussagekräftig |
| Intensitätsverteilung | Dreizonenmodell Seiler, Elite ≈ 75/8/17 | polarisiert vorn beim VO2peak, kleiner Effekt, begründeter Widerspruch |
| HRV-Trend | 7-Tage-Mittel ln(rMSSD) gegen kleinste bedeutsame Änderung (±0,5 SD) | Nachtmessung, nicht die validierte Morgenmessung im Liegen |
| Entkopplung | Joe Friel: ≤ 5 % bei ruhigen Dauereinheiten | negativ = kein Warnzeichen; nur bei gleichmäßiger Fahrt aussagekräftig |
| DFA alpha-1 | Rogers/Gronwald: 0,75 ≈ VT1, 0,5 ≈ VT2 | gegen Gasaustausch validiert; empfindlich für Artefakte und Gerät |
| Selbsteinschätzung | Saw et al., systematischer Review über 56 Studien | eigene Angaben schlagen objektive Messwerte in Empfindlichkeit |
| **Bereitschaftsampel** | hier aus den Zeilen darüber zusammengesetzt | Bestandteile belegt, **Kombination nicht** — kein kommerzieller Bereitschaftswert ist unabhängig validiert |
| **Lastbudget** | ACWR-Definition nach heute aufgelöst | `7 × chronisch × Ziel − letzte sechs Tage`; Zielwahl je Ampelfarbe ist eine Setzung |

---

## 5. Das Panel (neu in 0.9.0)

Sieben Ansichten, **Startseite ist „Heute"** — das Urteil zuerst, die Herleitung
darunter.

1. **Heute** — Ring aus sieben Segmenten, eines je Signal in dessen Ampelfarbe:
   man sieht nicht nur *dass* es rot ist, sondern *woraus* das Rot besteht.
   Daneben der Urteilssatz, das Lastbudget als Bullet-Graph mit den Marken
   „gleichbleibend / Korridor / Risiko" und einem aufklappbaren Rechenweg, dazu
   die nächste geplante Einheit mit Budget-Abgleich. Darunter je Signal eine
   Karte mit Großwert, Referenz, immer sichtbarer 42-Tage-Kurve und einem
   **einzeln** aufklappbaren Feld „Verlauf & Quelle".
2. **Kalender** — Wochenraster: Wochenkarte links (Last, Abweichung vom Schnitt,
   Stunden/km/Einheiten, Fitness/Form), sieben Tagesspalten mit Wellness-Werten
   als Symbole. Einheiten als Kacheln mit Sportfarbe und DFA-Mikrobalken, Klick
   öffnet das Detail. Geplantes gestrichelt, mit drei getrennten Zuständen:
   erledigt (Haken) · ausgelassen (Kreuz) · geplant.
3. **Fitness** — drei gestapelte Felder (Fitness/Ermüdung · Tagesbelastung ·
   Form mit Friel-Zonenbändern) über einer gemeinsamen Zeitachse mit **einem**
   Ablese-Cursor. Zeitraum 42 Tage bis ein Jahr.
4. **Aktivitäten** — Tabelle, Detail je Einheit: Kennzahlen als Kachelraster,
   darunter der Verlauf als gestapelte Kleinvielfache (Leistung roh + 30-s-Mittel,
   Herzfrequenz, DFA mit 0,75/0,5-Bändern, Kadenz, Tempo, Höhe), ein Cursor über
   alle Felder. Dazu die DFA-Bandverteilung und die abgelesene Schwelle.
5. **Belastung** — fünf Abschnitte, jeder mit einer Zeile „Zu lesen als:" und
   aufklappbarer Quelle: Wochenlast mit Bezugslinie und Monotonie-Markern,
   ACWR mit Korridorbändern, Intensitätsverteilung **zweifach** (geplante Zonen
   gegen DFA-gemessen — weichen sie ab, passen die Zonen nicht zur Physiologie),
   HRV-Trend mit Basislinienband, Entkopplung gegen die 5-%-Marke.
6. **DFA** — Erklärtext, Sportfilter, Kennzahlen, Schwellen-Herzfrequenz mit
   rollierendem Median; die Leistung liegt als **eigenes Feld** darunter statt
   auf einer zweiten Achse. Dünne Messungen (< 5 Punkte im Schwellenfenster)
   sind hohl gezeichnet und zählen nicht in den Median.
7. **Plan** — geplante Workouts nach Tagen gruppiert, Volltext aufklappbar,
   für heute mit Budget-Abgleich.

### Gestaltungsregeln (aus der Wahrnehmungsforschung)

Cleveland & McGill, mehrfach repliziert: Position ist der genaueste Kanal, dann
Länge auf gemeinsamer Grundlinie; Winkel, Fläche und Farbe liegen dahinter.
Daraus und aus der Recherche für 0.9.0:

- **Menge → Länge auf gleicher Grundlinie.** Keine Kreise, keine Flächen.
- **Zeit → Position** im Raster.
- **Kategorie → Farbton** (Sportart), nie eine Menge.
- **Zustand → Farbe *und* Wort *und* eigene Icon-Form.** Dreifach, weil rund
  8 % der Männer Rot und Grün nicht trennen können (WCAG 1.4.1).
- **Wichtigkeit → Größe.** Eine Leitzahl je Ansicht.
- **Keine zweiten Achsen.** Verwandte Reihen stapeln als Kleinvielfache über
  einer gemeinsamen Zeitachse mit einem Cursor.
- **Kein Tacho.** Für „Ist-Wert gegen Zielbereich" ein Bullet-Graph (Few).
- **Aufklappfelder sind unabhängig.** Gemeinsames Zuklappen verhindert
  Vergleichen; native `<details>` überall.
- **Quellen eingeklappt**, nicht als Textwand daneben.

**Geändert gegenüber 0.8.0:** die Formsprache ist nicht mehr Monospace mit
`── ABSCHNITT ──`-Trennern, sondern eine proportionale Systemschrift mit
Tabellenziffern, 15 px Grundgröße. Grund: Lesbarkeit auf Distanz und am Handy.

---

## 6. Prüfstand

**Achtung — der Prüfstand ist seit 0.9.0 nur noch zur Hälfte gültig.**

| Datei | prüft | Stand |
|---|---|---|
| `test_derive.py` | Parselogik gegen echte Payloads | gültig |
| `test_dfa.py` | DFA-Auswertung, Bandgrenzen, Artefakte, Aussetzer | gültig |
| `test_import.py` | vollständiger Import gegen einen Nachbau des Kontos | gültig |
| `test_analytics.py` | Trainingsmetriken gegen bekannte Ergebnisse | gültig |
| `test_setup_simulation.py` | Entity-Aufbau, Übersetzungen, unique_ids | gültig |
| `test_panel_utils.mjs` | Formatierung und Zeichenlogik | **veraltet** — prüft das alte Panel |
| `test_panel.mjs` | Panel im simulierten DOM | **veraltet** |
| `test_panel_load.mjs` | Ladekette wie im Browser | **veraltet** |
| `test_design.mjs` | Gestaltungsregeln: Rangfolge, Farbe+Wort, Palette | **veraltet** |

Der Neubau wurde vor der Auslieferung gegen zwei eigene Simulationsläufe
geprüft (alle sieben Ansichten mit vollen, leeren, löchrigen und degenerierten
Daten; Cursor-Geometrie, Randklemmung, Extremwerte, Zahlenformatierung).
**Diese Läufe liegen bislang nicht im Repository** — sie gehören als Ersatz für
die vier veralteten Dateien eingecheckt. Bis dahin gilt: das Frontend hat keinen
laufenden Regressionsschutz.

Ausführen: `python3 tests/<datei>.py` bzw. `node tests/<datei>.mjs`.

---

## 7. Fehler, die der Prüfstand gefunden hat

| Version | Fehler | Ursache |
|---|---|---|
| 0.2.0 | alle Wellness-Sensoren `unavailable` | Methode `_entry()` überschrieb ein Basis-Attribut |
| 0.3.0 | Historien-Import lief nie | „Archiv leer?" wurde geprüft, *nachdem* es befüllt war |
| 0.5.0 | alle Ansichten „Unknown error" | Zonenzeiten in Objektform, `float()` auf ein dict |
| 0.5.0 | ein Ausfall riss alles mit | `Promise.all` statt `allSettled` |
| 0.5.1 | Panel lädt nicht | zweite JS-Datei fehlte beim Kopieren |
| 0.6.0 | Absturz bei `null`-Antwort | Feldform ging verloren |
| 0.7.0 | zwei verschiedene Gelbtöne | Palettendisziplin |
| 0.8.0 | zweites Blau | dieselbe Fehlerklasse |
| 0.9.0 | einzelne Messpunkte zwischen Datenlücken unsichtbar | Pfad nur mit `M`, ohne `L` — in der Simulation gefunden und behoben |

---

## 8. Offen

**Bekannte Fehler in 0.9.0** (im Livebetrieb gefunden, noch nicht behoben):

| # | Fehler | Regel, gegen die er verstößt |
|---|---|---|
| 1 | zwei Blautöne (Tempo neben Blau) und zwei Rottöne (Herzfrequenz neben Rot) | Abschnitt 7, Fehlerklasse 0.7.0/0.8.0 — dritter Rückfall |
| 2 | Nullwerte in HF-, Watt- und DFA-Strömen roh gezeichnet | Abschnitt 3: Nullen sind Aussetzer, keine Messwerte; `dfa_summary` filtert sie, das Detail-Chart nicht |
| 3 | DFA-Sportfilter zeigt „Rad" doppelt (`Ride` und `VirtualRide`) | Filter muss nach Sportgruppe zusammenfassen |
| 4 | ACWR-Diagramm von einem Ausreißer gequetscht, Beschriftungen überlappen | Achse kappen, Labels entzerren |
| 5 | x-Achse zeigt Monate doppelt | Tickabstand rechnet in Punkten statt in Kalendermonaten |
| 6 | Ablese-Kasten am rechten Rand abgeschnitten | Umklappen rechnet mit fester statt echter Kastenbreite |
| 7 | HRV-Karte mischt Einheiten (Großwert `ln rMSSD`, Kurve „in ms") | eine Einheit je Kachel |
| 8 | DFA-Tab zeigt vier gleich große Zahlen | „eine Leitzahl je Ansicht" |

**Danach:**
- Frontend-Tests neu schreiben, die beiden Simulationsläufe ins Repository
- einfacherer Weg, Änderungen einzuspielen (bislang: Dateien von Hand kopieren)
- Webhooks statt Polling — Intervals bietet sie für Uploads und Kalenderänderungen
- Schreibseite: Workouts aus HA heraus planen
- Historien-Import in die HA-Langzeitstatistik (`async_import_statistics`),
  damit HEIMDALL auf Trainingsdaten automatisieren kann

**Für die Veröffentlichung:**
- Repository bei GitHub anlegen, MIT-Lizenz liegt bei
- CI läuft bereits mit: `hacs/action` + `home-assistant/actions/hassfest`
- Brand-Icon 256×256 an `home-assistant/brands` (PR)
- Aufnahme in den HACS-Standardkatalog beantragen — dauert erfahrungsgemäß Monate,
  bis dahin Installation über „Custom repository"

**Zwei Hinweise persönlich:**
1. Der API-Key steht im Klartext im Chatverlauf. Vor Veröffentlichung in
   Intervals neu erzeugen, in HA über den Reauth-Dialog eintragen.
2. Die tägliche Wellness-Abfrage in Intervals einschalten. Selbsteingeschätzte
   Werte sind laut Review der empfindlichste Einzelindikator — das ist die
   stärkste mögliche Verbesserung der Bereitschaftsampel.

---

## 9. Betrieb

**Installation/Update:** Ordner `custom_components/intervals_icu` komplett
ersetzen, HA neu starten, Browser hart neu laden (Strg+Shift+R).

**Wichtig:** Die Unterordner `frontend/` und `translations/` müssen mitkopiert
werden. Fehlt `frontend/`, schreibt die Integration eine klare Fehlermeldung ins
Log und das Panel erscheint nicht.

**Cache:** `PANEL_VERSION` in `const.py` hängt an der Modul-URL. Wer das Panel
ändert, ohne die Zahl zu erhöhen, sieht im Browser weiter die alte Fassung.

**Diagnose:**
- Archivstand: Sensor „Archiv" oder
  `jq '{tage:(.data.wellness|length), akt:(.data.activities|length), dfa:(.data.dfa|length)}' /homeassistant/.storage/intervals_icu.i123456`
- Log: `custom_components.intervals_icu`
- Panel-Fehler: Browser-Konsole (F12)

**Datenhaltung:** Archiv in `.storage/intervals_icu.<athlet>`, API-Key im
Config-Entry. Beides überlebt ein Ersetzen des Integrationsordners.
