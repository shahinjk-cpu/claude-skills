# Meshaufbereitung und bewegliche Verbindungen

Diese Referenz beschreibt die im BMPT-72-Durchlauf geprüften Verfahren und deren Grenzen. Pfade beziehen sich auf die Pipeline-Wurzel `war_thunder_print`. Die Zahlen im Abschnitt „BMPT-72-Rezept“ sind fahrzeugspezifisch. Für jedes andere Fahrzeug misst `auto_recipe.py` Zuordnung und Ringwerte, und `prepare_generic.py` setzt dieselben Prinzipien generisch um (Turmboden, Drehfreistellung aus dem echten Turmprofil statt festem Z/R-Profil, Rohranhebung, Klebeplatten aus gemessener Kettenkontur); Details in [vehicle-recipe.md](vehicle-recipe.md). Ein Austausch der Fahrzeug-ID im BMPT-Rezept genügt weiterhin nicht.

## Unveränderliche Anforderungen

- Den Originalexport unverändert aufbewahren. Quelle, Rezept und verwendete Implementierungen über Hashes zuordnen. Veränderte Quelldaten erfordern eine erneute Rezeptprüfung.
- Alle Reparaturen und mechanischen Maße in **Millimetern des gedruckten Modells** ausführen. Baugruppenpositionen und Drehachsen bis zur Druckausrichtung in einem gemeinsamen Koordinatensystem halten.
- Ein endgültiges Druckteil muss nach erneutem Einlesen seiner tatsächlichen STL genau einen zusammenhängenden, geschlossenen Körper mit positivem Volumen bilden. Mehrere geschlossene, voneinander getrennte Schalen erfüllen diese Anforderung nicht.
- Sichtbare Änderungen, entfernte Fragmente, ergänzte Verbindungen und lokale Ersatzverfahren protokollieren. Ein geschlossenes Netz allein ist kein Nachweis für erhaltene Details oder Druckbarkeit.
- Erst die exportierten Teile prüfen und verpacken. Eine erfolgreiche Prüfung eines Zwischenstands darf spätere Vereinfachung, Ausrichtung oder Zahlenrundung nicht überdecken.
- Ein gemeinsames Bambu-Projekt enthält getrennte, benannte Druckobjekte und bei Bedarf mehrere Druckplatten. Die Teile nicht zu einem einzigen starren Netz verschmelzen, um „eine Datei“ zu erzeugen.

## 1. Quelle, Einheiten und Bauteilzuordnung

`inspect_scene.import_model(path)`, `inspect_scene.world_mesh(obj)` und `inspect_scene.inspect(path, output, render=False)` liefern Import, ausgewertete Weltgeometrie und Szeneninventar. Lokale Meshkoordinaten reichen nicht: Hierarchie, Spiegelung und Transformationen beeinflussen Geometrie und Drehpunkte.

Der aktuelle GLB-Export ist in Metern. Für diesen Export gilt `Druckmaß_mm = Weltmaß_m × 1000 / Maßstabsnenner`. Diese Einheit bei neuen Quellen zuerst durch Inventar, bekannte Fahrzeugabmessungen und Gesamtansicht bestätigen. Importskalierung und Rezeptskalierung nicht doppelt anwenden. STL trägt keine verbindliche Einheit; STL-Koordinaten und 3MF-Einheit ausdrücklich auf Millimeter festlegen.

Negative Transformationsdeterminanten können die Dreiecksorientierung umkehren. Nach der Welttransformation geometrische Normalen und Orientierung prüfen. Die vorhandene `prepare_vehicle.group_source(input_path, recipe, scale)`-Implementierung berechnet nach Zusammenführen der Quellpunkte die Normalen neu. Vorheriges negatives Volumen eines gespiegelten Imports ist kein Grund, Außenflächen zu entfernen.

Zuordnung aus Elternhierarchie, räumlicher Lage und getrennten Ansichten ableiten. Bewegte Untergruppen vor ihren übergeordneten Gruppen behandeln. Links/rechts anhand des bestätigten Fahrzeugkoordinatensystems bestimmen, nicht aus der aktuellen Kameraansicht. Knotenbezeichnungen allein reichen nicht: Beim BMPT stecken Granatwerferdetails in `bone_turret`; sie haben keine eigenständigen Objektknoten.

Das Rezept muss enthalten, welche Außengeometrie verwendet wird, welche Varianten oder Innengeometrie entfallen und wo Drehachsen liegen. Unbekannte Objekte bei einem neuen Fahrzeug nicht ungeprüft der Wanne zuschlagen. Die bestehende BMPT-Zuordnung mit ihrer Wannen-Auffanggruppe gilt nur für den geprüften Quell-Hash. Die aktuelle `build_parts(...)`-Funktion enthält zusätzlich BMPT-spezifische Konstruktionen; ein neues Rezept macht sie noch nicht fahrzeugunabhängig.

