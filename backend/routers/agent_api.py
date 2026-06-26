from fastapi import APIRouter

from backend.db import get_connection
from backend.schemas.agent import AgentLog
from backend.services.agent_logger import list_agent_logs

router = APIRouter(prefix="/api", tags=["agent-logs"])


@router.get("/agent-logs", response_model=list[AgentLog])
def get_agent_logs(
    pricing_session_id: int | None = None,
    candidate_table_id: int | None = None,
    validation_result_id: int | None = None,
) -> list[dict]:
    with get_connection() as connection:
        return list_agent_logs(
            connection,
            pricing_session_id=pricing_session_id,
            candidate_table_id=candidate_table_id,
            validation_result_id=validation_result_id,
        )
