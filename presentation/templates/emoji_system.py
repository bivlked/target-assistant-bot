"""
Emoji Design System for Target Assistant Bot

Systematic emoji usage following the UI Style Guide principles.
Provides consistent emoji language across all user interactions.
"""

from enum import Enum
from typing import Dict, List, Optional
from dataclasses import dataclass


class EmojiCategory(Enum):
    """Categories of emojis used in the design system"""

    CORE_ACTIONS = "core_actions"
    STATUS_FEEDBACK = "status_feedback"
    MOTIVATION = "motivation"
    TIME_SCHEDULING = "time_scheduling"


@dataclass
class EmojiDefinition:
    """Definition of an emoji with its meaning and usage context"""

    emoji: str
    name: str
    meaning: str
    usage_context: str
    category: EmojiCategory


class EmojiSystem:
    """
    Centralized emoji design system implementation

    Provides systematic emoji usage following the UI Style Guide:
    - 🎯 Core Actions & Features
    - ✅ Status & Feedback
    - 🎉 Motivation & Celebration
    - 📅 Time & Scheduling
    """

    # Core Actions & Features
    CORE_ACTIONS = {
        "goals": EmojiDefinition(
            "🎯",
            "target",
            "Goals & Targets",
            "Main goal creation, goal management",
            EmojiCategory.CORE_ACTIONS,
        ),
        "tasks": EmojiDefinition(
            "📝",
            "memo",
            "Tasks & Planning",
            "Daily tasks, planning activities",
            EmojiCategory.CORE_ACTIONS,
        ),
        "progress": EmojiDefinition(
            "📊",
            "bar_chart",
            "Progress & Analytics",
            "Statistics, progress tracking",
            EmojiCategory.CORE_ACTIONS,
        ),
        "settings": EmojiDefinition(
            "⚙️",
            "gear",
            "Settings & Configuration",
            "Bot settings, preferences",
            EmojiCategory.CORE_ACTIONS,
        ),
        "help": EmojiDefinition(
            "❓",
            "question",
            "Help & Support",
            "Help commands, assistance",
            EmojiCategory.CORE_ACTIONS,
        ),
    }

    # Status & Feedback
    STATUS_FEEDBACK = {
        "success": EmojiDefinition(
            "✅",
            "check_mark",
            "Success",
            "Completed actions, achievements",
            EmojiCategory.STATUS_FEEDBACK,
        ),
        "error": EmojiDefinition(
            "❌",
            "cross_mark",
            "Error",
            "Failures, problems, errors",
            EmojiCategory.STATUS_FEEDBACK,
        ),
        "warning": EmojiDefinition(
            "⚠️",
            "warning",
            "Warning",
            "Cautions, important notices",
            EmojiCategory.STATUS_FEEDBACK,
        ),
        "info": EmojiDefinition(
            "ℹ️",
            "information",
            "Information",
            "General info, explanations",
            EmojiCategory.STATUS_FEEDBACK,
        ),
        "in_progress": EmojiDefinition(
            "🔄",
            "arrows_counterclockwise",
            "In Progress",
            "Loading, processing, ongoing actions",
            EmojiCategory.STATUS_FEEDBACK,
        ),
    }

    # Motivation & Celebration
    MOTIVATION = {
        "celebration": EmojiDefinition(
            "🎉",
            "party_popper",
            "Celebration",
            "Goal completion, major achievements",
            EmojiCategory.MOTIVATION,
        ),
        "streak": EmojiDefinition(
            "🔥",
            "fire",
            "Streak & Momentum",
            "Consistency, hot streaks",
            EmojiCategory.MOTIVATION,
        ),
        "encouragement": EmojiDefinition(
            "💪",
            "flexed_biceps",
            "Encouragement",
            "Motivation, support",
            EmojiCategory.MOTIVATION,
        ),
        "achievement": EmojiDefinition(
            "🏆",
            "trophy",
            "Achievement",
            "Milestones, awards",
            EmojiCategory.MOTIVATION,
        ),
        "excellence": EmojiDefinition(
            "⭐",
            "star",
            "Excellence",
            "Outstanding performance",
            EmojiCategory.MOTIVATION,
        ),
    }

    # Time & Scheduling
    TIME_SCHEDULING = {
        "calendar": EmojiDefinition(
            "📅",
            "calendar",
            "Calendar",
            "Date-related actions",
            EmojiCategory.TIME_SCHEDULING,
        ),
        "time": EmojiDefinition(
            "⏰",
            "alarm_clock",
            "Time",
            "Time-sensitive actions, reminders",
            EmojiCategory.TIME_SCHEDULING,
        ),
        "schedule": EmojiDefinition(
            "📆",
            "tear_off_calendar",
            "Schedule",
            "Planning, scheduling",
            EmojiCategory.TIME_SCHEDULING,
        ),
        "deadline": EmojiDefinition(
            "🕐",
            "one_oclock",
            "Deadline",
            "Due dates, urgency",
            EmojiCategory.TIME_SCHEDULING,
        ),
    }

    @classmethod
    def get_emoji(cls, key: str, category: Optional[EmojiCategory] = None) -> str:
        """
        Get emoji by key, optionally filtered by category

        Args:
            key: Emoji key (e.g., 'goals', 'success', 'celebration')
            category: Optional category filter

        Returns:
            str: Emoji character

        Raises:
            KeyError: If emoji key not found
        """
        all_emojis = {
            **cls.CORE_ACTIONS,
            **cls.STATUS_FEEDBACK,
            **cls.MOTIVATION,
            **cls.TIME_SCHEDULING,
        }

        if key not in all_emojis:
            raise KeyError(f"Emoji key '{key}' not found in design system")

        emoji_def = all_emojis[key]

        if category and emoji_def.category != category:
            raise KeyError(f"Emoji '{key}' not found in category '{category.value}'")

        return emoji_def.emoji

    @classmethod
    def get_emoji_definition(cls, key: str) -> EmojiDefinition:
        """Get complete emoji definition by key"""
        all_emojis = {
            **cls.CORE_ACTIONS,
            **cls.STATUS_FEEDBACK,
            **cls.MOTIVATION,
            **cls.TIME_SCHEDULING,
        }

        if key not in all_emojis:
            raise KeyError(f"Emoji key '{key}' not found in design system")

        return all_emojis[key]

    @classmethod
    def get_category_emojis(cls, category: EmojiCategory) -> Dict[str, EmojiDefinition]:
        """Get all emojis from a specific category"""
        category_maps = {
            EmojiCategory.CORE_ACTIONS: cls.CORE_ACTIONS,
            EmojiCategory.STATUS_FEEDBACK: cls.STATUS_FEEDBACK,
            EmojiCategory.MOTIVATION: cls.MOTIVATION,
            EmojiCategory.TIME_SCHEDULING: cls.TIME_SCHEDULING,
        }

        return category_maps.get(category, {})

    @classmethod
    def format_combination_pattern(cls, pattern: str) -> str:
        """
        Format emoji combination patterns

        Examples:
        - "goals -> success" → "🎯 New Goal → ✅ Goal Created"
        - "tasks -> in_progress -> success" → "📝 Task Added → 🔄 In Progress → ✅ Completed"
        """
        steps = [step.strip() for step in pattern.split("->")]
        formatted_steps = []

        for step in steps:
            if step in cls.get_all_emoji_keys():
                emoji = cls.get_emoji(step)
                definition = cls.get_emoji_definition(step)
                formatted_steps.append(f"{emoji} {definition.meaning}")
            else:
                formatted_steps.append(step)

        return " → ".join(formatted_steps)

    @classmethod
    def get_all_emoji_keys(cls) -> List[str]:
        """Get all available emoji keys"""
        return list(
            {
                **cls.CORE_ACTIONS,
                **cls.STATUS_FEEDBACK,
                **cls.MOTIVATION,
                **cls.TIME_SCHEDULING,
            }.keys()
        )

    @classmethod
    def validate_emoji_usage(cls, text: str) -> List[str]:
        """
        Validate emoji usage in text against design system

        Returns:
            List[str]: Warnings about non-standard emoji usage
        """
        warnings = []
        known_emojis = {
            emoji_def.emoji
            for emoji_def in {
                **cls.CORE_ACTIONS,
                **cls.STATUS_FEEDBACK,
                **cls.MOTIVATION,
                **cls.TIME_SCHEDULING,
            }.values()
        }

        # Find all emojis in text (basic detection)
        used_emojis = [char for char in text if ord(char) > 0x1F600]

        for emoji in used_emojis:
            if emoji not in known_emojis:
                warnings.append(
                    f"Non-standard emoji '{emoji}' found - consider using design system emoji"
                )

        return warnings


