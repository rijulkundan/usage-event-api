
from database import SessionLocal
from models import RatePlan

db = SessionLocal()

try:
    existing_plan = db.query(RatePlan).first()

    if existing_plan:
        existing_plan.name = "Default Plan"
        existing_plan.voice_price = 2.00
        existing_plan.sms_price = 3.00
        existing_plan.data_price = 1.00

        db.commit()
        print("Rate plan updated successfully!")

    else:
        plan = RatePlan(
            name="Default Plan",
            voice_price=2.00,
            sms_price=3.00,
            data_price=1.00,
        )

        db.add(plan)
        db.commit()
        print("Default rate plan created successfully!")

finally:
    db.close()
