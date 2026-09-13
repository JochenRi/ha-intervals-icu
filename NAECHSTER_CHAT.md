# Anweisung für den nächsten Chat — Stand 0.44.0

**Kontext:** ha-intervals-icu, Stand **0.44.0** (ausgeliefert, Refs verifiziert —
**noch nicht am System verifiziert**, siehe Teil C). Hintergründe:
PROJEKTSTAND.md §7 (Fehlerkapitel, jetzt mit 0.44.0-Abschnitt), §9 (Prüfstand,
jetzt sechzehn Dateien), §11 (Auslieferungsweg), §12 (Audit-Hauptbuch).

---

## Teil A — was in dieser Session passiert ist

### A1 · Paket K Stufe 1 gebaut und als 0.44.0 ausgeliefert

Das Durability-Protokoll als Einheit. **K1 und K2 sind gebaut, K3 (die Hantel)
bewusst nicht** — sie braucht zwei Messungen, vorher gäbe es nichts zu zeichnen.

Was dazukam:

- **`durability_tests.py`** (neu, HA-frei): der Archivblock aus J7. Markieren,
  Zurücknehmen, Migration, Anker, Paare. Keine automatische Erkennung, keine
  automatische Paarung, Markierung rücknehmbar.
- **`derive.best_mean_watts()` / `test_measures()`**: die J1-Maschine auf einer
  Bewegungszeit-Achse. Lücken über 60 s brechen das Fenster, das Mittel ist
  dauergewichtet, ein Fenster länger als die Fahrt gibt **None** statt des Werts
  eines kürzeren.
- **`workouts.py`**: `durability_test_fresh` als Katalogeintrag,
  `durability_test_fatigued` **abgeleitet** über `fatigued_session()`, eigene
  Familie, nur bei grünem Zustand, mit eigener Begründung (Messfehler, kein
  Sicherheitshinweis). `protocol_load()` rechnet die Last aus den Abschnitten.
- **`websocket.py`**: `set_durability_test` (holt ungedünnte Ströme, misst,
  schreibt) und `durability_tests`. 26 Kommandos statt 24.
- **Panel**: Markierung im Aktivitätsdetail mit bestätigter Paarung,
  Protokollblock im Trainer-Reiter.

### A2 · Drei Spec-Korrekturen VOR dem Bau

Alle drei gemeldet, freigegeben, in `docs/ausbau.md` unter „Was der Bau von K
an dieser Spezifikation korrigiert hat" nachgetragen:

1. **K1 war nicht „nur `workouts.py`".** Der 20-Minuten-Bestwert steht in keinem
   archivierten Feld, also zieht K2 das ganze J7 mit herein.
2. **Die Lastregel aus I3 gilt bei konstanter Intensität** und ist für eine
   Einheit mit fester Arbeit und abgeleiteter Dauer nicht anwendbar.
3. **Die Ausschlusswarnung zielte auf den falschen Filter** — es sind drei Tore,
   und der Intensitätsfilter beißt zuerst.

### A3 · Drei Befunde, in §7

1. **Der Vorgabewert ist die Schwester von Fehlerklasse 3.** `recovery_offered`
   wurde nie an `suggest()` übergeben — die Reiz-Stufe konnte im Trainer-Reiter
   nie erscheinen. Elf Gegenproben aus 0.42.0 haben es nicht gesehen, weil alle
   `stage()` prüften und keine den Weg dorthin.
2. **Eine Regel, die nur in eine Richtung schützt, ist eine halbe.** Die
   Plausibilitätsregel fängt nur einen zu niedrigen Anker.
3. **Ein gelockerter Wächter ist keiner mehr.** Die Zahl wird aufgelöst, nicht
   die Prüfung aufgeweicht.

### A4 · Prüfstand: sechzehn Dateien, 4.943 Prüfungen

- **`test_projektstand.py`** (neu): der §9-Wächter. Fährt die fünfzehn übrigen
  Dateien als Subprozesse und hält die gedruckten Zahlen gegen die
  Tabellenzeilen. Die eigene Zeile gegen den eigenen Zähler — ein Fixpunkt, der
  Grund steht als Absatz in der Datei.
- **Der Vorgabewert-Wächter** in `test_websocket_registration`: jeder Aufruf
  nennt jeden Urteilseingang, **und** die Liste der Urteilsfunktionen ist
  vollständig.
- **Der Reiz-Gleichstand** über acht Kombinationen: gleiche Stufe **und** gleiche
  Begründung in beiden Ansichten.
- **Siebzehn Gegenproben**, alle einzeln zurückgedreht und gezählt und benannt
  fallen gesehen. Zwei waren stumpf und wurden geschärft.
- **`ring()` entfernt** (tot seit 0.37.0). `rd` bleibt — es ist die
  Bereitschafts-Payload.

---

## Teil B — was als Nächstes ansteht

### B1 · Verifikation von 0.44.0 am lebenden System (zuerst)

Siehe Teil C. Nichts Neues bauen, bevor das gelaufen ist.

### B2 · Der erste echte Durchlauf des Protokolls

Der eigentliche Zweck von Paket K. Reihenfolge:

1. `durability_test_fresh` aus dem Trainer-Reiter in den Kalender legen, bei
   grünem Zustand fahren (Rolle, All-outs **nicht** in ERG).
