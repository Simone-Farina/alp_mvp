import os
import random
from typing import Literal

from openai import OpenAI

STYLES: list[Literal["Visual", "Auditory", "Kinesthetic", "Analytical"]] = [
    "Visual", "Auditory", "Kinesthetic", "Analytical"
]

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


# IDEA: if for some reason the gpt didn't give us one of the expected answers
#       we should store in a DB table this status flag signaling that the assessment must be completed again
def detect_learning_style(answers: dict[str, str], use_gpt: bool = False) -> str:
    """
        Given a dict of question -> answer, return a learning style string.
        If use_gpt is False or OPENAI_API_KEY is missing, fall back to a heuristic.
    """
    if use_gpt:
        prompt = (
                "You are an educational psychologist. "
                "Classify the learner into one of these styles: "
                f"{', '.join(STYLES)}.\n\nAnswers:\n"
                + "\n".join(f"- {q}: {a}" for q, a in answers.items())
                + "\nAnswer with ONLY the style word."
        )
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0
        )
        style = resp.choices[0].message.content.strip()
        if style in STYLES:
            return style
    ans_flat = " ".join(answers.values()).lower()
    if "diagram" in ans_flat or "visual" in ans_flat:
        return "Visual"
    if "listen" in ans_flat or "audio" in ans_flat:
        return "Auditory"
    if "hands-on" in ans_flat or "practice" in ans_flat:
        return "Kinesthetic"
    return random.choice(STYLES)
