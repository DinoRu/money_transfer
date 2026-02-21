from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from uuid import UUID
from typing import List, Optional, Tuple
from dataclasses import dataclass

from fastapi import APIRouter, Query, status, HTTPException, Depends, BackgroundTasks, WebSocket, WebSocketDisconnect
from fastapi_mail import ConnectionConfig, MessageSchema, FastMail
from sqlalchemy.ext.asyncio.session import AsyncSession
from sqlalchemy.orm import selectinload
from sqlmodel import select

from src.auth.dependances import get_current_user
from src.auth.permission import agent_or_admin_required
from src.config import settings
from src.db.models import (
    Country, ExchangeRates, Fee, PaymentType, ReceivingType, 
    Transaction, TransactionStatus, User
)
from src.db.session import get_session
from src.schemas.transaction import (
    TransactionRead, TransactionCreate, TransactionUpdate, 
    TransferEstimateRequest, TransferEstimateResponse, 
    TransferLimits, TransferMethodsResponse, 
    TransferPreviewRequest, TransferPreviewResponse, 
    TransferQuoteRequest, TransferQuoteResponse
)
from src.firebase import messaging

router = APIRouter()

# =============================================================================
# CONSTANTS
# =============================================================================

HUNDRED = Decimal("100")
DEFAULT_SCALE = Decimal("0.01")
QUOTE_EXPIRY_MINUTES = 30
DEFAULT_ESTIMATED_FEE = Decimal("5.0")


# =============================================================================
# WEBSOCKET MANAGER
# =============================================================================

class ConnectionManager:
    """Gestionnaire de connexions WebSocket pour les notifications en temps réel"""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        """Diffuse un message à toutes les connexions actives"""
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                disconnected.append(connection)
        
        # Nettoyer les connexions mortes
        for conn in disconnected:
            self.disconnect(conn)


manager = ConnectionManager()


# =============================================================================
# MAIL CONFIGURATION
# =============================================================================

mail_conf = ConnectionConfig(
    MAIL_USERNAME="diarra.msa",
    MAIL_PASSWORD=settings.MAIL_PASSWORD,
    MAIL_FROM=settings.MAIL_FROM,
    MAIL_FROM_NAME=settings.MAIL_FROM_NAME,
    MAIL_PORT=587,
    MAIL_SERVER="smtp.gmail.com",
    MAIL_STARTTLS=True,
    MAIL_SSL_TLS=False,
    USE_CREDENTIALS=True,
    VALIDATE_CERTS=True
)


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class TransferCalculation:
    """Résultat des calculs de transfert"""
    sender_amount: Decimal
    receiver_amount: Decimal
    total_to_pay: Decimal
    fee_value: Decimal
    fee_percent: Decimal
    exchange_rate: Decimal


# =============================================================================
# UTILITY FUNCTIONS - DATABASE
# =============================================================================

async def get_country_with_methods(
    country_id: UUID,
    session: AsyncSession
) -> Country:
    """
    Récupère un pays avec toutes ses méthodes de paiement et de réception
    
    Args:
        country_id: ID du pays
        session: Session de base de données
        
    Returns:
        Country: Objet pays avec relations chargées
        
    Raises:
        HTTPException: Si le pays n'existe pas
    """
    stmt = select(Country).options(
        selectinload(Country.currency),
        selectinload(Country.payment_types),
        selectinload(Country.receiving_types)
    ).where(Country.id == country_id)
    
    result = await session.execute(stmt)
    country = result.scalar_one_or_none()
    
    if not country:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pays avec l'ID {country_id} non trouvé"
        )
    
    return country


async def get_exchange_rate(
    from_currency_id: UUID,
    to_currency_id: UUID,
    session: AsyncSession
) -> ExchangeRates:
    """
    Récupère le taux de change entre deux devises
    
    Args:
        from_currency_id: ID de la devise source
        to_currency_id: ID de la devise destination
        session: Session de base de données
        
    Returns:
        ExchangeRates: Taux de change
        
    Raises:
        HTTPException: Si le taux n'existe pas
    """
    stmt = select(ExchangeRates).options(
        selectinload(ExchangeRates.from_currency),
        selectinload(ExchangeRates.to_currency)
    ).where(
        ExchangeRates.from_currency_id == from_currency_id,
        ExchangeRates.to_currency_id == to_currency_id
    )
    
    result = await session.execute(stmt)
    rate = result.scalar_one_or_none()
    
    if not rate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Taux de change non trouvé pour cette paire de devises"
        )
    
    return rate


async def get_fee(
    from_country_id: UUID,
    to_country_id: UUID,
    amount: Decimal,
    session: AsyncSession
) -> Optional[Fee]:
    """
    Récupère les frais applicables pour un transfert
    
    Args:
        from_country_id: ID du pays source
        to_country_id: ID du pays destination
        amount: Montant du transfert
        session: Session de base de données
        
    Returns:
        Optional[Fee]: Frais applicables ou None
    """
    stmt = select(Fee).where(
        Fee.from_country_id == from_country_id,
        Fee.to_country_id == to_country_id
    )
    
    result = await session.execute(stmt)
    fee = result.scalar_one_or_none()
    
    return fee


