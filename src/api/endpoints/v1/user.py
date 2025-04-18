from datetime import datetime
from typing import List

from fastapi import APIRouter, status, HTTPException, Depends, Request
from fastapi.security import HTTPBearer
from sqlmodel import select, or_
from sqlmodel.ext.asyncio.session import AsyncSession

from src.auth.auth import hash_password, verify_password, create_access_token, create_refresh_token, decode_token
from src.auth.dependances import get_current_user
from src.auth.permission import admin_required
from src.config import settings
from src.db.models import User
from src.db.session import get_session
from src.email_service import send_email
from src.schemas.user import UserRead, UserCreate, UserWithToken, UserLogin, UserUpdate, EmailModel


import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

router = APIRouter()

security = HTTPBearer()

smtp_server = "smtp.mailmug.net"
port = 2525
login = "3ilpqpzrmlczkvjh"
password = "059l7cnworh775rb"

sender_mail = "diarra.msa1@gmail.com"
to_mail = "diarra.msa@gmail.com"

message = MIMEMultipart("alternative")
message['From'] = sender_mail
message["To"] = to_mail
message["Subject"] = "Subject here"

async def get_user_or_phone(user_phone: str, session: Depends(get_session)):
    stmt = select(User).where(User.phone == user_phone)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()
    return user


async def authenticate_user(credential: str, password: str, session: AsyncSession = Depends(get_session)):
    # Recherche par email OU téléphone
    stmt = select(User).where(or_(
        User.email == credential,
        User.phone == credential
    ))
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        return None
    if not verify_password(password, user.hash_password):
        return None
    return user

@router.post("/send-mail")
async def send_mail():
    to = "diarra.msa@gmail.com"
    subject = "Confirmation de votre transfert"
    html = """
    <h2>Merci pour votre confiance</h2>
    <p>Votre transfert est en cours de traitement.</p>
    """
    result = send_email(to, subject, html)
    return {"status": "sent", "resend_response": result}

@router.post('/sign-up', response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def create_user(user: UserCreate, session: AsyncSession = Depends(get_session)):
    result = await session.execute(
        select(User).where(User.phone == user.phone)
    )
    existing_user = result.scalar_one_or_none()
    if existing_user:
        raise HTTPException(status_code=400, detail="Phone number already registered")

    hashed_password = hash_password(user.password)
    user_data = User(**user.dict(exclude={'password'}), hash_password=hashed_password)
    session.add(user_data)
    await session.commit()
    await session.refresh(user_data)

    return user_data


@router.post("/login", response_model=UserWithToken)
async def login(user_data: UserLogin, session: AsyncSession = Depends(get_session)):
    user = await authenticate_user(credential=user_data.credential, password=user_data.password, session=session)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Identifiants invalides",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token({'sub': str(user.id)})
    refresh_token = create_refresh_token({"sub": str(user.id)})

    return UserWithToken(
        id=user.id,
        full_name=user.full_name,
        phone=user.phone,
        email=user.email,
        country=user.country,
        role=user.role,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        access_token=access_token,
        refresh_token=refresh_token,
    )

@router.post("/refresh-token")
async def refresh_token(request: Request):
    body = await request.json()
    refresh_token = body.get("refresh_token")
    if not refresh_token:
        raise HTTPException(status_code=400, detail="Refresh token required")
    payload = decode_token(refresh_token, settings.REFRESH_SECRET_KEY)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    user_id = payload.get("sub")
    new_access_token = create_access_token({"sub": user_id})
    return {"access_token": new_access_token}


@router.get("/user-info", status_code=status.HTTP_200_OK, response_model=UserRead)
async def user_info(current_user = Depends(get_current_user)):
    return current_user



@router.get("/", response_model=List[UserRead], dependencies=[Depends(admin_required)])
async def get_all_users(
    session: AsyncSession = Depends(get_session)
):
    stmt = select(User).order_by(User.created_at.desc())
    results = await session.execute(stmt)
    users = results.scalars().all()
    return users


@router.patch("/{user_id}", response_model=UserRead)
async def update_user(
        user_data: UserUpdate,
        user: User = Depends(get_current_user),
        session: AsyncSession = Depends(get_session)
):
    user_data_dict = user_data.model_dump()
    for key, value in user_data_dict.items():
        setattr(user, key, value)
    await session.commit()
    await session.refresh(user)
    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
        user: User = Depends(get_current_user),
        session: AsyncSession = Depends(get_session)
):
    await session.delete(user)
    await session.commit()
    return {"message": "Votre compte a été supprimé avec success!"}