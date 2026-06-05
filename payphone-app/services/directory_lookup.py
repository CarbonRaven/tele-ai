"""Directory lookup helpers for the operator."""

from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher
import re

from config.phone_directory import PHONE_DIRECTORY

__all__ = ["DirectoryMatch", "lookup"]


@dataclass(frozen=True)
class DirectoryMatch:
    """A fuzzy match result for a phone directory entry."""

    number: str
    name: str
    description: str
    score: float


_STOP_WORDS = {
    "a",
    "an",
    "and",
    "for",
    "from",
    "i",
    "line",
    "me",
    "my",
    "of",
    "please",
    "service",
    "show",
    "some",
    "the",
    "to",
    "want",
}

_FEATURE_KEYWORDS = {
    "jokes": {"joke", "funny", "laugh", "comedy"},
    "trivia": {"quiz", "question", "facts"},
    "fortune": {"psychic", "future", "destiny"},
    "weather": {"forecast", "temperature", "rain", "sunny"},
    "horoscope": {"zodiac", "sign", "astrology"},
    "news": {"headlines", "current", "events"},
    "sports": {"scores", "game", "games", "team"},
    "stories": {"story", "bedtime", "tale"},
    "advice": {"help", "guidance"},
    "compliment": {"praise", "confidence", "kindness"},
    "roast": {"insult", "burn", "tease"},
    "nintendo_tips": {"nintendo", "games", "gaming", "mario", "zelda"},
    "time_temp": {"time", "clock", "popcorn", "temperature"},
    "moviefone": {"movie", "movies", "film", "showtimes"},
    "life_coach": {"goals", "motivation", "coaching"},
    "confession": {"secret", "secrets", "confess"},
    "vent": {"rant", "complain", "frustrated"},
    "collect_call": {"collect", "operator-assisted"},
    "time_traveler": {"travel", "future", "past", "year"},
    "calculator": {"math", "compute", "calculation"},
    "translator": {"translate", "language", "translation"},
    "spelling": {"spell", "spelling", "words"},
    "dictionary": {"define", "definition", "meaning"},
    "recipe": {"cook", "cooking", "food", "meal"},
    "debate": {"argue", "argument", "discussion"},
    "interview": {"job", "practice", "career"},
    "madlibs": {"mad", "libs", "story game"},
    "would_you_rather": {"choice", "choices", "either"},
    "twenty_questions": {"guessing", "guess", "twenty"},
    "persona_sage": {"wise", "wisdom"},
    "persona_comedian": {"comic", "comedian"},
    "persona_detective": {"noir", "mystery", "detective"},
    "persona_grandma": {"grandma", "southern", "grandmother"},
    "persona_robot": {"robot", "future", "machine"},
    "persona_valley": {"valley", "girl"},
    "persona_beatnik": {"poet", "poetry", "beatnik"},
    "persona_gameshow": {"game", "show", "host"},
    "persona_conspiracy": {"conspiracy", "aliens", "tinfoil"},
    "easter_jenny": {"jenny"},
    "easter_phreaker": {"phreaker", "blue", "box", "hack"},
    "easter_hacker": {"hacker", "elite", "leet"},
    "easter_pizza": {"pizza"},
    "easter_haunted": {"haunted", "ghost", "spooky"},
    "operator": {"operator", "help", "assistant"},
}


def _tokenize(text: str) -> list[str]:
    return [
        token
        for token in re.findall(r"[a-z0-9]+", text.lower())
        if token not in _STOP_WORDS
    ]


def _entry_keywords(number: str, entry: dict[str, str]) -> set[str]:
    tokens = set(_tokenize(entry["name"]))
    feature = entry["feature"]
    tokens.update(_tokenize(feature.replace("_", " ")))

    alias = entry.get("alias")
    if alias:
        tokens.update(_tokenize(alias))

    greeting = entry.get("greeting", "")
    tokens.update(_tokenize(" ".join(greeting.split()[:8])))
    tokens.update(_FEATURE_KEYWORDS.get(feature, set()))

    digits = number.replace("-", "")
    tokens.add(number.lower())
    tokens.add(digits)
    return tokens


def _description(entry: dict[str, str]) -> str:
    parts = [entry["type"].replace("_", " ")]
    alias = entry.get("alias")
    if alias:
        parts.append(f"alias {alias}")
    return ", ".join(parts)


def lookup(query: str, top_n: int = 3) -> list[DirectoryMatch]:
    """Find the most likely directory entries for a spoken request."""
    query_tokens = set(_tokenize(query))
    query_text = " ".join(sorted(query_tokens)) or query.strip().lower()
    if not query_text:
        return []

    matches: list[DirectoryMatch] = []

    for number, entry in PHONE_DIRECTORY.items():
        keywords = _entry_keywords(number, entry)
        overlap = len(query_tokens & keywords) / max(len(query_tokens), 1)

        candidate_phrases = [
            entry["name"].lower(),
            entry["feature"].replace("_", " ").lower(),
        ]
        similarity = max(
            SequenceMatcher(None, query_text, phrase).ratio()
            for phrase in candidate_phrases
        )

        score = (overlap * 0.65) + (similarity * 0.35)
        if overlap == 0 and similarity < 0.72:
            continue
        if score < 0.38:
            continue

        matches.append(
            DirectoryMatch(
                number=number,
                name=entry["name"],
                description=_description(entry),
                score=round(score, 3),
            )
        )

    matches.sort(key=lambda match: (-match.score, match.name, match.number))
    return matches[:top_n]
