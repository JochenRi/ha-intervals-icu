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
    from .const import STEERING_T90, T90_ONE_SIDED, T90_TWO_SIDED, T90_TWO_SIDED_INF
except ImportError:  # standalone (test suite loads this file directly)
    import derive  # type: ignore[no-redef]
    import fatigue  # type: ignore[no-redef]
    from const import (  # type: ignore[no-redef]
        STEERING_T90, T90_ONE_SIDED, T90_TWO_SIDED, T90_TWO_SIDED_INF,
    )

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

# DIE EINSEITIGE Tabelle, fuer `band()` weiter unten - die Kette der
# Ermuedung. Sie kommt aus `const.py`, wo BEIDE Quantile stehen; hier wird
# keine Liste gefuehrt. Bis 0.65.2 behauptete diese Stelle, es gebe ueberhaupt
# nur eine Tabelle - da stand die zweiseitige schon dreihundert Zeilen
# weiter unten in derselben Datei.
T90 = T90_ONE_SIDED


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
                    # Name, Umgebung und Dauer reisen seit 0.64.0 mit: die
                    # Fahrtenliste der Umkehrung zeigt sie, und sie nachtraeglich
                    # aus `activities` zu holen waere ein zweiter Weg zu
                    # denselben Feldern.
                    "name": ride.get("name"),
                    "virtual": bool(ride.get("virtual")),
                    "minutes": ride.get("minutes"),
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


def curve(data: dict[str, Any], today: str | None = None) -> dict[str, Any]:
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
            # DIE UMKEHRUNG (0.64.0). Sie reist im selben Block mit, weil
            # sie dieselbe Ablesestelle liest - nur die Frage ist gedreht.
            "reversal": reversal(data, today),
            "reversal_words": REVERSAL_WORDS,
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
    "die Umrechnung alpha → Watt: Setzung aus deinem Stufentest (Minuten, steigende Last), "
    "hier über Stunden angewendet — verfällt ohne neuen Test nach sechs Monaten",
    "die Spanne quadratisch aus Streuung und Umrechnung zusammengelegt",
    "die Studienform hinter dem belegten Bereich, verankert an Stunde 1",
    # 0.64.0: die Grenze der Umkehrung. Der Ausschlag ist GERECHNET und in
    # jeder Stunde gleich, weil die Grenze linear ueber dieselbe Umrechnung
    # eingeht - deshalb steht er als eine Zahl da und nicht als Spanne.
    "die Grenze alpha 1,0 (0,1 alpha mehr oder weniger sind rund 10 W)",
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


