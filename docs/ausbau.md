# Ausbauplan — Pakete A, B, C

**Stand:** 12.09.2026 · gehört zu PROJEKTSTAND.md §12 (Audit-Hauptbuch)

Drei Pakete, je ein Chat, je ein Release. Die Entscheidungen stehen hier, damit
die Umsetzung nicht mit Designfragen anfängt und die Recherche nicht zweimal
bezahlt wird. Reihenfolge der Arbeit in jedem Paket: PROJEKTSTAND §5–§9 lesen,
dann den Code, dann bauen — Suite vorher grün, nachher grün, Gegenproben mit
sichtbarer Fehlermeldung.

| Paket | Inhalt | berührt | Aufwand |
|---|---|---|---|
| **A** | DFA-Tab: Brushing, Zeitraumwahl, Sprung in die Aktivität · Signalkarten: Datumsachse | Frontend **+ drei additive Backend-Felder** (siehe unten) | mittel |
| **B** | Tageskontext: Etiketten, Gewichte, zweite Basislinie, eigene Kachel | Archiv + `coach.py` + WebSocket + Frontend | groß |
| **C** | Vergleichsgruppe: Caliper statt fester Prozentzahl | `workouts.py`/`analytics.py` + Frontend | klein |

---

## Paket A — DFA-Tab und Signalkarten

> **Korrektur beim Bauen (0.36.0):** „nur Frontend" hielt nicht. Die Datumsachse aus A5
> braucht Daten, die das Panel nicht hat — `today.history` war eine reine Werteliste, und
> die 42 Einträge sind die *vorhandenen* Wellness-Tage, nicht 42 Kalendertage. Die Spalten
> aus A3 hätten gegen eine auf 300 Einheiten begrenzte Aktivitätenliste gejoint werden
> müssen und wären älter still leer geblieben. Ergänzt wurden daher `coach.history_days`,
> fünf Felder an `importer.threshold_series` und ein optionaler `since`-Parameter — alles
> additiv, nichts Bestehendes geändert.

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
  hellerer Zeilenhintergrund. Kein `border`, sonst verschiebt sich die Zeile um
  die Randbreite.
  > **Korrektur 0.36.1:** hier stand ursprünglich, den Treffer ins Bild zu ziehen.
  > Am lebenden Panel war das falsch — `:host` ist selbst der Scroll-Kasten und
  > die Tabelle steht unter den Graphen, also bewegte jede Zeigerbewegung die
  > ganze Seite und trug den Graphen aus dem Fenster. Eine flüchtige Markierung
  > bewegt die Seite nicht, auf der sie gezeichnet wird.
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

## Was Paket A über diese Spezifikation gelehrt hat

**Nachgetragen am 12.09.2026, nach 0.36.0/0.36.1.** Die Bau-Session hat acht
Widersprüche zwischen dieser Datei und dem Quelltext gemeldet, statt darüber
hinwegzubauen. Vier davon sind Muster, keine Einzelfälle — sie gelten für B und
C genauso, und die nächste Session liest sie, bevor sie der Spezifikation
glaubt.

**1 · „Berührt nur das Frontend" war falsch — prüf es am Feld, nicht am Text.**
A5 sollte laut Spezifikation ohne Backend auskommen. Tatsächlich war
`today.history` eine reine Werteliste über *die vorhandenen* Wellness-Tage: eine
Achse nach „heute minus n" wäre ab der ersten Lücke falsch gewesen. Es brauchte
`history_days` mit Datum, Last und Zustand je Tag. **Für B heißt das:** vor dem
ersten Handgriff nachsehen, welche Felder überhaupt ein Datum tragen. Der
Tageskontext ist datumsindiziert, die Signalreihen waren es nicht.

**2 · Eine vorgeschriebene Prüfung ist erst eine Prüfung, wenn die Fixture sie
unterscheidbar macht.** Zwei der vier Fallen aus Paket A schlugen zunächst
überhaupt nicht an: die Fixture ließ die Schwelle in jedem Fenster zwischen 150
und 171 kreisen, eine fensterweise skalierte Achse hätte identisch ausgesehen.
Und alle relativen Fenster enden „jetzt", haben also dieselben letzten fünf
Messungen — die Fensterunabhängigkeit der Leitzahl zeigt sich erst an einem
**eingefrorenen** Zeitraum. Jede Zusicherung in B und C braucht deshalb den
Nachweis, dass die Fixture zwei unterscheidbare Fälle enthält.

**3 · Aussagen über DOM-Verhalten gehören simuliert, nicht gegrept.** Der
`scrollIntoView`-Rat aus A1 stand so in dieser Datei und war falsch: bei
`:host{overflow-y:auto}` scrollt er den ganzen Panel-Container, der Graph floh
vor dem Zeiger (0.36.1). Eine Quelltextsperre hätte drei der sechs
Kausalpfade nie gesehen — erst der echte `pointermove` über einem
aufzeichnenden DOM zeigte es. **Für B:** jede Behauptung über Fokus, Scrollen
oder Neuaufbau beim Setzen eines Etiketts wird am simulierten Ereignis geprüft.

**4 · Kennzahlen des Prüfstands gegen die Tabelle halten, nicht gegen den
Fließtext.** Der PROJEKTSTAND sprach von 15 Testdateien, es waren 14 — ein
Zählfehler aus 0.35.0. Schwerer: fünf Dateien liefen 187 Prüfungen, **ohne sie
zu melden**, und der Hygiene-Wächter ließ das durch, weil „höchstens eine
Summary" auch null erlaubt. Die Kennzahl 2.354 deckte 9 von 14 Dateien ab.
Beides in 0.36.0 behoben (jetzt 2.778 über 14 Dateien). **Regel:** eine Datei
ohne gemeldete Zahl im Suite-Lauf ist ein Befund, kein Schönheitsfehler.

### Was daraus für das Archiv in Paket B folgt

`importer.empty_data()` legt das Grundgerüst an: `wellness`, `activities`,
`dfa`, `unavailable`, `goal`, `last_import` und die Versionsmarken. **`day_context`
muss dort hinein** — sonst wiederholt sich exakt die Lücke, die 0.35.0
repariert hat: `store.async_load` füllt fehlende Schlüssel nur auf der obersten
Ebene auf, und ein Block, den das Grundgerüst nicht kennt, entsteht bei
Altbeständen nie. Dazu gehört eine Migration in der Bauart von
`plan.migrate_goal()` samt Gegenprobe.

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

### Präzisierungen aus dem Bau (0.37.0 — B2, B3, B6 plus Chips geliefert)

Festgelegt beim Bauen, damit 0.38.0 nicht neu entscheidet, was schon
entschieden ist:

- **Datenschlüssel sind ASCII-Slugs** (`spaetschicht`, `uhr_nicht_getragen`),
  die deutschen Anzeigenamen stehen im Vokabular `day_context.TAGS` — eine
  Quelle für Speicher UND Anzeige. Die Migration lässt einen UNBEKANNTEN Slug
  mit gültigem Gewicht überleben (Downgrade-Schutz: ein 0.38-Etikett darf ein
  0.37-Laden nicht kosten); der Schreibweg dagegen ist strikt und kennt nur
  das Vokabular.
- **Löschen läuft über `tag: null`** am selben Kommando und ist eine
  RÜCKNAHME, keine Aussage: sichtbar anders als „Normal" setzen (gestrichelte
  eigene Zeile statt Kategorien-Chip), und der Schlüssel verschwindet
  komplett — ein gelöschter Tag rechnet byte-gleich zu einem nie
  etikettierten (Gegenprobe: ein `normal`-Stummel wird benannt gefangen).
