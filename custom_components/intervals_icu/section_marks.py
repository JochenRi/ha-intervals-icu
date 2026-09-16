"""Die Zuordnung trifft der Athlet: welcher Abschnitt zu welcher Familie gehoert.

WARUM DIESER BLOCK UEBERHAUPT EXISTIERT
Das System raet heute an drei Stellen ueber eine Fahrt, von der es nichts
weiss: die Familie aus dem NAMEN (blocks.family_of), die Eignung aus dem
ZONENANTEIL (derive.fatigue_curve_reason) und die Bloecke aus den
LAP-ETIKETTEN (label == "WORK", nachkorrigiert von drop_warmup_blocks). Jede
der drei Vermutungen lag in diesem Projekt schon nachweislich daneben
(docs/ausbau.md P0). Und keine Automatik kann sehen, was zaehlt - Temperatur,
Verpflegung, Schlaf und Wind stehen in keinem Feld.

Also dieselbe Bauart wie ramp_tests und K2, nur nicht mehr als Sonderfall:
DER ATHLET ORDNET ZU, DAS SYSTEM RECHNET.

DER SCHLUESSEL IST `start_index`, NIEMALS DIE LAUFENDE NUMMER
Es gibt zwei Abschnittslisten, und sie sind NICHT deckungsgleich:

  * die Rundenliste im Panel kommt LIVE ueber derive.normalize_laps und
    nummeriert mit `n` = Position in der Rohliste, JEDEN Lap, auch Pausen;
  * die Bloecke im Archiv entstehen ueber derive.dfa_blocks und FALLEN WEG,
    wenn moving_time < BLOCK_MIN_SECONDS, wenn start_index/end_index fehlen,
    oder wenn nach dem 120-Sekunden-Verwerfen zu wenige alpha-Werte bleiben.

Wer im Panel Abschnitt 7 anhakt und das als Index 7 ablegt, trifft im Archiv
einen ANDEREN Block. Der einzige gemeinsame Schluessel ist `start_index`: er
steht in _LAP_FIELDS, kommt also in der Panel-Payload an, und dfa_blocks
schreibt ihn gerundet mit. Das Schreiben prueft deshalb streng gegen die
uebergebenen Laps - eine laufende Nummer ist dort in aller Regel kein
vorkommender start_index und faellt mit Grund auf.

DER ANKER IST FUER DIE DRIFTERKENNUNG, NICHT FUER DEN SCHNITT
`{laps, sections[{i, s}]}` sieht nach einem Verstoss gegen J7 aus (gespeichert
wird nur, was nicht herleitbar ist) und ist keiner:
importer.drop_outdated_dfa() setzt bei abweichender DFA_ALGO_VERSION schlicht
`data["dfa"] = {}`. Damit sind alle Bloecke samt ihrer start_index weg, und
der Vergleichsstand nach dem Bump ist genau das, was gerade geloescht wurde -
siebter Fall (0.49.2) in neuer Gestalt. Deshalb wird der Anker BEIM MARKIEREN
gesichert, nicht hinterher gesucht.

Wozu er NICHT taugt: zum Maskieren. Ein Ausschnitt aus dem Strom braucht
start_index UND end_index; der Anker haelt start_index und die Dauer. Die
Grenzen holt der Messweg live aus den Laps (docs/ausbau.md P4, Befund 4) -
wer aus dem Anker zu schneiden versucht, baut einen Ausschnitt aus einer
Bewegungszeit auf einer Stromachse, und das ist genau der Versatz aus §7.

DAS SCHREIBEN IST STRENG, DAS LESEN IST NACHSICHTIG - dieselbe Trennung wie
in day_context und ramp_tests.
"""

from __future__ import annotations

from typing import Any

BLOCK = "section_marks"

# Wird erhoeht, wenn sich die MESSUNG aendert - nicht die Anzeige. Ein Eintrag
# mit aelterer Marke verliert seine `hours`, BEHAELT aber Marken und Anker:
# die Aussage des Athleten, welcher Abschnitt welcher Familie gehoert, verfaellt
# nicht, wenn sich die Mathematik aendert.
# 2 seit 0.54.1: der Messweg maskierte familienUEBERGREIFEND und mischte auf
# einer Fahrt mit VO2max- UND Grundlagen-Marken zwei Punktwolken in EINE
# Gerade - genau der Fit-durch-zwei-Wolken aus Paket M, der dort schon einmal
# behoben war. Die Zahlen aus 0.54.0 sind damit falsch gemessen und fallen
# beim Laden; die Marken bleiben.
MEASURE_VERSION = 3

# Vier Familien mit Abschnitts-Haken. Der Stufentest steht NICHT dabei - eine
# Messfahrt ist als GANZES eine Messfahrt, es gibt daran keinen Abschnitt zu
# markieren, und sie hat mit ramp_tests ihren eigenen Block.
FAMILIES: tuple[str, ...] = ("vo2max", "sweetspot", "tempo", "endurance")

