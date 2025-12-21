"""
Router pour l'authentification et la gestion des utilisateurs
Endpoints: login, register, refresh, me, change-password
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.dependencies import create_access_token, create_refresh_token, get_db, get_current_user, get_current_active_user
from src.services import user_service

from src.schemas.user import RefreshTokenRequest, TokenResponse, UserResponse, UserCreate, UserLogin, UserWithToken, UserLoginResponse



router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Créer un nouveau compte utilisateur
    
    - **email**: Email unique
    - **password**: Mot de passe (min 8 caractères)
    - **full_name**: Nom complet
    - **phone**: Numéro de téléphone
    """
    try:
        user = await user_service.create(db, user_data)
        return user
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/login", response_model=UserLoginResponse)
async def login(
    credentials: UserLogin,
    db: AsyncSession = Depends(get_db)
):
    """
    Se connecter et obtenir un token d'accès
    
    - **email**: Email du compte
    - **password**: Mot de passe
    
    Returns:
        - user: Informations utilisateur
        - access_token: Token JWT pour les requêtes
        - refresh_token: Token pour renouveler l'accès
        - token_type: "bearer"
    """
    # Authentifier l'utilisateur
    user = await user_service.authenticate(db, credentials.email, credentials.password)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou mot de passe incorrect",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Compte désactivé"
        )
    
    # Créer les tokens
    access_token = create_access_token(data={"sub": str(user.id)})
    refresh_token = create_refresh_token(data={"sub": str(user.id)})
    
    return UserLoginResponse(
        user=UserResponse.model_validate(user),
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer"
    )

class verify_token:
    def __init__(self):
        pass


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    request: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Renouveler le token d'accès avec un refresh token
    
    - **refresh_token**: Token de rafraîchissement valide
    
    Returns:
        - access_token: Nouveau token d'accès
        - refresh_token: Nouveau token de rafraîchissement
        - token_type: "bearer"
    """
    try:
        # Vérifier le refresh token
        payload = verify_token(request.refresh_token)
        user_id = payload.get("sub")
        
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token invalide"
            )
        
        # Vérifier que l'utilisateur existe toujours
        user = await user_service.get(db, user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Utilisateur non trouvé"
            )
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Compte désactivé"
            )
        
        # Créer de nouveaux tokens
        new_access_token = create_access_token(data={"sub": user_id})
        new_refresh_token = create_refresh_token(data={"sub": user_id})
        
        return TokenResponse(
            access_token=new_access_token,
            refresh_token=new_refresh_token,
            token_type="bearer"
        )
    
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalide ou expiré"
        )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user = Depends(get_current_active_user)
):
    """
    Obtenir les informations de l'utilisateur connecté
    
    Requires: Token d'authentification valide
    """
    return UserResponse.model_validate(current_user)


# @router.post("/change-password", status_code=status.HTTP_200_OK)
# async def change_password(
#     password_data: ChangePasswordRequest,
#     db: AsyncSession = Depends(get_db),
#     current_user = Depends(get_current_active_user)
# ):
#     """
#     Changer le mot de passe de l'utilisateur connecté
    
#     - **old_password**: Ancien mot de passe
#     - **new_password**: Nouveau mot de passe (min 8 caractères)
    
#     Requires: Token d'authentification valide
#     """
#     try:
#         await user_service.change_password(
#             db,
#             current_user.id,
#             password_data.old_password,
#             password_data.new_password
#         )
        
#         await db.commit()
        
#         return {"message": "Mot de passe changé avec succès"}
    
#     except ValueError as e:
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail=str(e)
#         )


@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout(current_user = Depends(get_current_active_user)):
    """
    Se déconnecter (côté client uniquement)
    
    Note: Le client doit supprimer le token de son côté.
    Les tokens JWT ne peuvent pas être révoqués côté serveur
    sans un système de blacklist.
    
    Requires: Token d'authentification valide
    """
    return {
        "message": "Déconnexion réussie",
        "note": "Supprimez le token côté client"
    }