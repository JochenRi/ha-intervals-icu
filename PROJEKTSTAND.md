# ha-intervals-icu — Projektstand

**Stand:** 15.09.2026 · **Version:** 0.53.0 · **Status:** produktiv auf HEIMDALL,
Auslieferung über HACS aus `github.com/JochenRi/ha-intervals-icu`

Eine eigene Home-Assistant-Integration, die Trainingsdaten von Intervals.icu lokal
archiviert, auswertet und in einem eigenen Seitenleisten-Panel darstellt.

**Umfang:** ~14.760 Zeilen, davon ~4.960 Frontend · 27 WebSocket-Befehle · 16 Einheiten in
9 Familien · 20 Testdateien mit **6.167** gezählten Einzelprüfungen · 60 Releases.

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
├── durability_tests.py  markierte Protokolltests und ihre Messwerte (HA-frei)
├── sensor.py         49 Entitäten
├── calendar.py       Kalender-Entität mit geplanten Workouts
├── websocket.py      26 Kommandos für das Panel
└── frontend/
    └── intervals-panel.js   Panel, eine Datei ohne Abhängigkeiten (3.137 Zeilen)
```

**Sechs HA-freie Module** (`derive`, `analytics`, `coach`, `workouts`, `plan`,
`durability_tests`) importieren
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
| DFA alpha-1 | Rogers/Gronwald: 0,75 ≈ VT1, 0,5 ≈ VT2 | **Validierungslage 2024–2026, nicht „gegen Gasaustausch validiert"**: die zweite Schwelle (0,5) hält durchgängig, die erste (0,75) nicht — Olieslagers 2026 findet für HRVT1 schlechte Übereinstimmung mit LT1/VT1 bei einem Bias von −21 bis −45 W. Empfindlich für Artefakte und Gerät. Die Zeile stand bis 0.51.0 noch auf dem alten Stand, obwohl 0.34.0 „beide DFA-Quellzeilen" umgestellt haben wollte (§7, siebzehnter Fall) |
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

**0.47.2 / 0.48.0 — vier Befunde.**

**1 · `stream_types` sagt, was in der DATEI lag — nicht, was die SCHNITTSTELLE
liefert.** Die Aktivitäten führen `hrv` in `stream_types`. Der Streams-Endpunkt
liefert ihn nicht: abgerufen kamen `cadence, dfa_a1, heartrate, time, watts`
zurück, der angeforderte Kanal fehlte vollständig. **Wer aus dieser Liste
ableitet, welche Daten verfügbar sind, liegt falsch** — sie ist eine Auskunft
über den Inhalt der hochgeladenen Datei, nicht über die API.

**Geprüft, ob das eine Klasse ist: es sind zwei weitere Stellen, und sie
funktionieren** — `importer.has_watts()` und `has_dfa()` schließen ebenfalls aus
`stream_types`. Für diese beiden Kanäle trägt der Schluss (58 DFA-Auswertungen
existieren). **Die Bauart bleibt trotzdem riskant, und zwar still:** meldet
`has_dfa()` True und der Abruf kommt leer zurück, schreibt
`async_import_dfa()` ein leeres Dict — die Fahrt gilt als abgearbeitet und wird
nie wieder geholt. Ein Kanal, den die Datei führt und die API nicht liefert,
verschwindet damit lautlos aus dem Bestand. **Kein Fehler, der passiert ist —
einer, der auf seinen Anlass wartet.**

**2 · Zweimal dieselbe Fehlkorrektur bei der Vermessung für Paket M.**

**Eine Messgröße wurde zweimal als untauglich verworfen, bevor der Ausschnitt
stimmte, aus dem sie gerechnet wurde.** Beide Male traf es VO2max, beide Male
mit einer Zahl, die etwas anderes maß, als ihr Name sagte.

**Erster Fehlschluss: eine Division als methodische Grenze.** „VO2max-Blöcke
tragen ein auswertbares 2-Minuten-Fenster" — das war Blockdauer geteilt durch
120 Sekunden, also eine Zählung von Zeitabschnitten. Eine DFA-Fensterbreite ist
etwas völlig anderes, und Intervals liefert ohnehin je Sekunde einen fertigen
Wert: ein 4-Minuten-Block trägt **240**, nicht einen. **Der Satz „vier Minuten
sind zu kurz" klingt nach einem Naturgesetz und war eine Division** — und er
hätte eine Familie endgültig ausgeschlossen.

**Zweiter Fehlschluss: eine Streuung, die zu 80 % aus dem Anlauf stammte.** Die
Blockmediane streuten mit SD 0,25 bis 0,53, und daraus wurde „der Gurt trägt
oben nicht". Tatsächlich beginnt jeder Block bei hohem alpha und fällt
innerhalb der ersten zwei Minuten — der kardiale Nachlauf, den Rogers (2021)
und Andriolo genau deshalb verwerfen. Nach dem Verwerfen bleibt SD **0,087**,
ein Gewinn von 69 bis 83 %. **VO2max hat damit die KLEINSTE Streuung aller drei
Familien** (gegen 0,156 bei SweetSpot) — das Gegenteil des Befunds, mit dem es
ausgeschlossen wurde.

**Dazwischen lag noch ein dritter Irrtum derselben Wurzel:** aus „Block 1 liegt
höher als Block 2, in allen sieben Paaren" wurde Ermüdung gelesen. Der Beleg
dagegen stand in denselben Daten — die zweite Hälfte von Block 1 liegt bei
0,67, Block 2 im Median bei 0,67. **Es gab keinen Abfall zwischen den Blöcken;
Block 1 hatte nur einen Anlauf, den Block 2 nicht mehr hat.**

**Vierter Fall, und er sitzt außerhalb des Codes: eine FIXTURE-Zahl im Bericht
an den Athleten.** Die Leitzahl wurde ihm als **262 W** gemeldet, während die
Simulationstabelle derselben Meldung 259/260 W nannte. Der Unterschied war
keiner: 262 W stammten aus der Test-Fixture, in der eine sechste VO2max-Einheit
erfunden ist, damit der Fall „genug Punkte für eine Linie" überhaupt prüfbar
wird. Aufgefallen ist es nur, weil er nach dem Unterschied zwischen zwei
ähnlichen Zahlen gefragt hat.

**Das ist keine Entlastung, sondern eine eigene Gefahrenstelle.**
Fixture-Werte sehen wie Messwerte aus — dieselbe Form, dieselbe Einheit,
derselbe Lauf. Und **ein Bericht wird nicht getestet**: der Prüfstand deckt den
Code ab, nicht das, was über ihn geschrieben wird. Der Fehler hatte hier
Folgen über die zwei Watt hinaus: mit fünf statt sechs Einheiten erscheint im
Panel **keine Verlaufslinie**, und ohne die Rückfrage wäre das nach dem Update
für ein fehlendes Diagramm gehalten worden.

**Fünfter Fall (0.48.1): ein Kommentar, der nur die halbe Bedingung nennt.**
`normalize_laps` hielt seit Paket K fest: *„der Index zählt im ORIGINAL-1-Hz-Strom,
während das Panel einen gedünnten bekommt, deshalb ist die Zuordnung über die
ZEIT der sichere Weg und der Index nur ein Rückfall."* Das stimmt **für das
Panel**. Für den Import gilt das Gegenteil: dort läuft der Strom ungedünnt mit
1 Hz, der Index ist exakt — und die Sekunden sind es nicht, weil `start_s` in
verstrichener Zeit läuft und der Strom in Bewegungszeit. Bei der Einheit vom
01.09.2026 sind das **114 Stellen Versatz**, genau die Standzeit.

Die Folge stand danach im Archiv: ein als `WORK` etikettierter Abschnitt mit
**88 W** neben einer `RECOVERY` mit **253 W**. Sämtliche Blockwerte, Mediane
und Vorschläge des Release kamen aus vertauschten Ausschnitten.

**Ein Kommentar, der nur die halbe Bedingung nennt, ist gefährlicher als
keiner** — er sieht aus wie eine Klärung und führt zur falschen Wahl. Das ist
die Verwandte der Zahl, die nicht misst, was ihr Name sagt: hier ein Hinweis,
der nicht gilt, wo er gelesen wird. Er nennt jetzt **beide** Fälle.

**Sechster Fall (0.49.1): eine Gegenprobe, deren Toleranz geraten war.** Die
Prüfung gegen Intervals' eigene Lap-Werte meldete fünf Widersprüche. Nach dem
Aussortieren der falsch etikettierten Einrollblöcke waren es **immer noch
fünf** — die Regel behob keinen einzigen, weil die Widersprüche gar nicht
daher kamen. Die Einheit vom 01.09. hat keinen Einrollblock; unsere Reihe
steigt im letzten Schritt um **0,024**, die fremde fällt, und das genügte.

**Intervals mittelt jeden Block samt Anlauf, wir verwerfen ihn — der
Unterschied ist systematisch und kein Fehler.** Die Schwelle von 0,02 und die
Forderung, dass ALLE Paare übereinstimmen, waren aus einer Wunschgenauigkeit
gegriffen, nicht aus dem Unterschied der beiden Rechenwege.

**Gemessen in 0.49.2:** Intervals' Wert liegt über 80 Blöcke im Median **0,224**
über unserem, Spanne 0,004–0,539. Die Toleranz folgt daraus: ein eigener
Schritt unter **0,05** liegt unter der Schwankung dieses Versatzes und kann
seine Richtung allein daraus beziehen. Sechs der acht beanstandeten Paare lagen
darunter (Median 0,038).

**Eine Mehrheitsregel wäre eine Abschaltung gewesen.** Von 25 Einheiten haben 8
eine Abweichung, und **jede hat genau ein abweichendes Paar** — Anteile 0,25 /
0,33 / 0,50, nie darüber. "Mehr als die Hälfte weicht ab" ergäbe im ganzen
Bestand null Meldungen, auch die berechtigten nicht. **Eine Regel, die nie
greift, ist keine Regel.** Sie wurde deshalb nicht gebaut.

**Siebter Fall (0.49.2): die Neuberechnung hat die Belege gelöscht.** Die
Konstellationen, an denen sich die Gegenprobe hätte beweisen müssen, gab es
nach 0.49.1 nicht mehr — der Fix hatte sie beseitigt. **Wer einen Fix
ausliefert, verliert damit die Belege für die Prüfung, die den Fix gefunden
hat.** Nachgebaut ist keine Messung; die Fixture in `test_blocks.py` ist
ausdrücklich als Stand vor 0.49.1 beschriftet und belegt nur, dass die Regel
bei dieser Konstellation anschlägt — nicht, dass sie noch vorkommt.
**Lehre: solche Fälle VOR der Neuberechnung als Fixture sichern, nicht danach
suchen.**

**Achter Fall (Paket N, in der Literatur statt im Code): aus zwei Arbeiten je
die passende Hälfte.** Für den Stufentest wurde die personalisierte Schwelle
als „praktisch exakt" zitiert (Rogers 2024) und die Unsicherheit der absoluten
Schwellenhöhe mit 21–45 W beziffert — **die zweite Zahl stammt aus einer Arbeit
von 2026, die genau diese personalisierte Schwelle NICHT bestätigt** (nur
marginale Verbesserung, systematischer Bias bleibt). Aus der einen Quelle kam
das Günstige, aus der anderen das Skeptische, und der Widerspruch zwischen
beiden fiel niemandem auf. **Wer aus zwei Arbeiten je die passende Hälfte
zitiert, baut sich einen Beleg, den es nicht gibt.**

**Neunter Fall, derselben Klasse und ebenfalls aus der Literatur: zwei
verschieden ERHOBENE Größen unter einer Überschrift.** Fleitas-Paniagua 2023
fand keinen Effekt der Rampensteigung auf HRVT1/HRVT2 — gemessen in HF und VO2.
Rogers warnt davor, aus steilen Rampen die LEISTUNG abzulesen. Das sah nach
Widerspruch aus und ist keiner: bei steileren Rampen liegt die Leistung am
selben VO2 höher, weil die Sauerstoffaufnahme hinterherhinkt. **Dieselbe Klasse
wie 0.49.2, nur diesmal zwischen zwei Veröffentlichungen statt zwischen zwei
Rechenwegen.** Wer Studien vergleicht, prüft zuerst, in WELCHER Größe sie
gemessen haben.

**Zehnter Fall (0.50.0, gefunden vor dem Bau): eine Ableseleiste, die den Wert
einer ANDEREN Kurve zeigte.** Die Spezifikation zu Paket O sagte, beim
Überfahren der Block-Kurven komme „nichts". Am Code nachgesehen kam sehr wohl
etwas — nur das Falsche. Die Durability-Kachel klammert Kopf, Ermüdungskurve,
Block-Karten, Tabellen und Rechenweg in EINEN Gruppen-Wrapper
(`data-grp="fat"`). Der Zeiger-Handler sucht mit `closest("[data-grp]")` und
findet damit auch über einer Block-Karte diesen Wrapper; `_xhMove` nahm dann
`querySelector("svg.ch")`, also das ERSTE Diagramm darin — die Ermüdungskurve.
Simuliert: der Zeiger auf Höhe einer Block-Karte schrieb „2,50 h Fahrtzeit"
samt gemessen/Studienform/Belegung in die Leiste.

**Dieselbe Klasse wie die sechs Fälle darüber, nur eine Ebene tiefer: eine
Zahl, die nicht misst, was daneben steht.** Der Unterschied ist die Herkunft —
die anderen entstanden in einer Rechnung, diese in einem WRAPPER. Kein
Testfall war falsch, keine Formel war falsch; falsch war, welches Element der
Handler unter dem Zeiger für zuständig hielt. **Eine Gruppierung im DOM ist
eine Zuständigkeitsaussage und gehört geprüft wie eine Formel.**

Behoben an der Wurzel statt an der Stelle: die Leiste schreibt nur noch, wenn
der Zeiger senkrecht über dem Diagramm liegt, und die Block-Karten bekommen je
Familie eine eigene, geschachtelte Gruppe. Waagerecht bleibt es beim Klemmen —
ein Zeiger neben der Achsenbeschriftung meint den ersten Punkt und nicht
„nichts", und das ist seit 0.9.3 zugesichert.

**Elfter Fall (0.50.0, in der eigenen Gegenprobe): eine Mutation, die nicht
griff, sieht aus wie ein bestandener Test.** Eine der Gegenproben zu Paket O
drehte den Läufer-Hinweis zurück — und die Suite blieb grün. Die Ersetzung
hatte den Text gar nicht getroffen (ein Zeilenumbruch im Template), also
prüfte die Gegenprobe eine unveränderte Datei. Mit einer Trefferzusicherung
vor der Mutation fiel derselbe Test sofort an vier Stellen.
**Lehre: eine Gegenprobe braucht den Nachweis, dass sie überhaupt etwas
verändert hat** — sonst ist „grün nach der Mutation" die Auskunft über eine
Mutation, die es nie gab. Dieselbe Klasse wie die stumpfen Tests aus 0.36.0,
nur auf der Werkzeugseite.

**Nachgesehen, ob es eine Klasse ist — und die Zahl steht hier, weil sie die
Frage beantwortet, wie viele Prüfungen womöglich nichts prüfen.** 122 Stellen
im Prüfstand tragen das Wort „Gegenprobe" oder „Fixture-Beweis", davon 44 als
reiner Kommentar, bleiben 78 Prüfungen. Aufgeteilt: **9** pflanzen ein Literal
und halten den Wächter-Ausdruck dagegen (die Mutation IST das Literal, ein
Fehlschlag ist unmöglich), **26** sind Fixture-Beweise, die genau diesen
Nachweis bereits führen, **43** bauen einen eigenen Gegenfall. Von diesen 43
konnten **drei** unbemerkt zum Nichts werden: das gefilterte Literaturraster in
`test_panel_fixes`, die geleerte Ausschlusszahl in `test_panel_views` und
`mutated.pop("checked_unavailable", None)` in `test_reconcile` — `pop` mit
Vorgabewert schluckt einen Schlüsselnamen, der sich geändert hat. **Alle drei
haben in 0.50.0 eine Trefferzusicherung bekommen**, jede einzeln gegengeprüft:
zum No-op entschärft, fällt sie benannt. Der Fall in `test_reconcile` fiel
dabei schon über die bestehende Prüfung — die neue Zusicherung deckt die
andere Richtung ab, in der das Feld ganz aus dem Bericht verschwindet.
**Keine Datei nutzt die riskanteste Bauart** (eine Textersetzung am echten
Quelltext) für eine Gegenprobe; die trat nur in der Sitzungsarbeit auf, und
genau dort hat sie zugeschlagen.

**Zwölfter Fall (0.51.0): ein Fix, der das Problem nicht behob — und dabei
aussah, als hätte er es.** Bei den Gegenproben zur Stufentest-Auswertung
meldeten fünf von acht Mutationen grün. Nicht weil die Tests stumpf waren:
Python hatte die **alte Fassung aus dem Bytecode-Cache** geladen. Die
Invalidierung einer `.pyc` läuft über mtime **und** Größe der Quelldatei — und
eine Mutation, die gleich lang ist und in derselben Sekunde geschrieben wird,
ist genau der Fall, in dem beides unverändert aussieht. Eine Gegenprobe, die
die alte Fassung misst, ist keine.

**Die zweite Schicht ist die schlimmere.** Als Abhilfe lief die nächste Runde
mit `python3 -B`, und alle zehn Mutationen fielen — gemeldet als „alle zehn
fallen gezählt und benannt". **`-B` verhindert nur das SCHREIBEN neuer
Dateien; vorhandene liest Python weiterhin.** Der Fix hat nichts behoben und
sah aus wie eine Lösung. Nachgestellt, Quelle 100 → 999 bei gleicher Länge und
zurückgesetzter mtime:

| Aufruf | geladen |
|---|---|
| `python3` | 100 (Cache) |
| `python3 -B` | **100 — der Fix greift nicht** |
| frischer `pycache_prefix` | 999 |
| `rm -rf __pycache__` | 999 |

**Das ist die Verwandte des elften Falls, eine Ebene tiefer.** Dort verfehlte
eine Ersetzung ihren Text; die Antwort darauf war eine Trefferzusicherung auf
der DATEI. Die reicht nicht — sie prüft, was auf der Platte steht, nicht was
der Interpreter daraus lädt. **Zwischen „die Datei ist geändert" und „der Test
misst die Änderung" liegt eine Schicht, die niemand geprüft hatte.**

**Die Reichweite ist offen, und das gehört gesagt.** Jede Gegenprobe dieses
Projekts, die vor dieser Erkenntnis gefahren wurde, könnte betroffen sein —
überall dort, wo eine Mutation gleich lang war und schnell genug kam. Eine
Nachprüfung aller Prüfungen findet nicht statt; was stattfindet, ist die
Regel, die es ab jetzt unmöglich macht. **Ein Befund, der nur als Einzelfall
verbucht wird, wiederholt sich in der nächsten Datei.**

**Dreizehnter Fall (0.51.0): eine Zahl, die aus einer GERADEN entsteht statt
aus einer Messung.** Die Stufentest-Auswertung legt eine Ausgleichsgerade
durch den Abfall von DFA a1 und liest die Schwelle als deren Schnittpunkt mit
0,75 bzw. 0,5. Bei einem **konvexen** Abfall — steil, dann flach, Boden bei
0,55 — schneidet diese Gerade die 0,5 **mitten im Segment**, während die
Messung nie unter 0,55 war. Ohne eine Bedingung stünde dort eine zweite
Schwelle, die der Athlet nie gefahren ist: eine Zahl mit Einheit, Datum und
Herkunftsangabe, und ohne Messung dahinter.

**Dieselbe Klasse wie die Zahlen, die nicht messen, was ihr Name sagt — nur
ist die Quelle diesmal ein Rechenverfahren.** Die Regel heißt jetzt: eine
Schwelle gibt es nur, wenn der zugehörige Bereich auch gemessen wurde, und
über das Segment hinaus wird nicht hochgerechnet. Dieselbe Regel, die die
Durability-Kachel über ihre arbeitsreichste Fahrt hinaus einhält.

**Und der Weg dorthin gehört dazu: eine eigene Fixture hat den Autor
widerlegt.** Gebaut war zuerst ein Fall mit kurz gehaltenem Boden, in der
Annahme, `reached_anaerobic` bedeute „der Boden wurde gehalten". Der Code
meinte „die Kurve ging unter 0,5 und blieb dort" — bei einer Rampe, die auf
0,45 endet, ist das dasselbe, und die Fixture prüfte nichts. Erst der konvexe
Fall trennt beides. **Eine Fixture, die die eigene Annahme nicht überlebt, ist
der billigste Befund, den dieses Projekt kennt.**

**Vierzehnter Fall, derselben Runde: sechs Gegenproben bissen nicht, weil die
saubere Fixture ihre Regel nie beanspruchte.** Nach dem Abschalten des Caches
fielen von zehn Mutationen zunächst nur vier. Die übrigen sechs — kein
Hochrechnen, gemessener Boden, Glättung, zwei Haltebedingungen, Median beim
Ablesen — waren nicht falsch, sie waren **ungeprüft**: der glatte, saubere
Testfall löst keine einzige dieser Regeln aus. **Dieselbe Lehre wie die
Dosis-Frage aus 0.45.0**, nur auf der Fixture-Seite: eine Gegenprobe muss den
Fall treffen, für den die Regel gebaut wurde, nicht den Normalfall. Jede der
sechs hat jetzt eine eigene Fixture, die genau ihre Regel trifft.

**Fünfzehnter Fall (0.51.0): ein Schnitt ohne Zusicherung über die
Dateigröße.** Beim Ausbau des Durability-Protokolls sollten drei Funktionen
aus `workouts.py` verschwinden. Die Schnittregel lautete „von der Leerzeile vor
der Funktion bis zur nächsten nicht eingerückten Zeile" — und sie ist falsch,
weil **mehrzeilige Zeichenketten Zeilen am Spaltenanfang enthalten**. Der
Schnitt endete mitten im Docstring, der Rest der Datei wurde mehrfach
angehängt: **1.445 Zeilen wurden 3.603.**

**Aufgefallen ist es nur, weil die Zeilenzahl hinterher gegengeprüft wurde.**
Der Syntaxbaum war intakt, der Import lief, die Datei sah aus wie eine Datei.
Ohne den Blick auf `wc -l` wäre eine dreifach vorhandene Funktionsliste in den
nächsten Testlauf gegangen — und dort grün geworden, weil die letzte Definition
gewinnt.

**Das ist dieselbe Klasse wie eine Mutation ohne Trefferzusicherung (§7,
elfter und zwölfter Fall), nur auf der anderen Seite der Werkzeugkiste:** dort
wurde eine Änderung gemacht, die nicht ankam; hier wurde eine gemacht, die zu
viel traf. Beide Male sah der Lauf danach richtig aus. **Regel: am Syntaxbaum
schneiden, nicht am Zeilenbild — und die erwartete Größenänderung mitnennen.**

**Das Gegenstück gehört in denselben Eintrag, weil es zeigt, wo schon ein
Wächter steht:** in derselben Sitzung sind mehrere Ersetzungsskripte an einer
Zeichenkette gescheitert, die es nicht mehr gab. Jedes Mal hat die
Trefferzusicherung aus 0.51.0 zugeschlagen, laut gemeldet und **nichts
geschrieben**. Genau so soll ein Fehler aussehen. Der Größenfall zeigt die
Stelle, an der noch keiner laut scheitert.

**Sechzehnter Fall (0.51.0): eine Bauregel, die nur aufgeschrieben ist — und
ein Kommentar, der sie falsch zitiert.** Die erste der zwei Bauregeln aus
0.41.0 (§9) verlangt, dass Feldzugriffe **im Testcode** über `.get()` laufen und
nie über `[]`: ein fehlendes Feld ist genau das, was eine Mutation herstellt,
und es muss als gezählter, benannter Fehler erscheinen. **Sie ist an keiner
Stelle erzwungen.** Kein Wächter prüft sie; sie steht in §9 und sonst nirgends.

**Die neue Testdatei verletzt sie an 41 Stellen.** Alle 41 liegen auf
Payloads, die das Bauteil zurückgibt — `res` aus `ramp.evaluate()` (33), `seg`
aus `ramp.segment()` (5), `_f` aus `ramp._fit()` (2) —, also genau auf der
Klasse von Objekten, gegen die eine Mutation gefahren wird. Nachgestellt mit
Trefferzusicherung und kaltem Cache, `"hrvt1"` aus der Payload entfernt:

    File ".../test_ramp.py", line 118, in <module>
        near("HRVT1: Zeitpunkt", at(res["hrvt1"], "seconds"), ...)
    KeyError: 'hrvt1'

Kein Summary, keine Zählung, kein benannter Fehler — nur `rc=1`. Das ist
wortwörtlich die Fehlerklasse, gegen die die Regel 0.41.0 geschrieben wurde,
fünf Releases später und in der Datei, die sie hätte kennen müssen.

**Gefangen hat es trotzdem etwas, aber auf einem Umweg:** `test_projektstand`
fährt jede Datei als Unterprozess und meldete den Absturz als vier gezählte,
benannte Fehler („meldet keine Zahl", „läuft nicht grün", „steht in der
Tabelle, läuft aber nicht", Kopfzahl 5.758 statt 5.669). Die Panne wird also
gesehen — aber als **Prüfstandsdefekt**, nicht als der Befund, den die Mutation
beweisen sollte. **Ein Rauchmelder im Flur, kein Feuerlöscher am Herd.**

**Und der Grund, warum dieser Befund zweimal falsch weitergereicht wurde,
gehört in denselben Eintrag.** Ein Kommentar in `workouts.py` zitierte die
Regel als „§9, **zweite** Bauregel" — sie ist die erste — und er stand an einer
Stelle im **Bauteil**, für die sie ihrem Wortlaut nach gar nicht gilt. Daraus
entstand über zwei Sitzungen der Auftrag, „einen Verstoß im Bauteil"
aufzuschreiben, den es nie gab: das danebenstehende `node["watts"]` liegt unter
der Vorprüfung `if node.get("watts") and node.get("hr")` in derselben Bedingung
und kann nicht fehlen. **Dieselbe Klasse wie der falsche Kommentar in
`normalize_laps` aus 0.48.1: ein Hinweis, der nicht stimmt, ist gefährlicher
als keiner, weil er wie eine Klärung aussieht** — und dieser hier hat zusätzlich
bewirkt, dass niemand die Regel nachlas. Der Kommentar ist in 0.51.0
geradegezogen, mit dem Geltungsbereich daneben. **Der Wächter ist bewusst NICHT
in diesem Release gebaut** (§10): er erzwingt eine Regel, die über alle
Python-Testdateien 1.633 lesende `[]`-Zugriffe beträfe, und ein Umbau dieser
Größe gehört nicht in ein Auslieferungs-Release.

**Siebzehnter Fall (0.51.0): eine Aufräumrunde, die „alle Stellen" behauptet,
ohne eine Prüfung zu hinterlassen, die es erzwingt.** 0.34.0 hält fest, dass
**beide** DFA-Quellzeilen die Validierungslage 2024–2026 tragen statt „gegen
Gasaustausch validiert". Die Zeile in §5 trug den alten Satz weiter — aufgefallen
erst, als der Bau von Paket N sich auf Olieslagers 2026 stützte und damit auf
einen Befund, dem die eigene Belegtabelle widersprach.

**Und der Suchraum war kleiner als der Befund.** Nachgezählt in 0.51.1: der Satz
steht nicht nur im PROJEKTSTAND, sondern auch **zweimal im README** — Zeile 113
englisch, Zeile 252 deutsch, dieselbe Tabelle in beiden Sprachfassungen. Die
Aufräumrunde von 0.34.0 hat nur im PROJEKTSTAND gesucht und „beide" gesagt, ohne
zu benennen, **worin** sie gesucht hat. Das ist die Verschärfung der
Listen-Klasse: eine handgepflegte Vollständigkeit scheitert nicht erst an der
nächsten Stelle, sondern schon an der nächsten **Datei** — und ein Suchraum, den
niemand aufschreibt, kann von keinem Nachfolger nachgeprüft werden. Seit 0.51.1
stehen alle auf der Validierungslage 2024–2026. **Siebter Fall der
Listen-Klasse** (vierte Bauregel, §9): eine handgepflegte Vollständigkeit ohne
Vollständigkeitsprüfung hält genau bis zur nächsten Stelle, an die niemand
denkt. Hier ist die Stelle korrigiert; die Klasse bleibt offen, weil ein
Wächter über Fließtext-Belege in einer Markdown-Tabelle mehr verspräche, als er
halten kann.

**Achtzehnter Fall (0.51.1): ein Wächter, der die Ausnahme bewacht und die
Regel nicht.** N1 lässt für den Stufentest genau drei feste Zahlen zu —
Einrolldauer, Ausrolldauer, Rampensteigung — und verbietet alles andere:
**keine festen Leistungszahlen.** Ausgeliefert wurde in 0.51.0 ein
Katalogeintrag mit `ramp 60-115%` und den Blöcken 60/90/60, **allesamt
Ableitungen der FTP**. Ein Wächter darüber existierte, war grün, und prüfte:

    for _literal, _name in ((" 15 ", "Einrolldauer"), (" 10 ", "Ausrolldauer"),
                            (" 5 W", "Rampensteigung")):

Er stellte sicher, dass die **Dauern** nicht im Eintrag stehen — also genau das,
was N1 als einzige feste Zahlen **erlaubt**. Über die Prozentwerte, also über
das, was N1 **verbietet**, sagte er nichts. **Ein Wächter, der die Ausnahme
bewacht und die Regel nicht, ist schlimmer als keiner: er sieht aus wie
Absicherung und lässt genau das durch, wogegen die Regel geschrieben wurde.**

**Und es funktionierte nicht, messbar.** Bei FTP 200 endete die Rampe bei
230 W, während die eigene VO2max-Leitzahl bei **257 W und alpha 0,47** steht —
also **27 W unter** der Leistung, bei der der Athlet bereits unter 0,5 misst.
Die zweite Schwelle war nicht erreichbar; der halbe Test lieferte nichts. Genau
die Schwelle, für die der Test gebaut wurde, und genau die Frage (die 40 Watt),
die er beantworten sollte.

**Dazu ein zweiter Widerspruch, im selben Eintrag.** Dauer (30 min), Steigung
(5 W/min) und Spanne (55 % der FTP) standen nebeneinander und passten **nur bei
einer einzigen FTP** zusammen: 272,7 W. Bei 200 W behauptete die Karte 30
Minuten für eine Rampe, die nach 22 zu Ende ist. Drei Zahlen, von denen keine
aus den anderen folgte.

Gebaut ist seit 0.51.1: zwei getrennte Quellenketten (Start aus der
Ermüdungskurve, Ende aus der Blockmessung), die Reserve als **Zeit** statt als
Anteil — sie sagt, was sie bedeutet, und hängt nicht an einer zweiten
Prozentzahl —, und **die Dauer wird gerechnet, nie gesetzt**. Der Widerspruch
ist damit nicht mehr herstellbar, nicht bloß geprüft. **Regel: wo ein
Widerspruch konstruierbar bleibt, genügt eine Zusicherung nicht; die bessere
Antwort ist, die dritte Zahl aus den beiden anderen zu rechnen.**

Und beim Bau lauerte die Falle daneben: die Blockmessung liefert **zwei**
Zahlen, die Leitzahl (257 W bei alpha 0,47) und die Trainingsvorgabe (250 W bei
Median-alpha 0,40). Die falsche hätte 300 W ergeben — plausibel aussehend und
falsch begründet, **0.49.2 in neuer Gestalt**. Der Wächter prüft deshalb nicht
nur den richtigen Wert, sondern **schließt den falschen namentlich aus**. Das
ist die schärfere Bauart und ab hier das Muster: *eine Prüfung, die nur das
Richtige bestätigt, übersteht jede Verwechslung, die zufällig auch richtig
aussieht.*

**Neunzehnter Fall (0.51.1): ein Umzug zwischen zwei Payloads, und ein `|| []`,
das ihn verschluckt hat.** Die zehn Punkte, die sagen, **wie** der Stufentest zu
fahren ist, waren in 0.51.0 unsichtbar. Das Bauteil legte sie als `protocol` in
die `ramp_tests`-Payload; das Panel liest sie als `entry.standard` **an der
Einheit**. Zwei verschiedene Payloads, zwei verschiedene Namen — und
`(entry.standard || []).length ? … : ""` macht aus einem fehlenden Feld eine
leere Liste und aus einem Fehler **eine Anzeige ohne Inhalt.** Kein Test schlug
an: der eine prüft die Liste im Bauteil, der andere die Darstellung im Panel,
und dazwischen sah niemand hin. **Das leere Fallback ist der eigentliche Täter.**

Warum es nie auffiel: bis 0.50.0 stand dort das Durability-Protokoll — eine
Einheit, die nie gefahren wurde. **Ein Feld, das niemand vermisst, ist kein
Beweis dafür, dass es ankommt.** Erst als Paket N zehn Punkte hineinlegte, die
jemand lesen wollte, wurde die Lücke sichtbar. Dasselbe gilt für `derivation`:
es stand seit 0.51.0 leer, weil niemand es mehr füllte, und niemand bemerkte es.

**Die Bauart-Umfrage entlastet den Rest:** 64 stille Rückfälle
(`x.feld || []`) auf payload-artige Objekte im Panel, davon lesen **zwei** einen
Namen, den kein Bauteil schreibt — genau `standard` und `derivation`. Die
übrigen sind Panel-Eigenzustand und Diagramm-Optionen. **Kein Muster, ein Nest.**

**Und ein Befund über den Befund.** Die erste Meldung dieses Falls lautete
„seit 0.44.0 unsichtbar, sieben Releases" — und war falsch: durchsucht worden
war nur `websocket.py`, während die Felder in `workouts.py` an den
Durability-Katalogeinträgen hingen und dort bis 0.50.0 gerendert wurden.
Gebrochen ist es in **einem** Release, nicht sieben, und der Mechanismus ist ein
anderer: kein Umbenennen, sondern ein Umzug zwischen zwei Payloads. **Eine
schärfere Zahl, als die Prüfung hergibt, macht einen richtigen Befund
angreifbar** — derselbe Satz wie bei der 24-Fenster-Richtigstellung aus 0.46.0,
und das **zweite Mal**.

**Zwanzigster Fall (0.51.1): eine Zahl, die man korrigieren kann, ohne dass sie
richtig wird.** Die Stufentest-Karte nannte ein Pulsfenster von 112–160 bpm —
`hr_hint` (0,70–1,00) skaliert auf die **aerobe** Schwelle von 160 bpm. Die
Rampe geht bis stabil unter alpha 0,5; die eigene Blockmessung liegt dort bei
**172–186 bpm**. Das Fenster konnte den Test nicht beschreiben: es hörte
bauartbedingt an der aeroben Schwelle auf.

Der Reflex wäre, die Spanne zu verbreitern. **Der wäre falsch.** Bei jeder
anderen Einheit ist das Fenster ein **Ziel**, in dem man bleibt. Bei einer Rampe
wandert der Puls über den ganzen Bereich — ein Fenster ist dort nicht bloß
ungenau, es ist die **falsche Art von Aussage**: wer darin bliebe, bräche den
Test ab. 110–190 bpm wäre korrekt und nutzlos gewesen. **Eine breitere Spanne
hätte es nur unauffälliger gemacht, nicht besser.** Regel: **eine Zahl, die man
korrigieren kann, ohne dass sie richtig wird, gehört weg und nicht angepasst.**
An ihrer Stelle steht seit 0.51.1 ein Satz, der genau das sagt.

**Einundzwanzigster Fall (0.51.1): ein Auslieferungsschritt, den keine Prüfung
erzwingt, fällt irgendwann aus — und es war der, an dem man das Update
erkennt.** §11 Schritt 3 lautet seit vielen Releases: *„Version heben:
`manifest.json` **und** `const.py PANEL_VERSION` (beide!)"*. Das Ausrufezeichen
stand da, weil der Schritt schon einmal halb ausgefallen war. **Erzwungen hat
ihn nichts.** Nachgezählt: **keine einzige Testdatei des Prüfstands las
`manifest.json` oder `PANEL_VERSION`** — der Schritt lebte ausschließlich in
einer Aufzählung.

In 0.51.1 fiel er ganz aus. Tag, GitHub-Release und der PROJEKTSTAND-Kopf
standen auf 0.51.1; das ausgelieferte Bauteil meldete sich weiter als 0.51.0.
**Die Folge wäre nicht bloß eine falsche Zahl gewesen:** HACS hätte das Release
installiert, die Integration hätte die alte Version gemeldet, und damit wäre
**nicht erkennbar gewesen, ob das Update überhaupt angekommen ist** — dazu ein
dauerhaft offenes Update in HACS. Gemerkt hat es der Athlet beim Nachfahren,
nicht die Suite.

**Gegen den Tag kann der Prüfstand nichts halten** — den gibt es zur Laufzeit
nicht. **Gegen den Gleichstand der drei Stellen im Arbeitsbaum schon**, und
genau das prüft er seit 0.51.1: `manifest.json` gegen `const.py PANEL_VERSION`
gegen den PROJEKTSTAND-Kopf, dazu die Form. Die Gegenprobe war hier ausnahmsweise
keine Mutation, sondern **der Defekt selbst**: der Wächter meldete beim ersten
Lauf „der PROJEKTSTAND-Kopf und manifest.json stehen auseinander: '0.51.1' statt
'0.51.0'".

**Die Klasse dahinter ist nicht neu, nur neu belegt.** Sechsmal war es eine
handgepflegte Liste ohne Vollständigkeitsprüfung (vierte Bauregel), einmal ein
Suchraum, den niemand benannt hat (siebzehnter Fall), einmal eine Bauregel, die
nur aufgeschrieben ist (sechzehnter Fall). Hier ist es ein **Arbeitsschritt**.
**Regel: jeder Schritt einer verbindlichen Anleitung, der nicht von einer
Prüfung erzwungen wird, ist eine Absichtserklärung.** Und die Reihenfolge dabei
ist nicht beliebig — der Wächter wurde VOR dem Nachziehen der Version gebaut,
damit er den echten Fehler einmal meldet. Ein Wächter, den man erst nach der
Reparatur schreibt, hat nie bewiesen, dass er den Fall findet.

**Und ein zweiter Fehlalarm derselben Art wie in §9.** Der neue Wächter liest
Bauteildateien als Text, und die Hygieneprüfung verlangte daraufhin von
`test_projektstand` einen kalten Bytecode-Cache — sie löste auf die
Zeichenkette `custom_components` aus statt auf das **Laden** eines Bauteils.
`test_projektstand` lädt keines, es fährt Unterprozesse. Auch hier: **verengt,
nicht entschärft** — der Auslöser trifft jetzt `sys.path.insert(` und
`spec_from_file_location`, und eine eigene Zusicherung belegt, dass die alte und
die neue Auslösermenge sich in **genau einer** Datei unterscheiden, nämlich der
mit dem Fehlalarm. Beide Gegenproben (coldcache entfernt, coldcache hinter den
ersten Import geschoben) beißen unverändert.

**Regel: wer zwei verschieden gerechnete Größen vergleicht, bildet die Toleranz
aus dem Unterschied der Rechenwege, nicht aus einer Wunschgenauigkeit.** Die
Empfindlichkeit einer Prüfung ist selbst eine Messgröße — dieselbe Klasse wie
die Dosis der Gegenprobe aus 0.45.0. Bis die Toleranz gemessen ist, sagt die
Karte ausdrücklich, dass die Prüfung auch bei sauberen Ausschnitten anschlägt:
fünf Warnungen sind sonst fünf vermeintliche Fehler.

**Regel: eine Zahl in einem Bericht an den Athleten sagt, woher sie kommt —
Bestand oder Fixture.** Sonst prüft er eine erfundene Zahl gegen eine echte und
findet einen Unterschied, den es nicht gibt.

**Regel: bevor eine Messgröße als untauglich verworfen wird, muss der
Ausschnitt belegt sein, aus dem sie gerechnet wurde.** Ein Ausschluss wirkt
endgültig — er wird nicht wieder aufgerollt, weil niemand eine verworfene Größe
ein zweites Mal prüft. Und der Ausschnitt ist keine Geschmacksfrage: für die
DFA-Auswertung ist er publiziert (zwei Minuten), am eigenen Bestand bestätigt
(der Anlauf endet bei 90–120 s) und damit nachprüfbar statt geraten.

**0.47.1 — zwei Befunde aus der Live-Verifikation von 0.47.0.**

**1 · Die Messung ist nicht die Vorgabe.** Die Kurve liefert P(alpha = 0,75) —
**das IST die aerobe Schwelle.** In 0.47.0 wurde dieser Wert direkt als
Wattvorgabe der Grundlageneinheit eingesetzt. Damit schickte die Karte den
Athleten **auf** die Schwelle, während dieselbe Karte in ihrem eigenen Text
sagt: „durchgehend über 0,75 — wenn er darunter rutscht, bist du zu schnell".

**Der Beleg lag die ganze Zeit in derselben Einheit:** das HF-Fenster der
Grundlage steht bei **88–97 %** der Schwellen-HF, die Wattvorgabe stand bei
**100 %** der Schwellenleistung. Zwei Vorgaben derselben Einheit, die
verschiedene Intensitäten meinen — und niemand hielt sie gegeneinander.

Behoben: die Vorgabe ist ein ANTEIL der gemessenen Schwelle,
`CURVE_TARGET_SHARE = 0,90`. Die Zahl ist keine Hausnummer, sondern die
Vorgabe, mit der in den Durability-Studien gefahren wurde (Stevenson 2022,
Gallo 2024: 90 % der Leistung an der ersten ventilatorischen Schwelle) —
dieselben Arbeiten, aus denen Kurvenform und HF-Korrektur stammen.

**Die Lehre, und sie ist allgemein: eine gemessene Schwelle ist ein BEZUGSPUNKT,
keine Anweisung.** Wo zwei Vorgaben derselben Einheit auf dieselbe Schwelle
zeigen, müssen sie denselben relativen Abstand zu ihr haben. Der Test hält
Watt- und Pulsseite jetzt gegeneinander und prüft, dass der Wattanteil im
HF-Fenster liegt — mit der Gegenprobe, dass 100 % durchfielen.

**2 · Zweimal dieselbe Lehre in drei Runden: am Feld prüfen, nicht am Text.**
Die Vorher-Nachher-Tabelle des Releases rechnete mit FTP **215 W** — dem Wert
aus den Aktivitätsdaten. `_latest_ftp()` liefert **200 W**. Damit war die ganze
Vorher-Spalte falsch, und aus angekündigten „+7 W" wurden tatsächlich +17 W;
aus „−6 W" wurden +8 W. **Keine Vorgabe fiel, alle stiegen.**

Das ist derselbe Fehler wie der FTP-Fund eine Runde zuvor (Befund 0.47.0 unten),
nur eine Ebene später: dort wurde angenommen, WOHER die Zahl kommt, hier, WIE
HOCH sie ist. **Eine Zahl, die eine Ansage an den Athleten trägt, wird an der
Stelle gelesen, an der sie ankommt — nicht an der, an der sie plausibel
aussieht.**

**0.47.0 — ein Befund aus dem Bau von L4.**

**1 · Die Wattvorgaben kamen aus der FTP, nicht aus dem Anker — und beide zeigten
dieselbe Zahl.** Vor dem Bau stand die Frage: gilt künftig die 146 W aus
`coach.anchors` oder die 154 W der Kurve? **Die Frage war falsch gestellt.**
`scaled()` rechnet `blocks_w` aus `ftp * prozent / 100`; der Anker steuert
**keine einzige Wattvorgabe**. Er wird für die Plausibilitätsregel, die
Konfliktwarnung und — über `aerobic_hr` — für die Herzfrequenzfenster benutzt.
Die 146 W der Grundlageneinheit sind 68 % von 215 W.

**Dass beide Wege bei derselben Zahl landen, ist Zufall** — und genau deshalb
ist es niemandem aufgefallen. **Zwei Zahlen, die sich zufällig treffen,
verbergen den Unterschied besser als zwei, die auseinanderliegen:** bei einer
Abweichung fragt jemand nach, bei Gleichstand niemand. Bewegt sich der
Profilwert, springt jede Grundlagenvorgabe mit, ohne dass eine Messung sich
gerührt hätte.

**Ich habe den Fehler selbst festgeschrieben.** Der Rechenweg der Kachel sagte
seit 0.46.0, der Trainer verankere seine Einheiten auf dem Anker-Median. Das
stimmte nie. Der Satz ist korrigiert und nennt jetzt die FTP als die Zahl, die
tatsächlich steuert. **Am Feld prüfen, nicht am Text** — Lehre 1 aus Paket A,
diesmal von mir selbst gerissen, und zwar in einem Text, der erklären sollte,
warum zwei Zahlen auseinanderliegen.

**Nebenbefund, den der Athlet wissen muss:** die Katalogvorgabe für SweetSpot
sind 88 % von 215 W = 189 W; gefahren werden rund 180 W. Gegen die
`icu_rolling_ftp` (193 W) sind das 94 % — die Einheit landet im richtigen
Bereich, **weil sich zwei Fehler aufheben**: überhöhter Profilwert nach oben,
Fahrweise darunter. Ein Wechsel auf die rollende FTP ohne weitere Änderung
ergäbe 170 W und machte die Einheit zu leicht.

**0.46.0 — vier Befunde aus dem Umbau von Paket L.**

**1 · Zwei Kacheln für eine Frage, in zwei Reitern.** `rFatigue` saß im
DFA-Reiter, `rDurability` mit der Entkopplungswolke im Trainer. Beide
beantworteten „wie lange trägt die Grundlage" — mit zwei verschiedenen
Rechnungen, zwei verschiedenen Bildern, und **man bekam sie nicht einmal
nebeneinander zu sehen, um sie zu vergleichen.** Das ist Fehlerklasse 3
(zwei Rechenwege auf dieselbe Frage), aber eine Ebene höher als bisher: nicht
zwei Funktionen, sondern zwei ANSICHTEN. Die Klasse endet nicht am Quelltext.

Seit 0.46.0 sitzt die Kurve in der Durability-Kachel und ersetzt dort die
Wolke. Was mit ihr wegfiel, war ein Bild, das nichts trug: die Trendgerade
durfte ohnehin nicht gezeichnet werden, weil die Steigung nicht von null zu
unterscheiden ist. **Die Verweigerung der Leitzahl steht weiter im Text** —
gegangen ist die Zeichnung, nicht die Aussage.

**2 · Zwei Teile derselben Kachel dürfen verschiedene Achsen haben — wenn beide
begründet sind und der Unterschied benannt ist.** Nach dem Umzug stehen unter
einer Überschrift: die Schwellenleistung über der DAUER und die Entkopplung
über der angesammelten ARBEIT. Das sieht aus wie ein Widerspruch, und die
naheliegende Reaktion wäre, es zu vereinheitlichen. **Sie wäre falsch.** L1 hat
sich gegen die kJ-Achse entschieden, weil die Arbeit an der Intensität hängt
und den Bergeffekt aus Runde 1 zurückholt; Paket F/G hat sich für sie
entschieden, weil der 90-Minuten-Schnitt nicht hielt. Beide Entscheidungen sind
am selben Bestand belegt. **Eine Vereinheitlichung hätte eine davon kassiert,
und zwar stillschweigend** — das wäre schlimmer gewesen als das Problem.

Gebaut sind deshalb drei Abschnitte mit eigenen Überschriften und ein Satz im
Bild, der beide Achsen gegeneinanderstellt. **Ohne den Satz ist es ein
Widerspruch, mit ihm eine Entscheidung.** Er steht dort und nicht nur in der
Spezifikation, damit die nächste Session nicht „vereinheitlicht".

**3 · Der Schutz vor Hochrechnung wurde zur Quelle des Artefakts.** Die
Stundenablesung gibt einen Wert nur aus, wenn alpha 0,75 im tatsächlich
gefahrenen Bereich LIEGT — keine Extrapolation, und das bleibt richtig. Genau
diese Regel erzeugt aber eine AUSWAHL: ausgeruht liegt alpha hoch, die Schwelle
wird in Stunde 1 also nur berührt, wenn härter gefahren wurde. **Stunde 1 steht
damit auf einer systematisch härteren Population als Stunde 2**, und ein Teil
des gemessenen Abfalls ist diese Auswahl und keine Ermüdung.

**Das Erkennungszeichen ist billig und allgemein: n steigt, wo es fallen
müsste.** Am Livebestand trägt Stunde 1 elf Werte und Stunde 2 zwölf — jede
Fahrt mit einer zweiten Stunde hat aber auch eine erste. **Regel, als eine
Zeile im Test:** die Belegung zeitlich aufeinanderfolgender Bins muss monoton
fallen; tut sie es nicht, liegt ein Auswahleffekt vor. Dazu rechnet die Kachel
seit 0.46.0 gepaart — jede Fahrt ihre eigene Kontrolle — und sagt es im
HAUPTBILD, wenn gepaart und ungepaart auseinanderlaufen. Die Verwandtschaft zu
J1 ist eng: dort maß die Messung etwas anderes als behauptet, hier misst sie
zum Teil den Unterschied zwischen Fahrten statt den Verlauf innerhalb einer.

**Und die allgemeine Form, weil uns das wieder begegnet:** eine Regel, die
Werte nur dort ausgibt, wo die gesuchte Größe im gemessenen Bereich liegt, ist
richtig — und erzeugt eine Auswahl, die mit der gesuchten Größe korreliert.
Beides zugleich.

**4 · Eine Karte, die aus einer gekappten Liste zählt, verkleinert die Lücke,
die sie erklären soll.** Die Ausschlussliste der Ermüdungskurve zeigt je Grund
die letzten acht Fahrten. Die Gesamtzahl darüber wurde aus genau diesen
Listen summiert statt aus den Zählfeldern der Payload: bei 45 Fahrten ohne
DFA-Strom und zwei gezeigten hätte dort „von 31 Einheiten" gestanden statt „von
74". Der Fehler fiel nur auf, weil eine Fixture mehr zählte, als sie auflistete.

**Anderswo geprüft, und das Ergebnis ist beruhigend:** die DFA-Tabelle kappt bei
50 Zeilen und nennt daneben `w.kept`, also die Fensterzahl — richtig gebaut, und
sie sagt die Kappung sogar dazu. Der Abgleich-Dialog führt die vollständige
Liste. **Es ist ein Einzelfall, keine Klasse** — aber die richtige Bauart steht
jetzt als Regel in §9, weil der Unterschied zwischen beiden Fassungen von außen
nicht zu sehen ist.

**0.45.0 — fünf Befunde aus dem Bau von Paket L.**

**1 · Eine fehlende Versionsmarke heißt URALT, nicht aktuell.** Der Ausfall vom
06.06.2026 (0,0 bpm über 24 Fenster) wurde von der Mathematik vor 0.9.0
gerechnet. Der Fix kam in 0.9.0, zusammen mit `DFA_ALGO_VERSION = 2` und
`drop_outdated_dfa()` — und erreichte den Wert trotzdem nie. Grund:
`store.async_load` füllt das Grundgerüst auf (`base.update(stored)`), und ein
Archiv aus der Zeit vor der Marke trägt keine. Also blieb der Wert des
Grundgerüsts stehen — der AKTUELLE. Die Migration verglich danach aktuell gegen
aktuell und verwarf nichts.

**Ein Migrationsmechanismus, der beim Laden die aktuelle Marke einsetzt,
deaktiviert sich selbst — und zwar still.** Er meldet keinen Fehler, er findet
nur nie etwas. Dieselbe Klasse wie die 0.35.0-Lücke, eine Ebene höher: dort
wurde ein fehlender Block nie angelegt, hier wurde eine fehlende Marke FALSCH
angelegt.

**Es sind ZWEI Marken, und das ist der eigentliche Befund:** `dfa_version` und
`fields_version`. Die zweite hat denselben Defekt — der Feld-Refetch konnte bei
Altarchiven ebenso nie feuern. Der Wächter hat sie im ALLERERSTEN Lauf gefunden,
genau wie der Vorgabewert-Wächter aus 0.44.0 seine beiden übersehenen
Funktionen. Ein Einzelfall wird zur Klasse, sobald man sie zählt.
`durability_tests.migrate()` macht es seit Paket K richtig — die Marke sitzt IM
RECORD statt obendrauf, wo kein Auffüllen sie erreicht. Die Bauart war im Haus,
nur nicht an dieser Stelle.

**2 · Eine Belegungszahl, die zu einem anderen Wert gehört als zu dem, neben dem
sie steht.** `derive.dfa_summary()` meldete
`"threshold_samples": len(hr_window) or len(watt_window)`. Fällt der Gurt aus,
ist das linke Fenster leer, und das `or` schiebt die WATT-Belegung an die Stelle
der Herzfrequenz-Belegung. Kein falscher Wert — eine falsche Begründung für
einen Wert, und die ist schwerer zu sehen.

**Richtigstellung, nachgetragen am 13.09.2026 nach der Live-Verifikation.** Die
erste Fassung dieses Eintrags behauptete, die Fahrt vom 06.06. habe „24 Fenster
neben einer Schwelle gezeigt, die kein einziges hatte". **Das stimmt nicht.**
Die 24 WAREN Herzfrequenz-Fenster — 24 Nullen, die der Filter vor 0.9.0
mitzählte. Das `or` hat dort gar nicht gegriffen. Neu gerechnet steht die Fahrt
heute auf `hr_windows: 0` und `power_windows: 5`, und **genau dort hätte die
alte Zeile gegriffen**: `0 or 5` hätte die Watt-Zahl neben eine fehlende
Herzfrequenz gestellt. Der Befund ist also richtig, sein Beleg war es nicht —
und ein Beleg, der nicht trägt, macht einen richtigen Befund angreifbar. Seit 0.45.0 zwei
Felder, `hr_windows` und `power_windows`, jedes neben seinem eigenen Wert.

**Und die Prüfung sitzt jetzt am ERGEBNIS statt am Eingang.** `dfa_summary`
filterte jedes einzelne Sample und ließ den Mittelwert am Ende ungeprüft durch —
genau deshalb sah es die Ausfälle nicht, die über die ganze Fahrt gehen: dann
ist jedes Sample für sich schon verworfen, und übrig bleibt ein Mittelwert über
nichts. `derive.threshold_verdict()` ist die eine Stelle, an der das Ergebnis
beurteilt wird; vorher stand diese Regel in FÜNF Fassungen im Haus (vier
verschiedene Grenzen, eine Stelle ganz ohne), weshalb die HF-Kurve im DFA-Reiter
den Ausfall verwarf, während die Leistungskurve zwölf Zeilen darunter dieselbe
Fahrt behielt.

**3 · Der Variabilitätsindex misst Zappeligkeit, nicht Struktur.** Für Paket L
mussten strukturierte Einheiten VOR der Messung ausgeschlossen werden. Der
naheliegende Griff war der VI — er ist da, er ist belegt, er misst
Gleichmäßigkeit. Er trennt nicht:

| Einheit | Intensität | VI | über Zone 2 |
|---|---|---|---|
| SweetSpot 2×20 (24.08.) | 80,0 | 1,0955 | **51,4 %** |
| volumen + SweetSpot 2×15 (20.08.) | 77,7 | **1,0309** | 33,3 % |
| Tempo 2×20 (13.09.) | 77,0 | 1,0694 | 46,0 % |
| VO2max 3×4 (01.09.) | 90,7 | 1,2745 | 38,8 % |
| volumen Rad (30.08.) | 68,8 | **1,0882** | 14,4 % |
| volumen Rad (04.09.) | 60,9 | 1,0738 | 4,4 % |
| volumen Rolle (11.09.) | 61,9 | 1,0000 | 0,0 % |

**Die VI-Bereiche überlappen vollständig** (strukturiert 1,031–1,275 gegen
Grundlage 1,000–1,088): `DURABILITY_VI_NONE = 1,25` hätte ALLE DREI Störer aus
L0 Runde 3 durchgelassen, und die SweetSpot-Fahrt vom 20.08. ist mit 1,0309
gleichmäßiger als jede Ausfahrt draußen. Der Grund ist sachlich: ein
20-Minuten-Block IST sehr gleichmäßig, nur auf einem anderen Niveau. NP/AP
sieht ihn deshalb wie eine ruhige Ausfahrt. Der Anteil der Zeit über Zone 2
trennt mit einer Lücke von 19 Punkten ohne Überlappungsfall — und fängt den
Störer aus Runde 1 mit, weil eine Ausfahrt mit erstem Berg ebenfalls dort steht.
**Zwei Kriterien, zwei Fragen, und keines ersetzt das andere.** Der Satz steht
im Quelltext an der Stelle, wo beide Filter stehen — sonst greift die nächste
Session wieder zum VI, weil er naheliegt.

**4 · Robustheit ist kein Schutz.** Die Gegenprobe zum Ausschluss sollte zeigen,
dass eine strukturierte Einheit den gemessenen Abfall verfälscht. Erste Fassung:
eine Störfahrt unter acht Volumenfahrten — der Median rührte sich nicht, der
Test blieb grün und bewies nichts. Nachgemessen:

| Störer : Grundlage | Abfall Stunde 1 → 2 |
|---|---|
| 1 : 8 | +4,0 W (unverändert) |
| 4 : 8 | +4,0 W (unverändert) |
| **8 : 8** | **+42,0 W** |

**Der Median dämpft, er rettet nicht.** Er hält, bis die Störer die Hälfte
stellen — und bei diesem Athleten stellen sie sie: Rollen-SweetSpots und
VO2max-Einheiten sind hier keine Ausreißer, sondern das halbe Training. **Wer
aus der Dämpfung schließt, der Ausschluss sei entbehrlich, hält Robustheit für
Schutz.**

**Die Lehre über die Gegenprobe selbst, und sie gilt für jede künftige:** eine
Mutation, die den Test nicht bewegt, beweist nicht die Robustheit des Codes,
sondern die Stumpfheit des Tests. **Geprüft wird, AB WELCHER DOSIS sie beißt,
nicht ob sie bei Dosis eins beißt.**

**Nachtrag 0.46.0 — dieselbe Stelle, zum zweiten Mal.** Die Gegenprobe zum
Auswahleffekt (Befund 3 oben) brauchte wieder acht Störfahrten statt vier; mit
vier blieb der Median unbewegt und der Test still. **Die Dosis, bei der eine
Gegenprobe beißt, ist eine Eigenschaft des jeweiligen Verfahrens und muss je
Fixture NEU BESTIMMT werden** — sie lässt sich nicht von der vorigen übernehmen,
auch wenn die Zahl am Ende dieselbe ist. Wer sie überträgt, prüft die Dosis von
gestern an der Regel von heute. Beide Enden stehen jetzt als Zusicherung in
`test_fatigue.py` — auch die Nicht-Bewegung bei 1:8, sonst lernt die nächste
Session die falsche Hälfte.

**5 · Ein Wächter, der je Kachel eingetragen werden muss, schützt nur das, woran
jemand gedacht hat.** Der Quelltext-Wächter aus Paket F läuft global über drei
bekannte Zahlenklassen, im Detail aber je Kachel — und dort stand bis 0.45.0
ausschließlich `rDurability`. Er hat die Durability-Kachel geprüft und wäre an
der Ermüdungskachel vorbeigelaufen, ohne ein Wort zu sagen. Behoben, indem die
Liste der geprüften Kacheln gegen den Quelltext gehalten wird.

**Das ist jetzt drei Mal dieselbe Lösung für dasselbe Muster** — und damit ein
Verfahren statt dreier Einzelfälle:

| Liste | eingeführt | was die Vollständigkeitsprüfung beim ersten Lauf fand |
|---|---|---|
| `JUDGEMENT_FUNCTIONS` (Vorgabewerte) | 0.44.0 | `fatigued_session()` und `scaled()` |
| Versionsmarken in `store.async_load` | 0.45.0 | `fields_version` |
| geprüfte Kacheln im Quelltext-Wächter | 0.45.0 | `rFatigue` |
| `curve` unter den Urteilseingängen | 0.47.0 | die Wattvorgabe fiele sonst stillschweigend auf die FTP zurück |
| Watt- gegen Pulsseite derselben Einheit | 0.47.1 | die Wattvorgabe saß auf der Schwelle, die Pulsvorgabe bei 88–97 % |
| deutsche Zahlwörter für die Dateizahl | 0.44.0–0.48.0 | lief bei der achtzehnten Datei auf `None` — **abgeschafft statt gepflegt**: die Zahl steht als Ziffer da |
| Kachel → Reiter (wo eine Kachel gerendert wird) | 0.48.1 | in 0.46.0 von Hand korrigiert, ohne Zusicherung — die nächste Kachel landete wieder im falschen Reiter. **Eine Korrektur ohne Zusicherung ist keine.** |

**Fünf Mal dieselbe Form in zwei Paketen, und die ZAHL DER FÄLLE ist selbst die
Aussage:** das
ist kein Muster mehr, das man erkennt, sondern eines, mit dem man rechnet. Jede
neue handgepflegte Liste bekommt ihre Vollständigkeitsprüfung mit, bevor sie
zum vierten Mal jemandem auffällt.

**Und der fünfte Fall zeigt den besseren Ausweg: eine Liste, die man abschaffen
kann, ist besser als eine, die man pflegt.** Die Zahlwörter waren nur nötig,
weil die Dateizahl im Einleitungssatz ausgeschrieben stand. Als Ziffer braucht
sie keine Liste, keinen Wächter und keine Pflege. **Vor dem Wächter kommt die
Frage, ob die Liste überhaupt sein muss.**

**Regel: eine von Hand gepflegte Liste braucht eine Prüfung, die das Pflegen
erzwingt.** Ohne sie schützt der Wächter genau bis zum nächsten Fall, an den
jemand gedacht hat — und dass er dann schweigt, ist sein gefährlichster
Zustand. Jede dieser drei Prüfungen hat beim ALLERERSTEN Lauf etwas gefunden;
keine davon war Zierrat.

**6 · Ein Modell außerhalb seines Gültigkeitsbereichs zu strecken erzeugt
Unsinn, auch wenn die Rechnung formal aufgeht.** Das Unsicherheitsband der
Ermüdungskurve sollte die publizierte Streuung des −5-%-Zeitpunkts tragen
(139 ± 78 min). Erste Fassung: die Zeitachse strecken, `f(t · k)` — formal
sauber, und bis zwei Stunden sah es richtig aus. Jenseits des Studienhorizonts
von rund 3,4 h läuft die quadratische Form aus ihrem Gültigkeitsbereich, und die
UNTERE Bandkante stieg über die Kurve. **Eine Unsicherheit, die sich selbst
überholt, ist keine.** Jetzt skaliert die Streuung den VERLUST statt der Zeit;
die Breite wächst monoton von 1,7 W nach einer halben Stunde auf 41,8 W nach
4,5 h. Das ist die Verwandte der J1-Lehre — dort maß die Messung etwas anderes
als behauptet, hier zeigt die Darstellung etwas anderes als gerechnet.

**13.09.2026 — zwei Befunde aus der Vermessung für Paket L, die den Trainer
schon heute betreffen.**

**1 · Ein Schwellenwert, der keine Messung sein kann, zählt trotzdem mit.**
`derive.dfa_summary()` verwirft einzelne Nullwerte — eine Herzfrequenz von 0 ist
ein abgerissenes Gurtsignal und wird pro Sample übersprungen. Was es **nicht**
prüft, ist das Ergebnis: die Fahrt vom 06.06.2026 mit dem sprechenden Namen
„neuer pulsgurt" trägt eine **Schwellen-HF von 0,0 bpm über 24 Fenster** und
geht als vollwertige Messung in die Schwellenreihe ein.

Am ganzen Bestand geprüft (58 Fahrten mit DFA-Auswertung): **genau eine Fahrt**
mit einer unmöglichen Herzfrequenz. Dazu **vier Fahrten mit weniger als zehn
Fenstern**, davon zwei mit **einem einzigen** (03.07.2026 und, außerhalb des
Rads, 09.09.2026) — ein Fenster ist keine Messung, wird aber gleich gewichtet
wie eine Fahrt mit 1.484 Fenstern.

Die Fehlerklasse ist die, die sich durchzieht: **die Prüfung sitzt am Eingang,
nicht am Ergebnis.** Ein Filter, der jedes einzelne Sample kontrolliert und den
Mittelwert am Ende ungeprüft durchlässt, sieht genau die Ausfälle nicht, die
über die ganze Fahrt gehen — denn dann ist jedes Sample für sich schon
verworfen worden und übrig bleibt ein Mittelwert über nichts.

**Regel, verbindlich:** eine Schwellen-HF unterhalb einer physiologischen
Mindestgrenze und eine Schwellenleistung unterhalb einer Mindestgrenze sind
**Ausfälle, keine Messungen**. Sie erscheinen als Ausfall gekennzeichnet, gehen
in keine Mittelung, keinen Median und keine Kurve ein. Dasselbe gilt für eine
Fahrt unterhalb einer Mindestzahl von Fenstern — der Wert wird gezeigt, aber mit
seiner Belegung, und er zieht keinen Median.

**2 · Die DFA-Historie ist 3,5 Monate, das Panel legt 16 nahe.** Von 240
Aktivitäten tragen 58 eine DFA-Auswertung, und alle liegen ab dem 31.05.2026.
Die Kopfzeile zeigt „240 Einheiten · 489 Tage · 58 DFA" und stellt damit die
DFA-Zahl direkt neben einen Zeitraum, für den sie nicht gilt. Das ist keine
fehlende Angabe, sondern eine irreführende Nachbarschaft — Einzelheiten und der
Auftrag stehen in `docs/ausbau.md` unter „Eigener Punkt — der Historienbeginn
gehört sichtbar gemacht".

**0.44.0 — drei Befunde beim Bau von Paket K.**

**1 · Der Vorgabewert ist die Schwester von Fehlerklasse 3.** `websocket_workouts`
hat `recovery_offered` nie an `suggest()` übergeben. Der Vorgabewert `False` ist
stillschweigend eingesprungen, und damit konnte die **Reiz-Stufe auf dem
Trainer-Reiter nie erscheinen** — während die Wochenansicht sie korrekt zeigt,
weil `rate_sessions()` den Wert bekommt.

Das ist nicht Fehlerklasse 3. Dort stehen **zwei Rechenwege** auf dieselbe Frage.
Hier gibt es genau einen, an genau einem Ort: `stage()`. Es gibt nur **zwei
Aufrufer, von denen einer die Frage mit einem Vorgabewert füttert**. Ein
Vorgabewert ist eine zweite Wahrheit in Tarnung, weil er unauffällig richtig
aussieht — es steht ja nichts Falsches da, es steht nur nichts da.

**Was es gekostet hat:** 0.42.0 hat die vierte Stufe eingeführt, eine
Wahrheitstabelle über alle vier Stufen geschrieben und **elf Gegenproben**
gefahren. Keine davon hat gesehen, dass die neue Stufe auf genau dem Reiter, für
den sie gebaut wurde, nicht erscheinen kann. Der Grund ist derselbe bei allen
elf: sie haben `stage()` geprüft, **nicht den Weg dorthin**. Eine Funktion, die
unter allen Eingaben richtig antwortet, sagt nichts darüber, ob sie die richtigen
Eingaben bekommt.

**Die Klassenaussage, und sie ist der eigentliche Befund:** `suggest()` trägt
**neun Urteilseingänge mit Vorgabewert** (`ftp`, `aerobic_hr`, `max_hr`,
`infection`, `budget`, `hard_days_last_7`, `layoff_days`, `goal`,
`recovery_offered`), `rate_sessions()` acht. Nichts zwingt einen Aufrufer, einen
davon zu nennen. Das ist kein Fehler, der passiert ist — das ist ein Fehler, der
**auf seinen Anlass wartet**. Dass es diesmal nur **eine** Stelle war, war
Zufall und keine Eigenschaft des Entwurfs; nachgezählt wurde es mit dem AST, nicht
mit dem Auge. Nach dem Fix fehlt an den Aufrufstellen noch `limit` — eine
Anzeigegrenze, kein Urteilseingang, und deshalb bewusst nicht im Wächter: eine
Prüfung, die Harmloses mitzählt, wird abgeschaltet statt befolgt.

**Lehre: ein Vorgabewert an einem Urteilseingang gehört geprüft wie ein zweiter
Rechenweg.** Der Wächter in `test_websocket_registration` tut zweierlei — jeder
Aufruf nennt jeden Urteilseingang ausdrücklich, **und** die Liste der
Urteilsfunktionen ist vollständig. Ohne den zweiten Teil schützte er genau bis zur
nächsten Funktion mit Vorgabewerten und wäre wieder Einzelfall statt Klasse.

**2 · Eine Regel, die nur in eine Richtung schützt, ist keine Absicherung,
sondern eine halbe.** Die Plausibilitätsregel aus K0 fängt eine Zielleistung, die
**unter** der gemessenen aeroben Schwelle liegt — dann war Termin 1 kein All-out.
Gegen einen zu **hohen** Anker fängt sie nichts: 80 % der aus 215 W abgeleiteten
Schwelle wären 181 W, 35 W über der gemessenen aeroben Schwelle, und die Regel
schwiege dazu.

Die einzige Verteidigung nach oben ist, dass der Anker **gar nicht aus dem
FTP-Feld kommt**. Das ist keine Vorsichtsmaßnahme, sondern die einzige, und
deshalb hat sie eine eigene Gegenprobe: ein Gitter aus **zwei FTP-Werten (215,
260) mal zwei frischen Tests (192 W, 164 W)**. Über die FTP-Spalte darf sich
Zielleistung, Blockdauer, Gesamtdauer und jede einzelne Blockleistung um kein
Watt und keine Minute bewegen; über die Test-Zeile muss alles mitwandern. Dazu
eine Zeile, die ausdrücklich ausschließt, dass der FTP-Weg zufällig dieselbe Zahl
ergibt — ohne sie bestünde der Test auch dann, wenn beide Wege zusammenfielen.

**Die erste Fassung dieser Gegenprobe war stumpf:** sie fiel bei der Mutation nur
über die **Dauer**, nicht über die Zielleistung selbst. Ein FTP-Weg, der zufällig
auf dieselbe Leistung käme, wäre durchgekommen. Geschärft, nicht gelobt — die
Mutation meldet jetzt 26 benannte Fehler statt drei.

**3 · Ein Wächter, den man für einen Sonderfall lockert, ist ab dann keiner
mehr.** Die neue Prüfung „keine Schwelle als Zahl im Protokollteil von
`workouts.py`" hat eine nackte `1000` gemeldet. Sie war eine **Einheitenumrechnung**
(kJ → J), keine Schwelle — die Prüfung hatte sachlich unrecht und formal recht,
denn ein Wächter kann das eine vom anderen nicht unterscheiden. Also ist die Zahl
nach `const.py` aufgelöst worden (`DURABILITY_TEST_WORK_J`), statt die Prüfung um
eine Ausnahme zu erweitern. Siehe §9.

---

**0.43.1 — eine Begründung war zu bescheiden, und das ist auch ein Fehler.**

Die Streckungsregel war in 0.43.0 vollständig als „Angabe des Autors, keine
gemessene Größe" beschriftet. Der wichtigste Teil ist aber **belegt**: Aufwärmen
wird in absoluten Minuten verschrieben (10–15, optimal 15–20, bei Belastungen
über drei Stunden eher 10–15), und zu langes Aufwärmen mindert die Leistung
messbar (J Appl Physiol 2011, „Less is more" — 50 Minuten erzeugten Ermüdung).
Intervalle stehen ebenso absolut. Dass das Einrollen nicht mitwächst, ist damit
kein Geschmacksurteil. **Setzung** ist nur, dass die Differenz vollständig auf
den gleichmäßigen Block geht — was aus dem Belegten folgt, aber selbst nicht
gemessen ist.

Beides steht jetzt getrennt auf der Karte, „Beleg" und „Grenze" in eigenen
Zeilen. **Lehre: eine Setzung als Befund auszugeben ist der bekannte Fehler —
einen Befund als Setzung auszugeben ist derselbe Fehler rückwärts.** Beide Male
kann der Leser nicht mehr unterscheiden, worauf er sich stützen darf. Ein Test
prüft deshalb, dass die beiden Aussagen dastehen UND dass sie nicht im selben
Feld landen.

**0.43.0 — zwei Befunde, beide über Grenzen, die niemand gesetzt hatte.**

1. **`1fr` ist nicht „ein Siebtel".** Der Kalender-Reiter schob sich rechts aus
   dem Bild. `repeat(7, 1fr)` ist `minmax(auto, 1fr)`: die Spalte darf **nicht**
   unter ihre Inhaltsbreite schrumpfen, also setzte ein langer Aktivitätsname
   die Mindestbreite seiner Spalte, und sieben davon sprengten die Zeile. Der
   Fix braucht **drei** Teile — `minmax(0, 1fr)`, `min-width: 0` auf den
   Zellinhalten (Grid- und Flex-Kinder bauen dieselbe Sperre eine Ebene tiefer
   wieder auf), und Kürzung mit `title`, damit der volle Name nicht verloren
   geht. Keiner allein reicht. **Lehre: eine Regel, die nur eine der drei
   Ebenen anfasst, sieht aus wie ein Fix und ist keiner.**
2. **Die Streckung brauchte keine Schwelle, sondern eine Autorenangabe.** Ob
   ein Abschnitt gedehnt werden darf, ist am Block selbst notiert —
   Einrollen, Ausrollen, Intervalle und Pausen fest, gleichmäßige Blöcke
   elastisch. Damit kommt keine neue gemessene Zahl ins Haus, sondern eine
   Aussage dessen, der die Einheit geschrieben hat, und sie ist als solche
   beschriftet. Wo es nichts Elastisches gibt, wird **nicht** gestreckt und
   beide Dauern bleiben sichtbar: eine 40-Minuten-Regenerationsfahrt *ist*
   ihre Dauer.

**Und ein Prüfstandsfund nebenbei:** die erste Fassung des Streckungstests griff
direkt auf `stretched[1][0]` zu. Bei der Gegenprobe — Elastizitätsmarke entfernt
— wurde `stretched` zu `None`, der Test **stürzte ab** und meldete am Ende
nichts. Genau der Fall, vor dem §9 warnt: ein Test, der bei der Mutation
abstürzt, überspringt alles Folgende. Nachgezogen, Gegenprobe wiederholt, 13
benannte Fehler.

**0.42.2 — drei Befunde aus dem aufgeklappten Zustand, alle drei dieselbe Wurzel.**

1. **Zwei Bauarten für dieselbe Sache.** Aufgeklappt war die Wochenansicht eine
   Textwand: kein Segmentbalken, keine Watt- und Pulsbereiche, keine Zweckzeile,
   dafür fünf Absätze Fließtext je Einheit. Die Trainer-Karte kann all das —
   die Wochenansicht hatte nur nie darauf zugegriffen, weil `rate_sessions()`
   einen dünneren Datensatz lieferte. **Eine Karte, die aus weniger gebaut wird,
   wird zwangsläufig dünner.** `_sessionCard()` baut jetzt beide Ansichten,
   `rate_sessions()` liefert dieselben Felder wie `suggest()`.
2. **Dieselbe Warnung dreimal.** Die Zustandswarnung stand an jeder Einheit der
   Woche erneut, im Trainer-Reiter im Einbruchsfall sogar fünfmal. Sie gilt dem
   Zustand, nicht der Einheit. Eine Warnung, die dreimal hintereinander
   dasteht, wird beim dritten Mal nicht gelesen — das ist keine Redundanz,
   sondern Verlust. Gesammelt wird jetzt an einer Stelle; was mehr als eine
   Einheit teilt, steht einmal oben, was nur eine betrifft, bleibt an ihr.
3. **Der Nachweis stand in der Aussagezeile.** „Last 118 · Budget 94
   (Katalogeinheit 72 bei 95 min — auf 2,6 h hochgerechnet)" war als Beleg
   richtig und als Kopfzeile falsch. Die Hochrechnung ist die Herleitung, nicht
   die Aussage: sie gehört in den Rechenweg. **Lehre: eine Zahl muss
   nachweisbar sein, nicht dauerhaft sichtbar.**

**Die gemeinsame Wurzel** ist dieselbe wie bei Fehlerklasse 3: zwei Wege auf
dieselbe Frage, diesmal nicht in der Rechnung, sondern in der Darstellung. Eine
zweite Bauart desselben Objekts driftet genauso auseinander wie eine zweite
Rechenregel — nur merkt man es später, weil nichts falsch wird, sondern nur
ärmer.

**0.42.1 — der Zielblock war seit 0.20.0 beim ersten Aufbau unsichtbar.**

`_boot()` rief `this._render()` direkt. `_need("goal")` hängt aber allein an
`_setTab()`, und `_boot` ist diesen Weg nie gegangen — es holte `status`,
`readiness`, `days`, `load`, `coach`, `day_context` und `workouts` selbst und
rief dann das Rendern. Die Ziel-Payload war die **einzige**, die kein anderer
Pfad besorgt. Ergebnis auf dem Trainer-Reiter beim ersten Aufbau:

| Block | braucht | zeigte |
|---|---|---|
| `rTrainer` | `_coach` | ✅ alles, inklusive Durability-Kachel |
| `rWorkouts` | `_workouts` | ✅ die Einheitenliste |
| `rGoal` | `_goal` | ❌ „Ziel wird geladen …", **dauerhaft** |
| `rPlanWeeks` | `_goal` | ❌ nichts, Leerstring |

**Warum es niemandem auffiel.** Wer irgendeinen Reiter anklickt und zurückgeht,
löst `_setTab("trainer")` aus — und dann ist alles da. Der Fehler traf also nur
den ersten Blick nach jedem Neuladen, und genau dort sah er aus wie ein
langsamer Ladevorgang. Datierung über die Historie: `rPlanWeeks` existiert seit
**0.33.0**, `_need("goal")` hängt seit **0.20.0** an `_setTab`, und `_boot` hat
in keiner Fassung dazwischen `_setTab` gerufen. Der Zielblock war damit seit
0.20.0 auf dem Erstaufbau nicht zu sehen, der Wochenplan seit 0.33.0.

**Der eigentliche Fehler war nicht der Ladepfad, sondern der stille Ausstieg.**
`rPlanWeeks` gab bei fehlender Payload `""` zurück, `rGoal` einen Ladehinweis,
der nie auflöste. Ein Block, der nichts zeichnet, weil seine Daten fehlen, muss
das **sagen** — dieselbe Klasse wie die stille Fensterausweitung aus H2. Seit
0.42.1 trennt `_dataGap()` drei Zustände, und der dritte ist der, den es
vorher nicht gab: *nie angefordert* ist ein Defekt im Panel und wird als
solcher benannt, nicht als leerer Bestand.

**Und die Testlücke, die es durchließ:** die Panel-Tests riefen die Renderer
immer mit vorhandener Fixture auf. Eine Zusicherung lautete sogar wörtlich
`rPlanWeeks(null) === ""` — sie hat den Fehler festgeschrieben statt ihn zu
finden. Sie ist jetzt umgedreht, und ein Wächter prüft, dass `_boot` den Reiter
über `_setTab` aufbaut und jeder gerenderte Reiter seine Payload auf diesem Weg
auch anfordert.

**0.42.0 — was der Bau von Paket I zutage gefördert hat:**

1. **Die Wochenansicht wurde mit der Last einer KÜRZEREN Einheit bewertet — der
   teuerste Fund des Pakets.** Der Plan führt je Einheit einen Schlüssel in den
   Katalog und daneben seine eigene Dauer. Der Katalogeintrag trägt aber eine
   feste Last für eine feste Minutenzahl, und beides fällt auseinander, sobald
   der Plan eine Einheit streckt. Am Livebestand:

   | Einheit | Katalogeintrag | geplant | Last laut Katalog | Last wie geplant |
   |---|---|---|---|---|
   | langer Tag | `z2_90`, 95 min | 4,0 h | **72** | **182** |
   | großer Tag | `z2_210_late`, 210 min | 5,0 h | **175** | **250** |

   Gegen ein Tagesbudget von 200 heißt das: nach Katalog wären **beide** grün,
   tatsächlich fällt der große Tag am Budget. Betroffen war ausgerechnet die
   Einheit, um die es beim Ziel „lange Fahrten" geht, und der Fehler zeigte
   sich nirgends — er machte das Urteil nur systematisch zu freundlich. Seit
   0.42.0 rechnet `workouts.session_load()` die Kataloglast auf die geplante
   Dauer hoch, an einer Stelle, und die Ansicht legt beide Zahlen offen. Der
   Test hält die vier Zahlen oben fest: eine Prüfung, die nur „es wird
   skaliert" behauptet, ginge auch bei Faktor 1,001 durch.

2. **Die Vierstufigkeit hätte eine zweite Regel im Haus erzeugt.** Die
   Zusammenführung von Zustand und Budget stand im FRONTEND (`rWorkouts`:
   `fit === "ok" && fits_budget === false` → Bernstein), während das Backend
   beide Hälften getrennt lieferte. Die vier Stufen ins Backend zu legen und
   das stehen zu lassen wäre Fehlerklasse 3 gewesen — deshalb entscheidet
   `workouts.stage()` einmal und beide Ansichten lesen. Der Schwellen-Wächter
   aus F sah nur `rDurability` und hatte diese Stelle nie geprüft; er deckt
   jetzt beide ab.

3. **Ein Urteil ohne seine Stufe kann das Backend nicht erzeugen — zwei
   Fixtures konnten es doch.** Beim Nachziehen der Panel-Tests fiel auf, dass
   zwei Fälle `fit` auf `"no"` drehten und die grüne Stufe daneben stehen
   ließen; das Panel folgte korrekt der Stufe und die Prüfung fiel. Das ist
   keine Fixture-Panne, sondern eine fehlende Zusicherung: sie steht jetzt als
   Test da, über jeden Zustand und jedes Budget, mit zwei Gegenproben. Sonst
   baut die nächste Session wieder so eine Payload und wundert sich.

4. **Die Spezifikation maß mit zwei Maßen.** I4 verbot das Fragen nach
   kommenden Tagen, weil das System eine solche Angabe nicht prüfen kann — und
   I3 verlangte im selben Atemzug eine Bewertung über acht Wochen. Das
   Lastbudget rechnet aus den letzten sechs Tagen, der Zustand aus den Werten
   von heute. Bewertet wird deshalb nur die laufende Woche; spätere tragen
   einen Satz, der sagt warum. Gefunden beim Lesen, nicht beim Bauen.

5. **Und die Kleinigkeit, die zeigt, dass Gegenproben nicht optional sind:**
   `BLOCKED_BY[...].capitalize()` schrieb den REST des Satzes klein — „Der
   zustand verbietet es heute." Die Prüfung „rot nennt, welches von beiden"
   suchte nach „Zustand" und fiel sofort. Ohne sie wäre es in die Auslieferung
   gegangen.

**0.41.0 — was der Bau von Paket H zutage gefördert hat:**

1. **Die Ausweitung des Bezugsfensters wäre STILL passiert.** Im Panel stand
   `p.widened` statt `p.recent.widened` — das Feld liegt eine Ebene tiefer, der
   Ausdruck war damit immer `undefined`, also immer falsch. Ausgerechnet H2
   schreibt vor: „wird der Bezug ausgeweitet und der Zeitraum genannt — **nie
   still**." Gefunden von einer der neuen Gegenproben, nicht von Hand.
   **Und das Gefährliche daran ist nicht, dass der Fall selten ist, sondern
   dass er selten ist:** aufgefallen wäre er erst nach 30 Tagen ohne
   qualifizierte Fahrt — also genau dann, wenn der Athlet lange nicht gefahren
   ist und den Satz zum ersten Mal wirklich liest. Ein Fehler, der nur im
   seltenen Fall zuschlägt, ist schlimmer als einer, der immer zuschlägt: der
   zweite wird sofort gemeldet.

2. **Zwei verschiedene Fehler wären am eigenen Livebestand beide unsichtbar
   geblieben — die Zufalls-Lehre in ihrer schärfsten Form.** Der Kopf der Kachel
   nennt die *längste* Fahrt (nach Zeit) mit *deren eigener* Leistung. Am Archiv
   vom 13.09.2026 gilt zufällig beides:

   | Größe | Wert | Womit sie zusammenfällt |
   |---|---|---|
   | längste Fahrt nach Zeit | 260 min, 08.08.2026 | ist **dieselbe Fahrt** wie die arbeitsreichste (2.153 kJ) |
   | Leistung dieser Fahrt | 136 W | ist **genau** der Pool-Median aus `_conversion_power()` (136 W) |

   Wer im Kopf versehentlich nach Arbeit sortiert oder versehentlich den
   Pool-Median druckt, bekommt an diesen Daten **dieselbe Ausgabe**. Eine aus dem
   Livebestand abgeleitete Fixture hätte keinen der beiden Fehler finden können.
   **Die Regel:** an einem Bestand, in dem zwei Größen zufällig zusammenfallen,
   prüft kein Test die Unterscheidung — wer eine Fixture aus Livedaten ableitet,
   muss die Größen, die auseinandergehalten werden sollen, **absichtlich
   auseinanderziehen**. Das ist Muster 2 aus Paket A („eine Prüfung ist erst eine
   Prüfung, wenn die Fixture die Fälle unterscheidbar macht"), zweimal in einer
   einzigen Kachel. Beide Fälle liegen jetzt erzwungen in der Fixture: eine lange
   leichte gegen eine kurze arbeitsreiche Fahrt, und eine Kopf-Wattzahl abseits
   des Pool-Medians.

3. **Neue Tests stürzen ab, statt zu zählen — zum dritten Mal, also ein Muster
   und keine Panne.** Zwei der elf Gegenproben (Dauer/Leistung aus der Payload
   entfernt; Kopfbereich ganz entfernt) brachten den Prüfstand mit `KeyError`
   bzw. einem `null`-Regex-Treffer zum Absturz. Ein abgestürzter Test überspringt
   alles Folgende und meldet am Ende „0 Fehler" — dieselbe Klasse wie der
   Zählfehler aus 0.35.0 und die nicht beißende Gegenprobe aus 0.38.0.
   **Zwei Bauregeln daraus, ab sofort für jeden neuen Test:**
   - **Feldzugriffe im Testcode gehen über `.get()` / `?.`, nie über `[]`** —
     ein fehlendes Feld ist genau das, was die Mutation herstellt, und es muss
     als gezählter, benannter Fehler erscheinen.
   - **Jeder Regex-Treffer wird auf `null` geprüft, bevor auf `[0]` zugegriffen
     wird**, und das Fehlen bekommt eine eigene benannte Prüfung.

   Beide Tests wurden danach nachgeschärft und die Mutationen wiederholt: 24
   bzw. 17 gezählte, benannte Fehler.

4. **Die eigene Erklärung hätte den eigenen Wächter gerissen.** Der Text zu den
   Grenzen der Progressionsregel soll „die 10 % sind der gemessene Risikoknick"
   sagen, und der Rundungsschritt „auf fünf Minuten". Beides sind Literale im
   Frontend, also genau das, was der F-Wächter verbietet. Der richtige Zug ist
   nicht, den Wächter zu umgehen, sondern die Zahlen dorthin zu schaffen, wo sie
   hingehören: der Prozentsatz wird als `(Faktor − 1) × 100` aus der Payload
   gerechnet, der Rundungsschritt kommt aus `const.py`, und gerundet wird im
   Backend. Der Wächter wurde dabei um vier Muster erweitert — eines davon
   (`\b30\b`) war zunächst zu stumpf und traf den unbeteiligten Satz „die letzten
   30–60 min" aus G5: **ein Wächter muss die Klasse treffen, nicht die Ziffer.**

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

**Zweiundzwanzigster Fall (0.52.0, in der eigenen Arbeit gefunden): ein
Zustand, der gebaut ist und von nichts geprüft wird, ist am lebenden System von
einem fehlenden nicht zu unterscheiden.** Die Kachel der Zuordnung zeigte den
Zustand „markiert, noch nicht gemessen" von Anfang an — P2b verlangt ihn, und er
war da. **Keine einzige Prüfung hat ihn angefasst.** Gemerkt wurde es erst, als
der Athlet vor der Auslieferung nachfragte, ob er überhaupt sehen kann, dass
sein Haken angekommen ist.

Das ist nicht dieselbe Klasse wie ein fehlendes Feld, sondern eine eigene: der
Code war richtig, der Prüfstand war blind, und die Lücke wäre **erst am
lebenden System** aufgefallen — dort, wo Nachbessern am teuersten ist. Ein
Bericht, der aufzählt, was gebaut wurde, deckt sie zu; erst die Frage „woran
sehe ich das?" hat sie geöffnet.

Beim Nachsehen fiel zugleich der zweite Mangel auf, und der gehört zur alten
Klasse: **derselbe Satz stand doppelt da**, einmal als Text im Frontend
(„Noch nicht gemessen.") und einmal als Grund aus der Payload („Markiert, noch
nicht gemessen — …"). Zwei Wahrheiten für einen Text, fünfte Bauregel. Jetzt
kommt der Satz einmal und aus der Payload, und die Kachel nennt daneben, was
wirklich im Archiv steht: Zahl der Marken, Zahl der Familien, Setzdatum.

**Die Regel daraus:** eine Zustandsanzeige, die ein Bauteil verspricht, gilt
erst als gebaut, wenn eine Prüfung sie an einer gegenprobten Fixture SIEHT. „Es
steht im Code" ist keine Auslieferung.

### Die drei Fehlerklassen, die sich durchziehen

1. **Falsche Quelle statt falscher Anzeige.** FTP, Tageslast — beide standen in den Daten und
   wurden am falschen Ort gesucht. **Lehre: bei „X erscheint nicht" zuerst prüfen, ob die
   Quelle ankommt.** Das hat einen ganzen Nachmittag gekostet.
2. **Tests, die nur ein Ziel messen.** Die Rundenkurven waren „grün" mit Amplitude 1 px. Ein
   Test muss beide Ziele prüfen — vergleichbar *und* lesbar.
3. **Zwei Rechenwege auf dieselbe Frage.** Zustandsbänder gegen Trainerurteil (0.11.0),
   Empfehlungsblock gegen Einheitenliste (0.27.0). Beide Male: eine Quelle, ein Weg.
4. **Der stille Ausstieg.** Ein Block, der nichts zeichnet, weil seine Daten fehlen, sieht aus
   wie einer, dessen Daten leer sind — und ein Ladehinweis, der nie auflöst, sieht aus wie ein
   langsames Netz. Die stille Fensterausweitung (0.41.0) und der nie geholte Zielblock (0.42.1)
   sind derselbe Fehler in zwei Gewändern. **Lehre: was nicht passiert ist, muss dastehen.**
   Und eine Zusicherung der Form „ohne Daten kein Abschnitt" schreibt diesen Fehler fest,
   statt ihn zu finden.

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

**20 Dateien, 6.167 gezählte Einzelprüfungen, alle grün.** Kein Test braucht eine laufende
HA-Instanz oder einen Browser.

| Datei | prüft | Umfang |
|---|---|---|
| `test_derive.py` | Parselogik gegen echte Payloads | 44 |
| `test_dfa.py` | DFA-Auswertung, Bandgrenzen, Artefakte, **die Plausibilitätsregel: Ausfall gegen Messung, Belegung je Wert getrennt, die alte `or`-Formel als Gegenprobe** | 44 |
| `test_import.py` | vollständiger Import gegen einen Nachbau des Kontos, Schwellenreihe und `since`, day_context-Migration und Schreibweg, Quellenblock-Auflagen, **der Versionsmarken-Wächter mit Gegenprobe über eine dritte Marke, der Historienbeginn getrennt vom Bestandszeitraum** | 120 |
| `test_analytics.py` | Trainingsmetriken gegen bekannte Ergebnisse, Ebene-3-Wächter (Last kennt keine Etiketten, Quelltext und Verhalten), **die Wochenbilanz aus dem Archiv — Abgrenzung, und dass nichts gepaart wird** | 108 |
| `test_setup_simulation.py` | Entity-Aufbau, Übersetzungen, unique_ids | 22 |
| `test_laps.py` | Runden-Normalisierung | 34 |
| `test_coach.py` | Zustandsregeln, Trigger-Schärfung, Infektverlauf, Nachtreaktion, Einordnung, Bereiche, benannter 42-Tage-Verlauf, Basislinien-Primitive mit AST-Wächter, eingefrorene No-op-Referenz, gewichtete Basislinie mit Fixture-Beweis, **Durability: die drei Ehrlichkeitsregeln einzeln, Gewichtungs- und Umrechnungs-Gegenprobe, Blockverlauf; der Kopf: belegte Dauer am gesperrten Fall, längste ≠ arbeitsreichste und Fahrt-Watt ≠ Pool-Median je erzwungen, Fensterausweitung mit Gegenfall, Progressionsfaktor mit 1,0-Gegenprobe**; **die Erholungs-Setzung hinter der Reiz-Stufe** | 423 |
| `test_plan.py` | Zielprofil, Wochenmuster, Zeitbudget, Progressions- und Kalender-Anker-Vertrag, Profil-Migration | 405 |
| `test_workouts.py` | Einheitenauswahl, HF-Klemme, Infektleiter, Wattumrechnung, Intervals-Syntax, **die vier Stufen über die volle Wahrheitstabelle, rot mit Begründung welches von beiden, dieselbe Einheit über alle vier Stufen, die Lastskalierung an den Zahlen des Livebestands, eine Zustandsregel für beide Ansichten, kein Urteil ohne Stufe**; **die Staffelung aus der Kurve: gepaarte Reihe, Studienform darüber, Ein- und Ausrollen bleiben FTP, harte Familien unberührt**; **die Vorgabe ist ein Anteil der Schwelle, nicht die Schwelle — Watt- und Pulsseite gegeneinander gehalten** ; **Watt und Puls der harten Familien aus DERSELBEN Quelle, mit dem umgeschriebenen Gleichstandstest: fällt eine Seite auf die FTP zurück, muss die andere mitfallen**; **seit 0.51.0 die Quellenkette je Familie als EINE Tabelle: Rangfolge am Ergebnis von `scaled()` erzwungen, jede Stufe beschriftet einschließlich des Rückfalls, der Gleichstand über den Stufentest hinweg, und der LEERZUSTAND Zahl für Zahl — ohne markierten Test entscheidet die Kette wie zuvor** | 1656 |
| `test_websocket_registration.py` | Registrierung, Dekoratoren, FTP-Quelle, eine Ankerregel, day_context-Lese/Schreibweg, Ampel-Herkunftsnotiz, **der goal-Handler verdrahtet nur und bewertet ausschließlich die laufende Woche**; **`blocks` gehört zu den Payloads, ohne die eine Vorgabe still zurückfällt**; **seit P3 die drei Zuordnungswege samt FEHLERPFAD: in keinem Fehlerzweig des Schreibwegs wird geschrieben oder gespeichert, jeder bricht ab — am Syntaxbaum geprüft und mit eingebautem Schreibvorgang gegengeprobt; die Rücknahme holt keine Abschnitte; Familien und Driftsätze kommen aus dem Modul** | 414 |
| `test_reconcile.py` | Abgleich mit Intervals: die drei Sperren einzeln, die datumslosen Aufräumstellen, No-op ohne Speichervorgang, der Handler am echten Aufruf (Import läuft, Historie nie geholt, Zwischenstand) | 130 |
| `test_fatigue.py` | die Ermüdungskurve: strukturierte Einheiten VOR der Messung ausgeschlossen — mit der Gegenprobe, dass sie den Abfall von +4,0 auf +42,0 W verfälschen, wenn man sie drin lässt; Bereichsgrenzen aus der Belegung an zwei Beständen; Anker gemessen gegen Form gesetzt; **L1b: die HF-Setzung skaliert am eigenen Anker**; **die gepaarte Gegenrechnung und das Erkennungszeichen: die Belegung steigt, wo sie fallen müsste — mit Gegenprobe am sauberen Bestand**; **p050 wird erhoben und von nichts benutzt, mit Quelltext-Wächter über alle Verbraucher** | 54 |
| `test_blocks.py` | ein Wert je Block: der Anlauf wird verworfen (mit der Gegenprobe am 4-Minuten-Block, wo auch der Median kippt), der echte Median gegen die Index-Bildung, der Regelkreis nach oben wie nach unten mit familieneigener Schrittgrenze, Steuergröße Median gegen Verlaufsgröße erster Block, Belegungsgrenze für die Linie; **die Physik-Gegenprobe an den echten Lap-Grenzen (Arbeit trägt mehr als die Pause daneben) mit dem Sekunden-Fehler als Gegenfall, und die fremde Gegenprobe gegen Intervals' eigenen Abschnittswert** | 66 |
| `test_suite_hygiene.py` | der Prüfstand prüft sich selbst: **genau eine** Summary je Datei, die etwas zählt, nichts Gezähltes dahinter, Fehler werden gedruckt; **seit 0.51.0 der kalte Bytecode-Cache — Import vorhanden, VOR dem ersten Bauteil-Import, und das Verzeichnis nicht fest, jedes mit Gegenprobe**; **der Doppelwächter über jedes Bauteil — zwei Definitionen desselben Namens sind ein zu weit gegangener Schnitt, und die letzte gewinnt** | 153 |
| `test_panel_views.js` | alle Ansichten gegen volle, leere, löchrige, entartete Daten; Zeitfenster, Brushing, Achsenregel; Tagesbeschriftung und Abgleich-Dialog mit Schreibweg und Scroll-Erhalt; **die Durability-Wolke: Gewicht als Größe und Deckkraft, Gerade nur bei gesicherter Steigung, Register getrennt; der Kopf: drei Zeilen, weder Urteils- noch Datenregister, Rückfall-Satz und Ausweitungshinweis je mit Gegenfall**; **der Wochenplan: Stufen nur in der laufenden Woche, Satz statt Stufe ab Woche zwei, gefahren gegen vorgesehen ohne Paarung, Legende und Quellenblock**; **der Historienbeginn: eigener DFA-Zeitraum in Kopfzeile und Reiter, mit Gegenfall und leerer Payload**; **die Ermüdungskurve: Beleg und Setzung im Bild und im Text getrennt, beide Leserichtungen, die namentliche Ausschlussliste, der Zustand „rechnet noch" mit Fortschritt**; **L1b als Setzung beschriftet, mit der eigenen Messung daneben**; **der Umzug in die Durability-Kachel: die Ehrlichkeitsregel übertragen, die Ausschlusszahl aus dem Zählfeld statt aus der gekappten Liste**; **die tauben Abschnitte klappen zu, und die Datenlage öffnet sie wieder — mit beiden Öffnungsbedingungen einzeln**; **die Einheitenkarte nennt die Herkunft je Abschnitt — gemessen, Studienform oder Rückfall auf die FTP; **die Herkunft an der Einheit samt Rolle-Grenze, und der Rückfall-Hinweis nur dort, wo gemessen werden soll**; **die Blockmessung: der Widerspruch der fremden Gegenprobe wird als Hinweis und nicht als Fehler beschriftet, Leitzahl erster Block, Steuerung auf ihren Einzelwerten sichtbar, Belegung mit Gegenfall, die Rolle-Grenze**; **0.50.0: der Kopf der Durability-Kachel ist fort und der Rechenweg sagt, wohin — die Progressionszeile in den Wochenplan, die längste Fahrt ersatzlos; die doppelte Wertetabelle aufgelöst, die Bandbreite als SPANNE in der Leiste** | 1338 |
| `test_panel_fixes.js` | je ein Nachweis pro behobenem Fehler, plus die Zeiger-Simulation; Quelltext-Wächter über das ganze Frontend, beidseitig (keine Zahl im Quelltext, jede Schwelle nachweislich aus der Payload), seit 0.41.0 auch über Progressionsfaktor, Risikoknick, Rundungsschritt und Bezugsfenster, **seit 0.42.0 über `rWorkouts` UND `rPlanWeeks` (keine Urteilsregel im Frontend) plus den Wortabgleich Fixture gegen `workouts.py`**, **seit 0.45.0 über `rFatigue` samt Rechenweg-Helfer — je Kachel nachzutragen, deshalb mit Existenzprüfung der Liste**; **der Zeiger über der Ermüdungskurve am simulierten Ereignis, und der eine Ladeweg für ihre Payload**; **`rBlocks` unter demselben Wächter**; **die Zuordnung Kachel → Reiter, vollständig und mit Gegenprobe**; **seit 0.50.0 die Zeigerlogik als EINE Mechanik mit ZWEI zugesicherten Verhaltensweisen: die Leitzahl folgt in der Ermüdungskachel und bleibt in den Block-Karten stehen, beides am simulierten `pointermove`; der Wächter über `rPlanWeeks`, dem die Progressionszahlen gefolgt sind**; **die Zuordnung am simulierten Klick: der Haken schickt den `start_index` und nicht die laufende Nummer, der gesetzte Haken nimmt zurück, ein zweiter Klick während des Schreibens fällt aus, die drei Fehlergründe kommen im Klartext an und die Scroll-Lage überlebt sie; **die Quittung: die Kachel nennt Zahl der Marken, Familien und Setzdatum aus dem Archiv, der Grund kommt EINMAL und aus der Payload — mit der nie markierten Fahrt als Gegenprobe**; **EIN Abschnitt ist kein Mangel: kein Unterteilen-Hinweis, kein Mangelwort, „die ganze Fahrt“ statt „1 Abschnitt“ — mit der vierrundigen Fahrt als Gegenprobe**; **die Markenspalte am gerenderten `rAkt`, Zeile für Zeile: die Kürzel in IHRER Zeile, leer heißt unberührt, der Messzustand blass UND in Worten, kein Driftzeichen — mit der leeren Payload als Gegenprobe** | 602 |
| `test_panel_design.js` | Gestaltungsregeln als Zusicherung, Auswahl als Form, Achse im Aufklappen, Etiketten im Kategorienregister; **eingefrorene `chart()`-Referenz aus dem Stand vor dem Eingriff** und der Zeiger-Unverändert-Beweis über vier Ansichten; **vier Urteilsfarben, vier Formen, der Reiz-Ton in keinem Kategorienregister, die Reiz-Form kein Last-Blitz**; **die sechs Zuordnungs-Familien: eigene Form UND eigenes Kürzel je Familie, keine Urteilsfarbe, keine Kreisgrundform des Urteilsregisters, paarweise verschieden — mit eingebauter Dublette als Gegenprobe** | 309 |
| `test_ramp.py` | die Stufentest-Auswertung: die Segmentregel (letzter Hochpunkt vor dem Abfall, Ende erst nach gehaltener Flachstrecke), die Gerade durch den Abfall statt einer Ablesung, die drei Zahlen, **kein Hochrechnen über das Segment hinaus — mit dem konvexen Abfall, bei dem die Gerade 0,5 schneidet und die Messung nie dort war**, die Erholung im Ausrollen; jede Setzung mit einer Fixture, die genau sie trifft | 89 |
| `test_section_marks.py` | die Zuordnung Abschnitt → Familie: **der Schlüssel ist `start_index` und nicht die laufende Nummer — an einer Fahrt, bei der ein Lap durch `dfa_blocks` fällt, mit der naiven Zuordnung als Gegenprobe**; die zwei J7-Auflagen einzeln samt eingefrorener No-op-Referenz; ältere Messmarke verliert die Stunden und behält Marken und Anker; die Rücknahme auf der EINZELNEN Marke, und mit der letzten fällt der Eintrag bit-identisch; **der Haken misst NICHT — mit eingebautem implizitem Messpfad, an dem dieselbe Zusicherung fällt**; die Drift meldet statt zu rechnen, und Bestätigen ist ein Knopf; die Rücknahme braucht weder Laps noch Datum | 83 |
| `test_projektstand.py` | die Tabelle unter diesem Absatz gegen einen echten Suite-Lauf: jede Zeile einzeln, Dateien ohne gemeldete Zahl, Kopfzeile und Einleitungssatz; **die eigene Zeile gegen den eigenen Zähler** | 73 |

**Das Prinzip:** Ein Test, der den alten Fehler nicht nachweislich findet, ist kein Test. Bei
den kritischen Fixes wurde der Fix zurückgedreht und geprüft, dass der Test fehlschlägt —
und zwar **gezählt und benannt**: ein Test, der bei der Mutation abstürzt, überspringt alles
Folgende und meldet am Ende „0 Fehler".
Diese Gegenproben haben mehrfach gezeigt, dass ein Test *nicht* scharf war — dann wurde er
geschärft, nicht der Code gelobt.

**Zwei Bauregeln für neue Tests, aus 0.41.0 (§7 Punkt 3):** Feldzugriffe im Testcode gehen über
`.get()` / `?.`, nie über `[]` — ein fehlendes Feld ist genau das, was eine Mutation herstellt.
Und jeder Regex-Treffer wird auf `null` geprüft, bevor auf `[0]` zugegriffen wird, mit einer
eigenen benannten Prüfung für das Fehlen. Ohne beides stürzt der Test bei der Mutation ab, statt
sie zu zählen.

**Regel über Wächter selbst (0.51.1): ein Wächter, der bei RICHTIGEM Text
anschlägt, wird abgeschaltet statt befolgt.** Die Zahlenprüfung des
Stufentest-Katalogeintrags durchsuchte per Textsuche alles bis
`LIBRARY.append` — also auch die Beschreibung und die Kommentare — und meldete
den völlig richtigen Satz „im Fenster 0 bis 10 Minuten" als verbotene Zahl. Der
Ausweg ist **verengen, nicht entschärfen**: sie trifft jetzt über den AST genau
das Dict, trägt eine eigene Prüfung, dass sie den richtigen Abschnitt sieht, und
ihre Gegenproben beißen unverändert. Derselbe Gedanke steht seit 0.44.0 am
Kommentar von `JUDGEMENT_INPUTS` — ab hier gilt er als Regel für jeden Wächter.

**Wofür die §9-Tabelle da ist, an einer einzigen Zahl.** In 0.51.1 ist
`test_coach` **zweimal** von 424 auf 423 gefallen, an derselben Schleife (sie
zählt eine Prüfung je Einheit **mit** Pulsfenster). Beim **ersten** Mal war es
ein Fehler: ein zu früher `return` in `scaled()` nahm dem Stufentest sein
Fenster **still** — also eine Entscheidung, die niemand getroffen hatte. Beim
**zweiten** Mal war es die Folge genau dieser Entscheidung (§7, zwanzigster
Fall). **Eine Zahl, die sich ändert, ohne dass jemand es wollte, ist ein
Befund** — und die Tabelle ist die Stelle, an der man den Unterschied überhaupt
bemerkt. Wer sie bei einer Abweichung nachzieht, statt ihr nachzugehen, schaltet
den einzigen Melder ab, der beide Fälle sichtbar macht.

**Beide sind bis heute NUR AUFGESCHRIEBEN — kein Wächter erzwingt sie** (§7, sechzehnter Fall).
`test_ramp.py` verletzt die erste an 41 Stellen, und eine Mutation stürzt dort ab, statt
gezählt zu werden. Gesehen wird das nur mittelbar, über den §9-Wächter, der die Datei als
Unterprozess fährt und „meldet keine Zahl" zurückgibt: ein Rauchmelder im Flur, kein
Feuerlöscher am Herd. Der Umbau steht in §10 mit seinen Zahlen; er gehört nicht in ein
Auslieferungs-Release.

**Dritte Bauregel, aus 0.44.0: wer einen Wächter für einen Sonderfall lockert, hat ab dann
keinen mehr.** Die Prüfung „keine Schwelle als Zahl im Protokollteil von `workouts.py`" meldete
eine nackte `1000`. Die war eine **Einheitenumrechnung** (kJ → J) und keine Schwelle — die Prüfung
hatte also sachlich unrecht. Sie hatte trotzdem recht, denn ein Wächter kann eine Umrechnung von
einer Schwelle nicht unterscheiden, und die Ausnahme, die man ihm dafür beibringt, gilt ab dann
für jede Zahl, die sich als Umrechnung ausgibt. **Die Zahl wird aufgelöst, nicht die Prüfung
aufgeweicht** — `DURABILITY_TEST_WORK_J` steht jetzt in `const.py`, direkt neben der Größe in kJ,
mit dem Grund daneben.

**Zehnte Bauregel, aus 0.51.0: am Syntaxbaum schneiden, nicht am Zeilenbild — und was
dabei kaputtgeht, fällt laut auf.** „Bis zur nächsten nicht eingerückten Zeile" taugt als
Schnittregel nicht, weil mehrzeilige Zeichenketten Zeilen am Spaltenanfang enthalten (§7,
fünfzehnter Fall). **Der Schnitt selbst ist vom Prüfstand aus nicht erzwingbar** — er
passiert im Werkzeug der Sitzung, nicht im Bestand; erzwingbar ist sein SCHADEN, und der hat
eine eindeutige Form. Der Wächter in `test_suite_hygiene` hält jedes Bauteil gegen seinen
eigenen Syntaxbaum und lässt keine zwei Definitionen desselben Namens auf oberster Ebene
durch. Das ist wichtig, weil bei einer Doppeldefinition **die letzte gewinnt** und die Suite
sonst grün bliebe. Am echten Schadensfall gegengeprüft: Datei aufgebläht, Wächter meldet
Namen und beide Zeilennummern. **Wer schneidet, nennt trotzdem die erwartete
Größenänderung** — der Wächter fängt den Schaden, nicht den Fehler.

**Neunte Bauregel, aus 0.51.0: eine Gegenprobe läuft mit KALTEM Bytecode-Cache — erzwungen,
nicht aufgeschrieben.** Python invalidiert eine `.pyc` über mtime und Größe der Quelle; eine
Mutation, die gleich lang ist und in derselben Sekunde geschrieben wird, sieht damit wie keine
Änderung aus (§7, zwölfter Fall). `python3 -B` hilft nicht — es verhindert nur das Schreiben.
**Gewählt ist ein frischer `sys.pycache_prefix` je Lauf und nicht das Löschen von
`__pycache__`:** löschen muss jemand VOR jedem Lauf an jeder Aufrufstelle, und eine
handgepflegte Regel schützt in diesem Projekt nachweislich bis zum nächsten Mal, an dem
niemand daran denkt. Ein frisches Verzeichnis ist **kalt von Bauart** — es gibt nichts zu
invalidieren, die Länge der Mutation spielt keine Rolle und die Sekunde auch nicht, und es
löscht nichts (ein `rm -rf` mit falschem Pfad ist ein eigenes Risiko). Umgesetzt in
`tests/coldcache.py`, importiert als erste Zeile jeder Testdatei, die ein Bauteil lädt.
**Der Wächter in `test_suite_hygiene` erzwingt es** und prüft drei Dinge einzeln: dass der
Import da ist, dass er VOR dem ersten Bauteil-Import steht (dahinter wäre er wirkungslos),
und dass das Verzeichnis nicht fest ist (sonst ist es beim zweiten Lauf nicht mehr kalt).

**Achte Bauregel, aus 0.50.0: ein Gegenfall weist nach, dass er etwas verändert hat.** Wer
einen Wert filtert, eine Zahl entfernt oder einen Schlüssel `pop`t, prüft zuerst, dass der
Bestand vorher anders war — sonst läuft die Gegenprobe am Originalzustand und besteht dabei.
Der Fall aus §7 kostete nichts, weil er auffiel; er wäre nicht aufgefallen, wenn die Mutation
nur beinahe getroffen hätte. **Das gilt für die Sitzungsarbeit genauso wie für den Prüfstand:
vor jeder zurückgedrehten Zeile steht eine Zusicherung, dass die Ersetzung gegriffen hat.**

**Siebte Bauregel, aus 0.48.1: ein Ausschnitt aus einem Strom braucht eine Plausibilitätsprüfung
gegen die erwartete Physik.** Ein Abschnitt, der als Arbeit etikettiert ist, muss mehr Leistung
tragen als die Pause daneben. Der Fehler aus 0.48.0 war in den Daten sofort sichtbar — 88 W
Arbeit gegen 253 W Pause —, nur sah niemand hin, weil kein Test danach fragte. Die Prüfung steht
jetzt in `test_blocks.py`, mit dem Sekunden-Fehler als Gegenfall.

**Sechste Bauregel, aus 0.46.0: eine Anzeige, die eine gekürzte Liste zeigt, zählt aus dem
ZÄHLFELD, nie aus der Liste.** Die Liste darf gekappt sein, die Zahl daneben nie — sonst
verkleinert die Karte genau die Lücke, die sie erklären soll (§7). Die DFA-Tabelle macht es
richtig vor: 50 Zeilen gezeigt, die Gesamtzahl aus der Fensterzählung, und die Kappung
ausdrücklich benannt.

**Fünfte Bauregel, aus 0.45.0: ein Erklärtext, der eine Schwelle nennt, nennt sie AUS DER
PAYLOAD oder gar nicht.** Drei Mal hat inzwischen ein Wächter die eigene Begründung gerissen:
beim F-Wächter, bei den 80 g/h und zuletzt an dem Satz, der erklärt, warum die Ermüdungskachel
nicht behaupten darf, nach Andriolos Verfahren gerechnet zu haben. Jedes Mal hatte die Prüfung
sachlich unrecht und in der Sache recht — ein Wächter kann eine Erklärung nicht von einer
Behauptung unterscheiden. Statt sich weiter überraschen zu lassen: der Erklärtext holt seine
Zahl aus derselben Payload wie die Anzeige, oder er nennt keine. **Das macht die Regel zur
Bauvorschrift statt zur wiederkehrenden Überraschung** — und es gilt in beide Richtungen, denn
ein Erklärtext, der seine Zahl aus der Payload zieht, bleibt auch dann richtig, wenn die
Schwelle sich ändert.

**Vierte Bauregel: ein Wächter über eine handgepflegte Liste braucht eine Prüfung, die das
Pflegen erzwingt.** Der Vorgabewert-Wächter (§7) führt `JUDGEMENT_FUNCTIONS` von Hand — und
prüft zugleich, dass **keine** Funktion in `workouts.py` Vorgabewerte für Urteilseingaben trägt,
ohne darin zu stehen. Dass das kein Zierrat ist, hat der **allererste Lauf** gezeigt: er meldete
sofort zwei übersehene Funktionen, `fatigued_session()` — die in derselben Sitzung geschriebene —
und `scaled()`. Eine Liste ohne Vollständigkeitsprüfung schützt genau bis zur nächsten Funktion.

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
5. **Die erste Bauregel aus 0.41.0 ist nicht erzwungen** (§7, sechzehnter Fall). Feldzugriffe
   im Testcode sollen über `.get()` laufen; geprüft wird es nirgends. Stand 0.51.0:
   **41** lesende `[]`-Zugriffe in `test_ramp.py`, alle auf Bauteil-Payloads, und
   **1.633** über alle Python-Testdateien zusammen; die JS-Seite ist sauber (2 Stellen, und
   dort wird durchgehend `?.` benutzt). Ein Wächter dafür ist ~20 Zeilen AST — der Umbau
   dahinter ist es nicht.

   **Der Autor der Regel hat sie selbst verletzt.** Beim Bau von 0.51.1 standen zwei neue
   Prüfzeilen auf `[]`, und die eigene Gegenprobe **stürzte ab, statt zu zählen** — genau
   der sechzehnte Fall, in der Datei, die ihn aufgeschrieben hat, zwei Sitzungen später.
   Es wurde nicht daran gedacht, obwohl der Fall aus derselben Hand stammt. **Eine Regel,
   die ihr eigener Autor zwei Sitzungen später verletzt, ist nicht aufgeschrieben genug —
   sie muss erzwungen werden.**

   **Drei Zuschnitte, gemessen in 0.51.1:**

   | Zuschnitt | Stellen | Taugt er? |
   |---|---|---|
   | nur Neubau (`test_ramp.py`) | **41** | **Nein.** Der Verstoß von 0.51.1 lag in `test_workouts.py`, einer Altdatei — dieser Zuschnitt hätte genau den Fall verfehlt, für den er gedacht war. Dazu bräuchte er eine eingefrorene Altbestandsliste, also die Bauart, vor der die vierte Bauregel warnt |
   | nach **Herkunft**: `[]` auf Variablen aus einem Bauteil-Aufruf | **632** | **Ja** — das ist genau die Klasse, gegen die eine Mutation fährt, und sie hätte beide Verstöße gefangen |
   | ganzer Bestand, jeder lesende `[]` mit String-Schlüssel | **1.676** | Ja, aber der Umbau ist unverhältnismäßig |

   Die JS-Seite ist sauber (2 Stellen, dort wird durchgehend `?.` benutzt). **Bewusst nicht
   in 0.51.0 und nicht in 0.51.1 gebaut**, damit ein Auslieferungs-Release nicht an einem
   Prüfstands-Umbau hängt — der Zuschnitt nach Herkunft ist der, der gebaut gehört.

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
3. Version heben: `manifest.json` **und** `const.py PANEL_VERSION` (beide!) —
   **seit 0.51.1 von `test_projektstand` erzwungen**, zusammen mit dem
   PROJEKTSTAND-Kopf. Vorher stand der Schritt nur hier und fiel deshalb aus
   (§7, einundzwanzigster Fall). Gegen den **Tag** kann die Suite nichts halten;
   dass Tag und Bauteil übereinstimmen, bleibt Handarbeit — dafür ist Schritt 5
   erst nach einem grünen Lauf zu tun, nie davor
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

**Handgriff, der jede Sitzung trifft (0.51.1): `git push -u` schreibt die Push-URL
SAMT TOKEN nach `.git/config`.** Wer mit `https://x-access-token:$TOKEN@…` pusht
und dabei `-u` setzt, hinterlässt den Token dauerhaft unter
`branch.<name>.remote` — im Klartext, in einer Datei, die jeder spätere Befehl
ausgibt. Drei Gegenmittel, in dieser Reihenfolge:

1. **`origin` gleich nach dem Klonen token-frei setzen:**
   `git remote set-url origin https://github.com/JochenRi/ha-intervals-icu.git`
2. **Ohne `-u` pushen** und die URL je Aufruf mitgeben — dann landet sie nirgends.
3. **Nachsehen, nicht annehmen:** `grep -c "x-access-token" .git/config` muss `0`
   ergeben. Falls nicht: `git branch --unset-upstream <zweig>` und die beiden
   Schlüssel `branch.<zweig>.remote` / `.merge` entfernen.

Dasselbe gilt für jede Ausgabe, in der ein Token, ein Geheimnispfad oder eine
geheimnisartige Zeichenkette Richtung einer fremden Domain auftaucht — sie wird
gemeldet, nicht stillschweigend behoben.


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
| **Trainer** | ✅ auditiert 12.09. — 14 Befunde; Paket 1 (Befunde 1–6) als **0.32.0 ausgeliefert und am System verifiziert** (Konfliktwächter feuert live mit 68 %); Paket 2 (Plan-Umbau + Rest Befund 10) als **0.33.0 gebaut**, ✅ verifiziert: WORK 248–257 W gegen RECOVERY 87–95 W, Leitzahl 250 W. **0.49.0 stellt die Vorgaben der harten Familien auf die Messung um — Watt UND Puls aus derselben Quelle** |
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
| **Trainer (Wochenplan + Einheitenliste, Paket I)** | ✅ gebaut als **0.42.0**. Vier Urteilsstufen (grün / gelb / **Reiz** / rot) an EINER Stelle im Backend, beide Ansichten lesen sie aus der Payload — die Zusammenführung von Zustand und Budget stand bis dahin im Frontend. Bewertet wird nur die laufende Woche; spätere tragen einen Satz statt einer Stufe, weil ein Budget aus den letzten sechs Tagen nichts über Woche sechs sagt. Gefahren gegen vorgesehen aus dem Archiv, **ungepaart**. Die Spezifikation wurde vor dem Bau an sechs Stellen korrigiert: die Ansicht existierte bereits seit 0.33.0, die Stufenliste hatte drei Punkte bei vier Stufen, die Last der geplanten Einheit war die einer kürzeren (siehe §7), das Urteil über acht Wochen widersprach I4, „Erholung war da" war undefiniert, und der Trainer-Reiter musste mit. Verifikation am System steht aus |
| **Durability-Messung als Einheit (Paket K, Stufe 1)** | ✅ gebaut als **0.44.0**. K1 und K2; K3 (die Hantel) bleibt zurückgestellt, bis zwei Messungen vorliegen. Die Spezifikation wurde vor dem Bau an drei Stellen korrigiert: K1 war **nicht** „nur `workouts.py`" (der 20-Minuten-Bestwert steht in keinem Feld, also zieht K2 das ganze J7 mit rein — Archivblock, Migration, Messweg aus den ungedünnten Strömen); die Lastregel aus I3 gilt bei **konstanter** Intensität und ist für eine Einheit mit fester Arbeit und abgeleiteter Dauer nicht anwendbar (jetzt gerechnet statt skaliert); und die Ausschlusswarnung zielte auf `DURABILITY_EXCLUDED_TYPES`, während in Wahrheit der **Intensitätsfilter** beißt. Verifikation am System steht aus |
| **Durability-Kachel (Paket H)** | ✅ gebaut als **0.41.0**. Kopfbereich aus drei Zeilen: belegte Fähigkeit (längste gleichmäßige Fahrt nach ZEIT, mit der Leistung dieser Fahrt), Bezug der letzten 30 Tage mit sichtbarer Ausweitung, nächster Schritt ×1,10 auf fünf Minuten gerundet. Die Spezifikation wurde vor dem Bau an drei Stellen korrigiert: H war **nicht** frontend-only (Dauer und Leistung fehlten in der Payload), der Rückfall ist die **Regel** statt einer Ausnahme (am Livebestand 230 gegen 260 min bei gefülltem Fenster), und vier Fallen fehlten. Verifikation am System steht aus |
| **Trainer (Ermüdungskurve, Paket L)** | ✅ gebaut als **0.45.0**, in **0.46.0** an ihren Platz gerückt: sie ist das Hauptbild der Durability-Kachel im Trainer und ersetzt dort die Punktwolke — vorher stand sie im DFA-Reiter neben einer zweiten Kachel zur selben Frage (§7). Dazu die fehlende Bedienung (Ablesestreifen, Zeiger, Wertetabelle, beide Leserichtungen) und die gepaarte Gegenrechnung zum Auswahleffekt. L1/L1a/L1b: Anker gemessen (Repräsentantenmethode je Fahrtstunde, aus den ungedünnten Strömen beim Import), Form nach Gallo gesetzt und daran verankert, Unsicherheitsband aus der publizierten Streuung. Die Bereichsgrenzen rechnen sich aus der Belegung — zwei Bestände ergeben nachweislich zwei Grenzen. Vorgeschaltet zwei Bugfixes, die heute schon wirken: die Plausibilitätsregel an EINER Stelle statt in fünf Fassungen, und der Historienbeginn. Die Spezifikation wurde vor dem Bau an vier Stellen korrigiert: L1 war NICHT payload-fertig (das Archiv trug ein Fenstermittel je Fahrt, keinen Stundenverlauf — also Algorithmus-Bump, Neuberechnung, Fortschrittsanzeige), die Ausdünnung ist auf dem Importweg gar nicht da, der VI kann strukturierte Einheiten nicht trennen (§7), und L2–L6 existieren nicht und wurden nicht erfunden. Verifikation am System steht aus |
| **Trainer (Wattvorgaben, Paket L4)** | ✅ gebaut als **0.47.0**, korrigiert in **0.47.1** (die Vorgabe ist ein Anteil der Schwelle, nicht die Schwelle selbst — §7). Grundlage und lange Fahrt beziehen ihre Watt aus der gemessenen Kurve, gestaffelt nach Fahrtdauer auf der gepaarten Reihe; die übrigen Familien bleiben bei der FTP, die dort als **Rückfall** beschriftet ist. Die Einheitenkarte nennt je Abschnitt, ob die Zahl gemessen oder Studienform ist. Die Spezifikation wurde vor dem Bau an einer Stelle korrigiert: nicht „SweetSpot liegt außerhalb des Messbereichs" (falsch — es liegt drin), sondern „aus arbiträren Fahrten ist dort kein tragfähiger Fit zu gewinnen". Dazu `p050` und die Signalqualität unter alpha 0,5 erhoben, von nichts benutzt. Verifikation am System steht aus |
| **Trainer (Leistung je Block, Paket M)** | ✅ gebaut als **0.48.0**. Ein Wert je Arbeitsblock, direkt abgelesen nach dem Verwerfen der ersten zwei Minuten (Rogers 2021, am Bestand bestätigt: Anlauf endet bei 90–120 s). Verlauf je Familie mit der Leistung im ersten eingeschwungenen Block als Leitzahl; dazu ein Regelkreis, der einen Vorschlag rechnet und nichts selbst tut. Blockgrenzen aus Intervals' eigenen Abschnitten (K2). Die Vermessung lief in drei Runden und korrigierte drei Zahlen, bevor eine Zeile entstand (§7). Verifikation am System steht aus |
| **Anzeige-Release (Paket O)** | ✅ gebaut als **0.50.0**. Reine Darstellung, kein Algorithmus-Bump: der Kopf der Durability-Kachel entfällt, die Progressionszeile steht jetzt im Wochenplan (samt ihrer Grenze), die doppelte Wertetabelle ist auf die im Rechenweg zusammengezogen, die Bandbreite ist als **Spanne** in die Ableseleiste gewandert, und die Leitzahl folgt dem Zeiger — **nur in der Ermüdungskachel**; in den Block-Karten bleibt sie stehen, weil sie dort die Steuergröße ist. Beide Verhaltensweisen sind zugesichert. Die Spezifikation wurde vor dem Bau an sechs Stellen korrigiert (docs/ausbau.md): der Kopf sitzt in `rDurability` und nicht in `rFatigue`; „aus dem Graphen ablesbar" galt nur für die Dauer, nicht für die Watt; Punkt 3 und 4 widersprachen sich über die Wertetabelle; die Bandbreite war nicht „nirgends", sondern als Breite statt als Spanne da; beim Überfahren einer Block-Kurve kam nicht „nichts", sondern ein Wert der Ermüdungskurve (§7); und „bei welchem alpha" nannte den Median statt des alpha des aufgetragenen Blocks. Die sieben eingefrorenen `chart()`-Hashes haben gehalten. Verifikation am System steht aus |
| **Block-Kurven: Ableseleiste und Datumsachse** | ✅ Ableseleiste als **0.50.0** gebaut — Einheit, Datum, Watt, alpha des aufgetragenen Blocks und Zahl der Blöcke, je Familie eine eigene geschachtelte Zeigergruppe. **Die Datumsachse ist gestrichen**, nicht vertagt: wer beim Überfahren das volle Datum bekommt, braucht den Monat unter der Achse nicht (Entscheidung des Athleten, 14.09.2026). Verifikation am System steht aus |
| **Stufentest (Paket N)** | ✅ gebaut als **0.51.0**. Der Durability-Test ist aus dem Katalog entfernt, der Stufentest steht dort neu — beide Schwellen aus EINER Fahrt, unter gleichen Bedingungen, statt zweier Termine und 1.000 kJ, die auf absehbare Zeit nicht gefahren würden. Neu: `ramp.py` (die Schwelle wird **gefittet, nicht abgelesen** — eine Ausgleichsgerade durch den Abfall von DFA a1, Schnittpunkt mit 0,75 bzw. 0,5; über das gemessene Segment hinaus wird **nicht** hochgerechnet), `ramp_tests.py` (Archivblock mit Migration und Messmarke, drei Regeln aus K2: keine Erkennung, keine stille Messung, rücknehmbar), `set_ramp_test` an der Stelle von `set_durability_test` (Ströme LIVE und ungedünnt, nur das Ergebnis wird gespeichert), die **Quellenkette je Familie** als eine Mechanik mit verschiedener Rangfolge, und die Stufentest-Karte mit drei Zahlen plus der 40-Watt-Frage. **Kein Algorithmus-Bump, keine Neuberechnung.** Die Spezifikation wurde beim Bau an fünf Stellen korrigiert (docs/ausbau.md): N4 ist nicht „nachzulesen", sondern in den zugänglichen Quellen **nicht beantwortbar** — Einrollen, Startleistung und Abbruchkriterium stehen dort nicht so, wie die Spec annahm; die Segmentregel ist deshalb eine **Setzung**, weil beide Arbeiten das Segment von Hand am Plot bestimmen; die personalisierte Schwelle ist eine Operationalisierung **aus zweiter Hand**; das Ausrollfenster ist eine eigene Idee ohne Protokollvorgabe; und die Erholungsgröße fließt in keine Vorgabe ein. **Nachgebessert in 0.51.1**, siehe die Zeile darunter |
| **Stufentest, Nachbesserung (Paket N1)** | ✅ gebaut als **0.51.1**, ohne Algorithmus-Bump. Der erste Live-Blick auf 0.51.0 fand vier Fehler, alle in der ausgelieferten Karte: (1) die Rampe hing komplett an der FTP (`ramp 60-115%`) und endete bei diesem Athleten **27 W UNTER** seiner eigenen Leitzahl — die zweite Schwelle war nicht erreichbar, und der Wächter darüber bewachte die Ausnahme statt der Regel; (2) Dauer, Steigung und Spanne passten nur bei genau einer FTP zusammen; (3) die zehn Beschreibungspunkte waren vorhanden, wurden aber nicht gerendert — ein Umzug zwischen zwei Payloads, verschluckt von einem `\|\| []`; (4) das Pulsfenster war die falsche **Art** von Aussage, und die Rampe wurde flach gezeichnet. Gebaut: zwei getrennte Quellenketten (Start Ermüdungskurve → HRVT1 → FTP, Ende Blockmessung-**Leitzahl** → HRVT2 → FTP, Reserve als ZEIT), **die Dauer wird gerechnet statt gesetzt**, Beschreibung an der Einheit mit einem Wächter, der belegt dass sie ankommt, Quellen schon im Leerzustand, Pulsfenster ersatzlos durch einen Satz ersetzt, Rampe als Rampe gezeichnet. Bei diesem Athleten: 138→307 W statt 120→230 W, 34 min statt behaupteter 30 (gerechnet wären es 22 gewesen). §7, Fälle 18–20. Verifikation am System steht aus |
| **Zuordnung: der Überblick (Paket P, Auslieferung A2)** | ✅ gebaut als **0.53.0**, **ohne Algorithmus-Bump** — reine Anzeige auf der Payload aus 0.52.0. Die Markenspalte in der Aktivitätenliste: je Fahrt die Kürzel der gewerteten Familien, **leer heißt noch nicht angefasst**, blass heißt markiert und noch nicht gemessen (der Unterschied auch im Klartext am `title`, nicht nur in der Sättigung). Die Liste bleibt chronologisch, die Zeile behält ihren Klickweg. **KEIN Driftzeichen, und das ist entschieden, nicht ausgelassen:** der Befund ist nur gegen live geholte Laps zu haben, und ein gespeicherter Stand wäre systematisch in genau den Fällen falsch, für die er gebaut wäre — Drift entsteht, wenn in Intervals neu unterteilt wird, also NACH dem letzten Öffnen. Dazu die Nachbesserung aus dem ersten Live-Blick auf 0.52.0: **ein Abschnitt ist kein Mangel** — eine Rolleneinheit IST die ganze Fahrt, und die Kachel sagt das jetzt so. Zugesichert war das vorher nicht (§7, zweiundzwanzigster Fall, zum zweiten Mal). Verifikation am System steht aus |
| **Zuordnung durch den Athleten (Paket P, Auslieferung A)** | ✅ gebaut als **0.52.0**, **ohne Algorithmus-Bump**. Der Archivblock `section_marks` (Schlüssel `start_index`, niemals die laufende Nummer), sein Anker samt Drifterkennung, drei WebSocket-Wege und die Kachelreihe im Aktivitätsdetail: sechs Familien mit eigener Form und eigenem Kürzel plus der Stufentest, der dort aufgeht — `_rampBlock` fällt. **Es wird noch nichts gerechnet:** die Vorgaben, die Verlaufskacheln und die Ermüdungskurve lesen weiter die Namenserkennung und die WORK-Etiketten. Die Spezifikation wurde vor und während des Baus an zehn Stellen korrigiert (docs/ausbau.md): P1 entfällt mit der Vorschlags-Streichung ganz, der mittlere DFA-Zustand ist geprüft und verworfen, der Anker wird beim ERSTEN Haken gesichert, `reanchor` ist streng, der Anker taugt nicht zum Maskieren, der Messweg braucht zwei Abrufe, P8 ist nicht frontend-only, der Stufentest misst beim Klick, die Reihenfolge ist umgedreht, und die Mobilfrage bleibt offen. §7, zweiundzwanzigster Fall. Verifikation am System steht aus |
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
