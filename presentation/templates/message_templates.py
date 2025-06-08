"""
Message Templates System for Target Assistant Bot

Implements standardized message formatting following UI Style Guide principles.
Provides consistent message structure across all user interactions.
"""

from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field
from enum import Enum
from .emoji_system import EmojiSystem


class MessageType(Enum):
    """Types of messages in the system"""

    SUCCESS = "success"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"
    PROGRESS = "progress"
    GOAL_SUMMARY = "goal_summary"
    TASK_LIST = "task_list"
    ACHIEVEMENT = "achievement"
    MAIN_MENU = "main_menu"
    CONTEXT_MENU = "context_menu"


@dataclass
class MessageComponent:
    """Individual message component with formatting"""

    content: str
    emoji_key: Optional[str] = None
    formatting: Optional[str] = None  # 'bold', 'italic', 'code'

    def render(self) -> str:
        """Render component with proper formatting"""
        text = self.content

        # Add emoji if specified
        if self.emoji_key:
            emoji = EmojiSystem.get_emoji(self.emoji_key)
            text = f"{emoji} {text}"

        # Apply formatting
        if self.formatting == "bold":
            text = f"**{text}**"
        elif self.formatting == "italic":
            text = f"*{text}*"
        elif self.formatting == "code":
            text = f"`{text}`"

        return text


@dataclass
class ProgressIndicator:
    """Progress visualization component"""

    current: int
    total: int
    style: str = "bar"  # 'bar', 'simple', 'detailed'

    def render(self) -> str:
        """Render progress indicator"""
        percentage = (self.current / self.total * 100) if self.total > 0 else 0

        if self.style == "bar":
            filled = int(percentage / 10)
            empty = 10 - filled
            bar = "█" * filled + "░" * empty
            return f"{bar} {percentage:.0f}%"

        elif self.style == "simple":
            return f"{self.current}/{self.total}"

        elif self.style == "detailed":
            return f"━━━━━━━━━━ {percentage:.0f}%\n{self.current} completed • {self.total - self.current} remaining"

        return f"{self.current}/{self.total}"


@dataclass
class ActionButton:
    """Action button component"""

    text: str
    emoji_key: Optional[str] = None
    callback_data: Optional[str] = None
    url: Optional[str] = None
    style: str = "primary"  # 'primary', 'secondary', 'destructive'

    def render(self) -> str:
        """Render button text"""
        text = self.text
        if self.emoji_key:
            emoji = EmojiSystem.get_emoji(self.emoji_key)
            text = f"{emoji} {text}"
        return text


@dataclass
class MessageTemplate:
    """Complete message template structure"""

    message_type: MessageType
    title: Optional[str] = None
    title_emoji: Optional[str] = None
    subtitle: Optional[str] = None
    content: List[MessageComponent] = field(default_factory=list)
    progress: Optional[ProgressIndicator] = None
    actions: List[ActionButton] = field(default_factory=list)
    footer: Optional[str] = None

    def render(self) -> str:
        """Render complete message"""
        parts = []

        # Title with emoji
        if self.title:
            title_text = self.title
            if self.title_emoji:
                emoji = EmojiSystem.get_emoji(self.title_emoji)
                title_text = f"{emoji} **{self.title}**"
            else:
                title_text = f"**{self.title}**"
            parts.append(title_text)

        # Subtitle
        if self.subtitle:
            parts.append(self.subtitle)

        # Empty line after title section
        if self.title or self.subtitle:
            parts.append("")

        # Content components
        for component in self.content:
            parts.append(component.render())

        # Progress indicator
        if self.progress:
            parts.append("")
            parts.append(self.progress.render())

        # Action buttons section
        if self.actions:
            parts.append("")
            # Note: Actual button rendering would be handled by Telegram formatter
            action_texts = [action.render() for action in self.actions]
            parts.append("Actions: " + " | ".join(action_texts))

        # Footer
        if self.footer:
            parts.append("")
            parts.append(self.footer)

        return "\n".join(parts)


