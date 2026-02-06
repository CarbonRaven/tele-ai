"""Phone directory mapping dialed numbers to features and personas.

Each entry maps a 7-digit phone number (XXX-XXXX format) to a service.
Entry types:
- "feature": A distinct service like Dial-A-Joke or Trivia
- "persona": A character personality for the operator
- "easter_egg": Hidden/fun numbers with special behavior
"""

from typing import TypedDict

__all__ = [
    "PhoneDirectoryEntry",
    "PHONE_DIRECTORY",
    "OPERATOR_NUMBER",
    "BIRTHDAY_PATTERN",
    "BIRTHDAY_GREETING",
    "DEFAULT_GREETING_NOT_IN_SERVICE",
    "FEATURE_TO_NUMBER",
    "DTMF_SHORTCUTS",
]


# TypedDict with inheritance for Python 3.10 compat (total=False optional keys)
class _PhoneDirectoryRequired(TypedDict):
    feature: str
    name: str
    type: str
    greeting: str


class PhoneDirectoryEntry(_PhoneDirectoryRequired, total=False):
    alias: str
    persona_key: str


OPERATOR_NUMBER = "555-0000"

# Matches 555-MMDD where MM is 01-12 and DD is 01-31
BIRTHDAY_PATTERN = r"^555-(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01])$"

# Greeting for the regex-matched birthday easter egg (not in PHONE_DIRECTORY)
BIRTHDAY_GREETING = "Happy birthday to you! The AI Payphone wishes you a wonderful day!"

DEFAULT_GREETING_NOT_IN_SERVICE = (
    "We're sorry. The number you have dialed is not in service. "
    "Please check the number and try again, "
    "or dial 555-0000 for the operator."
)

