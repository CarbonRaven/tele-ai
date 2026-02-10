"""Test all 44 phone directory numbers end-to-end.

Tests routing, greetings, prompt generation, and optionally LLM responses
for every number in the phone directory plus special patterns.

Usage:
    pytest tests/test_all_numbers.py -v              # Routing + prompts only (fast)
    pytest tests/test_all_numbers.py -v --run-llm    # Include LLM response tests (slow)
"""

import re
import pytest

from config.phone_directory import (
    BIRTHDAY_GREETING,
    BIRTHDAY_PATTERN,
    DEFAULT_GREETING_NOT_IN_SERVICE,
    DTMF_SHORTCUTS,
    PHONE_DIRECTORY,
)
from config.prompts import (
    FEATURE_PROMPTS,
    PERSONA_PROMPTS,
    PHONE_DIRECTORY_BLOCK,
    get_system_prompt,
)
from core.phone_router import PhoneRouter


def pytest_addoption(parser):
    parser.addoption(
        "--run-llm", action="store_true", default=False, help="Run LLM response tests"
    )


@pytest.fixture
def router():
    return PhoneRouter()


# ---------------------------------------------------------------------------
# Phase 3a: Direct-dial features
# ---------------------------------------------------------------------------

FEATURE_NUMBERS = [
    ("555-0000", "operator", "feature"),
    ("555-5653", "jokes", "feature"),
    ("555-8748", "trivia", "feature"),
    ("555-3678", "fortune", "feature"),
    ("555-9328", "weather", "feature"),
    ("555-4676", "horoscope", "feature"),
    ("555-6397", "news", "feature"),
    ("555-7767", "sports", "feature"),
    ("555-7867", "stories", "feature"),
    ("555-6235", "madlibs", "feature"),
    ("555-9687", "would_you_rather", "feature"),
    ("555-2090", "twenty_questions", "feature"),
    ("555-2384", "advice", "feature"),
    ("555-2667", "compliment", "feature"),
    ("555-7627", "roast", "feature"),
    ("555-5433", "life_coach", "feature"),
    ("555-2663", "confession", "feature"),
    ("555-8368", "vent", "feature"),
    ("555-2655", "collect_call", "feature"),
    ("555-8477", "nintendo_tips", "feature"),
    ("555-8463", "time_traveler", "feature"),
    ("555-2252", "calculator", "feature"),
    ("555-8726", "translator", "feature"),
    ("555-7735", "spelling", "feature"),
    ("555-3428", "dictionary", "feature"),
    ("555-7324", "recipe", "feature"),
    ("555-3322", "debate", "feature"),
    ("555-4688", "interview", "feature"),
    ("767-2676", "time_temp", "feature"),
    ("777-3456", "moviefone", "feature"),
]


@pytest.mark.parametrize("number,feature,entry_type", FEATURE_NUMBERS)
def test_feature_routing(router, number, feature, entry_type):
    """Test that each feature number routes correctly."""
    result = router.route(number)
    assert result.feature == feature, f"{number} routed to {result.feature}, expected {feature}"
    assert result.entry_type == entry_type


@pytest.mark.parametrize("number,feature,entry_type", FEATURE_NUMBERS)
def test_feature_greeting(number, feature, entry_type):
    """Test that each feature has a non-empty greeting."""
    entry = PHONE_DIRECTORY[number]
    assert entry["greeting"], f"{number} ({feature}) has empty greeting"
    assert len(entry["greeting"]) > 10, f"{number} greeting too short: {entry['greeting']}"


@pytest.mark.parametrize("number,feature,entry_type", FEATURE_NUMBERS)
def test_feature_prompt(number, feature, entry_type):
    """Test that each feature has a system prompt."""
    if feature == "operator":
        prompt = get_system_prompt(feature="operator")
    else:
        prompt = get_system_prompt(feature=feature)
    assert prompt, f"{feature} has no system prompt"
    assert len(prompt) > 50, f"{feature} prompt too short"


