# Fahrzeugrezepte: automatisch erzeugen, prüfen, bauen

## Zwei Builder, eine Pipeline

| Rezept | Builder | Gültigkeit |
|---|---|---|
| `schema: 2` (Standard für jedes Fahrzeug) | `tools/prepare_generic.py` | Jedes Bodenfahrzeug mit WT-Hierarchie (`bone_turret`, `bone_gun`, `track_l/r`, `wheel_*`, `suspension_*`); Werte werden aus dem Modell gemessen |
| ohne `schema` (`recipes/ussr_bmpt_72.json`) | `tools/prepare_vehicle.py` | Nur der handgeprüfte BMPT-72-Stand 1:72 mit getrennten Raketenbehältern und Klebeschlüsseln |

`pipeline.py` wählt den Builder über `builder_for(recipe)` und hasht pro Builder die passenden Dateien (`GENERIC_IMPLEMENTATION` bzw. `GEOMETRY_IMPLEMENTATION`). Ein Bericht des einen Builders gibt keine Geometrie des anderen frei.

## Automatisches Rezept (`--stage recipe`)

`tools/auto_recipe.py --input raw/<id>/<model>.glb --output recipes/<id>.json --scale <n>` liest das GLB in Blender und schreibt ein vollständiges, prüfbares Rezept:

- **`objects`**: jedes Mesh-Objekt → genau ein Teil. Regeln: unter `bone_gun` (innerhalb des Hauptturms) → `gun_group`; unter Hauptturm (`bone_turret`, sonst größter oberster `bone_turret_N`) → `turret`; Name/Vorfahre `track|wheel|suspension|bone_wheel|…_l_…` bzw. `_r_` → `running_gear_left/right`; Rest → `hull`. Verschachtelte Türme (z. B. Waffenstation `bone_turret_01` im Turm) bleiben im Hauptturm. Weitere oberste Türme bleiben fest auf der Wanne (Hinweis in `notes`).
- **`excluded_objects`** mit Grund: Schadens-/Zerstörungsstand, Effekt-Emitter, Kollisions-/Röntgenhelfer, Peitschenantennen/Drähte (> 8 mm lang, < 0,6 mm dick beim Maßstab), Splitter < 0,3 mm. Sonst wird nichts entfernt.
- **Radfahrzeuge** (kein Kettenband `track_l/r`): Räder bleiben an der Wanne, weil eine Klebeplatte zwischen Rädern sichtbar wäre.
- **`sheet_objects`**: Kettenbänder, die als offene Bänder verdickt statt zugedeckelt werden (sonst füllen Deckel die Laufrollenöffnung).
- **`turret`** (`mode: rotating`): Achse aus dem `bone_turret`-Ursprung; Deckhöhe per Raycasts auf die Wanne in Ringen um die Achse (erster stabiler Bereich ±6 mm um den Ursprung → `ring_hole_radius_mm`, `deck_z_mm`); `trim_z_mm = deck + 0,5`; Lagerscheibe `bearing_radius_mm = min(max(8, Lochradius + 1,5), Turmreichweite_P15 − 1)`; Wannendeckel `cap_radius_mm ≥ Lochradius + 1,5`; Nabe bis Turmunterseite (Raycast nach oben). Zapfen/Spiel sind Druckmaße (Ø 5 mm, 0,20 mm je Seite, Eingriff 3 mm, Bohrung 3,4 mm) und skalieren nicht.
- **`parts`** mit Druckorientierung: `as_is`, `left_inner_down`, `right_inner_down`, `muzzle_up`, `upside_down`; `merge_into`. Regel für `gun_group`: mit Turmkörper → `turret` (nach der Turmfreistellung); **ohne Turmkörper** (Kasematte, Sturmgeschütz, Sturmtiger, oder `bone_turret` trägt nur `bone_gun`) → `hull`, `turret.mode: none`, Hinweis in `notes`. Ein `gun_group` ohne `merge_into` und ohne geprüften Klebeschlüssel lehnt `validate_recipe` ab („loose gun“); ein lose gebliebenes Geschütz zerfiel sonst in mehrere Schalen und brach beim Verbinden ab. Ältere Auto-Rezepte ohne diese Regel mit `--regenerate-recipe` neu erzeugen oder `"merge_into": "hull"` von Hand setzen.
- **`attachment`**: Stege, die abgetrennte Detailschalen eines Teils an den Hauptkörper binden (siehe unten).
- **`review`**: `auto_generated: true`, `human_reviewed: false`.

