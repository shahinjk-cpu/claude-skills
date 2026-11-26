# war-thunder-tank-print

Claude-Code-Skill: aus dem Namen eines War-Thunder-Bodenfahrzeugs (Panzer, SPz, Jagdpanzer, Rad- oder Flakfahrzeug) wird ein mehrteiliger, montierbarer Modellbausatz als **eine native Bambu-Studio-Druckdatei** (`.gcode.3mf`).

Standardprofil: Maßstab 1:72, Bambu Lab A1 mini, 0,2-mm-Düse, PLA, 0,08-mm-Schichten. Kettenfahrzeuge bekommen Wanne, linkes und rechtes Laufwerk mit verdeckter Klebeplatte und einen drehbaren, abnehmbaren Turm auf gedrucktem Zapfen. Fahrzeuge ohne Turm (Sturmgeschütze, Kasematten) bekommen ein fest verschmolzenes Geschütz.

## Was der Skill macht

1. Fahrzeugname → exakte Katalog-ID aus der lokalen Spielinstallation (`scripts/vehicle_catalog.py`)
2. Export des Spielmodells (WT Asset Explorer, höchste Außen-LOD, ohne Texturen)
3. Automatisch gemessenes, prüfbares Fahrzeugrezept (`tools/auto_recipe.py`): Teilezuordnung, begründete Ausschlüsse, Turmringmaße
4. Druckgeometrie (`tools/prepare_generic.py`): lokale Mesh-Reparatur, Turmgelenk, Drehfreistellung, Rohranhebung, Stege, Export mit STL-Rücklesen und 360°-Rotationsprüfung
5. Einzelslices, Anordnung aller Teile auf einer Platte, natives Slicing in Bambu Studio (`tools/combine_plate.py`)
6. Fail-closed-Prüfungen über Hashes von Quelle, Rezept, Code und STL; Status in `logs/latest_run.json`

Details: [SKILL.md](SKILL.md) und [references/](references/).

## Voraussetzungen

- Windows, [Claude Code](https://claude.com/claude-code)
- installiertes War Thunder (die Modelle werden lokal gelesen, dieses Repo enthält **keine Spieldaten**)
- Python 3.11 mit `bpy` 4.5.3 (Abhängigkeiten: `assets/engine/requirements-lock.txt`, Einrichtung über `assets/engine/Setup-Panzer.ps1`; braucht Git und uv)
- [WT Asset Explorer](https://github.com/NotNekroz/wt-asset-explorer) und wt_ext_cli 0.6.6 im Laufzeitprojekt
- Bambu Studio (getestet 02.08.02.61), optional FreeCAD 1.0 für die Passprobe

## Installation

```powershell
git clone https://github.com/gingerthighs/war-thunder-tank-print "$env:USERPROFILE\.claude\skills\war-thunder-tank-print"
```

Danach in Claude Code zum Beispiel:

```
/war-thunder-tank-print Leopard 2A7V
/war-thunder-tank-print Sturmtiger, Maßstab 1:72
```

## Installations-Prompt für Agents

Diesen Text einem Coding-Agent (Claude Code oder ähnlich) geben. Er installiert den Skill und die lokale Laufzeit und prüft beides; danach reicht `/war-thunder-tank-print <Fahrzeug>`.

```text
Installiere den Claude-Code-Skill war-thunder-tank-print und richte seine lokale Laufzeit ein (Windows).

1. Skill: https://github.com/gingerthighs/war-thunder-tank-print nach
   %USERPROFILE%\.claude\skills\war-thunder-tank-print klonen. Existiert der Ordner schon als
   Git-Klon: git pull. Existiert er ohne Git: nicht überschreiben, mich fragen.
   Danach README.md, SKILL.md und references/local-runtime.md lesen.
2. Voraussetzungen prüfen und Fehlendes konkret mit Pfad/Version melden, nichts ersetzen:
   War Thunder (Standard: C:\Program Files (x86)\Steam\steamapps\common\War Thunder),
   Bambu Studio (C:\Program Files\Bambu Studioambu-studio.exe), git, uv, optional FreeCAD 1.0.
   Programme nur nach meiner Zustimmung installieren.
3. Laufzeitprojekt anlegen, kurzer Pfad (Windows-Grenze 260 Zeichen), z. B.
   %USERPROFILE%\Documents\wt_print:
   uv run --python 3.11 <skill>\scriptsootstrap_project.py --destination <laufzeitprojekt>
   Das Ziel muss leer sein oder fehlen.
4. Im Laufzeitprojekt Setup-Panzer.ps1 ausführen (lädt WT Asset Explorer auf festem Commit,
   wt_ext_cli 0.6.6, Python 3.11 mit bpy 4.5.3 nach requirements-lock.txt). Erfolg nur gelten lassen,
   wenn die letzte Zeile "Bereit: Blender 4.5.3" lautet.
5. Prüfen: Test-Panzer.ps1 im Laufzeitprojekt (FreeCAD-Pfad per -FreeCADPython, falls abweichend)
   und die Skript-Tests:
   <laufzeitprojekt>\.venv\Scripts\python.exe -m unittest discover -s <skill>\scripts -p "test_*.py"
   <laufzeitprojekt>\.venv\Scripts\python.exe <laufzeitprojekt>	ools\pipeline.py --help
   muss mit "Engine snapshot: 2026-11-25-generic" enden.
6. Katalog-Test: scripts/vehicle_catalog.py --project <laufzeitprojekt> --query "Leopard 2A7V"
   muss status "resolved" liefern (erster Aufruf entpackt Spieldaten, dauert einige Minuten).
7. Ergebnis melden: Skill-Pfad und Commit, Laufzeitprojekt, Python/bpy-Version, Testergebnis
   (bestanden/übersprungen/fehlgeschlagen mit Ausgabe), fehlende Programme.
   Nichts exportieren, slicen oder an einen Drucker senden.
```

## Tests

```powershell
& '<python>' -m unittest discover -s scripts -p 'test_*.py'
& '<python>' -m unittest discover -s assets/engine/tools -p 'test_*.py'
```

## Grenzen

- Automatisch erzeugte Rezepte ersetzen keine Sichtprüfung; Review-Hinweise stehen in `print_report.json`.
- Keine automatische Teilung zu großer Wannen und keine Mehrplattenprojekte.
- Passung und Druckbarkeit sind nur per Slicer und Geometrieprüfung belegt; die reale Passprobe steht aus.

## Lizenz

Code und Dokumentation: [MIT](LICENSE). Frei nutzbar, änderbar und weitergebbar, auch kommerziell; nur der Lizenzhinweis muss erhalten bleiben. Gilt nicht für War-Thunder-Spieldaten oder daraus erzeugte Modelle.

## Hinweis

Inoffizielles Fanprojekt, nicht mit Gaijin Entertainment verbunden. War Thunder und die Fahrzeugmodelle gehören ihren Rechteinhabern. Das Repo enthält nur Quellcode und Dokumentation; Spielmodelle werden ausschließlich lokal aus der eigenen Installation gelesen. Erzeugte Modelle nur privat verwenden.
