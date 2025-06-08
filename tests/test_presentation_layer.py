"""
Tests for Presentation Layer Components

Tests emoji system, message templates, and Telegram formatter.
"""

import pytest
from presentation.templates.emoji_system import EmojiSystem, EmojiCategory
from presentation.templates.message_templates import (
    MessageTemplates,
    ActionButton,
    CommonTemplates,
)
from presentation.formatters.telegram_formatter import TelegramFormatter


class TestEmojiSystem:
    """Test emoji design system"""

    def test_get_emoji_by_key(self):
        """Test getting emoji by key"""
        emoji = EmojiSystem.get_emoji("goals")
        assert emoji == "🎯"

        emoji = EmojiSystem.get_emoji("success")
        assert emoji == "✅"

    def test_get_emoji_with_category_filter(self):
        """Test getting emoji with category filter"""
        emoji = EmojiSystem.get_emoji("goals", EmojiCategory.CORE_ACTIONS)
        assert emoji == "🎯"

        # This should raise KeyError since 'goals' is not in STATUS_FEEDBACK
        with pytest.raises(KeyError):
            EmojiSystem.get_emoji("goals", EmojiCategory.STATUS_FEEDBACK)

    def test_invalid_emoji_key(self):
        """Test invalid emoji key raises KeyError"""
        with pytest.raises(KeyError):
            EmojiSystem.get_emoji("invalid_key")

    def test_get_all_emoji_keys(self):
        """Test getting all available emoji keys"""
        keys = EmojiSystem.get_all_emoji_keys()
        assert "goals" in keys
        assert "success" in keys
        assert "celebration" in keys
        assert len(keys) > 0

    def test_emoji_combination_patterns(self):
        """Test emoji combination formatting"""
        pattern = EmojiSystem.format_combination_pattern("goals -> success")
        assert "🎯" in pattern
        assert "✅" in pattern
        assert "→" in pattern


class TestMessageTemplates:
    """Test message template system"""

    def test_success_message_template(self):
        """Test success message creation"""
        template = MessageTemplates.success_message(
            title="Test Success",
            description="Test description",
            next_steps=["Step 1", "Step 2"],
        )

        assert template.title == "Test Success"
        assert template.title_emoji == "success"
        assert len(template.content) >= 2  # description + next steps

        rendered = template.render()
        assert "Test Success" in rendered
        assert "Test description" in rendered
        assert "Step 1" in rendered

    def test_error_message_template(self):
        """Test error message creation"""
        template = MessageTemplates.error_message(
            error_type="Test Error",
            description="Something went wrong",
            solutions=["Try again", "Contact support"],
        )

        assert template.title == "Test Error"
        assert template.title_emoji == "error"
        assert len(template.actions) >= 2  # Default retry and back buttons

        rendered = template.render()
        assert "Test Error" in rendered
        assert "Something went wrong" in rendered
        assert "Try again" in rendered

    def test_goal_summary_card(self):
        """Test goal summary card creation"""
        template = MessageTemplates.goal_summary_card(
            goal_name="Test Goal",
            deadline="2025-02-01",
            progress_current=3,
            progress_total=10,
            time_left="24 days",
        )

        assert template.title == "Test Goal"
        assert template.title_emoji == "goals"
        assert template.progress is not None
        assert template.progress.current == 3
        assert template.progress.total == 10

        rendered = template.render()
        assert "Test Goal" in rendered
        assert "2025-02-01" in rendered
        assert "24 days" in rendered

    def test_main_menu_template(self):
        """Test main menu creation"""
        template = MessageTemplates.main_menu(user_name="TestUser")

        assert "TestUser" in template.title
        assert len(template.actions) >= 5  # Default menu actions

        rendered = template.render()
        assert "TestUser" in rendered
        assert "Choose an action" in rendered


class TestCommonTemplates:
    """Test common template shortcuts"""

    def test_goal_created_success(self):
        """Test goal creation success template"""
        template = CommonTemplates.goal_created_success("My New Goal")

        assert template.title == "Goal Created!"
        assert "My New Goal" in template.render()
        assert len(template.actions) >= 2

    def test_task_completed_celebration(self):
        """Test task completion template"""
        template = CommonTemplates.task_completed_celebration("Complete project")

        assert "Achievement Unlocked!" in template.title
        assert "Task Completed!" in template.render()  # This is what appears in content
        assert "Great work!" in template.render()

    def test_network_error(self):
        """Test standard network error template"""
        template = CommonTemplates.network_error()

        assert template.title == "Connection Problem"
        assert "internet connection" in template.render()
        assert len(template.actions) >= 2