async def get_payment_method(
    payment_type_id: UUID,
    country_id: UUID,
    session: AsyncSession
) -> PaymentType:
    """
    Récupère une méthode de paiement et valide qu'elle appartient au pays
    
    Args:
        payment_type_id: ID de la méthode de paiement
        country_id: ID du pays pour validation
        session: Session de base de données
        
    Returns:
        PaymentType: Méthode de paiement
        
    Raises:
        HTTPException: Si la méthode n'existe pas ou n'appartient pas au pays
    """
    stmt = select(PaymentType).where(PaymentType.id == payment_type_id)
    result = await session.execute(stmt)
    payment_method = result.scalar_one_or_none()
    
    if not payment_method:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Méthode de paiement avec l'ID {payment_type_id} non trouvée"
        )
    
    if payment_method.country_id != country_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La méthode de paiement n'appartient pas au pays source"
        )
    
    return payment_method


async def get_receiving_method(
    receiving_type_id: UUID,
    country_id: UUID,
    session: AsyncSession
) -> ReceivingType:
    """
    Récupère une méthode de réception et valide qu'elle appartient au pays
    
    Args:
        receiving_type_id: ID de la méthode de réception
        country_id: ID du pays pour validation
        session: Session de base de données
        
    Returns:
        ReceivingType: Méthode de réception
        
    Raises:
        HTTPException: Si la méthode n'existe pas ou n'appartient pas au pays
    """
    stmt = select(ReceivingType).where(ReceivingType.id == receiving_type_id)
    result = await session.execute(stmt)
    receiving_method = result.scalar_one_or_none()
    
    if not receiving_method:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Méthode de réception avec l'ID {receiving_type_id} non trouvée"
        )
    
    if receiving_method.country_id != country_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La méthode de réception n'appartient pas au pays destination"
        )
    
    return receiving_method


async def get_transaction_or_404(
    transaction_id: UUID,
    session: AsyncSession = Depends(get_session)
) -> Transaction:
    """
    Récupère une transaction ou lève une erreur 404
    
    Args:
        transaction_id: ID de la transaction
        session: Session de base de données
        
    Returns:
        Transaction: Transaction avec relations chargées
        
    Raises:
        HTTPException: Si la transaction n'existe pas
    """
    stmt = select(Transaction).options(
        selectinload(Transaction.sender)
    ).where(Transaction.id == transaction_id)
    
    result = await session.execute(stmt)
    transaction = result.scalar_one_or_none()
    
    if not transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Transaction avec l'ID {transaction_id} non trouvée"
        )
    
    return transaction


# =============================================================================
# UTILITY FUNCTIONS - CALCULATIONS
# =============================================================================

def calculate_transfer_amounts(
    amount: Decimal,
    exchange_rate: Decimal,
    fee_percent: Decimal,
    include_fee: bool,
    scale: Decimal = DEFAULT_SCALE,
) -> Tuple[Decimal, Decimal, Decimal, Decimal]:
    """
    Calcule les montants du transfert avec frais
    
    Args:
        amount: Montant entré par l'utilisateur
        exchange_rate: Taux de change
        fee_percent: Pourcentage de frais
        include_fee: Si True, les frais sont inclus dans le montant
        scale: Précision des calculs
        
    Returns:
        Tuple: (sender_amount, receiver_amount, total_to_pay, fee_value)
        
    Example:
        >>> calculate_transfer_amounts(
        ...     amount=Decimal("100"),
        ...     exchange_rate=Decimal("0.92"),
        ...     fee_percent=Decimal("5"),
        ...     include_fee=False
        ... )
        (Decimal("100.00"), Decimal("92.00"), Decimal("105.00"), Decimal("5.00"))
    """
    
    # Calcul du montant de frais
    fee_value = (amount * fee_percent / HUNDRED).quantize(
        scale, rounding=ROUND_HALF_UP
    )
    
    if include_fee:
        # Les frais sont INCLUS dans le montant
        # Le montant envoyé = montant saisi
        # Montant réel à convertir = montant - frais
        # Montant reçu = montant_reel * taux
        sender_amount = amount
        amount_to_convert = (amount - fee_value).quantize(
            scale, rounding=ROUND_HALF_UP
        )
        receiver_amount = (amount_to_convert * exchange_rate).quantize(
            scale, rounding=ROUND_HALF_UP
        )
        total_to_pay = sender_amount
    else:
        # Les frais sont AJOUTÉS au montant
        # Le montant envoyé = montant saisi
        # Montant reçu = montant * taux
        # Total à payer = montant + frais
        sender_amount = amount
        receiver_amount = (amount * exchange_rate).quantize(
            scale, rounding=ROUND_HALF_UP
        )
        total_to_pay = (amount + fee_value).quantize(
            scale, rounding=ROUND_HALF_UP
        )
    
    return sender_amount, receiver_amount, total_to_pay, fee_value


