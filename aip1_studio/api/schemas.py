from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class Payload(BaseModel):
    model_config = ConfigDict(extra="allow")


class LoginRequest(BaseModel):
    username: str
    password: str


class RegisterRequest(LoginRequest):
    display_name: str = ""


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str = Field(min_length=6)


class DraftRequest(BaseModel):
    code: str = ""


class AssignmentRunRequest(DraftRequest):
    case_index: int = 0


class BugTestsRequest(BaseModel):
    test_code: str = ""


class BugFixRequest(BaseModel):
    corrected_code: str


class HumanWorkRequest(BaseModel):
    solution_code: str = ""
    test_code: str = ""


class HumanChatRequest(HumanWorkRequest):
    message: str
    history: list[dict[str, Any]] = Field(default_factory=list)


class EducationVideoRequest(BaseModel):
    question: str = Field(min_length=3, max_length=1000)


class CreateUserRequest(RegisterRequest):
    role: str = "student"


class UnlockRequest(BaseModel):
    user_id: int
    assignment_id: str


class ResetPasswordRequest(BaseModel):
    user_id: int
    password: str = Field(min_length=6)


class BehaviorRequest(BaseModel):
    events: list[dict[str, Any]] = Field(default_factory=list)
