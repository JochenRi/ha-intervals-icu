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
    from .const import (
        FATIGUE_MAX_ABOVE_Z2,
        FATIGUE_MIN_MINUTES,
        FATIGUE_SOLID_MIN_RIDES,
        FATIGUE_THIN_MIN_RIDES,
    )
except ImportError:  # standalone (test suite loads this file directly)
    import derive  # type: ignore[no-redef]
    from const import (  # type: ignore[no-redef]
        FATIGUE_MAX_ABOVE_Z2,
        FATIGUE_MIN_MINUTES,
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


def literature_factor(hours: float) -> float:
    """Anteil der Ausgangsleistung nach ``hours`` Stunden - reine Setzung."""
    return 1.0 - GALLO_LINEAR * hours - GALLO_QUADRATIC * hours * hours


def rides(data: dict[str, Any]) -> dict[str, Any]:
    """Welche Fahrten ihren Stundenverlauf hergeben - und welche warum nicht.

    Der Ausschluss sitzt VOR der Messung. Ein Guetekriterium hinterher hat in
    L0 Runde 3 die Auswahl genau auf die strukturierten Einheiten verengt und
    den Stoerer eingesammelt statt ihn auszuschliessen: die -31,9 W waren der
    Trainingsplan, nicht die Ermuedung.
    """
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


def curve(data: dict[str, Any]) -> dict[str, Any]:
    """Anker, gemessene Stundenwerte, Literaturform und Belegungsgrenzen."""
    selection = rides(data)
    by_hour: dict[int, list[float]] = {}
    for ride in selection["used"]:
        for row in ride["hours"]:
            value = row.get("p075")
            if value is not None:
                by_hour.setdefault(int(row["hour"]), []).append(float(value))

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
        })

    anchor = measured[0]["watts"] if measured else None
    anchor_n = measured[0]["n"] if measured else 0
    literature = []
    if anchor is not None:
        # Der Anker sitzt auf der ERSTEN gemessenen Stunde, die Form wird von
        # dort aus auf t = 0 zurueckgerechnet. Sonst haenge die Literaturkurve
        # an einem Punkt, den niemand gefahren ist.
        base = anchor / literature_factor(measured[0]["t"])
        for row in measured:
            literature.append({"hour": row["hour"], "t": row["t"],
                               "watts": round(base * literature_factor(row["t"]), 1)})
        last = measured[-1]["t"]
        step = 0.5
        t = last + step
        while t <= last + 2.0:
            literature.append({"hour": None, "t": round(t, 2),
                               "watts": round(base * literature_factor(t), 1)})
            t += step
    else:
        base = None

    solid_until = max([row["hour"] for row in measured if row["band"] == "solid"], default=None)
    thin_until = max([row["hour"] for row in measured if row["band"] in ("solid", "thin")],
                     default=None)

    return {
        "measured": measured,
        "literature": literature,
        "anchor_watts": anchor,
        "anchor_n": anchor_n,
        "anchor_base": round(base, 1) if base is not None else None,
        "solid_until_hour": solid_until,
        "thin_until_hour": thin_until,
        "rides_used": len(selection["used"]),
        "dropped": selection["dropped"],
        "dropped_counts": {reason: len(items) for reason, items in selection["dropped"].items()},
        # Die Grenzen reisen mit, damit die Kachel sie NENNEN kann, ohne sie
        # zu kennen - und damit keine zweite Wahrheit im Frontend entsteht.
        "max_above_z2": FATIGUE_MAX_ABOVE_Z2,
        "min_minutes": FATIGUE_MIN_MINUTES,
        "solid_min_rides": FATIGUE_SOLID_MIN_RIDES,
        "thin_min_rides": FATIGUE_THIN_MIN_RIDES,
    }
