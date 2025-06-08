# Target Assistant Bot - UI Style Guide

## 🎨 Brand Identity & Voice

### Brand Personality
**Target Assistant** - профессиональный, дружелюбный и мотивирующий AI-помощник для достижения целей.

### Voice & Tone
- **Professional yet Approachable**: Компетентный совет с warm personality
- **Motivational**: Поощряющий и supportive tone
- **Clear & Concise**: Simple language, избегаем jargon
- **Action-Oriented**: Focus на actionable steps и progress

### Communication Principles
- **Positive Language**: Use encouraging phrases
- **Progress Celebration**: Acknowledge achievements
- **Solution-Focused**: Always provide next steps  
- **User Empowerment**: Help users feel in control

## 🎯 Emoji Design Language

### Systematic Emoji Usage

#### 🎯 Core Actions & Features
- `🎯` **Goals & Targets**: Main goal creation, goal management
- `📝` **Tasks & Planning**: Daily tasks, planning activities  
- `📊` **Progress & Analytics**: Statistics, progress tracking
- `⚙️` **Settings & Configuration**: Bot settings, preferences
- `❓` **Help & Support**: Help commands, assistance

#### ✅ Status & Feedback
- `✅` **Success**: Completed actions, achievements
- `❌` **Error**: Failures, problems, errors
- `⚠️` **Warning**: Cautions, important notices
- `ℹ️` **Information**: General info, explanations
- `🔄` **In Progress**: Loading, processing, ongoing actions

#### 🎉 Motivation & Celebration
- `🎉` **Celebration**: Goal completion, major achievements
- `🔥` **Streak & Momentum**: Consistency, hot streaks
- `💪` **Encouragement**: Motivation, support
- `🏆` **Achievements**: Milestones, awards
- `⭐` **Excellence**: Outstanding performance

#### 📅 Time & Scheduling
- `📅` **Calendar**: Date-related actions
- `⏰` **Time**: Time-sensitive actions, reminders
- `📆` **Schedule**: Planning, scheduling
- `🕐` **Deadline**: Due dates, urgency

### Emoji Combination Patterns
```
🎯 New Goal → ✅ Goal Created
📝 Task Added → 🔄 In Progress → ✅ Completed
📊 View Stats → 🎉 Achievement Unlocked
❌ Error → ℹ️ Help Available → ✅ Resolved
```

## 🖼️ Message Component Library

### 1. Header Components

#### Goal Header
```
🎯 **[Goal Title]**
Progress: [X]/[Y] tasks completed
```

#### Task Header  
```
📝 **Daily Tasks** • [Date]
[X]/[Y] completed
```

#### Status Header
```
✅ **Success** | ❌ **Error** | ⚠️ **Warning** | ℹ️ **Info**
```

### 2. Content Components

#### Goal Summary Card
```
🎯 **[Goal Name]**
📅 Deadline: [Date]
📊 Progress: [XX]% • [X]/[Y] tasks
⏰ Time left: [X] days

[Optional: Next action button]
```

#### Task List Item
```
[✅|📝] **[Task Name]**
   📅 Due: [Date]
   [Optional: Progress indicator]
```

#### Progress Indicator
```
📊 **Progress Report**
━━━━━━━━━━ [XX]%
[X] completed • [Y] remaining
```

#### Achievement Badge
```
🏆 **Achievement Unlocked!**
🎉 [Achievement Name]
💪 [Description/Motivation]
```

### 3. Interactive Components

#### Action Buttons
```
Primary: 🎯 Create Goal | 📝 Add Task | 📊 View Progress
Secondary: ⚙️ Settings | ❓ Help | 📅 Calendar
Destructive: ❌ Delete | 🗑️ Remove
```

#### Quick Actions Keyboard
```
Row 1: [🎯 New Goal] [📝 Add Task]
Row 2: [📊 Progress] [⚙️ Settings]  
Row 3: [❓ Help]
```

#### Navigation Flow
```
Main Menu → Feature → Action → Confirmation → Result
     ↓         ↓        ↓           ↓         ↓
   🏠 Home  🎯 Goals  📝 Create   ✅ Success  🎉 Done
```

## 📱 Typography & Formatting

### Text Hierarchy

#### Headers
```markdown
# 🎯 Main Title (Goals, Major Sections)
## 📊 Section Title (Progress, Statistics) 
### 💪 Subsection (Motivational, Details)
```

#### Body Text
- **Bold** for emphasis and key information
- *Italic* for subtle emphasis and quotes
- `Code` for technical terms and commands
- Normal text for general content

#### Lists & Structure
```markdown
• Primary list items (actions, features)
  - Secondary items (details, options)
    ○ Tertiary items (examples, notes)

1. Numbered steps (procedures, tutorials)
2. Sequential actions (goal creation, setup)
```

### Formatting Patterns

#### Success Messages
```
✅ **Success!**
[Action completed successfully]
[Optional: Next steps or motivation]
```

#### Error Messages  
```
❌ **Error**
[Clear error description]
💡 **Solution**: [Actionable fix]
❓ Need help? Use /help
```

#### Information Messages
```
ℹ️ **[Topic]**
[Key information]
[Optional: Related actions]
```

## 🎨 Visual Design Patterns

### Message Structure Template

```
[EMOJI] **[TITLE]**
[Optional: Subtitle or context]

[Main content with proper formatting]
[Optional: Progress indicators, lists, etc.]

[Action buttons or next steps]
[Optional: Help or navigation hints]
```

