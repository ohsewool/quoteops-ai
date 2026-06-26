from pydantic import BaseModel, Field


class AdminPublic(BaseModel):
    id: int
    email: str
    display_name: str
    role: str
    is_active: bool
    created_at: str


class AdminLoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=1, max_length=255)


class AdminLoginResponse(BaseModel):
    access_token: str
    token_type: str
    admin: AdminPublic


class AdminLogoutResponse(BaseModel):
    status: str
    message: str
