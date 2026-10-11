"""Lazily load RION secrets through the ECS task role (no static AWS keys)."""

import json
from functools import lru_cache

from .settings import settings


@lru_cache(maxsize=1)
def get_runtime_config() -> dict[str, str]:
    if not settings.runtime_secret_arn:
        return {}
    import boto3

    response = boto3.client("secretsmanager").get_secret_value(SecretId=settings.runtime_secret_arn)
    value = json.loads(response["SecretString"])
    return {str(key): str(item) for key, item in value.items()}
