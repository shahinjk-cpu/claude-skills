---
name: war-thunder-tank-print
description: Erzeuge aus einem beliebigen War-Thunder-Bodenfahrzeugnamen (Panzer, SPz, Jagdpanzer, Rad-/Flakfahrzeug) einen mehrteiligen, montierbaren Modellbausatz als eine native Bambu-Studio-Druckdatei (.gcode.3mf). Nutze lokale Spielmodelle, automatisch gemessene und prüfbare Fahrzeugrezepte und geprüfte Druckgeometrie. Anwenden bei War-Thunder-Bodenfahrzeugen für den 3D-Druck, nicht bei reiner Spielberatung.
---

# War-Thunder-Fahrzeug → eine Bambu-Druckdatei

Liefere **eine native `.gcode.3mf` mit allen Bausatzteilen**. Bevorzugt eine Platte; wenn bei gewähltem Maßstab nicht möglich, ein geprüftes Projekt mit mehreren Platten. Eine ZIP, einzelne STL oder ein bloß umbenanntes ZIP erfüllen diesen Auftrag nicht. Arbeite bis zur Datei und deren Prüfung; beschreibe nicht nur den möglichen Ablauf.

## Vorgaben dieses Nutzers

Ohne abweichende aktuelle Angabe: **1:72, Bambu A1 mini, 0,2-mm-Düse, PLA, 0,08-mm-Schichten**; erste Schicht gemäß geprüftem Profil. Bauraum 180 × 180 × 180 mm, angestrebte belegte XY-Fläche einschließlich Brim und Stützen höchstens 170 × 170 mm. Temperatur aus passendem Filamentprofil.

Abnehmbarer, drehbarer Turm über gedruckten Zapfen, falls Fahrzeug und Geometrie das zulassen. Keine zusätzlichen Magnete oder Schrauben. Startspiel 0,20 mm **je Seite**, Passprobe 0,15/0,20/0,25 mm; kleine Waffenteile mit formschlüssigen Klebeverbindungen und fester Höhenrichtung. Strukturelles Wandziel zunächst 0,8 mm, gezielt verstärken. Das ist keine nachgewiesene Mindestdicke jedes Details.

Diese Defaults dürfen durch Nutzerwünsche ersetzt werden. Einen gewünschten Maßstab nicht stillschweigend verkleinern. Keine echte Passform oder durchgehende Kollisionsfreiheit behaupten, bevor entsprechend nachgewiesen. Druckerübertragung und Druckstart gehören nicht zum Erstellen der Datei.

## Name und Arbeitsumgebung

Lies [local-runtime.md](references/local-runtime.md) für vorhandene lokale Werkzeuge, Bootstrap und Befehle. Arbeite in einem beschreibbaren Fahrzeugprojekt, nicht im installierten Skill. `assets/engine` enthält den getesteten Quellstand, den generischen Builder und das BMPT-Rezept, **keine Spielmodelle und keine Python-Umgebung**.

**Nur die Pipeline der Projekt-Kopie verwenden.** Jedes Fahrzeug bekommt per `scripts/bootstrap_project.py` ein eigenes Projekt mit aktuellem `tools/`. Das vorhandene Runtime-Projekt (mit `.venv`, `vendor/`, Spielcache) liefert nur Interpreter, Exporter und Rohdaten; sein `tools/pipeline.py` ist ein alter BMPT-Stand ohne `recipe`, `combine` und generischen Builder. Nie `<runtime>\tools\pipeline.py` starten. Prüfung: `pipeline.py --help` muss mit `Engine snapshot: 2026-11-25-generic` enden, und jeder Lauf druckt zuerst `ENGINE 2026-11-25-generic`.

