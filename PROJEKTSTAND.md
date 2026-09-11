# ha-intervals-icu — Projektstand

**Stand:** 11.09.2026 · **Version:** 0.31.0 · **Status:** produktiv auf HEIMDALL,
Auslieferung über HACS aus `github.com/JochenRi/ha-intervals-icu`

Eine eigene Home-Assistant-Integration, die Trainingsdaten von Intervals.icu lokal
archiviert, auswertet und in einem eigenen Seitenleisten-Panel darstellt.

**Umfang:** ~8.900 Zeilen, davon 3.130 Frontend · 21 WebSocket-Befehle · 15 Einheiten in
8 Familien · 14 Testdateien mit rund 1.900 Einzelprüfungen · 31 Releases.

---

## 1. Was das Ding tut

| Ebene | Inhalt |
|---|---|
| API-Client | Wellness, Aktivitäten, Kalender, Streams, Runden; ein Schreibweg (Workout planen) |
| Archiv | Vollständige Historie lokal in `.storage`, ~300 kB, keine Datenbank |
| Entitäten | 49 Sensoren + Kalender-Entität für Automationen und Langzeitstatistik |
| Auswertung | Trainingslast, DFA alpha-1, Zustandserkennung, Lastbudget, Einheitenvorschläge, Nachtreaktion, Einordnung gegen die eigene Historie |
| Panel | Eintrag „Intervals" in der Seitenleiste, acht Ansichten |

**Datenbestand:** 487 Wellness-Tage · 239 Aktivitäten · 57 DFA-Auswertungen

---

## 2. Aufbau

```
custom_components/intervals_icu/
├── api.py            REST-Client: Basic Auth, Drosselung, Wiederholung bei 429/5xx
│                     — Schreibzugriffe werden NICHT wiederholt (siehe 8.)
├── config_flow.py    Einrichtung nur mit API-Key, Reauth bei abgelaufenem Schlüssel
├── coordinator.py    Abruf im Takt, Auth-Fehler → Reauth, Archiv-Synchronisation
├── store.py          Archiv über die offizielle HA-Storage-Schnittstelle
├── importer.py       Import- und Zusammenführ-Logik, versioniert
├── derive.py         Parselogik: Streams, DFA, Runden (HA-frei)
├── analytics.py      PMC, ACWR, Monotonie, Bereitschaft (HA-frei)
├── coach.py          Zustand, Anker, Signalmatrix, Nachtreaktion, Einordnung (HA-frei)
├── workouts.py       Einheitenbibliothek mit Belegen und Intervals-Syntax (HA-frei)
├── plan.py           Zielprofil und Wochenlogik (HA-frei)
├── sensor.py         49 Entitäten
├── calendar.py       Kalender-Entität mit geplanten Workouts
├── websocket.py      21 Kommandos für das Panel
└── frontend/
    └── intervals-panel.js   Panel, eine Datei ohne Abhängigkeiten (3.130 Zeilen)
```

**Fünf HA-freie Module** (`derive`, `analytics`, `coach`, `workouts`, `plan`) importieren
nichts von Home Assistant. Jede Rechnung und jede Regel lässt sich außerhalb von HA gegen
echte Datensätze durchspielen — der gesamte Prüfstand beruht darauf.

**Archiv statt Recorder.** HA löscht Rohzustände nach ~10 Tagen und erzeugt Statistiken
nicht rückwirkend. Streams und Runden liegen bewusst *nicht* im Archiv: sie werden beim
Öffnen einer Einheit live geholt, auf höchstens 900 Punkte ausgedünnt und nicht gespeichert.

---

## 3. Verifizierte Erkenntnisse über die Intervals-API

Alles am eigenen Konto geprüft, nicht aus Dokumentation übernommen.

