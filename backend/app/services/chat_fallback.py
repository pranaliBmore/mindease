import random
import re

from app.services.local_nlp import classify_emotion_vader


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip())


_MODE_REPLIES = {
    "breathing": [
        "Let's breathe together. Inhale for 4, hold for 4, breathe out for 4, hold for 4. "
        "Repeat that four times and notice how your body feels after.",
        "Try this for a minute: slow breath in through your nose for 4, gentle hold for 4, "
        "long breath out for 6. Let each exhale be a little longer than the one before.",
        "Place one hand on your chest and one on your belly. Breathe so only the lower hand "
        "moves, slow and even, for six breaths.",
        "Two quick inhales through the nose, then one long slow exhale through the mouth. "
        "Do that three times - it settles the nervous system fast.",
    ],
    "grounding": [
        "Let's ground for a moment. Name 5 things you can see, 4 you can feel, 3 you can hear, "
        "2 you can smell, and 1 you can taste. Take your time with each one.",
        "Press both feet into the floor and feel the chair holding you. Look slowly around the "
        "room and name five ordinary objects out loud.",
        "Hold something cool or textured. Notice its weight and temperature for a slow count of ten, "
        "then take one deep breath.",
    ],
    "journal_prompt": [
        "Here's a prompt: What is one thing that felt heavy today, and one small thing that felt okay?",
        "Try writing about this: If a good friend felt exactly how you feel now, what would you want them to hear?",
        "A prompt for you: What do you need more of this week, and what could you let go of?",
        "Write freely for two minutes on: 'Right now I'm feeling... and what I'd like is...'.",
        "Prompt: name one worry, then write the most likely outcome next to the worst one.",
    ],
    "reframe": [
        "That thought sounds exhausting to carry. A softer version might be: this is hard, "
        "and I can handle hard things one step at a time. What would you tell a friend in your place?",
        "Notice the shape of the thought: 'I'm telling myself that...'. A kinder, truer version "
        "could be that you're doing your best with a genuinely difficult situation.",
        "The fear is loud, but loud isn't the same as accurate. What's one piece of evidence "
        "that it might not go the way you're picturing?",
    ],
    "pep_talk": [
        "You showed up and you're still trying, and that counts for a lot. Pick one small next step, "
        "just one, and let the rest wait. You've got this.",
        "You've gotten through every hard day so far. This one is not the exception. One small "
        "thing now, and be as kind to yourself as you'd be to a friend.",
        "Progress isn't always loud. Sometimes it's just not giving up today - and you haven't. "
        "Choose the next tiny step and let that be enough.",
    ],
}


def generate_support_reply(message: str, emotion_hint: str | None, mode: str = "chat") -> str:
    """Offline reply used when no AI provider is reachable.

    Short and plain: a warm opening plus one small step, sometimes a gentle question.
    Randomised so it never feels canned. Honours guided ``mode`` requests.
    """
    msg = _normalize(message)
    local = classify_emotion_vader(msg)
    emotion = (emotion_hint or "").strip().lower() or local.emotion

    rnd = random.Random(f"{local.emotion}:{mode}:{hash(msg)}")

    if mode in _MODE_REPLIES:
        return rnd.choice(_MODE_REPLIES[mode])

    openings = [
        "I'm here with you.",
        "Thanks for telling me.",
        "That sounds like a lot right now.",
        "I hear you.",
        "I'm glad you reached out.",
    ]
    questions = [
        "What feels hardest right now?",
        "Where do you notice this in your body?",
        "What would help most: calm, clarity, or comfort?",
        "What's one small thing that would make this a little easier?",
    ]

    steps = {
        "stress": [
            "Try slow breathing for a minute: in for 4, hold 4, out for 4, hold 4.",
            "Pick just one thing for the next ten minutes. The rest can wait.",
            "Drop your shoulders, unclench your jaw, and make your next breath out a little longer.",
            "Write down the top three things on your mind, then circle the one you can act on today.",
            "Step away for five minutes - water, a window, a short walk - before the next task.",
            "Ask 'will this matter in a week?' and let that set how much energy it gets.",
        ],
        "anxiety": [
            "Let's ground for a moment: name 5 things you can see and 3 you can hear.",
            "Breathe out slowly, longer than you breathe in, a few times.",
            "Ask yourself: is this certain, or just possible? For now, treat it as just possible.",
            "Give the worry a 10-minute window on paper, then close the notebook.",
            "Move your body for two minutes - anxious energy needs somewhere to go.",
            "Name it out loud: 'I'm feeling anxious.' Naming it tends to shrink it.",
        ],
        "sadness": [
            "Be gentle with yourself. A small kind act helps: water, food, or a short walk.",
            "If you can, message one person and ask for five minutes of their time.",
            "You don't have to fix everything today. One small step is enough.",
            "Try five minutes near a window or outside - light nudges mood chemistry.",
            "Write three lines to yourself the way you'd write to a friend who felt this.",
            "Lower today's list to the essentials plus one kind thing.",
        ],
        "happiness": [
            "Take twenty seconds to really enjoy this. What feels good about it?",
            "Maybe note what led to this so you can come back to it later.",
            "What could you do again tomorrow to keep this going?",
            "Text one person a simple win from today - sharing it makes it last.",
            "Name the three things that helped build this good moment.",
        ],
        "anger": [
            "Before you reply to anyone, take a slow breath or a short walk first.",
            "Anger often points to a need. What feels crossed here?",
            "We can write a calm boundary sentence together if you like.",
            "Draft the message but don't send it - come back to it in twenty minutes.",
            "Lower your volume on purpose; the body tends to follow the voice.",
            "Two minutes of fast movement to burn off the adrenaline, then talk.",
        ],
        "fear": [
            "Let's find what you can control in the next five minutes.",
            "Name three signs that you're safe right now.",
            "If nothing is dangerous this second, we can take one tiny step together.",
            "Slow your exhale to a count of six - it tells your body the threat has passed.",
            "Break the scary thing into just the first 30-second step.",
            "Write the 'if it goes wrong' plan so your brain can stop rehearsing it.",
        ],
        "neutrality": [
            "Neutral is okay. It can be a good place to reset.",
            "On a scale of 0 to 10, where's your energy right now?",
            "What would you like to focus on: calm, focus, or connection?",
            "This is a good moment to plant a small habit - pick one tiny thing.",
            "Do a two-minute tidy of one surface near you; it clears the head a little.",
            "Message someone you haven't spoken to in a while.",
        ],
    }

    step = rnd.choice(steps.get(emotion, steps["neutrality"]))
    opening = rnd.choice(openings)
    if rnd.random() < 0.6:
        return f"{opening} {step}"
    return f"{opening} {step} {rnd.choice(questions)}"
