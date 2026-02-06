"""Tests for phone routing: normalization, routing, DTMF, birthday, directory integrity.

Uses importlib to load config/core modules without triggering pydantic
dependencies from settings.py, so tests run in any environment.
"""

import importlib
import re
import sys
import types
import unittest
from pathlib import Path


def _load_modules():
    """Load phone_directory and phone_router without pydantic dependency.

    Stubs out the config and core packages so only the two target modules
    are loaded, avoiding any import of settings.py or other heavy deps.
    """
    app_root = Path(__file__).resolve().parent.parent
    if str(app_root) not in sys.path:
        sys.path.insert(0, str(app_root))

    # Stub parent packages so importlib finds submodules
    for pkg in ("config", "core"):
        if pkg not in sys.modules:
            mod = types.ModuleType(pkg)
            mod.__path__ = [str(app_root / pkg)]
            sys.modules[pkg] = mod

    directory = importlib.import_module("config.phone_directory")
    router = importlib.import_module("core.phone_router")
    return directory, router


directory_mod, router_mod = _load_modules()

PHONE_DIRECTORY = directory_mod.PHONE_DIRECTORY
FEATURE_TO_NUMBER = directory_mod.FEATURE_TO_NUMBER
BIRTHDAY_PATTERN = directory_mod.BIRTHDAY_PATTERN
BIRTHDAY_GREETING = directory_mod.BIRTHDAY_GREETING
DTMF_SHORTCUTS = directory_mod.DTMF_SHORTCUTS
DEFAULT_GREETING_NOT_IN_SERVICE = directory_mod.DEFAULT_GREETING_NOT_IN_SERVICE

PhoneRouter = router_mod.PhoneRouter
RouteResult = router_mod.RouteResult


class TestNormalize(unittest.TestCase):
    """PhoneRouter.normalize() edge cases."""

    def setUp(self):
        self.normalize = PhoneRouter.normalize

    def test_seven_digits(self):
        self.assertEqual(self.normalize("5555653"), "555-5653")

    def test_seven_digits_with_dash(self):
        self.assertEqual(self.normalize("555-5653"), "555-5653")

    def test_ten_digits_strips_area_code(self):
        self.assertEqual(self.normalize("2125555653"), "555-5653")

    def test_eleven_digits_strips_country_and_area(self):
        self.assertEqual(self.normalize("12125555653"), "555-5653")

    def test_non_standard_short(self):
        result = self.normalize("123")
        self.assertEqual(result, "123")

    def test_non_standard_long(self):
        result = self.normalize("123456789012")
        self.assertEqual(result, "123456789012")

    def test_strips_special_chars(self):
        self.assertEqual(self.normalize("(555) 565-3"), "555-5653")

    def test_eleven_digits_not_starting_with_1(self):
        result = self.normalize("22125555653")
        self.assertEqual(result, "22125555653")


class TestRoute(unittest.TestCase):
    """PhoneRouter.route() for direct-dial numbers."""

    def setUp(self):
        self.router = PhoneRouter()

    def test_known_feature(self):
        result = self.router.route("5555653")
        self.assertEqual(result.feature, "jokes")
        self.assertEqual(result.name, "Dial-A-Joke")
        self.assertEqual(result.entry_type, "feature")
        self.assertTrue(result.is_direct_dial)

    def test_persona(self):
        result = self.router.route("5557243")
        self.assertEqual(result.feature, "persona_sage")
        self.assertEqual(result.persona_key, "sage")
        self.assertEqual(result.entry_type, "persona")
        self.assertTrue(result.is_direct_dial)

    def test_easter_egg(self):
        result = self.router.route("8675309")
        self.assertEqual(result.feature, "easter_jenny")
        self.assertEqual(result.entry_type, "easter_egg")

    def test_birthday_valid(self):
        result = self.router.route("5550704")
        self.assertEqual(result.feature, "easter_birthday")
        self.assertEqual(result.entry_type, "easter_egg")
        self.assertTrue(result.is_direct_dial)

    def test_birthday_december_31(self):
        result = self.router.route("5551231")
        self.assertEqual(result.feature, "easter_birthday")

    def test_birthday_january_01(self):
        result = self.router.route("5550101")
        self.assertEqual(result.feature, "easter_birthday")

    def test_unknown_number(self):
        result = self.router.route("5559999")
        self.assertEqual(result.feature, "invalid")
        self.assertEqual(result.entry_type, "invalid")
        self.assertFalse(result.is_direct_dial)

    def test_ten_digit_area_code(self):
        result = self.router.route("2125555653")
        self.assertEqual(result.feature, "jokes")

    def test_eleven_digit_country_code(self):
        result = self.router.route("12125555653")
        self.assertEqual(result.feature, "jokes")

    def test_historic_number_popcorn(self):
        result = self.router.route("7672676")
        self.assertEqual(result.feature, "time_temp")

    def test_historic_number_moviefone(self):
        result = self.router.route("7773456")
        self.assertEqual(result.feature, "moviefone")