class MessageTemplates:
    """
    Collection of standardized message templates

    Implements all message patterns from UI Style Guide:
    - Header Components
    - Content Components
    - Interactive Components
    - Error Handling Templates
    """

    @staticmethod
    def success_message(
        title: str,
        description: Optional[str] = None,
        next_steps: Optional[List[str]] = None,
        actions: Optional[List[ActionButton]] = None,
    ) -> MessageTemplate:
        """Create success message template"""
        content = []

        if description:
            content.append(MessageComponent(description))

        if next_steps:
            content.append(MessageComponent("Next steps:", formatting="bold"))
            for step in next_steps:
                content.append(MessageComponent(f"• {step}"))

        return MessageTemplate(
            message_type=MessageType.SUCCESS,
            title=title,
            title_emoji="success",
            content=content,
            actions=actions or [],
        )

    @staticmethod
    def error_message(
        error_type: str,
        description: str,
        solutions: List[str],
        actions: Optional[List[ActionButton]] = None,
    ) -> MessageTemplate:
        """Create error message template following UI Style Guide pattern"""
        content = [MessageComponent(description)]

        if solutions:
            content.append(
                MessageComponent("💡 **What you can do:**", formatting="bold")
            )
            for solution in solutions:
                content.append(MessageComponent(f"• {solution}"))

        default_actions = actions or [
            ActionButton("🔄 Retry", emoji_key="in_progress"),
            ActionButton("🔙 Back", callback_data="back"),
        ]

        return MessageTemplate(
            message_type=MessageType.ERROR,
            title=error_type,
            title_emoji="error",
            content=content,
            actions=default_actions,
        )

    @staticmethod
    def goal_summary_card(
        goal_name: str,
        deadline: str,
        progress_current: int,
        progress_total: int,
        time_left: str,
        actions: Optional[List[ActionButton]] = None,
    ) -> MessageTemplate:
        """Create goal summary card following UI Style Guide pattern"""
        progress = ProgressIndicator(progress_current, progress_total, style="detailed")

        content = [
            MessageComponent(f"📅 Deadline: {deadline}"),
            MessageComponent(f"⏰ Time left: {time_left}"),
        ]

        default_actions = actions or [
            ActionButton("Add Task", emoji_key="tasks"),
            ActionButton("View Progress", emoji_key="progress"),
        ]

        return MessageTemplate(
            message_type=MessageType.GOAL_SUMMARY,
            title=goal_name,
            title_emoji="goals",
            content=content,
            progress=progress,
            actions=default_actions,
        )

    @staticmethod
    def task_list_item(
        task_name: str,
        due_date: Optional[str] = None,
        is_completed: bool = False,
        progress_current: Optional[int] = None,
        progress_total: Optional[int] = None,
    ) -> MessageTemplate:
        """Create task list item following UI Style Guide pattern"""
        emoji_key = "success" if is_completed else "tasks"
        content = []

        if due_date:
            content.append(MessageComponent(f"📅 Due: {due_date}"))

        progress = None
        if progress_current is not None and progress_total is not None:
            progress = ProgressIndicator(progress_current, progress_total)

        return MessageTemplate(
            message_type=MessageType.TASK_LIST,
            title=task_name,
            title_emoji=emoji_key,
            content=content,
            progress=progress,
        )

    @staticmethod
    def achievement_badge(
        achievement_name: str, description: str, motivation_text: str
    ) -> MessageTemplate:
        """Create achievement badge following UI Style Guide pattern"""
        content = [
            MessageComponent(achievement_name, emoji_key="celebration"),
            MessageComponent(motivation_text, emoji_key="encouragement"),
        ]

        return MessageTemplate(
            message_type=MessageType.ACHIEVEMENT,
            title="Achievement Unlocked!",
            title_emoji="achievement",
            content=content,
        )

    @staticmethod
    def main_menu(
        user_name: Optional[str] = None, actions: Optional[List[ActionButton]] = None
    ) -> MessageTemplate:
        """Create main menu following UI Style Guide pattern"""
        title = "Target Assistant"
        if user_name:
            title = f"Target Assistant - {user_name}"

        content = [MessageComponent("Choose an action:")]

        default_actions = actions or [
            ActionButton("Manage Goals", emoji_key="goals"),
            ActionButton("Daily Tasks", emoji_key="tasks"),
            ActionButton("View Progress", emoji_key="progress"),
            ActionButton("Settings", emoji_key="settings"),
            ActionButton("Help & Support", emoji_key="help"),
        ]

        return MessageTemplate(
            message_type=MessageType.MAIN_MENU,
            title=title,
            content=content,
            actions=default_actions,
        )

    @staticmethod
    def context_menu(
        context_name: str, context_emoji: str, actions: List[ActionButton]
    ) -> MessageTemplate:
        """Create context menu following UI Style Guide pattern"""
        content = [MessageComponent("Actions available:")]

        # Add back button to all context menus
        back_action = ActionButton("Back", callback_data="back", style="secondary")
        all_actions = actions + [back_action]

        return MessageTemplate(
            message_type=MessageType.CONTEXT_MENU,
            title=context_name,
            title_emoji=context_emoji,
            content=content,
            actions=all_actions,
        )

    @staticmethod
    def progress_report(
        title: str,
        progress_current: int,
        progress_total: int,
        completed_items: List[str],
        remaining_items: List[str],
        streak_count: Optional[int] = None,
        motivation_text: Optional[str] = None,
    ) -> MessageTemplate:
        """Create progress report following UI Style Guide pattern"""
        progress = ProgressIndicator(progress_current, progress_total, style="detailed")

        content = []

        if completed_items:
            content.append(MessageComponent("Completed:", formatting="bold"))
            for item in completed_items:
                content.append(MessageComponent(f"✅ {item}"))

        if remaining_items:
            content.append(MessageComponent("Remaining:", formatting="bold"))
            for item in remaining_items:
                content.append(MessageComponent(f"📝 {item}"))

        if streak_count:
            content.append(MessageComponent(f"🔥 {streak_count}-day streak!"))

        if motivation_text:
            content.append(MessageComponent(motivation_text, emoji_key="encouragement"))

        return MessageTemplate(
            message_type=MessageType.PROGRESS,
            title=title,
            title_emoji="progress",
            content=content,
            progress=progress,
        )

    @staticmethod
    def info_message(
        topic: str,
        information: str,
        related_actions: Optional[List[ActionButton]] = None,
    ) -> MessageTemplate:
        """Create information message following UI Style Guide pattern"""
        content = [MessageComponent(information)]

        return MessageTemplate(
            message_type=MessageType.INFO,
            title=topic,
            title_emoji="info",
            content=content,
            actions=related_actions or [],
        )

    @staticmethod
    def warning_message(
        warning_type: str,
        description: str,
        recommendations: List[str],
        actions: Optional[List[ActionButton]] = None,
    ) -> MessageTemplate:
        """Create warning message following UI Style Guide pattern"""
        content = [MessageComponent(description)]

        if recommendations:
            content.append(
                MessageComponent("💡 **Recommendations:**", formatting="bold")
            )
            for rec in recommendations:
                content.append(MessageComponent(f"• {rec}"))

        return MessageTemplate(
            message_type=MessageType.WARNING,
            title=warning_type,
            title_emoji="warning",
            content=content,
            actions=actions or [],
        )


