"""
User Repository Interface

Defines the contract for user data persistence operations.
Implements Repository pattern for domain layer.
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any

from domain.entities.user import User, UserStatus


class UserRepository(ABC):
    """
    Abstract repository interface for User entity

    Defines all persistence operations for users following
    the Repository pattern principles.
    """

    @abstractmethod
    async def create(self, user: User) -> User:
        """
        Create a new user

        Args:
            user: User entity to create

        Returns:
            User: Created user with updated timestamps
        """
        pass

    @abstractmethod
    async def get_by_id(self, user_id: str) -> Optional[User]:
        """
        Get user by ID

        Args:
            user_id: Unique user identifier

        Returns:
            Optional[User]: User if found, None otherwise
        """
        pass

    @abstractmethod
    async def get_by_telegram_id(self, telegram_id: int) -> Optional[User]:
        """
        Get user by Telegram ID

        Args:
            telegram_id: Telegram user identifier

        Returns:
            Optional[User]: User if found, None otherwise
        """
        pass

    @abstractmethod
    async def update(self, user: User) -> User:
        """
        Update existing user

        Args:
            user: User entity with updates

        Returns:
            User: Updated user
        """
        pass

    @abstractmethod
    async def delete(self, user_id: str) -> bool:
        """
        Delete user by ID

        Args:
            user_id: User identifier

        Returns:
            bool: True if deleted, False if not found
        """
        pass

    @abstractmethod
    async def get_all_active(self) -> List[User]:
        """
        Get all active users

        Returns:
            List[User]: List of active users
        """
        pass

    @abstractmethod
    async def search_by_name(self, name: str) -> List[User]:
        """
        Search users by name

        Args:
            name: Name to search for

        Returns:
            List[User]: List of matching users
        """
        pass
