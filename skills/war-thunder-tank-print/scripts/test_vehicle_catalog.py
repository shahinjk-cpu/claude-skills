"""Behavioral catalog-resolution tests; no game, native libraries or extraction."""
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest

import vehicle_catalog as catalog


@contextlib.contextmanager
def local_temporary_directory():
    """Keep test writes/cleanup in this known workspace, not sandbox TEMP."""
    parent = Path.cwd().resolve()
    temporary = tempfile.TemporaryDirectory(prefix="catalog_test_", dir=parent)
    root = Path(temporary.name).resolve()
    if root.parent != parent:
        raise RuntimeError("Test temporary path escaped its intended directory")
    try:
        yield root
    finally:
        temporary.cleanup()


FIXTURE = [
    {"id":"ussr_bmpt_72", "name":"BMPT-72", "nation":"USSR", "type":"Tanks", "model_id":"bmpt_72"},
    {"id":"ussr_pantsyr_s1", "name":"Pantsir-S1", "nation":"USSR", "type":"Tanks", "model_id":"pantsyr_s1"},
    {"id":"germ_leopard_2a4", "name":"Leopard 2A4", "nation":"Germany", "type":"Tanks", "model_id":"leo2a4", "premium":False},
    {"id":"sw_leopard_2a4", "name":"Leopard 2A4", "nation":"Sweden", "type":"Tanks", "model_id":"leo2a4"},
    {"id":"germ_leopard_2a6", "name":"Leopard 2A6", "nation":"Germany", "type":"Tanks", "model_id":"leo2a6"},
    {"id":"germ_tiger_h1", "name":"Tiger H1", "nation":"Germany", "type":"Tanks", "model_id":"tiger_h1"},
    {"id":"germ_tiger_e", "name":"Tiger E", "nation":"Germany", "type":"Tanks", "model_id":"tiger_e"},
    {"id":"jp_heavy_tank_no6", "name":"Tiger E", "nation":"Japan", "type":"Tanks", "model_id":"tiger_e", "premium":True},
    {"id":"germ_tiger_animal_version", "name":"␠Tiger", "nation":"Germany", "type":"Tanks", "model_id":"tiger_animal"},
    {"id":"germ_sturmmorser_sturmtiger", "name":"38 cm Sturmmörser", "nation":"Germany", "type":"Tanks", "model_id":"sturmmorser_sturmtiger"},
    {"id":"ussr_is_2_1943", "name":"IS-2", "nation":"USSR", "type":"Tanks", "model_id":"is_2"},
    {"id":"cn_is_2_1943", "name":"␗IS-2", "nation":"China", "type":"Tanks", "model_id":"is_2"},
    {"id":"ussr_is_2_1944", "name":"IS-2 (1944)", "nation":"USSR", "type":"Tanks", "model_id":"is_2_1944"},
    {"id":"us_m24_chaffee", "name":"M24", "nation":"USA", "type":"Tanks", "model_id":"m24_chaffee"},
    {"id":"it_m24_chaffee", "name":"▄M24", "nation":"Italy", "type":"Tanks", "model_id":"m24_chaffee_it"},
    {"id":"us_t28", "name":"T28", "nation":"USA", "type":"Tanks", "model_id":"t28"},
    {"id":"ussr_t_28", "name":"T-28", "nation":"USSR", "type":"Tanks", "model_id":"t_28"},
    {"id":"ariete", "name":"Ariete", "nation":"Italy", "type":"Planes", "model_id":"ariete"},
    {"id":"it_c1_ariete", "name":"Ariete", "nation":"Italy", "type":"Tanks", "model_id":"c1_ariete"},
]


