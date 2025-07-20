def test_plan_logs(caplog, monkeypatch):
    from alp.ai.service import OpenAIService
    ai = OpenAIService(api_key=None)
    caplog.set_level("INFO")
    plan = ai.generate_learning_plan("Recursion", 2, "Visual", 5, [])
    assert "generate_learning_plan" in caplog.text
