from __future__ import annotations

from typing import Optional, Dict

from alp.ai.service import AIService
from alp.db.models import User
from alp.db.session import session_scope

from alp.logging.config import get_logger
from alp.logging.instrumentation import traced

log = get_logger("user.service")


class UserService:
    """
    Service layer for user management and onboarding operations.
    """

    @classmethod
    def get_user_by_id(cls, user_id: str) -> Optional[User]:
        """Retrieve a user by their ID (returns None if not found)."""
        with session_scope() as db:
            return db.query(User).filter(User.id == user_id).first()

    @classmethod
    def get_first_user(cls) -> Optional[User]:
        """Retrieve the first user in the database (used for single-user mode)."""
        with session_scope() as db:
            return db.query(User).first()

    @classmethod
    def create_user(cls, name: str, learning_style: Optional[str] = None) -> User:
        """
        Create a new User with the given name and learning_style.
        Returns the newly created User object.
        """
        with session_scope() as db:
            user = User(name=name, learning_style=learning_style)
            db.add(user)
            # Flush to generate user.id; commit will happen on context exit
            db.flush()
            # We can return the user instance (detached after session close, but with fields populated)
            return user

    @classmethod
    @traced("user.onboard")
    def onboard_user(cls, name: str, answers: Dict[str, str], ai_service: AIService) -> User:
        """
        Complete the onboarding process for a new user:
        - Determine learning style via AI service (with fallback).
        - Create and store the new user in the database.
        Returns the new User object.
        """
        log.info("onboard.start", name=name)
        # Determine the user's learning style using the AI service
        style = ai_service.detect_learning_style(answers)
        # Create the user with the derived learning style
        user = cls.create_user(name=name, learning_style=style)
        log.info("onboard.done", user_id=user.id, style=style)
        return user
