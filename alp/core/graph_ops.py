from alp.db.models import Concept, Edge, Note, User
from alp.db.session import session_scope


def create_known_concept(user: User, title: str, markdown: str, parent_name: str | None = None):
    """Create Note + Concept(is_known=True) and optional parent edge."""
    with session_scope() as db:
        # re-fetch user if needed (user object might be detached)
        # user_id = user.id  (store early)
        note = Note(user_id=user.id, title=title, content=markdown)
        db.add(note)
        db.flush()

        concept = Concept(
            user_id=user.id,
            name=title,
            content=markdown,
            is_known=True,
        )
        db.add(concept)
        db.flush()

        if parent_name:
            parent = (
                db.query(Concept)
                .filter_by(user_id=user.id, name=parent_name)
                .first()
            )
            if not parent:
                parent = Concept(
                    user_id=user.id,
                    name=parent_name,
                    is_known=False,
                    content=None,
                )
                db.add(parent)
                db.flush()
            db.add(Edge(user_id=user.id, source_id=parent.id, target_id=concept.id))
