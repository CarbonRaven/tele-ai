"""Feature modules for the AI Payphone.

Features are modular components that provide specific functionality
like jokes, trivia, fortune telling, etc.
"""

from features.base import BaseFeature
from features.registry import FeatureRegistry

__all__ = ["BaseFeature", "FeatureRegistry"]
