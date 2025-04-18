import uuid
from decimal import Decimal

from pydantic import BaseModel


class BaseSchema(BaseModel):
	class Config:
		from_attributes = True


class RateRequest(BaseModel):
	base_code: str
	conversion_rates: dict


class Rates(BaseModel):
	quote: Decimal


class ConvertRequestModel(BaseModel):
	base: str
	to: str
	amount: Decimal


class ConvertResponseModel(BaseModel):
	base: str
	to: str
	amount: Decimal
	rates: Rates
	result: Decimal


class ExchangeRate(BaseSchema):
	from_currency_id: uuid.UUID
	to_currency_id: uuid.UUID


class CreateExchangeRate(ExchangeRate):
	rate: Decimal


class UpdateExchangeRate(ExchangeRate):
	rate: Decimal


class ExchangeRateRead(ExchangeRate):
	id: uuid.UUID
	rate: Decimal
