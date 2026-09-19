"""Ermuedungsrechnung v2 - die Kurve aus der Ablesestelle statt aus dem Fit.

WARUM ES DIESES MODUL GIBT. Die alte Rechnung liest die Linie bei alpha 0,75
ab. Dort ist Johannes bei seinen Grundlagenfahrten fast nie: er faehrt 118 bis
150 W, die Schwelle liegt bei rund 157 W. Jede Fahrt wird also aus dem
Datenbereich HERAUS gerechnet. Der Beleg ist der 20.08.2026: im alpha-Fenster
0,65-0,85 lagen NULL Punkte, der Fit warf trotzdem 187,4 W aus - den hoechsten
Wert des ganzen Bestands - und genau der blies das Band auf 107 bis 196 W auf.

DIE ABLESESTELLE fragt anders: nicht "wo kreuzt die Linie 0,75", sondern "wie
hoch ist alpha BEI DER LAST, DIE ICH FAHRE, und wie verschiebt sich das ueber
die Fahrtdauer". Dort liegen im Median 110 Punkte je Stunde gegen 7 im
alpha-Fenster; 11 von 42 Fahrtstunden haben im alpha-Fenster gar keinen Punkt,
im Lastfenster keine einzige. Es wird interpoliert statt extrapoliert, und
Rollenfahrten zaehlen mit (7 von 7 statt 2 von 7).

DIE LITERATUR LIEST AN DIESER STELLE, nicht am Kreuzungspunkt - vier von vier
gegengelesenen Arbeiten. Die schaerfste Stelle steht in J Sports Sci 2023
(02640414.2023.2277034): nach Ermuedung bricht die Uebereinstimmung des
Kreuzungspunkts mit VT1 ein (R2 0,83 -> 0,62), DFA-a1 koenne Schwellen "nur im
unermuedeten Zustand" genau abgrenzen. Wer Durability am Kreuzungspunkt misst,
misst sie also mit einem Werkzeug, das genau dort seine Gueltigkeit verliert.
medRxiv 2026 (26354281) sagt es positiv: Aenderungen von DFA-a1 BEI FESTER
INTENSITAET schaetzen die angesammelte Ermuedung.

WAS GEMESSEN IST UND WAS GESETZT. Gemessen ist der Verlauf in alpha:
-0,080 alpha je Stunde, Median ueber 14 Fahrten, 13 davon fallen. Die Zahl
haelt jede Zusammenfassung (Median, gewichtet, nur lange, nur draussen liegen
zwischen -0,075 und -0,080) und jedes Weglassen einer Fahrt (Spanne 0,004).
GESETZT sind: der Schnitt nach Fahrtstunden (keine Quelle), das Lastfenster
+/- 5 W, der gerade Abfall ab Stunde 2 (bis dahin an 13 Fahrten belegt,
danach an drei), die Umrechnung alpha -> Watt und die Studienform hinter dem
belegten Bereich. Sie stehen woertlich auf der Kachel.
"""

from __future__ import annotations

from typing import Any

try:  # inside the package (Home Assistant)
    from . import derive
    from . import fatigue
    from .const import STEERING_T90
except ImportError:  # standalone (test suite loads this file directly)
    import derive  # type: ignore[no-redef]
    import fatigue  # type: ignore[no-redef]
    from const import STEERING_T90  # type: ignore[no-redef]

# DER SCHALTER. Wie `CURVE_SWITCH` im Archiv, nicht in den Optionen: er gehoert
# zu den Daten, die er umschaltet. ZWEI Fragen, ZWEI Schalter - die Auswahl der
# Fahrten ("meine Markierungen") bleibt davon unberuehrt.
V2_SWITCH = derive.DFA_WATT_WINDOW_SETTING

