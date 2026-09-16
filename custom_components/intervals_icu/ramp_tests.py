"""Stufentest-Archiv: welche Fahrten Tests waren, und was sie gemessen haben.

WARUM DIESER BLOCK UEBERHAUPT EXISTIERT
Die Auswertung braucht den Strom je Sekunde. Der Import wirft die Stroeme nach
dem Reduzieren weg (importer.async_import_dfa) - im Archiv liegen Summary,
Stundenverlauf und Bloecke, kein Sekundenstrom. Eine Gerade durch den Abfall
von DFA a1 ist daraus nicht mehr zu legen.

Deshalb dieselbe Mechanik wie beim Durability-Protokoll, das dieser Test
abgeloest hat: der Athlet MARKIERT eine Fahrt, die Stroeme werden dabei LIVE
und UNGEDUENNT geholt, gemessen, und nur das Ergebnis wird gespeichert. Kein
Algorithmus-Bump, keine Neuberechnung des Bestands - nur die eine markierte
Fahrt wird angefasst.

DREI REGELN, UEBERNOMMEN AUS K2 UND HIER GENAUSO GUELTIG
  1. **Keine Erkennung.** "Lange Rolleneinheit mit steigender Leistung, das
     wird der Stufentest gewesen sein" ist eine Behauptung ueber eine Fahrt,
     von der das System nichts weiss. Der Athlet markiert.
  2. **Keine stille Messung.** Schlaegt der Abruf fehl oder traegt die Fahrt
     keinen auswertbaren Abfall, steht die Markierung TROTZDEM - aber mit dem
     Grund daneben. Eine Markierung mit leeren Zahlen und ohne Grund ist der
     stille Ausstieg aus 0.42.1.
  3. **Ruecknehmbar.** Eine falsch markierte Fahrt darf nicht heissen, das
     Archiv von Hand zu reparieren.

WAS GESPEICHERT WIRD UND WAS NICHT
Nur die gemessenen Zahlen, nie Stroeme (J7). Der Zustand am Testtag wird auch
nicht gespeichert - er ist aus state_series() fuer das Datum ableitbar,
dieselbe Regel wie bei den Stroemen.

DER ABLAUF IST EINTEILIG, anders als beim Durability-Protokoll: ein Termin,
eine Fahrt, drei Zahlen. Es gibt deshalb weder Testarten noch eine Paarung -
und damit auch keine Stelle, an der etwas automatisch gepaart werden koennte.
"""

from __future__ import annotations

from typing import Any

BLOCK = "ramp_tests"

# Wird erhoeht, wenn sich die MESSUNG aendert - nicht die Anzeige. Eintraege
# mit aelterer Marke gelten als ueberholt und werden zum Neumessen angeboten:
# die Stroeme liegen nicht im Archiv, eine Korrektur erreicht die gespeicherten
# Werte sonst nie.
# 2 = Rechenweg e1 (16.09.2026): Segment ab Rampenbeginn bis Lastende statt vom
#     Hochpunkt bis zum ersten Lauf unter 0,5; Protokollpruefung. 0.59.0 schrieb 1.
MEASURE_VERSION = 2

NOTE_LIMIT = 256

SOURCES = [
    "Rogers, Giles, Draper, Hoos, Gronwald, Front Physiol 11:596567 (2021): "
    "DFA a1 erreicht 0,75 an der ersten ventilatorischen Schwelle. LAUFBAND, "
    "15 Läufer, Bruce-Protokoll bis zur willentlichen Erschöpfung.",
    "Rogers, Giles, Draper, Mourot, Gronwald, JFMK 6:38 (2021): derselbe "
    "Zusammenhang für 0,5 und die zweite Schwelle. LAUFBAND.",
    "Rogers, Murias, Fleitas-Paniagua, IJSPP 19(12) (2024): die "
    "personalisierte erste Schwelle, mittig zwischen dem Hochpunkt der frühen "
    "Rampe und 0,5. Bessere Übereinstimmung als der feste Wert, aber "
    "Korrelationen nur 0,67 bis 0,70.",
    "Olieslagers u. a., Physiol Rep 14:e70777 (2026): Stufentest auf dem Rad, "
    "21 Trainierte. HRVT1 zeigte schlechte Übereinstimmung mit LT1/VT1, die "
    "personalisierte Variante nur triviale bis mittlere Korrelationen — beide "
    "mit erheblichem systematischem Bias. HRVT2 dagegen deutlich besser.",
    "Meta-Analyse, Sports Med Open (2024), 50 Studien und 1.160 Personen: "
    "HRV-Schwellen allgemein stimmen gut mit Laktat- und "
    "Atemgasschwellen überein (r = 0,85). Das gilt für ALLE dort geprüften "
    "HRV-Verfahren zusammen; RMSSD war für die erste Schwelle das genaueste, "
    "DFA a1 das zweite — und ruht dort auf sechs Studien.",
]