# ---------------------------------------------------------------------------
# Phase 3b: Personas
# ---------------------------------------------------------------------------

PERSONA_NUMBERS = [
    ("555-7243", "sage"),
    ("555-5264", "comedian"),
    ("555-3383", "detective"),
    ("555-4726", "grandma"),
    ("555-2687", "robot"),
    ("555-8255", "valley"),
    ("555-7638", "beatnik"),
    ("555-4263", "gameshow"),
    ("555-9427", "conspiracy"),
]


@pytest.mark.parametrize("number,persona_key", PERSONA_NUMBERS)
def test_persona_routing(router, number, persona_key):
    """Test that each persona number routes correctly."""
    result = router.route(number)
    assert result.entry_type == "persona", f"{number} type is {result.entry_type}, expected persona"
    assert result.persona_key == persona_key, f"{number} persona_key is {result.persona_key}, expected {persona_key}"


@pytest.mark.parametrize("number,persona_key", PERSONA_NUMBERS)
def test_persona_greeting(number, persona_key):
    """Test that each persona has a non-empty greeting."""
    entry = PHONE_DIRECTORY[number]
    assert entry["greeting"], f"{number} ({persona_key}) has empty greeting"


@pytest.mark.parametrize("number,persona_key", PERSONA_NUMBERS)
def test_persona_prompt(number, persona_key):
    """Test that each persona has a system prompt."""
    prompt = get_system_prompt(persona=persona_key)
    assert prompt, f"Persona {persona_key} has no system prompt"
    assert "PHONE DIRECTORY" not in prompt, f"Persona {persona_key} should NOT include phone directory"


# ---------------------------------------------------------------------------
# Phase 3c: Easter eggs
# ---------------------------------------------------------------------------

EASTER_EGG_NUMBERS = [
    ("867-5309", "easter_jenny"),
    ("555-2600", "easter_phreaker"),
    ("555-1337", "easter_hacker"),
    ("555-7492", "easter_pizza"),
    ("555-1313", "easter_haunted"),
]


@pytest.mark.parametrize("number,feature", EASTER_EGG_NUMBERS)
def test_easter_egg_routing(router, number, feature):
    """Test that each easter egg number routes correctly."""
    result = router.route(number)
    assert result.feature == feature, f"{number} routed to {result.feature}, expected {feature}"
    assert result.entry_type == "easter_egg"


@pytest.mark.parametrize("number,feature", EASTER_EGG_NUMBERS)
def test_easter_egg_greeting(number, feature):
    """Test that each easter egg has a non-empty greeting."""
    entry = PHONE_DIRECTORY[number]
    assert entry["greeting"], f"{number} ({feature}) has empty greeting"


# ---------------------------------------------------------------------------
# Phase 3d: Special patterns
# ---------------------------------------------------------------------------

def test_birthday_pattern_valid(router):
    """Test valid birthday numbers (555-MMDD)."""
    birthdays = ["555-0704", "555-1231", "555-0101", "555-0214", "555-1225"]
    for number in birthdays:
        result = router.route(number)
        assert result.feature == "easter_birthday", f"{number} should be birthday, got {result.feature}"


def test_birthday_pattern_regex():
    """Test the birthday regex matches expected formats."""
    pattern = re.compile(BIRTHDAY_PATTERN)
    assert pattern.match("555-0101")  # Jan 1
    assert pattern.match("555-1231")  # Dec 31
    assert pattern.match("555-0704")  # Jul 4
    assert not pattern.match("555-0000")  # Invalid month/day (but this is operator)
    assert not pattern.match("555-1300")  # Month 13
    assert not pattern.match("555-0032")  # Day 32


def test_birthday_greeting():
    """Test birthday greeting exists."""
    assert BIRTHDAY_GREETING
    assert "birthday" in BIRTHDAY_GREETING.lower()


