# Ausbauplan — Pakete A, B, C

**Stand:** 12.09.2026 · gehört zu PROJEKTSTAND.md §12 (Audit-Hauptbuch)

Drei Pakete, je ein Chat, je ein Release. Die Entscheidungen stehen hier, damit
die Umsetzung nicht mit Designfragen anfängt und die Recherche nicht zweimal
bezahlt wird. Reihenfolge der Arbeit in jedem Paket: PROJEKTSTAND §5–§9 lesen,
dann den Code, dann bauen — Suite vorher grün, nachher grün, Gegenproben mit
sichtbarer Fehlermeldung.

| Paket | Inhalt | berührt | Aufwand |
|---|---|---|---|
| **A** | DFA-Tab: Brushing, Zeitraumwahl, Sprung in die Aktivität · Signalkarten: Datumsachse | nur Frontend | mittel |
| **B** | Tageskontext: Etiketten, Gewichte, zweite Basislinie, eigene Kachel | Archiv + `coach.py` + WebSocket + Frontend | groß |
| **C** | Vergleichsgruppe: Caliper statt fester Prozentzahl | `workouts.py`/`analytics.py` + Frontend | klein |

---

## Paket A — DFA-Tab und Signalkarten

### A1 · Graph und Liste verbinden (Brushing & Linking)

**Muster:** Brushing & Linking, eingeführt von Becker und Cleveland
(*Brushing Scatterplots*, Technometrics 29, 1987). Linking heißt: derselbe
Datenpunkt wird in mehreren Darstellungen hervorgehoben; Brushing ist dasselbe
in Echtzeit, während der Zeiger über eine Darstellung fährt. Genau der Fall
hier: oben die Punktwolke der Schwellenmessungen, unten die Tabelle.

**Ein Auswahlzustand, nicht zwei.** Schlüssel ist die `activity_id`, nicht der
Index und nicht das Datum — an einem Tag können zwei Einheiten liegen, und zwei
Listen, die sich über das Datum suchen, sind Fehlerklasse 3 in klein.

- `_dfaHover` (flüchtig, aus `pointermove`) und `_dfaPick` (fest, aus `click`).
  Die Trennung flüchtig/fest ist Teil des Musters, nicht Geschmack.
- **Graph → Liste:** Randbalken (3 px, Sportfarbe) *innen* an der Zeile, leicht
  hellerer Zeilenhintergrund, `scrollIntoView({block:"nearest"})`. Kein
  `border`, sonst verschiebt sich die Zeile um die Randbreite.
- **Liste → Graph:** nicht den Treffer aufhellen, sondern die übrigen Punkte
  abdunkeln (`opacity 0.35`), Treffer mit Ring und `r + 2`. Bei 49 Punkten
  liest sich De-Emphase besser als Hervorhebung. Zusätzlich die Cursor-Linie
  auf das Datum setzen, dann liest die Kopfleiste mit.
- **Zweitkodierung ist Pflicht:** der Ring ist Form, nicht Farbe. Die bekannte
  Schwäche des Musters ist, dass die Hervorhebung rein visuell bleibt und die
  Interaktion nicht auffindbar ist — deshalb zusätzlich ein sichtbarer Hinweis
  „Auswahl aufheben" bei fester Auswahl.
- Punkte ohne belastbare Messung (hohl gezeichnet) bleiben unmarkierbar.

### A2 · Zeitraumwahl

