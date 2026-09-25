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
PANEL_VERSION = "0.70.0"

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

# --- Ermuedungskurve: welche Fahrten ihren Stundenverlauf hergeben ------------
# ZWEI KRITERIEN, ZWEI FRAGEN - und keines ersetzt das andere:
#   * DURABILITY_VI_* fragt "wie ZAPPELIG wurde getreten" (Ampeln, Wind, Berge).
#   * Diese Grenze hier fragt "war die Einheit STRUKTURIERT" (Bloecke im Plan).
# Dass das zwei Fragen sind, hat die Vermessung vom 13.09.2026 erzwungen: der
# VI trennt strukturierte Einheiten NICHT, weil ein 20-Minuten-Block sehr
# gleichmaessig ist - nur auf anderem Niveau. Gemessen (Anteil der Zeit
# oberhalb Zone 2 des Dreizonenmodells, §5):
#
#   SweetSpot 2x20   24.08.  VI 1,0955  51,4 %      volumen Rad 30.08. VI 1,0882  14,4 %
#   vol+SweetSpot    20.08.  VI 1,0309  33,3 %      volumen Rad 04.09. VI 1,0738   4,4 %
#   Tempo 2x20       13.09.  VI 1,0694  46,0 %      volumen Rad 27.08. VI 1,0476   3,2 %
#   VO2max 3x4       01.09.  VI 1,2745  38,8 %      volumen Rolle      VI 1,0000   0,0 %
#
# Die VI-Bereiche ueberlappen vollstaendig (1,031-1,275 gegen 1,000-1,088):
# DURABILITY_VI_NONE = 1,25 haette ALLE DREI Stoerer aus L0 Runde 3 durchgelassen.
# Der Zonenanteil trennt mit einer Luecke von 19 Punkten ohne einen einzigen
# Ueberlappungsfall. Er faengt zugleich den Stoerer aus Runde 1 mit: eine
# Ausfahrt, deren erster Berg die Stunde 1 anhebt, steht ebenfalls ueber Zone 2.
#
# SETZUNG, an ZEHN Fahrten EINES Bestands gemessen - keine Studiengrenze. Wer
# ueberwiegend strukturiert faehrt, verliert daran viel; deshalb weist die
# Kachel aus, wie viele Fahrten daran scheitern, statt eine leere Kurve zu
# zeigen. Mittig in der belegten Luecke: 6 Punkte Abstand nach unten, 13 nach oben.
FATIGUE_MAX_ABOVE_Z2 = 20.0
# Eine Ermuedungskurve braucht Fahrten, die ueberhaupt zwei Stunden erreichen
# koennen. Unterhalb einer Stunde gibt es keinen Stundenverlauf zu lesen.
FATIGUE_MIN_MINUTES = 60
# Die Darstellungsbereiche der Kurve. Was hier steht, ist die MINDESTBELEGUNG -
# die Stundengrenzen selbst rechnen sich daraus und stehen NIRGENDS im Code:
# ein Bestand mit langen Fahrten bekommt andere als einer mit kurzen. Setzung.
# Am eigenen Bestand ergibt das durchgezogen bis Stunde 2 (26 und 23 Fahrten),
# duenn fuer Stunde 3 (5) und gestrichelt ab Stunde 4 (1).
FATIGUE_SOLID_MIN_RIDES = 10
FATIGUE_THIN_MIN_RIDES = 2
# Wie viele PAARE die gepaarte Gegenrechnung braucht, bevor sie eine Zahl
# zeigen darf. L0 Runde 3 hat es vorgefuehrt: bei drei Paaren kann der
# Vorzeichentest strukturell nicht unter p = 0,25 fallen - der Test hat dort
# keine Trennschaerfe, unabhaengig vom Ergebnis. Setzung, bewusst niedrig
# genug, dass die Rechnung auf diesem Bestand ueberhaupt laeuft, und hoch
# genug, dass sie nicht auf einer Handvoll Fahrten eine Zahl behauptet.
FATIGUE_MIN_PAIRS = 6

