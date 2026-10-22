
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_access_without_token_is_rejected():
    response = client.get("/customers/me")

    assert response.status_code == 401


def test_register_and_login():
    import uuid

    unique_email = f"{uuid.uuid4().hex}@example.com"

    # Register a new customer
    register_response = client.post(
        "/register",
        json={
            "name": "Test Customer",
            "email": unique_email,
            "password": "TestPassword123!"
        },
    )

    assert register_response.status_code in (200, 201)

    # Log in with the same credentials
    login_response = client.post(
        "/login",
        data={
            "username": unique_email,
            "password": "TestPassword123!"
        },
    )

    assert login_response.status_code == 200
    assert "access_token" in login_response.json()


def test_duplicate_event_is_stored_only_once():
    import uuid

    # Create a test customer
    email = f"{uuid.uuid4().hex}@example.com"
    register_response = client.post(
        "/register",
        json={
            "name": "Duplicate Test Customer",
            "email": email,
            "password": "TestPassword123!",
        },
    )
    assert register_response.status_code in (200, 201)
    customer_id = register_response.json()["id"]

    # Log in to get an access token
    login_response = client.post(
        "/login",
        data={
            "username": email,
            "password": "TestPassword123!",
        },
    )
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Submit the same event twice
    event = [{
        "event_id": f"duplicate-{uuid.uuid4().hex}",
        "customer_id": customer_id,
        "event_type": "voice",
        "quantity": 10,
        "timestamp": "2026-10-21T12:00:00Z",
    }]

    first_response = client.post(
        "/events", json=event, headers=headers
    )
    second_response = client.post(
        "/events", json=event, headers=headers
    )

    assert first_response.status_code in (200, 201)
    assert second_response.status_code in (200, 201)
    assert first_response.json()["stored"] == 1
    assert second_response.json()["stored"] == 0
    assert second_response.json()["duplicates_ignored"] == 1


def test_charge_preview_calculation():
    import uuid
    from datetime import datetime, timezone
    from database import SessionLocal
    from models import RatePlan

    email = f"{uuid.uuid4().hex}@example.com"

    # Register a customer
    register_response = client.post(
        "/register",
        json={
            "name": "Charge Test Customer",
            "email": email,
            "password": "TestPassword123!",
        },
    )
    assert register_response.status_code in (200, 201)
    customer_id = register_response.json()["id"]

    # Log in
    login_response = client.post(
        "/login",
        data={
            "username": email,
            "password": "TestPassword123!",
        },
    )
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Ensure the database has the intended test rates
    db = SessionLocal()
    try:
        plan = db.query(RatePlan).first()
        if plan is None:
            plan = RatePlan(
                name="Test Plan",
                voice_price=2.00,
                sms_price=3.00,
                data_price=1.00,
            )
            db.add(plan)
        else:
            plan.voice_price = 2.00
            plan.sms_price = 3.00
            plan.data_price = 1.00
        db.commit()
    finally:
        db.close()

    # Add a voice event
    event_response = client.post(
        "/events",
        json=[{
            "event_id": f"charge-{uuid.uuid4().hex}",
            "customer_id": customer_id,
            "event_type": "voice",
            "quantity": 10,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }],
        headers=headers,
    )
    assert event_response.status_code in (200, 201)

    # Request the charge preview
    preview_response = client.get(
        f"/customers/{customer_id}/charge-preview",
        params={
            "from": "2026-01-01T00:00:00Z",
            "to": "2027-01-01T00:00:00Z",
        },
        headers=headers,
    )
    assert preview_response.status_code == 200

    result = preview_response.json()
    assert result["usage"]["voice"]["quantity"] == 10
    assert result["usage"]["voice"]["charge"] == 20
