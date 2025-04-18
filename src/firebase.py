import os
import firebase_admin
from firebase_admin import credentials, messaging


current_dir = os.path.dirname(__file__)
service_account_path = os.path.abspath(
    os.path.join(current_dir, '..', 'service.json')
)

if not firebase_admin._apps:
    cred = credentials.Certificate(service_account_path)
    firebase_admin.initialize_app(cred)


__all__ = ["messaging"]