| Erkenntnis | Bedeutung |
|---|---|
| Auth ist **HTTP Basic** mit dem literalen Benutzernamen `API_KEY` | Bearer-Token funktioniert nicht — der häufigste 403-Grund |
| Athlete-IDs tragen meist ein führendes `i` | nur früh registrierte Strava-Nutzer haben reine Zahlen |
| CTL/ATL heißen im Wellness-Datensatz **`ctl`/`atl`** | nicht `icu_ctl`, wie im Forum behauptet |
| **Die FTP steht auf jeder Aktivität als `icu_ftp`** | nicht in `sport_settings` — das kostete drei Releases (siehe 7.) |
| **Die Tageslast steht in den Aktivitäten**, nicht verlässlich in `wellness.load` | dasselbe Muster, derselbe Tag |
| `fields=` funktioniert | ganzer Jahresbestand in einer Anfrage |
| Zonenzeiten kommen in **zwei Formaten** | Puls: Zahlenliste · Leistung: Objekte mit `secs` |
| Strava-Aktivitäten liefert die API **nicht** aus | Platzhalter mit `_note`, müssen übersprungen werden |
| `/activity/<id>/streams.json` liefert eine **Liste** | kein Mapping — `derive.streams_to_dict` macht daraus `name → daten` |
| **Runden** haben keinen eigenen Endpunkt | sie hängen an der Aktivität: `?intervals=true`, Feld `icu_intervals`; mit `start_index`/`end_index` **und** `start_time`/`end_time` |
| **Workouts planen:** Schritte als Plaintext ins Feld `description` | `workout_doc` bleibt leer, Intervals parst selbst |
| `dfa_a1` liegt sekundengenau in den Streams | bei 57 von 239 Einheiten, abhängig von der Aufzeichnung |
| DFA-Streams enthalten `0.0`-Artefakte am Anfang | zählt sonst fälschlich als anaerob |
| Puls- und Wattströme enthalten Nullen (Aussetzer, Rollen) | verfälschen sonst die Schwellenablesung |
| Gewicht ist **nicht gemessen** | `icu_weight_sync: NONE`, Wert stammt aus der Aktivitätsdatei |
| VO2max kommt nur an Trainingstagen | Garmin rechnet ihn nur nach passenden Einheiten neu |

---

## 4. Die acht Ansichten

| Ansicht | Inhalt |
|---|---|
| **Trainer** | Zwei Kacheln (Ziel, Zeit) · Zustand als drei beschriftete Zeilen auf einer Achse · Leitempfehlung für heute · sieben Einheiten mit Watt, Wirkung, Beleg und Tagesurteil |
| **Signale** | Alle Signale auf einer Zeitachse in Standardabweichungen, Zustandsbänder im Hintergrund, Lastbalken nach gefahrenen DFA-Bereichen |
| **Heute** | Was heute möglich ist + Obergrenze als Bullet-Graph · jedes Signal einzeln mit seinem System, aufklappbar mit 42-Tage-Kurve und eigenen Bereichen · sieben Tage Last · die Nacht nach der letzten Einheit |
| **Kalender** | Wochenraster mit Wellness-Symbolen, Einheiten als Kacheln |
| **Fitness** | Fitness/Ermüdung · Tagesbelastung · Form mit Friel-Zonen, gemeinsame Zeitachse |
| **Aktivitäten** | Tabelle; je Einheit: Kennzahlen, Runden, Segmentanalyse, Einordnung gegen die eigene Historie, Nachtreaktion, Verlaufskurven |
| **Belastung** | Wochenlast, ACWR, Intensitätsverteilung zweifach, HRV-Trend, Entkopplung |
| **DFA** | Schwellenverlauf mit rollierendem Median |

---

## 5. Auswertungen und ihre Belege

Jede Kennzahl trägt Quelle und Grenze sichtbar mit sich.