- **Hinweisregel:** die Rückfallregel (`Σw < 30` → ungewichtet) ist überall
  dieselbe; der sichtbare Hinweis erscheint nur, wenn mindestens ein Tag mit
  `w < 1` im Fenster liegt, und nennt dann die Zahlen („nur 25 belastbare
  Tage von 30 nötigen, 35 Tage sind etikettiert"). Der Rückfallwert ist
  bit-identisch zum ungewichteten Bestand — `_norm_band` delegiert in beiden
  Fällen (kein Etikett / unter der Schwelle) direkt an `_band`, es gibt
  keinen zweiten Rechenweg.
- **Eine Primitive, fünf wären es fast gewesen:** `state()`, `_z_series()`,
  `_night_z()` und `_signal_bands()` rechnen über `_norm_band`/`_z_at`
  (AST-Wächter auf den Aufrufern). Dabei kam die Log-Diskrepanz von state()
  ans Licht (§7) — behoben als eigener Commit VOR dem Einfrieren der
  No-op-Referenzen. Die Mindestbelegung 20 gilt seitdem auch im
  Trainerurteil. Das Peer-Band in `night_after` bleibt bewusst ungewichtet:
  es aggregiert z-Werte, die bereits gegen gewichtete Basislinien gerechnet
  sind.
- **`analytics` bleibt komplett kontextfrei** — auch `hrv_status`, obwohl es
  die Readiness-Ampel speist. Eine Tages-Gewichtung nur der Ampel-Basislinie
  wäre halbrichtig (die rollenden 7-Tage-Mittel blieben kontaminiert). Die
  Divergenz wird gesagt statt geschluckt: `websocket_readiness` hängt eine
  Herkunftsnotiz an, wenn etikettierte Tage im Fenster liegen. Sauber trennt
  das erst B4. Nebenfund: `ring()` und der `rd`-Parameter von `rTrainer`
  sind im Panel derzeit toter Code — die Ampel rendert nur über Sensor und
  Websocket, nicht im Panel.
- **Der Beschriftungsdialog ist ein FESTER, zentrierter Kasten mit Backdrop**
  — kein am Klickpunkt schwebender Kasten (die 0.9.1–0.9.3-Fehlerklasse).
  Zukunftstage sind nicht beschriftbar: ein Etikett beschreibt eine Messung,
  keinen Plan.
- **Zyklus als Etikett:** offener Punkt für die Veröffentlichung (0.38+),
  bewusst nicht in 0.37.0. Ebenso offen für 0.38.0: die Gewichtungs-Kachel,
  Mehrfachauswahl, das Notizfeld in der Bedienung und der Kurzweg — der
  Schreibweg (`note`-Feld inklusive) trägt sie bereits.

---

## Paket D — Abgleich mit Intervals

**Aufgenommen am 13.09.2026.** Vorrang vor Paket C: ein Archiv mit Karteileichen
verfälscht jede Vergleichsgruppe, weil gelöschte Einheiten als Vergleichspartner
mitzählen. Erst abgleichen, dann den Caliper verfeinern — sonst weiß niemand, ob
sich ein Prozentrang wegen der neuen Toleranz verschoben hat oder wegen einer
Leiche.

### D1 · Der Befund

`async_get_activities(oldest, newest)` holt ein Zeitfenster, und der Importer
**fügt nur hinzu**. Im ganzen Code gibt es keinen Pfad, der eine Aktivität
wieder entfernt. Was einmal im Archiv liegt, bleibt dort — auch wenn es in
Intervals gelöscht wurde.

### D2 · Was die API hergibt (recherchiert, nicht angenommen)

Es gibt **keinen Lösch-Feed** und keinen Zeitstempel, über den sich Löschungen
erkennen ließen. Die offizielle Swagger-Dokumentation ist nachweislich veraltet
— sie erwähnt nicht einmal die `oldest`/`newest`-Parameter, die es längst gibt.
Verlässlich ist nur, was der Endpunkt tatsächlich liefert.

Damit bleibt der **Fenster-Abgleich**: die Antwort für ein Fenster ist
autoritativ, was darin fehlt, existiert nicht mehr. Er ist billiger als
befürchtet, weil der `fields`-Parameter die Antwort serverseitig trimmt —
`fields=id,start_date_local` liefert eine winzige Nutzlast. **`api.py` kann das
bereits:** `async_get_activities()` nimmt `fields` entgegen ("a full season then
fits into a single request"). Die ganze Historie passt damit in einen Abruf,
eine Zeitraumauswahl in der Bedienung entfällt.

**Offen, an der echten API zu prüfen, nicht anzunehmen:** ob der
Aktivitäten-Endpunkt ein `updated`-Feld führt. Für Wellness ist es belegt, für
Aktivitäten nicht.

### D3 · Abgleich, keine Löschfunktion — die Grenze

**Entschieden am 13.09.2026.** Es wird **keine** Bedienhandlung „Aktivität
löschen" gebaut, und sie soll auch später nicht gebaut werden. Gebaut wird ein
Knopf „Mit Intervals abgleichen". Der Unterschied ist nicht Wortklauberei:

- Die Entfernung ist **keine Entscheidung, sondern eine Folge**. Sie hat immer
  nur ein Ergebnis — Gleichstand mit Intervals.
- Sie lässt sich nicht auf eine einzelne Einheit anwenden und nicht
  missbrauchen. Was in Intervals steht, kann in HEIMDALL nicht verschwinden.
- Die Richtung bleibt einseitig: der Abgleich **liest nur**. Der einzige
  Schreibweg der Integration bleibt die geplante Einheit auf den Kalender, und
  der wird hiervon nicht berührt.

### D4 · Die drei Sperren — der eigentliche Inhalt

Ein Fehlschlag darf nie als „alles gelöscht" gelesen werden. Ein Timeout, ein
500er, eine halb gelesene Antwort — und ein Jahr Historie ist weg.

1. Entfernt wird **nur nach einer nachweislich vollständigen, fehlerfreien
   Antwort**. Jede Ausnahme, jeder Fehlerstatus bricht den Abgleich ab, ohne
   etwas anzufassen.
2. **Nur innerhalb des abgefragten Fensters**, nie darüber hinaus.
3. **Deckelung:** fehlen mehr als 20 % der Einheiten eines Fensters, wird
   **nichts** entfernt, sondern gemeldet. Das ist die Sicherung gegen einen
   API-Fehler, der wie eine leere Antwort aussieht.

Dazu die Bestätigung vorher — nicht als Erlaubnis, sondern als Kontrolle:
„3 Einheiten sind in Intervals nicht mehr vorhanden: 04.09. Rad, … — abgleichen?"
Stehen dort beim ersten Lauf plötzlich 40, ist nicht das Archiv falsch, sondern
der Abruf.

### D5 · Drei Aufräumstellen, sonst bleiben Leichen zweiter Ordnung

`activities` ist die offensichtliche. Dazu gehören der `dfa`-Block (an der
Aktivitäts-ID hängend) und die `unavailable`-Liste. Die Zähler im Kopf
("239 Einheiten · 57 DFA") lesen aus allen dreien — bleibt eine stehen, zeigt
das Panel wieder zwei Zahlen, die nicht zusammenpassen.

### Tests D

- Fenster mit einer fehlenden ID: genau diese verschwindet, aus allen drei
  Stellen, keine andere.
- **Sperre 1:** die API wirft — nichts wird angefasst, der Bestand ist
  bit-identisch.
- **Sperre 2:** eine Einheit außerhalb des Fensters bleibt unberührt.
- **Sperre 3:** Fenster liefert 50 % weniger — nichts entfernt, Meldung statt
  Vollzug.
- Der No-op-Fall: ein Abgleich ohne Abweichung verändert das Archiv nicht und
  löst keinen Speichervorgang aus.
- Gegenproben: jede der drei Sperren einzeln entfernen — jede Mutation muss
  gezählt und benannt melden.

### Präzisierungen aus dem Bau (0.38.0 — Paket D geliefert)

**1 · Zwei der drei Aufräumstellen tragen kein Datum.** D5 zählt sie
gleichrangig auf, aber `unavailable` ist eine nackte ID-Liste und eine
DFA-Waise hat keine Aktivität mehr, an der ein Datum hinge. Sperre 2 ist dort
nicht beweisbar. Gelöst über `covers_history()`: die beiden Stellen werden nur
angefasst, wenn das Fenster nachweislich den ganzen Bestand umfasst — ein
einziges unlesbares Datum im Archiv genügt, um das zu verweigern. Eine
Zusicherung, die nur zufällig gilt (weil der Abruf ohnehin voll ist), ist
keine.

**2 · Die Gegenprobe dazu biss zunächst nicht** — Muster 2 aus Paket A, wieder
wörtlich: in der Fixture waren Platzhalter und Waise drüben vorhanden, ihr
Stehenbleiben bewies also nichts. Erst als derselbe Bestand mit denselben
Lücken einmal im Teilfenster und einmal im Vollfenster läuft und zu
verschiedenen Ergebnissen kommen muss, schlug die Mutation an.

**3 · D4 fehlte eine Sperre:** zwischen Anzeige und Klick liegt ein zweiter
Abruf. Der Vollzug schickt deshalb die angezeigten IDs mit; ausgeführt wird
nur die Schnittmenge mit dem frischen Befund, sonst `stale` ohne Handgriff.
Dazu zwei Zustandssperren, die die Spezifikation nicht nennt: ein laufender
Import (er schreibt denselben Bestand und würde seine Kopie danach
zurückschreiben) und eine nie vollständig geholte Historie (dann ist das
Archiv kein Maßstab).

**4 · Die Deckelung zählt die Platzhalter mit.** Rechnete sie nur über
`activities`, könnte ein Abruf, der die Strava-Stubs stillschweigend weglässt,
die ganze `unavailable`-Liste mitnehmen, ohne die 20 % je zu berühren.

**5 · `updated` ist gegenstandslos.** Eine Löschung hinterlässt keinen
Zeitstempel — jeder Löschbefund braucht die vollständige ID-Liste des
Fensters. Ein `updated`-Feld könnte nur Änderungen verbilligen; ob der
Endpunkt eines führt, bleibt für Paket D ohne Folgen.

**6 · Der Importer bleibt nachsichtig, der Abgleich nicht.**
`merge_activities` überspringt eine kaputte Zeile und macht weiter — richtig
beim Hinzufügen. Beim Abgleich hieße dieselbe Nachsicht „diese Einheit gibt es
drüben nicht mehr", also bricht `remote_index()` bei allem ab, wofür die
Antwort nicht geradesteht. Zwei Wege, zwei Urteile, beide geprüft.

### D6 · Der Kalender ist nicht das Archiv (Live-Befund, 13.09.2026)

**Zur Nummer:** die Spezifikation nannte diesen Fix „D2". D2 ist vergeben
(„Was die API hergibt"). Er steht deshalb als D6 hinter den Präzisierungen —
eine zweite D2 wäre genau die Art von Doppelbelegung, gegen die dieses Kapitel
sonst anschreibt.

**Der Befund.** Eine für den 16.09.2026 **geplante** Einheit in Intervals
gelöscht, danach „Abgleichen". Der Dialog meldete Gleichstand über 240
archivierte Einheiten. Die Einheit stand weiter im Kalender. Die Meldung war
wörtlich richtig und trotzdem irreführend. Drei Schichten, nicht eine:

**1 · Der Abgleich sieht geplante Einheiten prinzipiell nicht.**
`reconcile.plan()` baut seine Kandidaten aus `activities`, `unavailable` und den
DFA-Waisen — alles Archiv — und vergleicht gegen `/athlete/{id}/activities`.
Geplante Einheiten liegen auf `/athlete/{id}/events`, gehen über
`coordinator.data["planned"]`/`["events"]` in Kalenderkachel und Kalender-Reiter
und berühren das Archiv **nie**. Der Abgleich kann sie weder finden noch
vermissen. Das ist eine Lücke der Spezifikation, kein Umsetzungsfehler: sie hat
die geplanten Einheiten nirgends erwähnt.

**2 · Die Zahl beschreibt das Archiv und klingt wie eine Aussage über den
Kalender.** Live: `activities: 239`, `unavailable: 1` → `checked = 240`. Der
Satz „alle 240 archivierten Einheiten sind in Intervals vorhanden" sagt nicht,
**was** geprüft wurde und erst recht nicht, was nicht.

**3 · Selbst ein frischer Stand erreicht den offenen Browser-Tab nicht.**
Events werden bei jedem Coordinator-Refresh frisch geholt (Fenster −30/+60 Tage,
Intervall 30 min) — eine gelöschte geplante Einheit fällt also von allein raus.
Aber der Abgleich stößt keinen Refresh an (`async_update_listeners()` rendert
aus den **vorhandenen** Daten), und das Panel hält `_cal` und `_days` für die
ganze Browser-Sitzung: geleert werden sie nur nach einem **angewandten**
Abgleich. Ein Gleichstand wendet nichts an, leert also nichts.

**Was daraus wird:**

- **D6a · Die Meldung sagt, was sie geprüft hat.** Die Aufschlüsselung kommt aus
  der Payload (`checked_activities`, `checked_unavailable`, `checked_dfa`), nicht
  im Frontend aus `status` zusammengerechnet — das wäre die zweite Wahrheit.
  Text: „239 gefahrene Einheiten und 1 Platzhalter". Und sie nennt die Grenze:
  geplante Einheiten sind **nicht** Teil des Abgleichs.
- **D6b · Der Knopf stößt den Refresh mit an.** `await coordinator.async_refresh()`
  nach der Auswertung, in beiden Zweigen. Bewusst `async_refresh()` und nicht
  `async_request_refresh()`: der Entpreller würde genau den Fall überspringen,
  um den es geht. Ein Refresh ist ein Lesevorgang — die Grenze aus D3 bleibt
  unberührt, es gibt weiterhin keine Bedienhandlung „Einheit löschen" und es geht
  weiterhin nichts nach Intervals.
- **D6c · Das Panel leert seine Kalender-Caches nach **jedem** Abgleich**, nicht
  nur nach einem angewandten, und lädt den offenen Reiter neu.

**Tests D6:**

- Der Bericht führt die drei `checked_*`-Zahlen, und ihre Summe ist `checked`.
- Gegenprobe: eine der drei weglassen — die Summenprüfung muss **gezählt und
  benannt** fallen.
- Der Handler ruft den Refresh in beiden Zweigen (Gleichstand und Vollzug).
  Gegenprobe: Refresh nur im Vollzugszweig — muss fallen.
- Quelltext-Wächter: der Abgleich fasst weiterhin keine `events` an und ruft
  keinen schreibenden Endpunkt.

---

## Paket C — Vergleichsgruppe

### C1 · Was heute dasteht

„Verglichen wird mit deinen eigenen früheren Einheiten derselben Sportart,
deren Intensität um höchstens 10 Punkte und deren Dauer um höchstens 40 %
abweicht." 40 % ist geraten, und der Text behauptet eine Strenge, die die Zahl
nicht hat.

### C2 · Was die Forschung macht — und wo sie hier nicht hinreicht

Matching mit **Caliper**. Austin (*Optimal caliper widths for propensity-score
matching*, Pharmaceutical Statistics 10 (2), 2011) empfiehlt aus
Monte-Carlo-Simulationen eine Breite von **0,2 Standardabweichungen**: das
minimiert den mittleren quadratischen Fehler und beseitigt mindestens 98 % der
Verzerrung des rohen Schätzers. Der Kern ist der Handel dahinter: ein enger
Caliper verbessert die Balance und verwirft Fälle (mehr Streuung), ein weiter
behält Fälle und lässt schlechtere Treffer zu (mehr Verzerrung).

**Nachgerechnet am 13.09.2026 am echten Bestand (137 Radeinheiten von 239
Aktivitäten) — die wörtliche Übernahme trägt nicht:**

| | |
|---|---|
| SD der log-Dauer | **0,511** |
| 0,2 SD in Prozent | **−9,7 % / +10,8 %** — nicht ±20 % |
| 0,2 SD auf der Intensität | **2,8 Punkte** (heute: 10) |
| Vergleichseinheiten bei 0,2 SD | **Median 1**, 98,5 % unter n ≥ 8 |
| Leiter 0,2 → 0,3 → 0,4 → 0,6 SD | **75 von 137 erreichen auf keiner Stufe n ≥ 8** |
| heutige Regel (40 % / 10 Punkte) | Median **11** Peers, 36,5 % unter 8 |
| 40 % Dauer entspricht | **0,66 SD** |
| 10 Intensitätspunkte entsprechen | **0,71 SD** |

Zwei Sätze aus dieser Tabelle:

**1 · Die Klammer „0,2 SD ≈ ±20 %" war auf diesen Daten um Faktor zwei daneben**,
und die Leiter „20 → 30 → 40 %" mischte zwei Register: sie will weg von festen
Prozenten und misst die Stufen dann wieder in festen Prozenten. Die heutige
Regel ist bereits ein ≈0,7-SD-Caliper — 40 % war nicht die weiteste denkbare
Stufe, sondern ungefähr die engste, die noch trägt.

**2 · Austin gilt hier nicht 1:1.** Er rechnet Propensity-Score-Matching mit
großem Spenderpool. Hier ist der Pool ≤ 137, und Vergleichspartner müssen
**früher** liegen (`other_day >= day → continue`). Für die ersten Dutzend
Einheiten ist er strukturell leer: nur **129** haben überhaupt acht Vorgänger,
nur **112** haben sechs Vorgänger mit Entkopplungswert. 0,2 SD ist hier kein
strengerer Wert, sondern ein Kategorienfehler.

### C3 · Übersetzung

- Toleranz **nicht in Prozent der Dauer**, sondern als SD-Vielfaches der eigenen
  Dauer-Verteilung derselben Sportart, gerechnet auf der **log-Dauer** — Dauern
  sind rechtsschief, 45 min ↔ 3 h ist kein symmetrisches ±40 %.
- **Gemessene Leiter: 0,2 → 0,4 → 0,6 → 0,8 → 1,0 SD**, auf beiden Achsen,
  **Abbruch bei 1,0 SD**. Das sind schon −40 % / +67 %, breiter als die heutigen
  40 %. 1,5 SD würde 14 weitere Fälle retten, ist mit +115 % aber keine
  Vergleichsgruppe mehr. Ergebnis am Bestand: **91 von 137 bekommen eine Gruppe,
  46 nicht — davon 25 strukturell unmöglich.**
- **Die Weitung läuft gegen das `n` DER KENNZAHL, nicht gegen die Zahl der
  Peers.** Nur 115 von 137 Radeinheiten tragen überhaupt einen
  Entkopplungswert; 14 Fälle haben Peers ≥ 8, aber Entkopplung < Mindestzahl.
  Gegen die Peers zu weiten hieße „±11 %, 8 Einheiten" auszuweisen und daneben
  „zu dünn" zu schreiben — zwei Zahlen im Haus, Lehre 4.
- **Zwei Gründe für „keine Gruppe", zwei Sätze.** Ist der Bestand vor dieser
  Einheit zu klein, heißt das **„zu früh in deiner Historie"** — die 25 Fälle
  oben. Reicht der Bestand, aber kein Fenster füllt ihn, heißt es **„zu wenige
  vergleichbare Einheiten"**. Die beiden dürfen nicht denselben Satz bekommen:
  der erste heilt von selbst, der zweite nicht.
- **Anzeige nie als gelogenes „±".** Ein Log-Caliper ist in Prozent
  unsymmetrisch. Es stehen **beide** Zahlen da („−10 % / +11 %") oder der Faktor
  („0,90× bis 1,11×"). Die gegriffene Stufe wird immer ausgewiesen: „0,4 SD,
  −18 % / +23 %, 11 Einheiten".
- **Die SD wandert.** Sie wird aus dem wachsenden Bestand gerechnet — dieselbe
  alte Einheit zeigt in einem Monat eine andere Gruppe und einen anderen
  Prozentrang. Das steht im Quellenblock, und die Fixture friert dafür einen
  Bestand ein (Lehre 2).
- **Intensität nach derselben Logik** als SD-Caliper, dieselben Stufen.
- **Keine Bedienung, kein Schlüssel im Archiv.** Die Schieber aus der ersten
  Fassung entfallen: sie hätten ein Archivschema samt Migration in ein sonst
  kleines Paket gezwungen, ohne begründbaren Nutzen. Die Leiter läuft
  automatisch. Sollte sich später zeigen, dass daran gedreht werden soll, kommt
  es als `localStorage`-Einstellung in der Bauart des Zeitwählers aus A2 — eine
  **Anzeigepräferenz, kein Datum**.
- Der Beschreibungstext nennt die Weitung und die gegriffene Stufe — sonst
  behauptet die Karte wieder eine Strenge, die sie nicht hat.

### Tests C

- Vertrag: die gewählte Stufe ist immer die **engste**, die das Mindest-`n` der
  Kennzahl liefert.
- Vertrag **Reziprozität**: ist A Vergleichspartner von B, dann ist B es von A
  (zeitliche Reihenfolge ausgenommen). Die heutige Regel
  `abs(other_min - minutes) > minutes * 0.4` misst am *aktuellen* Datensatz und
  verletzt das; der Log-Caliper heilt es. Eigener Test, sonst geht die
  Eigenschaft beim nächsten Umbau wieder verloren.
- Beide Dünn-Fälle getrennt: „zu früh in deiner Historie" (zu wenige Vorgänger
  überhaupt) und „zu wenige vergleichbare Einheiten" (Vorgänger da, Fenster
  leer). Die Fixture enthält **beide unterscheidbar**.
- Die Anzeige enthält nie ein symmetrisches „±" für den Dauer-Caliper —
  Quelltext-Wächter.
- Gegenproben, jede **gezählt und benannt**: feste 40 % wieder einbauen; gegen
  die Peer-Zahl statt gegen das Kennzahl-`n` weiten; die Stufe nicht ausweisen;
  die beiden Dünn-Gründe zu einem Satz zusammenziehen.


---

## Paket F — Die Durability-Kachel auf den Hausstandard

**Aufgenommen am 13.09.2026** nach einem Live-Befund: „Wie lange trägt die
Grundlage?" zeigt drei gleichrangige Zahlen — 0,9 % · 0,7 % · 81 — die sich
nicht zuordnen lassen. Gehört zusammen mit Paket C in ein Release: beides sind
Karten, die Zahlen zeigen, ohne ihre Herkunft mitzuliefern.

### F1 · Was die Kachel rechnet — und was die Recherche daran umgeworfen hat

**Recherchiert am 13.09.2026, danach umgebaut.** Die Kachel teilte bei 90
Minuten und verglich gegen `DECOUPLING_GOOD = 5.0`. Beides hat die Prüfung an
der Literatur und am eigenen Bestand nicht überstanden.

**1 · Die Achse war falsch — Arbeit, nicht Dauer.** Durability wird in der
Literatur durchgehend über **angesammelte Arbeit** indiziert: Maunder 2021
definiert sie als Zeitpunkt und Ausmaß der Verschlechterung von Profilgrößen im
Verlauf langer Belastung; Spragg trennt das Leistungsprofil bei 2000 kJ in
„frisch" und „ermüdet"; in den Monumenten wird nach 30–60 kJ/kg ausgewertet.
Der systematische Review 2025 (Eur J Appl Physiol) schränkt ein: kJ allein
bildet die Intensität nicht ab — ein Arbeits-Schnitt gehört in einen
intensitätsbegrenzten Pool, und genau so steht er hier.

Am eigenen Bestand (81 Einheiten) ist der Unterschied nicht akademisch:

| Trennung | Gruppen | Median klein | Median groß | Leitzahl |
|---|---|---|---|---|
| 90 min (bis 0.38.0) | 41 / 40 | 0,86 % | 0,73 % | **−0,1 pp** |
| 800 kJ | 62 / 19 | 0,61 % | 2,08 % | **+1,5 pp** |
| 800 kJ, ohne Rolle | 40 / 16 | −0,04 % | 2,21 % | **+2,3 pp** |

Der Dauer-Schnitt sagte „die Grundlage trägt", der Arbeits-Schnitt sagt das
Gegenteil. Grund: Dauer ist hier ein schlechter Stellvertreter für Arbeit.

**2 · Die Trennstelle ist eine Setzung und wird so beschriftet.** Belegt ist die
**Achse**, nicht die Zahl: 1.500–2.000 kJ stammen von Rennprofis und liegen über
dem p90 dieses Bestands (1.003 kJ). 800 kJ liegt dort, wo die obere Gruppe
gerade noch belastbar besetzt ist (19 Einheiten) — **nicht** dort, wo der
Unterschied am größten aussieht. Bei 1.200 kJ fällt sie auf 5, und die
kJ/kg-Reihe war bei 12 kJ/kg nicht einmal monoton (0,81 gegen 0,71 bei n = 11).
Genau das ist der Grund, die Schwelle über die Gruppengröße zu begründen und
nicht über den Effekt.

**Absolute kJ, nicht kJ/kg.** Das Gewichtsfeld ist an 6 von 489 Wellness-Tagen
gefüllt — eine kJ/kg-Schwelle stünde auf einem Feld, das jederzeit leer sein
kann. Die Umrechnung bleibt Nebeninformation im Rechenweg und führt **das Datum
des Gewichts** mit, sonst rechnet sie in zwei Jahren mit einem Wert von 2026.

**3 · Die 5-%-Marke ist eine Faustregel, kein Befund.** Sie stammt aus Friels
Trainerpraxis und wurde über TrainingPeaks verbreitet; keine gefundene Arbeit
leitet sie aus Daten ab. Belegt ist das Phänomen dahinter — der kardiovaskuläre
Drift — und dass es stark von der Umgebung abhängt: in Hitze stieg die
Herzfrequenz zwischen Minute 15 und 45 um 11 %, in kühler Umgebung um 2 %.
Setzung und Beleg stehen im Quellenblock **getrennt**, und die Leitzahl
beantwortet die Überschrift über den **Gruppenunterschied**, nicht über das
Über- oder Unterschreiten der Marke.

**4 · VirtualRide fliegt raus — als Homogenitätsargument, nicht als
Gültigkeitsurteil.** Die Literatur belegt nicht „Rollenfahrten sind ungültig".
Sie belegt, dass die Entkopplung umgebungsabhängig ist, und zwar in beide
Richtungen (Brown/Banister: draußen lag die Herzfrequenz bei vergleichbarer
äußerer Arbeitsrate 7–13 % höher als im Labor). Zwei Umgebungen in einem
Vergleich zu mischen ist ein Homogenitätsproblem. Dazu ein Messbefund aus dem
eigenen Bestand: der Variabilitätsindex liegt auf der Rolle bei **1,026**,
draußen bei **1,058** — bei fester Last ist auch das Belastungsmuster ein
anderes. Der Rechenweg sagt genau das, als **begründete Setzung**.

**5 · `icu_intensity < 80` war der falsche Filter.** Die Bedingung für eine
interpretierbare Entkopplung ist **Gleichmäßigkeit**, nicht niedrige
Durchschnittsintensität — das sagt der eigene Quellenblock der Kachel seit jeher,
gefiltert wurde nach etwas anderem. Eine wellige Gruppenausfahrt mit Intensität
70 rutschte durch, ein gleichmäßiger Tempolauf mit 81 flog raus. Der
Variabilitätsindex (normalisierte durch mittlere Leistung) ist aus vorhandenen
Feldern auf **allen 81** Einheiten berechenbar; VI ≤ 1,10 behält 69 davon. Die
Zahl ist eine Setzung, das **Kriterium** ist belegt.

**6 · Derselbe Filter fehlte im Belastungs-Reiter.** `analytics.decoupling_series`
versprach im eigenen Docstring „steady endurance session" und filterte nur nach
Dauer — die Kachel und das Diagramm daneben konnten also Entkopplung aus zwei
verschiedenen Grundgesamtheiten zeigen, ohne dass irgendetwas das gesagt hätte.
Beide fragen jetzt **ein** Prädikat: `derive.steady_endurance_reason()`.

### F2 · Was der Kachel gefehlt hat

- **Die Einheit fehlte.** Dass 0,9 % eine *Entkopplung* ist, stand nirgends.
- **Die Bezugsmarke fehlte** in der Payload — sie steckte im Quelltext.
- **`n` je Gruppe fehlte.** 81 war die Gesamtzahl, nicht die Aufteilung.
- **Keine Leitzahl.** Drei gleich große Zahlen, keine beantwortete die Frage.
- **Kein Rechenweg.**

### F3 · Was daraus wird

- **Leitzahl oben:** um wie viele Prozentpunkte sich die Entkopplung zwischen
  den beiden Arbeitsgruppen unterscheidet. Die Gruppenwerte werden Beleg.
- **Die Marke sichtbar:** zwei Balken gegen dieselbe Skala, die Marke als Linie.
- **`n` je Gruppe.** Unter `MIN_SESSIONS_TO_CLAIM_GROUP` wird der Wert **nicht
  behauptet**, sondern als zu dünn ausgewiesen — und dann gibt es **keine
  Leitzahl**, sondern den Satz, was fehlt: „Keine Aussage über Einheiten ab
  800 kJ: nur 3 Einheiten in dieser Gruppe." Eine Leitzahl aus einer leeren
  Gruppe ist schlimmer als keine.
- **Rundung:** Leitzahl und Gruppenwerte kommen aus **denselben gerundeten**
  Zahlen. Aus den ungerundeten Medianen gerechnet stand neben 0,9 und 0,7 eine
  Leitzahl von 0,1 — wer subtrahiert, liest 0,2.
- **Rechenweg** mit allen fünf Begründungen aus F1, jede als Setzung oder Beleg
  gekennzeichnet.
- **Die Grenze nach vorn**, dorthin, wo sie erklärt, warum Fahrten nicht zählen.

**Ein Fehler, kein Spec-Punkt:** bei leerer Lang-Gruppe fiel `verdict` auf die
kurze zurück und behauptete „die aerobe Basis trägt auch lange Einheiten" —
eine Aussage über lange Einheiten ohne eine einzige lange Einheit. Behoben, mit
eigenem Test und eigener Gegenprobe; Fehlerkapitel PROJEKTSTAND §7.

### F4 · Backend

`durability()` liefert `n_low`, `n_high`, `low_thin`, `high_thin`, `lead`,
`headline`, `dropped` je Ausschlussgrund, `weight` mit Datum — und **jede Zahl,
die das Panel zeigt**: `decoupling_good`, `split_kj`, `min_minutes`,
`max_intensity`, `max_vi`, `min_per_group`, `min_sessions`.

`DECOUPLING_GOOD` lebt in `const.py`. Es stand vorher **zweimal** im Backend
(`coach.py` und `analytics.py`) und **fünfmal** im Frontend — F hätte, nur auf
das Frontend angewandt, genau den Satz verletzt, den es aufschreibt.

**Drei Mindestzahlen, drei Fragen, drei Namen.** Sie auf eine Zahl zu ziehen
wäre derselbe Fehler, nur umgekehrt:

| Konstante | Frage |
|---|---|
| `MIN_SESSIONS_FOR_TILE` (8) | reicht der Bestand für die Kachel überhaupt? |
| `MIN_SESSIONS_TO_CLAIM_GROUP` (5) | darf ein Gruppenwert behauptet werden? |
| `MIN_PEERS_TO_RANK_METRIC` (6) | darf eine Kennzahl als Prozentrang eingeordnet werden? |

Alle drei sind **Setzungen** — das ist Statistik, keine Sportmedizin; eine
Literaturangabe wäre hier eine Behauptung.

### Tests F

- `n_low + n_high == n`, beide in der Payload.
- Eine Gruppe unter der Mindestzahl wird als dünn ausgewiesen, ihr Wert nicht
  gezeichnet, und es entsteht **keine** Leitzahl.
- Leere Lang-Gruppe: das Urteil enthält keine Aussage über große Einheiten.
- Die Leitzahl ist die Differenz der **angezeigten** Werte.
- Je ein Ausschlussgrund pro Fall, einzeln nachgewiesen (Rolle, wellig, hart,
  kurz) — die Fixture belegt, dass jede Zeile an **genau einem** Kriterium
  scheitert.
- Fixture-Beweis: Dauer- und Arbeits-Schnitt liefern an derselben Fixture
  **verschiedene** Aufteilungen, sonst belegt der Vertrag den Umbau nicht.
- Quelltext-Wächter über das **ganze** Frontend, mit eigener Gegenprobe an einer
  eingebauten Konstante.

---

## Eigenes Paket — die restlichen Dubletten und der tote Code

**Aufgenommen am 13.09.2026.** Der Wächter aus Paket F meldet neun
Frontend-Dubletten von vier Backend-Konstanten. Fünf davon (die
Entkopplungsmarke) sind Gegenstand von F und behoben. Die übrigen vier sind
**gezählt und eingefroren**, nicht stillschweigend mitgefixt — 0.39.0 soll kein
Konstanten-Umbau werden:

| Konstante | Backend | Frontend-Dubletten |
|---|---|---|
| `DFA_AEROBIC` / `DFA_ANAEROBIC` | `coach.py` | 2 (Achsenmarken im DFA-Reiter) |
| `ACWR_HIGH` / `ACWR_RISK` | `analytics.py` | 2 (Korridor-Ampel im Belastungs-Reiter) |

Dazu gehörte in dasselbe Paket der **tote `ring()`/`rd`-Code aus 0.37.0**.

**Korrigiert am 13.09.2026 beim Bau von Paket K, nachgesehen statt geglaubt.**
Dieser Absatz stand hier in zwei Punkten falsch, und beide waren aus einem
früheren Sessionbericht übernommen, nicht am Quelltext geprüft. Wer danach
sucht, sucht nach totem Code, den es nicht gibt:

- **`ring()` war tot — `rd` nicht.** `ring()` war einmal definiert und nirgends
  gerufen; es ist in 0.44.0 entfernt, samt `.ring`, `.ringbox`, `.ringword` und
  `.ringsub`, dem Export im Harness und der einen Prüfung in
  `test_panel_views.js` (deshalb 1.165 statt 1.166). **`rd` ist die
  Bereitschafts-Payload:** `_boot()` holt sie, `this._rd` hält sie,
  `rTrainer(c, rd)` verarbeitet sie, drei Testdateien fassen sie an. Sie bleibt.
- **`decoupling_series` hat sehr wohl einen Konsumenten.** `analytics.py`
  Zeile 437 legt sie als `decoupling` in die Payload, und `rBelastung` zeichnet
  daraus das Entkopplungs-Diagramm im Belastungs-Reiter, mit der Marke aus
  `thresholds.decoupling_good`. Wer sie entfernt, entfernt ein laufendes
  Diagramm. **Nichts daran anfassen.**

### Zuerst in diesem Paket: der §7-Eintrag zu J1

**Offen geblieben beim Bau von 0.44.0, dort gemeldet, hier vorgemerkt, damit er
nicht ein zweites Mal untergeht.** Er ist Dokumentation eines negativen
Ergebnisses — es hängt nichts daran, deshalb kein eigenes Release, aber er
gehört ins Fehlerkapitel, und zwar als **eigene Fehlerklasse**.

Der Eintrag benennt die Klasse, nicht den Einzelfall. Nicht „zu wenig Daten" —
das wäre ein Belegungsproblem und ginge mit mehr Fahrten weg. Sondern: **die
Messung misst etwas anderes als behauptet.** Das ist ein Konstruktionsfehler,
und er verschwindet nicht mit mehr Material: zehn weitere lange Fahrten liefern
zehn weitere submaximale Abschnitte.

Was in den Eintrag muss:

- **Der Befund:** Leistungserhalt aus gewöhnlichen Fahrten gerechnet ergab
  93,4 % (t = −2,53) — und bestand damit das Steigungskriterium aus G2.
  Längengleich gerechnet: 99,5 %, t = −0,18. Der Verlust war die Abschnittslänge.
- **Die Placebo-Schwelle als Beleg:** dieselbe Rechnung bei **200 kJ**, wo der
  ermüdete Abschnitt der lange ist, ergibt **+110,2 %, t = +4,18**. Der Athlet
  wäre „signifikant stärker, wenn er müde ist". Gleiches Artefakt, umgekehrtes
  Vorzeichen — und deshalb ein Beweis und nicht bloß ein Verdacht.
- **Was es gefangen hat:** der **längengleiche Kontrollabschnitt**. Nichts
  sonst.
- **Was es NICHT gefangen hätte:** eine Regression auf das Längenverhältnis.
  Die Korrelation zwischen Längenverhältnis und gemessenem Erhalt liegt bei
  **r = +0,18**. Wer den Fehler statistisch zu korrigieren versucht hätte,
  hätte ihn nicht einmal gesehen.
- **Und der Satz, der die Klasse von den anderen drei trennt:** gegen diese
  Fehlerklasse hilft **kein Wächter**. Die anderen drei lassen sich einsperren —
  eine zweite Quelle, ein zweiter Rechenweg, ein stiller Ausstieg sind am
  Quelltext oder am Verhalten erkennbar. Eine Kennzahl, die sauber rechnet und
  dabei die falsche Größe misst, sieht von innen korrekt aus. Was sie auffliegen
  lässt, ist ein **Kontrollabschnitt, den jemand absichtlich baut** — also die
  Frage „was müsste herauskommen, wenn hier nichts wäre?", vor der Messung
  gestellt und mitgerechnet.

**Was von diesem Paket sonst übrig ist:** die vier Frontend-Dubletten
oben. Der Wächter hält die Zahl bei 2 und 2 fest. Steigt sie, ist eine neue
Dublette dazugekommen; fällt sie, ist dieses Paket gelaufen und der Wächter
gehört nachgezogen.

---

## Paket G — Die Durability-Kachel wird eine Kurve

**Aufgenommen am 13.09.2026** nach dem Live-Befund zu 0.39.0. Die Kachel rechnet
seit F das Richtige, aber sie zeigt es nicht: zwei Balken bei 0,0 % und 1,4 %
gegen eine Skala bis 5 % zeigen nichts, kJ ist keine Größe, die ein Fahrer
fühlt, und die Zweiteilung beantwortet die Frage der Überschrift nicht. Gefragt
ist: **wie lange halte ich durch, bevor es kippt — und wird es besser?**

### G1 · Punktwolke statt Balken

Die Feldforschung wertet Durability über eine **Reihe** von Arbeitsschwellen aus
(0–50 kJ/kg; WorldTour-Fahrer heben sich oberhalb 7,5 kJ/kg ab), und die
Praxisauswertung legt Leistungskurven bei mehreren Vorbelastungen übereinander
(frisch / 1.000 / 1.500 / 2.000 kJ). Das Muster ist eine **Kurve über der
Arbeit**, kein Vorher–Nachher.

- x = angesammelte Arbeit der Einheit (kJ), y = Entkopplung (%), ein Punkt je
  qualifizierte Einheit.
- Gewichtete Trendgerade darüber, die 5-%-Marke als Waagerechte.
- Punktdichte und Streuung werden damit sichtbar — heute steckt beides in zwei
  Medianen und ist nicht prüfbar.
- Balken entfallen. Bei Werten von 0,0 % und 1,4 % gegen eine 5er-Skala ist
  Länge das falsche Mittel; Lage auf gemeinsamer Skala schlägt Länge.

### G2 · Die Leitzahl ist der Kipppunkt, in Stunden

Schnittpunkt der Trendgeraden mit der 5-%-Marke, umgerechnet in Zeit:
*„Bis etwa 1.400 kJ bleibst du unter 5 % — rund 2 h 40 bei deiner üblichen
Grundlagenleistung."*

**Nachgemessen am 13.09.2026, vor dem Bau: die Steigung besteht das Kriterium
NICHT.** Gewichtet +2,95 % je 1.000 kJ bei einem Standardfehler von 2,22, also
|t| = 1,33 gegen die geforderten 2,0. Auf zwei weiteren Wegen gegengeprüft, weil
ein Kriterium auch nur ein Kriterium ist: Kendall-Tau z = 1,57, Bootstrap-Intervall
[−1,65; +6,55]. Der Schnittpunkt läge bei 2.398 kJ und damit **jenseits** der
arbeitsreichsten ausgewerteten Fahrt (2.153 kJ) — Regel 1 und Regel 2 feuern
gleichzeitig. Die Kachel nennt heute also keinen Kipppunkt, sondern sagt, woran
es liegt. **Krümmung:** quadratischer Term |t| = 0,85 — eine Gerade ist die
richtige Form, eine Kurve wäre eine Erfindung.

**Umrechnung über die Medianleistung der qualifizierten Einheiten**, nicht über
die aerobe Schwellenleistung — der Pool, der die Punkte liefert, liefert auch
den Umrechnungsfaktor, sonst rechnet die Kachel mit einer Leistung, die in ihren
eigenen Daten nicht vorkommt. Die Schwellenleistung steht als Alternativwert im
Rechenweg. Die verwendete Leistung wird immer genannt.

**Präzisierung 13.09.2026, gemessen.** „Der Pool" darf nicht der ganze Bestand
sein: dessen Medianleistung liegt bei **86 W** und spannt 61–151 W über elf
Monate Progression — derselbe Kipppunkt ergäbe 6 h 45 statt 4 h 15. Gerechnet
wird deshalb mit dem Median der qualifizierten Einheiten der letzten **90 Tage**
(136 W), mit **sichtbarem** Rückfall auf 180 Tage, wenn das nahe Fenster zu dünn
besetzt ist. Der Pool-Median und die Schwellenleistung stehen als Alternativwerte
im Rechenweg.

**Drei Ehrlichkeitsregeln, nicht verhandelbar:**

1. **Nie über den Bestand hinaus hochrechnen.** Liegt der Schnittpunkt jenseits
   der arbeitsreichsten ausgewerteten Fahrt, wird er nicht genannt. Stattdessen:
   „Bis 1.100 kJ — deine längste ausgewertete Fahrt — bleibst du unter der
   Marke. Weiter reichen deine Daten nicht."
2. **Keine Leitzahl ohne erkennbare Steigung.** Die Steigung muss sich von null
   unterscheiden lassen (Vorschlag: Betrag größer als das Doppelte ihres
   Standardfehlers, als Setzung beschriftet). Sonst: „kein Zusammenhang mit der
   Arbeit erkennbar" — das ist eine Aussage, keine Lücke.
3. **Keine Leitzahl unter Mindestbelegung** (effektives n, siehe G3).

### G3 · Gleichmäßigkeit gewichten statt ausschließen

Heute fallen 64 Einheiten als „zu wellig" heraus — mehr als durch jedes andere
Kriterium, und aus 239 Aktivitäten bleiben 45. Das ist eine dünne Grundlage für
eine Trendgerade, und es ist das falsche Werkzeug: **ein Ausschluss ist eine
Ja/Nein-Entscheidung über eine stufenlose Größe.**

- Der Variabilitätsindex wird zum **Gewicht**, nicht zum Türsteher:
  `w = clamp((1,25 − VI) / (1,25 − 1,05), 0, 1)` — VI 1,05 zählt voll, 1,15 zur
  Hälfte, ab 1,25 gar nicht. Die Grenzen sind eine **Setzung** und werden so
  beschriftet.
- Sichtbar im Bild: volles Gewicht = voller Punkt, geringes Gewicht = kleiner
  und blasser. Man sieht, worauf der Trend ruht.
- Die Trendgerade ist eine **gewichtete** Ausgleichsgerade, Mindestbelegung über
  die Summe der Gewichte (Vorschlag Σw ≥ 20, Setzung).
- **Hart bleiben:** Mindestdauer 45 min, Intensitätsgrenze (hält
  Intervalleinheiten draußen — andere Frage als Gleichmäßigkeit), und
  Rollenfahrten (Homogenität, entschieden in F). Der Rechenweg nennt weiter
  jeden Ausschlussgrund mit Anzahl.

Erwartete Wirkung: Datenbasis von 45 auf ~110 Einheiten.

**Nachgemessen am 13.09.2026, vor dem Bau — die Erwartung war falsch: 45 auf 56.**
Die Annahme hinter diesem Kapitel stimmt nicht. Von den 64 Einheiten, die heute
als „zu wellig" herausfallen, haben **53 überhaupt keine Leistungsmessung** —
ohne NP und AP ist kein Variabilitätsindex berechenbar, und was nicht messbar
ist, kann auch nicht gewichtet werden. Tatsächlich wellig (VI zwischen 1,10 und
1,25) sind **11**. Die Gewichtung holt also genau diese 11 zurück, nicht 65.

Daraus folgt zweierlei. Erstens: die heutige Kachel **behauptet etwas über
Fahrten, über die sie nichts weiß** — „64 zu wellige" ist über 53 davon eine
Erfindung. Das ist ein Fehler, kein Spec-Punkt; getrennte Zählung ab 0.40.0,
Fehlerkapitel PROJEKTSTAND §7. Zweitens: der begrenzende Faktor ist nicht die
Gleichmäßigkeit, sondern der Bestand — 85 Einheiten unter 45 Minuten, 38 auf der
Rolle, 53 ohne Leistungsmesser.

### G4 · Der Verlauf über die Saison

Zweites, kleineres Feld: der Kipppunkt je Block (Vorschlag 8 Wochen) über die
Zeit, nur für Blöcke mit ausreichender Belegung; leere Blöcke bleiben leer und
werden nicht interpoliert. **Das ist die eigentliche Frage des Athleten** —
„wird es besser?" —, und zugleich die methodisch sauberere Auswertung: der
Verlauf im eigenen Athleten ist belegt, der Abstand zu einer Populationsgrenze
nicht.

**Präzisierung 13.09.2026 (Lücke in dieser Spezifikation, im Bau gefunden).**
Oben stand nur „ausreichende Belegung". Damit wäre der Blockverlauf eine
Hintertür um G2 gewesen: ein Block mit flacher Steigung oder mit einem
Schnittpunkt jenseits **seiner eigenen** arbeitsreichsten Fahrt hätte trotzdem
einen Punkt in die Kurve gesetzt. **Alle drei Ehrlichkeitsregeln gelten je
Block**, und „der Bestand" ist dort der Block, nicht das Archiv. Ein Block, der
eine Regel reißt, bleibt leer und wird nicht überbrückt — mit Angabe, welche.

Am Livebestand ist das keine Theorie: der 12-Wochen-Block ab 22.04.2026 besteht
aus **vier** Fahrten, liefert |t| = 3,30 und einen Kipppunkt von 640 kJ. Die
Steigungsregel allein hätte ihn durchgelassen; die Belegungsregel fängt ihn.
Dieser Fall liegt als Testfall in der Fixture.

**Blocklänge 12 Wochen statt 8, gemessen.** Bei acht Wochen entsteht auf diesem
Bestand ein Block aus einer einzigen Fahrt und kein Block erreicht die Belegung;
bei zwölf liegt der vollste bei Σw 27, keiner unter drei Einheiten.

**Eigene, niedrigere Mindestbelegung je Block.** Die Pool-Schwelle (Σw ≥ 20)
erreicht auf diesem Archiv kein einziger Block — eine Leitzahl, die nie
erscheint, ist keine. Der Block bekommt seine eigene Zahl mit eigenem Namen.

### G5 · „Was das ausbaut" — die Kachel verweist auf die Einheit

Die Kachel sagt heute, dass es kippt, aber nicht, was dagegen hilft. Belegt ist:
Durability wird **sowohl durch niedrig- als auch durch hochintensives
Ausdauertraining** verbessert (Maunder et al. 2023) und ist unabhängig von der
VO2max trainierbar. Der Reiz entsteht durch Qualität **unter bestehender
Ermüdung**, nicht durch mehr Kilometer.

Eine Zeile mit Verweis auf den Trainer-Reiter (`workouts.py` führt bereits eine
Einheit mit dem Zweck „Durability, spezifisch"), dazu im Rechenweg die drei
Formen: negativ gesplittete Fahrt (letzte 30–60 min zwischen aerober Schwelle
und FTP) · Intervalle an den Anfang einer langen Fahrt, danach 1–2 h ruhig ·
späte Anstiege von 5–20 min, 6–8 Wochen vor einem Ziel.

**Mit der Warnung, die dazugehört:** der Reiz soll aus der Anstrengung kommen,
nicht aus dem Hungerast — schlecht gefütterte Fahrten sind kein
Durability-Training (Empfehlung über 80 g Kohlenhydrate je Stunde).

### G6 · Was NICHT hineingehört

- **Der Amateur-Vergleichsmaßstab** (erfolgreiche Amateure verlieren nach
  1.000 kJ 6,5 % Leistung, weniger erfolgreiche 12,5 %) gehört zum
  **Leistungserhalt**, nicht zur Entkopplung. Er darf als Kontextsatz auftauchen,
  **niemals** als Marke an dieser Skala. Zwei Kennzahlen in einen Maßstab zu
  legen wäre genau die Sorte Fehler, die dieses Paket behebt.
  **Kein Widerspruch zu J5, wo derselbe Maßstab erlaubt ist:** dort misst die
  Kachel Watt gegen Watt wie die Studie, hier Herzfrequenz gegen Leistung. Beide
  Stellen gelten — wer eine davon „aufräumt", hebt die Unterscheidung auf, um die
  es geht.
- **Leistungserhalt selbst** (beste 20-min-Leistung frisch gegen nach 1.000 kJ)
  ist die Kennzahl, die der Forschung am nächsten liegt — braucht aber
  Verlaufsdaten, die heute nur live geholt werden. Eigene Stufe, erst prüfen,
  ob rechenbar.
- **Temperatur als Randnotiz** am Punkt (Entkopplung hängt stark an Hitze und
  Flüssigkeit): nur wenn das Feld in den Aktivitäten vorliegt. Prüfen, nicht
  annehmen.

### Tests G

- Der Kipppunkt wird bei Extrapolation über den Bestand hinaus **nicht** genannt;
  Gegenprobe: Bestand künstlich verkürzen, die Aussage muss umschlagen.
- Keine Leitzahl bei flacher Steigung, keine bei Σw < Mindestbelegung — beide
  einzeln geprüft.
- Gewichtung wirkt: derselbe Bestand einmal mit, einmal ohne Gewichte muss
  verschiedene Trendgeraden ergeben (sonst prüft der Test nichts).
- Zeitumrechnung: die genannte Leistung stammt aus dem Pool, nicht aus einer
  Konstante; Gegenprobe mit verändertem Pool.
- Blockverlauf: leere Blöcke werden nicht interpoliert.
- Alle Schwellen (VI-Gewichtsgrenzen, Σw, Blocklänge, Steigungskriterium) liegen
  in const.py, genau einmal, und in der Payload — unter dem Wächter aus F.

---

## Paket H — Der Kopfbereich der Durability-Kachel

**Aufgenommen am 13.09.2026** nach dem Live-Befund zu 0.40.0. Die Kachel ist
seither ehrlich, aber sie beantwortet die Frage des Fahrers nicht: „wie lange
kann ich fahren, und was soll ich tun, damit es besser wird". Die Kernaussage
steht klein und grau, und „es bräuchte 128 statt 56 Einheiten" ist für einen
Menschen ohne Statistikneigung keine Handlungsanweisung.

**H ist bewusst klein und kommt zuerst**: der größte Verständlichkeitssprung für
den geringsten Aufwand, ohne neue Daten, ohne Archivschema.

### H1 · Drei Zeilen, groß, in der Bauart der Signalkarten

| Zeile | Inhalt | Quelle |
|---|---|---|
| **Was du kannst** | „3 h 10 bei 128 W" — die längste gleichmäßige Fahrt des Bestands, mit Datum | belegt (eigene Messung, kein Modell) |
| **Wie weit du gekommen bist** | längste Fahrt der letzten 30 Tage, als Bezug für den nächsten Schritt | belegt |
| **Was als Nächstes** | „nächste lange Fahrt bis 2 h 15" | Progressionsregel, siehe H2 |

Die erste Zeile ist **demonstrierte Fähigkeit, kein geschätzter Grenzwert**. Sie
steht ab der ersten Fahrt da, sie kippt nicht, wenn die Statistik nicht trägt,
und sie wird mit jeder längeren Fahrt besser. Das ist die Antwort für Nutzer mit
dünner Datenlage — und der Grund, warum H nicht auf J warten muss.

### H2 · Die Progressionsregel

Eine Kohortenstudie über 18 Monate mit mehr als 5.200 Läufern (BJSM) fand ein
deutlich erhöhtes Überlastungsrisiko, wenn eine **einzelne Einheit** die längste
der **letzten 30 Tage** um mehr als 10 % übersteigt. Der Risikofaktor ist der
einzelne Sprung, nicht die Wochensumme.

Die verbreitete 10-%-**Wochen**regel ist dagegen nicht belegt: sie stammt aus
einem Laienratgeber von 1980, und in zwei Untersuchungen senkte sie die
Verletzungsrate nicht.

Also: `nächster Schritt = längste Einheit der letzten 30 Tage × 1,10`, gerundet
auf fünf Minuten. Ist in den letzten 30 Tagen nichts Qualifiziertes gefahren
worden, wird der Bezug ausgeweitet und der Zeitraum genannt — nie still.

**Grenzen, die dranstehen müssen:** die Studie ist an Läufern erhoben, nicht an
Radfahrern; die 10 % sind der gemessene Risikoknick, keine Trainingsvorschrift.
Der Satz sagt, was ohne erhöhtes Risiko geht, nicht was nötig ist.

**Der Rückfall ist die REGEL, nicht der Sonderfall — korrigiert am 13.09.2026,
gemessen.** Diese Fassung las sich, als sei „nächster Schritt liegt unter der
Bestleistung" eine Ausnahme nach einer Pause. Am Livebestand tritt er bei **gut
gefülltem** Fenster ein: längste Fahrt 260 min, längste der letzten 30 Tage
208 min, Schritt 230 — und damit 30 Minuten unter dem, was schon gefahren ist.
Er greift, sobald eine einzelne Ausreißer-Langfahrt mehr als den Faktor über dem
nahen Bezug liegt, also für jeden, der einmal eine hatte, den größten Teil des
Jahres. Also: **kein Sonderzweig, sondern die Regel, sobald Zeile 3 unter Zeile 1
liegt**, mit einem eigenen Satz, der keine Ursache behauptet, die die Kachel
nicht kennt:

> Dein nächster Schritt liegt unter dem, was du schon gefahren bist — der Bezug
> ist bewusst die letzten 30 Tage, nicht deine Bestleistung. Riskant ist der
> Sprung gegen das, was gerade in den Beinen steckt, nicht der Abstand zum
> Rekord.

Eine frühere Fassung endete mit „Nach einer Pause baust du wieder auf." Das ist
gestrichen: die Kachel kann nicht nachweisen, dass eine war — am Livebestand
liegen drei qualifizierte Fahrten im Fenster.

### H3 · Der Rest wandert nach unten

Punktwolke, Bänder, Blockverlauf und die Steigung mit ihrem Standardfehler
bleiben — aber als **Beleg unter der Aussage**, nicht als Botschaft. Die Zeile
„es bräuchte rund 128 Einheiten" wird ersetzt durch den Progressionssatz aus H2;
die Stückzahl wandert in den Rechenweg.

### Tests H

- Die belegte Dauer stammt aus demselben Pool wie die Wolke — Gegenprobe mit
  verändertem Pool, beide Zahlen müssen sich gemeinsam bewegen.
- Kein Bestand in 30 Tagen: der Bezugszeitraum wird ausgeweitet UND genannt.
- Der Progressionsfaktor liegt in const.py, einmal, und in der Payload.
- Gegenprobe: Faktor auf 1,0 setzen — der Satz muss seine Aussage verlieren und
  der Test fallen.

**Nachgetragen am 13.09.2026 aus dem Bau von 0.41.0 — vier Fallen, die hier
fehlten.** Die ersten beiden sind am Livebestand **unsichtbar**, siehe unten.

- **Längste (nach Zeit) ist nicht arbeitsreichste (nach kJ).** Die Kachel druckt
  unten `max_kj` als „arbeitsreichste ausgewertete Fahrt"; oben steht eine Dauer.
  Das können verschiedene Fahrten sein. Beide Superlative werden beschriftet, und
  die Fixture **erzwingt** den Unterschied: eine lange leichte gegen eine kurze
  arbeitsreiche Fahrt.
- **Die Wattzahl in Zeile 1 ist die der Fahrt, nie der Pool-Median aus der
  Umrechnung.** Eine Leihgabe aus einer anderen Rechnung in einer Zeile, die
  „demonstriert" heißt, ist derselbe Fehler wie der Amateur-Maßstab in G6. Die
  Fixture erzwingt eine Kopf-Wattzahl, die vom Pool-Median abweicht.
- **Zeile 2 kann Zeile 1 nie übersteigen**, und beide stammen aus demselben
  Prädikat. „Konstruktiv unmöglich" war in 0.39.0 auch die Annahme, bis `verdict`
  auf die leere Gruppe zurückfiel. Über vier Bestände geprüft.
- **Der Kopf trägt kein Urteilsregister.** Die Bauart der Signalkarten zu
  übernehmen heißt Aufbau und Typografie zu übernehmen, nicht deren Farblogik:
  „was du kannst" ist eine Tatsache, „was als Nächstes" eine Risikoaussage,
  keins von beidem ein Ampelzustand. Das Datenregister ist in dieser Ansicht
  außerdem schon an Wolke (blau) und Trendgerade (violett) vergeben — der Kopf
  bleibt neutral, und ein Test prüft beide Register gegen den Kopfausschnitt.

### H ist NICHT frontend-only — korrigiert am 13.09.2026, vor dem Bau

Die Einordnung „klein, ohne neue Daten" stimmte, „ohne Backend" nicht.
`durability()` emittierte je Punkt `{kj, dec, w, vi, date, id}` — **weder Dauer
noch Leistung**. Beide lagen im Archiv (`moving_time`, `icu_average_watts`), und
`durability()` las die Leistung intern sogar schon, warf sie beim Emittieren aber
weg. „3 h 10 bei 128 W" war aus der Payload von 0.40.0 nicht darstellbar.

Das ist wörtlich Muster 1 aus „Was Paket A über diese Spezifikation gelehrt hat":
vor dem ersten Handgriff nachsehen, welche Felder überhaupt existieren. Der
Umbau hat einen Nebennutzen, der eine Zusicherung ersetzt: Kopf und Punktwolke
kommen jetzt aus **einer** Liste, „gleicher Pool" folgt damit aus der
Datenstruktur statt aus einem Test, der danebensteht.

---

## Paket I — Der Wochenplan als Ansicht

### I1 · Kein zweiter Planer

`plan.py` erzeugt bereits Wochen mit 3:1-Rhythmus und Phasen, `workouts.py`
führt die Einheiten samt Zweck (darunter „Durability, spezifisch"). Der
Wochenplan unter der Kachel ist eine **Ansicht darauf**, kein eigener Motor.
Zwei Planer im Haus wären Fehlerklasse 3 in groß.

**Korrigiert am 13.09.2026, vor dem Bau: die Ansicht gibt es schon.**
`rPlanWeeks()` rendert auf dem Trainer-Reiter (`rGoal` + `rTrainer` +
`rPlanWeeks`) acht Wochen aus `plan.weeks` — Phase, Entlastungswoche, großer
Tag, Wochenstunden, `budget_note` und `caveat`; eingeklappt Titel-Chips,
aufgeklappt `detail`, `why` und `fuel`. I1 und der aufklappbare Teil von I2
waren mit 0.33.0 gebaut. Paket I ist damit **kein Neubau, sondern eine
Erweiterung** — und das ist auch die einzige zulässige Lesart, denn ein
zweiter Wochenplan neben diesem wäre genau der zweite Planer.

Neu sind: die laufende Woche mit erledigt/offen (I2), die vierstufige
Bewertung (I3) und der Quellenblock (I4).

### I2 · Was die Ansicht zeigt

- Acht Wochen, je Woche die vorgeschlagenen Einheiten, aufklappbar mit ihrem
  Zweck und dem, was sie bringt.
- In der laufenden Woche: was erledigt ist, was noch fehlt.
- Je Einheit der laufenden Woche eine von vier Stufen (I3).

**Woher das Erledigte kommt — entschieden am 13.09.2026.** Aus dem **Archiv**,
mitgeliefert in der `goal`-Payload. Nicht aus `_days` im Panel: der Browser
hält `_days` die ganze Sitzung und leert es nur nach einem angewandten Abgleich
(D6, Schicht 3). Eine Wochenansicht, die an diesem Cache hängt, zeigt nach der
ersten Fahrt des Tages weiter den Stand von heute früh. Nicht aus den geplanten
Einheiten in `events`: die berühren das Archiv nie (D6, Schicht 1).

**Und „erledigt" bleibt ungepaart.** Der Plan sagt „SweetSpot 2×20" und
„Grundlage — 1,3 h"; im Archiv liegen Fahrten mit Dauer und Last, ohne Etikett,
welche Plan-Einheit sie hätten sein sollen. Jede automatische Paarung wäre eine
Behauptung, die das System nicht belegen kann — dieselbe Klasse wie „es
bräuchte rund 128 Einheiten" aus H, eine Zahl, die genauer klingt, als sie ist.
Die Ansicht stellt deshalb **gefahren** (Einheiten, Stunden, Last) gegen
**vorgesehen** (Anzahl, Stunden) und sagt hin, dass die Zuordnung Sache des
Fahrers ist.

### I3 · Vier Stufen, an einer Stelle

Je Einheit **der laufenden Woche** eine von vier Stufen. Vier Stufen, vier
Wörter, vier Formen, vier Töne:

| Stufe | Wann | Was sie sagt |
|---|---|---|
| **grün** | Zustand unauffällig, passt ins Lastbudget | normal fahren |
| **gelb** | Zustand trägt nur bedingt (`fit = maybe`), Budget reicht | geht, kostet aber |
| **Reiz** | über dem Budget, ABER Zustand trägt und die letzten Tage boten Erholung | kostet Erholung, setzt aber den Reiz |
| **rot** | Zustand ODER Budget verbieten es — mit Begründung, welches von beiden | heute nicht |

**Die vierte Stufe ist die inhaltliche Neuerung.** Heute kennt das Panel
grün/gelb/rot als Urteilsabstufung, nicht „Reiz" als eigene Kategorie. Belegt
ist sie als **funktionelles Überreichen** (Meeusen 2013, Konsenspapier
ECSS/ACSM): ein kurzer gewollter Einbruch, der nach Erholung in
Superkompensation mündet. Mit der Grenze daneben: neuere Arbeiten zeigen bei
überreichten Athleten teils **schwächere** Anpassungen. Die Aussage ist „gelb
und Reiz gehören dosiert dazu", nicht „je öfter, desto besser".

**Nur die laufende Woche wird bewertet — korrigiert am 13.09.2026, vor dem
Bau.** Die erste Fassung verlangte die Stufe für alle acht Wochen. Das geht
nicht: `load_budget()` rechnet `7 × chronic × Ziel − last_six` aus den letzten
sechs Tagen, und die Zustandsregel liest HRV und Ruhepuls von heute. Für eine
Einheit in fünf Wochen existiert keine der beiden Größen. Eine Stufe dort wäre
**genau die Prognose, die I4 verbietet** — I4 begründet das Nicht-Fragen nach
kommenden Tagen damit, dass das System die Angabe nicht prüfen kann; für das
eigene Urteil gilt dasselbe Argument, sonst misst die Spezifikation mit zwei
Maßen. Spätere Wochen tragen deshalb einen Satz statt einer Stufe: bewertet
wird in der Woche selbst, Budget und Zustand von übernächstem Donnerstag kennt
niemand.

**Die Abwesenheit eines Urteils ist kein fünfter Zustand.** Sie bekommt keine
Urteilsfarbe, keine Urteilsform und kein Urteilswort — sie ist ein Satz im
Fließtext der Woche.

**Die Last der Plan-Einheit ist nicht die Last des Katalogeintrags — Bugfix,
gefunden am 13.09.2026.** Der große Tag heißt im Plan „5,0 h", trägt aber
`z2_210_late`: 210 Minuten, Last 175. Wer `BY_KEY[...]["load"]` gegen das
Budget hält, beurteilt eine dreieinhalbstündige Fahrt statt einer
fünfstündigen — ausgerechnet bei der Einheit, um die es beim Ziel „lange
Fahrten" geht, und systematisch zu grün. Die Last wird auf `session.hours`
skaliert, bei konstanter Intensität linear in der Dauer, an **einer** Stelle in
`workouts.py`, mit eigener Prüfung und eigener Gegenprobe.

### I4 · Die Auswahl trifft der Mensch

Am Tag, an dem trainiert werden soll, wählt der Athlet aus den Vorschlägen —
bewertet nach Zustand und Budget, entschieden vom Menschen. Das Panel fragt
**nicht** nach kommenden Tagen, Schichten oder Terminen: eine Vorab-Angabe wäre
eine Prognose, die das System nicht prüfen kann. Es schlägt vor und bewertet,
mehr nicht.

Das ist nicht die schwächere Variante, sondern die belegte: zustandsgeführtes
Training hatte bei Javaloyes deutlich weniger Nicht-Responder — **1 von 7
gegen 3 von 8** mit Leistungsverlust —, und die beste Variante nutzte die
breiteste Eingabe: Zustand, Befinden, Ruhepuls. **Die Überlegenheit bei der
Leistung selbst ist klein und unsicher**; beides steht im Quellenblock, nicht
nur die erste Hälfte.

### I5 · Der Trainer-Reiter wird mit umgebaut

**Aufgenommen am 13.09.2026, vor dem Bau.** Die Zusammenführung von Zustand und
Budget steht heute **im Frontend**: `rWorkouts` setzt bei `fit === "ok" &&
fits_budget === false` selbst auf Bernstein. Das Backend liefert `fit` und
`fits_budget` getrennt, die Regel „über Budget trotz grünem Zustand" existiert
nur im Panel.

Kommen die vier Stufen ins Backend und bleibt das stehen, stehen **zwei Regeln
im Haus** — Fehlerklasse 3, wörtlich der Fall, den dieses Paket ausschließt.
Also: die Stufe wird in `workouts.py` einmal entschieden, `suggest()` emittiert
sie mit, und **beide** Ansichten lesen sie aus der Payload. Der Umfangszuwachs
gegenüber „nur eine Ansicht" ist der Preis dafür.

Der Schwellen-Wächter aus F deckte bisher nur `rDurability` ab und hat diese
Stelle deshalb nie gesehen. Er wird auf beide Stellen ausgeweitet.

### I6 · Das Urteilsregister bekommt eine vierte Farbe

Es hat drei Töne plus Grau für „unbekannt"; Blau/Violett/Cyan/Magenta/Schiefer
sind das Kategorienregister und bleiben tabu. Die vierte Stufe braucht einen
Ton, der in **keiner** der beiden Listen steht, und eine eigene Icon-Form —
`IC` führt mit `ok`/`warn`/`stop`/`na` vier unterscheidbare Formen, das reicht.
Vier Stufen heißt vier Formen, nicht drei plus eine Schattierung. Der
Register-Test zählt künftig vier Urteilsfarben statt drei.

### I7 · „Erholung war da" ist eine Setzung

Die Reiz-Stufe braucht die Aussage „die letzten Tage boten Erholung". Ohne eine
festgezurrte Regel entsteht sie als zweite Zustandsregel durch die Hintertür.
Sie steht deshalb an **einer** Stelle in `coach.py`, aus Größen, die es schon
gibt:

- Zustand `ready`, **und**
- `hard_days_last_7 == 0`, **und**
- die Last der letzten zwei Tage unter dem chronischen Tagesschnitt.

Die Zahlen sind **gewählt, nicht gemessen** — das steht in der Payload und im
Panel dran, wie bei der Zielwahl je Ampelfarbe im Lastbudget.

### I8 · Nachtrag aus dem Betrieb (0.42.1)

**Live-Befund am 13.09.2026, direkt nach dem Einspielen von 0.42.0:** auf dem
Trainer-Reiter fehlten `rGoal` und `rPlanWeeks` — die einzigen beiden Blöcke,
die `this._goal` brauchen. Ursache ist nicht Paket I: `_boot()` rendert direkt,
`_need("goal")` hängt allein an `_setTab()`, und `_boot` ist diesen Weg nie
gegangen. Der Zielblock war damit seit 0.20.0 beim **ersten** Aufbau
unsichtbar, der Wochenplan seit 0.33.0; ein Klick auf irgendeinen Reiter und
zurück hat es jedes Mal geheilt, weshalb es nie auffiel.

Zwei Fixes, weil es zwei Fehler sind:

- **Der Ladepfad.** `_boot` zeichnet erst das Gerüst und baut den Reiter dann
  über `_setTab` auf. Ein Reiter wird ab jetzt auf genau einem Weg aufgebaut.
- **Der stille Ausstieg**, und das ist der eigentliche Fehler. `_dataGap()`
  trennt drei Zustände: *nie angefordert* (ein Defekt im Panel, wird als
  solcher benannt), *unterwegs* (Ladehinweis) und *fehlgeschlagen* (mit Grund).
  Vorher gab es den ersten Zustand nicht, und er sah aus wie der zweite.

**Und die Testlücke:** die Panel-Tests riefen die Renderer immer mit vorhandener
Fixture auf; eine Zusicherung lautete wörtlich `rPlanWeeks(null) === ""` und hat
den Fehler damit festgeschrieben. Umgedreht, plus ein Wächter über den
Ladepfad: jeder Reiter, den `_render` bedient, muss seine Payload auf dem Weg
über `_setTab` auch anfordern.

### I9 · Eine Karte, nicht zwei Bauarten (0.42.2)

**Live-Befund am 13.09.2026.** Aufgeklappt war die Wochenansicht keine
Entsprechung zur Trainer-Karte, sondern eine Textwand: kein Segmentbalken,
keine Watt- und Pulsbereiche, keine Zweckzeile — stattdessen fünf Absätze
Fließtext, bei drei Einheiten übereinander. Genau das, woran eine Einheit
erkannt wird, fehlte.

Zwei Darstellungen desselben Objekts sind die Layout-Fassung einer zweiten
Regel im Haus. Die gemeinsame Renderfunktion ist deshalb die **Trainer-Karte**:
`_sessionCard()` baut beide Ansichten, und die Wochenansicht bekommt deren
kompakte Variante, keine eigene magerere Bauart. Was dabei an Fließtext
wegfällt, ist richtig — „Was das bringt", Beleg, Grenze, Verpflegung und der
Rechenweg gehören in den **aufklappbaren Teil der Karte**, nicht untereinander
in die Wochenzeile.

Damit das geht, liefert `rate_sessions()` dieselben Felder wie `suggest()`:
Schritte in Watt aus der eigenen FTP, Pulsfenster aus der gemessenen aeroben
Schwelle, Zweck, Beleg und Grenze. Eine Karte, die aus einem dünneren Datensatz
gebaut wird, wird zwangsläufig dünner.

**Die Dauer steht doppelt da, und das mit Absicht.** Die Vorlage `z2_90` trägt
95 Minuten, geplant sind 4,0 Stunden. Die Kopfzeile nennt **beides** —
„geplant 4,0 h · Vorlage 95 min" —, weil das Verschweigen einer der beiden
Zahlen genau der Fehler ist, aus dem der Lastbug bestand. Ob der Segmentbalken
auf die geplante Dauer gestreckt werden soll, ist damit **nicht** entschieden:
siehe die offene Frage unten.

### I10 · Eine Zustandswarnung gehört dem Zustand, nicht der Einheit (0.42.2)

Die Infektwarnung stand bei jeder Einheit derselben Woche erneut — dreimal
untereinander dieselbe Zeile. Beim dritten Mal liest sie niemand. Sie gilt dem
**Zustand**, also steht sie einmal oben.

Und es war eine **Klasse, kein Ort**: derselbe Fehler trat im Trainer-Reiter
auf, sobald mehrere Einheiten dieselbe Zustandsbegründung trugen — im
Einbruchsfall fünfmal. `_sharedReasons()` sammelt deshalb die Begründungen, die
**mehr als eine** Einheit teilen, und stellt sie einmal über die Liste; eine
Begründung, die nur eine einzelne Einheit betrifft („zwei harte Tage liegen
schon in dieser Woche"), bleibt an ihrer Karte. Beide Ansichten nutzen denselben
Sammler, und beide werden darauf geprüft.

### I11 · Die Hochrechnung ist die Herleitung, nicht die Aussage (0.42.2)

„Last 118 · Budget 94 (Katalogeinheit 72 bei 95 min — auf 2,6 h hochgerechnet)"
war als Nachweis richtig und in der ersten Zeile falsch. Oben steht die
Aussage — `Last 118 · Budget 94` —, der Klammerzusatz wandert in den
Rechenweg im aufklappbaren Teil. Die Zahl war der teuerste Fund von Paket I;
sie muss **nachweisbar** bleiben, nicht dauerhaft sichtbar. Ein Wächter prüft
beides: nichts von der Hochrechnung im Kartenkopf, und sie steht vollständig
im aufgeklappten Teil.

### I12 · Elastizität ist eine Eigenschaft des Abschnitts (0.43.0)

**Entschieden am 13.09.2026**, nachdem 0.42.2 die Frage offengelassen hatte.
Der Segmentbalken wird auf die geplante Dauer gebracht — aber **nicht** über
eine Schwelle, die jemand herleitet, sondern über eine **Autorenangabe je
Abschnitt** im Katalog:

- Einrollen, Ausrollen, Intervalle und Pausen sind **fest**.
- Gleichmäßige Blöcke sind **elastisch** und nehmen die Differenz auf.

Die Marke steht am Block selbst (`(80, 68, "gleichmäßig", True)`). Damit gibt
es keine neue Zahl im Haus — nur eine Aussage, die derjenige trifft, der die
Einheit ohnehin geschrieben hat.

**Belegt und Setzung stehen getrennt — nachgeschärft am 13.09.2026.** Die erste
Fassung hat die ganze Regel als „Angabe des Autors" beschriftet. Das war zu
bescheiden: der wichtigste Teil ist belegt.

- **Belegt, und damit nicht verhandelbar: das Einrollen wächst nicht mit.** Die
  Literatur verschreibt Aufwärmen in **absoluten Minuten** — 10 bis 15, optimal
  15 bis 20, bei Ausdauerbelastungen über drei Stunden eher 10 bis 15. Zu
  langes Aufwärmen ermüdet nachweislich: traditionelles Aufwärmen über 50
  Minuten erzeugte Ermüdung und minderte die Leistung (J Appl Physiol 2011,
  „Less is more"). **Je länger die Einheit, desto weniger Aufwärmen — nicht
  mehr.** Intervalle stehen ebenso absolut in der Literatur (4×4, 2×20, 5×8),
  nie als Anteil einer Gesamtdauer.
- **Setzung, und als solche beschriftet: dass die Differenz auf den
  gleichmäßigen Block geht.** Das *folgt* aus dem Belegten — wenn Aufwärmen,
  Intervalle und Ausrollen fest sind, bleibt nichts anderes übrig —, ist aber
  selbst nicht gemessen.

Beides steht im **aufklappbaren Teil der Karte**, in zwei getrennten Zeilen
(„Beleg" und „Grenze"). Zusammengezogen fängt die Setzung an, als Befund
durchzugehen; ein Test prüft deshalb nicht nur, dass beide Aussagen dastehen,
sondern auch, dass sie **nicht im selben Feld** stehen.

**Wo es keinen elastischen Abschnitt gibt, wird nicht gestreckt.** Die
40-Minuten-Regenerationsfahrt, der abgestufte Wiedereinstieg und jedes
Intervallprotokoll **sind** ihre Dauer; eine längere Fassung zu erfinden hieße,
dem Autor Worte in den Mund zu legen. Für diese Einheiten bleibt die
Doppelangabe „geplant X · Vorlage Y" stehen — sichtbar, statt still etwas zu
dehnen. Ein Test geht jede Vorlage durch: entweder sie hat einen dehnbaren
Abschnitt, oder sie wird nachweislich nicht gestreckt.

Heute betrifft das die vier Z2-Vorlagen (dehnbar) gegen elf feste. Die
Schrittliste wird bei gestreckten Einheiten **aus den Blöcken gebaut**: der
handgeschriebene Text der Vorlage nennt ihre eigenen Minuten, und zwei Dauern
für eine Einheit sind die Form des Lastfehlers, eine Ebene höher.

**Die Last bleibt, wo sie war.** Sie kommt weiterhin aus `session_load()` —
lineare Skalierung der Kataloglast über die Dauer — und *nicht* aus der
gestreckten Blockliste. Zwei Wege auf dieselbe Zahl wären genau das, was Paket
I ausschließt; ein Test hält das fest.

### Tests I

- Die vier Stufen: ein Bestand, in dem **dieselbe** Einheit je nach Zustand
  grün, gelb, Reiz und rot wäre. Sonst prüft der Test die Einheit, nicht die
  Stufe.
- Rot nennt, welches von beiden verbietet — Zustand, Budget oder beides; je ein
  Fall.
- Lastskalierung: eine Plan-Einheit, deren Stunden von den Katalogminuten
  abweichen, und eine, bei der sie übereinstimmen. Gegenprobe: Skalierung
  ausbauen — die Prüfung muss **gezählt und benannt** fallen.
- Spätere Wochen tragen keine Stufe: Quelltext- und Payload-Wächter, plus der
  Nachweis, dass der Satz dasteht.
- Wächter: weder `rPlanWeeks` noch `rWorkouts` führen eine eigene Schwelle;
  jede Stufe kommt nachweislich aus der Payload. Gegenprobe mit
  wiedereingebauter Regel.
- Register: vier Urteilsfarben, vier Formen, vier Wörter, keine davon im
  Kategorienregister; der Satz für spätere Wochen trägt **keine** davon.
- Erledigt/offen: gefahren gegen vorgesehen, ohne Paarung. Die Fixture enthält
  eine Fahrt, die zu **zwei** Plan-Einheiten passen würde — der Test prüft,
  dass die Ansicht sich für keine entscheidet.
- Der Quellenblock trägt beide Hälften des Javaloyes-Befunds: die Zahlen der
  Nicht-Responder **und** die kleine, unsichere Überlegenheit bei der Leistung.

---

## Paket E — Der Kalender läuft rechts aus dem Bild

### E1 · `1fr` ist nicht „ein Siebtel"

**Live-Befund, 13.09.2026.** Der Kalender-Reiter schiebt sich rechts aus dem
Fenster. `.wkrow` und `.calhead` benutzen `grid-template-columns: 190px
repeat(7, 1fr)`. `1fr` ist die Kurzform von `minmax(auto, 1fr)` — die Spalte
darf also **nicht unter ihre Inhaltsbreite schrumpfen**. Eine Tageszelle mit
einem langen Aktivitätsnamen setzt damit ihre eigene Mindestbreite, sieben
davon plus 190 px sprengen die Zeile, und das Raster wächst über den
Viewport hinaus statt umzubrechen.

Das ist kein Kalender-Sonderfall, sondern die häufigste Grid-Falle überhaupt:
`1fr` verteilt den ÜBRIGEN Platz, garantiert aber keine Obergrenze.

**Der Fix, drei Teile — keiner allein reicht:**

- `minmax(0, 1fr)` statt `1fr`: die Spalte darf jetzt kleiner werden als ihr
  Inhalt.
- `min-width: 0` auf den Zellinhalten: Flex- und Grid-Kinder haben
  `min-width: auto`, das dieselbe Sperre eine Ebene tiefer noch einmal
  aufbaut. Ohne das schiebt der Chip die Zelle weiter auf.
- Lange Namen werden **gekürzt** — Auslassungspunkte plus `title`-Attribut, so
  dass der volle Name beim Überfahren lesbar bleibt. Abschneiden ohne `title`
  wäre Informationsverlust; abschneiden ohne Zeichen dafür wäre eine stille
  Kürzung, und still ist in diesem Haus die falsche Antwort.

**Tests E1:**

- Quelltext-Wächter: kein `repeat(7, 1fr)` in den Rasterregeln des Kalenders,
  und `minmax(0, 1fr)` steht dort. Gegenprobe mit wiedereingebautem `1fr`.
- Die Zellinhalte tragen `min-width: 0`.
- Ein langer Aktivitätsname erscheint gekürzt UND vollständig im
  `title`-Attribut. Gegenprobe: `title` entfernt — muss fallen.

---

## Paket J — Ermüdungswiderstand aus Sekundendaten

### J1 · Gemessen am 13.09.2026 — das Ergebnis: es trägt nicht

Die Messung aus der ersten Fassung dieses Kapitels ist gelaufen, lesend, am
Livebestand (239 Aktivitäten, 13.05.2025 bis 11.09.2026). **Leistungserhalt ist
aus gewöhnlichen Fahrten nicht rechenbar.** Nicht wegen der Datenmenge und nicht
wegen des Aufwands — die sind harmlos —, sondern weil die Zahl, die dabei
herauskommt, die Abschnittslängen misst und nicht die Ermüdung.

**Die Belegung.** 116 Radfahrten tragen einen Leistungsstrom. Davon erreichen,
mit genug Restfahrt, um einen ermüdeten Abschnitt zu füllen (Freiluft /
inklusive Rolle):

| Schwelle | ≥ Schwelle | + 5 min Restfahrt | + 20 min Restfahrt |
|---|---|---|---|
| 800 kJ | 16 / 19 | 14 / 17 | **11 / 13** |
| 1.000 kJ | 7 / 9 | 5 / 6 | **4 / 5** |
| 1.500 kJ | 3 / 3 | 2 / 2 | **1 / 1** |

1.000 kJ ist damit kein Schwellenwert, sondern ein Einzelfallfilter; 1.500 kJ
scheidet aus. Gerechnet wurde bei **800 kJ** über alle 19 Fahrten ab dieser
Marke.

**Befund 1 · Es wurde nie maximal gefahren.** Der beste 5-Minuten-Abschnitt
dieser Fahrten liegt bei 75,4 % der FTP (Spanne 61,2–92,5 %). Das ist keine
Faustregel, sondern am eigenen Bestand gegengerechnet: die gemessene
5-Minuten-Bestleistung im aktuellen Formniveau beträgt **251 W** (23.07.2026,
119,5 % FTP), mehrfach bestätigt durch 242–245 W an anderen Tagen. Der
„frische" Abschnitt der langen Fahrten kommt im Mittel auf **171 W** — **68 %**
dieser Kapazität, im besten Fall 78 %. Verglichen werden also nicht zwei
Leistungsfähigkeiten, sondern zwei Geländeabschnitte.

**Befund 2 · Der scheinbare Verlust ist ein Längenartefakt.** Dieselben 19
Fahrten, einziger Unterschied: der frische Abschnitt wird auf dieselbe Länge
beschnitten wie der ermüdete (die letzten L Sekunden vor dem Schwellenübertritt,
L = Länge des ermüdeten Abschnitts).

| Rechnung | Mittel | SD | t gegen 100 % |
|---|---|---|---|
| frisch = alles vor 800 kJ | 93,4 % | 11,4 | **−2,53** |
| frisch = gleich langer Abschnitt | **99,5 %** | 11,2 | **−0,18** |

Die ungleiche Rechnung besteht das Steigungskriterium aus G2 (|t| > 2) — und
zwar ausschließlich deshalb, weil ein Maximum über mehr Material höher ausfällt.
Längengleich gerechnet ist der Verlust null.

**Befund 3 · Die Placebo-Schwelle beweist es.** Dieselbe Rechnung bei 200 kJ,
wo der ermüdete Abschnitt der lange ist: **110,2 %**, t = **+4,18**. Der Athlet
wäre „signifikant stärker, wenn er müde ist". Gleiches Artefakt, umgekehrtes
Vorzeichen.

**Warum eine Korrektur das nicht rettet.** Die direkte Korrelation zwischen dem
Längenverhältnis der Abschnitte und dem gemessenen Erhalt liegt bei r = +0,18 —
eine Regression auf die Abschnittslänge hätte den Fehler nicht gefunden. Was ihn
findet, ist der längengleiche Kontrollabschnitt. Das ist ein Konstruktionsfehler,
kein Statistikfehler, und er verschwindet nicht mit mehr Fahrten: fehlende
Maximalanstrengung ist kein Belegungsproblem. Zehn weitere lange Fahrten liefern
zehn weitere submaximale Abschnitte.

**Der Aufwand, gemessen — damit ihn niemand neu misst:**

- **Abrufe:** einer je Fahrt über `intervals_icu/streams`. 19 Fahrten in **7,4 s**,
  0,39 s je Fahrt; die längste Fahrt (268 min Bewegungszeit) einzeln 0,42 s.
  Gemessen über die HA-Uhr, inklusive Ausdünnung auf 900 Punkte und sieben
  Kanäle — J bräuchte nur `time` und `watts`, der Wert ist also eine Obergrenze.
- **Rohdatenmenge:** die 19 Fahrten tragen 180.641 s Bewegungszeit, alle 116
  Leistungsfahrten zusammen 588.102 s. Zwei Kanäle, ungedünnt, grob 5 Byte je
  Zahl: **~1,8 MB** für die 19, **~5,9 MB** für alle. Einmalig, nichts davon
  bleibt liegen.
- **Archivzuwachs:** ein Kennzahlensatz je Fahrt (`p5_fresh`, `p5_fat`,
  `p20_fresh`, `p20_fat`, `fresh_s`, `fat_s`, `thr_kj`, `v`) misst **122
  Zeichen**. Über 116 Fahrten **~14 kB** gegen ein Archiv von rund 300 kB. Der
  Archivzuwachs war nie das Problem.

**Messmethodisches zum Nachlesen.** Gerechnet auf den ausgedünnten Strömen des
Panel-Endpunkts (max. 900 Punkte, Schrittweite 7–18 s je nach Fahrtlänge),
Rollmittel über eine **Bewegungszeit**-Achse: Lücken über 60 s zählen weder als
Arbeit noch als Fahrzeit. Ohne diese Achse bricht die Fensterbildung an jeder
Fahrtpause ab — in der ersten Rechnung dieser Session lieferte sie
20-Minuten-Werte ohne zugehörige 5-Minuten-Werte, was unmöglich ist und den
Fehler verriet. Die so summierte Arbeit liegt 2–3 % über `icu_joules`; für eine
Ja/Nein-Entscheidung unerheblich, für einen Bau nicht — der echte Durchlauf holt
die ungedünnten Ströme.

### J2 · Was daraus folgt

J ist als **Auswertepaket geschlossen.** Es wird nichts gebaut, das Leistungserhalt
aus dem vorhandenen Bestand herausrechnet.

J bleibt als **Protokollpaket offen.** J3 bis J7 beschreiben, wie es dann
aussieht. Der Unterschied ist die Datenquelle, nicht die Darstellung: die Werte
kommen aus einer Messeinheit, nicht aus geklaubten Abschnitten. J8 sagt, was in
der Zwischenzeit mit dem Mittelteil der Kachel geschieht.

### J3 · Die Leitdarstellung ist ein Hantel-Diagramm

Nicht zwei Kurven. Ein **Hantel-Diagramm** (dumbbell):

- Je Dauer **eine Zeile**: 5 min und 20 min. Zwei Punkte je Zeile — frisch und
  ermüdet —, verbunden durch einen Strich. **Der Abstand ist die Aussage**, nicht
  die Lage und nicht die Farbe.
- **Gefüllter Punkt = frisch, hohler Punkt = ermüdet.** Die Form trägt die
  Unterscheidung, nicht die Farbe allein (Hausregel Dreifachkodierung; beide
  Punkte stehen im selben Register, es ist kein Urteil).
- **Direkte Beschriftung am Punkt** — der Wattwert steht am Punkt, der
  Prozentwert am Verbindungsstrich. **Keine Legende.**
- **Genau zwei Punkte je Zeile.** Kein dritter Zustand, keine Zwischenpunkte,
  keine Fehlerbalken an der Hantel. Was mehr zeigt, gehört in den Rechenweg.
- Gemeinsame Watt-Achse für beide Zeilen, damit die Abstände vergleichbar sind.
  **Die Achse beginnt nicht bei null** — eine Hantel zeigt einen Abstand, und ein
  Nullpunkt drückt ihn optisch platt. Dafür stehen beide Wattwerte am Punkt und
  der Prozentwert am Strich: die Zahl trägt die Aussage, das Bild ordnet sie ein.
  Das ist eine **Setzung** und wird so beschriftet.
- Mehrere Messtermine übereinander wären ein Kleinvielfaches und gehören in den
  Verlauf, nicht in die Leitdarstellung.

### J4 · Die zwei Leistungskurven gehören in den Rechenweg, nicht nach oben

Die Zwei-Kurven-Darstellung (Leistung über Dauer, frisch gegen nach X kJ) ist die
etablierte Praxis in WKO5 und TrainingPeaks. Sie ist der richtige Ort, um zu
zeigen, **woher** die zwei Punkte kommen — aber sie ist nicht die Aussage: eine
Kurve über sechs Dauern beantwortet sechs Fragen gleichzeitig, die Kachel stellt
eine. Also in den Rechenweg, mit derselben Kodierung gefüllt/hohl.

**Und nur, wenn es Stützstellen gibt.** Liefert das Protokoll wie in J8 nur 5 und
20 min, sind das **zwei Punktepaare, keine Kurve** — eine interpolierte Linie
über zwei gemessene Dauern ist eine Erfindung. Die Zahl der Stützstellen steht
je Kurve dabei.

### J5 · Der Amateur-Vergleichsmaßstab gehört HIER hin — mit zwei Bedingungen

Die Zahl: erfolgreiche Amateure verlieren nach 1.000 kJ **6,5 %** über 20 min,
weniger erfolgreiche **12,5 %** (Frontiers in Sports and Active Living 2025,
„Enhanced durability predicts success in amateur road cycling"). Als
Größenordnung daneben: 20 gut trainierte Amateure verloren nach demselben
1.000-kJ-Protokoll 10,1 ± 6,5 % über 20 min und 10,8 ± 7,8 % über 5 min
(BMC Sports Sci Med Rehabil 2025).

**Warum er hier erlaubt ist und in G6 verboten — dieser Absatz bleibt stehen,
sonst hebt ihn jemand später als vermeintlichen Widerspruch wieder auf.** G6
handelt von **Entkopplung**: Herzfrequenz gegen Leistung, Prozent Drift. Der
Maßstab ist an **Leistungserhalt** erhoben: Watt gegen Watt. Das sind zwei
verschiedene Größen, und den Maßstab an die Entkopplungsskala zu legen hieße,
zwei Kennzahlen in einen Maßstab zu legen — genau der Fehler, den Paket G behebt.
Hier misst die Kachel dieselbe Größe wie die Studie: derselbe Zähler, derselbe
Nenner, dieselbe Schwellenarbeit. Deshalb darf er hier als Marke stehen.

**Bedingung 1 — nur neben protokollgemessenen Werten.** Der Maßstab ist an
**All-out-Zeitfahren** nach einem normierten Ermüdungsprotokoll erhoben: 70–80 %
der frischen 20-min-Leistung bis 1.000 kJ, danach 5- und 20-min-TT. Neben Werten,
die aus gewöhnlichen Fahrten geklaubt sind, ist er falsch — das ist exakt der
Fehler, den J1 misst. Liegt keine Protokollfahrt vor, erscheint die Marke nicht.

**Bedingung 2 — nur an der 20-Minuten-Zeile.** Die Studie fand für das
5-Minuten-Intervall **keinen** Unterschied zwischen den Gruppen. Die 5-min-Hantel
bleibt ohne Marke, mit dem Satz dazu, dass dort keine Trennung belegt ist. Eine
Marke an beiden Zeilen wäre eine Erfindung mit Quellenangabe.

### J6 · Die Skala wird nicht geliehen

WKO führt eine vergleichbare Größe („Stamina", 0–100 %, typisch 70–90) — aber aus
einem proprietären Modell. **Deren Bereich darf nicht als Maßstab für eine anders
gerechnete Zahl dienen.** Bezug ist der eigene Verlauf über die Zeit, nicht eine
fremde Population. Das ist etwas anderes als J5: dort stimmt die gerechnete
Größe mit der Studie überein, hier ist das Modell unbekannt.

### J7 · Archivschema und Migration — die Lücke aus 0.35.0 darf sich nicht wiederholen

- Neuer Block im Archiv (Vorschlag `durability_tests`), **eingetragen in
  `importer.empty_data()`**. Ohne diesen Eintrag entsteht der Block auf
  Altbeständen nie: `store.async_load` füllt fehlende Schlüssel nur auf der
  obersten Ebene auf. Das ist die Lücke aus 0.35.0, zum dritten Mal — nach `goal`
  und `day_context`.
- Dazu eine Migration **in der Bauart von `plan.migrate_goal()`**: aufgerufen in
  `store.async_load`, gibt `None` zurück, wenn nichts zu tun ist, sonst den
  normalisierten Block; `schedule_save()` **nur** im Änderungsfall. Die
  eingefrorene No-op-Referenz aus `test_coach` gilt hier genauso — ein No-op darf
  keinen Speichervorgang auslösen.
- **Versionsmarke je Satz** (`v`), Bauart `DFA_ALGO_VERSION` /
  `ACTIVITY_FIELDS_VERSION`: ändert sich die Rechnung, werden gespeicherte Sätze
  verworfen und neu gerechnet. Die Ströme liegen nicht im Archiv, also erreicht
  eine Korrektur die alten Werte sonst nie.
- Gespeichert werden nur Kennzahlen, nie Ströme: `p5_fresh`, `p5_fat`,
  `p20_fresh`, `p20_fat`, `fresh_s`, `fat_s`, `thr_kj`, `v` — 122 Zeichen je
  Fahrt (J1).

### J8 · Was stattdessen mit dem Mittelteil der Kachel geschieht

**Entschieden am 13.09.2026: Weg 1, in zwei Stufen. Ausgeführt als Paket K.**
Die Wege 2 und 3 bleiben als Begründung stehen, damit nachvollziehbar ist,
wogegen entschieden wurde — nicht als offene Auswahl.

Drei Möglichkeiten, in der Reihenfolge der Empfehlung.

**1 (empfohlen) · Der Mittelteil bleibt, wie er ist — und der Aufwand geht in die
Messeinheit.** `workouts.py` führt bereits die Familie „Durability, spezifisch".
Dazu kommt eine **Messeinheit nach dem Studienprotokoll**: 5- und 20-min-All-out
frisch, dann 70–80 % der frischen 20-min-Leistung bis 1.000 kJ, dann 5- und
20-min-All-out. Auf der Rolle sauber fahrbar — der Bestand zeigt 1.216 kJ in
130 min bei 156 W, das Protokoll ist in gut zwei Stunden erledigt, und die Rolle
hält die Bedingungen konstant, was für einen Vergleichswert wichtiger ist als
Freiluft-Homogenität. Erst wenn **eine** solche Fahrt im Bestand liegt, zeichnet
die Kachel die Hantel; ab **zwei** auch den Verlauf. Bis dahin steht an der
Stelle ein Satz, was fehlt, plus der Knopf, der die Einheit in den Kalender legt
— dieselbe Bauart wie „Was das ausbaut" in G5.

**2 · Der Innenverlauf einer Fahrt.** Die Kachel hat heute einen Punkt je Fahrt;
das Innere einer Fahrt ist ungenutzt. Rollende 20-min-Fenster, Verhältnis
Herzfrequenz zu Leistung, aufgetragen über die kumulierte Arbeit **innerhalb
einer Fahrt**, wählbar je Fahrt, gezeichnet nur für Fahrten, die die Filter aus
G3 ohnehin bestehen. Das braucht keine Maximalanstrengung — genau deshalb
funktioniert die Kachel heute mit Entkopplung und nicht mit Watt. **Mit der
Bremse:** ein Bild, keine Leitzahl, keine Schwelle, keine Urteilsfarbe. Ein
rollendes HF/Watt-Verhältnis reagiert auf Gelände, Hitze und Intensitätswechsel;
als Beschreibung ist das ehrlich, als Zahl wäre es die nächste Auflage desselben
Fehlers.

**3 · Nichts.** Die Kachel ist mit Kopf, Wolke, Bins und Blockverlauf bereits
dicht. Nichts zu bauen ist ein gültiges Ergebnis einer Messung.

**Nicht 1 und 2 im selben Release.** 2 kommt nur, wenn der Mittelteil nach 1
sichtbar leer wirkt.

### Tests J

Erst relevant, wenn J als Protokollpaket gebaut wird — hier festgehalten, damit
die Bau-Session sie nicht neu erfindet.

- **Längengleich ist Pflicht:** eine Fixture, deren ungleiche Rechnung einen
  Verlust zeigt und deren längengleiche Rechnung keinen. Der Test muss den
  Unterschied sehen — sonst prüft er nichts (Lehre 2 aus Paket A: zwei
  unterscheidbare Fälle in der Fixture).
- **Bewegungszeit statt Uhrzeit:** Fixture mit 20 min Pause mittendrin. Ohne die
  Bewegungszeit-Achse bricht die Fensterbildung ab; die Gegenprobe muss das
  Fehlen der 5-Minuten-Werte melden, nicht daran abstürzen.
- **Keine Hantel ohne Protokollfahrt:** Gegenprobe mit Fahrten aus dem
  gewöhnlichen Bestand — die Kachel darf nichts zeichnen und muss sagen, warum.
- **Die Marke aus J5 an der 20-min-Zeile und nicht an der 5-min-Zeile:** beide
  Zeilen einzeln prüfen, nicht nur eine.
- **Migration (J7), drei Fälle einzeln:** Altbestand ohne Block → Block entsteht;
  Bestand mit kaputtem Block → wird normalisiert; Bestand mit gültigem Block →
  **kein** Speichervorgang.
- Alle Schwellen (Zieldauern, Schwellenarbeit, Mindestzahl Protokollfahrten,
  Achsen-Setzung aus J3) liegen in `const.py`, genau einmal, und in der Payload —
  unter dem Quelltext-Wächter aus F.

---

## Paket K — Die Durability-Messung als Einheit

Die Fortsetzung von J nach Weg 1 aus J8, in zwei Stufen: **Stufe 1** ist der
Katalog samt Zuordnung (K1, K2, K4), **Stufe 2** die Hantel (K3). Stufe 2 wird
erst gebaut, wenn Stufe 1 zwei Messungen geliefert hat — vorher gäbe es nichts
zu zeichnen.

### K0 · Das Protokoll und seine Quelle

Barsumyan, Soost, Burchard: „Durability as an independent parameter of endurance
performance in cycling", BMC Sports Sci Med Rehabil 17:192 (2025). Heimtest an
zwei Terminen, ausdrücklich für Amateure entwickelt statt für Profis — die
älteren Protokolle (Spragg, Leo, ~4-h-Vorbelastung, 40 kJ/kg) sind an kleinen
Profikohorten erhoben und für einen Schichtarbeiter mit Rolle nicht fahrbar.

- **Termin 1 (frisch):** standardisiertes Einrollen → 5 min all-out →
  20 min all-out.
- **Termin 2 (ermüdet, anderer Tag):** Einrollen → fahren bei 80 % der
  **frischen 20-Minuten-Leistung**, bis 1.000 kJ Arbeit geleistet sind →
  5 min all-out → 20 min all-out.

Validierung an 20 gut trainierten Amateuren: **−10,1 ± 6,5 %** über 20 min,
**−10,8 ± 7,8 %** über 5 min. Zu standardisieren sind Arbeit in kJ, Route bzw.
Rolle und die Energiezufuhr vor und während.

**Der Anker kommt aus Termin 1 selbst — und das ist keine Bequemlichkeit,
sondern die Rettung dieses Protokolls auf diesem Konto.** Gemessen am
13.09.2026:

| Feld | Wert | was es ist |
|---|---|---|
| `icu_ftp` | **215 W**, über alle Fahrten konstant | der im Intervals-Profil **eingetragene** Wert |
| `icu_rolling_ftp` | **192–194 W** | Intervals' eigene Schätzung **aus den Leistungsdaten** |
| `icu_pm_ftp` | 132–194 W, je Fahrt schwankend | Einzelfahrt-Schätzung, als Anker unbrauchbar |
| beste gemessene 20-min-Leistung | **192 W** (aktuelles Formniveau) | siehe J1 |
| gemessene aerobe Schwelle | **146 W** (DFA alpha-1 = 0,75) | Anker-Konflikt im Trainer-Reiter |

Die 215 bewegen sich seit Monaten keinen Watt, während die datengetriebene
Schätzung bei 193 liegt und die tatsächlich gefahrene 20-Minuten-Bestleistung
bei 192. **Die 215 sind gesetzt, nicht abgeleitet, und liegen rund 10 % zu
hoch.** Ein aus ihnen abgeleitetes Protokolltempo wäre 80 % von 226 W
(= 215 / 0,95) ≈ **181 W** — 35 W über der gemessenen aeroben Schwelle, also
kein Ermüdungsblock, sondern ein Tempotest bis zum Abbruch. Aus der gemessenen
frischen 20-Minuten-Leistung ergeben sich **~154 W**, knapp über der aeroben
Schwelle, und das ist die Absicht des Protokolls.

**Daraus eine Plausibilitätsregel, die gebaut wird:** liegt die aus Termin 1
errechnete Zielleistung **unter** der gemessenen aeroben Schwelle, war Termin 1
kein All-out. Die Einheit wird dann nicht ausgegeben, sondern sagt das — mit
beiden Zahlen. Ein Ermüdungsblock unterhalb der aeroben Schwelle ermüdet nicht.

### K1 · Zwei Katalogeinheiten in `workouts.py`

Bauart wie `z2_210_late` (`key`, `title`, `purpose`, `minutes`, `intensity`,
`load`, `blocks`, `text`, `hr_hint`, `dfa`, `effect`, `evidence`, `limit`,
`states`). Neue Familie in der Familienliste, damit sie nicht unter „Lange
Fahrt" verschwindet.

**`durability_test_fresh` — „Durability-Test, frisch"**

- Einrollen 20 min · 5 min all-out · 10 min locker · 20 min all-out ·
  10 min ausrollen. Rund **65 min**.
- Die Reihenfolge 5 vor 20 stammt aus dem Protokoll und wird nicht gedreht.
  Die 10 min dazwischen sind eine **Setzung** (das Protokoll nennt keine
  Erholungsdauer) und werden so beschriftet — aber sie müssen bei beiden
  Terminen **gleich** sein, sonst vergleicht der zweite Termin etwas anderes.
- `evidence` trägt die Quelle aus K0, `effect` sagt, was gemessen wird:
  die beiden frischen Bezugswerte, aus denen alles Weitere folgt.

**`durability_test_fatigued` — „Durability-Test, ermüdet"**

- Einrollen 20 min · Ermüdungsblock bei **80 % der frischen
  20-Minuten-Leistung**, bis **1.000 kJ** im Block geleistet sind · direkt
  anschließend 5 min all-out · 10 min locker · 20 min all-out · ausrollen.
- **Die Zielleistung ist kein Katalogwert, sondern wird gerechnet** — aus dem
  Ergebnis von `durability_test_fresh`. Liegt kein frischer Test vor, erscheint
  die Einheit **nicht** im Katalog, sondern ein Satz, dass Termin 1 fehlt, plus
  der Knopf, der ihn in den Kalender legt. Dieselbe Bauart wie „Was das ausbaut"
  in G5.
- **Dauer ist keine Konstante, sondern folgt aus der Zielleistung**: bei 154 W
  braucht der Block 1.000.000 J / 154 W ≈ **1 h 48**, der ganze Termin also
  knapp **drei Stunden**. Die angezeigte Dauer wird mitgerechnet, nicht
  eingetragen — sonst steht sie nach der nächsten Messung falsch da (dieselbe
  Falle wie die Last des großen Tags in I3).
- `load` wird wie in I3 auf die gerechnete Dauer skaliert, nicht als Zahl
  gepflegt.

**Standardisierung, in `limit` und im Panel bei beiden Einheiten:**

1. **Rolle**, nicht Straße — konstante Bedingungen sind für einen Vergleichswert
   wichtiger als Freiluft-Homogenität. Der Ermüdungsblock in **ERG**, die
   All-out-Abschnitte **nicht** in ERG (ERG deckelt genau das, was gemessen
   werden soll).
2. **Gleiche Mahlzeit im gleichen zeitlichen Abstand** vor beiden Terminen.
   Während Termin 2 mindestens `DURABILITY_FUELLING_G_PER_H` (80 g
   Kohlenhydrate je Stunde, G5) — bei drei Stunden also rund 240 g. Der Reiz
   soll aus der Arbeit kommen, nicht aus dem Hungerast; ein schlecht gefütterter
   Termin 2 misst die Energiezufuhr.
3. **Die 1.000 kJ zählen ab Beginn des Ermüdungsblocks**, nicht ab Fahrtbeginn.
   Der Radcomputer zeigt die Gesamtarbeit — der Wert beim Blockstart wird
   notiert und 1.000 addiert. Das steht als Satz in der Einheit, nicht als
   Fußnote.
4. Gleiche Tageszeit, gleicher Lüfter, gleiche Übersetzung. Alles, was nicht
   gleich war, gehört in den Rechenweg der Kachel.

**Die Ausschlussregel aus F/G gilt hier NICHT.** `DURABILITY_EXCLUDED_TYPES`
hält `VirtualRide` aus der Entkopplungs-Wolke heraus, weil dort Bedingungen
vergleichbar sein müssen. Hier ist die Rolle genau richtig. Die Bau-Session muss
aufpassen, dass sie ihre eigenen Testfahrten nicht wegfiltert — das ist der
naheliegendste Fehler in diesem Paket.

### K2 · Die Zuordnung trifft der Athlet, nicht die Erkennung

Nach dem Muster von „gefahren gegen vorgesehen" (I2) und dem Tageskontext (B):
**der Athlet markiert eine Fahrt als frischen oder ermüdeten Test.** Eine
automatische Erkennung — „lange Fahrt mit zwei harten Blöcken am Ende, das wird
der ermüdete Test sein" — wäre wieder eine Behauptung über eine Fahrt, über die
das System nichts weiß. Genau die Fehlerklasse aus J1 und aus dem
„64 zu wellige"-Befund in G3.

- Schreibweg wie `set_day_context`: ein eigener WebSocket-Befehl, der in den
  Archivblock aus J7 schreibt, Schlüssel ist die `activity_id`.
- **Auch die Paarung ist Sache des Athleten.** Beim Markieren eines ermüdeten
  Tests wird gefragt, zu welchem frischen Test er gehört; gibt es genau einen,
  wird der vorgeschlagen und **bestätigt**, nicht gesetzt. Automatisch den
  nächstliegenden vorherigen zu nehmen, wäre dieselbe Paarung, die
  `test_analytics` an anderer Stelle ausdrücklich verbietet.
- Die Markierung ist **rücknehmbar**. Ein falsch markierter Test darf nicht
  bedeuten, dass das Archiv von Hand repariert werden muss.
- Der **Zustand am Testtag** wird nicht mitgespeichert, sondern aus
  `state_series()` für das Datum gerechnet und neben der Messung gezeigt (K4).
  Gespeichert wird nur, was nicht wieder herleitbar ist — dieselbe Regel wie bei
  den Strömen.

### K3 · Stufe 2: die Hantel erst bei zwei Messungen

- **Weniger als ein Paar (frisch + ermüdet): keine Hantel.** Der Mittelteil der
  Kachel bleibt exakt wie er ist (Wolke, Bins, Blockverlauf aus G). Eine leere
  Kachelfläche mit einem Platzhalter wäre schlechter als gar nichts.
- An der Stelle steht bis dahin ein Satz, welcher der beiden Termine fehlt, plus
  der Knopf. Der Satz nennt den Grund, nicht nur den Mangel.
- Liegt ein Paar vor, zeichnet die Kachel die Hantel nach **J3**: zwei Zeilen
  (5 und 20 min), je zwei Punkte, gefüllt gegen hohl, direkte Beschriftung,
  Achse nicht bei null (Setzung, beschriftet). Die Marke aus **J5** steht an der
  20-Minuten-Zeile und **nicht** an der 5-Minuten-Zeile — die Studie fand für
  5 min keinen Gruppenunterschied. Das ist keine Vorsichtsmaßnahme, die man
  später lockern kann, sondern die Aussage der Quelle.
- Ab dem **zweiten Paar** kommt der Verlauf: dieselben zwei Zeilen über die
  Termine, im Register des Blockverlaufs aus G4. Ein Paar ist ein Wert, zwei
  Paare sind eine Richtung — und die Ehrlichkeitsregeln aus G2 gelten auch hier:
  aus zwei Punkten wird keine Gerade gelegt.

### K4 · Die ermüdete Einheit ist die härteste im Katalog

- **`states`: `["ready"]`.** Bei gelbem oder rotem Zustand misst der Test die
  Ermüdung statt der Durability — das ist kein Sicherheitshinweis, sondern ein
  Messfehler. Die Einheit wird dann nicht als „geht, kostet aber" ausgegeben,
  sondern als **rot mit Begründung, welches von beiden** (Zustand oder Budget),
  nach der Wahrheitstabelle aus I3.
- **Die Vierstufigkeit aus I3 gilt unverändert**, inklusive der Stufe „Reiz".
  Eine Ausnahme für die Testeinheit würde genau die Regel aufweichen, die I3
  gegen Sonderfälle verteidigt.
- `limit`-Text in der Bauart von `z2_210_late`: mindestens zwei ruhige Tage
  davor, grüner Zustand, keine harte Einheit in den 48 h danach. Und der Satz,
  warum: ein Test in müdem Zustand liefert eine Zahl, die später nicht mehr von
  einer echten Verschlechterung zu unterscheiden ist.
- **Der Zustand am Testtag wird neben dem Ergebnis ausgewiesen** (K2). Ein Paar,
  dessen ermüdeter Termin auf einen gelben Tag fiel, bleibt sichtbar
  gekennzeichnet — sonst wandert es beim nächsten Vergleich als gültiger Wert
  mit durch.
- `durability_test_fresh` ist demgegenüber harmlos (65 min, zwei kurze
  All-outs), braucht aber denselben grünen Zustand: der frische Bezugswert ist
  der Anker für alles Weitere, und ein zu niedriger Anker macht den
  Ermüdungsblock zu leicht und den gemessenen Erhalt zu gut.

### Was der Bau von K an dieser Spezifikation korrigiert hat

**Nachgetragen am 13.09.2026, nach 0.44.0.** Drei Stellen, alle vor dem Bau
gemeldet und freigegeben — nach dem Muster aus „Was Paket A über diese
Spezifikation gelehrt hat".

**1 · K1 war nicht „zwei Katalogeinheiten in `workouts.py`" — geprüft am Feld,
nicht am Text.** Die Zielleistung von Termin 2 ist 80 % der frischen
20-Minuten-Leistung. Dieser Wert steht in **keinem** archivierten Feld:
`ACTIVITY_FIELDS` führt `icu_average_watts`, `icu_weighted_avg_watts` und
`icu_joules`, aber keinen Wert aus der Leistungskurve. Also zieht K2 das ganze
**J7** mit herein — Archivblock, Eintrag in `importer.empty_data()`, Migration
in `store.async_load`, und ein Messweg, der beim Markieren die **ungedünnten**
Ströme holt und das beste 5- und 20-Minuten-Mittel über eine Bewegungszeit-Achse
rechnet. Ohne das wäre `durability_test_fatigued` toter Katalogcode gewesen.
Das ist wörtlich Muster 1 aus der Paket-A-Lehre, diesmal im Auftrag selbst.

**2 · „`load` wird wie in I3 auf die gerechnete Dauer skaliert" gilt hier
nicht.** `session_load()` streckt einen Katalogwert im Verhältnis der Stunden,
und sein eigener Docstring nennt die Bedingung: **konstante Intensität**. Eine
längere Grundlagenfahrt ist dieselbe Fahrt, nur länger. Der Ermüdungsblock ist
das nicht: er hält die **Arbeit** fest, also macht eine niedrigere Zielleistung
ihn zugleich **länger** und **lockerer**. Der Stunden-Skalierer sieht nur die
erste Hälfte und zöge die Last in die Richtung, der die zweite widerspricht.
Deshalb wird sie aus den Abschnitten **gerechnet** (`protocol_load`), mit
`icu_ftp` als Bezug — nicht mit dem Anker, weil das Budget, gegen das die Zahl
gehalten wird, aus Intervals' eigener Lastrechnung kommt und zwei verglichene
Zahlen auf derselben Bezugsgröße stehen müssen. **Der Anker entscheidet die
Watt, die FTP entscheidet, was sie kosten.** Der Grund steht im Rechenweg auf
der Karte, nicht nur im Code, sonst baut es die nächste Sitzung wieder als
Konstante.

**3 · Die Ausschlusswarnung zielte auf den falschen Filter.** K1 warnt vor
`DURABILITY_EXCLUDED_TYPES`. Es sind aber **drei** Tore in
`derive.steady_endurance_reason()`, und der frische Test (65 min, zwei
All-outs) fliegt über das **Intensitätstor** (`DURABILITY_MAX_INTENSITY`, ≥ 80)
raus, bevor der Typ überhaupt geprüft wird. Für die Entkopplungswolke ist das
richtig — dort hat er nichts verloren. Der Markierungs- und Messweg aus K2 läuft
deshalb an **allen dreien** vorbei, mit Gegenprobe in beide Richtungen.

### Tests K

- **Die Zielleistung von `durability_test_fatigued` kommt aus dem frischen
  Test**, nicht aus der FTP: Gegenprobe mit verändertem frischem Ergebnis — die
  Zielleistung muss mitwandern. Und eine zweite Gegenprobe mit einer FTP von
  215 im Archiv: die Zielleistung darf sich **nicht** ändern.
- **Kein ermüdeter Test ohne frischen:** Gegenprobe, die Einheit darf nicht im
  Katalog stehen und der Ersatzsatz muss erscheinen.
- **Plausibilitätsregel aus K0:** Zielleistung unter der gemessenen aeroben
  Schwelle → die Einheit wird nicht ausgegeben, mit beiden Zahlen im Text.
- **Keine Hantel unter einem Paar** und **keine Gerade unter zwei Paaren:**
  beide einzeln geprüft.
- **Die Marke aus J5 an der 20-min-Zeile und nicht an der 5-min-Zeile:** beide
  Zeilen prüfen, nicht nur eine.
- **Keine automatische Erkennung und keine automatische Paarung:** ein Bestand
  mit zwei unmarkierten, protokollförmigen Fahrten darf **nichts** zeichnen.
- **`VirtualRide` wird hier nicht ausgefiltert:** ein Paar auf der Rolle muss
  gezeichnet werden. Gegenprobe gegen die Filter aus G3.
- Die Dauer der ermüdeten Einheit ist gerechnet, nicht eingetragen: Gegenprobe
  mit zwei verschiedenen Zielleistungen.
- Alle Schwellen (Protokolldauern, 1.000 kJ, 80-%-Faktor, Erholungsdauer
  zwischen den All-outs) in `const.py`, genau einmal, und in der Payload — unter
  dem Quelltext-Wächter aus F.

---

## Paket L — Die Ermüdungskurve der aeroben Schwelle

Gemessen am 13.09.2026, lesend am Livebestand. **Die Kurve wird nicht gemessen.
Sie wird an einem eigenen Wert verankert und aus der Literatur gezeichnet.** Was
davon Beleg ist und was Setzung, steht in L1 Zeile für Zeile.

### L0 · Drei gescheiterte Runden — damit es niemand ein viertes Mal versucht

**Vorbemerkung zur Nachprüfbarkeit.** Die Zahlen der Runden 1 und 2 stammen aus
dem Bericht der damaligen Session; die Zwischentabellen sind verloren und nicht
rekonstruierbar. Sie stehen hier, damit die Richtung erkennbar bleibt — **die
Lehre zählt, nicht die letzte Nachkommastelle.** Runde 3 ist vollständig
nachgerechnet und mit Belegung ausgewiesen.

**Runde 1 — ein Kipppunkt je Fahrt.** Aus jeder Fahrt wurde ein einzelner
Umschlagpunkt gelesen. Übrig blieben **vier brauchbare Punkte, alle zwischen 129
und 153 W**, und in **12 von 19 Fällen** markierte der „Kipppunkt" den ersten
Berg statt die Ermüdung. Eine Geländeform wurde als Physiologie gelesen.

**Runde 2 — alpha aus Watt und Zeit modelliert.** Ein Modell für alpha aus
Leistung und Dauer, aufgelöst nach 0,75. Ergebnis: **246 W bei kurzer Dauer
gegen 146 W beim Trainer**, und das Modell verfehlte die **54 real gemessenen
Schwellenfenster um 82 W**. Das Modell war nicht falsch gerechnet, es war an
einem Bestand gerechnet, der die Antwort nicht enthält.

**Die Lehre aus 1 und 2 ist dieselbe:** die Kurvenform aus einem Bestand
pressen, der sie nicht enthält. **Die Form kommt aus der Literatur, der Anker
aus den eigenen Daten** — das ist die Konsequenz, und sie ist in L1 gebaut.

**Runde 3 — Repräsentantenmethode je Fahrtstunde, gepaart.** Diesmal mit der
Methode aus Andriolo/Rummel/Gronwald (siehe L1), angewandt nicht auf
Kalenderfenster, sondern auf Fahrtstunden-Bins, und **gepaart**: nur Fahrten, die
zwei benachbarte Bins selbst befüllen, damit jede Fahrt ihre eigene Kontrolle
ist. Live abgerufen: 79 Fahrten ab einer Stunde, davon 31 mit DFA-Strom.

| Rechnung | n | Mittel | SD | Permutation |
|---|---|---|---|---|
| Bewegungszeit, Stunde 1 → 2 | 21 | **−6,6 W** | 21,6 | **p = 0,189** |
| Kumulierte Arbeit, 0–500 → 500–1000 kJ | 25 | −4,5 W | 17,6 | p = 0,219 |
| nur Fits mit R² ≥ 0,75 | **3** | −31,9 W | 11,2 | p = 0,256 |

**Trägt nicht.** Bei der dritten Zeile ist der p-Wert zudem bedeutungslos: bei
drei Paaren kann der Vorzeichen-Permutationstest **strukturell nicht unter 0,25
fallen**. Der Test hat dort keine Trennschärfe, unabhängig vom Ergebnis.

**Runde 3 ist aber ein anderer Fehler als 1 und 2, und das ist die neue Lehre.**

Ungepaart ergibt derselbe Bestand **−9,3 W**, gepaart **−6,6 W**. In J1 klafften
die beiden weit auseinander (93,4 % gegen 99,5 %) — das war der Beweis für das
Längenartefakt. **Hier liegen sie nah beieinander: es gibt keinen
Konstruktionsfehler.** Richtung und Größenordnung stimmen sogar — alle vier
Rechnungen zeigen Abfall, und −4,5 bis −9,3 W je Stunde passt zu Gallo. Was
fehlt, ist die Absicherung: der erwartete Effekt in diesem Stundenschritt liegt
bei **3 bis 4 W**, die Streuung der Einzelmessungen bei **21,6 W**. Um das zu
trennen, bräuchte es grob **150 gepaarte Fahrten statt 21**.

**Die Messung widerspricht der Literatur also nicht — sie kann sie nur nicht
bestätigen.** Das ist ein anderer Satz als „es trägt nicht", und beide gelten.

**Die Falle in Runde 3, die beim nächsten Versuch sofort ausgeschlossen werden
muss:** die drei Fahrten mit R² ≥ 0,75 waren **allesamt SweetSpot-Rollenfahrten**
(24.08. „SweetSpot 2x20Min", 20.08. „volumen + SweetSpot 2x15Min", 14.08.
„SweetSpot 2x20Min"). Die Blöcke liegen in Stunde 1, danach wird ausgefahren.
Die −31,9 W sind **der Trainingsplan, nicht die Ermüdung** — Runde 1 in neuer
Verkleidung, diesmal nicht der erste Berg, sondern der erste Block. Ein
Gütekriterium auf den Fit hat die Auswahl genau auf die strukturierten Einheiten
verengt und damit den Störer eingesammelt statt ihn auszuschließen. **Wer es
erneut versucht, schließt strukturierte Einheiten vorher aus, nicht nachher.**

### L1 · Die Kachel — Anker gemessen, Form aus der Literatur

**Die Form.** Gallo, Faelli, Ruggeri, Filipas, Codella, Plews, Maunder: „Power
output at the moderate-to-heavy intensity transition decreases in a non-linear
fashion during prolonged exercise", Eur J Appl Physiol 124:2353–2364 (2024),
open access. Zwölf trainierte Radfahrer, Alter 40 ± 8, VO2peak 52,3 ± 5,2,
Wochenumfang 10,3 ± 3,4 h. Quadratischer Verlauf bei 11 von 12,
Anpassungsgüte R² 0,92 ± 0,09. Zeit bis 5 % Abfall 139 ± 78 min (Spanne
21–279), Time-to-task-failure 234 ± 66 min, Zusammenhang r_s = 0,676, p = 0,016.

Die veröffentlichten Polynomkoeffizienten liegen nicht vor — modelliert wurde je
Teilnehmer. **Die Gruppenmittelwerte liegen vor**, und daraus ist die Form
rekonstruierbar: ausgeruht 184 ± 35 W, nach einer Stunde 181 ± 37 W (kein
signifikanter Unterschied, p = 0,290), im Test unmittelbar vor dem Abbruch
165 ± 34 W (p < 0,001). Drei Punkte, letzter bei t ≈ 3,4 h (rund eine halbe
Stunde vor den 234 min):

> **P(t) / P₀ = 1 − 0,0104·t − 0,0059·t²**   (t in Stunden)

**Die Probe, die sie trägt:** diese Kurve erreicht −5 % nach **130 min**.
Publiziert sind **139 ± 78 min**, aus einer unabhängigen Rechnung (individuelle
Fits). Sensitivität gegen die Annahme zum letzten Testzeitpunkt: bei 3,0 h →
119 min, bei 3,8 h → 140 min. Alles innerhalb der publizierten Streuung. **Die
Form ist belastbar, die Punktgenauigkeit ist es nicht.**

**Der Anker.** Andriolo, Rummel, Gronwald: „Relationship of Cycling Power and
Non-Linear Heart Rate Variability from Everyday Workout Data", Sensors 2024, 24,
4468, open access. 3.123 Alltagseinheiten von 21 Radfahrern, kein Labor. Der
Hebel ist nicht das Poolen, sondern die **Repräsentantenmethode**: die
DFA-Achse wird in Intervalle geschnitten, je Intervall der Mittelwert von
Leistung und alpha gebildet, und nur diese Mittelpunkte werden korreliert. Das
räumt den kardialen Nachlauf aus. Wirkung: mittlere Korrelation bei Gruppen von
−0,32 auf −0,75, Anteil stärker als −0,7 von 4 % auf 66 %. Abgelesen wird über
den linearen Fit P = m · DFA-a1 + q als P(0,75) = 0,75m + q.

**Warum Andriolo den Anker liefert und nicht die Kurve — und warum die beiden
Zahlen auseinanderlaufen dürfen.** Ihre Methode wertet **nur die Minuten 5 bis
20 jeder Einheit** aus; sie schließt Ermüdung ausdrücklich aus. Ihr Ergebnis ist
die Schwellenleistung im praktisch unermüdeten Zustand. **Das ist kein Mangel,
das ist die Bauart**, und es ist der Grund, warum ein aus ganzen Fahrten
gemittelter Wert tiefer liegen muss als der Ankerwert. **Wer die eine Zahl an
der anderen „korrigiert", zerstört genau die Trennung, auf der diese Kachel
steht.**

**Beschriftung, verbindlich:** „Repräsentantenmethode nach Andriolo, auf
Intervals' eigener DFA-Fensterung". **Nicht** „nach Andriolo gerechnet". Die
Abweichungen gehören in den aufklappbaren Rechenweg der Karte, nicht nur hierhin:

- **Keine RR-Daten.** Intervals liefert `dfa_a1` als fertigen Sekundenstrom
  (`derive.py`, `DFA_STREAMS`). Andriolos Vorverarbeitung — 120-s-Fenster,
  5-s-Gitter, Artefaktkorrektur, Detrending mit Lambda 500 — ist nicht
  nachbaubar. Die Fensterung ist Intervals' eigene und nicht dokumentiert.
- **Ausdünnung — KORRIGIERT beim Bau (0.45.0), sie trifft nicht zu.** Der
  Panel-Endpunkt liefert `sample_secs` zwischen 5 und 18 s und mittelt über den
  Bucket — der IMPORTWEG aber nicht: `api.async_get_streams()` holt ungedünnt,
  und dort entsteht die Auswertung. Gerechnet wird also sauberer, als diese
  Spezifikation annahm. **Kehrseite:** die Messzahlen unten (152,5 W und die
  Prüfpunkttabelle) sind an GEDÜNNTEN Daten entstanden. Sie dürfen deshalb in
  keinem Test als Erwartungswert stehen — der Test prüft die Rechenvorschrift,
  die Kachel rechnet den Anker aus dem Bestand.
- **Artefaktkriterium entfällt.** Andriolos Grenze von 5 % ist nicht abbildbar,
  weil kein Artefaktfeld existiert. **Ersatzmaß** (ausdrücklich als solches
  beschriftet, nicht als Andriolos Kriterium): Anteil verworfener Punkte je
  Fahrt — HF null, Watt null, alpha außerhalb 0 bis 2. Gemessen: Median 1,7 %,
  Mittel 2,3 %, Maximum 14,4 %; zwei Fahrten über 5 % (25.06. mit 14,4 %,
  26.06. mit 8,5 %). Fahrten oberhalb der Grenze werden gekennzeichnet, nicht
  stillschweigend verworfen.
- **Dynamikkriterium gelockert.** Andriolo verlangt, dass mindestens die Hälfte
  der Punkte unter alpha 1,0 liegt. Am eigenen Bestand erfüllen das **13 von 70
  Bins (18,6 %)**, Median des Dynamikanteils **19,6 %**. Mit dem Kriterium
  bliebe zu wenig übrig, um irgendetwas zu entscheiden. Es wird deshalb **als
  Kennzahl je Bin ausgewiesen statt als Filter angewandt** — und diese Abweichung
  steht im Rechenweg.

**Die Zeitachse ist die Bewegungszeit**, entschieden an der Belegung: die
kJ-Achse liefert praktisch dieselbe (26/27/5/1/1 gegen 26/23/5/1/1), weil 500 kJ
bei rund 150 W etwa 55 Minuten entsprechen. Die Belegung gibt also keinen Grund
für kJ; damit entscheidet der zweite Grund, und der spricht dagegen: **die
kJ-Achse koppelt an die Intensität und holt den Bergeffekt aus Runde 1 zurück.**
Die kJ-Rechnung läuft als Gegenprobe mit, nicht als Hauptachse.

**Was die Kachel zeigt.** Drei Kurven, wie gebrieft — aber die mittlere ist nach
Runde 3 keine Kurve mehr, sondern zwei Punkte:

| | Inhalt | Beleg |
|---|---|---|
| GEMESSEN | Stunde 1: **151,5 W** (26 Fahrten) · Stunde 2: **142,2 W** (23 Fahrten) | eigene Messung |
| HEUTE | letzter 10-Tage-Block nach Andriolo, sofern ≥ 4 Fahrten | eigene Messung |
| SCHÄTZUNG | P₀ = **152,5 W**, Form nach Gallo, Streuung als sichtbares Band | Setzung |

**Die Leitzahl oben** ist der Anker P₀ = 152,5 W bei Dauer null, darunter der
Beleg: 26 Fahrten, Stunde 1, Repräsentantenmethode. Der aufklappbare Rechenweg
trägt die vier Abweichungen von oben, die Achsenentscheidung und die
Belegungstabelle.

**Die Prüfpunkte, mit Abweichung — und mit ihrer Belegung:**

| Stunde | Literaturkurve | Gemessen | n | Abweichung |
|---|---|---|---|---|
| 1 (t = 0,5 h) | 151,5 W | 151,5 W | 26 | ±0,0 (Anker) |
| 2 (t = 1,5 h) | 148,1 W | 142,2 W | 23 | **−5,9 W** |
| 3 (t = 2,5 h) | 142,9 W | 131,5 W | **5** | −11,4 W |
| 4 (t = 3,5 h) | 136,0 W | 133,8 W | **1** | −2,2 W |
| 5 (t = 4,5 h) | 127,2 W | 131,9 W | **1** | +4,7 W |

Belastbar ist Zeile 1, mit Vorbehalt Zeile 2. **Zeile 3 steht auf fünf Fahrten,
Zeile 4 und 5 auf je einer — das sind keine Prüfpunkte, das sind Einzelfälle**
und werden als solche gezeichnet.

**Beide Leserichtungen** bleiben: „3 h — wie viel Watt" und „150 W — wie lange".
Jenseits des eigenen Datenbereichs wird nichts behauptet.

### L1a · Die Grenzen kommen aus der Belegung, nicht aus dem Code

Die Kurve endet **bei der längsten Fahrt des Nutzers**, nicht bei einer festen
Stundenzahl. Drei Bereiche, deren Grenzen aus der Belegungszählung folgen:

- **durchgezogen** — genug Fahrten für eine belastbare Aussage
- **dünn, mit ausgewiesenem n** — Daten vorhanden, aber wenige
- **gestrichelt mit Unsicherheitsband** — jenseits des Bestands, reine Literatur

Für den aktuellen Bestand ergibt das: durchgezogen bis Stunde 2 (n ≥ 20), dünn
für Stunde 3 (n = 5), gestrichelt ab Stunde 4 (n ≤ 1). **Die Grenze liegt damit
bei rund drei Stunden, nicht bei 4 h 20** — die längste Fahrt ist nicht die
Grenze, die Belegung ist es, und sie reißt vorher ab.

**Der Übergang wird benannt, nicht nur gezeichnet**, in der Sprache der Karte:
„ab 3 Stunden stützt sich die Kurve auf eine einzige Fahrt — ab hier zeichnet
die Studienform."

**Der Test dazu ist Pflicht:** zwei erfundene Bestände mit unterschiedlichen
Fahrtlängen müssen **zwei verschiedene Grenzen** ergeben. Kommt zweimal dieselbe
heraus, sind die Schwellen doch hartkodiert.

**Das Unsicherheitsband** zeichnet die publizierte Streuung mit: Δ5 % bei
139 ± 78 min, 1 bis 45 W Verlust nach 2,5 h (Stevenson), Anpassungsgüte
0,92 ± 0,09. Das Band wird bei drei Stunden **breiter als 40 W**. Die Karte darf
dort keine Punktgenauigkeit vortäuschen — die Leitzahl wird im gestrichelten
Bereich nicht als Zahl, sondern als Spanne gesetzt.

### L1b · Die HF-Korrektur — Literatur, nicht Messung

Stevenson, Kilding, Plews, Maunder (Eur J Appl Physiol 2022): nach zwei Stunden
fiel die Schwellenleistung von 217 auf 196 W, und die **Schwellen-Herzfrequenz
stieg von 142 auf 151 bpm**. Praktisch ist das wichtiger als die Kurve selbst:
das Panel nennt 160 bpm als aerobe Schwelle, und wer sich nach drei Stunden noch
daran hält, fährt zu hart.

**Am eigenen Bestand nicht wiederfindbar**, und der Grund ist sauber. Gepaart
über Fahrtstunden, Band alpha 0,65–0,85, beide Bins mit mindestens zehn
Fenstern, n = 17:

- **Δ Schwellen-HF: −2,2 bpm** (Median −0,8, SD 7,1, Spanne −17,4 bis +11,7),
  **p = 0,225** — Gegenrichtung zu Stevenson
- **r(Δ Leistung im Band, Δ HF im Band) = +0,815**

Die HF-Änderung folgt fast vollständig der Leistungsänderung. **Was hier gemessen
wird, ist nicht die Ermüdungsverschiebung, sondern dass in Stunde 2 eine andere
Leistung getreten wurde** (Δ Leistung im Mittel −9,5 W). Stevenson misst im
standardisierten Stufentest, wo die Belastung kontrolliert ist; im Feld ist sie
das nie.

**Folge für die Kachel:** L1b bleibt ein eigener, gleichwertiger Teil, aber
vollständig als **Setzung aus der Literatur** beschriftet. Die Aussage „was im
Panel als aerobe HF steht, gilt für den ausgeruhten Zustand" bleibt gültig und
richtig — sie ist nur an Alltagsfahrten nicht prüfbar, und das steht dabei.

**Die fehlende Temperatur** (nicht in `ACTIVITY_FIELDS`, nicht in
`DETAIL_STREAMS`) wird benannt, nicht nachgerüstet — ein Feld hinzuzufügen löst
über `ACTIVITY_FIELDS_VERSION` einen Vollabruf aus. Nach diesem Befund ist sie
ohnehin zweitrangig: **die Leistung ist der stärkere Störer, und sie liegt vor.**

### L2–L6 · nicht rekonstruierbar

Die Vorfassung dieser Abschnitte war nie im Repo; `docs/ausbau.md` endete vor
dieser Session mit Paket K. L2 bis L6 sind hier **absichtlich nicht
ausgeschrieben**, weil ihr Inhalt nur aus dem Briefing als Verweis bekannt ist
und alles andere Erfindung wäre. Wer sie braucht, schreibt sie neu — die
Grundlagen dafür stehen vollständig in L0, L1, L1a und L1b.

**Stand nach 0.45.0: sie sind OFFEN und wurden nicht gebaut.** Der Bauauftrag
nannte sie („L1b, L2–L6 wie spezifiziert"), die Spezifikation gibt es aber
nicht — die Bau-Session hat das gemeldet statt zu erfinden, und der Auftrag
wurde daraufhin auf L1/L1a/L1b eingegrenzt. **Woher ihr Inhalt kommen muss:
vom Athleten, nicht aus dieser Datei.** Wer sie wiederhaben will, schreibt auf,
was die fünf Punkte leisten sollen; alles, was eine nächste Session hier
herauslesen könnte, wäre eine Rekonstruktion aus dem Nichts. Diese Notiz steht
hier, damit die nächste Session nicht dieselbe Frage noch einmal stellt.

### Was der Bau von L an dieser Spezifikation korrigiert hat

**Nachgetragen am 13.09.2026, nach 0.45.0.** Vier Stellen, an denen die
Spezifikation vor dem ersten Handgriff nicht trug:

**1 · L1 war nicht payload-fertig — und das war der halbe Umfang.** Die
Spezifikation las sich, als müsse nur die Kachel gebaut werden. Tatsächlich trug
das Archiv **ein Fenstermittel je Fahrt** (`hr_at_threshold` /
`power_at_threshold`) und keinen Stundenverlauf: die Zahlen „Stunde 1: 151,5 W"
und „Stunde 2: 142,2 W" existierten nirgends im Bestand, sie waren live gerechnet
worden. Die Sekundenströme werden nach der Verdichtung weggeworfen. Daraus folgte
der eigentliche Bau: `derive.dfa_hours()` beim Import, `DFA_ALGO_VERSION` 2 → 3,
Neuberechnung aller Auswertungen über mehrere Abgleiche und eine sichtbare
Fortschrittsanzeige, weil ein leerer Platz nach dem Update wie ein Defekt
aussieht. **Das ist wörtlich Lehre 1 aus Paket A: am Feld prüfen, nicht am Text.**

**2 · Die Ausdünnung trifft auf dem Importweg nicht zu** (siehe L1). Gerechnet
wird sauberer als angenommen — und deshalb dürfen die gemessenen Zahlen dieser
Spezifikation nicht als Erwartungswerte in Tests stehen.

**3 · Der Variabilitätsindex kann strukturierte Einheiten nicht ausschließen.**
L0 verlangt den Ausschluss, nennt aber kein Kriterium, und der VI liegt nahe. Er
trennt nicht: die Bereiche überlappen vollständig, und `DURABILITY_VI_NONE`
hätte alle drei Störer aus Runde 3 durchgelassen. Gemessen wurde stattdessen der
Anteil der Zeit über Zone 2 (Lücke von 19 Punkten, kein Überlappungsfall). Die
Tabelle steht im PROJEKTSTAND §7 — dort, wo die nächste Session sie sucht.

**4 · L2–L6 existieren nicht** und wurden nicht erfunden (siehe oben).

**5 · Wo die Kachel sitzt und was sie ersetzt, stand nirgends** — nachgetragen
im Abschnitt darüber, nachdem der Bau zwei Kacheln für eine Frage erzeugt hatte.

**6 · „Ablesen ohne Schätzen" war nicht gebaut.** Die Kachel hatte keine
Bedienung: nichts anklickbar, nichts abgreifbar, zwei Sätze unter dem Bild als
Ersatz. Seit 0.46.0 trägt sie einen festen Ablesestreifen im Kartenkopf, einen
Zeiger über einem feinen Raster, eine Wertetabelle und **beide**
Leserichtungen — die zweite („150 W — wie lange") fehlte ganz.

**Und eine Falle, die in „Tests L" fehlte:** die Falle aus L0 Runde 3 selbst.
Sie ist jetzt der wichtigste Test des Pakets — mit der Gegenprobe, dass die
Störer den gemessenen Abfall von +4,0 auf +42,0 W treiben, wenn man sie drin
lässt. Beim Bau dieser Gegenprobe kam der Befund heraus, dass der Median dämpft,
aber nicht schützt (PROJEKTSTAND §7).

### WO die Kachel sitzt, und was sie ERSETZT (korrigiert 13.09.2026, nach 0.45.0)

**Diese Spezifikation hat nie ausgeschrieben, wohin die Kachel gehört und was
mit dem bisherigen Bild geschieht — und das war der Fehler.** Gebaut wurde sie
daraufhin als eigene Karte im DFA-Reiter, während die Durability-Kachel im
Trainer mit ihrer Entkopplungswolke stehen blieb. Ergebnis: **zwei Kacheln für
eine Frage, in zwei Reitern**, mit zwei Rechnungen und zwei Bildern, die man
nicht nebeneinander sehen konnte (PROJEKTSTAND §7, 0.46.0).

**Verbindlich, damit es nicht wieder passiert:**

- Die Ermüdungskurve ist das **Hauptbild der Durability-Kachel im
  Trainer-Reiter**. Es gibt keine zweite Kachel zu dieser Frage.
- Sie **ERSETZT die Entkopplungs-Punktwolke**. Die Wolke verschwindet als Bild;
  ihre Rechnung (Bins, Blöcke, Steigung, Verweigerung der Leitzahl) bleibt
  unberührt und steht weiter im Text.
- Was in der Kachel bleibt: der Kopfbereich aus H1/H2, die Mediane je
  Arbeitsband, der Blockverlauf, „Was das ausbaut", Rechenweg und Quellenblöcke.
- **Drei Abschnitte, drei Überschriften** — weil zwei der Teile über
  verschiedene Achsen laufen (Dauer für die Schwelle, Arbeit für die
  Entkopplung). Beide Achsenentscheidungen sind belegt, der Unterschied wird im
  Bild benannt, und **vereinheitlicht wird nicht**: das kassierte eine der
  beiden Begründungen stillschweigend.
- Das Entkopplungs-Diagramm im BELASTUNGS-Reiter ist eine andere Stelle
  (`analytics.decoupling_series`) und bleibt unangetastet.

### L4 · Die Wattvorgabe kommt aus der Messung (gebaut 0.47.0)

**Welche Familien, und warum genau die.** Grundlage und lange Fahrt beziehen
ihre Wattvorgabe aus der Kurve, die übrigen bleiben bei der FTP-Skalierung.

**Die Begründung ist NICHT „SweetSpot liegt außerhalb des Messbereichs" — das
ist falsch, und die erste Fassung dieses Abschnitts behauptete es.** Gemessen am
eigenen Bestand liegt die SweetSpot-Leistung mitten im messbaren Band: im
Fenster alpha 0,70–0,80 werden dort 180–185 W getreten. Der Grund ist ein
anderer und liegt bei der QUELLE, nicht beim Bereich:

> **Aus einer Fahrt mit Blöcken und Pausen ist kein tragfähiger Fit zu
> gewinnen.** Die Repräsentantengerade läuft dort über ZWEI getrennte
> Punktwolken — Block bei niedrigem alpha und hoher Leistung, Pause umgekehrt.
> Gemessen an der SweetSpot-Fahrt vom 24.08.2026: alpha-Spanne 0,25 bis 1,77
> **in derselben Stunde**, und P(0,75) ergibt 181 W im Block-Abschnitt gegen
> 153,8 W beim Ausfahren **derselben Fahrt**. Was bei 0,75 herauskommt, ist ein
> Punkt auf einer Geraden zwischen zwei Zuständen, keine Messung an der Schwelle.

**Der Weg zu Vorgaben für die übrigen Familien führt deshalb über eine EIGENE
MESSEINHEIT** — einen Stufentest, der den Bereich gleichmäßig durchläuft —
**nicht über die FTP.** Die FTP ist dort **Rückfall**, und die Einheitenkarte
beschriftet sie als solchen.

**Wie gestaffelt wird.** Auf der GEPAARTEN Reihe; die ungepaarte trägt einen
nachgewiesenen Auswahlanteil. Bis zur letzten gemessenen Stunde ist es Messung,
darüber Studienform — und welches von beidem, sagt **jeder Abschnitt der
Einheitenkarte selbst**, nicht eine Fußzeile. Trägt ein gepaarter Schritt nicht,
wird nicht auf ihm gestaffelt. Ein- und Ausrollen bleiben Prozent der FTP: das
sind Prozentangaben auf eine Schwelle, die dort nicht gemessen wurde.

**Die Kurve begrenzt NICHT die Dauer** (das macht die Progressionsregel aus H2)
und ersetzt NICHT die Zustandsbewertung aus Paket I.

### L4a · Warum der Plan neben die Kurve schickt — und warum nicht durch Streuung

Liegt jede Fahrt exakt auf der Kurve, liegen alle neuen Messpunkte auf der Kurve
und sie versteinert. Gebaut ist die Gegenprobe **aus dem Aufbau der Einheit**:
der Endblock der langen Fahrt (`z2_210_late`, 88 % FTP) ist nicht als
„gleichmäßig" markiert, bleibt deshalb FTP-skaliert und liegt über der Kurve.

**Warum nicht künstliche Streuung:** eine erfundene Abweichung müsste erklärt
werden, hätte keine Begründung im Trainingsaufbau und wäre beim nächsten Umbau
das Erste, was jemand „aufräumt". Eine, die aus der Struktur der Einheit folgt,
erklärt sich selbst und überlebt.

**Offener Punkt, gemessen und nicht gelöst: das reicht vermutlich nicht.** Ein
Endblock sitzt am Ende einer Fahrt ab drei Stunden. Am eigenen Bestand
(105 Tage DFA-Historie) erreichen **fünf** Fahrten die dritte Stunde und
**drei** die vierte — eine Gegenprobe alle drei bis fünf Wochen. Für eine Kurve,
die laufend neue Punkte bekommt, ist das dünn. **Wer hier weiterbaut, braucht
eine zweite Quelle für Punkte oberhalb der Kurve** — die naheliegende ist der
Stufentest aus der Richtungsentscheidung, der ohnehin gebraucht wird.

### Richtungsentscheidung: die eigene Messung vor dem Profilfeld

**Festgelegt am 13.09.2026.** Die DFA-Messung ist die maßgebliche Größe, nicht
die FTP: die FTP ist eine Eintragung in einem Profil, der alpha-Wert eine
Messung aus eigenen Fahrten. Daraus folgt für alles Weitere:

1. **FTP-Skalierung ist RÜCKFALL, nicht Regel.** Wo eine eigene Messung
   vorliegt, gilt sie; wo keine vorliegt, wird sichtbar zurückgefallen, mit
   Angabe warum — nie stillschweigend.
2. **Die obere Schwelle ist methodisch die zuverlässigere, das Signal dort
   schlechter.** In Radstudien: HRVT1 ICC 0,87 / typischer Fehler 18 W gegen
   HRVT2 ICC 0,97 / 5 W; eine Ruderstudie nennt HRVT1 ausdrücklich weniger
   geeignet für Trainingssteuerung. Umgekehrt zeigt ein Gurtvergleich gegen EKG
   bei niedriger Intensität etwa ±10 % Abweichung im DFA-Wert, bei hoher
   +58 bis −41 %. **Methode oben besser, Aufzeichnung oben schlechter — beides
   muss gemessen sein, bevor darauf gebaut wird.** `p050` und der Anteil
   verworfener Punkte unterhalb alpha 0,5 werden seit 0.47.0 erhoben und von
   nichts benutzt.
3. **Die tragfähige Frage ist nicht „welcher alpha-Wert IST die Schwelle",
   sondern „bei welcher Leistung erreiche ich MEINEN eigenen Wert"** (Physiol
   Rep 2026, Olieslagers et al.). Wer bei 175 W einen persönlichen Wert von 0,85
   zeigt und ihn später bei 225 W erreicht, hat sich belegbar verbessert — ohne
   Labortest.

### Offene Punkte, damit sie nicht untergehen

**L6 · `coach.anchors` auf die Kurve umstellen.** Heute rechnet der Anker das
Fenstermittel über die ganze Fahrt, die Kurve den Fit bei genau 0,75 auf der
ersten Stunde. Methodisch ist der Fit sauberer. **Nicht nebenbei umstellen:** am
Anker hängen die Herzfrequenzfenster jeder Einheit, die Plausibilitätsregel aus
K0 und die Konfliktwarnung. Eigener Schritt mit eigener Vorher-Nachher-Messung.

**Die FTP-Quelle.** Der Profilwert steht auf 215 W, `icu_rolling_ftp` bei
191–194, die gemessene 20-Minuten-Bestleistung bei 192 — der steuernde Wert
steht rund 10 % zu hoch. **Ein Wechsel ist mehr als ein Feldwechsel:**
`_latest_ftp()` trägt eine eigene Quellenlogik mit Vorrangregeln, und an ihr
hängen außer den Wattvorgaben auch `anchor_conflict()` (die Warnung FTP gegen
gemessene Schwelle) und `protocol_load()` (die Lastrechnung jeder Einheit). Wer
das angeht, prüft alle drei zusammen — und rechnet vor, was sich je Einheit
verschiebt.

**Der Stufentest.** Eine eigene Katalogeinheit, die den Bereich stufenweise
durchläuft und beide Schwellen in Watt misst — analog zum Durability-Test aus
Paket K, aber kürzer und ohne Vollgas. Er löst gleich zwei offene Punkte: die
Vorgaben für die übrigen Familien, und die zu dünne Gegenprobe aus L4a.

## Paket M — Ein Wert je Block, aufgetragen über die Zeit

**Vermessen in drei Runden am 13.09.2026. Noch nichts gebaut.**

### M0 · Warum die Stundeneinteilung hier NICHT gilt

Die Fahrtstunden-Einteilung aus Paket L ist für die **Grundlagenkurve** gebaut.
Auf strukturierte Rolleneinheiten angewandt misst sie etwas anderes, als sie
behauptet:

> SweetSpot 2×20 vom 24.08.2026. Stunde 1 (Einrollen, zwei Blöcke, Pause):
> P(0,75) = **181,1 W**. Stunde 2 (Ausrollen): **153,8 W**. Dieselbe Fahrt,
> 27 W Unterschied, alpha-Spanne 0,25 bis 1,77 in einer einzigen Stunde.

Der Unterschied ist **der zwischen Block und Ausrollen**, kein Ermüdungsverlauf.
Der Ausschluss strukturierter Einheiten aus der Grundlagenkurve bleibt.

### M1 · DIE AUSSCHNITTSREGEL — zwei Minuten, publiziert und am Bestand bestätigt

**Die ersten zwei Minuten jedes Blocks werden verworfen.** Rogers
(Front Sports Act Living 2021): die ersten zwei Minuten eines Abschnitts sind
nicht im metabolischen Gleichgewicht; für die Schwellenbestimmung taugen die
Werte bei Minute 4 und 6, weshalb sein Protokoll mit 6-Minuten-Stufen arbeitet.
Andriolo wertet aus demselben Grund nur die Minuten 5 bis 20.

**Am eigenen Bestand gemessen** (Median je 30-Sekunden-Segment ab Blockstart,
VO2max, drei typische Blöcke):

```
1,66 → 1,67 → 1,06 → 0,51 → 0,70 → 0,60 → 0,28 → 0,36
1,68 → 1,28 → 0,90 → 0,42 → 0,33 → 0,42 → 0,63 → 0,34
1,04 → 1,21 → 0,62 → 0,49 → 0,42 → 0,43 → 0,36 → 0,32
```

**Der Anlauf endet bei 90 bis 120 Sekunden.** Bei SweetSpot dauert er länger
(Umschlag erst im fünften Segment). Die publizierte Grenze ist damit bei VO2max
leicht konservativ und bei SweetSpot eher knapp — **sie bleibt, und zwar
begründet: sie deckt den langsameren Fall mit ab.**

Die Zwei-Minuten-Grenze gehört als Konstante nach `const.py`, **einmal**, mit
Rogers als Quelle und dem eigenen Befund als Bestätigung daneben.

**WO DIE METHODE IHRE GRENZE HAT — als Regel, nicht als Beobachtung.** Der
Median ist gegen den Anlauf robust, **solange der Anlauf unter der Hälfte des
Blocks liegt**. Bei einem 20-Minuten-Block sind zwei Minuten ein Zehntel und
das Verwerfen ändert kaum etwas; bei einem 4-Minuten-Block sind sie die Hälfte,
und dort kippt auch der Median. **Genau deshalb fiel der Fehler bei VO2max auf
und bei SweetSpot nicht — es ist die Blocklänge, nicht die Regel.**

**Daraus folgt die Untergrenze: unterhalb von rund vier Minuten Blockdauer
trägt diese Methode nicht mehr.** Nach dem Verwerfen bliebe zu wenig übrig, um
einen Median zu bilden, der etwas anderes misst als den Anlauf. Wer 3-Minuten-
oder 30/15-Intervalle auswerten will, braucht ein anderes Verfahren — nicht
eine kleinere Verwurfzeit.

### M2 · Was die Vermessung ergeben hat

**a) Die Blockerkennung steht.** `derive.normalize_laps` liefert `start_s` /
`end_s` und die Labels `WORK` / `RECOVERY`; das `dfa_a1`-Feld war in **48 von
48** Abschnitten gefüllt. Keine Segmentierungsheuristik — die Zuordnung trifft
der Athlet (K2).

**b) und c) Nach dem Verwerfen der ersten zwei Minuten:**

| Familie | Blöcke | alpha (Median) | Spanne | Streuung (SD) | Punkte je Block |
|---|---|---|---|---|---|
| **VO2max** | 11 | **0,40** | 0,34–0,52 | **0,087** | 39 |
| SweetSpot | 6 | 0,73 | 0,65–0,91 | 0,156 | 180 |
| Tempo | 4 | 0,97 | 0,85–1,53 | 0,144 | 103 |

Abgelesen wird **direkt** — Median über den eingeschwungenen Teil, kein Fit,
keine Interpolation. Damit entfällt der Fehler vom 24.08. (Gerade über zwei
getrennte Punktwolken).

**Streuungsgewinn durch das Verwerfen: 69 bis 83 % bei VO2max.** Aus SD 0,53
wird 0,165, aus 0,25 wird 0,043.

**d) VO2max trägt — und zwar am besten von allen drei.** Die kleinste Streuung
liegt ausgerechnet dort, wo die Gurtliteratur sie am größten vermuten lässt.
Der frühere Ausschluss stand auf einem Blockmedian, der den Anlauf
mitgemittelt hatte (PROJEKTSTAND §7).

**e) Belegung:** SweetSpot etwa wöchentlich mit zwei Blöcken je Einheit,
VO2max mit drei bis vier Blöcken — rund zwölf bis zwanzig Punkte in sechs
Wochen je Familie. Trägt.

### M3 · Die Zahl, die am meisten hergibt: der erste eingeschwungene Block

| Einheit | Blöcke (Watt / alpha, eingeschwungen) |
|---|---|
| 01.09. | **260/0,49** · 250/0,40 · 250/0,37 · 247/0,41 |
| 19.08. | **259/0,52** · 246/0,36 · 230/0,34 |
| 11.08. | **259/0,43** · 250/0,40 · 237/0,34 · 231/0,43 |

**Der erste eingeschwungene Block liegt über sechs Wochen bei 260 / 259 /
259 W** — bei alpha um 0,5, also an der anaeroben Schwelle. Direkt abgelesen,
ohne Modell. **Steigt diese Zahl bei gleichem alpha, ist das eine belegbare
Verbesserung** (Olieslagers et al. 2026: nicht „welcher alpha-Wert IST die
Schwelle", sondern „bei welcher Leistung erreiche ich MEINEN Wert").

**Und der Leistungsabfall kompensiert die Ermüdung nicht, er verlangsamt sie
nur:** am 19.08. werden 29 W abgegeben und alpha liegt trotzdem 0,18 tiefer.
Ein Vergleich bei ungleicher Leistung misst also nicht Ermüdungsresistenz — der
Abfall ist der Sinn der Einheit, nicht ihr Mangel, und er gehört
mitgerechnet statt vorausgesetzt.

### M3b · Die Zuordnung läuft über den INDEX, nicht über die Sekunden

**Korrigiert in 0.48.1, nachdem der erste Bau daran gescheitert war.** Die Laps
tragen beides: `start_s`/`end_s` in verstrichener Zeit und
`start_index`/`end_index` als Position im Strom. **Für den Import gilt der
Index.** Der Strom läuft in Bewegungszeit und ist ungedünnt; bei der Einheit
vom 01.09.2026 endet der letzte Index bei 2859 (= Zahl der Stromwerte), die
Sekundenachse bei 2973 — **114 Stellen Versatz, genau die Standzeit.** Für das
PANEL gilt das Gegenteil: dort kommt der Strom gedünnt an, und die Zeit ist die
richtige Achse.

`end_index` zeigt auf die Stelle **nach** dem Block, die Grenze ist also
exklusiv. Eine Umrechnung über `moving/elapsed` scheidet aus: die Standzeit
fällt dort an, wo gestanden wurde, nicht gleichmäßig verteilt — das wäre eine
Schätzung im Gewand einer Messung.

**Zwei Gegenproben halten das fest**, beide in `test_blocks.py`: die Physik
(ein Arbeitsabschnitt trägt mehr Leistung als die Pause daneben, mit dem
Sekunden-Fehler als Gegenfall) und eine FREMDE Quelle — Intervals' eigener
`dfa_a1`-Wert je Lap. Er liegt systematisch höher, weil er den Anlauf
mitmittelt, und taugt nicht als Ersatz; aber seine **Reihenfolge** muss zu
unserer passen. Läuft sie auseinander, sagt die Karte es.

### M3c · Die Blockauswahl: Ausreisser gegen die eigene Einheit (0.49.1)

Geraete etikettieren Einroll- oder Ausrollteile gelegentlich als `WORK`. Die
Leitzahl traf dann den falschen Abschnitt — **am 02.07. 182 W statt 238, am
19.07. 197 statt 278, am 02.08. 206 statt 250, bei Tempo 164 statt 183.** Es
war nie ein Tempo-Problem: fuenf der sechs betroffenen Einheiten sind VO2max.

**Nicht ueber die Leistung**: bei Tempo traegt der lockere Abschnitt 164 W und
der echte vierte Block 165 W. **Nicht gegen den Korridor** — das waere
zirkulaer und loeschte genau den Befund, den die Regelung melden soll. Es liegt
nahe und ist falsch; wer hier baut, lese das zuerst.

**Sondern als Ausreisser gegen die Einheit selbst:** alpha mehr als drei
Streuungen der uebrigen Bloecke ueber deren Median UND weniger Leistung als der
staerkste. Das Abstandsmass ist nicht schmueckend: am 11.08. liegt ein ECHTER
Block mit alpha 0,431 ueber dem staerksten (0,426) und muss bleiben.

### M4 · Was gebaut wird, wenn freigegeben

1. **Blockwerte beim Import mitrechnen und archivieren**, in der Bauart von
   `dfa_hours` (Archivblock, Versionsmarke, Migration). Laps werden heute nicht
   archiviert und die Ströme sind nach dem Import weg — ohne das gibt es keinen
   Verlauf über Wochen. **Zweiter Abruf je Aktivität im Importweg, plus
   Algorithmus-Bump.**
2. **Verlaufsanzeige je Familie** — SweetSpot und VO2max über die letzten
   Wochen. Hausmuster: Leitzahl oben, Belegung dabei, Rechenweg aufklappbar,
   unterscheidbar was Messung ist und was zu dünn belegt.
3. **Die Leitzahl ist der erste eingeschwungene Block**, über die Zeit
   aufgetragen.
4. **Zu prüfen, bevor daraus Vorgaben werden:** taugen die 260 W als Anker für
   die harten Familien anstelle der FTP? Das ist der Punkt, an dem auch
   SweetSpot und VO2max aus einer Messung kämen statt aus einer Eintragung, die
   nachweislich rund 10 % zu hoch steht.

### M5 · ABGESCHLOSSEN: die Fensterbreite liegt NICHT bei uns

Die DFA-Fensterbreite liegt **nicht bei uns** — Intervals liefert `dfa_a1` als
fertigen Strom, jeder Wert bereits gefenstert, die Breite undokumentiert. Ein
nachträgliches Mittel über fertige alpha-Werte ist **nicht** dasselbe wie ein
alpha über ein kürzeres Fenster: rechnet Intervals mit zwei Minuten, enthält
der Wert bei Minute 3 noch Daten aus Minute 1 — also genau den Anlauf, den M1
verwirft. Er käme durch die Hintertür zurück.

Seit **0.47.2** wird der `hrv`-Kanal mit abgerufen, **ausschließlich um zu
messen**, ob RR-Intervalle darin stehen. Zu prüfen an mehreren Merkmalen, nicht
an einem: Wertebereich und Einheit, Verhältnis zur gleichzeitig aufgezeichneten
Herzfrequenz (600 ms entsprächen 100 bpm), ob die Summe der Werte über einen
Abschnitt dessen Dauer ergibt, und ob die Zahl der Werte zur Zahl der
Herzschläge passt oder zum Sekundenraster.

**GEMESSEN AM 13.09.2026, NACH 0.47.2 — die Frage ist beantwortet, negativ.**
Zwei Aktivitaeten, die `hrv` in ihren `stream_types` fuehren, wurden abgerufen.
Geliefert wurden beide Male `cadence, dfa_a1, heartrate, time, watts` —
**kein `hrv`, null Werte.** Die Filterstelle scheidet aus (`thin_streams` laesst
durch, was in `DETAIL_STREAMS` steht, und dort stand der Kanal), die Version war
nachweislich installiert (HACS: `v0.47.2`, kein ausstehendes Update).

**Folge, und sie ist endgueltig:** die RR-Intervalle sind ueber diesen Weg nicht
zu bekommen. Die DFA-Fensterbreite bleibt Intervals' Sache — eine Grenze der
DATENQUELLE, keine Rechenfrage. Die vier Abweichungen von Andriolo aus 0.45.0
bleiben **vollstaendig** bestehen, keine ist hinfaellig. Die Arbeit zur
intensitaetsabhaengigen Fensterlaenge ist auf diese Daten **nicht anwendbar**;
sie setzt voraus, dass alpha selbst berechnet wird.

**Diese Frage wird nicht noch einmal gestellt.** Die Zeile in `DETAIL_STREAMS`
bleibt stehen, damit es auffaellt, falls Intervals den Kanal spaeter liefert.

Der historische Stand der Ueberlegung, zur Einordnung:

**Wenn es RR waere:** die Fensterbreite läge bei uns, die Arbeit zur
intensitätsabhängigen Fensterlänge (bioRxiv 02/2026: 1-min-Fenster gegen das
2-min-Fenster, ICC 0,95 beim Zeitfahren gegen 0,37 bei niedriger Intensität —
kürzere Fenster gewinnen mit steigender Herzfrequenz, weil die Rechnung eine
Mindestzahl an HERZSCHLÄGEN braucht, nicht an Sekunden) wäre direkt anwendbar,
und die vier Abweichungen von Andriolo aus 0.45.0 wären teilweise hinfällig.
**Das ist dann ein eigener Befund und gehört gemeldet, bevor daraus ein
Bauauftrag wird.**

**Wenn es kein RR ist:** ebenfalls ein Ergebnis. Dann bleibt es bei Intervals'
Fensterung — eine Grenze der Datenquelle, keine Rechenfrage.

**Es ist kein Blocker.** Mit der Zwei-Minuten-Regel trägt VO2max bereits; RR
würde es verbessern, nicht erst ermöglichen. M kann unabhängig davon gebaut
werden.

### M6 · Randbedingung: Versions-Bumps werden gebündelt

Paket M braucht einen weiteren Algorithmus-Bump. **Zwei Neuberechnungen kurz
hintereinander sind nicht zuzumuten** — jede kostet rund drei Abgleiche, in
denen die Kachel leer ist und der Trainer auf den Rückfall zurückgeht. **Wird M
gebaut, wird es zusammen mit allem gebaut, was ebenfalls einen Bump braucht.**
Wer einen Bump allein auslöst, obwohl ein zweiter absehbar ist, hat die
Reihenfolge falsch geplant.

### Hausmuster für die Kachel

Leitzahl oben, Beleg darunter, aufklappbarer Rechenweg, **Beleg und Setzung
getrennt**, und sichtbar, welche Fahrten zählen und welche warum nicht. Konkret
gehören in den Rechenweg: der Historienbeginn (siehe eigener Punkt unten), die
vier Abweichungen von Andriolo, die Achsenentscheidung, die Belegungstabelle je
Stunde und die Liste der gekennzeichneten Fahrten nach Ersatzmaß.

### Tests L

1. Die Form-Funktion liefert bei t = 0 exakt 1,0 und erreicht −5 % zwischen 119
   und 140 min (Sensitivitätsspanne aus L1).
2. Der Anker skaliert die Form, ohne sie zu verformen: P₀ verdoppelt → jeder
   Kurvenwert verdoppelt, der Δ5-%-Zeitpunkt unverändert.
3. **Zwei erfundene Bestände mit verschiedenen Fahrtlängen ergeben verschiedene
   Bereichsgrenzen** (durchgezogen / dünn / gestrichelt). Der Test, der die
   Hartkodierung ausschließt.
4. Ein Bestand ohne Fahrt über einer Stunde ergibt **keine** gemessene Zeile,
   sondern nur Anker und Literaturkurve — und sagt das.
5. Das Unsicherheitsband ist bei drei Stunden breiter als 40 W, und die Leitzahl
   wird im gestrichelten Bereich als Spanne gesetzt, nicht als Zahl.
6. Die Beschriftung enthält wörtlich „auf Intervals' eigener DFA-Fensterung".
7. Plausibilitätsregel (siehe eigener Punkt): eine Fahrt mit Schwellen-HF
   unterhalb der Mindestgrenze erscheint als Ausfall, nicht als Messwert, und
   geht in keine Mittelung ein.

---

## Eigener Punkt — der Historienbeginn gehört sichtbar gemacht

**Befund vom 13.09.2026.** Von 240 Aktivitäten tragen **58 eine DFA-Auswertung**,
und **alle davon liegen ab dem 31.05.2026**. Stichproben bis zurück in den Mai
2025 liefern durchgehend keinen `dfa_a1`-Strom. **Jede DFA-gestützte Aussage im
Panel stützt sich damit auf 3,5 Monate, nicht auf 16.**

Sichtbar ist das nirgends. Die Kopfzeile des Panels zeigt
„240 Einheiten · 489 Tage · 58 DFA" — **und damit steht die Zahl 58 direkt neben
489 Tagen, was den gegenteiligen Eindruck erzeugt**: dass die 58 Auswertungen
über den ganzen Zeitraum verteilt wären. Das ist keine bloß fehlende Angabe,
sondern eine irreführende Nachbarschaft.

**Zu tun:** der DFA-Reiter, der Trainer und die Schwellenkachel weisen den
Zeitraum aus, über den DFA-Daten tatsächlich vorliegen — in derselben Klasse wie
„welche Fahrten zählen und welche nicht". In der Kopfzeile wird die DFA-Zahl um
ihren eigenen Zeitraum ergänzt statt neben dem Wellness-Zeitraum zu stehen.

**Test:** ein Bestand, dessen DFA-Daten später beginnen als die Aktivitäten,
zeigt beide Zeiträume getrennt an.

---

## Kleinkram für die nächste Session

Vier Posten, die keine eigene Spec brauchen, aber liegen bleiben, wenn sie
nirgends stehen. **Stand nach 0.44.0: 1 und 3 sind erledigt, 2 und 4 offen.**

**1 · ERLEDIGT in 0.44.0 — die §9-Tabelle im PROJEKTSTAND ist zum ZWEITEN Mal
veraltet.** Am
13.09.2026 summierte sie auf **4.185**, der Kopf derselben Datei auf **4.518**;
vier Zeilen hingen hinterher (`test_workouts` 1.030 statt 1.230,
`test_panel_views` 1.114/1.170, `test_panel_fixes` 312/373, `test_panel_design`
219/235). Beim ersten Mal (Lehre 4 aus Paket A) war das ein Einzelfall — beim
zweiten Mal ist es ein Muster, und das Muster heißt: eine von Hand gepflegte
Zahl neben einer gerechneten Zahl geht auseinander, immer.

**Gebaut als `tests/test_projektstand.py`**, allerdings anders als hier
vorgeschlagen: nicht als Läufer neben der Suite, sondern als 16. Testdatei, die
die übrigen fünfzehn als Subprozesse fährt. Der Grund gegen „Läufer": ein
Prüfstandsteil, der selbst nicht mitgezählt wird, ist genau die Lücke aus
0.36.0. Die eigene Zeile wird gegen den eigenen Zähler gehalten — ein Fixpunkt,
kein Zirkelschluss, und der Grund steht als Absatz in der Datei, damit ihn
niemand „richtig" umbaut. Der ursprüngliche Vorschlag im Wortlaut:

> **Ein Wächter gehört gebaut.** Er kann nicht in eine einzelne Testdatei, weil
die Zahl erst nach dem Lauf existiert: also ein Läufer (`tests/run_all.py` o. ä.),
der jede Datei fährt, die gemeldeten Zahlen einsammelt und **beides** gegen den
PROJEKTSTAND hält — die Tabelle **und** die Kopfzahl. Nur die Kopfzahl zu
prüfen hätte den jetzigen Fall nicht gefunden; nur die Tabelle zu prüfen hätte
den Fall aus 0.36.0 nicht gefunden. Ausgabe als Differenzliste je Datei, Urteil
im Exit-Code.

**2 · OFFEN — Fehlerkapitel PROJEKTSTAND §7, Eintrag zu J1 — eine eigene
Fehlerklasse.** Bei 0.44.0 ausgefallen, vorgemerkt als erster Punkt des
Aufräum-Pakets (siehe dort, „Zuerst in diesem Paket").
Bisher sammelt §7 vor allem „zu wenig Daten" und „Prüfstand meldet nicht, was er
prüft". J1 ist etwas Drittes: **die Messung misst etwas anderes als behauptet.**

Die naheliegende Rechnung (bester 5-min-Abschnitt vor der kJ-Schwelle gegen den
besten danach) hätte einen Verlust von 6,6 % **angezeigt** und dabei das eigene
Signifikanzkriterium aus G2 **bestanden** (|t| = 2,53 gegen geforderte 2,0).
Gefangen hat ihn nicht die Statistik, sondern ein **längengleicher
Kontrollabschnitt**: wird der frische Abschnitt auf die Länge des ermüdeten
beschnitten, steht der Erhalt bei 99,5 % und |t| bei 0,18. Der ganze Effekt war
„Maximum über mehr Material".

**Der Beleg, der es unstrittig macht, gehört mit hinein:** dieselbe Rechnung bei
einer Placebo-Schwelle von 200 kJ — wo der ermüdete Abschnitt der lange ist —
liefert **110,2 %** bei t = **+4,18**. Der Athlet wäre „signifikant stärker,
wenn er müde ist". Ein Signifikanzkriterium schützt gegen Rauschen, nicht gegen
eine falsch konstruierte Messung; dagegen hilft nur ein Kontrollfall, dessen
Ergebnis man vorher kennt.

**3 · ERLEDIGT in 0.44.0 — `NAECHSTER_CHAT.md` stand noch auf Paket 4 /
0.34.0.** Neu geschrieben auf den Stand nach K.

**4 · OFFEN — der README beschreibt ein Projekt von vor 35 Releases.**
Aufgefallen am 13.09.2026 beim Lesen der HACS-Antwort nach der Auslieferung von
0.44.0. Er steht auf **„Stand: 0.9.1 — das Panel, neu gebaut"**, nennt sieben
Ansichten (es sind acht) und führt „Schreibseite (Workouts planen)" unter „als
Nächstes" — die gibt es seit 0.31.0. Weder der Trainer-Reiter noch der
Wochenplan, die Durability-Kachel oder das Protokoll kommen darin vor.

**Das Repository ist öffentlich, und der README ist die Fassung, die jeder
Fremde sieht.**

**Das gehört NICHT in das Aufräum-Paket.** Der richtige Ort ist das schon
einmal geplante und liegengebliebene **Namenspaket: Umbenennung plus Git-Ausbau
nach Standard** — README mit Screenshots, Einrichtung, Buy-me-a-coffee, dazu
Repository-Topics und der Brand-Icon-PR aus §10. Der README ist dort kein
Nebenposten, sondern das Hauptstück.

**Und bis dahin nicht anfassen:** ein halb aktualisierter README ist schlechter
als ein erkennbar alter. Beim erkennbar alten weiß der Leser, woran er ist; beim
halb aktualisierten stimmt die eine Hälfte und die andere lügt, und man sieht es
ihm nicht an. Dieselbe Unterscheidung wie bei einer Setzung, die als Befund
ausgegeben wird (§7, 0.43.1).

---

## Reihenfolge und Modellwahl

| Session | Paket | Warum |
|---|---|---|
| S2 | A | eng spezifiziert, viele kleine Eingriffe im Panel, kein Backend |
| S3 | B | Archivschema, Migration, dieselbe Regel an mehreren Orten — das schwerste |
| S4 | C | Mathematik und Formulierung, klein |
| S5 | D | Abgleich mit Intervals — Sperren, nicht Löschfunktion |
| S6 | C + D6 + F | zusammen ausgeliefert als 0.39.0 |

**Nachtrag 13.09.2026 zur Einordnung von C.** Die erste Fassung von C3 forderte
zwei Schieber und einen Schalter. Das hätte ein Archivschema samt Migration
erzwungen — ein Block, den `importer.empty_data()` nicht kennt, entsteht bei
Altbeständen nie (die Lücke aus 0.35.0). Die Bedienung ist deshalb gestrichen:
die Leiter läuft automatisch, die gegriffene Stufe wird ausgewiesen, **kein
Schlüssel im Archiv**. Damit ist C wieder das, als was es hier steht —
Mathematik und Formulierung. Sollte später daran gedreht werden, kommt es als
`localStorage`-Anzeigepräferenz in der Bauart des Zeitwählers aus A2.


---

## Paket N — Stufentest (GEBAUT, 0.51.0, 14.09.2026)

**Aufgeschrieben als Übergabestand, gebaut in der Folgesitzung. Was der Bau an
diesem Abschnitt korrigiert hat, steht unten — besonders N4: die offenen
Fragen sind nicht beantwortet worden, sie sind als unbeantwortbar
zurückgekommen.**

### N0 · Der Auftrag

**Der Durability-Test kommt RAUS, der Stufentest kommt REIN.** Begründung des
Athleten: der Durability-Test misst nur die Durability, braucht zwei Termine
und 1.000 kJ und wird auf absehbare Zeit nicht gefahren. Der Stufentest misst
BEIDE Schwellen plus die Erholung, dauert knapp eine Stunde auf der Rolle und
prüft die Zahlen nach, die heute aus den Einheiten kommen. Er ist zugleich der
Einstieg für jemanden, der die App neu nutzt und noch keine Messwerte hat.

**ALLES IN EINEM RELEASE** — Katalogeintrag und Auswertung zusammen. Ein
Katalogeintrag ohne Auswertung hieße: eine Fahrt liegt im Archiv, die niemand
lesen kann, und die Auswertung muss später rückwirkend an sie heran. Genau der
Zwischenzustand, der in diesem Projekt schon zweimal Arbeit gekostet hat. Es
eilt nicht, der Test ist alle paar Monate gedacht.

### N1 · DER GRUNDSATZ, der alles andere bestimmt

**Das Protokoll wird nach der STUDIENLAGE gebaut** und nur dort auf dieses
System zugeschnitten, wo die Auswertung es erzwingt. **Jede Abweichung wird als
solche beschriftet, mit Grund.**

**KEINE FESTEN LEISTUNGSZAHLEN.** Alles leitet sich aus den gerechneten
DFA-Werten ab. Eine feste Endleistung wäre für den einen richtig und für einen
Fahrer, der 800 W tritt, sinnlos.

    Einrollen    feste DAUER, Leistung = Grundlagenvorgabe für 1 h
    Rampenstart  dieselbe Zahl
    Rampenende   an einem ZUSTAND, nicht an einer Wattzahl: wenn alpha stabil
                 unter 0,5 liegt, ist der Tiefpunkt nachgewiesen. Die Zahl
                 fällt an (hier vielleicht 290 W, bei einem Spitzenfahrer 480),
                 sie wird nicht gesetzt.
    Ausrollen    feste DAUER, Leistung = dieselbe Grundlagenvorgabe, KONSTANT
    Ohne eigene Messwerte fällt alles sichtbar auf die FTP zurück.

**Die einzigen festen Zahlen im ganzen Test sind die DAUER von Ein- und
Ausrollen.** Alle Leistungen kommen aus den eigenen Zonen.

### N2 · GEKLÄRT

**Die Rampensteigung — der Widerspruch löst sich auf, es sind zwei Größen.**
Fleitas-Paniagua 2023 fand bei 15/30/45 W/min keinen Effekt auf HRVT1/HRVT2 —
aber gemessen in **HF und VO2**, nicht in Watt (so auch die Definition dort:
"the V̇O2 or HR at which DFA a1 reached 0.75"). Rogers spricht von der
**Leistung**, und die liegt bei steileren Rampen am selben VO2 systematisch
höher, weil die Sauerstoffaufnahme hinterherhinkt. **Kein Widerspruch — zwei
verschieden erhobene Größen unter einer Überschrift** (dieselbe Klasse wie
0.49.2, diesmal in der Literatur statt im Code).

**Folge: FLACHE RAMPE, und die Steigung wächst NICHT mit der eigenen Spanne.**
Eine relative Steigung wäre für einen starken Fahrer genau die steile Rampe,
aus der man die Leistung nicht ablesen darf. Die längere Testdauer bei einem
starken Fahrer ist der Preis, kein Konstruktionsfehler.

**Die personalisierte Schwelle — Definition bestätigt, Nutzen umstritten.**
Rogers 2024 definiert sie als den DFA-a1-Wert mittig zwischen dem "maximum seen
during the early ramp incremental" und 0,5, und berichtet nahezu exakte
Übereinstimmung mit der Laborschwelle. **Eine Arbeit von 2026 findet das
Gegenteil**: HRVT1 zeigte schlechte Übereinstimmung mit VT1/LT1 (Bias bei der
Leistung −21 bis −45 W), und die personalisierte Variante brachte nur
marginale Verbesserung. **Dieselbe Arbeit ist die Quelle der 21–45 W**, die im
Beschreibungstext als Unsicherheit genannt werden sollen.

→ **Berechnen, als DRITTE Zahl neben HRVT1 zeigen, Nutzen als umstritten
beschriften. Kein Ersatz für HRVT1.** HRVT2 ist die belastbarere der beiden
Schwellen (durchgängig hohe Übereinstimmung mit zweiten Schwellen).

**Die Quellenkette — eine Mechanik, verschiedene Rangfolge:**

| Familie | 1. Wahl | 2. | 3. |
|---|---|---|---|
| VO2max, SweetSpot | Blockmessung | **Stufentest** | FTP |
| Grundlage, lange Fahrt | Ermüdungskurve | **Stufentest** (HRVT1) | FTP |
| Tempo, Schwelle | **Stufentest** | — | FTP |

Für einen Einsteiger rutscht der Test automatisch nach oben, weil nichts
darüber liegt. Die Karte beschriftet wie überall, welche Stufe greift.

**ZURÜCKGENOMMEN in 0.60.0 (Variante B, PROJEKTSTAND §7 Fall 38):** der Stufentest steht
in keiner Kette mehr. Gebaut war die Stufe als „jeder Arbeitsblock = HRVT2 × 1,0" — mit
dem ersten gefüllten Test hätten VO2max, SweetSpot, Tempo und Schwelle dieselben 233 W
bekommen. Die Messung steht auf der Karte und steuert nichts; die Vorgabe daraus wird als
Ablesung je alpha-Korridor neu gebaut (PROJEKTSTAND §10 Punkt 0).

**Die Zuordnung zu unseren Größen — NICHT Schwelle gegen Trainingsvorgabe:**
HRVT2 (alpha 0,5) gehört gegen die **Leitzahl**, den ersten eingeschwungenen
Block (260 W bei alpha 0,49) — das ist per Definition dieselbe Größe. HRVT1
(alpha 0,75) gegen **P(0,75) aus der Ermüdungskurve** (153 W). HRVT2 gegen die
VO2max-Trainingsvorgabe (250 W bei Median-alpha 0,405) zu halten wäre 0.49.2
in neuer Gestalt.

### N3 · DIE OFFENE FRAGE, DIE DER TEST BEANTWORTEN SOLL

**Die 40 Watt.** Die SweetSpot-Blöcke liegen bei **alpha 0,73 und 194 W**, die
Ermüdungskurve kommt bei **alpha 0,75 auf 153 W**. Derselbe alpha-Wert, 41 Watt
Unterschied, seit Wochen bekannt und nie aufgelöst. **Der Stufentest erhebt
beide Zahlen in EINER Fahrt unter gleichen Bedingungen — das ist der stärkste
Grund, ihn zu bauen, und er darf nicht untergehen.**

### N4 · OFFEN — vor dem Bau im VOLLTEXT nachzulesen

Aus den Abstracts NICHT zu beantworten, deshalb ungeklärt:

1. **Einrollen** — Dauer, Leistung, überhaupt vorhanden? (Rogers 2021a,
   Olieslagers 2026)
2. **Startleistung der Rampe** — woraus abgeleitet?
3. **Rampenende / Abbruchkriterium** im Originalprotokoll
4. **"early ramp incremental"** bei Rogers 2024 — wie genau abgegrenzt? Das ist
   die Grundlage der personalisierten Schwelle
5. **Dauer der parasympathischen Reaktivierung** für das Ausrollen. Die
   Erholungsmessung ist eine EIGENE Idee ohne Protokollvorgabe und als
   Ergänzung zu beschriften, nicht als Protokollteil. Ergibt die Literatur
   nichts Belastbares, wird bewusst gesetzt und als gesetzt benannt.

**Wo die Quellen schweigen, wird das gesagt** — dann setzen wir mit Begründung,
statt eine Zahl zu übernehmen, die wie ein Befund aussieht.

### N5 · Weitere Festlegungen

- **Keine Abweichungstoleranz beim ersten Test:** beide Zahlen nebeneinander,
  kein Urteil. Eine Toleranz wird gebildet, wenn es mehrere Tests gibt — wie
  bei der HF-Spanne und der Gegenprobe.
- **Die Erholungsgröße fließt in KEINE Vorgabe ein.** Messen, anzeigen, und
  beschriften, dass es dafür keine Studienlage gibt (belegt ist nur, dass fitte
  Menschen sich autonom schneller erholen). Sie sagt erst nach mehreren Tests
  etwas.
- **Zustandsbewertung aus Paket I:** bei gelbem oder rotem Zustand wird der
  Test NICHT vorgeschlagen, er gehört ausgeruht gefahren.
- **Die BESCHREIBUNG ist der wichtigste Teil.** Sie entscheidet, ob jemand den
  Test richtig fährt oder eine Stunde umsonst tritt. Inhalt mindestens: wofür,
  wie oft (alle paar Monate), Voraussetzungen (Rolle, BRUSTGURT — optische
  Messung am Handgelenk taugt nachweislich nicht — ausgeruht), während des
  Tests (gleichmäßig treten, nicht aus dem Sattel, Trittfrequenz konstant,
  nicht sprechen), Abbruch (wenn du nicht mehr kannst — vorgesehen und kein
  Fehlversuch, wichtig ist nur dass alpha vorher unter 0,5 war), danach (die
  Ausrollzeit NICHT abkürzen, sie ist Teil der Messung), und was der Test NICHT
  kann (die absolute Höhe ist unsicher, belastbar ist die Veränderung bei
  derselben Person).

---

## Was der Bau von N an dieser Spezifikation korrigiert hat

**Nachgetragen am 14.09.2026, nach 0.51.0.** Fünf Stellen, alle vor der ersten
Zeile Code gemeldet und einzeln entschieden — Lehre 1 aus Paket A: **am Feld
prüfen, nicht am Text.**

**1 · N4 ist nicht „im Volltext nachzulesen" — die Quellen geben es nicht
her.** Die drei Punkte, an denen die Spezifikation auf eine Antwort gewartet
hat, haben keine:

| N4-Punkt | Was die Spec annahm | Was tatsächlich dasteht |
|---|---|---|
| Einrollen | Dauer und Leistung stehen im Protokoll | **Kein Protokoll nennt beides.** Die Arbeiten beschreiben die Rampe, nicht den Vorlauf |
| Startleistung | „woraus abgeleitet?" — also: es gibt eine Ableitung | **Es gibt keine.** Wo eine Zahl steht, ist sie absolut und an die jeweilige Kohorte gebunden — genau das, was N1 verbietet |
| Abbruchkriterium | im Originalprotokoll benannt | **Willentliche Erschöpfung** bzw. Abbruch des Probanden. Ein Zustand, kein Wert — und damit nichts, woraus sich eine Wattzahl ableiten ließe |

**Entscheidung: gesetzt und als gesetzt beschriftet, statt eine Zahl zu
übernehmen, die wie ein Befund aussieht.** `RAMP_WARMUP_MIN = 15`,
`RAMP_COOLDOWN_MIN = 10`, `RAMP_STEP_W_PER_MIN = 5` stehen in `const.py`, jede
mit ihrem Grund und ihrem Status daneben. Das ist kein Mangel des Baus, sondern
die Auskunft, die N4 selbst verlangt hat: **wo die Quellen schweigen, wird das
gesagt.** Die Spec hat diese Möglichkeit vorgesehen und trotzdem so formuliert,
als sei sie der Ausnahmefall. Sie war der Regelfall.

**2 · Die Segmentregel ist eine SETZUNG, und zwar eine unvermeidliche.** Die
Spec sprach vom „Rampenende an einem Zustand" und las sich, als sei das
Segment damit bestimmt. Ist es nicht: **bei Rogers 2021a/b (Laufband) wird der
lineare Abfall nach Augenschein am Plot abgegrenzt** — visuell, vom Autor; es gibt
dort keine Vorschrift, die man nachbauen könnte, nur ein Bild und ein Ergebnis.
**KORRIGIERT (16.09.2026, Rechenweg e1):** Hier stand „in beiden Arbeiten … VON
HAND". Für Olieslagers 2026 (Rad) ist das nicht belegt: der gelesene Ausschnitt des
Methodenteils nennt die Grenze des Beginns nicht, der Volltext ist nicht nachgelesen.

Damit hängt an der Segmentwahl alles: ein einzelner Ausreißer entscheidet
nichts mehr (das ist der Gewinn der Gerade gegenüber dem Ablesen), dafür
entscheidet die Wahl der Grenzen das ganze Ergebnis. Gebaut war bis Rechenweg e1:
**Ende** = der erste Punkt, ab dem die geglättete Kurve `RAMP_FLAT_S` unter 0,5
bleibt; **Anfang** = der höchste Wert davor, bei Gleichstand die späteste Stelle
(hier stand „der letzte Hochpunkt davor" — ein Etikett, das der Code nie umgesetzt
hat, §7 Fall 37). **Seit e1:** Anfang = höchster Wert ab Rampenbeginn
(`RAMP_WARMUP_MIN`), Ende = Lastende (Fahrtlänge − `RAMP_COOLDOWN_MIN`), beide
Grenzen SETZUNGEN aus dem Protokoll. Geglättet wird nur für die Suche,
gerechnet auf den ungeglätteten Werten. **Die Karte sagt ausdrücklich, dass
diese Wahl unsere ist** — und das ist keine Bescheidenheitsfloskel, sondern die
einzige ehrliche Beschriftung für eine Zahl, deren Bezugsgröße wir selbst
festlegen.

**3 · Die personalisierte Schwelle ist aus zweiter Hand, und die beiden Sätze
sind nicht derselbe.** N2 zitiert Rogers 2024: mittig zwischen dem „maximum
seen during the early ramp incremental" und 0,5. Was „früh" heißt, steht dort
nicht, und die Arbeit ist nicht frei zugänglich. Olieslagers 2026 setzt es um
und zitiert Rogers dafür — aber als **höchsten Wert am Beginn des linearen
Abfalls**. **Ein Maximum in einem ZEITFENSTER ist etwas anderes als eines an
einem KURVENPUNKT.** Gebaut ist die Fassung von Olieslagers, weil nur sie
implementierbar ist und an dasselbe Segment hängt, das die Regression ohnehin
braucht — **beschriftet als Operationalisierung aus zweiter Hand, nicht als
Rogers' Wortlaut.** Seit e1 fallen Zeitfenster und Kurvenpunkt hier zusammen, aber
nur per Setzung: der Beginn des Abfalls ist selbst als höchster Wert ab Rampenbeginn
definiert. Das ist dieselbe Klasse wie der achte und neunte Fall in
§7: zwei verschieden erhobene Größen unter einer Überschrift.

**4 · Die Erholungsmessung hat kein Fenster in der Literatur.** N4 Punkt 5
fragte nach der „Dauer der parasympathischen Reaktivierung". Belegt ist das
Fenster 0–10 min nach Belastungsende (Michael 2017) und die vollständige
Rückkehr in 24–72 h (Stanley/Peake/Buchheit 2013) — **eine Ausrolldauer nennt
niemand.** `RAMP_RECOVERY_WINDOW_S = 120` ist gesetzt, in `const.py` als eigene
Idee ohne Protokollvorgabe markiert, und die Größe fließt nach N5 in **keine**
Vorgabe ein.

**5 · Und eine Ergänzung, die die Spec nicht hatte: das Ausleseverfahren ist
selbst eine Abweichung.** Die Arbeiten lesen VO2 und Herzfrequenz an der
Schnittstelle über **eigene Regressionen** ab. Hier steht der **Median eines
30-Sekunden-Fensters** um den Zeitpunkt. Das ist die praktikable Variante auf
einem Sekundenstrom, aber es ist nicht dasselbe Verfahren — `RAMP_READ_WINDOW_S`
trägt den Vermerk „ABWEICHUNG, beschriftet". N1 verlangt genau das für jede
Abweichung; diese hier stand in N1 nur nicht auf der Liste, weil niemand sie
kommen sah.

**Zur Teilung:** „alles in einem Release" (N0) hat gehalten, und die Begründung
auch — ein Katalogeintrag ohne Auswertung hätte eine Fahrt im Archiv erzeugt,
die niemand lesen kann. Ausgeliefert sind Katalogeintrag, Auswertung,
Archivblock, Quellenkette und Karte zusammen.

**6 · Nachtrag aus dem Live-Blick (0.51.1): die Spezifikation hat übersehen,
woraus die Rampe gerechnet wird.** N1 verbot feste Leistungszahlen, sagte aber
nirgends, WORAUS Start und Ende dann kommen sollen. Gebaut wurde daraufhin ein
Katalogeintrag mit `ramp 60-115%` — Prozente der FTP, also formal keine „feste
Zahl" und sachlich genau das, was N1 verhindern wollte. Bei diesem Athleten
endete die Rampe damit **27 W unter seiner eigenen Leitzahl**, und die zweite
Schwelle war nicht erreichbar. **Ein Verbot ohne benannte Quelle ist keine
Vorschrift, sondern eine Lücke mit gutem Gewissen.** Die Spezifikation trägt
seit 0.51.1 die beiden Ketten ausdrücklich: Start aus der Ermüdungskurve, Ende
aus der Blockmessungs-**Leitzahl** (nicht der Trainingsvorgabe), beides mit
Rückfall auf die FTP und beschrifteten Enden.

**7 · Und eine Regel über Zahlen, die N4 hätte brauchen können.** Das
Pulsfenster des Tests war mit 112–160 bpm falsch — aber der Reflex, es zu
verbreitern, wäre ebenfalls falsch gewesen. Bei einer Rampe wandert der Puls
über den ganzen Bereich; ein Fenster ist dort die **falsche Art von Aussage**,
nicht bloß der falsche Wert. 110–190 bpm wäre korrekt und nutzlos gewesen —
**eine breitere Spanne hätte es nur unauffälliger gemacht, nicht besser.**
Daraus die Regel für jede künftige Spezifikation: **eine Zahl, die man
korrigieren kann, ohne dass sie richtig wird, gehört weg und nicht angepasst.**

**Was der Bau NICHT beantwortet hat: die 40 Watt (N3).** Das war immer die
Aufgabe des Tests, nicht die des Baus. Die Frage steht jetzt sichtbar in der
Karte — mit beiden eigenen Zahlen nebeneinander und dem Satz, dass es bisher
nichts gibt, was zwischen ihnen entscheidet. **Sie wird beantwortet, wenn der
erste Test gefahren ist.**

---

## Paket O — Anzeige-Release 0.50.0 (GEBAUT, 14.09.2026)

**Fünf Punkte: 1, 2, 3, 4, 5 — Punkt 6 ist gestrichen.**

**Stand: 14.09.2026. Reine Darstellung: kein neuer Algorithmus, KEIN
Algorithmus-Bump, KEINE Neuberechnung.**

### O0 · Die Teilung — NEU ABGEWOGEN, nachdem Punkt 6 entfiel

**Punkt 6 (Datumsachse) ist gestrichen**, siehe O2. Damit wurde die Aufteilung
noch einmal geprüft, und sie verschiebt sich:

**EMPFEHLUNG: die vier verbleibenden Punkte in EIN Release.** Grund ist nicht
der Umfang, sondern eine Abhängigkeit, die durch die Entscheidung zu Punkt 4
entstanden ist: **die Bandbreite wandert aus der gestrichenen oberen Tabelle in
die Ablesezeile aus Punkt 3.** Wer Punkt 4 ohne Punkt 3 ausliefert, entfernt
die Tabelle, bevor ihr Ersatz steht — die Bandbreite wäre zwischenzeitlich
NIRGENDS. Das ist genau der Zwischenzustand, den Paket N für den Stufentest
ausdrücklich ausschließt, nur kleiner.

**Punkt 4 hängt damit an Punkt 3, und Punkt 3 hängt an Punkt 5** (dieselbe
Mechanik, siehe unten). Übrig bliebe für ein eigenes Vorab-Release nur 1 und 2
— zu dünn, um ein Release zu rechtfertigen.

**Falls der Kontext einer Sitzung doch nicht reicht**, ist die einzige saubere
Schnittlinie: **1 und 2 vorziehen, dann 3 + 4 + 5 zusammen.** NICHT 1/2/4
zusammen — das zerreißt die Bandbreite.

**Das Hash-Risiko war ohnehin keins** (O1): die beiden Punkte, denen es
zugeschrieben wurde, waren Punkt 6 und Punkt 5, und beide fassen `chart()`
nicht an. Die Teilung stützte sich also nie darauf.

**Punkt 3 und 5 bleiben in jedem Fall zusammen.** Sie sind DIESELBE Mechanik — die große Zahl folgt
dem Zeiger, an Graph und Tabelle, in der Ermüdungskachel wie in den
Block-Karten. **Wer die Zeigerlogik trennt, baut zweimal dasselbe und bekommt
zwei Fassungen.** Das ist dieselbe Klasse wie die Reiter-Zuordnung aus 0.48.1,
nur eine Ebene tiefer: dort ging es um den Ort einer Kachel, hier um die
Mechanik hinter zweien. Beide Punkte brauchen DOM-Aussagen am simulierten
`pointermove`, nicht per grep.

### O1 · DIE HASH-WARNUNG — und eine Richtigstellung

**Grundsatz:** kippt ein eingefrorener `chart()`-Hash, **ist das die Funktion
des Wächters und nicht sein Versagen.** Die Neusetzung muss im Commit sichtbar
sein, mit Begründung — sie darf nicht als Nebeneffekt eines Umbaus
durchrutschen. Wer einen Hash stillschweigend nachzieht, hat den Wächter
abgeschaltet, statt ihm zu antworten.

**RICHTIGSTELLUNG (nachgesehen, nicht vermutet):** ich hatte gewarnt, Punkt 6
kippe die Hashes „mit Sicherheit". **Das stimmt so nicht.** Die sieben
eingefrorenen Fälle in `tests/test_panel_design.js` (`CHART_CASES` /
`CHART_FROZEN`: balken, linie+flaeche, punkte, baender+marken, achsen+tags,
einzelpunkt, entartet) rufen `chart()` mit FESTEN Optionen auf — die
x-Beschriftungen stehen dort als Literale (`xt: [{ i: 0, t: "Mo" }]`). Sie
prüfen den gemeinsamen HELFER, nicht seine Aufrufer.

- **Punkt 6** (Datumsachse mit Monat) ändert `dShort()` bzw. die Stelle, an der
  die Aufrufer ihre `xt` bilden — **außerhalb** von `chart()`. Die Hashes
  bleiben voraussichtlich stehen.
- **Punkt 5** (Ableseleiste) ist HTML im Kartenkopf plus die bereits
  vorhandene `grp:`-Option (im eingefrorenen Fall „punkte" schon belegt).
  Ebenfalls kein Kippen zu erwarten.
- **Kippen würden sie**, wenn jemand `chart()` selbst anfasst — etwa die
  x-Achsen-Ausgabe im Helfer statt bei den Aufrufern ändert. **Das ist dann der
  Hinweis, dass der Eingriff an der falschen Stelle sitzt**, und sollte den
  Umbau zurück zu den Aufrufern schieben, statt die Hashes neu zu setzen.

### O2 · Die sechs Punkte im Wortlaut

**1 · Der Kopfbereich der Ermüdungskachel fällt weg.** Die drei Kacheln („Was
du kannst" / „Wie weit du gekommen bist" / „Was als Nächstes") und die
Erklärabsätze darüber. Zwei davon sind aus dem Graphen ablesbar. **Die
Erklärungen werden NICHT gelöscht, sondern in den Rechenweg verschoben** —
einschließlich des Hinweises, dass die 10 % aus einer Kohortenstudie an Läufern
stammen und keine Trainingsvorschrift sind. Der gehört zur Zahl dazu.

**2 · Die Progressionszeile wandert in den Trainer.** „Was als Nächstes — bis
3 h 50" ist die einzige der drei, die im Graphen nicht steht: sie sagt, wie
LANG die nächste Fahrt sein darf, nicht wie viel Watt. Sie gehört zu „Die
nächsten Wochen", wo über Dauern entschieden wird. **Als eine Zeile, nicht als
Kachel**, mit der Herkunft dabei (höchstens 10 % über der längsten Fahrt der
letzten 30 Tage).

**3 · Die große Zahl folgt dem Zeiger.** Heute steht oben 154 W für Dauer null
und bleibt stehen. Künftig zeigt sie den Wert der Stelle, auf die gezeigt wird,
samt der Infos darunter (gemessen oder Studienform, Belegung, Datum bzw.
Dauer). **An BEIDEN Stellen: Graph UND Wertetabelle** — in der Tabelle auf
„2 h" heißt oben 138 W. Geht der Zeiger weg, fällt sie auf den Ausgangswert
zurück.

**4 · Die doppelte Tabelle auflösen. ENTSCHIEDEN: die Tabelle im RECHENWEG
bleibt, die obere fällt weg.** Begründung: sie trägt die Abweichungsspalte und
steht dort, wo ohnehin nachgelesen wird, wie die Zahl zustande kommt; die obere
wiederholt nur, was der Graph zeigt. **Die Bandbreite wandert in die Ablesezeile
aus Punkt 3**, wo sie zur jeweiligen Stelle gehört statt als Spalte für alle —
das ist besser als der Ist-Zustand, nicht bloß ein Ersatz.

**5 · Ableseleiste für die Block-Kurven** (SweetSpot, VO2max, Tempo). Heute
kommt beim Überfahren nichts, obwohl die Ermüdungskurve daneben es kann.
Fehlen: welche Einheit, welches Datum, wie viel Watt, bei welchem alpha, auf
wie vielen Blöcken. **Alle Zahlen liegen bereits in der Payload** (`points[]`
trägt `date`, `first_watts`, `median_alpha`, `n_blocks`, `block_alphas`).
**Dieselbe Bauart wie bei der Ermüdungskurve: feste Leiste im Kartenkopf, kein
schwebender Kasten**, und die große Zahl folgt wie in Punkt 3.

**6 · Datumsachse mit Monat — GESTRICHEN (14.09.2026).** Entscheidung des
Athleten: wer beim Überfahren eines Punktes ohnehin das vollständige Datum
bekommt (Punkt 3 und 5), für den ist die Achse darunter nur noch grobe
Orientierung und muss nicht umgebaut werden. **Die Datumsachse bleibt, wie sie
ist.** Der Punkt ist erledigt, nicht vertagt.

### O3 · Nicht verhandelbar

- Suite grün, neue Zählung melden; **alle Wächter grün**, einschließlich
  Zuordnungstabelle Kachel → Reiter und Vorgabewert-Wächter.
- Die eingefrorenen `chart()`-Hashes müssen halten — siehe O1. Kippt einer,
  **vor** dem Umbau melden.
- **DOM-Aussagen am simulierten `pointermove`**, nicht per grep. Gilt besonders
  für Punkt 3 und 5.
- Jede Gegenprobe gilt erst als bestanden, wenn der Fehler **gezählt und
  benannt** erscheint.
- Eine **sinkende** Prüfungszahl in einer Datei muss einzeln erklärt werden.

---

## Was der Bau von O an dieser Spezifikation korrigiert hat

**Nachgetragen am 14.09.2026, nach 0.50.0.** Die Bau-Session hat sechs
Widersprüche zwischen diesem Abschnitt und dem Quelltext gemeldet, bevor eine
Zeile entstand — Lehre 1 aus Paket A angewandt: **am Feld prüfen, nicht am
Text.** Alle sechs wurden vorgelegt und einzeln entschieden.

**1 · Der Kopf sitzt nicht in der Ermüdungskachel.** Punkt 1 sprach vom
„Kopfbereich der Ermüdungskachel". Die drei Kacheln und ihre Erklärabsätze
stehen in `rDurability`; `rFatigue` wird von dort aus aufgerufen. Nur eine
Ortsangabe, aber eine, an der sich der Eingriff entscheidet.

**2 · „Zwei davon sind aus dem Graphen ablesbar" galt nur zur Hälfte.** Die
Kurve trägt **Schwellenleistung** über der Fahrtdauer. „Was du kannst" nennt
Minuten und die **Durchschnittsleistung jener einen Fahrt** — eine andere
Größe. Ablesbar ist die Dauer am Kurvenende, die Wattzahl nicht.
**Entscheidung: ersatzlos aufgegeben**, weil gefahren wird nach alpha und
Schwellenleistung und nicht nach dem Schnitt einer alten Fahrt. Der Rechenweg
sagt, dass die Angabe gestrichen ist und warum — sonst sucht sie in vier Wochen
jemand.

**3 · Punkt 3 und Punkt 4 widersprachen sich.** Punkt 3 verlangte den Zeiger
„an BEIDEN Stellen: Graph UND Wertetabelle". Die Wertetabelle ist die obere —
und genau die streicht Punkt 4. **Entscheidung: der Zeilen-Zeiger sitzt auf der
Rechenweg-Tabelle**, der einzigen, die bleibt.

**4 · „Die Bandbreite wäre zwischenzeitlich NIRGENDS" stimmte nicht — und die
Abhängigkeit war eine andere.** Die Ableseleiste trägt seit 0.45.0 eine Zeile
`Bandbreite`. Sie zeigte aber die **Breite** (`hi − lo`, „7 W"), die Tabelle
die **Spanne** („143–151 W"). Zwei verschiedene Zahlen unter einem Namen.
Gestrichen wurde also nicht die Bandbreite, sondern die Spanne.
**Entscheidung: die Leiste zeigt die Spanne** — sie ist auch die nützlichere
Zahl. Das ist die echte Kopplung von Punkt 4 an 3/5.

**5 · „Heute kommt beim Überfahren nichts" stimmte nicht, und der Ist-Zustand
war schlechter als nichts.** Es kam ein Wert der **Ermüdungskurve**, weil alle
Block-Karten im selben Gruppen-Wrapper liegen (PROJEKTSTAND §7, zehnter Fall).
Keine fehlende Funktion, sondern eine falsche Anzeige. Behoben an der Wurzel:
geschachtelte Gruppen je Familie **und** die Leiste schreibt nur noch, wenn der
Zeiger senkrecht über dem Diagramm liegt — halb beheben wäre schlechter
gewesen, weil es dann bei den Block-Karten stimmt und beim Rest nicht.

**6 · „Bei welchem alpha" nannte das falsche Feld.** Punkt 5 führte
`median_alpha` auf. Aufgetragen wird `first_watts`, also gehört `first_alpha`
daneben; der Median ist die **Steuergröße** und steht als eigene Zeile. Das ist
genau die Trennung, die `test_blocks.py` erzwingt — sie wäre im Frontend wieder
eingerissen worden. Zusatz: `points[]` trägt auch `name`, „welche Einheit" ist
damit wörtlich beantwortbar.

**Und zur Teilung:** die Empfehlung „ein Release" hielt, ihre Begründung nicht.
Sie stützte sich darauf, dass die Bandbreite zwischenzeitlich nirgends wäre —
das war falsch (Punkt 4 oben). Getragen hat sie trotzdem, aus dem korrigierten
Grund: die Leiste musste von Breite auf Spanne umgestellt werden, und das
gehört zur Mechanik aus 3/5.

**Zur Hash-Warnung:** die Richtigstellung in O1 war richtig. Angefasst wurden
ausschließlich die Aufrufer; `grp:` ist eine vorhandene Option, im eingefrorenen
Fall „punkte" schon belegt. **Alle sieben Hashes haben gehalten.**

---

## Paket P — Die Zuordnung trifft der Athlet, überall (SPEZIFIKATION, 15.09.2026)

**Stand bei der Niederschrift: 0.51.1, Prüfstand 19 Dateien / 5.861 Prüfungen
grün.** Diese Spezifikation ist geschrieben, nicht gebaut. Jede Festlegung ist
am Quelltext geprüft; wo die Auftragsfassung am Code nicht trug, steht die
Korrektur mit ihrem Grund daneben (Abschnitt „Was die Prüfung dieser
Spezifikation ergeben hat"). Zwei Punkte sind **bewusst gestrichen** und stehen
samt Gegenargument in P11 — damit die nächste Sitzung sie nicht für ein
Versehen hält und nachbaut.

### P0 · Warum überhaupt

Das System rät heute an drei Stellen, und jedes Mal über eine Fahrt, von der es
nichts weiß:

1. **Die Familie aus dem Namen** — `blocks.family_of` sucht „sweetspot", „vo2"
   oder „tempo" im Titel.
2. **Die Eignung aus dem Zonenanteil** — `derive.fatigue_curve_reason` mit
   `FATIGUE_MAX_ABOVE_Z2 = 20.0`.
3. **Die Blöcke aus den Lap-Etiketten** — `derive.dfa_blocks` über
   `label == "WORK"`, nachkorrigiert von `drop_warmup_blocks`.

Beim Autor trägt das halbwegs, weil er seine Einheiten diszipliniert benennt.
Bei einem zweiten Nutzer mit anderem Fahrprofil trägt es nicht.

**Drei eigene Fehler dieses Projekts belegen, dass jede der drei Vermutungen
schon danebenlag:**

- **Der Einrollblock als WORK etikettiert.** Am 02.07.2026 stand die Leitzahl
  bei 182 statt 238 W, am 19.07. bei 197 statt 278. Die Reparatur ist
  `drop_warmup_blocks` — eine Ausreisserregel aus den Zahlen der Einheit
  selbst, weil weder eine Wattschwelle noch der Korridor taugten. Sie ist gut
  gebaut und rät trotzdem.
- **Die Tempo-Einheit vom 13.09.2026** trägt einen lockeren Abschnitt mit 164 W
  neben einem echten vierten Block mit 165 W. Dazwischen liegen 0,6
  Prozentpunkte. Keine Automatik trennt das; der Athlet trennt es, ohne
  nachzudenken.
- **Der 20-%-Filter erbt eine FTP, die selbst bestritten ist.**
  `above_endurance_share` liest `icu_zone_times` — eine Zonenrechnung von
  Intervals, die an der FTP hängt. Solange der Profilwert 200 W beträgt und die
  gemessene 20-Minuten-Leistung bei 192 liegt, schneidet der Filter an der
  falschen Stelle (P9). **Ein Ausschlusskriterium auf einer bestrittenen Zahl
  ist eine Vermutung mit Dezimalstelle.**

#### P0a · Und die Automatik kann nicht sehen, was zählt

Der Ermüdungsverlauf einer Fahrt hängt an Bedingungen, die in **keinem Feld
dieses Systems** stehen:

- **Umgebungstemperatur.** Lafrenz, Wingo, Ganio und Cureton (Med Sci Sports
  Exerc 2008;40(6):1065–71) maßen den Anstieg der Herzfrequenz und den Abfall
  des Schlagvolumens zwischen Minute 15 und 45 bei 59,2 ± 1,9 % VO2max an zehn
  ausdauertrainierten Männern, einmal bei 35 °C und einmal bei 22 °C. **Der
  Befund ist ein UNTERSCHIED, kein Schalter:** das Ausmaß des kardialen Drifts
  und der begleitende Abfall der VO2max sind in der Hitze GRÖSSER als in der
  Kühle — nicht „dort ja, hier nichts". Die erste Fassung dieser Zeile behauptete
  das Schärfere; das wäre der achte §7-Fall gewesen, aus einer Arbeit die
  günstige Hälfte.
- **Verpflegung.** Clark u. a. (J Appl Physiol 2019;127:726–736) zeigen den
  zeitlichen Verlauf der Abnahme von CP und W′ über zwei Stunden und dass
  Kohlenhydratzufuhr während der Belastung **CP erhält — W′ nicht**, und zwar
  ohne den Glykogenabbau im Muskel zu verändern. **Zwei Einschränkungen gehören
  dazu:** erhalten wurde eine Größe von zweien, und die Vorbelastung war
  **schwer-intensiv**, nicht moderat — unsere Ermüdungskurve fragt nach der
  moderat-zu-schwer-Grenze und liegt damit woanders.

**Das Argument steht NICHT auf „es gibt kein Temperaturfeld".** Das wäre
widerlegbar: `average_temp`, `min_temp` und `max_temp` stehen im dokumentierten
Datenmodell von Intervals, und `temp` ist ein dokumentierter Stromtyp. Sie
werden trotzdem nicht geholt, und das ist eine **Entscheidung des Athleten vom
15.09.2026**, kein Versäumnis — siehe P11, Streichung 3.

**Das Argument steht darauf, dass selbst mit einem Temperaturfeld niemand
wüsste, ob verpflegt wurde, wie geschlafen wurde und ob Gegenwind stand.** Das
ist unangreifbar — und es ist genau der Grund, warum das eine verfügbare Feld
die Lücke nicht schließt.

Künftig gilt in diesem Projekt durchgehend: **der Athlet ordnet zu, das System
rechnet.** Dieselbe Bauart wie K2 und N — nur nicht mehr als Sonderfall zweier
Messungen, sondern als Regel.

### P1 · Einstellungen über das Archiv — und der Schalter heißt „Vorschläge"

**Befund am Code: es gibt heute keinen Schaltermechanismus.**
`grep -rn "async_get_options_flow\|OptionsFlow" custom_components/` liefert null
Treffer; `config_flow.py` kann `user` und `reauth`, sonst nichts.

**Kein Options-Flow, sondern ein Archivblock**, und der Grund ist nicht
Bequemlichkeit: ein Options-Flow ist ein HA-Dialog **außerhalb** des Panels und
stünde damit an einem anderen Ort als das, was er schaltet — die Trennung, die
0.46.0 zurücknehmen musste. Das Archiv trägt das Muster bereits dreimal (`goal`,
`day_context`, `ramp_tests`): Eintrag in `importer.empty_data()`, Migration in
`store.async_load`, WebSocket-Schreibweg, Panel liest ohne HA-Neustart. Und
entscheidend für §9: **ein Archivblock ist HA-frei prüfbar, ein Options-Flow
nicht.**

Zu bauen: Block `settings`, WebSocket-Paar `settings` / `set_setting`, im Panel
ein Reiter, der jeden Schalter **mit seiner Begründung** zeigt. Ein Schalter
ohne Satz daneben ist eine Falle für den, der ihn in drei Monaten findet.

#### P1a · „Vorschläge an/aus", nicht „Automatik an/aus" — und warum

Der erste Schalter heißt `suggestions`, Vorgabe `true`. **Die Automatik darf
vorschlagen; gezählt wird nichts, bis es bestätigt ist.** Das Archiv enthält
ausschließlich bestätigte Marken.

Das ist keine Geschmacksfrage, sondern die Auflösung eines belegten Zielkonflikts:

- **Vorschläge sparen sehr viel Zeit.** Eine industrielle Segmentierungsstudie
  misst 73–84 % gesparte Beschriftungszeit (im Mittel 78 %) und eine um das 8-
  bis 17-fache **kleinere Streuung** zwischen den Elementen — die Bearbeiter
  konvergieren auf gleichmäßige Nachbesserungszeiten.
- **Sie kosten aber Initiative.** Eine CHI-Studie zu vorbefüllten
  Annotationsvorschlägen findet, dass Fachleute Modellfehler zwar abfangen,
  **aber weniger Eigeninitiative entwickeln**; die ausdrückliche Sorge war, dass
  Nutzer bei unvollkommenen Modellen das Interesse verlieren und Vorschläge mit
  falschen Bereichen oder Etiketten annehmen.
- **Zur Ankerwirkung ist die Lage uneinheitlich, und das ist selbst ein
  Befund.** Fort/Sagot und Névéol finden keine Verzerrung durch Vorannotation;
  andere Arbeiten weisen Ankereffekte auch bei Fachleuten nach, schwächer als
  in den frühen Experimenten, und stärker, wenn die Entscheidungszeit knapp ist.
  Eine Studie zur De-Identifikation klinischer Texte fand sogar, dass die
  Bearbeiter die Maschinenvorschläge nur für einen kleinen Teil ihrer
  Annotationen nutzten, weil sie auf dem Rohtext leichter arbeiteten.

**Daraus die Bauregel: Vorschläge werden NICHT vorangehakt.** Sie stehen als
blasse Geisterhaken da, die angeklickt werden müssen. **Der Unterschied
zwischen „ich muss abwählen" und „ich muss auswählen" ist der ganze
Unterschied** zwischen Unterkorrektur und Entscheidung.

**Und die Parallele, die im Haus schon gilt:** ein Diarisierungswerkzeug von
2026 füllt seine Oberfläche mit der Ausgabe einer automatischen Pipeline, damit
der Bearbeiter eine Hypothese korrigiert statt von null zu zeichnen — und
**bindet den Export an eine Bestätigung JE SEGMENT durch den Menschen, damit
automatische Ausgabe nicht unbestätigt nach außen gelangt.** Das ist 0.49.2 in
einem anderen Fach: eine Zahl, die nicht misst, was daneben steht, darf nicht in
die Auswertung.

### P2 · Die Zuordnung — sieben Kacheln, eine Reihe, ein Ort

**Ort: das Aktivitätsdetail, zwischen `kvgrid` und `_lapBlock`** — also zwischen
den Kennzahlen und der Rundenliste, direkt über dem, was gehakt wird. Die Haken
selbst stehen in einer eigenen, beschrifteten Spalte der Rundenliste.

| Kachel | Art |
|---|---|
| VO2max · SweetSpot · Tempo · Schwelle | Abschnitte |
| Grundlage · lange Fahrt | Abschnitte |
| Stufentest | ganze Fahrt |

**Der bestehende `_rampBlock` fällt weg.** Er sitzt heute zwischen `_ctxBlock`
und `_nightBlock` und trägt wörtlich die Begründung, die jetzt für alles gilt
(„du markierst, das System erkennt nicht") — nur an einem anderen Ort als die
neuen Kacheln. **Zwei Bedienelemente für dieselbe Frage war der Fehler aus
0.46.0.** Eine Reihe, eine Frage, ein Ort. `set_ramp_test` bleibt unverändert;
nur sein Bedienort wandert.

**Der Stufentest ist die einzige Familie ohne Abschnitte:** eine Messfahrt ist
als Ganzes eine Messfahrt, es gibt daran keinen Abschnitt zu markieren.

`threshold` bekommt Haken, obwohl `BLOCK_CORRIDORS` heute nur drei Familien
führt und `SOURCE_CHAIN["threshold"]` keine Blockstufe hat: Schwelle fährt
Blöcke, und sobald der Athlet sie benennt, gibt es keinen Grund, sie
auszuschließen. **Der Korridor für `threshold` gehört gemessen, nicht gesetzt** —
bis er belegt ist, bleibt die Familie in der Quellenkette, wo sie ist.

**Ein Abschnitt kann Marken mehrerer Familien tragen.** Der Datentyp ist eine
Menge, keine Auswahl. Zur Mehrfachzuordnung je Element gibt es keine Studie —
die Werkzeuge können es, gemessen hat es niemand. Deshalb bleibt die Regel
klein: **eine Marke je Familie je Abschnitt, kein Rang, keine Gewichtung.**

#### P2a · Farbe, Form, Kürzel — und warum die Farbe hier nicht allein trägt

**Die Auflage bleibt: keine Urteilsfarbe.** Grün/Gelb/Orange/Rot gehören
ausschließlich dem Urteilsregister; `test_panel_design` erzwingt die Trennung,
und dieselbe Fehlerklasse hat 0.7.0, 0.8.0 und 0.9.0 je ein Release gekostet.

**Die Farbe kann die Identität hier aber nicht allein tragen, aus zwei
unabhängigen Gründen am Code:**

1. **`ROLE` belegt das Kategorienregister in genau dieser Ansicht vollständig.**
   Im Aktivitätsdetail gilt `pow: C.violet`, `hr: C.magenta`, `dfa: C.cyan`,
   `cad: C.slate`, `vel: C.blue`, `alt: C.deep`. Die Rundenliste zeichnet den
   EF-Balken in `ROLE.pow` (violett) und den DFA-Balken in `ROLE.dfa` (cyan) —
   **direkt neben der Spalte, in der die Haken stehen.** Ein violetter
   SweetSpot-Haken zwei Spalten neben einem violetten Leistungsbalken ist
   dieselbe Registervermischung, nur innerhalb des Kategorienregisters.
2. **Das Kategorienregister hat in der Praxis sieben Farben, nicht fünf, und
   alle sind belegt.** `CTX_COLOR` führt slate/violet/blue/cyan/magenta/deep/grey
   mit festen Bedeutungen, und `test_panel_design` erzwingt `cats.length === 7`
   samt paarweiser Verschiedenheit. Dazu sind `C.deep` (#64748b) und `C.slate`
   (#94a3b8) zwei Graustufen desselben Tons.

**Also: Form und Kürzel tragen die Identität, die Farbe ist Zweitkodierung.**
Belegt, nicht ausgewichen: CatPAW (CHI '26) prüft redundante Kodierung aus Farbe
UND Form gegen jede Einzelkodierung und findet eine signifikante Verbesserung
der Erkennung, am stärksten bei **fünf bis acht Kategorien**. Die Einzelgrenzen
sind beziffert — Farbe allein trägt bis sieben, Form allein bis fünf. **Sechs
Familien mit Haken liegen über der Formgrenze und unter der Farbgrenze, also
braucht es beide**, und das ist genau der Bereich, für den die Arbeit den
größten Gewinn misst. WCAG 1.4.1 ist damit nebenbei erfüllt und nicht der Grund.

Auflagen:

- Jede Familie trägt **eine eigene Form** aus `IC` (keine Variante einer
  anderen — die Regel aus dem Urteilsregister gilt hier genauso) und ein
  **Kürzel** von zwei bis vier Zeichen.
- Die Haken stehen in **einer eigenen Spalte mit Kopfzeile**, nicht zwischen den
  rollengefärbten Balken.
- **Die aktive Kachel ist deutlich erkennbar** — Rahmen, Wort und Form, nicht
  nur eine Sättigungsstufe. Wer die aktive Kachel nicht sieht, hakt in die
  falsche Familie, und das ist ein Fehler ohne Fehlermeldung.

#### P2b · Haken sofort, Messung nur auf „übernehmen"

**Der Haken ist sofort im Archiv.** Die Messung läuft **ausschließlich** auf
einen ausdrücklichen Knopf „übernehmen und messen".

**Warum es kein „beim Verlassen" gibt — am Code geprüft:** das Aktivitätsdetail
hat zwar `data-act="close"`, aber das ist **einer von mindestens vier
Ausgängen**. Die anderen: eine andere Fahrt anklicken (`_openAct` überschreibt
`_sel`), den Reiter wechseln, die Hash-Route `#activities/<id>`, den Browser
schließen. Keiner läuft über den Close-Handler, es gibt kein `beforeunload`, und
die HA-WebSocket-Verbindung kann fallen. **„Gehakt, weggegangen, nichts
gemessen" wäre der stille Ausstieg aus 0.42.1.**

Also steht der Eintrag nach dem Haken mit `hours: null` und
`reason: "noch nicht gemessen"` im Archiv, und die Kachel zeigt diesen Zustand.
Das ist die zweite Regel aus `ramp_tests` wörtlich: **keine stille Messung — die
Markierung steht trotzdem, aber mit dem Grund daneben.**

#### P2c · Drei Zustände statt zwei, wenn keine DFA-Daten da sind

Die Auflage „ohne DFA-Daten ausgegraut" trifft sonst eine Gruppe mit, die man
nicht ausgrauen darf: `async_import_dfa` schreibt bei einem fehlgeschlagenen
Stromabruf ausdrücklich `data["dfa"][key] = {}`, damit die Fahrt nicht bei jedem
Refresh erneut geholt wird. **Eine Fahrt, deren Abruf ein einziges Mal
scheiterte, wäre damit für immer „ohne DFA-Daten" — ohne Grund und ohne zweiten
Versuch.**

| Zustand | Verhalten |
|---|---|
| Fahrt führt kein `dfa_a1` | ausgegraut, Satz dazu |
| Abruf ist gescheitert (`{}` im Archiv) | **nicht** ausgegraut, Knopf „nochmal holen" |
| Summary da, aber keine `blocks` | Abschnittsfamilien ausgegraut, Grundlage und lange Fahrt **nicht** — sie messen über `hours`, nicht über Blöcke |

**Und der Satz, der dazugehört:** das Markieren holt die Ströme ohnehin LIVE;
der Archivstand ist nur ein Stellvertreter. §7 erster Fall gilt hier genau —
`stream_types` sagt, was in der Datei lag, nicht was die Schnittstelle liefert.
Wer nach einem Stellvertreter ausgraut, sagt daneben, dass es einer ist.

### P3 · Der Archivblock

Ein Block `section_marks`, Schlüssel `activity_id`:

```
section_marks: {
  "<activity_id>": {
    "date": "YYYY-MM-DD",
    "marks": { "<familie>": [<start_index>, ...] },
    "anchor": { "laps": <n>,
                "sections": [ {"i": <start_index>, "s": <moving_time>} ] },
    "hours": [...] | null,
    "reason": "...",
    "set_at": "...",
    "v": MEASURE_VERSION
  }
}
```

#### P3a · DER SCHLÜSSEL IST `start_index`, NIEMALS DIE LAUFENDE NUMMER

**Das ist die wichtigste einzelne Festlegung dieses Pakets, und sie steht hier
in dieser Schärfe, weil der falsche Weg naheliegt und in der ersten Fixture
funktioniert.**

Es gibt **zwei getrennte Abschnittslisten, und sie sind nicht deckungsgleich:**

- Die **Rundenliste im Panel** (`_lapBlock`) kommt LIVE über `websocket_laps`
  → `derive.normalize_laps`. Sie nummeriert mit `n` = Position in der Rohliste,
  **jeder** Lap, auch Pausen.
- Die **Blöcke im Archiv** (`dfa[key]["blocks"]`) entstehen beim Import über
  `derive.dfa_blocks` und **fallen weg**, wenn `moving_time < BLOCK_MIN_SECONDS`
  (150 s), wenn `start_index`/`end_index` fehlen, oder wenn nach dem
  120-Sekunden-Verwerfen weniger als `BLOCK_MIN_POINTS` (20) brauchbare
  alpha-Werte übrigbleiben.

**Wer im Panel Abschnitt 7 anhakt und das als Index 7 ablegt, trifft im Archiv
einen anderen Block.** Der einzige gemeinsame Schlüssel ist `start_index`: er
steht in `_LAP_FIELDS`, kommt also in der Panel-Payload an, und `dfa_blocks`
schreibt ihn gerundet mit.

**Wer `[3, 5]` als laufende Nummern baut, baut einen Fehler, der bei einer Fahrt
ohne Pausen nicht auffällt und bei jeder Intervalleinheit zuschlägt.** Die
Fixture in „Tests P" muss deshalb **zwingend** eine Fahrt enthalten, bei der
mindestens ein Lap durch `dfa_blocks` fällt — sonst besteht dieser Fehler die
ganze Suite.

#### P3b · Der Fingerabdruck, und warum er kein Verstoß gegen J7 ist

J7 sagt: gespeichert wird nur, was nicht wieder herleitbar ist. Der Anker
`{laps, sections[{i, s}]}` sieht nach einer Verletzung aus und ist keine.

**`importer.drop_outdated_dfa()` setzt bei abweichender `DFA_ALGO_VERSION`
schlicht `data["dfa"] = {}`.** Damit sind alle `blocks` samt ihrer `start_index`
weg und werden beim Re-Import aus **frisch geholten Laps** neu gerechnet. Die
Auswahl überlebt — ihre Ankerpunkte nicht. **Nach dem Bump ist der
Vergleichsstand genau das, was gerade gelöscht wurde.**

Das ist der **siebte Fall (0.49.2) in neuer Gestalt: wer einen Fix ausliefert,
verliert damit die Belege für die Prüfung, die den Fix gefunden hat.** Die Lehre
dort lautete, solche Fälle VOR der Neuberechnung als Fixture zu sichern statt
danach zu suchen. Hier heißt dasselbe: **den Anker beim Markieren sichern.**

Gespeichert wird das Minimum: Zahl der Laps, und je markiertem Abschnitt
`start_index` und `moving_time`.

**Die Drifterkennung:** beim Lesen wird der Anker gegen die aktuellen Blöcke
gehalten. Weicht die Lap-Zahl ab, oder findet sich zu einem gespeicherten
`start_index` kein Abschnitt mit passender Dauer, **MELDET das System das** —
`marks_stale: true` samt Grund, an der Kachel **und als eigenes Zeichen in der
Aktivitätenliste** (P5). Die Markierung bleibt stehen und wird **nicht**
stillschweigend weiterverrechnet; die betroffene Fahrt fällt aus Messung und
Kurve, bis der Athlet sie bestätigt oder neu hakt.

**Stillschweigend weiterrechnen wäre der stille Ausstieg** (§7, vierte
Fehlerklasse): ein Wert aus verschobenen Abschnitten sieht aus wie einer aus
richtigen.

#### P3c · Die zwei Auflagen aus J7, zum fünften Mal

1. **Eintrag in `importer.empty_data()`.** `store.async_load` füllt fehlende
   Schlüssel **nur auf der obersten Ebene** auf; ein Block, den das Grundgerüst
   nicht kennt, entsteht auf Altbeständen nie. Das ist die Lücke aus 0.35.0 —
   nach `goal`, `day_context` und `ramp_tests` das fünfte Mal.
2. **Migration in `store.async_load`**, Bauart `plan.migrate_goal()` /
   `ramp_tests.migrate()`: `None` zurück, wenn nichts zu tun ist, sonst der
   normalisierte Block; `schedule_save()` **nur** im Änderungsfall. Die
   eingefrorene No-op-Referenz gilt — **ein No-op darf keinen Speichervorgang
   auslösen.**

Dazu die Trennung aus `day_context` und `ramp_tests`: **das Schreiben ist
streng** (`ValueError` mit einem Grund, den die Karte zeigen kann), **das Lesen
ist nachsichtig.**

**Eigene `MEASURE_VERSION`.** Sie deckt die Messung ab, nicht die Anzeige.
Ändert sich die Rechnung, verliert der Eintrag seine `hours` — **die Markierung
und der Anker bleiben.** Die Aussage des Athleten, welcher Abschnitt welcher
Familie gehört, verfällt nicht, wenn sich die Mathematik ändert. Veraltete
Messungen sind in der Kachel **sichtbar**, nicht still.

#### P3d · Die Rücknahme sitzt auf der einzelnen Marke

**Nicht auf „letzter Zustand".** Die Kritik an einem verbreiteten
Annotationswerkzeug trifft genau diesen Punkt: seine Rücknahme entfernt nur
Ebenen, statt die tatsächlich zuletzt ausgeführte Aktion rückgängig zu machen.
**Eine Rücknahme, die etwas anderes zurücknimmt als das Getane, ist schlimmer
als keine.**

Also: rückgenommen wird **eine Familie an einem Abschnitt**. Ist danach keine
Familie mehr übrig, fällt der ganze Eintrag — kein Rumpf bleibt stehen, und die
Fahrt rechnet wieder bit-identisch wie eine nie markierte. Das ist eine
Rücknahme, keine Aussage.

#### P3e · Die Rangfolge gegen `drop_warmup_blocks`

`drop_warmup_blocks` etikettiert Ausreisser auf `WARMUP_LABELLED_WORK` um. Ist
derselbe Abschnitt von Hand markiert, stehen zwei Aussagen gegeneinander.

**Die Markierung schlägt die Heuristik, und die Karte sagt, dass sie es tut** —
ein Satz an der Einheit, nicht ein stiller Vorrang. Stillschweigend gewinnen zu
lassen, in welcher Richtung auch immer, wäre der stille Ausstieg: **was nicht
passiert ist, muss dastehen.**

### P4 · Maskieren, nicht neu basieren — und das Markieren misst

**Warum das Markieren misst:** `dfa_hours` läuft in
`importer.async_import_dfa` auf den ungedünnten Strömen, die unmittelbar danach
weggeworfen werden. Im Archiv liegen Summary, Stundenverlauf und Blöcke — **kein
Sekundenstrom.** Ein bereinigter Strom ist daraus nicht zu bauen. Also dieselbe
Mechanik wie bei `set_ramp_test`: Ströme LIVE und UNGEDÜNNT, messen, **nur das
Ergebnis** speichern. Kein Algorithmus-Bump, keine Neuberechnung des Bestands.

**MASKIEREN, NICHT NEU BASIEREN.** `dfa_hours` bildet die Stundenkübel über die
Stromposition (`hour * per_hour`). Zwei Wege wären denkbar:

- **Neu basieren:** der markierte Bereich wird zusammengeschoben, die Uhr fängt
  bei null an.
- **Maskieren:** die Kübelgrenzen bleiben auf der Fahrtzeit, ausgeschlossene
  Sekunden liefern keine Punkte mehr.

Bei „zwei Stunden Grundlage, SweetSpot am Ende" liefern beide dasselbe. Bei
„30 min Tempo, danach zwei Stunden Grundlage" nicht: neu basiert wäre „Stunde 1"
die Grundlagenminute 0 bis 60 — **und behauptet damit eine Frische, die nicht
vorlag.** Der Athlet war 30 Minuten auf dem Rad.

**L1 misst Ermüdung über die Zeit AUF DEM RAD, nicht über die Zeit in der
Zone.** Die Tempominuten zählen für die Ermüdung; nur ihre alpha-Watt-Paare
taugen nicht für die Ablesung. Ein ausmaskierter Berg bei 1:40 nimmt Stunde 2
zwanzig Minuten Punkte — **und Stunde 2 bleibt Stunde 2, weil der Berg müde
gemacht hat.** Maskieren ist nie schlechter und manchmal richtig.

Fünf Auflagen an `dfa_hours`, alle aus der Maskierung:

1. **Ein dritter Zähler `excluded` neben `dropped`.** `dropped_share` ist der
   Ersatz für Andriolos Artefaktkriterium und sagt, was die MESSUNG verloren
   hat. Zählt man bewusst ausgeschlossene Sekunden dort mit, sieht eine sauber
   markierte Fahrt wie ein Datenschaden aus. Der Nenner bleibt auf dem
   zugelassenen Fenster.
2. **`occupancy_rising` darf nicht auf sauberen Daten feuern.** Das
   Erkennungszeichen vergleicht die Zahl der Fahrten **mit** p075-Wert je
   Stunde. Maskieren nimmt Stunde 1 überproportional Punkte (dort liegen
   Anwärmen und Anlaufblöcke), also können weniger Fahrten in Stunde 1 einen
   Wert liefern als in Stunde 2 — **und der Auswahleffekt-Alarm ginge los,
   obwohl keiner vorliegt.** Der Vergleich läuft künftig auf „Fahrten, die diese
   Stunde ANGEBOTEN haben", nicht auf „Fahrten, die einen Wert erzeugt haben".
   Das ist die §9-Regel wörtlich: **ein Wächter, der bei richtigem Sachverhalt
   anschlägt, wird verengt, nicht entschärft.**
3. **Der Anker nennt seine Stunde.** `anchor = measured[0]["watts"]`, und die
   Literaturform wird von dort auf t = 0 zurückgerechnet. Verliert Stunde 1 ihre
   Fahrten, sitzt der Anker auf Stunde 2 — auf einem bereits ermüdeten Punkt —
   und `anchor_base` springt nach oben. Die Payload führt `anchor_n`, aber nicht
   `anchor_hour`. Eine Zahl dazu, und die Kachel nennt sie.
4. **Die maskierte `hours`-Liste gewinnt, und die Karte sagt, welche galt.** Das
   Archiv behält die Ganzfahrt-Liste aus dem Import; der Zuordnungsblock trägt
   die maskierte. `fatigue.curve()` zieht die maskierte vor, und
   `rides()["used"]` führt je Fahrt `hours_source` (`markiert` / `ganze Fahrt`).
   **Zwei verschieden erhobene Größen unter einer Überschrift ist 0.49.2.**
5. **Für markierte Fahrten fällt das VI-Tor konstruktiv weg, `short` wird neu
   gerechnet.** `moving_time`, `icu_zone_times` und `variability_index` sind
   alle Ganzfahrt-Felder aus dem Summary; für den markierten Bereich gibt es
   weder Zonenverteilung noch VI. Der Athlet hat gesagt, welche Sekunden
   gleichmäßig waren — das ist die Ersetzung, und sie ist beabsichtigt.
   **`short` dagegen rechnet sich aus der markierten Bewegungszeit gegen
   `FATIGUE_MIN_MINUTES`**, nicht aus der Fahrtdauer. Sonst verschwindet ein Tor
   stillschweigend.

**P4 ist der Teilungspunkt des Pakets.** Wächst es beim Bau, sind **P3**
(Block, Anker, Schreibweg — ungemessen) und **P4** (Messung und Maskierung)
zwei Auslieferungen.

### P5 · Die Spalte in der Aktivitätenliste

Dieselben Marken (Form + Kürzel, Farbe als Zweitkodierung) als kompakte Reihe je
Zeile. **Leer heißt: noch nicht angefasst** — genau das ist die Aussage, die die
Spalte liefern soll. Eine markierte Fahrt ohne Familie gibt es nicht, weil der
Eintrag dann fällt (P3d).

**`marks_stale` trägt ein eigenes Zeichen**, und eine veraltete Messung
ebenfalls — beides sind eigene Zustände, nicht „unbearbeitet".

**Die Liste bleibt chronologisch, neueste zuerst.** Sie bekommt die Spalte, mehr
nicht (P11, Streichung 2).

**Der Aufwand sitzt im CSS, nicht in der Logik.** `.arow`/`.ahead` sind ein Grid
mit neun Spalten, und die mobile Regel blendet `nth-child` (4), (6), (7), (8),
(9) aus. Eine zehnte Spalte heißt: **zwei** `grid-template-columns` ändern, die
Kopfzeile ergänzen, **und die mobile Ausblendliste nachziehen** — sonst rutscht
die Markierungsspalte auf dem Telefon in die vier sichtbaren und verdrängt die
Last.

### P6 · Die Herkunftsspur — und sie ist NICHT frontend-only

Auf eine Zahl klicken → welche Einheiten, welche Abschnitte, welcher Wert je
Abschnitt → klicken → die Aktivität öffnet sich.

**Am Code geprüft: `blocks.series()` baut seine `points` aus `_sessions()` und
lässt dabei `activity_id` fallen.** Drin sind `date` und `name`, nicht die ID.
Der Sprung braucht die Hash-Route `#activities/<id>` aus A4, und die ID kommt in
der Payload nicht an.

Eine Zeile Backend — **aber sie muss hier stehen.** „Berührt nur das Frontend"
war bei A5 falsch und bei H falsch; das dritte Mal wäre kein Zufall mehr,
sondern eine Bauart. `fatigue.rides()` macht es richtig vor.

Was die Spur zeigt: Leitzahl und Steuergröße **getrennt**, mit den Einzelwerten
je Block (`block_alphas`, `block_watts_each` reisen bereits mit) · welche
Abschnitte beigetragen haben, und bei markierten Fahrten, dass es die markierten
waren · bei der Kurve die Fahrten mit ihrem `hours_source`.

### P7 · Das Subjektive an EINEN Ort — Intervals' eigene Felder

**Kein eigenes Notizfeld.** Der Athlet schreibt ohnehin in Intervals, und ein
lokales Feld daneben wäre der zweite Ort für dieselbe Frage — die 0.46.0-Klasse
in klein.

Zu holen und anzuzeigen, **ohne jede Rechnung, ohne Filter, ohne Auswertung**:

- **`description`** — Intervals' eigene Notiz zur Fahrt.
- **`icu_rpe` und `feel`** stehen bereits in `ACTIVITY_FIELDS` und werden im
  Detail angezeigt (`stat("user", "RPE / Gefühl", …)`) — **von nichts benutzt.**
  Sie gehören neben die Notiz, damit das Subjektive an einem Ort steht statt
  verstreut.

**Das ist alles.** `description` kommt neu in `ACTIVITY_FIELDS`,
`ACTIVITY_FIELDS_VERSION` geht von 2 auf 3 (der Nachlade-Weg über
`needs_activity_refetch` steht bereits), und die drei Angaben stehen im
Aktivitätsdetail beieinander. Kein weiteres Feld, keine Rechnung, kein Filter.

**Leer heißt sichtbar leer.** Eine Fahrt ohne Notiz zeigt das, statt die Zeile
wegzulassen — sonst sieht „keine Notiz geschrieben" aus wie „Feld gibt es
nicht" (§7, vierte Fehlerklasse).

### P8 · Hinweise: klein, aufklappbar, ohne Urteil

Hausmuster: Zeichen oben, Erklärung darunter — im Panel ist das
`<details class="more"><summary>…`, durchgehend nativ und mit
Accordion-Barrierefreiheit begründet.

**Zwei Hinweise, beide ZEIGEN nur:**

1. **Fahrt mit nur einem Abschnitt.** `normalize_laps` liefert eine einzige
   Runde → Satz, dass in Intervals unterteilt werden muss, damit es hier etwas
   zu markieren gibt. Keine Sperre.
2. **Wo der geglättete alpha-Strom 0,75 oder 0,5 kreuzt.** Eine Marke an der
   Stelle, und der Text sagt **„hier kreuzt alpha 0,75"** — nicht „hier bist du
   eingebrochen".

**Warum es KEINE Einbruchs-Definition gibt:** die Auftragsfassung wollte eine
Marke bei einem „Alpha-Einbruch". Das wäre eine Erkennung, und P0 verbietet
Erkennungen. Schlimmer: eine neu erfundene Einbruchs-Statistik ist wörtlich L0
Runde 3 — eine Größe, die eine Auswahl erzeugt und die gesuchte Eigenschaft mit
einsammelt. **Die zwei Schwellen 0,75 und 0,5 sind dagegen im Haus belegt**
(Rogers 2021a für 0,75, 2021b für 0,5, beide Laufband, mit der Validierungslage 2024–2026 daneben) und werden
von der Kurve und vom Stufentest ohnehin benutzt.

**Die Zahlen kommen AUS DER PAYLOAD** (fünfte Bauregel: ein Erklärtext, der eine
Schwelle nennt, nennt sie aus der Payload oder gar nicht), und **kein
Urteilston** — die Marke liegt im Kategorienregister, nicht im Urteilsregister.

#### P8a · Der Zuordnungshinweis, und was er nicht wissen kann

Beim Anhaken erscheint ein Hinweis, wenn der Abschnitt nach Abzug der zwei
Anlaufminuten kaum etwas trägt. **Er kann sich nur auf die DAUER stützen.** Die
Live-Lap-Payload führt `moving_time`; die Zahl der brauchbaren alpha-Punkte
entsteht erst in `dfa_blocks` beim Messen (`BLOCK_MIN_POINTS = 20` nach
`BLOCK_WARMUP_DISCARD_S = 120`). Der Hinweis nennt Dauer und
`BLOCK_MIN_SECONDS` und sonst nichts — wer mehr verspricht, baut einen Hinweis,
der still falsch liegt. **Er hält nicht auf.**

### P9 · Die Rückfallkette bleibt — und es wird erst schlechter

Ohne Zuordnung rutscht jede Familie auf die FTP, **sichtbar beschriftet**:
`SOURCE_LABEL["ftp"]` sagt schon heute „Rückfall auf die FTP — nicht gemessen".
Kein Loch, nur ein schlechterer Rückfall.

Die Belegungsstaffelung bleibt: `BLOCK_MIN_FOR_SOURCE = 3` für die Blockmessung,
`FATIGUE_MIN_PAIRS = 6` für die Staffelung der Kurve, `_band()` für die
Darstellungsbereiche.

#### P9a · Die Kachel sagt, wie viele Einheiten noch fehlen

**„Noch eine, dann misst SweetSpot wieder."** Die Zahl liegt vor — `sessions`
gegen `min_for_source` reisen beide in der Payload —, sie muss nur genannt
werden. Damit weiß der Athlet, worauf er zuarbeitet, **ohne dass ihn etwas
führt** (P11, Streichung 2).

#### P9b · Es sind rund ZWANZIG Fahrten, nicht achtundfünfzig

Diese Rechnung ändert die ganze Bewertung des Aufwands und gehört deshalb hier
hin, aus den eigenen Konstanten:

- vier Abschnittsfamilien × `BLOCK_MIN_FOR_SOURCE` (3) = **12 Einheiten**
- plus rund **8 lange Fahrten** für `FATIGUE_MIN_PAIRS` (6)

**Etwa zwanzig Fahrten, und jede Quelle steht wieder.** Die übrigen achtunddreißig
sind Nachlauf. `FATIGUE_SOLID_MIN_RIDES = 10` betrifft nur den vollen
Darstellungsbereich, nicht die Messfähigkeit.

#### P9c · Es wird erst schlechter, bevor es besser wird

Maskieren nimmt zunächst Punkte weg: weniger Punkte je Stunde → weniger Bins →
`FATIGUE_MIN_BINS = 3` und die Nicht-Extrapolationsregel greifen häufiger → mehr
`p075: None`. Das wirkt weiter: `measured[].n` → `_band()` → `paired[].enough` →
`workouts.curve_watts()` bricht die Staffelung früher ab → **Grundlage und lange
Fahrt fallen eher auf die FTP zurück.**

**Das sagt die Kachel vorher, nicht die Überraschung nach dem Update.**

#### P9d · Die rollende FTP — beziffert, damit sie nicht wieder geschoben wird

`websocket._latest_ftp()` läuft `for field in ("icu_ftp", "icu_rolling_ftp")` und
nimmt den ersten Treffer. **Der rollende Wert liegt also bereits auf jeder
Aktivität und wird nur von der Reihenfolge verdeckt.** Das ist keine
Forschungsfrage: **eine Umsortierung plus eine Quellzeile**, die sagt, welcher
der beiden Werte gilt und warum.

Solange der Rückfall greift, hängt alles am Profilwert 200 W, während die
gemessene 20-Minuten-Leistung bei 192 und die rollende Schätzung bei 191–194
liegt — und der 20-%-Filter aus P0 erbt denselben Fehler. **Nicht Teil von P**,
damit P nicht daran hängenbleibt; aber beziffert, damit die nächste Sitzung es
nicht für ein großes Thema hält.

### P10 · Der Rückbau, ZULETZT — mit einer Auflage, die keine Option ist

Erst wenn P2 bis P6 tragen, und zwar **am lebenden System verifiziert**, nicht
nur grün. Was namentlich fällt:

| fällt | Verbraucher heute | was mitgeht |
|---|---|---|
| `blocks.family_of` | **einer**: `blocks._sessions` | die namensbasierten Fixtures in `test_blocks.py` (6 Stellen) |
| die Namensableitung in `_sessions` | — | ersetzt durch die Marken aus `section_marks` |
| `label == "WORK"` als Blockauswahl | `blocks._sessions` | WORK-Fixtures in `test_blocks`, `fixtures.py`, `panel_fixtures.js` |
| `derive.drop_warmup_blocks` (die Alpha-Blockauswahl) | `importer.async_import_dfa` | die Ausreisser-Fixture und die 0.49.1-Gegenprobe |
| `derive.above_endurance_share` **als Tor** | `fatigue_curve_reason`, `fatigue.rides` | die zugehörigen Zusicherungen |
| die Erklärtexte, die Ausschlüsse begründen | Panel `rFatigue`, `rBlocks` | die Zusicherungen in `test_panel_views` |

**DIE AUFLAGE — und sie ist keine Option:**

**`derive.fatigue_curve_reason` BLEIBT stehen, als Rückfall für UNMARKIERTE
Fahrten.**

Grund: `test_fatigue` prüft heute, dass strukturierte Einheiten VOR der Messung
ausgeschlossen werden — **mit der Gegenprobe, dass sie den Abfall von +4,0 auf
+42,0 W verfälschen, wenn man sie drinlässt.** Das ist der einzige vorhandene
Beleg dafür, dass L0 Runde 3 nicht wiederkommt: dort wurde aus einem
Trainingsplan „Ermüdung", weil ein Gütekriterium hinterher die Auswahl genau auf
die strukturierten Fahrten verengte und den Störer einsammelte statt ihn
auszuschließen.

**Die manuelle Zuordnung ersetzt diesen Schutz nur für Fahrten, die der Athlet
angefasst hat.** Für alle anderen — und das sind nach der Umstellung erst einmal
alle — bleibt der Ausschluss die einzige Sicherung. **Wer ihn mit `family_of`
zusammen entfernt, liefert den teuersten Fehler dieses Projekts erneut aus.**

Rangfolge: **erst die Markierung, dann der Ausschluss.** Eine markierte Fahrt
geht nicht mehr durch `fatigue_curve_reason`. (Was dabei mit dem VI-Tor und mit
`short` geschieht, steht in P4, Auflage 5.)

### P11 · Reihenfolge, Umfang, und was bewusst NICHT gebaut wird

**Reihenfolge:** P1 → P3 → P4 → P2 → P5 → P6 → P7/P8 → P10.
**Kein Algorithmus-Bump** — die maskierten Stunden leben im neuen Block mit
eigener Messmarke, der Bestand wird nicht neu gerechnet.
`ACTIVITY_FIELDS_VERSION` 2 → 3 in P7 — für `description` allein — ist kein
Algorithmus-Bump, sondern ein Nachladen der Summaries.

| Stufe | Umfang |
|---|---|
| P1 Einstellungsblock + Schalter | klein — vierte Wiederholung des Archivmusters, HA-frei prüfbar |
| P3 Archivblock, Anker, Drift, Schreibweg | mittel |
| P4 maskierte Stunden + fünf `dfa_hours`-Auflagen | **groß** — der einzige echte Rechenweg-Eingriff; berührt `derive`, `fatigue`, `workouts` und vier Zusicherungsgruppen |
| P2 Kachelreihe, Haken, Formen/Kürzel, Wegfall `_rampBlock` | mittel bis groß, hoher Prüfstandsanteil |
| P5 Spalte | klein, mit CSS-Anteil |
| P6 Herkunftsspur | mittel |
| P7 `description` holen, mit RPE und Gefühl anzeigen | klein |
| P8 Hinweise | klein |
| P10 Rückbau | mittel, fast vollständig Tests |

#### Streichung 1 · KEINE TASTENKÜRZEL — bewusst, mit dem Gegenargument

**Alles wird geklickt.** Das ist eine Entscheidung des Athleten vom 15.09.2026,
und sie steht **gegen** die Recherche, damit die nächste Sitzung sie nicht für
ein Versehen hält:

> Die Tastatur ist der einzige gemessene Hebel auf den Durchsatz, den die
> Recherche hergibt. ATLAS erreicht die niedrigste durchschnittliche Zeit je
> Aktion und ist schneller als ROSAnnotator und ELAN; die Autoren führen das
> ausdrücklich auf ein **tastaturzentriertes Design** zurück, das den
> Interaktionsaufwand senkt. CVAT begründet dasselbe aus der Praxis: Annotieren
> ist ermüdend, alles mit der Maus zu machen erschöpft schnell, deshalb nimmt
> CVAT Tastatureingaben und ist voll von Kürzeln.

**Warum trotzdem nicht:** bei rund zwanzig Fahrten (P9b) statt achtundfünfzig
fällt der Durchsatz kaum ins Gewicht, und Klicken ist eindeutiger. **Wer das
später nachbauen will, baut damit nichts kaputt** — aber er soll wissen, dass es
hier abgewogen und verworfen wurde.

#### Streichung 2 · KEINE WARTESCHLANGE, kein „nächste unbearbeitete"

**Der Athlet wählt die Fahrten selbst aus der Liste.** Die Aktivitätenliste
bleibt chronologisch, neueste zuerst, und bekommt nur die Markenspalte dazu
(P5).

Auch das steht gegen ein Rechercheergebnis, und auch das gehört notiert: für
Audio wurden Segmente in einen 2D-Raum abgebildet und in großen Mengen
beschriftet, indem Punktmengen in der Farbe eines Etiketts eingefärbt wurden —
bei der Sprachaktivitätserkennung ergab das deutliche Beschleunigungen gegenüber
der Annotation Stück für Stück; CVAT hat 2026 eigens Massenaktionen nachgerüstet.

**Warum trotzdem nicht:** das Verfahren passt nicht — es gibt hier keinen
sinnvollen 2D-Raum über Abschnitte —, und der wertvolle Teil des Befunds ist
ohnehin gerettet: **P9a nennt die fehlende Zahl je Familie.** Damit weiß der
Athlet, worauf er zuarbeitet, ohne dass ihn etwas führt. **Eine Warteschlange,
die nach dem Vorschlag der Automatik gefüllt wäre, hätte zusätzlich genau den
Ankerfall aus P1a erzeugt** — zwölfmal bestätigen und nichts entschieden.

#### Streichung 3 · KEINE TEMPERATUR — weder holen noch anzeigen

**Entscheidung des Athleten vom 15.09.2026, nachdem die Felder benannt waren.**
`average_temp`, `min_temp` und `max_temp` stehen im dokumentierten Datenmodell
von Intervals, `temp` ist ein dokumentierter Stromtyp, und das Markieren holt
die Ströme ohnehin live — **der Weg wäre also billig gewesen und wird trotzdem
nicht gegangen.** Kein Feld in `ACTIVITY_FIELDS`, kein Wert in der Kachel, kein
Wert je Abschnitt.

**Der Grund steht in P0a und ist derselbe, der das ganze Paket trägt:** ein
Temperaturwert schließt die Lücke nicht, weil Verpflegung, Schlaf und Wind
ohnehin fehlen. Eine Zahl, die nur einen von vier Einflüssen abbildet, lädt
dazu ein, den Rest für erklärt zu halten — und das ist die Fehlerklasse aus §7,
eine Größe unter einer Überschrift, die mehr verspricht als sie misst. **Wer
Bedingungen festhalten will, schreibt sie in die Notiz** (P7), wo sie als das
stehen, was sie sind: eine Auskunft des Athleten, keine Messung des Systems.

**Nicht vergessen, sondern abgewogen und verworfen.** Wer es später bauen will,
baut nichts kaputt — aber er soll wissen, dass es hier auf dem Tisch lag.

#### Was sonst nicht zu Paket P gehört

- **Die `[]`-Regel aus §10.** Der Zuschnitt nach Herkunft (632 Stellen) ist ein
  eigener Punkt und **ausdrücklich nicht Teil von P**. Er gehört gebaut, aber
  nicht hier — ein Auslieferungs-Release hängt nicht an einem Prüfstands-Umbau.
- **Die rollende FTP** (P9d) — beziffert, verwiesen, nicht gebaut.
- **Ein Korridor für `threshold`** — die Familie bekommt Haken, der Korridor
  gehört gemessen, sobald Daten da sind. Eine gesetzte Zahl wäre die
  Fehlerklasse, gegen die dieses ganze Paket gebaut wird.
- **Jede Form von Temperatur** — nicht vergessen, sondern gestrichen. Siehe
  P11, Streichung 3.

### Tests P

Nach der Regel aus §9: ein Test, der den alten Fehler nicht nachweislich findet,
ist keiner. Jede Gegenprobe wird **gezählt und benannt** fallen gesehen, und vor
jeder zurückgedrehten Zeile steht eine Zusicherung, dass die Ersetzung gegriffen
hat (achte Bauregel).

**Die Fixture muss zwei unterscheidbare Fälle tragen** (Lehre 2 aus Paket A).
Eine Zuordnungs-Fixture, in der jeder Abschnitt dieselbe Familie trägt, besteht
jede Prüfung und beweist nichts. Zwingend enthalten:

- eine Fahrt, bei der **mindestens ein Lap durch `dfa_blocks` fällt** — sonst
  ist der Unterschied zwischen laufender Nummer und `start_index` unsichtbar und
  der Fehler aus P3a besteht die Suite;
- ein Abschnitt mit **zwei** Familienmarken;
- eine **verschobene** Fahrt (Lap-Zahl geändert, `start_index` verschoben);
- eine Fahrt „Grundlage + SweetSpot am Ende", die heute als `structured` ganz
  fällt und markiert ihre zwei Stunden hergibt;
- eine Fahrt mit **einem** Lap (für den Hinweis aus P8);
- eine Fahrt mit `dfa: {}` im Archiv (gescheiterter Abruf, P2c).

Was beißen muss:

1. **`start_index` gegen laufende Nummer**, an der Fahrt mit dem gefallenen Lap:
   die Zuordnung über `n` trifft nachweislich den falschen Block.
2. **Die zwei J7-Auflagen einzeln**: Altbestand bekommt den Block aus
   `empty_data()`; die Migration normalisiert einen kaputten Block; **ein No-op
   löst keinen Speichervorgang aus** (eingefrorene Referenz).
3. **Die Rücknahme sitzt auf der einzelnen Marke** — eine von zwei Familien
   zurückgenommen, die andere steht; die letzte zurückgenommen, der Eintrag
   fällt ganz, und die Fahrt rechnet bit-identisch wie eine nie markierte.
4. **Die Messmarke**: älterer `v` verliert `hours`, behält Marken und Anker, und
   der Zustand ist in der Payload **sichtbar**.
5. **Die Drift meldet, statt zu rechnen**: verschobene Fahrt → `marks_stale`,
   und sie zieht **keinen** Median.
6. **Der Haken misst nicht.** Nach `set_section_marks` steht der Eintrag mit
   `hours: null` und einem Grund; erst „übernehmen" misst. Gegenprobe: ein
   impliziter Messpfad wird eingebaut und muss auffallen.
7. **Maskieren gegen neu basieren**, an „30 min Tempo, dann Grundlage": die
   maskierte Stunde 1 ist halb belegt und heißt Stunde 1; die neu basierte
   Fassung wird als Gegenprobe eingebaut und muss eine **andere** Zahl liefern —
   sonst unterscheidet die Fixture die beiden Wege nicht.
8. **`excluded` ist nicht `dropped`**: eine markierte Fahrt hat trotz großer
   Maskierung einen kleinen `dropped_share`.
9. **`occupancy_rising` feuert NICHT** auf einem sauberen, maskierten Bestand —
   **mit Gegenprobe, dass es bei echtem Auswahleffekt weiter feuert** (die
   vorhandene 8→16-Fixture bleibt).
10. **Der Anker nennt seine Stunde**, und ein auf Stunde 2 gerutschter Anker ist
    benannt statt still.
11. **Die Markierung schlägt `drop_warmup_blocks`**, und der Satz dazu steht in
    der Payload.
12. **Die drei DFA-Zustände** aus P2c einzeln, mit dem Knopf „nochmal holen" nur
    im mittleren Fall.
13. **`test_panel_design`**: sechs Familien, sechs Formen, sechs Kürzel, keine
    Urteilsfarbe, keine Form eine Variante einer anderen — mit eingebauter
    Dublette als Gegenprobe. Und: die alpha-Marken aus P8 liegen im
    Kategorienregister.
14. **`test_panel_fixes`**: der Haken am simulierten Zeigerereignis, und
    `scrollTop` überlebt das Re-Render (Lehre 3 aus Paket A; `_rtWrite` macht es
    vor). Dazu der Quelltext-Wächter: **keine Schwelle als Zahl im Frontend** —
    0,75 und 0,5 kommen aus der Payload.
15. **Vorschläge sind nicht vorangehakt.** Bei `suggestions: true` steht kein
    Haken im Archiv, bevor geklickt wurde — Gegenprobe: ein vorangehakter
    Vorschlag muss fallen.
16. **P10-Auflage als Zusicherung**: eine **unmarkierte** strukturierte Fahrt
    wird weiterhin ausgeschlossen, und die +4,0/+42,0-Gegenprobe bleibt in
    `test_fatigue` stehen.
17. **`test_projektstand`**: die §9-Tabelle wird nachgezogen, nicht der Zähler.
    Eine Zahl, die sich ändert, ohne dass jemand es wollte, ist ein Befund.

### Was der Bau von P an dieser Spezifikation korrigiert hat

**Nachgetragen ab 15.09.2026, während des Baus.** Vier Befunde am Code vor dem
ersten Handgriff, zwei Streichungen des Athleten daraufhin, und zwei Funde, die
erst beim Bauen entstanden sind. Alle gemeldet und einzeln freigegeben, nach
Lehre 1 aus Paket A: am Feld prüfen, nicht am Text.

#### Streichung 4 · KEINE VORSCHLÄGE — und damit entfällt P1 ganz

**Entscheidung des Athleten vom 15.09.2026.** Es gibt keine Automatik, die
vorschlägt; markiert wird alles selbst. Die Automatik wird in P10 **ersatzlos**
zurückgebaut und nicht in einen Vorschlagsmodus überführt.

**Damit fällt P1 vollständig weg, und das gehört hier hin, damit die nächste
Sitzung keinen Schritt sucht, den es nicht mehr gibt.** P1 bestand aus drei
Teilen: Archivblock `settings`, WebSocket-Paar `settings` / `set_setting`, und
ein Panel-Reiter, der jeden Schalter mit seiner Begründung zeigt. Der einzige
Schalter darin war `suggestions`. Fällt er, bleibt ein Archivblock ohne
Schlüssel, zwei Kommandos ohne Verbraucher und ein Reiter ohne Inhalt —
**Vorrat auf Verdacht**, und toter Code ist in diesem Projekt eine eigene
Fehlerklasse (§12, `ring()`/`rd`). Die Reihenfolge beginnt deshalb mit P3.

**Die Recherche zu Geisterhaken und Ankerwirkung bleibt in P1a stehen** — als
Begründung, warum es keine Vorschläge gibt, nicht als verworfene Option. Wer
sie später doch bauen will, soll den Zielkonflikt vor sich haben und nicht nur
das Ergebnis.

#### Streichung 5 · Der mittlere DFA-Zustand aus P2c — geprüft und verworfen

P2c wollte drei Zustände und für den mittleren einen Knopf „nochmal holen".
**Am Code trägt der mittlere Zustand nicht, aus zwei unabhängigen Gründen:**

1. **`{}` im Archiv entsteht auf ZWEI Wegen.** `async_import_dfa` schreibt es
   im `except` nach einem geplatzten Abruf — und ein zweites Mal am Ende über
   `data["dfa"][key] = summary or {}`, weil `dfa_summary` `None` liefert,
   sobald der Strom keine alpha-Werte trägt. Der zweite Weg ist nicht selten:
   `pending_dfa` filtert über `has_dfa()`, also über `stream_types`, und das
   ist §7 erster Fall — die Liste sagt, was in der hochgeladenen Datei lag,
   nicht was die Schnittstelle herausgibt. **Ein Knopf „nochmal holen" holt für
   diese Fahrten dasselbe Nichts, jedes Mal.**
2. **Die Detail-Payload kann die Unterscheidung ohnehin nicht liefern.**
   `websocket_activity` baut sie mit `summary = data["dfa"].get(id) or None` —
   das leere Dict kollabiert dort auf `None`. Im Panel ist „nie abgerufen" und
   „Abruf gescheitert" schon heute derselbe Zustand.

   **NACHTRAG 15.09.2026, beim Kommando-Audit zu 0.54.0: dieser Punkt nannte
   die falsche Funktion.** Das Panel ruft `intervals_icu/activity` **nie** —
   es baut die Detailansicht aus der Aktivitätenliste, und `a.dfa` kommt von
   dort. **Der Befund überlebt trotzdem, und zwar unverändert**, weil
   `importer.activity_list()` in Zeile 321 exakt dieselbe Zeile fährt:
   `merged["dfa"] = data["dfa"].get(key) or None`. Derselbe Kollaps, anderer
   Weg. Die Streichung bleibt also richtig, ihre **Begründung** stand auf
   einem Bauteil, das an dieser Stelle gar nicht beteiligt ist — und eine
   Begründung, die auf das falsche Bauteil zeigt, trägt beim nächsten Umbau
   in die falsche Richtung. Deshalb steht es hier, statt still korrigiert zu
   werden (§7, achte Klasse).

Und für Altbestände wäre die ehrliche Antwort ohnehin „warum es leer blieb,
steht nicht im Archiv". **Also zwei Zustände: „führt kein `dfa_a1`" und „hat
Daten".** Nicht vergessen, sondern geprüft und verworfen.

#### Der Anker wird beim ERSTEN Haken gesichert — und danach nicht mehr angefasst

**Beim Bauen gefunden, und die naive Fassung liegt näher.** Wer den Anker bei
jeder Marke neu aus den aktuellen Laps bildet, schreibt sauberen Code, der
genau das zerstört, wofür der Anker da ist: eine spätere Marke auf einer
inzwischen veränderten Fahrt **frischt den Vergleichsstand auf, und die Drift
verschwindet still.** Der Athlet hakt ein zweites Mal, und das System vergisst
dabei, dass die erste Marke nicht mehr sitzt.

Das ist die Klasse aus 0.49.2 — **wer einen Fix ausliefert, verliert damit die
Belege für die Prüfung, die den Fix gefunden hat** —, hier vor dem Bau
gefangen. Also: je Abschnitt einmal gesichert, und `sections` wächst nur um
neue Abschnitte. Die Lap-Zahl bleibt die des ersten Eintrags. Zugesichert in
`test_section_marks`.

#### `reanchor` ist streng — eine Bestätigung, die auf nichts zeigt, ist schlimmer als keine

Der Weg aus der Drift ist ein Knopf, kein Automatismus (P3b). Beim Bauen kam
die Frage dazu, was er tut, wenn ein markierter Abschnitt in den neuen Laps
gar nicht mehr vorkommt. **Er bestätigt dann NICHT**, sondern wirft mit Grund:
die Zuordnung ist neu zu setzen. Alles andere hieße, eine Marke auf einen
Abschnitt zeigen zu lassen, den es nicht gibt — und sie sähe danach aus wie
eine, die sitzt. Bestätigen löscht außerdem die `hours`, weil die Messung auf
dem alten Ausschnitt saß.

#### Die Rücknahme auf der einzelnen Marke ist belegt, nicht nur entschieden

P3d nannte „ein verbreitetes Annotationswerkzeug" ohne Namen. **Gemeint ist
Label Studio**, und die Kritik trifft genau diesen Punkt: seine Rücknahme
entfernt Ebenen, statt die tatsächlich zuletzt ausgeführte Aktion rückgängig zu
machen. Der Name steht hier, damit die Regel beim nächsten Umbau nicht zu
„einfach den letzten Zustand zurücksetzen" vereinfacht wird — **eine Rücknahme,
die etwas anderes zurücknimmt als das Getane, ist schlimmer als keine.**

#### Der Anker taugt NICHT zum Maskieren, und der Messweg braucht ZWEI Abrufe

P4 sagt „dieselbe Mechanik wie bei `set_ramp_test`: Ströme LIVE und
UNGEDÜNNT". **Das reicht nicht.** Maskieren heißt, Stromstellen auszuschließen,
und die Grenzen dafür sind `start_index` UND `end_index` der Laps — die stehen
nicht im Strom. `async_import_dfa` macht deshalb den zweiten Abruf
(`async_get_intervals`) und sagt dazu, warum; `set_ramp_test` braucht ihn nicht
und hat ihn nicht. Der Messweg der Zuordnung braucht ihn, samt eigenem
Fehlerpfad: Ströme da, Laps nicht.

**Und der Anker schließt die Lücke nicht.** Er hält `start_index` und die
DAUER, nicht das Ende. Wer daraus zu schneiden versucht, baut einen Ausschnitt
aus einer Bewegungszeit auf einer Stromachse — genau der Versatz aus §7
(114 Stellen bei der Einheit vom 01.09.2026). Der Anker ist für die
Drifterkennung da. Das steht jetzt auch im Kopf von `section_marks.py`, damit
es niemand aus dem Feldnamen erschließen muss.

#### Der Fehlerpfad beim Markieren: hier steht die Marke NICHT ohne Anker

`ramp_tests` Regel 2 lautet: keine stille Messung — die Markierung steht
trotzdem, aber mit dem Grund daneben. **Diese Regel ist hier NICHT übertragbar,
und der Unterschied ist genau zu benennen:** beim Stufentest fällt die MESSUNG
aus, und die Aussage „diese Fahrt war ein Stufentest" ist auch ohne sie
vollständig. Beim Markieren eines Abschnitts fiele das aus, was die Aussage
überhaupt erst BESTIMMT — ohne Laps gibt es weder einen geprüften Schlüssel
noch einen Anker. **Eine Marke ohne Anker ist eine, deren Drift nie auffallen
kann; sie gälte für immer als sitzend.** Der stille Ausstieg, eine Ebene tiefer.

Also: scheitert der Lap-Abruf beim Setzen, wird **nichts geschrieben**, und der
Grund steht an der Kachel. Drei Fälle, getrennt benannt: Abruf gescheitert ·
Intervals liefert für diese Fahrt keine Abschnitte · der Schlüssel ist keine
Abschnittsstelle.

**Die RÜCKNAHME läuft in allen drei Lagen durch.** Sie braucht weder Laps noch
Datum — geprüft wird beim Setzen, das Datum steht im Eintrag. Deshalb sind
`set_mark` und `unset_mark` getrennt: eine falsch gesetzte Marke ausgerechnet
dann nicht loswerden zu können, wenn die Schnittstelle klemmt, wäre der
ärgerlichste denkbare Zustand.

#### Die Regel über allem: WAS MARKIERT IST, ZÄHLT. WAS NICHT MARKIERT IST, NICHT

**Entscheidung des Athleten vom 15.09.2026, und sie hebt eine frühere Formulierung
auf.** P4 sprach davon, das VI-Tor für markierte Fahrten zu umgehen. Das ist zu
wenig und auch falsch gedacht: **die Filter werden nicht umgangen, sie fallen.**

Kein Filter, keine Prüfung, keine Heuristik entscheidet mehr mit. Ein Filter
weiß nicht, wie warm es war oder ob der Athlet verpflegt war — der Athlet weiß
es. Wer eine Fahrt nicht gewertet haben will, markiert sie nicht. **Und es gibt
auch keinen Hinweis darauf, was ein Filter gesagt hätte** — den gibt es dann
nicht mehr.

Betroffen sind alle drei Tore in `derive.fatigue_curve_reason` (`short`,
`structured`, `variable`), nicht nur `variable`. Der Anlass war eine echte
Fahrt: die vom 04.09.2026 hat drei Abschnitte, die beiden Grundlagenteile sind
markiert, der WORK-Teil in der Mitte bewusst nicht. Genau richtig markiert — und
`structured` hätte sie ausgeschlossen, **bevor** irgendetwas gemessen wird, weil
es den Z2-plus-Anteil der GANZEN Fahrt liest. Ein Tor, das die Handauswahl
überstimmt, ist die Automatik durch die Hintertür.

`rides()["dropped"]` behält seine Bauart und wechselt die Bedeutung: statt
„vom Filter ausgeschlossen" trägt es künftig „markiert, noch nicht gemessen"
und „Abschnitte in Intervals verschoben". Dieselbe Liste, ehrlichere Gründe.

#### Der Einstellungs-Reiter kommt zurück — jetzt mit einem Zweck

P1 entfiel mit der Vorschlags-Streichung, weil ein Archivblock ohne Schlüssel
Vorrat auf Verdacht gewesen wäre. **Mit dem Umschalten hat er einen Zweck** und
kommt zurück: dort wird die automatische Erkennung abgeschaltet. Solange sie an
ist, läuft alles wie heute; ist sie aus, zählen nur die Markierungen. Damit hat
der Athlet den Übergang in der Hand — erst in Ruhe sammeln, dann umlegen.

**Er gehört nach B2, nicht nach B1:** erst die Messung sehen, dann umschalten.

**ZWEI Schalter, nicht einer, und die Trennlinie läuft entlang der MESSWEGE:**

1. *Blockfamilien* (VO2max, SweetSpot, Tempo, Schwelle) → speisen
   `blocks.series` und darüber `workouts.SOURCE_CHAIN`.
2. *Ermüdungskurve* (Grundlage, lange Fahrt) → speist `fatigue.curve`.

Der Grund ist nicht Geschmack, sondern die Reifezeit: drei markierte Einheiten
je Blockfamilie sind in zwei Wochen beisammen, acht lange Fahrten dauern
Monate. Ein einziger Schalter zwänge dazu, entweder auf den langsameren zu
warten oder die Kurve zu früh umzustellen.

**Drei oder mehr Schalter wären falsch**, und zwar nach derselben Regel, die
0.46.0 gekostet hat: Schalter dürfen sich nicht kreuzen. Die beiden oben haben
getrennte Verbraucher und überschneiden sich nirgends — alle vier Zustände sind
sinnvoll. Ein dritter Schalter etwa für die Familienerkennung aus dem Namen
träfe denselben Verbraucher wie Schalter 1; man könnte ihn so stellen, dass eine
markierte Fahrt trotzdem nicht zählt, und suchte dann den Fehler an der falschen
Stelle.

**Der Stufentest bleibt von beiden unberührt** — er ist seit 0.51.1 Handarbeit
und hat mit der Erkennung nichts zu tun. Das ist kein dritter Schalter, nur eine
Klarstellung.

**Jeder Schalter sagt, was er bewirkt, und nennt seinen Stand**, nicht bloß
an/aus: „Aus — nur deine Markierungen zählen. Derzeit: 12 markierte Fahrten."

#### Der Rest-Stellvertreter bei der Drift — benannt, nicht versteckt

`fatigue.rides()` ist eine reine Archivfunktion ohne Netzzugang und hat die
Runden nicht; `section_marks.usable_hours` braucht sie aber, um den Anker zu
vergleichen. Für dreihundert Fahrten wären das dreihundert Abrufe.

**Also wird die Drift dort geprüft, wo die Runden ohnehin vorliegen:** beim
Messen und beim Öffnen der Fahrt. Ein Eintrag mit `hours` ist damit driftfrei
**zum Messzeitpunkt** — das ist der Stellvertreter, und er steht hier, damit
niemand ihn für eine Zusicherung hält.

**Entschärft wird er so:** wird eine gedriftete Fahrt geöffnet, werden ihre
`hours` gelöscht. Sie fällt aus der Kurve, sobald man sie ansieht, statt erst
wenn man reagiert. Der Rest — zwischen dem Umbau in Intervals und dem nächsten
Öffnen rechnet die Kurve mit den alten Zahlen — bleibt und ist hiermit benannt.

#### `short` fällt ganz weg, statt auf die markierte Dauer umgestellt zu werden

P4 Auflage 5 wollte `short` für markierte Fahrten neu rechnen. **Das ist falsch
herum.** Die Achse der Ermüdungskurve ist die FAHRTZEIT — `dfa_hours` bildet die
Stunden über die Stromposition. Eine fünfstündige Fahrt mit vierzig markierten
Minuten in Stunde fünf ist für die Kurve wertvoll, weil sie einen Punkt in
Stunde fünf liefert. Auf die markierte Dauer gerechnet, flöge genau dieser Fall
raus. Was zu wenige Punkte hat, regelt die Nicht-Extrapolation von selbst:
`p075` bleibt `None`, und die Stunde trägt nichts bei.

#### Maskieren heißt VERWERFEN, nicht ZUSAMMENSCHIEBEN

Die naheliegende Abkürzung wäre, die markierten Punkte aneinanderzureihen.
Dann wäre „Stunde 2" die zweite Stunde der MARKIERTEN TEILE statt die zweite
Stunde der Fahrt — und die Ermüdungsfrage, wie weit man in der Fahrt ist, wäre
falsch beantwortet. **Die Achse bleibt, die Punkte fallen weg.** Genau daher
kommt die Verschlechterung aus P9c.

#### B ist geteilt: B1 misst, B2 rechnet damit

**Entschieden vor dem Bau.** B1: der Übernehmen-Knopf, der Messweg mit zwei
Abrufen, die Maskierung in `dfa_hours`, `set_measurement`. Die Fahrt bekommt
ihre maskierten Stunden und zeigt sie — die Kurve nutzt sie noch nicht. B2: die
Kurve schaltet um, die Tore fallen, `occupancy_rising` zählt angebotene Stunden,
dazu der Einstellungs-Reiter, die P9c-Ansage und die Zeile „noch eine Einheit,
dann misst SweetSpot".

Der Schnitt ist nicht nur Umfang: **so sind die maskierten Zahlen zu sehen,
bevor die Kurve darauf umschaltet.** P9c wird damit ablesbar statt vorhergesagt,
und der B2-Release kann sagen, was sich an den ZAHLEN DES ATHLETEN verschiebt,
statt es allgemein zu behaupten.

#### Der Übernehmen-Knopf, und was nach einer Änderung passiert

Er misst NUR, was markiert ist. Er hakt nichts an, schlägt nichts vor, ergänzt
nichts. Grün bei Erfolg, sonst der Grund im Klartext mit den drei Fällen aus dem
Schreibweg.

**Ändert sich die Auswahl nach dem Messen, wird der Knopf wieder aktiv und die
Kachel sagt, dass die Messung veraltet ist.** Der Mechanismus steht schon:
`set_mark` und `unset_mark` setzen `hours` bei jeder Änderung auf `None`. Was
fehlt, ist die UNTERSCHEIDUNG — „Auswahl geändert, neu zu messen" ist eine
andere Aussage als „noch nicht gemessen", und wer schon einmal gemessen hat,
soll die erste lesen. Das braucht ein Feld im Eintrag, keinen neuen Weg.

#### P8 ist nicht frontend-only — das dritte Mal

Die Auflage lautet, 0,75 und 0,5 kämen aus der Payload (fünfte Bauregel).
**Sie stehen in keiner Aktivitätsdetail-Payload:** `DFA_AEROBIC` und
`DFA_ANAEROBIC` sind Modulkonstanten in `derive.py` und `coach.py` und reisen
nirgends mit. Im Panel stehen sie als nackte Zahlen in `_streamPanels`, und der
Dublettenwächter in `test_panel_fixes` friert genau diese zwei auf
`dfa.length === 2` ein. **Wer die alpha-Marken naiv baut, hebt die Zahl und
reißt einen Wächter, der zu Recht anschlägt.** Also eine Backend-Zeile, wie bei
P6 — und nach A5 und H das dritte Mal, dass „berührt nur das Frontend" am Code
nicht trägt. Beim Bau von P8 gehört das in §7.

#### Der Stufentest misst beim Klick, die sechs anderen nicht

P2 stellt sieben Kacheln nebeneinander und lässt `set_ramp_test` unverändert.
Damit stehen sieben gleich aussehende Bedienelemente da, von denen **eines
sofort Ströme holt und misst**, während die sechs anderen nur haken (P2b). Der
Fehler aus 0.46.0 war zwei Orte für eine Frage; das hier ist ein Ort mit zwei
Verhalten.

**Entschieden am 15.09.2026: ein deutlicher Hinweis an der Stufentest-Kachel,
kein Umbau.** Der Weg trägt seit 0.51.1 live; ihn für einen Gleichklang
anzufassen wäre Risiko ohne Gewinn. Der Hinweis ist aber Pflicht, nicht
Zierrat.

#### Die Reihenfolge ist umgedreht: P3 → P2 → P4

P11 setzte P4 vor P2. **Dagegen steht die eigene Auflage aus P10: verifiziert
wird am lebenden System.** Eine Maskierungsrechnung ohne Bedienung ist nur
gegen Fixtures prüfbar — es gäbe keinen einzigen echten Haken, gegen den man
messen könnte. P2 ohne P4 ist dagegen widerspruchsfrei baubar, und zwar genau
so, wie P2b es ohnehin verlangt: haken, Eintrag mit `hours: null` und Grund,
Knopf „übernehmen und messen" kommt mit P4. Dazu praktisch: die rund zwanzig
Fahrten aus P9b sind Handarbeit und brauchen Zeit, die sonst ungenutzt
verstreicht.

**Vier Auslieferungen:** A = P3 + P2 (ungemessen) · B = P4 · C = P5, P6, P7, P8 ·
D = P10.

#### Die Mobilfrage aus P5 ist OFFEN, nicht entschieden

P5 sagt, die mobile Ausblendliste sei nachzuziehen. In der Konsequenz hieße das:
die Markenspalte ist auf dem Telefon unsichtbar, und damit ist die Aussage
„noch nicht angefasst" dort nicht zu haben. **Das ist eine Entscheidung, keine
CSS-Kleinigkeit, und sie wird beim Bau von P5 getroffen, nicht vorweg.** P5
baut die Spalte für den Rechner.

#### Zwei Familien fallen aus der Markierungsreihe — mit dem Grund, nicht nur der Entscheidung

**Entscheidung des Athleten vom 15.09.2026, am Code nachgeprüft.** Markiert
werden nur noch **VO2max · SweetSpot · Tempo · Grundlage**, dazu der Stufentest
als ganze Fahrt.

- **`long` rechnet mit `endurance` identisch.** Beide tragen in
  `workouts.SOURCE_CHAIN` dieselbe Kette (`curve`, `ramp_hrvt1`, `ftp`; seit 0.60.0 `curve`, `ftp`) und
  stehen beide in `CURVE_FAMILIES`. Und die Kurve misst **je Fahrtstunde**:
  eine Achtstundenfahrt liefert acht Punkte, eine Zweistundenfahrt zwei — sie
  ordnet sich von selbst ein und braucht kein Etikett. Eine Grenze „ab wann ist
  lang" wäre für einen Anfänger mit zwei Stunden und einen Trainierten mit acht
  verschieden, und niemand könnte sie prüfen. **Zwei Familien mit identischer
  Rechnung sind zwei Namen für eine Sache.**
- **`threshold` kommt in `blocks.py` und `BLOCK_CORRIDORS` überhaupt nicht
  vor**: keine Blockmessung, kein Zielkorridor. Ihr Wert kommt allein aus dem
  Stufentest — ein Haken dort ändert nichts. **Ein Bedienelement ohne Wirkung
  ist schlimmer als keines**, und es war zugleich die Wurzel des
  dreiundzwanzigsten §7-Falls: `FAM_BLOCKS` musste für sie zwei Bedeutungen
  tragen.

**Im Trainer bleibt die Unterscheidung unberührt** — dort entscheidet `long`,
welche Einheit vorgeschlagen und wie der Zustand bewertet wird. `CURVE_FAMILIES`
wird nicht angefasst. Stillgelegt ist nur das MARKIEREN.

**Die Migration sagt, was sie wegwirft.** Die Leseschleife läuft über
`FAMILIES`; eine Alt-Marke fiele damit still, und der Eintrag sähe aus, als
hätte dort nie jemand gehakt. Sie wird deshalb benannt und steht an der Kachel.
Die **eine** Lage, in der der Hinweis nicht ankommt: trug eine Fahrt NUR
stillgelegte Familien, fällt der ganze Eintrag (P3d, ein Rumpf ist kein
Eintrag). Am Bestand vom 15.09.2026 sind das null Fahrten (Schwelle 0, lange
Fahrt 0, am System gelesen) — die Grenze steht hier, damit sie niemand für eine
Zusicherung hält.

#### Die Schwellen-Kachel im Trainer: nach B2, und warum nicht früher

`coach.anchors()` nimmt heute den Median der letzten fünf DFA-Ablesungen über
ALLE Fahrten. Das widerspricht der Regel über allem — eine bei 30 Grad
verfälschte Fahrt verfälscht auch die Schwellenzahl. Die Kette soll dieselbe
werden wie überall: **markierte Fahrten → Stufentest → FTP.**

**Nicht in B1, und der Grund steht am Code, nicht am Umfang.** `anchors()` liest
`derive.threshold_verdict(summary)` — die **Ganzfahrt-Ablesung** aus dem Archiv,
nicht die maskierten Stunden. Ein Filter „nur markierte Fahrten" nähme von der
Fahrt vom 04.09.2026 weiterhin den WORK-Teil in der Mitte mit, den der Athlet
bewusst NICHT markiert hat. **Ein Filter, der Fahrten filtert statt Abschnitte,
wäre ein halber Umbau, der aussieht wie ein ganzer** — und die Halbheit wäre
danach unsichtbar, weil die Zahl plausibel bleibt. Die ehrliche Fassung liest
die maskierte Messung, und die gibt es erst, wenn B1 gelaufen ist. Dazu kommt
der Rückfall mit sichtbarer Beschriftung plus „noch N Fahrten" — das ist das
B2-Muster.

**Am Bestand gerechnet, bevor es gebaut wird (15.09.2026):** die heutigen fünf
tragenden Ablesungen (27.08. bis 13.09.) gehören **alle fünf** zu markierten
Fahrten. Der Anker steht mit und ohne Filter bei **160 bpm / 146 W** — der
Umbau bewegt heute nichts, und deshalb bewegt sich auch am Pulsfenster der
Einheiten und an der FTP-Konfliktwarnung nichts. **Das ist ein Zufall des
Zeitpunkts und keine Zusicherung:** die einzige nicht markierte Fahrt im Fenster
ist die VO2max-Einheit vom 02.08. mit 168,1 W — läge sie unter den letzten
fünf, zöge sie den Leistungsanker nach oben. Genau dagegen ist der Filter
gebaut.

#### B2b-2 · Der Blockschalter — Simulation, Klarstellung, Sperre (16.09.2026)

**Die Simulation, am Bestand vor dem Bau gemeldet** (live `blocks` gegen die
markierten, gemessenen Blöcke aus `section_marks`, mit den Funktionen des Repos):

| | heute (Namenserkennung) | umgelegt (Markierungen) |
|---|---|---|
| VO2max Vorgabe · Einheiten · Pulsfenster | 250 W · 15 · 172–186 | 250 W · **6** · **176–186** |
| SweetSpot Vorgabe · Einheiten · Pulsfenster | 196 W · 10 · 155–174 | 196 W · **4** · **159–173** |
| Tempo Vorgabe | 160 W aus der FTP | unverändert — `SOURCE_CHAIN` hat für Tempo keine Blockstufe |
| Trendbalken (braucht 6) | VO2max ja, SweetSpot ja | VO2max **genau auf der Grenze**, SweetSpot **fort** |
| Einheiten außerhalb ihres Korridors | VO2max **7 von 15**, SweetSpot **7 von 10** | VO2max **0 von 6**, SweetSpot **2 von 4** |
| Streuung der Einheitsmediane (Regelkreis) | VO2max 0,086 · SweetSpot 0,194 | VO2max **0,039** · SweetSpot **0,028** |

**Das ist der beste Beleg für das ganze Paket:** die Handauswahl räumt auf. Von
fünfzehn namenserkannten VO2max-Einheiten lagen sieben über ihrem Korridor,
von den sechs markierten keine; der Regelkreis rechnet danach auf einer
Streuung, die halb bis ein Siebtel so groß ist. Die Vorgaben bewegen sich
nicht, weil sie an der jeweils letzten Einheit hängen, und die ist in beiden
Auswahlen dieselbe. **Die engeren Pulsfenster sind keine Korrektur, sondern
die Folge der kleineren Zahl** — die Breite kommt aus der Streuung zwischen
den Einheiten. Der Satz beim Umlegen sagt das.

Die zwei SweetSpot-Blöcke außerhalb (05.08. 0,809 · 24.08. 0,869) heben ihre
Einheit knapp über den Korridor, und der 24.08. ist die letzte: **der
+5-%-Vorschlag hängt allein am ersten 20-Minuten-Block** — in beiden
Stellungen. Nicht Teil des Schalters, aber festgehalten.

**KLARSTELLUNG ZUR AUFLAGE „keine Kachel mit zwei Zahlen aus zwei Quellen"
(Johannes, 16.09.2026).** Gemeint war: keine EINE Zahl aus zwei Quellen, und
keine Zwischenstufe, in der dieselbe Größe zweimal verschieden dasteht. Der
Stufentest hat von Natur aus zwei Zahlen aus zwei Ketten — der Start aus der
Grundlage, das Ende aus der Blockmessung, so entworfen. **Zwei Zahlen mit zwei
Quellen sind kein Widerspruch, solange beide beschriftet sind.** Seit zwei
Schaltern gehört zur Beschriftung auch die AUSWAHL: in gemischten Stellungen
(bei Johannes seit dem Kurvenschalter „Marken / Namenserkennung") steht an
jeder Zahl, ob sie aus seinen Markierungen oder aus der Namenserkennung kommt.
Dasselbe in der 40-Watt-Frage, die zwei Zahlen aus zwei Ketten gegeneinander
hält. Die Auflage ist damit nicht weiter zu dehnen.

**Die Auswahl steht NEBEN `SOURCE_LABEL`, nicht darin.** `SOURCE_LABEL` ist
nach dem Messweg verschlüsselt; dieselbe Kurve kann aus beiden Auswahlen kommen.
Dort hineingeschrieben bräuchte es je Messweg zwei Schlüssel mit doppeltem Text.
`section_marks.selection()` liefert Stellung und Etikett an einer Stelle; Kurve
und Blockreihe tragen sie in ihrer Payload, `ramp_protocol` hängt sie an
`start_source`/`end_source`.

**DIE SPERRE FÄLLT.** Ihr erster Grund (die Kurve steuere das Pulsfenster der
Blockfamilien) war am Code widerlegt, ihr zweiter („noch nicht gebaut") ist mit
dem Bau erledigt. Einen dritten gibt es nicht: die einzige Kopplung beider
Schalter sind Karten mit je einer Zahl aus beiden Ketten, und deren Mischung
entsteht schon mit dem Kurvenschalter allein. **Eine Sperre, die den Zustand
nicht verhindert, gegen den sie gebaut wäre, ist Theater.** Die Karten nennen
stattdessen je Zahl ihre Auswahl.

#### B2b-3 · Vorrechnung vor dem Bau (16.09.2026) — NICHT gebaut, Entscheidung offen

**Der Anker heute:** Median der letzten fünf GANZFAHRT-Ablesungen (27.08., 30.08.,
01.09., 04.09., 13.09.) = **160 bpm / 146 W**. Die Aussage vom 15.09. („der Umbau
bewegt nichts") galt für einen Filter „irgendeine Marke"; gekoppelt an den
Kurvenschalter zählen nur Grundlagen-Marken, und 01.09. (VO2max) und 13.09.
(Tempo) fallen heraus.

| Lesart | Anker | Tempo | Schwelle | Regeneration |
|---|---|---|---|---|
| heute, Ganzfahrt, alle | 160 / 146 | 155–163 | 166–178 | 115–131 |
| F · Ganzfahrt, nur Grundlagen-Fahrten | 155 / 152 | 150–158 | 161–172 | 112–127 |
| M1 · maskiert, Stunde 1 | 148 / 137 | 144–151 | 154–165 | 107–122 |
| M2 · maskiert, Median der Stunden | 149 / 135 | 144–152 | 155–165 | 107–122 |

F ist die verworfene Halbheit (nimmt Arbeitsteile markierter Fahrten mit).
**Drei** Familien hängen am Anker, nicht zwei: Regeneration auch. Die
Grundlagen-Watt bewegen sich nicht.

**Die Gegenrechnung Methode gegen Auswahl** an den acht Fahrten mit beiden
Ablesungen (Ganzfahrt-Regression gegen maskierten Stundenmedian):

| | n | HR, Median der Differenz | Watt |
|---|---|---|---|
| Marke = ganze Fahrt (nur **Methode**: 03.08., 27.08., 12.08.) | 3 | **−2,5 bpm** (−3,0 … −0,5) | uneinheitlich (−17,4 … +0,8) |
| Marke ≠ ganze Fahrt (**Methode + Auswahl**) | 5 | **−10,1 bpm** (−15,2 … +0,5) | −32,5 W (−45 … +2,5) |

Zerlegt am Anker: 160 → 148 bpm sind rund **−9 bis −10 aus der Auswahl** (−5 durch
den Wegfall der VO2max- und Tempo-Fahrt, der Rest durch ausmaskierte
Arbeitsteile) und rund **−2,5 aus der Methode**. **Beim Puls überwiegt die
Auswahl klar — aber der Methodenanteil steht auf drei Fahrten**, und bei der
Leistung ist er nicht zu trennen (eine der drei weicht um 17 W ab).

**Die Literatur, nachgesehen.** Rogers 2021a (Laufband) bestimmte die Schwelle an einer
STUFENRAMPE: lineare Regression über den fast linearen Abfall von alpha,
abgelesen bei 0,75; verglichen wurde mit Gasaustausch (VT1) auf dem Laufband.
Andriolo, Rummel und Gronwald (Sensors 2024) werteten Leistung gegen DFA a1 aus
ALLTAGSFAHRTEN aus — darauf beruht die Repräsentantenmethode dieses Projekts.
**Beide Lesarten dieses Systems sind Übertragungen:** die Ganzfahrt-Regression
wendet die Rampenmethode auf Fahrten ohne Rampe an, wovor Praktiker ausdrücklich
warnen; die Stundenwerte folgen Andriolos Alltagsansatz. **Einen Vergleich
beider Verfahren an denselben Fahrten gibt es in dem, was nachzusehen war,
nicht** — die Wahl ist eine SETZUNG und wird so beschriftet. Für die Stunde als
Zeitraum spricht, dass DFA a1 bei gleicher Belastung mit der Dauer driftet
(Gronwald u. a. 2024, konstante Läufe): „ausgeruht" ist Stunde 1 näher als ein
Median über alle Stunden.

**Und ein Befund, der gegen jede der drei neuen Zahlen spricht:** die markierten
Tempo-Blöcke liegen bei alpha 0,87–0,92 und Puls 161–167 — also OBERHALB von
0,75 bei höherem Puls, als der maskierte Anker für alpha 0,75 angibt (148). Die
Tempo-Blöcke sind Rolle (VirtualRide), die Grundlagen-Fahrten draußen. Dieselbe
Grenze, die an jeder Blockkarte steht („gemessen auf der Rolle"): **ein Anker aus
Fahrten draußen legt ein Pulsfenster für Rolleneinheiten fest.** Ein Tempo-Fenster
von 144–151 wäre auf der Rolle nicht zu treffen, ohne unter der Tempo-Intensität
zu bleiben. Das gehört entschieden, bevor umgestellt wird.

### Was die Prüfung dieser Spezifikation ergeben hat

**Sieben Korrekturen, alle VOR dem Schreiben gemeldet und einzeln freigegeben** —
nach Lehre 1 aus Paket A: am Feld prüfen, nicht am Text.

1. **„Positionsnummern im Strom" war zweideutig.** Es gibt zwei
   Abschnittslisten, sie sind nicht deckungsgleich, und die laufende Nummer aus
   der Panel-Rundenliste trifft im Archiv einen anderen Block. Der Schlüssel ist
   `start_index` (P3a).
2. **Die Farbauflage trug am Code nicht.** `ROLE` belegt das Kategorienregister
   in genau dieser Ansicht bereits vollständig, und das Register hat sieben
   Farben, nicht fünf (P2a).
3. **`endurance`/`long` als Fahrt-Schalter trug nicht** — eine Grundlagenfahrt
   mit angehängtem SweetSpot-Block braucht Abschnitts-Haken. Und die Korrektur
   an der Korrektur: **maskieren, nicht neu basieren** (P4).
4. **P6 war nicht frontend-only.** `blocks.series()` lässt `activity_id` fallen.
5. **„Messung beim Verlassen" hat keinen verlässlichen Haken** — vier Ausgänge,
   keiner über den Close-Handler (P2b).
6. **Die Marke beim „Alpha-Einbruch" wäre selbst eine Erkennung gewesen.**
   Ersetzt durch die zwei vorhandenen, belegten Schwellen (P8).
7. **Ein eigenes Notizfeld wäre der zweite Ort für dieselbe Frage.** Ersetzt
   durch Intervals' eigene Felder (P7).

**Dazu sechs Befunde, die die Spezifikation nicht kannte:**
`drop_outdated_dfa` löscht bei einem Bump die Anker mit (P3b) ·
`occupancy_rising` würde auf sauberen Daten feuern (P4) · der 20-%-Filter erbt
die bestrittene FTP (P0) · die rollende FTP ist eine Umsortierung, keine
Forschungsfrage (P9d) · ein einmal gescheiterter Stromabruf bliebe für immer
„ohne DFA-Daten" (P2c) · es sind rund zwanzig Fahrten, nicht achtundfünfzig
(P9b).

**Und zwei Quellenkorrekturen, beide der achten §7-Klasse:** die 2008er Arbeit
zur Umgebungstemperatur ist **Lafrenz** als Erstautor, nicht Wingo, und ihr
Befund ist ein **Unterschied** zwischen 35 °C und 22 °C, nicht „in der Kälte
passiert nichts". Clark 2019 erhielt **CP, nicht W′**, und die Vorbelastung war
**schwer-intensiv**, nicht moderat (P0a).