class ResolutionTests(unittest.TestCase):
    def setUp(self):
        self.vehicles = catalog.normalize_catalog(FIXTURE)

    def test_exact_id_preserves_variant_and_unknown_premium(self):
        result = catalog.resolve("USSR_BMPT_72", self.vehicles)
        self.assertEqual(result["status"], "resolved")
        self.assertEqual(result["exact_id"], "ussr_bmpt_72")
        row = result["candidates"][0]
        self.assertEqual((row["nation"], row["type"], row["model_id"]), ("USSR", "Tanks", "bmpt_72"))
        self.assertIsNone(row["premium"])
        self.assertEqual(row["premium_status"], "unverified")

    def test_known_aliases_resolve_only_existing_catalog_ids(self):
        for query, expected in [("BMPT72", "ussr_bmpt_72"), ("Terminator 2", "ussr_bmpt_72"),
                                ("Pantsir S1", "ussr_pantsyr_s1")]:
            with self.subTest(query=query):
                self.assertEqual(catalog.resolve(query, self.vehicles)["exact_id"], expected)
                without = [v for v in self.vehicles if v["id"] != expected]
                self.assertIsNone(catalog.resolve(query, without)["exact_id"])

    def test_family_queries_cannot_choose_a_variant(self):
        for query in ("Leopard2", "Tiger"):
            with self.subTest(query=query):
                result = catalog.resolve(query, self.vehicles)
                self.assertEqual(result["status"], "ambiguous")
                self.assertIsNone(result["exact_id"])
                self.assertTrue(result["requires_selection"])
                self.assertGreaterEqual(result["candidate_count"], 2)

    def test_same_model_copies_resolve_with_equivalents(self):
        for query, expected, twin in [("Leopard 2A4", "germ_leopard_2a4", "sw_leopard_2a4"),
                                      ("Tiger E", "germ_tiger_e", "jp_heavy_tank_no6"),
                                      ("IS-2", "ussr_is_2_1943", "cn_is_2_1943")]:
            with self.subTest(query=query):
                result = catalog.resolve(query, self.vehicles)
                self.assertEqual(result["status"], "resolved")
                self.assertEqual(result["exact_id"], expected)
                self.assertEqual(result["candidates"][0]["equivalent_ids"], [twin])

    def test_exact_name_with_longer_family_is_not_a_false_alarm(self):
        result = catalog.resolve("IS-2", self.vehicles)
        self.assertEqual(result["status"], "resolved")
        self.assertIn("ussr_is_2_1944", {v["id"] for v in result["variants"]})
        self.assertFalse(result["requires_selection"])

    def test_plain_name_beats_decorated_foreign_copy_of_other_model(self):
        result = catalog.resolve("M24", self.vehicles)
        self.assertEqual((result["status"], result["exact_id"]), ("resolved", "us_m24_chaffee"))
        self.assertIn("it_m24_chaffee", {v["id"] for v in result["variants"]})
        decorated = catalog.resolve("▄M24", self.vehicles)
        self.assertEqual(decorated["exact_id"], "it_m24_chaffee")

    def test_two_distinct_plain_ground_models_stay_ambiguous(self):
        result = catalog.resolve("T28", self.vehicles)
        self.assertEqual(result["status"], "ambiguous")
        self.assertEqual({v["id"] for v in result["candidates"]}, {"us_t28", "ussr_t_28"})

    def test_non_ground_rows_are_not_plausible(self):
        result = catalog.resolve("Ariete", self.vehicles)
        self.assertEqual((result["status"], result["exact_id"]), ("resolved", "it_c1_ariete"))
        self.assertEqual(result["ignored_non_ground"], ["ariete"])

    def test_in_game_alias_sturmtiger(self):
        for query in ("Sturmtiger", "Sturmmörser", "38 cm Sturmmörser"):
            with self.subTest(query=query):
                self.assertEqual(catalog.resolve(query, self.vehicles)["exact_id"], "germ_sturmmorser_sturmtiger")

    def test_exact_short_name_does_not_choose_event_variant_over_family(self):
        result = catalog.resolve("Tiger", self.vehicles)
        self.assertEqual(result["status"], "ambiguous")
        self.assertEqual(result["match_kind"], "exact_name_with_variants")
        self.assertIsNone(result["exact_id"])
        self.assertIn("germ_tiger_h1", {v["id"] for v in result["candidates"]})
        explicit = catalog.resolve("germ_tiger_animal_version", self.vehicles)
        self.assertEqual(explicit["exact_id"], "germ_tiger_animal_version")

    def test_single_fuzzy_suggestion_requires_confirmation(self):
        # Explicit isolated record keeps this a genuine one-candidate fuzzy case.
        result = catalog.resolve("BMPT73", catalog.normalize_catalog(FIXTURE[:1]))
        self.assertEqual(result["status"], "needs_confirmation")
        self.assertIsNone(result["exact_id"])

    def test_no_match_and_explicit_premium_flags(self):
        result = catalog.resolve("xqzv nonexistent unicorn", self.vehicles)
        self.assertEqual((result["status"], result["candidates"]), ("no_match", []))
        rows = {v["id"]:v for v in self.vehicles}
        self.assertIs(rows["germ_leopard_2a4"]["premium"], False)
        self.assertIs(rows["jp_heavy_tank_no6"]["premium"], True)

    def test_conflicting_duplicate_ids_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "Conflicting"):
            catalog.normalize_catalog([FIXTURE[0], {**FIXTURE[0], "name":"Different vehicle"}])


