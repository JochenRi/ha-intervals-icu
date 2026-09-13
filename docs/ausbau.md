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