| Kennzahl | Quelle | Grenze |
|---|---|---|
| Form-Zonen | Joe Friel | Faustregel, „keine Wissenschaft" — sagt der Entwickler selbst |
| Akut zu chronisch | Gabbett/Blanch, Korridor 0,8–1,3 | korrelativ, mathematisch gekoppelt, formelle Richtigstellung beantragt, RCT ohne Nutzen |
| Monotonie / Strain | Foster: Wochenmittel ÷ Streuung | erst ab drei Trainingstagen aussagekräftig |
| Intensitätsverteilung | Dreizonenmodell Seiler, Elite ≈ 75/8/17 | 80/20 ist eine Beschreibung, keine Vorschrift; Review 2023: sieben Studien, kein Beleg für ein überlegenes Modell |
| HRV-Trend | 7-Tage-Mittel ln(rMSSD) gegen 60-Tage-Band, Schwelle 0,5 SD (Plews/Altini) | Nachtmessung der Uhr, nicht die validierte Morgenmessung im Liegen |
| Entkopplung | Friel: ≤ 5 %; trainierte oft < 3 %, Freizeit 5–10 % | nur bei gleichmäßiger Fahrt aussagekräftig |
| DFA alpha-1 | Rogers/Gronwald: 0,75 ≈ VT1, 0,5 ≈ VT2 | gegen Gasaustausch validiert; empfindlich für Artefakte und Gerät |
| Durability | Maunder: Zeitpunkt und Ausmaß der Verschlechterung während langer Belastung | eigene Eigenschaft, unabhängig von FTP und VO2max |
| Kardiale Drift | HF steigt bei konstanter Last; bei Trainierten abgeschwächt | das *Was*; ob Watt/Herzschlag hält, ist das *Na und* |
| Nachtreaktion | Nachtmessung ist die sauberste Bedingung; Rückkehr zur Ruhe-HRV dauert Minuten bis 24 h | **glockenförmiger** Zusammenhang zwischen Last und HRV-Änderung — deshalb nur gegen die eigene übliche Antwort lesbar |
| 30/15 | Rønnestad: signifikant größere Zuwächse über 10 Wochen | **Richtigstellung:** der Vergleich ist *nicht* aufwandsgleich — 29,5 min Arbeit gegen 20 min bei 4×5 |
| VO2max-Formate | 4×4 als Einstiegsdosis, 5×4 als Progression, 30/30 (Billat), 4×8 (Seiler) | „wer den letzten Block nicht mit derselben Leistung schafft, ist zu hart gestartet" |
| Schwellenprogression | erst Häufigkeit, dann Dauer (4×10 → 3×15 → 2×20), zuletzt Intensität | — |
| Harte Tage pro Woche | 2 ist Standard für 8–14-h-Wochen; WorldTour bei 25 h selten mehr als 3 | 80/20 zählt Einheiten, nicht Minuten |
| Blockperiodisierung | 12 Wochen, lastgleich, trainierte Radfahrer | **kein Unterschied** zur traditionellen Periodisierung; ihr Vorteil ist praktisch |
| **Bereitschaftswerte allgemein** | 14 Werte aus 10 Wearable-Häusern untersucht | **keiner legt seine Formel offen**, kaum einer ist validiert; ein niedriger Wert aus kurzer Nacht sieht aus wie einer aus beginnendem Infekt |
| **Bereitschaftsampel hier** | aus den Zeilen darüber zusammengesetzt | Bestandteile belegt, **Kombination nicht** |
| **Lastbudget** | ACWR-Definition nach heute aufgelöst | Zielwahl je Ampelfarbe ist eine Setzung |

### Der wichtigste Befund: die eigene Kalibrierung

Bevor eine Ampel gebaut wurde, wurde geprüft, ob sie bei diesem Athleten überhaupt etwas
vorhersagt. Zielgröße: Watt pro Herzschlag je Einheit, intensitätsbereinigt.

| Prädiktor | r | erklärt | n |
|---|---|---|---|
| HRV, 7-Tage gegen Basislinie | 0,155 | 2,4 % | 97 |
| Ruhepuls | 0,120 | 1,4 % | 97 |
| Schlaf | −0,060 | 0,4 % | 97 |
| Last der letzten 7 Tage | 0,263 | 6,9 % | 100 |

**Bei n = 97 ist r = 0,155 nicht signifikant.** Die Morgenwerte sagen die *feine* Tagesform
dieses Athleten nicht vorher. Das steht so im Panel. **Wofür sie taugen:** einen Infekt
haben sie sauber abgebildet — Ruhepuls +3,7 SD, HRV −2,7 SD. Warnlampe, nicht Feinsteuerung.

### Fallbeispiel: der Infekt vom September 2026

| Tag | HRV | Ruhepuls | Zustand laut Panel |
|---|---|---|---|
| 04.09. | 45 | 59 | Normalbereich, letzte Einheit (Last 129) |
| 06.09. | **30 (−2,7 SD)** | **66 (+3,7 SD)** | Einbruch |
| 08.09. | 55 | 53 | noch im Einbruch (Schlaf 10,9 h) |
| 10.–11.09. | 63 (+1,9 SD) | 50–51 (−2,1 SD) | Erholung nach Einbruch |

Die Erwartung für die erste Einheit danach wurde **vor** der Fahrt festgelegt (9
vergleichbare lockere Einheiten): EF 0,968 ± 0,032 · HF 143 ± 4 · Leistung 139 ± 5 W.

Ergebnis am 11.09.: **EF 1,00 · HF 133 · 133 W · Entkopplung 1,5 %.** Intensitätsbereinigt
wären 0,938 zu erwarten gewesen — tatsächlich 1,00, also **+3,4 Standardabweichungen**. Kein
erhöhter Puls bei gewohnter Leistung, sondern ein deutlich niedrigerer. Einschränkung: ein
Teil davon ist die Erholungsphase selbst und verschwindet mit den nächsten Einheiten.