# Welchen ANTEIL der gemessenen Schwelle eine Grundlageneinheit traegt. Die
# Kurve liefert P(alpha = 0,75) - das IST die aerobe Schwelle, keine
# Trainingsvorgabe. Wer dort faehrt, faehrt an der Schwelle und nicht darunter.
#
# 90 %, und das ist keine Hausnummer: Stevenson, Kilding, Plews, Maunder
# (Eur J Appl Physiol 2022) und Gallo et al. (Eur J Appl Physiol 2024) liessen
# ihre Probanden bei 90 % der Leistung an der ersten ventilatorischen Schwelle
# fahren - dieselben Studien, aus denen die Form der Kurve und die HF-Korrektur
# stammen. Die Vorgabe steht damit auf derselben Quelle wie alles andere hier.
#
# Und sie passt zur PULSSEITE derselben Einheit: das HF-Fenster der Grundlage
# liegt bei 88-97 % der Schwellen-HF. Dass beide Seiten auseinanderliefen -
# Puls bei 88-97 %, Watt bei 100 % - war der Fehler aus 0.47.0 (PROJEKTSTAND §7).
CURVE_TARGET_SHARE = 0.90

# --- Paket M: ein Wert je Block ----------------------------------------------
# Die ersten zwei Minuten jedes Blocks werden verworfen. Rogers (Front Sports
# Act Living 2021): die ersten zwei Minuten sind nicht im metabolischen
# Gleichgewicht, geeignet sind die Werte bei Minute 4 und 6; Andriolo wertet
# aus demselben Grund nur die Minuten 5 bis 20. AM EIGENEN BESTAND BESTAETIGT:
# der Anlauf endet bei 90-120 s (Mediane je 30-s-Segment, VO2max:
# 1,66 -> 1,67 -> 1,06 -> 0,51 -> 0,70). Bei SweetSpot dauert er laenger, die
# publizierte Grenze deckt also den langsameren Fall mit ab - sie bleibt.
BLOCK_WARMUP_DISCARD_S = 120
# Unter so vielen Punkten nach dem Verwerfen traegt der Median nicht.
BLOCK_MIN_POINTS = 20
# Ein Block unter dieser Dauer kann nach dem Verwerfen nichts mehr hergeben.
BLOCK_MIN_SECONDS = 150
# Unter so vielen Bloecken wird KEINE Verlaufslinie gezeichnet - zwei Punkte
# sind kein Verlauf, und eine Linie durch drei ist die 0.13.0-Falle.
BLOCK_MIN_FOR_TREND = 6

# Die Zielkorridore je Familie. SETZUNG AUS DER PRAXIS DES ATHLETEN, nicht aus
# einer Studie: er faehrt VO2max unter alpha 0,5 und SweetSpot zwischen 0,5 und
# 0,75, schaut waehrend der Einheit auf alpha und regelt die Leistung nach.
# Beide Grenzen zaehlen - faellt alpha unter die untere, wird Leistung
# herausgenommen. Am Bestand geprueft: von 30 gemessenen Bloecken lag KEINER
# unter seinem Korridor, 11 darueber - die Korridore sitzen dort, wo seine
# Werte hinstreben.
BLOCK_CORRIDORS = {
    "vo2max": (0.20, 0.50),
    "sweetspot": (0.50, 0.75),
    "tempo": (0.75, 1.00),
}
# Die Schrittweiten des Regelkreises. Die Grenze zwischen "knapp" und "weit"
# wird NICHT gesetzt, sondern aus der Streuung DERSELBEN Familie gerechnet:
# eine Abweichung, die kleiner ist als die uebliche Schwankung, ist keine.
BLOCK_STEP_NEAR_PCT = 5
BLOCK_STEP_FAR_PCT = 10
# Wie breit das HF-Fenster einer Familie ist: der Median der Block-Herzfrequenzen
# plus/minus ZWEI Streuungen ZWISCHEN den Einheiten. Keine gesetzte Zahl - sie
# reproduziert das Beobachtete. Gemessen: die Block-HF streut INNERHALB einer
# Einheit kaum (SweetSpot Median 1 bpm, VO2max 6), fast die ganze Streuung sitzt
# zwischen den Einheiten, also in der Tagesform (SD 3,2 bzw. 3,6). Mit Faktor 2
# ergibt das VO2max 171-186 (beobachtet 171,5-185,0) und SweetSpot 159-171
# (beobachtet 159,5-168,5).
BLOCK_HR_WINDOW_SD_FACTOR = 2.0
# Unter so vielen Einheiten bleibt das alte Fenster stehen - dieselbe
# Belegungsstaffelung wie bei den Watt. Kein halb umgestelltes Fenster.
BLOCK_MIN_FOR_SOURCE = 3
# Ab welchem eigenen Schritt eine Richtungsumkehr gegen Intervals' Werte etwas
# aussagt. GEMESSEN, nicht gesetzt: Intervals mittelt jeden Block samt Anlauf,
# wir verwerfen ihn - ueber 80 Bloecke liegt sein Wert im Median 0,224 ueber
# unserem, mit einer Spanne von 0,004 bis 0,539. Ein Schritt, der KLEINER ist
# als die Schwankung dieses Versatzes, kann seine Richtung allein daraus
# beziehen. 0,05 liegt darunter; sechs der acht beanstandeten Paare hatten
# einen eigenen Schritt unter 0,05 (Median 0,038).
BLOCK_ORDER_TOLERANCE = 0.05

