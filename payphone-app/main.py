#!/usr/bin/env python3
"""AI Payphone Application - Main Entry Point.

This is the entry point for the AI Payphone voice pipeline application.
It starts the AudioSocket server and handles incoming calls from Asterisk.
"""

import asyncio
import logging
import signal
import sys

from config import get_settings
from core.audiosocket import AudioSocketServer, AudioSocketConnection, AudioSocketProtocol

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)


class PayphoneApplication:
    """Main application class for the AI Payphone."""

    def __init__(self):
        self.settings = get_settings()
        self.server = AudioSocketServer(
            host=self.settings.audio.audiosocket_host,
            port=self.settings.audio.audiosocket_port,
        )
        self._shutdown_event = asyncio.Event()

        # Services (initialized lazily)
        self._vad = None
        self._stt = None
        self._llm = None
        self._tts = None
        self._pipeline = None

    async def initialize_services(self) -> None:
        """Initialize all AI services."""
        logger.info("Initializing AI services...")

        # Import services here to avoid circular imports
        from services.vad import SileroVAD
        from services.stt import WhisperSTT
        from services.llm import OllamaClient
        from services.tts import KokoroTTS
        from core.pipeline import VoicePipeline

        # Initialize VAD
        logger.info("Loading Silero VAD...")
        self._vad = SileroVAD(self.settings.vad)
        await self._vad.initialize()

        # Initialize STT
        logger.info(f"Loading Whisper model: {self.settings.stt.model_name}...")
        self._stt = WhisperSTT(self.settings.stt)
        await self._stt.initialize()

        # Initialize LLM
        logger.info(f"Connecting to Ollama: {self.settings.llm.model}...")
        self._llm = OllamaClient(self.settings.llm)
        await self._llm.initialize()

        # Initialize TTS
        logger.info("Loading Kokoro TTS...")
        self._tts = KokoroTTS(self.settings.tts)
        await self._tts.initialize()

        # Create pipeline
        self._pipeline = VoicePipeline(
            vad=self._vad,
            stt=self._stt,
            llm=self._llm,
            tts=self._tts,
            settings=self.settings,
        )

        logger.info("All services initialized successfully")

    async def handle_call(self, connection: AudioSocketConnection) -> None:
        """Handle an incoming call.

        This is the main call handler that creates a protocol handler
        and manages the voice interaction loop.
        """
        protocol = AudioSocketProtocol(connection)

        # Wait for UUID (call identifier)
        if not await protocol.start():
            logger.error("Failed to start protocol handler")
            return

        call_id = protocol.call_id
        logger.info(f"Handling call: {call_id}")

        try:
            # Import session manager
            from core.session import Session, SessionManager
            from core.state_machine import StateMachine, State

            # Create session for this call
            session = Session(
                call_id=call_id,
                protocol=protocol,
                settings=self.settings,
            )

            # Create state machine
            state_machine = StateMachine(session)

            # Run the conversation loop
            await self._run_conversation(session, state_machine)

        except asyncio.CancelledError:
            logger.info(f"Call cancelled: {call_id}")
        except Exception as e:
            logger.exception(f"Error handling call {call_id}: {e}")
        finally:
            await protocol.stop()
            logger.info(f"Call completed: {call_id}")

    async def _run_conversation(self, session, state_machine) -> None:
        """Run the main conversation loop for a call."""
        from core.state_machine import State

        # Main conversation loop - state machine handles greeting via IDLE -> GREETING
        while session.is_active and state_machine.state != State.HANGUP:
            try:
                # Process based on current state
                await state_machine.process(self._pipeline)

            except asyncio.TimeoutError:
                # Handle silence timeout
                if state_machine.state == State.LISTENING:
                    await state_machine.handle_timeout()
            except Exception as e:
                logger.error(f"Error in conversation loop: {e}")
                break

    async def start(self) -> None:
        """Start the application."""
        logger.info("Starting AI Payphone application...")

        # Set log level from settings
        if self.settings.debug:
            logging.getLogger().setLevel(logging.DEBUG)
        else:
            logging.getLogger().setLevel(getattr(logging, self.settings.log_level))

        # Auto-discover features
        from features.registry import FeatureRegistry
        FeatureRegistry.auto_discover()
        logger.info(f"Registered features: {list(FeatureRegistry.list_features().keys())}")

        # Initialize services
        await self.initialize_services()

        # Set up connection handler
        self.server.set_handler(self.handle_call)

        # Start server
        await self.server.start()
        logger.info(
            f"AudioSocket server listening on "
            f"{self.settings.audio.audiosocket_host}:{self.settings.audio.audiosocket_port}"
        )

    async def stop(self) -> None:
        """Stop the application."""
        logger.info("Shutting down AI Payphone application...")
        await self.server.stop()

        # Clean up services
        if self._vad:
            await self._vad.cleanup()
        if self._stt:
            await self._stt.cleanup()
        if self._llm:
            await self._llm.cleanup()
        if self._tts:
            await self._tts.cleanup()

        logger.info("Shutdown complete")

    async def run(self) -> None:
        """Run the application until shutdown."""
        await self.start()

        # Wait for shutdown signal
        await self._shutdown_event.wait()

        await self.stop()

    def shutdown(self) -> None:
        """Signal the application to shut down."""
        self._shutdown_event.set()


async def main() -> None:
    """Main entry point."""
    app = PayphoneApplication()

    # Set up signal handlers
    loop = asyncio.get_running_loop()

    def signal_handler():
        logger.info("Received shutdown signal")
        app.shutdown()

    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, signal_handler)

    try:
        await app.run()
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        app.shutdown()
        await app.stop()


if __name__ == "__main__":
    asyncio.run(main())