1. Löse den Namen mit `scripts/vehicle_catalog.py` gegen den lokalen WT-Katalog auf. Verwende dessen exakte Fahrzeug-ID. Nur Bodenfahrzeuge (`type: Tanks`) gelten als plausibel; Flugzeuge, Hubschrauber und Schiffe mit gleichem Namen landen in `ignored_non_ground`. Ein exakter Name oder eine exakte ID ergibt `resolved`, auch wenn es längere Varianten (`variants`, z. B. „IS-2 (1944)“ zu „IS-2“) oder Länderkopien mit gleichem Modell (`equivalent_ids`) gibt. Bei gleichem Namen mit verschiedenen Modellen gewinnt der Name ohne Sonderzeichen-Präfix (Länderkopie, Staffel, Event). **Nur nachfragen, wenn mehr als ein plausibles Bodenfahrzeug mit unterschiedlichem Modell übrig bleibt** (`ambiguous`, z. B. „T28“/„T-28“) oder der Treffer nur fuzzy ist (`needs_confirmation`). `variants` und `equivalent_ids` in der Antwort nennen, nicht abfragen. Ingame-/Umgangsnamen stehen in `ALIASES` in `vehicle_catalog.py` (z. B. „Sturmtiger“ → `germ_sturmmorser_sturmtiger`, Katalogname „38 cm Sturmmörser“). Gelten nur, wenn die ID im Katalog existiert. Neue Aliase dort ergänzen und Test hinzufügen. Installation, Katalogprüfung und allgemeine Vorbereitung dürfen parallel weitergehen. Premiumstatus nur als bestätigt ausgeben, wenn belegt.
2. Prüfe vorhandene Originalexporte und deren SHA-256. Behalte Rohdaten unverändert. WT Asset Explorer mit höchster intakter Außen-LOD, ohne Effekte und ohne Texturen exportieren. Ein Texturbild ist keine druckbare Geometrie.
3. Rezept: Ein bestehendes Rezept nur bei passender ID, Originalhash, Maßstab und Druckprofil verwenden. Sonst erzeugt `--stage recipe` (`tools/auto_recipe.py`) ein **Schema-2-Rezept** aus dem Modell: vollständige Objektzuordnung, begründete Ausschlüsse, gemessene Turmringwerte. Danach Zuordnung und Ausschlüsse sichten, wie in [vehicle-recipe.md](references/vehicle-recipe.md) beschrieben.

**Ein Ablauf für jedes Bodenfahrzeug:**

```powershell
& '<python>' '<project>\tools\pipeline.py' --vehicle '<exact_id>' --scale 72 --stage all --display-name '<Name>'
```

`all` = `export` → `recipe` → `check-scale` → `inspect` → `prepare` → `package` → `combine` → `calibration`, nur für den **ersten Komplettlauf**. Schema-2-Rezepte laufen über `prepare_generic.py`; nur das handgeprüfte BMPT-Rezept nutzt weiterhin `prepare_vehicle.py`. Das Ergebnis `<Name>_1-<n>_A1mini.gcode.3mf` landet im Projektordner.

**Nach einer Rezeptänderung** (Zuordnung, Ausschluss, `attachment`, Orientierung, Turmwerte) nur `--stage prepare`, dann `--stage package`, dann `--stage combine`, jeweils einzeln und nur nach Erfolg der vorigen. Kein `all`: Export, Rezept, Inspektion und Kalibrierung sind unverändert und kosten nur Zeit. `calibration` wird bei Fahrzeugen ohne Drehturm (`turret.mode` ≠ `rotating`) automatisch übersprungen (Event `skipped` in `run.json`), weil die Zapfen-Passprobe dort nichts prüft.