# Pre-defined common templates for quick usage
class CommonTemplates:
    """Collection of frequently used template instances"""

    @staticmethod
    def goal_created_success(goal_name: str) -> MessageTemplate:
        """Quick template for goal creation success"""
        return MessageTemplates.success_message(
            title="Goal Created!",
            description=f"🎯 {goal_name}",
            next_steps=["Add tasks to your goal", "Set up reminders", "Start working!"],
            actions=[
                ActionButton("Add Tasks", emoji_key="tasks"),
                ActionButton("View Goal", emoji_key="progress"),
            ],
        )

    @staticmethod
    def task_completed_celebration(task_name: str) -> MessageTemplate:
        """Quick template for task completion"""
        return MessageTemplates.achievement_badge(
            achievement_name="Task Completed!",
            description=f"📝 {task_name}",
            motivation_text="Great work! Keep the momentum going!",
        )

    @staticmethod
    def network_error() -> MessageTemplate:
        """Standard network error template"""
        return MessageTemplates.error_message(
            error_type="Connection Problem",
            description="Unable to connect to the service.",
            solutions=[
                "Check your internet connection",
                "Wait a moment and retry",
                "Contact support if problem persists",
            ],
            actions=[
                ActionButton("Retry", emoji_key="in_progress"),
                ActionButton("Back", callback_data="back"),
            ],
        )

    @staticmethod
    def invalid_input_error(issue: str, example: str) -> MessageTemplate:
        """Standard input validation error template"""
        return MessageTemplates.error_message(
            error_type="Invalid Input",
            description=issue,
            solutions=[f"Example: {example}", "Try again with correct format"],
            actions=[
                ActionButton("Try Again", callback_data="retry"),
                ActionButton("Help", emoji_key="help"),
            ],
        )
