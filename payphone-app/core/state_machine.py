"""State machine for conversation flow management.

Handles state transitions for the voice assistant including:
- Main menu navigation
- Feature/persona selection
- Listening -> Processing -> Speaking cycle
- Timeout handling
- Barge-in support
"""

__all__ = [
    "State",
    "StateTransition",
    "StateMachine",
]

import asyncio
import logging
import time
from dataclasses import dataclass
from enum import Enum, auto
from typing import TYPE_CHECKING

from config.phone_directory import (
    BIRTHDAY_GREETING,
    DEFAULT_GREETING_NOT_IN_SERVICE,
    FEATURE_TO_NUMBER,
    PHONE_DIRECTORY,
)
from core.phone_router import PhoneRouter, RouteResult

if TYPE_CHECKING:
    from core.session import Session
    from core.pipeline import VoicePipeline

logger = logging.getLogger(__name__)


def _get_greeting(feature: str) -> str:
    """Look up greeting for a feature from the phone directory.

    Handles the birthday easter egg (regex-matched, not in PHONE_DIRECTORY)
    and falls back to a generated greeting for unknown features.
    """
    if feature == "easter_birthday":
        return BIRTHDAY_GREETING
    number = FEATURE_TO_NUMBER.get(feature)
    if number and number in PHONE_DIRECTORY:
        return PHONE_DIRECTORY[number]["greeting"]
    return f"Welcome to {feature.replace('_', ' ').title()}!"


class State(Enum):
    """Conversation states.

    State transitions:
        IDLE -> GREETING (call_start)
        GREETING -> LISTENING (greeting_complete)
        LISTENING -> PROCESSING (transcript_ready)
        LISTENING -> TIMEOUT (silence_timeout)
        PROCESSING -> SPEAKING (response_ready)
        SPEAKING -> LISTENING (response_complete)
        SPEAKING -> BARGE_IN (user_interrupt)
        BARGE_IN -> LISTENING (barge_in)
        TIMEOUT -> LISTENING (timeout_prompt)
        TIMEOUT -> GOODBYE (extended_silence)
        GOODBYE -> HANGUP (goodbye_complete)
        * -> HANGUP (remote_hangup)
    """

    IDLE = auto()  # Waiting for call
    GREETING = auto()  # Playing welcome message
    MAIN_MENU = auto()  # Awaiting input at main menu
    LISTENING = auto()  # Recording user speech
    PROCESSING = auto()  # STT -> LLM processing
    SPEAKING = auto()  # TTS playback (managed externally by pipeline)
    BARGE_IN = auto()  # User interrupted TTS
    TIMEOUT = auto()  # Silence timeout prompt
    FEATURE = auto()  # In a specific feature (reserved for future use)
    GOODBYE = auto()  # Playing farewell message
    HANGUP = auto()  # Call ended


@dataclass
class StateTransition:
    """Represents a state transition."""

    from_state: State
    to_state: State
    trigger: str


