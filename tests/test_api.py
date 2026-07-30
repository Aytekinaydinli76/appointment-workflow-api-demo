from fastapi.testclient import TestClient

from app.database import connect, initialize
from app.main import app


def setup_function() -> None:
    initialize()
    with connect() as db:
        db.execute("DELETE FROM appointments")


def sample_payload() -> dict:
    return {
        "customer_name": "Demo Customer",
        "customer_phone": "+212600000000",
        "services": ["Haircut", "Color"],
        "starts_at": "2026-08-01T10:00:00+01:00",
        "notes": "Combo-service demonstration",
    }


def test_full_appointment_lifecycle() -> None:
    with TestClient(app) as client:
        created = client.post("/appointments", json=sample_payload())
        assert created.status_code == 201
        appointment_id = created.json()["id"]
        assert created.json()["services"] == ["Haircut", "Color"]

        rescheduled = client.patch(
            f"/appointments/{appointment_id}/reschedule",
            json={"starts_at": "2026-08-02T14:30:00+01:00"},
        )
        assert rescheduled.status_code == 200
        assert rescheduled.json()["starts_at"].startswith("2026-08-02T14:30:00")

        cancelled = client.post(f"/appointments/{appointment_id}/cancel")
        assert cancelled.status_code == 200
        assert cancelled.json()["status"] == "cancelled"

        rejected = client.patch(
            f"/appointments/{appointment_id}/reschedule",
            json={"starts_at": "2026-08-03T10:00:00+01:00"},
        )
        assert rejected.status_code == 409


def test_rejects_duplicate_services() -> None:
    payload = sample_payload()
    payload["services"] = ["Haircut", "Haircut"]
    with TestClient(app) as client:
        response = client.post("/appointments", json=payload)
    assert response.status_code == 422
