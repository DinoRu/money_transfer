from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from src.api.endpoints.v1 import currency, rates, country, receiving_type, payment_method, fees, fcm_token, exchange_rates, transfer, user, \
    healthcheck

version = 'v1'
app = FastAPI(
    title="Money transfer",
    version=version
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# app.include_router(healthcheck.router, tags=['Health Check'])
# app.include_router(currency.router, prefix=f"/api/{version}/currency", tags=['Currency'])
# app.include_router(rates.router, prefix=f"/api/{version}/currency", tags=['Rate'])
# app.include_router(country.router, prefix=f"/api/{version}/country", tags=['Country'])
# app.include_router(receiving_type.router, prefix=f"/api/{version}/receiving-type", tags=['Receiving types'])
# app.include_router(payment_method.router, prefix=f"/api/{version}/payment-type", tags=['Payment types'])
# app.include_router(transfer.router, prefix=f"/api/{version}/transactions", tags=['Transactions'])
# app.include_router(fees.router, prefix=f"/api/{version}/fees", tags=['Fees'])
# app.include_router(fcm_token.router, prefix=f"/api/{version}/tokens", tags=['Tokens'])
# app.include_router(exchange_rates.router, prefix=f"/api/{version}/exchange-rates", tags=['Exchange Rates'])
# app.include_router(user.router, prefix=f"/api/{version}/users", tags=['Users'])





@app.get("/")
def home():
    return {"message": "Bienvenue sur l'API de conversion et de transfert d'argent"}
