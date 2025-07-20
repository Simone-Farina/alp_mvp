from __future__ import annotations

import json
import textwrap
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

# System prompt instruction for generating a curriculum plan
SYSTEM_INSTRUCTION: str = (
    "You are an adaptive curriculum generator. "
    "Given a TARGET TOPIC, DEPTH LEVEL (1=overview,4=deep), USER LEARNING STYLE, "
    "and (optionally) some KNOWN CONCEPT NAMES, produce a dependency set of nodes. "
    "Each node has: name (unique), summary (<=60 words), difficulty (1-4), prerequisites (names). "
    "Return ONLY valid minified JSON—no markdown fences."
)


def build_plan_prompt(topic: str, depth: int, style: str, max_nodes: int, known_samples: List[str]) -> str:
    """
    Construct the prompt to request a learning plan from the AI.
    """
    sample_known = ", ".join(known_samples[:15]) if known_samples else "None"
    # Use textwrap.dedent for consistent formatting
    return textwrap.dedent(f"""\
        TARGET TOPIC: {topic.strip()}
        DEPTH LEVEL: {depth}
        USER LEARNING STYLE: {style}
        MAX NODES: {max_nodes}
        KNOWN CONCEPT SAMPLE: {sample_known}

        Produce up to MAX NODES nodes whose difficulty <= DEPTH LEVEL.
        If foundational concepts lie *above* requested depth, omit them (user can request deeper later).
        JSON SCHEMA:
        {{
          "root_topic": "<string>",
          "nodes": [
            {{
              "name": "<string>",
              "summary": "<<=60 words>",
              "difficulty": <1-4>,
              "prerequisites": ["<other node name>", ...]
            }}
          ]
        }}
    """).strip()


@dataclass
class LearningPlanNode:
    """Represents a single node in a learning plan (concept with summary and prerequisites)."""
    name: str
    summary: str
    difficulty: int
    prerequisites: List[str]


@dataclass
class LearningPlan:
    """Data structure for a generated learning plan containing multiple nodes."""
    root_topic: str
    nodes: List[LearningPlanNode]

    def filtered(self, depth: int, max_nodes: int) -> LearningPlan:
        """
        Return a new LearningPlan with nodes filtered to those <= given depth,
        sorted by difficulty and name, limited to max_nodes.
        """
        selected = [n for n in self.nodes if int(n.difficulty) <= depth]
        selected.sort(key=lambda n: (n.difficulty, n.name.lower()))
        if max_nodes and len(selected) > max_nodes:
            selected = selected[:max_nodes]
        return LearningPlan(self.root_topic, selected)


def extract_plan_json(text: str) -> Optional[Dict[str, Any]]:
    """
    Extract JSON data from the AI's response text. Ignores any Markdown formatting.
    Returns a dict if JSON is found, otherwise None.
    """
    text = text.strip()
    # Remove markdown fences if present
    if text.startswith("```"):
        lines = [ln for ln in text.splitlines() if not ln.strip().startswith("```")]
        text = "\n".join(lines)
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    json_str = text[start:end + 1]
    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        return None


def parse_plan_json(raw: Dict[str, Any]) -> LearningPlan:
    """
    Parse a raw JSON dict (from extract_plan_json) into a LearningPlan object,
    cleaning and validating fields.
    """
    root = (raw.get("root_topic") or raw.get("topic") or "Unknown Topic").strip()
    nodes_list: List[LearningPlanNode] = []
    seen: set[str] = set()
    for node in raw.get("nodes", []):
        name = (node.get("name") or "").strip()
        if not name:
            continue
        lname = name.lower()
        if lname in seen:
            continue  # skip duplicate concept names
        seen.add(lname)
        # Difficulty: ensure int in range 1-4
        diff = node.get("difficulty", 1)
        try:
            diff = int(diff)
        except Exception:
            diff = 1
        diff = max(1, min(4, diff))
        # Prerequisites: ensure list of clean strings
        prereqs = node.get("prerequisites") or []
        if not isinstance(prereqs, list):
            prereqs = []
        prereqs_clean = [p.strip() for p in prereqs if isinstance(p, str) and p.strip()]
        summary = (node.get("summary") or "").strip()
        nodes_list.append(LearningPlanNode(name=name, summary=summary, difficulty=diff, prerequisites=prereqs_clean))
    return LearningPlan(root_topic=root, nodes=nodes_list)
