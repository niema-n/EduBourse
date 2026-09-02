from typing import Literal

from pydantic import BaseModel, ConfigDict

HealthStatus = Literal["ok", "degraded", "unavailable"]
ComponentStatus = Literal["ok", "unavailable"]
CollectionStatus = Literal["present", "missing", "unknown"]


class ComponentHealth(BaseModel):
    status: ComponentStatus


class VectorStoreHealth(ComponentHealth):
    collection: str
    collection_status: CollectionStatus
    document_count: int = 0


class HealthResponse(BaseModel):
    status: HealthStatus
    app: str
    version: str
    environment: str
    postgres: ComponentHealth
    chroma: VectorStoreHealth

    model_config = ConfigDict(extra="forbid")


class LiveResponse(BaseModel):
    status: Literal["ok"]
    app: str
    version: str

    model_config = ConfigDict(extra="forbid")