**Und rückblickend der stärkste Einzelbefund des Systems:** die Fahrt vom 04.09. (3h28,
Last 129) hatte eine Entkopplung von 10,6 % gegen einen eigenen Median von 2,1 % bei 17
Vergleichsfahrten — **Prozentrang 94**. Die Nacht danach lag 2,7 SD unter der eigenen
Normalreaktion auf solche Einheiten. **Der Einbruch kam zwei Tage später.**

---

## 6. Gestaltungsregeln, jede mit Grund

Cleveland & McGill, mehrfach repliziert: **Positionsurteile sind 1,4–2,5 mal genauer als
Längenurteile und rund doppelt so genau wie Winkelurteile.** Daraus und aus der weiteren
Recherche:

- **Menge → Länge auf gemeinsamer Grundlinie.** Keine Kreise, keine Flächen, kein Tacho.
- **Vergleich → Position auf einer gemeinsamen Achse**, nicht Winkel (kein Steigungsdiagramm)
  und nicht getrennte Spuren (keine drei Einzelbalken).
- **Abweichung statt Absolutwert**, wenn die Bezugsgröße bekannt ist — mit **Skala**, sonst
  ist ein Balken eine Ordnung und keine Messung.
- **Zahl in der eigenen Einheit, Balkenlänge normiert.** „+11 bpm" sagt etwas, „+6,5 %" nicht.
- **Zustand → Farbe *und* Wort *und* eigene Icon-Form.** Rund 8 % der Männer trennen Rot und
  Grün nicht (WCAG 1.4.1).
- **Zwei Farbregister, die sich nie mischen.** Grün/Gelb/Rot ausschließlich für Urteile;
  Blau/Violett/Cyan/Magenta/Schiefer für Kategorien. Ein Test erzwingt beides — dieselbe
  Fehlerklasse hat 0.7.0, 0.8.0 und 0.9.0 je ein Release gekostet.
- **Direktbeschriftung statt Legende.** Eine Legende zwingt den Blick zwischen zwei Orten
  und die Zuordnung ins Gedächtnis.
- **Mehrere Zeitreihen: gestapelt, nicht überlagert** (Javed/McDonnel/Elmqvist) — außer bei
  wenigen, sehr ähnlichen Objekten, wo Superposition gewinnt (Gleicher). Bei verrauschten
  Sekundendaten gewinnt **keins von beidem**: dort aggregieren.
- **Keine zweiten Achsen**, ein Cursor über gestapelte Kleinvielfache.
- **Kein schwebender Ablesekasten** — feste Leiste im Kartenkopf.
- **Eine Leitzahl je Ansicht.** **Quellen eingeklappt**, Wissen neben der Sache.

---

## 7. Fehler und was sie gelehrt haben

