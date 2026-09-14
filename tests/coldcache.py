"""Jeder Testlauf bekommt einen FRISCHEN Bytecode-Cache. Vor jedem Import.

WARUM DAS HIER STEHT UND NICHT ALS REGEL IM DOKUMENT
Python entscheidet ueber die Gueltigkeit einer `.pyc` anhand von mtime UND
Groesse der Quelldatei. Eine Mutation, die gleich lang ist und in derselben
Sekunde geschrieben wird - also genau das, was eine Gegenprobe tut - sieht
damit aus wie keine Aenderung. Python laedt dann die ALTE Fassung, der Test
laeuft gegen unveraenderten Code und meldet gruen. **Eine Gegenprobe, die die
alte Fassung misst, ist keine.**

Das ist in 0.50.0 schon einmal passiert (§7, elfter Fall): eine Ersetzung, die
ihren Text verfehlte. Dort war der Fix eine Trefferzusicherung auf der DATEI -
und die reicht nicht, denn sie prueft, was auf der Platte steht, nicht was der
Interpreter daraus laedt. Der zweite Anlauf war `python3 -B`, und der ist noch
schlechter: er sieht aus wie eine Loesung und ist keine. **`-B` verhindert nur
das SCHREIBEN neuer Dateien, vorhandene liest Python weiterhin.** Nachgestellt:

    Quelle 100 -> 999, gleiche Laenge, mtime zurueckgesetzt
    python3            -> 100   (Cache)
    python3 -B         -> 100   (Cache, trotz -B)
    frischer Prefix    -> 999
    rm -rf __pycache__ -> 999

WARUM EIN FRISCHES VERZEICHNIS UND NICHT LOESCHEN
Beides wirkt. Geloescht werden muss aber VOR jedem Lauf, an jeder Aufrufstelle,
von jemandem, der daran denkt - eine handgepflegte Regel, und die schuetzt in
diesem Projekt nachweislich bis zum naechsten Mal, an dem niemand daran denkt
(§7, vierte Bauregel). Ein frisches Verzeichnis ist dagegen KALT VON BAUART:
es gibt nichts zu invalidieren, die Laenge der Mutation spielt keine Rolle, die
Sekunde auch nicht. Und es loescht nichts - ein `rm -rf` mit dem falschen Pfad
ist ein eigenes Risiko.

Der Import muss VOR dem ersten Import eines Bauteils stehen, sonst ist das
Modul schon geladen. Ein Waechter in test_suite_hygiene erzwingt das, damit die
naechste Testdatei es nicht vergisst.
"""

from __future__ import annotations

import atexit
import shutil
import sys
import tempfile

PREFIX = tempfile.mkdtemp(prefix="ha-intervals-pyc-")
sys.pycache_prefix = PREFIX
atexit.register(shutil.rmtree, PREFIX, ignore_errors=True)
