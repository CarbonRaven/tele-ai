"""AudioSocket protocol implementation for Asterisk integration.

The AudioSocket protocol is used by Asterisk to stream bidirectional audio
over a TCP connection. This module implements the server-side protocol handler.

Protocol Format:
- Frame: [type:1byte][length:2bytes BE][payload]
- Message types:
  - UUID (0x01): Call identifier (36-byte ASCII UUID)
  - AUDIO (0x10): Audio data (signed 16-bit PCM, 8kHz mono)
  - DTMF (0x03): DTMF digit (1 byte ASCII)
  - HANGUP (0x00): Call ended
  - ERROR (0xFF): Error message
"""

__all__ = [
    "MessageType",
    "AudioSocketMessage",
    "AudioSocketConnection",
    "AudioSocketProtocol",
    "AudioSocketServer",
    "ConnectionHandler",
]

import asyncio
import logging
import struct
import uuid
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Callable, Awaitable

logger = logging.getLogger(__name__)


class MessageType(IntEnum):
    """AudioSocket message types."""

    HANGUP = 0x00
    UUID = 0x01
    DTMF = 0x03
    AUDIO = 0x10
    ERROR = 0xFF


@dataclass
class AudioSocketMessage:
    """Represents an AudioSocket protocol message."""

    type: MessageType
    payload: bytes

    @property
    def as_uuid(self) -> str | None:
        """Get payload as UUID string if message type is UUID."""
        if self.type == MessageType.UUID:
            return self.payload.decode("ascii").strip()
        return None

    @property
    def as_dtmf(self) -> str | None:
        """Get payload as DTMF digit if message type is DTMF."""
        if self.type == MessageType.DTMF:
            return self.payload.decode("ascii")
        return None

    @property
    def as_audio(self) -> bytes | None:
        """Get payload as raw audio if message type is AUDIO."""
        if self.type == MessageType.AUDIO:
            return self.payload
        return None


@dataclass
class AudioSocketConnection:
    """Represents an active AudioSocket connection."""

    reader: asyncio.StreamReader
    writer: asyncio.StreamWriter
    call_id: str | None = None
    peer_address: tuple[str, int] = field(default_factory=lambda: ("unknown", 0))

    # Maximum payload size to prevent memory exhaustion attacks
    # Audio at 8kHz 16-bit mono: 16KB/sec, so 64KB allows ~4 sec buffer
    MAX_PAYLOAD_SIZE = 65536  # 64KB

    async def read_message(self) -> AudioSocketMessage | None:
        """Read a single message from the AudioSocket stream.

        Returns:
            AudioSocketMessage or None if connection closed/error.
        """
        try:
            # Read header: type (1 byte) + length (2 bytes big-endian)
            header = await self.reader.readexactly(3)
            msg_type = MessageType(header[0])
            length = struct.unpack(">H", header[1:3])[0]

            # Validate payload size to prevent memory exhaustion
            if length > self.MAX_PAYLOAD_SIZE:
                logger.error(
                    f"Payload too large: {length} bytes (max {self.MAX_PAYLOAD_SIZE})"
                )
                return None

            # Read payload
            payload = b""
            if length > 0:
                payload = await self.reader.readexactly(length)

            return AudioSocketMessage(type=msg_type, payload=payload)

        except asyncio.CancelledError:
            # Task was cancelled - re-raise to allow proper cleanup
            raise
        except asyncio.IncompleteReadError:
            logger.debug(f"Connection closed by peer: {self.peer_address}")
            return None
        except ValueError as e:
            # Invalid message type from enum conversion
            logger.error(f"Invalid message type: {e}")
            return None
        except (ConnectionError, OSError) as e:
            # Network-related errors
            logger.error(f"Connection error reading message: {e}")
            return None
        except struct.error as e:
            # Malformed header
            logger.error(f"Malformed message header: {e}")
            return None
        except Exception as e:
            # Unexpected error - log with full traceback
            logger.exception(f"Unexpected error reading message: {e}")
            return None

    async def send_audio(self, audio_data: bytes) -> bool:
        """Send audio data to the AudioSocket stream.

        Args:
            audio_data: Raw audio bytes (signed 16-bit PCM, 8kHz mono)

        Returns:
            True if sent successfully, False otherwise.
        """
        try:
            # Build message: type (1 byte) + length (2 bytes BE) + payload
            header = struct.pack(">BH", MessageType.AUDIO, len(audio_data))
            self.writer.write(header + audio_data)
            await self.writer.drain()
            return True
        except Exception as e:
            logger.error(f"Error sending audio: {e}")
            return False

    async def send_hangup(self) -> bool:
        """Send hangup message."""
        try:
            header = struct.pack(">BH", MessageType.HANGUP, 0)
            self.writer.write(header)
            await self.writer.drain()
            return True
        except Exception as e:
            logger.error(f"Error sending hangup: {e}")
            return False

    async def close(self) -> None:
        """Close the connection."""
        try:
            self.writer.close()
            await self.writer.wait_closed()
        except Exception as e:
            logger.debug(f"Error closing connection: {e}")


