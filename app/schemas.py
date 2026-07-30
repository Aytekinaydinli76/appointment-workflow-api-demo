from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field, field_validator


class AppointmentStatus(str, Enum):
    confirmed = "confirmed"
    cancelled = "cancelled"
    completed = "completed"


class AppointmentCreate(BaseModel):
    customer_name: str = Field(min_length=2, max_length=100)
    customer_phone: str = Field(min_length=6, max_length=30)
    services: list[str] = Field(min_length=1, max_length=5)
    starts_at: datetime
    notes: str | None = Field(default=None, max_length=500)

    @field_validator("services")
    @classmethod
    def validate_services(cls, services: list[str]) -> list[str]:
        cleaned = [service.strip() for service in services if service.strip()]
        if not cleaned:
            raise ValueError("At least one service is required")
        if len(set(cleaned)) != len(cleaned):
            raise ValueError("Duplicate services are not allowed")
        return cleaned


class AppointmentReschedule(BaseModel):
    starts_at: datetime


class AppointmentRead(AppointmentCreate):
    id: int
    status: AppointmentStatus
    created_at: datetime
    updated_at: datetime
