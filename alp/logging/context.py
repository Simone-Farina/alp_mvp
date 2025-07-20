import uuid
import structlog

def new_request_context():
    rid = str(uuid.uuid4())
    structlog.contextvars.bind_contextvars(request_id=rid)
    return rid

def clear_request_context():
    structlog.contextvars.clear_contextvars()
