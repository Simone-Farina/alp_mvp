from __future__ import annotations

import os
import random
from abc import ABC, abstractmethod
from typing import Optional, Dict, List

# Import learning plan structures for type hints
from alp.ai.learning_plan import LearningPlan
from alp.logging.config import get_logger
from alp.logging.instrumentation import traced

# Supported learning styles
STYLES: List[str] = ["Visual", "Auditory", "Kinesthetic", "Analytical"]


class AIService(ABC):
    """Abstract interface for AI-related operations (can be implemented by different AI providers)."""

    @abstractmethod
    def detect_learning_style(self, answers: Dict[str, str], use_gpt: bool = False) -> str:
        """
        Determine the user's learning style given answers to onboarding questions.
        If use_gpt is True and an AI API is available, use it; otherwise use a heuristic fallback.
        """
        ...

    @abstractmethod
    def suggest_parent_topic(self, title: str, content: str) -> Optional[str]:
        """
        Suggest a broader parent topic for a note, using AI. Returns None if no suggestion or no AI available.
        """
        ...

    @abstractmethod
    def generate_learning_plan(self, topic: str, depth: int, style: str,
                               max_nodes: int, known_samples: List[str]) -> Optional[LearningPlan]:
        """
        Generate a LearningPlan (set of interconnected concepts) for a given topic and user style.
        Returns a LearningPlan object, or None if generation failed or no AI available.
        """
        ...


class OpenAIService(AIService):
    """
    AIService implementation using OpenAI's API.
    This class handles detection of learning style, parent topic suggestion, and learning plan generation.
    """

    def __init__(self, api_key: Optional[str] = None):
        self._log = get_logger("ai.openai")
        try:
            import openai
        except ImportError as e:
            self._log.info("ai.provider.import_error", ex=e.msg)
            openai = None
        self._openai = openai
        self._log.info("ai.provider._openai", openai=self._openai)
        # Configure API key if available
        if self._openai and api_key:
            self._openai.api_key = api_key
        elif self._openai:
            key = os.getenv("OPENAI_API_KEY")
            self._log.info("ai.provider.key", openai_api_key=key)
            if key:
                self._openai.api_key = key
            else:
                # If no API key is provided or configured, disable OpenAI usage
                self._openai = None

        self._log.info("ai.provider.init", openai_enabled=bool(self._openai))

    @traced("ai.detect_learning_style")
    def detect_learning_style(self, answers: Dict[str, str], use_gpt: bool = False) -> str:
        # If allowed and OpenAI is configured, try using AI to classify the learning style
        self._log.debug("detect_learning_style.call", answers=answers)
        if use_gpt and self._openai:
            prompt = (
                    "You are an educational psychologist. "
                    "Classify the learner into one of these styles: "
                    f"{', '.join(STYLES)}.\n\nAnswers:\n"
                    + "\n".join(f"- {q}: {a}" for q, a in answers.items())
                    + "\nAnswer with ONLY the style word."
            )
            try:
                resp = self._openai.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0
                )
                style = resp.choices[0].message.content.strip()
                if style in STYLES:
                    self._log.info("detect_learning_style.result", style=style, used_gpt=bool(use_gpt and self._openai))
                    return style
            except Exception:
                # On any API error, fall back to heuristic
                pass
        # Heuristic fallback: decide based on keywords in answers
        ans_flat = " ".join(answers.values()).lower()
        if "diagram" in ans_flat or "visual" in ans_flat:
            return "Visual"
        if "listen" in ans_flat or "audio" in ans_flat:
            return "Auditory"
        if "hands" in ans_flat or "practice" in ans_flat:
            return "Kinesthetic"
        # Default to a random style if no clear signals
        return random.choice(STYLES)

    @traced("ai.suggest_parent")
    def suggest_parent_topic(self, title: str, content: str) -> Optional[str]:
        self._log.debug("suggest_parent_topic.call", title=title)
        if not self._openai:
            return None
        prompt = (
            "You are a knowledge graph assistant. "
            f"Note title: {title}\n"
            "Suggest ONE broader parent topic; reply ROOT if none.\n\n"
            f"CONTENT:\n{content[:4000]}"
        )
        try:
            resp = self._openai.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0
            )
        except Exception:
            return None
        ans = resp.choices[0].message.content.strip()
        self._log.info("suggest_parent_topic.result", ans=ans)
        if ans.upper() == "ROOT":
            return None
        return ans

    @traced("ai.generate_learning_plan")
    def generate_learning_plan(self, topic: str, depth: int, style: str,
                               max_nodes: int, known_samples: List[str]) -> Optional[LearningPlan]:
        self._log.info("generate_learning_plan.call", topic=topic, depth=depth, style=style, max_nodes=max_nodes)
        if not self._openai:
            return None
        # Build the prompt for the AI
        from alp.ai.learning_plan import SYSTEM_INSTRUCTION, build_plan_prompt, extract_plan_json, parse_plan_json
        prompt = build_plan_prompt(topic, depth, style, max_nodes, known_samples)
        try:
            resp = self._openai.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": SYSTEM_INSTRUCTION},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2
            )
        except Exception:
            return None
        content = resp.choices[0].message.content
        data = extract_plan_json(content)
        if not data:
            return None
        plan = parse_plan_json(data)
        if not plan:
            self._log.warning("generate_learning_plan.empty_or_parse_fail", topic=topic)
        else:
            self._log.info("generate_learning_plan.success", nodes=len(plan.nodes))
        return plan
