# ha-intervals-icu — Projektstand

**Stand:** 11.09.2026 · **Version:** 0.9.5 · **Status:** läuft produktiv auf HEIMDALL, Auslieferung über HACS

Eine eigene Home-Assistant-Integration, die Trainingsdaten von Intervals.icu
lokal archiviert, auswertet und in einem eigenen Seitenleisten-Panel darstellt.
Später als kostenloses HACS-Repository für andere gedacht.

**Was 0.9.1 gegenüber 0.9.0 ändert:** die acht im Livebetrieb gefundenen
Anzeigefehler sind behoben, dazu ein echter Fehler im Backend — der
Archiv-Abgleich lief nur beim Start, nie im Sechs-Stunden-Takt. Jeder Wert
trägt jetzt sichtbar sein Datum. Der Prüfstand ist wieder vollständig: vier
neue Frontend-Tests ersetzen die vier veralteten.

**Auslieferung seit 0.9.1 über HACS** — Repository `JochenRi/ha-intervals-icu`,
eingetragen als benutzerdefiniertes Repository, Kategorie Integration. Dateien
werden nicht mehr von Hand kopiert.

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
    └── intervals-panel.js   Panel, eine einzige Datei ohne Abhängigkeiten (1.619 Zeilen)
```

**Rund 5.200 Zeilen Code, davon ~1.600 Frontend.**

### Die Palette, seit 0.9.1 in zwei Registern

Dreimal in Folge (0.7.0, 0.8.0, 0.9.0) ist dieselbe Fehlerklasse durchgerutscht:
zwei Töne für dieselbe Rolle. Deshalb liegt die Farbgebung jetzt strukturell fest:

- **Zustandsregister** (grün, gelb, rot, grau) bedeutet ein Urteil — sonst nichts.
  Keine Sportart, keine Datenreihe trägt je einen dieser Töne.
- **Datenregister** (blau, violett, cyan, magenta, schiefer, dunkelgrau) trägt
  Kategorien und Kanäle. Innerhalb einer Ansicht kommt jeder Ton höchstens einmal vor.

`tests/test_panel_fixes.js` prüft beide Regeln bei jedem Lauf.

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
| Runden liefert die API **nicht** als eigenen Endpunkt | sie hängen an der Aktivität: `/activity/<id>?intervals=true` (Forum-Thread 126341, bestätigt) |
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

**Acht Testläufe, 576 Einzelprüfungen, alle grün.** Kein Test braucht eine
laufende HA-Instanz oder einen Browser.

| Datei | prüft |
|---|---|
| `test_derive.py` | Parselogik gegen echte Payloads |
| `test_dfa.py` | DFA-Auswertung, Bandgrenzen, Artefakte, Aussetzer |
| `test_import.py` | vollständiger Import gegen einen Nachbau des Kontos |
| `test_analytics.py` | Trainingsmetriken gegen bekannte Ergebnisse |
| `test_setup_simulation.py` | Entity-Aufbau, Übersetzungen, unique_ids |
| `test_laps.py` | Runden-Normalisierung gegen unbekannte Feldnamen und kaputte Payloads (34) |
| `test_websocket_registration.py` | jeder registrierte Befehl trägt seinen Dekorator, Namen eindeutig, Panel ruft nichts Unbekanntes (73) |
| `test_panel_views.js` | alle sieben Ansichten gegen volle, leere, löchrige und entartete Daten (283) |
| `test_panel_fixes.js` | je ein Nachweis pro behobenem Fehler (136) |
| `test_panel_design.js` | Cursor-Geometrie und die Gestaltungsregeln als Zusicherung (44) |

Die drei Frontend-Tests laden `intervals-panel.js` ohne Browser und rendern
jede Ansicht gegen erfundene, aber formgleiche Payloads. `panel_harness.js`
stellt die Umgebung, `panel_fixtures.js` die Daten — darunter bewusst
Aussetzer, Nullwerte, ein ACWR-Ausreißer und ein Morgen ohne Wellness-Zeile.

Ausführen: `python3 tests/<datei>.py` bzw. `node tests/<datei>.js`.

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
| 0.9.1 | Archiv-Abgleich lief nur beim Start, nie im Takt | Timer-Aktion war ein Lambda statt einer Coroutine-Funktion: HA führt sie im Executor-Thread aus, die erzeugte Aufgabe wird nie abgewartet. HA protokolliert genau das |
| 0.9.1 | Ablesekasten ragte bei Mauszeiger außerhalb des Fensters hinaus | Klemmung nur in eine Richtung — in der neuen Simulation gefunden |
| 0.9.2 | Ablesekasten rutschte auf breitem Monitor weiter aus dem Bild | gegen das Panel-Element geklemmt statt gegen `#app` (max. 1240 px, **zentriert**). Beide Rahmen waren im Test gleich groß gestubbt — der Test war grün, die Realität nicht. Die Testumgebung hält jetzt zwei verschiedene Rahmen |
| 0.9.5 | **Integration startete nicht mehr** — kein Dashboard, keine Entitäten | der neue Handler wurde zwischen die Dekoratoren und das `def` des Nachbarn gesetzt: die Dekoratoren erwischten den neuen Befehl, `websocket_streams` ging nackt raus, HA lehnte die Registrierung ab und das Setup brach ab. Gefunden im Livebetrieb, gekostet: ein Neustart. Seitdem prüft `test_websocket_registration.py` genau das |
| 0.9.4 | Runden-Urteil verglich Aufwärmen mit Ausfahren und meldete „34 % Abfall" | ein Serienurteil darf nur **vergleichbare** Abschnitte gegeneinander stellen (ähnliche Leistung, ähnliche Dauer) — in der Simulation gefunden, bevor es je jemand sah |
| 0.9.3 | Ablesekasten **zum dritten Mal** am falschen Fleck | zweimal an der Positionsrechnung repariert, zweimal falsch. Statt eines dritten Versuchs wurde die Fehlerklasse entfernt: die Werte stehen jetzt in einer **festen Leiste** im Kartenkopf, es gibt kein positioniertes Element mehr. Kein Rahmen, den man verwechseln kann |
| 0.9.2 | DFA-Achse von 0 bis 160, echte Schwelle als Strich | eine Null-Schwelle und eine Gehen-Messung aus einem einzigen Messpunkt bestimmten die Achse — dieselbe Artefaktklasse wie in den Strömen, nur in der Schwellenreihe |

