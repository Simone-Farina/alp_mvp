# alp/core/learning_plan.py
from __future__ import annotations
import json, textwrap, os
from typing import Any, List, Dict, Optional

try:
    # Expect your ai_helper to expose openai (adjust if different)
    from alp.core.ai_helper import openai
except Exception:
    openai = None  # fallback if not available

SYSTEM_INSTRUCTION = (
    "You are an adaptive curriculum generator. "
    "Given a TARGET TOPIC, DEPTH LEVEL (1=overview,4=deep), USER LEARNING STYLE, "
    "and (optionally) some KNOWN CONCEPT NAMES, produce a dependency set of nodes. "
    "Each node has: name (unique), summary (<=60 words), difficulty (1-4), prerequisites (names). "
    "Return ONLY valid minified JSON—no markdown fences."
)


def build_prompt(topic: str, depth: int, style: str, max_nodes: int, known_samples: list[str]) -> str:
    sample_known = ", ".join(known_samples[:15]) if known_samples else "None"
    return textwrap.dedent(f"""
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


class LearningPlanNode(dict):
    @property
    def name(self) -> str: return self["name"]

    @property
    def prerequisites(self) -> list[str]: return self.get("prerequisites", [])


class LearningPlan:
    def __init__(self, root_topic: str, nodes: List[LearningPlanNode]):
        self.root_topic = root_topic
        self.nodes = nodes

    def filtered(self, depth: int, max_nodes: int) -> LearningPlan:
        sel = [n for n in self.nodes if int(n.get("difficulty", depth)) <= depth]
        sel.sort(key=lambda n: (int(n.get("difficulty", 4)), n["name"].lower()))
        if max_nodes and len(sel) > max_nodes:
            sel = sel[:max_nodes]
        return LearningPlan(self.root_topic, sel)


def _coerce(raw: Dict[str, Any]) -> LearningPlan:
    root = (raw.get("root_topic") or raw.get("topic") or "Unknown Topic").strip()
    clean_nodes: list[LearningPlanNode] = []
    seen = set()
    for node in raw.get("nodes", []):
        name = (node.get("name") or "").strip()
        if not name: continue
        lname = name.lower()
        if lname in seen: continue
        seen.add(lname)
        diff = node.get("difficulty", 1)
        try:
            diff = int(diff)
        except:
            diff = 1
        diff = max(1, min(4, diff))
        prereqs = node.get("prerequisites") or []
        if not isinstance(prereqs, list): prereqs = []
        prereqs_clean = []
        for p in prereqs:
            if isinstance(p, str) and p.strip():
                prereqs_clean.append(p.strip())
        summary = (node.get("summary") or "").strip()
        clean_nodes.append(LearningPlanNode(
            name=name,
            summary=summary,
            difficulty=diff,
            prerequisites=prereqs_clean
        ))
    return LearningPlan(root, clean_nodes)


def _extract_json(text: str) -> Optional[Dict[str, Any]]:
    text = text.strip()
    if text.startswith("```"):
        lines = [ln for ln in text.splitlines() if not ln.strip().startswith("```")]
        text = "\n".join(lines)
    # brute force
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    slice_ = text[start:end + 1]
    try:
        return json.loads(slice_)
    except json.JSONDecodeError:
        return None


def generate_learning_plan(topic: str, depth: int, style: str, max_nodes: int,
                           known_samples: list[str]) -> LearningPlan | None:
    if not (openai and os.getenv("OPENAI_API_KEY")):
        return None
    prompt = build_prompt(topic, depth, style, max_nodes, known_samples)
    resp = openai.ChatCompletion.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_INSTRUCTION},
            {"role": "user", "content": prompt}
        ],
        temperature=0.2,
    )
    content = resp.choices[0].message.content
    parsed = _extract_json(content)
    if not parsed:
        return None
    return _coerce(parsed)
