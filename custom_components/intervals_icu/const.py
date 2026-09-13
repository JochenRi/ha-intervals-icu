"""Constants for the Intervals.icu integration."""

from __future__ import annotations

from datetime import timedelta

DOMAIN = "intervals_icu"

CONF_API_KEY = "api_key"
CONF_ATHLETE_ID = "athlete_id"

# Stage 1 uses plain polling. From stage 5 on, Intervals.icu webhooks push
# activity uploads and calendar changes, and this interval becomes a fallback.
DEFAULT_SCAN_INTERVAL = timedelta(minutes=30)

# Wellness rows are filled in over the course of a day and can be corrected
# days later, so a window is both cheaper and safer than a single day. Thirty
# days is also the window used to decide which sensors are enabled by default:
# fields that carry no value at all in a month are created disabled.
WELLNESS_LOOKBACK_DAYS = 30

# Calendar window fetched on every refresh.
EVENTS_PAST_DAYS = 30
EVENTS_FUTURE_DAYS = 60

# Archive maintenance.
RECENT_DAYS = 30                  # window re-checked on every routine sync
HISTORY_START_FALLBACK_DAYS = 730  # used when the athlete has no activation date
DFA_BATCH_SIZE = 25               # stream fetches per routine sync
ARCHIVE_SYNC_INTERVAL = timedelta(hours=6)

MANUFACTURER = "Intervals.icu"

# Sidebar panel. PANEL_VERSION is appended to the module URL so browsers pick
# up a new build instead of serving the cached one.
PANEL_URL_PATH = DOMAIN
PANEL_STATIC_PATH = f"/{DOMAIN}_panel"
PANEL_COMPONENT = "intervals-icu-panel"
PANEL_FILE = "intervals-panel.js"
PANEL_TITLE = "Intervals"
PANEL_ICON = "mdi:chart-timeline-variant"
PANEL_VERSION = "0.44.0"

# --- thresholds shared by backend and panel -----------------------------------
# One definition per number, here, because the panel has to show several of them
# and a second copy in the frontend (or in a second module) is a second truth.
# The NAMES carry the question the number answers, not the place it is used.

DECOUPLING_GOOD = 5.0  # FRIEL - a coach's rule of thumb, NOT a study threshold

# --- Plausibilitaet einer Schwellenmessung (PROJEKTSTAND §7, 13.09.2026) ------
# Eine Schwellen-HF unterhalb einer physiologischen Mindestgrenze ist ein
# AUSFALL, keine Messung. Die Fahrt vom 06.06.2026 ("neuer pulsgurt") traegt
# 0,0 bpm ueber 24 Fenster und ging bis 0.44.0 als vollwertige Messung in die
# Reihe ein. 80 bpm, gemessen am Bestand: der niedrigste ECHTE Wert ueber alle
# 53 Messungen liegt bei 90,0 bpm (Gehen) bzw. 130,0 bpm (Rad) - die Grenze
# trennt den Ausfall ab, ohne eine einzige echte Messung zu kosten. Eine aerobe
# Schwelle (alpha-1 = 0,75!) unterhalb davon gibt es physiologisch nicht.
THRESHOLD_MIN_HR = 80.0
# Dieselbe Klasse fuer die Leistung. Am heutigen Bestand faengt sie NICHTS
# (Spanne 116,6-189,6 W) - sie steht hier, weil ein ausgefallener Leistungsmesser
# dieselbe Null liefert wie ein ausgefallener Gurt, und eine Regel, die nur in
# eine Richtung schuetzt, ist eine halbe (§7, 0.44.0).
THRESHOLD_MIN_POWER = 40.0
# Ein Fenster ist keine Messung. Zwei Fahrten stehen auf einem einzigen Fenster
# und wogen bis 0.44.0 so viel wie eine mit 1.484. Zehn statt fuenf, gemessen:
# die Grenze kostet gegenueber fuenf genau zwei Fahrten (9 und 8 Fenster), waehrend
# sie vier statt zwei Scheinmessungen faengt. Der Wert wird weiter GEZEIGT, mit
# seiner Belegung - er zieht nur keinen Median.
THRESHOLD_MIN_WINDOWS = 10

# Which sessions the durability tile may look at.
DURABILITY_MIN_MINUTES = 45      # below this a decoupling reading is not usable
DURABILITY_MAX_INTENSITY = 80    # interval sessions are a different question
DURABILITY_EXCLUDED_TYPES = ("VirtualRide",)  # different environment, fixed load

