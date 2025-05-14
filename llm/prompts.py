from typing import Final

PLAN_PROMPT: Final[
    str
] = """Instructs the LLM to generate a daily task plan.

Placeholders:
    {goal_text}: The user's goal description.
    {deadline}: The deadline for the goal.
    {time}: Daily time commitment.

Expected output: A JSON array of objects, each with "day" and "task".
"""

MOTIVATION_PROMPT: Final[
    str
] = """Instructs the LLM to act as a motivational coach.

Placeholders:
    {goal_text}: The user's goal.
    {progress_summary}: A summary of the user's current progress.

Expected output: A short (2-3 sentences, <150 chars) inspirational message in Russian.
"""

# Общий системный промпт для LLM
SYSTEM_PROMPT: Final[str] = (
    """General system prompt to guide LLM behavior across different tasks.

    Emphasizes conciseness, strict adherence to requested formats (especially JSON),
    and a helpful, focused persona for goal setting and planning.
    """
    "You are a helpful assistant focused on goal setting, task planning, and motivation. "
    "Respond concisely and follow the requested format strictly. "
    "If generating JSON, ensure the entire response is a single valid JSON object (e.g., a list of tasks or a structured message)."
)
