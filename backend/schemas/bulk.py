from pydantic import BaseModel


class ImportRowError(BaseModel):
    row: int
    field: str
    message: str


class CsvImportResponse(BaseModel):
    status: str
    valid_count: int
    error_count: int
    inserted_count: int
    errors: list[ImportRowError]
