# Ein druckbares Bambu-Projekt aus mehreren Teilen

Diese Referenz verwenden, wenn der Nutzer mehrere geprüfte Druckteile in **einer Bambu-Datei** erhalten möchte. Zuerst eine gemeinsame Platte prüfen. Wenn diese bei festgelegtem Maßstab nicht passt, ein gemeinsames Projekt mit mehreren Platten erstellen. Maßstab, Bauteilgeometrie und vorbereitete Druckorientierungen bleiben erhalten; niemals stillschweigend verkleinern.

## Arbeitsverzeichnis und Umfang

`<project>` bezeichnet die **beschreibbare Arbeitskopie** des Engines mit `tools/`, `recipes/`, `outputs/` und eingerichtetem Python. Das gebündelte `assets/engine/` zuerst dorthin kopieren. Laufzeit, Modelle und Ergebnisse niemals im installierten Skill-Verzeichnis erzeugen. Befehle unten werden in `<project>` ausgeführt; Beispielnamen und Eingabepfade an den Auftrag anpassen.

Getestet wurde Bambu Studio **02.08.02.61 unter Windows**, A1 mini, 0,2-mm-Düse, PLA, 0,08-mm-Schichten. Installationspfad im Test: `C:\Program Files\Bambu Studio\bambu-studio.exe`. Bei anderen Versionen oder Druckern deren tatsächliche CLI/Profile prüfen; nicht dieselbe Kompatibilität behaupten.

**Allgemeiner Fahrzeugpacker: `tools/combine_plate.py`** (Pipeline-Stufe `combine`). Er liest die geprüften Teile aus `print_report.json` (über `pipeline.verified_parts`) und die Einzelslices aus `bambu/packaging_report.json`, prüft STL-Hashes und Einzelslice-Status, legt die gemessenen Stützen-/Brim-Hüllrechtecke per Bottom-Left-Packung mit 3 mm Abstand in 170 × 170 mm (vier Sortierungen × Vierteldrehung je Teil um Z, kleinste belegte Fläche gewinnt), schreibt ein Projekt mit je einem Objekt pro Teil, vergleicht jedes Mesh vor der Drehung mit der geprüften STL, sliced nativ, prüft Objektnamen im geslicten Projekt und kopiert bei `passed` `<Name>_1-<n>_A1mini.gcode.3mf` byte-identisch in `--deliver-dir`. Bericht: `bambu_gesamt/combined_report.json`. Passt die Packung nicht: Status `does_not_fit_one_plate`, kein Verkleinern.

Eine Vierteldrehung um die Bettnormale ändert keine Überhänge; Stützen werden im Gesamtslice ohnehin neu berechnet. `tools/combine_bmpt_plate.py` bleibt als erprobtes BMPT-Layout erhalten.

## Profile aus der tatsächlichen Installation

`tools/package_bambu.py` löst sowohl `inherits` als auch `include` rekursiv auf. Nur die sichtbare Profil-JSON zu kopieren lässt wichtige Maschinen-/Filamenteinstellungen aus. Die getesteten Ausgangsprofile liegen unter `resources/profiles/BBL/` neben der EXE:

| Bereich | Profil |
| --- | --- |
| Maschine | `Bambu Lab A1 mini 0.2 nozzle` |
| Prozess | `0.08mm High Quality @BBL A1M 0.2 nozzle` |
| Material | `Generic PLA @BBL A1M 0.2 nozzle` |

Die abgeflachten Dateien `profiles/machine.json`, `process.json`, `filament.json` gemeinsam aufbewahren. PLA-Temperatur und Flussgrenzen aus dem passenden Filamentprofil übernehmen. Ein anderes Materialprofil nicht durch Umbenennen zu PLA machen. Ein konkretes Nutzerfilament hat Vorrang vor dem hier getesteten Generic-PLA-Beispiel.

Der getestete Prozess nutzt `print_sequence="by layer"`, 0,08 mm Schichthöhe, 0,1 mm erste Schicht, vier Wände, 15 % Gyroid, 3 mm Außenbrim und bei Fahrzeugteilen automatische Baumstützen. `enable_arc_fitting="0"` hält die ausgegebenen Druckbahnen für den vorhandenen G0/G1-Prüfer auswertbar. Das sind Startwerte für diesen Druckauftrag, keine universellen Werte für jedes Modell. Kalibrierteile mit absichtlichem Brückentest wurden mit `--supports off` gesliced.