| Version | Fehler | Ursache und Lehre |
|---|---|---|
| 0.2.0 | alle Wellness-Sensoren `unavailable` | `_entry()` überschrieb ein Basis-Attribut |
| 0.3.0 | Historien-Import lief nie | „Archiv leer?" wurde geprüft, *nachdem* es befüllt war |
| 0.5.0 | alle Ansichten „Unknown error" | Zonenzeiten in Objektform, `float()` auf ein dict |
| 0.5.0 | ein Ausfall riss alles mit | `Promise.all` statt `allSettled` |
| 0.5.1 | Panel lädt nicht | zweite JS-Datei fehlte beim Kopieren |
| 0.7.0 / 0.8.0 / 0.9.0 | zwei Gelbtöne, zweites Blau, zweites Rot | dreimal dieselbe Klasse → zwei getrennte Farbregister mit Test |
| 0.9.0 | Messpunkte zwischen Lücken unsichtbar | Pfad nur mit `M`, ohne `L` |
| 0.9.1–0.9.3 | Ablesekasten dreimal am falschen Fleck | zweimal die Rechnung repariert, zweimal falsch. Beim dritten Mal die **Fehlerklasse entfernt**: feste Leiste statt positioniertem Kasten |
| 0.9.4 | **Integration startete nicht** | neuer Handler zwischen fremde Dekoratoren gesetzt. 544 grüne Prüfungen halfen nicht, weil keine den **Start** prüfte |
| 0.11.0 | Zustandsbänder widersprachen dem Trainerurteil | zwei Regeln für dieselbe Frage |
| 0.12.0 | `VO2max 4×8` behauptete 75 min, Blöcke ergaben 67 | Dauer und Last im Kalender wären falsch gewesen |
| 0.13.0 | Rundenkurven unlesbar | gemeinsame Skala über alle Zeilen machte jede Kurve zum Strich. **Der Test maß nur ein Ziel und meldete Erfolg** |
| 0.13.0 | Segmentierung zog den ersten Messpunkt der nächsten Runde mit | bei einer Pause vor 259 W ein Sprung mitten in der Erholungskurve |
| 0.14.0 | Steigungsdiagramm unlesbar | Information lag im **Winkel** — dem schlechtesten Kanal |
| 0.16.0 | überlagerte Blockkurven blieben ein Knäuel | theoriegerecht, aber die Daten zu verrauscht. Behoben hat es erst das **Weglassen** |
| 0.19.0 | 2,0 % gegen Median 1,71 % hieß „schlechter als sonst" | Urteil hing am Prozentrang; jetzt am Verlassen der mittleren Hälfte |
| 0.24.0 | bei „Erholung" blieben drei Grundlagenfahrten übrig | **gefiltert statt bewertet** — drei Varianten derselben Sache sind keine Auswahl |
| **0.28.1** | **Prozente statt Watt — trotz dreier Releases, die das Gegenteil behaupteten** | Die FTP steht als `icu_ftp` auf **jeder Aktivität**; gesucht wurde sie in `sport_settings`. `ftp = None` → Rückfall auf Prozente. **Zweimal die Anzeige repariert, nie die Eingabe geprüft.** |
| 0.29.0 | „0 Last in sieben Tagen" bei Ausfahrt und Spaziergang | dasselbe Muster: Last aus `wellness.load` statt aus den Aktivitäten |
| 0.30.0 | Ruhepuls-Warnlinie unsichtbar | sie lag außerhalb der Achse und wurde stillschweigend nicht gezeichnet |
| 0.30.1 | Wochenbalken verrutscht | Flex-Zeile unten ausgerichtet; Tage mit Einheitennamen wurden höher und schoben ihren Balken hoch — **die gemeinsame Grundlinie war dahin** |

### Die drei Fehlerklassen, die sich durchziehen

1. **Falsche Quelle statt falscher Anzeige.** FTP, Tageslast — beide standen in den Daten und
   wurden am falschen Ort gesucht. **Lehre: bei „X erscheint nicht" zuerst prüfen, ob die
   Quelle ankommt.** Das hat einen ganzen Nachmittag gekostet.
2. **Tests, die nur ein Ziel messen.** Die Rundenkurven waren „grün" mit Amplitude 1 px. Ein
   Test muss beide Ziele prüfen — vergleichbar *und* lesbar.
3. **Zwei Rechenwege auf dieselbe Frage.** Zustandsbänder gegen Trainerurteil (0.11.0),
   Empfehlungsblock gegen Einheitenliste (0.27.0). Beide Male: eine Quelle, ein Weg.

---

## 8. Sicherheitsentscheidungen

- **Ein einziger Schreibzugriff.** `POST /athlete/<id>/events` legt ein geplantes Workout an.
  Nur auf einen Klick im Panel, nie auf einem Timer, nie als Nebenwirkung.
- **Schreibzugriffe werden nicht wiederholt.** Ein Timeout nach erfolgreichem POST hätte den
  Termin doppelt angelegt. Nur `429` wird erneut versucht — dort hat die Anfrage den Kalender
  nachweislich nicht erreicht.
- **Kalendereinträge tragen absolute Watt**, keine Prozente: eine Prozentangabe landet nur
  richtig, wenn die FTP in Intervals mit der übereinstimmt, aus der gerechnet wurde.
- **Jeder erzeugte Eintrag trägt seine Herkunft** im Beschreibungstext.
- **Das Zielprofil liegt lokal** im Archiv und geht nicht an intervals.icu.

---

## 9. Prüfstand

**Vierzehn Dateien, rund 1.900 Einzelprüfungen, alle grün.** Kein Test braucht eine laufende
HA-Instanz oder einen Browser.