# STILLGELEGT am 15.09.2026, und der GRUND gehoert hierher, nicht nur die
# Entscheidung - sonst baut sie jemand beim naechsten Umbau zurueck:
#
#   * `long` rechnet mit `endurance` IDENTISCH. Beide tragen in
#     workouts.SOURCE_CHAIN dieselbe Kette ("curve", "ramp_hrvt1", "ftp") und
#     stehen beide in CURVE_FAMILIES. Und die Kurve misst je FAHRTSTUNDE:
#     eine Achtstundenfahrt liefert acht Punkte, eine Zweistundenfahrt zwei -
#     sie ordnet sich von selbst ein und braucht kein Etikett. Eine Grenze
#     "ab wann ist lang" waere fuer einen Anfaenger mit zwei Stunden und einen
#     Trainierten mit acht verschieden, und niemand koennte sie pruefen. Zwei
#     Familien mit identischer Rechnung sind zwei Namen fuer eine Sache.
#   * `threshold` kommt in blocks.py und BLOCK_CORRIDORS ueberhaupt nicht vor:
#     keine Blockmessung, kein Zielkorridor. Ihr Wert kommt allein aus dem
#     Stufentest. Ein Haken dort aendert nichts - ein Bedienelement ohne
#     Wirkung ist schlimmer als keines.
#
# Im TRAINER bleibt die Unterscheidung unberuehrt: dort entscheidet `long`,
# welche Einheit vorgeschlagen und wie der Zustand bewertet wird. Stillgelegt
# ist nur das MARKIEREN.
RETIRED: tuple[str, ...] = ("threshold", "long")

RETIRED_REASON = ("Die Familien „Schwelle“ und „lange Fahrt“ werden nicht mehr "
                  "markiert — ihre Marken an dieser Fahrt sind gefallen. Die "
                  "Schwelle kommt aus dem Stufentest, die lange Fahrt rechnet "
                  "wie die Grundlage.")

REASON_LIMIT = 256

# Der Satz, der nach dem Haken dasteht, solange nicht gemessen wurde.
#
# ER WIRD NICHT MEHR IN DEN EINTRAG GESCHRIEBEN, sondern reist im Leseweg mit.
# Der Grund steht in 0.53.1: der alte Satz verwies auf einen Knopf, den es
# noch nicht gibt, und weil er GESPEICHERT war, stand er auch in Eintraegen,
# die laengst vor der Textaenderung entstanden sind. Ein gespeicherter
# Anzeigetext veraltet mit jedem Umbau und muss dann migriert werden - das ist
# die Listen-Klasse aus §7, nur mit Prosa statt mit Zahlen.
#
# `reason` bleibt fuer ECHTE Gruende: eine gescheiterte Messung, ein
# Versionswechsel. Die blosse ABWESENHEIT einer Messung ist kein Grund, sie
# ist ein Zustand - und Zustaende werden aus `hours is None` gelesen, nicht
# aus einem Satz.
# Der Satz zeigt jetzt auf einen Knopf, DEN ES GIBT. Bis 0.53.1 stand hier
# "der Knopf dafuer kommt mit der Messung", weil er noch fehlte - genau die
# Sorte Text, die mit dem naechsten Umbau veraltet. Er reist deshalb im
# Leseweg mit und steht nicht im Eintrag: waere er gespeichert, muesste jede
# solche Aenderung migriert werden.
NOT_MEASURED = "Markiert, noch nicht gemessen — auf „übernehmen und messen“."

# Die ZWEITE Aussage, und sie ist eine andere als die erste. Wer schon einmal
# gemessen hat und danach einen Haken setzt oder zuruecknimmt, soll nicht
# "noch nicht gemessen" lesen - das klingt, als waere sein Knopfdruck nie
# angekommen. Er HAT gemessen; die Auswahl ist seither eine andere.
#
# Unterschieden wird an `measured_at`, nicht an `reason`: der Zustand steht in
# Feldern, der SATZ kommt aus dem Leseweg (0.53.1). Beide reisen ueber die
# section_marks-Payload, damit das Frontend keine zweite Fassung fuehrt.
REMEASURE = ("Die Auswahl hat sich seit der Messung geändert — neu zu messen "
             "auf „übernehmen und messen“.")

# WAS DIE MARKIERUNGEN HEUTE BEWIRKEN: nichts. Das muss dastehen, solange es
# so ist - wer markiert und glaubt, es passiere etwas, markiert ins Leere.
#
# UND ES SIND ZWEI SAETZE, KEIN EINER. Die beiden Lagen sind verschieden, und
# der Unterschied entscheidet, welche Reparatur noetig ist:
#   * Die BLOCKFAMILIEN messen bereits - die Blockmessung laeuft seit Paket M
#     beim Import und waehlt ihre Bloecke SELBST, an den Marken vorbei. Nicht
#     "nicht angeschlossen", sondern "laeuft daneben".
#   * Die KURVE liest die Marken ebenfalls nicht, aber sie hat auch keine
#     eigene Auswahl - sie laeuft auf der Namenserkennung.
# Ein gemeinsamer Satz muesste beides verschweigen, um zu stimmen.
NOT_ACTIVE_BLOCKS = ("VO2max, SweetSpot und Tempo messen über deine "
                     "Arbeitsblöcke — und diese Messung wählt ihre Blöcke bis "
                     "heute selbst, an deinen Marken vorbei. Was du hier "
                     "anhakst, ändert an ihren Wattvorgaben noch nichts.")

NOT_ACTIVE_CURVE = ("Die Grundlage misst über die Ermüdungskurve. Der Knopf "
                    "misst deine markierten Abschnitte bereits — die Kurve "
                    "liest das Ergebnis aber noch nicht, sie läuft weiter auf "
                    "der Namenserkennung. Beides stellt B2 um.")