class TestRouteDtmf(unittest.TestCase):
    """PhoneRouter.route_dtmf() for in-call digit entry."""

    def setUp(self):
        self.router = PhoneRouter()

    def test_single_digit_shortcut_0(self):
        result = self.router.route_dtmf("0")
        self.assertEqual(result.feature, "operator")
        self.assertFalse(result.is_direct_dial)

    def test_single_digit_shortcut_1(self):
        result = self.router.route_dtmf("1")
        self.assertEqual(result.feature, "jokes")

    def test_single_digit_shortcut_9(self):
        result = self.router.route_dtmf("9")
        self.assertEqual(result.feature, "roast")

    def test_multi_digit_routes_as_phone_number(self):
        result = self.router.route_dtmf("5555653")
        self.assertEqual(result.feature, "jokes")
        self.assertTrue(result.is_direct_dial)

    def test_unknown_multi_digit(self):
        result = self.router.route_dtmf("5559999")
        self.assertEqual(result.entry_type, "invalid")


class TestBirthdayPattern(unittest.TestCase):
    """BIRTHDAY_PATTERN regex edge cases."""

    def test_valid_jan_01(self):
        self.assertRegex("555-0101", BIRTHDAY_PATTERN)

    def test_valid_dec_31(self):
        self.assertRegex("555-1231", BIRTHDAY_PATTERN)

    def test_valid_feb_29(self):
        self.assertRegex("555-0229", BIRTHDAY_PATTERN)

    def test_invalid_month_00(self):
        self.assertIsNone(re.match(BIRTHDAY_PATTERN, "555-0001"))

    def test_invalid_month_13(self):
        self.assertIsNone(re.match(BIRTHDAY_PATTERN, "555-1301"))

    def test_invalid_day_00(self):
        self.assertIsNone(re.match(BIRTHDAY_PATTERN, "555-0100"))

    def test_invalid_day_32(self):
        self.assertIsNone(re.match(BIRTHDAY_PATTERN, "555-0132"))

    def test_no_match_without_555_prefix(self):
        self.assertIsNone(re.match(BIRTHDAY_PATTERN, "666-0704"))


class TestDirectoryIntegrity(unittest.TestCase):
    """Structural integrity of PHONE_DIRECTORY and related constants."""

    REQUIRED_KEYS = {"feature", "name", "type", "greeting"}
    VALID_TYPES = {"feature", "persona", "easter_egg"}

    def test_all_entries_have_required_keys(self):
        for number, entry in PHONE_DIRECTORY.items():
            for key in self.REQUIRED_KEYS:
                self.assertIn(
                    key, entry,
                    f"{number} missing required key '{key}'",
                )

    def test_all_entries_have_non_empty_greeting(self):
        for number, entry in PHONE_DIRECTORY.items():
            self.assertTrue(
                entry["greeting"].strip(),
                f"{number} has empty greeting",
            )

    def test_valid_entry_types(self):
        for number, entry in PHONE_DIRECTORY.items():
            self.assertIn(
                entry["type"], self.VALID_TYPES,
                f"{number} has invalid type '{entry['type']}'",
            )

    def test_personas_have_persona_key(self):
        for number, entry in PHONE_DIRECTORY.items():
            if entry["type"] == "persona":
                self.assertIn(
                    "persona_key", entry,
                    f"{number} is persona but missing persona_key",
                )

    def test_feature_to_number_complete(self):
        for number, entry in PHONE_DIRECTORY.items():
            feature = entry["feature"]
            self.assertIn(
                feature, FEATURE_TO_NUMBER,
                f"Feature '{feature}' not in FEATURE_TO_NUMBER",
            )
            self.assertEqual(
                FEATURE_TO_NUMBER[feature], number,
                f"FEATURE_TO_NUMBER['{feature}'] != '{number}'",
            )

    def test_all_features_round_trip(self):
        router = PhoneRouter()
        for number, entry in PHONE_DIRECTORY.items():
            result = router.route(number)
            self.assertEqual(
                result.feature, entry["feature"],
                f"Routing {number} returned '{result.feature}', expected '{entry['feature']}'",
            )

    def test_dtmf_shortcuts_map_to_directory(self):
        for digit, feature in DTMF_SHORTCUTS.items():
            self.assertIn(
                feature, FEATURE_TO_NUMBER,
                f"DTMF shortcut '{digit}' -> '{feature}' not in directory",
            )

    def test_birthday_greeting_constant_exists(self):
        self.assertTrue(BIRTHDAY_GREETING.strip())

    def test_route_result_has_no_greeting_field(self):
        result = RouteResult(
            feature="test", name="Test", entry_type="feature",
        )
        self.assertFalse(hasattr(result, "greeting"))


if __name__ == "__main__":
    unittest.main()
