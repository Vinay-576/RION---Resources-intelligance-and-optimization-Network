"""Optional RDS/PostgreSQL policy lookup using SQLAlchemy bound parameters."""

import json
import logging
from typing import Any

from .schemas import Material, PolicySource
from .settings import settings

logger = logging.getLogger(__name__)
_engine = None


def _get_engine():
    global _engine
    from .aws_runtime_config import get_runtime_config

    database_url = settings.database_url or get_runtime_config().get("database_url", "")
    if not database_url:
        return None
    if _engine is None:
        from sqlalchemy import create_engine

        _engine = create_engine(database_url, pool_pre_ping=True, pool_size=3, max_overflow=2, pool_timeout=5)
    return _engine


def _array(value: Any) -> list[str]:
    if isinstance(value, str):
        value = json.loads(value)
    return [str(item) for item in value or []]


def find_facility_guidance(material: Material, facility_id: str) -> dict[str, object] | None:
    engine = _get_engine()
    if engine is None:
        return None
    from sqlalchemy import text
    from sqlalchemy.exc import SQLAlchemyError

    statement = text(
        "SELECT route, reason, needs_review, possible_outputs, reuse_ideas, policy_title, "
        "policy_url, reviewed_at, is_example FROM facility_material_rules "
        "WHERE facility_id = :facility_id AND material = :material"
    )
    try:
        with engine.connect() as connection:
            row = connection.execute(statement, {"facility_id": facility_id, "material": material}).mappings().first()
    except SQLAlchemyError:
        logger.exception("RION policy database lookup failed; using illustrative in-app guidance")
        return None
    if row is None:
        return None
    return {
        "route": row["route"],
        "reason": row["reason"],
        "needs_review": bool(row["needs_review"]),
        "possible_outputs": _array(row["possible_outputs"]),
        "reuse_ideas": _array(row["reuse_ideas"]),
        "policy_source": PolicySource(
            title=row["policy_title"],
            url=row["policy_url"],
            reviewed_at=row["reviewed_at"].isoformat() if row["reviewed_at"] else None,
            is_example=bool(row["is_example"]),
        ),
    }


def get_facility_policy_version(facility_id: str) -> str | None:
    engine = _get_engine()
    if engine is None:
        return None
    from sqlalchemy import text
    from sqlalchemy.exc import SQLAlchemyError

    try:
        with engine.connect() as connection:
            return connection.execute(
                text(
                    "SELECT policy_version FROM facility_material_rules "
                    "WHERE facility_id = :facility_id ORDER BY policy_version DESC LIMIT 1"
                ),
                {"facility_id": facility_id},
            ).scalar_one_or_none()
    except SQLAlchemyError:
        logger.exception("RION policy version lookup failed; using the built-in version")
        return None