**Erfolg nur aus dem Laufprotokoll lesen**, nie aus Konsolentext oder einem selbst geschriebenen Echo: `logs/latest_run.json` (bzw. `logs/pipeline_*/run.json`) mit `status` `completed`/`failed`, `error`, `review_flags`, `deliverable` und `deliverable_sha256`; die letzte Ausgabezeile `PIPELINE_RESULT {…}` enthält dasselbe. `tools/run_status.py` fasst das zusammen und endet mit Exit 0 (completed), 1 (failed) oder 3 (läuft/unlesbar). Bei langen Läufen das Überwachungsmuster aus [local-runtime.md](references/local-runtime.md#lange-läufe-überwachen) verwenden.

**Was automatisch geht, was nicht:** Kettenfahrzeuge → Wanne, linkes/rechtes Laufwerk mit verdeckter Klebeplatte, drehbarer Turm mit Rohr. Radfahrzeuge → Räder an der Wanne. Fahrzeuge ohne Turmkörper (Sturmgeschütze, Kasematten, Sturmtiger; auch wenn `bone_turret` nur das Geschütz trägt) → kein Drehgelenk, Geschütz fest mit der Wanne verschmolzen (`gun_group` mit `merge_into: hull`). Nicht automatisch: Teilung zu großer Wannen, getrenntes Rohr ohne geprüfte Klebeschlüssel, Mehrplattenprojekte. Dann konkret melden und Nutzer entscheiden lassen (anderer Maßstab, Rezept anpassen).

## Geometrie und Montage

Lies [mesh-and-joints.md](references/mesh-and-joints.md) vor einer Geometrieänderung. Prüfe reale Abmessungen, GLB-Einheiten, Welttransformationen, Spiegelung und Drehpunkte; Meter → Millimeter mit `1000 / Maßstabsnenner`. Bewahre Quelle, Bauzustand und Druckorientierungen getrennt.

Teile nach dem konkreten Fahrzeug wählen: Wanne, linkes/rechtes Laufwerk mit festen Ketten, Turm sowie empfindliche Rohr-/Anbauteile sind ein Ausgangspunkt, keine vorgeschriebene Teilezahl. Bauteilzuordnung und ausgeschlossene Schadens-, Innen- oder Effektgeometrie speichern. Keine sichtbaren Teile löschen, nur damit ein Mesh geschlossen wird. Details lokal reparieren; pauschales Voxelverschmelzen vermeiden. Jede sichtbare Vereinfachung im Bericht aufführen.

Nach `prepare` immer `assembly_preview.png`, `assembly_exploded.png` ansehen und `print_report.json:review_flags` lesen (Ersatzgeometrie, entfernte Deckdetails, blockierte Turmwinkel, Stege über > 1 mm Lücke, freistehende Stege < 1 mm, viele verbundene Einzelschalen, Steg-Wiederholungen). Ein Review-Hinweis ist kein Fehler, muss aber in der Antwort stehen. Verbindungen im montierten Zustand konstruieren, Zugänglichkeit beim Zusammenbau prüfen. Turmspiel einschließlich möglicher Exzentrizität testen. Fertige STL erneut einlesen: geschlossen, positive Volumen, keine defekten Kanten oder ungewollten losen Fragmente. Kollisionsprüfung mit **final exportierten** Teilen und ihren rückführbaren Montagepositionen wiederholen. Numerische Toleranz, getestete Winkel/Positionen und verbleibende Risiken dokumentieren.

## Eine Datei, native Prüfung

Lies [bambu-single-file.md](references/bambu-single-file.md) vor dem Slicen. Druckorientierungen erhalten; Teile über XY-Translation und höchstens Vierteldrehung um die Bettnormale platzieren (`tools/combine_plate.py`, für jedes Fahrzeug). Mit tatsächlich geslicten Stütz-/Brimflächen planen, nicht nur STL-Abmessungen. Falls eine Platte nicht reicht (`does_not_fit_one_plate`), mehrere Platten innerhalb **einer** nativen Datei prüfen; das ist noch nicht automatisiert.

Nur nach folgenden Gates als druckvorbereitet ausgeben:

- Herkunft/Rezepte/Geometriecode/STL-Hashes gehören zum aktuellen Lauf; fehlgeschlagene Läufe dürfen keine alten PASS-Berichte hinterlassen.
- Alle Druckteile nach Datei-Roundtrip geschlossen und montierbar; notwendige strukturelle Verstärkungen sowie Detailänderungen geprüft und dokumentiert.
- Native Bambu-Profile stimmen mit Drucker, Düse, Material und Schichthöhe überein; Ergebnisdatei, Plattenzahl, Warnungen, ZIP-CRC und G-Code-Prüfsummen geprüft.
- Alle Extrusionslagen einschließlich Linienbreite, Stützen und Brim automatisiert auf Bauraum geprüft; kritische Schichten/Überhänge visuell kontrolliert. Stichproben nicht als vollständige visuelle Prüfung bezeichnen.
- Alle Teile sind in der finalen Datei enthalten; realer Druck und Passprobe bleiben bis zum Nutzerfeedback unbestätigt.

Ungeklärte Slicerwarnungen, fehlende Geometrie, Übermaß oder ungültige Körper → korrigieren, nicht als fertig kaschieren. Wenn nur eine externe Voraussetzung fehlt, benenne sie konkret und liefere den überprüften Zwischenstand mit entsprechendem Status.

## Ergebnis

Lege die eine finale Datei mit verständlichem Namen im Nutzerprojekt ab. Behalte separat Originalexport, Rezept, bearbeitbare `.blend`, STL, Montagevorschau und Prüfbericht für spätere Änderungen. Passprobe/Detailtest können eigene Hilfsdateien bleiben; sie ersetzen nicht die vollständige Fahrzeugdatei.

Antworte mit Dateilink, Fahrzeug/Variante, Maßstab, Profil, Teile-/Plattenzahl, Slicerzeit und Materialbedarf. Nenne wesentliche Vereinfachungen, Review-Hinweise, automatisch erzeugtes vs. geprüftes Rezept und ausstehende reale Passprobe knapp. Beispielaufruf: `/war-thunder-tank-print BMPT-72`, `/war-thunder-tank-print Leopard 2A7V` oder `/war-thunder-tank-print M1A2 Abrams, Maßstab 1:72`.