def tile_numbers(data: dict[str, Any]) -> dict[str, Any]:
    """WAS DIE KACHEL ZEIGT - an EINER Stelle, fuer alle, die es brauchen.

    Der Trockenlauf hatte bis 0.64.0 seine EIGENE Liste davon und trug deshalb
    nach dem Umbau auf die Umkehrung weiter die alte Kette: das Werkzeug, das
    vor dem Umlegen absichern soll, zeigte den Stand von vorgestern. Dieselbe
    Klasse wie der fehlende Schalter-Knopf in 0.63.0 - gebaut, aber ein Weg
    dorthin vergessen.

    Seitdem gibt es diese Funktion, und der Trockenlauf ruft sie. Wer der
    Kachel eine Zahl hinzufuegt, fuegt sie hier hinzu - und sie steht in
    beiden Stellungen des Trockenlaufs, ohne dass jemand daran denken muss.
    """
    alt = fatigue.curve(data) or {}
    neu = curve(data) or {}
    rv = neu.get("reversal") or {}
    return {
        # Die ALTE Kette, damit der Vergleich zwischen den Stellungen bleibt.
        "anchor_watts": alt.get("anchor_watts"), "anchor_n": alt.get("anchor_n"),
        "rides_used": alt.get("rides_used"),
        "plan": [{k: row.get(k) for k in ("hours", "watts", "n", "step", "band")}
                 for row in (alt.get("plan") or [])],
        "solid_until_hours": alt.get("plan_solid_until_hours"),
        "thin_until_hours": alt.get("plan_thin_until_hours"),
        # DIE UMKEHRUNG - was die Kachel seit 0.64.0 wirklich zeigt: je Stunde
        # die Zahl mit Band, daneben die Studienform, dazu Reichweite,
        # Fortschreibung, Umrechnung und die Gruppen der Fahrtenliste.
        "reversal": {
            "alpha_floor": rv.get("alpha_floor"),
            "floor_step": rv.get("floor_step"),
            "floor_step_watts": rv.get("floor_step_watts"),
            "min_rides_for_band": rv.get("min_rides_for_band"),
            "covered_until_hours": rv.get("covered_until_hours"),
            "slope_per_hour": rv.get("slope_per_hour"),
            "bridges": rv.get("bridges"),
            "plan": [{k: row.get(k) for k in ("hours", "watts", "load_w", "alpha",
                                              "n", "band", "form_watts", "observed")}
                     for row in (rv.get("plan") or [])],
            "groups": {"carries": sum(1 for r in (rv.get("rides") or []) if r.get("carries")),
                       "supports": sum(1 for r in (rv.get("rides") or [])
                                       if not r.get("carries"))},
            "rides": rv.get("rides") or [],
        },
        # Die Ablesestelle selbst, unveraendert: sie traegt den Verlauf.
        "v2": {"decline": neu.get("decline"), "rides_used": neu.get("rides_used"),
               "covered_until_hours": neu.get("covered_until_hours")},
    }


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
        kacheln[name] = tile_numbers(_shadow(data, schatten[w], w))
        kacheln[name]["window_s"] = w
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


# --- DIE UMKEHRUNG (0.64.0) ---------------------------------------------------
# DIE FRAGE IST GEDREHT. Nicht mehr "bei welcher Leistung liegt meine Schwelle"
# - das ist aus Grundlagenfahrten NICHT bestimmbar und seit dem 19.09. belegt:
# Johannes' Lastfenster ist 29 W breit, sichtbar waere der Effekt erst ab rund
# 150 W, und unterhalb davon kann die Probe "kein Zusammenhang" nicht von "zu
# schmal" unterscheiden. Sondern: "bei wieviel Watt bleibe ich ueber alpha 1,0,
# fuer eine Fahrt von X Stunden".
#
# WARUM DAS GEHT, WO DAS ANDERE NICHT GING: gerechnet wird aus Gemessenem, und
# der Weg ist kurz. Johannes faehrt bei alpha 1,33; bis 1,00 sind es 0,33.
# Ueber diese Strecke liegen Stufentest und Leiter nur 1,6 bis 6,9 W
# auseinander - bei der alten Frage (Weg 0,58 hinaus aus dem Datenbereich)
# waren es 65 W. Dieselben zwei Bruecken, zwei Groessenordnungen Unterschied:
# das ist der ganze Grund, warum diese Kachel eine Zahl nennen darf.
ALPHA_FLOOR = 1.0

# DER VERFALL DER UMRECHNUNG (0.67.0). Die einzige Quelle der Umrechnung ist
# der Stufentest; ohne einen markierten Test binnen dieser Frist zeigt die
# Kachel den Verlauf in alpha und sagt, dass ein Test fehlt. Sechs Monate,
# als Kalendermonate gerechnet (16.09. -> 16.03.): am Stichtag selbst ist er
# verfallen. Eine Setzung - es gibt keine Arbeit, die eine Haltbarkeit der
# Rampensteigung nennt; die Frist ist die Entscheidung vom 23.09.
RAMP_BRIDGE_MAX_AGE_MONTHS = 6