## Einplattenlayout mit gemessenen Stützen

Vor dem Verpacken aktuelle Geometriefreigabe und STL-Prüfsummen prüfen. Im vorhandenen Engine umfasst `pipeline.verified_parts` zusätzlich Originalexport, Maßstab, Fahrzeug, Profil, Rezept und die vier relevanten Geometriecode-Dateien. Eine alte erfolgreiche STL darf nach einer Passungsänderung nicht unverändert weitergereicht werden.

Der einfache `--single-plate`-Packer verwendet Modellgrenzen, 160 mm Regalbreite und 10 mm Abstand. Das ist ein erster Layoutversuch. Stützen und Brim können weiter wachsen als diese Modellgrenzen; der finale native Slice entscheidet über die Passung.

Für ein belastbareres Layout zuerst erfolgreiche Einzelslices auswerten:

1. Pro Teil die **Vereinigung aller Extrusionsbahnen über alle Schichten**, inklusive Linienbreite, Stützen, Brim und Skirt, bestimmen. Eine Modell-Bounding-Box oder nur die erste Schicht reicht nicht.
2. Gemessene `extrusion_bbox_xy_mm` um die ursprüngliche `plate_translation_mm` zurückverschieben. So entsteht die Stützengrenzbox relativ zur unveränderten STL.
3. Diese Rechtecke mit zusätzlichem Abstand anordnen. Im Pilot waren 3 mm zwischen den gemessenen Grenzboxen erfolgreich. Das ist ein erprobter Ausgangspunkt, keine universelle Sicherheitsdistanz.
4. Die neue XY-Translation aus der gewünschten unteren Grenzbox-Ecke berechnen. Z-Lage, Rotation und Skalierung unverändert lassen. Für einen bestehenden, am Bett ausgerichteten Bausatz `--arrange 0 --orient 0` verwenden.
5. Das komplette Layout **erneut nativ slicen**. Stützverläufe können sich mit Nachbarteilen oder neuer Position ändern; verschobene Einzelslices sind eine Prognose, kein fertiger Gesamtdruck.

Für eine Achse gilt `lokales_min = gemessenes_min - alte_translation`, anschließend `neue_translation = gewünschtes_min - lokales_min`. Das gilt für reine Translation ohne Rotation/Skalierung.

A1-mini-Ziel dieses Auftrags: höchstens **170 × 170 mm** tatsächliche belegte Fläche und sämtliche relevanten Bahnen innerhalb **180 × 180 × 180 mm**. Breite/Höhe allein genügen nicht: Auch die absolute Platzierung muss innerhalb des Bauraums liegen. Hohe schmale Teile deshalb nicht zur Flächenersparnis ungeprüft umkippen.

## 3MF-Geometrie und Objektstruktur erhalten

Ein 3MF ist ein ZIP mit XML-Ressourcen und Bambu-Metadaten. Beim Zusammenführen:

- `unit="millimeter"` beibehalten; keine automatische Einheitenkonvertierung.
- Mesh-Ressourcen und Komponenten-Wrapper mit eindeutigen IDs versehen. Alle `component.objectid`, Build-Items, Objekt-/Part-Metadaten und Platteninstanzen konsistent umschreiben. Gleiche IDs aus verschiedenen Einzelprojekten kollidieren sonst.
- Jedes Teil als eigenes Objekt erhalten. Vertices, Faces, Hierarchie und vorbereitete Orientierungen gegen die geprüfte Quelle vergleichen. Für das Abstandslayout genügt eine Änderung der Build-Translation; ein boolesches Verschmelzen ist unnötig.
- Bei bereits zusammengeführtem Projekt die unveränderten Ressourcen zusätzlich vor/nach dem Schreiben hashen. Quell-STL-Hashes, Transformationen und Objektzahl im Bericht festhalten.
- Koordinaten nicht durch grobe Dezimalrundung verändern. Die getestete Serialisierung `.9g` erhält Float32-STL-Koordinaten beim Roundtrip; sie ist keine allgemeine Garantie für beliebige Float64-Geometrie.
- Software-Vorschaubilder aus den tatsächlich platzierten Meshes neu erzeugen. Stale Thumbnails oder Auswahl-IDs nicht aus einem anderen Layout übernehmen. Ein neutraler Pick-Puffer wurde im CLI-Workflow verwendet; interaktive Auswahlfunktionen dadurch nicht als geprüft ausgeben.

