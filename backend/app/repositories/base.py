"""
Base repository providing generic CRUD operations.
"""
from typing import TypeVar, Generic, Type, Optional, List

from app.core.extensions import db

T = TypeVar('T', bound=db.Model)


class BaseRepository(Generic[T]):
    """Abstract base repository with common CRUD methods."""

    def __init__(self, model: Type[T]):
        self.model = model

    def get_by_id(self, entity_id: int) -> Optional[T]:
        """Get a single entity by its primary key."""
        return db.session.get(self.model, entity_id)

    def get_all(self, limit: int = 100, offset: int = 0) -> List[T]:
        """Get all entities with optional pagination."""
        return self.model.query.limit(limit).offset(offset).all()

    def create(self, entity: T) -> T:
        """Add and persist a new entity."""
        db.session.add(entity)
        db.session.commit()
        return entity

    def update(self, entity: T) -> T:
        """Persist changes to an existing entity."""
        db.session.commit()
        return entity

    def delete(self, entity_id: int) -> bool:
        """Delete an entity by its primary key. Returns True if deleted."""
        entity = self.get_by_id(entity_id)
        if entity is None:
            return False
        db.session.delete(entity)
        db.session.commit()
        return True

    def count(self) -> int:
        """Return the total number of entities."""
        return self.model.query.count()