def create_breakdown(
    sender_amount: Decimal,
    receiver_amount: Decimal,
    total_to_pay: Decimal,
    fee_value: Decimal,
    exchange_rate: Decimal,
    from_currency_code: str,
    to_currency_code: str,
    include_fee: bool
) -> dict:
    """
    Crée le détail du transfert pour l'affichage
    
    Args:
        sender_amount: Montant envoyé
        receiver_amount: Montant reçu
        total_to_pay: Total à payer
        fee_value: Montant des frais
        exchange_rate: Taux de change
        from_currency_code: Code devise source
        to_currency_code: Code devise destination
        include_fee: Si les frais sont inclus
        
    Returns:
        dict: Détails formatés du transfert
    """
    return {
        "you_send": f"{float(sender_amount):.2f} {from_currency_code}",
        "fee": f"{float(fee_value):.2f} {from_currency_code}",
        "fee_included": include_fee,
        "total_to_pay": f"{float(total_to_pay):.2f} {from_currency_code}",
        "exchange_rate": f"1 {from_currency_code} = {float(exchange_rate):.4f} {to_currency_code}",
        "they_receive": f"{float(receiver_amount):.2f} {to_currency_code}"
    }
    
    
def build_payment_instructions(
    payment_type: PaymentType,
) -> dict:
    return {
        "type": payment_type.type,
        "owner_name": payment_type.owner_full_name,
        "phone_number": payment_type.phone_number,
        "account_number": payment_type.account_number,
        # "note": (
        #     "Envoyez exactement le montant indiqué"
        #     if is_mobile_money
        #     else "Indiquez la référence dans le commentaire du virement"
        # ),
    }



async def perform_transfer_calculation(
    from_country_id: UUID,
    to_country_id: UUID,
    amount: Decimal,
    include_fee: bool,
    session: AsyncSession
) -> TransferCalculation:
    """
    Effectue tous les calculs nécessaires pour un transfert
    
    Args:
        from_country_id: ID pays source
        to_country_id: ID pays destination
        amount: Montant du transfert
        include_fee: Si les frais sont inclus
        session: Session de base de données
        
    Returns:
        TransferCalculation: Résultats des calculs
    """
    # Récupérer les pays
    from_country = await get_country_with_methods(from_country_id, session)
    to_country = await get_country_with_methods(to_country_id, session)
    
    # Vérifier si l'envoi est autorisé
    if not from_country.can_send:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Les transferts depuis {from_country.name} ne sont pas autorisés"
        )
    
    # Récupérer le taux de change
    rate = await get_exchange_rate(
        from_country.currency_id,
        to_country.currency_id,
        session
    )
    
    # Récupérer les frais
    fee = await get_fee(
        from_country_id,
        to_country_id,
        amount,
        session
    )
    
    fee_percent = fee.fee if fee else Decimal('0')
    
    # Calculer les montants
    sender_amount, receiver_amount, total_to_pay, fee_value = calculate_transfer_amounts(
        amount,
        rate.rate,
        fee_percent,
        include_fee
    )
    
    return TransferCalculation(
        sender_amount=sender_amount,
        receiver_amount=receiver_amount,
        total_to_pay=total_to_pay,
        fee_value=fee_value,
        fee_percent=fee_percent,
        exchange_rate=rate.rate
    )


# =============================================================================
# UTILITY FUNCTIONS - NOTIFICATIONS
# =============================================================================

async def send_notification_email(
    transaction: Transaction,
    background_tasks: BackgroundTasks
):
    """
    Envoie un email de notification pour un nouveau dépôt
    
    Args:
        transaction: Transaction concernée
        background_tasks: FastAPI background tasks
    """
    message = MessageSchema(
        subject="Nouveau dépôt confirmé",
        recipients=[
            "madibablackpes@gmail.com",
            "diarra.msa.pro@gmail.com",
            "diarraOO@bk.ru"
        ],
        body=f"""
        <html>
            <body>
                <h2>Nouvelle transaction nécessitant validation</h2>
                <p><strong>Référence:</strong> {transaction.reference}</p>
                <p><strong>Montant:</strong> {transaction.sender_amount} {transaction.sender_currency}</p>
                <p><strong>De:</strong> {transaction.sender_country}</p>
                <p><strong>Vers:</strong> {transaction.receiver_country}</p>
                <p><strong>Destinataire:</strong> {transaction.recipient_name}</p>
                <p><strong>Téléphone:</strong> {transaction.recipient_phone}</p>
                <p><strong>Méthode de paiement:</strong> {transaction.payment_method}</p>
                <p><strong>Méthode de réception:</strong> {transaction.receiving_method}</p>
            </body>
        </html>
        """,
        subtype="html"
    )
    
    fm = FastMail(mail_conf)
    background_tasks.add_task(fm.send_message, message)


