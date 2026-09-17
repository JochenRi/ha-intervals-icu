"""Ein Wert je Block, aufgetragen über die Zeit (docs/ausbau.md Paket M).

ZWEI GRÖSSEN MIT VERSCHIEDENEN AUFGABEN, und sie werden nie vertauscht:

* Der ERSTE eingeschwungene Block ist die VERLAUFSGRÖSSE. Er misst den
  frischesten Zustand und ist über Wochen erstaunlich stabil (259/260 W).
  Steigt er bei gleichem alpha, ist das eine belegbare Verbesserung.
* Der MEDIAN über alle eingeschwungenen Blöcke ist die STEUERGRÖSSE. Er misst
  die Einheit statt den frischesten Moment. Eine Regelung auf dem ersten Block
  sieht dauerhaft den besten Wert und driftet nach oben - in der Simulation
  +12 % gegen tatsächlich +2 % (PROJEKTSTAND §7).

Der Unterschied ist PHYSIOLOGIE, keine Datenstörung: die Lap-Etiketten wurden
geprüft, der erste harte Block trägt auch bei gleicher Leistung und nach zwei
Minuten Verwerfen systematisch das höhere alpha.

DER REGELKREIS IST KEIN SPIEGEL. Gemessen werden zwei Dinge zugleich - die
Leistung UND das alpha dabei. Das alpha sagt, ob die Leistung gepasst hat; die
Zahl kann deshalb steigen, ohne dass die Vorgeschichte sie treibt. Und NICHTS
davon greift automatisch: gerechnet wird ein Vorschlag, entschieden wird am
Rad.
"""

from __future__ import annotations

from typing import Any

try:  # inside the package (Home Assistant)
    from . import derive
    from . import section_marks as marks_lib
    from .const import (
        BLOCK_CORRIDORS,
        BLOCK_MIN_FOR_TREND,
        BLOCK_STEP_FAR_PCT,
        BLOCK_STEP_NEAR_PCT,
        BLOCK_WARMUP_DISCARD_S,
        BLOCK_HR_WINDOW_SD_FACTOR,
        BLOCK_MIN_FOR_SOURCE,
        BLOCK_ORDER_TOLERANCE,
    )
except ImportError:  # standalone (test suite loads this file directly)
    import derive  # type: ignore[no-redef]
    import section_marks as marks_lib  # type: ignore[no-redef]
    from const import (  # type: ignore[no-redef]
        BLOCK_CORRIDORS,
        BLOCK_MIN_FOR_TREND,
        BLOCK_STEP_FAR_PCT,
        BLOCK_STEP_NEAR_PCT,
        BLOCK_WARMUP_DISCARD_S,
        BLOCK_HR_WINDOW_SD_FACTOR,
        BLOCK_MIN_FOR_SOURCE,
        BLOCK_ORDER_TOLERANCE,
    )


def family_of(name: str | None) -> str | None:
    """Zu welcher Familie gehört eine Einheit? Aus ihrem NAMEN.

    Der Athlet benennt seine Einheiten nach dem, was er fährt. Eine Erkennung
    aus der Blockstruktur wäre eine zweite Wahrheit - und sie hielte eine
    abgebrochene VO2max-Einheit für etwas anderes als eine ganze.
    """
    low = str(name or "").lower()
    if "sweetspot" in low or "sweet spot" in low:
        return "sweetspot"
    if "vo2" in low:
        return "vo2max"
    if "tempo" in low:
        return "tempo"
    return None


# DER BLOCKSCHALTER. Er steht im Archiv neben dem Kurvenschalter und aus
# denselben Gruenden: er gehoert zu den Daten, die er umschaltet. Umgelegt
# liest die Blockreihe NUR die markierten und gemessenen Bloecke je Familie;
# `family_of` und das WORK-Etikett bleiben als Rueckfall fuer die Aus-Stellung
# stehen - ein Bauteil, nicht zwei.
BLOCK_SWITCH = "blocks_from_marks"


def blocks_from_marks(data: dict[str, Any]) -> bool:
    """Steht der Blockschalter auf AN?"""
    box = (data or {}).get("settings")
    return bool(isinstance(box, dict) and box.get(BLOCK_SWITCH))


def _flipped(data: dict[str, Any]) -> dict[str, Any]:
    """Dieselben Daten, der Blockschalter andersherum - ohne den Bestand anzufassen."""
    box = dict((data or {}).get("settings") or {})
    box[BLOCK_SWITCH] = not blocks_from_marks(data)
    return {**(data or {}), "settings": box}


