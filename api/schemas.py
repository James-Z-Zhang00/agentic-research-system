from pydantic import BaseModel, Field


class ResearchRequest(BaseModel):
    query: str = Field(min_length=10, max_length=2000)
    session_id: str | None = None


class ResearchResponse(BaseModel):
    session_id: str
    synthesis: str
    critic_score: dict
    requires_hitl: bool


class HITLItem(BaseModel):
    session_id: str
    synthesis: str
    critic_score: dict
