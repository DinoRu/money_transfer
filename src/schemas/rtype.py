import uuid
from typing import Optional

from pydantic import BaseModel


class ReceivingTypeBase(BaseModel):
	type: str
	country_id: uuid.UUID


class ReceivingTypeCreate(ReceivingTypeBase):
	pass

class ReceivingTypeRead(ReceivingTypeBase):
	id: uuid.UUID

class ReceivingTypeUpdate(BaseModel):
	type: Optional[str] = None
	country_id: Optional[uuid.UUID] = None