def _marked_sessions(data: dict[str, Any]) -> list[dict[str, Any]]:
    """Je Fahrt und Familie: die MARKIERTEN, gemessenen Bloecke.

    Was markiert ist, zaehlt; was nicht markiert ist, kommt nicht vor. Eine
    Fahrt mit Marken zweier Familien liefert zwei Einheiten - der Block am
    20.08.2026, den die Namenserkennung als SweetSpot las, gehoert hier der
    Familie, der ihn der Athlet zugeordnet hat. Die Bloecke kommen aus der
    Messung, die frisch gerechnet wurde (§7, siebenundzwanzigster Fall), nicht
    aus dem Archivblock des Imports.
    """
    out: list[dict[str, Any]] = []
    activities = data.get("activities") or {}
    for key, entry in ((data.get(marks_lib.BLOCK) or {}).items()):
        activity = activities.get(key) or {"start_date_local": (entry or {}).get("date")}
        for family in BLOCK_CORRIDORS:
            if not marks_lib.marked(entry, family):
                continue
            work = ((marks_lib.measurement(entry, family) or {}).get("blocks")) or []
            row = _session(key, activity, family, [b for b in work if isinstance(b, dict)])
            if row is not None:
                out.append(row)
    out.sort(key=lambda row: row["date"])
    return out


def _sessions(data: dict[str, Any]) -> list[dict[str, Any]]:
    """Je Einheit: die eingeschwungenen Arbeitsblöcke, ihre Zahlen."""
    out: list[dict[str, Any]] = []
    for key, activity in (data.get("activities") or {}).items():
        family = family_of(activity.get("name"))
        if family is None:
            continue
        summary = (data.get("dfa") or {}).get(key) or {}
        work = [b for b in (summary.get("blocks") or []) if b.get("label") == "WORK"]
        row = _session(key, activity, family, work)
        if row is not None:
            out.append(row)
    out.sort(key=lambda row: row["date"])
    return out


def _session(key: str, activity: dict[str, Any], family: str,
             work: list[dict[str, Any]]) -> dict[str, Any] | None:
    """EINE Zeile je Einheit - dieselbe Bauart fuer beide Auswahlen.

    Zwei Zeilenbauer fuer dieselbe Einheit waeren die Klasse aus 0.42.2: zwei
    Bauarten fuer eine Sache driften auseinander.
    """
    if not work:
        return None
    alphas = [float(b["alpha"]) for b in work if b.get("alpha") is not None]
    powers = [float(b["watts"]) for b in work if b.get("watts")]
    pulses = [float(b["hr"]) for b in work if b.get("hr")]
    if not alphas or not powers:
        return None
    # DIE GEGENPROBE AUS FREMDER QUELLE: Intervals' eigener Abschnittswert
    # je Lap. Er liegt systematisch hoeher (Mittel ueber den ganzen Block
    # samt Anlauf) und taugt nicht als Ersatz - aber die REIHENFOLGE muss
    # dieselbe sein. Faellt unser Median von Block 1 auf Block 2 und der
    # fremde Wert steigt, stimmt etwas an unserem Ausschnitt.
    foreign = [b.get("lap_alpha") for b in work]
    order_ok = None
    if len(work) >= 2 and all(x is not None for x in foreign):
        pairs = 0
        agree = 0
        for i in range(len(work) - 1):
            d_own = alphas[i + 1] - alphas[i]
            d_ext = float(foreign[i + 1]) - float(foreign[i])
            # Die Toleranz stammt aus dem UNTERSCHIED der Rechenwege, nicht
            # aus einer Wunschgenauigkeit (PROJEKTSTAND §7). Geprueft wird
            # nur unser eigener Schritt: der fremde traegt den schwankenden
            # Anlauf-Versatz und taugt nicht als Massstab fuer sich selbst.
            #
            # KEINE MEHRHEITSREGEL. Gemessen: von 25 Einheiten haben 8 eine
            # Abweichung, und JEDE hat genau EIN abweichendes Paar - die
            # Anteile liegen bei 0,25 / 0,33 / 0,50, nie darueber. Eine
            # Regel "mehr als die Haelfte weicht ab" ergaebe im ganzen
            # Bestand NULL Meldungen, auch die berechtigten nicht. Eine
            # Regel, die nie greift, ist keine Regel, sondern eine
            # Abschaltung.
            if abs(d_own) < BLOCK_ORDER_TOLERANCE:
                continue
            pairs += 1
            if (d_own > 0) == (d_ext > 0):
                agree += 1
        order_ok = None if not pairs else (agree == pairs)

    return {
        "activity_id": key,
        "foreign_alphas": foreign,
        "order_ok": order_ok,
        "date": str(activity.get("start_date_local") or "")[:10],
        "name": activity.get("name"),
        "family": family,
        "n_blocks": len(work),
        # Die EINZELWERTE reisen mit: die Karte soll zeigen, worauf die
        # Steuerung ruht, statt eine geglättete Zahl zu drucken.
        "block_alphas": [b.get("alpha") for b in work],
        "block_watts_each": [b.get("watts") for b in work],
        "block_watts": [b.get("watts") for b in work],
        "first_alpha": work[0].get("alpha"),
        "first_watts": work[0].get("watts"),
        "median_alpha": round(derive._median(alphas), 3),
        "median_watts": round(derive._median(powers)),
        "median_hr": round(derive._median(pulses)) if pulses else None,
        "block_hr": [b.get("hr") for b in work],
        # Die DAUER je Block reist mit. Sie aendert nichts an der Auswahl -
        # sie sagt der Kachel, WORAN gemessen wurde: ein Median aus
        # 3-4-Minuten-Bloecken ist keine Vorgabe fuer einen 8-Minuten-Block,
        # und ohne diese Zahl kann die Karte den Unterschied nicht benennen.
        "block_minutes": [b.get("minutes") for b in work],
        "alpha_span": round(max(alphas) - min(alphas), 3),
    }


