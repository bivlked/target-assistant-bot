"""
Telegram Formatter for Target Assistant Bot

Converts message templates into Telegram-compatible format including:
- MarkdownV2 formatting
- Inline keyboard generation
- Message length validation
- Telegram-specific optimizations
"""

import re
from typing import Dict, List, Optional, Tuple, Any
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from ..templates.message_templates import MessageTemplate, ActionButton, MessageType
from ..templates.emoji_system import EmojiSystem


class TelegramFormatter:
    """
    Formats message templates for Telegram Bot API

    Handles:
    - MarkdownV2 formatting and escaping
    - Inline keyboard creation
    - Message length validation (4096 char limit)
    - Telegram-specific optimizations
    """

    # Telegram limits
    MAX_MESSAGE_LENGTH = 4096
    MAX_BUTTONS_PER_ROW = 3
    MAX_KEYBOARD_ROWS = 8
    MAX_BUTTON_TEXT_LENGTH = 64

    # MarkdownV2 characters that need escaping
    MARKDOWNV2_ESCAPE_CHARS = [
        "_",
        "*",
        "[",
        "]",
        "(",
        ")",
        "~",
        "`",
        ">",
        "#",
        "+",
        "-",
        "=",
        "|",
        "{",
        "}",
        ".",
        "!",
    ]

    @classmethod
    def escape_markdownv2(cls, text: str) -> str:
        """
        Escape special characters for MarkdownV2

        Args:
            text: Text to escape

        Returns:
            str: Escaped text safe for MarkdownV2
        """
        for char in cls.MARKDOWNV2_ESCAPE_CHARS:
            text = text.replace(char, f"\\{char}")
        return text

    @classmethod
    def format_bold(cls, text: str) -> str:
        """Format text as bold in MarkdownV2"""
        escaped_text = cls.escape_markdownv2(text)
        return f"*{escaped_text}*"

    @classmethod
    def format_italic(cls, text: str) -> str:
        """Format text as italic in MarkdownV2"""
        escaped_text = cls.escape_markdownv2(text)
        return f"_{escaped_text}_"

    @classmethod
    def format_code(cls, text: str) -> str:
        """Format text as code in MarkdownV2"""
        # Code blocks don't need escaping
        return f"`{text}`"

    @classmethod
    def format_link(cls, text: str, url: str) -> str:
        """Format link in MarkdownV2"""
        escaped_text = cls.escape_markdownv2(text)
        return f"[{escaped_text}]({url})"

    @classmethod
    def create_inline_keyboard(
        cls, actions: List[ActionButton]
    ) -> Optional[InlineKeyboardMarkup]:
        """
        Create inline keyboard from action buttons

        Args:
            actions: List of action buttons

        Returns:
            InlineKeyboardMarkup or None if no actions
        """
        if not actions:
            return None

        keyboard = []
        current_row: List[InlineKeyboardButton] = []

        for action in actions:
            # Validate button text length
            button_text = action.render()
            if len(button_text) > cls.MAX_BUTTON_TEXT_LENGTH:
                button_text = button_text[: cls.MAX_BUTTON_TEXT_LENGTH - 3] + "..."

            # Create button
            if action.url:
                button = InlineKeyboardButton(button_text, url=action.url)
            else:
                callback_data = action.callback_data or action.text.lower().replace(
                    " ", "_"
                )
                button = InlineKeyboardButton(button_text, callback_data=callback_data)

            # Button placement logic
            if action.style == "primary" or len(current_row) == 0:
                # Primary buttons get their own row, or start new row
                if current_row:
                    keyboard.append(current_row)
                    current_row = []
                current_row.append(button)
                keyboard.append(current_row)
                current_row = []

            elif len(current_row) < cls.MAX_BUTTONS_PER_ROW:
                # Add to current row
                current_row.append(button)

            else:
                # Start new row
                keyboard.append(current_row)
                current_row = [button]

        # Add any remaining buttons
        if current_row:
            keyboard.append(current_row)

        # Validate keyboard size
        if len(keyboard) > cls.MAX_KEYBOARD_ROWS:
            keyboard = keyboard[: cls.MAX_KEYBOARD_ROWS]

        return InlineKeyboardMarkup(keyboard)

    @classmethod
    def format_message_template(
        cls, template: MessageTemplate
    ) -> Tuple[str, Optional[InlineKeyboardMarkup]]:
        """
        Format complete message template for Telegram

        Args:
            template: Message template to format

        Returns:
            Tuple of (formatted_text, inline_keyboard)
        """
        parts = []

        # Title with emoji (formatted as bold)
        if template.title:
            title_text = template.title
            if template.title_emoji:
                emoji = EmojiSystem.get_emoji(template.title_emoji)
                title_text = f"{emoji} {template.title}"

            parts.append(cls.format_bold(title_text))

        # Subtitle
        if template.subtitle:
            parts.append(cls.escape_markdownv2(template.subtitle))

        # Empty line after title section
        if template.title or template.subtitle:
            parts.append("")

        # Content components
        for component in template.content:
            component_text = component.content

            # Add emoji if specified
            if component.emoji_key:
                try:
                    emoji = EmojiSystem.get_emoji(component.emoji_key)
                    component_text = f"{emoji} {component_text}"
                except KeyError:
                    # If emoji key not found, continue without emoji
                    pass

            # Apply formatting
            if component.formatting == "bold":
                component_text = cls.format_bold(component_text)
            elif component.formatting == "italic":
                component_text = cls.format_italic(component_text)
            elif component.formatting == "code":
                component_text = cls.format_code(component_text)
            else:
                component_text = cls.escape_markdownv2(component_text)

            parts.append(component_text)

        # Progress indicator
        if template.progress:
            parts.append("")
            progress_text = template.progress.render()
            parts.append(cls.escape_markdownv2(progress_text))

        # Footer
        if template.footer:
            parts.append("")
            parts.append(cls.escape_markdownv2(template.footer))

        # Join all parts
        message_text = "\n".join(parts)

        # Validate message length
        if len(message_text) > cls.MAX_MESSAGE_LENGTH:
            # Truncate message if too long
            truncated_text = message_text[: cls.MAX_MESSAGE_LENGTH - 50]
            message_text = (
                truncated_text
                + "\n\n"
                + cls.escape_markdownv2("... (message truncated)")
            )

        # Create inline keyboard
        keyboard = cls.create_inline_keyboard(template.actions)

        return message_text, keyboard

    @classmethod
    def format_progress_bar(cls, current: int, total: int, width: int = 10) -> str:
        """
        Create Telegram-optimized progress bar

        Args:
            current: Current progress value
            total: Total value
            width: Bar width in characters

        Returns:
            str: Formatted progress bar
        """
        if total == 0:
            return "▫️" * width + " 0%"

        percentage = current / total
        filled = int(percentage * width)
        empty = width - filled

        # Use Telegram-friendly progress symbols
        bar = "▪️" * filled + "▫️" * empty
        percentage_text = f"{percentage * 100:.0f}%"

        return f"{bar} {percentage_text}"

    @classmethod
    def create_quick_reply_keyboard(
        cls, options: List[str], max_per_row: int = 2
    ) -> InlineKeyboardMarkup:
        """
        Create quick reply keyboard for common responses

        Args:
            options: List of quick reply options
            max_per_row: Maximum buttons per row

        Returns:
            InlineKeyboardMarkup: Quick reply keyboard
        """
        keyboard = []
        current_row = []

        for option in options:
            if len(option) > cls.MAX_BUTTON_TEXT_LENGTH:
                option = option[: cls.MAX_BUTTON_TEXT_LENGTH - 3] + "..."

            button = InlineKeyboardButton(
                option, callback_data=f"quick_{option.lower().replace(' ', '_')}"
            )
            current_row.append(button)

            if len(current_row) >= max_per_row:
                keyboard.append(current_row)
                current_row = []

        if current_row:
            keyboard.append(current_row)

        return InlineKeyboardMarkup(keyboard)

    @classmethod
    def format_list_items(cls, items: List[str], emoji_prefix: str = "•") -> str:
        """
        Format list items with consistent styling

        Args:
            items: List of items to format
            emoji_prefix: Emoji to use as bullet point

        Returns:
            str: Formatted list
        """
        formatted_items = []
        for item in items:
            escaped_item = cls.escape_markdownv2(item)
            formatted_items.append(f"{emoji_prefix} {escaped_item}")

        return "\n".join(formatted_items)

    @classmethod
    def create_navigation_keyboard(
        cls, current_page: int, total_pages: int, prefix: str = "page"
    ) -> InlineKeyboardMarkup:
        """
        Create navigation keyboard for paginated content

        Args:
            current_page: Current page number (1-based)
            total_pages: Total number of pages
            prefix: Callback data prefix

        Returns:
            InlineKeyboardMarkup: Navigation keyboard
        """
        keyboard = []
        nav_row = []

        # Previous button
        if current_page > 1:
            nav_row.append(
                InlineKeyboardButton(
                    "◀️ Prev", callback_data=f"{prefix}_{current_page-1}"
                )
            )

        # Current page indicator
        nav_row.append(
            InlineKeyboardButton(f"{current_page}/{total_pages}", callback_data="noop")
        )

        # Next button
        if current_page < total_pages:
            nav_row.append(
                InlineKeyboardButton(
                    "Next ▶️", callback_data=f"{prefix}_{current_page+1}"
                )
            )

        keyboard.append(nav_row)
        return InlineKeyboardMarkup(keyboard)

    @classmethod
    def validate_telegram_message(cls, text: str) -> Tuple[bool, List[str]]:
        """
        Validate message for Telegram compatibility

        Args:
            text: Message text to validate

        Returns:
            Tuple of (is_valid, list_of_issues)
        """
        issues = []

        # Check message length
        if len(text) > cls.MAX_MESSAGE_LENGTH:
            issues.append(f"Message too long: {len(text)} > {cls.MAX_MESSAGE_LENGTH}")

        # Check for unescaped MarkdownV2 characters
        for char in cls.MARKDOWNV2_ESCAPE_CHARS:
            if char in text and f"\\{char}" not in text:
                # Simple check - this could be improved with regex
                pattern = f"(?<!\\\\)\\{re.escape(char)}"
                if re.search(pattern, text):
                    issues.append(f"Unescaped MarkdownV2 character: {char}")

        # Check for emoji validity (basic check)
        emoji_warnings = EmojiSystem.validate_emoji_usage(text)
        issues.extend(emoji_warnings)

        return len(issues) == 0, issues

    @classmethod
    def optimize_for_mobile(cls, template: MessageTemplate) -> MessageTemplate:
        """
        Optimize message template for mobile viewing

        Args:
            template: Original template

        Returns:
            MessageTemplate: Mobile-optimized template
        """
        # Create a copy of the template
        optimized = MessageTemplate(
            message_type=template.message_type,
            title=template.title,
            title_emoji=template.title_emoji,
            subtitle=template.subtitle,
            content=template.content[:],  # Copy content list
            progress=template.progress,
            actions=template.actions[:],  # Copy actions list
            footer=template.footer,
        )

        # Shorten title if too long for mobile
        if optimized.title and len(optimized.title) > 30:
            optimized.title = optimized.title[:27] + "..."

        # Limit number of content components for mobile
        if len(optimized.content) > 8:
            optimized.content = optimized.content[:7]
            optimized.content.append(
                type(optimized.content[0])("... (tap for more)", formatting="italic")
            )

        # Optimize action buttons for mobile
        if len(optimized.actions) > 6:
            # Keep most important actions
            primary_actions = [a for a in optimized.actions if a.style == "primary"][:2]
            secondary_actions = [a for a in optimized.actions if a.style != "primary"][
                :3
            ]
            more_button = ActionButton(
                "More...", callback_data="more_actions", style="secondary"
            )

            optimized.actions = primary_actions + secondary_actions + [more_button]

        return optimized


