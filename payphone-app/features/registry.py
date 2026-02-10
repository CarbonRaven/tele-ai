"""Feature registry for dynamic feature discovery and routing.

The registry auto-discovers feature modules and provides routing
by dial code or voice trigger.
"""

__all__ = [
    "FeatureRegistry",
    "register_feature",
]

import importlib
import logging
from pathlib import Path
from typing import Type

from features.base import BaseFeature

logger = logging.getLogger(__name__)


class FeatureRegistry:
    """Registry for feature discovery and routing.

    Uses class-level state as a singleton pattern — all instances share the
    same feature registry. Call clear() to reset state (useful in tests).

    Features are registered by their dial code and optional voice triggers.
    The registry can auto-discover features from the features directory.
    """

    _features: dict[str, Type[BaseFeature]] = {}
    _voice_triggers: dict[str, str] = {}  # trigger -> dial_code

    @classmethod
    def register(cls, feature_class: Type[BaseFeature]) -> None:
        """Register a feature class.

        Args:
            feature_class: Feature class to register.
        """
        dial_code = feature_class.dial_code
        cls._features[dial_code] = feature_class

        # Register voice triggers
        for trigger in getattr(feature_class, "voice_triggers", []):
            cls._voice_triggers[trigger.lower()] = dial_code

        logger.debug(f"Registered feature: {feature_class.name} ({dial_code})")

    @classmethod
    def auto_discover(cls, features_dir: Path | None = None) -> None:
        """Auto-discover feature modules from directory.

        Args:
            features_dir: Path to features directory. Defaults to ./features.
        """
        if features_dir is None:
            features_dir = Path(__file__).parent

        logger.info(f"Auto-discovering features from {features_dir}")

        for module_path in features_dir.glob("*.py"):
            # Skip private modules and base/registry
            if module_path.name.startswith("_"):
                continue
            if module_path.stem in ("base", "registry", "__init__"):
                continue

            try:
                module = importlib.import_module(f"features.{module_path.stem}")

                # Find feature classes in module
                for attr_name in dir(module):
                    try:
                        attr = getattr(module, attr_name)

                        if (
                            isinstance(attr, type)
                            and issubclass(attr, BaseFeature)
                            and attr is not BaseFeature
                            and hasattr(attr, "dial_code")
                            and attr.dial_code != "0"  # Skip base class default
                        ):
                            cls.register(attr)
                    except Exception as e:
                        logger.error(
                            f"Error inspecting attribute '{attr_name}' in "
                            f"module {module_path.stem}: {e}"
                        )

            except ImportError as e:
                logger.error(
                    f"Failed to import feature module {module_path.stem}: {e}"
                )
            except Exception as e:
                logger.exception(
                    f"Unexpected error loading feature module {module_path.stem}: {e}"
                )

        logger.info(f"Discovered {len(cls._features)} features")

    @classmethod
    def get(cls, dial_code: str) -> Type[BaseFeature] | None:
        """Get feature class by dial code.

        Args:
            dial_code: DTMF dial code.

        Returns:
            Feature class or None if not found.
        """
        return cls._features.get(dial_code)

    @classmethod
    def get_instance(cls, dial_code: str) -> BaseFeature | None:
        """Create a new feature instance by dial code.

        Always creates a fresh instance so that per-call state
        (e.g. InteractiveFeature._state) is never shared across calls.

        Args:
            dial_code: DTMF dial code.

        Returns:
            New feature instance or None if not found.
        """
        feature_class = cls._features.get(dial_code)
        if feature_class:
            return feature_class()
        return None

    @classmethod
    def get_by_voice(cls, trigger: str) -> Type[BaseFeature] | None:
        """Get feature class by voice trigger.

        Args:
            trigger: Voice trigger word/phrase.

        Returns:
            Feature class or None if not found.
        """
        dial_code = cls._voice_triggers.get(trigger.lower())
        if dial_code:
            return cls._features.get(dial_code)
        return None

    @classmethod
    def get_by_voice_match(cls, text: str) -> Type[BaseFeature] | None:
        """Get feature class by matching text against voice triggers.

        Args:
            text: Text to match against triggers.

        Returns:
            Feature class or None if no match.
        """
        lower_text = text.lower()
        for trigger, dial_code in cls._voice_triggers.items():
            if trigger in lower_text:
                return cls._features.get(dial_code)
        return None

    @classmethod
    def list_features(cls) -> dict[str, str]:
        """List all registered features.

        Returns:
            Dict of dial_code -> feature_name.
        """
        return {code: feat.name for code, feat in cls._features.items()}

    @classmethod
    def get_menu_text(cls) -> str:
        """Get text describing available features for menu.

        Returns:
            Menu text listing features and their dial codes.
        """
        lines = ["Available services:"]

        for dial_code, feature_class in sorted(cls._features.items()):
            lines.append(f"  Press {dial_code} for {feature_class.name}")

        lines.append("  Press star to return to the main menu")

        return " ".join(lines)

    @classmethod
    def clear(cls) -> None:
        """Clear all registered features."""
        cls._features.clear()
        cls._voice_triggers.clear()


def register_feature(cls: Type[BaseFeature]) -> Type[BaseFeature]:
    """Decorator to register a feature class.

    Usage:
        @register_feature
        class MyFeature(BaseFeature):
            ...
    """
    FeatureRegistry.register(cls)
    return cls