def _spread(values: list[float]) -> float:
    """Die übliche Schwankung DERSELBEN Familie - die Schrittgrenze folgt ihr.

    Sie wird nicht gesetzt: eine Abweichung, die kleiner ist als die übliche
    Schwankung, ist keine Abweichung. Deshalb ist die Grenze bei jeder Familie
    eine andere.
    """
    if len(values) < 2:
        return 0.1
    mean = sum(values) / len(values)
    return max((sum((x - mean) ** 2 for x in values) / len(values)) ** 0.5, 0.02)


def suggest_step(alpha: float, corridor: tuple[float, float], spread: float) -> dict[str, Any]:
    """Ein Vorschlag, keine Anweisung. Nach oben wie nach unten."""
    low, high = corridor
    if alpha > high:
        gap = alpha - high
        pct = BLOCK_STEP_FAR_PCT if gap >= spread else BLOCK_STEP_NEAR_PCT
        where = "above"
    elif alpha < low:
        gap = low - alpha
        pct = -(BLOCK_STEP_FAR_PCT if gap >= spread else BLOCK_STEP_NEAR_PCT)
        where = "below"
    else:
        return {"pct": 0, "gap": 0.0, "where": "inside"}
    return {"pct": pct, "gap": round(gap, 3), "where": where}