async def send_push_notification(transaction: Transaction):
    """
    Envoie une notification push Firebase
    
    Args:
        transaction: Transaction concernée
    """
    try:
        token = settings.TOKEN
        message = messaging.Message(
            notification=messaging.Notification(
                title="Transaction Validée ✅",
                body=f"Votre transaction de {transaction.sender_amount} {transaction.sender_currency} a été approuvée !",
            ),
            token=token,
            data={
                "transaction_id": str(transaction.id),
                "reference": transaction.reference,
                "type": "TRANSACTION_UPDATE"
            }
        )
        messaging.send(message)
    except Exception as e:
        # Log l'erreur mais ne fait pas échouer la requête
        print(f"Erreur lors de l'envoi de la notification push: {e}")


# =============================================================================
# TRANSACTION ENDPOINTS - CRUD
# =============================================================================

@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=TransactionRead,
    summary="Créer une nouvelle transaction",
    description="Crée une nouvelle transaction après validation complète du preview"
)
async def create_transaction(
    transaction_data: TransactionCreate,
    sender: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Crée une nouvelle transaction dans le système
    
    Cette route est appelée après que l'utilisateur a validé le preview
    et confirmé tous les détails du transfert.
    """
    # Créer la transaction
    transaction = Transaction(
        **transaction_data.dict(),
        sender_id=sender.id
    )
    
    session.add(transaction)
    await session.commit()
    await session.refresh(transaction)
    
    # Charger les relations
    await session.refresh(transaction, ["sender"])
    
    # Envoyer notification WebSocket
    await manager.broadcast({
        "type": "NEW_TRANSACTION",
        "data": {
            "id": str(transaction.id),
            "reference": transaction.reference,
            "amount": float(transaction.sender_amount),
            "currency": transaction.sender_currency,
            "status": transaction.status,
            "timestamp": transaction.timestamp.isoformat()
        }
    })
    
    return transaction


@router.get(
    "",
    response_model=List[TransactionRead],
    summary="Liste des transactions",
    description="Récupère la liste des transactions avec filtres et pagination"
)
async def get_transactions(
    status: Optional[TransactionStatus] = Query(None, description="Filtrer par statut"),
    page: int = Query(1, ge=1, description="Numéro de page"),
    limit: int = Query(100, ge=1, le=100, description="Nombre d'éléments par page"),
    session: AsyncSession = Depends(get_session)
):
    """Liste toutes les transactions avec pagination et filtres optionnels"""
    stmt = select(Transaction).options(
        selectinload(Transaction.sender)
    ).order_by(Transaction.timestamp.desc())
    
    if status:
        stmt = stmt.where(Transaction.status == status)
    
    # Pagination
    offset = (page - 1) * limit
    stmt = stmt.offset(offset).limit(limit)
    
    results = await session.execute(stmt)
    transactions = results.scalars().all()
    
    return transactions


@router.get(
    "/{transaction_id}",
    response_model=TransactionRead,
    status_code=status.HTTP_200_OK,
    summary="Détails d'une transaction",
    description="Récupère les détails complets d'une transaction par son ID"
)
async def get_transaction(
    transaction: Transaction = Depends(get_transaction_or_404)
):
    """Récupère une transaction spécifique par son ID"""
    return transaction


@router.get(
    "/reference/{reference}",
    response_model=TransactionRead,
    summary="Transaction par référence",
    description="Récupère une transaction par son numéro de référence"
)
async def get_transaction_by_reference(
    reference: str,
    session: AsyncSession = Depends(get_session)
):
    """Récupère une transaction par sa référence unique"""
    stmt = select(Transaction).options(
        selectinload(Transaction.sender)
    ).where(Transaction.reference == reference)
    
    result = await session.execute(stmt)
    transaction = result.scalar_one_or_none()
    
    if not transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Transaction avec la référence {reference} non trouvée"
        )
    
    return transaction


@router.patch(
    "/{id}",
    response_model=TransactionRead,
    dependencies=[Depends(agent_or_admin_required)],
    summary="Mettre à jour une transaction",
    description="Met à jour le statut d'une transaction (agents et admins uniquement)"
)
async def update_transaction_status(
    update_data: TransactionUpdate,
    transaction: Transaction = Depends(get_transaction_or_404),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Met à jour le statut d'une transaction
    
    Envoie des notifications WebSocket et push lorsque le statut change
    """
    previous_status = transaction.status
    
    if update_data.status:
        transaction.status = update_data.status
    
    session.add(transaction)
    await session.commit()
    await session.refresh(transaction, ["sender"])
    
    # Notifier le changement de statut
    if previous_status != transaction.status:
        await manager.broadcast({
            "type": "STATUS_CHANGE",
            "data": {
                "id": str(transaction.id),
                "reference": transaction.reference,
                "old_status": previous_status,
                "new_status": transaction.status,
                "updated_by": user.full_name,
                "timestamp": datetime.utcnow().isoformat()
            }
        })
        
        # Envoyer notification push si transaction complétée
        if transaction.status == TransactionStatus.COMPLETED:
            await send_push_notification(transaction)
    
    return transaction


@router.delete(
    "/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(agent_or_admin_required)],
    summary="Supprimer une transaction",
    description="Supprime une transaction (agents et admins uniquement)"
)
async def delete_transaction(
    transaction: Transaction = Depends(get_transaction_or_404),
    session: AsyncSession = Depends(get_session)
):
    """Supprime une transaction du système"""
    await session.delete(transaction)
    await session.commit()
    return None


@router.post(
    "/{id}/send-email",
    summary="Envoyer email de notification",
    description="Envoie un email de notification pour une transaction"
)
async def send_deposit_email(
    id: UUID,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session)
):
    """Envoie un email de notification pour un nouveau dépôt"""
    transaction = await get_transaction_or_404(id, session)
    await send_notification_email(transaction, background_tasks)
    
    return {
        "message": "Email envoyé avec succès 🎉",
        "reference": transaction.reference
    }


