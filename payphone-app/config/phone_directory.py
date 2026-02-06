"""Phone directory mapping dialed numbers to features and personas.

Each entry maps a 7-digit phone number (XXX-XXXX format) to a service.
Entry types:
- "feature": A distinct service like Dial-A-Joke or Trivia
- "persona": A character personality for the operator
- "easter_egg": Hidden/fun numbers with special behavior
"""

__all__ = [
    "PHONE_DIRECTORY",
    "OPERATOR_NUMBER",
    "BIRTHDAY_PATTERN",
    "DEFAULT_GREETING_NOT_IN_SERVICE",
    "FEATURE_TO_NUMBER",
    "DTMF_SHORTCUTS",
]

OPERATOR_NUMBER = "555-0000"

BIRTHDAY_PATTERN = r"^555-[01]\d[0-3]\d$"

DEFAULT_GREETING_NOT_IN_SERVICE = (
    "We're sorry. The number you have dialed is not in service. "
    "Please check the number and try again, "
    "or dial 555-0000 for the operator."
)

PHONE_DIRECTORY: dict[str, dict] = {
    # === CORE SERVICES ===
    "555-0000": {"feature": "operator", "name": "The Operator", "type": "feature"},

    # === HISTORIC NUMBERS (actual 80s-90s service numbers) ===
    "767-2676": {"feature": "time_temp", "name": "Time & Temperature", "alias": "POPCORN", "type": "feature"},
    "777-3456": {"feature": "moviefone", "name": "Moviefone", "alias": "777-FILM", "type": "feature"},
    "867-5309": {"feature": "easter_jenny", "name": "Jenny", "type": "easter_egg"},

    # === INFORMATION ===
    "555-9328": {"feature": "weather", "name": "Weather Forecast", "alias": "WEAT", "type": "feature"},
    "555-4676": {"feature": "horoscope", "name": "Daily Horoscope", "alias": "HORO", "type": "feature"},
    "555-6397": {"feature": "news", "name": "News Headlines", "alias": "NEWS", "type": "feature"},
    "555-7767": {"feature": "sports", "name": "Sports Scores", "alias": "SPOR", "type": "feature"},

    # === ENTERTAINMENT ===
    "555-5653": {"feature": "jokes", "name": "Dial-A-Joke", "alias": "JOKE", "type": "feature"},
    "555-8748": {"feature": "trivia", "name": "Trivia Challenge", "alias": "TRIV", "type": "feature"},
    "555-7867": {"feature": "stories", "name": "Story Time", "alias": "STOR", "type": "feature"},
    "555-3678": {"feature": "fortune", "name": "Fortune Teller", "alias": "FORT", "type": "feature"},
    "555-6235": {"feature": "madlibs", "name": "Mad Libs", "alias": "MADL", "type": "feature"},
    "555-9687": {"feature": "would_you_rather", "name": "Would You Rather", "alias": "WRTH", "type": "feature"},
    "555-2090": {"feature": "twenty_questions", "name": "20 Questions", "alias": "20QS", "type": "feature"},

    # === ADVICE & SUPPORT ===
    "555-2384": {"feature": "advice", "name": "Advice Line", "alias": "ADVI", "type": "feature"},
    "555-2667": {"feature": "compliment", "name": "Compliment Line", "alias": "COMP", "type": "feature"},
    "555-7627": {"feature": "roast", "name": "Roast Line", "alias": "ROAS", "type": "feature"},
    "555-5433": {"feature": "life_coach", "name": "Life Coach", "alias": "LIFE", "type": "feature"},
    "555-2663": {"feature": "confession", "name": "Confession Line", "alias": "CONF", "type": "feature"},
    "555-8368": {"feature": "vent", "name": "Vent Line", "alias": "VENT", "type": "feature"},

    # === NOSTALGIC ===
    "555-2655": {"feature": "collect_call", "name": "Collect Call Simulator", "alias": "COLL", "type": "feature"},
    "555-8477": {"feature": "nintendo_tips", "name": "Nintendo Tip Line", "alias": "TIPS", "type": "feature"},
    "555-8463": {"feature": "time_traveler", "name": "Time Traveler's Line", "alias": "TRAV", "type": "feature"},

    # === UTILITIES ===
    "555-2252": {"feature": "calculator", "name": "Calculator", "alias": "CALC", "type": "feature"},
    "555-8726": {"feature": "translator", "name": "Translator", "alias": "TRAN", "type": "feature"},
    "555-7735": {"feature": "spelling", "name": "Spelling Bee", "alias": "SPEL", "type": "feature"},
    "555-3428": {"feature": "dictionary", "name": "Dictionary", "alias": "DICT", "type": "feature"},
    "555-7324": {"feature": "recipe", "name": "Recipe Line", "alias": "RECI", "type": "feature"},
    "555-3322": {"feature": "debate", "name": "Debate Partner", "alias": "DEBA", "type": "feature"},
    "555-4688": {"feature": "interview", "name": "Interview Mode", "alias": "INTV", "type": "feature"},

    # === PERSONAS ===
    "555-7243": {
        "feature": "persona_sage", "name": "Wise Sage", "alias": "SAGE",
        "type": "persona", "persona_key": "sage",
    },
    "555-5264": {
        "feature": "persona_comedian", "name": "Comedian", "alias": "LAFF",
        "type": "persona", "persona_key": "comedian",
    },
    "555-3383": {
        "feature": "persona_detective", "name": "Noir Detective", "alias": "DETE",
        "type": "persona", "persona_key": "detective",
    },
    "555-4726": {
        "feature": "persona_grandma", "name": "Southern Grandma", "alias": "GRAN",
        "type": "persona", "persona_key": "grandma",
    },
    "555-2687": {
        "feature": "persona_robot", "name": "Robot from Future", "alias": "BOTT",
        "type": "persona", "persona_key": "robot",
    },
    "555-8255": {
        "feature": "persona_valley", "name": "Valley Girl", "alias": "VALL",
        "type": "persona", "persona_key": "valley",
    },
    "555-7638": {
        "feature": "persona_beatnik", "name": "Beatnik Poet", "alias": "POET",
        "type": "persona", "persona_key": "beatnik",
    },
    "555-4263": {
        "feature": "persona_gameshow", "name": "Game Show Host", "alias": "GAME",
        "type": "persona", "persona_key": "gameshow",
    },
    "555-9427": {
        "feature": "persona_conspiracy", "name": "Conspiracy Theorist", "alias": "XFIL",
        "type": "persona", "persona_key": "conspiracy",
    },

    # === EASTER EGGS ===
    "555-2600": {"feature": "easter_phreaker", "name": "Blue Box Secret", "type": "easter_egg"},
    "555-1337": {"feature": "easter_hacker", "name": "Hacker Mode", "type": "easter_egg"},
    "555-7492": {"feature": "easter_pizza", "name": "Joe's Pizza", "type": "easter_egg"},
    "555-1313": {"feature": "easter_haunted", "name": "Haunted Booth", "type": "easter_egg"},
}

# Single-digit DTMF shortcuts for quick access during a call
DTMF_SHORTCUTS: dict[str, str] = {
    "0": "operator",
    "1": "jokes",
    "2": "trivia",
    "3": "fortune",
    "4": "horoscope",
    "5": "stories",
    "6": "compliment",
    "7": "advice",
    "8": "time_temp",
    "9": "roast",
}

# Reverse lookup: feature name -> phone number (built at import time)
FEATURE_TO_NUMBER: dict[str, str] = {
    entry["feature"]: number
    for number, entry in PHONE_DIRECTORY.items()
}
