import logging

from itsdangerous import URLSafeTimedSerializer
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
	ENV: str
	APP_ENV: str
	APP_DEBUG: bool
	DATABASE_URL: str
	MAIL_USERNAME: str
	MAIL_PASSWORD: str
	MAIL_FROM: str
	MAIL_PORT: int
	MAIL_SERVER: str
	MAIL_FROM_NAME: str
	MAIL_STARTTLS: bool = True
	MAIL_SSL_TLS: bool = False
	USE_CREDENTIALS: bool = True
	VALIDATE_CERTS: bool = True
	TOKEN:str
	SECRET_KEY: str
	ALGORITHM: str
	REFRESH_SECRET_KEY:str
	REDIS_URL: str = "redis://localhost:6379/0"

	POSTGRES_DB: str
	POSTGRES_USER: str
	POSTGRES_PASSWORD: str
	POSTGRES_HOST: str
	POSTGRES_PORT: int
	DB_URL: str
 
	# Database Pool
	DB_POOL_SIZE: int
	DB_MAX_OVERFLOW: int
	DB_POOL_TIMEOUT: int
	DB_POOL_RECYCLE: int
 
	 
    # Application
	APP_NAME: str = "ChapMoney Transfer API"
	APP_VERSION: str = "2.0.0"
	DEBUG: bool = True
 

	# Rate Limiting
	RATE_LIMIT_PER_MINUTE: int = 60
 
	# Pagination
	DEFAULT_PAGE_SIZE: int = 20
	MAX_PAGE_SIZE: int = 100
 
	# Security
	BCRYPT_ROUNDS: int = 12
 
	ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
	REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # CORS
	CORS_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://localhost:8080",
    ]
    


	model_config = SettingsConfigDict(env_file=".env", extra='ignore')

	def active_database_url(self):
		return self.DB_URL if self.ENV == 'docker' else self.DATABASE_URL


settings = Settings()

broker_url = settings.REDIS_URL
result_backend = settings.REDIS_URL
broker_connection_retry_on_startup = True


serializer = URLSafeTimedSerializer(
	secret_key=settings.SECRET_KEY, salt="email-configuration"
)

def create_url_safe_token(data: dict):
	token = serializer.dumps(data)
	return token

def decode_url_safe_token(token: str):
	try:
		token_data = serializer.loads(token)
		return token_data
	except Exception as e:
		logging.error(str(e))
		return None