# ---------------------------------------------------------------------------
# STEUERUNG v2 (Paket "Kreuzprobe klein"). Alles hier haengt am Schalter
# STEERING_SWITCH; steht er aus, wird keine dieser Zahlen gelesen.
# ---------------------------------------------------------------------------
# BLOCK 1 STEUERT NICHT. Am eigenen Bestand gemessen: in 9 von 10 Einheiten
# faellt alpha von Block 1 auf Block 2, im Median um 0,10 - der erste Block
# traegt systematisch das hoehere alpha (PROJEKTSTAND §7, blocks.py Kopf).
# Wer auf ihm regelt, regelt auf dem frischesten Moment statt auf der Einheit.
# Er bleibt sichtbar und beschriftet, er zaehlt nur nicht mit.
STEERING_FIRST_BLOCK_COUNTS = False
# DER STARTWERT ENTSTEHT JE ATHLET IM ARCHIV, NICHT HIER (0.66.3, Michael-
# Befund, Bauregel 10). Bis 0.66.2 standen hier zwei Konstanten mit Johannes'
# Startwerten (SweetSpot 190, VO2max 250) und seinem Stichtag (17.09.2026),
# fest im Code. Ein zweiter Athlet sah im Kachelkopf eine
# fremde Vorgabe und seine eigenen Einheiten darunter, und alles vor dem
# 17.09.2026 zaehlte fuer ihn nicht. Jetzt entsteht der Startwert aus den
# eigenen Einheiten am Tag des Einschaltens (steering.ensure_anchors) und
# steht im Archiv (settings.steering_anchor).
#
# Was bleibt, ist die UEBERNAHME fuer Archive, die von 0.62.0 bis 0.66.2 mit
# eingeschalteter Steuerung liefen: dort GALT der Startwert schon, und er darf
# durch die Reparatur nicht neu entstehen (er laege bei 191/250 statt 190/250).
# Gelesen wird diese Konstante ausschliesslich in steering.migrate_legacy_anchor,
# ein Waechter in test_steering haelt das fest.
LEGACY_STEERING_ANCHOR = {"w": {"sweetspot": 190, "vo2max": 250}, "date": "2026-09-17",
                          "source": "übernommen aus 0.62.0"}
