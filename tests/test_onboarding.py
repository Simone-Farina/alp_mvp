from alp.user import UserService
from alp.ai.service import OpenAIService

def test_onboard_user(monkeypatch):
    """Test that onboarding a new user uses the AI service and creates a User with a learning style."""
    # Monkeypatch the AI service's learning style detection to return a fixed value
    dummy_style = "Visual"
    monkeypatch.setattr(OpenAIService, "detect_learning_style", lambda self, answers, use_gpt=False: dummy_style)
    # Perform onboarding
    new_user = UserService.onboard_user(name="Test User", answers={"Q1": "X", "Q2": "Y"}, ai_service=OpenAIService())
    # Verify the user is created with the expected style and name
    assert new_user.id is not None
    assert new_user.name == "Test User"
    assert new_user.learning_style == dummy_style
