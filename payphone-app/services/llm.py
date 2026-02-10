"""Language Model service using Ollama.

Provides async interface to local LLMs via Ollama with streaming support
for low-latency responses. Default: Llama 3.2 3B for best latency on Pi 5.
Alternative: Ministral 8B for better conversational quality.
"""

__all__ = [
    "Message",
    "LLMResponse",
    "ConversationContext",
    "OllamaClient",
    "SentenceBuffer",
]

import asyncio
import logging
import re
import time
from dataclasses import dataclass, field
from typing import AsyncIterator

from config.settings import LLMSettings
from config.prompts import get_system_prompt

logger = logging.getLogger(__name__)


@dataclass
class Message:
    """Chat message."""

    role: str  # "system", "user", or "assistant"
    content: str


@dataclass
class LLMResponse:
    """Response from LLM generation."""

    text: str
    tokens_generated: int
    generation_time_ms: float
    model: str


@dataclass
class ConversationContext:
    """Maintains conversation history for a session.

    Optimized to avoid unnecessary list copies during history trimming.
    System messages are preserved at the front of the list.
    """

    messages: list[Message] = field(default_factory=list)
    max_history: int = 10  # Keep last N exchanges (user + assistant pairs)
    _non_system_count: int = field(default=0, repr=False)

    def add_user_message(self, content: str) -> None:
        """Add a user message to history."""
        self.messages.append(Message(role="user", content=content))
        self._non_system_count += 1
        self._trim_history()

    def add_assistant_message(self, content: str) -> None:
        """Add an assistant message to history."""
        self.messages.append(Message(role="assistant", content=content))
        self._non_system_count += 1
        self._trim_history()

    def _trim_history(self) -> None:
        """Keep only the last max_history exchanges (excluding system).

        Optimized to only rebuild list when actually needed, and tracks
        non-system count incrementally to avoid O(n) counting.
        """
        max_non_system = self.max_history * 2  # pairs of user + assistant

        if self._non_system_count <= max_non_system:
            return  # No trimming needed

        # Find where non-system messages start
        system_end_idx = next(
            (i for i, m in enumerate(self.messages) if m.role != "system"),
            len(self.messages),
        )

        # All messages are system — nothing to trim
        if system_end_idx == len(self.messages):
            self._non_system_count = 0
            return

        # Keep system messages + last N non-system messages
        keep_count = max_non_system
        trim_start = len(self.messages) - keep_count
        if trim_start > system_end_idx:
            self.messages = self.messages[:system_end_idx] + self.messages[trim_start:]
            self._non_system_count = keep_count

    def get_messages_for_api(self) -> list[dict]:
        """Get messages formatted for Ollama API."""
        return [{"role": m.role, "content": m.content} for m in self.messages]

    def clear(self) -> None:
        """Clear conversation history (keeps system message if present)."""
        self.messages = [m for m in self.messages if m.role == "system"]
        self._non_system_count = 0


