"""Voice pipeline orchestration.

Coordinates the flow: VAD → STT → LLM → TTS
Handles audio conversion, streaming, and telephone filtering.
"""

import asyncio
import logging
import time
from pathlib import Path
from typing import TYPE_CHECKING, AsyncIterator, Callable

import numpy as np
import soundfile as sf
from numpy.typing import NDArray

from config.settings import Settings
from core.audio_processor import AudioProcessor, AudioBuffer
from services.vad import SileroVAD, SpeechState
from services.stt import WhisperSTT
from services.llm import OllamaClient, SentenceBuffer, ConversationContext
from services.tts import KokoroTTS, get_voice_for_feature

if TYPE_CHECKING:
    from core.session import Session
    from core.audiosocket import AudioSocketProtocol

logger = logging.getLogger(__name__)


class VoicePipeline:
    """Orchestrates the complete voice processing pipeline.

    Flow:
    1. Audio in (8kHz) → Resample (16kHz) → VAD → Buffer speech
    2. Speech end → STT → Transcript
    3. Transcript → LLM (streaming) → Sentence buffer
    4. Sentences → TTS → Audio (24kHz)
    5. Audio → Resample (8kHz) → Telephone filter → Send
    """

    def __init__(
        self,
        vad: SileroVAD,
        stt: WhisperSTT,
        llm: OllamaClient,
        tts: KokoroTTS,
        settings: Settings,
    ):
        self.vad = vad
        self.stt = stt
        self.llm = llm
        self.tts = tts
        self.settings = settings

        # Audio processor for conversions
        self.audio_processor = AudioProcessor(settings.audio)

    async def listen_and_transcribe(
        self,
        session: "Session",
    ) -> tuple[NDArray[np.float32] | None, str | None]:
        """Listen for speech and transcribe it.

        Uses the session's exclusive VAD model from the pool for lock-free
        inference. If barge-in audio was buffered during TTS playback, it is
        pre-loaded into the audio buffer so the start of the utterance is preserved.

        Args:
            session: Current call session.

        Returns:
            Tuple of (audio_samples, transcript) or (None, None) if no speech.
        """
        protocol = session.protocol
        audio_buffer = AudioBuffer(sample_rate=16000)

        # Reset per-session VAD state for new utterance
        session.reset_vad_state()

        speech_started = False

        # Pre-load barge-in audio if available (preserves start of utterance)
        if session.barge_in_audio:
            for chunk in session.barge_in_audio:
                audio_buffer.add(chunk)
            speech_started = True
            logger.debug(
                f"Pre-loaded {len(session.barge_in_audio)} barge-in chunks "
                f"(call {session.call_id})"
            )
            session.barge_in_audio = None

        # Max utterance duration from settings to prevent runaway recordings
        max_duration_samples = self.settings.vad.max_utterance_seconds * 16000

        # Use session's exclusive VAD model if available, else fall back to shared
        vad_model = session.vad_model

        while protocol.is_active and audio_buffer.num_samples < max_duration_samples:
            # Check for barge-in request (user pressed key during playback)
            if session.barge_in_requested:
                break

            # Read audio chunk from Asterisk
            audio_bytes = await protocol.read_audio(timeout=0.5)
            if audio_bytes is None:
                if not speech_started:
                    # No audio and no speech yet - timeout
                    return None, None
                # No more audio but we had speech - process what we have
                break

            # Process audio: 8kHz bytes → 16kHz float32
            try:
                audio_float = self.audio_processor.process_for_stt(audio_bytes)
            except Exception as e:
                logger.warning(f"Corrupt audio chunk (call {session.call_id}): {e}")
                continue

            # Run VAD — use session's exclusive model (no lock) if available
            if vad_model is not None:
                vad_result = await vad_model.process_chunk(
                    audio_float,
                    sample_rate=16000,
                    session_state=session.vad_state,
                )
            else:
                vad_result = await self.vad.process_chunk(
                    audio_float,
                    sample_rate=16000,
                    session_state=session.vad_state,
                )

            if vad_result.state == SpeechState.SPEECH_START:
                speech_started = True
                audio_buffer.add(audio_float)
                logger.debug(f"Speech started (call {session.call_id})")

            elif vad_result.state == SpeechState.SPEECH:
                if speech_started:
                    audio_buffer.add(audio_float)

            elif vad_result.state == SpeechState.SPEECH_END:
                if speech_started:
                    # Add final chunk with padding
                    audio_buffer.add(audio_float)
                    logger.debug(
                        f"Speech ended (call {session.call_id}), "
                        f"duration: {audio_buffer.get_duration_ms():.0f}ms"
                    )
                    break

        # If no speech detected, return early
        if audio_buffer.is_empty:
            return None, None

        # Transcribe
        audio = audio_buffer.get_all()
        session.metrics.total_speech_duration_ms += audio_buffer.get_duration_ms()

        result = await self.stt.transcribe(audio, sample_rate=16000)

        if result.is_empty:
            logger.debug("Transcription empty")
            return audio, None

        logger.info(f"Transcribed: '{result.text}' (confidence: {result.confidence:.2f})")
        return audio, result.text

    async def generate_response(
        self,
        session: "Session",
        transcript: str,
    ) -> str:
        """Generate LLM response for user input.

        Args:
            session: Current call session.
            transcript: User's transcribed speech.

        Returns:
            Generated response text.
        """
        response = await self.llm.generate(
            prompt=transcript,
            context=session.context,
        )

        logger.info(
            f"LLM response ({response.generation_time_ms:.0f}ms): "
            f"'{response.text[:100]}...'" if len(response.text) > 100 else f"'{response.text}'"
        )

        return response.text

    async def _monitor_barge_in(self, session: "Session") -> None:
        """Monitor for DTMF and voice input during speech playback.

        Runs while TTS audio is being sent. Checks for:
        1. DTMF keypresses (existing behavior)
        2. Voice activity via the session's exclusive VAD model

        Voice barge-in uses a higher threshold (barge_in_threshold) to
        reduce false positives from echo/sidetone. When speech is detected,
        the triggering audio chunks are buffered in session.barge_in_audio
        so listen_and_transcribe() can preserve the start of the utterance.

        Args:
            session: Current call session.
        """
        vad_model = session.vad_model
        voice_barge_in = (
            self.settings.vad.barge_in_enabled
            and vad_model is not None
        )
        barge_in_threshold = self.settings.vad.barge_in_threshold

        # Local accumulator for pre-trigger audio while speech_samples is building
        pending_chunks: list[np.ndarray] = []

        # Use a dedicated VAD state for barge-in detection (separate from listen state)
        barge_in_vad_state = self.vad.create_session_state()

        while session.is_speaking and session.is_active:
            # 1. Check DTMF queue
            if session.protocol.has_dtmf():
                session.request_barge_in()
                logger.debug("DTMF detected during speech - requesting barge-in")
                break

            # 2. Check for voice barge-in
            if voice_barge_in:
                audio_bytes = await session.protocol.read_audio(timeout=0.05)
                if audio_bytes is not None:
                    try:
                        audio_float = self.audio_processor.process_for_stt(audio_bytes)
                    except Exception:
                        continue

                    vad_result = await vad_model.process_chunk(
                        audio_float,
                        sample_rate=16000,
                        session_state=barge_in_vad_state,
                        threshold_override=barge_in_threshold,
                    )

                    if vad_result.state == SpeechState.SPEECH_START:
                        # Speech confirmed — buffer all accumulated chunks + this one
                        pending_chunks.append(audio_float)
                        session.barge_in_audio = pending_chunks
                        session.request_barge_in()
                        logger.debug("Voice detected during speech - requesting barge-in")
                        break
                    elif vad_result.state == SpeechState.SILENCE:
                        # Not speech — discard any pending accumulation
                        pending_chunks.clear()
                    else:
                        # SPEECH state (pre-trigger accumulation while speech_samples builds)
                        pending_chunks.append(audio_float)
            else:
                # No voice barge-in — just poll at 50ms like the old DTMF-only monitor
                await asyncio.sleep(0.05)

    async def speak(
        self,
        session: "Session",
        text: str,
        check_barge_in: bool = True,
    ) -> bool:
        """Synthesize and play text as speech.

        Args:
            session: Current call session.
            text: Text to speak.
            check_barge_in: Whether to check for user interruption.

        Returns:
            True if playback completed, False if interrupted.
        """
        if not text or not text.strip():
            return True

        session.is_speaking = True
        session.barge_in_audio = None
        barge_in_monitor_task = None

        # Reset VAD state for clean barge-in detection
        session.reset_vad_state()

        try:
            # Start barge-in monitoring (DTMF + voice)
            if check_barge_in:
                barge_in_monitor_task = asyncio.create_task(
                    self._monitor_barge_in(session)
                )

            # Get appropriate voice for current feature/persona
            voice = get_voice_for_feature(
                feature=session.current_feature,
                persona=session.current_persona,
            )

            # Synthesize entire text
            audio = await self.tts.synthesize(text, voice=voice)

            if len(audio) == 0:
                return True

            # Process for output: 24kHz → 8kHz + telephone filter
            output_bytes = self.audio_processor.process_for_output(
                audio,
                from_rate=self.tts.sample_rate,
            )

            # Build a stop callback that checks barge-in and session state
            def _should_stop_speaking():
                if check_barge_in and session.barge_in_requested:
                    return True
                if not session.is_active:
                    return True
                return False

            success = await self.send_audio(
                session.protocol, output_bytes, should_stop=_should_stop_speaking
            )

            if not success and check_barge_in and session.barge_in_requested:
                logger.debug("Playback interrupted by barge-in")

            return success

        finally:
            session.is_speaking = False
            if barge_in_monitor_task:
                barge_in_monitor_task.cancel()
                try:
                    await barge_in_monitor_task
                except asyncio.CancelledError:
                    pass

    async def speak_streaming(
        self,
        session: "Session",
        text_generator: AsyncIterator[str],
        check_barge_in: bool = True,
    ) -> bool:
        """Synthesize and play streaming text with overlapped LLM+TTS.

        Uses a producer-consumer pattern where:
        - Producer: LLM tokens stream into sentence buffer, complete sentences queued
        - Consumer: Background task synthesizes and plays sentences concurrently

        This overlaps LLM generation with TTS synthesis, reducing latency by ~30%.

        Args:
            session: Current call session.
            text_generator: Async generator yielding text tokens.
            check_barge_in: Whether to check for user interruption.

        Returns:
            True if playback completed, False if interrupted.
        """
        session.is_speaking = True
        session.barge_in_audio = None
        barge_in_monitor_task = None

        # Reset VAD state for clean barge-in detection
        session.reset_vad_state()

        sentence_buffer = SentenceBuffer(
            min_length=self.settings.tts.min_sentence_length,
            delimiters=self.settings.tts.sentence_delimiters,
        )

        voice = get_voice_for_feature(
            feature=session.current_feature,
            persona=session.current_persona,
        )

        # Queue for sentences ready for TTS (bounded to prevent memory growth)
        sentence_queue: asyncio.Queue[str | None] = asyncio.Queue(maxsize=5)
        playback_error = False
        interrupted = False

        async def tts_consumer() -> None:
            """Background task that consumes sentences and plays them."""
            nonlocal playback_error, interrupted

            while True:
                try:
                    sentence = await sentence_queue.get()

                    # None signals end of stream
                    if sentence is None:
                        break

                    # Check for barge-in before each sentence
                    if check_barge_in and session.barge_in_requested:
                        interrupted = True
                        break

                    # Synthesize and send
                    if not await self._send_sentence(session, sentence, voice):
                        playback_error = True
                        break

                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"TTS consumer error: {e}")
                    playback_error = True
                    break

        # Start barge-in monitoring (DTMF + voice)
        if check_barge_in:
            barge_in_monitor_task = asyncio.create_task(
                self._monitor_barge_in(session)
            )

        # Start TTS consumer task
        consumer_task = asyncio.create_task(tts_consumer())

        try:
            async for token in text_generator:
                if check_barge_in and session.barge_in_requested:
                    logger.debug("Streaming interrupted by barge-in")
                    interrupted = True
                    break

                if playback_error:
                    break

                # Add token to sentence buffer
                sentence = sentence_buffer.add_token(token)

                if sentence:
                    # Queue sentence for TTS (may block briefly if queue is full)
                    await sentence_queue.put(sentence)

            # Flush remaining text
            if not interrupted and not playback_error:
                remaining = sentence_buffer.flush()
                if remaining:
                    await sentence_queue.put(remaining)

            # Signal end of stream
            await sentence_queue.put(None)

            # Wait for TTS to finish playing all queued sentences
            await consumer_task

            return not playback_error and not interrupted

        except asyncio.CancelledError:
            consumer_task.cancel()
            try:
                await consumer_task
            except asyncio.CancelledError:
                pass
            raise

        finally:
            session.is_speaking = False
            if barge_in_monitor_task:
                barge_in_monitor_task.cancel()
                try:
                    await barge_in_monitor_task
                except asyncio.CancelledError:
                    pass
            # Ensure consumer is cleaned up
            if not consumer_task.done():
                consumer_task.cancel()
                try:
                    await consumer_task
                except asyncio.CancelledError:
                    pass

    async def _send_sentence(
        self,
        session: "Session",
        sentence: str,
        voice: str,
    ) -> bool:
        """Synthesize and send a single sentence.

        Args:
            session: Current call session.
            sentence: Sentence to speak.
            voice: Voice to use.

        Returns:
            True if sent successfully, False if interrupted or error.
        """
        if not sentence.strip():
            return True

        # Synthesize
        audio = await self.tts.synthesize(sentence, voice=voice)
        if len(audio) == 0:
            return True

        # Process for output
        output_bytes = self.audio_processor.process_for_output(
            audio,
            from_rate=self.tts.sample_rate,
        )

        # Build stop callback for mid-sentence interrupt
        def _should_stop_speaking():
            if session.barge_in_requested:
                return True
            if not session.is_active:
                return True
            return False

        # Send with interrupt support
        return await self.send_audio(
            session.protocol, output_bytes, should_stop=_should_stop_speaking
        )

    async def generate_and_speak_streaming(
        self,
        session: "Session",
        transcript: str,
        check_barge_in: bool = True,
    ) -> tuple[str, bool]:
        """Generate LLM response and speak it with streaming overlap.

        Replaces the sequential generate_response() + speak() pair.
        Streams LLM tokens into speak_streaming() so TTS starts on the
        first complete sentence while the LLM is still generating.

        Args:
            session: Current call session.
            transcript: User's transcribed speech.
            check_barge_in: Whether to check for user interruption.

        Returns:
            Tuple of (full_response_text, playback_completed).
        """
        # Collect all tokens for logging and context (generate_streaming
        # already manages context.add_user_message / add_assistant_message)
        collected_tokens: list[str] = []
        first_sentence_time: float | None = None
        stream_start = time.perf_counter()

        text_generator = self.llm.generate_streaming(
            prompt=transcript,
            context=session.context,
        )

        async def collecting_generator() -> AsyncIterator[str]:
            """Wraps the LLM stream to collect tokens and track first sentence."""
            nonlocal first_sentence_time
            async for token in text_generator:
                collected_tokens.append(token)
                yield token

        try:
            completed = await self.speak_streaming(
                session,
                collecting_generator(),
                check_barge_in=check_barge_in,
            )
        finally:
            # Close the LLM stream promptly (terminates Ollama HTTP connection)
            await text_generator.aclose()

        full_response = "".join(collected_tokens)

        # Record first-sentence latency (approximate: time to stream enough
        # tokens for the first TTS sentence, measured from stream start)
        elapsed_ms = (time.perf_counter() - stream_start) * 1000
        session.metrics.first_sentence_latency_ms = elapsed_ms

        logger.info(
            f"Streaming response ({elapsed_ms:.0f}ms total): "
            f"'{full_response[:80]}...'" if len(full_response) > 80
            else f"Streaming response ({elapsed_ms:.0f}ms total): '{full_response}'"
        )

        return full_response, completed

    async def send_audio(
        self,
        protocol: "AudioSocketProtocol",
        audio_bytes: bytes,
        should_stop: Callable[[], bool] | None = None,
    ) -> bool:
        """Send audio bytes to the caller.

        Args:
            protocol: AudioSocket protocol handler.
            audio_bytes: Processed audio bytes (8kHz, 16-bit PCM).
            should_stop: Optional callback that returns True to abort playback.

        Returns:
            True if sent successfully, False if interrupted or error.
        """
        # Calculate chunk duration for pacing
        chunk_size = self.settings.audio.chunk_size
        chunk_duration_sec = chunk_size / (self.settings.audio.output_sample_rate * 2)

        # Track timing for backpressure-aware pacing
        playback_start = time.perf_counter()
        chunks_sent = 0

        for chunk in self.audio_processor.chunk_audio(audio_bytes):
            if should_stop and should_stop():
                return False

            if not protocol.is_active:
                return False

            success = await protocol.send_audio(chunk)
            if not success:
                return False

            chunks_sent += 1

            # Backpressure-aware pacing
            expected_elapsed = chunks_sent * chunk_duration_sec
            actual_elapsed = time.perf_counter() - playback_start
            sleep_time = expected_elapsed - actual_elapsed

            if sleep_time > 0:
                await asyncio.sleep(sleep_time)
            elif sleep_time < -0.5:
                # We're more than 500ms behind - network is congested
                logger.warning(
                    f"Audio send falling behind by {-sleep_time:.2f}s, "
                    "network may be congested"
                )

        return True

    async def play_sound(
        self,
        session: "Session",
        sound_name: str,
    ) -> bool:
        """Play a pre-recorded sound effect.

        Args:
            session: Current call session.
            sound_name: Name of sound file (without extension).

        Returns:
            True if played successfully.
        """
        sound_path = Path(__file__).parent.parent / "audio" / "sounds" / f"{sound_name}.wav"
        if not sound_path.exists():
            logger.warning(f"Sound not found: {sound_path}")
            return False

        # Load audio
        audio, sample_rate = sf.read(str(sound_path), dtype="float32")

        # Convert to mono if stereo
        if len(audio.shape) > 1:
            audio = audio.mean(axis=1)

        # Process for output
        output_bytes = self.audio_processor.process_for_output(
            audio,
            from_rate=sample_rate,
        )

        return await self.send_audio(session.protocol, output_bytes)