def _months_later(day: str, months: int) -> str:
    """Dasselbe Tagesdatum `months` Monate spaeter (Monatsende wird gekappt).

    Ohne das Modul `calendar`: im flach geladenen Pruefstand hiesse das die
    HA-Kalenderdatei dieses Pakets.
    """
    import datetime as _dt
    d = _dt.date.fromisoformat(str(day)[:10])
    m = d.month - 1 + months
    y, m = d.year + m // 12, m % 12 + 1
    letzter = (_dt.date(y + (m == 12), m % 12 + 1, 1) - _dt.timedelta(days=1)).day
    return _dt.date(y, m, min(d.day, letzter)).isoformat()

# DIE WOERTER DER KACHEL. Sie stehen hier, nicht im Panel - wie bei den
# Setzungen und den Schalterwoertern. Sichtbar ist EIN Satz; alles andere
# klappt auf, und zwar in der Reihenfolge, in der gefragt wird.
REVERSAL_WORDS = {
    # SETZUNG, nicht "gemessen" (0.67.0): gemessen sind Last und alpha der
    # Stunde; die Umrechnung von alpha zu Watt stammt aus dem Stufentest
    # (Minuten, steigende Last) und wird hier ueber Stunden angewendet. Dass
    # sie dort gilt, belegt keine Arbeit - siehe `literature`.
    "state": "Setzung: Umrechnung aus deinem Stufentest",
    "lead": "Für eine Fahrt von",
    "unit_note": "so lange bleibst du über alpha {floor}",
    # NICHT "8 von 10 Fahrten". Der Weglass-Rueckblick am Bestand trifft mit
    # diesem Band 70 % (Stunde 1) und 66 % (Stunde 2), nicht 80 - die
    # alpha-Verteilung zwischen den Fahrten hat schwerere Enden, als das
    # t-Band unterstellt. Die Zeile sagt deshalb, WIE das Band gebaut ist,
    # und verspricht keine Trefferquote, die es nicht haelt. Die Abhilfe
    # (empirisches Quantil statt t-Band) ist eine eigene Entscheidung und
    # steht als offener Punkt.
    # Die Quote steht nur da, wo sie nachpruefbar ist. Darunter sagt die Zeile,
    # WIE das Band gebaut ist - und verspricht nichts.
    "band_share": "8 von 10 Fahrten",
    "band_no_quote": "t-Band über {n} Fahrten",
    "no_band": "unter {min} Fahrten keine Spanne",
    "mean": ("Die Zahl ist keine Schwelle. Sie sagt: über eine Fahrt dieser Länge "
             "bleibt dein alpha im Mittel über {floor} — also im Bereich, in dem "
             "dein Herzschlag noch geordnet läuft. Gerechnet aus der Last, die du "
             "wirklich gehalten hast, und dem alpha, das dabei gemessen wurde."),
    "form": ("Die Studienform ist an deine erste Stunde gehängt und zeigt, wie eine "
             "Arbeit mit anderem Kollektiv den Abfall beschreibt. Bei dieser Frage "
             "laufen beide fast zusammen — das war bei der alten Frage nie so."),
    "rides": ("Es zählen nur Fahrten mit einer Ablesestelle: mindestens 20 Punkte im "
              "Lastfenster um die Leistung, die du gehalten hast. Ohne die gibt es "
              "keine Zahl, und die Stunde fehlt."),
    "others": ("Wieviel Watt ein Schritt von 1,0 alpha wert ist, sagt allein dein "
               "Stufentest — die Steigung seiner Fitgeraden zwischen alpha 0,75 und der "
               "persönlichen Schwelle. Die Blockleiter aus deinen Blockeinheiten steht "
               "daneben als Gegenprobe; sie rechnet seit 0.67.0 nicht mehr mit."),
    "ladder_note": ("Gegenprobe, rechnet nicht mit: die Leiter stand auf zwei Sprossen, die "
                    "weit von alpha 1,0 entfernt lagen (eine davon ein einzelner Tempo-Block), "
                    "und sie sprang um bis zu 60 W je alpha, wenn eine Sprosse fehlte."),
    "literature": ("Dass eine Steigung aus einer Rampe von Minuten auch in Stunde 3 einer "
                   "Grundlagenfahrt gilt, ist eine Annahme: van Rassel 2025, Gronwald 2024, "
                   "Ajayi 2025 und Rogers 2021 zeigen für Dauerbelastung, dass alpha bei "
                   "gleicher Last mit der Zeit fällt — keine gibt eine Umrechnung Watt je "
                   "alpha her. Deine eigenen Fahrten zeigen in diesem Bereich keinen "
                   "Zusammenhang zwischen alpha und Watt."),
    "missing_no_ramp": ("Kein markierter Stufentest — ohne ihn gibt es keine Umrechnung "
                        "und keine Wattzahl. Gezeigt wird dein Verlauf in alpha."),
    "missing_expired": ("Dein letzter Stufentest ist älter als {months} Monate ({date}) — "
                        "die Umrechnung ist verfallen. Ein neuer Test bringt die Wattzahl "
                        "zurück; bis dahin steht dein Verlauf in alpha."),
    "ramp_note": ("Umrechnung aus dem Stufentest vom {date}, Rampe {rate} W/min, "
                  "gemessen zwischen alpha {a_lo} und {a_hi}."),
    "why": ("Warum diese Frage und nicht „wo liegt meine Schwelle“: die alte Zahl "
            "musste von deinem alpha weit hinaus gerechnet werden, hier ist der Weg "
            "kurz. Über diese kurze Strecke sind sich die beiden Messungen fast "
            "einig, über die lange nicht."),
}