## 2. Konservative Komponentenreparatur

Öffentliche Schnittstelle: `mesh_repair.repair_mesh(trimesh_mesh, target_mm=0.8, label="mesh", sheet_first=None)` liefert `(mesh, audit)`. Eingabe und Ausgabe bleiben an ihrer Weltposition in Druckmillimetern. Das Ergebnis darf hier noch mehrere geschlossene Komponenten besitzen; die physische Verbindung entsteht erst bei der Baugruppenmontage.

1. Getrennte Flächenkomponenten bestimmen und deren Ausgangsgrenzen erfassen. Automatisches Lochschließen durch Hilfsfunktionen nicht unbemerkt auslösen: Die Reparatur verwendet explizite Teilnetze mit `repair=False`.
2. Bei tatsächlich unvollständigen Volumenkörpern Randöffnungen gezielt schließen. Ergebnis auf positives geschlossenes Volumen und unerwartete Deckflächen prüfen.
3. Offene Bleche verdicken, statt große Öffnungen als fehlende Deckel zu interpretieren. Erst danach lokal vereinigen.
4. Dünne tragende Komponenten anhand ihrer Gestalt und Wandstärkenstichprobe gezielt verstärken. Ein kleiner dekorativer Bolzen darf nicht automatisch auf die strukturelle Mindestwandstärke aufgeblasen werden. Bereits ausreichend starke, lange Rohre erhalten ihre Kontur.
5. Reparierte Außenmaße, Volumen, Komponenten und Detailansichten mit dem Ausgangsstand vergleichen. Restinseln sichtbar melden; noch nicht verbundene Kosmetik ist kein fertiges Druckteil.

Der Helper nutzt unter anderem `_bmesh_cap`, `_solidify`, `_sample_thickness`, `_manifold` und `_trimesh`. Dies sind interne Funktionen, keine stabile allgemeine Modellierungs-API. Wandstärkenstichproben können dünne Stellen übersehen; `minimum_thickness_certified` bleibt deshalb `False`.

### Solidify-Spitzen erkennen und begrenzen

Die Kombination aus scharfen Falten, gleichmäßiger Versatzberechnung und dem `NON_MANIFOLD`-Modus kann lange Gehrungsspitzen erzeugen. Eine spätere Boolesche Vereinigung kann diese Spitzen zu großen, scheinbar gültigen Außenkörpern machen. Den Fehler bereits **pro Quellkomponente** erkennen: maximale Ausdehnung nach außen gegenüber der ursprünglichen achsenparallelen Bounding Box messen.

Der vorhandene Helper verwendet als Implementierungsgrenze `target_mm + 0.10 mm`. Bei Überschreitung verwirft er den ersten Reparaturversuch und beginnt erneut mit der ursprünglichen Komponente: begrenzte feste Dicke, deaktivierter gleichmäßiger Versatz, zunächst `NON_MANIFOLD`, danach `EXTRUDE`. Scheitert auch das, abbrechen und die Komponente untersuchen. Diese Grenze berücksichtigt die hier kombinierten Reparaturschritte; sie ist keine zulässige Formänderung für jedes Fahrzeugdetail.

Im BMPT-Prototyp wuchs eine Turmkomponente durch den Fehler um ungefähr 48 mm nach außen. Der begrenzte Neuversuch blieb unter 0,4 mm. Deshalb Gesamtmaße und Komponentenmaße prüfen; eine bloße Volumenprüfung hätte den Defekt akzeptiert.

`mesh_repair.cache_compatible(audit, target_mm)` prüft die gespeicherten Komponentenbegrenzungen. Der Aufrufer muss zusätzlich Quelle, Zielstärke und ausdrücklich zugelassene Implementierungsversionen abgleichen. Alte Reparaturcaches nicht allein wegen vorhandener Dateien wiederverwenden.

Zwischenstände möglichst als indizierte Netze mit doppelt genauen Koordinaten speichern. Bei einem reinen Quantisierungsfehler kann `repair_mesh` einen Fehler mit `unquantized_mesh` und `audit` liefern. `prepare_vehicle.repair_source(...)` übernimmt diesen Zwischenstand nur, wenn er weiterhin ein gültiges geschlossenes Volumen bildet, und dokumentiert die bis nach der endgültigen Vereinigung verschobene STL-Quantisierung. Andere Reparaturfehler nicht auf diesem Weg übergehen.