# ER KOSTET ETWAS, und das muss VOR dem Umlegen dastehen. Die 120-s-Paarung
# aendert jedes gespeicherte p075, also muss der Bestand neu gemessen werden.
# Ausgeschaltet passiert nichts: das Archiv bleibt unberuehrt.
SWITCH_NOTE = (
    "Umgelegt rechnet die Kurve anders: die Watt werden über dasselbe "
    "120-Sekunden-Fenster gemittelt wie alpha, und der Verlauf wird an deiner "
    "eigenen gehaltenen Last abgelesen statt am Kreuzungspunkt 0,75. "
    "ES ÄNDERT SICH NUR DIE ERMÜDUNGSKURVE: deine aerobe Schwellen-HF, die "
    "Schwellenleistung des Ankers, die Trainer-Einheiten, die Blockmessung, "
    "der DFA-Reiter und die Belastungsansichten lesen eine andere Größe und "
    "bleiben unberührt. "
    "Es kostet einen Reimport: {rides} Fahrten werden neu EINGELESEN (alle mit "
    "alpha-Daten, in Schüben zu {batch}, also {batches} Abgleiche). "
    "FÜR DIE KURVE zählen weiterhin nur deine {curve} markierten Fahrten — sie "
    "sind neu zu messen, weil die alte Messung auf der anderen Wattachse sitzt. "
    "Bis der Reimport durch ist, sind Blockmessung und Steuerung leer. "
    "Ausgeschaltet bleibt alles, wie es ist."
)


# DIE WOERTER DES SCHALTERS, wie bei den drei anderen aus dem Modul und nicht
# aus dem Panel. Ohne sie gab es 0.63.0 zwar den Befehl, aber keinen Knopf:
# Johannes konnte die neue Rechnung gar nicht einschalten.
SWITCH_WORDS = {
    "title": "Rechnung der Ermüdungskurve",
    "off_label": "Kreuzungspunkt 0,75",
    "on_label": "meine eigene Last",
    "go_label": "auf die neue Rechnung umstellen",
    "back_label": "zurück auf den Kreuzungspunkt",
    "off_note": ("Die Kurve liest heute ab, wo die Ausgleichsgerade alpha 0,75 "
                 "schneidet — bei deinen Grundlagenfahrten liegt das über der "
                 "Last, die du wirklich trittst, die Zahl wird also aus dem "
                 "Datenbereich heraus gerechnet."),
    "on_note": ("Die Kurve liest alpha bei der Last ab, die du wirklich "
                "gefahren bist, und die Watt werden über dasselbe "
                "120-Sekunden-Fenster gemittelt wie alpha."),
}


