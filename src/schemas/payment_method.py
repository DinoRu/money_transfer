import uuid
from typing import Optional

from pydantic import BaseModel, validator
from pydantic.v1 import root_validator


class PaymentTypeBase(BaseModel):
	type: str
	owner_full_name: str
	phone_number: Optional[str]
	account_number: Optional[str]
	country_id: uuid.UUID

	@root_validator
	def require_at_least_one_contact(cls, values):
		phone = values.get('phone_number')
		account = values.get('account_number')
		if not phone and not account:
			raise ValueError('Phone number or account number must be provided')
		return values


class PaymentTypeCreate(PaymentTypeBase):
	pass


class PaymentTypeRead(PaymentTypeBase):
	id: uuid.UUID


class PaymentTypeUpdate(BaseModel):
	type: Optional[str]
	owner_full_name: Optional[str]
	phone_number: Optional[str] = None
	account_number: Optional[str] = None
	country_id: Optional[uuid.UUID] = None

	@root_validator
	def check_at_least_one_field_updated(cls, values):
		if not any([
			values.get('type'),
			values.get('owner_first_name'),
			values.get('phone_number'),
			values.get('account_number'),
			values.get('country_id'),
		]):
			raise ValueError('At least one field must be updated')
		return values