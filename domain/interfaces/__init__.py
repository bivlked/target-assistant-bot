"""
Domain Interfaces Package

Contains repository interfaces and other domain contracts.
"""

from .goal_repository import GoalRepository
from .task_repository import TaskRepository  
from .user_repository import UserRepository

__all__ = [
    'GoalRepository',
    'TaskRepository',
    'UserRepository'
] 