from sqlalchemy.exc import IntegrityError
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from models import Customer, UsageEvent, RatePlan
from schemas import UsageEventInput
from fastapi import FastAPI, Depends, HTTPException, status, Form, Query
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy import func
import jwt
from schemas import (
    RegisterRequest,
    LoginRequest,
    CustomerResponse,
    UsageEventInput,
    UsageEventResponse,
)

from database import get_db
from models import Customer
from schemas import RegisterRequest, LoginRequest, CustomerResponse
from auth import (
    hash_password,
    verify_password,
    create_access_token,
    get_customer_id_from_token,
)

app = FastAPI(title="Usage Event API")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")


def get_current_customer(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
):
    try:
        customer_id = get_customer_id_from_token(token)
    except (jwt.InvalidTokenError, ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    customer = db.query(Customer).filter(
        Customer.id == customer_id
    ).first()

    if customer is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Customer not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return customer


@app.get("/")
def home():
    return {"message": "Usage Event API is running!"}


@app.post(
    "/register",
    response_model=CustomerResponse,
    status_code=status.HTTP_201_CREATED,
)
def register(
    request: RegisterRequest,
    db: Session = Depends(get_db),
):
    customer = Customer(
        name=request.name,
        email=str(request.email).lower(),
        password_hash=hash_password(request.password),
    )

    db.add(customer)

    try:
        db.commit()
        db.refresh(customer)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A customer with this email already exists",
        )

    return customer


@app.post("/login")
def login(
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    email = username.lower()

    customer = db.query(Customer).filter(
        Customer.email == email
    ).first()

    if customer is None or not verify_password(
        password,
        customer.password_hash,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = create_access_token(customer.id)

    return {
        "access_token": token,
        "token_type": "bearer",
    }


@app.get("/customers/me", response_model=CustomerResponse)
def get_my_profile(
    customer: Customer = Depends(get_current_customer),
):
    return customer



@app.post("/events", status_code=status.HTTP_201_CREATED)
def create_events(
    events: UsageEventInput | list[UsageEventInput],
    customer: Customer = Depends(get_current_customer),
    db: Session = Depends(get_db),
):
    event_list = events

    # Accept a single event as well as a list of events.
    if not isinstance(event_list, list):
        event_list = [event_list]

    if not event_list:
        raise HTTPException(
            status_code=400,
            detail="At least one event is required",
        )

    if len(event_list) > 1000:
        raise HTTPException(
            status_code=400,
            detail="Maximum 1000 events per request",
        )

    rows = []

    for event in event_list:
        if event.customer_id != customer.id:
            raise HTTPException(
                status_code=403,
                detail="You can only submit events for your own customer account",
            )

        rows.append({
            "event_id": event.event_id,
            "customer_id": event.customer_id,
            "event_type": event.event_type,
            "quantity": event.quantity,
            "timestamp": event.timestamp,
        })

    statement = (
        insert(UsageEvent)
        .values(rows)
        .on_conflict_do_nothing(index_elements=["event_id"])
        .returning(UsageEvent.event_id)
    )

    inserted = db.execute(statement).scalars().all()
    db.commit()

    return {
        "received": len(rows),
        "stored": len(inserted),
        "duplicates_ignored": len(rows) - len(inserted),
        "stored_event_ids": inserted,
    }



from datetime import datetime


@app.get("/events", response_model=list[UsageEventResponse])
def get_events(
    customer_id: int | None = None,
    event_type: str | None = None,
    from_date: datetime | None = Query(default=None, alias="from"),
    to_date: datetime | None = Query(default=None, alias="to"),
    customer: Customer = Depends(get_current_customer),
    db: Session = Depends(get_db),
):
    # Customers can only access their own usage events.
    if customer_id is not None and customer_id != customer.id:
        raise HTTPException(
            status_code=403,
            detail="You can only view your own usage events",
        )

    if event_type is not None and event_type not in {
        "voice", "sms", "data"
    }:
        raise HTTPException(
            status_code=422,
            detail="event_type must be voice, sms, or data",
        )

    if from_date is not None and to_date is not None:
        if from_date > to_date:
            raise HTTPException(
                status_code=400,
                detail="'from' must be earlier than or equal to 'to'",
            )

    query = db.query(UsageEvent).filter(
        UsageEvent.customer_id == customer.id
    )

    if event_type is not None:
        query = query.filter(UsageEvent.event_type == event_type)

    if from_date is not None:
        query = query.filter(UsageEvent.timestamp >= from_date)

    if to_date is not None:
        query = query.filter(UsageEvent.timestamp <= to_date)

    return query.order_by(UsageEvent.timestamp.desc()).all()

@app.get("/customers/{customer_id}/charge-preview")
def charge_preview(
    customer_id: int,
    from_date: datetime = Query(alias="from"),
    to_date: datetime = Query(alias="to"),
    customer: Customer = Depends(get_current_customer),
    db: Session = Depends(get_db),
):
    if customer_id != customer.id:
        raise HTTPException(
            status_code=403,
            detail="You can only preview your own charges",
        )

    if from_date > to_date:
        raise HTTPException(
            status_code=400,
            detail="'from' must be earlier than or equal to 'to'",
        )

    rate_plan = db.query(RatePlan).first()

    if rate_plan is None:
        raise HTTPException(
            status_code=500,
            detail="No rate plan has been configured",
        )

    rows = (
        db.query(
            UsageEvent.event_type,
            func.sum(UsageEvent.quantity).label("total_quantity"),
        )
        .filter(UsageEvent.customer_id == customer_id)
        .filter(UsageEvent.timestamp >= from_date)
        .filter(UsageEvent.timestamp <= to_date)
        .group_by(UsageEvent.event_type)
        .all()
    )

    totals = {
        "voice": {"quantity": 0, "unit_price": rate_plan.voice_price, "charge": 0},
        "sms": {"quantity": 0, "unit_price": rate_plan.sms_price, "charge": 0},
        "data": {"quantity": 0, "unit_price": rate_plan.data_price, "charge": 0},
    }

    for row in rows:
        usage_type = row.event_type
        quantity = float(row.total_quantity or 0)
        unit_price = totals[usage_type]["unit_price"]

        totals[usage_type]["quantity"] = quantity
        totals[usage_type]["charge"] = round(quantity * unit_price, 2)

    total_charge = round(
        sum(item["charge"] for item in totals.values()),
        2,
    )

    return {
        "customer_id": customer_id,
        "from": from_date,
        "to": to_date,
        "usage": totals,
        "total_charge": total_charge,
    }
