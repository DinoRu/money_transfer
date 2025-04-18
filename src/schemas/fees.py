import uuid
from decimal import Decimal

from pydantic import BaseModel

class BaseSchema(BaseModel):
	class Config:
		from_attributes = True

class FeeModel(BaseSchema):
	from_country_id: uuid.UUID
	to_country_id: uuid.UUID
	fee: Decimal


class CreateFee(FeeModel):
	pass

class UpdateFee(BaseSchema):
	fee: float

class FeeView(FeeModel):
	id: uuid.UUID