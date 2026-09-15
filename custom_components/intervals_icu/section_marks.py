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
MEASURE_VERSION = 1

# Sechs Familien mit Abschnitts-Haken. Der Stufentest steht NICHT dabei - eine
# Messfahrt ist als GANZES eine Messfahrt, es gibt daran keinen Abschnitt zu
# markieren, und sie hat mit ramp_tests ihren eigenen Block.
FAMILIES: tuple[str, ...] = (
    "vo2max", "sweetspot", "tempo", "threshold", "endurance", "long",
)

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
NOT_MEASURED = ("Markiert, noch nicht gemessen — der Knopf dafür kommt mit der "
                "Messung.")

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


def usable_hours(entry: Any, laps: Any) -> list[Any] | None:
    """Der maskierte Stundenverlauf - oder nichts, mit Grund an der Kachel.

    DREI Gruende, nichts herauszugeben, und alle drei sind an anderer Stelle
    SICHTBAR: keine Messung, eine veraltete Messmarke, eine verschobene Fahrt.
    Diese Funktion ist die einzige Tuer, durch die maskierte Stunden in die
    Kurve gelangen - damit es nicht zwei Antworten auf eine Frage gibt.
    """
    if not isinstance(entry, dict):
        return None
    hours = entry.get("hours")
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
        "hours": None,
        # KEIN Anzeigetext in den Eintrag - siehe NOT_MEASURED.
        "reason": "",
        "set_at": set_at,
        "v": MEASURE_VERSION,
    }
    block[key] = entry
    return entry


def set_measurement(data: dict[str, Any], activity_id: Any,
                    hours: Any = None, reason: str = "") -> dict[str, Any]:
    """Das Ergebnis von "uebernehmen und messen" ablegen.

    Die Markierung steht auch, wenn die Messung ausfaellt - dann aber MIT
    GRUND (zweite Regel aus ramp_tests). Gespeichert wird nur das Ergebnis,
    nie ein Strom (J7).
    """
    entry = entry_for(data, activity_id)
    if entry is None:
        raise ValueError(f"für Fahrt {activity_id} ist nichts markiert")
    if hours is not None and not isinstance(hours, list):
        raise ValueError("Stundenverlauf muss eine Liste sein")
    if not isinstance(reason, str):
        raise ValueError("Grund muss Text sein")
    entry["hours"] = hours
    entry["reason"] = (reason or "")[:REASON_LIMIT]
    entry["v"] = MEASURE_VERSION
    return entry


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
    entry["hours"] = None
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
        if not marks:
            # Ein Rumpf ohne Familie ist kein Eintrag (P3d).
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
        row: dict[str, Any] = {
            "date": date,
            "marks": marks,
            "anchor": {"laps": _index(anchor_raw.get("laps")), "sections": sections},
            "hours": entry.get("hours") if isinstance(entry.get("hours"), list) else None,
            "reason": str(entry.get("reason") or "")[:REASON_LIMIT],
            "set_at": str(entry.get("set_at") or ""),
            "v": MEASURE_VERSION,
        }
        if entry.get("v") != MEASURE_VERSION and row["hours"] is not None:
            row["hours"] = None
            row["reason"] = ("Nach einer Änderung der Messung neu zu messen — "
                             "die Ströme liegen nicht im Archiv. Die Zuordnung "
                             "und ihr Anker bleiben stehen.")
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