def _valid_day(day: Any) -> bool:
    if not isinstance(day, str) or len(day) != 10:
        return False
    return day[4] == "-" and day[7] == "-" and day[:4].isdigit()


def entry_for(data: dict[str, Any], activity_id: Any) -> dict[str, Any] | None:
    block = data.get(BLOCK)
    if not isinstance(block, dict):
        return None
    entry = block.get(str(activity_id))
    return entry if isinstance(entry, dict) else None


def entries(data: dict[str, Any]) -> list[dict[str, Any]]:
    """Alle markierten Tests, aelteste zuerst.

    Die Reihenfolge ist die des DATUMS und nicht die der Aktivitaets-ID: eine
    nachtraeglich markierte aeltere Fahrt gehoert an ihren Platz, nicht ans
    Ende.
    """
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


def latest(data: dict[str, Any]) -> dict[str, Any] | None:
    """Der juengste Test, der ueberhaupt etwas gemessen hat.

    Ein markierter Test OHNE Messung ist kein Anker - er waere sonst der
    juengste und wuerde einen aelteren, gueltigen verdraengen. Er bleibt aber
    in entries() sichtbar, samt Grund.
    """
    for row in reversed(entries(data)):
        if (row.get("result") or {}).get("hrvt1") or (row.get("result") or {}).get("hrvt2"):
            return row
    return None


def set_entry(data: dict[str, Any], activity_id: Any, date: str,
              result: Any = None, reason: str = "", note: str = "",
              set_at: str = "") -> dict[str, Any]:
    """Eine Fahrt als Stufentest markieren. Das SCHREIBEN ist streng.

    Die Nachsicht von migrate() gilt fuer fremde Daten, nicht fuer selbst
    erzeugte - dieselbe Trennung wie in day_context. Wirft ValueError mit
    einem Grund, den die Karte zeigen kann.
    """
    if not _valid_day(date):
        raise ValueError(f"kein gültiges Datum: {date!r}")
    if not isinstance(note, str):
        raise ValueError("Notiz muss Text sein")
    if not isinstance(reason, str):
        raise ValueError("Grund muss Text sein")
    if result is not None and not isinstance(result, dict):
        raise ValueError("Messergebnis muss ein Block sein")
    entry: dict[str, Any] = {
        "date": date,
        "result": result,
        # Warum KEINE Zahlen da sind, wenn keine da sind. Ein leeres Feld ohne
        # Grund ist die Luecke, die niemand erklaeren kann.
        "reason": reason[:NOTE_LIMIT],
        "note": note[:NOTE_LIMIT],
        "set_at": set_at,
        "v": MEASURE_VERSION,
    }
    data.setdefault(BLOCK, {})[str(activity_id)] = entry
    return entry


def remove_entry(data: dict[str, Any], activity_id: Any) -> bool:
    """Eine Markierung VOLLSTAENDIG zuruecknehmen.

    Eine Ruecknahme, keine Aussage: danach rechnet die Fahrt genau wie eine,
    die nie markiert war - also bleibt kein Rumpf zurueck.
    """
    block = data.get(BLOCK)
    if not isinstance(block, dict) or str(activity_id) not in block:
        return False
    del block[str(activity_id)]
    return True


def migrate(block: Any) -> dict[str, Any] | None:
    """Fremde oder aeltere Bestaende einlesen. Das LESEN ist nachsichtig.

    Gibt None zurueck, wenn nichts zu tun ist - der Aufrufer schreibt dann
    auch nicht. Eintraege mit einer aelteren Messmarke behalten ihren Platz
    und ihr Datum, verlieren aber das Ergebnis: die Zahl waere sonst nach
    einer Korrektur der Messung stillschweigend die alte. Der Grund sagt es.
    """
    # Kein dict heisst: es gibt keinen brauchbaren Block, also einen leeren -
    # und zwar AUCH fuer None. Die Migration laeuft nur ueber einen Bestand,
    # der schon geladen ist; ein fehlender Block wird vom Grundgeruest
    # aufgefuellt, nicht hier.
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
        row: dict[str, Any] = {
            "date": date,
            "result": entry.get("result") if isinstance(entry.get("result"), dict) else None,
            "reason": str(entry.get("reason") or "")[:NOTE_LIMIT],
            "note": str(entry.get("note") or "")[:NOTE_LIMIT],
            "set_at": str(entry.get("set_at") or ""),
            "v": MEASURE_VERSION,
        }
        if entry.get("v") != MEASURE_VERSION and row["result"] is not None:
            row["result"] = None
            row["reason"] = ("Nach einer Änderung der Messung neu zu messen — "
                             "die Ströme liegen nicht im Archiv.")
            changed = True
        if row != {k: entry.get(k) for k in row}:
            changed = True
        out[str(activity_id)] = row
    return out if changed or out != block else None
