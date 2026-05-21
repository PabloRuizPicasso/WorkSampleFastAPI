from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


# ── Employee ─────────────────────────────────────────────────────────────────

class EmployeeCreate(BaseModel):
    full_name: str = Field(..., min_length=1, max_length=200)
    position: str = Field(..., min_length=1, max_length=200)
    hired_at: date | None = None

    @field_validator("full_name", "position", mode="before")
    @classmethod
    def strip_whitespace(cls, v: str) -> str:
        if isinstance(v, str):
            v = v.strip()
        return v


class EmployeeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    department_id: int
    full_name: str
    position: str
    hired_at: date | None
    created_at: datetime


# ── Department ────────────────────────────────────────────────────────────────

class DepartmentCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    parent_id: int | None = None

    @field_validator("name", mode="before")
    @classmethod
    def strip_name(cls, v: str) -> str:
        if isinstance(v, str):
            v = v.strip()
        return v


class DepartmentPatch(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    parent_id: int | None = None

    @field_validator("name", mode="before")
    @classmethod
    def strip_name(cls, v: str | None) -> str | None:
        if isinstance(v, str):
            v = v.strip()
        return v


class DepartmentBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    parent_id: int | None
    created_at: datetime


class DepartmentDetail(DepartmentBase):
    employees: list[EmployeeResponse] = []
    children: list["DepartmentDetail"] = []


# Required for self-referencing model
DepartmentDetail.model_rebuild()


# ── Delete params ─────────────────────────────────────────────────────────────

class DeleteMode:
    CASCADE = "cascade"
    REASSIGN = "reassign"
