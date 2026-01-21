"""Operator feature - default conversational AI assistant.

The operator is the main interface when no specific feature is selected.
It can answer questions, help navigate the system, and make small talk.
"""

from features.base import ConversationalFeature
from features.registry import register_feature


@register_feature
class OperatorFeature(ConversationalFeature):
    """Default operator/assistant feature.

    This is the main conversational interface that handles:
    - General questions and conversation
    - Help navigating the payphone system
    - Routing to other features based on user requests
    """

    name = "The Operator"
    dial_code = "0"
    description = "Talk to the friendly AI operator for help or general conversation"
    system_prompt_key = "operator"

    voice_triggers = [
        "operator",
        "help",
        "assistant",
        "talk",
        "chat",
        "hello",
        "hi",
    ]

    def get_greeting(self) -> str:
        """Get operator greeting."""
        return (
            "You're speaking with the operator. "
            "I can help you navigate our services or just chat. "
            "What would you like to do?"
        )

    async def handle(self, session, pipeline) -> None:
        """Handle operator conversation.

        The operator can detect intent and route to other features,
        or engage in general conversation.
        """
        from features.registry import FeatureRegistry

        # Set up operator context
        session.switch_feature(self.system_prompt_key)

        # Play greeting
        await self.on_enter(session, pipeline)

        # Conversation loop
        while session.is_active:
            # Listen for input
            audio, transcript = await pipeline.listen_and_transcribe(session)

            if transcript is None:
                continue

            # Check for feature routing
            feature_class = FeatureRegistry.get_by_voice_match(transcript)
            if feature_class and feature_class.dial_code != "0":
                # Route to requested feature
                session.switch_feature(feature_class.dial_code)
                feature = feature_class()
                await feature.handle(session, pipeline)
                # Return to operator after feature
                session.switch_feature(self.system_prompt_key)
                await pipeline.speak(
                    session,
                    "Is there anything else I can help you with?",
                )
                continue

            # Check for goodbye
            if self._is_goodbye(transcript):
                await pipeline.speak(
                    session,
                    "Thanks for calling! Have a wonderful day!",
                )
                await session.hangup()
                break

            # Regular conversation
            response = await pipeline.generate_response(session, transcript)
            await pipeline.speak(session, response)

        await self.on_exit(session)

    def _is_goodbye(self, text: str) -> bool:
        """Check if user wants to end the call."""
        lower = text.lower().strip()
        goodbye_phrases = [
            "goodbye",
            "bye",
            "hang up",
            "end call",
            "that's all",
            "i'm done",
            "gotta go",
        ]
        return any(phrase in lower for phrase in goodbye_phrases)
