"""Die Ermuedungskurve der aeroben Schwelle (docs/ausbau.md Paket L).

ZWEI QUELLEN, GETRENNT GEHALTEN - das ist der ganze Bau:

* Der ANKER ist gemessen. P(alpha = 0,75) aus den eigenen Fahrten, nach der
  Repraesentantenmethode (Andriolo/Rummel/Gronwald, Sensors 2024, 24, 4468),
  je Fahrtstunde in ``derive.dfa_hours()``.
* Die FORM ist Literatur. Gallo et al., Eur J Appl Physiol 124:2353-2364
  (2024): quadratischer Abfall, aus den publizierten Gruppenmittelwerten
  rekonstruiert. Sie wird am eigenen Anker VERANKERT, nicht an ihm geprueft.

Was Messung ist und was Setzung, bleibt in jedem Feld unterscheidbar. Ein
Feld, das beides mischte, waere genau die Zahl, der man spaeter nicht mehr
ansieht, woher sie kommt.

NICHT GEMESSEN WIRD DIE KURVE SELBST. Drei Anlaeufe sind daran gescheitert
(L0); der dritte hat gezeigt, dass der Bestand die Absicherung nicht hergibt -
erwarteter Effekt 3 bis 4 W je Stunde gegen 21,6 W Streuung, dafuer braeuchte
es rund 150 gepaarte Fahrten statt 21. Die Messung widerspricht der Literatur
nicht, sie kann sie nur nicht bestaetigen. Beides gilt, und beides steht dran.
"""

from __future__ import annotations

from statistics import median
from typing import Any

try:  # inside the package (Home Assistant)
    from . import derive
    from . import section_marks as marks_lib
    from .const import (
        FATIGUE_MAX_ABOVE_Z2,
        FATIGUE_MIN_MINUTES,
        FATIGUE_MIN_PAIRS,
        FATIGUE_SOLID_MIN_RIDES,
        FATIGUE_THIN_MIN_RIDES,
    )
except ImportError:  # standalone (test suite loads this file directly)
    import derive  # type: ignore[no-redef]
    import section_marks as marks_lib  # type: ignore[no-redef]
    from const import (  # type: ignore[no-redef]
        FATIGUE_MAX_ABOVE_Z2,
        FATIGUE_MIN_MINUTES,
        FATIGUE_MIN_PAIRS,
        FATIGUE_SOLID_MIN_RIDES,
        FATIGUE_THIN_MIN_RIDES,
    )

# Gallo et al. 2024, aus den Gruppenmittelwerten rekonstruiert: ausgeruht
# 184 +- 35 W, nach einer Stunde 181 +- 37 (p = 0,290), unmittelbar vor dem
# Abbruch 165 +- 34 (p < 0,001) bei t ~ 3,4 h.
#     P(t) / P0 = 1 - 0,0104 * t - 0,0059 * t^2
# Die Probe, die sie traegt: -5 % nach 130 min gegen publizierte 139 +- 78 min,
# aus einer UNABHAENGIGEN Rechnung (individuelle Fits). Sensitivitaet gegen die
# Annahme zum letzten Testzeitpunkt: 3,0 h -> 119 min, 3,8 h -> 140 min.
# Die FORM ist belastbar, die Punktgenauigkeit ist es nicht.
GALLO_LINEAR = 0.0104
GALLO_QUADRATIC = 0.0059
# Die publizierte Streuung des -5-%-Zeitpunkts: 139 +- 78 min. Sie ist die
# Quelle des Unsicherheitsbands - NICHT eine gesetzte Bandbreite. Gerechnet
# wird sie als Streckung der ZEITACHSE derselben Form: eine Person, die ihre
# 5 % schon nach 61 min verliert, faellt entsprechend schneller, eine mit
# 217 min entsprechend langsamer. Daraus folgt die Breite, statt sie zu setzen -
# bei drei Stunden ergibt das rund 40 W, und genau dort darf die Kachel keine
# Punktgenauigkeit mehr vortaeuschen.
GALLO_T5_MIN = 139.0
GALLO_T5_SD = 78.0

