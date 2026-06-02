# seed.py - create the first company + admin user from environment variables.
import os

from sqlalchemy.orm import Session

from .auth import hash_password
from .database import SessionLocal
from .models import Company, User


def seed_initial_data():
    company_name = os.getenv("COMPANY_NAME", "My Company")
    admin_email = os.getenv("ADMIN_EMAIL", "admin@example.com")
    admin_password = os.getenv("ADMIN_PASSWORD", "admin12345")

    db: Session = SessionLocal()
    try:
        if db.query(User).first():
            return  # already seeded

        company = Company(
            name=company_name,
            system_prompt=os.getenv("DEFAULT_SYSTEM_PROMPT") or None,
        )
        db.add(company)
        db.flush()

        db.add(
            User(
                company_id=company.id,
                email=admin_email,
                password_hash=hash_password(admin_password),
                role="admin",
            )
        )
        db.commit()
        print(f"🌱 Seeded company '{company_name}' with admin '{admin_email}'.")
    finally:
        db.close()