# Die Uebernahme greift nur, wenn der Code-Startwert zum BESTAND des Archivs
# passt: der eigene Startwert (letzte vier Einheiten vor dem Stichtag) darf
# hoechstens um diesen Anteil abweichen. Beim ersten Athleten sind es 0,5 %
# (191 gegen 190) und 2,4 % (244 gegen 250); ein anderer Athlet mit 150 W
# liegt 21 % daneben und bekommt keine fremde Zahl - unabhaengig davon, wie
# sein Schalter beim Update steht.
LEGACY_ANCHOR_TOLERANCE = 0.10
# Wie viele der letzten eigenen Einheiten den Startwert bilden, und ab wie
# vielen er ueberhaupt entsteht. Vier, weil 0.62.0 ihn fuer den ersten
# Athleten so gebildet hat (Block 2 der letzten vier Einheiten); drei als
# Mindestzahl, dieselbe Schranke wie BLOCK_MIN_FOR_SOURCE.
STEERING_ANCHOR_UNITS = 4
STEERING_ANCHOR_MIN_UNITS = 3
# C6: ein Schritt von 5 W, und nur dann, wenn MINDESTENS ZWEI der letzten DREI
# Einheiten derselben Familie auf DERSELBEN Seite ausserhalb des Korridors
# liegen. Bezug ist die VORGABE, nicht die gefahrenen Watt.
STEERING_STEP_W = 5
STEERING_WINDOW = 3
STEERING_NEED = 2
# Und unter DREI Einheiten seit dem Startwert bewegt sich gar nichts, auch
# wenn die ersten beiden beide dieselbe Seite zeigen: zwei Einheiten sind
# kein Belegungsstand, sondern zwei Tage. Die Karte sagt es statt zu schweigen.
STEERING_MIN_UNITS = 3
# Nach einem Schritt faengt das Fenster neu an. Ohne das schieben dieselben
# zwei Einheiten mehrfach: simuliert 6,0 statt 2,6 Bewegungen, die Vorgabe
# wandert bis 210 statt 230 W. Eine Ratsche, kein Regelkreis.
STEERING_CLEAR_AFTER_STEP = True
# Das t-Band: Median +/- t(0,90; n-1) * s * sqrt(1 + 1/n), ab n = 3, ueber die
# letzten vier Einheiten. Das ist das VORHERSAGEband fuer die naechste Einheit,
# nicht das Band des Mittelwerts. MAD und Bootstrap NICHT: unter n = 10 decken
# sie 50-75 % statt der genannten 80 % (Kreuzprobe K7, 40.000 Laeufe je Fall).
STEERING_BAND_MIN_N = 3
STEERING_BAND_WINDOW = 4
# AB WIE VIELEN EINHEITEN EINE QUOTE ANGESAGT WIRD. Dieselbe Schranke und
# derselbe Grund wie bei der Ermuedungskachel (`fatigue_v2.BAND_QUOTE_MIN_N`):
# "8 von 10" ist an vier Einheiten NICHT nachpruefbar. Die Probe, die es tut,
# ist die Vorwaertsprobe (Band aus den Einheiten davor, gegen die naechste) -
# der Weglass-Rueckblick ist bei einem Fenster von vier um 2,6 bis 3,6 Punkte
# verzerrt, weil ein Weglassen dort einen Punkt TAUSCHT statt ihn zu
# entfernen (docs/rechenwege.md K9.1). Bei n = 5 bleiben zwei ehrliche Faelle.
#
# ACHTUNG, AUSDRUECKLICH: solange STEERING_BAND_WINDOW auf 4 steht, ist n im
# Band nie groesser als 4, und die Quote wird damit NIRGENDS mehr angezeigt.
# Das ist Absicht und keine Nebenwirkung - eine Zusage, die nicht nachprueftbar
# ist, gehoert nicht in die Kachel. Die Schranke bleibt als Zahl stehen, damit
# ein wachsendes Fenster sie wieder erreichen kann, statt dass jemand die
# Zeile neu erfinden muss.
STEERING_BAND_QUOTE_MIN_N = 9
# =====================================================================
# DIE t-TABELLEN - EINE STELLE, ZWEI QUANTILE (0.66.0)
#
# Bis 0.65.2 stand die einseitige Tabelle hier und die zweiseitige in
# `fatigue_v2.py` - zwei Listen an zwei Orten, genau der Fall, den die zweite
# Bauregel verbietet. Der Kommentar ueber der zweiten behauptete dabei, es
# gebe nur eine. Beide stehen jetzt hier, nebeneinander, mit der Angabe,
# WOFUER jede gebraucht wird. Wer eine tauscht, sieht die andere dabei.
#
# EINSEITIG t(0,90; df) - fuer eine Aussage "hoechstens so viel".
#   Verwendet von: steering.t_band (Blockband, Watt UND Puls) und
#   fatigue_v2.band (das Band der Ermuedungskette).
#   Symmetrisch um eine Mitte gelegt schliesst sie 80 % ein, nicht 90 %.
# ZWEISEITIG t(0,95; df) - fuer ein SYMMETRISCHES Band, das 90 % einschliesst.
#   Verwendet von: fatigue_v2.reversal_band (seit 0.64.3). Mit der einseitigen
#   Tabelle traf jenes Band am Bestand 70 % statt 80; mit dieser 88 %.
#
# df 1..8 reichen fuer ein Fenster von 4 NICHT nur knapp, sondern mit
# Ueberschuss: dort ist df hoechstens 3. Die hoeheren Eintraege stehen fuer
# den Fall, dass ein Fenster waechst - die Ermuedungskachel rechnet ueber ALLE
# Fahrten und braucht sie heute schon.
T90_ONE_SIDED = {1: 3.078, 2: 1.886, 3: 1.638, 4: 1.533, 5: 1.476,
                 6: 1.440, 7: 1.415, 8: 1.397, 9: 1.383, 10: 1.372}
T90_TWO_SIDED = {1: 6.314, 2: 2.920, 3: 2.353, 4: 2.132, 5: 2.015, 6: 1.943,
                 7: 1.895, 8: 1.860, 9: 1.833, 10: 1.812, 11: 1.796, 12: 1.782,
                 13: 1.771, 14: 1.761, 15: 1.753, 16: 1.746, 17: 1.740,
                 18: 1.734, 19: 1.729, 20: 1.725}
