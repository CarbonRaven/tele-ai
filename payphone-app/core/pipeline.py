"""Voice pipeline orchestration.

Coordinates the flow: VAD → STT → LLM → TTS
Handles audio conversion, streaming, and telephone filtering.
"""

import asyncio
import logging
from typing import TYPE_CHECKING

import numpy as np
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

        Args:
            session: Current call session.

        Returns:
            Tuple of (audio_samples, transcript) or (None, None) if no speech.
        """
        protocol = session.protocol
        audio_buffer = AudioBuffer(sample_rate=16000)

        # Reset VAD state for new utterance
        self.vad.reset()

        speech_started = False
        max_duration_samples = 30 * 16000  # 30 second max utterance

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
            audio_float = self.audio_processor.process_for_stt(audio_bytes)

            # Run VAD
            vad_result = await self.vad.process_chunk(audio_float, sample_rate=16000)

            if vad_result.state == SpeechState.SPEECH_START:
                speech_started = True
                audio_buffer.add(audio_float)
                logger.debug("Speech started")

            elif vad_result.state == SpeechState.SPEECH:
                if speech_started:
                    audio_buffer.add(audio_float)

            elif vad_result.state == SpeechState.SPEECH_END:
                if speech_started:
                    # Add final chunk with padding
                    audio_buffer.add(audio_float)
                    logger.debug(
                        f"Speech ended, duration: {audio_buffer.get_duration_ms():.0f}ms"
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

    async def _monitor_dtmf_for_barge_in(self, session: "Session") -> None:
        """Monitor for DTMF input during speech and trigger barge-in.

        Args:
            session: Current call session.
        """
        while session.is_speaking and session.is_active:
            if session.protocol.has_dtmf():
                session.request_barge_in()
                logger.debug("DTMF detected during speech - requesting barge-in")
                break
            await asyncio.sleep(0.05)  # Check every 50ms

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
        dtmf_monitor_task = None

        try:
            # Start DTMF monitoring if barge-in is enabled
            if check_barge_in:
                dtmf_monitor_task = asyncio.create_task(
                    self._monitor_dtmf_for_barge_in(session)
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

            # Send in chunks
            chunks = self.audio_processor.chunk_audio(output_bytes)

            for chunk in chunks:
                if check_barge_in and session.barge_in_requested:
                    logger.debug("Playback interrupted by barge-in")
                    return False

                if not session.is_active:
                    return False

                await session.send_audio(chunk)

                # Small delay to pace playback
                await asyncio.sleep(0.02)  # 20ms per chunk

            return True

        finally:
            session.is_speaking = False
            if dtmf_monitor_task:
                dtmf_monitor_task.cancel()
                try:
                    await dtmf_monitor_task
                except asyncio.CancelledError:
                    pass

    async def speak_streaming(
        self,
        session: "Session",
        text_generator,
        check_barge_in: bool = True,
    ) -> bool:
        """Synthesize and play streaming text.

        Uses sentence buffering to start TTS as soon as complete
        sentences are available from the LLM.

        Args:
            session: Current call session.
            text_generator: Async generator yielding text tokens.
            check_barge_in: Whether to check for user interruption.

        Returns:
            True if playback completed, False if interrupted.
        """
        session.is_speaking = True
        sentence_buffer = SentenceBuffer(
            min_length=self.settings.tts.min_sentence_length,
            delimiters=self.settings.tts.sentence_delimiters,
        )

        voice = get_voice_for_feature(
            feature=session.current_feature,
            persona=session.current_persona,
        )

        try:
            async for token in text_generator:
                if check_barge_in and session.barge_in_requested:
                    logger.debug("Streaming playback interrupted")
                    return False

                # Add token to sentence buffer
                sentence = sentence_buffer.add_token(token)

                if sentence:
                    # Synthesize and send complete sentence
                    if not await self._send_sentence(session, sentence, voice):
                        return False

            # Flush remaining text
            remaining = sentence_buffer.flush()
            if remaining:
                if not await self._send_sentence(session, remaining, voice):
                    return False

            return True

        finally:
            session.is_speaking = False

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
            True if sent successfully.
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

        # Send
        return await self.send_audio(session.protocol, output_bytes)

    async def send_audio(
        self,
        protocol: "AudioSocketProtocol",
        audio_bytes: bytes,
    ) -> bool:
        """Send audio bytes to the caller.

        Args:
            protocol: AudioSocket protocol handler.
            audio_bytes: Processed audio bytes (8kHz, 16-bit PCM).

        Returns:
            True if sent successfully.
        """
        chunks = self.audio_processor.chunk_audio(audio_bytes)

        for chunk in chunks:
            if not protocol.is_active:
                return False

            success = await protocol.send_audio(chunk)
            if not success:
                return False

            # Pace the sending
            await asyncio.sleep(0.02)

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
        from pathlib import Path
        import soundfile as sf

        sound_path = Path("audio/sounds") / f"{sound_name}.wav"
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