class TestTelegramFormatter:
    """Test Telegram formatter"""

    def test_escape_markdownv2(self):
        """Test MarkdownV2 escaping"""
        text = "Test (with) special-chars!"
        escaped = TelegramFormatter.escape_markdownv2(text)

        assert "\\(" in escaped
        assert "\\)" in escaped
        assert "\\-" in escaped
        assert "\\!" in escaped

    def test_format_bold(self):
        """Test bold formatting"""
        formatted = TelegramFormatter.format_bold("Bold Text")
        assert formatted.startswith("*")
        assert formatted.endswith("*")
        assert "Bold Text" in formatted

    def test_format_message_template(self):
        """Test complete message template formatting"""
        template = MessageTemplates.success_message(
            title="Test Success", description="Test description"
        )

        text, keyboard = TelegramFormatter.format_message_template(template)

        assert "✅" in text  # Success emoji
        assert "*✅ Test Success*" in text  # Bold title with emoji
        assert "Test description" in text
        assert keyboard is None  # No actions = no keyboard

    def test_format_template_with_actions(self):
        """Test template formatting with action buttons"""
        actions = [
            ActionButton("Test Action", callback_data="test"),
            ActionButton("Another Action", callback_data="another"),
        ]

        template = MessageTemplates.info_message(
            topic="Test Info", information="Test information", related_actions=actions
        )

        text, keyboard = TelegramFormatter.format_message_template(template)

        assert keyboard is not None
        assert len(keyboard.inline_keyboard) >= 1

    def test_create_inline_keyboard(self):
        """Test inline keyboard creation"""
        actions = [
            ActionButton("Button 1", callback_data="btn1"),
            ActionButton("Button 2", callback_data="btn2", style="secondary"),
        ]

        keyboard = TelegramFormatter.create_inline_keyboard(actions)

        assert keyboard is not None
        assert len(keyboard.inline_keyboard) >= 1

        # Check button text includes emoji if specified
        button_with_emoji = ActionButton(
            "Test", emoji_key="goals", callback_data="test"
        )
        keyboard_with_emoji = TelegramFormatter.create_inline_keyboard(
            [button_with_emoji]
        )

        button_text = keyboard_with_emoji.inline_keyboard[0][0].text
        assert "🎯" in button_text

    def test_validate_telegram_message(self):
        """Test message validation"""
        # Valid message
        valid_text = "This is a valid message"
        is_valid, issues = TelegramFormatter.validate_telegram_message(valid_text)
        assert is_valid
        assert len(issues) == 0

        # Message too long
        long_text = "x" * 5000
        is_valid, issues = TelegramFormatter.validate_telegram_message(long_text)
        assert not is_valid
        assert any("too long" in issue for issue in issues)


class TestUIIntegration:
    """Integration tests for UI components"""

    def test_complete_ui_flow(self):
        """Test complete UI flow from template to formatted output"""
        # Create a template
        template = MessageTemplates.goal_summary_card(
            goal_name="Learn Python",
            deadline="2025-02-15",
            progress_current=7,
            progress_total=10,
            time_left="15 days",
            actions=[
                ActionButton("Add Task", emoji_key="tasks"),
                ActionButton("View Progress", emoji_key="progress"),
            ],
        )

        # Format for Telegram
        text, keyboard = TelegramFormatter.format_message_template(template)

        # Verify output
        assert "🎯" in text  # Goal emoji
        assert "*🎯 Learn Python*" in text  # Bold title with emoji
        assert "2025\\-02\\-15" in text  # Deadline escaped in MarkdownV2
        assert "15 days" in text  # Time left
        assert keyboard is not None  # Has action buttons
        assert len(keyboard.inline_keyboard) >= 1  # At least one row

        # Verify keyboard buttons
        button_texts = []
        for row in keyboard.inline_keyboard:
            for button in row:
                button_texts.append(button.text)

        assert any("📝" in text for text in button_texts)  # Tasks emoji
        assert any("📊" in text for text in button_texts)  # Progress emoji

    def test_emoji_accessibility(self):
        """Test emoji accessibility features"""
        from presentation.templates.emoji_system import AccessibilityEmojis

        # Test text alternative
        text_with_alt = AccessibilityEmojis.add_text_alternative("🎯", "target")
        assert "🎯 (target)" in text_with_alt

        # Test accessible message creation
        message = "Check your 🎯 goals and 📝 tasks"
        accessible = AccessibilityEmojis.create_accessible_message(
            message, ["goals", "tasks"]
        )
        assert "(Goals & Targets)" in accessible
        assert "(Tasks & Planning)" in accessible
