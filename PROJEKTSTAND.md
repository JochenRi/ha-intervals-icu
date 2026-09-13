# ha-intervals-icu — Projektstand

**Stand:** 13.09.2026 · **Version:** 0.40.0 · **Status:** produktiv auf HEIMDALL,
Auslieferung über HACS aus `github.com/JochenRi/ha-intervals-icu`

Eine eigene Home-Assistant-Integration, die Trainingsdaten von Intervals.icu lokal
archiviert, auswertet und in einem eigenen Seitenleisten-Panel darstellt.

**Umfang:** ~10.870 Zeilen, davon ~4.020 Frontend · 24 WebSocket-Befehle · 15 Einheiten in
8 Familien · 15 Testdateien mit **3.421** gezählten Einzelprüfungen · 41 Releases.

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
    └── intervals-panel.js   Panel, eine Datei ohne Abhängigkeiten (3.137 Zeilen)
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
| Durability | Maunder: Zeitpunkt und Ausmaß der Verschlechterung während langer Belastung; über angesammelte Arbeit indiziert | eigene Eigenschaft, unabhängig von FTP und VO2max; **am eigenen Bestand ist die Steigung über der Arbeit nicht von null zu unterscheiden** — die Kachel sagt das, statt eine Leitzahl zu erfinden |
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

**0.40.0 — was der Bau von Paket G zutage gefördert hat:**

1. **Die Kachel behauptete etwas über 53 Fahrten, über die sie nichts wusste.**
   `steady_endurance_reason()` gab „variable" zurück, wenn der Variabilitätsindex
   *zu hoch* war — und ebenso, wenn er **gar nicht berechenbar** war, weil die
   Fahrt keine Leistungsmessung trägt. Beides landete in einem Zähler, und der
   Rechenweg druckte „64 zu wellige". Tatsächlich wellig waren **11**; die
   anderen 53 sind unbekannt, nicht wellig. Ein Bugfix, kein Feature: getrennte
   Gründe, getrennte Zahlen, eigener Test und eigene Gegenprobe.
   **Die Lehre:** ein Zähler, der zwei Gründe zusammenfasst, erfindet den
   häufigeren. Wer „nicht messbar" unter „gemessen und schlecht" verbucht,
   schreibt eine Messung hin, die nie stattgefunden hat.

2. **Die erwartete Wirkung eines Umbaus war um Faktor fünf daneben** (45 → ~110
   erwartet, 45 → 56 gemessen) — und zwar aus demselben Grund wie Punkt 1: die
   Spezifikation hatte den falsch beschrifteten Zähler geglaubt. Eine Erwartung
   aus einer Zahl, die man nicht selbst nachgerechnet hat, ist eine Vermutung.

3. **Die Umrechnung Arbeit → Zeit hätte mit einer Leistung aus dem Vorjahr
   gerechnet.** „Median der qualifizierten Einheiten" klingt richtig und ist es
   nicht, wenn der Pool elf Monate Progression umfasst: 86 W über den ganzen
   Bestand gegen 136 W in den letzten 90 Tagen, aus demselben Kipppunkt 6 h 45
   gegen 4 h 15. **Die Lehre:** ein Median über einen Zeitraum, in dem sich die
   Größe verändert hat, ist kein Wert, sondern ein Durchschnitt aus zwei
   Athleten.

4. **Der Blockverlauf wäre eine Hintertür um die Ehrlichkeitsregeln gewesen.**
   Die Spec verlangte für die Blöcke nur „ausreichende Belegung". Am Livebestand
   liefert ein Block aus **vier** Fahrten |t| = 3,30 und einen Kipppunkt von
   640 kJ — die Steigungsregel allein hätte ihn durchgewinkt. Alle drei Regeln
   gelten jetzt je Block, und „der Bestand" ist dort der Block.

5. **Methodisch, und das Wichtigste an dieser Session:** die Spezifikation wurde
   **an den Livedaten widerlegt, bevor eine Zeile gebaut wurde.** G2 verlangte
   eine Leitzahl aus der Steigung der Trendgeraden — die Steigung besteht das
   eigene Zwei-Standardfehler-Kriterium nicht (|t| = 1,33), und der Schnittpunkt
   läge jenseits des Bestands. Geprüft auf **drei** Wegen statt einem, weil ein
   Kriterium auch nur ein Kriterium ist: gewichtete Kleinste-Quadrate,
   Kendall-Tau (z = 1,57) und Bootstrap ([−1,65; +6,55]) — alle drei sagen
   dasselbe. Gebaut wurde daraufhin die Kachel, die **das** sagt: „Die Richtung
   stimmt, aber die Streuung ist zu groß für eine Aussage", mit der Angabe, was
   fehlen würde (rund 128 statt 56 Einheiten; lange Fahrten zählen stärker, weil
   der Fehler an der Spannweite der Arbeit hängt). Eine Zahl, die nur dasteht,
   weil eine Kachel eine Zahl haben soll, ist schlimmer als keine.

**0.39.0 — was der Bau von C/D6/F zutage gefördert hat:**

1. **Der Abgleich meldete Gleichstand, die gelöschte Einheit stand weiter im
   Kalender.** Die Meldung war wörtlich richtig: `reconcile.plan()` vergleicht
   das **Archiv**, geplante Einheiten liegen auf dem events-Endpunkt und kommen
   dort nie hin. Drei Schichten, nicht eine — der Abgleich sah sie nicht, der
   Knopf stieß keinen Refresh an, und das Panel hielt `_cal`/`_days` für die
   ganze Browser-Sitzung. Behoben als D6a/D6b/D6c.

2. **`durability()` behauptete etwas über lange Einheiten ohne eine einzige
   lange Einheit.** Bei leerer Gruppe fiel `verdict` auf die andere zurück und
   meldete „die aerobe Basis trägt auch lange Einheiten". Ein echter Fehler,
   kein Spezifikationspunkt. Es entsteht jetzt **keine** Leitzahl aus einer
   leeren oder dünnen Gruppe, sondern der Satz, was fehlt.

3. **`DECOUPLING_GOOD` stand zweimal im Backend und fünfmal im Frontend.** Paket
   F verbot ausdrücklich die Konstante im Frontend — und hätte, nur so
   angewandt, den eigenen Satz verletzt. Jetzt einmal in `const.py`, Wächter
   über das ganze Frontend, die restlichen vier Dubletten gezählt und
   eingefroren.