# =============================================================================
# TRANSFER FLOW ENDPOINTS
# =============================================================================

@router.get(
    "/methods",
    response_model=TransferMethodsResponse,
    status_code=status.HTTP_200_OK,
    summary="Méthodes de transfert disponibles",
    description="Récupère les méthodes de paiement et de réception pour une route"
)
async def get_transfer_methods(
    from_country_id: UUID = Query(..., description="ID du pays source"),
    to_country_id: UUID = Query(..., description="ID du pays destination"),
    session: AsyncSession = Depends(get_session)
):
    """
    Étape 1 du flow de transfert : Récupère les méthodes disponibles
    
    Appelé quand l'utilisateur sélectionne les pays source et destination
    pour afficher les options de paiement et réception disponibles.
    
    Example:
        GET /transfer/methods?from_country_id=xxx&to_country_id=yyy
    """
    # Récupérer les deux pays avec leurs méthodes
    from_country = await get_country_with_methods(from_country_id, session)
    to_country = await get_country_with_methods(to_country_id, session)
    
    # Vérifier si le transfert est possible
    can_transfer = from_country.can_send
    message = None
    
    if not can_transfer:
        message = f"Les transferts depuis {from_country.name} ne sont pas autorisés"
    elif not from_country.payment_types:
        can_transfer = False
        message = f"Aucune méthode de paiement disponible pour {from_country.name}"
    elif not to_country.receiving_types:
        can_transfer = False
        message = f"Aucune méthode de réception disponible pour {to_country.name}"
    
    return TransferMethodsResponse(
        from_country=from_country,
        to_country=to_country,
        payment_methods=from_country.payment_types,
        receiving_methods=to_country.receiving_types,
        can_transfer=can_transfer,
        message=message
    )


@router.post(
    "/quote",
    response_model=TransferQuoteResponse,
    status_code=status.HTTP_200_OK,
    summary="Calculer un devis de transfert",
    description="Calcule tous les montants et frais pour un transfert"
)
async def get_transfer_quote(
    quote_request: TransferQuoteRequest,
    session: AsyncSession = Depends(get_session)
):
    """
    Étape 2 du flow de transfert : Calcule le devis
    
    Appelé quand l'utilisateur entre un montant pour afficher
    combien il paiera et combien sera reçu.
    
    Example request:
        POST /transfer/quote
        {
            "from_country_id": "uuid-france",
            "to_country_id": "uuid-senegal",
            "amount": 100,
            "include_fee": false
        }
    
    Example response:
        {
            "sender_amount": 100.00,
            "fee_amount": 5.00,
            "total_to_pay": 105.00,
            "receiver_amount": 65500.00,
            "exchange_rate": 655.00,
            ...
        }
    """
    # Récupérer les pays
    from_country = await get_country_with_methods(
        quote_request.from_country_id,
        session
    )
    to_country = await get_country_with_methods(
        quote_request.to_country_id,
        session
    )
    
    # Effectuer les calculs
    calc = await perform_transfer_calculation(
        quote_request.from_country_id,
        quote_request.to_country_id,
        quote_request.amount,
        quote_request.include_fee,
        session
    )
    
    # Créer le détail
    breakdown = create_breakdown(
        calc.sender_amount,
        calc.receiver_amount,
        calc.total_to_pay,
        calc.fee_value,
        calc.exchange_rate,
        from_country.currency.code,
        to_country.currency.code,
        quote_request.include_fee
    )
    
    # Calculer la date d'expiration du taux
    rate_expires_at = datetime.utcnow() + timedelta(minutes=QUOTE_EXPIRY_MINUTES)
    
    return TransferQuoteResponse(
        from_country_id=from_country.id,
        from_country_name=from_country.name,
        from_currency=from_country.currency.code,
        from_currency_symbol=from_country.currency.symbol,
        to_country_id=to_country.id,
        to_country_name=to_country.name,
        to_currency=to_country.currency.code,
        to_currency_symbol=to_country.currency.symbol,
        sender_amount=float(calc.sender_amount),
        receiver_amount=float(calc.receiver_amount),
        exchange_rate=float(calc.exchange_rate),
        fee_amount=float(calc.fee_value),
        fee_included=quote_request.include_fee,
        total_to_pay=float(calc.total_to_pay),
        breakdown=breakdown,
        rate_expires_at=rate_expires_at,
        estimated_delivery="Instant"
    )