### Ketten als dokumentierte lokale Ausnahme

Animierte Ketten können aus offenen Bändern bestehen. Ihre Randkonturen zu schließen kann den Raum für die Laufrollen mit großen Scheiben füllen. Für bestätigte Bandgeometrie `sheet_first=True` verwenden und zentrale Öffnung, Seitenkontur und Profil gegen die Quelle prüfen. Die automatische Namensprüfung `track_*_mesh` im bestehenden Helper ist eine BMPT-Konvention, keine allgemeine Erkennung aller Ketten.

Beim BMPT blieb die vereinigte Bandgeometrie nach Zahlenrundung problematisch. Nur diese beiden Kettenquellen erhielten `_local_voxel(..., pitch=0.05)` und anschließend eine Vereinfachung mit 0,01 mm Toleranz. Die innere Öffnung und der äußere Verlauf wurden geprüft. Diese Werte dokumentieren die geprüfte Ausnahme. Andere Ketten benötigen eigene Detail- und Öffnungsprüfungen; Wanne oder Gesamtfahrzeug nicht auf dieser Grundlage voxelisieren. Aus dem glatten Quellband lassen sich keine fehlenden Einzelglieder rekonstruieren.

## 3. Physische Verbindung und Montageflächen

`prepare_vehicle.connect_shells(mesh, label, radius=..., max_gap=...)` verbindet voneinander getrennte Schalen über protokollierte lokale Stege. Jeder Steg muss beide Körper mit echter Überdeckung schneiden. Nur tangential anliegende oder koplanar berührende Körper können numerisch getrennt bleiben.

Die geometrisch kürzeste Verbindung ist nicht automatisch unsichtbar oder konstruktiv passend. Stege in montierter und zerlegter Ansicht prüfen. Größere Abstände, freie Antennen oder sichtbare Gitter erfordern eine gezielte Konstruktion, ein eigenes Druckteil oder eine dokumentierte Detailänderung. Die im Helper vorhandenen Grenzen für Steglänge und winzige Fragmente nicht als allgemeine Freigabe zum Löschen sichtbarer Geometrie übernehmen.

Für Laufwerke eignet sich eine verdeckte innere Klebeplatte, sofern sie innerhalb der tatsächlichen Kettenkontur liegt. `running_gear_backplate(...)` setzt dies im BMPT um. Eine rechteckige Platte, die an den gerundeten Kettenenden sichtbar herausragt, ist trotz geschlossenem Netz falsch. Der dort verwendete Umriss einer Stützplatte ersetzt keine sichtbare Außengeometrie durch deren konvexe Hülle.

Spielmodelle enthalten oft absichtliche Durchdringungen. `fit_and_check(parts, audit, recipe)` schneidet beim geprüften BMPT Gegenstücke an den tatsächlichen Montagekörpern frei. Danach erneut Körperanzahl und Volumen prüfen: Ein Ausschnitt kann einen bisher verbundenen Bereich abtrennen. Entfernte versteckte Reststücke gehören mit Lage, Größe und Grund in den Audit.

Formschlüssige Klebeverbindungen brauchen eindeutige Orientierung, ausreichende Auflage und eigenes Klebespiel. Ein später drehbarer Turm darf nicht durch Kleben der Lagerflächen oder eine ungeprüfte Verbindung mit der Wanne fixiert werden.

## 4. Abnehmbarer, drehbarer Turm

Achse aus der überprüften Quellhierarchie ableiten. Lagerhöhe an der tatsächlichen Wannenoberseite messen; keine pauschale globale Z-Höhe annehmen. Zapfen, Aufnahme, tragende Auflage und Anschlag müssen im selben Bezugssystem liegen.

Radiales Spiel und diametrales Spiel unterscheiden: Bei einem Zapfen mit Durchmesser `d` und radialem Spiel `s` ist der Bohrungsdurchmesser `d + 2s`. Die Aufnahme braucht zusätzlich ausreichende Tiefe, damit der Turm auf seiner Auflage sitzt und nicht am Zapfenende aufsteht. Passproben mit denselben Druckparametern und demselben Anschlussprofil wie das Endmodell erzeugen.

Wandverstärkung kann den ursprünglichen Freiraum zwischen bewegter Plattform und festem Panzerkragen schließen. Zuerst Quell- und Reparaturquerschnitte um die Drehachse vergleichen. Sichtbaren Kragen, Dachkanten, Luken und Granatwerfer schützen. Eine abgestufte oder konische, rotationssymmetrische Freistellung an verdeckten Kontaktflächen ist dann gezielter als großflächiges Abschneiden.