class TelegramMessageBuilder:
    """Helper class for building complex Telegram messages"""

    def __init__(self) -> None:
        self.formatter = TelegramFormatter()
        self.parts: List[str] = []
        self.buttons: List[ActionButton] = []

    def add_header(
        self, text: str, emoji_key: Optional[str] = None
    ) -> "TelegramMessageBuilder":
        """Add header with emoji"""
        if emoji_key:
            emoji = EmojiSystem.get_emoji(emoji_key)
            text = f"{emoji} {text}"

        self.parts.append(self.formatter.format_bold(text))
        return self

    def add_text(
        self, text: str, formatting: Optional[str] = None
    ) -> "TelegramMessageBuilder":
        """Add formatted text"""
        if formatting == "bold":
            text = self.formatter.format_bold(text)
        elif formatting == "italic":
            text = self.formatter.format_italic(text)
        elif formatting == "code":
            text = self.formatter.format_code(text)
        else:
            text = self.formatter.escape_markdownv2(text)

        self.parts.append(text)
        return self

    def add_list(
        self, items: List[str], emoji_prefix: str = "•"
    ) -> "TelegramMessageBuilder":
        """Add formatted list"""
        formatted_list = self.formatter.format_list_items(items, emoji_prefix)
        self.parts.append(formatted_list)
        return self

    def add_progress(self, current: int, total: int) -> "TelegramMessageBuilder":
        """Add progress bar"""
        progress_bar = self.formatter.format_progress_bar(current, total)
        self.parts.append(progress_bar)
        return self

    def add_button(
        self, text: str, callback_data: str, emoji_key: Optional[str] = None
    ) -> "TelegramMessageBuilder":
        """Add button to keyboard"""
        if emoji_key:
            emoji = EmojiSystem.get_emoji(emoji_key)
            text = f"{emoji} {text}"

        button = ActionButton(text, callback_data=callback_data)
        self.buttons.append(button)
        return self

    def add_empty_line(self) -> "TelegramMessageBuilder":
        """Add empty line"""
        self.parts.append("")
        return self

    def build(self) -> Tuple[str, Optional[InlineKeyboardMarkup]]:
        """Build final message"""
        message_text = "\n".join(self.parts)
        keyboard = (
            self.formatter.create_inline_keyboard(self.buttons)
            if self.buttons
            else None
        )

        return message_text, keyboard
