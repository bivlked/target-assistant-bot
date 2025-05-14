"""Prometheus metrics definitions for the TargetBot."""

from prometheus_client import Counter, Gauge, Histogram

# --- LLM Related Metrics ---
LLM_API_CALLS = Counter(
    "targetbot_llm_api_calls_total",
    "Total calls made to the LLM API.",
    ["method_name", "status"],  # e.g., generate_plan, success/error/ratelimited
)

LLM_API_LATENCY = Histogram(
    "targetbot_llm_api_latency_seconds",
    "Latency of LLM API calls in seconds.",
    ["method_name"],
    buckets=(0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0, 7.5, 10.0, float("inf")),
)

# --- Google Sheets Related Metrics ---
SHEETS_API_CALLS = Counter(
    "targetbot_sheets_api_calls_total",
    "Total calls made to the Google Sheets API.",
    ["method_name", "operation_type"],  # e.g., get_goal_info (read), save_plan (write)
)

SHEETS_API_LATENCY = Histogram(
    "targetbot_sheets_api_latency_seconds",
    "Latency of Google Sheets API calls in seconds.",
    ["method_name"],
    buckets=(0.05, 0.1, 0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 5.0, float("inf")),
)

# --- Bot Business Logic Metrics ---
GOALS_SET_TOTAL = Counter(
    "targetbot_goals_set_total", "Total number of new goals set by users."
)

TASKS_STATUS_UPDATED_TOTAL = Counter(
    "targetbot_tasks_status_updated_total",
    "Total number of tasks whose status was updated.",
    ["new_status"],  # e.g., Выполнено, Не выполнено, Частично выполнено
)

USER_COMMANDS_TOTAL = Counter(
    "targetbot_user_commands_total",
    "Total number of commands received from users.",
    ["command_name"],
)

# --- Scheduler Metrics ---
SCHEDULED_JOBS_EXECUTED_TOTAL = Counter(
    "targetbot_scheduled_jobs_executed_total",
    "Total number of scheduled jobs executed.",
    ["job_name", "status"],  # e.g., daily_reminder, success/error
)

# --- Application Info ---
APP_INFO = Gauge(
    "targetbot_app_info",
    "Information about the running application (e.g., version).",
    ["version"],
)

# Example: APP_INFO.labels(version="1.0.0").set(1)