T90_TWO_SIDED_INF = 1.645
# ALTER NAME, DIESELBE LISTE. `STEERING_T90` steht in Prüfstand und Doku; er
# bleibt als Zeiger auf die einseitige Tabelle, damit hier kein zweiter Wert
# entsteht. Neue Aufrufer nehmen den sprechenden Namen.
STEERING_T90 = T90_ONE_SIDED
# =====================================================================

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

# --- Stufentest (docs/ausbau.md N) -------------------------------------------
# Die Auswertung angelehnt an Olieslagers 2026 (Rad, Methodenteil): eine
# Regressionsgerade von DFA a1 ueber der ZEIT, vom Beginn des nahezu linearen
# Abfalls bis zum letzten Zeitpunkt; die Schwelle ist der SCHNITTPUNKT der
# Geraden mit 0,75 bzw. 0,5. Das ist NICHT "der erste Punkt unter 0,75" - eine
# andere Rechnung mit einem anderen Ergebnis. Rogers 2021a/b (Laufband) legen
# die Gerade nur ueber den Abfall von etwa 1,0 bis etwa 0,5, 2021b gegen die
# Herzfrequenz, und bestimmen den Abschnitt nach Augenschein; ob Olieslagers
# den Beginn von Hand setzt, ist nicht nachgelesen. Hier sucht eine Regel den
# Beginn automatisch - eine SETZUNG, und sie steht als solche in der Karte.
#
# Glaettungsbreite fuer die SEGMENTSUCHE. Gerechnet wird danach auf den
# ungeglaetteten Werten - die Glaettung sucht die Grenzen, sie verschiebt
# keinen Messwert. SETZUNG.
RAMP_SMOOTH_S = 30
# Wie lange die geglaettete Kurve IM SEGMENT unter 0,5 bleiben muss, damit der
# Boden als erreicht gilt (Bedingung fuer HRVT2). Ein einzelner Ausreisser unter
# 0,5 ist kein Boden. Das Segment ENDET nicht mehr hier, sondern am Lastende
# (seit Rechenweg e1). SETZUNG.
RAMP_FLAT_S = 60
# Fensterbreite, aus der Watt und Puls AN einer Schnittstelle abgelesen werden.
# Die Arbeiten lesen VO2 und HF ueber eigene Regressionen ab; wir lesen den
# Median eines Fensters um den Zeitpunkt. ABWEICHUNG, beschriftet.
RAMP_READ_WINDOW_S = 30
# Unter so vielen Punkten im Abfall wird keine Gerade gelegt. Aus zwei Punkten
# wird keine Regression, und aus zwanzig keine belastbare.
RAMP_MIN_POINTS = 60
# Erholung im Ausrollen: Fenster am Ende der Fahrt, aus dem der Erholungswert
# gebildet wird. EIGENE IDEE OHNE PROTOKOLLVORGABE - die Literatur betrachtet
# das Fenster 0-10 min nach Belastungsende (Michael 2017; Stanley/Peake/
# Buchheit 2013 fuer die vollstaendige Rueckkehr in 24-72 h), nennt aber keine
# Dauer fuer ein Ausrollen. Gesetzt, nicht gemessen.
RAMP_RECOVERY_WINDOW_S = 120
# Protokolldauern. Die EINZIGEN festen Zahlen des Tests (docs/ausbau.md N1) -
# alle Leistungen leiten sich aus den eigenen Werten ab.
RAMP_WARMUP_MIN = 15
RAMP_COOLDOWN_MIN = 10
# Rampensteigung. FLACH, und sie waechst NICHT mit der eigenen Spanne: bei
# steileren Rampen liegt die Leistung am selben VO2 hoeher, weil die
# Sauerstoffaufnahme hinterherhinkt - dann ist die WATTZAHL nicht mehr
# ablesbar, auch wenn HF und VO2 es waeren (Fleitas-Paniagua 2023 gegen
# Rogers). Die laengere Testdauer bei einem starken Fahrer ist der Preis.
RAMP_STEP_W_PER_MIN = 5
# PROTOKOLLPRUEFUNG (Rechenweg e1). Die Segmentgrenzen kommen aus dem Protokoll
# - Hochpunktsuche ab RAMP_WARMUP_MIN, Ende bei Laenge minus RAMP_COOLDOWN_MIN -,
# also muss die Fahrt dieses Protokoll auch TRAGEN, sonst stehen die Grenzen an
# der falschen Stelle. Die folgenden Zahlen sind alle SETZUNGEN, keine Quelle
# nennt sie:
# Anteil der Rampensteigung, der die Grenze zwischen "flach" und "steigt"
# bildet: Einrollen flach heisst Watt-Steigung unter diesem Anteil von
# RAMP_STEP_W_PER_MIN, Rampe steigt heisst mindestens dieser Anteil. SETZUNG.
# Am Test vom 16.09.2026 gemessen: Einrollen 1,26 W/min, Rampe 5,69 W/min.
RAMP_PROTOCOL_SLOPE_SHARE = 0.5
# Ausrollen sitzt: der Watt-Median kurz NACH dem Protokollende liegt bei hoechstens
# diesem Anteil des Medians kurz DAVOR. SETZUNG. Am 16.09.2026: 130 gegen 249 W.
RAMP_COOLDOWN_MAX_SHARE = 0.8
# Die beiden Vergleichsfenster um das Protokollende: je so breit, und so weit vom
# Ende abgesetzt. SETZUNG. Ein um weniger als den Abstand verschobenes Lastende
# faellt der Pruefung sicher nicht auf; wie weit darueber hinaus, haengt an der
# Form von Rampe und Ausrollen. Am Test vom 16.09.2026: 90 s zu kurz faellt NICHT
# auf, 120 s zu kurz und 90 s zu lang schon (test_ramp, Toleranz am echten Strom).
RAMP_END_CHECK_WINDOW_S = 60
RAMP_END_CHECK_GAP_S = 60
# ERWARTUNG fuer die Lastschaetzung der Katalogkarte, KEINE Vorgabe: die Rampe
# endet an einem Zustand und nicht an der Uhr. Wie lange sie dauert, haengt an
# der eigenen Spanne - bei einem starken Fahrer laenger, und das ist der Preis
# der flachen Steigung und kein Konstruktionsfehler.
RAMP_EXPECTED_MIN = 30
# Reserve ueber der eigenen Leitzahl hinaus, als ZEIT und nicht als Anteil:
# nach dem Erreichen der Leitzahl wird noch so lange weitergefahren, damit die
# flache Strecke unter 0,5 ueberhaupt aufgezeichnet wird. SETZUNG - die
# Literatur nennt dafuer nichts. RAMP_FLAT_S (60 s) ist das mathematische
# Minimum; das hier ist eine Testauslegung. Eine Zeit sagt, was sie bedeutet,
# und haengt nicht an einer zweiten Prozentzahl.
RAMP_END_RESERVE_MIN = 10
# Der sichtbare Rueckfall auf die FTP, wenn weder Ermuedungskurve noch
# Blockmessung tragen - der Einsteigerfall aus N1. BEIDE Enden werden als
# Rueckfall beschriftet, wie ueberall sonst. Diese zwei Zahlen sind die
# EINZIGEN Prozentwerte des Tests und stehen deshalb hier und nicht im
# Katalogeintrag (0.51.0 hatte sie dort, und kein Waechter sah hin - §7).
RAMP_FALLBACK_START_PCT = 60
RAMP_FALLBACK_END_PCT = 115
# Quellen, als Groessenordnung neben dem eigenen Ergebnis. Sportart dazu: die
# 0,75 stammt vom LAUFBAND (Rogers 2021a, 15 Laeufer, Bruce-Protokoll).
RAMP_REFERENCE_RUN = "Laufband, 15 Läufer: VT1 bei 152 bpm gegen HRVT1 bei 154 bpm"
RAMP_REFERENCE_BIKE = "Rad, 9 Elite-Triathleten: LT1 bei 252,3 W gegen HRVT1 bei 247,0 W"
RAMP_REFERENCE_PATIENTS = "Rad, Herzpatienten: 73,2 W gegen 67,8 W, r = 0,87"

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

# --- Einstellungen des Athleten (Options-Flow, Bauregel 10) -------------------
# Die alpha-Werte der Grundlagen-Einheit (0.68.0): Grenze und Ziel der
# Umkehrung. Vorbelegt ist nur die Grenze (alpha 1,0); das Ziel bleibt leer,
# dann traegt die Einheit die Grenze. Eine Regel des Athleten, keine
# Literaturschwelle - die Zone-1-Obergrenze liegt in der Literatur bei 0,75.
OPT_GA_ALPHA_LIMIT = "ga_alpha_limit"
OPT_GA_ALPHA_TARGET = "ga_alpha_target"
DEFAULT_GA_ALPHA_LIMIT = 1.0

