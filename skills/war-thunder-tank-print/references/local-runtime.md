# Lokale Laufzeit und reproduzierbarer Start

## Vorhandener Host, Stand 2026-11-07

Zuerst diese Pfade auf Existenz prüfen; sie sind lokale Fundstellen, keine universellen Installationspfade:

| Ressource | Pfad |
|---|---|
| Arbeitsprojekt | `%USERPROFILE%\<Dokumente>\war_thunder_print` |
| Python mit bpy | `<Arbeitsprojekt>\.venv\Scripts\python.exe` |
| Bambu Studio | `C:\Program Files\Bambu Studio\bambu-studio.exe` |
| FreeCAD-Python für Passproben | `C:\Program Files\FreeCAD 1.0\bin\python.exe` |
| WT-Spielinstallation | `C:\Program Files (x86)\Steam\steamapps\common\War Thunder` |
| uv | `uv.exe (im PATH oder lokaler Installationsort)` |

Getestet: Python 3.11, bpy 4.5.3; weitere Pakete in `assets/engine/requirements-lock.txt`. WT Asset Explorer: [Repository](https://github.com/NotNekroz/wt-asset-explorer), Commit `99c794ab102785c39e628033a09bf4ff18dbe64e` des damaligen testing-Zweigs. WT_ext_cli v0.6.6. Vor Änderungen an Versionen gezielt Kompatibilität prüfen. Keine blinden Updates der funktionierenden Pipeline.

Die vorhandenen `vendor/` und `cache/exporter/` können groß sein. Nicht rekursiv den ganzen Cache ausgeben. Exakte ID, Katalog-API und gezielte Dateisuche verwenden. DLLs über `PySide6.QtCore.QCoreApplication` **vor** dem nativen Exporter initialisieren; vorhandener Exporter erledigt dies. Spielarchive nur lesen.

## Namensauflösung

`<skill>` ist der Ordner dieses SKILL.md, `<runtime>` das vorhandene Arbeitsprojekt. Befehle zeigen PowerShell-Syntax; absolute Pfade als Argumente übergeben, nicht in zusammengesetzte Shell-Befehle interpolieren.

```powershell
& '<runtime>\.venv\Scripts\python.exe' '<skill>\scripts\vehicle_catalog.py' --project '<runtime>' --query 'BMPT-72'
```

JSON-Ausgabe lesen. Nur `status=resolved` mit `exact_id` erlaubt automatisches Fortsetzen. `ambiguous`/`needs_confirmation` zeigt konkrete Kandidaten. Ein fremdes Fahrzeug mit ähnlich geschriebenem Namen darf nicht gewählt werden. `--catalog-json` erlaubt einen vorhandenen JSON-Katalog ohne native Bibliotheken; `--refresh` aktualisiert den lokalen Katalog nach Spielupdates. Fehlen Modelle/Archive, keine Ersatzgeometrie erfinden.

## Neues Fahrzeugprojekt

`scripts/bootstrap_project.py` kopiert ausschließlich den geprüften Quellstand. Kein Download, keine Installation, kein Export oder Slicing beim Bootstrap. Es verweigert nichtleere Ziele und prüft den Bundle-Hash jedes Quellfiles.

```powershell
& '<runtime>\.venv\Scripts\python.exe' '<skill>\scripts\bootstrap_project.py' --destination '<neues-projekt>' --runtime-project '<runtime>'
```

Das vorhandene Python darf die Skripte des neuen Projekts ausführen. `.venv` nicht kopieren: Windows-Umgebungen können absolute Interpreterpfade enthalten. `local_runtime.json` merkt sich die geprüfte Interpreteradresse; neue Werkzeuge mit dieser Adresse starten. Die mitgelieferten PowerShell-Starter erwarten dagegen eine **eigene** `.venv` im Projekt.

**Zwei `pipeline.py`, nur eine gilt.** `<runtime>\tools\` ist ein älterer, BMPT-only-Stand: keine Stufen `recipe`, `check-scale`, `combine`, kein `prepare_generic.py`, `all` ohne generischen Pfad. Aus dem Runtime-Projekt nur `.venv`, `vendor/`, Spielcache, `raw/` und `export_vehicle.py` (unten) nutzen. Die Pipeline immer aus `<neues-projekt>\tools\` starten. Vor dem ersten Lauf: `pipeline.py --help` endet mit `Engine snapshot: 2026-11-25-generic`; fehlt die Zeile, ist es die falsche Kopie.

Für einen neuen Export: im vorhandenen Runtimeprojekt den allgemeinen Exporter mit exakter ID ausführen. Er schreibt eine neue `raw/<id>` und prüft existierende Snapshots. Nach Spielupdates bei veränderter Quelle einen neuen Snapshotordner nutzen; kein Original überschreiben.

```powershell
& '<runtime>\.venv\Scripts\python.exe' '<runtime>\tools\export_vehicle.py' '<exact_id>'
```

Danach frisches Fahrzeugprojekt **samt gewähltem Original** anlegen:

```powershell
& '<runtime>\.venv\Scripts\python.exe' '<skill>\scripts\bootstrap_project.py' --destination '<neues-projekt>' --runtime-project '<runtime>' --source-vehicle '<exact_id>'
```

Der zweite Befehl ist eine Alternative zum Bootstrap ohne Original, kein Aufruf auf dasselbe bereits gefüllte Ziel. Er kopiert nur GLB, Extraktionsmanifest und Inventar des gewählten Fahrzeugs, prüft Identität und SHA-256. Bei abweichendem Snapshotpfad `--source-project` auf einen Projektordner mit `raw/<id>` setzen oder kontrolliert dieselben drei Dateien kopieren und Hash prüfen.

Fehlt die vorhandene Laufzeit: Bootstrap mit beliebigem Python 3.11+ ausführen, anschließend im neuen Projekt `Setup-Panzer.ps1`. Das Setup benötigt Git und uv, lädt die festgelegten Abhängigkeiten und legt projektlokale Caches an. Installierte Versionen/Imports prüfen; Setup-Erfolg nicht aus Dateiexistenz ableiten. Bambu Studio und FreeCAD sind gesonderte lokale Anwendungen. Fehlende Programme genau benennen, vorhandene Ersatzpfade prüfen. Kein Druckerzugriff zum Erstellen einer Datei erforderlich.

## Beliebiges Fahrzeug (generischer Pfad)

Frisches Projekt per Bootstrap (mit `--runtime-project`), dann mit dem Runtime-Python die Pipeline des **neuen** Projekts starten. `pipeline.py` nutzt den aufrufenden Interpreter für alle Kindprozesse. Fehlt im Projekt `vendor/`, exportiert `--stage export` über die in `local_runtime.json` vermerkte Runtime und kopiert GLB, Manifest und Inventar hash-geprüft nach `raw/<id>`. Ein bereits vorhandener, hash-gültiger Snapshot wird wiederverwendet (`--reexport` erzwingt Neuexport).

```powershell
& '<runtime>\.venv\Scripts\python.exe' '<skill>\scripts\bootstrap_project.py' --destination '<neues-projekt>' --runtime-project '<runtime>'
& '<runtime>\.venv\Scripts\python.exe' '<neues-projekt>\tools\pipeline.py' --vehicle '<exact_id>' --scale 72 --stage all --display-name '<Name>'
```

Stufen: `export`, `recipe` (Auto-Rezept, nur wenn keins passt; `--regenerate-recipe` erneuert ein ungeprüftes), `check-scale` (Wannenfläche inkl. Reserve), `inspect` (`--render-source` für Ansicht), `prepare` (Builder nach Rezept-Schema + Montagevorschau), `package` (Einzelslices aller Teile), `combine` (eine Platte, natives Slicing, Kopie `<Name>_1-<n>_A1mini.gcode.3mf` in den Projektordner), `calibration` (Passprobe via FreeCAD; übersprungen ohne Drehturm). Laufprotokolle unter `logs/pipeline_*/run.json`, aktueller Stand zusätzlich in `logs/latest_run.json`. Dauer: Reparatur je nach Modell 10–40 min (danach Cache), Einzelslices und Gesamtslice je einige Minuten.

**Kurzer Projektpfad.** Bambu Studio slict auch bei überlangen Pfaden, scheitert dann aber beim Schreiben (`Failed exporting 3mf files`, Rückgabe −13), sobald eine Ausgabedatei die Windows-Grenze von 260 Zeichen erreicht. `package` und `combine` prüfen das vorab und brechen mit der nötigen Kürzung ab. Projekt deshalb nahe am Laufwerk anlegen, z. B. `…\3d projekte\<kurzname>`, nicht in tiefen Temp-Ordnern; lange Fahrzeug-IDs (`germ_sturmmorser_sturmtiger`) verbrauchen zusätzlich Zeichen.

### Nach Rezeptänderung

`all` nur als erster Komplettlauf. Nach Änderung am Rezept (`objects`, `excluded_objects`, `attachment`, Orientierung, Turmwerte) nacheinander, jeweils nur nach `completed` der vorigen Stufe:

```powershell
& '<runtime>\.venv\Scripts\python.exe' '<neues-projekt>\tools\pipeline.py' --vehicle '<exact_id>' --scale 72 --stage prepare --display-name '<Name>'
& '<runtime>\.venv\Scripts\python.exe' '<neues-projekt>\tools\pipeline.py' --vehicle '<exact_id>' --scale 72 --stage package --display-name '<Name>'
& '<runtime>\.venv\Scripts\python.exe' '<neues-projekt>\tools\pipeline.py' --vehicle '<exact_id>' --scale 72 --stage combine --display-name '<Name>'
```

Export, Rezepterzeugung, Inspektion und Kalibrierung bleiben gültig. Ein geändertes Rezept macht alte Freigaben ungültig (`prepare` invalidiert, `package`/`combine` prüfen Hashes), deshalb keine Stufe auslassen.

### Status richtig lesen

Erfolg nur aus `run.json` ableiten, nie aus Konsolentext oder selbst geschriebenem Echo (ein fest codiertes `PIPELINE_EXIT: 0` meldet auch einen Absturz grün):

```powershell
& '<runtime>\.venv\Scripts\python.exe' '<neues-projekt>\tools\run_status.py'
```

Exit 0 = `completed`, 1 = `failed` (Feld `error`, `failed_stages`), 3 = läuft noch oder unlesbar. Ausgabe enthält `review_flags`, `geometry_passed`, `combine_status`, `deliverable`, `deliverable_sha256`, `skipped`. Die Pipeline druckt als letzte Zeile `PIPELINE_RESULT {"status": …, "run_json": …}`. `Start-Panzer.ps1` prüft beides.

### Lange Läufe überwachen

Bewährtes Muster für das Monitor-Werkzeug (Bash): echten Exit-Code mit `$?` anhängen, Fortschritt filtern, bei `PIPELINE_EXIT` enden, `FEHLER`/`Traceback` als Ereignis melden:

```bash
( '<python>' '<projekt>/tools/pipeline.py' --vehicle '<id>' --scale 72 --stage prepare 2>&1; echo "PIPELINE_EXIT: $?" ) \
  | awk '/^(ENGINE|START|FERTIG|UEBERSPRUNGEN|ABGESCHLOSSEN|PIPELINE_RESULT)/ {print; fflush()}
         /FEHLER|Traceback|Error/ {print "EVENT " $0; fflush()}
         /^PIPELINE_EXIT/ {print; fflush(); exit}'
```

`$?` steht direkt hinter dem Pipeline-Aufruf in derselben Subshell, nie als Konstante. Kindprozess-Meldungen (`ATTACH`, `RECONNECT`, Reparatur) stehen in den Stufenprotokollen `logs/pipeline_*/NN_<stufe>.log`. Nach `PIPELINE_EXIT` immer `run_status.py` ausführen und dessen Ergebnis berichten.

## Erprobter BMPT-72-Pfad

Nur bei übereinstimmendem Originalhash, 1:72 und Profil `a1mini_02_pla`. Ein bereits geprüfter identischer Endstand kann nach erneuter Herkunfts-/Hash-/Archivprüfung wiederverwendet werden. Kein teures Neu-Slicing nur für einen neuen Dateinamen. Das BMPT-Rezept (ohne `schema`) läuft weiter über `prepare_vehicle.py`; `combine_bmpt_plate.py` bleibt für das vorhandene BMPT-Layout erhalten, `combine_plate.py` funktioniert ebenso.

```powershell
& '<project>\.venv\Scripts\python.exe' '<project>\tools\pipeline.py' --vehicle ussr_bmpt_72 --scale 72 --profile a1mini_02_pla --stage all
```

`check-pantsir` ist eine optionale Einzelstufe (Pantsir-Größenreferenz), nicht mehr Teil von `all`. CLI mit `--help` prüfen, keine Optionen erfinden.

Vorhandenes Endergebnis: `<runtime>/BMPT72_1-72_A1mini.gcode.3mf`, SHA-256 `57f24f62dc546cb8b410d3ebf7eb7b750417e1718229bc36f75cebb6845f0596`. Der Prüfbericht liegt unter `outputs/ussr_bmpt_72_1_72/bambu_gesamt/spaced_plate_report.json`. Sieben Teile, eine Platte, gemessene Fläche 163,219 × 137,774 mm inklusive Stützen/Brim, 628 Lagen, ca. 25 h 10 min und 57,38 g. Diese Angaben gelten nur für diesen Stand; echte Passprobe unbestätigt.

Pantsir-S1 bleibt Größenreferenz: 1:72, komplette Export-Außenmaße ca. 144,215 × 45,625 × 86,817 mm; ungeteiltes Fahrgestell ca. 144,215 × 43,211 × 46,438 mm. Diese Messung ist kein reparierter oder geslicter Pantsir-Bausatz.
