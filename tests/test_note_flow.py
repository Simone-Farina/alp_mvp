from alp.db.models import User, Concept
from alp.core.graph_ops import create_known_concept
from alp.db.session import SessionLocal, engine
import uuid

def test_note_insert():
    db = SessionLocal()
    user = User(id=str(uuid.uuid4()), name="SAMPLE NAME", learning_style="Visual")
    db.add(user)
    create_known_concept(user, "Algebra", "Sample content", parent_name=None)
    concept=db.query(Concept).filter_by(user_id=user.id, name="Algebra").first()
    assert concept and concept.is_known
    db.close()