# Steadiness is a STEPLESS quantity, so it weighs instead of admitting: a ride
# at VI 1.05 counts fully, 1.15 by half, from 1.25 not at all. Both numbers are
# house settings (docs/ausbau.md G3). The upper one is also the outer gate in
# derive.steady_endurance_reason() - one boundary, not two, or the tile and the
# load tab would again read from two different populations (the F6 error).
DURABILITY_VI_FULL = 1.05
DURABILITY_VI_NONE = 1.25

# A trend line needs a base to rest on, and the base is the SUM OF WEIGHTS, not
# the head count: thirty rides at weight 0.1 are three rides. Setting.
DURABILITY_MIN_WEIGHT_SUM = 20.0
# Per season block the same question has a smaller answer - a block that had to
# clear the pool threshold could never exist. Own number, own name (measured on
# the live archive: the fullest 12-week block carries 27, the others 8 to 14).
DURABILITY_MIN_WEIGHT_SUM_BLOCK = 8.0

# A slope has to be distinguishable from zero before it may carry a claim:
# larger in magnitude than twice its own standard error. Setting, and the one
# that today keeps the tile from naming a tipping point at all.
DURABILITY_MIN_SLOPE_T = 2.0

# Season blocks. Twelve weeks, not eight: measured on the live archive, eight
# produces a block of a single ride while twelve leaves none below three.
DURABILITY_BLOCK_WEEKS = 12

# Work bands for the binned medians under the cloud - a DESCRIPTION of where
# the points sit, never a forecast. Boundaries in kJ.
DURABILITY_BINS_KJ = (400.0, 600.0, 800.0, 1100.0)

# Which power turns work into time. The median over the whole pool spans a
# season of progression (61-151 W on this archive) and would convert with a
# figure from last winter, so the window is recent - and when it is too thinly
# populated it widens VISIBLY to the fallback, never silently.
DURABILITY_POWER_DAYS = 90
DURABILITY_POWER_DAYS_FALLBACK = 180
DURABILITY_MIN_POWER_SESSIONS = 5

# Der Reiz soll aus der Anstrengung kommen, nicht aus dem Hungerast: eine
# schlecht gefuetterte Fahrt ist kein Durability-Training. Empfehlung aus der
# Literatur, und weil die Kachel sie DRUCKT, steht sie hier und nicht dort.
DURABILITY_FUELLING_G_PER_H = 80

# --- Durability-Testprotokoll (docs/ausbau.md K0/K1) --------------------------
# Barsumyan, Soost, Burchard: "Durability as an independent parameter of
# endurance performance in cycling", BMC Sports Sci Med Rehabil 17:192 (2025).
# Heimtest an zwei Terminen, ausdruecklich fuer Amateure entwickelt. Jede Zahl
# steht GENAU HIER, weil die Kachel und die Einheitenkarte sie drucken - eine
# zweite Kopie im Frontend waere eine zweite Wahrheit (Waechter aus Paket F).
DURABILITY_TEST_WARMUP_MIN = 20      # Einrollen, beide Termine gleich
DURABILITY_TEST_SHORT_MIN = 5        # kurzes All-out
DURABILITY_TEST_LONG_MIN = 20        # langes All-out, der Bezugswert
DURABILITY_TEST_COOLDOWN_MIN = 10    # Ausrollen
# SETZUNG: das Protokoll nennt keine Erholungsdauer zwischen den beiden
# All-outs. Gewaehlt, nicht gemessen - und sie muss an BEIDEN Terminen gleich
# sein, sonst vergleicht Termin 2 etwas anderes.
DURABILITY_TEST_RECOVERY_MIN = 10
# Arbeit im Ermuedungsblock. Aus dem Protokoll, nicht verhandelbar.
DURABILITY_TEST_WORK_KJ = 1000.0
# Dieselbe Groesse in Joule. Steht HIER und nicht als Umrechnung an der
# Rechenstelle, damit im Protokollteil von workouts.py keine nackte 1000 mehr
# auftaucht - der Waechter aus Paket F kann eine Einheitenumrechnung nicht von
# einer Schwelle unterscheiden, und ein Waechter, den man dafuer lockert, ist
# ab dann keiner mehr.
DURABILITY_TEST_WORK_J = DURABILITY_TEST_WORK_KJ * 1000.0
# Zielleistung des Ermuedungsblocks als Anteil der FRISCHEN 20-min-Leistung.
DURABILITY_TEST_BLOCK_FRACTION = 0.80
# Einroll-/Ausroll-Intensitaet, als Anteil desselben Ankers.
DURABILITY_TEST_EASY_FRACTION = 0.55
DURABILITY_TEST_SPIN_FRACTION = 0.50
# SETZUNG fuer die VORAB-Lastrechnung: wie sich die erwartete 5-min-Leistung
# zur 20-min-Leistung verhaelt. Am eigenen Bestand gemessen (251 W ueber 5 min
# gegen 192 W ueber 20 min = 1,31), aber als Faktor fuer kuenftige Termine
# gesetzt. Er geht NUR in die geschaetzte Last ein, nie in eine Vorgabe: die
# All-out-Abschnitte haben keine Zielleistung, das ist ihr Zweck.
DURABILITY_TEST_ALLOUT_5_FACTOR = 1.30
# Validierung der Quelle, als Groessenordnung neben dem eigenen Ergebnis.
DURABILITY_TEST_REFERENCE = "-10,1 ± 6,5 % über 20 min, -10,8 ± 7,8 % über 5 min"

