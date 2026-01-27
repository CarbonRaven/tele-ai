"""Session management for call handling.

Each incoming call gets a Session that tracks:
- Call identifier and metadata
- Current state and feature
- Conversation history
- Audio buffers and timing
"""

__all__ = [
    "SessionMetrics",
    "Session",
    "SessionManager",
]

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from config.prompts import get_system_prompt
from config.settings import Settings
from services.llm import ConversationContext, Message

if TYPE_CHECKING:
    from core.audiosocket import AudioSocketProtocol

logger = logging.getLogger(__name__)


@dataclass
class SessionMetrics:
    """Metrics for a single call session."""

    start_time: float = field(default_factory=time.time)
    end_time: float | None = None
    total_speech_duration_ms: float = 0.0
    total_silence_duration_ms: float = 0.0
    stt_calls: int = 0
    llm_calls: int = 0
    tts_calls: int = 0
    dtmf_digits: int = 0
    features_used: list[str] = field(default_factory=list)

    @property
    def duration_seconds(self) -> float:
        """Get total call duration in seconds."""
        end = self.end_time or time.time()
        return end - self.start_time

    def add_feature(self, feature: str) -> None:
        """Record feature usage."""
        if feature not in self.features_used:
            self.features_used.append(feature)


@dataclass
class Session:
    """Represents an active call session.

    Manages all state and context for a single phone call.
    """

    call_id: str
    protocol: "AudioSocketProtocol"
    settings: Settings

    # Session state
    current_feature: str = "operator"
    current_persona: str | None = None
    is_active: bool = True

    # Conversation context
    context: ConversationContext = field(default_factory=ConversationContext)

    # Metrics
    metrics: SessionMetrics = field(default_factory=SessionMetrics)

    # DTMF buffer for collecting multi-digit input
    dtmf_buffer: str = ""
    dtmf_last_time: float = 0.0

    # Barge-in state
    is_speaking: bool = False
    barge_in_requested: bool = False

    def __post_init__(self):
        """Initialize session-specific state."""
        # Set up conversation context with default system prompt
        system_prompt = get_system_prompt(feature=self.current_feature)
        self.context.messages.insert(0, Message(role="system", content=system_prompt))

    async def send_audio(self, audio_bytes: bytes) -> bool:
        """Send audio to the caller.

        Args:
            audio_bytes: Raw audio bytes (8kHz, 16-bit PCM).

        Returns:
            True if sent successfully.
        """
        if not self.is_active:
            return False
        return await self.protocol.send_audio(audio_bytes)

    async def hangup(self) -> None:
        """End the call."""
        self.is_active = False
        self.metrics.end_time = time.time()
        await self.protocol.hangup()

    # Valid DTMF digits and maximum buffer size
    VALID_DTMF_DIGITS = set("0123456789*#ABCD")
    MAX_DTMF_BUFFER_SIZE = 32

    def add_dtmf(self, digit: str) -> str | None:
        """Add a DTMF digit to the buffer.

        Args:
            digit: Single DTMF digit (0-9, *, #, A-D).

        Returns:
            Complete number if inter-digit timeout exceeded, None otherwise.
            Returns None if digit is invalid or buffer is full.
        """
        # Validate digit
        if not digit or digit not in self.VALID_DTMF_DIGITS:
            logger.warning(f"Invalid DTMF digit received: {digit!r}")
            return None

        current_time = time.time()
        self.metrics.dtmf_digits += 1

        # Check for inter-digit timeout
        if self.dtmf_buffer and (
            current_time - self.dtmf_last_time > self.settings.timeouts.dtmf_inter_digit
        ):
            # Return accumulated digits and start fresh
            result = self.dtmf_buffer
            self.dtmf_buffer = digit
            self.dtmf_last_time = current_time
            return result

        # Check buffer size limit to prevent memory issues
        if len(self.dtmf_buffer) >= self.MAX_DTMF_BUFFER_SIZE:
            logger.warning(f"DTMF buffer full ({self.MAX_DTMF_BUFFER_SIZE} digits), dropping oldest")
            self.dtmf_buffer = self.dtmf_buffer[1:]  # Drop oldest digit

        self.dtmf_buffer += digit
        self.dtmf_last_time = current_time
        return None

    def get_dtmf_buffer(self) -> str:
        """Get and clear the DTMF buffer."""
        result = self.dtmf_buffer
        self.dtmf_buffer = ""
        return result

    def switch_feature(self, feature: str) -> None:
        """Switch to a different feature.

        Args:
            feature: Feature name to switch to.
        """
        self.current_feature = feature
        self.current_persona = None
        self.metrics.add_feature(feature)

        # Update system prompt
        system_prompt = get_system_prompt(feature=feature)
        self._update_system_prompt(system_prompt)

        logger.info(f"Session {self.call_id}: Switched to feature '{feature}'")

    def switch_persona(self, persona: str) -> None:
        """Switch to a different persona.

        Args:
            persona: Persona name to switch to.
        """
        self.current_persona = persona
        self.metrics.add_feature(f"persona_{persona}")

        # Update system prompt
        system_prompt = get_system_prompt(persona=persona)
        self._update_system_prompt(system_prompt)

        logger.info(f"Session {self.call_id}: Switched to persona '{persona}'")

    def _update_system_prompt(self, system_prompt: str) -> None:
        """Update the system prompt in conversation context."""
        # Remove existing system message and add new one
        self.context.messages = [
            m for m in self.context.messages if m.role != "system"
        ]
        self.context.messages.insert(0, Message(role="system", content=system_prompt))

    def request_barge_in(self) -> None:
        """Request to interrupt current TTS playback."""
        if self.is_speaking:
            self.barge_in_requested = True
            logger.debug(f"Session {self.call_id}: Barge-in requested")

    def clear_barge_in(self) -> None:
        """Clear barge-in request."""
        self.barge_in_requested = False


class SessionManager:
    """Manages all active call sessions."""

    def __init__(self):
        self._sessions: dict[str, Session] = {}
        self._lock = asyncio.Lock()

    async def create_session(
        self,
        call_id: str,
        protocol: "AudioSocketProtocol",
        settings: Settings,
    ) -> Session:
        """Create a new session for an incoming call.

        Args:
            call_id: Unique call identifier.
            protocol: AudioSocket protocol handler.
            settings: Application settings.

        Returns:
            New Session instance.
        """
        async with self._lock:
            session = Session(
                call_id=call_id,
                protocol=protocol,
                settings=settings,
            )
            self._sessions[call_id] = session
            logger.info(f"Created session: {call_id}")
            return session

    def get_session(self, call_id: str) -> Session | None:
        """Get a session by call ID.

        Note: This is a simple dict lookup and doesn't require async/lock.

        Args:
            call_id: Call identifier.

        Returns:
            Session or None if not found.
        """
        return self._sessions.get(call_id)

    async def remove_session(self, call_id: str) -> None:
        """Remove a session and clean up resources.

        Args:
            call_id: Call identifier.
        """
        async with self._lock:
            if call_id in self._sessions:
                session = self._sessions.pop(call_id)
                session.is_active = False
                session.metrics.end_time = time.time()

                # Clear conversation context to free memory
                # This prevents large conversation histories from lingering
                session.context.clear()

                logger.info(
                    f"Removed session: {call_id} "
                    f"(duration: {session.metrics.duration_seconds:.1f}s)"
                )

    @property
    def active_count(self) -> int:
        """Get number of active sessions."""
        return len(self._sessions)

    def get_all_sessions(self) -> list[Session]:
        """Get all active sessions."""
        return list(self._sessions.values())
