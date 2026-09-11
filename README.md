# Intervals.icu for Home Assistant

Bring your [Intervals.icu](https://intervals.icu) training data into Home Assistant.
Not affiliated with, endorsed by, or supported by Intervals.icu.

> **Status: 0.9.1 — the panel, rebuilt.** Seven views, opening on today's
> verdict: a readiness ring made of one segment per signal, the load budget as
> a bullet graph with its arithmetic laid open, per-activity charts stacked on
> a shared time axis, and every derived number carrying its source next to it.

*Deutsche Fassung weiter unten.*

---

## Installation

**HACS (custom repository)**

1. HACS → ⋮ → *Custom repositories* → add this repository, category **Integration**
2. Download *Intervals.icu*, restart Home Assistant
3. Settings → Devices & Services → *Add integration* → **Intervals.icu**

**Manual**

Copy `custom_components/intervals_icu/` into your `config/custom_components/`
directory and restart Home Assistant.

## Setup

You only need an API key. Create one at intervals.icu under
**Settings → Developer Settings**. The athlete ID is optional — the integration
asks the API which athlete the key belongs to.

The key is stored in the config entry and is sent to intervals.icu only.
No telemetry, no third-party services.

## Entities

**Training load:** Fitness (CTL), Fatigue (ATL), Form (TSB), ramp rate, daily load.

**Wellness:** resting heart rate, HRV, HRV SDNN, sleeping heart rate, sleep time,
sleep score, sleep quality, readiness, SpO2, respiration, VO2max, weight, body
fat, steps, calories, hydration, blood glucose, blood pressure, and the
subjective fields (stress, mood, motivation, soreness, fatigue).

**Per sport:** FTP, LTHR and max HR from your sport settings, plus the values
Intervals estimates from recent activities (eFTP, W', Pmax).

**Calendar:** a calendar entity with your planned workouts, plus sensors for the
next workout, its date and its planned load.

Every sensor shows the newest value that actually exists and carries the date it
belongs to as the `value_date` attribute — a wellness row fills up over the day,
so reading only "today" would leave most sensors unknown every morning.
Values Intervals marks as provisional (a weight taken from an activity file
rather than a scale) carry `provisional: true`.

Fields that carry no value at all in the last 30 days are created **disabled**,
so nothing sits at "unknown" forever. Enable one and it starts working the day
data arrives.

Numeric sensors carry `state_class: measurement`, so Home Assistant records
long-term statistics. The built-in **Statistics graph** card plots the PMC
without any additional cards.

## Panel

The integration adds an **Intervals** entry to the sidebar. It serves its own
web component and registers it automatically — nothing to install, no Lovelace
resources to configure. Seven views:

- **Today** — a ring of seven segments, one per readiness signal in its own
  traffic-light colour: you see not only *that* it is red, but *what* the red
  is made of. Next to it the verdict, the load budget as a bullet graph with
  the marks "steady / corridor / risk" and a fold-out showing the arithmetic,
  plus the next planned session checked against that budget. Below, one card
  per signal with a large value, its reference, an always-visible 42-day curve
  and an **independently** collapsible "history & source".
- **Calendar** — a week grid: week card on the left (load, deviation from the
  mean, hours/km/sessions, fitness/form), seven day columns with wellness
  values as icons. Sessions as tiles in the sport's colour with a DFA
  micro-bar; planned items dashed, in three distinct states: done, missed,
  planned.
- **Fitness** — three stacked panels (fitness/fatigue · daily load · form with
  Friel zone bands) over one shared time axis with a single cursor.
- **Activities** — a table, and per session: metrics as a tile grid, then the
  recording as stacked small multiples (power raw + 30 s average, heart rate,
  DFA with the 0.75/0.5 bands, cadence, speed, elevation) under one cursor.
- **Load** — five sections, each with a "read this as:" line and a collapsible
  source: weekly load, ACWR with its corridor, intensity distribution shown
  twice (planned zones against DFA-measured), HRV trend, decoupling.
- **DFA** — the heart rate at which DFA alpha-1 crosses 0.75, over the season,
  with a rolling median; thin readings are drawn hollow and left out of it.
- **Plan** — planned workouts grouped by day, full text on demand.

The panel reads the integration's WebSocket API, not entities: a year of
history has no business in the state machine. Per-second streams are never
stored — they are fetched live when a session is opened, and thinned in
transit.

## Analysis

Every derived number in the panel carries its origin and its limits:

| Metric | Source | Read as |
|---|---|---|
| Form zones | Joe Friel; Intervals applies them to form % by default | rule of thumb, not science — its own author says so |
| Acute:chronic ratio | Gabbett/Blanch, corridor 0.8–1.3, elevated above 1.5 | contested: correlational evidence, mathematical coupling, a formal request for correction |
| Monotony, strain | Foster: weekly mean over standard deviation; strain = load × monotony | flags weeks without a real rest day |
| Intensity distribution | Seiler's three-zone model, elite reference ≈ 75/8/17 | polarized wins on VO2peak by a small margin, and is disputed |
| HRV trend | 7-day rolling mean of ln(rMSSD) against the smallest worthwhile change | your value is an overnight wearable reading, not a morning supine one |
| Decoupling | Joe Friel: ≤ 5 % on steady aerobic rides | only meaningful on steady sessions |
| DFA alpha-1 | Rogers/Gronwald: 0.75 ≈ aerobic threshold (VT1), 0.5 ≈ anaerobic (VT2) | validated against gas exchange; sensitive to artefacts and recording device |
| Subjective wellness | Saw et al., systematic review | self-reported measures track load more sensitively than objective ones |
| Readiness light | composed here from the rows above | the components are published, the combination is not — and no commercial readiness score is independently validated |
| Load budget | the ACWR definition solved for today | 7 × chronic × target − last six days; the target choice per light colour is a setting, not a finding |

## Roadmap

| Stage | Contents |
|---|---|
| 1 | API client, config flow, re-auth, PMC sensors ✅ |
| 2 | Full wellness set, per-sport thresholds, calendar entity ✅ |
| 3 | Local archive, history import, DFA alpha-1 analysis, WebSocket API ✅ |
| 4 | Sidebar panel: fitness curve, activity list, calendar, DFA views ✅ |
| 5 | Analysis views with sourced metrics ✅ |
| 6 | Panel rebuilt: readiness ring, bullet graph, per-activity charts ✅ |
| next | Webhooks instead of polling; write support (planning workouts) |

## Notes

- Authentication is HTTP basic auth with the literal username `API_KEY`.
  Bearer tokens do not work with personal API keys.
- Athlete IDs usually carry a leading `i` (`i12345`). Only early
  Strava-registered athletes have a bare numeric ID. Both are handled.

---

# Intervals.icu für Home Assistant

Holt deine Trainingsdaten von [Intervals.icu](https://intervals.icu) nach Home
Assistant. Kein offizielles Projekt von Intervals.icu.

> **Stand: 0.9.1 — das Panel, neu gebaut.** Sieben Ansichten, Startseite ist
> das Urteil für heute: ein Bereitschaftsring aus je einem Segment pro Signal,
> das Lastbudget als Bullet-Graph mit offengelegtem Rechenweg, Verlaufskurven
> je Einheit über einer gemeinsamen Zeitachse, jede Zahl mit ihrer Quelle.

## Installation

**HACS (eigenes Repository)**

1. HACS → ⋮ → *Benutzerdefinierte Repositories* → dieses Repository hinzufügen,
   Kategorie **Integration**
2. *Intervals.icu* herunterladen, Home Assistant neu starten
3. Einstellungen → Geräte & Dienste → *Integration hinzufügen* → **Intervals.icu**

**Manuell**

`custom_components/intervals_icu/` nach `config/custom_components/` kopieren und
Home Assistant neu starten.

## Einrichtung

Du brauchst nur einen API-Key. Erzeugen auf intervals.icu unter
**Einstellungen → Developer Settings**. Die Athlete-ID ist optional — die
Integration fragt die API, zu wem der Key gehört.

Der Key liegt im Config-Entry und geht ausschließlich an intervals.icu.
Keine Telemetrie, keine Drittdienste.

## Entitäten

**Trainingslast:** Fitness (CTL), Ermüdung (ATL), Form (TSB), Steigerungsrate,
Tagesbelastung.

**Wellness:** Ruhepuls, HRV, HRV SDNN, Schlafpuls, Schlafdauer, Schlafscore,
Schlafqualität, Bereitschaft, SpO2, Atemfrequenz, VO2max, Gewicht, Körperfett,
Schritte, Kalorien, Flüssigkeit, Blutzucker, Blutdruck sowie die subjektiven
Werte (Stress, Stimmung, Motivation, Muskelkater, Müdigkeit).

**Pro Sportart:** FTP, LTHR und maximale Herzfrequenz aus deinen
Sport-Einstellungen, dazu die von Intervals geschätzten Werte (eFTP, W', Pmax).

**Kalender:** eine Kalender-Entität mit den geplanten Workouts, dazu Sensoren
für das nächste Workout, dessen Datum und geplante Last.

Jeder Sensor zeigt den neuesten tatsächlich vorhandenen Wert und trägt das
zugehörige Datum als Attribut `value_date`. Ein Wellness-Datensatz füllt sich
über den Tag; wer nur „heute" liest, hat jeden Morgen lauter unbekannte Werte.
Von Intervals als vorläufig markierte Werte (z. B. ein Gewicht aus der
Aktivitätsdatei statt von einer Waage) tragen `provisional: true`.

Felder, die in den letzten 30 Tagen keinen einzigen Wert hatten, werden
**deaktiviert** angelegt. Nichts steht dauerhaft auf „unbekannt"; ein Klick
genügt, sobald Daten kommen.

Numerische Sensoren haben `state_class: measurement`, Home Assistant führt also
Langzeitstatistiken. Die eingebaute Karte **Statistikdiagramm** zeichnet damit
die PMC-Kurve ohne Zusatzkarte.

## Panel

Die Integration legt einen Eintrag **Intervals** in der Seitenleiste an. Sie
liefert ihre eigene Web-Component aus und meldet sie selbst an — nichts zu
installieren, keine Lovelace-Ressourcen einzutragen. Sieben Ansichten:

- **Heute** — ein Ring aus sieben Segmenten, eines je Signal in dessen
  Ampelfarbe: man sieht nicht nur, *dass* es rot ist, sondern *woraus* das Rot
  besteht. Daneben der Urteilssatz, das Lastbudget als Bullet-Graph mit den
  Marken „gleichbleibend / Korridor / Risiko" und aufklappbarem Rechenweg,
  dazu die nächste geplante Einheit mit Budget-Abgleich. Darunter je Signal
  eine Karte mit Großwert, Referenz, immer sichtbarer 42-Tage-Kurve und einem
  **einzeln** aufklappbaren Feld „Verlauf & Quelle".
- **Kalender** — Wochenraster: Wochenkarte links (Last, Abweichung vom
  Schnitt, Stunden/km/Einheiten, Fitness/Form), sieben Tagesspalten mit
  Wellness-Werten als Symbole. Einheiten als Kacheln in der Sportfarbe mit
  DFA-Mikrobalken; Geplantes gestrichelt, in drei Zuständen: erledigt,
  ausgelassen, geplant.
- **Fitness** — drei gestapelte Felder (Fitness/Ermüdung · Tagesbelastung ·
  Form mit Friel-Zonenbändern) über einer gemeinsamen Zeitachse mit **einem**
  Ablese-Cursor.
- **Aktivitäten** — Tabelle, je Einheit: Kennzahlen als Kachelraster, darunter
  der Verlauf als gestapelte Kleinvielfache (Leistung roh + 30-s-Mittel,
  Herzfrequenz, DFA mit 0,75/0,5-Bändern, Kadenz, Tempo, Höhe), ein Cursor
  über alle Felder.
- **Belastung** — fünf Abschnitte, jeder mit einer Zeile „Zu lesen als:" und
  aufklappbarer Quelle: Wochenlast, ACWR mit Korridor, Intensitätsverteilung
  zweifach (geplante Zonen gegen DFA-gemessen), HRV-Trend, Entkopplung.
- **DFA** — die Herzfrequenz, bei der DFA alpha-1 durch 0,75 fällt, über die
  Saison, mit rollierendem Median; dünne Messungen sind hohl gezeichnet und
  zählen nicht hinein.
- **Plan** — geplante Workouts nach Tagen gruppiert, Volltext aufklappbar.

Das Panel liest die WebSocket-Schnittstelle der Integration, nicht die
Entitäten: ein Jahr Historie gehört nicht in die State-Machine. Sekundendaten
werden nie gespeichert — sie kommen beim Öffnen einer Einheit live und
ausgedünnt über die Leitung.

## Auswertung

Jede abgeleitete Zahl im Panel trägt ihre Herkunft und ihre Grenzen mit sich:

| Kennzahl | Quelle | Zu lesen als |
|---|---|---|
| Form-Zonen | Joe Friel; Intervals rechnet sie standardmäßig relativ zur Fitness | Faustregel, keine Wissenschaft — sagt der Entwickler selbst |
| Akut-zu-chronisch | Gabbett/Blanch, Korridor 0,8–1,3, erhöht ab 1,5 | umstritten: korrelative Belege, mathematische Kopplung, formeller Antrag auf Richtigstellung |
| Monotonie, Strain | Foster: Wochenmittel durch Streuung; Strain = Last × Monotonie | zeigt Wochen ohne echten Ruhetag |
| Intensitätsverteilung | Dreizonenmodell nach Seiler, Elite-Referenz ≈ 75/8/17 | polarisiert liegt beim VO2peak knapp vorn und wird bestritten |
| HRV-Trend | 7-Tage-Mittel von ln(rMSSD) gegen die kleinste bedeutsame Änderung | dein Wert kommt aus der Nachtmessung, nicht aus der Morgenmessung im Liegen |
| Entkopplung | Joe Friel: ≤ 5 % bei ruhigen Dauereinheiten | nur bei gleichmäßiger Fahrt aussagekräftig |
| DFA alpha-1 | Rogers/Gronwald: 0,75 ≈ aerobe Schwelle (VT1), 0,5 ≈ anaerobe (VT2) | gegen Gasaustausch validiert; empfindlich für Artefakte und Aufzeichnungsgerät |
| Selbsteinschätzung | Saw et al., systematischer Review | eigene Angaben bilden Belastung empfindlicher ab als objektive Messwerte |
| Bereitschaftsampel | hier aus den Zeilen darüber zusammengesetzt | die Bestandteile sind belegt, die Kombination nicht — und kein kommerzieller Bereitschaftswert ist unabhängig validiert |
| Lastbudget | die ACWR-Definition nach heute aufgelöst | 7 × chronisch × Ziel − letzte sechs Tage; die Zielwahl je Ampelfarbe ist eine Setzung, kein Befund |

## Fahrplan

| Stufe | Inhalt |
|---|---|
| 1 | API-Client, Config-Flow, Reauth, PMC-Sensoren ✅ |
| 2 | Vollständige Wellness-Werte, Schwellen pro Sportart, Kalender ✅ |
| 3 | Lokales Archiv, Historien-Import, DFA-alpha-1-Auswertung, WebSocket ✅ |
| 4 | Seitenleisten-Panel: Fitness-Kurve, Aktivitätenliste, Kalender, DFA ✅ |
| 5 | Auswertungsansichten mit belegten Kennzahlen ✅ |
| 6 | Panel neu gebaut: Bereitschaftsring, Bullet-Graph, Verlaufskurven ✅ |
| als Nächstes | Webhooks statt Polling; Schreibseite (Workouts planen) |
