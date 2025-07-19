from alp.core.ai_helper import detect_learning_style


def test_ai_helper_fallback():
    answers = {"Q1": "I like watching diagrams", "Q2": "A colorful mind-map"}
    style = detect_learning_style(answers)
    assert style in {"Visual", "Kinesthetic", "Analytical", "Auditory"}