---

## 8. Offen

**In 0.9.1 behoben** (alle im Livebetrieb gefunden, jeder mit eigenem Regressionstest):

| # | war | jetzt |
|---|---|---|
| 1 | zwei Blau- und zwei Rottöne | Palette in Zustands- und Datenregister getrennt, Test erzwingt es |
| 2 | Nullwerte in HF-, Watt- und DFA-Strömen roh gezeichnet | Null gilt dort als Aussetzer und wird zur Lücke; bei Kadenz und Tempo bleibt sie ein Messwert (Stillstand) |
| 3 | DFA-Sportfilter zeigte „Rad" doppelt | Filter gruppiert nach Sportgruppe, `Ride` und `VirtualRide` fallen zusammen |
| 4 | ACWR-Diagramm von einem Ausreißer gequetscht | Achse bei 2,2 gekappt, Ausreißer geklemmt und mit Höchstwert ausgewiesen; Beschriftungen weichen nach links aus |
| 5 | x-Achse zeigte Monate doppelt | Ticks sitzen auf Kalendermonaten statt auf Punktabständen |
| 6 | Ablesekasten am Rand abgeschnitten | Umklappen rechnet mit der gemessenen Kastenbreite, beidseitig geklemmt |
| 7 | HRV-Karte mischte Einheiten | Kurve zeigt ln(rMSSD) mit Basislinienband, dieselbe Größe wie der Großwert |
| 8 | DFA-Tab zeigte vier gleich große Zahlen | eine Leitzahl, drei Nebenwerte |
| 6b | Kasten rutschte auf breitem Monitor trotzdem heraus (0.9.2) | Klemmung gegen `#app` statt gegen das Panel-Element |
| 10 | DFA-Achse von Artefakten bestimmt (0.9.2) | Achse folgt den belastbaren Messungen, Artefakte werden geklemmt und ausgewiesen |
| 9 | kein Datum sichtbar | Kopfzeile mit vollem Datum, jede Signalkarte mit „heute" oder „Stand TT.MM.JJJJ" in Warnfarbe |

**Als Nächstes:**
- Webhooks statt Polling — Intervals bietet sie für Uploads und Kalenderänderungen
- Schreibseite: Workouts aus HA heraus planen
- Historien-Import in die HA-Langzeitstatistik (`async_import_statistics`),
  damit HEIMDALL auf Trainingsdaten automatisieren kann
- Brand-Icon 256×256 an `home-assistant/brands` (PR) — solange es fehlt, bleibt
  die HACS-Prüfung im CI rot; für die Installation als benutzerdefiniertes
  Repository ist das ohne Belang

**Für die Veröffentlichung:**
- Repository liegt öffentlich: `github.com/JochenRi/ha-intervals-icu`, MIT-Lizenz
- CI läuft: `hacs/action` + `home-assistant/actions/hassfest` (hassfest grün)
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

**Installation/Update:** über HACS — Repository ist als benutzerdefiniertes
Repository eingetragen (Kategorie Integration). Neue Version erscheint dort,
herunterladen, HA neu starten, Browser hart neu laden (Strg+Shift+R).
Von Hand geht es weiterhin: Ordner `custom_components/intervals_icu` ersetzen.

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
