"""
Extended tests for Emoji System to improve coverage

Tests edge cases and error handling in emoji_system.py
"""

import pytest
from presentation.templates.emoji_system import (
    EmojiSystem,
    EmojiCategory,
    EmojiCombinations,
    AccessibilityEmojis,
)


class TestEmojiSystemErrorCases:
    """Test error cases and edge scenarios for EmojiSystem"""

    def test_get_emoji_definition_invalid_key(self):
        """Test get_emoji_definition with invalid key raises KeyError"""
        with pytest.raises(KeyError, match="not found in design system"):
            EmojiSystem.get_emoji_definition("nonexistent_key")

    def test_get_category_emojis_invalid_category(self):
        """Test get_category_emojis with invalid category returns empty dict"""

        # Create a mock invalid category (enum values not in the mapping)
        class InvalidCategory:
            pass

        result = EmojiSystem.get_category_emojis(InvalidCategory())
        assert result == {}

    def test_format_combination_pattern_with_unknown_steps(self):
        """Test format_combination_pattern with steps that are not emoji keys"""
        # Pattern with unknown step
        pattern = "goals -> unknown_step -> success"
        result = EmojiSystem.format_combination_pattern(pattern)

        # Should contain emoji for known steps and preserve unknown steps
        assert "🎯" in result  # goals emoji
        assert "✅" in result  # success emoji
        assert "unknown_step" in result  # preserved as-is
        assert "→" in result  # separator

    def test_format_combination_pattern_with_mixed_content(self):
        """Test format_combination_pattern with mixed known/unknown content"""
        pattern = "custom text -> goals -> another text"
        result = EmojiSystem.format_combination_pattern(pattern)

        assert "custom text" in result
        assert "🎯" in result  # goals emoji
        assert "another text" in result
        assert "→" in result

    def test_validate_emoji_usage_empty_text(self):
        """Test validate_emoji_usage with empty text"""
        warnings = EmojiSystem.validate_emoji_usage("")
        assert warnings == []

    def test_validate_emoji_usage_text_without_emojis(self):
        """Test validate_emoji_usage with text containing no emojis"""
        warnings = EmojiSystem.validate_emoji_usage("Just plain text with no emojis")
        assert warnings == []

    def test_validate_emoji_usage_non_standard_emojis(self):
        """Test validate_emoji_usage with non-standard emojis"""
        # Use emojis that are not in the design system
        text = "Check this out 😀 and this 🚀"
        warnings = EmojiSystem.validate_emoji_usage(text)

        # Should have warnings for non-standard emojis
        assert len(warnings) > 0
        assert any("Non-standard emoji" in warning for warning in warnings)

    def test_validate_emoji_usage_standard_emojis(self):
        """Test validate_emoji_usage with standard design system emojis"""
        text = f"Goals {EmojiSystem.get_emoji('goals')} and success {EmojiSystem.get_emoji('success')}"
        warnings = EmojiSystem.validate_emoji_usage(text)

        # Should have no warnings for standard emojis
        assert warnings == []


class TestAccessibilityEmojisExtended:
    """Test AccessibilityEmojis edge cases"""

    def test_emoji_to_text_all_keys(self):
        """Test emoji_to_text with all available emoji keys"""
        for key in EmojiSystem.get_all_emoji_keys():
            text = AccessibilityEmojis.emoji_to_text(key)
            assert isinstance(text, str)
            assert len(text) > 0

    def test_create_accessible_message_empty_keys(self):
        """Test create_accessible_message with empty emoji keys list"""
        message = "Test message with 🎯 emoji"
        result = AccessibilityEmojis.create_accessible_message(message, [])

        # Should return original message if no keys provided
        assert result == message

    def test_create_accessible_message_keys_not_in_message(self):
        """Test create_accessible_message with keys that don't appear in message"""
        message = "Simple message without emojis"
        result = AccessibilityEmojis.create_accessible_message(
            message, ["goals", "success"]
        )

        # Should return original message if emojis not found
        assert result == message

    def test_create_accessible_message_multiple_same_emoji(self):
        """Test create_accessible_message with multiple instances of same emoji"""
        goals_emoji = EmojiSystem.get_emoji("goals")
        message = f"First {goals_emoji} and second {goals_emoji} goal"
        result = AccessibilityEmojis.create_accessible_message(message, ["goals"])

        # Both instances should be replaced
        assert result.count("(Goals & Targets)") == 2


class TestEmojiCombinations:
    """Test EmojiCombinations class"""

    def test_predefined_combinations_are_valid(self):
        """Test that all predefined combinations contain valid emojis"""
        # Goal Creation Flow
        assert "🎯" in EmojiCombinations.GOAL_CREATION
        assert "✅" in EmojiCombinations.GOAL_CREATION

        # Task Flow
        assert "📝" in EmojiCombinations.TASK_FLOW
        assert "🔄" in EmojiCombinations.TASK_FLOW
        assert "✅" in EmojiCombinations.TASK_FLOW

        # Progress Flow
        assert "📊" in EmojiCombinations.PROGRESS_FLOW
        assert "🎉" in EmojiCombinations.PROGRESS_FLOW

        # Error Recovery
        assert "❌" in EmojiCombinations.ERROR_RECOVERY
        assert "ℹ️" in EmojiCombinations.ERROR_RECOVERY
        assert "✅" in EmojiCombinations.ERROR_RECOVERY


class TestEmojiSystemComprehensive:
    """Comprehensive tests to ensure all functionality is covered"""

    def test_all_categories_have_emojis(self):
        """Test that all emoji categories have emojis defined"""
        for category in EmojiCategory:
            emojis = EmojiSystem.get_category_emojis(category)
            assert len(emojis) > 0

    def test_get_emoji_with_category_validation(self):
        """Test get_emoji with strict category validation"""
        # Valid case
        emoji = EmojiSystem.get_emoji("goals", EmojiCategory.CORE_ACTIONS)
        assert emoji == "🎯"

        # Invalid category for emoji
        with pytest.raises(KeyError, match="not found in category"):
            EmojiSystem.get_emoji("goals", EmojiCategory.STATUS_FEEDBACK)

    def test_emoji_definitions_completeness(self):
        """Test that all emoji definitions are complete"""
        for key in EmojiSystem.get_all_emoji_keys():
            definition = EmojiSystem.get_emoji_definition(key)

            # All fields should be present and non-empty
            assert definition.emoji
            assert definition.name
            assert definition.meaning
            assert definition.usage_context
            assert isinstance(definition.category, EmojiCategory)
