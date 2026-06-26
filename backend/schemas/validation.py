from pydantic import BaseModel


class ValidationCheck(BaseModel):
    code: str
    level: str
    message: str


class ValidationItemResult(BaseModel):
    quantity: int
    candidate_price: float
    status: str
    risk_level: str
    checks: list[ValidationCheck]


class ValidationSummary(BaseModel):
    item_count: int
    pass_count: int
    info_count: int
    warning_count: int
    error_count: int


class CandidateValidationResponse(BaseModel):
    validation_result_id: int
    candidate_table_id: int
    candidate_table_name: str
    overall_status: str
    risk_level: str
    summary: ValidationSummary
    results: list[ValidationItemResult]
    thresholds: dict[str, float]
    warnings: list[str]
