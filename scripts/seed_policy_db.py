"""Seed RION's illustrative facility rules into PostgreSQL using bound SQL parameters."""

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from sqlalchemy import create_engine, text

from app.catalog import POLICY_VERSION, list_guidance


def main() -> None:
    database_url = os.environ.get("DATABASE_URL", "").strip()
    runtime_secret_arn = os.environ.get("RION_RUNTIME_SECRET_ARN", "").strip()
    if not database_url and runtime_secret_arn:
        import boto3

        value = boto3.client("secretsmanager").get_secret_value(SecretId=runtime_secret_arn)
        database_url = json.loads(value["SecretString"]).get("database_url", "")
    if not database_url:
        raise SystemExit("Set DATABASE_URL from a secure secret source before running this script.")
    schema = Path("infra/aws/db/schema.sql").read_text(encoding="utf-8")
    insert = text(
        "INSERT INTO facility_material_rules "
        "(facility_id, material, route, reason, needs_review, possible_outputs, reuse_ideas, "
        "policy_title, policy_url, reviewed_at, is_example, policy_version) "
        "VALUES (:facility_id, :material, :route, :reason, :needs_review, CAST(:possible_outputs AS JSONB), "
        "CAST(:reuse_ideas AS JSONB), :policy_title, :policy_url, :reviewed_at, :is_example, :policy_version) "
        "ON CONFLICT (facility_id, material) DO UPDATE SET route=EXCLUDED.route, reason=EXCLUDED.reason, "
        "needs_review=EXCLUDED.needs_review, possible_outputs=EXCLUDED.possible_outputs, "
        "reuse_ideas=EXCLUDED.reuse_ideas, policy_title=EXCLUDED.policy_title, policy_url=EXCLUDED.policy_url, "
        "reviewed_at=EXCLUDED.reviewed_at, is_example=EXCLUDED.is_example, policy_version=EXCLUDED.policy_version"
    )
    rows = []
    for item in list_guidance():
        source = item["policy_source"]
        rows.append({
            "facility_id": "example_facility",
            "material": item["material"],
            "route": item["route"],
            "reason": item["reason"],
            "needs_review": item["needs_review"],
            "possible_outputs": json.dumps(item["possible_outputs"]),
            "reuse_ideas": json.dumps(item["reuse_ideas"]),
            "policy_title": source.title,
            "policy_url": source.url,
            "reviewed_at": source.reviewed_at,
            "is_example": source.is_example,
            "policy_version": POLICY_VERSION,
        })
    engine = create_engine(database_url, pool_pre_ping=True)
    with engine.begin() as connection:
        for statement in (part.strip() for part in schema.split(";")):
            if statement:
                connection.execute(text(statement))
        connection.execute(insert, rows)
    print(f"Seeded {len(rows)} explicitly illustrative material rules for example_facility.")
    print("Replace fixture rules with facility-reviewed sources before production use.")


if __name__ == "__main__":
    main()