# WARUM KEIN WERT HERAUSKAM, und vor allem: WAS DAS HEISST. Eine Zahl ohne
# Folge laesst den Athleten raten. Die Schwelle selbst wird NICHT genannt -
# sie steht in keiner Payload (P8 ist nicht gebaut), und eine hier
# abgeschriebene Zahl waere die zweite Wahrheit.
# KEIN WORT, DAS NACH MANGEL KLINGT. Die erste Fassung sagte "zu locker fuer
# diese Messung" - beschrieben war damit die Fahrt aus der Sicht einer
# Schwellenmessung, die der Athlet gar nicht gefahren hat. Eine Grundlagenfahrt
# bei hohem alpha ist genau richtig gefahren; dass sie der Kurve keinen Punkt
# gibt, ist eine Eigenschaft der MESSUNG, nicht der Fahrt.
#
# Die Schwellenzahl wird NICHT genannt: sie steht in keiner Payload (P8), und
# eine hier abgeschriebene waere die zweite Wahrheit.
NO_VALUE = ("Diese Fahrt gibt der Ermüdungskurve keinen Punkt: dein alpha ist "
            "durchgehend über der Schwelle geblieben, du bist also darunter "
            "gefahren — für eine Grundlagenfahrt genau richtig. Die Kurve liest "
            "nur Stunden, in denen die Schwelle im Verlauf erreicht wird; das "
            "sind meist die längeren Fahrten. Für dein Training zählt diese "
            "Fahrt wie jede andere Grundlagenfahrt.")

# Der Messweg rechnet heute NUR die Kurve. Fuer die Blockfamilien gibt es ihn
# noch nicht, und lieber gar keine Zahl als eine, die niemand angefordert hat.
ONLY_CURVE = ("An dieser Fahrt ist kein Grundlagen-Abschnitt markiert. Dieser "
              "Knopf misst die Ermüdungskurve, und die rechnet über "
              "Grundlagen-Abschnitte. VO2max, SweetSpot und Tempo messen über "
              "Blöcke — diesen Weg gibt es hier noch nicht, er kommt mit B2.")

# Was frueher in die Eintraege geschrieben wurde. Wird beim Laden GEZIELT
# geleert, damit kein veralteter Satz stehenbleibt; alles andere in `reason`
# bleibt unangetastet.
_LEGACY_NOT_MEASURED = (
    "Markiert, noch nicht gemessen — die Messung läuft auf „übernehmen und messen“.",
    "Markiert, noch nicht gemessen",
)

# Warum eine vorhandene Messung nicht mehr gilt.
STALE_REASON = {
    "laps_missing": "Die Runden dieser Fahrt sind nicht geladen — ohne sie ist "
                    "nicht zu prüfen, ob die Markierung noch sitzt.",
    "lap_count": "Die Fahrt hat jetzt eine andere Zahl von Abschnitten als beim "
                 "Markieren — die Zuordnung ist zu bestätigen oder neu zu setzen.",
    "section_moved": "Mindestens ein markierter Abschnitt hat eine andere Dauer "
                     "als beim Markieren — die Zuordnung ist zu bestätigen oder "
                     "neu zu setzen.",
}


def _valid_day(day: Any) -> bool:
    if not isinstance(day, str) or len(day) != 10:
        return False
    return day[4] == "-" and day[7] == "-" and day[:4].isdigit()


def _index(value: Any) -> int | None:
    """Ein Abschnittsschluessel, oder nichts. Bools zaehlen NICHT als Zahl."""
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value if value >= 0 else None
    if isinstance(value, float) and value >= 0 and float(value).is_integer():
        return int(value)
    return None


def _seconds(lap: Any) -> int | None:
    """Die Dauer eines Laps, auf die Sekunde gerundet.

    GERUNDET UND NICHT MIT TOLERANZ VERGLICHEN: moving_time kommt aus derselben
    Quelle wie beim Markieren. Eine Toleranz waere eine geratene Zahl, und eine
    geratene Toleranz hat in diesem Projekt schon eine Gegenprobe stumpf
    gemacht (§7, sechster Fall).
    """
    if not isinstance(lap, dict):
        return None
    try:
        return round(float(lap.get("moving_time")))
    except (TypeError, ValueError):
        return None


def lap_index(lap: Any) -> int | None:
    """Der Schluessel EINES Laps - an einer Stelle, damit es nur einen gibt."""
    if not isinstance(lap, dict):
        return None
    return _index(lap.get("start_index"))


def entry_for(data: dict[str, Any], activity_id: Any) -> dict[str, Any] | None:
    block = data.get(BLOCK)
    if not isinstance(block, dict):
        return None
    entry = block.get(str(activity_id))
    return entry if isinstance(entry, dict) else None


def entries(data: dict[str, Any]) -> list[dict[str, Any]]:
    """Alle zugeordneten Fahrten, aelteste zuerst - nach DATUM, nicht nach ID."""
    block = data.get(BLOCK)
    if not isinstance(block, dict):
        return []
    out = []
    for activity_id, entry in block.items():
        if not isinstance(entry, dict):
            continue
        row = dict(entry)
        row["activity_id"] = str(activity_id)
        out.append(row)
    out.sort(key=lambda row: (str(row.get("date") or ""), row["activity_id"]))
    return out