### Stege zwischen Schalen (`attachment`)

Nach Freistellung und Zusammenführung muss jedes Teil **ein** Körper sein. `connect_parts` verbindet jede abgetrennte Schale über den kürzesten Eckpunktabstand mit einem zylindrischen Steg. Alle Werte stehen im Rezept; fehlende Schlüssel nehmen die Standardwerte:

| Schlüssel | Standard | Wirkung |
|---|---|---|
| `bridge_diameter_mm` | 0,8 | Stegdurchmesser im ersten Versuch (≥ 0,6) |
| `bridge_retry_step_mm` | 0,2 | Zuwachs des Durchmessers je Wiederholung |
| `bridge_max_retries` | 2 | Wiederholungen, wenn die Vereinigung noch mehrere Schalen ergibt (Versuch 0: 0,8 → 1: 1,0 → 2: 1,2 mm) |
| `max_bridge_gap_mm` | 5,0 | Größere Lücke → Abbruch mit Nennung des Schlüssels; Objekt anders zuordnen, ausschließen oder Klebeschlüssel |
| `min_shell_volume_mm3` | 0,002 | Schalen darunter werden **nur nach Volumen** verworfen, unabhängig von ihrer Größe. Flache Nullvolumen-Reste (z. B. 4 koplanare Flächen) sind oft mehrere mm groß, Manifold lehnt sie ab; früher führte die zusätzliche Größengrenze (0,3/0,8 mm) zum Absturz |
| `review_bridge_gap_mm` | 1,0 | Stege über längere Lücken → Review-Hinweis (sichtbare Strebe) |
| `review_thin_bridge_diameter_mm` | 1,0 | Lange Stege (über `review_bridge_gap_mm`) dünner als dieser Wert → Review-Hinweis „bruchgefährdet“; kurze dünne Verbindungen sind normal |
| `review_max_shells` | 100 | Mehr verbundene Einzelschalen → Review-Hinweis (schwebende Details). Detailreiche Modelle haben normal 30–90 Schalen (Leopard 2A7V: Wanne 86, Turm 32) |

Jede Wiederholung steht in `construction_audit.json → attachments[].attempts` (Versuch, Schalen vorher, Durchmesser) und im Stufenprotokoll als `RECONNECT <teil>: attempt n/N, … bridge diameter … mm`. Jeder Steg trägt `gap_mm`, `diameter_mm` und `attempt`; gemischte Durchmesser nach Wiederholungen erzeugen einen Review-Hinweis mit allen Werten. Für dauerhaft dickere Stege `bridge_diameter_mm` erhöhen (z. B. 1,2) statt auf Wiederholungen zu setzen. Verworfene Reste stehen in `attachments[].removed_slivers` und `removed_fragments`.

Kalibrierung der Heuristik am handgeprüften BMPT: automatisch `trim_z 20,05 mm` gegenüber geprüften `20,0 mm`. Ein automatisch erzeugtes Rezept ersetzt trotzdem **keine** Sichtprüfung.

## Pflichtprüfung nach dem Rezept

1. `source_inspection/source_preview.png` (`--stage inspect --render-source`) und `source_groups.json` ansehen: Stimmen Teile, Turmzugehörigkeit, links/rechts?
2. `excluded_objects` lesen. Sichtbare, druckbare Teile nicht ausschließen; ggf. Objekt in `objects` eintragen.
3. Nach `prepare` (Status: `combine_status` lautet `not_run_in_this_run`, alte `.gcode.3mf` gehört dann zur vorigen Geometrie, `combined_report.json` ist `stale` bis `package` + `combine`): `assembly_exploded.png`, `construction_audit.json` (`sweep_relief.removed_fraction`, `rotation_check.blocked_angles_degrees`, `fallback_repairs`, `removed_fragments`, `attachments[].bridges`/`attempts`) und `print_report.json:review_flags` prüfen. Leere `review_flags` heißen nicht „keine Stege“: lange oder dünne Stege und viele Schalen erzeugen eigene Hinweise, die Rohdaten stehen in `attachments`.
4. Wird etwas geändert: Rezept von Hand anpassen, `review.human_reviewed: true` setzen. Ein geprüftes Rezept wird von der Pipeline nie überschrieben; passt es nicht mehr zu Quelle/Maßstab, stoppt sie.

Bei Mehrdeutigkeit, die Geometrie und Ansichten nicht klären, den Nutzer fragen und die Entscheidung im Rezept speichern.