**Muster:** der Zeitwähler aus Grafana/Kibana — voreingestellte relative
Bereiche („quick ranges") plus ein Bereich, der explizite und relative Angaben
mischt; explizites Format `JJJJ-MM-TT`.

- Chips oben rechts in der Karte: `42 T · 3 M · 6 M · 12 M · alles · eigener
  Zeitraum`, Vorauswahl **3 M**, Semantik als Radiogruppe (Pfeiltasten).
- Eigener Zeitraum: zwei Datumsfelder **und** Ziehen im Graphen, Doppelklick
  setzt zurück. Das Ziehen ist der billigste Weg zu einem freien Fenster und
  braucht kein Datepicker-Widget.
- **Relativ ist nicht absolut, und das steht dran:** Chips bedeuten
  „jetzt−3 M … jetzt" und verschieben sich täglich; ein eigener Zeitraum ist
  eingefroren.
- Merken in `localStorage` unter versioniertem Schlüssel, je Ansicht.
- **Backend bleibt unberührt.** 57 Auswertungen kommen ohnehin vollständig;
  gefiltert wird im Client. Einen optionalen `since`-Parameter am WS-Befehl
  vorsehen, damit das bei 500 Auswertungen kein Umbau wird.

**Vier Fallen:**

1. **Die Leitzahl darf nicht am Fenster hängen.** „Aktuelle aerobe Schwelle,
   Median der letzten 5 belastbaren" bleibt fensterunabhängig — sonst ändert
   sich die Schwelle, weil jemand gezoomt hat (zwei Rechenwege auf dieselbe
   Frage). Nur die Zeichnung folgt dem Fenster, und das steht in der Quellzeile.
2. **n im Fenster ausweisen; unter 5 belastbaren Messungen die Medianlinie
   weglassen**, nicht dünn zeichnen. Eine Trendlinie aus drei Punkten ist der
   Fehler von 0.13.0 in neuer Verkleidung.
3. **Y-Achse nicht je Fenster neu skalieren** — sonst sieht jeder Zeitraum
   gleich dramatisch aus. Feste Skala über den Gesamtbestand oder ein
   sichtbarer Schalter „Skala: Fenster / gesamt".
4. **Die Liste folgt dem Fenster**, sonst bricht A1 (Punkt im Graph ohne Zeile).
   Zähler: „14 von 49 Einheiten im Fenster".

Als eigene Komponente bauen, nicht als DFA-Sonderfall — Fitness und Belastung
wollen denselben Wähler.

### A3 · Mehr Spalten in der Liste

Heute: Datum, Sport, Schwelle, Leistung, Güte. Dazu: Dauer, Last, Ø-HF,
Entkopplung, Messpunkte und **Abweichung der Schwelle gegen den rollierenden
Median in bpm** — die Zahl, um die es in dem Reiter geht, und die einzige, die
heute fehlt.

### A4 · Sprung in die Aktivität

Klick auf eine Zeile öffnet den Aktivitäten-Reiter mit genau dieser Einheit.
Umsetzung als Hash-Route (`#activities/<id>`): Reiterwechsel setzt den Hash,
ein `hashchange`-Listener öffnet das Detail. Kostet kaum mehr als eine
Zustandsvariable, liefert aber Zurück-Taste und teilbare Links; Kalender und
Heute können denselben Weg später mitbenutzen.

### A5 · Datumsachse in den aufgeklappten Signalkarten

Die kleine Kurve ist eine Sparkline und darf achsenlos sein. Sobald sie groß
aufgeht, ist sie ein Diagramm und braucht eine Achse.

- 60-Tage-Fenster: Tick alle 7 Tage, Beschriftung alle 14 Tage, Monatswechsel
  immer beschriftet.
- Cursor liest Datum und Wert in der **festen Kopfleiste** der Karte (kein
  schwebender Kasten — die Fehlerklasse wurde in 0.9.3 entfernt).
- Zusätzlich eine **Ereignisspur** unter der Kurve: je Trainingstag ein kurzer
  Strich, Einbruchstage markiert. Damit steht „HRV fällt zwei Tage nach der
  langen Fahrt" ohne Reiterwechsel da.

### Tests A

- `test_panel_views.js`: Auswahl-Zustand wird in beide Richtungen gerendert
  (Punkt markiert ⇒ Zeile markiert und umgekehrt); Fenster filtert Graph **und**
  Liste; Leitzahl bleibt über alle Fenster gleich; unter 5 Messungen keine
  Medianlinie.
- `test_panel_design.js`: Ring ist Form (nicht nur Farbe); Achsenbeschriftung
  vorhanden, sobald die Karte aufgeklappt ist.
- Gegenproben: Filter aus der Liste entfernen, Leitzahl ans Fenster hängen,
  Medianlinie bei n = 3 zeichnen — jede Mutation muss gezählt melden.

---

## Paket B — Tageskontext (Etiketten und Gewichte)

### B1 · Was die Forschung macht

**Etikettieren, nicht frei gewichten.** HRV4Training (Altini et al., *What Is
behind Changes in Resting Heart Rate and Heart Rate Variability?*, Sensors 21
(23), 2021) erhebt nach jeder Messung Kontext — Trainingsintensität, Alkohol,
Krankheit, Zyklus — und wertet danach getrennt aus: **akute** Stressoren über
Tag-zu-Tag-Differenzen, **mehrtägige** Stressoren (krank, Reise, Zyklus) über
den Vergleich der Mittelwerte in den beiden Bedingungen.

**Geräte machen daraus einen Modus, keine Zahl.** Oura Rest Mode gewichtet die
Beiträge des Bereitschaftswerts um (Erholungsmetriken hoch, Aktivität raus);
die Nap-Erkennung nennt Schichtarbeit ausdrücklich als Anwendungsfall, und eine
falsch erkannte Schlafphase lässt sich löschen, um ihren Einfluss auf die Werte
zu entfernen.

**Der Messbefund zur Nachtschicht:** Aktivitäts- und Schlafalgorithmen sind für
normale Schlaf-Wach-Zeiten gebaut; bei Schichtarbeit bleibt Tagschlaf häufig
unerkannt, was die Quantifizierung verfälscht. Physiologisch kommt hinzu: bei
Schichtarbeitern ohne zirkadiane Anpassung war die LF/HF-Ratio im Tagschlaf
signifikant erhöht gegenüber angepassten. **Der Wert nach einer Nachtschicht
ist also nicht „schlecht" — er misst etwas anderes.** Eine freie Zahl kann das
nicht unterscheiden, ein Etikett schon, und aus Etiketten wird später Statistik.

### B2 · Datenmodell

Eigener Archivblock, nicht nach Intervals zurückschreiben:

```
data["day_context"] = {
  "2026-09-11": {"tag": "nachtschicht", "weight": 0.0, "note": "", "set_at": "2026-09-12"},
  ...
}
```

| Etikett | Vorgabe `weight` | Bedeutung |
|---|---|---|
| `normal` | 1,0 | voller Beitrag |
| `nachtschicht` | 0,0 | Messbedingung abweichend — zählt nicht in die Basislinie |
| `spätschicht` | 0,5 | verschobener, aber nächtlicher Schlaf |
| `alkohol` | 0,5 | belegter akuter Stressor, Wert bleibt echt |
| `reise` | 0,5 | akuter Stressor, klingt meist nach einem Tag ab |
| `krank` | 0,0 | für die Basislinie; **für die Warnlampe voll** (siehe B3) |
| `uhr nicht getragen` | 0,0 | Messfehler, kein Zustand |

`weight` ist die Feinjustage (0–1 in Schritten von 0,25), Vorgabe kommt vom
Etikett. Das Etikett ist die Regel, die Zahl die Ausnahme.

### B3 · Die Trennung, an der so etwas sonst kippt

**Entschieden am 12.09.2026.** Drei Ebenen, strikt getrennt:

1. **Basislinie und Referenz** (60-Tage-Mittel, Standardabweichung): hier wird
   gewichtet. Gewichtetes Mittel und gewichtete Streuung, Mindestbelegung
   `Σw ≥ 30` Tage, sonst Rückfall auf ungewichtet **mit sichtbarem Hinweis**.
2. **Warnlampe und Zustandsmaschine**: hier wird **nie** ausgeschlossen. Sonst
   blendet das System genau den Infekt aus, der der einzige nachgewiesene
   Nutzen der Morgenwerte ist (September 2026: −2,7 / +3,7 SD). Stattdessen
   trägt der Tag ein Merkmal „erklärt": ein −2-SD-Tag nach Nachtschicht löst
   keinen Einbruch aus, bleibt aber sichtbar und wird benannt.

3. **Last, ACWR, Monotonie, Lastbudget: unberührt.** Die Last ist kein Messwert
   unter schwankenden Bedingungen, sondern ein Ereignisprotokoll — die 129 Last
   vom 04.09. sind gefahren, gleich wie die Nacht davor war. Die Definitionen
   von ACWR (Gabbett/Blanch) und Monotonie (Foster) beruhen auf **rohen**
   Lastsummen; eine gewichtete Last macht beide bedeutungslos. Dazu ein
   Sicherheitsargument: das Lastbudget rechnet „7 × chronisch × Ziel − letzte
   sechs Tage" — eine kleingerechnete Last **erlaubt mehr**, nicht weniger.
   Genau die falsche Richtung.

   Dass eine Nachtschicht den Vorschlag beeinflusst, bleibt richtig — aber über
   den **Zustand**, nicht über die Last. Der Weg ist: Kontext → Bereitschaft →
   Einheitenurteil („heute Nachtschicht, harte Einheit verschieben"), nie eine
   heimlich gekürzte Wochenlast.

Tage mit `w = 0` werden weiter gezeichnet, nur hohl — dasselbe Muster wie die
dünnen DFA-Messungen. Konsistenz spart Erklärung.

### B4 · Ausbaustufe: zweite Basislinie je Bedingung

Ab etwa 15 Tagen mit demselben Etikett: eigene Basislinie für diese Bedingung
statt Ausschluss. Dann sagt das Panel nicht mehr „Tag ignoriert", sondern
„nach Nachtschicht liegst du üblicherweise 8 ms tiefer — heute normal für
Nachtschicht". Das ist der Weg aus B1 und deutlich mehr wert als jede
Gewichtung. Erst bauen, wenn B2/B3 stehen.

### B5 · Bedienung und Ort

- **Erfassung dort, wo der Tag entsteht:** Klick auf die Tagesspalte in „Woher
  das kommt" (Heute) und auf den Tag im Kalender öffnet ein Popover mit Chips.
  Ein Klick, kein Formular.
- **Kein Schichtmuster im Profil, keine Automatik — entschieden am 12.09.2026.**
  Die Etiketten werden von Hand gepflegt. Ein automatisch gesetztes Etikett, das
  niemand bestätigt hat, ist eine erfundene Messbedingung, und die landet als
  harte Zahl in der Basislinie. Ein früher erwogenes Profilfeld „Schichtmuster"
  entfällt ersatzlos; abgeleitet wird **nichts**.
- Damit Handpflege keine Klickarbeit wird, zwei Hilfen, die nichts raten:
  **Mehrfachauswahl** im Kalender (Zeitraum ziehen, ein Etikett auf mehrere
  Tage) und **„letztes Etikett wiederholen"** als Kurzweg. Eine Nachtschicht-
  woche kostet dann zwei Handgriffe statt sieben.
- **Eigene Kachel auf Heute**, in der Form der Signalkarten (HFV, Ruhepuls,
  Schlafdauer):
  - Großwert „1,0" bzw. „0,0 · Nachtschicht", Referenz rechts „Standard 1,0".
  - Kurve als **Stufenkurve** (Gewichte sind Setzungen, keine Messreihe),
    y von 0 bis 1, Datumsachse nach A5.
  - Kopfzahl der Karte: **„belastbare Tage in 60: 84 %"** — das Maß dafür, wie
    fest die Basislinie steht.
  - Aufgeklappt: Liste der letzten Tage mit Datum, Etikett-Chip, Gewicht,
    Eingabefeld; darunter der übliche Quellenblock mit der Erklärung, was das
    Gewicht beeinflusst (Basislinie ja, Warnlampe nein), den Vorgabewerten und
    dem Vorbehalt, dass die Gewichte eine **Setzung** sind.

### B6 · Schnittstelle

Zwei WebSocket-Befehle: `intervals_icu/day_context` liest,
`intervals_icu/set_day_context` schreibt einen Tag. **Nicht** `context` — der
Name ist belegt: `intervals_icu/context` liefert die Einordnung einer Einheit
gegen vergleichbare (`coach.session_context`) und gehört zu Paket C. Schreibweg
lokal, nichts geht an Intervals.

### Tests B

- `test_coach.py`: gewichtete Basislinie gegen bekannte Ergebnisse; `Σw < 30`
  fällt zurück und meldet es; ein `w = 0`-Tag verändert die Basislinie nicht,
  **löst aber weiterhin die Einbruchserkennung aus**, wenn er extrem ist.
- Regel identisch in `state()` und `state_series()` — Wächter wie bei der
  Trigger-Schärfung aus 0.34.0, sonst laufen Trainerurteil und Verlaufsbänder
  wieder auseinander.
- `test_plan.py`/`test_import.py`: Archiv ohne `day_context` lädt (Altbestand),
  Migration legt den Block leer an.
- **Wächter: die Last bleibt roh.** Ein Test, der beweist, dass `analytics`
  (ACWR, Monotonie, Budget) die Gewichte nicht liest — sonst wandert die
  Gewichtung beim nächsten Umbau still in die Lastrechnung.
- Gegenproben: Gewichtung in der Warnlampe aktivieren (der Infekt-Fall muss
  dann durchfallen), Mindestbelegung entfernen, Gewichte in die Lastsumme
  ziehen — jede Mutation muss gezählt und benannt melden.

---

## Paket C — Vergleichsgruppe

### C1 · Was heute dasteht

„Verglichen wird mit deinen eigenen früheren Einheiten derselben Sportart,
deren Intensität um höchstens 10 Punkte und deren Dauer um höchstens 40 %
abweicht." 40 % ist geraten, und der Text behauptet eine Strenge, die die Zahl
nicht hat.

### C2 · Was die Forschung macht

Matching mit **Caliper**. Austin (*Optimal caliper widths for propensity-score
matching*, Pharmaceutical Statistics 10 (2), 2011) empfiehlt aus
Monte-Carlo-Simulationen eine Breite von **0,2 Standardabweichungen**: das
minimiert den mittleren quadratischen Fehler und beseitigt mindestens 98 % der
Verzerrung des rohen Schätzers. Der Kern ist der Handel dahinter: ein enger
Caliper verbessert die Balance und verwirft Fälle (mehr Streuung), ein weiter
behält Fälle und lässt schlechtere Treffer zu (mehr Verzerrung).

### C3 · Übersetzung

- Toleranz **nicht in Prozent der Dauer**, sondern als 0,2 SD der eigenen
  Dauer-Verteilung derselben Sportart, gerechnet auf der **log-Dauer** — Dauern
  sind rechtsschief, 45 min ↔ 3 h ist kein symmetrisches ±40 %. Anzeige darf
  weiter in Prozent erfolgen.
- **Automatische Weitung mit Mindest-n:** eng starten (0,2 SD ≈ ±20 %), in
  Stufen weiten (20 → 30 → 40 %), bis `n ≥ 8`. Immer ausweisen, welche Stufe
  gegriffen hat: „±20 %, 14 Einheiten" bzw. „auf ±40 % geweitet, sonst nur 5".
- Intensität („höchstens 10 Punkte") nach derselben Logik als SD-Caliper.
- Bedienung im aufklappbaren Quellenblock der Karte, wo der Satz heute schon
  steht: zwei Schieber (Dauer, Intensität), Schalter „automatisch weiten",
  darunter live `n = 14 · Median-Dauer 1:52 · diese Einheit 2:05`. Einstellung
  und Wirkung im selben Blickfeld.
- Der Beschreibungstext nennt die Weitung — sonst behauptet die Karte wieder
  eine Strenge, die sie nicht hat.

### Tests C

- Vertrag: die gewählte Stufe ist immer die engste, die `n ≥ 8` liefert.
- Bei zu dünner Lage auch auf der weitesten Stufe: keine Einordnung, sondern
  die Aussage, dass es zu wenige Vergleichseinheiten gibt.
- Gegenprobe: feste 40 % wieder einbauen — der Vertragstest muss fallen.

---

## Reihenfolge und Modellwahl

| Session | Paket | Warum |
|---|---|---|
| S2 | A | eng spezifiziert, viele kleine Eingriffe im Panel, kein Backend |
| S3 | B | Archivschema, Migration, dieselbe Regel an mehreren Orten — das schwerste |
| S4 | C | Mathematik und Formulierung, klein |

A und C lassen sich zusammenlegen, wenn A glatt läuft. Entschieden wird das am
Ende von S2 nach Kontextstand, nicht vorher.