# --- Progressionsregel (docs/ausbau.md H2) ------------------------------------
# BJSM-Kohortenstudie ueber 18 Monate mit mehr als 5.200 Laeufern: deutlich
# erhoehtes Ueberlastungsrisiko, wenn eine EINZELNE Einheit die laengste der
# letzten 30 Tage um mehr als 10 % uebersteigt. Der Risikofaktor ist der
# einzelne Sprung, nicht die Wochensumme - die verbreitete 10-%-WOCHENregel
# stammt aus einem Laienratgeber von 1980 und senkte in zwei Untersuchungen die
# Verletzungsrate nicht.
#
# ZWEI GRENZEN, die ueberall mitgedruckt werden muessen: erhoben an LAEUFERN,
# nicht an Radfahrern; und die 10 % sind der gemessene Risikoknick, keine
# Trainingsvorschrift. Der Satz sagt, was ohne erhoehtes Risiko geht, nicht was
# noetig ist.
PROGRESSION_FACTOR = 1.10
# Auf fuenf Minuten gerundet, und zwar HIER im Backend: wer die gedruckte Zahl
# nachrechnet, muss auf die gedruckte Zahl kommen (dieselbe Regel wie bei der
# Umrechnung Arbeit -> Zeit, docs/ausbau.md F3).
PROGRESSION_ROUND_MINUTES = 5
# Die Leiter der Bezugsfenster. Das ERSTE Fenster ist das der Studie; steht
# darin nichts Qualifiziertes, wird ausgeweitet - und der Zeitraum genannt, nie
# still. None heisst "ganzer Bestand". Die 30 steht nur hier, damit nicht eine
# zweite Wahrheit daneben entsteht.
PROGRESSION_WINDOWS_DAYS = (30, 90, 365, None)

# Three minimum counts, three different questions. Collapsing them into one
# number would be the same error as the duplicated 5.0, only inverted.
MIN_SESSIONS_FOR_TILE = 8          # is there enough history for the tile at all?
MIN_SESSIONS_TO_CLAIM_GROUP = 5    # may a single group's value be asserted?
MIN_PEERS_TO_RANK_METRIC = 6       # may one metric be placed as a percentile?

# Comparison group (docs/ausbau.md C3): caliper widths as multiples of the
# athlete's own standard deviation, widened in steps until the metric has
# enough peers. Stops at 1.0 SD - wider is no longer a comparison group.
PEER_CALIPER_STAGES = (0.2, 0.4, 0.6, 0.8, 1.0)

# --- Paket I: "Erholung war da" ------------------------------------------------
# Die Reiz-Stufe (funktionelles Ueberreichen) braucht die Aussage, dass die
# letzten Tage Erholung geboten haben. Ohne festgezurrte Regel entstuende sie
# als ZWEITE Zustandsregel durch die Hintertuer - deshalb steht sie einmal hier
# und einmal in coach.recovery_offered(), sonst nirgends.
#
# GRENZE, die ueberall mitgedruckt werden muss: diese Zahlen sind GEWAEHLT,
# nicht gemessen - dieselbe Ehrlichkeit wie bei der Zielwahl je Ampelfarbe im
# Lastbudget. Die Bestandteile (Zustand, harte Tage, Tageslast) sind belegt,
# ihre Kombination zu genau dieser Schwelle ist eine Setzung.
RECOVERY_QUIET_DAYS = 2        # wie viele Tage "ruhig" gewesen sein muessen
RECOVERY_MAX_HARD_DAYS_7 = 0   # harte Tage in den letzten sieben, die erlaubt sind