## Was der generische Builder macht

1. Zuordnung vollständig prüfen: nicht zugeordnete oder fehlende Objekte → Abbruch. Quell-Hash muss passen.
2. Komponentenweise konservative Reparatur (`mesh_repair.repair_mesh`). Scheitert eine Komponente: pro Komponente erneut; kleine Details ≤ 6 mm → konvexe Hülle (flache Bleche mit Wandziel), größere → begrenzte Verdickung + lokales 0,05-mm-Voxel. Jeder Ersatz steht in `repair_audits.json` und `review_flags`.
3. Laufwerk: verdeckte 2-mm-Klebeplatte innerhalb der gemessenen Kettenkontur (Ränder 3,5 % Länge, 17,5 %/16 % Höhe, 0,6 mm Einzug).
4. Turm: Korb unter Ringebene abschneiden; geschlossener Turmboden aus dem Turmumriss, Lagerscheibe, Nabe, Zapfenbohrung; Wanne: Deckel, Lagerpad, Zapfen mit Fase.
5. **Rohranhebung** (`gun.auto_elevate`, Drehpunkt = `bone_gun`-Ursprung): Spielmodelle speichern das Rohr oft leicht gesenkt, es taucht dann in Bugplatte/Heckdeck. Das Rohr wird in 1°-Schritten (max. `max_elevation_deg`, Standard 12°) angehoben, bis alle 24 Turmwinkel frei sind; sonst kleinster Winkel mit freier Grundstellung. Teile unter der Ringebene werden danach erneut gekappt. Gewählter Winkel → `gun_elevation` und Review-Hinweis.
6. Montagefreistellungen (`assembly_reliefs`), danach **Drehfreistellung**: maximaler Turmradius je 0,25-mm-Höhenband (exakt aus Ecken und Kantenschnitten) + 0,35 mm radial, 0,3 mm vertikal, als Rotationskörper aus allen festen Teilen entfernt; Kern r 5,1 mm geschützt. > 3 % entferntes Volumen eines Teils → Review-Hinweis, > 15 % → Abbruch. Das Rohr ist ausgenommen; stößt es beim Drehen an (z. B. über dem Heck), meldet `rotation_check` die blockierten Winkel, statt Wannendetails abzufräsen.
7. Rohr mit Turm (ohne Turmkörper: mit Wanne) verschmelzen, Nullvolumen-Fragmente nach Volumen entfernen (protokolliert), Schalen über Stege nach `attachment` verbinden (> `max_bridge_gap_mm` → Abbruch), automatische Steg-Review-Hinweise.
8. Export, STL-Rücklesen, Größenprüfung (Teil + 16 mm Reserve ≤ 170 mm), Rotationsprüfung 24 Winkel × 5 Exzenterlagen an den **rückgelesenen** STL.

Klebeschlüssel (`glue_keys`) mit expliziten Koordinaten funktionieren im generischen Builder wie beim BMPT, etwa für ein getrenntes Rohr (`gun_group` ohne `merge_into`, Orientierung `muzzle_up`, Schlüssel `turret`→`gun_group`). Ohne geprüfte Schlüsselposition bleibt das Rohr am Turm.

## Grenzen

- Ein Teil größer als 154 mm (170 − Reserve) beim gewählten Maßstab stoppt den Export. Maßstab nicht stillschweigend ändern; Nutzer fragen (größerer Nenner) oder Teilung planen.
- Keine automatische Teilung von Wannen, keine beweglichen Ketten/Räder, kein automatisch getrenntes Rohr.
- Physische Passung bleibt bis zur Passprobe unbestätigt; Kalibrierstatus nur bei gleicher Düse, Material und Einstellung übertragen.

## Änderungsdisziplin

Vor einem neuen Geometrielauf werden Freigaben invalidiert (`invalidate_prepared_outputs`). Reparaturcache nur bei gleicher Quellgeometrie, Zielstärke, Bandmodus und `mesh_repair.py`-Hash. Nach Rezept-, Orientierungs- oder Profiländerung genau `--stage prepare` → `--stage package` → `--stage combine` nacheinander wiederholen, jede erst nach `completed` der vorigen (`tools/run_status.py`). `--stage all` nur für den ersten Komplettlauf oder nach Spielupdate (neuer Export). `calibration` entfällt bei Fahrzeugen ohne Drehturm. Keine Toleranzen nachträglich aufweiten, damit ein Fehler verschwindet.
