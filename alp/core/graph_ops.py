from alp.db.session import SessionLocal
from alp.db.models import Concept, Edge, Note, User


def create_known_concept(user: User, title: str, markdown: str, parent_name: str | None = None):
    """Create Note + Concept(is_known=True) and optional parent edge."""
    db = SessionLocal()
    # 1. insert note
    note = Note(user_id=user.id, title=title, content=markdown)
    db.add(note)
    db.flush()  # to get note.id

    # 2. insert concept
    concept = Concept(
        user_id=user.id,
        name=title,
        content=markdown,
        is_known=True,
    )
    db.add(concept)
    db.flush()

    # 3. if parent given, ensure parent concept exists (unknown if new)
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

    db.commit()
    db.close()
