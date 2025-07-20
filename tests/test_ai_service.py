from alp.ai.service import OpenAIService, STYLES

def test_detect_learning_style_fallback():
    """The AIService should return a valid style (and use heuristics if no API)."""
    ai = OpenAIService(api_key=None)  # Initialize without API key to force fallback
    answers = {"Q1": "I like watching diagrams", "Q2": "A colorful mind-map"}
    style = ai.detect_learning_style(answers)
    # The heuristic should detect "Visual" from keywords, but ensure it's one of the known styles
    assert style in STYLES
    assert style == "Visual"

def test_suggest_parent_monkeypatch(monkeypatch):
    """Test that suggest_parent_topic can be monkey patched for predictable output."""
    dummy_response = "Mathematics"
    # Monkeypatch OpenAIService.suggest_parent_topic to return a fixed string
    monkeypatch.setattr(OpenAIService, "suggest_parent_topic", lambda self, title, content: dummy_response)
    ai = OpenAIService(api_key=None)
    result = ai.suggest_parent_topic("Limits", "Some content")
    assert result == dummy_response
