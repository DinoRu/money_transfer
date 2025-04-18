import uuid
from typing import List

from pydantic import BaseModel

from src.db.models import PaymentType
from src.schemas.payment_method import PaymentTypeRead
from src.schemas.rtype import ReceivingTypeBase, ReceivingTypeRead

class BaseSchema(BaseModel):
    class Config:
        from_attributes = True


class CurrencyCreate(BaseSchema):
    code: str


class CurrencyModel(BaseSchema):
    id: uuid.UUID
    code: str
    name: str
    symbol: str

class CountryBase(BaseSchema):
    name: str
    code_iso: str
    dial_code: str
    phone_pattern: str
    can_send: bool = True

class CountryCreate(CountryBase):
    currency_id: uuid.UUID

class UpdateCountrySchema(CountryBase):
    pass

class CountryModel(CountryBase):
    id: uuid.UUID
    currency: CurrencyModel
    payment_types: List[PaymentTypeRead] = []
    receiving_types: List[ReceivingTypeRead] = []

