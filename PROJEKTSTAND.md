# ha-intervals-icu — Projektstand

**Stand:** 11.09.2026 · **Version:** 0.21.0 · **Status:** produktiv auf HEIMDALL,
Auslieferung über HACS aus `github.com/JochenRi/ha-intervals-icu`

Eine eigene Home-Assistant-Integration, die Trainingsdaten von Intervals.icu lokal
archiviert, auswertet und in einem eigenen Seitenleisten-Panel darstellt. Später als
kostenloses HACS-Repository für andere gedacht.

---

## 1. Was das Ding tut

| Ebene | Inhalt |
|---|---|
| API-Client | Wellness, Aktivitäten, Kalender, Streams, Runden; ein Schreibweg (Workout planen) |
| Archiv | Vollständige Historie lokal in `.storage`, ~300 kB, keine Datenbank |
| Entitäten | 49 Sensoren + Kalender-Entität für Automationen und Langzeitstatistik |
| Auswertung | Trainingslast, DFA alpha-1, Zustandserkennung, Lastbudget, Einheitenvorschläge |
| Panel | Eintrag „Intervals" in der Seitenleiste, neun Ansichten |

**Datenbestand (Konto i123456):** 487 Wellness-Tage · 239 Aktivitäten · 57 DFA-Auswertungen

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
├── analytics.py      Trainingsauswertung: PMC, ACWR, Monotonie, Bereitschaft (HA-frei)
├── coach.py          Zustandserkennung, Anker, Signalmatrix, Empfehlung (HA-frei)
├── workouts.py       Einheitenbibliothek mit Belegen und Intervals-Syntax (HA-frei)
├── sensor.py         49 Entitäten
├── calendar.py       Kalender-Entität mit geplanten Workouts
├── websocket.py      16 Kommandos für das Panel
└── frontend/
    └── intervals-panel.js   Panel, eine Datei ohne Abhängigkeiten
