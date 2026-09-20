# Belegter Rechenweg für alle Ableseverfahren

> **BESCHRIFTUNG, nachgetragen am 19.09.2026 (0.63.3).** Alle Zahlen dieser
> Datei und der Runden vom 17./18.09. zur 120-s-Paarung sind **am gedünnten
> Strom über GANZE Fahrten** gerechnet. Die Produktion rechnet auf den
> **markierten Abschnitten** am vollen Strom. Der Trockenlauf am Livebestand
> (19.09.2026, 17 Fahrten) liefert deshalb andere Zahlen: verkehrte Steigungen
> 14 → **8 von 27** (gemeldet 14 → 0 von 25), Median-R² 0,098 → **0,324**
> (gemeldet 0,092 → 0,752), Kopfzahl 149,6 → **147,6 W** (gemeldet ~156,6 W —
> sie sinkt). Beide Reihen sind richtig gerechnet und beantworten verschiedene
> Fragen; wer sie gegeneinanderhält, hält ganze Fahrten gegen Ausschnitte.
> Wo unten eine Zahl ohne Zusatz steht, ist die erste Lesart gemeint.

**Stand:** 18.09.2026 · gegen `main` = `07df34a` (0.62.2) · Prüfstand 22 Dateien /
7.241 Prüfungen / 0 Fehler, selbst nachgefahren.
**Auftrag:** PROJEKTSTAND §10 Punkt 11. Eine LISTE, kein Bau. Kein Code, keine
Version, kein Verhalten geändert.
**Nachtrag 18.09.2026, abends:** die Rampen-Lesart ist entschieden (§7 Fall 39) —
K1.4 trägt die Entscheidung, K1.5 ist berichtigt. Beides unten markiert.

**Wie zu lesen:** je Verfahren eine Tabelle mit vier Spalten. Spalte 1 nennt die
Stelle in der Quelle und den Lesestand. Spalte 2 nennt Datei und Zeile, am Code
nachgesehen. Spalte 3 beziffert die Abweichung am Livebestand oder sagt
„NICHT PRÜFBAR" mit Grund. Spalte 4 urteilt: SETZUNG · VERSEHEN ·
DECKUNGSGLEICH · UNBELEGT.

**Was simuliert wurde:** jede bezifferte Behauptung in Spalte 3. Die Simulationen
stehen unter jeder Tabelle, gezählt und benannt. Die Rampen-Kausa konnte
vollständig im Container gerechnet werden — `tests/data/ramp_i187258578.json`
trägt den 1-Hz-Strom der Aktivität vom 16.09. (2.735 Punkte, alpha/Watt/Puls,
lückenlos). **Für K1 wurde HEIMDALL nicht gebraucht.** Für K2/K3/K4 fehlt der
Livebestand im Container; was davon abhängt, steht als NICHT PRÜFBAR.

---

## K1 · Stufentest

Betroffen: `ramp.py` — `segment()` (Z. 371), `_fit()` (Z. 417), `at()` (Z. 480,
innerhalb `measure()`), `protocol()` (Z. 284), sowie `RAMP_START/END_CHAIN` in
`steering.py`.

### K1.1 · Der Fit-Bereich (wo die Gerade anfängt)

