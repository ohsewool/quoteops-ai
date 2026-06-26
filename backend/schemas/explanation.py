from pydantic import BaseModel


class CandidateExplanationResponse(BaseModel):
    candidate_table_id: int
    explanation: str
    source: str
    warnings: list[str]
    created_at: str