4. **`analytics.decoupling_series` versprach „steady endurance session" und
   filterte nur nach Dauer.** Kachel und Diagramm daneben konnten Entkopplung
   aus zwei verschiedenen Grundgesamtheiten zeigen. Ein Prädikat für beide:
   `derive.steady_endurance_reason()`.

5. **Der 90-Minuten-Schnitt versteckte das Signal.** −0,1 pp gegen +1,5 pp beim
   Arbeits-Schnitt am selben Bestand. Die Spezifikation hatte die Achse nie
   geprüft; die Literatur misst Durability über angesammelte Arbeit.

**0.38.0 — drei Funde beim Bau von Paket D (Abgleich):**

| Fund | Klasse | Fix |
|---|---|---|
| **Zwei der drei Aufräumstellen tragen gar kein Datum.** `unavailable` ist eine nackte ID-Liste, und eine DFA-Zusammenfassung, deren Aktivität schon fort ist, hat nichts mehr, woran sie zu datieren wäre. Sperre 2 („nur innerhalb des Fensters") ist dort **nicht beweisbar** — sie hätte stillschweigend gegolten, weil Paket D ohnehin immer die ganze Historie abruft. | Die Zusicherung gilt nur, wo sie prüfbar ist | `reconcile.covers_history()` entscheidet aus dem Bestand, ob das Fenster nachweislich alles umfasst; nur dann werden die beiden datumslosen Stellen angefasst. Ein einziges unlesbares Datum im Archiv genügt, um den Vollabgleich zu verweigern. |
| **Die Gegenprobe zur Fenstersperre biss nicht.** Die Mutation („datumslose Stellen auch ohne Vollabgleich aufräumen") lief grün durch: in der Fixture waren Platzhalter und DFA-Waise auf der Intervals-Seite **vorhanden**, fehlten also nie — das Stehenbleiben bewies nichts. | Paket A, Muster 2: eine vorgeschriebene Prüfung ist erst eine Prüfung, wenn die Fixture die Fälle unterscheidbar macht | Teilfenster und Vollfenster laufen jetzt über **denselben** Bestand mit **denselben** Lücken und müssen zu verschiedenen Ergebnissen kommen. Danach schlug die Mutation an: vier gezählte, benannte Fehler. |
| **Zwischen Anzeige und Klick liegt ein zweiter Abruf.** D4 sah Bestätigung vor, aber nicht, dass der Vollzug einen frischen Befund erhebt — er hätte etwas anderes entfernen können als das, was im Dialog stand. | Bestätigt wird eine Anzeige, ausgeführt wird ein Befund | Der Vollzug schickt die angezeigten IDs mit; das Backend führt nur die Schnittmenge mit dem neuen Befund aus und meldet sonst `stale`, ohne etwas anzufassen. |

**Nebenbefund:** §9 führte `test_websocket_registration.py` mit 172 statt 174 —
die Tabelle summierte 2.973, der Kopf 2.975. Dieselbe Klasse wie der
Zählfehler aus 0.35.0, eine Zeile weiter; beim Nachziehen korrigiert.

**0.37.0 — Fund beim Lesen für Paket B, VOR der Gewichtung behoben:**

| Fund | Klasse | Fix |
|---|---|---|
| **`state()` rechnete die HRV-Basislinie roh, `state_series()` im Log.** 0.34.0 hatte die Triggerregeln angeglichen, die z-Berechnung nicht — Trainerurteil und Verlaufsband konnten am selben Tag verschieden ausfallen (Fixture: heute −2,6 SD im Log, aber nur −1,5 SD roh: das Band sagte Einbruch, der Trainer nicht). Dazu rechneten `_night_z` und `_signal_bands` dieselbe Basislinie ein drittes und viertes Mal von Hand. | Fehlerklasse 3 (zwei Rechenwege), fünfter Fall — diesmal vierfach | EINE Primitive `_norm_band`/`_z_at`, alle vier Orte rufen sie; AST-Wächter prüft die Aufrufer (Block 29). `week_z` ist jetzt das Mittel der ln-Werte gegen das Log-Band (die publizierte Vergleichsgröße, §5). Die Mindestbelegung 20 gilt damit auch im Trainerurteil, vorher nur in den Bändern. **Das Live-Urteil kann sich durch die Log-Skala ändern** — bewusst als eigener Commit VOR der Gewichtung, damit der No-op-Beweis von Paket B nicht die Gleichheit eines Fehlers einfriert. |

**0.37.0 — Fund beim Bau der Gewichtung (Paket B3):**

| Fund | Klasse | Entscheidung |
|---|---|---|
| **`analytics.hrv_status` rechnet eine fünfte HRV-Basislinie von Hand** (eigene `_baseline` über rollende 7-Tage-ln-Mittel) und speist die Readiness-Ampel. Mit gewichteter Trainer-Basislinie können Ampel und Trainerurteil bei etikettierten Fenstern auseinanderlaufen. Eine Tages-Gewichtung NUR der Ampel-Basislinie wäre halbrichtig: die rollenden 7-Tage-Mittel selbst blieben kontaminiert. | Fehlerklasse 3, sechster Fall — diesmal bewusst NICHT vereinheitlicht | analytics bleibt komplett kontextfrei (Ebene 3, Quelltext- UND Verhaltens-Wächter in test_analytics); die Websocket-Schicht hängt der Ampel eine Herkunftsnotiz an, wenn etikettierte Tage im Fenster liegen. Die saubere Lösung heißt B4 (Basislinie je Bedingung), nicht eine zweite Gewichtungsmechanik in analytics. |

**0.35.0 — zwei Funde beim Aufräumen, beide aus bekannten Klassen:**

| Fund | Klasse | Fix |
|---|---|---|
| **`test_plan.py` hatte zwei Summary-Abschnitte** — dieselbe Falle wie `test_workouts.py` in 0.34.0. Hinter der Zusammenfassung lief der **Stundenvertrag** mit, also genau die Prüfung, die nach dem 0.31.0-Budgetfehler geschrieben wurde: 193 Prüfungen, weder gezählt noch meldefähig. Gegenprobe: fünf echte Fehler eingebaut → die Datei druckte „188 Prüfungen, 0 Fehler" und endete mit 1. | Prüfstand meldet nicht, was er prüft | Summary ans Dateiende (188 → 405 gezählt). Und die **Fehlerklasse entfernt** statt nur den Fall: neuer Wächter `test_suite_hygiene.py` — eine Summary je Datei, keine gezählte Prüfung dahinter, Fehlerliste wird gedruckt, Exit-Code trägt das Urteil |
| **Ein Zielprofil aus der Zeit vor 0.33.0 bekam nie einen Kalenderanker.** Das Archiv füllt Schlüssel späterer Versionen nur auf der **obersten Ebene** auf; das verschachtelte `goal` behielt seine alte Form ohne `plan_start`. Der Plan fiel auf „Montag dieser Woche" zurück — stabil innerhalb der Woche, wandernd ab Montag. Simulation über 90 Tage: **14 verschiedene Anker, die Entlastungswoche 14-mal verschoben.** Geheilt hätte das nur ein zufälliges Neuspeichern des Ziels. | Migration fehlt (Verwandter von Fehlerklasse 1: der Wert steht nicht da, wo gesucht wird) | `plan.migrate_goal()` repariert den Datensatz beim Laden des Archivs und speichert einmal; ohne Ziel wird **kein** Anker erfunden. Die Montagsregel liegt jetzt einmal in `plan.anchor_stamp()`, `set_goal` rechnet sie nicht mehr selbst — Quelltext-Wächter gegen die Rückkehr beider Kopien. Nach der Migration: **ein** Anker über 90 Tage, Entlastungswochen auf festen Daten (28.09., 26.10., 23.11., 21.12.) |

**Die Lehre aus den Gegenproben dieser Runde:** zwei der vier Mutationen ließen
den Test *abstürzen* statt melden — `TypeError` auf `None`, `ValueError` bei
einem fehlenden Substring. Ein Absturz überspringt jede folgende Prüfung der
Datei und erzeugt genau die Lage, die oben repariert wurde: Exit-Code 1, aber
„0 Fehler" gedruckt. **Eine Gegenprobe gilt erst als bestanden, wenn der Fehler
gezählt und benannt erscheint** — nicht, wenn er irgendwie auffällt. Beide
Tests wurden entsprechend gehärtet (`.get()` statt `[...]`, Existenzprüfung vor
`index()`).

**0.34.0 — Paket 3, Zustandsmaschine + Quellen (`coach.py`, `workouts.py`), plus zwei Prüfstand-Lehren:**

| Fund | Klasse | Fix |
|---|---|---|
| Slump-Trigger: EIN Signal an EINEM Tag (OR ab 2 SD) löste aus — der eigene Tension-Text nennt einen Einzeltag Rauschen. | Code widerspricht dem eigenen Text | Auslösung nur bei HRV **und** Ruhepuls am selben Tag (Infektmuster) oder EINEM Signal an zwei Folgetagen; identisch in `state()` und `state_series()`. Ursache (`cause`) und Infektverdacht (`infection_suspected`) wandern in die Payload; bei Infektverdacht symptomgeleitete Leiter (Halsregel, **als Konvention gekennzeichnet**) in Warnung und Einheiten-Urteilen |
| Anker-Block rechnete **zwei verschiedene „jetzt"-Werte**: Leitwert = Median der letzten 5, Trend-„now" = Mittel der neueren Hälfte — das Panel zeigte beide nebeneinander. | berechnet doppelt, zeigt Widerspruch | Ein „jetzt" im ganzen Block (Median letzte 5); die Hälften liefern nur noch das „vorher" |
| `endurance` bei Pause ≥ 7 Tagen ausgeblendet — direkt unter dem Docstring „never filtered away". | Filter trotz eigener Filter-Warnung | Grundlage bleibt sichtbar, Urteil „maybe" mit Begründung (Wiedereinstieg als besserer erster Schritt); Limit 7→8, sonst fiel `return_45` durchs Raster |
| VO2max-HF-Fenster extrapolierte die aerobe Schwelle über das gemessene Maximum hinaus (bis 1,18×). | Fantasiewerte | Klemme an `max_hr` aus `sport_settings`; Fenster entfällt, wenn schon die Untergrenze an der Decke liegt |
| DFA-Quellzeile „gegen Gasaustausch validiert" — die Validierungslage 2024–2026 sagt: VT1 schwach (weite Übereinstimmungsgrenzen, fitnessabhängiger Bias), VT2 robuster. | Quelle freundlicher als die Lage | Beide Panel-Quellzeilen und die Anker-Quelle tragen jetzt den Vorbehalt: als Trend brauchbar, als alleinige Verankerung nicht |
| Stunden erschienen mit Punkt („8.7 h") in allen Python-Texten; `rebound`/`elevated` trugen Blau/Violett (Kategorienfarben) als Urteil; goalbar-Ternary warf seinen Text weg. | Register- und Formatverstöße | `_h()`-Helfer mit Komma (Wächter: genau EIN `:.1f` bleibt, im Helfer); Zustandsfarben ins Urteilsregister, Wort+Icon tragen die Unterscheidung; Grundsatz-Text statisch |

**Zwei Prüfstand-Lehren aus den Gegenproben:** (1) `test_workouts.py` hatte **zwei
Summary-Abschnitte** — neue Blöcke hinter dem ersten liefen mit, wurden aber weder
gezählt noch gemeldet, nur der Exit-Code wusste Bescheid; erst die Konsolidierung
machte einen echten, maskierten Fund sichtbar. (2) Ein Quelltext-Wächter, dessen
Suchmuster das tatsächliche Format nicht matcht, ist zahnlos — **eine Gegenprobe
muss die Mutation UND das Feuern verifizieren**, sonst prüft sie nur sich selbst.

**0.33.0 — Paket 2, der Plan-Umbau (`plan.py`), plus ein Fund beim Hinsehen:**

| Fund | Klasse | Fix |
|---|---|---|
| `hard_per_week` lieferte bei 4 Fahrtagen 2 harte Einheiten (50 % der Einheiten hart) — `hard_note` und Formular predigten das Gegenteil. | Code widerspricht dem eigenen Text | Regel: ≤ 4 Tage → 1 hart, 5–6 → 2, 7 → 3; Formular und Note angeglichen; zweite Qualitätseinheit variiert (long_ride: SweetSpot + Tempo statt 2× SweetSpot) |
| `LONG_DAY_SHARE = 0.6` als Wochenregel verbot mathematisch jede Fahrt über 60 % des Wochenbudgets → 8 identische „3,3 h gedeckelt"-Wochen, Ziel-Default `longest × 1.6 = 9 h` mit „brauchst 15 Wochenstunden"-Note. | Regel modelliert die Praxis falsch | Langstrecken-Rhythmus: einzelner **großer Tag** je Zyklus (letzte Belastungswoche vor der Entlastung, alle 3–4 Wochen), wächst ~12 %/Schritt (als Konvention gekennzeichnet), Deckel nur am Ziel. Die Woche des großen Tages ist offen eine größere Woche (`big_day`-Flag). Ziel-Default = 6 h (das Ziel selbst), Budget-Note erklärt die Ausnahme statt Stunden zu fordern |
| Der Plan startete bei jedem Öffnen „ab heute" — die Entlastungswoche war immer „Woche 4 ab jetzt" und kam nie. | Zustand ohne Anker | `plan_start` (Montag) wird bei `set_goal` im Archiv persistiert, Wochen sind an Kalenderwochen gebunden; Kalender-Anker-Vertrag in `test_plan` (Entlastungswoche erreicht ein festes Datum, aus vier Blickdaten geprüft) |
| `rGoal` baute `weeks` und `budget_note` in Konstanten — und setzte beides nie ins Template ein. Die Planwochen waren im Panel **unsichtbar**. | „berechnet, aber nie verbaut" — zweiter Frontend-Fall nach 0.32.0 | Eigene Sektion `rPlanWeeks` unten im Trainer-Tab (die Tagesfrage bleibt oben, wie der Views-Test es erzwingt); Quelltext-Wächter in `test_panel_fixes` Block 16 |

Dazu Rest von Trainer-Befund 10: bei `trained_today` sagen Leitkarte, Kartenliste und
Kalenderknopf jetzt explizit „für morgen" (Block 15) — vorher stand der Hinweis über
Karten, die zwei Zeilen tiefer „HEUTE EMPFOHLEN" behaupteten.

**0.36.1 — der Graph floh vor dem Zeiger:**

| Fund | Klasse | Fix |
|---|---|---|
| **Zeiger über den DFA-Graphen → die Seite sprang zur Tabelle, der Graph war weg.** `scrollIntoView` zog die markierte Zeile ins Bild — nur ist `:host` selbst der Scroll-Kasten und die Tabelle steht unter den Graphen, also bewegte jede Zeigerbewegung die ganze Seite. Die Ansicht floh vor dem Zeiger, der sie gerade las. Steht so in `docs/ausbau.md` A1 und war trotzdem falsch: **der Code entscheidet, nicht das Papier.** | Muster aus der Spec ungeprüft übernommen | Ersatzlos entfernt. Eine flüchtige Markierung darf die Seite, auf der sie gezeichnet wird, niemals bewegen — die Zeile trägt weiter ihren Innenbalken, die feste Auswahl nennt die Einheit über den Graphen. Spec korrigiert |
| **Die erste Sperre dagegen schlug auf dem reparierten Stand an** — mein eigener Erklärkommentar enthielt das gesperrte Wort. | Test prüft den Text, nicht die Sache | Begründung über die Methode gezogen, Rumpf frei von den gesperrten Begriffen |
| **Und die Layout-Prüfung war leer:** `\.trow\.hovered\{([^}]*)\}` bricht an der `}` in `${C.bg2}` ab, lief also auf `background:${C.bg2` — die verbotenen Eigenschaften konnten darin gar nicht vorkommen. | Fehlerklasse 2 (Test kann nicht fehlschlagen) | Bis Zeilenende statt bis zur ersten Klammer, plus eine Prüfung, die zuerst verlangt, dass die Regel überhaupt vollständig gelesen wurde |

**Statt einer Quelltextsperre eine Simulation.** Ein `grep` fängt genau einen
Mechanismus; eine Seite kann sich aus mehreren Gründen unter dem Zeiger bewegen.
Block 19 fährt daher den echten `pointermove`-Pfad über einem aufgezeichneten
DOM — zwei volle Überstreichungen des Graphen, dann über die Liste, dann das
Verlassen — und schließt jede Ursache einzeln aus: etwas ins Bild ziehen
(`scrollIntoView`, `focus`, `scrollTo`), den View neu aufbauen (setzt die
Scroll-Position zurück) und ein Layout-Sprung durch die Markierung selbst.
Sechs Kausalpfade einzeln zurückgedreht, sechs gefangen, keiner abgestürzt.

**0.36.0 — Paket A (DFA-Reiter und Signalkarten), und drei stumpfe Tests:**

| Fund | Klasse | Fix |
|---|---|---|
| **Der Prüfstand zählte fünf Dateien nicht mit.** `test_analytics`, `test_derive`, `test_dfa`, `test_import`, `test_setup_simulation` liefen 187 Prüfungen, druckten aber keine Summary — und `test_suite_hygiene` ließ das durch, weil `len(summaries) <= 1` auch **null** erlaubt und die Reihenfolge-Regel bei null Summaries gar nicht greift. Die Kennzahl „2.354 gezählte Prüfungen" deckte real 9 von 14 Dateien ab. | Prüfstand meldet nicht, was er prüft (dritter Fall) | Zähler und Summary in allen fünf Dateien. Regel auf `== 1` verschärft **und** die Spiegellücke geschlossen: eine Summary, die nichts zählt, ist auch eine Lüge (`len(counted) > 0`) |
| **„Fünfzehn Testdateien" seit mindestens 0.33.0** — real waren es 13, dann 14. Die Tabelle in §9 listete die ganze Zeit die richtige Zahl, der Fließtext darüber nicht. `git log --diff-filter=D -- tests/` belegt: keine Datei verloren, reiner Erbfehler beim Hochzählen. | Doku | Zahl aus der Tabelle abgeleitet statt fortgeschrieben |
| **Falle 3 war nicht prüfbar.** Die Prüfung „Y-Achse skaliert nicht je Fenster" lief gegen eine Fixture, deren Schwellen zwischen 150 und 171 kreisen — jedes Fenster hat dieselbe Spannweite, eine fensterweise skalierte Achse sähe identisch aus. Die Mutation schlug **gar nicht** an. | Fehlerklasse 2 (Test misst nur ein Ziel) | Eigene, trendende Reihe (130→185 bpm) für diese Prüfung; zusätzlich der tiefste tatsächlich gezeichnete Tick statt eines Labels, das `tickVals` nie erzeugt |
| **Falle 1 war nicht prüfbar.** Verglichen wurden nur relative Fenster — die enden alle *jetzt*, also sind ihre letzten fünf belastbaren Messungen dieselben fünf. Eine fensterabhängige Leitzahl wäre unentdeckt geblieben. | Fehlerklasse 2 | Ein **eingefrorener** Zeitraum, der in der Vergangenheit endet, kam in den Vergleich. Die Mutation liefert jetzt `156 … 156 \| 163` |
| **Der Ring deckte sich selbst.** Die Prüfung „Auswahl trägt eine Form" fragte nur, *ob* ein `pickring` existiert. Der Ring im Leistungsfeld deckte den fehlenden im HF-Feld, die Mutation schlüpfte durch. | Fehlerklasse 2 | Existenzprüfung durch **Zählung** ersetzt (`rings === 2`) |
| **Und eine Gegenprobe, die abstürzte statt zu melden** — der neue `history_days`-Test griff mit `len(hdays)` auf `None` zu, als die Mutation den Schlüssel entfernte. Genau die Bauart, die in 0.35.0 am teuersten war. | Prüfstand meldet nicht, was er prüft | `.get()`, Existenzprüfung, Zugriff nur auf eine Liste, die es gibt. Bei jeder der 13 Mutationen bleibt die Zählung konstant — nichts wird übersprungen |

**Und die Befunde aus dem Lesen, bevor gebaut wurde:**

| Befund | warum es nicht „nur Frontend" blieb |
|---|---|
| `today.history[key]` war eine **reine Werteliste** über `days[-42:]` — ohne Datum. Die 42 Einträge sind die *vorhandenen* Wellness-Tage, nicht 42 zusammenhängende Kalendertage; eine Achse nach „heute minus n" wäre ab der ersten Lücke durchgehend verschoben. | Neuer Schlüssel `history_days` (`date`, `load`, `state`) in `coach.py`. Die Tageslast läuft über **eine** lokale Funktion, die auch die 7-Tage-Leiste speist — kein zweiter Rechenweg. Der Test stanzt ein Loch ins Archiv und verlangt, dass die Datumsliste darüber springt |
| Die neuen Spalten (Dauer, Last, Ø HF, Entkopplung) hätte das Frontend gegen `_acts` joinen müssen — das reicht 300 Einheiten weit und hätte ältere Zeilen **still leer** gelassen. | `threshold_series()` liefert die Felder mit der Messung; `since` am WS-Befehl vorgesehen, damit das bei 500 Auswertungen kein Umbau wird — **ohne** Obergrenze, sonst verschwände ein zukunftsdatierter Wert wortlos |
| Ein per `${false ?}` stillgelegter zweiter Chart in der aufgeklappten Signalkarte. | entfernt; Quelltext-Sperre dagegen in `test_panel_fixes` Block 18 |
| Die Threshold-Fixture erzeugte Daten bis einen Monat **in die Zukunft**. | rückwärts von `TODAY` erzeugt |
| Der Zeitbezug der Fenster hing an der Wanduhr — die Suite wäre in einigen Monaten von selbst rot geworden. | Ein `_now()` fürs ganze Panel, in den Tests gepinnt |
| `localStorage` war nirgends in Benutzung, und das Harness stellt keins bereit. | Dreifach gekapselt: `typeof`-Prüfung, Falsy-Prüfung, `try/catch` — Safaris privater Modus wirft beim **Schreiben** |

**0.32.0 — vier Funde aus dem Trainer-Audit, drei davon bekannte Fehlerklassen:**

| Fund | Klasse | Fix |
|---|---|---|
| `rTrainer` baute Warnungen (u. a. den Infekt-Hinweis), Gründe und eine 7-Tage-Leiter — und setzte nichts davon ins Template ein. Die verwaisten CSS-Klassen verrieten den verlorenen Block aus dem 0.9-Neubau. | „berechnet, aber nie verbaut" — Frontend-Variante von 0.9.4 | Warnungen + Gründe werden gerendert; tote Blöcke und CSS entfernt; `test_panel_fixes` Block 11 prüft gerendert **und** auf Quelltextebene („const X ohne ${X}") |
| Zweiter Empfehler: `coach.recommend()` wählte Einheiten parallel zu `workouts.suggest()` — live widersprachen sich beide (Leitempfehlung „Tempo" vs. Familie „maybe"), dazu eine dritte Lastschätzung. | Fehlerklasse 3 (zwei Rechenwege), vierter Fall | `coach.py` liefert nur noch die Bewertung (`assessment`): Zustand, Anker, Gründe, Warnungen. Einheitenwahl **nur** in `workouts.suggest`. AST-Wächter in `test_websocket_registration` |
| `_state_for_plan` las die Wochenlast aus `wellness.load` → `weekly_load: 0` bei 239 Aktivitäten im Archiv. | Fehlerklasse 1 (richtige Zahl, falscher Ort), dritter Fall | Summe `icu_training_load` der letzten 28 Tage; Wächter gegen `row.get("load")` |
| Entlastungswoche: 4,5 h Einheiten in 3,6 h Budget (1,0-h-Floor + nachträgliche Kürzung des langen Tags). | Arithmetik | Kürzen **vor** dem Verteilen, kein Floor — zu kleine Slots entfallen statt aufgefüllt zu werden. Stundenvertrag in `test_plan`: Summe ≤ Wochenbudget, für jede Woche jedes Plans |

**Neu in 0.32.0 — der Anker-Konfliktwächter:** Watt kommen aus der FTP, Puls aus der
DFA-Schwelle — zwei Anschläge, die nichts aufs selbe Maß zwingt. Liegt die gemessene
Schwellenleistung im oder unter dem Grundlagen-Wattfenster (bei Johannes: 146 W bei
FTP 215 → 68 %), zeigt das Panel den Widerspruch offen an, statt beide Zahlen
kommentarlos nebeneinander zu drucken (`workouts.anchor_conflict`, Banner in
`rWorkouts`). Hintergrund aus der Validierungslage 2024–2026: DFA-a1 unterschätzt
Schwellen bei fitteren Athleten systematisch, die Übereinstimmung von HRVT1 mit
VT1/LT1 ist schwach — als Trend brauchbar, als alleinige Watt-Verankerung nicht.
Dazu: Lead-Karte muss ins Lastbudget passen; „heute schon gefahren" wird erkannt
(`trained_today`) und über den Karten ausgewiesen; Evidence-Block nennt jetzt auch
den Non-Responder-Befund (Manresa-Rocamora 2021).


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

**Fünfzehn Dateien, 3.421 gezählte Einzelprüfungen, alle grün.** Kein Test braucht eine laufende
HA-Instanz oder einen Browser.

| Datei | prüft | Umfang |
|---|---|---|
| `test_derive.py` | Parselogik gegen echte Payloads | 29 |
| `test_dfa.py` | DFA-Auswertung, Bandgrenzen, Artefakte | 25 |
| `test_import.py` | vollständiger Import gegen einen Nachbau des Kontos, Schwellenreihe und `since`, day_context-Migration und Schreibweg, Quellenblock-Auflagen | 76 |
| `test_analytics.py` | Trainingsmetriken gegen bekannte Ergebnisse, Ebene-3-Wächter (Last kennt keine Etiketten, Quelltext und Verhalten) | 90 |
| `test_setup_simulation.py` | Entity-Aufbau, Übersetzungen, unique_ids | 22 |
| `test_laps.py` | Runden-Normalisierung | 34 |
| `test_coach.py` | Zustandsregeln, Trigger-Schärfung, Infektverlauf, Nachtreaktion, Einordnung, Bereiche, benannter 42-Tage-Verlauf, Basislinien-Primitive mit AST-Wächter, eingefrorene No-op-Referenz, gewichtete Basislinie mit Fixture-Beweis, **Durability: die drei Ehrlichkeitsregeln einzeln, Gewichtungs- und Umrechnungs-Gegenprobe, Blockverlauf** | 333 |
| `test_plan.py` | Zielprofil, Wochenmuster, Zeitbudget, Progressions- und Kalender-Anker-Vertrag, Profil-Migration | 405 |
| `test_workouts.py` | Einheitenauswahl, HF-Klemme, Infektleiter, Wattumrechnung, Intervals-Syntax | 575 |
| `test_websocket_registration.py` | Registrierung, Dekoratoren, FTP-Quelle, eine Ankerregel, day_context-Lese/Schreibweg, Ampel-Herkunftsnotiz | 180 |
| `test_reconcile.py` | Abgleich mit Intervals: die drei Sperren einzeln, die datumslosen Aufräumstellen, No-op ohne Speichervorgang, der Handler am echten Aufruf (Import läuft, Historie nie geholt, Zwischenstand) | 129 |
| `test_suite_hygiene.py` | der Prüfstand prüft sich selbst: **genau eine** Summary je Datei, die etwas zählt, nichts Gezähltes dahinter, Fehler werden gedruckt | 66 |
| `test_panel_views.js` | alle Ansichten gegen volle, leere, löchrige, entartete Daten; Zeitfenster, Brushing, Achsenregel; Tagesbeschriftung und Abgleich-Dialog mit Schreibweg und Scroll-Erhalt; **die Durability-Wolke: Gewicht als Größe und Deckkraft, Gerade nur bei gesicherter Steigung, Register getrennt** | 1014 |
| `test_panel_fixes.js` | je ein Nachweis pro behobenem Fehler, plus die Zeiger-Simulation; Quelltext-Wächter über das ganze Frontend, beidseitig (keine Zahl im Quelltext, jede Schwelle nachweislich aus der Payload) | 256 |
| `test_panel_design.js` | Gestaltungsregeln als Zusicherung, Auswahl als Form, Achse im Aufklappen, Etiketten im Kategorienregister; **eingefrorene `chart()`-Referenz aus dem Stand vor dem Eingriff** und der Zeiger-Unverändert-Beweis über vier Ansichten | 187 |

**Das Prinzip:** Ein Test, der den alten Fehler nicht nachweislich findet, ist kein Test. Bei
den kritischen Fixes wurde der Fix zurückgedreht und geprüft, dass der Test fehlschlägt —
und zwar **gezählt und benannt**: ein Test, der bei der Mutation abstürzt, überspringt alles
Folgende und meldet am Ende „0 Fehler".
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

### Auslieferungsweg (verbindlich, gilt für jede Version)

Arbeitsteilung: **Claude baut, testet, committet, pusht und legt das Release an —
Johannes aktualisiert über HACS und startet HA neu.** Claude fasst HA nie direkt an;
HEIMDALL-Schreibtools (z. B. `ha_manage_hacs update_information`) nur nach einzelner
Freigabe.

1. Repo klonen: `git clone --depth 1 https://github.com/JochenRi/ha-intervals-icu`
2. Ändern, **komplette Testsuite grün** (Python + Node, siehe §9), End-to-End-Simulation
   mit realistischen Daten
3. Version heben: `manifest.json` **und** `const.py PANEL_VERSION` (beide!)
4. PROJEKTSTAND.md nachziehen (Fehlerkapitel + Kopf)
5. Commit (user `JochenRi` / `JochenRi@users.noreply.github.com`), Tag `vX.Y.Z`,
   Push von `main` **und** Tag
6. **GitHub-Release zum Tag anlegen** (`POST /repos/.../releases`) — HACS liest
   ausschließlich Releases (`version_or_commit: "version"`); ein nackter Tag ist für
   HACS unsichtbar, egal wie oft man refresht. Das war der 0.32.0-Stolperer.
7. `ha_manage_hacs(action="update_information", ...)` nach Freigabe — sonst sieht
   HACS das Release erst nach ~48 h und ein Update installiert die alte Version neu
8. Johannes: HACS-Update + **HA-Neustart** (ohne Neustart laufen die alten Module)
9. Claude verifiziert am lebenden System: `intervals_icu/status` (Archivzähler),
   Payload-Form der geänderten Kommandos — dabei **Erfolgs-Felder prüfen, nie
   Key-Abwesenheit** (ein 502 während des Neustarts liefert leere Antworten, und ein
   leeres Dict besteht jeden Abwesenheits-Check)

**Token:** Johannes stellt den GitHub-Token je Session als Datei bereit
(`GIT_Intervals.txt`, eine Zeile). Der Token bleibt in Shell-Variablen, wird nie in
den Chat gedruckt; Ausgaben werden geschwärzt (`sed 's/gh[pousr]_.../[TOKEN]/'`).
GitHub-REST von der Sandbox aus ist unauthentifiziert oft rate-limitiert (geteilte
IP) — Refs verlässlich über `git ls-remote origin` prüfen, Repo-Details über
`ha_get_hacs_info(action="info")` (nutzt den HACS-eigenen Token).


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


---

## 12. Reiter-Audit — Hauptbuch

Vereinbart 12.09.2026: jeder Reiter wird einzeln auditiert (Design, Darstellung,
Berechnung, Studienlage 2024–2026), Befunde als nummerierte Fix-Pakete, ein Paket
bzw. ein Reiter je Chat.

| Reiter | Status |
|---|---|
| **Trainer** | ✅ auditiert 12.09. — 14 Befunde; Paket 1 (Befunde 1–6) als **0.32.0 ausgeliefert und am System verifiziert** (Konfliktwächter feuert live mit 68 %); Paket 2 (Plan-Umbau + Rest Befund 10) als **0.33.0 gebaut**, Verifikation am System steht aus |
| **Trainer (Durability-Kachel, Paket F)** | ✅ auditiert 13.09. an der Fachliteratur (Maunder 2021, Spragg, Review Eur J Appl Physiol 2025, Wingo/Lafrenz zum kardiovaskulären Drift): der 90-Minuten-Schnitt hielt nicht — Durability wird über angesammelte Arbeit gemessen. Als **0.39.0 gebaut**, Verifikation am System steht aus |
| **Aktivitätsdetail (Vergleichsgruppe, Paket C)** | ✅ auditiert 13.09.; feste 40 % durch SD-Caliper ersetzt, die Spec-Zahl „0,2 SD ≈ ±20 %" war am eigenen Bestand um Faktor zwei daneben. Als **0.39.0 gebaut**, Verifikation am System steht aus |
| Belastung | ⏳ nächster Audit-Kandidat (seit 0.6.0 unangetastet, am weitesten hinter der Studienlage) |
| **DFA** | ✅ Paket A als **0.36.0 gebaut** — Brushing, Zeitfenster, Spalten, Sprung; Verifikation am System steht aus |
| **Signale (aufgeklappte Karte in Heute)** | ✅ Datumsachse und Ereignisspur als Teil von Paket A; Hohlpunkte für w=0-Tage seit 0.37.0 |
| **Heute, Kalender (Teilaspekt Tagesbeschriftung)** | ✅ Paket B (B2/B3/B6 + Chips) als **0.37.0 gebaut** — Verifikation am System steht aus; B5-Rest (Kachel, Mehrfachauswahl, Notizfeld, Kurzweg) und B4 offen für 0.38.0 |
| **Archiv-Pflege (Paket D)** | ✅ Abgleich mit Intervals als **0.38.0 gebaut** — Verifikation am System steht aus |
| **Archiv-Pflege (Paket D6)** | ✅ Kalender vs. Archiv in **0.39.0** getrennt: Aufschlüsselung aus der Payload, Refresh am Knopf, Cache-Verwerfen — Verifikation am System steht aus |
| **Vergleichsgruppe (Paket C)** | ✅ SD-Caliper auf der log-Dauer als **0.39.0 gebaut**, Leiter 0,2–1,0 SD, Weitung gegen das Kennzahl-n — Verifikation am System steht aus |
| **Durability-Kachel (Paket F)** | ✅ Arbeitsachse statt Dauer, VirtualRide raus, VI ≤ 1,10, Leitzahl mit Dünn-Regel als **0.39.0 gebaut** — Verifikation am System steht aus |
| **Durability-Kachel (Paket G)** | ✅ auditiert 13.09. **an den eigenen Livedaten, vor dem Bau**: die Zweiteilung beantwortet die Überschrift nicht, und die in G2 geforderte Leitzahl trägt auf diesem Bestand nicht (Steigung +2,95 ± 2,22 %/1.000 kJ, |t| 1,33; Kipppunkt 2.398 kJ jenseits der längsten Fahrt von 2.153 kJ; keine Krümmung nachweisbar). Punktwolke über der Arbeit, VI als Gewicht statt als Türsteher, gebinnte Mediane, Blockverlauf über 12 Wochen — als **0.40.0 gebaut**; die Kachel verweigert die Leitzahl und sagt, woran es liegt. Verifikation am System steht aus |
| **Konstanten-Dubletten (DFA/ACWR) + toter ring()/rd-Code** | ⬜ eigenes Paket, vom Wächter bei 2+2 eingefroren (docs/ausbau.md) |
| Heute, Kalender (voller Audit), Fitness, Aktivitäten | offen |

### Erledigt in 0.38.0: Paket D — Abgleich mit Intervals

Knopf „Abgleichen" im Kopf, ein Abruf über die ganze Historie mit
`fields=id,start_date_local`, Vergleich der IDs, Entfernen aus allen drei
Aufräumstellen (`activities`, `dfa`, `unavailable`). **Keine** Bedienhandlung
„Aktivität löschen" — die Entfernung ist Folge des Abgleichs und hat ein
Ergebnis: Gleichstand. Der Abgleich liest nur.

Die drei Sperren liegen in `reconcile.py`, das Lesen und Entscheiden
(`plan()`) vom Schreiben (`apply()`) trennt — ein Fehlschlag kann damit nur
vor dem ersten Handgriff passieren. Dazu drei Zustandssperren im Handler:
laufender Import, nie geholte Historie, veränderter Befund zwischen Anzeige
und Klick. Sechs Gegenproben, jede gezählt und benannt; eine davon biss
zunächst nicht und wurde geschärft (§7).

**Offen geblieben:** ob der Aktivitäten-Endpunkt ein `updated`-Feld führt, ist
weiter unbelegt — die Frage ist für den Abgleich aber gegenstandslos: eine
Löschung hinterlässt keinen Zeitstempel, also braucht jeder Löschbefund die
vollständige ID-Liste. Ein `updated` könnte nur *Änderungen* verbilligen.

### Erledigt in 0.37.0: Paket B — Tageskontext (B2, B3, B6 plus Chips)

Etiketten je Tag (`day_context`-Archivblock mit Migration), gewichtete
Basislinie über die EINE Primitive (`Σw ≥ 30`, sonst bit-identischer
Rückfall mit Zahlen-Hinweis), drei Ebenen strikt getrennt und bewacht
(Basislinie gewichtet · Warnlampe schließt nie aus, erklärt-Merkmal ·
Last kennt keine Etiketten), Websocket-Lese/Schreibweg (`tag: null`
löscht rückstandsfrei), Beschriftungsdialog als fester Kasten mit
Kategorien-Chips, Quellenblock nach Auflage A (belegt / Setzung / B4)
und Erklärtext nach Auflage B. Präzisierungen in `docs/ausbau.md`;
zwei Funde in §7 (Log-Diskrepanz in `state()`, fünfte HRV-Basislinie
in `analytics.hrv_status`). Geliefert bewusst OHNE Automatik oder
Schichtmuster-Ableitung (Entscheidung 12.09.2026).

### Erledigt in 0.36.0: Paket A — DFA-Reiter und Signalkarten

**Abweichung von der Spec, bewusst und einzeln freigegeben:** `docs/ausbau.md` führt Paket A
als „berührt: nur Frontend". Das hielt nicht. Zwei Punkte brauchten das Backend, beide
additiv, beide ohne Änderung an Bestehendem:

- `coach.py` → `history_days` (A5: die Achse braucht Daten, die es im Frontend nicht gibt)
- `importer.py` → fünf Felder an der Schwellenreihe, `websocket.py` → optionaler `since`
  (A3: die Spalten hätten sonst jenseits von 300 Einheiten still leer gestanden)

Geliefert: A1 Brushing & Linking über die `activity_id`, flüchtig per Zeiger und **fest im
Render** (nicht nur im DOM — sonst überlebt „fest" kein Neuzeichnen und ist nicht prüfbar);
A2 Zeitwähler als eigene Komponente mit allen vier Fallen; A3 elf Spalten inkl. Abweichung
gegen den rollierenden Median in bpm; A4 Hash-Route `#activities/<id>` mit sichtbarem
Scheitern, wenn die Einheit älter als der geladene Bereich ist; A5 Datumsachse und
Ereignisspur in der aufgeklappten Signalkarte.

Entscheidungen: Liste kappt bei **50** mit ausgesprochener Kappung (nicht stumm bei 15, nicht
stumm bei 400). Die Leitzahl bleibt fensterunabhängig, folgt aber weiter dem **Sportfilter** —
sachlich richtig, und die Quellzeile sagt jetzt, welcher Sport gemeint ist. Relative Fenster
haben **keine Obergrenze**. 13 Gegenproben gefahren, 13 bestanden, keine abgestürzt.

### Erledigt in 0.33.0: Paket 2 — Plan-Umbau (`plan.py`)

Alle vier Punkte umgesetzt (Details im Fehlerkapitel §7): `hard_per_week` ≤ 4 → 1
mit variierter zweiter Qualitätseinheit · großer Tag je Zyklus statt
`LONG_DAY_SHARE`-Wochenregel, Ziel-Default 6 h, Budget-Note als Ausnahme-Erklärung ·
`plan_start` persistiert, Wochen an Kalenderwochen · „für morgen"-Auszeichnung bei
`trained_today`. Dazu (Fund beim Umbau): die Planwochen wurden nie gerendert —
jetzt `rPlanWeeks` unten im Trainer-Tab. Neue Verträge in `test_plan`:
Progressions-Vertrag (großer Tag wächst über die Zyklen, Routinewoche wächst NICHT),
Kalender-Anker-Vertrag (Entlastungswoche erreicht ihr festes Datum aus vier
Blickdaten), Livefall-Simulation (4 Tage, 5,5 h, Ziel 6 h). Gegenproben: alte
hard-Regel, Anker aus, Progression aus, Duplikat statt Variation — jeder Vertrag
findet seinen Fehler.

### Erledigt in 0.35.0: Prüfstand-Hygiene und Profil-Migration

Kein Reiter-Audit, sondern zwei Altlasten (§7, 0.35.0) — und der **Ausbauplan
für die nächsten drei Pakete liegt jetzt im Repo**: `docs/ausbau.md` (A: DFA-Tab
mit Brushing, Zeitraumwahl und Sprung in die Aktivität, Datumsachse in den
Signalkarten · B: Tageskontext mit Etiketten und Gewichten · C: Vergleichsgruppe
über Caliper statt fester Prozentzahl). Jedes Paket mit Muster, Quelle, Grenze,
Datenmodell und den Gegenproben, die beißen müssen.

### Erledigt in 0.34.0: Paket 3 — Zustandsmaschine + Quellen

Befunde 5–8 umgesetzt, Details im Fehlerkapitel (§7, 0.34.0). Perspektive aus
Befund 7 bleibt offen: Anker triangulieren (DFA + LTHR aus `sport_settings` +
HF-Drift).

**Nächstes:** Audit des Belastungs-Reiters, danach Heute, Kalender, Fitness,
Aktivitäten, DFA, Signale — gleiche Methode wie beim Trainer (jede Zeile gegen
Code, Zahlen nachgerechnet, Quellen geprüft).

### Ursprünglicher Auftrag Paket 3 (Referenz)

5. **Slump-Trigger schärfen:** aktuell reicht EIN Signal an EINEM Tag (OR ab 2 SD) —
   der eigene Tension-Text nennt einen Einzeltag Rauschen. Ziel: HRV **und** RHR
   gemeinsam, oder ein Signal an 2 Folgetagen (der September-Infekt −2,7/+3,7 SD
   hätte weiter getriggert).
6. **Einbruchsursache klassifizieren:** beide Signale extrem → Infektverdacht →
   konservativere, symptomgeleitete Wiedereinstiegsleiter über mehrere lockere
   Einheiten (RTP-Praxis: „above/below neck", Stufen nur ohne Symptomrückkehr).
7. **DFA-Quellzeile aktualisieren:** „gegen Gasaustausch validiert" ist zu freundlich —
   Validierungslage 2024–2026: HRVT1-Übereinstimmung schwach (weite LOA), fitness-
   abhängiger Bias (bei Fitteren unterschätzt), HRVT2 robuster; als Trend brauchbar,
   als alleinige Verankerung nicht. Perspektive: Anker triangulieren (DFA + LTHR aus
   sport_settings + HF-Drift).
8. Kleinkram: VO2max-HF-Fenster gegen max_hr klemmen oder streichen; Anker-Block auf
   EINEN „jetzt"-Wert (Median letzte 5); `endurance`-Familie nie ausblenden
   (layoff-Skip verletzt „nie filtern, nur bewerten"); Zahlformat Komma statt Punkt;
   goalbar-Ternary; Zustandsfarben Rebound/Elevated vs. Farbregister klären.

### Trainer-Restbefunde, erledigt in 0.32.0

Verwaiste rTrainer-Blöcke (Infekt-Warnung!) · zweiter Empfehler · Anker-Konflikt-
wächter · Budget-Lead · Entlastungs-Arithmetik · `weekly_load`-Quelle — Details im
Fehlerkapitel (§7).
