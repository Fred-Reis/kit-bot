from sqlalchemy import select

from db import SessionLocal
from flows.lead_flow import handle_lead_message
from flows.tenant_flow import handle_tenant_message
from models import Lease, User


async def route_message(chat_id: str, message: str) -> None:
    db = SessionLocal()
    try:
        user = db.execute(
            select(User).where(User.whatsapp_id == chat_id)
        ).scalar_one_or_none()

        if not user:
            user = User(whatsapp_id=chat_id, role="lead")
            db.add(user)
            db.commit()
            db.refresh(user)

        lease_exists = db.execute(
            select(Lease.id).where(Lease.tenant_id == user.id).limit(1)
        ).first()

        if lease_exists and user.role != "tenant":
            user.role = "tenant"
            db.commit()
    finally:
        db.close()

    if lease_exists:
        await handle_tenant_message(chat_id, message, user.id)
    else:
        await handle_lead_message(chat_id, message, user.id)
