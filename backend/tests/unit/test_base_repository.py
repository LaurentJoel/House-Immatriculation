"""
Tests for the BaseRepository (Step 3.1).
"""
from app.models import User
from app.repositories.base import BaseRepository


def _make_user(**overrides):
    """Helper to create a User instance with defaults."""
    defaults = dict(
        username='testuser',
        email='test@gov.cm',
        full_name='Test User',
        role='field_agent',
    )
    defaults.update(overrides)
    user = User(**defaults)
    user.set_password('password123')
    return user


class TestBaseRepository:
    """Step 3.1: Base repository CRUD tests."""

    def test_base_repository_create(self, db_session):
        """Create persists an entity and assigns an id."""
        repo = BaseRepository(User)
        user = _make_user()
        created = repo.create(user)
        assert created.user_id is not None

    def test_base_repository_get_by_id(self, db_session):
        """get_by_id returns the correct entity."""
        repo = BaseRepository(User)
        user = _make_user()
        repo.create(user)
        found = repo.get_by_id(user.user_id)
        assert found is not None
        assert found.username == 'testuser'

    def test_base_repository_get_all(self, db_session):
        """get_all returns all persisted entities."""
        repo = BaseRepository(User)
        for i in range(5):
            repo.create(_make_user(username=f'user_{i}', email=f'u{i}@gov.cm'))
        users = repo.get_all()
        assert len(users) == 5

    def test_base_repository_delete(self, db_session):
        """delete removes the entity and returns True."""
        repo = BaseRepository(User)
        user = _make_user()
        repo.create(user)
        uid = user.user_id
        assert repo.delete(uid) is True
        assert repo.get_by_id(uid) is None

    def test_base_repository_delete_nonexistent(self, db_session):
        """delete returns False for a missing id."""
        repo = BaseRepository(User)
        assert repo.delete(99999) is False

    def test_base_repository_count(self, db_session):
        """count returns the number of entities."""
        repo = BaseRepository(User)
        for i in range(3):
            repo.create(_make_user(username=f'cnt_{i}', email=f'c{i}@gov.cm'))
        assert repo.count() == 3
