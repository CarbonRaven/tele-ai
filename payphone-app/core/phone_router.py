"""Phone number routing for per-service direct dial.

Routes dialed numbers (from the Asterisk dialplan or in-call DTMF) to the
correct feature, persona, or easter egg.
"""

__all__ = [
    "RouteResult",
    "PhoneRouter",
]

import logging
import re
from dataclasses import dataclass

from config.phone_directory import (
    PHONE_DIRECTORY,
    BIRTHDAY_PATTERN,
    DEFAULT_GREETING_NOT_IN_SERVICE,
    DTMF_SHORTCUTS,
    FEATURE_TO_NUMBER,
)

logger = logging.getLogger(__name__)


@dataclass
class RouteResult:
    """Result of routing a dialed number."""

    feature: str
    name: str
    entry_type: str  # "feature", "persona", "easter_egg", "invalid"
    greeting: str | None = None
    persona_key: str | None = None
    is_direct_dial: bool = False


class PhoneRouter:
    """Routes dialed numbers to features."""

    def route(self, dialed_number: str) -> RouteResult:
        """Route a dialed number to the appropriate feature.

        Args:
            dialed_number: Raw digits from the Asterisk dialplan.

        Returns:
            RouteResult describing where to route the call.
        """
        normalized = self.normalize(dialed_number)

        # Check direct match in directory
        if normalized in PHONE_DIRECTORY:
            entry = PHONE_DIRECTORY[normalized]
            return RouteResult(
                feature=entry["feature"],
                name=entry["name"],
                entry_type=entry.get("type", "feature"),
                persona_key=entry.get("persona_key"),
                is_direct_dial=True,
            )

        # Check birthday pattern (555-MMDD)
        if re.match(BIRTHDAY_PATTERN, normalized):
            return RouteResult(
                feature="easter_birthday",
                name="Birthday Line",
                entry_type="easter_egg",
                is_direct_dial=True,
            )

        # Unknown number
        return RouteResult(
            feature="invalid",
            name="Not In Service",
            entry_type="invalid",
            greeting=DEFAULT_GREETING_NOT_IN_SERVICE,
            is_direct_dial=False,
        )

    def route_dtmf(self, digits: str) -> RouteResult:
        """Route DTMF digits entered during a call.

        Handles both single-digit shortcuts (1=jokes, 2=trivia, etc.)
        and full 7-digit numbers typed during a call.

        Args:
            digits: One or more DTMF digits.

        Returns:
            RouteResult describing where to route.
        """
        # Single-digit shortcut
        if len(digits) == 1 and digits in DTMF_SHORTCUTS:
            feature = DTMF_SHORTCUTS[digits]
            # Look up the name via pre-built reverse index
            number = FEATURE_TO_NUMBER.get(feature)
            if number and number in PHONE_DIRECTORY:
                name = PHONE_DIRECTORY[number]["name"]
            else:
                name = feature.replace("_", " ").title()
            return RouteResult(
                feature=feature,
                name=name,
                entry_type="feature",
                is_direct_dial=False,
            )

        # Multi-digit: treat as a phone number
        return self.route(digits)

    @staticmethod
    def normalize(number: str) -> str:
        """Normalize a phone number to XXX-XXXX format.

        Handles 7-digit, 10-digit (strip area code), and 11-digit
        (strip country+area code) inputs.

        Args:
            number: Raw digits, possibly with dashes or prefix.

        Returns:
            Normalized number in XXX-XXXX format, or cleaned input
            if it doesn't match expected lengths.
        """
        # Strip everything except digits
        digits = re.sub(r"\D", "", number)

        # 11 digits: 1 + area code + 7 digits -> take last 7
        if len(digits) == 11 and digits[0] == "1":
            digits = digits[4:]
        # 10 digits: area code + 7 digits -> take last 7
        elif len(digits) == 10:
            digits = digits[3:]

        # Format as XXX-XXXX
        if len(digits) == 7:
            return f"{digits[:3]}-{digits[3:]}"

        # Non-standard length: return digits only (will not match any directory entry)
        return digits