@router.post(
    "/preview",
    response_model=TransferPreviewResponse,
    status_code=status.HTTP_200_OK,
    summary="Prévisualiser un transfert complet",
    description="Affiche le récapitulatif complet avant confirmation"
)
async def get_transfer_preview(
    preview_request: TransferPreviewRequest,
    session: AsyncSession = Depends(get_session)
):
    """
    Étape 3 du flow de transfert : Preview complet avant confirmation
    
    Affiche TOUS les détails du transfert incluant :
    - Montants calculés
    - Méthodes de paiement et réception choisies
    - Informations du destinataire
    - Récapitulatif détaillé
    
    L'utilisateur voit cet écran avant de confirmer définitivement le transfert.
    
    Example request:
        POST /transfer/preview
        {
            "from_country_id": "uuid-france",
            "to_country_id": "uuid-senegal",
            "amount": 100,
            "include_fee": false,
            "payment_type_id": "uuid-card",
            "receiving_type_id": "uuid-mobile",
            "recipient_name": "Amadou Diallo",
            "recipient_phone": "+221701234567"
        }
    """
    # Validation : Méthodes requises
    if not preview_request.payment_type_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La méthode de paiement est requise pour le preview"
        )
    
    if not preview_request.receiving_type_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La méthode de réception est requise pour le preview"
        )
    
    # Validation : Informations destinataire requises
    if not preview_request.recipient_name or not preview_request.recipient_name.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Le nom du destinataire est requis"
        )
    
    if not preview_request.recipient_phone or not preview_request.recipient_phone.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Le téléphone du destinataire est requis"
        )
    
    # Récupérer les pays
    from_country = await get_country_with_methods(
        preview_request.from_country_id,
        session
    )
    to_country = await get_country_with_methods(
        preview_request.to_country_id,
        session
    )
    
    # Effectuer les calculs
    calc = await perform_transfer_calculation(
        preview_request.from_country_id,
        preview_request.to_country_id,
        preview_request.amount,
        preview_request.include_fee,
        session
    )
    
    # Récupérer et valider les méthodes
    payment_method = await get_payment_method(
        preview_request.payment_type_id,
        from_country.id,
        session
    )
    
    receiving_method = await get_receiving_method(
        preview_request.receiving_type_id,
        to_country.id,
        session
    )
    
    # Créer le détail
    breakdown = create_breakdown(
        calc.sender_amount,
        calc.receiver_amount,
        calc.total_to_pay,
        calc.fee_value,
        calc.exchange_rate,
        from_country.currency.code,
        to_country.currency.code,
        preview_request.include_fee
    )
    
    return TransferPreviewResponse(
        # Informations pays et devises
        from_country_id=from_country.id,
        from_country_name=from_country.name,
        from_currency=from_country.currency.code,
        from_currency_symbol=from_country.currency.symbol,
        to_country_id=to_country.id,
        to_country_name=to_country.name,
        to_currency=to_country.currency.code,
        to_currency_symbol=to_country.currency.symbol,
        
        # Montants calculés
        sender_amount=float(calc.sender_amount),
        receiver_amount=float(calc.receiver_amount),
        exchange_rate=float(calc.exchange_rate),
        fee_value=float(calc.fee_value),
        fee_included=preview_request.include_fee,
        total_to_pay=float(calc.total_to_pay),
        
        # Informations destinataire
        recipient_name=preview_request.recipient_name.strip(),
        recipient_phone=preview_request.recipient_phone.strip(),
        
        # Méthodes choisies
        payment_method=payment_method.type,
        receiving_method=receiving_method.type,
        
        # Payment instructions
        payment_instructions=build_payment_instructions(payment_type=payment_method),
        
        # Détail pour affichage
        breakdown=breakdown
    )


# =============================================================================
# ADDITIONAL ENDPOINTS
# =============================================================================

@router.post(
    "/estimate",
    response_model=TransferEstimateResponse,
    status_code=status.HTTP_200_OK,
    summary="Estimation rapide",
    description="Calcul rapide basé uniquement sur les devises (pour calculatrice)"
)
async def get_quick_estimate(
    estimate_request: TransferEstimateRequest,
    session: AsyncSession = Depends(get_session)
):
    """
    Estimation rapide pour une calculatrice sur l'écran d'accueil
    
    Ne nécessite que les codes de devises, pas les pays complets.
    Utile pour donner une idée rapide à l'utilisateur.
    """
    # Récupérer les devises
    from sqlmodel import select
    from src.db.models import Currency
    
    stmt_from = select(Currency).where(
        Currency.code == estimate_request.from_currency.upper()
    )
    stmt_to = select(Currency).where(
        Currency.code == estimate_request.to_currency.upper()
    )
    
    result_from = await session.execute(stmt_from)
    result_to = await session.execute(stmt_to)
    
    from_currency = result_from.scalar_one_or_none()
    to_currency = result_to.scalar_one_or_none()
    
    if not from_currency or not to_currency:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Devise non trouvée"
        )
    
    # Récupérer le taux
    rate = await get_exchange_rate(
        from_currency.id,
        to_currency.id,
        session
    )
    
    # Calculs simples
    send_amount = Decimal(str(estimate_request.amount))
    receive_amount = send_amount * rate.rate
    estimated_fee = DEFAULT_ESTIMATED_FEE
    total_to_pay = send_amount + estimated_fee
    
    summary = (
        f"Envoyez {float(send_amount):.2f} {from_currency.code}, "
        f"le destinataire recevra {float(receive_amount):.2f} {to_currency.code} "
        f"(frais estimés: {float(estimated_fee):.2f} {from_currency.code})"
    )
    
    return TransferEstimateResponse(
        send_amount=float(send_amount),
        receive_amount=float(receive_amount),
        exchange_rate=float(rate.rate),
        estimated_fee=float(estimated_fee),
        total_to_pay=float(total_to_pay),
        summary=summary
    )