class CliTests(unittest.TestCase):
    def test_localized_name_survives_legacy_windows_stdout(self):
        with local_temporary_directory() as root:
            fixture = root / "catalog.json"
            fixture.write_text(json.dumps([{"id": "test_tiger", "name": "\u2420Tiger"}]), encoding="utf-8")
            buffer = io.BytesIO()
            capture = io.TextIOWrapper(buffer, encoding="cp1252", write_through=True)
            with contextlib.redirect_stdout(capture):
                code = catalog.main(["--project", str(root), "--query", "Tiger", "--catalog-json", str(fixture)])
            result = json.loads(buffer.getvalue().decode("cp1252"))
            capture.close()
            self.assertEqual(code, 0)
            self.assertEqual(result["candidates"][0]["name"], "\u2420Tiger")

    def test_fixture_cli_returns_json_without_native_runtime_or_game(self):
        with local_temporary_directory() as folder:
            root = Path(folder)
            fixture = root / "catalog.json"
            fixture.write_text(json.dumps({"vehicles": FIXTURE}), encoding="utf-8")
            capture = io.StringIO()
            with contextlib.redirect_stdout(capture):
                code = catalog.main(["--project", str(root / "not-created"), "--query", "Terminator2",
                                     "--catalog-json", str(fixture)])
            result = json.loads(capture.getvalue())
            self.assertEqual(code, 0)
            self.assertEqual(result["exact_id"], "ussr_bmpt_72")
            self.assertFalse((root / "not-created").exists())

    def test_unsafe_query_rejected_before_catalog_or_cache_access(self):
        with local_temporary_directory() as folder:
            project = Path(folder) / "must-not-exist"
            for query in ("../../missing_vehicle", "ussr_bmpt_72; whoami", "$(Get-Content secret)", "C:\\secret"):
                with self.subTest(query=query), contextlib.redirect_stdout(io.StringIO()) as capture:
                    code = catalog.main(["--project", str(project), "--query", query,
                                         "--catalog-json", str(project / "absent.json")])
                result = json.loads(capture.getvalue())
                self.assertEqual(code, 2)
                self.assertEqual(result["status"], "invalid_query")
                self.assertIsNone(result["exact_id"])
            self.assertFalse(project.exists())

    def test_generated_cache_cannot_escape_project(self):
        with local_temporary_directory() as folder:
            root = Path(folder).resolve()
            with self.assertRaisesRegex(ValueError, "escapes"):
                catalog.project_child(root, root / ".." / "outside")


if __name__ == "__main__":
    unittest.main()