2. Die Fahrt im Aktivitätsdetail als **Termin 1 — frisch** markieren. Danach
   prüfen: erscheint `durability_test_fatigued` mit einer Zielleistung, und ist
   sie 80 % der gemessenen 20-Minuten-Leistung?
3. Mindestens zwei ruhige Tage, dann Termin 2. Verpflegung mitrechnen
   (80 g/h, bei ~3 h also rund 240 g), die 1.000 kJ **ab Blockstart** zählen.
4. Termin 2 markieren und die Paarung **bestätigen**.

**Erwartung nach K0:** aus 192 W frisch folgt eine Zielleistung von 154 W, und
die liegt 8 W über der gemessenen aeroben Schwelle von 146 W. Das ist knapp —
kommt der frische Test unter 183 W herein, greift die Plausibilitätsregel und
die Einheit erscheint nicht. Das ist gewollt, aber es sollte niemanden
überraschen.

### B3 · Paket K Stufe 2 (K3, die Hantel)

**Erst wenn zwei Messungen vorliegen.** Zwei Zeilen (5 und 20 min), je zwei
Punkte, gefüllt gegen hohl, Achse nicht bei null. Die 6,5-/12,5-%-Marke aus J5
**nur an der 20-Minuten-Zeile** — die Studie fand für 5 min keinen
Gruppenunterschied. Aus zwei Punkten wird keine Gerade.

### B4 · Das Aufräum-Paket (Punkt 6 aus dem K-Auftrag)

**Ganz oben auf der Liste, weil er bei 0.44.0 ausgefallen ist: der §7-Eintrag
zu J1 als eigene Fehlerklasse.** Nicht „zu wenig Daten", sondern „die Messung
misst etwas anderes als behauptet". Mit der Placebo-Schwelle bei 200 kJ
(+110,2 %, t = +4,18 — signifikant stärker im ermüdeten Zustand) als Beleg, dem
längengleichen Kontrollabschnitt als dem, was es gefangen hat, und r = +0,18 als
dem Beleg, dass eine Regression es nicht gefunden hätte. Die einzige der vier
Klassen, gegen die kein Wächter hilft — nur ein Kontrollabschnitt, den jemand
absichtlich baut. Der volle Wortlaut steht in `docs/ausbau.md` unter „Zuerst in
diesem Paket".

Der Rest als eigenes Release zurückgestellt. **Übrig ist nur noch die DFA/ACWR-Dublette**
— vier Frontend-Stellen, Wächter steht auf exakter Gleichheit `=== 2` und muss
mit umgeschrieben werden. `ring()` ist erledigt, `decoupling_series` bleibt
stehen (sie hat einen Konsumenten). Siehe `docs/ausbau.md`, Abschnitt „Eigenes
Paket — die restlichen Dubletten und der tote Code", dort korrigiert.

### B5 · Belastungs-Reiter

Weiterhin der nächste Audit-Kandidat: seit 0.6.0 unangetastet, am weitesten
hinter der Studienlage (§10 Punkt 1).

---

## Teil C — Verifikation von 0.44.0, lesend am System

Nach HACS-Update, HA-Neustart und hartem Reload. **Erfolgs-Felder prüfen, nie
Key-Abwesenheit** — ein 502 während des Neustarts liefert leere Antworten, und
ein leeres Dict besteht jeden Abwesenheits-Check.

| Kommando | Erwartung |
|---|---|
| `intervals_icu/status` | Archivzähler unverändert, kein Datenverlust durch die Migration |
| `intervals_icu/durability_tests` | antwortet; `tests` leer, `anchor` **null**, `pairs` leer, `kinds` trägt `fresh` und `fatigued`, `sources` gefüllt |
| `intervals_icu/workouts` | `protocol.available` ist **false**, `protocol.why` ist `no_anchor`, `protocol.cta` ist `durability_test_fresh` — und der Ersatzsatz nennt Termin 1 **und** die FTP-Entscheidung |
| `intervals_icu/workouts` | `workouts[]` enthält einen Eintrag mit `family: "durability_test"` |
| `intervals_icu/workouts` | jeder Eintrag trägt `stage.key`; mindestens einer ist nicht `green` (sonst sagt die Payload nichts) |

**Die eine Sache, die wirklich neu ist und nur am System geht:** ob der
Archivblock nach dem Neustart **existiert und leer ist**. Die Migration ist ein
No-op auf einem Altbestand, darf also keinen Speichervorgang auslösen — im Log
von `custom_components.intervals_icu` darf beim Start kein Schreibvorgang des
Archivs stehen, der nur davon kommt.

**Nicht am System prüfbar** und deshalb im Prüfstand abgesichert: die
Zielleistungs-Herkunft (Gitter aus zwei FTP-Werten mal zwei frischen Tests), die
Plausibilitätsregel in beiden Richtungen, der Reiz-Gleichstand über beide
Ansichten.

---

## Arbeitsweise

Unverändert: Vertrauensmodus, skeptisch, erst lesen und widersprechen, dann
bauen. **Zuerst sichern, dann bauen** — der erste Befehl ist der Commit auf
einen `-wip`-Zweig, nicht der letzte. HEIMDALL-Schreibtools nur nummeriert
vorschlagen und einzeln freigeben lassen. Token bleibt in einer Shell-Variablen,
Ausgaben schwärzen. Gegenproben gelten erst als bestanden, wenn der Fehler
**gezählt und benannt** erscheint; wo ein Test stumpf bleibt, wird er geschärft
und nicht der Code gelobt.