def marked(entry: Any, family: str | None = None) -> list[int]:
    """Die markierten start_index - einer Familie, oder aller zusammen."""
    marks = (entry or {}).get("marks")
    if not isinstance(marks, dict):
        return []
    out: set[int] = set()
    for name, indices in marks.items():
        if family is not None and name != family:
            continue
        if not isinstance(indices, list):
            continue
        for value in indices:
            found = _index(value)
            if found is not None:
                out.add(found)
    return sorted(out)


def families_at(entry: Any, start_index: Any) -> list[str]:
    """Welche Familien an EINEM Abschnitt haengen.

    Ein Abschnitt kann Marken mehrerer Familien tragen - der Datentyp ist eine
    Menge, keine Auswahl. Eine Marke je Familie je Abschnitt, kein Rang, keine
    Gewichtung (P2).
    """
    want = _index(start_index)
    if want is None:
        return []
    marks = (entry or {}).get("marks")
    if not isinstance(marks, dict):
        return []
    return sorted(
        name for name, indices in marks.items()
        if isinstance(indices, list) and want in [_index(v) for v in indices]
    )


def marked_blocks(entry: Any, blocks: Any, family: str | None = None) -> list[dict[str, Any]]:
    """Die ARCHIVBLOECKE zu den markierten Abschnitten - ueber start_index.

    Das ist die Bruecke zwischen den beiden Listen, und sie ist der Grund fuer
    P3a: waere hier die laufende Nummer der Schluessel, traefe sie bei jeder
    Fahrt mit einem gefallenen Lap einen anderen Block.
    """
    want = set(marked(entry, family))
    if not want or not isinstance(blocks, list):
        return []
    return [
        block for block in blocks
        if isinstance(block, dict) and _index(block.get("start_index")) in want
    ]


def anchor_of(laps: Any, indices: list[int]) -> dict[str, Any]:
    """Der Fingerabdruck: Zahl der Runden, und je markiertem Abschnitt i und s.

    Das MINIMUM, mehr nicht - alles Weitere ist aus den Laps herleitbar,
    solange es sie gibt (J7).
    """
    rows = laps if isinstance(laps, list) else []
    want = set(indices)
    sections = []
    for lap in rows:
        found = lap_index(lap)
        if found is None or found not in want:
            continue
        sections.append({"i": found, "s": _seconds(lap)})
    sections.sort(key=lambda row: row["i"])
    return {"laps": len(rows), "sections": sections}


# WAS EIN BLOCK AUSSERHALB SEINES KORRIDORS BEDEUTET - und warum es den
# Athleten angeht. Kein Vorwurfston: der Korridor steht fest, die alpha-Werte
# sind gemessen, verglichen werden zwei Zahlen. Gesagt wird die FOLGE, nicht
# nur die Feststellung.
OUTSIDE_NOTE = ("Ein Block außerhalb des Bereichs zieht den Median seiner "
                "Familie in seine Richtung — und der Regelkreis will die "
                "Vorgabe daraufhin korrigieren. Die Zahl stimmt; sie beschreibt "
                "dann nur einen anderen Abschnitt, als du steuern wolltest.")


