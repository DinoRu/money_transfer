"""
Repository de base pour toutes les opérations CRUD en mode asynchrone
"""
from typing import Generic, TypeVar, Type, Optional, List
from uuid import UUID

from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.session import Base



ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """
    Repository de base pour les opérations CRUD asynchrones
    """
    
    def __init__(self, model: Type[ModelType]):
        self.model = model
    
    async def get(self, db: AsyncSession, id: UUID) -> Optional[ModelType]:
        """
        Récupère un objet par son ID
        
        Args:
            db: Session de base de données asynchrone
            id: UUID de l'objet
            
        Returns:
            L'objet trouvé ou None
        """
        result = await db.execute(
            select(self.model).where(self.model.id == id)
        )
        return result.scalar_one_or_none()
    
    async def get_multi(
        self,
        db: AsyncSession,
        skip: int = 0,
        limit: int = 100
    ) -> List[ModelType]:
        """
        Récupère plusieurs objets avec pagination
        
        Args:
            db: Session de base de données asynchrone
            skip: Nombre d'objets à sauter
            limit: Nombre maximum d'objets à retourner
            
        Returns:
            Liste des objets
        """
        result = await db.execute(
            select(self.model).offset(skip).limit(limit)
        )
        return list(result.scalars().all())
    
    async def create(self, db: AsyncSession, obj_in: dict) -> ModelType:
        """
        Crée un nouvel objet
        
        Args:
            db: Session de base de données asynchrone
            obj_in: Dictionnaire ou objet Pydantic avec les données
            
        Returns:
            L'objet créé
        """
        # Convertir l'objet Pydantic en dict si nécessaire
        if hasattr(obj_in, 'model_dump'):
            obj_data = obj_in.model_dump(exclude_unset=True)
        else:
            obj_data = obj_in
        
        db_obj = self.model(**obj_data)
        db.add(db_obj)
        await db.flush()
        await db.refresh(db_obj)
        return db_obj
    
    async def update(
        self,
        db: AsyncSession,
        db_obj: ModelType,
        obj_in: dict
    ) -> ModelType:
        """
        Met à jour un objet existant
        
        Args:
            db: Session de base de données asynchrone
            db_obj: Objet à mettre à jour
            obj_in: Dictionnaire ou objet Pydantic avec les nouvelles données
            
        Returns:
            L'objet mis à jour
        """
        # Convertir l'objet Pydantic en dict si nécessaire
        if hasattr(obj_in, 'model_dump'):
            update_data = obj_in.model_dump(exclude_unset=True)
        else:
            update_data = obj_in
        
        # Mettre à jour les attributs
        for field, value in update_data.items():
            if hasattr(db_obj, field):
                setattr(db_obj, field, value)
        
        await db.flush()
        await db.refresh(db_obj)
        return db_obj
    
    async def delete(self, db: AsyncSession, id: UUID) -> bool:
        """
        Supprime un objet
        
        Args:
            db: Session de base de données asynchrone
            id: UUID de l'objet à supprimer
            
        Returns:
            True si l'objet a été supprimé, False sinon
        """
        result = await db.execute(
            delete(self.model).where(self.model.id == id)
        )
        await db.flush()
        return result.rowcount > 0