def series(data: dict[str, Any], with_other: bool = True) -> dict[str, Any]:
    """Der Verlauf je Familie, die Steuergröße und der Vorschlag."""
    from_marks = blocks_from_marks(data)
    sessions = _marked_sessions(data) if from_marks else _sessions(data)
    families: dict[str, Any] = {}
    for family, corridor in BLOCK_CORRIDORS.items():
        rows = [s for s in sessions if s["family"] == family]
        if not rows:
            continue
        spread = round(_spread([r["median_alpha"] for r in rows]), 3)
        points = []
        for row in rows:
            step = suggest_step(row["median_alpha"], corridor, spread)
            points.append({
                "date": row["date"], "name": row["name"],
                "order_ok": row["order_ok"], "foreign_alphas": row["foreign_alphas"],
                "n_blocks": row["n_blocks"],
                "block_alphas": row["block_alphas"], "block_watts": row["block_watts"],
                "block_watts_each": row["block_watts_each"],
                "block_minutes": row["block_minutes"],
                "alpha_span": row["alpha_span"],
                # Verlaufsgröße
                "first_alpha": row["first_alpha"], "first_watts": row["first_watts"],
                # Steuergröße
                "median_alpha": row["median_alpha"], "median_watts": row["median_watts"],
                "median_hr": row["median_hr"], "block_hr": row["block_hr"],
                "step_pct": step["pct"], "step_gap": step["gap"], "step_where": step["where"],
                "suggested_watts": round(row["median_watts"] * (1 + step["pct"] / 100.0)),
            })
        # Wo die fremde Quelle widerspricht, sagt es die Karte - eine
        # Gegenprobe, die niemand sieht, ist keine.
        disagree = [p["date"] for p in points if p["order_ok"] is False]
        # DAS HF-FENSTER AUS DERSELBEN QUELLE wie die Wattvorgabe. Beide bewegen
        # sich damit gemeinsam: ueber drei Monate wandert die Blockleistung von
        # 216 auf 251 W und die Block-HF von 176 auf 185 - ein Fenster aus einer
        # FREMDEN Schwelle waere dabei stehengeblieben, und der Unterschied
        # faellt erst auf, wenn er weh tut.
        hr_medians = [p["median_hr"] for p in points if p["median_hr"]]
        hr_window = None
        if len(hr_medians) >= BLOCK_MIN_FOR_SOURCE:
            mid = derive._median(hr_medians)
            mean_hr = sum(hr_medians) / len(hr_medians)
            sd_hr = (sum((x - mean_hr) ** 2 for x in hr_medians) / len(hr_medians)) ** 0.5
            half = BLOCK_HR_WINDOW_SD_FACTOR * sd_hr
            hr_window = {
                "low": round(mid - half), "high": round(mid + half),
                "median": round(mid, 1), "sd": round(sd_hr, 1),
                "n": len(hr_medians), "source": "measured",
            }
        newest = points[-1]
        families[family] = {
            "corridor": list(corridor),
            "sessions": len(points),
            "spread": spread,
            # Die Linie wird NUR gezeichnet, wenn sie getragen wird. Zwei Punkte
            # sind kein Verlauf, und eine Linie durch drei ist die 0.13.0-Falle.
            "trend": len(points) >= BLOCK_MIN_FOR_TREND,
            "min_for_trend": BLOCK_MIN_FOR_TREND,
            "points": points,
            "latest": newest,
            # Der Verlauf der VERLAUFSGRÖSSE - die Zahl, an der sich Fortschritt
            # zeigt: dieselbe Leistung bei gleichem alpha bedeutet nichts,
            # MEHR Leistung bei gleichem alpha ist die Verbesserung.
            "first_block_watts": [p["first_watts"] for p in points],
            "order_conflicts": disagree,
            "hr_window": hr_window,
            # Belegung entscheidet, OB umgestellt wird - fuer beide Seiten
            # gleich. Zu duenn heisst: die FTP bleibt, und die Karte sagt warum.
            "source_ok": len(points) >= BLOCK_MIN_FOR_SOURCE,
            "min_for_source": BLOCK_MIN_FOR_SOURCE,
            # Der Zeitraum, ueber den geschaut wird - sonst weiss niemand,
            # worauf der Verlauf ruht.
            "from": points[0]["date"], "to": points[-1]["date"],
            # Der erste Arbeitsblock ist nicht immer der haerteste: manche
            # Geraete etikettieren einen lockeren Abschnitt als WORK. Wo das
            # so ist, sagt die Karte es, statt die Zahl zu tauschen - die
            # saubere Loesung ist ein eigener Schritt.
            "first_is_weak": bool(
                newest.get("block_watts_each")
                and newest["block_watts_each"][0] is not None
                and len([w for w in newest["block_watts_each"][1:] if w]) > 0
                and newest["block_watts_each"][0]
                < 0.9 * max(w for w in newest["block_watts_each"][1:] if w)
            ),
        }
    out = {
        "families": families,
        # WELCHE Auswahl diese Reihe traegt - fuer jede Karte, die eine Zahl
        # daraus neben eine Zahl aus der Kurve stellt (Stufentest, 40-Watt-Frage).
        "from_marks": from_marks,
        "selection": marks_lib.selection(from_marks),
        "discarded_s": BLOCK_WARMUP_DISCARD_S,
        "step_near_pct": BLOCK_STEP_NEAR_PCT,
        "step_far_pct": BLOCK_STEP_FAR_PCT,
        # Die Grenze, und sie steht in jeder Karte: gemessen wurde auf der
        # Rolle, in eigenen Einheiten, bei fester Blockstruktur. DERSELBE
        # alpha-Wert bedeutet draußen eine andere Leistung - am eigenen Bestand
        # liegen zwischen beiden Zusammenhängen 40 W (PROJEKTSTAND §7).
        "scope": "rolle",
    }
    if with_other:
        # DIE ANDERE STELLUNG WIRD GERECHNET, nicht im Frontend geschaetzt -
        # dieselbe Bauart wie `plan_other` beim Kurvenschalter.
        other = series(_flipped(data), with_other=False)
        out["other"] = {fam: summary(box) for fam, box in other["families"].items()}
        out["switch_note"] = switch_note(out, other)
    return out