# Wie stark die Zahl an dieser Setzung haengt - GERECHNET, nicht behauptet, und
# sie steht in den Setzungen der Kachel: die Grenze geht linear ueber dieselbe
# Umrechnung ein, also ist der Ausschlag in JEDER Stunde gleich.
ALPHA_FLOOR_STEP = 0.1

# UNTER VIER FAHRTEN KEINE SPANNE. Am Bestand ergibt Stunde 4 (n=3, s=0,270)
# ein Band von +-92 W - das ist keine Auskunft, sondern ein Eingestaendnis mit
# Zahlen. Die Zeile verschwindet dann ganz, wie an der Stunde ohne Band.
MIN_RIDES_FOR_BAND = 4

# DIE TABELLENSEITE. Die einseitige Tabelle ist richtig fuer eine Aussage
# "hoechstens so viel", falsch fuer ein SYMMETRISCHES Band, das 80 %
# einschliessen soll. Dafuer braucht es das zweiseitige 90-%-Quantil, also
# t(0,95) einseitig. Mit der einseitigen Tabelle traf das Band am Bestand
# 70 % statt 80; mit dieser 88 %.
# Die Liste selbst steht in `const.py` neben der einseitigen (0.66.0); die
# beiden Namen hier sind nur der Zeiger darauf, damit `reversal_band` unten
# unveraendert lesbar bleibt.

# AB WIE VIELEN FAHRTEN EINE QUOTE ANGESAGT WIRD. Darunter steht keine - nicht
# weil das Band schlechter waere, sondern weil "8 von 10" an vier Fahrten nicht
# nachpruefbar ist: ein Weglass-Rueckblick hat dort drei Faelle.
BAND_QUOTE_MIN_N = 9


