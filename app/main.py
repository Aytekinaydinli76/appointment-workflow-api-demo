from __future__ import annotations

import json
from contextlib import asynccontextmanager
from datetime import UTC, datetime

from fastapi import FastAPI, HTTPException, Query, status

from .database import connect, initialize
from .schemas import (
    AppointmentCreate,
    AppointmentRead,
    AppointmentReschedule,
    AppointmentStatus,
)


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def serialize(row) -> AppointmentRead:
    data = dict(row)
    data["services"] = json.loads(data["services"])
    return AppointmentRead.model_validate(data)


@asynccontextmanager
async def lifespan(_: FastAPI):
    initialize()
    yield


app = FastAPI(
    title="Appointment Workflow API",
    version="1.0.0",
    description=(
        "Production-style demonstration of single and combo-service appointment "
        "creation, cancellation, rescheduling, and lifecycle queries."
    ),
    lifespan=lifespan,
)


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post(
    "/appointments",
    response_model=AppointmentRead,
    status_code=status.HTTP_201_CREATED,
    tags=["appointments"],
)
def create_appointment(payload: AppointmentCreate) -> AppointmentRead:
    timestamp = utc_now()
    with connect() as db:
        cursor = db.execute(
            """
            INSERT INTO appointments
            (customer_name, customer_phone, services, starts_at, status, notes, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                payload.customer_name,
                payload.customer_phone,
                json.dumps(payload.services),
                payload.starts_at.isoformat(),
                AppointmentStatus.confirmed.value,
                payload.notes,
                timestamp,
                timestamp,
            ),
        )
        row = db.execute(
            "SELECT * FROM appointments WHERE id = ?", (cursor.lastrowid,)
        ).fetchone()
    return serialize(row)


@app.get(
    "/appointments",
    response_model=list[AppointmentRead],
    tags=["appointments"],
)
def list_appointments(
    appointment_status: AppointmentStatus | None = Query(
        default=None, alias="status"
    ),
) -> list[AppointmentRead]:
    with connect() as db:
        if appointment_status:
            rows = db.execute(
                "SELECT * FROM appointments WHERE status = ? ORDER BY starts_at",
                (appointment_status.value,),
            ).fetchall()
        else:
            rows = db.execute(
                "SELECT * FROM appointments ORDER BY starts_at"
            ).fetchall()
    return [serialize(row) for row in rows]


@app.get(
    "/appointments/{appointment_id}",
    response_model=AppointmentRead,
    tags=["appointments"],
)
def get_appointment(appointment_id: int) -> AppointmentRead:
    with connect() as db:
        row = db.execute(
            "SELECT * FROM appointments WHERE id = ?", (appointment_id,)
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Appointment not found")
    return serialize(row)


@app.patch(
    "/appointments/{appointment_id}/reschedule",
    response_model=AppointmentRead,
    tags=["appointments"],
)
def reschedule_appointment(
    appointment_id: int, payload: AppointmentReschedule
) -> AppointmentRead:
    with connect() as db:
        current = db.execute(
            "SELECT * FROM appointments WHERE id = ?", (appointment_id,)
        ).fetchone()
        if current is None:
            raise HTTPException(status_code=404, detail="Appointment not found")
        if current["status"] == AppointmentStatus.cancelled.value:
            raise HTTPException(
                status_code=409, detail="Cancelled appointments cannot be rescheduled"
            )
        db.execute(
            "UPDATE appointments SET starts_at = ?, updated_at = ? WHERE id = ?",
            (payload.starts_at.isoformat(), utc_now(), appointment_id),
        )
        row = db.execute(
            "SELECT * FROM appointments WHERE id = ?", (appointment_id,)
        ).fetchone()
    return serialize(row)


@app.post(
    "/appointments/{appointment_id}/cancel",
    response_model=AppointmentRead,
    tags=["appointments"],
)
def cancel_appointment(appointment_id: int) -> AppointmentRead:
    with connect() as db:
        current = db.execute(
            "SELECT * FROM appointments WHERE id = ?", (appointment_id,)
        ).fetchone()
        if current is None:
            raise HTTPException(status_code=404, detail="Appointment not found")
        if current["status"] == AppointmentStatus.cancelled.value:
            raise HTTPException(status_code=409, detail="Appointment already cancelled")
        db.execute(
            "UPDATE appointments SET status = ?, updated_at = ? WHERE id = ?",
            (AppointmentStatus.cancelled.value, utc_now(), appointment_id),
        )
        row = db.execute(
            "SELECT * FROM appointments WHERE id = ?", (appointment_id,)
        ).fetchone()
    return serialize(row)