`relieve_turret_ring(parts, audit, settings)` verarbeitet dafür ein fahrzeugspezifisches Z/R-Profil und schützt einen zentralen Lagerbereich. Zwischen dem unteren Rotationskörper und der unveränderten oberen Geometrie muss echte Boolesche Überdeckung bestehen. Beim BMPT verhinderte eine Überdeckung von 0,05 mm einen mikroskopischen Trennspalt. Höhe, Radien und Überdeckung für andere Fahrzeuge neu prüfen.

Der äußere Ringspalt muss auch bei exzentrisch sitzendem Turm erhalten bleiben. Mindestens berücksichtigen:

`erforderlicher Ringspalt >= maximales radiales Zapfenspiel + gewählte zusätzliche Reserve`

Die Reserve hängt von Druckprozess, Verformung und Geometrie ab. Eine Passprobenänderung des Zapfenspiels muss deshalb auch die Ringfreistellung und Kollisionsprüfung neu auslösen. `fit_and_check` setzt die BMPT-Freistellung entsprechend `minimum_eccentric_margin_mm` nach.

`check_rotation(parts, audit)` prüft feste Wanne samt Laufwerken gegen den gesamten bewegten Aufbau einschließlich Rohrgruppe und Raketenbehältern. Der aktuelle Test umfasst 24 Winkel in 15°-Schritten, jeweils zentriert sowie mit maximalem Zapfenspiel in vier Achsrichtungen. Das sind 120 diskrete Posen, **kein Beweis kontinuierlicher Kollisionsfreiheit**. Volumenschwellen dienen der numerischen Bewertung; gemessene Maximalüberschneidung immer berichten. Bei weiteren hervorstehenden Teilen Zwischenwinkel oder einen geeigneten Bewegungsraum prüfen.

## 5. STL-Präzision ohne Verlust sichtbarer Geometrie

Ein geschlossenes Netz mit doppelt genauen Koordinaten kann nach STL-Export offen werden. Distinkte topologische Punkte liegen nach Booleschen Operationen manchmal näher beieinander, als `float32` darstellen kann. Beim Einlesen der STL werden sie zusammengeführt; das Entfernen der dadurch entstehenden Dreiecke erzeugt Löcher. ASCII-STL beseitigte dieses Problem im BMPT ebenfalls nicht, weil auch dort unindizierte Punkte beim Einlesen verschweißt werden.

`stl_precision.prepare_stl_mesh(mesh, max_displacement_mm=0.001)` wird **nach der Druckausrichtung, vor dem Export und vor destruktivem Zusammenführen oder Löschen kollabierter Flächen** aufgerufen. Es liefert `(mesh, audit)`. Es verlangt bereits einen geschlossenen Einzelkörper und repariert keine beliebige defekte Spielgeometrie.

Der Helper verschiebt ausschließlich kollabierende Punkte oder Endpunkte kollabierender Dreiecke deterministisch, begrenzt und innerhalb der quantisierten Ausgangs-Bounding-Box. Er erhält Dreiecksindizes und Orientierung. Alle Ergebniswerte sind als `float32` darstellbar. Ein frischer binärer STL-Durchlauf muss alle Flächen und einen geschlossenen Einzelkörper erhalten.

Bei unveränderten Dreiecksindizes begrenzt die maximale korrespondierende Punktverschiebung auch die beidseitige Oberflächenabweichung: Jeder Punkt eines Dreiecks besitzt denselben baryzentrischen Gegenpunkt im Ergebnis. Dies ist stärker als eine zufällige Oberflächenstichprobe. Es beweist jedoch nicht, dass sämtliche lokalen Selbstüberschneidungen ausgeschlossen sind; die native Slicer-Prüfung bleibt erforderlich.

Im geprüften BMPT-Durchlauf betrug die größte Verschiebung rund 0,000083 mm, bei unveränderten Flächenzahlen. Die größte absolute Volumenänderung lag bei rund 0,000607 mm³. Die konfigurierte Grenze von 0,001 mm ist eine Exportgrenze dieses Verfahrens, keine allgemeine Fertigungstoleranz.

Ein globaler MeshFix-Versuch erzeugte zwar einen geschlossenen Körper, veränderte die Wanne aber um rund 811 mm³ und die Oberfläche lokal um Millimeter. Er wurde verworfen. Generische Reparaturprogramme nur mit nachgewiesenen Geometriegrenzen verwenden; „watertight“ allein rechtfertigt keine Übernahme.

## 6. Abnahme an den tatsächlichen Ausgabedateien