| 1 · WAS DIE QUELLE MACHT | 2 · WAS WIR MACHEN | 3 · ABWEICHUNG, BEZIFFERT | 4 · URTEIL |
|---|---|---|---|
| **Rogers 2021a** (Front Physiol 11:596567, Methoden) legt die Gerade über den nahezu linearen Abfall von etwa 1,0 bis etwa 0,5, Abschnitt nach Augenschein. **Laufband.** *Lesestand: Volltext (16.09., laut Modulkopf `ramp.py` Z. 8–11).* **Rogers 2021b** (JFMK, 0,5) ebenso, „1,0 bis 0,5 oder tiefer, solange die Werte gerade bleiben". **Laufband.** *Lesestand: Volltext.* **Olieslagers 2026** (Physiol Rep, Rad, 4-min-Stufen): vom Beginn des nahezu linearen Abfalls bis zum letzten Zeitpunkt. Ob der Beginn von Hand gesetzt wird: **nicht nachgelesen.** *Lesestand: Ausschnitt des Methodenteils.* | `ramp.segment()` Z. 383 ruft `_peak(smooth, first_index, last_index)`; `_peak()` Z. 359 nimmt den **höchsten Wert der geglätteten Kurve ab Rampenbeginn** (`RAMP_WARMUP_MIN` = 15 min), bei Gleichstand die späteste Stelle. Ende ist das Lastende aus `protocol()` (Länge minus `RAMP_COOLDOWN_MIN` = 10 min). Am echten Strom: Hochpunkt **t = 1058 s, α = 1,662**; Lastende **t = 2134 s**. Der Punkt, an dem α erstmals unter 1,0 fällt, liegt bei **t = 1302 s** — der Fit beginnt also **244 s vor** dem Bereich, den Rogers benennt. | **Gerechnet, S1.** α = 0,75: heute **213 W / 178 bpm** (t = 1630 s) gegen ab-1,0 **205 W / 176 bpm** (t = 1542 s) → **+8 W, +2 bpm**. α = 0,50: heute **233 W** gegen **235 W** → **−2 W**. Steigung −0,0649/min gegen −0,0448/min, r² **0,815 gegen 0,650**. Rampensteigung gemessen 5,69 W/min, also 1 s Fehler = 0,095 W. | **SETZUNG, jetzt begründbar — aber unbeschriftet.** Der Modulkopf nennt die Abweichung („der Startpunkt wird hier automatisch gesucht"), die **Karte im Panel nennt sie nicht**. Und die Begründung in §10 Punkt 10 („Plateau im Fit → Gerade zu flach, unten zu hoch") ist **am Bestand widerlegt**: der Hochpunkt-Start macht die Gerade **steiler**, nicht flacher, und r² **besser**, nicht schlechter. Der Fit beginnt nicht im Plateau — er beginnt dort, wo der Abfall am steilsten ist. |

### K1.2 · Die Fit-Achse (Zeit oder Herzfrequenz)

| 1 · QUELLE | 2 · WIR | 3 · ABWEICHUNG | 4 · URTEIL |
|---|---|---|---|
| **Rogers 2021a**: über die **ZEIT** für VO₂ **und** gegen die **HERZFREQUENZ** für HF — beide Achsen, je nach Zielgröße. **Rogers 2021b**: gegen die **HERZFREQUENZ**. **Olieslagers 2026**: über die **ZEIT**. *Lesestände wie oben.* | `ramp._fit()` Z. 417–423: `xs.append(float(index * step))` — regressiert gegen die **Zeit**, immer, für beide Schwellen. Die Herzfrequenz wird nur als Ableseachse benutzt (`_window_median(heartrate, index, half)`, Z. 492). | **Gerechnet, S2.** α = 0,75 gegen HF statt Zeit, gleicher Bereich: **177 bpm / 205 W** gegen **178 bpm / 213 W** → **−8 W, −1 bpm**. α = 0,50: **186 bpm / 228 W** gegen **186 bpm / 233 W** → **−5 W, ±0 bpm**. r² gegen HF **0,850** gegen Zeit 0,815. **Beide Abweichungen zusammen** (Rogers-treu: ab 1,0, gegen HF): α = 0,75 → **199 W**, gegen heute 213 W = **−14 W**. | **SETZUNG (Olieslagers-Fassung), unbeschriftet an der Karte.** Die Wahl ist begründbar: Olieslagers ist die einzige RAD-Arbeit der drei, und die Zeitachse ist die ihre. Aber der Puls ist bei diesem Athleten die knappere Größe (HRVT1 bei 178 bpm, Maximum 194), und die HF-Achse trifft ihn direkter. Für den Puls ist die Zeitachse ein Umweg. |

### K1.3 · Die personalisierte Schwelle (dritte Zahl)

| 1 · QUELLE | 2 · WIR | 3 · ABWEICHUNG | 4 · URTEIL |
|---|---|---|---|
| **Rogers 2024**: mittig zwischen „the maximum seen during the **early ramp incremental**" und 0,5. Was „früh" heißt, steht im Abstract nicht. *Lesestand: **nur Abstract**, Volltext nicht frei zugänglich.* **Olieslagers 2026** setzt es um als höchster Wert **am Beginn des linearen Abfalls**: HRVT1pers = (max. DFAa1start + 0,5)/2. *Lesestand: Ausschnitt.* | `ramp.measure()` Z. 495: `pers_alpha = (peak + DFA_ANAEROBIC) / 2.0`, mit `peak` = derselbe Hochpunkt aus `segment()`. Am echten Strom: (1,662 + 0,5)/2 = **α = 1,081 → 183 W / 167 bpm bei t = 1324 s**. | Ein Maximum **in einem Zeitfenster** (Rogers) und ein Maximum **an einem Kurvenpunkt** (Olieslagers) sind nicht dasselbe. Hier fallen sie nur zusammen, **weil der Abfallbeginn per Setzung als Hochpunkt definiert ist** — nicht weil es gezeigt wäre. **Nicht beziffert**, weil dafür Rogers' Volltext fehlt: ohne die Definition von „früh" gibt es keine Vergleichszahl. | **SETZUNG, korrekt beschriftet.** Der Modulkopf `ramp.py` Z. 51–66 sagt das Nötige und nennt sich „Operationalisierung aus zweiter Hand". Das ist die sauberste Stelle des ganzen Moduls. **Hinweis zu §10 Punkt 0:** die 183 W liegen bei α = 1,081, nicht bei 0,75 — dass sie zu den Blöcken passen, belegt für α = 0,75 nichts. Der Satz in §10 stimmt. |

### K1.4 · Erste gegen dauerhafte Unterschreitung

| 1 · QUELLE | 2 · WIR | 3 · ABWEICHUNG | 4 · URTEIL |
|---|---|---|---|
| Keine der gelesenen Arbeiten liest die Schwelle als **Unterschreitung** ab — alle legen eine Gerade und schneiden. Die Frage „erste oder dauerhafte" ist eine Frage, die aus **unserem** Prüfstein stammt, nicht aus der Literatur. | Wir lesen ebenfalls am Schnittpunkt ab (`at()`, Z. 480). Die Unterschreitung wird nur als **Prüfstein** gegen den Schnitt gehalten (§10 Punkt 0, Kreuzprobe Runde 3). `RAMP_FLAT_S` = 60 s ist die Dauer, ab der „Boden erreicht" gilt (`segment()` Z. 394). | **Gerechnet, S3.** Bei 30 s Glättung: α = 0,75 **erste** Unterschreitung t = 1447 s / **193 W** / 174 bpm; **dauerhafte** (60 s) t = 1631 s / **213 W**. Die Gerade liegt bei **1630 s / 213 W** — sie trifft die **dauerhafte** Unterschreitung **auf 1 Sekunde und 0 Watt**. Differenz erste↔dauerhaft: **20 W**. Bei α = 0,50 fallen erste und dauerhafte zusammen (t = 1807 s / 226 W), die Gerade liegt bei 233 W → **+7 W**. **Nachgerechnet 18.09.: die 217 W aus §7 Fall 39 und diese 213 W widersprechen sich nicht.** Fall 39 rechnet am **gedünnten** Strom (Stufe 4 s) über 20-s-Klassen; dort liegt die letzte Klasse über 0,75 bei 1640 s, dauerhaft ab 1660 s = **216 W**. Die **4 W sind Auflösung, nicht Lesart.** Dazu: bei 30 s Glättung fallen die beiden denkbaren Definitionen von „dauerhaft" (60 s ununterbrochen darunter · letzte Rückkehr darüber) auf **dieselbe Sekunde**; bei 60 s Glättung nicht (1447 gegen 1645 s). Die Glättungsbreite entscheidet mit, und sie ist eine Setzung. | **SETZUNG — ENTSCHIEDEN (Johannes, 18.09.2026, §7 Fall 39): die DAUERHAFTE Unterschreitung ist der Prüfstein.** Aus der Literatur folgt das nicht; es ist die Feststellung, dass unsere beiden eigenen Verfahren dasselbe sagen, sobald die erste Unterschreitung nicht als Messwert genommen wird. Die Entscheidung betrifft den **Prüfstein**, nicht die Produktion: `ramp.at()` liest weiter an der Geraden ab, `RAMP_FLAT_S` bleibt 60 s, keine Zeile Code geändert. |

### K1.5 · Die Abweichung 1649 gegen 1705 s (§10 Punkt 10c)

**Sie ist gegenstandslos.** Am heutigen Code (`ramp.measure`, 0.62.2, Rechenweg e1)
liegt der Schnitt mit 0,75 bei **1630 s**, nicht bei 1649 und nicht bei 1705. Beide
Zahlen aus §10 stammen aus der Fassung **vor** e1 (Johannes' Nachrechnung: Segment
224 → 1807 s, Hochpunkt 1,731, Gefälle −0,0413/min, r² 0,716). Der heutige Lauf
liefert Segment **1058 → 2134 s**, Hochpunkt **1,662**, Gefälle **−0,0649/min**,
r² **0,815**.

**BERICHTIGUNG 18.09.2026:** die erste Fassung dieser Liste schrieb „nicht aufgelöst,
nur verschwunden". **Das war falsch — die Frage war bereits geklärt.**
`NAECHSTER_CHAT.md` Z. 229–232 hält seit dem 16.09. fest: **1705,2 s ist der Schnitt der
GERADEN** (`at()`), das 30-s-Fenster betrifft nur Watt und Puls; Johannes' Nachrechnung war
in **beiden** Schnitten um konstant **56 s** verschoben (1649/1705,2 und 2012/2068,7) bei
gleicher Steigung — ein **Zeitachsenversatz, keine Ablesemethode**. Die Ursache des Versatzes
ist unbelegt und bleibt es.

**URTEIL: doppelt erledigt — inhaltlich am 16.09., zusätzlich gegenstandslos durch e1.**
Der eigentliche Befund ist ein anderer: **§10 Punkt 10c stand noch als offen, während die
Übergabe die Frage längst als geklärt führte.** Zwei Dokumente, eine Frage, zwei Stände.
Das ist dieselbe Klasse wie der `SOURCE_CHAIN`-Befund unter K4. **Doku-Befund, kein
Codefehler.** Beide Stellen sind mit diesem Commit berichtigt.

### K1.6 · Der Widerspruch „reached_anaerobic true, hrvt2 null" (§10 Punkt 10)

Ebenfalls **erledigt durch e1**. Der heutige Lauf liefert `hrvt2` = **233 W / 186 bpm
bei 1861 s**, `contradiction` = `None`. Der Wächter (`measure()` Z. 525) steht und ist
unter e1 nur noch mit einer Mulden-Fixture auslösbar — so ist er auch beschriftet.
**URTEIL: DECKUNGSGLEICH mit dem, was §10 als gebaut meldet.**

---

### Simulationen zu K1 — 5 Läufe, alle gerechnet

**S1 · Fit-Bereich, Variantenrechnung am Livebestand.** Sechs Varianten über den
echten Strom, mit den Produktionsfunktionen `ramp._clean`, `_smooth`, `_peak`,
`_fit`, `_window_median`:

| Variante | n | Steigung | r² | α = 0,75 | α = 0,50 |
|---|---|---|---|---|---|
| **V0 heute** Hochpunkt→Lastende, Zeit | 1077 | −0,0649/min | **0,815** | 1630 s · **213 W** · 178 bpm | 1861 s · **233 W** · 186 bpm |
| V1 ab 1,0→Lastende, Zeit | 833 | −0,0448/min | 0,650 | 1542 s · 205 W · 176 bpm | 1877 s · 235 W · 186 bpm |
| V2 ab 1,0→erster <0,5, Zeit | 506 | −0,0500/min | 0,370 | 1546 s · 206 W · 176 bpm | außerhalb |
| V3 Hochpunkt→Lastende, **HF** | 1077 | −0,0300/bpm | **0,850** | 177 bpm · 205 W | 186 bpm · 228 W |
| V4 ab 1,0→Lastende, **HF** | 833 | −0,0231/bpm | 0,648 | 175 bpm · 199 W | 186 bpm · 232 W |
| V5 ab 1,0→erster <0,5, **HF** | 506 | −0,0238/bpm | 0,356 | 176 bpm · 199 W | außerhalb |

**Spanne über alle Varianten: α = 0,75 → 199–213 W (14 W). α = 0,50 → 228–235 W (7 W).**

**S2 · Prüfstein: die gemessene Kreuzung, über 6 Glättungsbreiten** (15/30/45/60/90/120 s).
Die dauerhafte Unterschreitung bei α = 0,75 liegt zwischen 193 und 216 W, die Gerade
(V0) bei 213 W. Bei 60 s und 90 s Glättung fallen erste und dauerhafte zusammen (193 W)
— **die Glättungsbreite entscheidet mit**, und 30 s ist eine Setzung
(`RAMP_SMOOTH_S`). α = 0,50 ist über alle Breiten stabil bei 226–240 W.

**S3 · Leave-one-out.** Bei K1 gibt es **eine** Einheit — ein Leave-one-out über
Einheiten ist nicht bildbar. **Ersatz: Parameter-Leave-one-out** über die Glättungsbreite
(S2) und über den Fit-Bereich (S1). **Richtung kippt nicht:** in allen 6 Varianten und
allen 6 Glättungsbreiten liegt α = 0,50 über α = 0,75 und beide über den Blockwerten.

**S4 · Synthetik mit bekannter Wahrheit, 3 Kurvenformen × 2 Zielwerte × 5 Seeds = 30 Läufe.**
Fehler gegen die wahre Kreuzung, in Sekunden:

| Form | Ziel | V0 Hochpunkt | V1 ab 1,0 | V2 ab 1,0→<0,5 |
|---|---|---|---|---|
| linear | 0,75 | **−0 s** | −2 s | −1 s |
| linear | 0,50 | **+1 s** | −1 s | kein Schnitt |
| konvex | 0,75 | **+53 s** | **+13 s** | +10 s |
| konvex | 0,50 | +23 s | +28 s | −14 s |
| konkav | 0,75 | −6 s | −7 s | −3 s |
| konkav | 0,50 | **+60 s** | **−0 s** | kein Schnitt |

**Gegenprobe (Wahrheit muss treffbar sein):** rauschfrei + linear → V0 und V1 treffen
beide auf **1 Sekunde** genau, r² = 1,0000. Das Verfahren kann die Wahrheit finden;
die Fehler oben sind Form-Fehler, keine Rechenfehler.

**S5 · Welche Form hat der echte Abfall?** Quadratischer Fit über das Segment:
α(t) = 1,5631 − 0,002168·t **+ 1,009 × 10⁻⁶ · t²** → **konvex**, oben steiler.
Steigung in Dritteln: **−0,117 / −0,043 / −0,027 pro Minute**. Der erste Abschnitt fällt
**4,4-mal so steil** wie der letzte.

**Was S4 und S5 zusammen sagen:** der echte Strom ist genau die Form, in der V0 in der
Synthetik am schlechtesten abschneidet (+53 s bei α = 0,75). Umgerechnet mit der
gemessenen Rampensteigung von 5,69 W/min sind 53 s = **5,0 W**. Die real gemessene
Differenz V0 ↔ V1 ist **8 W** — dieselbe Größenordnung, dieselbe Richtung.
**Der Hochpunkt-Start liest α = 0,75 systematisch zu hoch ab, um rund 5 bis 8 Watt.**

Dass r²(V0) trotzdem größer ist als r²(V1), ist **kein Gegenargument**: das große r²
kommt vom steilen ersten Drittel, das den Hebel der Regression stellt. Ein besseres r²
über einen falschen Bereich ist kein besserer Schätzer. Das ist die eigentliche Antwort
auf §10 Punkt 10 — die Vermutung dort war richtig, die Begründung („Gerade zu flach")
war falsch herum.

---

## K2 · Blockmessung

Betroffen: `const.py` Z. 130–182, `derive.py` Z. 847–905 (`dfa_blocks`),
`blocks.py` Z. 196–198 (Mediane), `steering.py` (C6, t-Band).

| 1 · QUELLE | 2 · WIR | 3 · ABWEICHUNG | 4 · URTEIL |
|---|---|---|---|
| **Rogers 2021** (Front Sports Act Living), zitiert in `const.py` Z. 131–133: die ersten zwei Minuten sind nicht im metabolischen Gleichgewicht, geeignet sind die Werte bei Minute 4 und 6. *Lesestand: **nicht im Volltext gelesen** — das Zitat steht im Code, die Stelle ist in dieser Sitzung nicht nachgeschlagen worden.* **Andriolo 2024** (Sensors 24:4468), Abschnitt 2.3 „Fatigue Consideration": nur Minute **5 bis 20** je Einheit. *Lesestand: **Volltext**, 18.09. gelesen.* | `BLOCK_WARMUP_DISCARD_S = 120` (`const.py` Z. 138), angewandt in `derive.py` Z. 871: `kept = start + BLOCK_WARMUP_DISCARD_S / max(sample_secs, 1)`. Danach Median je Block (`blocks.py` Z. 196–198). Steuergröße ist der Median **ab Block 2** (`STEERING_FIRST_BLOCK_COUNTS = False`, `const.py` Z. 193). | **Der Andriolo-Grund ist falsch zitiert.** Andriolo schließt die ersten 5 Minuten aus, weil der **Brustgurt noch nicht genug Feuchtigkeit** hat und die Gurtposition in den ersten Minuten justiert wird — also wegen **HRV-Artefakten**, nicht wegen metabolischen Gleichgewichts. Der Code-Kommentar sagt „aus demselben Grund". Das ist er nicht. **Wirkung in Watt: null** — die Zahl 120 s bleibt dieselbe, nur ihre Begründung trägt zur Hälfte nicht. | **VERSEHEN, folgenlos für die Zahl.** Der Kommentar in `const.py` Z. 134 gehört korrigiert: Andriolo begründet mit Artefakten, Rogers mit Gleichgewicht. Beide Gründe stützen ein Verwerfen, aber sie sind nicht derselbe Grund. |
| — | Der Kommentar `const.py` Z. 135–137 sagt: „AM EIGENEN BESTAND BESTÄTIGT: der Anlauf endet bei 90–120 s … **Bei SweetSpot dauert er länger, die publizierte Grenze deckt also den langsameren Fall mit ab — sie bleibt.**" | **Der Satz ist logisch verdreht.** Wenn der Anlauf bei SweetSpot **länger** dauert als 120 s, dann deckt eine Grenze von 120 s ihn gerade **nicht** ab — sie schneidet zu früh, und der Median trägt noch Anlauf. Der Satz behauptet das Gegenteil seiner eigenen Beobachtung. **NICHT PRÜFBAR in Watt:** dafür bräuchte es den 1-Hz-Strom einer SweetSpot-Fahrt; im Container liegt nur die Rampen-Fixture. | **VERSEHEN, Wirkung unbekannt.** Die Richtung ist bekannt: zu kurz verworfen heißt Median **zu hoch** (der Anlauf trägt das höhere alpha, `blocks.py` Kopf Z. 6–17). Wie viel, ist offen. **Das ist die erste Zahl, die am Livebestand nachzurechnen ist** — je SweetSpot-Block die Mediane in 30-s-Segmenten, wie es `const.py` Z. 135 für VO2max schon getan hat. |
| **Die Korridore.** `const.py` Z. 147–152 beschriftet `BLOCK_CORRIDORS` ausdrücklich als „SETZUNG AUS DER PRAXIS DES ATHLETEN, nicht aus einer Studie". **Die Literatur gibt DFA-Zonen als GRENZEN, nicht als Korridore je Trainingsfamilie:** Zone 1 „moderat" bis zur aeroben Schwelle, Zone 2 „schwer" darüber bis zur anaeroben, Zone 3 „schwer/severe" darüber — mit den diskreten Werten 0,75 und 0,5 als Grenzen. *Lesestand: Volltext Andriolo 2024, Einleitung; dazu Rogers 2020/2021a im Abstract.* | `BLOCK_CORRIDORS`: vo2max 0,20–0,50 · sweetspot 0,50–0,75 · tempo 0,75–1,00. | **Teils deckungsgleich, teils erfunden.** Deckungsgleich: 0,50–0,75 ist exakt Zone 2 des Drei-Zonen-Modells, unter 0,50 exakt Zone 3. **Nicht deckungsgleich:** (a) die **Untergrenze 0,20** für VO2max steht in keiner gelesenen Quelle — sie ist frei gesetzt; (b) **„Tempo" bei 0,75–1,00**: ein alpha ÜBER 0,75 heißt eine Intensität UNTER der aeroben Schwelle — also Zone 1, die Grundlagenzone. Die Familie heißt Tempo und liegt physiologisch in der Grundlage. | **§10 Punkt 0 Schritt 2 ist damit beantwortet: die Literatur gibt WEDER alpha-Korridore je Familie NOCH einen Anteil einer Schwelle — sie gibt zwei Grenzen und drei Zonen.** Unsere Korridore sind eine SETZUNG, und sie ist korrekt so beschriftet. Aber der Zuschnitt „vier Familien in drei Zonen" ist eine zweite Setzung obendrauf, und **die ist nirgends beschriftet**. Besonders Tempo/0,75–1,00 verdient einen Satz an der Karte. |

### Simulationen zu K2

**NICHT PRÜFBAR — Grund: fehlende Daten.** Alle drei bezifferbaren Behauptungen
(Anlaufdauer bei SweetSpot, Median-Verschiebung, Korridorwirkung auf C6) brauchen
den 1-Hz-Strom markierter Block-Fahrten. Der Container trägt nur die Rampen-Fixture.
Der Zugriff auf HEIMDALL wäre über ein nur lesendes Custom-Tool möglich und war
freigegeben — **er wurde nicht genutzt**, weil K1 vollständig im Container lief und
eine Freigabe nur dann in Anspruch genommen wird, wenn sie das Ergebnis trägt.
**Für die nächste Sitzung:** `tests/data/` um den Strom einer SweetSpot-Fahrt
erweitern, dann läuft K2 genauso im Container wie K1.

---

## K3 · Ermüdungskurve und ihre Grundlage

Betroffen: `derive.py` Z. 270–300 (`_read_at`, `DFA_BIN_WIDTH`, `FATIGUE_MIN_BINS`),
Z. 457–480 (p075-Zweig), `fatigue.py` Z. 49–60 (Gallo-Form), Z. 479–520 (Anker).

**Quelle durchgehend: Andriolo, Rummel, Gronwald, Sensors 2024, 24, 4468.
Lesestand: VOLLTEXT, am 18.09.2026 gelesen.** Das ist die einzige Kausa, in der die
Quelle in dieser Sitzung im Volltext gegen den Code gehalten wurde.

| 1 · QUELLE (Abschnitt) | 2 · WIR (Datei, Zeile) | 3 · ABWEICHUNG | 4 · URTEIL |
|---|---|---|---|
| **2.3, letzter Absatz / 4. Diskussion:** das gewählte Modell wird nur verwendet, wenn das Bestimmtheitsmaß 0,75 übersteigt, was einen robusten Fit anzeigt. Abb. 5 zeigt ausschließlich Gruppen mit R² > 0,75. | **Es gibt keine R²-Schranke.** `derive.py` Z. 467–480: `row["p075"]` wird gesetzt, sobald `len(mids) >= FATIGUE_MIN_BINS` (= 3) und 0,75 im Bereich liegt. `row["r2"]` wird **berechnet und gespeichert** (Z. 479) — und von **niemandem gelesen**: `grep -rn 'r2' derive.py fatigue.py blocks.py` findet keine einzige Schranke, keinen Vergleich, kein `if`. | **Die größte Abweichung im ganzen System.** Laut §10-Auftragstext: 27 Fahrtstunden, **14 mit positiver Steigung**, **keine ≥ 0,75**. Wenn das stimmt, trägt **kein einziger** Stundenfit Andriolos Gültigkeitskriterium — und die gesamte Ermüdungskurve steht auf Fits, die die Quelle verworfen hätte. **NICHT PRÜFBAR in Watt im Container** (kein Archiv), aber **am Code vollständig belegt**: die Schranke existiert nicht. | **VERSEHEN, und das schwerste.** Eine positive Steigung heißt: mehr Leistung bei höherem alpha — physiologisch verkehrt herum. Dass 14 von 27 so liegen, ist kein Rauschen, sondern ein Befund. **Die Kurve meldet als „gemessen", was nach dem Maßstab ihrer eigenen Quelle nicht messbar war.** Das ist dieselbe Klasse wie §7 Fall 13 und §10 Punkt 7. |
| **2.3, „Data Segmentation":** für Einzeleinheiten acht gleich lange Intervalle im Bereich [a1min, a1*], a1* das Kleinere aus 1,2 und dem Maximum; für Einheitengruppen neun Intervalle innerhalb [a1min, 1,0] und fünf im Bereich [1,0, a1*] — also **gleich viele Intervalle, variable Breite**. | `derive.py` Z. 273: `DFA_BIN_WIDTH = 0.05` — **feste Breite, variable Anzahl**. | Bei einem Stundenverlauf, der von α = 1,2 bis 0,6 reicht, ergibt feste Breite 0,05 **zwölf** Bins; Andriolo bildete acht über denselben Bereich. Bei schmalem Bereich (etwa 0,9–0,7) ergeben sich **vier** Bins gegen Andriolos acht. **Wirkung: NICHT PRÜFBAR in Watt** ohne Archiv, aber die Richtung ist klar — schmale Bereiche werden bei uns **dünner** besetzt, breite dichter. | **SETZUNG, korrekt beschriftet.** `derive.py` Z. 272 sagt es selbst: „Width and minimum count are house settings: the published work bins by group, not by a stated width." Vorbildliche Stelle. |
| **2.3, „Representative Points":** für Einzeleinheiten wird ein Repräsentant nur berechnet, wenn das Intervall mindestens acht Datenpunkte enthält, für Einheitengruppen mindestens zehn. | **Es gibt keine Mindestpunktzahl je Bin.** `derive.py` Z. 287–289 mittelt jedes Bin, gleich wie viele Punkte drinstehen. `FATIGUE_MIN_BINS = 3` ist die Mindestzahl **der Bins**, nicht der Punkte darin. | Ein Bin mit **einem** Punkt zählt bei uns genauso schwer wie eines mit hundert. Bei 1-Hz-Daten über eine Fahrtstunde sind die Randbins (sehr hohes und sehr tiefes alpha) typischerweise die dünnsten — und sie stellen den **Hebel** der Regression. **NICHT PRÜFBAR in Watt** ohne Archiv. | **VERSEHEN.** Der Nachbau ist billig (eine Zeile: `if len(items) >= N`), und er greift genau dort, wo p075 am empfindlichsten ist. Kandidat für den ersten Fix nach der R²-Schranke. |
| **2.3, „Fatigue Consideration":** nur Minute 5 bis 20 jeder Einheit — 15 Minuten, früh in der Fahrt. | Wir rechnen p075 **je Fahrtstunde** über die **ganze** Stunde (`derive.dfa_hours`), und `fatigue.curve()` (Z. 354 ff.) setzt gerade diese Stunden **gegeneinander**, um den Abfall zu sehen. | **Das ist keine Abweichung, sondern eine Umkehrung des Zwecks.** Andriolo schließt späte Minuten aus, **um Ermüdung zu vermeiden**. Wir messen die Ermüdung selbst — dafür müssen die späten Stunden gerade drinbleiben. Wirkung in Watt nicht angebbar, weil es keine gemeinsame Größe gibt. | **SETZUNG, begründet, aber unbeschriftet.** Der Modulkopf `fatigue.py` Z. 5–7 nennt Andriolo als Quelle der **Repräsentantenmethode** und sagt nicht dazu, dass Andriolos Ausschlusskriterium hier bewusst umgedreht ist. Ein Satz fehlt. |
| **2.4 Statistik:** Spearmans r, weil die Variablen nicht normalverteilt sind und ein nichtlinearer Zusammenhang vermutet wird; zusätzlich **linear UND hyperbolisch**, Modellwahl nach dem R² näher an 1,0. | `derive.py` Z. 474–480: nur **lineare** Regression, r² nach Pearson-Art. Kein hyperbolisches Modell. | Andriolo fand Mittelwerte von 0,59 (linear) und 0,64 (hyperbolisch) im dynamischen Bereich — der hyperbolische Fit war im Mittel **besser**, und die Arbeit wählt je Fall das bessere. Wir haben nur eines. **NICHT PRÜFBAR in Watt** ohne Archiv. | **SETZUNG, unbeschriftet.** Andriolo wählt selbst am Ende das lineare Modell „for its simplicity" — die Wahl ist also gedeckt. Dass sie eine Wahl ist, steht bei uns nirgends. |
| **Die Kopfzahl „ausgeruht, bei Dauer null: 173 W".** | `fatigue.py` Z. 495/498: `base = tail["watts"] / literature_factor(...)` — der letzte getragene Kettenpunkt, mit der Gallo-Form auf Dauer null zurückgerechnet. | §10 Punkt 7 meldet das als **ERLEDIGT in 0.58.1**. **Gegengeprüft:** `anchor_base` existiert weiter (Z. 605), aber `test_panel_fixes.js` schließt ihn seit 0.58.1 namentlich aus und prüft, dass die Kopfzahl der **erste Leitzahl-Punkt mit seiner eigenen Belegung** ist. Der Auftrag fragt: was wäre sie gemessen? **Gemessen in Stunde 1: 149,6 W** (§10 Punkt 7) gegen gerechnet **173 W** → **23,4 W**, die eine Rechnung und keine Messung waren. | **ERLEDIGT — aber die Zahl gehört in die Übersicht,** weil sie den Maßstab setzt: 23,4 W ist die größte belegte Einzelabweichung, die dieses Projekt je an sich selbst gefunden hat. Sie steht hier als Vergleichsgröße für alles andere in dieser Liste. |

### Simulationen zu K3

**NICHT PRÜFBAR — Grund: fehlende Daten.** Alle fünf bezifferbaren Behauptungen
brauchen das Archiv (`.storage/intervals_icu.<athlet>`) oder die Stundenverläufe.
Die entscheidende Zahl — **wie viele der 27 Fahrtstunden hätten Andriolos R² > 0,75
bestanden** — steht als Behauptung im Auftragstext (§10: keine) und ist **in dieser
Sitzung nicht nachgerechnet worden**. Sie ist die erste, die nachzurechnen ist:
sie entscheidet, ob die Ermüdungskurve überhaupt eine Messung ist.

**Was geprüft wurde und trägt:** dass es im Code **keine R²-Schranke gibt**. Das ist
am Quelltext belegt, nicht erschlossen — `grep` über `derive.py`, `fatigue.py`,
`blocks.py` findet keinen Vergleich gegen r².

---

## K4 · Anker

Betroffen: `coach.py` Z. 393–442 (`anchors`), `workouts.py` Z. 629–636
(`SOURCE_CHAIN`), `docs/ausbau.md` Z. 4487 ff. (B2b-3 Vorrechnung).

| 1 · QUELLE | 2 · WIR | 3 · ABWEICHUNG | 4 · URTEIL |
|---|---|---|---|
| **Keine.** Für „Ganzfahrt-Regression" — die Rampenmethode auf Fahrten **ohne** Rampe anzuwenden — findet sich in den gelesenen Arbeiten nichts. Andriolo kommt dem am nächsten, aber mit **anderer Bauart**: Einheiten werden zu Gruppen innerhalb eines 10-Tage-Fensters zusammengefasst, nur Gruppen mit mindestens vier Einheiten. *Lesestand: Volltext.* | `coach.anchors()` Z. 393–442: Median der letzten fünf Ganzfahrt-Ablesungen. Laut `docs/ausbau.md` Z. 4489: **160 bpm / 146 W** aus fünf Fahrten (27.08./30.08./01.09./04.09./13.09.). | **Wir gruppieren nach Anzahl (letzte 5), Andriolo nach Zeitfenster (10 Tage).** Die fünf genannten Fahrten spannen **17 Tage** — knapp doppelt so lang wie Andriolos Fenster, das er ausdrücklich begrenzt, um den Einfluss physiologischer Anpassung auf die Kurzzeitanalyse zu vermeiden. **NICHT PRÜFBAR in Watt** ohne Archiv. | **UNBELEGT.** Es gibt keine Quelle für die Ganzfahrt-Regression in unserer Bauart. Die nächstliegende Quelle baut anders und begründet ihre Bauart. Das gehört an die Karte. |
| — | **SOURCE_CHAIN, am Code nachgesehen (`workouts.py` Z. 629–636):** vo2max/sweetspot → `blocks`, `ftp`. tempo/threshold → `ftp`. endurance/long → `curve`, `ftp`. | **Der Stufentest steht in KEINER Kette.** `NAECHSTER_CHAT.md` (Stand 16.09.) beschreibt noch `ramp_hrvt2` als zweite Stufe für vo2max/sweetspot und `ramp_hrvt1` für endurance/long. Am Code von 0.62.2 sind beide **fort** — konsistent mit §7 Fall 38 („seit 0.60.0 steuert der Stufentest nichts") und mit §10 Punkt 0. | **DECKUNGSGLEICH mit §10, aber `NAECHSTER_CHAT.md` ist veraltet.** Wer nur die Übergabe liest, hält den Stufentest für eine Quelle. Er ist keine. **Doku-Befund.** |
| **Umgebung.** Keine der gelesenen Arbeiten mischt Labor- und Feldbedingungen für einen Anker. Andriolo erhebt ausschließlich Feld, Rogers 2021a/b ausschließlich Labor (Laufband). | §10 Punkt 9: **10 der 12 kurventragenden Fahrten sind draußen**, Tempo und SweetSpot auf der Rolle. Die Rampe vom 16.09. ist Rolle. | **Der Anker aus Grundlagenfahrten setzte ein ROLLEN-Pulsfenster aus DRAUSSEN-Daten.** Das ist in §10 Punkt 9 benannt und der Grund, warum B2b-3 zurückgestellt ist. **NICHT PRÜFBAR in Watt** ohne Archiv — aber die Richtung ist bekannt: draußen liegt bei gleicher Leistung der Puls typischerweise tiefer (Kühlung, Rollwiderstand wechselt, keine ERG-Klemme). | **Richtig zurückgestellt.** Das ist die eine Stelle, an der dieses Projekt eine Abweichung erkannt und den Bau **angehalten** hat, statt sie zu beschriften. Als Verfahren ist das die beste Stelle der vier Kausas. |

### Simulationen zu K4

**NICHT PRÜFBAR — Grund: fehlende Daten.** Die vom Auftrag verlangte Rechnung
(„was ergibt der Anker aus Rollen-Fahrten gegen Draußen-Fahrten") braucht das Archiv.
Im Container liegt keine einzige Grundlagenfahrt.

---

## Übersicht

### Alle VERSEHEN, nach Größe der Wirkung

| # | Stelle | Wirkung | Belegt durch |
|---|---|---|---|
| 1 | **K3 · keine R²-Schranke für p075** (`derive.py` Z. 467–480) | **Unbeziffert, potenziell die ganze Ermüdungskurve.** Wenn §10 stimmt (14/27 Stunden mit positiver Steigung, keine ≥ 0,75), steht die Kurve auf Fits, die Andriolo verworfen hätte. | Volltext Andriolo 2024, 2.3 + Abb. 5 · `grep` über alle Verbraucher |
| 2 | **K1 · Fit beginnt am Hochpunkt statt bei α = 1,0** (`ramp.segment()` Z. 383) | **+8 W bei α = 0,75** (213 gegen 205), −2 W bei α = 0,50. Synthetik bestätigt die Richtung: bei konvexem Abfall +53 s ≈ +5 W. Der echte Abfall **ist** konvex (c₂ = +1,01 × 10⁻⁶). | S1, S4, S5 am Livestrom |
| 3 | **K1 · Fit gegen die Zeit statt gegen die HF** (`ramp._fit()` Z. 421) | **−8 W bei α = 0,75** wenn umgestellt, −5 W bei α = 0,50. Zusammen mit #2: **−14 W** (213 → 199 W). | S1 am Livestrom |
| 4 | **K3 · keine Mindestpunktzahl je Bin** (`derive.py` Z. 287) | Unbeziffert. Trifft die Randbins, also den Hebel der Regression. Andriolo: mind. 8 Punkte je Bin. | Volltext Andriolo 2024, 2.3 |
| 5 | **K2 · der SweetSpot-Satz in `const.py` Z. 135–137** | Unbeziffert, aber die Richtung steht fest: zu kurz verworfen → Median **zu hoch**. Der Satz behauptet das Gegenteil seiner eigenen Beobachtung. | Lesen des Kommentars gegen `blocks.py` Kopf |
| 6 | **K2 · Andriolos Grund für Minute 5–20 falsch zitiert** (`const.py` Z. 134) | **0 W.** Reiner Doku-Fehler. | Volltext Andriolo 2024, 2.3 |
| 7 | **Doku · §10 Punkt 10c stand offen, obwohl die Übergabe die Frage geklärt führte** | **0 W.** Zeitachsenversatz von 56 s, geklärt am 16.09.; zusätzlich gegenstandslos seit e1 (heute 1630 s). **Mit diesem Commit berichtigt.** | `NAECHSTER_CHAT.md` Z. 229–232 · Produktionslauf `ramp.measure()` |
| 8 | **K4 · `NAECHSTER_CHAT.md` nennt Stufentest-Stufen, die es nicht gibt** | **0 W** am Code, aber irreführend für jeden neuen Chat. | `workouts.SOURCE_CHAIN` Z. 629–636 |

### Alle UNBELEGTEN Stellen (Suchweg dabei)

| Stelle | Gesucht wo | Befund |
|---|---|---|
| **Ganzfahrt-Regression** (K4) | Andriolo 2024 Volltext; Suche „DFA alpha1 whole ride regression threshold" | Nichts. Andriolo gruppiert nach 10-Tage-Fenstern mit ≥ 4 Einheiten — eine andere Bauart mit eigener Begründung. |
| **Korridor-Untergrenze 0,20 für VO2max** | Andriolo 2024 Volltext (Einleitung, Drei-Zonen-Modell); Rogers 2020/2021a Abstracts | Nichts. Die Literatur kennt **zwei Grenzen** (0,75 / 0,50) und **drei Zonen**, keine untere Kappung. |
| **„Tempo" bei α 0,75–1,00** | dieselben | Widerspricht der Zonenlogik: alpha über 0,75 = Intensität unter der aeroben Schwelle = Zone 1 (Grundlage). Die Familie heißt Tempo und liegt physiologisch in der Grundlage. |
| **Trainingsbereiche als alpha-Korridore** (§10 Punkt 0, Schritt 2) | Andriolo 2024 Volltext; Rogers/Gronwald 2020, 2022; Suche „DFA alpha1 training intensity zones corridor prescription" | **Beantwortet: weder noch.** Die Literatur gibt Grenzen und Zonen, nicht Korridore je Familie und nicht Anteile einer Schwelle. Unsere Korridore sind eine Setzung — und in `const.py` Z. 147 korrekt so beschriftet. |
| **Drift von alpha und Puls in 10-min-Blöcken nahe der zweiten Schwelle** | Suche in dieser Sitzung **nicht durchgeführt** | **OFFEN.** Steht als Auftrag und ist nicht erledigt. Ehrlich als Lücke gemeldet, nicht als „nicht dokumentiert". |
| **Vorhersagebänder bei n < 10** | Suche in dieser Sitzung **nicht durchgeführt** | **OFFEN.** Dasselbe. |
| **Erste gegen dauerhafte Unterschreitung** | alle gelesenen Arbeiten | Nichts — die Literatur liest nicht an Unterschreitungen ab. Die Frage entsteht aus unserem Prüfstein. Am Bestand fällt die Antwort trotzdem: die Gerade trifft die dauerhafte auf 1 s / 0 W. |

### Alle SETZUNGEN mit ihrer Begründung

| Setzung | Begründung | Beschriftet? |
|---|---|---|
| Fit-Anfang = Hochpunkt ab Rampenbeginn | automatisch findbar, ohne Handeingriff; Olieslagers setzt den Beginn möglicherweise von Hand (nicht nachgelesen) | im Modulkopf ja, **an der Karte nein** |
| Fit gegen die Zeit | Olieslagers ist die einzige RAD-Arbeit der drei | im Modulkopf ja, **an der Karte nein** |
| `RAMP_SMOOTH_S` = 30 s | nur zur Segmentsuche, verschiebt keinen Messwert | ja (`ramp.py` Z. 47–49) |
| `RAMP_FLAT_S` = 60 s als „Boden erreicht" | `const.py` Z. 384: „Literatur nennt dafür nichts" | ja, vorbildlich |
| HRVT1pers nach Olieslagers statt Rogers' Wortlaut | implementierbar, hängt am selben Segment | **ja, die sauberste Stelle im Projekt** (`ramp.py` Z. 51–66) |
| `BLOCK_WARMUP_DISCARD_S` = 120 s | Rogers 2021 + Andriolo, am eigenen Bestand geprüft | ja — aber mit **einem falschen Grund** (siehe Versehen #6) |
| `BLOCK_CORRIDORS` | Praxis des Athleten, am Bestand geprüft (30 Blöcke, keiner unter Korridor) | ja (`const.py` Z. 147–152) |
| `DFA_BIN_WIDTH` = 0,05 feste Breite | Andriolo binnt nach Anzahl, nicht nach Breite | **ja, ausdrücklich** (`derive.py` Z. 272) |
| Nur lineares Modell, kein hyperbolisches | Andriolo wählt am Ende selbst linear „for simplicity" | **nein** |
| Späte Fahrtstunden bleiben drin (gegen Andriolos Ausschluss) | wir messen die Ermüdung, die Andriolo vermeidet | **nein** |
| Anker = Median der letzten 5 Ganzfahrten | — | **nein, und es gibt keine Quelle** (siehe UNBELEGT) |

**Keine Empfehlung, was zuerst gebaut wird.** Das entscheidet Johannes.

---

## Quellenliste mit Lesestand

| Quelle | Lesestand | Wo im Projekt zitiert |
|---|---|---|
| **Andriolo, Rummel, Gronwald 2024** · Sensors 24(14):4468 | **VOLLTEXT**, 18.09.2026 gelesen | `derive.py` Z. 270, 417, 425 · `fatigue.py` Z. 6 · `const.py` Z. 134 |
| **Rogers, Giles, Draper, Hoos, Gronwald 2021a** · Front Physiol 11:596567 | **Volltext** (16.09.2026, laut `ramp.py` Z. 8; in dieser Sitzung nur Abstract gegengelesen) | `ramp.py` Kopf |
| **Rogers et al. 2021b** · JFMK | **Volltext** (16.09.2026, laut `ramp.py` Z. 12) | `ramp.py` Kopf |
| **Rogers 2021** · Front Sports Act Living (2-Minuten-Anlauf) | **NICHT GELESEN** — Zitat steht im Code, Stelle in dieser Sitzung nicht nachgeschlagen | `const.py` Z. 131–133 |
| **Rogers, Gronwald 2024** (personalisierte Schwelle) | **NUR ABSTRACT** — Volltext nicht frei zugänglich | `ramp.py` Z. 51–56 |
| **Olieslagers 2026** · Physiol Rep | **NUR AUSSCHNITT des Methodenteils** — Fit-Bereich steht im Abstract nicht | `ramp.py` Z. 14–19 |
| **Gallo et al. 2024** · Eur J Appl Physiol 124:2353–2364 | **NICHT GELESEN in dieser Sitzung** — die Form ist aus Gruppenmittelwerten rekonstruiert, `fatigue.py` Z. 49–58 legt die Rekonstruktion offen | `fatigue.py` Z. 8 |
| **Gronwald, Rogers, Hoos 2020** · Front Physiol 11:550572 | **Abstract** | Zonenmodell, Herkunft von 0,75/0,50 |
| **Rogers, Gronwald 2022** · Front Physiol 13:879071 (Update) | **Abstract** | — |
| **Fleitas-Paniagua 2023/24 · Sempere-Ruiz 2024 · Gronwald 2019/2024 · Ajayi 2025 · Van Hooren 2023** | **NICHT GEPRÜFT in dieser Sitzung** | Lesestand je Zitat weiterhin offen |
| **AI Endurance Blog (Rummel/Andriolo)** — kein Peer-Review, aber von denselben Autoren | gelesen | „in manchen Fällen überschätzt die Rampenerkennung die Schwellen, was sich in neueren physiologischen Arbeiten spiegelt; Schwellen aus dem Clustering von DFA-alpha-1-Werten stimmen dagegen gut mit der neuen Methode überein" — **das ist die 40-Watt-Frage dieses Projekts, in der Literatur, mit derselben Richtung: Rampe 213 W, Blöcke 174–194 W.** |

---

## K5 · Die Umkehrung — „bei wieviel Watt bleibe ich über alpha 1,0"

**Seit 0.64.0.** Die Ermüdungskachel beantwortet nicht mehr „wo liegt meine Schwelle" —
das ist aus Grundlagenfahrten nicht bestimmbar (Befund vom 19.09., PROJEKTSTAND §10,
Kopf der Liste). Sie beantwortet: **bei wieviel Watt bleibe ich über alpha 1,0 — für eine
Fahrt von X Stunden.**

Diese Kausa hat nicht die Vier-Spalten-Form von K1–K4: es gibt keine Quelle, gegen die
abzugleichen wäre. Die Frage ist neu gestellt, die Herleitung steht am eigenen Code.

### K5.1 · Der Rechenweg, und warum er trägt

Gerechnet wird aus **Gemessenem**, je Stunde:

    Zielleistung(h) = gehaltene Last(h) + (alpha bei dieser Last(h) − 1,000) × Umrechnung

`fatigue_v2.reversal(data)` über `reading_rows`; die Umrechnung holt `bridges_alpha(data)`
aus **Stufentest und Blockleiter am Bestand** — nie aus den Stundenfits, die 20-mal
flacher sind (Median-R² 0,32).

**Warum das trägt, wo die alte Frage nicht trug:** der Weg ist kurz. Von der gefahrenen
Last bis alpha 1,0 sind es **0,07 bis 0,31 alpha**. Über diese kurze Strecke liegen die
beiden Umrechnungen — Stufentest **90,6 W je alpha**, Blockleiter **111,7 W je alpha** —
nur **1,6 bis 6,9 W** auseinander. Bei der alten Frage (Extrapolation hinunter bis 0,75)
spannten dieselben zwei Brücken **65 W** auf. Die Unkenntnis über die Brücke ist
unverändert dieselbe; nur der Hebel, mit dem sie auf die Antwort wirkt, ist rund zehnmal
kleiner.

**Das ist der ganze Grund, und er ist geometrisch, nicht physiologisch.** Wer die Brücke
für belegt hält, irrt sich in beiden Fragen gleich stark — es fällt nur in der einen auf.

### K5.2 · Livestand 19.09.2026

| h | Zielleistung | Band | Belegung |
|---|---|---|---|
| 1 | **174 W** | ± 28 W | 17 Fahrten |
| 2 | **166 W** | ± 25 W | 14 Fahrten |
| 3 | **151 W** | ± 12 W | 4 Fahrten |
| 4 | **147 W** | *unter 4 Fahrten keine Spanne* | 3 Fahrten |
| 5 | **130 W** | *unter 4 Fahrten keine Spanne* | 1 Fahrt |

Verlauf **−0,0485 alpha je Stunde**, aus **14 Fahrten**, davon **12 fallend**.

Die Trefferquote steht erst **ab 9 Fahrten** (`BAND_QUOTE_MIN_N`); darunter sagt die Zeile
„t-Band über n Fahrten" und verspricht keine Quote. Grund: bei vier Fahrten hat ein
Weglass-Rückblick drei Fälle — eine Quote ist dort nicht nachprüfbar, weder nach oben noch
nach unten.

*Beschriftung:* die Zahlen der Kachel zum Stand 0.64.0 lauteten 173/166/151/147/130 W mit
±26/±36/±19 W. Die Bänder oben sind der Stand NACH den beiden Bandfehlern (K5.3) und der
Punktschwelle (K5.4). Es sind dieselben Stunden, nicht dieselbe Rechnung.

### K5.3 · Die zwei Bandfehler (0.64.3) — als Kreuztabelle

Das Band war **zweimal unabhängig falsch**, und die beiden Fehler haben sich addiert.
Weglass-Rückblick mit der Produktionsfunktion, Stunde 1 (n = 17) / Stunde 2 (n = 12):

| Streuung aus … | einseitiges t (`STEERING_T90`) | zweiseitiges t (richtig) |
|---|---|---|
| **alpha allein** | **70 % / 66 %** ← war ausgeliefert | 82 % / 75 % |
| **der fertigen Wattzahl** | 76 % / 83 % | **88 % / 91 %** ← seit 0.64.3 |

**Fehler 1 — die halbe Streuung fehlte.** Gerechnet wurde `s(alpha) × Umrechnung` = 14,0 W.
Die **gehaltene Last streut aber selbst um 8,7 W** (117–154 W), und darauf kommt es an: das
Band soll die fertige Wattzahl einschließen, nicht das alpha. Die Streuung der fertigen
Zahl je Fahrt beträgt **15,9 W**.

**Fehler 2 — die falsche Tabellenseite.** `STEERING_T90` ist ein **einseitiges**
90-%-Quantil. Richtig ist es für „höchstens so viel". Für ein **symmetrisches** Band, das
80 % einschließen soll, braucht es das **zweiseitige** — also t(0,95) einseitig.

Beide behoben. Neues Band: Stunde 1 **± 28,7** · Stunde 2 **± 26,7** · Stunde 3 **± 11,6 W**.

Die Aufteilung der Streuung bleibt, mit neuer Beschriftung: `from_spread` ist die Streuung
**zwischen den Fahrten** (Last und alpha zusammen), `from_bridge` der **systematische**
halbe Abstand der beiden Umrechnungen. Das eine ist Streuung, das andere Unkenntnis — sie
quadratisch zusammenzulegen bleibt richtig, sie zusammenzuwerfen wäre falsch.

**OFFEN, ausdrücklich festgehalten: die Blockkacheln benutzen dieselbe einseitige
Tabelle.** SweetSpot, VO2max und Tempo rechnen mit derselben Formel und tragen dieselbe
Zusage „8 von 10 Einheiten". Am Bestand halten sie sie — **83 % bei n = 6** (VO2max),
**80 % bei n = 5** (SweetSpot). Das ist **Glück bei kleinem n**: die einseitige Tabelle ist
bei kleinem df großzügiger als nötig und gleicht den Fehler zufällig aus. **Nachgewiesen
ist das nicht.** Nicht angefasst in 0.64.3, weil eine Änderung dort Trainingsvorgaben
verschiebt — das ist eine eigene Entscheidung.

*Nebenbefund:* der Rat „empirisches Quantil statt t-Formel" ist **widerlegt**. Am Bestand
trifft er schlechter (76 % gegen 88 %), und die oft zitierte Obergrenze (n−1)/(n+1) gilt
nur für **verteilungsfreie** Bänder aus Ordnungsstatistiken. Die Blockkacheln liegen mit 83
und 80 % über ihrer angeblichen Obergrenze von 71 und 67 % — ein parametrisches Band kann
das. Die Obergrenze ist damit kein Argument gegen die Zusage, sondern gegen das empirische
Quantil.

### K5.4 · Die Punktschwelle zählt Sekunden (0.64.2)

**`load_n` zählt STELLEN.** `derive.dfa_hours` läuft über die Stromstellen und sammelt je
Stelle einen Wert; `sample_secs` steht auf **1**, und **beide** Aufrufer
(`importer.py:344`, `websocket.py:1786`) lassen die Vorgabe stehen. **Eine Stelle ist also
eine Sekunde, eine volle Stunde rund 3.600** — im Prüfstand am Zähler nachgewiesen
(3.600 Stellen bei fester Last ergeben `load_n = 3600`).

**Damit hieß die alte Schwelle `DFA_LOAD_MIN_POINTS = 20` genau: 20 Sekunden** — bei einem
alpha, das selbst ein Fenster über **120 Sekunden** ist. Unterhalb von 120 s liegt keine
einzige vollständige Messung vor; die Schwelle ließ Werte durch, die es gar nicht geben
kann.

**Sie steht jetzt auf 120 und wird gegen `DFA_WATT_WINDOW_S` geprüft, nicht gegen eine
Zahl.** Sie ist aus der Bauart des Messwerts **abgeleitet**, nicht gesetzt — genau darauf
kommt es hier an, und deshalb steht sie in dieser Liste.

*Wirkung, mit den Produktionsfunktionen gerechnet:* Kette, Verlauf und Reichweite bleiben
unverändert. Weg fallen genau zwei Stunden, beide auf der Rolle — **9908 h2** (22 s, alpha
0,78) und **4325 h2** (20 s, alpha 1,64), die beiden Ausreißer, die das Band der zweiten
Stunde aufgebläht haben: **± 27,7 → ± 14,8 W**, praktisch halbiert. Stunde 1 bleibt 17 von
17. Bei 300 s fiele Stunde 5 weg, bei 900 s kippt der Verlauf (−0,106 alpha/h aus 6
Fahrten) — die 120 s sind nicht der Punkt, an dem es am besten aussieht, sondern der, an
dem der Messwert vollständig ist.

---

## Was diese Liste NICHT leistet

1. **K2, K3 und K4 sind nicht am Livebestand gerechnet.** Der Container trägt nur
   die Rampen-Fixture. Jede Zahl dieser drei Kausas steht entweder am Code oder als
   NICHT PRÜFBAR — **keine Zahl ohne Deckung**.
2. **Zwei der drei neu zu suchenden Literaturfragen** (10-min-Drift nahe der zweiten
   Schwelle · Vorhersagebänder bei n < 10) sind **nicht gesucht worden**. Sie stehen
   als OFFEN, nicht als „nicht dokumentiert".
3. **Sechs zitierte Arbeiten** sind in dieser Sitzung nicht gegen ihre Zitatstelle
   gehalten worden (Tabelle oben, vorletzte Zeile).
4. Der Auftrag verlangt, jede Studie in **jeder** Kausa neu gegen ihre Stelle zu
   halten. Geleistet ist das für Andriolo 2024 (K2, K3, K4) und für Rogers 2021a/b
   (K1). Nicht geleistet für die übrigen.
5. **Die entschiedene Lesart (K1.4) erklärt den Abstand zu den Blöcken NICHT** — und
   seit dem 19.09. muss sie das auch nicht mehr. Unter „erste Unterschreitung" (193 W)
   wäre er verschwunden, unter „dauerhaft" (213 W) bleibt er bestehen: Blöcke 174–194 W
   gegen Rampe 213 W, rund **20 bis 40 W**. **Der Abstand ist inzwischen erklärt, aber
   anders als gesucht:** die Rampe steht auf einer breiten Lastspanne, die Blöcke auf
   einer schmalen — die beiden Zahlen beantworten nicht dieselbe Frage (PROJEKTSTAND §10,
   Kopf der Liste). Eine Umrechnung zwischen ihnen wird es nicht geben.
6. **K5 ist nicht am Livebestand nachgerechnet worden.** Die Zahlen in K5.2 sind der
   Livestand vom 19.09., von Johannes gemeldet und gegen die Fixture gehalten — nicht in
   diesem Container aus Rohströmen neu gerechnet. Der Container trägt nur die
   Rampen-Fixture.

## K6 · Das Blockband am Livebestand nachgerechnet (20.09.2026)

Gerechnet mit den Produktionsfunktionen (`steering.t_band`, `steering.c6`) über den
Livebestand aus `intervals_icu/blocks`. Die Zahlen der Kachel sind bitgenau
reproduziert (TREFFER): VO2max `235–265` (half 14,6 · sd 7,97 · t 1,638 · n 4),
SweetSpot `186–194` (half 4,06 · sd 2,22 · t 1,638 · n 4).

### K6.1 · Das Fenster ist vier — n ist nie größer

`t_band` schneidet `values[-STEERING_BAND_WINDOW:]` ab, und `STEERING_BAND_WINDOW = 4`.
**Die Zahl der Einheiten einer Familie geht nicht ins Band ein**, nur die letzten vier.
VO2max hat 6 Einheiten und rechnet mit 4; SweetSpot hat 5 und rechnet mit 4. In beiden
Fällen df = 3, t = 1,638 — nicht df 5 / df 4.

Damit fällt bei SweetSpot die älteste Einheit (05.07., 167 W) ganz aus dem Band heraus,
bei VO2max die beiden Juli-Einheiten (258 / 258 W). Der Einheiten-Median des Fensters
liegt deshalb bei VO2max auf **243,8 W**, während die Vorgabe auf **250 W** steht.

### K6.2 · Die Tabellenseite, mit den richtigen Freiheitsgraden

Faktor ist `t(0,95; 3) / t(0,90; 3) = 2,353 / 1,638 = 1,43651` — für **beide** Familien
derselbe, weil beide bei df 3 rechnen.

| Familie | Vorgabe | heute (einseitig) | zweiseitig | half heute → danach |
|---|---|---|---|---|
| VO2max | 250 W | **235 – 265** | **229 – 271** | 14,60 → 20,97 |
| SweetSpot | 190 W | **186 – 194** | **184 – 196** | 4,06 → 5,83 |

### K6.3 · Die Zusage „8 von 10" — Synthetik, fünf Seeds, je 20.000 Läufe

Einheiten ~ Normal(µ, s), Fenster 4, Band wie Produktion. Entscheidend ist der
**Versatz** zwischen Vorgabe und dem Median des Fensters:

| Versatz | heute (einseitig) | nur Tabelle getauscht |
|---|---|---|
| 0 Streuungen | 83,3 % | 91,8 % |
| 0,50 | 79,6 % | 89,8 % |
| **0,78** (= VO2max heute) | **74,9 %** | **86,8 %** |
| 1,25 | 63,0 % | 78,7 % |

Sitzt die Vorgabe auf dem Gefahrenen, hält die einseitige Tabelle die 80 % sogar über.
Am Bestand sitzt sie nicht: VO2max 6,2 W = 0,78 Streuungen daneben, SweetSpot 1,0 W =
0,45. **Die Zusage hält heute bei VO2max nicht** (≈75 %), bei SweetSpot knapp (≈79 %).
Mit der zweiseitigen Tabelle hält sie in beiden Fällen.

### K6.4 · Der Weglass-Rückblick trägt hier nicht

Weil das Fenster vier ist, **entfernt ein Weglassen keinen Punkt, sondern tauscht einen**:
die nächstältere Einheit rückt nach. Bei SweetSpot zieht das die 167-W-Einheit ins
Fenster, die sd springt von 2,22 auf ~12,5, und das Band 167–213 enthält trivial alles.
Von fünf nominellen Fällen verändern vier das Fenster, einer gar nicht. Die Quoten
6/6 (VO2max) und 4/5 (SweetSpot) sind **Artefakte, keine Messung**.

Die ehrliche Probe ist die **Vorwärtsprobe** (Band aus den Einheiten davor, gegen die
nächste): VO2max 2/3 einseitig, 3/3 zweiseitig · SweetSpot 2/2 in beiden. Drei und zwei
Fälle — das trägt keine Quotenangabe.

`fatigue_v2.BAND_QUOTE_MIN_N = 9` regelt genau das für die Ermüdungskachel. **Die
Blockkacheln haben keine solche Schranke**: `band_share` (8) steht in
`intervals-panel.js:1728` und `:1838` immer da, sobald es ein Band gibt — ab drei
Einheiten.

### K6.5 · Die fehlende zweite Streuung — es gibt eine, und sie ist nicht die erwartete

Fehler 1 der Ermüdungskachel (Streuung von alpha statt der fertigen Zahl) hatten die
Blockkacheln nie: `family_state` gibt `watts_raw` an `t_band`, die fertige Wattzahl je
Einheit. Beide Streuungsquellen stecken darin.

Das Gegenstück zu `bridge_half` ist ein anderes: **der Versatz zwischen Vorgabe und
Fenster-Median.** Er ist keine Streuung zwischen Einheiten, sondern ein systematischer
Abstand — genau die Bauart, die `reversal_band` quadratisch dazulegt. Im Blockband
fehlt er ganz. Synthetik mit `half² + Versatz²`:

| Versatz | heute | nur Tabelle | Tabelle + Versatz |
|---|---|---|---|
| 0 W | 83,3 % | 91,8 % | 93,2 % |
| 6,2 W | 74,9 % | 86,8 % | **90,6 %** |
| 10 W | 63,0 % | 78,7 % | **87,6 %** |

### K6.6 · Tempo (n = 1) — zwei Sätze, die sich widersprechen

`state["band"] = t_band(...) if state.get("watts") else None`. Tempo hat keinen
Startwert (`STEERING_ANCHOR_W` kennt nur sweetspot und vo2max), also `watts = None`,
also **nie ein Band — auch bei zehn Einheiten nicht.** Das Pulsfenster dagegen hängt an
n ≥ 3 und käme mit mehr Einheiten.

Die Kachel zeigt heute nebeneinander:
`tile_no_band` — *„Für eine Spanne braucht es 3 gemessene Einheiten; solange steht die
Vorgabe allein."* und `tile_no_target` — *„Für diese Familie wird keine Vorgabe geführt."*
Der erste Satz ist für Tempo **falsch** (die Spanne kommt nie) und verweist auf eine
Vorgabe, die daneben als `–` steht. `band_note` sagt „noch keine Toleranz" — das „noch"
stimmt fürs Pulsfenster, nicht fürs Band.

### K6.7 · Was der Regler liest — am Syntaxbaum, nicht am Kommentar

`ast`-Lauf über `steering.py`: `c6` liest genau drei Schlüssel — `date`, `side`,
`usable` — ruft nur `len`, `list`, `str`, und enthält kein einziges Vorkommen von
„band". In `family_state` steht `c6` an Anweisung 3, `state["band"]` an Anweisung 7.
**Der Regler läuft vor dem Band und kann es nicht lesen.** `side()` entscheidet am
`BLOCK_CORRIDORS`-Korridor über alpha, nicht an Watt.

Folge: Eine andere Tabellenseite ändert **die angezeigte Spanne und sonst nichts.**
Die Vorgaben 190 W und 250 W bewegen sich nicht.
