"""Tests for directory lookup and ephemeral operator context."""

import importlib
import sys
import types
import unittest
from pathlib import Path


def _load_modules():
    """Load target modules without importing heavy runtime dependencies."""
    app_root = Path(__file__).resolve().parent.parent
    if str(app_root) not in sys.path:
        sys.path.insert(0, str(app_root))

    for pkg in ("config", "services"):
        if pkg not in sys.modules:
            mod = types.ModuleType(pkg)
            mod.__path__ = [str(app_root / pkg)]
            sys.modules[pkg] = mod

    if "config.settings" not in sys.modules:
        settings_mod = types.ModuleType("config.settings")

        class _FakeLLMSettings:
            pass

        settings_mod.LLMSettings = _FakeLLMSettings
        sys.modules["config.settings"] = settings_mod

    if "config.prompts" not in sys.modules:
        prompts_mod = types.ModuleType("config.prompts")
        prompts_mod.get_system_prompt = lambda **kw: "system prompt"
        sys.modules["config.prompts"] = prompts_mod

    directory_lookup_mod = importlib.import_module("services.directory_lookup")
    llm_mod = importlib.import_module("services.llm")
    return directory_lookup_mod, llm_mod


directory_lookup_mod, llm_mod = _load_modules()

lookup = directory_lookup_mod.lookup
ConversationContext = llm_mod.ConversationContext
Message = llm_mod.Message


class TestDirectoryLookup(unittest.TestCase):
    """Directory lookup ranking and filtering behavior."""

    def test_exact_name_match(self):
        matches = lookup("Dial-A-Joke")
        self.assertTrue(matches)
        self.assertEqual(matches[0].number, "555-5653")
        self.assertEqual(matches[0].name, "Dial-A-Joke")

    def test_fuzzy_partial_match(self):
        matches = lookup("joke line")
        self.assertTrue(matches)
        self.assertEqual(matches[0].number, "555-5653")
        self.assertEqual(matches[0].name, "Dial-A-Joke")

    def test_no_match_returns_empty(self):
        self.assertEqual(lookup("submarine gardening"), [])

    def test_top_3_ordering(self):
        matches = lookup("future", top_n=3)
        self.assertEqual(
            [match.number for match in matches],
            ["555-3678", "555-2687", "555-8463"],
        )
        self.assertTrue(matches[0].score >= matches[1].score >= matches[2].score)


class TestEphemeralContext(unittest.TestCase):
    """Ephemeral system messages should not persist in history."""

    def test_ephemeral_message_non_accumulation_across_two_turns(self):
        context = ConversationContext()
        context.messages.append(Message(role="system", content="base prompt"))
        context.add_user_message("first turn")
        context.add_assistant_message("first reply")

        first_api_messages = context.get_messages_for_api(
            ephemeral_context="Directory matches for this request: 555-5653 — Dial-A-Joke: feature"
        )
        self.assertEqual(first_api_messages[-1]["role"], "system")
        self.assertIn("555-5653", first_api_messages[-1]["content"])
        self.assertEqual(len(context.messages), 3)

        context.add_user_message("second turn")
        context.add_assistant_message("second reply")

        second_api_messages = context.get_messages_for_api(
            ephemeral_context="Directory matches for this request: 777-3456 — Moviefone: feature"
        )
        self.assertEqual(second_api_messages[-1]["role"], "system")
        self.assertIn("777-3456", second_api_messages[-1]["content"])
        self.assertNotIn("555-5653", second_api_messages[-1]["content"])
        self.assertEqual(len(context.messages), 5)
        self.assertTrue(
            all("Directory matches for this request:" not in msg.content for msg in context.messages)
        )


if __name__ == "__main__":
    unittest.main()
