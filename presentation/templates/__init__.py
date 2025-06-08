"""
Message Templates Package

Contains emoji system and message template implementations
for consistent UI/UX across the Target Assistant Bot.
"""

from .emoji_system import (
    EmojiSystem,
    EmojiCategory,
    EmojiDefinition,
    EmojiCombinations,
    AccessibilityEmojis,
)
from .message_templates import (
    MessageTemplates,
    MessageTemplate,
    MessageComponent,
    MessageType,
    ActionButton,
    ProgressIndicator,
    CommonTemplates,
)

__all__ = [
    "EmojiSystem",
    "EmojiCategory",
    "EmojiDefinition",
    "EmojiCombinations",
    "AccessibilityEmojis",
    "MessageTemplates",
    "MessageTemplate",
    "MessageComponent",
    "MessageType",
    "ActionButton",
    "ProgressIndicator",
    "CommonTemplates",
]