# --- L1b: die HF-Korrektur ----------------------------------------------------
# Stevenson, Kilding, Plews, Maunder (Eur J Appl Physiol 2022): nach zwei
# Stunden fiel die Schwellenleistung von 217 auf 196 W, waehrend die
# Schwellen-HERZFREQUENZ von 142 auf 151 bpm STIEG. Praktisch ist das
# wichtiger als die Kurve selbst - wer sich nach Stunden noch an die
# ausgeruhte Schwellen-HF haelt, faehrt zu hart.
#
# REINE SETZUNG, und sie bleibt es. Am eigenen Bestand ist der Anstieg nicht
# wiederfindbar, und der Grund ist sauber: Stevenson misst im standardisierten
# Stufentest, wo die Belastung kontrolliert ist. Im Feld ist sie das nie - die
# HF-Aenderung folgt dort fast vollstaendig der Leistungsaenderung. Die Aussage
# "was das Panel als aerobe HF nennt, gilt fuer den ausgeruhten Zustand" bleibt
# richtig; sie ist an Alltagsfahrten nur nicht pruefbar, und das steht dabei.
STEVENSON_HR_REST = 142.0
STEVENSON_HR_2H = 151.0
STEVENSON_HOURS = 2.0


def _t5_hours() -> float:
    """Wann erreicht die Form selbst -5 %? Gerechnet, nicht eingetragen."""
    step, t = 1.0 / 60.0, 0.0
    while t < 10.0:
        if literature_factor(t) <= 0.95:
            return t
        t += step
    return 10.0


def literature_factor(hours: float) -> float:
    """Anteil der Ausgangsleistung nach ``hours`` Stunden - reine Setzung."""
    return 1.0 - GALLO_LINEAR * hours - GALLO_QUADRATIC * hours * hours


# Was an der duennen Zone stehen MUSS. Der Auswahleffekt schliesst sich dort
# nicht mit mehr Fahrten: eine Fahrt, die vier Stunden ging, war eine besondere
# Fahrt. Am Bestand vom 15.09.2026 liefern 83 % der Fahrten eine zweite Stunde,
# aber nur 33 % eine dritte und 17 % eine vierte - fuer neun Vergleiche in
# Stunde 4 braeuchte es rund vierundfuenfzig Fahrten, und sie waeren alle vom
# selben seltenen Typ.
SELECTION_NOTE = ("Ab hier stammt die Zahl aus den wenigen Fahrten, die so lang "
                  "geworden sind — und eine Fahrt, die vier Stunden ging, war "
                  "keine durchschnittliche Fahrt. Das ist keine Lücke, die sich "
                  "mit mehr Fahrten schließt.")

# Die bekannte Schwaeche der Achse, und sie gehoert an die Kachel, nicht nur in
# die Spezifikation.
AXIS_NOTE = ("Die Achse ist reine Fahrtzeit. Ein Überblicksartikel von 2025 "
             "(Eur J Appl Physiol) zeigt, dass die INTENSITÄT der Vorbelastung "
             "stärker wirkt als ihre Menge — Stunde 3 einer lockeren Fahrt ist "
             "nicht Stunde 3 einer harten. Diese Kurve unterscheidet das nicht.")


