"""
Modèle Fee
"""
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional
from sqlalchemy.orm import relationship
from sqlalchemy import Column, Boolean, DateTime, ForeignKey, Index, Numeric
from sqlalchemy.dialects.postgresql import UUID, VARCHAR
from src.models.base import BaseModel



class Fee(BaseModel):
    __tablename__ = "fees"
    # __table_args__ = (
    #     Index("idx_fee_corri", "corridor"),
    # )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    # Devise source
    from_country_id = Column(UUID(as_uuid=True), ForeignKey("countries.id"), nullable=False)
    # Devise cible
    to_country_id = Column(UUID(as_uuid=True), ForeignKey("countries.id"), nullable=False)
    # Types de frais
    fee_type = Column(VARCHAR(20), nullable=False)
    fee_value = Column(Numeric(20, 2), nullable=False)
    # Applicabilité
    min_amount = Column(Numeric(20, 2), nullable=False, server_default="0")
    max_amount = Column(Numeric(20, 2), nullable=True)
    # Métadonnées
    is_active = Column(Boolean, nullable=False, server_default="true")
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
     # Relations
    from_country = relationship(
        "Country",
        foreign_keys=[from_country_id],
        back_populates="fee_from"
    )
    
    to_country = relationship(
        "Country",
        foreign_keys=[to_country_id],
        back_populates="fee_to"
    )
    

    def __repr__(self):
        return f"Fee(id={self.id}, fee_type={self.fee_type})"