class OllamaClient:
    """Async client for Ollama LLM API with streaming support."""

    def __init__(self, settings: LLMSettings | None = None):
        if settings is None:
            settings = LLMSettings()
        self.settings = settings

        self._client = None
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize the Ollama client and verify connection."""
        if self._initialized:
            return

        logger.info(f"Connecting to Ollama at {self.settings.host}")

        try:
            import ollama

            # Create async client
            self._client = ollama.AsyncClient(host=self.settings.host)

            # Verify model is available
            models = await self._client.list()
            model_names = [m.model for m in models.models]

            # Check if our model (or variant) is available
            model_base = self.settings.model.split(":")[0]
            if not any(model_base in name for name in model_names):
                logger.warning(
                    f"Model {self.settings.model} not found. "
                    f"Available: {model_names}. Attempting to pull..."
                )
                await self._client.pull(self.settings.model)

            # Warm up the model
            logger.info(f"Warming up model: {self.settings.model}")
            await self._client.generate(
                model=self.settings.model,
                prompt="Hello",
                options={"num_predict": 1},
                keep_alive=self.settings.keep_alive,
            )

            self._initialized = True
            logger.info("Ollama client initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize Ollama client: {e}")
            raise

    async def cleanup(self) -> None:
        """Clean up resources."""
        self._client = None
        self._initialized = False

    async def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        context: ConversationContext | None = None,
    ) -> LLMResponse:
        """Generate a response from the LLM.

        Args:
            prompt: User prompt/question.
            system_prompt: Optional system prompt override.
            context: Optional conversation context for multi-turn.

        Returns:
            LLMResponse with generated text and metadata.
        """
        if not self._initialized:
            raise RuntimeError("LLM not initialized. Call initialize() first.")

        start_time = time.perf_counter()

        # Build messages
        messages = []

        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        if context:
            context_msgs = context.get_messages_for_api()
            if system_prompt:
                context_msgs = [m for m in context_msgs if m["role"] != "system"]
            messages.extend(context_msgs)

        # Add current prompt
        messages.append({"role": "user", "content": prompt})

        try:
            response = await asyncio.wait_for(
                self._client.chat(
                    model=self.settings.model,
                    messages=messages,
                    options={
                        "temperature": self.settings.temperature,
                        "top_p": self.settings.top_p,
                        "num_predict": self.settings.max_tokens,
                    },
                    keep_alive=self.settings.keep_alive,
                ),
                timeout=self.settings.timeout,
            )

            elapsed_ms = (time.perf_counter() - start_time) * 1000
            text = response["message"]["content"]

            # Update context if provided
            if context:
                context.add_user_message(prompt)
                context.add_assistant_message(text)

            return LLMResponse(
                text=text,
                tokens_generated=response.get("eval_count", 0),
                generation_time_ms=elapsed_ms,
                model=self.settings.model,
            )

        except asyncio.TimeoutError:
            logger.warning(f"LLM generation timed out after {self.settings.timeout}s")
            return LLMResponse(
                text="I'm sorry, I'm taking too long to think. Let me try again.",
                tokens_generated=0,
                generation_time_ms=self.settings.timeout * 1000,
                model=self.settings.model,
            )

    async def generate_streaming(
        self,
        prompt: str,
        system_prompt: str | None = None,
        context: ConversationContext | None = None,
    ) -> AsyncIterator[str]:
        """Generate a streaming response from the LLM.

        Args:
            prompt: User prompt/question.
            system_prompt: Optional system prompt override.
            context: Optional conversation context.

        Yields:
            Token strings as they're generated.
        """
        if not self._initialized:
            raise RuntimeError("LLM not initialized. Call initialize() first.")

        # Build messages
        messages = []

        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        if context:
            context_msgs = context.get_messages_for_api()
            if system_prompt:
                context_msgs = [m for m in context_msgs if m["role"] != "system"]
            messages.extend(context_msgs)

        messages.append({"role": "user", "content": prompt})

        # Add user message to context before streaming so it's preserved
        # even if the stream fails (timeout, connection error, etc.)
        if context:
            context.add_user_message(prompt)

        # Use list for O(n) collection instead of O(n²) string concatenation
        response_parts: list[str] = []
        last_token_time = time.perf_counter()
        is_first_token = True

        try:
            stream = await asyncio.wait_for(
                self._client.chat(
                    model=self.settings.model,
                    messages=messages,
                    stream=True,
                    options={
                        "temperature": self.settings.temperature,
                        "top_p": self.settings.top_p,
                        "num_predict": self.settings.max_tokens,
                    },
                    keep_alive=self.settings.keep_alive,
                ),
                timeout=self.settings.first_token_timeout,
            )

            async for part in stream:
                current_time = time.perf_counter()

                # Use different timeout for first token vs subsequent tokens
                # First token takes longer due to prompt processing/model loading
                if is_first_token:
                    token_timeout = self.settings.first_token_timeout
                else:
                    token_timeout = self.settings.inter_token_timeout

                # Check for token timeout (no tokens received for too long)
                if current_time - last_token_time > token_timeout:
                    logger.warning(
                        f"Streaming timed out after {current_time - last_token_time:.1f}s "
                        f"({'first token' if is_first_token else 'between tokens'})"
                    )
                    yield " I need to pause here."
                    break

                last_token_time = current_time
                is_first_token = False
                token = part["message"]["content"]
                response_parts.append(token)
                yield token

            # Add assistant message only after successful completion
            if context and response_parts:
                context.add_assistant_message("".join(response_parts))

        except asyncio.TimeoutError:
            logger.warning(f"LLM streaming timed out after {self.settings.timeout}s")
            yield "I'm sorry, I'm taking too long to respond."

        except asyncio.CancelledError:
            # Task was cancelled - re-raise to allow proper cleanup
            raise

        except ConnectionError as e:
            logger.error(f"Connection error in streaming generation: {e}")
            yield "I'm sorry, I lost connection. Please try again."

        except (KeyError, TypeError, ValueError) as e:
            # Malformed response from Ollama
            logger.error(f"Invalid response in streaming generation: {e}")
            yield "I'm sorry, I received an invalid response. Please try again."

        except Exception as e:
            # Log unexpected errors with full context for debugging
            logger.exception(f"Unexpected error in streaming generation: {e}")
            yield "I'm sorry, I encountered an error. Please try again."

    async def generate_for_feature(
        self,
        prompt: str,
        feature: str,
        context: ConversationContext | None = None,
    ) -> LLMResponse:
        """Generate a response using a feature-specific system prompt.

        Args:
            prompt: User prompt/question.
            feature: Feature name (e.g., "jokes", "trivia").
            context: Optional conversation context.

        Returns:
            LLMResponse with generated text.
        """
        system_prompt = get_system_prompt(feature=feature)
        return await self.generate(prompt, system_prompt, context)

    async def generate_for_persona(
        self,
        prompt: str,
        persona: str,
        context: ConversationContext | None = None,
    ) -> LLMResponse:
        """Generate a response using a persona-specific system prompt.

        Args:
            prompt: User prompt/question.
            persona: Persona name (e.g., "detective", "grandma").
            context: Optional conversation context.

        Returns:
            LLMResponse with generated text.
        """
        system_prompt = get_system_prompt(persona=persona)
        return await self.generate(prompt, system_prompt, context)

    async def health_check(self) -> bool:
        """Check if Ollama is reachable and model is loaded.

        Returns:
            True if healthy, False otherwise.
        """
        try:
            if not self._initialized:
                return False

            # Quick generation test
            response = await asyncio.wait_for(
                self._client.generate(
                    model=self.settings.model,
                    prompt="Hi",
                    options={"num_predict": 1},
                ),
                timeout=5.0,
            )
            return bool(response.get("response"))

        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False


class SentenceBuffer:
    """Buffer for collecting LLM tokens into complete sentences for TTS.

    This enables streaming TTS by yielding complete sentences as they
    form from the token stream.

    Uses incremental search position tracking to achieve O(n) total complexity
    instead of O(n²) from searching the entire buffer on each token.
    """

    def __init__(
        self,
        min_length: int = 10,
        delimiters: str = ".!?,",
    ):
        self.min_length = min_length
        self.delimiters = delimiters
        # Pre-compile regex for efficient sentence boundary detection
        escaped_delims = re.escape(delimiters)
        self._sentence_pattern = re.compile(f"[{escaped_delims}]")
        self._buffer = ""

    def add_token(self, token: str) -> str | None:
        """Add a token and return a sentence if one is complete.

        Args:
            token: Token string from LLM.

        Returns:
            Complete sentence if available, None otherwise.
        """
        # Track position before adding token - search from just before new content
        # to catch delimiters at word boundaries
        search_from = max(0, len(self._buffer) - 1)
        self._buffer += token

        # Search only from where new content was added (O(token_len) not O(buffer_len))
        match = self._sentence_pattern.search(self._buffer, search_from)
        if match and match.end() >= self.min_length:
            # Extract sentence up to and including delimiter
            sentence = self._buffer[: match.end()].strip()
            remainder = self._buffer[match.end() :].lstrip()

            if len(sentence) >= self.min_length:
                self._buffer = remainder
                return sentence

            # Sentence too short after strip — prepend back to buffer
            # so the text is preserved and becomes part of the next sentence
            self._buffer = sentence + " " + remainder if remainder else sentence

        return None

    def flush(self) -> str | None:
        """Get any remaining text in the buffer.

        Returns:
            Remaining text or None if empty.
        """
        if self._buffer.strip():
            result = self._buffer.strip()
            self._buffer = ""
            return result
        return None

    def clear(self) -> None:
        """Clear the buffer."""
        self._buffer = ""
