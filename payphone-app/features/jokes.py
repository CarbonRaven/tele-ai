"""Dial-A-Joke feature - classic joke hotline.

Provides an endless supply of jokes in the style of 1990s
premium joke hotlines.
"""

from typing import TYPE_CHECKING

from features.base import ConversationalFeature
from features.registry import register_feature

if TYPE_CHECKING:
    from core.pipeline import VoicePipeline
    from core.session import Session


@register_feature
class JokesFeature(ConversationalFeature):
    """Dial-A-Joke feature.

    Tells jokes in the style of classic joke hotlines.
    Users can ask for specific types of jokes or just say "another one".
    """

    name = "Dial-A-Joke"
    dial_code = "1"
    description = "Hear hilarious jokes from our comedy hotline"
    system_prompt_key = "jokes"

    voice_triggers = [
        "jokes",
        "joke",
        "funny",
        "comedy",
        "laugh",
        "tell me a joke",
        "make me laugh",
    ]

    def __init__(self):
        super().__init__()
        self._jokes_told = 0

    def get_greeting(self) -> str:
        """Get jokes feature greeting."""
        return (
            "Welcome to Dial-A-Joke, your premier comedy hotline! "
            "I've got jokes for days. Want to hear one?"
        )

    async def handle(self, session: "Session", pipeline: "VoicePipeline") -> None:
        """Handle joke telling interaction."""
        session.switch_feature(self.system_prompt_key)
        self._jokes_told = 0

        # Play greeting
        await self.on_enter(session, pipeline)

        # Joke loop
        while session.is_active:
            # Listen for input
            audio, transcript = await pipeline.listen_and_transcribe(session)

            if transcript is None:
                # On timeout, offer another joke
                if self._jokes_told > 0:
                    await pipeline.speak(
                        session,
                        "Want to hear another one? Just say yes or press 1.",
                    )
                continue

            lower = transcript.lower().strip()

            # Check for exit
            if self._is_exit_command(lower):
                await pipeline.speak(
                    session,
                    f"Thanks for laughing with us! I told you {self._jokes_told} jokes today. "
                    "Come back anytime you need a laugh!",
                )
                break

            # Check for affirmative (wants a joke)
            if self._wants_joke(lower) or self._jokes_told == 0:
                # Generate and tell a joke
                prompt = self._get_joke_prompt(lower)
                response = await pipeline.generate_response(session, prompt)
                await pipeline.speak(session, response)
                self._jokes_told += 1

                # Follow up
                if self._jokes_told < 3:
                    await pipeline.speak(session, "Want to hear another one?")
                else:
                    await pipeline.speak(session, "Another? I've got plenty more!")

            else:
                # Handle other requests
                response = await pipeline.generate_response(session, transcript)
                await pipeline.speak(session, response)

        await self.on_exit(session)

    def _wants_joke(self, text: str) -> bool:
        """Check if user wants to hear a joke."""
        affirmative = [
            "yes",
            "yeah",
            "yep",
            "sure",
            "okay",
            "ok",
            "please",
            "another",
            "more",
            "hit me",
            "go ahead",
            "tell me",
            "joke",
            "1",
        ]
        return any(word in text for word in affirmative)

    def _get_joke_prompt(self, text: str) -> str:
        """Generate a prompt for the LLM to tell a joke.

        Args:
            text: User's request (may specify joke type).

        Returns:
            Prompt for joke generation.
        """
        # Check for specific joke types
        joke_types = {
            "knock knock": "Tell me a knock-knock joke.",
            "pun": "Tell me a pun or wordplay joke.",
            "dad joke": "Tell me a classic dad joke.",
            "one liner": "Tell me a quick one-liner joke.",
            "animal": "Tell me a joke about animals.",
            "tech": "Tell me a technology or computer joke.",
            "food": "Tell me a food-related joke.",
            "work": "Tell me a joke about work or offices.",
        }

        for keyword, prompt in joke_types.items():
            if keyword in text:
                return prompt

        # Default: any joke
        return "Tell me a joke. Make it funny and appropriate for all ages."

    def _is_exit_command(self, text: str) -> bool:
        """Check if user wants to exit jokes."""
        exit_phrases = [
            "no",
            "nope",
            "stop",
            "enough",
            "done",
            "quit",
            "exit",
            "menu",
            "main menu",
            "that's enough",
            "i'm good",
            "no more",
            "bye",
        ]
        return any(phrase in text for phrase in exit_phrases)

    async def handle_dtmf(
        self, digit: str, session: "Session", pipeline: "VoicePipeline"
    ) -> bool:
        """Handle DTMF in jokes feature.

        Args:
            digit: DTMF digit pressed.
            session: Current call session.
            pipeline: Voice pipeline for audio processing.

        Returns:
            True to continue in feature, False to return to menu.
        """
        if digit == "1":
            # Tell a joke
            response = await pipeline.generate_response(
                session,
                "Tell me a joke. Make it funny!",
            )
            await pipeline.speak(session, response)
            self._jokes_told += 1
            return True

        if digit == "*":
            return False  # Return to menu

        return True