def bridges_alpha(data: dict[str, Any], today: str | None = None) -> dict[str, Any]:
    """Die Umrechnung alpha -> Watt: EINE Quelle, der Stufentest (0.67.0).

    Bis 0.66.3 wurden zwei Quellen gemittelt - der Stufentest und eine
    "Blockleiter" aus den Blockfamilien. Die Leiter stand am Bestand auf zwei
    Sprossen weit von alpha 1,0 (eine davon ein einzelner Tempo-Block), sprang
    ohne Regel um bis zu 60 W je alpha und trug die Haelfte der Kachelzahl.
    Entscheidung 23.09.: sie faellt weg. Sie wird weiter GERECHNET und reist
    als Gegenprobe mit (`ladder`, `ladder_note`), aber `mid` ist der
    Stufentest allein. Kein Stufentest, oder aelter als
    RAMP_BRIDGE_MAX_AGE_MONTHS: keine Umrechnung, keine Wattzahl - die Kachel
    sagt es (`missing`).

    Die Umrechnung ist eine SETZUNG: Steigung der Fitgeraden zwischen zwei
    Ablesungen einer Rampe (Minuten), angewendet ueber Stunden. Siehe
    REVERSAL_WORDS["literature"].
    """
    try:
        from . import blocks as blocks_lib
        from . import ramp_tests
    except ImportError:
        import blocks as blocks_lib  # type: ignore[no-redef]
        import ramp_tests  # type: ignore[no-redef]

    out: dict[str, Any] = {"ramp": None, "ramp_date": None, "ramp_note": None,
                           "ramp_expired": False, "ramp_expires": None,
                           "ladder": None, "ladder_note": REVERSAL_WORDS["ladder_note"],
                           "mid": None, "spread": None, "sources": [], "missing": None}
    row = ramp_tests.latest(data) or {}
    got = row.get("result") or {}
    eins, pers = got.get("hrvt1") or {}, got.get("hrvt1_pers") or {}
    wa, wb = eins.get("watts"), pers.get("watts")
    aa, ab = eins.get("alpha"), pers.get("alpha")
    if None not in (wa, wb, aa, ab) and abs(ab - aa) > 1e-6:
        out["ramp"] = round(abs((wa - wb) / (ab - aa)), 1)
        out["ramp_date"] = str(row.get("date") or "")[:10] or None
        rate = ((got.get("protocol") or {}).get("ramp_w_per_min")
                or (row.get("protocol") or {}).get("ramp_w_per_min"))
        out["ramp_note"] = REVERSAL_WORDS["ramp_note"].format(
            date=out["ramp_date"] or "?", rate=("%.1f" % rate).replace(".", ",") if rate else "?",
            a_lo=("%.2f" % min(aa, ab)).replace(".", ","), a_hi=("%.2f" % max(aa, ab)).replace(".", ","))
        if out["ramp_date"] and today:
            out["ramp_expires"] = _months_later(out["ramp_date"], RAMP_BRIDGE_MAX_AGE_MONTHS)
            out["ramp_expired"] = str(today)[:10] >= out["ramp_expires"]

    # DIE LEITER - nur noch Gegenprobe. Gerechnet wie bis 0.66.3, damit die
    # Zahl im Rechenweg steht; sie geht in `mid` NICHT ein.
    fams = (blocks_lib.series(data, with_other=False) or {}).get("families") or {}
    sprossen = []
    for box in fams.values():
        alphas, watts = [], []
        for point in box.get("points") or []:
            alphas += list((point.get("block_alphas") or [])[1:])
            watts += list((point.get("block_watts") or [])[1:])
        if alphas and watts:
            sprossen.append((derive._median(alphas), derive._median(watts)))
    sprossen.sort()
    if len(sprossen) >= 2:
        naechste = sorted(sprossen, key=lambda s: abs(s[0] - ALPHA_FLOOR))[:2]
        (a1, w1), (a2, w2) = sorted(naechste)
        if abs(a2 - a1) > 1e-6:
            out["ladder"] = round(abs((w2 - w1) / (a2 - a1)), 1)

    if out["ramp"] is None:
        out["missing"] = REVERSAL_WORDS["missing_no_ramp"]
    elif out["ramp_expired"]:
        out["missing"] = REVERSAL_WORDS["missing_expired"].format(
            months=RAMP_BRIDGE_MAX_AGE_MONTHS, date=out["ramp_date"])
    else:
        out["mid"] = out["ramp"]
        out["spread"] = 0.0
        out["sources"] = ["Stufentest"]
    return out


