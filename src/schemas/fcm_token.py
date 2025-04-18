import uuid

from pydantic import BaseModel


class BaseSchema(BaseModel):
	class Config:
		from_attributes = True


class FCMToken(BaseSchema):
	pk: uuid.UUID
	token: str

class TokenRequest(BaseSchema):
	token: str