# Type alias for connection handler callback
ConnectionHandler = Callable[["AudioSocketConnection"], Awaitable[None]]


class AudioSocketProtocol:
    """High-level AudioSocket protocol handler for a single connection."""

    # Queue size limits to prevent unbounded memory growth
    # Audio queue: ~100 chunks at 20ms each = 2 seconds of buffered audio
    # DTMF queue: 32 digits should be more than enough for any input sequence
    AUDIO_QUEUE_MAXSIZE = 100
    DTMF_QUEUE_MAXSIZE = 32

    def __init__(self, connection: AudioSocketConnection):
        self.connection = connection
        self._audio_queue: asyncio.Queue[bytes] = asyncio.Queue(
            maxsize=self.AUDIO_QUEUE_MAXSIZE
        )
        self._dtmf_queue: asyncio.Queue[str] = asyncio.Queue(
            maxsize=self.DTMF_QUEUE_MAXSIZE
        )
        self._running = False
        self._read_task: asyncio.Task | None = None

    @property
    def call_id(self) -> str | None:
        """Get the call UUID."""
        return self.connection.call_id

    async def start(self) -> bool:
        """Start the protocol handler, wait for UUID message.

        Returns:
            True if UUID received and handler started, False otherwise.
        """
        # First message should be UUID
        msg = await self.connection.read_message()
        if msg is None or msg.type != MessageType.UUID:
            logger.error("Expected UUID message, connection failed")
            return False

        self.connection.call_id = msg.as_uuid
        logger.info(f"Call started: {self.connection.call_id}")

        # Start background reader
        self._running = True
        self._read_task = asyncio.create_task(self._reader_loop())
        return True

    async def stop(self) -> None:
        """Stop the protocol handler and clean up."""
        self._running = False
        if self._read_task:
            self._read_task.cancel()
            try:
                await self._read_task
            except asyncio.CancelledError:
                pass
        await self.connection.close()
        logger.info(f"Call ended: {self.connection.call_id}")

    async def _reader_loop(self) -> None:
        """Background task to read messages and dispatch to queues."""
        while self._running:
            msg = await self.connection.read_message()
            if msg is None:
                self._running = False
                break

            if msg.type == MessageType.AUDIO:
                try:
                    self._audio_queue.put_nowait(msg.payload)
                except asyncio.QueueFull:
                    try:
                        self._audio_queue.get_nowait()  # Drop oldest
                    except asyncio.QueueEmpty:
                        pass
                    try:
                        self._audio_queue.put_nowait(msg.payload)
                    except asyncio.QueueFull:
                        logger.warning("Audio queue full, dropping incoming chunk")
            elif msg.type == MessageType.DTMF:
                digit = msg.as_dtmf
                if digit:
                    logger.debug(f"DTMF received: {digit}")
                    try:
                        self._dtmf_queue.put_nowait(digit)
                    except asyncio.QueueFull:
                        logger.warning("DTMF queue full, dropping digit")
            elif msg.type == MessageType.HANGUP:
                logger.info("Hangup received")
                self._running = False
                break
            elif msg.type == MessageType.ERROR:
                logger.error(f"Error from Asterisk: {msg.payload.decode()}")
                self._running = False
                break

    async def read_audio(self, timeout: float | None = None) -> bytes | None:
        """Read next audio chunk from the queue.

        Args:
            timeout: Optional timeout in seconds.

        Returns:
            Audio bytes or None if timeout/hangup.
        """
        try:
            if timeout:
                return await asyncio.wait_for(self._audio_queue.get(), timeout)
            return await self._audio_queue.get()
        except asyncio.TimeoutError:
            return None
        except asyncio.CancelledError:
            return None

    async def read_dtmf(self, timeout: float | None = None) -> str | None:
        """Read next DTMF digit from the queue.

        Args:
            timeout: Optional timeout in seconds.

        Returns:
            DTMF digit or None if timeout.
        """
        try:
            if timeout:
                return await asyncio.wait_for(self._dtmf_queue.get(), timeout)
            return await self._dtmf_queue.get()
        except asyncio.TimeoutError:
            return None
        except asyncio.CancelledError:
            return None

    def has_dtmf(self) -> bool:
        """Check if DTMF digits are available."""
        return not self._dtmf_queue.empty()

    async def send_audio(self, audio_data: bytes) -> bool:
        """Send audio data to caller."""
        return await self.connection.send_audio(audio_data)

    async def hangup(self) -> None:
        """End the call."""
        await self.connection.send_hangup()
        await self.stop()

    @property
    def is_active(self) -> bool:
        """Check if the connection is still active."""
        return self._running


