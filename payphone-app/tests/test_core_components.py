"""Tests for core components: ConversationContext, SentenceBuffer, FeatureRegistry.

Uses importlib to load modules without triggering pydantic dependencies,
following the same pattern as test_phone_routing.py.
"""

import importlib
import sys
import types
import unittest
from pathlib import Path


def _load_modules():
    """Load llm and registry modules without heavy dependencies.

    Stubs out packages to avoid importing settings.py or other heavy deps.
    """
    app_root = Path(__file__).resolve().parent.parent
    if str(app_root) not in sys.path:
        sys.path.insert(0, str(app_root))

    # Stub parent packages
    for pkg in ("config", "core", "services", "features"):
        if pkg not in sys.modules:
            mod = types.ModuleType(pkg)
            mod.__path__ = [str(app_root / pkg)]
            sys.modules[pkg] = mod

    # Stub config.settings so llm.py import doesn't fail
    if "config.settings" not in sys.modules:
        settings_mod = types.ModuleType("config.settings")

        class _FakeLLMSettings:
            pass

        settings_mod.LLMSettings = _FakeLLMSettings
        sys.modules["config.settings"] = settings_mod

    # Stub config.prompts so llm.py import doesn't fail
    if "config.prompts" not in sys.modules:
        prompts_mod = types.ModuleType("config.prompts")
        prompts_mod.get_system_prompt = lambda **kw: "system prompt"
        sys.modules["config.prompts"] = prompts_mod

    # Stub features.base so registry.py import doesn't fail
    if "features.base" not in sys.modules:
        base_mod = types.ModuleType("features.base")

        class _BaseFeature:
            name: str = "Base"
            dial_code: str = "0"
            voice_triggers: list = []

        base_mod.BaseFeature = _BaseFeature
        sys.modules["features.base"] = base_mod

    llm_mod = importlib.import_module("services.llm")
    registry_mod = importlib.import_module("features.registry")
    return llm_mod, registry_mod


llm_mod, registry_mod = _load_modules()

Message = llm_mod.Message
ConversationContext = llm_mod.ConversationContext
SentenceBuffer = llm_mod.SentenceBuffer
FeatureRegistry = registry_mod.FeatureRegistry
BaseFeature = sys.modules["features.base"].BaseFeature


# ---------------------------------------------------------------------------
# ConversationContext tests
# ---------------------------------------------------------------------------


class TestConversationContext(unittest.TestCase):
    """ConversationContext: add messages, trim history, edge cases."""

    def test_add_user_message(self):
        ctx = ConversationContext()
        ctx.add_user_message("hello")
        self.assertEqual(len(ctx.messages), 1)
        self.assertEqual(ctx.messages[0].role, "user")
        self.assertEqual(ctx.messages[0].content, "hello")

    def test_add_assistant_message(self):
        ctx = ConversationContext()
        ctx.add_assistant_message("hi there")
        self.assertEqual(len(ctx.messages), 1)
        self.assertEqual(ctx.messages[0].role, "assistant")

    def test_get_messages_for_api(self):
        ctx = ConversationContext()
        ctx.add_user_message("q")
        ctx.add_assistant_message("a")
        api_msgs = ctx.get_messages_for_api()
        self.assertEqual(len(api_msgs), 2)
        self.assertIsInstance(api_msgs[0], dict)
        self.assertEqual(api_msgs[0]["role"], "user")

    def test_trim_preserves_system_messages(self):
        ctx = ConversationContext(max_history=2)
        ctx.messages.append(Message(role="system", content="sys"))
        # Add more than max_history * 2 non-system messages
        for i in range(6):
            if i % 2 == 0:
                ctx.add_user_message(f"u{i}")
            else:
                ctx.add_assistant_message(f"a{i}")
        # System message should be preserved
        self.assertEqual(ctx.messages[0].role, "system")
        self.assertEqual(ctx.messages[0].content, "sys")

    def test_trim_keeps_max_history_exchanges(self):
        ctx = ConversationContext(max_history=2)
        # 2 exchanges = 4 messages max
        for i in range(10):
            if i % 2 == 0:
                ctx.add_user_message(f"u{i}")
            else:
                ctx.add_assistant_message(f"a{i}")
        # Should have at most max_history * 2 non-system messages
        non_system = [m for m in ctx.messages if m.role != "system"]
        self.assertLessEqual(len(non_system), 4)

    def test_clear_keeps_system(self):
        ctx = ConversationContext()
        ctx.messages.append(Message(role="system", content="sys"))
        ctx.add_user_message("hello")
        ctx.add_assistant_message("hi")
        ctx.clear()
        self.assertEqual(len(ctx.messages), 1)
        self.assertEqual(ctx.messages[0].role, "system")

    def test_clear_empty(self):
        ctx = ConversationContext()
        ctx.clear()
        self.assertEqual(len(ctx.messages), 0)

    def test_all_system_messages_no_crash(self):
        """Edge case: all messages are system — _trim_history should not crash."""
        ctx = ConversationContext(max_history=1)
        ctx.messages = [Message(role="system", content=f"s{i}") for i in range(5)]
        # Force _non_system_count to a value that triggers trimming
        ctx._non_system_count = 10
        ctx._trim_history()
        # Should reset _non_system_count without crashing
        self.assertEqual(ctx._non_system_count, 0)

    def test_empty_context_for_api(self):
        ctx = ConversationContext()
        self.assertEqual(ctx.get_messages_for_api(), [])


# ---------------------------------------------------------------------------
# SentenceBuffer tests
# ---------------------------------------------------------------------------


