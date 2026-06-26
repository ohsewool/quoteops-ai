from typing import Any

from pydantic import BaseModel


class AgentLog(BaseModel):
    id: int
    pricing_session_id: int | None
    candidate_table_id: int | None
    validation_result_id: int | None
    step_type: str
    title: str
    message: str
    status: str
    metadata: dict[str, Any]
    created_at: str