def reversal_band(values: list[float], bridge_half: float = 0.0) -> dict[str, Any] | None:
    """Das Band einer Stunde - ueber die FERTIGEN Wattzahlen, nicht ueber alpha.

    ZWEI FEHLER STECKTEN HIER BIS 0.64.2, und sie haben sich addiert:

    1. Gerechnet wurde die Streuung von ALPHA, mal der Umrechnung. Die
       gehaltene Last streut aber selbst - am Bestand um 8,7 W -, und die
       fertige Zahl je Fahrt um 15,9 W statt der 14,0 W, die aus alpha allein
       folgen. Die halbe Streuung fehlte also.
    2. Genommen wurde `STEERING_T90`, ein EINSEITIGES Quantil, fuer ein
       SYMMETRISCHES Band.

    Weglass-Rueckblick an Stunde 1 (n = 17): alpha + einseitig 70 %, alpha +
    zweiseitig 82 %, fertige Zahl + einseitig 76 %, fertige Zahl + zweiseitig
    88 %. Stunde 2 (n = 12): 66 / 75 / 83 / 91 %.

    `bridge_half` ist der systematische Anteil aus der Umrechnung - er ist
    KEINE Streuung zwischen Fahrten, sondern der halbe Abstand der beiden
    Messungen, und wird deshalb quadratisch dazugelegt statt mitgemittelt.
    """
    n = len(values)
    if n < MIN_RIDES_FOR_BAND:
        return None
    mean = sum(values) / n
    sd = (sum((x - mean) ** 2 for x in values) / (n - 1)) ** 0.5
    t = T90_TWO_SIDED.get(n - 1, T90_TWO_SIDED_INF)
    aus_fahrten = t * sd * (1 + 1 / n) ** 0.5
    return {"half": round((aus_fahrten ** 2 + (bridge_half or 0.0) ** 2) ** 0.5, 1),
            "from_spread": round(aus_fahrten, 1),
            "from_bridge": round(bridge_half or 0.0, 1), "n": n,
            "quote_shown": n >= BAND_QUOTE_MIN_N}