# Common emoji combinations following the design patterns
class EmojiCombinations:
    """Pre-defined emoji combination patterns for common flows"""

    # Goal Creation Flow
    GOAL_CREATION = (
        f"{EmojiSystem.get_emoji('goals')} → {EmojiSystem.get_emoji('success')}"
    )

    # Task Flow
    TASK_FLOW = f"{EmojiSystem.get_emoji('tasks')} → {EmojiSystem.get_emoji('in_progress')} → {EmojiSystem.get_emoji('success')}"

    # Progress Flow
    PROGRESS_FLOW = (
        f"{EmojiSystem.get_emoji('progress')} → {EmojiSystem.get_emoji('celebration')}"
    )

    # Error Recovery Flow
    ERROR_RECOVERY = f"{EmojiSystem.get_emoji('error')} → {EmojiSystem.get_emoji('info')} → {EmojiSystem.get_emoji('success')}"


# Accessibility helpers
class AccessibilityEmojis:
    """Emoji accessibility helpers for screen readers"""

    @staticmethod
    def add_text_alternative(emoji: str, text_alt: str) -> str:
        """Add text alternative for emoji (screen reader support)"""
        return f"{emoji} ({text_alt})"

    @staticmethod
    def emoji_to_text(emoji_key: str) -> str:
        """Convert emoji key to readable text for accessibility"""
        definition = EmojiSystem.get_emoji_definition(emoji_key)
        return definition.meaning

    @staticmethod
    def create_accessible_message(message: str, emoji_keys: List[str]) -> str:
        """Create message with emoji text alternatives for accessibility"""
        accessible_msg = message
        for key in emoji_keys:
            emoji = EmojiSystem.get_emoji(key)
            text_alt = AccessibilityEmojis.emoji_to_text(key)
            accessible_msg = accessible_msg.replace(emoji, f"{emoji} ({text_alt})")
        return accessible_msg