class AudioSocketServer:
    """TCP server for handling AudioSocket connections from Asterisk."""

    def __init__(
        self,
        host: str = "0.0.0.0",
        port: int = 9092,
        handler: ConnectionHandler | None = None,
    ):
        self.host = host
        self.port = port
        self.handler = handler
        self._server: asyncio.Server | None = None
        self._connections: dict[str, asyncio.Task] = {}
        self._connections_lock = asyncio.Lock()

    def set_handler(self, handler: ConnectionHandler) -> None:
        """Set the connection handler callback."""
        self.handler = handler

    async def start(self) -> None:
        """Start the AudioSocket server."""
        self._server = await asyncio.start_server(
            self._handle_connection,
            self.host,
            self.port,
        )
        addrs = ", ".join(str(sock.getsockname()) for sock in self._server.sockets)
        logger.info(f"AudioSocket server listening on {addrs}")

    async def stop(self) -> None:
        """Stop the server and close all connections."""
        # Cancel all active connection handler tasks
        async with self._connections_lock:
            for conn_id, task in self._connections.items():
                if not task.done():
                    task.cancel()
                    logger.debug(f"Cancelling connection handler: {conn_id}")

            # Wait for all tasks to complete with timeout
            if self._connections:
                tasks = list(self._connections.values())
                done, pending = await asyncio.wait(tasks, timeout=5.0)
                for task in pending:
                    logger.warning(f"Connection handler did not terminate gracefully")

            self._connections.clear()

        # Stop server
        if self._server:
            self._server.close()
            await self._server.wait_closed()
            logger.info("AudioSocket server stopped")

    async def _handle_connection(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
    ) -> None:
        """Handle a new incoming connection."""
        peer = writer.get_extra_info("peername")
        logger.info(f"New connection from {peer}")

        connection = AudioSocketConnection(
            reader=reader,
            writer=writer,
            peer_address=peer or ("unknown", 0),
        )

        # If no handler is set, just log and close
        if self.handler is None:
            logger.warning("No handler set, closing connection")
            await connection.close()
            return

        # Generate unique connection ID for tracking
        conn_id = f"{peer[0]}:{peer[1]}:{id(connection)}" if peer else f"unknown:{id(connection)}"

        # Track this connection's handler task
        current_task = asyncio.current_task()
        async with self._connections_lock:
            self._connections[conn_id] = current_task

        try:
            await self.handler(connection)
        except asyncio.CancelledError:
            logger.info(f"Connection handler cancelled: {conn_id}")
            raise
        except Exception as e:
            logger.exception(f"Error in connection handler: {e}")
        finally:
            # Remove from tracking and close connection
            async with self._connections_lock:
                self._connections.pop(conn_id, None)
            await connection.close()
            logger.debug(f"Connection closed: {conn_id}")

    async def serve_forever(self) -> None:
        """Run the server until cancelled."""
        if self._server is None:
            await self.start()
        async with self._server:
            await self._server.serve_forever()
