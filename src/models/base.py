"""
Modèle de base avec fonctionnalités communes
"""
import uuid
from datetime import datetime
from typing import Any
from sqlalchemy import Column, DateTime, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import declared_attr
from src.db.session import Base


class TimestampMixin:
    """Mixin pour ajouter created_at et updated_at à tous les modèles"""
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, 
        default=datetime.utcnow, 
        onupdate=datetime.utcnow, 
        nullable=False
    )


class BaseModel(Base, TimestampMixin):
    """Modèle de base abstrait pour tous les modèles"""
    
    __abstract__ = True
    
    id = Column(UUID(as_uuid=True), primary_key=True, index=True, default=uuid.uuid4)
    
    def to_dict(self) -> dict[str, Any]:
        """Convertir le modèle en dictionnaire"""
        return {
            column.name: getattr(self, column.name)
            for column in self.__table__.columns
        }
    
    def __repr__(self) -> str:
        """Représentation string du modèle"""
        attrs = ", ".join(
            f"{key}={value!r}"
            for key, value in self.to_dict().items()
        )
        return f"{self.__class__.__name__}({attrs})" 