class TestSentenceBuffer(unittest.TestCase):
    """SentenceBuffer: token accumulation, sentence detection, flush."""

    def test_returns_none_for_partial(self):
        buf = SentenceBuffer(min_length=5)
        result = buf.add_token("Hello")
        self.assertIsNone(result)

    def test_detects_sentence_on_period(self):
        buf = SentenceBuffer(min_length=5)
        buf.add_token("Hello world")
        result = buf.add_token(".")
        self.assertIsNotNone(result)
        self.assertIn("Hello world", result)

    def test_detects_sentence_on_exclamation(self):
        buf = SentenceBuffer(min_length=5)
        result = buf.add_token("Great news!")
        # Should detect on the ! within the token and return the sentence
        self.assertIsNotNone(result)
        self.assertIn("Great news", result)

    def test_min_length_respected(self):
        buf = SentenceBuffer(min_length=20)
        result = buf.add_token("Hi.")
        # "Hi." is only 3 chars, below min_length
        self.assertIsNone(result)

    def test_flush_returns_remaining(self):
        buf = SentenceBuffer(min_length=5)
        buf.add_token("some remaining text")
        result = buf.flush()
        self.assertEqual(result, "some remaining text")

    def test_flush_empty_returns_none(self):
        buf = SentenceBuffer(min_length=5)
        result = buf.flush()
        self.assertIsNone(result)

    def test_flush_whitespace_only_returns_none(self):
        buf = SentenceBuffer(min_length=5)
        buf.add_token("   ")
        result = buf.flush()
        self.assertIsNone(result)

    def test_clear_empties_buffer(self):
        buf = SentenceBuffer(min_length=5)
        buf.add_token("some text")
        buf.clear()
        result = buf.flush()
        self.assertIsNone(result)

    def test_multiple_sentences(self):
        buf = SentenceBuffer(min_length=5)
        # First sentence
        buf.add_token("First sentence")
        s1 = buf.add_token(". Second")
        self.assertIsNotNone(s1)
        self.assertIn("First", s1)
        # Remainder should have "Second"
        buf.add_token(" sentence")
        s2 = buf.add_token(".")
        self.assertIsNotNone(s2)
        self.assertIn("Second", s2)

    def test_comma_as_delimiter(self):
        buf = SentenceBuffer(min_length=5, delimiters=",")
        buf.add_token("Hello there")
        result = buf.add_token(", friend")
        self.assertIsNotNone(result)
        self.assertIn("Hello", result)


# ---------------------------------------------------------------------------
# FeatureRegistry tests
# ---------------------------------------------------------------------------


class TestFeatureRegistry(unittest.TestCase):
    """FeatureRegistry: register, lookup, new-instance-per-call."""

    def setUp(self):
        FeatureRegistry.clear()

    def tearDown(self):
        FeatureRegistry.clear()

    def _make_feature_class(self, name, dial_code, triggers=None):
        """Create a minimal concrete feature class for testing."""
        attrs = {
            "name": name,
            "dial_code": dial_code,
            "voice_triggers": triggers or [],
            "handle": lambda self, s, p: None,
            "get_greeting": lambda self: f"Hello from {name}",
        }
        return type(name, (BaseFeature,), attrs)

    def test_register_and_get(self):
        cls = self._make_feature_class("TestFeature", "42")
        FeatureRegistry.register(cls)
        self.assertIs(FeatureRegistry.get("42"), cls)

    def test_get_unknown_returns_none(self):
        self.assertIsNone(FeatureRegistry.get("999"))

    def test_get_instance_returns_new_each_time(self):
        cls = self._make_feature_class("TestFeature", "42")
        FeatureRegistry.register(cls)
        inst1 = FeatureRegistry.get_instance("42")
        inst2 = FeatureRegistry.get_instance("42")
        self.assertIsNotNone(inst1)
        self.assertIsNotNone(inst2)
        self.assertIsNot(inst1, inst2)

    def test_get_instance_unknown_returns_none(self):
        self.assertIsNone(FeatureRegistry.get_instance("999"))

    def test_voice_trigger_lookup(self):
        cls = self._make_feature_class("Jokes", "1", triggers=["tell me a joke"])
        FeatureRegistry.register(cls)
        result = FeatureRegistry.get_by_voice("tell me a joke")
        self.assertIs(result, cls)

    def test_voice_trigger_case_insensitive(self):
        cls = self._make_feature_class("Jokes", "1", triggers=["jokes"])
        FeatureRegistry.register(cls)
        result = FeatureRegistry.get_by_voice("JOKES")
        self.assertIs(result, cls)

    def test_voice_match_substring(self):
        cls = self._make_feature_class("Jokes", "1", triggers=["joke"])
        FeatureRegistry.register(cls)
        result = FeatureRegistry.get_by_voice_match("tell me a joke please")
        self.assertIs(result, cls)

    def test_list_features(self):
        cls1 = self._make_feature_class("Jokes", "1")
        cls2 = self._make_feature_class("Trivia", "2")
        FeatureRegistry.register(cls1)
        FeatureRegistry.register(cls2)
        features = FeatureRegistry.list_features()
        self.assertEqual(features, {"1": "Jokes", "2": "Trivia"})

    def test_clear_removes_all(self):
        cls = self._make_feature_class("Jokes", "1", triggers=["joke"])
        FeatureRegistry.register(cls)
        FeatureRegistry.clear()
        self.assertIsNone(FeatureRegistry.get("1"))
        self.assertIsNone(FeatureRegistry.get_by_voice("joke"))


if __name__ == "__main__":
    unittest.main()