### Card-Style Information Display

```
┏━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ 🎯 Goal: [Name]        ┃
┠────────────────────────┨
┃ 📊 Progress: XX%       ┃
┃ 📅 Deadline: [Date]    ┃
┃ 📝 Tasks: X/Y          ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━┛
```

### Progress Visualization

#### Simple Progress Bar
```
Progress: ████████░░ 80%
```

#### Detailed Progress
```
📊 **Weekly Progress**
━━━━━━━━━━ 7/10 tasks
🔥 3-day streak!
💪 Keep going!
```

## 🔲 Button & Keyboard Patterns

### Primary Action Buttons
- Width: Full-width preferred for main actions
- Style: [🎯 Action Text] format
- Order: Most important actions first

### Secondary Actions
- Width: Half-width for paired actions
- Style: [📊 View] [⚙️ Edit] format
- Position: Below primary actions

### Navigation Patterns
```
┌─────────────────────────┐
│ 🎯 Create New Goal      │ ← Primary Action
├─────────────────────────┤
│ 📊 View Progress        │ ← Secondary Action
├─────────────────────────┤  
│ ⚙️ Settings │ ❓ Help   │ ← Utility Actions
└─────────────────────────┘
```

### Menu Structures

#### Main Menu
```
🏠 **Target Assistant**
Choose an action:

🎯 Manage Goals
📝 Daily Tasks  
📊 View Progress
⚙️ Settings
❓ Help & Support
```

#### Context Menus
```
🎯 **Goal: [Name]**
Actions available:

📝 Add Task
📊 View Progress
✏️ Edit Goal
❌ Delete Goal
🔙 Back to Goals
```

## ⚠️ Error Handling Templates

### Error Message Structure
```
❌ **[Error Type]**
[User-friendly error description]

💡 **What you can do:**
• [Solution 1]
• [Solution 2] 
• [Contact support if needed]

[Retry button or back navigation]
```

### Common Error Templates

#### Network/API Errors
```
❌ **Connection Problem**
Unable to connect to the service.

💡 **Try again:**
• Check your internet connection
• Wait a moment and retry
• Contact support if problem persists

[🔄 Retry] [🔙 Back]
```

#### Input Validation Errors
```
❌ **Invalid Input**
[Specific issue with user input]

💡 **Please:**
• [Specific correction needed]
• Example: [Show correct format]

[✏️ Try Again] [❓ Help]
```

#### Feature Unavailable
```
⚠️ **Feature Not Available**
[Feature] is temporarily unavailable.

💡 **Meanwhile:**
• [Alternative action 1]
• [Alternative action 2]

[🔙 Back] [📧 Contact Support]
```

## ♿ Accessibility Guidelines

### Screen Reader Compatibility
- Always provide text alternatives for emojis in critical information
- Use clear, descriptive text for actions
- Maintain logical reading order
- Avoid emoji-only messages for important content

### Clear Language Principles
- Use simple, common words
- Keep sentences short and direct
- Provide context for all actions
- Explain abbreviations and technical terms

### Navigation Support
- Always provide way to return to previous screen
- Offer help commands from any context
- Use consistent terminology for similar actions
- Group related functions logically

## 🌍 Multilingual Considerations

### Russian-First Approach
- Primary language: Russian
- All user-facing content in Russian
- Clear, natural Russian phrasing
- Cultural context consideration

### English Support Preparation
- Template structure supports language switching
- Emoji meanings remain consistent across languages
- Button actions translatable
- Cultural adaptation for different markets

### Text Structure
```python
# Template approach for multilingual support
templates = {
    'ru': {
        'goal_created': '✅ **Цель создана!**\n🎯 {goal_name}\n📅 Дедлайн: {deadline}',
        'task_completed': '🎉 **Задача выполнена!**\n💪 Отличная работа!'
    },
    'en': {
        'goal_created': '✅ **Goal Created!**\n🎯 {goal_name}\n📅 Deadline: {deadline}',
        'task_completed': '🎉 **Task Completed!**\n💪 Great work!'
    }
}
```

## 📏 Implementation Guidelines

### Component Naming Convention
```python
# Message templates naming
msg_[type]_[context]_[state]
# Examples:
msg_goal_create_success
msg_task_list_empty  
msg_error_network_retry
```

### Template Parameters
```python
# Standard template parameters
{
    'user_name': str,        # User's display name
    'emoji': str,           # Context-appropriate emoji
    'title': str,           # Message title
    'content': str,         # Main message content
    'actions': List[str],   # Available actions
    'help_text': str,       # Optional help information
}
```

### Validation Rules
- Maximum message length: 4096 characters (Telegram limit)
- Maximum button text: 64 characters
- Maximum buttons per row: 3
- Maximum rows: 8
- Always include fallback for failed emoji display

## 🔄 Continuous Improvement

### Usage Metrics to Track
- Message clarity (user confusion indicators)
- Action completion rates
- Error recovery success
- User satisfaction feedback
- Accessibility usage patterns

### Regular Review Schedule
- Monthly: Emoji usage effectiveness
- Quarterly: Message template performance  
- Bi-annually: Full style guide review
- As needed: User feedback integration

---

**Version**: 1.0
**Created**: 2025-01-08 (Creative Phase 1)
**Last Updated**: 2025-01-08
**Next Review**: 2025-04-08 