| Datei | prüft | Umfang |
|---|---|---|
| `test_derive.py` | Parselogik gegen echte Payloads | |
| `test_dfa.py` | DFA-Auswertung, Bandgrenzen, Artefakte | |
| `test_import.py` | vollständiger Import gegen einen Nachbau des Kontos | |
| `test_analytics.py` | Trainingsmetriken gegen bekannte Ergebnisse | |
| `test_setup_simulation.py` | Entity-Aufbau, Übersetzungen, unique_ids | |
| `test_laps.py` | Runden-Normalisierung | 34 |
| `test_coach.py` | Zustandsregeln, Infektverlauf, Nachtreaktion, Einordnung, Bereiche | 141 |
| `test_plan.py` | Zielprofil, Wochenmuster, Zeitbudget | 117 |
| `test_workouts.py` | Einheitenauswahl, Wattumrechnung, Intervals-Syntax | 545 |
| `test_websocket_registration.py` | Registrierung, Dekoratoren, FTP-Quelle | 135 |
| `test_panel_views.js` | alle Ansichten gegen volle, leere, löchrige, entartete Daten | 707 |
| `test_panel_fixes.js` | je ein Nachweis pro behobenem Fehler | 140 |
| `test_panel_design.js` | Gestaltungsregeln als Zusicherung | 49 |

**Das Prinzip:** Ein Test, der den alten Fehler nicht nachweislich findet, ist kein Test. Bei
den kritischen Fixes wurde der Fix zurückgedreht und geprüft, dass der Test fehlschlägt.
Diese Gegenproben haben mehrfach gezeigt, dass ein Test *nicht* scharf war — dann wurde er
geschärft, nicht der Code gelobt.

---

## 10. Offen — ehrlich priorisiert

**Was ich selbst als Lücke sehe:**

1. **Die Belastungs-Ansicht ist seit 0.6.0 unangetastet.** Die Kritik am ACWR ist seither
   härter geworden als das, was dort steht. Größte Lücke zwischen Inhalt und Stand.
2. **Der DFA-Tab** nutzt einen rollierenden Median über Einheiten. Ob das der richtige
   Schätzer ist, wurde nie geprüft.
3. **Die Kalender-Ansicht** stammt aus 0.9.0 und folgt nicht den Regeln, die seither
   entstanden sind (gemeinsame Grundlinie, Farbregister, Direktbeschriftung).
4. **Ein systematischer Durchlauf durch alle Datenquellen.** Zwei Felder wurden am falschen
   Ort gesucht; es gibt vermutlich weitere.

**Funktional offen:**
- Webhooks statt Polling
- Historien-Import in die HA-Langzeitstatistik (`async_import_statistics`)
- Runden-Visualisierung je Runde (nach dem Scheitern von 0.13.0–0.16.0 bewusst zurückgestellt)

**Für die Veröffentlichung:**
- Brand-Icon 256×256 an `home-assistant/brands` (PR) — solange es fehlt, bleibt die
  HACS-Prüfung im CI rot; für die Installation als benutzerdefiniertes Repository ohne Belang
- Repository-Topics setzen
- Aufnahme in den HACS-Standardkatalog beantragen

**Zwei Hinweise persönlich:**
1. **API-Key und GitHub-Token standen im Klartext im Chatverlauf.** Vor Veröffentlichung neu
   erzeugen; der Key in HA über den Reauth-Dialog.
2. **Die tägliche Wellness-Abfrage in Intervals einschalten.** Selbsteingeschätzte Werte sind
   laut Review der empfindlichste Einzelindikator — der größte verfügbare Hebel auf die
   Aussagekraft des ganzen Systems, und der einzige, der die 2-Prozent-Kalibrierung aus
   Abschnitt 5 nach oben bewegen könnte.

---

## 11. Betrieb

**Update:** HACS → *Intervals.icu* → aktualisieren → HA neu starten → Browser **hart** neu
laden. Der Service Worker des HA-Frontends bedient Module aus eigenem Speicher, an Strg+F5
vorbei: F12 offen lassen, Rechtsklick auf Reload → „Cache leeren und vollständig
aktualisieren". Gegenprobe im Inkognito-Fenster.

**Cache:** `PANEL_VERSION` in `const.py` hängt an der Modul-URL. Wer das Panel ändert, ohne
die Zahl zu erhöhen, sieht weiter die alte Fassung.

**Rückzieher:** In HACS lässt sich jede frühere Version wählen.

**Diagnose:** Sensor „Archiv" · Log `custom_components.intervals_icu` · Browser-Konsole (F12)

**Datenhaltung:** Archiv in `.storage/intervals_icu.<athlet>`, API-Key und Zielprofil im
Config-Entry bzw. Archiv. Beides überlebt ein Update.
