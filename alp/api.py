from typing import Dict, List, Optional

from fastapi import FastAPI, Depends, HTTPException
from fastapi import Request
from pydantic import BaseModel

from alp.ai.service import OpenAIService, AIService
from alp.graph import GraphService
from alp.logging.config import configure_logging, get_logger
from alp.logging.context import new_request_context, clear_request_context
from alp.logging.instrumentation import init_tracing
from alp.user import UserService

configure_logging()
init_tracing()
api_logger = get_logger("api")
api_logger.info("api.startup")

# Initialize FastAPI app
app = FastAPI(title="Adaptive Learning Platform API", version="1.0")


@app.middleware("http")
async def request_context_mw(request: Request, call_next):
    rid = new_request_context()
    try:
        response = await call_next(request)
        response.headers["X-Request-ID"] = rid
        return response
    finally:
        clear_request_context()


# Instantiate a single AI service instance (for reuse across requests)
_ai_service = OpenAIService()


def get_ai_service() -> AIService:
    """
    Dependency to provide the AIService (can be replaced for testing or different implementations).
    """
    return _ai_service


# Pydantic models for request/response bodies
class OnboardRequest(BaseModel):
    name: str
    answers: Dict[str, str]


class OnboardResponse(BaseModel):
    user_id: str
    name: str
    learning_style: str


class AddNoteRequest(BaseModel):
    user_id: str
    title: str
    content: str
    parent_topic: Optional[str] = None


class AddNoteResponse(BaseModel):
    concept_id: int


class LearningPlanRequest(BaseModel):
    user_id: str
    topic: str
    depth: int
    max_nodes: int


class LearningPlanResponse(BaseModel):
    added: int
    reused: int
    skipped: List[str]


# User onboarding endpoint
@app.post("/users/onboard", response_model=OnboardResponse)
def onboard_user(request: OnboardRequest, ai_service: AIService = Depends(get_ai_service)):
    """
    Onboard a new user by name and answers to questions.
    Returns the created user's ID and detected learning style.
    """
    new_user = UserService.onboard_user(name=request.name, answers=request.answers, ai_service=ai_service)
    return OnboardResponse(user_id=new_user.id, name=new_user.name, learning_style=new_user.learning_style or "")


# Get user profile endpoint
@app.get("/users/{user_id}", response_model=OnboardResponse)
def get_user_profile(user_id: str):
    """
    Retrieve a user's profile by ID.
    """
    user = UserService.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return OnboardResponse(user_id=user.id, name=user.name, learning_style=user.learning_style or "")


# Add a new note (concept) endpoint
@app.post("/notes", response_model=AddNoteResponse)
def add_note(request: AddNoteRequest):
    """
    Add a new note (and concept) to the user's knowledge graph.
    """
    # Ensure the user exists
    user = UserService.get_user_by_id(request.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    concept_id = GraphService.add_note(request.user_id, request.title, request.content, request.parent_topic or None)
    return AddNoteResponse(concept_id=concept_id)


# Generate and inject a learning plan endpoint
@app.post("/learning-plan", response_model=LearningPlanResponse)
def generate_learning_plan(request: LearningPlanRequest, ai_service: AIService = Depends(get_ai_service)):
    """
    Generate a learning plan for the given user and topic, and integrate it into the user's graph.
    """
    user = UserService.get_user_by_id(request.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    plan = ai_service.generate_learning_plan(request.topic, request.depth, user.learning_style or "", request.max_nodes,
                                             known_samples=[])
    if not plan:
        raise HTTPException(status_code=500, detail="Failed to generate learning plan")
    # Load current graph, inject the plan into it
    kg = GraphService.load_graph(request.user_id)
    added, reused, skipped = GraphService.inject_plan(request.user_id, kg, plan, request.depth, request.max_nodes)
    return LearningPlanResponse(added=added, reused=reused, skipped=skipped)