## Getestete Aufrufe

Ein Manifest enthält beispielsweise `{"parts":[{"name":"part_a","path":"stl/part_a.stl"},{"name":"part_b","path":"stl/part_b.stl"}]}`. Die Pfade sind relativ zum Manifest. Eine explizite Reihenfolge ist beim einfachen Regalpacker relevant.

```powershell
# Im <project>; Eingabemanifest und Ausgabenamen für den Auftrag einsetzen.
# Zuerst Einzelslices für gemessene Stützen-/Brim-Grenzen:
& .\.venv\Scripts\python.exe .\tools\package_bambu.py `
  --manifest .\outputs\vehicle_1_72\parts.json `
  --output-dir .\outputs\vehicle_1_72\bambu_individual `
  --name vehicle_1_72 --supports auto

# Einfacher gemeinsamer Layoutversuch, neue Ausgabe getrennt erhalten:
& .\.venv\Scripts\python.exe .\tools\package_bambu.py `
  --manifest .\outputs\vehicle_1_72\parts.json `
  --output-dir .\outputs\vehicle_1_72\bambu_combined `
  --name vehicle_1_72 --supports auto --single-plate
```

Diese CLI-Formen wurden mit den Pilotdaten erfolgreich ausgeführt. `--no-slice` erzeugt nur das Projekt und ist **keine Druckfreigabe**. Ohne `--single-plate` entstehen derzeit mehrere Einzeldateien; das erfüllt allein noch keinen Auftrag „eine Datei“.

Der native Aufruf hinter `slice_project` ist:

```powershell
$Bambu = 'C:\Program Files\Bambu Studio\bambu-studio.exe'
$Profiles = (Resolve-Path '.\outputs\vehicle_1_72\bambu_combined\profiles').Path
$Project3mf = (Resolve-Path '.\outputs\vehicle_1_72\bambu_combined\vehicle_1_72.3mf').Path
$SliceDir = Join-Path (Get-Location).Path 'outputs\vehicle_1_72\bambu_combined\combined_slice'
& $Bambu --load-settings "$Profiles\machine.json;$Profiles\process.json" `
  --load-filaments "$Profiles\filament.json" --arrange 0 --orient 0 `
  --slice 1 --outputdir $SliceDir --export-3mf 'vehicle_1_72.gcode.3mf' $Project3mf
```

**`--export-3mf` erhält nur den Dateinamen.** Die getestete Bambu-Version setzt das Ausgabeverzeichnis selbst davor; ein vollständiger Pfad führte zu einem ungültigen Zielpfad. Für den normalen Ablauf den Python-Helper verwenden, weil dieser Log, Frische und Ergebnisvalidierung übernimmt.

## Native Freigabe und Grenzen der Vorschau

Vor jedem Slice-Versuch nur dessen konkret benannte alte Ausgabe und `result.json` entfernen oder isolieren. Eine stehengebliebene alte Datei darf keinen fehlgeschlagenen Lauf erfolgreich aussehen lassen. Bereits erfolgreiche andere Platten nicht unnötig erneut slicen.

Eine Freigabe benötigt gemeinsam:

- Erfolgreichen Prozessstatus und **frisches** `result.json` mit Integer `return_code == 0`, erwarteter Plattenzahl und expliziten Warnungsfeldern. Warnungen zu Stützen, Geometrie oder Platzierung untersuchen; der Helper kennzeichnet sie als `review_required`.
- Vorhandenes natives 3MF, ZIP-CRC ohne Fehler, erwartete G-code-Datei je Platte und passende eingebettete G-code-MD5, soweit geliefert. Die getesteten nativen Ausgaben enthielten MD5-Dateien.
- Eingebettetes Maschinenmodell, Düse, Filament, Layerhöhe und Druckreihenfolge passend zum Auftrag. Nur den Dateinamen des Projekts zu prüfen reicht nicht.
- Alle erwarteten Meshes, Platteninstanzen und tatsächlich gedruckten Objektlabels. Im Einplatten-Pilot wurden sieben Build-Items, sieben Namen und G-code-Labels 1–7 geprüft.
- Numerische Prüfung **aller relevanten Schichten**: Extrusionsgrenzen inklusive halber Linienbreite, absolute XY-Bauraumgrenzen und maximale Layerhöhe. Der vorhandene Prüfer berücksichtigt G90/G91, M82/M83 und G92. Unerwartete Druckbögen G2/G3 werden abgelehnt, statt deren Verlauf aus Endpunkten zu erraten.

