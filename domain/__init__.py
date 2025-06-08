"""
Domain Package

Contains all domain layer components for Target Assistant Bot.
Includes entities, interfaces, and domain services.
"""

from .entities import Goal, GoalStatus, GoalPriority, Task, TaskStatus, TaskPriority, User, UserStatus, Language

__all__ = [
    'Goal', 'GoalStatus', 'GoalPriority',
    'Task', 'TaskStatus', 'TaskPriority', 
    'User', 'UserStatus', 'Language'
] 