def reversal(data: dict[str, Any], today: str | None = None) -> dict[str, Any]:
    """Die Kette der Umkehrung: je Stunde die Watt, bei denen alpha 1,0 bleibt.

    Gerechnet aus der GEHALTENEN Last der Stunde und dem dort GEMESSENEN alpha
    - beides steht in der Stundenzeile, nichts wird gefittet und nichts
    extrapoliert. Die einzige Umrechnung ist die kurze Strecke von alpha zur
    Grenze, und die traegt zwei eigene Messungen.

    Das BAND kommt zu 88 bis 99 % aus der Streuung zwischen den Fahrten und nur
    zum Rest aus der Umrechnung; beide Anteile reisen getrennt mit, damit nicht
    zwei Unsicherheiten als eine erscheinen. Gerechnet wie bei den
    Blockkacheln - t(0,90; n-1) mal s mal Wurzel(1+1/n) -, und der Rueckhalt
    dafuer ist gemessen: im Weglass-Rueckblick trifft das Band 82 % (Stunde 1)
    und 85 % (Stunde 2) der weggelassenen Fahrten.
    """
    br = bridges_alpha(data, today)
    mid = br.get("mid")
    rows = reading_rows(data)
    je_stunde: dict[int, list[tuple[float, float]]] = {}
    for row in rows:
        for hour in row.get("hours") or []:
            alpha, last = hour.get("alpha"), hour.get("load_w")
            if alpha is None or last is None:
                continue
            je_stunde.setdefault(int(hour.get("hour") or 0), []).append((float(last), float(alpha)))
    je_stunde.pop(0, None)
    rides_out = [{"activity_id": row.get("activity_id"), "date": row.get("date"),
                  "name": row.get("name"), "virtual": bool(row.get("virtual")),
                  "minutes": row.get("minutes"),
                  "load_w": derive._median([h["load_w"] for h in (row.get("hours") or [])
                                            if h.get("load_w") is not None] or [0]),
                  "alpha_from": row.get("first"), "alpha_to": row.get("last"),
                  "hours": len(row.get("hours") or []),
                  "carries": bool(row.get("carries_trend"))}
                 for row in rows]
    if not je_stunde:
        return {"plan": [], "bridges": br, "alpha_floor": ALPHA_FLOOR,
                "floor_step": ALPHA_FLOOR_STEP, "floor_step_watts": None,
                "min_rides_for_band": MIN_RIDES_FOR_BAND, "covered_until_hours": 0,
                "slope_per_hour": None, "rides": rides_out}

    # OHNE UMRECHNUNG KEINE WATTZAHL - aber der Verlauf in alpha bleibt (0.67.0):
    # je Stunde Last, alpha und Belegung, Watt und Band leer. Die Kachel zeigt
    # dann den alpha-Verlauf und den Grund (`bridges.missing`).
    if mid is None:
        plan = [{"hours": hour, "watts": None, "band": None,
                 "load_w": round(derive._median([w for w, _ in je_stunde[hour]]), 1),
                 "alpha": round(derive._median([a for _, a in je_stunde[hour]]), 3),
                 "n": len(je_stunde[hour]), "observed": True, "lower": None, "form_watts": None}
                for hour in sorted(je_stunde)]
        return {"plan": plan, "bridges": br, "alpha_floor": ALPHA_FLOOR,
                "floor_step": ALPHA_FLOOR_STEP, "floor_step_watts": None,
                "min_rides_for_band": MIN_RIDES_FOR_BAND,
                "covered_until_hours": max(je_stunde),
                "slope_per_hour": None, "rides": rides_out}

    spanne = br.get("spread") or 0.0
    plan = []
    for hour in sorted(je_stunde):
        paare = je_stunde[hour]
        n = len(paare)
        last = derive._median([w for w, _ in paare])
        alpha = derive._median([a for _, a in paare])
        watts = last + (alpha - ALPHA_FLOOR) * mid
        # DIE FERTIGEN ZAHLEN je Fahrt gehen hinein, nicht die alphas: die
        # gehaltene Last streut mit, und genau die fehlte bis 0.64.2.
        band = reversal_band([w + (a - ALPHA_FLOOR) * mid for w, a in paare],
                             abs(alpha - ALPHA_FLOOR) * spanne / 2)
        # `observed` heisst: fuer diese Stunde gibt es Fahrten. Bis 0.66.3
        # hiess das Feld `measured` - und die Umrechnung darin ist nicht
        # gemessen, sondern gesetzt (REVERSAL_WORDS["state"]).
        plan.append({"hours": hour, "watts": round(watts, 1),
                     "load_w": round(last, 1), "alpha": round(alpha, 3),
                     "n": n, "band": band, "observed": True, "lower": None,
                     "form_watts": None})

    # Die Fortschreibung: eine Gerade durch die gemessenen Stunden. Daneben die
    # Studienform, an Stunde 1 verankert. KEINE ist die Wahrheit - und an
    # diesem Bestand laufen sie fast zusammen (bei sieben Stunden 0,8 W
    # auseinander), was bei der alten Frage nie der Fall war.
    xs = [row["hours"] for row in plan]
    ys = [row["watts"] for row in plan]
    steigung = None
    if len(xs) >= 2:
        mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
        nenner = sum((x - mx) ** 2 for x in xs)
        if nenner:
            steigung = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / nenner
    basis = ys[0] / fatigue.literature_factor(1.0)
    for row in plan:
        row["form_watts"] = round(basis * fatigue.literature_factor(float(row["hours"])), 1)
    covered = max(xs)
    if steigung is not None:
        achse = (sum(ys) / len(ys)) - steigung * (sum(xs) / len(xs))
        for hour in range(covered + 1, PLAN_HORIZON_HOURS + 1):
            gerade = round(achse + steigung * hour, 1)
            form = round(basis * fatigue.literature_factor(float(hour)), 1)
            plan.append({"hours": hour, "watts": gerade, "form_watts": form,
                         "load_w": None, "alpha": None, "n": 0, "band": None,
                         "observed": False,
                         "lower": "form" if form <= gerade else "chain"})
    return {"plan": plan, "bridges": br, "alpha_floor": ALPHA_FLOOR,
            "floor_step": ALPHA_FLOOR_STEP,
            "floor_step_watts": round(mid * ALPHA_FLOOR_STEP, 1),
            "min_rides_for_band": MIN_RIDES_FOR_BAND,
            "covered_until_hours": covered,
            "slope_per_hour": None if steigung is None else round(steigung, 1),
            "rides": rides_out}


