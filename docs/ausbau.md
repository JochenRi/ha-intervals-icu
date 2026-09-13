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

### F1 · Was die Kachel rechnet (aus `coach.durability`, nachgelesen)

Ruhige Einheiten ab 45 Minuten, Intervalleinheiten ab `icu_intensity` 80
ausgeschlossen, mindestens 8 Einheiten insgesamt. Geteilt bei 90 Minuten, je
Gruppe der **Median der Entkopplung**. Das Urteil vergleicht gegen
`DECOUPLING_GOOD = 5.0` (Friel).

### F2 · Was fehlt

- **Die Einheit fehlt.** Dass 0,9 % eine *Entkopplung* ist, steht nirgends auf
  der Karte.
- **Die Bezugsmarke fehlt.** Bis 5 % gilt als unauffällig — ohne diese Zahl
  sagt „0,9 %" nichts. Sie steckt heute nur im Quelltext, nicht in der Payload.
- **`n` je Gruppe fehlt.** 81 ist die Gesamtzahl, nicht die Aufteilung. Wie
  viele Einheiten über 90 Minuten liegen, ist unsichtbar — und genau davon
  hängt ab, ob die rechte Zahl belastbar ist.
- **Keine Leitzahl.** Drei gleich große Zahlen, keine beantwortet die Frage der
  Überschrift.
- **Kein Rechenweg.** Der aufklappbare Block nennt Quelle und Grenze, aber
  nicht, wie die Zahlen zustande kommen.

### F3 · Was daraus wird

- **Leitzahl oben:** die Antwort auf die Überschrift — hält die Entkopplung mit
  der Dauer, und um wie viele Prozentpunkte sie sich zwischen den Gruppen
  unterscheidet. Die beiden Gruppenwerte werden Beleg, nicht Hauptsache.
- **Die 5-%-Marke sichtbar:** zwei kleine Balken gegen dieselbe Skala, die Marke
  als Linie. Dann ist der Gruppenvergleich eine Längendifferenz statt
  Kopfrechnen, und der Abstand zur Marke steht ohne Erklärung da.
- **`n` je Gruppe** neben jedem Wert. Unter 5 Einheiten in einer Gruppe wird die
  Zahl **nicht behauptet**, sondern als zu dünn ausgewiesen — dasselbe Muster
  wie die hohlen Punkte im DFA-Reiter.
- **„Mehr anzeigen" mit dem Rechenweg**, in der Bauart des Budget-Bullet-Graphen:
  welche Einheiten zählen (ab 45 min, Intensität unter 80), warum bei 90 Minuten
  geteilt wird, dass es **Mediane** sind und keine Mittelwerte, und was
  Entkopplung überhaupt ist — die Herzfrequenz driftet nach oben, während die
  Leistung gleich bleibt.
- **Die Grenze nach vorn:** Entkopplung ist nur auf gleichmäßigen Einheiten
  aussagekräftig. Steht heute im Quellenblock, gehört aber sichtbar dorthin, wo
  sie erklärt, warum manche Fahrten gar nicht mitzählen.

### F4 · Backend

`durability()` liefert zusätzlich: `n_short`, `n_long`, die Schwelle
(`DECOUPLING_GOOD`, nicht im Frontend hartkodieren — sonst stehen zwei Wahrheiten
im Haus) und den Unterschied zwischen den Gruppen. Additiv, keine bestehende
Zusicherung ändert sich.

### Tests F

- `n_short + n_long == n`, und beide werden in der Payload geführt.
- Eine Gruppe mit weniger als 5 Einheiten wird als dünn ausgewiesen, ihr Wert
  nicht als Aussage gezeichnet.
- Die Schwelle im Panel stammt aus der Payload, nicht aus einer eigenen
  Konstante — Quelltext-Wächter dagegen.
- Gegenproben: Schwelle im Frontend hartkodieren, `n` je Gruppe weglassen,
  dünne Gruppe trotzdem behaupten — jede Mutation muss gezählt und benannt
  melden.

---

## Reihenfolge und Modellwahl

| Session | Paket | Warum |
|---|---|---|
| S2 | A | eng spezifiziert, viele kleine Eingriffe im Panel, kein Backend |
| S3 | B | Archivschema, Migration, dieselbe Regel an mehreren Orten — das schwerste |
| S4 | C | Mathematik und Formulierung, klein |

A und C lassen sich zusammenlegen, wenn A glatt läuft. Entschieden wird das am
Ende von S2 nach Kontextstand, nicht vorher.
