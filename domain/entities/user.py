"""
User Domain Entity

Core business entity representing a bot user.
Implements domain logic for user management and preferences.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any, List
from enum import Enum
import uuid


class UserStatus(Enum):
    """User status enumeration"""

    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    DELETED = "deleted"


class Language(Enum):
    """Supported languages"""

    RUSSIAN = "ru"
    ENGLISH = "en"


class TimezoneEnum(Enum):
    """Common timezones"""

    UTC = "UTC"
    MOSCOW = "Europe/Moscow"
    LONDON = "Europe/London"
    NEW_YORK = "America/New_York"
    TOKYO = "Asia/Tokyo"


@dataclass
class UserPreferences:
    """User preferences and settings"""

    language: Language = Language.RUSSIAN
    timezone: str = TimezoneEnum.UTC.value
    notifications_enabled: bool = True
    daily_reminder_time: Optional[str] = None  # Format: "HH:MM"
    weekly_summary: bool = True
    theme: str = "default"
    date_format: str = "DD.MM.YYYY"
    time_format: str = "24h"

    def to_dict(self) -> Dict[str, Any]:
        """Convert preferences to dictionary"""
        return {
            "language": self.language.value,
            "timezone": self.timezone,
            "notifications_enabled": self.notifications_enabled,
            "daily_reminder_time": self.daily_reminder_time,
            "weekly_summary": self.weekly_summary,
            "theme": self.theme,
            "date_format": self.date_format,
            "time_format": self.time_format,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "UserPreferences":
        """Create preferences from dictionary"""
        return cls(
            language=Language(data.get("language", "ru")),
            timezone=data.get("timezone", "UTC"),
            notifications_enabled=data.get("notifications_enabled", True),
            daily_reminder_time=data.get("daily_reminder_time"),
            weekly_summary=data.get("weekly_summary", True),
            theme=data.get("theme", "default"),
            date_format=data.get("date_format", "DD.MM.YYYY"),
            time_format=data.get("time_format", "24h"),
        )


@dataclass
class UserStats:
    """User statistics and metrics"""

    total_goals: int = 0
    completed_goals: int = 0
    total_tasks: int = 0
    completed_tasks: int = 0
    current_streak: int = 0
    longest_streak: int = 0
    total_sessions: int = 0
    last_activity: Optional[datetime] = None

    def calculate_completion_rate(self) -> float:
        """Calculate goal completion percentage"""
        if self.total_goals == 0:
            return 0.0
        return (self.completed_goals / self.total_goals) * 100

    def calculate_task_completion_rate(self) -> float:
        """Calculate task completion percentage"""
        if self.total_tasks == 0:
            return 0.0
        return (self.completed_tasks / self.total_tasks) * 100

    def to_dict(self) -> Dict[str, Any]:
        """Convert stats to dictionary"""
        return {
            "total_goals": self.total_goals,
            "completed_goals": self.completed_goals,
            "total_tasks": self.total_tasks,
            "completed_tasks": self.completed_tasks,
            "current_streak": self.current_streak,
            "longest_streak": self.longest_streak,
            "total_sessions": self.total_sessions,
            "last_activity": (
                self.last_activity.isoformat() if self.last_activity else None
            ),
            "goal_completion_rate": self.calculate_completion_rate(),
            "task_completion_rate": self.calculate_task_completion_rate(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "UserStats":
        """Create stats from dictionary"""
        stats = cls(
            total_goals=data.get("total_goals", 0),
            completed_goals=data.get("completed_goals", 0),
            total_tasks=data.get("total_tasks", 0),
            completed_tasks=data.get("completed_tasks", 0),
            current_streak=data.get("current_streak", 0),
            longest_streak=data.get("longest_streak", 0),
            total_sessions=data.get("total_sessions", 0),
        )

        if data.get("last_activity"):
            stats.last_activity = datetime.fromisoformat(data["last_activity"])

        return stats


@dataclass
class User:
    """
    User domain entity

    Represents a bot user with business logic for user management,
    preferences, and statistics tracking.
    """

    # Identity
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    telegram_id: int = 0

    # User details
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    status: UserStatus = UserStatus.ACTIVE

    # Timestamps
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    last_login: Optional[datetime] = None

    # Preferences
    language: Language = Language.RUSSIAN
    timezone: str = "UTC"
    notifications_enabled: bool = True

    # User data
    preferences: UserPreferences = field(default_factory=UserPreferences)
    stats: UserStats = field(default_factory=UserStats)

    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)

    def __post_init__(self):
        """Post-initialization validation and setup"""
        if self.telegram_id <= 0:
            raise ValueError("Telegram ID must be positive")

        self.updated_at = datetime.now()

    @property
    def display_name(self) -> str:
        """Get user display name"""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        elif self.first_name:
            return self.first_name
        elif self.username:
            return f"@{self.username}"
        else:
            return f"User {self.telegram_id}"

    @property
    def is_active(self) -> bool:
        """Check if user is active"""
        return self.status == UserStatus.ACTIVE

    @property
    def is_new_user(self) -> bool:
        """Check if user is new (less than 24 hours old)"""
        return (datetime.now() - self.created_at).days < 1

    def activate(self) -> None:
        """Activate user account"""
        if self.status == UserStatus.DELETED:
            raise ValueError("Cannot activate deleted user")

        self.status = UserStatus.ACTIVE
        self.updated_at = datetime.now()

    def deactivate(self) -> None:
        """Deactivate user account"""
        if self.status == UserStatus.DELETED:
            raise ValueError("Cannot deactivate deleted user")

        self.status = UserStatus.INACTIVE
        self.updated_at = datetime.now()

    def suspend(self, reason: Optional[str] = None) -> None:
        """Suspend user account"""
        if self.status == UserStatus.DELETED:
            raise ValueError("Cannot suspend deleted user")

        self.status = UserStatus.SUSPENDED
        self.updated_at = datetime.now()

        if reason:
            self.metadata["suspension_reason"] = reason
            self.metadata["suspended_at"] = datetime.now().isoformat()

    def delete(self) -> None:
        """Mark user as deleted (soft delete)"""
        self.status = UserStatus.DELETED
        self.updated_at = datetime.now()
        self.metadata["deleted_at"] = datetime.now().isoformat()

    def record_login(self) -> None:
        """Record user login"""
        self.last_login = datetime.now()
        self.stats.total_sessions += 1
        self.stats.last_activity = datetime.now()
        self.updated_at = datetime.now()

    def record_activity(self) -> None:
        """Record user activity"""
        self.stats.last_activity = datetime.now()
        self.updated_at = datetime.now()

    def update_profile(
        self,
        username: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
    ) -> None:
        """Update user profile information"""
        if username is not None:
            self.username = username

        if first_name is not None:
            self.first_name = first_name

        if last_name is not None:
            self.last_name = last_name

        self.updated_at = datetime.now()

    def update_preferences(self, preferences: UserPreferences) -> None:
        """Update user preferences"""
        self.preferences = preferences
        self.updated_at = datetime.now()

    def set_language(self, language: Language) -> None:
        """Set user language preference"""
        self.preferences.language = language
        self.updated_at = datetime.now()

    def set_timezone(self, timezone: str) -> None:
        """Set user timezone"""
        self.preferences.timezone = timezone
        self.updated_at = datetime.now()

    def enable_notifications(self) -> None:
        """Enable notifications for user"""
        self.preferences.notifications_enabled = True
        self.updated_at = datetime.now()

    def disable_notifications(self) -> None:
        """Disable notifications for user"""
        self.preferences.notifications_enabled = False
        self.updated_at = datetime.now()

    def set_daily_reminder(self, time: str) -> None:
        """
        Set daily reminder time

        Args:
            time: Time in HH:MM format
        """
        # Validate time format
        try:
            hour, minute = map(int, time.split(":"))
            if not (0 <= hour <= 23 and 0 <= minute <= 59):
                raise ValueError("Invalid time format")
        except (ValueError, AttributeError):
            raise ValueError("Time must be in HH:MM format")

        self.preferences.daily_reminder_time = time
        self.updated_at = datetime.now()

    def clear_daily_reminder(self) -> None:
        """Clear daily reminder"""
        self.preferences.daily_reminder_time = None
        self.updated_at = datetime.now()

    def increment_goal_count(self) -> None:
        """Increment total goals count"""
        self.stats.total_goals += 1
        self.updated_at = datetime.now()

    def increment_completed_goals(self) -> None:
        """Increment completed goals count"""
        self.stats.completed_goals += 1
        self.updated_at = datetime.now()

    def increment_task_count(self) -> None:
        """Increment total tasks count"""
        self.stats.total_tasks += 1
        self.updated_at = datetime.now()

    def increment_completed_tasks(self) -> None:
        """Increment completed tasks count"""
        self.stats.completed_tasks += 1
        self.updated_at = datetime.now()

    def update_streak(self, current_streak: int) -> None:
        """Update user streak"""
        self.stats.current_streak = current_streak

        if current_streak > self.stats.longest_streak:
            self.stats.longest_streak = current_streak

        self.updated_at = datetime.now()

    def reset_streak(self) -> None:
        """Reset current streak to 0"""
        self.stats.current_streak = 0
        self.updated_at = datetime.now()

    def add_tag(self, tag: str) -> None:
        """Add tag to user"""
        tag = tag.strip().lower()
        if tag and tag not in self.tags:
            self.tags.append(tag)
            self.updated_at = datetime.now()

    def remove_tag(self, tag: str) -> bool:
        """Remove tag from user"""
        tag = tag.strip().lower()
        if tag in self.tags:
            self.tags.remove(tag)
            self.updated_at = datetime.now()
            return True
        return False

    def has_tag(self, tag: str) -> bool:
        """Check if user has specific tag"""
        return tag.strip().lower() in self.tags

    def get_days_since_registration(self) -> int:
        """Get days since user registration"""
        return (datetime.now() - self.created_at).days

    def get_days_since_last_activity(self) -> Optional[int]:
        """Get days since last activity"""
        if not self.stats.last_activity:
            return None

        return (datetime.now() - self.stats.last_activity).days

    def to_dict(self) -> Dict[str, Any]:
        """Convert user to dictionary representation"""
        return {
            "id": self.id,
            "telegram_id": self.telegram_id,
            "username": self.username,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "last_login": self.last_login.isoformat() if self.last_login else None,
            "language": self.language.value,
            "timezone": self.timezone,
            "notifications_enabled": self.notifications_enabled,
            "preferences": self.preferences.to_dict(),
            "stats": self.stats.to_dict(),
            "metadata": self.metadata,
            "tags": self.tags,
            "display_name": self.display_name,
            "is_active": self.is_active,
            "is_new_user": self.is_new_user,
            "days_since_registration": self.get_days_since_registration(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "User":
        """Create user from dictionary representation"""
        user = cls(
            id=data.get("id", str(uuid.uuid4())),
            telegram_id=data.get("telegram_id", 0),
            username=data.get("username"),
            first_name=data.get("first_name"),
            last_name=data.get("last_name"),
            status=UserStatus(data.get("status", "active")),
            language=Language(data.get("language", "ru")),
            timezone=data.get("timezone", "UTC"),
            notifications_enabled=data.get("notifications_enabled", True),
            metadata=data.get("metadata", {}),
            tags=data.get("tags", []),
        )

        # Set timestamps if provided
        if "created_at" in data:
            user.created_at = datetime.fromisoformat(data["created_at"])

        if "updated_at" in data:
            user.updated_at = datetime.fromisoformat(data["updated_at"])

        if data.get("last_login"):
            user.last_login = datetime.fromisoformat(data["last_login"])

        # Set preferences if provided
        if "preferences" in data:
            user.preferences = UserPreferences.from_dict(data["preferences"])

        # Set stats if provided
        if "stats" in data:
            user.stats = UserStats.from_dict(data["stats"])

        return user

    @classmethod
    def create_from_telegram(
        cls,
        telegram_id: int,
        username: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
    ) -> "User":
        """Create user from Telegram user data"""
        return cls(
            telegram_id=telegram_id,
            username=username,
            first_name=first_name,
            last_name=last_name,
            status=UserStatus.ACTIVE,
        )

    def __repr__(self) -> str:
        """String representation of user"""
        return f"User(id='{self.id}', telegram_id={self.telegram_id}, name='{self.display_name}', status='{self.status.value}')"

    def __eq__(self, other) -> bool:
        """Equality comparison based on ID"""
        if not isinstance(other, User):
            return False
        return self.id == other.id

    def __hash__(self) -> int:
        """Hash based on ID"""
        return hash(self.id)