def summary(box: dict[str, Any]) -> dict[str, Any]:
    """Was eine Familie an Vorgaben und Lesart traegt - fuer den Vergleich."""
    latest = box.get("latest") or {}
    window = box.get("hr_window") or {}
    return {
        "sessions": box.get("sessions"),
        "watts": latest.get("median_watts") if box.get("source_ok") else None,
        "hr_low": window.get("low"), "hr_high": window.get("high"),
        "trend": bool(box.get("trend")),
        "min_for_trend": box.get("min_for_trend"),
        "spread": box.get("spread"),
    }


_FAM_LABEL = {"vo2max": "VO2max", "sweetspot": "SweetSpot", "tempo": "Tempo"}


def switch_note(now: dict[str, Any], other: dict[str, Any]) -> str:
    """Was sich beim Umlegen AENDERT - an der Lesart, nicht nur an den Zahlen.

    Die Zahlen stehen daneben in der Tabelle. Der Satz sagt, was sie bedeuten:
    weniger Einheiten, ein Trendbalken, der eine Mindestzahl braucht, und
    Pulsfenster, deren Breite aus der Streuung weniger Werte folgt - ein
    engeres Fenster sieht aus wie eine Korrektur und ist keine.
    Alle Zahlen kommen aus den beiden gerechneten Reihen (fuenfte Bauregel).
    """
    to_marks = not now.get("from_marks")
    a = {fam: summary(box) for fam, box in (now.get("families") or {}).items()}
    b = {fam: summary(box) for fam, box in (other.get("families") or {}).items()}
    parts = [("Umgelegt zählen nur deine markierten und gemessenen Blöcke."
              if to_marks else
              "Zurückgestellt wählt wieder die Namenserkennung die Blöcke.")]
    counts, trends, windows = [], [], []
    for fam in ("vo2max", "sweetspot", "tempo"):
        x, y = a.get(fam) or {}, b.get(fam) or {}
        n_x, n_y = x.get("sessions") or 0, y.get("sessions") or 0
        name = _FAM_LABEL[fam]
        if n_x != n_y:
            counts.append(f"{name} {n_x} → {n_y}")
        need = y.get("min_for_trend") or x.get("min_for_trend")
        if x.get("trend") and not y.get("trend"):
            trends.append(f"der {name}-Trendbalken verschwindet (er braucht {need} "
                          f"Einheiten, es wären {n_y})")
        elif not x.get("trend") and y.get("trend"):
            trends.append(f"der {name}-Trendbalken erscheint")
        # Die Grenze betrifft MARKEN - in der Namenserkennung nimmt keine Marke
        # etwas weg, und der Satz waere dort falsch.
        if to_marks and y.get("trend") and need and n_y == need:
            trends.append(f"der {name}-Trend steht genau auf der Grenze von {need} — "
                          "eine zurückgenommene Marke nimmt ihn weg")
        if None not in (x.get("hr_low"), x.get("hr_high"), y.get("hr_low"), y.get("hr_high")) \
                and (x["hr_low"], x["hr_high"]) != (y["hr_low"], y["hr_high"]):
            windows.append((name, x, y))
    if counts:
        parts.append("Einheiten: " + " · ".join(counts) + ".")
    if trends:
        parts.append(trends[0][0].upper() + "; ".join(trends)[1:] + ".")
    if windows:
        breite = [(y["hr_high"] - y["hr_low"]) - (x["hr_high"] - x["hr_low"]) for _, x, y in windows]
        text = " · ".join(f"{n} {x['hr_low']}–{x['hr_high']} → {y['hr_low']}–{y['hr_high']}"
                          for n, x, y in windows)
        if all(d < 0 for d in breite):
            parts.append(f"Die Pulsfenster werden enger: {text}. Das ist keine Korrektur, "
                         "sondern die Folge der kleineren Zahl: die Breite kommt aus der "
                         "Streuung zwischen den Einheiten, und aus weniger Einheiten fällt "
                         "sie kleiner aus.")
        elif all(d > 0 for d in breite):
            parts.append(f"Die Pulsfenster werden breiter: {text}. Auch das ist keine "
                         "Korrektur: die Breite kommt aus der Streuung zwischen den "
                         "Einheiten, und mehr Einheiten bringen mehr davon mit.")
        else:
            parts.append(f"Die Pulsfenster verschieben sich: {text}. Ihre Breite kommt aus "
                         "der Streuung zwischen den Einheiten und folgt der Auswahl.")
    return " ".join(parts)