@router.get(
    "/limits",
    response_model=TransferLimits,
    status_code=status.HTTP_200_OK,
    summary="Limites de transfert",
    description="Récupère les limites pour une route de transfert"
)
async def get_transfer_limits(
    from_country_id: UUID = Query(..., description="ID du pays source"),
    to_country_id: UUID = Query(..., description="ID du pays destination"),
    session: AsyncSession = Depends(get_session)
):
    """
    Récupère les limites de transfert pour une route spécifique
    
    Peut être étendu pour inclure des limites personnalisées
    basées sur le niveau KYC de l'utilisateur.
    """
    from_country = await get_country_with_methods(from_country_id, session)
    
    # Limites par défaut (devraient être en base de données)
    # TODO: Récupérer depuis la base de données
    # TODO: Adapter selon le niveau KYC de l'utilisateur
    return TransferLimits(
        from_country_id=from_country_id,
        to_country_id=to_country_id,
        min_amount=10.0,
        max_amount=10000.0,
        daily_limit=5000.0,
        monthly_limit=50000.0,
        currency=from_country.currency.code
    )


# ============================================
# PATCH /transactions/{id}/confirm-payment
# ============================================

@router.patch("/{transaction_id}/confirm-payment")
async def confirm_payment(
    transaction_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    Confirmer qu'un paiement a été effectué
    
    Change le statut de "pending" → "processing"
    
    Flow:
    1. Vérifier que la transaction existe
    2. Vérifier qu'elle appartient au user
    3. Vérifier que le statut est "pending"
    4. Vérifier que le timer n'a pas expiré
    5. Changer le statut → "processing"
    6. Enregistrer l'heure de confirmation
    """
    
    # Récupérer la transaction
    transaction = await get_transaction_or_404(transaction_id, session)
    if transaction.sender_id != current_user.id:
        raise HTTPException(
            status_code=404,
            detail="Transaction non trouvée"
        )
    
    # Vérifier le statut
    if transaction.status != "pending":
        raise HTTPException(
            status_code=400,
            detail=f"Impossible de confirmer: statut actuel est '{transaction.status}'"
        )
    
    # Vérifier le timer (15 minutes max)
    elapsed_time = datetime.utcnow() - transaction.created_at
    if elapsed_time > timedelta(minutes=15):
        # Annuler automatiquement si expiré
        transaction.status = "cancelled"
        transaction.updated_at = datetime.utcnow()
        await session.commit()
        
        raise HTTPException(
            status_code=400,
            detail="Le délai de 15 minutes est écoulé. Transaction annulée."
        )
    
    # Confirmer le paiement
    transaction.status = "processing"  # ou "Dépôt confirmé"
    transaction.updated_at = datetime.utcnow()
    
    # TODO: Enregistrer d'autres informations
    # transaction.payment_confirmed_at = datetime.utcnow()
    
    await session.commit()
    await session.refresh(transaction)
    
    # TODO: Envoyer notification au user
    # TODO: Notifier l'admin pour vérification
    
    return transaction


# ============================================
# PATCH /transactions/{id}/cancel
# ============================================

@router.patch("/{transaction_id}/cancel")
async def cancel_transaction(
    transaction_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    Annuler une transaction
    
    Change le statut de "pending" → "cancelled"
    
    Peut être déclenché par:
    - L'utilisateur manuellement
    - Le timer automatiquement après 15 minutes
    """
    
    # Récupérer la transaction
    result = await session.execute(
        select(Transaction).where(
            Transaction.id == transaction_id,
            Transaction.sender_id == current_user.id,
        )
    )
    transaction = result.scalar_one_or_none()
    
    if not transaction:
        raise HTTPException(
            status_code=404,
            detail="Transaction non trouvée"
        )
    
    # Vérifier que la transaction peut être annulée
    if transaction.status not in ["pending", "processing"]:
        raise HTTPException(
            status_code=400,
            detail=f"Impossible d'annuler: statut actuel est '{transaction.status}'"
        )
    
    # Annuler la transaction
    transaction.status = "cancelled"  # ou "Annulée"
    transaction.updated_at = datetime.utcnow()
    
    # TODO: Rembourser si des fonds ont été débités
    # TODO: Libérer les ressources
    
    await session.commit()
    await session.refresh(transaction)
    
    # TODO: Envoyer notification au user
    
    return transaction


# ============================================
# GET /transactions/{id}/status
# ============================================

@router.get("/{transaction_id}/status")
async def get_transaction_status(
    transaction_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    Obtenir le statut d'une transaction en temps réel
    """
    
    # Récupérer la transaction
    result = await session.execute(
        select(Transaction).where(
            Transaction.id == transaction_id,
            Transaction.sender_id == current_user.id,
        )
    )
    transaction = result.scalar_one_or_none()
    
    if not transaction:
        raise HTTPException(
            status_code=404,
            detail="Transaction non trouvée"
        )
    
    # Vérifier si le timer a expiré
    elapsed_time = datetime.utcnow() - transaction.created_at
    is_expired = elapsed_time > timedelta(minutes=15)
    
    # Si expiré et toujours pending, annuler automatiquement
    if is_expired and transaction.status == "pending":
        transaction.status = "cancelled"
        transaction.updated_at = datetime.utcnow()
        await session.commit()
        await session.refresh(transaction)
    
    remaining_seconds = max(0, 900 - int(elapsed_time.total_seconds()))
    
    return {
        "transaction_id": transaction.id,
        "status": transaction.status,
        "created_at": transaction.created_at,
        "updated_at": transaction.updated_at,
        "elapsed_seconds": int(elapsed_time.total_seconds()),
        "remaining_seconds": remaining_seconds,
        "is_expired": is_expired,
    }


# ============================================
# GET /transactions/{id}/payment-details
# ============================================

@router.get("/{transaction_id}/payment-details")
async def get_payment_details(
    transaction_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    Obtenir les détails de paiement pour une transaction
    
    Retourne les informations du compte à créditer selon la méthode
    """
   # Récupérer la transaction
    result = await session.execute(
        select(Transaction).where(
            Transaction.id == transaction_id,
            Transaction.sender_id == current_user.id,
        )
    )
    transaction = result.scalar_one_or_none()
    
    if not transaction:
        raise HTTPException(
            status_code=404,
            detail="Transaction non trouvée"
        )
    
    # Récupérer la méthode de paiement
    payment_method = transaction.payment_method
    
    # TODO: Récupérer les vrais détails depuis la config/DB
    # Pour l'instant, retourner des données exemple
    
    details = {
        "payment_method": payment_method.type,
        "transaction_reference": transaction.reference,
        "amount_to_pay": transaction.total_amount,
        "currency": transaction.sender_currency,
    }
    
    # Instructions selon la méthode
    if "mobile" in payment_method.type.lower() or "money" in payment_method.type.lower():
        details.update({
            "account_number": "+221771234567",  # TODO: Récupérer le vrai numéro
            "account_name": "ChapMoney",
            "instructions": [
                "Ouvrez votre application Mobile Money",
                "Sélectionnez 'Transfert d'argent'",
                f"Envoyez {transaction.total_amount} {transaction.sender_currency} au +221771234567",
                f"Utilisez la référence: {transaction.reference}",
            ],
        })
    elif "bank" in payment_method.type.lower() or "banque" in payment_method.type.lower():
        details.update({
            "iban": "FR76XXXXXXXXXXXXXXXXXXXXXXXX",  # TODO: Récupérer le vrai IBAN
            "bic": "XXXXXXXXXX",
            "account_name": "ChapMoney SAS",
            "instructions": [
                "Effectuez un virement bancaire",
                f"Montant: {transaction.total_amount} {transaction.sender_currency}",
                f"IBAN: FR76XXXXXXXXXXXXXXXXXXXXXXXX",
                f"Référence: {transaction.reference}",
            ],
        })
    elif "card" in payment_method.type.lower() or "carte" in payment_method.type.lower():
        details.update({
            "instructions": [
                "Utilisez votre carte bancaire",
                "Suivez les instructions de paiement sécurisé",
            ],
        })
    else:
        details.update({
            "instructions": [
                f"Effectuez le paiement de {transaction.total_amount} {transaction.sender_currency}",
                f"Référence: {transaction.reference}",
            ],
        })
    
    return details





# =============================================================================
# WEBSOCKET ENDPOINT
# =============================================================================

@router.websocket("/ws/transactions")
async def websocket_endpoint(websocket: WebSocket):
    """
    Connexion WebSocket pour les notifications en temps réel
    
    Permet aux clients de recevoir des mises à jour instantanées sur :
    - Nouvelles transactions
    - Changements de statut
    - Autres événements importants
    """
    await manager.connect(websocket)
    try:
        while True:
            # Garder la connexion ouverte
            data = await websocket.receive_text()
            # On peut implémenter des commandes ici si nécessaire
            if data == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        manager.disconnect(websocket)