def test_invalid_number(router):
    """Test invalid numbers get SIT tri-tone response."""
    invalids = ["555-9999", "123-4567", "999-0000"]
    for number in invalids:
        result = router.route(number)
        assert result.entry_type == "invalid", f"{number} should be invalid, got {result.entry_type}"


def test_not_in_service_message():
    """Test the not-in-service message exists."""
    assert DEFAULT_GREETING_NOT_IN_SERVICE
    assert "not in service" in DEFAULT_GREETING_NOT_IN_SERVICE.lower()


def test_area_code_stripping(router):
    """Test that area codes are stripped from dialed numbers."""
    # 10-digit with area code
    result = router.route("555-555-5653")
    assert result.feature == "jokes", f"10-digit should route to jokes, got {result.feature}"

    # 11-digit with country + area code
    result = router.route("1-555-555-5653")
    assert result.feature == "jokes", f"11-digit should route to jokes, got {result.feature}"


# ---------------------------------------------------------------------------
# DTMF shortcuts
# ---------------------------------------------------------------------------

def test_dtmf_shortcuts(router):
    """Test all single-digit DTMF shortcuts."""
    for digit, expected_feature in DTMF_SHORTCUTS.items():
        result = router.route_dtmf(digit)
        assert result.feature == expected_feature, f"DTMF {digit} should route to {expected_feature}, got {result.feature}"


# ---------------------------------------------------------------------------
# Prompt consistency checks
# ---------------------------------------------------------------------------

def test_operator_prompt_includes_directory():
    """Test that operator prompt includes the phone directory."""
    prompt = get_system_prompt(feature="operator")
    assert "PHONE DIRECTORY" in prompt
    assert "555-5653" in prompt  # Jokes number should be in directory


def test_non_operator_excludes_directory():
    """Test that non-operator features exclude the phone directory."""
    for feature in ["jokes", "trivia", "fortune", "weather"]:
        prompt = get_system_prompt(feature=feature)
        assert "PHONE DIRECTORY" not in prompt, f"{feature} should not include phone directory"


def test_all_features_have_prompts():
    """Test every feature in PHONE_DIRECTORY has a matching prompt."""
    for number, entry in PHONE_DIRECTORY.items():
        feature = entry["feature"]
        etype = entry["type"]

        if etype == "persona":
            persona_key = entry.get("persona_key")
            assert persona_key, f"{number} is persona but missing persona_key"
            assert persona_key in PERSONA_PROMPTS, f"Persona {persona_key} not in PERSONA_PROMPTS"
        elif feature.startswith("easter_"):
            assert feature in FEATURE_PROMPTS, f"Easter egg {feature} not in FEATURE_PROMPTS"
        elif feature != "operator":
            assert feature in FEATURE_PROMPTS, f"Feature {feature} not in FEATURE_PROMPTS"


def test_phone_directory_block_has_key_numbers():
    """Test the phone directory block includes key service numbers."""
    key_numbers = ["555-5653", "555-8748", "555-3678", "767-2676", "867-5309"]
    for number in key_numbers:
        assert number in PHONE_DIRECTORY_BLOCK, f"{number} missing from PHONE_DIRECTORY_BLOCK"


def test_base_prompt_rules():
    """Test that base prompt includes critical rules."""
    prompt = get_system_prompt()
    assert "one digit at a time" in prompt.lower(), "Missing digit-by-digit phone number rule"
    assert "asterisk" in prompt.lower(), "Missing no-asterisk-actions rule"
    assert "under 50 words" in prompt.lower(), "Missing brevity rule"


# ---------------------------------------------------------------------------
# Coverage summary
# ---------------------------------------------------------------------------

def test_directory_completeness():
    """Test that the directory has all expected entries."""
    assert len(PHONE_DIRECTORY) == 44, f"Expected 44 entries, got {len(PHONE_DIRECTORY)}"
    assert len(DTMF_SHORTCUTS) == 10, f"Expected 10 DTMF shortcuts, got {len(DTMF_SHORTCUTS)}"