def switch_note(data: dict[str, Any], rides: int = 0, batch: int = 0) -> str:
    """Der Hinweis MIT den Zahlen dieses Bestands.

    Bis 0.63.0 standen 58 und 28 als Text im Satz - zwei Zahlen, die niemand
    nachzog, und sie lasen sich ausserdem so, als liefen alle 58 Fahrten in
    die Kurve. Eingelesen wird alles mit alpha-Daten; gerechnet wird mit den
    markierten. Das sind zwei Zahlen und zwei Saetze.
    """
    marked = len((fatigue.rides(data) or {}).get("used") or [])
    schuebe = max(1, -(-int(rides or 0) // max(1, int(batch or 1))))
    return SWITCH_NOTE.format(rides=int(rides or 0), batch=int(batch or 0),
                              batches=schuebe, curve=marked)


# DIE DREI BRUECKEN alpha -> Watt, in Watt je Stunde bei -0,080 alpha je Stunde.
# Sie stehen um den Faktor acht auseinander, und das ist keine Streuung,
# sondern ein Modellunterschied: die globale Fit-Steigung misst ueber die ganze
# alpha-Spanne (Median -27,9 W je alpha), die oertliche im Lastfenster
# (Median -97,8). Welche richtig ist, ist am Bestand NICHT entscheidbar - dafuer
# fehlt eine Fahrt, die zwei verschiedene Lasten lange haelt. Deshalb steht die
# mittlere in der Formelzeile und die Spanne im Band.
BRIDGE_GLOBAL = 0.92
BRIDGE_FLAT = 2.39
BRIDGE_LOCAL = 7.70

# Der gemessene Verlauf: Median der fahrtweisen alpha-Schritte je Stunde.
DECLINE_PER_HOUR = -0.080

# Ab hier traegt eine Fahrt einen VERLAUF und nicht nur die Hoehe.
MIN_HOURS_FOR_TREND = 2

# WIE WEIT DIE KETTE REICHT. Der Bestand endet heute bei vier Fahrtstunden,
# geplant wird aber laenger - und eine Kachel, die bei vier aufhoert, laesst
# den Athleten die Fortschreibung im Kopf machen. Acht Stunden ist eine
# SETZUNG: es ist die laengste Fahrt, die im Zielprofil vorkommt, keine Zahl
# aus einer Quelle.
PLAN_HORIZON_HOURS = 8

# ZWEI REIHEN JENSEITS DES BESTANDS, und beide werden HIER gerechnet - nicht im
# Panel. Die eine schreibt den eigenen gemessenen Schritt fort, die andere legt
# die Studienform an Stunde 1 an. Welche tiefer liegt, entscheidet sich an den
# Zahlen und nicht am Text: `lower` sagt es je Stunde.
ESTIMATE_WORDS = {
    "state": "geschätzt, keine Messung",
    "lead": "Fortschreibung aus deinen Fahrten",
    "form": "Studienform, an Stunde 1 verankert",
    "rides": "0 Fahrten",
    # Heute faellt Johannes flacher ab als die Studie. Dass das so BLEIBT, ist
    # nicht gesagt - deshalb zwei Saetze und eine Zahl, die entscheidet.
    "flat": ("Deine eigenen Fahrten fallen flacher ab als die Studie — die große "
             "Zahl steht deshalb über der Studienform. Für die erste Fahrt dieser "
             "Länge fang eher an der kleineren an: sie ist hier die vorsichtige."),
    "steep": ("Deine eigenen Fahrten fallen steiler ab als die Studie — die große "
              "Zahl steht deshalb unter der Studienform. Sie ist damit schon die "
              "vorsichtige Zahl; die Studienform daneben ist die Gegenrechnung, "
              "kein Ziel."),
    "first_ride": "Die erste Fahrt dieser Länge ersetzt die Schätzung.",
}

# WAS DAS BAND HEISST, in Worten. t(0,90) ist 90 % einseitig, also 80 %
# beidseitig - und das sind 8 von 10 Fahrten. Der Satz steht HIER und nicht im
# Panel: die Zahl gehoert zu der Tabelle, die sie erzeugt (T90). Eine zweite
# Fassung im Frontend waere eine zweite Wahrheit, und der Zahlen-Waechter ueber
# dem Panel wuerde sie zu Recht melden.
BAND_SHARE_WORDS = "8 von 10 Fahrten"

# Das Zustandsschildchen der Kachel - dieselbe Stelle wie `on_label` bei den
# Bloecken: das Wort gehoert zum Schalter, nicht zur Darstellung.
STATE_ON = "mit neuer Rechnung"

# t(0,90) nach Freiheitsgraden - DIESELBE Tabelle wie bei den Familien. Keine
# zweite Quelle: zwei Tabellen laufen frueher oder spaeter auseinander.
T90 = STEERING_T90


def v2_on(data: dict[str, Any]) -> bool:
    """Steht der Rechenschalter auf AN?"""
    box = (data or {}).get("settings")
    return bool(isinstance(box, dict) and box.get(V2_SWITCH))


def flipped(data: dict[str, Any]) -> dict[str, Any]:
    """Dieselben Daten, der Schalter andersherum - ohne den Bestand anzufassen."""
    box = dict((data or {}).get("settings") or {})
    box[V2_SWITCH] = not v2_on(data)
    return {**(data or {}), "settings": box}


def watt_window(data: dict[str, Any]) -> int:
    """Die Fensterbreite. DURCHGEREICHT - die Regel steht in `derive`.

    Drei Wege fragen danach (Import, Messweg der Markierungen, Leseweg der
    Kurve); eine zweite Fassung hier waere die zweite Wahrheit, die 0.63.0
    genau an dieser Stelle hatte.
    """
    return derive.watt_window(data)


def reading_rows(data: dict[str, Any]) -> list[dict[str, Any]]:
    """Je Fahrt die Ablesestelle, Stunde fuer Stunde.

    Die AUSWAHL der Fahrten kommt unveraendert aus `fatigue.rides` - der
    Auswahlschalter bleibt zustaendig. Dieses Modul entscheidet nur, WAS an
    einer ausgewaehlten Fahrt gelesen wird.

    DER CLUSTER-WAECHTER sitzt schon in `derive`: `load_alpha` ist None, wenn im
    Lastfenster weniger als DFA_LOAD_MIN_POINTS Punkte liegen. Hier wird er
    nicht noch einmal gelockert - eine Stunde ohne Punkte bekommt keine Zahl.
    """
    out: list[dict[str, Any]] = []
    for ride in (fatigue.rides(data) or {}).get("used") or []:
        hours = []
        for row in ride.get("hours") or []:
            if row.get("load_alpha") is None:
                continue
            hours.append({"hour": row.get("hour"),
                          "alpha": row.get("load_alpha"),
                          "n": row.get("load_n"),
                          "load_w": row.get("load_w")})
        if not hours:
            continue
        hours.sort(key=lambda item: item["hour"] or 0)
        out.append({"activity_id": ride.get("activity_id"),
                    "date": ride.get("date"),
                    "load_w": hours[0].get("load_w"),
                    "hours": hours,
                    "first": hours[0]["alpha"],
                    "last": hours[-1]["alpha"],
                    "span": (hours[-1]["hour"] or 0) - (hours[0]["hour"] or 0),
                    "carries_trend": len(hours) >= MIN_HOURS_FOR_TREND})
    return out


def decline(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Der Verlauf: Median der fahrtweisen Schritte, in alpha je Stunde.

    Je Fahrt EIN Schritt - nicht je Stundenpaar. Sonst zaehlte eine lange Fahrt
    dreimal und eine kurze einmal, und der Median waere ein Median ueber
    Fahrtlaengen statt ueber Fahrten.
    """
    steps = [(row["last"] - row["first"]) / row["span"]
             for row in rows if row["carries_trend"] and row["span"] > 0]
    if not steps:
        return {"alpha_per_hour": None, "n": 0, "falling": 0, "steps": []}
    return {"alpha_per_hour": round(derive._median(steps), 4),
            "n": len(steps),
            "falling": sum(1 for step in steps if step < 0),
            "steps": [round(step, 4) for step in steps]}


def alpha_by_hour(rows: list[dict[str, Any]]) -> dict[int, dict[str, Any]]:
    """Alpha je Fahrtstunde ueber alle Fahrten - Median, Streuung, Belegung."""
    pool: dict[int, list[float]] = {}
    for row in rows:
        for hour in row["hours"]:
            pool.setdefault(int(hour["hour"] or 0), []).append(float(hour["alpha"]))
    out: dict[int, dict[str, Any]] = {}
    for hour, values in sorted(pool.items()):
        mid = derive._median(values)
        mean = sum(values) / len(values)
        spread = (sum((x - mean) ** 2 for x in values) / len(values)) ** 0.5
        out[hour] = {"alpha": round(mid, 3), "n": len(values), "sd": round(spread, 3)}
    return out


def band(hour: int, entry: dict[str, Any]) -> dict[str, Any] | None:
    """Die Spanne je Stunde - ZWEI Anteile, quadratisch zusammengelegt.

    a) die Streuung zwischen den Fahrten an der Ablesestelle, ueber die
       mittlere Bruecke in Watt gebracht und als t-Band gefasst;
    b) die Unsicherheit der Umrechnung selbst: der Abfall gegenueber Stunde 1
       liegt je nach Bruecke zwischen (h-1)*0,92 und (h-1)*7,70 W.

    Quadratisch zusammengelegt ist eine SETZUNG: die beiden Anteile sind nicht
    streng unabhaengig, weil die Bruecke auch die Streuung umrechnet. Die
    Summe traefe im Backtest 8,8 von 10 statt 8,4, waere bei Stunde 4 aber
    +/- 23,7 statt +/- 16,9 W - fuer eine Zahl, die auf drei Fahrten steht, ist
    das mehr Breite, als die Belegung hergibt.
    """
    if not entry or entry["n"] < 2:
        return None
    watt_sd = entry["sd"] * (BRIDGE_FLAT / abs(DECLINE_PER_HOUR))
    degrees = entry["n"] - 1
    factor = T90.get(degrees, T90[max(T90)])
    spread = factor * watt_sd * (1 + 1 / entry["n"]) ** 0.5
    bridge = (hour - 1) * (BRIDGE_LOCAL - BRIDGE_GLOBAL) / 2.0
    half = (spread ** 2 + bridge ** 2) ** 0.5
    return {"half": round(half, 1),
            "from_spread": round(spread, 1),
            "from_bridge": round(bridge, 1),
            "n": entry["n"]}


def chain(anchor_watts: float | None, by_hour: dict[int, dict[str, Any]],
          step_watts: float = BRIDGE_FLAT,
          horizon: int = PLAN_HORIZON_HOURS) -> list[dict[str, Any]]:
    """Die Kette: Anker Stunde 1, danach der gemessene Verlauf - und darueber
    hinaus die Schaetzung bis `horizon`.

    ANKER UND VERLAUF, nicht p075 je Stunde. Die beiden sagen nicht dasselbe -
    bei Stunde 4 liegen sie 7,2 W auseinander, weil die Kette dort auf EINER
    Fahrt steht und die Ablesestelle auf drei. Gewaehlt ist Anker plus Verlauf,
    damit die Formelzeile unter der Zahl die Zahl auch ergibt.

    JENSEITS DES BESTANDS stehen ZWEI Zahlen nebeneinander, und beide werden
    hier gerechnet: `watts` schreibt den eigenen gemessenen Schritt fort,
    `form_watts` legt die Studienform (Gallo, ueber `fatigue.literature_factor`)
    an Stunde 1 an. Das Panel rechnet keine von beiden nach - es zeigt sie.
    `measured` sagt, auf welcher Seite der Grenze eine Zeile steht; eine
    geschaetzte Zeile traegt `n = 0` und KEIN Band, weil es nichts zu streuen
    gibt.
    """
    if anchor_watts is None:
        return []
    # Die Studienform haengt an Stunde 1 - dort steht der Anker, und dort steht
    # er GEMESSEN. Der Bezug auf die erste Stunde statt auf Dauer null ist
    # dieselbe Entscheidung wie in 0.58.1: bei Dauer null ist nie gefahren
    # worden.
    base = anchor_watts / fatigue.literature_factor(1.0)

    def _form(hour: int) -> float:
        return round(base * fatigue.literature_factor(float(hour)), 1)

    out = []
    for hour in sorted(by_hour):
        entry = by_hour[hour]
        out.append({"hours": hour,
                    "watts": round(anchor_watts - (hour - 1) * step_watts, 1),
                    "form_watts": _form(hour),
                    "alpha": entry["alpha"],
                    "n": entry["n"],
                    "measured": True,
                    "lower": None,
                    "band": band(hour, entry)})
    covered = max(by_hour) if by_hour else 0
    for hour in range(covered + 1, horizon + 1):
        watts = round(anchor_watts - (hour - 1) * step_watts, 1)
        form = _form(hour)
        out.append({"hours": hour,
                    "watts": watts,
                    "form_watts": form,
                    "alpha": None,
                    "n": 0,
                    "measured": False,
                    # WELCHE DER BEIDEN DIE VORSICHTIGE IST, steht als Zahl
                    # fest und nicht als Satz. Heute ist es die Studienform;
                    # wird der eigene Abfall steiler, kippt es, und der Text
                    # kippt mit.
                    "lower": "form" if form <= watts else "chain",
                    "band": None})
    return out


def groups(rows: list[dict[str, Any]], covered_until: int) -> dict[str, Any]:
    """Die drei Gruppen der Kachel - zwei Fahrtengruppen, eine Stundengruppe."""
    carries = [row for row in rows if row["carries_trend"]]
    supports = [row for row in rows if not row["carries_trend"]]

    def _short(row: dict[str, Any]) -> dict[str, Any]:
        return {"date": row["date"], "activity_id": row["activity_id"],
                "hours": len(row["hours"]),
                "alpha_from": row["first"], "alpha_to": row["last"]}

    return {"carries": [_short(row) for row in carries],
            "supports": [_short(row) for row in supports],
            "covered_until_hours": covered_until}


def curve(data: dict[str, Any]) -> dict[str, Any]:
    """Die ganze Kachel in einem Stueck."""
    rows = reading_rows(data)
    by_hour = alpha_by_hour(rows)
    trend = decline(rows)
    base = fatigue.curve(data) or {}
    plan = base.get("plan") or []
    anchor = plan[0].get("watts") if plan else None
    step = abs(trend["alpha_per_hour"] or DECLINE_PER_HOUR) * (BRIDGE_FLAT / abs(DECLINE_PER_HOUR))
    covered = max(by_hour) if by_hour else 0
    return {"on": v2_on(data),
            "switch_note": SWITCH_NOTE,
            "anchor_watts": anchor,
            "decline": trend,
            "step_watts": round(step, 2),
            "bridges": {"global": BRIDGE_GLOBAL, "flat": BRIDGE_FLAT,
                        "local": BRIDGE_LOCAL},
            "plan": chain(anchor, by_hour, step),
            "covered_until_hours": covered,
            "groups": groups(rows, covered),
            "rides_used": len(rows),
            # Was die Kachel BESCHRIFTET, kommt von hier - nicht aus dem
            # Frontend. Fensterbreite und Lastfenster sind Zahlen der
            # Rechenschicht; sie doppelt im Panel zu fuehren war der Fehler,
            # gegen den der Zahlen-Waechter seit 0.40.0 laeuft.
            "state_label": STATE_ON,
            "horizon_hours": PLAN_HORIZON_HOURS,
            "estimate_words": ESTIMATE_WORDS,
            "switch_words": SWITCH_WORDS,
            "band_share_words": BAND_SHARE_WORDS,
            "min_hours_for_trend": MIN_HOURS_FOR_TREND,
            "load_band_w": derive.DFA_LOAD_BAND_W,
            "watt_window_s": derive.DFA_WATT_WINDOW_S,
            "settings": SETTINGS_NOTE}


# WOERTLICH AUF DIE KACHEL. Jede Zeile ist eine Entscheidung ohne Messung.
SETTINGS_NOTE = [
    "der Schnitt nach Fahrtstunden (keine Quelle)",
    "das Lastfenster ± 5 W",
    "ein gerader Abfall ab Stunde 2 (bis dahin an 13 Fahrten belegt)",
    "die Umrechnung alpha → Watt (je nach Verfahren 0,9 bis 7,7 W je Stunde)",
    "die Spanne quadratisch aus Streuung und Umrechnung zusammengelegt",
    "die Studienform hinter dem belegten Bereich, verankert an Stunde 1",
]


# --- DER TROCKENLAUF ----------------------------------------------------------
# Heute ist der Schalter die einzige Art, den Bestand mit 120-s-Paarung zu
# sehen - und zugleich die Aktion, die abgesichert werden soll. Das ist
# strukturell unerfuellbar: man kann nicht vorher nachsehen, was danach
# herauskommt.
#
# Dieser Weg rechnet BEIDE Stellungen aus denselben Stroemen und fasst das
# Archiv NICHT an. Er nimmt die Stroeme entgegen, statt sie zu holen: das
# Holen gehoert dem Importweg, und eine zweite Fassung davon waere die zweite
# Wahrheit, die dieses Release gerade beseitigt.
#
# Er ueberlebt den Wegfall der Schalter. Verglichen werden zwei FENSTERBREITEN
# (0 und DFA_WATT_WINDOW_S), nicht zwei Schalterstellungen; faellt der Schalter
# weg, vergleicht derselbe Weg die naechste Umstellung.
DRY_FIELDS = ("p075", "r2", "slope", "load_w", "load_n", "load_alpha", "hr075")


def dry_hours(dfa: Any, watts: Any, heartrate: Any, keep: Any = None,
              window_s: int | None = None) -> list[dict[str, Any]]:
    """Je Fahrtstunde beide Achsen nebeneinander - ohne etwas abzulegen."""
    breite = derive.DFA_WATT_WINDOW_S if window_s is None else int(window_s)
    aus = derive.dfa_hours(dfa, watts, heartrate, keep=keep, watt_window_s=0)
    an = derive.dfa_hours(dfa, watts, heartrate, keep=keep, watt_window_s=breite)
    out = []
    for index, row in enumerate(aus):
        other = an[index] if index < len(an) else {}
        line: dict[str, Any] = {"hour": row.get("hour")}
        for field in DRY_FIELDS:
            line[field] = {"off": row.get(field), "on": other.get(field)}
        out.append(line)
    return out


def dry_run(data: dict[str, Any], streams: dict[str, Any],
            window_s: int | None = None) -> dict[str, Any]:
    """Beide Stellungen an EINEM Bestand - Stundenwerte UND Kachelzahlen.

    `streams` ist {activity_id: {"dfa_a1": [...], "watts": [...],
    "heartrate": [...], "keep": [...] | None}} und kommt von aussen.

    DAS ARCHIV WIRD NICHT ANGEFASST. Gerechnet wird auf zwei flachen Kopien,
    in die die frisch gerechneten Stunden gelegt werden; `data` selbst geht nur
    lesend hinein. Eine Pruefung haelt das fest (Archiv vorher/nachher
    identisch) - sonst waere die Zusicherung nur ein Satz.
    """
    breite = derive.DFA_WATT_WINDOW_S if window_s is None else int(window_s)
    je_fahrt = []
    schatten: dict[int, dict[str, Any]] = {0: {}, breite: {}}
    for key, chan in sorted((streams or {}).items()):
        keep = (chan or {}).get("keep")
        rows = dry_hours((chan or {}).get("dfa_a1"), (chan or {}).get("watts"),
                         (chan or {}).get("heartrate"), keep=keep, window_s=breite)
        je_fahrt.append({"activity_id": key, "hours": rows})
        for w in (0, breite):
            schatten[w][key] = derive.dfa_hours(
                (chan or {}).get("dfa_a1"), (chan or {}).get("watts"),
                (chan or {}).get("heartrate"), keep=keep, watt_window_s=w)

    kacheln: dict[str, Any] = {}
    for name, w in (("off", 0), ("on", breite)):
        schein = _shadow(data, schatten[w], w)
        alt = fatigue.curve(schein) or {}
        neu = curve(schein)
        kacheln[name] = {
            "window_s": w,
            "anchor_watts": alt.get("anchor_watts"), "anchor_n": alt.get("anchor_n"),
            "rides_used": alt.get("rides_used"),
            "plan": [{k: row.get(k) for k in ("hours", "watts", "n", "step", "band")}
                     for row in (alt.get("plan") or [])],
            "solid_until_hours": alt.get("plan_solid_until_hours"),
            "thin_until_hours": alt.get("plan_thin_until_hours"),
            "v2": {"anchor_watts": neu.get("anchor_watts"),
                   "step_watts": neu.get("step_watts"),
                   "decline": neu.get("decline"),
                   "covered_until_hours": neu.get("covered_until_hours"),
                   "rides_used": neu.get("rides_used"),
                   "groups": {"carries": len((neu.get("groups") or {}).get("carries") or []),
                              "supports": len((neu.get("groups") or {}).get("supports") or [])},
                   "plan": [{k: row.get(k) for k in
                             ("hours", "watts", "form_watts", "alpha", "n", "measured", "band")}
                            for row in (neu.get("plan") or [])]},
        }
    return {"window_s": breite, "rides": je_fahrt, "tiles": kacheln,
            "fields": list(DRY_FIELDS)}


def _shadow(data: dict[str, Any], hours_by_key: dict[str, Any],
            window_s: int) -> dict[str, Any]:
    """Ein Bestand, in dem die frisch gerechneten Stunden liegen - als KOPIE.

    Beide Lesewege werden bedient, weil beide vorkommen: `data["dfa"]` fuer
    die Auswahl ohne Marken und `section_marks` fuer die Auswahl mit ihnen.
    Angefasst wird nur die Kopie; die Originaldicts bleiben, wie sie sind.
    """
    dfa = {key: {**(((data.get("dfa") or {}).get(key)) or {}), "hours": rows}
           for key, rows in hours_by_key.items()}
    marks = {}
    for key, entry in (data.get("section_marks") or {}).items():
        if not isinstance(entry, dict):
            continue
        box = dict(entry.get("measure") or {})
        if key in hours_by_key and isinstance(box.get("endurance"), dict):
            box["endurance"] = {**box["endurance"], "hours": hours_by_key[key],
                                "w": window_s}
        marks[key] = {**entry, "measure": box}
    box = dict(data.get("settings") or {})
    box[V2_SWITCH] = bool(window_s)
    return {**data, "dfa": {**(data.get("dfa") or {}), **dfa},
            "section_marks": marks, "settings": box}