# ═══ DIE GA-EINHEIT LIEST DIE UMKEHRUNG (0.68.0, Entscheidung 24.09.) ═══════════
# Bis 0.67.4 las die Grundlageneinheit die p075-Kette der alten Kachel
# (0,90 x Schwelle bei alpha 0,75) - eine Ablesung im Bereich, in dem alpha
# keine Last-Information traegt (§10), und eine andere Zahl als die Kachel
# bei Rechenschalter an (133 auf der Karte, 170 auf der Kachel). Jetzt: EIN
# Erzeuger mit der Kachel. Je Stunde der Umkehrung:
#   Ziel   = Last + (alpha - ZIEL_ALPHA) x Umrechnung
#   Grenze = Last + (alpha - GRENZ_ALPHA) x Umrechnung
# Die alpha-Werte sind EINSTELLUNGEN des Athleten (Options-Flow, Regel 10):
# Grenze vorbelegt 1,0, Ziel leer - dann zeigt die Einheit nur die Grenze.
# Die 0,90 faellt weg. Ohne gueltigen Stufentest: keine Zahlen, die Einheit
# faellt beschriftet auf die FTP.
GA_WORDS = {
    "state": "Setzung: Umrechnung aus deinem Stufentest, alpha-Werte aus deiner eigenen Regel",
    "literature": ("Die Obergrenze der Zone 1 liegt in der Literatur bei alpha 0,75 "
                   "(Rogers u. a. 2021). Deine Grenze 1,0 und dein Ziel liegen darunter — "
                   "sie sind deine Regel, keine Literaturschwellen."),
    "lead": "fahr ~{target} W, nicht über {limit} W",
    "lead_limit_only": "nicht über {limit} W",
}


def ga_targets(data: dict[str, Any], today: str | None = None,
               limit_alpha: float = ALPHA_FLOOR, target_alpha: float | None = None) -> dict[str, Any]:
    """Ziel und Grenze je Fahrtstunde aus der Umkehrung - der eine Erzeuger."""
    rv = reversal(data, today)
    br = rv.get("bridges") or {}
    mid = br.get("mid")
    out: dict[str, Any] = {"mid": mid, "limit_alpha": float(limit_alpha),
                           "target_alpha": (None if target_alpha is None else float(target_alpha)),
                           "missing": br.get("missing"), "words": GA_WORDS, "hours": []}
    if mid is None:
        return out
    for row in rv.get("plan") or []:
        if not row.get("observed") or row.get("load_w") is None or row.get("alpha") is None:
            continue
        last, alpha = float(row["load_w"]), float(row["alpha"])
        out["hours"].append({
            "hours": int(row["hours"]), "n": int(row.get("n") or 0),
            "load_w": round(last, 1), "alpha": round(alpha, 3),
            "limit_w": round(last + (alpha - float(limit_alpha)) * mid, 1),
            "target_w": (None if target_alpha is None
                         else round(last + (alpha - float(target_alpha)) * mid, 1)),
        })
    return out