```

### Warum so und nicht anders

- **Vier HA-freie Module.** `derive`, `analytics`, `coach` und `workouts` importieren nichts
  von Home Assistant. Jede Rechnung und jede Regel lässt sich damit außerhalb von HA gegen
  echte Datensätze durchspielen — der gesamte Prüfstand beruht darauf.
- **Kein zweites Repository für die Karte.** Panel und Hilfsfunktionen liegen in einer
  Datei. Eine zweite Datei ist eine zweite Sache, die beim Kopieren verlorengeht — und der
  Browser meldet nie, *welcher* Import fehlte.
- **Archiv statt Recorder.** HA löscht Rohzustände nach ~10 Tagen und erzeugt Statistiken
  nicht rückwirkend. Aktivitäten gehören nicht in die State-Machine; das Panel liest die
  WebSocket-Schnittstelle.
- **Streams und Runden bewusst nicht im Archiv.** Ein Jahr Sekundendaten hat auf der Platte
  nichts verloren. Sie werden beim Öffnen einer Einheit live geholt, auf höchstens 900
  Punkte ausgedünnt und nicht gespeichert.

---

## 3. Verifizierte Erkenntnisse über die Intervals-API

Alles am eigenen Konto geprüft, nicht aus Dokumentation übernommen.

| Erkenntnis | Bedeutung |
|---|---|
| Auth ist **HTTP Basic** mit dem literalen Benutzernamen `API_KEY` | Bearer-Token funktioniert nicht — der häufigste 403-Grund |
| Athlete-IDs tragen meist ein führendes `i` | nur früh registrierte Strava-Nutzer haben reine Zahlen |
| CTL/ATL heißen im Wellness-Datensatz **`ctl`/`atl`** | nicht `icu_ctl`, wie im Forum behauptet |
| `fields=` funktioniert | ganzer Jahresbestand in einer Anfrage |
| Zonenzeiten kommen in **zwei Formaten** | Puls: Zahlenliste · Leistung: Objekte mit `secs` |
| Strava-Aktivitäten liefert die API **nicht** aus | Platzhalter mit `_note`, müssen übersprungen werden |
| `/activity/<id>/streams.json` liefert eine **Liste** | kein Mapping — `derive.streams_to_dict` macht daraus `name → daten` |
| **Runden** haben keinen eigenen Endpunkt | sie hängen an der Aktivität: `/activity/<id>?intervals=true`, Feld `icu_intervals` |
| **Workouts planen:** Schritte als Plaintext ins Feld `description` | `workout_doc` bleibt leer, Intervals parst selbst — ein Format statt zwei |
| `dfa_a1` liegt sekundengenau in den Streams | bei 57 von 239 Einheiten, abhängig von der Aufzeichnung |
| DFA-Streams enthalten `0.0`-Artefakte am Anfang | zählt sonst fälschlich als anaerob |
| Puls- und Wattströme enthalten Nullen (Aussetzer, Rollen) | verfälschen sonst die Schwellenablesung |
| Gewicht ist **nicht gemessen** | `icu_weight_sync: NONE`, Wert stammt aus der Aktivitätsdatei |
| VO2max kommt nur an Trainingstagen | Garmin rechnet ihn nur nach passenden Einheiten neu |

---

## 4. Die Ansichten

| Ansicht | Inhalt |
|---|---|
| **Trainer** | Zustand heute, konkrete Einheiten mit Wattzahlen und Kalender-Knopf, gemessene Anker, Durability, Wochenvorschlag, Einheitenkatalog |
| **Signale** | Alle Signale auf einer Zeitachse in Standardabweichungen, Zustandsbänder im Hintergrund, Lastbalken nach gefahrenen DFA-Bereichen |
| **Heute** | Bereitschaftsring aus sieben Signalen, Lastbudget als Bullet-Graph mit Rechenweg |
| **Kalender** | Wochenraster mit Wellness-Symbolen, Einheiten als Kacheln, Geplantes in drei Zuständen |
| **Fitness** | Fitness/Ermüdung · Tagesbelastung · Form mit Friel-Zonen, gemeinsame Zeitachse |
| **Aktivitäten** | Tabelle, je Einheit: Kennzahlen, **Runden** mit EF-Verlauf, **Rundenkurven mit gemeinsamer Skala**, gestapelte Verlaufskurven |
| **Belastung** | Wochenlast, ACWR, Intensitätsverteilung zweifach, HRV-Trend, Entkopplung |
| **DFA** | Schwellenverlauf mit rollierendem Median, Leistung als eigenes Feld |
| **Plan** | Geplante Workouts nach Tagen |

### Segmentanalyse (0.17.0) — dieselbe Tabelle für Intervalle und Grundlage

**Zwei verworfene Entwürfe stehen davor, beide lehrreich:**

1. *0.13.0 — eine Zeile je Runde, gemeinsame Skala.* Machte die Zeilen vergleichbar und jede
   einzelne Kurve zum Strich.
2. *0.14.0–0.16.0 — die Blöcke übereinandergelegt.* Theoretisch richtig (Gleicher:
   Superposition, wenn die Objekte ähnlich genug sind), praktisch ein Knäuel: bei
   verrauschten Sekundendaten gilt der Befund von Javed et al., dass mehr Linien die
   Korrektheit senken und die Elemente ihre Unterscheidbarkeit verlieren. Direktbeschriftung
   und Aufzoomen haben das gemildert, nicht behoben.

**Was bleibt, ist die Tabelle** — und sie ist jetzt ein allgemeines Werkzeug (`_devTable`),
das auf jede geordnete Liste von Abschnitten passt:

| Fall | Abschnitte |
|---|---|
| Intervalleinheit | die gleichartigen Arbeitsblöcke |
| Gleichmäßige Fahrt | vier gleich lange Viertel, Aufwärmphase ausgenommen |

Zeilen sind Kennzahlen (Leistung, Puls, DFA, Watt/Herzschlag, Puls-Erholung), Spalten sind
Abschnitte, jeder Balken die Abweichung vom ersten — **Länge an gemeinsamer Grundlinie**,
die am genauesten gelesene Kodierung, mit der Zahl in ihrer eigenen Einheit daneben und dem
Bezugswert in der Zeilenbeschriftung.

**Der Grundlagen-Fall ist der Entkopplungstest, sichtbar gemacht.** Kardiale Drift — der
Puls steigt bei konstanter Leistung — ist das *Was*; ob Watt pro Herzschlag zusammenhält,
das *Na und*. Die Einordnung folgt den veröffentlichten Richtwerten: unter 3 % halten
trainierte Fahrer, 5 % ist Friels Richtwert, 5–10 % ist der Freizeitbereich, über 10 % lag
die Einheit wahrscheinlich über der aeroben Schwelle. **Vier Viertel statt zwei Hälften**,
weil der Zeitpunkt der Veränderung selbst eine Information ist, die der übliche
Einzelwert verschweigt.

Ein Test fährt vier Fahrten mit unterschiedlicher Drift durch (1,1 % / 4,0 % / 5,3 % /
14,5 %) und verlangt für jede die richtige Einstufung.

### Heute, neu gebaut (0.21.0) — gegen die Kritik an Bereitschaftswerten

Ring, Punktwert („5 von 7 Signalen") und Monotonie sind raus. Zwei Befunde haben die
Ansicht neu geformt:

**Bereitschaft ist nicht Erholung.** *Erholung beschreibt, was als Reaktion auf vergangenen
Stress passiert ist; Bereitschaft, was im gegenwärtigen Moment vertragen wird.* Eine Zahl
presst beides zusammen — und ein niedriger Wert aus einer kurzen Nacht sieht aus wie einer
aus einem beginnenden Infekt, verlangt aber das Gegenteil.

**Von vierzehn Bereitschaftswerten aus zehn Wearable-Häusern** (Garmin, Whoop, Oura, Polar,
Fitbit …) legt **kein einziger seine Formel offen**, und kaum einer hat eine Validierung
vorzuweisen. Die Zutaten sind überall dieselben — HRV 86 %, Ruhepuls 79 %, Schlaf 71 % —,
die Gewichtung bleibt Betriebsgeheimnis.

**Die empfohlene Alternative steht in derselben Quelle** und ist jetzt die Gliederung der
Seite: solche Daten nicht als Urteil behandeln, sondern als Anstoß zur Nachfrage —
*was hat sich geändert, welches System treibt es, wie passt das zum jüngsten Training.*

1. **Was heute möglich ist** — ein Satz, dazu eine Obergrenze als Bullet-Graph mit dem
   heute schon Gefahrenen.
2. **Was sich bewegt hat** — jedes Signal einzeln, **mit dem System, über das es etwas
   aussagt** (autonomes Nervensystem vs. Verhalten) und mit dem, was es nicht kann.
   Nie gemittelt.
3. **Woher das kommt** — sieben Tage Last, nach Zustand eingefärbt, und die Nacht nach der
   letzten Einheit, ausdrücklich als *Erholung, nicht Bereitschaft* beschriftet.

**Wo Signale und Urteil auseinanderlaufen, sagt die Seite warum** statt es zu verstecken:
„Herzratenvariabilität liegt unter deiner Basislinie — aber weder weit genug noch lange
genug für einen Einbruch. Die Regel entscheidet über das Mittel der letzten drei Tage."

**Und sie reicht nicht über heute hinaus.** Was morgen geht, hängt an der Belastung
außerhalb des Trainings, und die steht in keinen Daten — *der wirksamste Einsatz solcher
Werte liegt in der Anpassung der heutigen Einheit, nicht in der Planung der Woche.*

Beim Umbau haben die alten Tests drei echte Regressionen gefangen: die Ampelfarbe ohne
Wort (WCAG), der verschwundene Bullet-Graph und der fehlende Stand je Wert.

### Ziel und Plan (0.20.0) — der Trainer ist entpausiert

Der Trainer schlug Einheiten vor, ohne zu wissen, wofür. Jetzt fragt er einmal: **Was
willst du können, wie viele Tage hast du, wie viele Stunden, was kann nicht verschoben
werden** — und leitet daraus Wochen ab. Das Profil liegt lokal im Archiv, nichts davon
geht an intervals.icu.

**Für das Ziel „lange Fahrten" ist die Zielgröße nicht FTP, sondern Durability.** Maunder
definiert sie als *Zeitpunkt und Ausmaß der Verschlechterung physiologischer Merkmale
während langer Belastung*. Sie ist eine eigene Eigenschaft: Profifahrer schlagen ihre
Konkurrenz nicht über die frische Leistung, sondern darüber, wie viel davon nach Stunden
übrig ist. Trainiert wird sie über lange Einheiten knapp unter der aeroben Schwelle — und
ab etwa sechs bis acht Wochen vor dem Ziel über **Qualität am Ende** der langen Fahrt, nicht
am Anfang. Dazu der Hinweis, der am häufigsten falsch gemacht wird: **durchgehend
verpflegen** — der Reiz soll aus der Belastung kommen, nicht aus leeren Speichern.

**Was der Planer bewusst NICHT behauptet:** dass Blockperiodisierung besser sei. Zwölf
Wochen, trainierte Radfahrer, lastgleich verglichen — **kein Unterschied** in der
Zeitfahrleistung. Ihr echter Vorteil ist praktisch: ein Reiz je Block vereinfacht die
Planung und lässt sie sich an die Wochen anpassen, die das Leben übrig lässt. Das steht so
im Panel.

**Belastungsmuster** 3:1 (ab vier Tagen) oder 2:1, Entlastungswoche bei rund zwei Dritteln
des Umfangs. Der lange Tag wächst etwa 12 % je Belastungswoche — **als Konvention
ausgewiesen, nicht als Studienergebnis**.

**Die ehrlichste Zeile im ganzen Planer** ist die Rechnung, die sagt, dass es nicht geht:
Bei 8 Wochenstunden ist eine 6,5-Stunden-Fahrt nicht aufzubauen — sie wäre 81 % der
Wochenzeit. Statt eine Zahl zu drucken und sie dann still zu kappen, steht da, wie viele
Wochenstunden das Ziel braucht (rund 11) und was aus der jetzigen Woche erreichbar ist
(4,8 h). Ein Test erzwingt, dass der angezeigte lange Tag nie über dem Wochenbudget liegt.

### Wie diese Einheit dasteht (0.19.0)

„Entkopplung 11,4 %" gegen Friels 5 % sagt, wo du gegenüber einer Population stehst. Die
Frage, die zählt, ist eine andere: **ist das für dich viel?** Dafür wird jede Einheit gegen
die eigenen vergleichbaren gestellt — dieselbe Sportart, Intensität ±10 Punkte, Dauer
±40 %, und nur Einheiten, die **vorher** lagen.

Gezeichnet als Bereich: die mittlere Hälfte der Vergleichseinheiten als Band, der Median
als Strich, diese Einheit als Punkt — Position auf gemeinsamer Skala. Daneben der
Prozentrang in Worten.

**Das Urteil hängt am Verlassen der mittleren Hälfte, nicht am Prozentrang.** Der erste
Entwurf nutzte Rang ≥ 60 bzw. ≤ 40; bei enger Verteilung landet damit ein Unterschied von
0,3 Prozentpunkten auf Rang 62 und hieße „schlechter als sonst" — Rauschen im Gewand eines
Befundes. Die mittlere Hälfte ist zugleich genau das Band, das gezeichnet wird: Wort und
Bild können nicht auseinanderlaufen.

**Am echten Konto geprüft**, Fahrt vom 04.09.2026 (3h28m, Last 129): Entkopplung 10,6 %
gegen einen eigenen Median von 2,1 % bei 17 Vergleichsfahrten — **Prozentrang 94**. Watt
pro Herzschlag dagegen 0,923 gegen Median 0,695, Rang 76. Eine starke und zugleich
ungewöhnlich entkoppelte Fahrt, zwei Tage vor dem Infekt.

### Die Nacht danach (0.18.0)

Jede Einheit bekommt die Frage beantwortet: **was hat sie gekostet?** Dafür wird die Nacht
direkt nach der Einheit ausgewertet — Schlaf ist die sauberste Messbedingung, die es gibt,
und nach einem harten Reiz steigt die nächtliche Herzfrequenz, ln(rMSSD) fällt; die
Rückkehr zu den Ruhewerten dauert Minuten bis einen ganzen Tag, getrieben vor allem von der
Intensität.

**Der entscheidende Kunstgriff: gelesen wird gegen die eigene übliche Antwort**, nicht
gegen einen Normwert. Der Zusammenhang zwischen Last und HRV-Änderung ist **glockenförmig**
— eine sehr lockere und eine sehr harte Einheit können beide eine unauffällige Nacht
hinterlassen, aus entgegengesetzten Gründen. Ein absoluter Schwellenwert würde nach jeder
harten Fahrt Fehlalarm schlagen. Stattdessen wird die Nacht mit den Folgenächten früherer
Einheiten **ähnlicher Last und Intensität** verglichen (mindestens fünf, sonst kein Urteil).

Beispiel aus der Simulation: HRV −1,54 SD unter der Basislinie — absolut ein Einbruch.
Üblich nach Einheiten dieser Größe ist bei diesem Athleten −1,49 SD. Urteil: **unauffällig.**

**Gewichtet statt gemittelt:** HRV 1,0 · Ruhepuls 0,8 · Schlafdauer 0,3. Die Studien messen
nächtliche Herzfrequenz und HRV — das ist die autonome Antwort. Schlafdauer ist Verhalten
und darf eine kurze Nacht nach spätem Feierabend nicht über das Herz stellen.

### Gestaltungsregeln, jede mit Grund

Cleveland & McGill, mehrfach repliziert: Position ist der genaueste Kanal, dann Länge auf
gemeinsamer Grundlinie; Winkel, Fläche und Farbe liegen dahinter. Daraus und aus der
weiteren Recherche:

- **Menge → Länge auf gleicher Grundlinie.** Keine Kreise, keine Flächen.
- **Zustand → Farbe *und* Wort *und* eigene Icon-Form.** Dreifach, weil rund 8 % der Männer
  Rot und Grün nicht trennen können (WCAG 1.4.1).
- **Zwei Farbregister, die sich nie mischen.** Grün/Gelb/Rot bedeuten ausschließlich ein
  Urteil; Blau/Violett/Cyan/Magenta/Schiefer tragen Kategorien und Kanäle. Innerhalb einer
  Ansicht kommt jeder Datenton höchstens einmal vor. Ein Test erzwingt beides — dieselbe
  Fehlerklasse hat 0.7.0, 0.8.0 und 0.9.0 je ein Release gekostet.
- **Keine zweiten Achsen.** Verwandte Reihen stapeln als Kleinvielfache über einer
  gemeinsamen Zeitachse mit einem Cursor.
- **Mehrere Zeitreihen: gestapelt, nicht überlagert.** Javed/McDonnel/Elmqvist (TVCG 2010):
  getrennte Felder je Reihe sind beim Vergleich über Reihen mit großer visueller Spannweite
  deutlich effizienter; acht dünne Linien überfordern die Farbauflösung des Auges.
  Überlagern bleibt als Schalter für den Fall kleiner Spannweite.
- **Kein Tacho.** Für „Ist-Wert gegen Zielbereich" ein Bullet-Graph (Few).
- **Kein schwebender Ablesekasten.** Die Werte stehen in einer festen Leiste im Kartenkopf.
  Ein positionierter Kasten war dreimal am falschen Fleck; die Fehlerklasse ist entfernt,
  nicht repariert.
- **Rohwerte in der Ableseleiste**, auch wenn die Kurven normalisiert sind: 63 ms erkennt
  man wieder, +1,9 SD nicht.
- **Aufklappfelder sind unabhängig**, Quellen eingeklappt statt als Textwand.

---

## 5. Auswertungen und ihre Belege

Jede Kennzahl trägt Quelle und Grenze sichtbar mit sich.

| Kennzahl | Quelle | Grenze |
|---|---|---|
| Form-Zonen | Joe Friel; Intervals rechnet relativ zur Fitness | Faustregel, „keine Wissenschaft" — sagt der Entwickler selbst |
| Akut zu chronisch (7:28) | Gabbett/Blanch, Korridor 0,8–1,3 | korrelativ, mathematisch gekoppelt, formelle Richtigstellung beantragt, RCT ohne Nutzen |
| Monotonie / Strain | Foster: Wochenmittel ÷ Streuung | erst ab drei Trainingstagen aussagekräftig |
| Intensitätsverteilung | Dreizonenmodell Seiler, Elite ≈ 75/8/17 | polarisiert knapp vorn beim VO2peak, begründeter Widerspruch |
| HRV-Trend | 7-Tage-Mittel ln(rMSSD) gegen 60-Tage-Band, Schwelle 0,5 SD (Plews/Altini) | Nachtmessung der Uhr, nicht die validierte Morgenmessung im Liegen |
| Entkopplung | Friel: ≤ 5 % bei ruhigen Dauereinheiten | nur bei gleichmäßiger Fahrt aussagekräftig |
| DFA alpha-1 | Rogers/Gronwald: 0,75 ≈ VT1, 0,5 ≈ VT2 | gegen Gasaustausch validiert; empfindlich für Artefakte und Gerät |
| Zustandsregel | Javaloyes 2019/2020, Vesterinen 2016: harter Reiz nur im oder über dem Normalband | Düking 2021 (8 Studien, 198 Teilnehmer): mittlerer Effekt submaximal, **klein und nicht signifikant** auf die Spitzenleistung |
| Wiedereinstieg | Mujika/Coyle: bis ~2 Wochen Pause überwiegend Plasmavolumen | darüber hinaus geht Substanz verloren |
| 30/15 | Rønnestad: 3×13×30/15 gegen aufwandsgleiche 4×5 min, 10 Wochen — signifikant größere Zuwächse | Protokollnamen sind keine Verschreibungen; Zeit nahe VO2max ist ein Sitzungsmaß |
| **Bereitschaftsampel** | aus den Zeilen darüber zusammengesetzt | Bestandteile belegt, **Kombination nicht** |
| **Lastbudget** | ACWR-Definition nach heute aufgelöst | Zielwahl je Ampelfarbe ist eine Setzung |

### Der wichtigste Befund: die eigene Kalibrierung

Bevor eine Ampel gebaut wurde, wurde geprüft, ob sie bei diesem Athleten überhaupt etwas
vorhersagt. Zielgröße: Watt pro Herzschlag je Einheit, intensitätsbereinigt und gegen die
jeweils letzten zehn vergleichbaren Einheiten normiert (damit der Saisonaufbau nicht als
Tagesform durchgeht).

| Prädiktor | r | erklärt | n |
|---|---|---|---|
| HRV, 7-Tage gegen Basislinie | 0,155 | 2,4 % | 97 |
| Ruhepuls | 0,120 | 1,4 % | 97 |
| Schlaf | −0,060 | 0,4 % | 97 |
| Last der letzten 7 Tage | 0,263 | 6,9 % | 100 |

**Bei n = 97 ist r = 0,155 nicht signifikant.** Der Ruhepuls dreht zwischen Gesamtdatensatz
und Rollenfahrten sein Vorzeichen. Das heißt: die Morgenwerte sagen die *feine* Tagesform
dieses Athleten nicht vorher. Das steht so im Panel.

**Wofür sie sehr wohl taugen:** einen Infekt haben sie sauber abgebildet — Ruhepuls
+3,7 SD an einem Tag, HRV −2,7 SD. Warnlampe, nicht Feinsteuerung.

### Fallbeispiel: der Infekt vom September 2026

Der einzige saubere Prüffall, den dieses System bisher hatte.

| Tag | HRV | Ruhepuls | Zustand laut Panel |
|---|---|---|---|
| 04.09. | 45 | 59 | Normalbereich, letzte Einheit (Last 129) |
| 06.09. | **30 (−2,7 SD)** | **66 (+3,7 SD)** | Einbruch |
| 08.09. | 55 | 53 | noch im Einbruch (Schlaf 10,9 h) |
| 10.–11.09. | 63 (+1,9 SD) | 50–51 (−2,1 SD) | Erholung nach Einbruch |

Die Erwartung für die erste Einheit danach wurde **vor** der Fahrt festgelegt (9
vergleichbare lockere Einheiten, 01.07.–04.09.): EF 0,968 ± 0,032 · HF 143 ± 4 ·
Leistung 139 ± 5 W.

Ergebnis der Einheit am 11.09.: **EF 1,00 · HF 133 · 133 W · Entkopplung 1,5 %.**
Intensitätsbereinigt wären 0,938 zu erwarten gewesen — tatsächlich 1,00, also **+3,4
Standardabweichungen**. Kein erhöhter Puls bei gewohnter Leistung, sondern ein deutlich
niedrigerer. Der Infekt war durch. Einschränkung: ein Teil davon ist die Erholungsphase
selbst (fünf Tage Pause, zwei Nächte über zehn Stunden Schlaf), und dieser Anteil
verschwindet mit den nächsten Einheiten.

---

## 6. Prüfstand

**Dreizehn Testläufe, über 1.100 Einzelprüfungen, alle grün.** Kein Test braucht eine
laufende HA-Instanz oder einen Browser.

| Datei | prüft |
|---|---|
| `test_derive.py` | Parselogik gegen echte Payloads |
| `test_dfa.py` | DFA-Auswertung, Bandgrenzen, Artefakte, Aussetzer |
| `test_import.py` | vollständiger Import gegen einen Nachbau des Kontos |
| `test_analytics.py` | Trainingsmetriken gegen bekannte Ergebnisse |
| `test_setup_simulation.py` | Entity-Aufbau, Übersetzungen, unique_ids |
| `test_laps.py` | Runden-Normalisierung gegen unbekannte Feldnamen und kaputte Payloads |
| `test_coach.py` | jede Zustandsregel gegen ihren Fall, inkl. echtem Infektverlauf; Bänder und Trainerurteil dürfen nie auseinanderlaufen |
| `test_workouts.py` | Einheitenauswahl je Zustand, Blocksummen, Intervals-Syntax des Kalendereintrags |
| `test_websocket_registration.py` | jeder registrierte Befehl trägt seinen Dekorator, Namen eindeutig, Panel ruft nichts Unbekanntes |
| `test_panel_views.js` | alle Ansichten gegen volle, leere, löchrige und entartete Daten |
| `test_panel_fixes.js` | je ein Nachweis pro behobenem Fehler |
| `test_panel_design.js` | Cursor-Geometrie und die Gestaltungsregeln als Zusicherung |

Ausführen: `python3 tests/<datei>.py` bzw. `node tests/<datei>.js`.

**Das Prinzip dahinter:** Ein Test, der den alten Fehler nicht nachweislich findet, ist
kein Test. Bei den kritischen Fixes wurde der Fix jeweils zurückgedreht und geprüft, dass
der Test fehlschlägt.

---

## 7. Fehler und was sie gelehrt haben

| Version | Fehler | Ursache und Lehre |
|---|---|---|
| 0.2.0 | alle Wellness-Sensoren `unavailable` | `_entry()` überschrieb ein Basis-Attribut |
| 0.3.0 | Historien-Import lief nie | „Archiv leer?" wurde geprüft, *nachdem* es befüllt war |
| 0.5.0 | alle Ansichten „Unknown error" | Zonenzeiten in Objektform, `float()` auf ein dict |
| 0.5.0 | ein Ausfall riss alles mit | `Promise.all` statt `allSettled` |
| 0.5.1 | Panel lädt nicht | zweite JS-Datei fehlte beim Kopieren |
| 0.7.0 / 0.8.0 / 0.9.0 | zwei Gelbtöne, zweites Blau, zweites Rot | dreimal dieselbe Klasse → seit 0.9.1 zwei getrennte Farbregister mit Test |
| 0.9.0 | einzelne Messpunkte zwischen Lücken unsichtbar | Pfad nur mit `M`, ohne `L` |
| 0.9.1 / 0.9.2 / 0.9.3 | Ablesekasten dreimal am falschen Fleck | zweimal die Rechnung repariert, zweimal falsch (zuletzt: gegen das Panel-Element geklemmt statt gegen das zentrierte `#app`). Beim dritten Mal die **Fehlerklasse entfernt**: feste Leiste statt positioniertem Kasten |
| 0.9.2 | DFA-Achse von 0 bis 160 | eine Null-Schwelle und eine Ein-Punkt-Messung bestimmten die Achse |
| 0.9.4 | **Integration startete nicht** | neuer Handler zwischen Dekoratoren und `def` des Nachbarn gesetzt → der Nachbar ging nackt raus. 544 grüne Prüfungen halfen nicht, weil keine davon den **Start** prüfte. Seitdem tut `test_websocket_registration.py` genau das |
| 0.9.4 | Runden-Urteil verglich Aufwärmen mit Ausfahren („34 % Abfall") | ein Serienurteil darf nur Gleichartiges vergleichen — in der Simulation gefunden |
| 0.11.0 | Zustandsbänder widersprachen dem Trainerurteil | Bänder nutzten den Tageswert, der Trainer das 3-Tage-Mittel |
| 0.19.0 | Einordnung nannte 2,0 % gegen Median 1,71 % „schlechter als sonst" | Urteil hing am Prozentrang; bei enger Verteilung ist Rang 62 kein Befund. Jetzt entscheidet das Verlassen der mittleren Hälfte — dasselbe Band, das gezeichnet wird |
| 0.12.0 | `VO2max 4×8` behauptete 75 min, Blöcke ergaben 67 | Dauer und Last im Kalender wären falsch gewesen |
| 0.16.0 | Überlagerte Blockkurven blieben unlesbar | die Konstruktion war theoriegerecht, die Daten aber zu verrauscht: vier Linien wurden zum Knäuel. Direktbeschriftung und Zoom milderten, behoben hat es erst das Weglassen — die Tabelle allein trägt die Aussage |
| 0.14.0 | Steigungsdiagramm „Alles auf einer Achse" war unlesbar | die Information lag im Winkel — der schlechteste der drei Kanäle; bei zwei Blöcken vier gerade Linien ohne Aussage. Ersetzt durch Abweichungsbalken an gemeinsamer Grundlinie |
| 0.13.0 | Rundenkurven waren unlesbar: gemeinsame Skala über alle Zeilen machte jede einzelne Kurve zum Strich | Vergleichbarkeit und Lesbarkeit gegeneinander eingetauscht. Der Test maß nur das eine Ziel und meldete Erfolg. Ersetzt durch Superposition + Indexierung; der neue Test misst die Kurvenamplitude |
| 0.13.0 | Rundenkurven zogen den ersten Messpunkt der nächsten Runde mit | das Ende einer Runde ist der erste Messpunkt der nächsten — bei einer Pause vor einem 259-W-Block ein Sprung von 91 auf 259 W mitten in der Erholungskurve. Vom Geometrie-Test gefunden, nicht vom Auge |

---

## 8. Sicherheitsentscheidungen

- **Ein einziger Schreibzugriff.** `POST /athlete/<id>/events` legt ein geplantes Workout
  an. Er passiert nur auf einen Klick im Panel, nie auf einem Timer, nie als Nebenwirkung.
- **Schreibzugriffe werden nicht wiederholt.** Ein Timeout nach erfolgreichem POST hätte
  den Termin doppelt angelegt. Stattdessen kommt eine klare Meldung mit der Bitte, im
  Kalender nachzusehen. Nur `429` wird erneut versucht — dort hat die Anfrage den Kalender
  nachweislich nicht erreicht.
- **Jeder erzeugte Eintrag trägt seine Herkunft** im Beschreibungstext.
- **Der API-Key** liegt im Config-Entry und geht ausschließlich an intervals.icu.

---

## 9. Offen

**Als Nächstes:**
- Signal-Ansicht: deutlicher zeigen, *warum* gerade was passiert — Ereignisse annotieren
  statt nur einfärben
- Ziel- und Zeitprofil als Eingabe, damit der Trainer planen statt vorschlagen kann
- Webhooks statt Polling
- Historien-Import in die HA-Langzeitstatistik (`async_import_statistics`)

**Für die Veröffentlichung:**
- Brand-Icon 256×256 an `home-assistant/brands` (PR) — solange es fehlt, bleibt die
  HACS-Prüfung im CI rot; für die Installation als benutzerdefiniertes Repository ohne Belang
- Repository-Topics setzen (macht die andere Hälfte der CI grün)
- Aufnahme in den HACS-Standardkatalog beantragen

**Zwei Hinweise persönlich:**
1. Der API-Key stand im Klartext im Chatverlauf. Vor Veröffentlichung in Intervals neu
   erzeugen, in HA über den Reauth-Dialog eintragen. Dasselbe gilt für den GitHub-Token.
2. Die tägliche Wellness-Abfrage in Intervals einschalten. Selbsteingeschätzte Werte sind
   laut Review der empfindlichste Einzelindikator — der größte verfügbare Hebel auf die
   Aussagekraft des ganzen Systems.

---

## 10. Betrieb

**Update:** HACS → *Intervals.icu* → aktualisieren → HA neu starten → Browser **hart** neu
laden. Der Service Worker des HA-Frontends bedient Module aus eigenem Speicher, an Strg+F5
vorbei: F12 offen lassen, Rechtsklick auf Reload → „Cache leeren und vollständig
aktualisieren". Gegenprobe im Inkognito-Fenster.

**Cache:** `PANEL_VERSION` in `const.py` hängt an der Modul-URL. Wer das Panel ändert, ohne
die Zahl zu erhöhen, sieht weiter die alte Fassung.

**Rückzieher:** In HACS lässt sich jede frühere Version wählen. Zusätzlich liegt eine
Sicherungskopie des Ordners auf dem PC.

**Diagnose:**
- Archivstand: Sensor „Archiv"
- Log: `custom_components.intervals_icu`
- Panel-Fehler: Browser-Konsole (F12)

**Datenhaltung:** Archiv in `.storage/intervals_icu.<athlet>`, API-Key im Config-Entry.
Beides überlebt ein Update.
