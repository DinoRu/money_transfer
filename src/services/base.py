"""
Service de base pour toutes les opérations CRUD en mode asynchrone
"""
from typing import Generic, TypeVar, Type, Optional, List
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from src.db.session import Base
from src.repositories import BaseRepository



ModelType = TypeVar("ModelType", bound=Base)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)
ResponseSchemaType = TypeVar("ResponseSchemaType", bound=BaseModel)


class BaseService(Generic[ModelType, CreateSchemaType, UpdateSchemaType, ResponseSchemaType]):
    """
    Service de base pour les opérations CRUD asynchrones
    
    Fournit des méthodes génériques pour:
    - Créer (create)
    - Lire (get, get_multi)
    - Mettre à jour (update)
    - Supprimer (delete)
    
    Usage:
        class UserService(BaseService[User, UserCreate, UserUpdate, UserResponse]):
            def __init__(self):
                super().__init__(user_repository, UserResponse)
    """
    
    def __init__(
        self,
        repository: BaseRepository[ModelType],
        response_schema: Type[ResponseSchemaType]
    ):
        """
        Initialise le service
        
        Args:
            repository: Repository pour les opérations DB
            response_schema: Schema Pydantic pour les réponses
        """
        self.repository = repository
        self.response_schema = response_schema
    
    async def create(
        self,
        db: AsyncSession,
        obj_in: CreateSchemaType
    ) -> ResponseSchemaType:
        """
        Crée un nouvel objet
        
        Args:
            db: Session asynchrone
            obj_in: Données de création (schema Pydantic)
            
        Returns:
            L'objet créé (schema de réponse)
        """
        obj = await self.repository.create(db, obj_in)
        return self.response_schema.model_validate(obj)
    
    async def get(
        self,
        db: AsyncSession,
        id: UUID
    ) -> Optional[ResponseSchemaType]:
        """
        Récupère un objet par son ID
        
        Args:
            db: Session asynchrone
            id: UUID de l'objet
            
        Returns:
            L'objet trouvé ou None
        """
        obj = await self.repository.get(db, id)
        if obj:
            return self.response_schema.model_validate(obj)
        return None
    
    async def get_multi(
        self,
        db: AsyncSession,
        skip: int = 0,
        limit: int = 100
    ) -> List[ResponseSchemaType]:
        """
        Récupère plusieurs objets avec pagination
        
        Args:
            db: Session asynchrone
            skip: Nombre d'objets à sauter
            limit: Nombre maximum d'objets à retourner
            
        Returns:
            Liste des objets (schemas de réponse)
        """
        objs = await self.repository.get_multi(db, skip=skip, limit=limit)
        return [self.response_schema.model_validate(obj) for obj in objs]
    
    async def update(
        self,
        db: AsyncSession,
        id: UUID,
        obj_in: UpdateSchemaType
    ) -> Optional[ResponseSchemaType]:
        """
        Met à jour un objet existant
        
        Args:
            db: Session asynchrone
            id: UUID de l'objet
            obj_in: Nouvelles données (schema Pydantic)
            
        Returns:
            L'objet mis à jour ou None si non trouvé
        """
        obj = await self.repository.get(db, id)
        if not obj:
            return None
        
        updated_obj = await self.repository.update(db, obj, obj_in)
        return self.response_schema.model_validate(updated_obj)
    
    async def delete(
        self,
        db: AsyncSession,
        id: UUID
    ) -> bool:
        """
        Supprime un objet
        
        Args:
            db: Session asynchrone
            id: UUID de l'objet
            
        Returns:
            True si supprimé, False sinon
        """
        return await self.repository.delete(db, id)
    
    async def exists(
        self,
        db: AsyncSession,
        id: UUID
    ) -> bool:
        """
        Vérifie si un objet existe
        
        Args:
            db: Session asynchrone
            id: UUID de l'objet
            
        Returns:
            True si existe, False sinon
        """
        obj = await self.repository.get(db, id)
        return obj is not None
    
    async def count(
        self,
        db: AsyncSession
    ) -> int:
        """
        Compte le nombre total d'objets
        
        Args:
            db: Session asynchrone
            
        Returns:
            Nombre d'objets
        """
        from sqlalchemy import select, func
        result = await db.execute(
            select(func.count()).select_from(self.repository.model)
        )
        return result.scalar()
    
    async def get_or_404(
        self,
        db: AsyncSession,
        id: UUID,
        error_message: str = "Objet non trouvé"
    ) -> ResponseSchemaType:
        """
        Récupère un objet ou lève une exception
        
        Args:
            db: Session asynchrone
            id: UUID de l'objet
            error_message: Message d'erreur personnalisé
            
        Returns:
            L'objet trouvé
            
        Raises:
            ValueError: Si l'objet n'existe pas
        """
        obj = await self.get(db, id)
        if not obj:
            raise ValueError(error_message)
        return obj
    
    async def create_bulk(
        self,
        db: AsyncSession,
        objs_in: List[CreateSchemaType]
    ) -> List[ResponseSchemaType]:
        """
        Crée plusieurs objets en une fois
        
        Args:
            db: Session asynchrone
            objs_in: Liste des données de création
            
        Returns:
            Liste des objets créés
        """
        created_objs = []
        for obj_in in objs_in:
            obj = await self.repository.create(db, obj_in)
            created_objs.append(obj)
        
        # Flush une seule fois à la fin
        await db.flush()
        
        return [self.response_schema.model_validate(obj) for obj in created_objs]
    
    async def update_partial(
        self,
        db: AsyncSession,
        id: UUID,
        obj_in: dict
    ) -> Optional[ResponseSchemaType]:
        """
        Met à jour partiellement un objet (seuls les champs fournis)
        
        Args:
            db: Session asynchrone
            id: UUID de l'objet
            obj_in: Dictionnaire avec les champs à mettre à jour
            
        Returns:
            L'objet mis à jour ou None
        """
        obj = await self.repository.get(db, id)
        if not obj:
            return None
        
        # Mettre à jour uniquement les champs fournis
        for field, value in obj_in.items():
            if hasattr(obj, field) and value is not None:
                setattr(obj, field, value)
        
        await db.flush()
        await db.refresh(obj)
        
        return self.response_schema.model_validate(obj)
    
    async def soft_delete(
        self,
        db: AsyncSession,
        id: UUID
    ) -> Optional[ResponseSchemaType]:
        """
        Suppression logique (soft delete) si le modèle a un champ is_deleted
        
        Args:
            db: Session asynchrone
            id: UUID de l'objet
            
        Returns:
            L'objet marqué comme supprimé ou None
        """
        obj = await self.repository.get(db, id)
        if not obj:
            return None
        
        # Vérifier si le modèle supporte le soft delete
        if hasattr(obj, 'is_deleted'):
            obj.is_deleted = True
            await db.flush()
            await db.refresh(obj)
            return self.response_schema.model_validate(obj)
        
        # Sinon, suppression réelle
        await self.repository.delete(db, id)
        return None
    
    async def restore(
        self,
        db: AsyncSession,
        id: UUID
    ) -> Optional[ResponseSchemaType]:
        """
        Restaure un objet supprimé logiquement
        
        Args:
            db: Session asynchrone
            id: UUID de l'objet
            
        Returns:
            L'objet restauré ou None
        """
        obj = await self.repository.get(db, id)
        if not obj:
            return None
        
        if hasattr(obj, 'is_deleted'):
            obj.is_deleted = False
            await db.flush()
            await db.refresh(obj)
            return self.response_schema.model_validate(obj)
        
        return None
    
    async def get_active(
        self,
        db: AsyncSession,
        skip: int = 0,
        limit: int = 100
    ) -> List[ResponseSchemaType]:
        """
        Récupère les objets actifs (si le modèle a un champ is_active)
        
        Args:
            db: Session asynchrone
            skip: Nombre d'objets à sauter
            limit: Nombre maximum d'objets
            
        Returns:
            Liste des objets actifs
        """
        from sqlalchemy import select
        
        # Vérifier si le modèle a un champ is_active
        if hasattr(self.repository.model, 'is_active'):
            result = await db.execute(
                select(self.repository.model)
                .where(self.repository.model.is_active == True)
                .offset(skip)
                .limit(limit)
            )
            objs = list(result.scalars().all())
            return [self.response_schema.model_validate(obj) for obj in objs]
        
        # Sinon, retourner tous les objets
        return await self.get_multi(db, skip=skip, limit=limit)
    
    async def activate(
        self,
        db: AsyncSession,
        id: UUID
    ) -> Optional[ResponseSchemaType]:
        """
        Active un objet (si le modèle a un champ is_active)
        
        Args:
            db: Session asynchrone
            id: UUID de l'objet
            
        Returns:
            L'objet activé ou None
        """
        obj = await self.repository.get(db, id)
        if not obj:
            return None
        
        if hasattr(obj, 'is_active'):
            obj.is_active = True
            await db.flush()
            await db.refresh(obj)
            return self.response_schema.model_validate(obj)
        
        return None
    
    async def deactivate(
        self,
        db: AsyncSession,
        id: UUID
    ) -> Optional[ResponseSchemaType]:
        """
        Désactive un objet (si le modèle a un champ is_active)
        
        Args:
            db: Session asynchrone
            id: UUID de l'objet
            
        Returns:
            L'objet désactivé ou None
        """
        obj = await self.repository.get(db, id)
        if not obj:
            return None
        
        if hasattr(obj, 'is_active'):
            obj.is_active = False
            await db.flush()
            await db.refresh(obj)
            return self.response_schema.model_validate(obj)
        
        return None
    
    async def search(
        self,
        db: AsyncSession,
        search_field: str,
        search_term: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[ResponseSchemaType]:
        """
        Recherche d'objets par un champ texte
        
        Args:
            db: Session asynchrone
            search_field: Nom du champ à rechercher
            search_term: Terme de recherche
            skip: Nombre d'objets à sauter
            limit: Nombre maximum d'objets
            
        Returns:
            Liste des objets trouvés
        """
        from sqlalchemy import select
        
        # Vérifier que le champ existe
        if not hasattr(self.repository.model, search_field):
            return []
        
        field = getattr(self.repository.model, search_field)
        result = await db.execute(
            select(self.repository.model)
            .where(field.ilike(f"%{search_term}%"))
            .offset(skip)
            .limit(limit)
        )
        objs = list(result.scalars().all())
        return [self.response_schema.model_validate(obj) for obj in objs]
    
    async def get_by_field(
        self,
        db: AsyncSession,
        field_name: str,
        field_value: any
    ) -> Optional[ResponseSchemaType]:
        """
        Récupère un objet par un champ spécifique
        
        Args:
            db: Session asynchrone
            field_name: Nom du champ
            field_value: Valeur à chercher
            
        Returns:
            L'objet trouvé ou None
        """
        from sqlalchemy import select
        
        if not hasattr(self.repository.model, field_name):
            return None
        
        field = getattr(self.repository.model, field_name)
        result = await db.execute(
            select(self.repository.model).where(field == field_value)
        )
        obj = result.scalar_one_or_none()
        
        if obj:
            return self.response_schema.model_validate(obj)
        return None
    
    async def get_multi_by_field(
        self,
        db: AsyncSession,
        field_name: str,
        field_value: any,
        skip: int = 0,
        limit: int = 100
    ) -> List[ResponseSchemaType]:
        """
        Récupère plusieurs objets par un champ spécifique
        
        Args:
            db: Session asynchrone
            field_name: Nom du champ
            field_value: Valeur à chercher
            skip: Nombre d'objets à sauter
            limit: Nombre maximum d'objets
            
        Returns:
            Liste des objets trouvés
        """
        from sqlalchemy import select
        
        if not hasattr(self.repository.model, field_name):
            return []
        
        field = getattr(self.repository.model, field_name)
        result = await db.execute(
            select(self.repository.model)
            .where(field == field_value)
            .offset(skip)
            .limit(limit)
        )
        objs = list(result.scalars().all())
        return [self.response_schema.model_validate(obj) for obj in objs]