`validate_and_export(parts, audit, source_report, recipe, out)` vereinfacht vorsichtig und prüft jeden Kandidaten erneut auf einen geschlossenen Einzelkörper. Eine gröbere Vereinfachung, die Schalen trennt, wird verworfen. Keine feste Dreieckszahl als alleinigen Qualitätsmaßstab verwenden.

Nach dem Schreiben jede STL frisch einlesen, Körperanzahl, Orientierung, Volumen und Abmessungen prüfen. Die gespeicherte `assembly_to_print_transform` invertieren und damit **diese eingelesenen Teile** wieder montieren. Auf diesen Geometrien `check_rotation` wiederholen. Der Bericht kennzeichnet dies mit `geometry_source = "final_exported_stl_readback"`; eine Prüfung vor Vereinfachung oder Quantisierung reicht nicht.

Bearbeitbare Blender-Datei, Montageansicht und Bambu-Projekt aus demselben geprüften Stand erstellen. Quellen-, Rezept-, Code- und STL-Hashes verhindern, dass alte Prüfberichte neue Geometrien freigeben. Zusätzlich native Bambu-Schichten und tatsächliche Belegung einschließlich Stützen und Brim prüfen. Ein passendes STL-Rechteck genügt nicht für den Bauraumnachweis.

Passende Regressionen liegen in `tools/test_mesh_repair.py`, `tools/test_prepare_vehicle.py` und `tools/test_stl_precision.py`. Sie prüfen unter anderem scharfe Solidify-Falten, Bandöffnungen, geschützte Lagerflächen, Verbindung über die obere Freistellungsebene und Topologieverlust durch STL-Rundung. Quellassetabhängige Tests ersetzen keine Prüfung eines neuen Fahrzeugs.

## BMPT-72-Rezept: geprüfter Ausgangspunkt, keine universellen Vorgaben

| Eigenschaft | BMPT-72 bei 1:72 |
|---|---|
| Rezept | `recipes/ussr_bmpt_72.json`; nur Maßstab 1:72 freigegeben |
| Teile | Wanne, Laufwerk links/rechts, Turm, Rohrgruppe, Raketenbehälter links/rechts |
| Druckprofil | A1 mini, 0,2-mm-Düse, PLA, zunächst 0,08-mm-Schichten |
| Strukturelles Wandstärkenziel | 0,8 mm; nicht global zertifiziert |
| Turmzapfen | Wanne als Besitzer; Ø 5 mm, Eingriff 3 mm, Spitzenfase 0,25 mm |
| Aufnahme | Tiefe 3,4 mm; radiales Startspiel 0,20 mm → Ø 5,40 mm |
| Passproben | 0,15 / 0,20 / 0,25 mm Spiel je Seite |
| Klebeverbindungen | Formschlüssige Schlüssel; 0,15 mm Spiel je Seite |
| Turmprofil `(Z, Radius)` | `(20,16.6)`, `(20.5,16.6)`, `(21,17.45)`, `(26.3,17.45)` mm im Modellbezugssystem |
| Ringspalt | 0,35 mm; mindestens gewähltes Zapfenspiel + 0,15 mm Reserve |
| Geschützter Lagerkern | Radius 5,1 mm |
| Druckraum | 180 × 180 × 180 mm; Zielbelegung einschließlich Druckhilfen höchstens 170 × 170 mm |

Koordinaten der Klebeschlüssel und Ringfreistellung gelten nur für die zugehörige BMPT-Quelle. Maßstabsänderungen verändern Fahrzeuggeometrie, während Düsengrenzen, Spiel und brauchbare Anschlussstärken nicht proportional mitskalieren. Daher ist ein anderer Maßstab ein erneut zu prüfendes Rezept.

## Physische Grenzen und ehrliche Statusangaben

`geometry_passed` beschreibt digitale Geometrieprüfung. `physical_calibration_passed` und `physical_print_verified` bleiben bis zum tatsächlichen Versuch falsch. Weder ein sauberes STL noch ein fehlerfrei erzeugtes G-Code-Projekt bestätigt Druckfestigkeit, Montage oder leichtgängige Drehung.

Zuerst Passprobe und Detailstück drucken. Danach gewähltes Spiel ins Rezept übernehmen, einschließlich Ringreserve neu prüfen und Endteile neu erzeugen. Antennen, Gitter, freie Rohre und kleine Überhänge einzeln beurteilen. Lokale Freistellungen können dünnere Wände hinterlassen; beim BMPT ist die globale 0,8-mm-Mindeststärke deshalb ausdrücklich nicht zugesichert. Erhaltene Reliefdetails können kleiner als das strukturelle Ziel sein und im realen PLA-Druck verloren gehen.
