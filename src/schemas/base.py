"""
Schemas de base pour Pydantic
"""
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class BaseSchema(BaseModel):
    """Schema de base avec configuration commune"""
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        use_enum_values=True,
        arbitrary_types_allowed=True
    )


class TimestampMixin(BaseModel):
    """Mixin pour les timestamps"""
    created_at: datetime
    updated_at: datetime


class IDMixin(BaseModel):
    """Mixin pour l'identifiant UUID"""
    id: UUID