def _alpha(value: Any) -> float | None:
    """Ein alpha-Wert, oder nichts. `_index` taugt nicht: alpha ist gebrochen."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)


def corridor_state(data: Any, corridors: Any) -> dict[str, Any]:
    """Je Familie: wie viele gemessene Bloecke liegen im Korridor, wie viele nicht.

    Eine reine GEGENUEBERSTELLUNG zweier Zahlen - der Korridor ist gesetzt, das
    alpha ist gemessen. Entschieden wird nichts; angezeigt wird, was der
    Regelkreis spaeter sieht, BEVOR er es tut.
    """
    out: dict[str, Any] = {}
    bounds = corridors if isinstance(corridors, dict) else {}
    for entry in (data or {}).values():
        if not isinstance(entry, dict):
            continue
        for family, got in ((entry.get("measure") or {}).items()):
            low_high = bounds.get(family)
            if not isinstance(got, dict) or not isinstance(low_high, (list, tuple)):
                continue
            box = out.setdefault(family, {"blocks": 0, "outside": []})
            for row in (got.get("blocks") or []):
                alpha = _alpha(row.get("alpha") if isinstance(row, dict) else None)
                if alpha is None:
                    continue
                box["blocks"] += 1
                if not float(low_high[0]) <= alpha <= float(low_high[1]):
                    box["outside"].append({"date": str(entry.get("date") or ""),
                                           "alpha": round(alpha, 3)})
    for box in out.values():
        box["outside"].sort(key=lambda row: row["date"])
    return out


def mask_ranges(laps: Any, indices: Any) -> tuple[list[tuple[int, int]], list[int]]:
    """Aus markierten `start_index` die Stromstellen-Bereiche [start, end).

    DIE ZWEITE HAELFTE DES SCHLUESSELS. `start_index` allein schneidet nichts:
    ein Ausschnitt braucht auch das ENDE, und das steht weder in den Marken
    noch im Anker (der haelt die DAUER, und Dauer ist Bewegungszeit auf einer
    Stromachse - genau der Versatz aus §7). Es steht in den Laps, und nur
    dort. Deshalb liegt diese Funktion hier und nicht in `derive`: sie ist die
    einzige Stelle, an der Marken und Laps aufeinandertreffen, und der
    Schluessel soll EINE Heimat haben.

    `end_index` zeigt auf die Stelle NACH dem Abschnitt - dieselbe Konvention
    wie in derive.dfa_blocks, und derive.dfa_hours(keep=...) erwartet sie so.
    Bei der Einheit vom 01.09.2026 endet der letzte Lap auf 2859 bei 2856
    Werten; mit `<=` liefe der erste Wert des Folgeabschnitts mit - bei einem
    Intervall waere das der erste Wert der Pause.

    KEIN 120-Sekunden-Verwerfen. Das gehoert zur BLOCKMESSUNG, wo ein Median
    ueber einen kurzen harten Abschnitt sonst den Einschwingvorgang mitmisst.
    Hier wird ueber STUNDEN gelesen; ein stiller zweiter Abzug an dieser
    Stelle waere eine Rechnung, die niemand angeordnet hat.

    Zurueck kommen ZWEI Dinge, und das zweite ist der Punkt: `missing` sind
    die markierten Abschnitte, zu denen sich in diesen Laps kein Bereich
    bilden laesst. Der Aufrufer macht daraus einen Abbruch mit Grund - still
    weniger zu maskieren als markiert wurde hiesse, auf einem anderen
    Ausschnitt zu messen als der Athlet gewaehlt hat, und das Ergebnis saehe
    aus wie ein richtiges.
    """
    want = sorted({found for found in (_index(v) for v in (indices or []))
                   if found is not None})
    by_index: dict[int, int] = {}
    for lap in (laps if isinstance(laps, list) else []):
        first = lap_index(lap)
        if first is None:
            continue
        last = _index(lap.get("end_index") if isinstance(lap, dict) else None)
        if last is None or last <= first:
            continue
        by_index[first] = last
    ranges = [(i, by_index[i]) for i in want if i in by_index]
    missing = [i for i in want if i not in by_index]
    return ranges, missing


def drift(entry: Any, laps: Any) -> str | None:
    """None, wenn die Markierung noch sitzt - sonst WARUM nicht.

    Gemeldet, nicht verrechnet. Stillschweigend weiterzurechnen waere der
    stille Ausstieg (§7, vierte Fehlerklasse): ein Wert aus verschobenen
    Abschnitten sieht aus wie einer aus richtigen.

    Wer nicht pruefen kann, rechnet nicht: fehlen die Laps, ist das ein eigener
    Grund und kein "alles in Ordnung".
    """
    anchor = (entry or {}).get("anchor")
    if not isinstance(anchor, dict):
        return "lap_count"
    if not isinstance(laps, list) or not laps:
        return "laps_missing"
    if _index(anchor.get("laps")) != len(laps):
        return "lap_count"
    by_index = {}
    for lap in laps:
        found = lap_index(lap)
        if found is not None:
            by_index[found] = _seconds(lap)
    for section in anchor.get("sections") or []:
        if not isinstance(section, dict):
            return "section_moved"
        want = _index(section.get("i"))
        if want is None or want not in by_index:
            return "section_moved"
        if by_index[want] != _index(section.get("s")):
            return "section_moved"
    return None


def measurement(entry: Any, family: str = "") -> dict[str, Any] | None:
    """Das Messergebnis EINER Familie, oder nichts.

    JE FAMILIE EIN EINTRAG, seit B2b-0. Vorher hing genau eine Zahlenreihe am
    Eintrag (`hours`), und die gehoerte still der Grundlage - eine Fahrt mit
    VO2max-Marken konnte gar nichts ablegen. Der Knopf misst jetzt ALLES, was
    markiert ist, und jede Familie bekommt ihr eigenes Fach mit ihrem eigenen
    Grund.
    """
    if not isinstance(entry, dict):
        return None
    box = entry.get("measure")
    if not isinstance(box, dict):
        return None
    found = box.get(family)
    return found if isinstance(found, dict) else None


def usable_hours(entry: Any, laps: Any) -> list[Any] | None:
    """Der maskierte Stundenverlauf - oder nichts, mit Grund an der Kachel.

    DREI Gruende, nichts herauszugeben, und alle drei sind an anderer Stelle
    SICHTBAR: keine Messung, eine veraltete Messmarke, eine verschobene Fahrt.
    Diese Funktion ist die einzige Tuer, durch die maskierte Stunden in die
    Kurve gelangen - damit es nicht zwei Antworten auf eine Frage gibt.
    """
    if not isinstance(entry, dict):
        return None
    got = measurement(entry, "endurance") or {}
    hours = got.get("hours")
    if not isinstance(hours, list) or not hours:
        return None
    if _index(entry.get("v")) != MEASURE_VERSION:
        return None
    if drift(entry, laps) is not None:
        return None
    return hours


def set_mark(data: dict[str, Any], activity_id: Any, date: str, family: str,
             start_index: Any, laps: Any, set_at: str = "") -> dict[str, Any]:
    """Eine Marke SETZEN. Das Schreiben ist streng.

    Wirft ValueError mit einem Grund, den die Karte zeigen kann. Die Laps
    muessen LIVE geholt sein: gegen sie wird der Schluessel geprueft, und aus
    ihnen entsteht der Anker.

    DER HAKEN MISST NICHT. Der Eintrag steht danach mit `hours: None` und dem
    Grund daneben; gemessen wird ausschliesslich auf "uebernehmen" (P2b).
    """
    if not _valid_day(date):
        raise ValueError(f"kein gültiges Datum: {date!r}")
    if family not in FAMILIES:
        raise ValueError(f"unbekannte Familie: {family!r}")
    index = _index(start_index)
    if index is None:
        raise ValueError(f"kein gültiger Abschnittsschlüssel: {start_index!r}")

    rows = laps if isinstance(laps, list) else []
    known = {lap_index(lap) for lap in rows}
    known.discard(None)
    if index not in known:
        # HIER faellt die laufende Nummer auf. Sie ist bei einer Fahrt ohne
        # Pausen zufaellig manchmal auch ein start_index und bei jeder
        # Intervalleinheit keiner (P3a).
        raise ValueError(
            f"Abschnitt {index} kommt in dieser Fahrt nicht vor — der Schlüssel "
            f"ist der start_index des Abschnitts, nicht seine laufende Nummer"
        )

    block, key, old, marks = _open(data, activity_id)
    marks[family] = sorted(set(marks.get(family) or []) | {index})
    return _write(block, key, old, date, marks, rows, set_at)


def unset_mark(data: dict[str, Any], activity_id: Any, family: str,
               start_index: Any) -> dict[str, Any] | None:
    """Eine Marke ZURUECKNEHMEN - und zwar GENAU sie.

    DIE RUECKNAHME SITZT AUF DER EINZELNEN MARKE, nicht auf "letztem Zustand".
    Die Kritik an Label Studio trifft genau diesen Punkt: dessen Ruecknahme
    entfernt Ebenen statt der tatsaechlich zuletzt ausgefuehrten Aktion. Eine
    Ruecknahme, die etwas anderes zuruecknimmt als das Getane, ist schlimmer
    als keine (P3d).

    Ist danach keine Familie mehr uebrig, faellt der GANZE Eintrag - kein Rumpf
    bleibt stehen, und die Fahrt rechnet wieder bit-identisch wie eine nie
    markierte. Das ist eine Ruecknahme, keine Aussage.

    SIE BRAUCHT WEDER LAPS NOCH DATUM: geprueft wird beim Setzen, und das
    Datum steht im Eintrag. Sonst waere eine falsch gesetzte Marke genau dann
    nicht loszuwerden, wenn die Schnittstelle klemmt.
    """
    if family not in FAMILIES:
        raise ValueError(f"unbekannte Familie: {family!r}")
    index = _index(start_index)
    if index is None:
        raise ValueError(f"kein gültiger Abschnittsschlüssel: {start_index!r}")
    block, key, old, marks = _open(data, activity_id)
    if old is None:
        return None
    rest = sorted(set(marks.get(family) or []) - {index})
    if rest:
        marks[family] = rest
    else:
        marks.pop(family, None)
    if not marks:
        block.pop(key, None)
        return None
    return _write(block, key, old, str(old.get("date") or ""), marks, None,
                  str(old.get("set_at") or ""))


def _open(data: dict[str, Any], activity_id: Any):
    """Den Block, den Schluessel, den alten Eintrag und seine Marken holen."""
    block = data.setdefault(BLOCK, {})
    if not isinstance(block, dict):
        block = data[BLOCK] = {}
    key = str(activity_id)
    old = block.get(key) if isinstance(block.get(key), dict) else None
    marks: dict[str, list[int]] = {}
    for name in FAMILIES:
        found = marked(old, name)
        if found:
            marks[name] = found
    return block, key, old, marks


def _write(block: dict[str, Any], key: str, old: dict[str, Any] | None,
           date: str, marks: dict[str, list[int]], laps: Any,
           set_at: str) -> dict[str, Any]:
    """Den Eintrag schreiben - EINE Stelle, damit es nur eine Bauart gibt."""
    rows = laps if isinstance(laps, list) else []

    # DER ANKER WIRD JE ABSCHNITT BEIM ERSTEN MAL GESICHERT und danach nicht
    # mehr angefasst. Wuerde ihn jede weitere Marke auffrischen, verschwaende
    # ein Haken auf einer inzwischen veraenderten Fahrt die Drift STILL - und
    # genau davor schuetzt er.
    want = sorted({i for values in marks.values() for i in values})
    fresh = anchor_of(rows, want)
    kept = {
        _index(section.get("i")): section
        for section in ((old or {}).get("anchor") or {}).get("sections") or []
        if isinstance(section, dict)
    }
    by_index = {section["i"]: section for section in fresh["sections"]}
    # Der ALTE Stand gewinnt je Abschnitt; der frische fuellt nur, was neu
    # dazugekommen ist. Andersherum waere der Anker nach jedem Haken wieder
    # aktuell - und damit nutzlos.
    sections = [kept[i] if i in kept else by_index[i]
                for i in want if i in kept or i in by_index]
    anchor = {
        "laps": (_index(((old or {}).get("anchor") or {}).get("laps"))
                 if old else None) or fresh["laps"],
        "sections": sections,
    }

    entry: dict[str, Any] = {
        "date": date,
        "marks": marks,
        "anchor": anchor,
        # Eine neue oder zurueckgenommene Marke aendert den Ausschnitt, also
        # gilt eine vorhandene Messung nicht mehr. Sie faellt SICHTBAR, mit
        # Grund - nicht still.
        # JE FAMILIE EIN FACH. Leer heisst: noch nichts gemessen.
        "measure": {},
        # KEIN Anzeigetext in den Eintrag - siehe NOT_MEASURED.
        "reason": "",
        # WANN zuletzt gemessen wurde, und es UEBERLEBT das Loeschen der
        # `hours`. Sonst waere "noch nie gemessen" von "seit der Messung
        # umgehakt" nicht zu unterscheiden - und der Athlet laese nach seinem
        # Klick, es sei nie etwas angekommen. Aus `hours` ist das nicht
        # herleitbar, denn die sind gerade weg; deshalb ein Feld und kein
        # J7-Verstoss.
        "measured_at": (old or {}).get("measured_at") or None,
        "set_at": set_at,
        "v": MEASURE_VERSION,
    }
    block[key] = entry
    return entry


def set_measurement(data: dict[str, Any], activity_id: Any, family: str = "",
                    hours: Any = None, blocks: Any = None, reason: str = "",
                    measured_at: str = "") -> dict[str, Any]:
    """Das Ergebnis von "uebernehmen und messen" ablegen - JE FAMILIE.

    Die Markierung steht auch, wenn die Messung ausfaellt - dann aber MIT
    GRUND (zweite Regel aus ramp_tests). Gespeichert wird nur das Ergebnis,
    nie ein Strom (J7).

    `hours` gehoert der Grundlage (Kurve), `blocks` den Blockfamilien. Beide
    im selben Fach, weil beide dieselbe Frage beantworten - "was hat diese
    Familie an dieser Fahrt gemessen" - und zwei Faecher zwei Antworten
    waeren.
    """
    entry = entry_for(data, activity_id)
    if entry is None:
        raise ValueError(f"für Fahrt {activity_id} ist nichts markiert")
    if family not in FAMILIES:
        raise ValueError(f"unbekannte Familie: {family!r}")
    if hours is not None and not isinstance(hours, list):
        raise ValueError("Stundenverlauf muss eine Liste sein")
    if blocks is not None and not isinstance(blocks, list):
        raise ValueError("Blockliste muss eine Liste sein")
    if not isinstance(reason, str):
        raise ValueError("Grund muss Text sein")
    box = entry.get("measure")
    if not isinstance(box, dict):
        box = {}
        entry["measure"] = box
    box[family] = {"hours": hours, "blocks": blocks,
                   "reason": (reason or "")[:REASON_LIMIT]}
    entry["reason"] = ""
    # Nur eine Messung MIT Zahlen zaehlt als gemessen. Ein gescheiterter
    # Versuch traegt seinen Grund und laesst den Zustand, wie er war - sonst
    # hiesse ein Fehlschlag spaeter "die Auswahl hat sich geaendert", und das
    # waere schlicht falsch.
    if (isinstance(hours, list) and hours) or (isinstance(blocks, list) and blocks):
        entry["measured_at"] = measured_at or entry.get("measured_at") or None
    entry["v"] = MEASURE_VERSION
    return entry


def drop_hours(data: dict[str, Any], activity_id: Any, reason: str = "") -> bool:
    """Eine Messung fallen lassen, die nicht mehr gilt - MIT Grund.

    Gebraucht beim OEFFNEN einer gedrifteten Fahrt. Der Stellvertreter, den
    der Bau von P benannt hat, lautet: ein Eintrag mit `hours` ist driftfrei
    ZUM MESSZEITPUNKT - `fatigue.rides()` hat die Runden nicht und koennte es
    fuer dreihundert Fahrten auch nicht pruefen, ohne dreihundert Abrufe zu
    machen. Entschaerft wird er hier: wer die Fahrt ansieht, hat die Runden
    ohnehin geholt, und dann faellt die Messung sofort - statt erst, wenn
    jemand reagiert.

    GIBT ZURUECK, OB SICH ETWAS GEAENDERT HAT. Der Aufrufer speichert nur
    dann; ein No-op darf keinen Speichervorgang ausloesen (J7, zweite
    Auflage).
    """
    entry = entry_for(data, activity_id)
    if entry is None or not isinstance(entry.get("measure"), dict) or not entry["measure"]:
        return False
    entry["measure"] = {}
    entry["reason"] = (reason or "")[:REASON_LIMIT]
    return True


def reanchor(data: dict[str, Any], activity_id: Any, laps: Any) -> dict[str, Any]:
    """Eine verschobene Fahrt AUSDRUECKLICH bestaetigen.

    Der Weg aus der Drift, und er ist ein Knopf, kein Automatismus. Die
    Marken bleiben, der Anker wird neu genommen - und die Messung faellt, weil
    sie auf dem alten Ausschnitt sass. Passt eine Marke nicht mehr auf die
    neuen Abschnitte, wird NICHT bestaetigt, sondern neu gehakt.
    """
    entry = entry_for(data, activity_id)
    if entry is None:
        raise ValueError(f"für Fahrt {activity_id} ist nichts markiert")
    rows = laps if isinstance(laps, list) else []
    known = {lap_index(lap) for lap in rows}
    known.discard(None)
    missing = [i for i in marked(entry) if i not in known]
    if missing:
        raise ValueError(
            "Diese Abschnitte gibt es nicht mehr: "
            + ", ".join(str(i) for i in missing)
            + " — die Zuordnung ist neu zu setzen, nicht zu bestätigen"
        )
    entry["anchor"] = anchor_of(rows, marked(entry))
    entry["measure"] = {}
    entry["reason"] = ""
    entry["v"] = MEASURE_VERSION
    return entry


def remove_entry(data: dict[str, Any], activity_id: Any) -> bool:
    """Die ganze Zuordnung einer Fahrt zuruecknehmen."""
    block = data.get(BLOCK)
    if not isinstance(block, dict) or str(activity_id) not in block:
        return False
    del block[str(activity_id)]
    return True


def migrate(block: Any) -> dict[str, Any] | None:
    """Fremde oder aeltere Bestaende einlesen. Das LESEN ist nachsichtig.

    Gibt None zurueck, wenn nichts zu tun ist - der Aufrufer schreibt dann auch
    nicht. Ein No-op darf keinen Speichervorgang ausloesen (J7, zweite
    Auflage).

    Eintraege mit aelterer Messmarke behalten MARKEN UND ANKER und verlieren
    nur die Zahlen: die Aussage des Athleten verfaellt nicht, wenn sich die
    Mathematik aendert.
    """
    if not isinstance(block, dict):
        return {}
    out: dict[str, Any] = {}
    changed = False
    for activity_id, entry in block.items():
        if not isinstance(entry, dict):
            changed = True
            continue
        date = entry.get("date")
        if not _valid_day(date):
            changed = True
            continue
        marks: dict[str, list[int]] = {}
        for name in FAMILIES:
            found = marked(entry, name)
            if found:
                marks[name] = found
        # EINE STILLGELEGTE FAMILIE FAELLT NICHT STILL. Die Schleife oben laeuft
        # ueber FAMILIES und wuerde eine `long`- oder `threshold`-Marke einfach
        # nicht mitnehmen - der Eintrag saehe danach aus, als haette der Athlet
        # dort nie gehakt. Eine Migration, die etwas wegwirft, ohne es zu
        # sagen, ist die Klasse, die dieses Projekt mehrfach getroffen hat.
        retired = [name for name in RETIRED if marked(entry, name)]
        if not marks:
            # Ein Rumpf ohne Familie ist kein Eintrag (P3d) - und das ist
            # zugleich die EINE Lage, in der der Wegfall nicht sichtbar wird:
            # trug die Fahrt NUR stillgelegte Familien, faellt sie ganz und mit
            # ihr der Hinweis. Ein Rumpf, der nur noch eine Meldung traegt,
            # waere schlimmer - er saehe aus wie eine Markierung. Am Bestand
            # vom 15.09.2026 betrifft es null Fahrten (Schwelle 0, lange
            # Fahrt 0, am System gelesen); die Grenze steht hier, damit sie
            # niemand fuer eine Zusicherung haelt.
            changed = True
            continue
        anchor_raw = entry.get("anchor") if isinstance(entry.get("anchor"), dict) else {}
        sections = []
        for section in anchor_raw.get("sections") or []:
            if not isinstance(section, dict):
                continue
            index = _index(section.get("i"))
            if index is None:
                continue
            sections.append({"i": index, "s": _index(section.get("s"))})
        sections.sort(key=lambda row: row["i"])
        # Der Anker fuehrt nur noch die Abschnitte, die auch markiert SIND -
        # dieselbe Regel wie in _write. Eine Ankerstelle ohne Marke wuerde die
        # Drift an einem Abschnitt messen, der niemanden mehr interessiert, und
        # die Fahrt aus Messung und Kurve werfen, ohne dass etwas Markiertes
        # verschoben waere.
        live = {i for values in marks.values() for i in values}
        sections = [row for row in sections if row["i"] in live]
        row: dict[str, Any] = {
            "date": date,
            "marks": marks,
            "anchor": {"laps": _index(anchor_raw.get("laps")), "sections": sections},
            "measure": (entry.get("measure")
                        if isinstance(entry.get("measure"), dict) else {}),
            "reason": str(entry.get("reason") or "")[:REASON_LIMIT],
            "measured_at": str(entry.get("measured_at") or "") or None,
            "set_at": str(entry.get("set_at") or ""),
            "v": MEASURE_VERSION,
        }
        if entry.get("v") != MEASURE_VERSION and row["measure"]:
            row["measure"] = {}
            row["reason"] = ("Nach einer Änderung der Messung neu zu messen — "
                             "die Ströme liegen nicht im Archiv. Die Zuordnung "
                             "und ihr Anker bleiben stehen.")
            changed = True
        if retired:
            # Die Marken sind fort, also gilt eine Messung darauf nicht mehr -
            # sie sass auf einem Ausschnitt, den es nicht mehr gibt.
            row["measure"] = {}
            row["reason"] = RETIRED_REASON
            changed = True
        if row["reason"] in _LEGACY_NOT_MEASURED:
            # Der veraltete Anzeigetext faellt; der Zustand steht weiter in
            # `hours is None` und der Satz kommt jetzt aus dem Leseweg.
            row["reason"] = ""
            changed = True
        if row != {k: entry.get(k) for k in row}:
            changed = True
        out[str(activity_id)] = row
    return out if changed or out != block else None
