def test_suggest_parent_mock(monkeypatch):
    from alp.core import parent_suggester
    def fake_call(title, content):
        return "Mathematics"

    monkeypatch.setattr(parent_suggester, "suggest_parent_via_ai", fake_call)
    assert fake_call("Limits", "Some content") == "Mathematics"
