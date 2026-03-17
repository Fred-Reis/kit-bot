from __future__ import annotations

from sqlalchemy import inspect, select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from config import SEED_MOCK_PROPERTIES
from db import SessionLocal, engine
from logger import get_logger
from models import Property

logger = get_logger("property_catalog")

MOCK_PROPERTIES = [
    {
        "reference": "KIT-01",
        "title": "Kitnet compacta no Centro",
        "category": "kitnet",
        "address": "Rua das Flores, 120",
        "neighborhood": "Centro",
        "bedrooms": 1,
        "bathrooms": 1,
        "monthly_rent": 950,
        "status": "vacant",
        "description": "Kitnet mobiliada, proxima ao comercio local e ao ponto de onibus.",
        "media_json": [],
    },
    {
        "reference": "APT-02",
        "title": "Apartamento de 2 quartos",
        "category": "apartamento",
        "address": "Av. Beira Mar, 450",
        "neighborhood": "Praia do Canto",
        "bedrooms": 2,
        "bathrooms": 2,
        "monthly_rent": 1850,
        "status": "vacant",
        "description": "Apartamento ventilado, com varanda e vaga compartilhada.",
        "media_json": [],
    },
]


def ensure_property_schema() -> None:
    inspector = inspect(engine)
    if "properties" not in inspector.get_table_names():
        return

    existing_columns = {column["name"] for column in inspector.get_columns("properties")}
    statements = []

    column_defs = {
        "reference": "ALTER TABLE properties ADD COLUMN IF NOT EXISTS reference VARCHAR(32)",
        "title": "ALTER TABLE properties ADD COLUMN IF NOT EXISTS title VARCHAR(120)",
        "category": "ALTER TABLE properties ADD COLUMN IF NOT EXISTS category VARCHAR(32)",
        "neighborhood": "ALTER TABLE properties ADD COLUMN IF NOT EXISTS neighborhood VARCHAR(120)",
        "bedrooms": "ALTER TABLE properties ADD COLUMN IF NOT EXISTS bedrooms INTEGER",
        "bathrooms": "ALTER TABLE properties ADD COLUMN IF NOT EXISTS bathrooms INTEGER",
        "monthly_rent": "ALTER TABLE properties ADD COLUMN IF NOT EXISTS monthly_rent INTEGER",
        "status": "ALTER TABLE properties ADD COLUMN IF NOT EXISTS status VARCHAR(32)",
        "description": "ALTER TABLE properties ADD COLUMN IF NOT EXISTS description TEXT",
        "media_json": (
            "ALTER TABLE properties ADD COLUMN IF NOT EXISTS media_json JSONB "
            "DEFAULT '[]'::jsonb NOT NULL"
        ),
    }

    for column, ddl in column_defs.items():
        if column not in existing_columns:
            statements.append(ddl)

    statements.append(
        "CREATE UNIQUE INDEX IF NOT EXISTS ix_properties_reference ON properties (reference)"
    )
    statements.append(
        "CREATE INDEX IF NOT EXISTS ix_properties_status ON properties (status)"
    )

    if not statements:
        return

    try:
        with engine.begin() as connection:
            for ddl in statements:
                connection.execute(text(ddl))
        logger.info("Property schema verified and updated.")
    except SQLAlchemyError as exc:
        logger.exception("Failed to update property schema: %s", exc)


def backfill_property_references(db: Session) -> None:
    properties_without_reference = db.execute(
        select(Property).where(Property.reference.is_(None)).order_by(Property.id.asc())
    ).scalars().all()

    changed = False
    for property_obj in properties_without_reference:
        property_obj.reference = f"IMV-{property_obj.id:02d}"
        if not property_obj.status:
            property_obj.status = "vacant"
        if property_obj.media_json is None:
            property_obj.media_json = []
        changed = True

    if changed:
        db.commit()
        logger.info("Backfilled property references for existing records.")


def seed_mock_properties(db: Session) -> None:
    if not SEED_MOCK_PROPERTIES:
        return

    for payload in MOCK_PROPERTIES:
        existing = db.execute(
            select(Property).where(Property.reference == payload["reference"])
        ).scalar_one_or_none()
        if existing:
            continue

        db.add(Property(**payload))

    db.commit()


def bootstrap_property_catalog() -> None:
    ensure_property_schema()

    db = SessionLocal()
    try:
        backfill_property_references(db)
        seed_mock_properties(db)
    except SQLAlchemyError as exc:
        db.rollback()
        logger.exception("Failed to bootstrap property catalog: %s", exc)
    finally:
        db.close()


def format_currency(value: int | None) -> str:
    if value is None:
        return "sob consulta"
    return f"R$ {value:,.0f}".replace(",", ".")


def serialize_property(property_obj: Property) -> dict:
    return {
        "reference": property_obj.reference,
        "title": property_obj.title or "",
        "category": property_obj.category or "",
        "address": property_obj.address or "",
        "neighborhood": property_obj.neighborhood or "",
        "bedrooms": property_obj.bedrooms,
        "bathrooms": property_obj.bathrooms,
        "monthly_rent": property_obj.monthly_rent,
        "monthly_rent_label": format_currency(property_obj.monthly_rent),
        "status": property_obj.status or "",
        "description": property_obj.description or "",
        "media_count": len(property_obj.media_json or []),
    }


def summarize_property(property_obj: Property) -> str:
    serialized = serialize_property(property_obj)
    parts = [serialized["reference"]]
    if serialized["title"]:
        parts.append(serialized["title"])
    if serialized["neighborhood"]:
        parts.append(serialized["neighborhood"])
    if serialized["monthly_rent_label"]:
        parts.append(serialized["monthly_rent_label"])
    if serialized["bedrooms"]:
        quarto_label = "quarto" if serialized["bedrooms"] == 1 else "quartos"
        parts.append(f"{serialized['bedrooms']} {quarto_label}")
    return " | ".join(parts)


def list_available_properties(db: Session) -> list[Property]:
    return db.execute(
        select(Property)
        .where(Property.status == "vacant")
        .where(Property.reference.is_not(None))
        .order_by(Property.reference.asc())
    ).scalars().all()


def find_property_by_reference(db: Session, reference: str | None) -> Property | None:
    if not reference:
        return None
    return db.execute(
        select(Property).where(Property.reference == reference.upper())
    ).scalar_one_or_none()