Herstellerspezifische Start-, Reinigungs- und Purge-Makros werden bei der **Modellfläche** getrennt behandelt. Sie können außerhalb der Modellfläche liegen. Das ersetzt keine Prüfung, dass das passende unveränderte Maschinenprofil verwendet wird.

`layers.png` zeigt ausgewählte echte G-code-Schichten. Das ist eine Stichprobenansicht, keine visuelle Prüfung jeder Schicht. Die numerische Grenzprüfung umfasst alle Schichten; sie bestätigt weder globale Mindestwandstärke noch jede ungestützte Insel oder reale Haftung/Passung. Ein schönes Thumbnail ist kein Slice-Nachweis. Gewünschte vollständige Schichtvorschau zusätzlich im nativen Projekt zugänglich machen und Prüfgrenzen im Bericht benennen.

## Begrenzte Wiederholung bei nativem Absturz

Beim getesteten Windows-CLI trat sporadisch **0xC0000005 / 3221225477** vor verwertbarem Ergebnis auf. Identische Dateien wurden im erneuten Versuch erfolgreich verarbeitet. Der Ursprung wurde nicht abschließend diagnostiziert; ein leerer Log beweist keinen Geometriefehler.

`run_native` wiederholt ausschließlich diesen Exitcode, insgesamt höchstens drei Versuche, mit kurzen Pausen und eigenem Log pro Versuch. Normale Slicerfehler, Warnungen oder ungültige Geometrie nicht auf diese Weise ignorieren. Nach ausgeschöpftem Limit fehlschlagen und den konkreten Lauf untersuchen.

Keine unbelegten Headless-Schalter ergänzen: `--sw-renderer` wurde von der getesteten nativen CLI zurückgewiesen. Software-Thumbnails verringerten die Abhängigkeit der Exportvorschau von OpenGL; daraus folgt kein garantierter vollständig grafikfreier Start. Keine ungetesteten DLL-Einstiegspunkte als normalen Produktionsweg verwenden. Nur eigene eindeutig identifizierte CLI-Prozesse beenden; eine offene Bambu-GUI des Nutzers gehört nicht dazu.

## Wenn eine Platte nicht passt

Den vereinbarten Maßstab erhalten. **Ein gemeinsames Bambu-Projekt mit mehreren Platten** ist der nächste Weg: Teile zu Platten zuordnen, jede Platte separat prüfen und die Platten samt korrekter Indizes, Instanzen, Thumbnails und Druckdaten in einer nativen Projektdatei erhalten. Eine ZIP-Sammlung mehrerer 3MF-Dateien ist kein solches Projekt.

Der aktuelle Helper implementiert diesen Mehrplatten-Export noch nicht; sein nativer Prüfer erwartet genau eine G-code-Datei. Dafür Bambu Studio oder eine gezielte Erweiterung verwenden und die Prüfung auf die tatsächliche Anzahl Platten erweitern. Einen ungetesteten Mehrplatten-CLI-Aufruf nicht als bereits verfügbare Automatisierung darstellen. Falls nur das bearbeitbare Mehrplattenprojekt fertig ist, offen angeben, welche Platten noch gesliced werden müssen.

## Auslieferung

Bei erfolgreicher Einplatte das **native, geslicte 3MF mit Projektgeometrie und G-code** als eine klar benannte Datei ausliefern, z. B. `<fahrzeug>_1-<maßstab>_<drucker>.gcode.3mf`. Die rein editierbare Ausgangs-3MF kann intern zusätzlich erhalten bleiben. Beim Kopieren der fertigen Datei Byteidentität per SHA-256 prüfen; keine Geometrieänderung nach der nativen Prüfung einschleusen.

Dem Nutzer Dateilink, Platten-/Teilzahl, passendes Druckprofil sowie native Zeit-/Materialschätzung nennen. Digitale Freigabe und ausstehende reale Passprobe auseinanderhalten. Das Erstellen der Datei startet keinen Druckauftrag.
