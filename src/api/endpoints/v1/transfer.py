# import os
# import uuid
# from typing import List, Optional, Annotated

# from fastapi import APIRouter, status, HTTPException, Depends, BackgroundTasks, WebSocket, WebSocketDisconnect
# from fastapi_mail import ConnectionConfig, MessageSchema, FastMail
# from sqlalchemy.ext.asyncio.session import AsyncSession
# from sqlalchemy.orm import selectinload
# from sqlmodel import select

# from src.auth.dependances import get_current_user
# from src.auth.permission import agent_or_admin_required
# from src.config import settings
# from src.db.models import Transaction, TransactionStatus, User
# from src.db.session import get_session
# from src.schemas.transfer import TransactionRead, TransactionCreate, TransactionUpdate
# from src.firebase import messaging

# router = APIRouter()


# class ConnectionManager:
# 	def __init__(self):
# 		self.active_connections: List[WebSocket] = []

# 	async def connect(self, websocket: WebSocket):
# 		await websocket.accept()
# 		self.active_connections.append(websocket)

# 	def disconnect(self, websocket: WebSocket):
# 		self.active_connections.remove(websocket)

# 	async def broadcast(self, message: dict):
# 		for connection in self.active_connections:
# 			await connection.send_json(message)

# manager = ConnectionManager()

# mail_conf = ConnectionConfig(
#     MAIL_USERNAME = "diarra.msa",
#     MAIL_PASSWORD = settings.MAIL_PASSWORD,
#     MAIL_FROM = settings.MAIL_FROM,
# 	MAIL_FROM_NAME=settings.MAIL_FROM_NAME,
#     MAIL_PORT = 587,
#     MAIL_SERVER = "smtp.gmail.com",
# 	MAIL_STARTTLS = True,
# 	MAIL_SSL_TLS=False,
#     USE_CREDENTIALS = True,
#     VALIDATE_CERTS = True
# )

# @router.post("/{id}/send-email")
# async def send_deposit_email(
# 		id: uuid.UUID,
# 		bg_tasks: BackgroundTasks,
# 		session: AsyncSession = Depends(get_session)
# ):
# 	transaction = await get_transaction_or_404(id, session)

# 	message = MessageSchema(
# 		subject="Nouveau dépôt confirmé",
# 		recipients=["madibablackpes@gmail.com", "diarra.msa.pro@gmail.com", "diarraOO@bk.ru"],
# 		body=f"""
# 	        <p>Transaction <strong>{transaction.reference}</strong> nécessite validation</p>
# 	        <p><strong>Montant</strong> : {transaction.sender_amount} {transaction.sender_currency}</p>
# 	        <p><strong>Compte</strong> : {transaction.payment_type}</p>
# 	    """,
# 		subtype="html"
# 	)

# 	fm = FastMail(mail_conf)
# 	bg_tasks.add_task(fm.send_message, message)
# 	return {"message": "Email envoyé avec succès 🎉"}


# async def get_transaction_or_404(id: uuid.UUID, session: AsyncSession = Depends(get_session)):
# 	stmt = select(Transaction).options(selectinload(Transaction.sender)).where(Transaction.id == id)
# 	result = await session.execute(stmt)
# 	transaction = result.scalar_one_or_none()
# 	return transaction

# @router.post("/", status_code=status.HTTP_201_CREATED, response_model=TransactionRead)
# async def create_transaction(
# 		transaction_data: TransactionCreate,
# 		sender: User = Depends(get_current_user),
# 		session: AsyncSession = Depends(get_session)
# ):
# 	transaction = Transaction(**transaction_data.dict(), sender_id=sender.id)
# 	session.add(transaction)
# 	await session.commit()
# 	await session.refresh(transaction)

# 	#Envoyer la notification
# 	await manager.broadcast({
# 		"type": "NEW_TRANSACTION",
# 		"data": {
# 			"id": str(transaction.id),
# 			"reference": transaction.reference,
# 			"amount": float(transaction.sender_amount),
# 			"currency": transaction.sender_currency,
# 			"status": transaction.status
# 		}
# 	})



# 	return transaction


# @router.websocket("/ws/transactions")
# async def websocket_endpoint(websocket: WebSocket):
# 	await manager.connect(websocket)
# 	try:
# 		while True:
# 			await websocket.receive_text()
# 	except WebSocketDisconnect:
# 		manager.disconnect(websocket)

# @router.get("/", response_model=List[TransactionRead])
# async def get_transactions(
# 		status: Optional[TransactionStatus] = None,
# 		page: int = 1,
# 		limit: int = 100,
# 		session: AsyncSession = Depends(get_session)
# ):
# 	stmt = select(Transaction).options(selectinload(Transaction.sender)).order_by(Transaction.timestamp.desc())

# 	if status:
# 		stmt = stmt.where(Transaction.status == status)

# 	results = await session.execute(stmt.offset((page-1)*limit).limit(limit))
# 	transactions = results.scalars().all()
# 	return transactions


# @router.get("/{id}", response_model=TransactionRead, status_code=status.HTTP_200_OK)
# async def get_transaction(
# 		transaction = Depends(get_transaction_or_404)
# ):
# 	return transaction


# @router.patch("/{id}", response_model=TransactionRead, dependencies=[Depends(agent_or_admin_required)])
# async def update_transaction_status(
# 		update_data: TransactionUpdate,
# 		transaction = Depends(get_transaction_or_404),
# 		user: User = Depends(get_current_user),
# 		session: AsyncSession = Depends(get_session),
# ):
# 	previous_status = transaction.status
# 	if update_data.status:
# 		transaction.status = update_data.status
# 	session.add(transaction)
# 	await session.commit()
# 	await session.refresh(transaction)

# 	# Envoyer une notification
# 	if previous_status != transaction.status:
# 		await manager.broadcast({
# 			"type": "STATUS_CHANGE",
# 			"data": {
# 				"id": str(transaction.id),
# 				"reference": transaction.reference,
# 				"old_status": previous_status,
# 				"new_status": transaction.status
# 			}
# 		})
# 	if transaction.status == TransactionStatus.COMPLETED:
# 		token = settings.TOKEN
# 		message = messaging.Message(
# 			notification=messaging.Notification(
# 			title="Transaction Validée ✅",
# 			body=f"Votre transaction de {transaction.sender_amount} {transaction.sender_currency} a été approuvée !",
# 		),
# 			token=token,
# 			data={
# 				"transaction_id": str(transaction.id),
# 				"type": "TRANSACTION_UPDATE"
# 			}
# 		)
# 		messaging.send(message)
# 	return transaction



# @router.get('/reference/{reference}', response_model=TransactionRead)
# async def get_transaction_by_reference_or_404(reference: str, session: AsyncSession = Depends(get_session)):
# 	stmt = select(Transaction).where(Transaction.reference == reference)
# 	result = await session.execute(stmt)
# 	transaction = result.scalar_one_or_none()
# 	if not transaction:
# 		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found")
# 	return transaction


# @router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
# async def delete_transaction(
# 		transaction = Depends(get_transaction_or_404),
# 		session: AsyncSession = Depends(get_session)
# ):
# 	await session.delete(transaction)
# 	await session.commit()
# 	return {"message": "Transaction supprimée avec succès"}