PHONE_DIRECTORY: dict[str, PhoneDirectoryEntry] = {
    # === CORE SERVICES ===
    "555-0000": {
        "feature": "operator",
        "name": "The Operator",
        "type": "feature",
        "greeting": "You're speaking with the operator. How can I help?",
    },

    # === HISTORIC NUMBERS (actual 80s-90s service numbers) ===
    "767-2676": {
        "feature": "time_temp",
        "name": "Time & Temperature",
        "alias": "POPCORN",
        "type": "feature",
        "greeting": "At the tone, the time will be now. Welcome to Time and Temperature.",
    },
    "777-3456": {
        "feature": "moviefone",
        "name": "Moviefone",
        "alias": "777-FILM",
        "type": "feature",
        "greeting": "Hello, and welcome to Moviefone! What movie would you like to see?",
    },
    "867-5309": {
        "feature": "easter_jenny",
        "name": "Jenny",
        "type": "easter_egg",
        "greeting": "Hello? Who is this? How did you get this number? Oh, you must have got it off the wall.",
    },

    # === INFORMATION ===
    "555-9328": {
        "feature": "weather",
        "name": "Weather Forecast",
        "alias": "WEAT",
        "type": "feature",
        "greeting": "Welcome to the Weather Forecast line. What city would you like the forecast for?",
    },
    "555-4676": {
        "feature": "horoscope",
        "name": "Daily Horoscope",
        "alias": "HORO",
        "type": "feature",
        "greeting": "Welcome to the Horoscope Line. What's your sign?",
    },
    "555-6397": {
        "feature": "news",
        "name": "News Headlines",
        "alias": "NEWS",
        "type": "feature",
        "greeting": "Welcome to News Headlines. Here are today's top stories.",
    },
    "555-7767": {
        "feature": "sports",
        "name": "Sports Scores",
        "alias": "SPOR",
        "type": "feature",
        "greeting": "Welcome to Sports Scores. What sport are you following?",
    },

    # === ENTERTAINMENT ===
    "555-5653": {
        "feature": "jokes",
        "name": "Dial-A-Joke",
        "alias": "JOKE",
        "type": "feature",
        "greeting": "Welcome to Dial-A-Joke! Want to hear a joke?",
    },
    "555-8748": {
        "feature": "trivia",
        "name": "Trivia Challenge",
        "alias": "TRIV",
        "type": "feature",
        "greeting": "Welcome to Trivia Challenge! Ready for a question?",
    },
    "555-7867": {
        "feature": "stories",
        "name": "Story Time",
        "alias": "STOR",
        "type": "feature",
        "greeting": "Welcome to Story Time. Would you like to hear a story?",
    },
    "555-3678": {
        "feature": "fortune",
        "name": "Fortune Teller",
        "alias": "FORT",
        "type": "feature",
        "greeting": "Welcome to the Fortune Teller. The spirits are listening. Ask about your future.",
    },
    "555-6235": {
        "feature": "madlibs",
        "name": "Mad Libs",
        "alias": "MADL",
        "type": "feature",
        "greeting": "Welcome to Mad Libs! Let's make a silly story together.",
    },
    "555-9687": {
        "feature": "would_you_rather",
        "name": "Would You Rather",
        "alias": "WRTH",
        "type": "feature",
        "greeting": "Welcome to Would You Rather! Ready for a tough choice?",
    },
    "555-2090": {
        "feature": "twenty_questions",
        "name": "20 Questions",
        "alias": "20QS",
        "type": "feature",
        "greeting": "Welcome to 20 Questions! Think of something and I'll try to guess it.",
    },

    # === ADVICE & SUPPORT ===
    "555-2384": {
        "feature": "advice",
        "name": "Advice Line",
        "alias": "ADVI",
        "type": "feature",
        "greeting": "Welcome to the Advice Line. What's on your mind?",
    },
    "555-2667": {
        "feature": "compliment",
        "name": "Compliment Line",
        "alias": "COMP",
        "type": "feature",
        "greeting": "Welcome to the Compliment Line. You're amazing, and here's why.",
    },
    "555-7627": {
        "feature": "roast",
        "name": "Roast Line",
        "alias": "ROAS",
        "type": "feature",
        "greeting": "Welcome to the Roast Line. Hope you can take the heat!",
    },
    "555-5433": {
        "feature": "life_coach",
        "name": "Life Coach",
        "alias": "LIFE",
        "type": "feature",
        "greeting": "Welcome to the Life Coach line. Let's talk about your goals.",
    },
    "555-2663": {
        "feature": "confession",
        "name": "Confession Line",
        "alias": "CONF",
        "type": "feature",
        "greeting": "Welcome to the Confession Line. Your secret is safe with me.",
    },
    "555-8368": {
        "feature": "vent",
        "name": "Vent Line",
        "alias": "VENT",
        "type": "feature",
        "greeting": "Welcome to the Vent Line. Go ahead, let it all out.",
    },

    # === NOSTALGIC ===
    "555-2655": {
        "feature": "collect_call",
        "name": "Collect Call Simulator",
        "alias": "COLL",
        "type": "feature",
        "greeting": "You have a collect call from, the AI Payphone. Press 1 to accept.",
    },
    "555-8477": {
        "feature": "nintendo_tips",
        "name": "Nintendo Tip Line",
        "alias": "TIPS",
        "type": "feature",
        "greeting": "Thank you for calling the Nintendo Power Line! What game do you need help with?",
    },
    "555-8463": {
        "feature": "time_traveler",
        "name": "Time Traveler's Line",
        "alias": "TRAV",
        "type": "feature",
        "greeting": "Welcome to the Time Traveler's Line. What year would you like to visit?",
    },

    # === UTILITIES ===
    "555-2252": {
        "feature": "calculator",
        "name": "Calculator",
        "alias": "CALC",
        "type": "feature",
        "greeting": "Welcome to Calculator. What would you like me to compute?",
    },
    "555-8726": {
        "feature": "translator",
        "name": "Translator",
        "alias": "TRAN",
        "type": "feature",
        "greeting": "Welcome to the Translator. What would you like translated?",
    },
    "555-7735": {
        "feature": "spelling",
        "name": "Spelling Bee",
        "alias": "SPEL",
        "type": "feature",
        "greeting": "Welcome to Spelling Bee! Ready for your first word?",
    },
    "555-3428": {
        "feature": "dictionary",
        "name": "Dictionary",
        "alias": "DICT",
        "type": "feature",
        "greeting": "Welcome to the Dictionary line. What word would you like defined?",
    },
    "555-7324": {
        "feature": "recipe",
        "name": "Recipe Line",
        "alias": "RECI",
        "type": "feature",
        "greeting": "Welcome to the Recipe Line. What are you in the mood to cook?",
    },
    "555-3322": {
        "feature": "debate",
        "name": "Debate Partner",
        "alias": "DEBA",
        "type": "feature",
        "greeting": "Welcome to the Debate Partner. Pick a topic and a side!",
    },
    "555-4688": {
        "feature": "interview",
        "name": "Interview Mode",
        "alias": "INTV",
        "type": "feature",
        "greeting": "Welcome to Interview Mode. Let's practice! What role are you going for?",
    },

    # === PERSONAS ===
    "555-7243": {
        "feature": "persona_sage",
        "name": "Wise Sage",
        "alias": "SAGE",
        "type": "persona",
        "persona_key": "sage",
        "greeting": "Greetings, seeker. The Wise Sage awaits your question.",
    },
    "555-5264": {
        "feature": "persona_comedian",
        "name": "Comedian",
        "alias": "LAFF",
        "type": "persona",
        "persona_key": "comedian",
        "greeting": "Hey hey hey! You've reached the Comedian! Let's have some laughs!",
    },
    "555-3383": {
        "feature": "persona_detective",
        "name": "Noir Detective",
        "alias": "DETE",
        "type": "persona",
        "persona_key": "detective",
        "greeting": "The name's Jones. Detective Jones. Something tells me you're not calling about the weather.",
    },
    "555-4726": {
        "feature": "persona_grandma",
        "name": "Southern Grandma",
        "alias": "GRAN",
        "type": "persona",
        "persona_key": "grandma",
        "greeting": "Well, bless your heart! It's Grandma Mae. Come sit down and chat with me, sugar.",
    },
    "555-2687": {
        "feature": "persona_robot",
        "name": "Robot from Future",
        "alias": "BOTT",
        "type": "persona",
        "persona_key": "robot",
        "greeting": "GREETINGS, HUMAN OF THE PAST. I AM COMP-U-TRON 3000. WHAT A DELIGHTFUL ARTIFACT, THIS TELEPHONE.",
    },
    "555-8255": {
        "feature": "persona_valley",
        "name": "Valley Girl",
        "alias": "VALL",
        "type": "persona",
        "persona_key": "valley",
        "greeting": "Oh my God, hi! Like, welcome to the Valley Girl line! This is gonna be totally awesome!",
    },
    "555-7638": {
        "feature": "persona_beatnik",
        "name": "Beatnik Poet",
        "alias": "POET",
        "type": "persona",
        "persona_key": "beatnik",
        "greeting": "Hey there, cool cat. You've reached the Beatnik Poet. Let the words flow, daddy-o.",
    },
    "555-4263": {
        "feature": "persona_gameshow",
        "name": "Game Show Host",
        "alias": "GAME",
        "type": "persona",
        "persona_key": "gameshow",
        "greeting": "Welcome, contestant! You're on the hottest game show on the payphone! Let's play!",
    },
    "555-9427": {
        "feature": "persona_conspiracy",
        "name": "Conspiracy Theorist",
        "alias": "XFIL",
        "type": "persona",
        "persona_key": "conspiracy",
        "greeting": "You found this number. That means you're ready. They don't want you to know what I'm about to tell you.",
    },

    # === EASTER EGGS ===
    "555-2600": {
        "feature": "easter_phreaker",
        "name": "Blue Box Secret",
        "type": "easter_egg",
        "greeting": "Two-six-hundred hertz. You know what that means. Welcome to the underground.",
    },
    "555-1337": {
        "feature": "easter_hacker",
        "name": "Hacker Mode",
        "type": "easter_egg",
        "greeting": "Access granted. Welcome to Hacker Mode. The mainframe awaits your commands.",
    },
    "555-7492": {
        "feature": "easter_pizza",
        "name": "Joe's Pizza",
        "type": "easter_egg",
        "greeting": "Joe's Pizza! You want a pizza? We got the best pizza in New York!",
    },
    "555-1313": {
        "feature": "easter_haunted",
        "name": "Haunted Booth",
        "type": "easter_egg",
        "greeting": "You shouldn't have called this number. The line is cold. Something is here with us.",
    },
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
