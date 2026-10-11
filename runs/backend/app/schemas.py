from typing import Literal

from pydantic import BaseModel, Field

Material = Literal[
    "steel",
    "metal",
    "rubber",
    "PET",
    "HDPE",
    "PVC",
    "LDPE",
    "PP",
    "PS",
    "mixed_plastic",
    "glass",
    "paper_cardboard",
    "battery",
    "organic",
    "textile",
    "composite",
    "other_waste",
    "unknown",
]
Route = Literal["recyclable", "reusable", "refuse_processing", "needs_review"]


class BoundingBox(BaseModel):
    x1: float = Field(ge=0, le=1)
    y1: float = Field(ge=0, le=1)
    x2: float = Field(ge=0, le=1)
    y2: float = Field(ge=0, le=1)


class PolicySource(BaseModel):
    title: str
    url: str | None = None
    reviewed_at: str | None = None
    is_example: bool = True


class Detection(BaseModel):
    box: BoundingBox
    object_label: str
    material: Material
    confidence: float = Field(ge=0, le=1)
    route: Route
    reason: str
    needs_review: bool
    policy_source: PolicySource
    possible_outputs: list[str]
    reuse_ideas: list[str]


class ClassificationResponse(BaseModel):
    request_id: str
    model_version: str
    policy_version: str
    policy_mode: Literal["illustrative"]
    facility_id: str
    detections: list[Detection]
    notice: str