class StateMachine:
    """State machine for managing conversation flow.

    Handles transitions between states based on events like:
    - User speech detected/ended
    - DTMF input received
    - TTS playback complete
    - Timeout events
    """

    def __init__(
        self,
        session: "Session",
        route_result: RouteResult | None = None,
        phone_router: PhoneRouter | None = None,
    ):
        self.session = session
        self._state = State.IDLE
        self._previous_state = State.IDLE
        self._route_result = route_result
        self._phone_router = phone_router or PhoneRouter()

        # Timeout tracking
        self._silence_start: float | None = None
        self._timeout_prompted = False

        # Safety timeout for SPEAKING state (seconds)
        self._speaking_entered: float | None = None
        self._speaking_safety_timeout = 5.0

        # Feature state
        self._current_feature_handler = None

    @property
    def state(self) -> State:
        """Get current state."""
        return self._state

    def transition_to(self, new_state: State, trigger: str = "manual") -> None:
        """Transition to a new state.

        Args:
            new_state: Target state.
            trigger: What triggered the transition.
        """
        if new_state == self._state:
            return

        logger.debug(
            f"Session {self.session.call_id}: "
            f"{self._state.name} -> {new_state.name} ({trigger})"
        )

        self._previous_state = self._state
        self._state = new_state

        # Reset timeout tracking on state change
        if new_state not in (State.TIMEOUT, State.LISTENING):
            self._silence_start = None
            self._timeout_prompted = False

        # Reset SPEAKING safety timer on state change
        if new_state != State.SPEAKING:
            self._speaking_entered = None

    async def process(self, pipeline: "VoicePipeline") -> None:
        """Process current state and handle transitions.

        Args:
            pipeline: Voice pipeline for audio processing.
        """
        if self._state == State.IDLE:
            # Start with greeting
            self.transition_to(State.GREETING, "call_start")
            await self._play_greeting(pipeline)

        elif self._state == State.GREETING:
            # After greeting, go to main menu/listening
            self.transition_to(State.LISTENING, "greeting_complete")

        elif self._state == State.MAIN_MENU:
            # Wait for input
            await self._handle_main_menu(pipeline)

        elif self._state == State.LISTENING:
            # Listen for speech or DTMF
            await self._handle_listening(pipeline)

        elif self._state == State.PROCESSING:
            # Process speech -> generate response
            await self._handle_processing(pipeline)

        elif self._state == State.SPEAKING:
            # TTS playback is handled externally by VoicePipeline.speak()
            # This state is set before calling speak() and transitions happen
            # after speak() returns. This branch is a safety net.
            if self._speaking_entered is None:
                self._speaking_entered = time.time()
            elapsed = time.time() - self._speaking_entered
            if elapsed >= self._speaking_safety_timeout:
                logger.warning(
                    f"Session {self.session.call_id}: SPEAKING state stuck for "
                    f"{elapsed:.1f}s, forcing transition to LISTENING"
                )
                self._speaking_entered = None
                self.transition_to(State.LISTENING, "speaking_safety_timeout")
            else:
                logger.debug(f"Session {self.session.call_id}: In SPEAKING state, waiting for TTS")
                await asyncio.sleep(0.1)  # Prevent busy-spinning

        elif self._state == State.BARGE_IN:
            # User interrupted, cancel TTS and listen
            self.session.clear_barge_in()
            self.transition_to(State.LISTENING, "barge_in")

        elif self._state == State.TIMEOUT:
            await self._handle_timeout(pipeline)

        elif self._state == State.GOODBYE:
            await self._play_goodbye(pipeline)
            self.transition_to(State.HANGUP, "goodbye_complete")

        elif self._state == State.HANGUP:
            await self.session.hangup()

    async def _play_greeting(self, pipeline: "VoicePipeline") -> None:
        """Play welcome greeting.

        If a route_result is set (direct-dial), applies the route to the
        session and plays the feature-specific greeting. Invalid numbers
        hear the "not in service" message and go to GOODBYE.
        """
        if self._route_result and self._route_result.entry_type == "invalid":
            # Not-in-service recording, then hang up
            self.transition_to(State.SPEAKING, "play_not_in_service")
            await pipeline.speak(self.session, DEFAULT_GREETING_NOT_IN_SERVICE)
            self.transition_to(State.GOODBYE, "invalid_number")
            return

        if self._route_result and self._route_result.is_direct_dial:
            # Apply the direct-dial route to the session
            self._apply_route(self._route_result)

            # Play feature-specific greeting
            greeting = _get_greeting(self._route_result.feature)
            self.transition_to(State.SPEAKING, "play_greeting")
            await pipeline.speak(self.session, greeting)
            self.transition_to(State.LISTENING, "greeting_complete")
            return

        # Default operator greeting
        greeting = (
            "Welcome to the AI Payphone! "
            "I'm your operator. You can talk to me naturally, "
            "or dial a number for specific services. "
            "Press star at any time to return to this menu. "
            "How can I help you today?"
        )

        self.transition_to(State.SPEAKING, "play_greeting")
        await pipeline.speak(self.session, greeting)
        self.transition_to(State.LISTENING, "greeting_complete")

    async def _handle_main_menu(self, pipeline: "VoicePipeline") -> None:
        """Handle main menu state."""
        # Check for DTMF input
        if self.session.protocol.has_dtmf():
            digit = await self.session.protocol.read_dtmf(timeout=0.1)
            if digit:
                await self._handle_dtmf(digit, pipeline)
                return

        # Otherwise listen for speech
        self.transition_to(State.LISTENING, "awaiting_input")

    async def _handle_listening(self, pipeline: "VoicePipeline") -> None:
        """Handle listening state - collect audio until speech ends."""
        # Start silence timer if not already running
        if self._silence_start is None:
            self._silence_start = time.time()

        # Check for DTMF interrupt
        if self.session.protocol.has_dtmf():
            digit = await self.session.protocol.read_dtmf(timeout=0.1)
            if digit:
                await self._handle_dtmf(digit, pipeline)
                return

        # Listen for speech
        try:
            audio, transcript = await asyncio.wait_for(
                pipeline.listen_and_transcribe(self.session),
                timeout=self.session.settings.timeouts.silence_prompt,
            )

            if transcript and transcript.strip():
                # Got speech, process it
                self._silence_start = None
                self.session.metrics.stt_calls += 1
                await self._process_transcript(transcript, pipeline)
            else:
                # No speech detected, check timeout
                elapsed = time.time() - self._silence_start
                if elapsed >= self.session.settings.timeouts.silence_prompt:
                    if not self._timeout_prompted:
                        self.transition_to(State.TIMEOUT, "silence_timeout")

        except asyncio.TimeoutError:
            # Silence timeout
            if not self._timeout_prompted:
                self.transition_to(State.TIMEOUT, "silence_timeout")

    async def _handle_processing(self, pipeline: "VoicePipeline") -> None:
        """Handle processing state - this is typically inline with listening."""
        # Processing is usually done inline in _process_transcript
        pass

    async def _process_transcript(
        self,
        transcript: str,
        pipeline: "VoicePipeline",
    ) -> None:
        """Process transcribed text and generate response.

        Args:
            transcript: User's transcribed speech.
            pipeline: Voice pipeline.
        """
        self.transition_to(State.PROCESSING, "transcript_ready")

        # Check for navigation commands
        lower_transcript = transcript.lower().strip()

        if any(word in lower_transcript for word in ["menu", "main menu", "go back"]):
            self.session.switch_feature("operator")
            await pipeline.speak(
                self.session,
                "Returning to the main menu. How can I help you?",
            )
            self.transition_to(State.LISTENING, "menu_return")
            return

        words = lower_transcript.split()
        if any(w in words for w in ["goodbye", "bye"]) or "hang up" in lower_transcript:
            self.transition_to(State.GOODBYE, "user_goodbye")
            return

        # Generate LLM response
        self.session.metrics.llm_calls += 1
        response = await pipeline.generate_response(self.session, transcript)

        # Speak response
        self.transition_to(State.SPEAKING, "response_ready")
        self.session.metrics.tts_calls += 1
        await pipeline.speak(self.session, response)

        # Check for barge-in during speech
        if self.session.barge_in_requested:
            self.transition_to(State.BARGE_IN, "user_interrupt")
        else:
            self.transition_to(State.LISTENING, "response_complete")

    async def _handle_dtmf(self, digit: str, pipeline: "VoicePipeline") -> None:
        """Handle DTMF digit input.

        Args:
            digit: DTMF digit received.
            pipeline: Voice pipeline.
        """
        logger.debug(f"DTMF received: {digit}")

        # Star returns to main menu
        if digit == "*":
            self._route_result = None
            self.session.switch_feature("operator")
            await pipeline.speak(
                self.session,
                "Returning to the main menu. How can I help you?",
            )
            self.transition_to(State.LISTENING, "menu_return")
            return

        # Pound could confirm input or have special meaning
        if digit == "#":
            # Get accumulated digits
            number = self.session.get_dtmf_buffer()
            if number:
                await self._route_number(number, pipeline)
            return

        # Accumulate digit
        complete_number = self.session.add_dtmf(digit)
        if complete_number:
            await self._route_number(complete_number, pipeline)

    async def _route_number(self, number: str, pipeline: "VoicePipeline") -> None:
        """Route a dialed number to appropriate feature.

        Args:
            number: Complete dialed number.
            pipeline: Voice pipeline.
        """
        logger.info(f"Routing number: {number}")

        result = self._phone_router.route_dtmf(number)

        if result.entry_type == "invalid":
            await pipeline.speak(self.session, DEFAULT_GREETING_NOT_IN_SERVICE)
            self.transition_to(State.LISTENING, "invalid_number")
            return

        # Apply route and play greeting
        self._apply_route(result)
        self._route_result = result
        greeting = _get_greeting(result.feature)
        await pipeline.speak(self.session, greeting)
        self.transition_to(State.LISTENING, f"feature_{result.feature}")

    def _apply_route(self, result: RouteResult) -> None:
        """Apply a route result to the session.

        This is the single place where feature/persona switching happens
        for routed calls (both direct-dial and in-call DTMF).

        Args:
            result: Route result to apply.
        """
        if result.entry_type == "persona" and result.persona_key:
            self.session.switch_persona(result.persona_key)
        else:
            self.session.switch_feature(result.feature)

    async def _handle_timeout(self, pipeline: "VoicePipeline") -> None:
        """Handle silence timeout."""
        if not self._timeout_prompted:
            # First timeout - prompt user
            self._timeout_prompted = True
            await pipeline.speak(
                self.session,
                "Are you still there? Say something or press any key to continue.",
            )
            self._silence_start = time.time()
            self.transition_to(State.LISTENING, "timeout_prompt")
        else:
            # Second timeout - check if we should hang up
            if self._silence_start:
                elapsed = time.time() - self._silence_start
                if elapsed >= self.session.settings.timeouts.silence_goodbye:
                    self.transition_to(State.GOODBYE, "extended_silence")

    async def _play_goodbye(self, pipeline: "VoicePipeline") -> None:
        """Play goodbye message."""
        goodbye = (
            "Thanks for calling the AI Payphone! "
            "Have a great day. Goodbye!"
        )

        self.transition_to(State.SPEAKING, "play_goodbye")
        await pipeline.speak(self.session, goodbye)

    async def handle_timeout(self) -> None:
        """Called when a timeout occurs during listening."""
        self.transition_to(State.TIMEOUT, "timeout")

    async def handle_hangup(self) -> None:
        """Called when the remote end hangs up."""
        self.transition_to(State.HANGUP, "remote_hangup")