def _plan_chain(used: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Die Leitzahl: welche Leistung haelt ueber eine GEPLANTE Dauer.

    ANDERE LESERICHTUNG, dieselbe Rechnung. Der Athlet plant keine einzelne
    Fahrtstunde - er plant eine Fahrt. Gesucht ist die Leistung, die er von
    Anfang an treten kann und die am ENDE noch im Bereich liegt, nicht die
    Schwelle zu Beginn und auch nicht der Abstand zwischen zwei Stunden.

    VERKETTET AUS DEN GEPAARTEN SCHRITTEN, nicht aus den rohen Stundenmedianen.
    Die rohen Mediane stammen aus verschiedenen Fahrten - Stunde 1 aus zehn
    Tagen, Stunde 4 aus zweien -, und das ist genau der Auswahleffekt, gegen
    den die Paarung gebaut wurde. Der Unterschied ist messbar: am Bestand vom
    15.09.2026 sagt der rohe Median fuer zwei Stunden 140,1 W, die Kette
    141,3 W. Die Kette ist die Zahl, die die eigene Einwendung ueberlebt.
    """
    by_hour: dict[int, list[float]] = {}
    for ride in used:
        for row in ride["hours"]:
            value = row.get("p075")
            if value is not None:
                by_hour.setdefault(int(row["hour"]), []).append(float(value))
    if 1 not in by_hour:
        return []
    out = [{"hours": 1, "watts": median(by_hour[1]), "n": len(by_hour[1]),
            "step": None, "step_n": None}]
    current = median(by_hour[1])
    hour = 1
    while True:
        deltas = []
        for ride in used:
            rows = {int(r["hour"]): r.get("p075") for r in ride["hours"]}
            here, nxt = rows.get(hour), rows.get(hour + 1)
            if here is not None and nxt is not None:
                deltas.append(float(nxt) - float(here))
        if not deltas:
            break
        current += median(deltas)
        hour += 1
        out.append({"hours": hour, "watts": current,
                    "n": len(by_hour.get(hour) or []),
                    "step": median(deltas), "step_n": len(deltas)})
    return out


def solid_until(plan: list[dict[str, Any]]) -> int:
    """Bis wohin die Linie DURCHGEZOGEN ist - bis zum ERSTEN Riss.

    Eigene Funktion, weil sie inline nicht pruefbar war: eine Fassung, die den
    Riss ueberspringt und den letzten festen Punkt nimmt, kam durch die
    Gegenprobe (Mutation M28, 0 Fehler). Eine Linie mit einem Loch, die
    dahinter wieder durchgezogen ist, behauptet Sicherheit, die es in der
    Mitte nicht gibt.
    """
    out = 0
    for row in plan:
        if row.get("band") != "solid":
            break
        out = int(row.get("hours") or 0)
    return out


# DER SCHALTER. Er steht im Archiv, nicht in den Integrationsoptionen: er
# gehoert zu den Daten, die er umschaltet, und er wird an der Kachel bedient,
# an der man die Folge sieht.
CURVE_SWITCH = "curve_from_marks"

# WAS SICH BEIM UMLEGEN AENDERT, und der wichtigste Teil sind nicht die Zahlen.
# Die LESERICHTUNG ist eine andere - ohne diesen Satz haelt der Athlet die
# verschobenen Werte fuer einen Rechenfehler.
SWITCH_NOTE = ("Umgelegt liest die Kurve NUR deine markierten Abschnitte — und "
               "sie liest sich anders: die große Zahl sagt, welche Leistung du "
               "über eine Fahrt DIESER LÄNGE hältst, nicht was in Stunde X war. "
               "Beides zusammen verschiebt die Zahlen; das ist kein "
               "Rechenfehler, sondern eine andere Frage.")

# Warum nur die markierten zaehlen, wenn der Schalter aus ist: die alte Auswahl
# schliesst strukturierte Einheiten VOR der Messung aus (derive-Bauteil aus L0
# Runde 3, +4 gegen +42 W). Sie bleibt als Rueckfall stehen, solange der
# Schalter aus sein kann - `fatigue_curve_reason` und `above_endurance_share`
# sind EIN Bauteil, nicht zwei.
NOT_MEASURED_REASON = "not_measured"

# DAS WORT ZUM GRUND, aus dem Modul, das den Grund vergibt. In 0.56.0 kannte
# das Panel nur die Gruende der Namenserkennung und zeigte fuer diesen den
# Rohschluessel "not_measured" (§7). Der Satz sagt nicht "noch nicht gemessen":
# eine Messung kann auch VERWORFEN sein (Versionssprung, Drift, Umhaken), und
# welches davon, steht heute nicht unterscheidbar im Eintrag.
DROPPED_WORDS: dict[str, tuple[str, str]] = {
    NOT_MEASURED_REASON: (
        "markiert, ohne gültige Messung",
        "die Kurve hat für diese Fahrt nichts zu lesen — im Aktivitätsdetail "
        "auf „übernehmen und messen“"),
}


def _flipped(data: dict[str, Any]) -> dict[str, Any]:
    """Dieselben Daten, der Schalter andersherum - OHNE den Bestand anzufassen.

    Eine flache Kopie mit ausgetauschtem `settings`: die Fahrten und Marken
    bleiben dieselben Objekte, nur die Stellung ist eine andere. So kostet die
    Gegenrechnung nichts und kann den Bestand auch nicht versehentlich aendern.
    """
    box = dict((data or {}).get("settings") or {})
    box[CURVE_SWITCH] = not curve_from_marks(data)
    return {**(data or {}), "settings": box}


def curve_from_marks(data: dict[str, Any]) -> bool:
    """Steht der Kurvenschalter auf AN?"""
    box = (data or {}).get("settings")
    return bool(isinstance(box, dict) and box.get(CURVE_SWITCH))


def _marked_rides(data: dict[str, Any]) -> dict[str, Any]:
    """Die Fahrten aus den MARKEN - eine Fahrt zaehlt, wenn sie gemessen ist.

    Kein Filter, keine Heuristik: was markiert und gemessen ist, geht in die
    Rechnung; was nicht markiert ist, kommt gar nicht erst vor. Markiert und
    noch nicht gemessen ist NAMENTLICH nachvollziehbar, statt still zu fehlen.
    """
    used: list[dict[str, Any]] = []
    dropped: dict[str, list[dict[str, Any]]] = {}
    marks_box = (data.get("section_marks") or {})
    for key, entry in marks_box.items():
        activity = (data.get("activities") or {}).get(key) or {}
        day = str(activity.get("start_date_local") or entry.get("date") or "")[:10]
        row = {"activity_id": key, "date": day, "name": activity.get("name"),
               "above_z2": None,
               "minutes": round((activity.get("moving_time") or 0) / 60)}
        if not marks_lib.marked(entry, "endurance"):
            continue
        got = marks_lib.measurement(entry, "endurance") or {}
        hours = got.get("hours")
        if not isinstance(hours, list) or not hours:
            dropped.setdefault(NOT_MEASURED_REASON, []).append(row)
            continue
        used.append({**row, "hours": hours})
    used.sort(key=lambda r: r["date"])
    for items in dropped.values():
        items.sort(key=lambda r: r["date"])
    return {"used": used, "dropped": dropped}


def rides(data: dict[str, Any]) -> dict[str, Any]:
    """Welche Fahrten ihren Stundenverlauf hergeben - und welche warum nicht.

    Der Ausschluss sitzt VOR der Messung. Ein Guetekriterium hinterher hat in
    L0 Runde 3 die Auswahl genau auf die strukturierten Einheiten verengt und
    den Stoerer eingesammelt statt ihn auszuschliessen: die -31,9 W waren der
    Trainingsplan, nicht die Ermuedung.
    """
    if curve_from_marks(data):
        return _marked_rides(data)
    used: list[dict[str, Any]] = []
    dropped: dict[str, list[dict[str, Any]]] = {}
    for key, activity in (data.get("activities") or {}).items():
        summary = (data.get("dfa") or {}).get(key) or {}
        hours = summary.get("hours") or []
        day = str(activity.get("start_date_local") or "")[:10]
        reason = derive.fatigue_curve_reason(activity)
        if reason is None and not hours:
            reason = "no_dfa"
        if reason is not None:
            # Jede ausgeschlossene Fahrt bleibt NAMENTLICH nachvollziehbar,
            # mit ihrer Zahl daneben. Sonst sucht der Athlet in zwei Wochen,
            # warum eine Fahrt fehlt, an die er sich erinnert.
            dropped.setdefault(reason, []).append({
                "activity_id": key,
                "date": day,
                "name": activity.get("name"),
                "above_z2": (lambda v: round(v, 1) if v is not None else None)(
                    derive.above_endurance_share(activity)
                ),
                "minutes": round((activity.get("moving_time") or 0) / 60),
            })
            continue
        used.append({
            "activity_id": key,
            "date": day,
            "name": activity.get("name"),
            "hours": hours,
        })
    used.sort(key=lambda row: row["date"])
    for items in dropped.values():
        items.sort(key=lambda row: row["date"])
    return {"used": used, "dropped": dropped}


def _band(count: int) -> str:
    """Welcher Darstellungsbereich - AUS DER BELEGUNG, nicht aus der Stunde."""
    if count >= FATIGUE_SOLID_MIN_RIDES:
        return "solid"
    if count >= FATIGUE_THIN_MIN_RIDES:
        return "thin"
    return "dashed"


def curve(data: dict[str, Any], aerobic_hr: float | None = None,
          aerobic_power: float | None = None) -> dict[str, Any]:
    """Anker, gemessene Stundenwerte, Literaturform und Belegungsgrenzen."""
    selection = rides(data)
    by_hour: dict[int, list[float]] = {}
    for ride in selection["used"]:
        for row in ride["hours"]:
            value = row.get("p075")
            if value is not None:
                by_hour.setdefault(int(row["hour"]), []).append(float(value))

    by_hour_hr: dict[int, list[float]] = {}
    for ride in selection["used"]:
        for row in ride["hours"]:
            value = row.get("hr075")
            if value is not None:
                by_hour_hr.setdefault(int(row["hour"]), []).append(float(value))

    measured = []
    for hour in sorted(by_hour):
        values = by_hour[hour]
        measured.append({
            "hour": hour,
            # Die Mitte der Fahrtstunde ist der Zeitpunkt, fuer den der Wert
            # gilt - Stunde 1 ist t = 0,5 h, nicht t = 0.
            "t": hour - 0.5,
            "watts": round(median(values), 1),
            "n": len(values),
            "band": _band(len(values)),
            # Die gemessene Gegenprobe zu Stevenson - aus DENSELBEN Fahrten,
            # damit "nicht wiederfindbar" eine eigene Zahl ist und kein Zitat.
            "hr": round(median(by_hour_hr[hour]), 1) if by_hour_hr.get(hour) else None,
            "hr_n": len(by_hour_hr.get(hour) or []),
        })

    # --- GEPAART, als Gegenrechnung zur ungepaarten Reihe oben ---------------
    # Die Mediane je Stunde stammen aus VERSCHIEDENEN Fahrten. Das ist genau
    # das Laengenartefakt aus J1 - und hier hat es eine eigene Quelle: p075
    # wird nur ausgegeben, wenn 0,75 im gefahrenen alpha-Bereich LIEGT (keine
    # Extrapolation, und das bleibt richtig). Ausgeruht liegt alpha hoch, die
    # Schwelle wird in Stunde 1 also nur beruehrt, wenn HAERTER gefahren wurde.
    # Der Schutz vor Hochrechnung erzeugt damit eine Auswahl, und die Auswahl
    # korreliert mit der gesuchten Groesse. Gepaart gerechnet ist jede Fahrt
    # ihre eigene Kontrolle.
    paired = []
    for hour in sorted(by_hour):
        deltas = []
        for ride in selection["used"]:
            rows = {int(r["hour"]): r.get("p075") for r in ride["hours"]}
            here, nxt = rows.get(hour), rows.get(hour + 1)
            if here is not None and nxt is not None:
                deltas.append(float(nxt) - float(here))
        if deltas:
            paired.append({
                "from_hour": hour, "to_hour": hour + 1,
                "delta": round(median(deltas), 1), "n": len(deltas),
                "enough": len(deltas) >= FATIGUE_MIN_PAIRS,
            })

    # DAS ERKENNUNGSZEICHEN, als Regel statt als Beobachtung: die Belegung
    # zeitlich aufeinanderfolgender Bins muss MONOTON FALLEN - jede Fahrt mit
    # einer zweiten Stunde hat auch eine erste. Steigt sie, liegt ein
    # Auswahleffekt vor, und dann ist der ungepaarte Verlauf kein Verlauf.
    counts = [row["n"] for row in measured]
    rising = [
        {"hour": measured[i + 1]["hour"], "n": counts[i + 1], "previous": counts[i]}
        for i in range(len(counts) - 1) if counts[i + 1] > counts[i]
    ]

    # --- DIE LEITZAHL UND IHRE WEGLASSPROBE ---------------------------------
    # Die Grenze zwischen "gemessen" und "duenn" wird hier nicht GESETZT,
    # sondern GEMESSEN, und zwar am Bestand selbst: eine Zahl gilt als
    # gemessen, wenn KEINE EINZELNE FAHRT sie um mehr verschiebt als der
    # Schritt gross ist, auf dem sie sitzt. Das Verhaeltnis ist massstabsfrei -
    # eine feste Wattgrenze saenke mit der Wurzel aus der Fahrtenzahl von
    # allein und waere in einem halben Jahr wirkungslos.
    #
    # Am Bestand vom 15.09.2026 (zwoelf Fahrten) sagt die Regel:
    #   1 h  Verschiebung 0,45 W   Verhaeltnis 0,05   gemessen
    #   2 h  Verschiebung 3,05 W   Verhaeltnis 0,37   gemessen
    #   3 h  Verschiebung 10,0 W   Verhaeltnis 2,94   duenn
    #   4 h  Verschiebung 14,4 W   Verhaeltnis 10,7   duenn
    # Das deckt sich mit der Belegung der Schritte (10 · 9 · 3 · 2) - zwei
    # voneinander unabhaengige Kriterien setzen die Grenze an dieselbe Stelle.
    # Die Uebereinstimmung ist der Grund, ihr zu trauen.
    plan = _plan_chain(selection["used"])
    if plan:
        keys = [ride["activity_id"] for ride in selection["used"]]
        shifts: dict[int, float] = {}
        for key in keys:
            ohne = _plan_chain([r for r in selection["used"] if r["activity_id"] != key])
            for row in ohne:
                base_row = next((b for b in plan if b["hours"] == row["hours"]), None)
                if base_row is not None:
                    shifts[row["hours"]] = max(shifts.get(row["hours"], 0.0),
                                               abs(row["watts"] - base_row["watts"]))
        for index, row in enumerate(plan):
            shift = shifts.get(row["hours"])
            # Die erste Stunde hat keinen eigenen Schritt - sie wird an dem
            # gemessen, der von ihr WEGFUEHRT. Ohne Nachfolger ist sie ein
            # einzelner Punkt und nie "gemessen".
            scale = abs(row["step"]) if row["step"] else (
                abs(plan[index + 1]["step"] or 0.0) if index + 1 < len(plan) else 0.0)
            ratio = (shift / scale) if (shift is not None and scale) else None
            row["loo_shift"] = round(shift, 2) if shift is not None else None
            row["loo_ratio"] = round(ratio, 2) if ratio is not None else None
            row["band"] = "solid" if (ratio is not None and ratio < 1.0) else "thin"
        # Gerundet wird ERST HIER, nach Kette, Weglassprobe und Anker.


    anchor = measured[0]["watts"] if measured else None
    anchor_n = measured[0]["n"] if measured else 0
    literature = []
    if anchor is not None:
        # DER ANKER SITZT AM LETZTEN GETRAGENEN PUNKT DER KETTE, nicht mehr an
        # der ersten Stunde. Die Studienform ist die Fortsetzung dort, wo die
        # eigenen Daten aufhoeren - haengt sie am Anfang, laeuft sie quer durch
        # den gemessenen Bereich und behauptet neben jeder eigenen Zahl eine
        # zweite. Angehaengt ans Ende sagt sie genau das, was sie kann: "so
        # ginge es weiter, wenn du weiterfaehrst".
        #
        # Die Zeitachse ist dabei die GEPLANTE DAUER, nicht die Stundenmitte:
        # der Kettenwert fuer drei Stunden gilt fuer eine Fahrt von drei
        # Stunden, also t = 3,0. Die Stundenmitte (t = hour - 0,5) gehoert zur
        # ungepaarten Reihe darueber und bleibt dort.
        tail = plan[-1] if plan else None
        if tail is not None:
            base = tail["watts"] / literature_factor(float(tail["hours"]))  # ungerundet
            attach_t = float(tail["hours"])
        else:
            base = anchor / literature_factor(measured[0]["t"])
            attach_t = measured[0]["t"]
        # Die Streuung skaliert den VERLUST, nicht die Zeitachse. Eine erste
        # Fassung streckte die Zeit (f(t * k)) - das laeuft jenseits des
        # Studienhorizonts von rund 3,4 h aus der Form heraus, und die untere
        # Bandkante stieg dort UEBER die Kurve. Eine Unsicherheit, die sich
        # selbst ueberholt, ist keine.
        fast = GALLO_T5_MIN / (GALLO_T5_MIN - GALLO_T5_SD)
        slow = GALLO_T5_MIN / (GALLO_T5_MIN + GALLO_T5_SD)

        def _point(t: float, hour: int | None) -> dict[str, Any]:
            return {
                "hour": hour, "t": round(t, 2),
                # JENSEITS des eigenen Bestands ist die Zahl reine Setzung.
                # Das Feld sagt es, statt es der Zeichnung zu ueberlassen -
                # eine gestrichelte Linie ist eine Gestaltung, kein Befund.
                "beyond": t > attach_t + 0.01,
                "watts": round(base * literature_factor(t), 1),
                # lo/hi sind die SETZUNG mit ihrer publizierten Streuung -
                # getrennt vom Mittelwert, damit das Band nie wie eine
                # zweite Messung aussieht.
                "lo": round(base * (1.0 - (1.0 - literature_factor(t)) * fast), 1),
                "hi": round(base * (1.0 - (1.0 - literature_factor(t)) * slow), 1),
            }

        for row in measured:
            literature.append(_point(row["t"], row["hour"]))
        # Feineres Raster als die Messstunden: der Zeiger soll ueber der Kurve
        # gleiten, nicht auf vier Punkte einrasten. Payload-Seite, damit
        # chart() unberuehrt bleibt.
        last = max(attach_t, measured[-1]["t"])
        t = 0.25
        while t <= last + 2.0:
            if all(abs(t - row["t"]) > 0.01 for row in measured):
                literature.append(_point(t, None))
            t += 0.25
        # KEINE ZAHL UNTERHALB DES BESTANDS. Das Feinraster begann fest bei
        # 0,25 h, unabhaengig davon, wo die eigenen Daten anfangen - und dort
        # unten stand eine Studienform-Zahl HOEHER als jede gemessene, in einem
        # Zeitbereich, in dem nie gefahren wurde.
        #
        # Nach unten gelesen beantwortet die Form eine ANDERE Frage: sie laeuft
        # auf den ausgeruhten Ausgangswert zu, und den gibt es schon - als
        # `anchor_base`, beschriftet. Zwei Wege zu einer Groesse ist 0.46.0.
        # Dazu traegt die Achse die Aussage dort nicht: "172 W ueber eine
        # Viertelstunde" ist keine aerobe Schwelle mehr.
        #
        # Gestrichen statt gekennzeichnet: eine Kennzeichnung wuerde die Zahl
        # RECHTFERTIGEN statt sie zu entfernen - dieselbe Entscheidung wie beim
        # Messknopf, der fuer Blockfamilien lieber gar nichts rechnet.
        #
        # DIE GRENZE HAENGT AM ERSTEN PLAN-PUNKT, nicht am ersten gemessenen:
        # `measured` traegt die Stundenmitte (t = 0,5), `plan` die geplante
        # Dauer (t = 1,0), und der Zeiger liest die LEITZAHL. Eine Grenze bei
        # 0,5 liesse genau den Punkt stehen, der keine Leitzahl hat und nur
        # eine Studienform-Zahl zeigt - also das Problem.
        floor_t = float(plan[0]["hours"]) if plan else None
        if floor_t is not None:
            literature = [row for row in literature if row["t"] >= floor_t - 0.01]
        literature.sort(key=lambda row: row["t"])
    else:
        base = None
        attach_t = None

    # GERUNDET WIRD ERST HIER - nach Kette, Weglassprobe UND Anker. Eine auf
    # 0,1 W gerundete Zwischenzahl traegt ihren Rundungsfehler sonst in jeden
    # Punkt der Studienform weiter; die Gegenprobe "doppelter Anker verdoppelt
    # jeden Kurvenwert" hat genau das gefunden.
    for row in plan:
        row["watts"] = round(row["watts"], 1)
        row["step"] = round(row["step"], 1) if row["step"] is not None else None

    # Die durchgezogene Linie endet, wo die Weglassprobe zum ersten Mal reisst -
    # und sie WAECHST MIT: faehrt er fuenf Stunden oft genug, rueckt die Grenze
    # nach rechts, ohne dass jemand eine Zahl anfasst.
    plan_solid = solid_until(plan)
    plan_thin = max([row["hours"] for row in plan], default=0)

    measured_solid = max([row["hour"] for row in measured if row["band"] == "solid"],
                         default=None)
    thin_until = max([row["hour"] for row in measured if row["band"] in ("solid", "thin")],
                     default=None)

    return {
        "measured": measured,
        # Die Leitzahl, nach GEPLANTER DAUER gelesen. Die verketteten Schritte
        # stehen als `step` daneben - sie sind der Rechenweg und gehoeren in
        # den aufklappbaren Teil, nicht in die grosse Zahl.
        "plan": plan,
        "plan_solid_until_hours": plan_solid or None,
        "plan_thin_until_hours": plan_thin or None,
        # Die Saetze reisen aus dem Modul, nicht als Literal im Frontend.
        "selection_note": SELECTION_NOTE,
        # Welche Quelle gerade zaehlt, und was das Umlegen aendert - beides aus
        # dem Modul, damit die Kachel es nennen kann, ohne es zu kennen.
        "from_marks": curve_from_marks(data),
        "switch_note": SWITCH_NOTE,
        # DIE ANDERE SCHALTERSTELLUNG, gerechnet statt behauptet. Der Reiter
        # soll beide Zahlenreihen nebeneinander zeigen, und die Gegenseite kann
        # nur HIER entstehen - im Frontend waere sie ein Literal ohne Herkunft,
        # das beim ersten Umbau falsch wird.
        "plan_other": _plan_chain(rides(_flipped(data))["used"]),
        "axis_note": AXIS_NOTE,
        "literature": literature,
        "anchor_watts": anchor,
        "anchor_n": anchor_n,
        "anchor_base": round(base, 1) if base is not None else None,
        # Wo die Setzung ansetzt - damit die Kachel sagen kann, ab wann sie
        # spricht, ohne es aus den Punkten zurueckzurechnen.
        "literature_from_hours": round(attach_t, 2) if measured else None,
        "solid_until_hour": measured_solid,
        "thin_until_hour": thin_until,
        "rides_used": len(selection["used"]),
        # WELCHE Fahrten es sind, nicht nur wie viele. Ohne diese Zeile ist der
        # Schalter nicht ueberpruefbar: die Kachel nennt "10 Fahrten" und
        # niemand kann nachsehen, ob es die richtigen sind. Schlank gehalten -
        # die Stundenreihen selbst bleiben draussen, sie stehen an der Fahrt.
        "used": [{"activity_id": row.get("activity_id"), "date": row.get("date"),
                  "name": row.get("name"),
                  "hours_with_value": sum(
                      1 for h in (row.get("hours") or []) if (h or {}).get("p075") is not None)}
                 for row in selection["used"]],
        "paired": paired,
        "occupancy_rising": rising,
        "min_pairs": FATIGUE_MIN_PAIRS,
        "dropped": selection["dropped"],
        "dropped_counts": {reason: len(items) for reason, items in selection["dropped"].items()},
        "dropped_words": {key: list(value) for key, value in DROPPED_WORDS.items()},
        # Die Grenzen reisen mit, damit die Kachel sie NENNEN kann, ohne sie
        # zu kennen - und damit keine zweite Wahrheit im Frontend entsteht.
        "max_above_z2": FATIGUE_MAX_ABOVE_Z2,
        "min_minutes": FATIGUE_MIN_MINUTES,
        "solid_min_rides": FATIGUE_SOLID_MIN_RIDES,
        "thin_min_rides": FATIGUE_THIN_MIN_RIDES,
        # L1b: die Setzung, je Stunde, relativ auf die eigene ausgeruhte
        # Schwellen-HF gerechnet - Stevensons absolute bpm gehoeren seinen
        # zwoelf Probanden, der PROZENTUALE Anstieg ist das Uebertragbare.
        "hr_drift_per_hour_pct": round(
            (STEVENSON_HR_2H / STEVENSON_HR_REST - 1) / STEVENSON_HOURS * 100, 2),
        "hr_drift_source_rest": STEVENSON_HR_REST,
        "hr_drift_source_2h": STEVENSON_HR_2H,
        "hr_drift_expected": [
            {"hour": row["hour"], "t": row["t"],
             "bpm": round(aerobic_hr * (1 + (STEVENSON_HR_2H / STEVENSON_HR_REST - 1)
                                        / STEVENSON_HOURS * row["t"]), 1)}
            for row in measured
        ] if aerobic_hr else [],
        "aerobic_hr": aerobic_hr,
        # Die ZWEITE Zahl im Haus, bewusst mitgeschickt: der Rechenweg nennt
        # beide und sagt, warum sie auseinanderliegen. Ein bekannter
        # Unterschied ist etwas anderes als ein unbemerkter.
        "aerobic_power": aerobic_power,
        "t5_minutes": round(_t5_hours() * 60),
        "t5_published": GALLO_T5_MIN,
        "t5_published_sd": GALLO_T5_SD,
    }
