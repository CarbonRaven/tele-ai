"""Base class for all payphone features.

Features provide specific functionality like jokes, trivia, fortune telling, etc.
Each feature handles its own conversation flow and DTMF navigation.
"""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.session import Session
    from core.pipeline import VoicePipeline


class BaseFeature(ABC):
    """Abstract base class for all payphone features.

    Subclasses must implement:
    - name: Human-readable feature name
    - dial_code: DTMF code to access feature (e.g., "1", "555-5653")
    - handle(): Main feature logic
    - get_greeting(): Initial greeting when feature is accessed
    """

    # Class attributes to be defined by subclasses
    name: str = "Base Feature"
    dial_code: str = "0"
    description: str = "Base feature description"

    # Optional: voice triggers for natural language access
    voice_triggers: list[str] = []

    def __init__(self):
        """Initialize feature state."""
        pass

    @abstractmethod
    async def handle(self, session: "Session", pipeline: "VoicePipeline") -> None:
        """Main feature handler.

        This method is called when the user accesses the feature.
        It should handle the complete interaction flow for this feature.

        Args:
            session: Current call session.
            pipeline: Voice pipeline for audio processing.
        """
        pass

    @abstractmethod
    def get_greeting(self) -> str:
        """Get the initial greeting when feature is accessed.

        Returns:
            Greeting text to be spoken when user enters this feature.
        """
        pass

    async def handle_dtmf(
        self,
        digit: str,
        session: "Session",
        pipeline: "VoicePipeline",
    ) -> bool:
        """Handle DTMF input within the feature.

        Override this method to provide custom DTMF handling.
        Default implementation returns to main menu on '*'.

        Args:
            digit: DTMF digit received (0-9, *, #).
            session: Current call session.
            pipeline: Voice pipeline.

        Returns:
            True if the digit was handled, False to return to main menu.
        """
        if digit == "*":
            return False  # Return to main menu
        return True  # Digit handled (or ignored)

    async def on_enter(self, session: "Session", pipeline: "VoicePipeline") -> None:
        """Called when user enters this feature.

        Override to perform setup when feature is accessed.

        Args:
            session: Current call session.
            pipeline: Voice pipeline.
        """
        # Play greeting
        greeting = self.get_greeting()
        if greeting:
            await pipeline.speak(session, greeting)

    async def on_exit(self, session: "Session") -> None:
        """Called when user exits this feature.

        Override to perform cleanup when leaving feature.

        Args:
            session: Current call session.
        """
        pass

    def get_help_text(self) -> str:
        """Get help text for this feature.

        Returns:
            Help text explaining how to use this feature.
        """
        return f"{self.name}: {self.description}"


class ConversationalFeature(BaseFeature):
    """Base class for features that primarily use LLM conversation.

    Provides a standard conversation loop that delegates to the LLM
    with a feature-specific system prompt.
    """

    # Override in subclass
    system_prompt_key: str = "operator"

    async def handle(self, session: "Session", pipeline: "VoicePipeline") -> None:
        """Run conversation loop for this feature.

        Args:
            session: Current call session.
            pipeline: Voice pipeline.
        """
        from config.prompts import get_system_prompt

        # Set up feature-specific context
        session.switch_feature(self.system_prompt_key)

        # Enter feature
        await self.on_enter(session, pipeline)

        # Conversation loop
        while session.is_active:
            # Listen for input
            audio, transcript = await pipeline.listen_and_transcribe(session)

            if transcript is None:
                # Timeout or no speech
                continue

            # Check for exit commands
            if self._is_exit_command(transcript):
                break

            # Generate and speak response
            response = await pipeline.generate_response(session, transcript)
            await pipeline.speak(session, response)

        await self.on_exit(session)

    def _is_exit_command(self, text: str) -> bool:
        """Check if text is an exit command.

        Args:
            text: Transcribed text.

        Returns:
            True if user wants to exit feature.
        """
        lower = text.lower().strip()
        exit_phrases = [
            "menu",
            "main menu",
            "go back",
            "exit",
            "quit",
            "done",
            "that's all",
            "thank you",
            "thanks",
        ]
        return any(phrase in lower for phrase in exit_phrases)


class InteractiveFeature(BaseFeature):
    """Base class for features with structured interactions (games, quizzes, etc.).

    Provides state management for multi-turn interactions.
    """

    def __init__(self):
        super().__init__()
        self._state: dict = {}

    def reset_state(self) -> None:
        """Reset feature state for new interaction."""
        self._state = {}

    async def on_enter(self, session: "Session", pipeline: "VoicePipeline") -> None:
        """Reset state when entering feature."""
        self.reset_state()
        await super().on_enter(session, pipeline)
